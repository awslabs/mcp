#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Migrate servers from MCP Python SDK v1 to v2 (`mcp.server.fastmcp` -> `mcp.server.mcpserver`).

MCP Python SDK 2.0.0 removed the vendored `mcp.server.fastmcp` module outright (it is
gone, not deprecated) and renamed `FastMCP` -> `MCPServer`. PR #4360 capped 44 servers
at `mcp[cli]<2.0.0` as a stopgap. This script performs the mechanical half of reversing
that cap. Tracking issue: https://github.com/awslabs/mcp/issues/4448

What it rewrites:
  1. Import module paths   `mcp.server.fastmcp[.sub]` -> `mcp.server.mcpserver[.sub]`
     (covers the bare module plus the `.tools`, `.prompts`, `.exceptions`, `.server`
     submodules — all seven import forms found in `src/`).
  2. The `FastMCP` identifier -> `MCPServer`, but ONLY in files that imported it from
     `mcp.server.fastmcp`. This matters: several servers use the *standalone* `fastmcp`
     PyPI package, which is a different project that still exports `FastMCP`. Renaming
     those would break them.
  3. String monkeypatch targets such as `patch('mcp.server.fastmcp.FastMCP')`. Both halves
     must move together: rewriting only the module yields `mcp.server.mcpserver.FastMCP`,
     which does not exist and fails at patch time rather than import time. Always flagged
     for review, since a mock that silently stops matching is worse than a hard error.
  4. Attribute *reads* of renamed `mcp.types` fields — `result.isError` -> `result.is_error`,
     `tool.inputSchema` -> `tool.input_schema`, and ~50 more. v2 put a camelCase alias
     generator on every model, so the wire format is unchanged and keyword *construction*
     (`Tool(inputSchema=...)`) still works via the alias — but reading the old spelling
     raises `AttributeError`. That asymmetry is why this shows up as a test failure rather
     than an import error, and why it is by far the largest source of post-rename breakage
     in this repo (964 reads, ~800 of them in two servers).
  5. `McpError` -> `MCPError` in `mcp.shared.exceptions`, another capitalization fix. The
     module path is unchanged, so this one breaks at import rather than at assert time.
  6. That same exception's *constructor*, which v2 flattened:
     `MCPError(ErrorData(code=c, message=m))` -> `MCPError(code=c, message=m)`. Reads of
     `.error`, `.code` and `.message` are unchanged, so as with the field renames only the
     construction sites break — with a `TypeError` when the error is raised. Handled through
     the AST (see `unwrap_errordata`), since the inner call spans lines and its `message=`
     argument routinely holds an f-string with its own parentheses. The now-unused
     `ErrorData` import is pruned along with it, because F401 is enabled fleet-wide.
  7. The dependency cap in `pyproject.toml` -> `>=2.0.0,<3.0.0`, preserving whichever
     extras the server declared (most use `mcp[cli]`; one declares bare `mcp`).

What it deliberately does NOT do:
  - Touch `uv.lock`. Lockfiles are generated artifacts; run `uv lock` per server instead.
    Text-editing them produces a lock matching no real resolution. Verify the result with
    `scripts/verify-mcp-v2-locks.py`: `uv run` resolves from the lock, so a lock left on
    mcp 1.x makes the whole suite pass against the OLD SDK — a false green.
  - Move transport configuration out of `Settings` onto `run()`. v2 removed `port`, `host`,
    `sse_path`, `message_path`, `mount_path`, `json_response`, `stateless_http`,
    `streamable_http_path` and `transport_security` from the settings model and made them
    `run()` keywords, so `mcp.settings.port = p` becomes `mcp.run(transport=..., port=p)`.
    Moving an argument across a call boundary needs human judgement (and usually a matching
    test edit), so affected files are reported, not rewritten. Only
    `well-architected-security-mcp-server` is affected in this repo, and note that pydantic
    intercepts the assignment: the symptom is `ValueError: "Settings" object has no field
    "port"`, not an `AttributeError`.
  - Resolve the standalone-`fastmcp` dependency question for the 4 servers that declare
    that package while also importing `mcp.server.fastmcp`.
  - Rename field reads in servers that do not depend on the `mcp` SDK at all
    (`mcp-lambda-handler` reimplements the protocol; `openapi-mcp-server` uses standalone
    `fastmcp`), or where the server declares its *own* attribute of the same name. Three
    such collisions exist and all are genuine: `sagemaker-ai-mcp-server` defines its own
    `class CallToolResult` with an `isError` field, `aws-healthomics-mcp-server` reads the
    AWS HealthOmics API's `taskId`, and `cloudwatch-mcp-server` has a PromQL `resultType`.
    A blanket rewrite would break all three.

