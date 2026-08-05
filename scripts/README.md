# Scripts

This directory contains utility scripts for the MCP project.

## migrate-mcp-v2.py

Migrates servers from MCP Python SDK v1 to v2, reversing the `mcp[cli]<2.0.0` cap added in
PR #4360. SDK 2.0.0 removed `mcp.server.fastmcp` outright and renamed `FastMCP` ->
`MCPServer`.

### Usage

```bash
scripts/migrate-mcp-v2.py                                   # dry-run report, whole fleet
scripts/migrate-mcp-v2.py --server lambda-tool-mcp-server   # one server
scripts/migrate-mcp-v2.py --apply --server iam-mcp-server   # write changes
scripts/migrate-mcp-v2.py --json                            # machine-readable
```

**Dry-run by default** — nothing is written without `--apply`.

### What it does

1. Rewrites all seven v1 import forms to `mcp.server.mcpserver[.sub]`.
2. Renames the `FastMCP` identifier to `MCPServer`, but only in files that imported it from
   `mcp.server.fastmcp` — never in files using the standalone `fastmcp` PyPI package, which
   is a different project that also exports `FastMCP`.
3. Rewrites string monkeypatch targets, both `patch('mcp.server.fastmcp.FastMCP')` and the
   indirect `patch('awslabs.<server>.server.FastMCP')` form, and flags each for review. The
   indirect form is resolved per module: it is rewritten only when that module is confirmed
   to export `MCPServer` after the rename, so servers built on standalone `fastmcp` — which
   patch an identically-shaped target — are left alone.
4. Renames reads of the ~50 `mcp.types` fields that v2 moved from camelCase to snake_case
   (`result.isError` → `result.is_error`, `tool.inputSchema` → `tool.input_schema`, …). See
   below for why this is the largest source of breakage.
5. Renames `McpError` → `MCPError` and flattens its constructor, which v2 changed from taking
   a prebuilt `ErrorData` to taking the fields directly:
   `MCPError(ErrorData(code=c, message=m))` → `MCPError(code=c, message=m)`. Done through the
   AST, since the inner call spans lines and `message=` routinely holds an f-string with its
   own parentheses. The now-dead `ErrorData` import is pruned too (`F401` is enabled fleet-wide).
6. Bumps the dependency to `>=2.0.0,<3.0.0`, preserving declared extras.

It does **not** touch `uv.lock` (generated — run `uv lock`, then check the result with
`verify-mcp-v2-locks.py`). It also does not move transport settings from `Settings` onto
`run()`: v2 dropped `port`, `host`, `stateless_http`, `sse_path` and friends from the settings
model in favour of `run()` keywords, so `mcp.settings.port = p` becomes
`mcp.run(transport=…, port=p)`. Moving an argument across a call boundary usually needs a
matching test change, so affected files are reported rather than rewritten. Note that pydantic
intercepts the assignment: the symptom is `ValueError: "Settings" object has no field "port"`,
not `AttributeError`.

Six servers are **skipped entirely** (`BLOCKED_SERVERS`), blocked upstream rather than by
anything here. `fastmcp` 3.x pins `mcp>=1.24.0,<2.0` through `fastmcp-slim`, and only the
unreleased `fastmcp` 4.0 lifts that ceiling. It bites in two ways, and the second is the
dangerous one:

1. **Loud.** The server's `fastmcp` floor is already `>=3`, so `mcp>=2.0.0` has no solution
   and `uv lock` fails outright: `aws-api` and `billing-cost-management` (direct `fastmcp>=3`
   dependents) and `dynamodb` (which inherits it via `awslabs-aws-api-mcp-server`).
2. **Silent.** The server's `fastmcp` floor *predates* that pin (`>=2.14.0`, `>=2.13.1`), so
   the resolver does not fail — it walks **backward** to a `fastmcp` old enough to accept
   mcp 2.x. In practice that is 2.14.1, which carries 4 known advisories, one CRITICAL. The
   result is a green test suite and a security regression at the same time:
   `amazon-keyspaces`, `amazon-translate`, `aws-iot-sitewise`.

Case 2 is exactly what `verify-mcp-v2-locks.py` is for; case 1 catches itself. A raised
dependency floor is not automatically a raised *resolved* version — always diff the lock.

Naming a blocked server with `--server` is a hard error, because a half-migrated blocked
server is broken against both SDKs.

### The field renames are the hard part

v2 attaches a camelCase alias generator to every `mcp.types` model. The wire format is
unchanged and keyword construction still works through the alias, so `Tool(inputSchema=…)`
is still valid — but **reading** the old spelling now raises `AttributeError`:

```python
tool = Tool(name='x', inputSchema={...})  # fine: camelCase alias accepted
tool.input_schema                          # fine
tool.inputSchema                           # AttributeError
```

That asymmetry is why this surfaces as a pile of test failures rather than an import error,
and why it dwarfs the rename itself: 964 reads across 9 servers, ~800 of them in
`aws-dataprocessing-mcp-server` and `eks-mcp-server` alone.

