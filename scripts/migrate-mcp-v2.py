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
  4. The dependency cap in `pyproject.toml` -> `>=2.0.0,<3.0.0`, preserving whichever
     extras the server declared (most use `mcp[cli]`; one declares bare `mcp`).

What it deliberately does NOT do:
  - Touch `uv.lock`. Lockfiles are generated artifacts; run `uv lock` per server instead.
    Text-editing them produces a lock matching no real resolution.
  - Move `stateless_http=` from the constructor to `run()` (a real v2 change, but it needs
    human judgement). Affected files are reported, not rewritten.
  - Resolve the standalone-`fastmcp` dependency question for the 4 servers that declare
    that package while also importing `mcp.server.fastmcp`.

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
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional


V1_MODULE = 'mcp.server.fastmcp'
V2_MODULE = 'mcp.server.mcpserver'
V2_BOUNDS = '>=2.0.0,<3.0.0'

# Rewrites `mcp.server.fastmcp` and any submodule of it, in `from`/`import` statements.
IMPORT_RE = re.compile(r'\bmcp\.server\.fastmcp\b')

# `FastMCP` as a whole identifier. Applied only to files that import it from the v1 module.
IDENT_RE = re.compile(r'\bFastMCP\b')

# The standalone `fastmcp` PyPI package — a DIFFERENT project that also exports `FastMCP`.
# Any file importing from it is excluded from identifier renaming.
STANDALONE_RE = re.compile(r'^\s*(?:from\s+fastmcp[\s.]|import\s+fastmcp\b)', re.MULTILINE)

# A dotted path inside a string literal, e.g. `patch('mcp.server.fastmcp.FastMCP')`.
# These are runtime-resolved monkeypatch targets, so the trailing attribute must be
# renamed too — rewriting only the module half yields `mcp.server.mcpserver.FastMCP`,
# which does not exist and fails at patch time rather than import time.
PATCH_STR_RE = re.compile(r'(["\'])(mcp\.server\.fastmcp)((?:\.\w+)*)\1')

STATELESS_RE = re.compile(r'\bstateless_http\s*=')

# The `mcp` / `mcp[cli]` dependency line in pyproject.toml, whatever its current bounds
# and comparison operators. The `[cli]` extra is optional: one server declares bare `mcp`.
DEP_RE = re.compile(r'(["\'])mcp(\[[\w,]+\])?\s*[><=!~][^"\']*\1')


def find_servers(src_dir: Path) -> List[str]:
    """Return sorted names of servers under `src/` whose Python files still import v1."""
    servers = set()
    for path in src_dir.glob('*/**/*.py'):
        if '.venv' in path.parts or '__pycache__' in path.parts:
            continue
        try:
            if V1_MODULE in path.read_text(encoding='utf-8'):
                servers.add(path.relative_to(src_dir).parts[0])
        except (UnicodeDecodeError, OSError):
            continue
    return sorted(servers)


def plan_file(path: Path) -> Optional[Dict]:
    """Compute the rewrite for one Python file, or None if it needs no change.

    Returns a dict with the new text plus per-file counts and any human-review flags.
    """
    try:
        original = path.read_text(encoding='utf-8')
    except (UnicodeDecodeError, OSError):
        return None
    if V1_MODULE not in original:
        return None

    # String monkeypatch targets first, while the v1 spelling is still intact. These are
    # dotted paths in quotes, so the `FastMCP` attribute at the end must move to
    # `MCPServer` in the same pass regardless of what this file imports.
    def _fix_patch_target(match: re.Match) -> str:
        quote, _, attrs = match.group(1), match.group(2), match.group(3)
        return f'{quote}{V2_MODULE}{attrs.replace(".FastMCP", ".MCPServer")}{quote}'

    updated, patch_hits = PATCH_STR_RE.subn(_fix_patch_target, original)

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

    flags = []
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

    if updated == original:
        return None
    return {
        'path': str(path),
        'module_renames': module_hits,
        'identifier_renames': ident_hits,
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


def plan_server(src_dir: Path, name: str) -> Dict:
    """Build the complete change plan for one server."""
    root = src_dir / name
    files = []
    for path in sorted(root.glob('**/*.py')):
        if '.venv' in path.parts or '__pycache__' in path.parts:
            continue
        planned = plan_file(path)
        if planned:
            files.append(planned)
    return {
        'server': name,
        'files': files,
        'pyproject': plan_pyproject(root / 'pyproject.toml'),
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
    flagged = []

    print(f'{verb}: {total_files} file(s) across {len(plans)} server(s); {total_caps} cap bump(s)')
    print()
    for plan in plans:
        cap = plan['pyproject']
        cap_note = (
            f'  cap: {cap["old_spec"]} -> {cap["new_spec"]}' if cap else '  cap: (none found)'
        )
        print(f'{plan["server"]}  [{len(plan["files"])} file(s)]')
        print(cap_note)
        for entry in plan['files']:
            rel = entry['path'].split('/src/', 1)[-1]
            print(
                f'    {rel}: {entry["module_renames"]} module, '
                f'{entry["identifier_renames"]} identifier'
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

    plans = [p for p in (plan_server(src_dir, n) for n in names) if p['files'] or p['pyproject']]

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