Verification: replaying this script over pristine v1 `lambda-tool-mcp-server` reproduces
the hand-migrated PoC commit byte-for-byte on all 4 files, so it inherits that port's
evidence (56 tests, live stdio handshake). It is also idempotent.

Dry-run by default. Nothing is written without `--apply`.

USAGE
  scripts/migrate-mcp-v2.py                          # dry-run report, whole fleet
  scripts/migrate-mcp-v2.py --server lambda-tool-mcp-server
  scripts/migrate-mcp-v2.py --apply --server iam-mcp-server
  scripts/migrate-mcp-v2.py --json                   # machine-readable

After `--apply` on a server, complete the migration by hand:
  cd src/<server> && uv lock && uv run pytest
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


V1_MODULE = 'mcp.server.fastmcp'
V2_MODULE = 'mcp.server.mcpserver'
V2_BOUNDS = '>=2.0.0,<3.0.0'

# Servers that CANNOT go to v2 yet, blocked upstream rather than by anything in this repo.
# `fastmcp` 3.x depends on `fastmcp-slim`, which pins `mcp>=1.24.0,<2.0`; only the unreleased
# `fastmcp` 4.0 lifts that ceiling. Declaring `mcp>=2.0.0` alongside `fastmcp>=3` makes the
# resolution unsatisfiable, and migrating the *code* would break these servers against the v1
# SDK they are stuck on -- so they are skipped entirely, not partially converted.
#   aws-api, billing-cost-management: depend on `fastmcp>=3` directly
#   dynamodb: inherits it through `awslabs-aws-api-mcp-server`
# Remove entries here once `fastmcp` 4.0 ships stable. Tracking: awslabs/mcp#4448.
BLOCKED_SERVERS = frozenset(
    {
        'aws-api-mcp-server',
        'billing-cost-management-mcp-server',
        'dynamodb-mcp-server',
    }
)

# Rewrites `mcp.server.fastmcp` and any submodule of it, in `from`/`import` statements.
IMPORT_RE = re.compile(r'\bmcp\.server\.fastmcp\b')

# `FastMCP` as a whole identifier. Applied only to files that import it from the v1 module.
IDENT_RE = re.compile(r'\bFastMCP\b')

# v2 normalized the capitalization of the shared exception, `McpError` -> `MCPError`, the
# same way it renamed `FastMCP` -> `MCPServer`. Unlike `FastMCP` there is no same-named class
# in the standalone `fastmcp` package to collide with, and the module path
# (`mcp.shared.exceptions`) is unchanged — so this is safe to rename unconditionally.
MCPERROR_RE = re.compile(r'\bMcpError\b')

# v2 also flattened the exception's constructor. v1 took a prebuilt `ErrorData`
# (`McpError(ErrorData(code=c, message=m))`); v2 takes the fields directly and builds the
# `ErrorData` itself (`MCPError(code=c, message=m)`). Reads still work — `.error.message`
# and `.code` are preserved — so, like the field renames, only the construction sites break,
# and they break with a `TypeError` at raise time rather than at import.
#
# This one cannot be a regex substitution: the call is nested, spans multiple lines, and the
# `message=` argument routinely contains f-strings with their own parentheses and quotes.
# `unwrap_errordata` rewrites it through the AST instead.
MCPERROR_CALL_RE = re.compile(r'\bMCPError\s*\(')

# A single-line `from mcp.types import ... ErrorData ...`, for pruning the import once the
# constructor flattening has removed every use of the name. The separator class is
# "horizontal whitespace" (`[ \t]`) and not `\s`: `\s` matches newlines, so under re.MULTILINE
# the `$` anchor would let the match run past the import and swallow the blank lines after it.
# Parenthesized multi-line imports are not matched and fall through to manual review.
IMPORT_ERRORDATA_RE = re.compile(
    r'^(?P<head>[ \t]*from[ \t]+mcp\.types[ \t]+import[ \t]+)(?P<names>[\w][\w, \t]*)$',
    re.MULTILINE,
)