Keyword *construction* is rewritten too, but only for servers actually on v2. It is not a
correctness fix — `CallToolResult(isError=True)` resolves through the alias and serializes
identically — it is a type-checking fix, because pydantic's stubs synthesize `__init__` from
field *names*, so pyright rejects the alias spelling. The gate matters: under v1,
`Tool.model_fields` literally contains `inputSchema` as the real field name, so renaming it in
a server still on v1 breaks it. `healthlake-mcp-server` is exactly that case — still on
`mcp>=1.23.0`, constructing `Tool(inputSchema=…)` 11 times — and is left alone. A server
being migrated in the same pass counts as v2, since the cap bump lands with the rename.

Attribute *reads* are always rewritten; a same-named dict key is unrelated data and is left
alone. Three servers are excluded because they declare
their *own* attribute of a renamed name (`sagemaker-ai-mcp-server` defines its own
`CallToolResult.isError`, `aws-healthomics-mcp-server` reads the HealthOmics API's `taskId`,
`cloudwatch-mcp-server` has a PromQL `resultType`), as are servers with no `mcp` SDK
dependency at all (`mcp-lambda-handler` reimplements the protocol; `openapi-mcp-server` and
`ecs-mcp-server` use standalone `fastmcp`). The report names every skipped read.

### Completing a migration

```bash
scripts/migrate-mcp-v2.py --apply --server <name>
cd src/<name> && uv lock && uv run pytest
python3 scripts/verify-mcp-v2-locks.py          # confirm the lock actually moved to 2.x
```

The rename and the cap bump must land in the same commit — v2-only imports break under a
1.x resolution.

Classify every failure against unmodified `origin/main` before calling it a regression: this
repo has a steady background of environment-dependent failures, and a suite that fails
identically on both sides is not this migration's doing.

### Expect a wall of pyright errors that the codemod cannot fix

v1 typed `tool()` as `Callable[[AnyFunction], AnyFunction]` where `AnyFunction =
Callable[..., Any]`, which erased every decorated tool's signature to `(...) -> Any`. v2 uses
a TypeVar and preserves it. **No call site changes** — v2 just stops hiding errors that were
always there. The fleet rollout surfaced 371 of them, and every one was a pre-existing defect:
mock contexts that never structurally matched `Context`, `None` passed to `str` parameters,
tuples passed to `List[str]`, a pytest fixture *function* passed where an instance was
expected, and four tests whose `pytest.raises(Exception)` was actually catching
`TypeError: missing 1 required positional argument` rather than the AWS error they claimed to
assert.

`pyright` runs at pre-commit **`stages: [pre-push]`**, so `pre-commit run --files …` never
exercises it. Run it per server directly:

```bash
cd src/<name> && uv run pyright          # some servers declare dev tools as an
                                         # optional extra: add --extra dev
```

Per-server config can also hide real errors — `aws-dataprocessing-mcp-server` sets
`reportCallIssue = false`, which masks 354 alias-spelled keyword arguments.

See https://github.com/awslabs/mcp/issues/4448 for the full migration plan and the list of
servers needing individual review.

## verify-mcp-v2-locks.py

Checks that every server's `uv.lock` agrees with the `mcp` bound in its `pyproject.toml`.

```bash
python3 scripts/verify-mcp-v2-locks.py            # report
python3 scripts/verify-mcp-v2-locks.py --strict   # exit 1 on any mismatch
```

`uv run pytest` resolves from `uv.lock`, not from `pyproject.toml`. A lock predating a cap
change keeps installing the old SDK, so the suite passes **against v1** while the manifest
claims v2 — a green run that proves nothing. This caught three such servers during the fleet
rollout. A mismatch can also mean the resolution is genuinely unsatisfiable (a transitive
dependency pinning `mcp<2.0`); `uv lock` reports that loudly, but only if you re-lock.

## verify_package_name.py

A Python script that verifies package name consistency between `pyproject.toml` and `README.md` files.

### Usage

```bash
python3 scripts/verify_package_name.py <package_directory> [--verbose]
```

### Examples

```bash
# Basic usage
python3 scripts/verify_package_name.py src/amazon-neptune-mcp-server

# Verbose output
python3 scripts/verify_package_name.py src/amazon-neptune-mcp-server --verbose
```

### What it does

1. Extracts the package name from the `pyproject.toml` file in the specified directory
2. Searches the `README.md` file for package name references in installation instructions, including:
   - JSON configuration blocks
   - Command-line examples (`uvx`, `uv tool run`, `pip install`)
   - Cursor installation links (with Base64-encoded config)
   - VS Code installation links (with URL-encoded JSON config)
   - Docker run commands
3. Intelligently filters out false positives like:
   - AWS service references (e.g., `aws.s3@ObjectCreated`)
   - JSON configuration keys
   - Command-line flags
   - Common non-package words
4. Verifies that all package references match the actual package name from `pyproject.toml`
5. Reports any mismatches that could lead to installation errors, including line numbers for easy debugging

### Integration

This script is automatically run as part of the GitHub Actions workflow for each MCP server to ensure package name consistency.

### Dependencies

- Python 3.10+
- `tomli` package (for Python < 3.11) or built-in `tomllib` (for Python 3.11+)

The script will automatically try to use the built-in `tomllib` (Python 3.11+) first, then fall back to `tomli` if needed.

Install tomli if needed:
```bash
pip install tomli
```