# Marker standing in for a whole line that is to be removed. `re.sub` cannot delete a line's
# trailing newline (it is outside the match, since `$` is zero-width), so the substitution
# leaves this sentinel and a second pass strips it together with its newline. Chosen to be
# something that cannot occur in real Python source.
_DROP_LINE = '\x00__migrate_mcp_v2_drop_line__'

# The standalone `fastmcp` PyPI package — a DIFFERENT project that also exports `FastMCP`.
# Any file importing from it is excluded from identifier renaming.
STANDALONE_RE = re.compile(r'^\s*(?:from\s+fastmcp[\s.]|import\s+fastmcp\b)', re.MULTILINE)

# A dotted path inside a string literal, e.g. `patch('mcp.server.fastmcp.FastMCP')`.
# These are runtime-resolved monkeypatch targets, so the trailing attribute must be
# renamed too — rewriting only the module half yields `mcp.server.mcpserver.FastMCP`,
# which does not exist and fails at patch time rather than import time.
PATCH_STR_RE = re.compile(r'(["\'])(mcp\.server\.fastmcp)((?:\.\w+)*)\1')

# A patch target aimed at a *server's own* module rather than at the SDK, e.g.
# `patch('awslabs.eks_mcp_server.server.FastMCP')`. `mock.patch` resolves the name on that
# module, and after the import rename the module exports `MCPServer` — so the target must
# follow. Whether to rewrite depends on where that module got `FastMCP` from, which is why
# this is resolved per module (see `mcpserver_exporters`) instead of matched blindly: the
# servers built on the standalone `fastmcp` package patch the same-shaped target and must
# be left alone.
OWN_MODULE_PATCH_RE = re.compile(r'(["\'])([\w.]+)\.FastMCP\1')

STATELESS_RE = re.compile(r'\bstateless_http\s*=')

# The `mcp` / `mcp[cli]` dependency line in pyproject.toml, whatever its current bounds
# and comparison operators. The `[cli]` extra is optional: one server declares bare `mcp`.
DEP_RE = re.compile(r'(["\'])mcp(\[[\w,]+\])?\s*[><=!~][^"\']*\1')

# v2 attached a camelCase alias generator to every `mcp.types` model, so each field has a
# snake_case Python name and a camelCase wire alias. Construction by either name still
# works (`populate_by_name=True`); only *reads* of the old spelling break. Harvested from
# the installed SDK rather than transcribed from docs:
#   for cls in vars(mcp.types).values(): cls.model_fields[f].alias != f
FIELD_RENAMES = {
    'cacheScope': 'cache_scope',
    'clientInfo': 'client_info',
    'costPriority': 'cost_priority',
    'createdAt': 'created_at',
    'destructiveHint': 'destructive_hint',
    'elicitationId': 'elicitation_id',
    'hasMore': 'has_more',
    'idempotentHint': 'idempotent_hint',
    'includeContext': 'include_context',
    'inputRequests': 'input_requests',
    'inputResponses': 'input_responses',
    'inputSchema': 'input_schema',
    'intelligencePriority': 'intelligence_priority',
    'isError': 'is_error',
    'lastModified': 'last_modified',
    'lastUpdatedAt': 'last_updated_at',
    'listChanged': 'list_changed',
    'maxTokens': 'max_tokens',
    'mimeType': 'mime_type',
    'modelPreferences': 'model_preferences',
    'nextCursor': 'next_cursor',
    'openWorldHint': 'open_world_hint',
    'outputSchema': 'output_schema',
    'pollInterval': 'poll_interval',
    'progressToken': 'progress_token',
    'promptsListChanged': 'prompts_list_changed',
    'protocolVersion': 'protocol_version',
    'readOnlyHint': 'read_only_hint',
    'requestId': 'request_id',
    'requestState': 'request_state',
    'requestedSchema': 'requested_schema',
    'requiredCapabilities': 'required_capabilities',
    'resourceSubscriptions': 'resource_subscriptions',
    'resourceTemplates': 'resource_templates',
    'resourcesListChanged': 'resources_list_changed',
    'resultType': 'result_type',
    'serverInfo': 'server_info',
    'speedPriority': 'speed_priority',
    'statusMessage': 'status_message',
    'stopReason': 'stop_reason',
    'stopSequences': 'stop_sequences',
    'structuredContent': 'structured_content',
    'supportedVersions': 'supported_versions',
    'systemPrompt': 'system_prompt',
    'taskId': 'task_id',
    'taskSupport': 'task_support',
    'toolChoice': 'tool_choice',
    'toolUseId': 'tool_use_id',
    'toolsListChanged': 'tools_list_changed',
    'ttlMs': 'ttl_ms',
    'uriTemplate': 'uri_template',
    'websiteUrl': 'website_url',
}

# Attribute access only — `result.isError`, not the keyword form `CallToolResult(isError=...)`
# (which the alias still accepts) nor a quoted dict key `{'isError': ...}` (unrelated data).
FIELD_READ_RE = re.compile(r'\.(' + '|'.join(FIELD_RENAMES) + r')\b')

# A pydantic/dataclass field declaration at class-body indentation, e.g. `    isError: bool`.
# A server declaring its own field of a renamed name is excluded from that rename: the
# attribute belongs to its model, not to `mcp.types`.
OWN_FIELD_RE = re.compile(r'^\s{2,8}(' + '|'.join(FIELD_RENAMES) + r')\s*:\s*\S', re.MULTILINE)


def unwrap_errordata(text: str) -> Tuple[str, int, bool]:
    """Flatten `MCPError(ErrorData(code=c, message=m))` to `MCPError(code=c, message=m)`.

    Returns (new_text, rewrites, needs_review). Operates on the AST because the inner call
    spans lines and its `message=` argument commonly holds an f-string with parentheses of
    its own, which no regex balances reliably. The AST gives exact offsets for the inner call,
    and its argument text is then copied over verbatim — preserving the author's formatting,
    comments, and line breaks instead of unparsing (which would reflow the whole file).

    The span copied runs from the first argument to just *inside* the inner call's own closing
    parenthesis, deliberately not to the last argument's `end_col_offset`. Redundant grouping
    parens are not AST nodes: in `message=(f'...')` the f-string node ends at its closing
    quote, so slicing to the argument's end would drop the author's `)` and emit unbalanced
    source. The inner call's closing paren is the one boundary that always encloses them.

    Call this AFTER the `McpError` -> `MCPError` rename so only the v2 spelling is matched.

    `needs_review` is set when a call looks like the v1 shape but cannot be rewritten safely
    (a splatted `**kwargs`, or `ErrorData` built elsewhere and passed by name). Those are
    reported rather than guessed at.
    """
    if not MCPERROR_CALL_RE.search(text):
        return text, 0, False
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text, 0, True

    # Cumulative character offset of the start of each line, so AST (lineno, col) pairs can be
    # turned into absolute indices into `text`.
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))

    edits, needs_review = [], False
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != 'MCPError':
            continue
        # Already flattened (v2 shape) — `MCPError(code=..., message=...)`.
        if node.keywords and not node.args:
            continue
        inner = node.args[0] if len(node.args) == 1 and not node.keywords else None
        if not (
            isinstance(inner, ast.Call)
            and isinstance(inner.func, ast.Name)
            and inner.func.id == 'ErrorData'
        ):
            # `MCPError(some_error_data)` or `MCPError(**kw)`: v1-shaped but the payload is
            # not constructed inline, so the arguments to forward are not visible here.
            if node.args or any(k.arg is None for k in node.keywords):
                needs_review = True
            continue
        parts = list(inner.args) + [k.value for k in inner.keywords]
        if not parts or any(k.arg is None for k in inner.keywords):
            needs_review = True
            continue

        # `end_lineno`/`end_col_offset` require Python 3.8+, which every server already needs.
        def pos(lineno: int, col: int) -> int:
            return offsets[lineno - 1] + col

        first = min(parts, key=lambda n: pos(n.lineno, n.col_offset))
        # A keyword's own node starts at its *value*, so back up over the `name=` prefix.
        arg_start = pos(first.lineno, first.col_offset)
        for keyword in inner.keywords:
            if keyword.value is first and keyword.arg:
                arg_start = text.rindex(keyword.arg, 0, arg_start)
                break
        inner_start = pos(inner.lineno, inner.col_offset)
        inner_end = pos(inner.end_lineno, inner.end_col_offset)
        # One char back from `inner_end` is the inner call's `)`; everything before it belongs
        # to the arguments, including any grouping parens and trailing comma the author wrote.
        arg_text = text[arg_start : inner_end - 1].rstrip().rstrip(',')
        edits.append((inner_start, inner_end, arg_text))

    # Apply back-to-front so earlier offsets stay valid.
    for start, end, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[end:]
    return text, len(edits), needs_review


def drop_unused_errordata_import(text: str) -> str:
    """Remove `ErrorData` from `mcp.types` imports once nothing references it.

    Flattening the constructors usually leaves the import as the only remaining mention, which
    trips ruff's F401 -- and F401 is enabled fleet-wide (unlike E501, which every server
    ignores), so leaving it behind fails the lint gate. Only runs when zero non-import uses
    remain anywhere in the file.

    Where `ErrorData` was one of several names, it is dropped from the list. Where it was the
    only name, the whole statement goes -- but only if it carries no trailing comment, since
    deleting the line would take the comment with it. Several servers import it inside a test
    function body, which is why the sole-name case has to be handled rather than skipped.
    """
    uses = [
        line
        for line in text.splitlines()
        if 'ErrorData' in line and not re.match(r'\s*(from|import)\s', line)
    ]
    if uses:
        return text

    def _strip(match: re.Match) -> str:
        original = [n.strip() for n in match.group('names').split(',') if n.strip()]
        if 'ErrorData' not in original:
            return match.group(0)
        names = [n for n in original if n != 'ErrorData']
        if names:
            return f'{match.group("head")}{", ".join(names)}'
        if '#' in match.group(0):
            return match.group(0)
        # Sole name and no comment: drop the statement. The sentinel is consumed below along
        # with its newline, so no blank line is left where the import used to be.
        return _DROP_LINE

    pruned = IMPORT_ERRORDATA_RE.sub(_strip, text)
    return pruned.replace(f'{_DROP_LINE}\n', '')


def iter_py(root: Path):
    """Yield the Python files under `root`, skipping virtualenvs and bytecode caches."""
    for path in sorted(root.glob('**/*.py')):
        if '.venv' not in path.parts and '__pycache__' not in path.parts:
            yield path


def find_servers(src_dir: Path) -> List[str]:
    """Return sorted names of servers under `src/` that need any part of the migration.

    A server qualifies if it imports the v1 module, reads a renamed `mcp.types` field, or
    patches a `FastMCP` attribute. These are independent: several servers never import
    `mcp.server.fastmcp` yet still read `result.isError`, and they break under v2 just the
    same. Whether a given patch target actually needs rewriting is settled later by
    `mcpserver_exporters`; this pass only needs to avoid skipping the server outright.
    """
    servers = set()
    for path in src_dir.glob('*/**/*.py'):
        if '.venv' in path.parts or '__pycache__' in path.parts:
            continue
        if path.relative_to(src_dir).parts[0] in BLOCKED_SERVERS:
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        if (
            V1_MODULE in text
            or FIELD_READ_RE.search(text)
            or MCPERROR_RE.search(text)
            or MCPERROR_CALL_RE.search(text)
            or OWN_MODULE_PATCH_RE.search(text)
        ):
            servers.add(path.relative_to(src_dir).parts[0])
    return sorted(servers)


def mcpserver_exporters(root: Path) -> set:
    """Return the dotted module paths in this server that will export `MCPServer` post-rename.

    A module qualifies if it imports the server class from the SDK, under either spelling:
    the v1 `fastmcp`/`FastMCP` form this script rewrites, or the v2 `mcpserver`/`MCPServer`
    form, so the script stays correct on a partially-migrated tree (the imports may already
    have been rewritten in an earlier run while a patch target still lags behind). Modules
    importing from the standalone `fastmcp` package are excluded — they keep exporting
    `FastMCP`, so a patch target aimed at them must not move.

    Used to decide whether `patch('<module>.FastMCP')` should become `.MCPServer`.
    """
    exporters = set()
    for path in iter_py(root):
        try:
            text = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        from_sdk = re.search(
            r'from\s+mcp\.server\.(?:fastmcp|mcpserver)[\w.]*\s+import\s+'
            r'[^\n]*\b(?:FastMCP|MCPServer)\b',
            text,
        )
        if from_sdk and not STANDALONE_RE.search(text):
            # `src/<server>/awslabs/foo/server.py` -> `awslabs.foo.server`
            parts = path.relative_to(root).with_suffix('').parts
            exporters.add('.'.join(parts))
    return exporters


def field_policy(root: Path) -> Dict[str, object]:
    """Decide which renamed fields are safe to rewrite across one server.

    This is a per-server decision, not per-file: a model can be declared in one module and
    read in another, so a file-local check would miss the collision. Two exclusions:

    - The server does not depend on the `mcp` SDK at all. `mcp-lambda-handler` reimplements
      the protocol from scratch and `openapi-mcp-server` uses the standalone `fastmcp`
      package; their camelCase attributes are their own and v2 does not touch them.
    - The server declares its own attribute of the same name, in which case the read
      resolves to that model rather than to `mcp.types`.
    """
    pyproject = root / 'pyproject.toml'
    try:
        depends_on_sdk = bool(DEP_RE.search(pyproject.read_text(encoding='utf-8')))
    except OSError:
        depends_on_sdk = False

    own = set()
    if depends_on_sdk:
        for path in iter_py(root):
            try:
                own.update(m.group(1) for m in OWN_FIELD_RE.finditer(path.read_text('utf-8')))
            except (UnicodeDecodeError, OSError):
                continue

    return {
        'renamable': set() if not depends_on_sdk else set(FIELD_RENAMES) - own,
        'no_sdk_dep': not depends_on_sdk,
        'shadowed': sorted(own),
    }


def plan_file(path: Path, renamable: set, exporters: set) -> Optional[Dict]:
    """Compute the rewrite for one Python file, or None if it needs no change.

    `renamable` is the set of camelCase field names this server may safely rewrite and
    `exporters` the modules whose `FastMCP` becomes `MCPServer`, both decided per server by
    `field_policy` and `mcpserver_exporters`. Returns a dict with the new text plus per-file
    counts and any human-review flags.
    """
    try:
        original = path.read_text(encoding='utf-8')
    except (UnicodeDecodeError, OSError):
        return None
    has_own_patch = any(m.group(2) in exporters for m in OWN_MODULE_PATCH_RE.finditer(original))
    if (
        V1_MODULE not in original
        and not FIELD_READ_RE.search(original)
        and not MCPERROR_RE.search(original)
        # Also match the v2 spelling: the constructor flattening is a separate change, so a
        # file already past the rename can still need it. Harmless when it is already
        # flattened, since a no-op plan returns None below.
        and not MCPERROR_CALL_RE.search(original)
        and not has_own_patch
    ):
        return None

    # String monkeypatch targets first, while the v1 spelling is still intact. These are
    # dotted paths in quotes, so the `FastMCP` attribute at the end must move to
    # `MCPServer` in the same pass regardless of what this file imports.
    def _fix_patch_target(match: re.Match) -> str:
        quote, _, attrs = match.group(1), match.group(2), match.group(3)
        return f'{quote}{V2_MODULE}{attrs.replace(".FastMCP", ".MCPServer")}{quote}'

    updated, patch_hits = PATCH_STR_RE.subn(_fix_patch_target, original)

    # Patch targets naming one of this server's own modules. Only rewrite when that module
    # is confirmed to export `MCPServer` after the rename; otherwise the target still
    # resolves to a real `FastMCP` from the standalone package.
    own_patch_hits = 0

    def _fix_own_patch_target(match: re.Match) -> str:
        nonlocal own_patch_hits
        quote, module = match.group(1), match.group(2)
        if module not in exporters:
            return match.group(0)
        own_patch_hits += 1
        return f'{quote}{module}.MCPServer{quote}'

    updated = OWN_MODULE_PATCH_RE.sub(_fix_own_patch_target, updated)
    patch_hits += own_patch_hits

    # Then the remaining import statements.
    updated, module_hits = IMPORT_RE.subn(V2_MODULE, updated)

    # Only rename the identifier when it demonstrably came from the v1 module, and the
    # file does not also pull from the standalone `fastmcp` package.
    uses_standalone = bool(STANDALONE_RE.search(original))
    imported_v1_class = bool(
        re.search(rf'from\s+{re.escape(V2_MODULE)}[\w.]*\s+import\s+[^\n]*\bFastMCP\b', updated)
    )
    ident_hits = 0
    if imported_v1_class and not uses_standalone:
        updated, ident_hits = IDENT_RE.subn('MCPServer', updated)

    # Renamed `mcp.types` field reads. Only attribute access is touched: keyword arguments
    # still resolve through the camelCase alias, and a same-named dict key is unrelated data.
    # Counted by hand rather than from `subn`, which tallies every *match* — including the
    # ones this function deliberately returns unchanged — and so overstates the diff.
    field_hits = 0
    skipped_fields = set()

    def _rename_field(match: re.Match) -> str:
        nonlocal field_hits
        field = match.group(1)
        if field not in renamable:
            skipped_fields.add(field)
            return match.group(0)
        field_hits += 1
        return f'.{FIELD_RENAMES[field]}'

    updated = FIELD_READ_RE.sub(_rename_field, updated)

    updated, mcperror_hits = MCPERROR_RE.subn('MCPError', updated)
    ident_hits += mcperror_hits

    # Flatten the constructor after the rename, so only the v2 spelling has to be matched.
    updated, unwrap_hits, unwrap_review = unwrap_errordata(updated)
    # Prune the now-dead import whenever this file uses the exception at all, rather than only
    # when this run did the flattening — otherwise a tree that was flattened by an earlier run
    # keeps its unused import forever and the script never converges.
    if MCPERROR_CALL_RE.search(updated):
        updated = drop_unused_errordata_import(updated)

    flags = []
    if unwrap_hits:
        flags.append(f'MCPError(ErrorData(...)) flattened x{unwrap_hits}')
    if unwrap_review:
        flags.append('MCPError call with a non-inline payload: flatten by hand')
    if uses_standalone:
        flags.append('standalone-fastmcp-in-file: identifier rename skipped')
    if patch_hits:
        flags.append(f'string-patch-target x{patch_hits}: rewritten, verify the test still mocks')
    if STATELESS_RE.search(original):
        flags.append('stateless_http: constructor arg moves to run() in v2')
    # A leftover bare `FastMCP` means the name is still referenced but was not renamed —
    # either the file uses the standalone package, or it aliases the import.
    if IDENT_RE.search(updated) and not uses_standalone:
        flags.append('residual FastMCP identifier: needs manual review')
    if skipped_fields:
        flags.append(
            f'field read(s) left alone (shadowed or non-SDK): {", ".join(sorted(skipped_fields))}'
        )

    if updated == original:
        return None
    return {
        'path': str(path),
        'module_renames': module_hits,
        'identifier_renames': ident_hits,
        'field_renames': field_hits,
        'flags': flags,
        'new_text': updated,
    }


def plan_pyproject(path: Path) -> Optional[Dict]:
    """Compute the `mcp[cli]` cap bump for a server's pyproject.toml, or None if absent."""
    try:
        original = path.read_text(encoding='utf-8')
    except OSError:
        return None
    match = DEP_RE.search(original)
    if not match:
        return None
    quote = match.group(1)
    # Preserve whichever extras the server declared; one uses bare `mcp`, not `mcp[cli]`.
    extras = match.group(2) or ''
    replacement = f'{quote}mcp{extras}{V2_BOUNDS}{quote}'
    if match.group(0) == replacement:
        return None
    updated = original[: match.start()] + replacement + original[match.end() :]
    return {
        'path': str(path),
        'old_spec': match.group(0).strip(quote),
        'new_spec': replacement.strip(quote),
        'new_text': updated,
    }


def plan_shared(repo_root: Path) -> Optional[Dict]:
    """Build the change plan for shared code outside `src/`, or None if it needs nothing.

    `testing/` holds an MCP client harness that several servers' integration tests import.
    Because it lives outside `src/`, a purely per-server sweep never reads it — and a single
    stale field read there fails every server that imports it. That is exactly how
    `aws-documentation-mcp-server` regressed on `init_result.serverInfo` while its own files
    were fully migrated. There is no `pyproject.toml` to cap here: these are test helpers
    resolved against whichever server's environment is running them.
    """
    shared = repo_root / 'testing'
    if not shared.is_dir():
        return None
    files = [p for p in (plan_file(f, set(FIELD_RENAMES), set()) for f in iter_py(shared)) if p]
    if not files:
        return None
    return {
        'server': 'testing/ (shared, outside src/)',
        'files': files,
        'pyproject': None,
        'no_sdk_dep': False,
        'shadowed_fields': [],
    }


def plan_server(src_dir: Path, name: str) -> Dict:
    """Build the complete change plan for one server."""
    root = src_dir / name
    policy = field_policy(root)
    exporters = mcpserver_exporters(root)
    files = [p for p in (plan_file(f, policy['renamable'], exporters) for f in iter_py(root)) if p]
    return {
        'server': name,
        'files': files,
        'pyproject': plan_pyproject(root / 'pyproject.toml'),
        'no_sdk_dep': policy['no_sdk_dep'],
        'shadowed_fields': policy['shadowed'],
    }


def apply_plan(plan: Dict) -> int:
    """Write a server's planned rewrites to disk. Returns the number of files written."""
    written = 0
    for entry in plan['files']:
        Path(entry['path']).write_text(entry['new_text'], encoding='utf-8')
        written += 1
    if plan['pyproject']:
        Path(plan['pyproject']['path']).write_text(plan['pyproject']['new_text'], encoding='utf-8')
        written += 1
    return written


def report(plans: List[Dict], applied: bool) -> None:
    """Print a human-readable table of the planned or applied changes."""
    verb = 'Applied' if applied else 'Would change'
    total_files = sum(len(p['files']) for p in plans)
    total_caps = sum(1 for p in plans if p['pyproject'])
    total_fields = sum(e['field_renames'] for p in plans for e in p['files'])
    flagged = []

    print(
        f'{verb}: {total_files} file(s) across {len(plans)} server(s); '
        f'{total_caps} cap bump(s); {total_fields} field read(s)'
    )
    print()
    for plan in plans:
        cap = plan['pyproject']
        cap_note = (
            f'  cap: {cap["old_spec"]} -> {cap["new_spec"]}' if cap else '  cap: (none found)'
        )
        print(f'{plan["server"]}  [{len(plan["files"])} file(s)]')
        print(cap_note)
        if plan['no_sdk_dep']:
            print('  note: no mcp SDK dependency — field reads left alone')
        elif plan['shadowed_fields']:
            print(f'  note: server declares its own {", ".join(plan["shadowed_fields"])}')
        for entry in plan['files']:
            # Trim to a repo-relative-ish path; `testing/` lives outside `src/`.
            rel = (
                entry['path'].split('/src/', 1)[-1]
                if '/src/' in entry['path']
                else (entry['path'].split('/testing/', 1)[-1])
            )
            print(
                f'    {rel}: {entry["module_renames"]} module, '
                f'{entry["identifier_renames"]} identifier, {entry["field_renames"]} field'
            )
            for flag in entry['flags']:
                print(f'      ! {flag}')
                flagged.append((rel, flag))
        print()

    if flagged:
        print(f'Needs manual review ({len(flagged)}):')
        for rel, flag in flagged:
            print(f'  {rel}: {flag}')
        print()

    if not applied:
        print('Dry run — nothing written. Re-run with --apply.')
    print('Next per server: cd src/<server> && uv lock && uv run pytest')


def main() -> int:
    """Parse arguments, build the migration plan, and report or apply it."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument(
        '--server',
        action='append',
        dest='servers',
        help='Server directory name under src/ (repeatable). Default: all affected.',
    )
    parser.add_argument('--apply', action='store_true', help='Write changes (default: dry run).')
    parser.add_argument('--json', action='store_true', help='Emit machine-readable JSON.')
    parser.add_argument(
        '--repo-root',
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help='Repository root (default: parent of scripts/).',
    )
    args = parser.parse_args()

    src_dir = args.repo_root / 'src'
    if not src_dir.is_dir():
        print(f'error: no src/ directory under {args.repo_root}', file=sys.stderr)
        return 2

    names = args.servers or find_servers(src_dir)
    missing = [n for n in names if not (src_dir / n).is_dir()]
    if missing:
        print(f'error: unknown server(s): {", ".join(missing)}', file=sys.stderr)
        return 2

    # `find_servers` already filters these out; this catches an explicit `--server` naming one.
    # Refuse rather than warn: a half-migrated blocked server is broken against both SDKs.
    blocked = sorted(set(names) & BLOCKED_SERVERS)
    if blocked:
        print(
            f'error: {", ".join(blocked)} cannot migrate to v2 yet -- fastmcp 3.x pins\n'
            'mcp<2.0 transitively (via fastmcp-slim), so the resolution is unsatisfiable.\n'
            'Remove from BLOCKED_SERVERS once fastmcp 4.0 ships. See awslabs/mcp#4448.',
            file=sys.stderr,
        )
        return 2

    plans = [p for p in (plan_server(src_dir, n) for n in names) if p['files'] or p['pyproject']]

    # Shared test helpers outside `src/`, unless the run was narrowed to specific servers.
    if not args.servers:
        shared = plan_shared(args.repo_root)
        if shared:
            plans.append(shared)

    if args.apply:
        for plan in plans:
            apply_plan(plan)

    if args.json:
        for plan in plans:
            for entry in plan['files']:
                entry.pop('new_text', None)
            if plan['pyproject']:
                plan['pyproject'].pop('new_text', None)
        print(json.dumps({'applied': args.apply, 'servers': plans}, indent=2))
    else:
        report(plans, args.apply)
    return 0


if __name__ == '__main__':
    sys.exit(main())
