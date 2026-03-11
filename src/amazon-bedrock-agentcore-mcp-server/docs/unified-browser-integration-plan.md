# Plan: Integrate Browser Tools into Unified AgentCore MCP Server

**Status**: Final
**Date**: 2026-03-10
**Goal**: Backfill the 25-tool browser MCP server (standalone PR #2510) into the unified `amazon-bedrock-agentcore-mcp-server`, making browser discoverable to every developer who already has the docs server installed.

## Context

The standalone browser MCP server ([PR #2510](https://github.com/awslabs/mcp/pull/2510)) is stalled in review. Meanwhile, the [AgentCore Claude Code Integration](https://quip-amazon.com/hnyFA8aYXmSh/AgentCore-Claude-Code-Integration) strategy doc proposes a unified server covering all 9 AgentCore primitives. Competitor research confirms:

- **GitHub** (80 tools, one server) and **Vercel** (one server) unify when it's one product
- **AWS awslabs/mcp** (66 servers), **GCP** (separate repos), **Cloudflare** (14 servers) split by service
- AgentCore's adoption bottleneck favors the unified approach: developers who install for docs should discover browser tools without a second install

This PR creates the template for how all future primitives (Code Interpreter, Memory, Policy, etc.) integrate into the unified server.

> **Divergence from strategy doc**: The [AgentCore Claude Code Integration](https://quip-amazon.com/hnyFA8aYXmSh/AgentCore-Claude-Code-Integration) strategy doc recommends optional extras (`[browser]`, `[code-interpreter]`). After refinement, we chose **all deps in base** instead — discovery trumps install size. This is a deliberate two-way door: the opt-in/opt-out env var mechanism means we can migrate to optional extras later if install weight becomes a problem at scale.

## Source Locations

| What | Path |
|------|------|
| **Unified server (target)** | `/Volumes/workplace/test-browser-mcp2/src/amazon-bedrock-agentcore-mcp-server/` |
| **Browser server (source)** | `/Volumes/workplace/test-browser-mcp2/src/agentcore-browser-mcp-server/` |
| **Monorepo root** | `/Volumes/workplace/test-browser-mcp2/` |
| **Fork remote** | `origin` = `github.com/kevin-orellana/mcp.git` |
| **Upstream remote** | `upstream` = `github.com/awslabs/mcp.git` |
| **Main branch** | `main` |

> **Note**: Both directories are in the same fork repo (monorepo). We work in `src/amazon-bedrock-agentcore-mcp-server/` and copy code from the sibling `src/agentcore-browser-mcp-server/`.

## Approach: `tools/browser/` Sub-Package with All Deps in Base

### Why a sub-package (not a single file)

The browser code has 25 tools across 5 categories, 2 stateful managers (ConnectionManager, SnapshotManager), models, error utilities, and an AWS client wrapper. A single `tools/browser.py` would be ~2,500 lines. A sub-package preserves the proven modular structure.

### Why all deps in base (not optional extras)

The whole point of a unified server is discovery. If a developer has to know to `pip install ...[browser]`, they already know browser exists — defeating the purpose. Per-primitive extras (`[browser]`, `[code-interpreter]`, etc.) fragment the experience.

All primitive dependencies go into base `[project.dependencies]`. One install, all tools, zero friction. The weight tradeoff (~50MB from playwright) is acceptable because the target user is a developer who wants AgentCore tools — not a minimal docs reader.

**Two-way door**: The opt-in/opt-out env var mechanism (`AGENTCORE_DISABLE_TOOLS`, `AGENTCORE_ENABLE_TOOLS`) plus lazy imports (`if _is_primitive_enabled('browser'): from .tools.browser import ...`) means we can move deps to optional extras later without changing any server.py code — just a `pyproject.toml` move plus a `try/except ImportError` guard.

### Key design: Self-contained sub-packages with opt-out

Each primitive sub-package owns its own tool registration logic. The browser module handles
manager creation and tool registration internally — `server.py` just calls
`register_browser_tools(mcp)` and doesn't need to know about Playwright internals.

Lifecycle management (cleanup task, signal handlers) lives in `server.py`'s `server_lifespan()`
because FastMCP only accepts `lifespan` as a **constructor parameter** — no post-init mutation
works (verified against FastMCP source). Each primitive exports its cleanup needs, and
`server_lifespan()` composes them.

```python
# tools/browser/__init__.py
from .connection_manager import BrowserConnectionManager
from .snapshot_manager import SnapshotManager
# ... other imports ...

def register_browser_tools(mcp):
    """Create managers, register 25 tools, return managers for lifecycle use."""
    connection_manager = BrowserConnectionManager()
    snapshot_manager = SnapshotManager()
    groups = [
        ('session', BrowserSessionTools),
        ('navigation', NavigationTools),
        ('interaction', InteractionTools),
        ('observation', ObservationTools),
        ('management', ManagementTools),
    ]
    for name, cls in groups:
        try:
            cls(connection_manager, snapshot_manager).register(mcp)
        except Exception as e:
            raise RuntimeError(f'Failed to register browser {name} tools: {e}') from e
    return connection_manager, snapshot_manager

async def cleanup_stale_sessions(connection_manager, snapshot_manager):
    """Background coroutine — prune stale Playwright connections."""
    ...
```

### Primitive opt-out via environment variable

By default all primitives are enabled (maximum discovery). Developers can disable
specific primitives to reduce tool namespace noise:

```bash
# Disable browser and code-interpreter, keep docs/runtime/memory/gateway
AGENTCORE_DISABLE_TOOLS=browser,code_interpreter

# Or use allowlist mode — only enable specific primitives
AGENTCORE_ENABLE_TOOLS=docs,browser
```

Implementation in `server.py` (case-insensitive, validates edge cases):
```python
def _is_primitive_enabled(name: str) -> bool:
    """Check if a primitive should be registered."""
    disable = os.getenv('AGENTCORE_DISABLE_TOOLS', '')
    enable = os.getenv('AGENTCORE_ENABLE_TOOLS', '')

    if enable and disable:
        logger.warning(
            'Both AGENTCORE_ENABLE_TOOLS and AGENTCORE_DISABLE_TOOLS are set. '
            'AGENTCORE_ENABLE_TOOLS takes precedence; AGENTCORE_DISABLE_TOOLS is ignored.'
        )

    if enable:
        allowed = {t.strip().lower() for t in enable.split(',') if t.strip()}
        if not allowed:
            logger.warning(
                'AGENTCORE_ENABLE_TOOLS is set but contains no valid entries. '
                'All primitives enabled.'
            )
            return True
        return name.lower() in allowed
    if disable:
        blocked = {t.strip().lower() for t in disable.split(',') if t.strip()}
        return name.lower() not in blocked
    return True
```

**Docs tools are always registered** regardless of opt-in/opt-out settings. They are the
core functionality of the server and have zero external dependencies. All other primitives
(runtime, memory, gateway, browser, etc.) respect the env var checks.

### Why opt-out matters at scale

At 30 tools (5 core + 25 browser) the namespace is manageable. But as all primitives
become real tool sets, the projected total is **80-110 tools**:

| Primitive | Est. Tools | Prefix Pattern |
|-----------|-----------|----------------|
| Docs | 2 | `search_agentcore_docs`, `fetch_agentcore_doc` |
| Browser | 25 | `browser_*`, `start/get/stop/list_browser_session` |
| Code Interpreter | 10-15 | `code_*` or `interpreter_*` |
| Runtime | 8-12 | `runtime_*` or `agent_*` |
| Memory | 8-10 | `memory_*` |
| Gateway | 8-10 | `gateway_*` |
| Observability | 5-8 | `observability_*` or `traces_*` |
| Identity | 5-8 | `identity_*` or `auth_*` |
| Policy | 5-8 | `policy_*` |
| Payments | 3-5 | `billing_*` or `usage_*` |

A developer using only Browser + Code Interpreter shouldn't see 50+ irrelevant Memory/Gateway/Policy tools in their tool list. Opt-out (or opt-in) keeps the namespace clean for power users while preserving full discovery as the default.

## Target Package Structure

```
awslabs/amazon_bedrock_agentcore_mcp_server/
  server.py                          # MODIFIED - instructions, lifespan, opt-out, browser registration
  config.py                          # UNCHANGED
  tools/
    docs.py                          # UNCHANGED
    runtime.py                       # UNCHANGED
    memory.py                        # UNCHANGED
    gateway.py                       # UNCHANGED
    browser/                         # NEW - 11 source files
      __init__.py                    # register_browser_tools() + cleanup_stale_sessions()
      connection_manager.py          # Playwright CDP connections (+idempotent cleanup)
      snapshot_manager.py            # Accessibility tree capture
      aws_client.py                  # BrowserClient SDK wrapper (browser-specific)
      models.py                      # Pydantic response models
      error_handler.py               # Shared error utilities
      session.py                     # 4 session tools
      navigation.py                  # 3 navigation tools
      interaction.py                 # 9 interaction tools
      observation.py                 # 5-6 observation tools
      management.py                  # 3 management tools
  utils/                             # UNCHANGED (all existing files)
tests/
  (existing 11 test files)           # UNCHANGED (except test_main.py — minor update)
  browser/                           # NEW - 11 test files
    __init__.py
    conftest.py                      # Browser-specific fixtures
    test_unit_session.py             # Migrated from standalone
    test_unit_connection.py          # Migrated from standalone
    test_unit_snapshot.py            # Migrated from standalone
    test_unit_interaction.py         # Migrated from standalone
    test_unit_management.py          # Migrated from standalone
    test_unit_observation.py         # NEW — write from scratch (no source test exists)
    test_unit_error_handler.py       # Migrated from standalone
    test_unit_aws_client.py          # Migrated from standalone
    test_unit_server_integration.py  # NEW — registration, lifespan, opt-out, cleanup tests
    test_integ_browser_session.py    # @pytest.mark.live — migrated from standalone
```

## Implementation Phases

### Phase 1: Branch & Sync Fork

```bash
git -C /Volumes/workplace/test-browser-mcp2 fetch upstream main
git -C /Volumes/workplace/test-browser-mcp2 checkout -b feature/unified-browser-integration upstream/main
```

### Phase 2: Copy & Rewrite Browser Source (11 files)
- Copy all browser source files into `tools/browser/`
- Rewrite all imports from absolute `awslabs.agentcore_browser_mcp_server.*` to relative `from .module import ...`
- Create `__init__.py` with `register_browser_tools()` and `cleanup_stale_sessions()`
- **Make `BrowserConnectionManager.cleanup()` idempotent**: Add `self._cleaned_up = False` to `__init__()`, add guard `if self._cleaned_up: return` at top of `cleanup()`, set `self._cleaned_up = True` before cleanup logic. This is required because both the signal handler and the lifespan `finally` block call `cleanup()`.
- See Appendix A for file-by-file details

### Phase 3: Integrate with Unified Server (3 files)

**`server.py`** (~90 lines, up from 46):

1. Add `_is_primitive_enabled()` opt-out helper (case-insensitive, validates edge cases)
2. Add `AGENTCORE_MCP_INSTRUCTIONS` constant (see below)
3. Add `server_lifespan()` context manager with signal handlers and browser cleanup
4. Change `FastMCP(APP_NAME)` to `FastMCP(APP_NAME, instructions=AGENTCORE_MCP_INSTRUCTIONS, lifespan=server_lifespan)`
5. Wrap existing tool registrations in `_is_primitive_enabled()` checks (docs always-on)
6. Add conditional browser import and registration **with `try/except ImportError` guard**
7. Update `tests/test_main.py`: add assertion that `mcp.settings.lifespan is server_lifespan`

**`instructions` constant** — forward-looking, covers all primitives with light references. Browser tips ported verbatim from standalone server (`server.py:92-116`):

```python
AGENTCORE_MCP_INSTRUCTIONS = (
    'Use this MCP server to access Amazon Bedrock AgentCore services — '
    'cloud browser sessions, code interpreter sandboxes, agent runtime, '
    'memory, gateway, identity, policy, evaluations, and documentation.\n\n'
    '## Browser Tools\n'
    'Start a browser session with start_browser_session, then use browser '
    'interaction tools (browser_navigate, browser_snapshot, browser_click, '
    'browser_type, etc.) to interact with web pages. Each session runs in an '
    'isolated cloud environment — no local browser installation is required. '
    'Call stop_browser_session when done.\n\n'
    'Tips:\n'
    '- Use DuckDuckGo or Bing instead of Google — Google blocks cloud browser '
    'IPs with CAPTCHAs.\n'
    '- For content-heavy pages, use browser_evaluate with JavaScript to extract '
    'specific data instead of relying solely on the accessibility snapshot, '
    'which can be very large.\n'
    '- For data extraction, prefer browser_evaluate over browser_snapshot. '
    'Use querySelectorAll to extract structured JSON (e.g., '
    '`[...document.querySelectorAll("tr")].map(r => r.innerText)`). '
    'Snapshots are best for understanding page structure and finding element refs; '
    'evaluate is best for extracting actual text and data.\n'
    '- To set long text in form fields, use browser_evaluate with '
    '`document.querySelector("selector").value = "text"` instead of browser_type '
    'or browser_fill_form, which type character-by-character and may timeout on '
    'long inputs.\n'
    '- The timeout_seconds parameter on start_browser_session is an idle timeout '
    'measured from the last activity, not an absolute session duration. Active '
    'sessions persist as long as there is interaction within the timeout window.'
)
```

> **Future primitives**: When Code Interpreter lands, add a `## Code Interpreter Tools` section. Each primitive team appends their section. Keep the opening sentence as the unified summary.

**Signal handlers** — centralized in `server_lifespan()`, not in the browser module. The MCP SDK does NOT handle SIGTERM/SIGINT — without explicit handlers, SIGTERM kills the process before `finally` runs. Capture `_browser_cm` via default argument to avoid late-binding bugs. `cleanup()` is idempotent (see Phase 2).

```python
@asynccontextmanager
async def server_lifespan(server) -> AsyncIterator[None]:
    if _browser_cm is not None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig, lambda cm=_browser_cm: asyncio.ensure_future(cm.cleanup())
            )
        task = asyncio.create_task(cleanup_stale_sessions(_browser_cm, _browser_sm))
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            await _browser_cm.cleanup()  # idempotent — safe if signal handler already called it
    else:
        yield
    # Future: add code_interpreter cleanup block here
```

> **Signal handler ownership**: Only `server_lifespan()` registers signal handlers. Primitive modules MUST NOT register their own — `loop.add_signal_handler()` replaces any previous handler for the same signal. When a second primitive needs signal cleanup, add it to the existing handler lambda.

**Browser registration with graceful degradation** — if playwright or bedrock-agentcore has a platform-specific import failure, log clearly and degrade to docs-only mode instead of crashing the entire server:

```python
# Docs always registered (no opt-out)
mcp.tool()(docs.search_agentcore_docs)
mcp.tool()(docs.fetch_agentcore_doc)

if _is_primitive_enabled('runtime'):
    mcp.tool()(runtime.manage_agentcore_runtime)
if _is_primitive_enabled('memory'):
    mcp.tool()(memory.manage_agentcore_memory)
if _is_primitive_enabled('gateway'):
    mcp.tool()(gateway.manage_agentcore_gateway)
if _is_primitive_enabled('browser'):
    try:
        from .tools.browser import register_browser_tools, cleanup_stale_sessions
        _browser_cm, _browser_sm = register_browser_tools(mcp)
        logger.info('Browser tools registered (25 tools)')
    except ImportError as e:
        logger.error(
            f'Browser tools disabled — failed to import dependencies: {e}. '
            f'Ensure playwright and bedrock-agentcore are installed.'
        )
    except Exception as e:
        logger.error(
            f'Browser tools disabled — initialization failed: {e}. '
            f'Set AGENTCORE_DISABLE_TOOLS=browser to suppress.'
        )
```

> **Lazy import**: Browser import is inside the `if` block. If `_is_primitive_enabled('browser')` returns False, browser modules are never imported. If the import fails, the server continues with 5 core tools instead of crashing.

> **Composability**: When a second primitive needs lifespan (e.g., Code Interpreter), add another conditional block to `server_lifespan()`. At 3+ stateful primitives, consider extracting a `LifespanRegistry` pattern.

**`pyproject.toml`**:

```diff
  dependencies = [
      "loguru>=0.7.0",
      "mcp[cli]>=1.23.0",
-     "fastmcp>=2.14.0",
      "pydantic>=2.10.6",
+     "bedrock-agentcore>=1.1.0,<2.0.0",
+     "playwright>=1.40.0",
  ]

  [tool.pytest.ini_options]
+ addopts = "-m 'not live and not local_browser'"
  markers = [
      "live: ...",
+     "local_browser: marks tests that launch a local Chromium browser",
      "asyncio: ...",
  ]
```

> **`fastmcp>=2.14.0` removed**: Dead weight. Zero imports of standalone `fastmcp` anywhere in the unified server. All code uses `from mcp.server.fastmcp import FastMCP` (from the `mcp[cli]` package).

### Phase 4: Migrate & Write Tests (11 files)

- Copy 7 browser unit tests into `tests/browser/`, rewrite import paths and `PATCH_BASE` strings (see Appendix B)
- Copy `conftest.py` and `test_integ_browser_session.py`
- Migrate selected test classes from standalone `test_unit_server.py` into `test_unit_server_integration.py` (see Appendix B for class-by-class disposition)
- Write `test_unit_observation.py` from scratch (see Appendix B)
- Write `test_unit_server_integration.py` from scratch (registration, lifespan, opt-out tests)

**PATCH_BASE rewrite mapping** — apply to ALL migrated test files:

| Old Prefix | New Prefix |
|---|---|
| `awslabs.agentcore_browser_mcp_server.server` | `awslabs.amazon_bedrock_agentcore_mcp_server.server` |
| `awslabs.agentcore_browser_mcp_server.browser.connection_manager` | `awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.connection_manager` |
| `awslabs.agentcore_browser_mcp_server.browser.snapshot_manager` | `awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.snapshot_manager` |
| `awslabs.agentcore_browser_mcp_server.utils.aws_client` | `awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.aws_client` |
| `awslabs.agentcore_browser_mcp_server.tools.<module>` | `awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.<module>` |
| `awslabs.agentcore_browser_mcp_server.models.session` | `awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.models` |

**Watch for inline imports** in test bodies (not just top-level). `test_unit_interaction.py` has 3 inline imports of `NAVIGATION_TIMEOUT_MS` from navigation at lines 176, 191, 224. The grep check will catch these, but be aware they exist.

After rewriting, verify: `grep -r 'agentcore_browser_mcp_server' tests/browser/` — must return zero.

### Phase 5: Documentation & README
- Add "Browser Tools" section to README with tool list, env var opt-out docs, and usage example

### Phase 6: Verification

```bash
WD=/Volumes/workplace/test-browser-mcp2/src/amazon-bedrock-agentcore-mcp-server

# Step 1: Install deps
cd $WD && uv sync

# Step 2: All tests pass
pytest tests/ -x -m "not live and not local_browser" -v

# Step 3: Coverage
pytest tests/ -m "not live and not local_browser" --cov=awslabs --cov-report=term-missing

# Step 4: Lint + format
ruff check awslabs/ tests/ && ruff format --check awslabs/ tests/

# Step 5: Import hygiene — must return zero
grep -r "agentcore_browser_mcp_server" awslabs/ tests/

# Step 6: Tool count — non-blocking (no server start)
uv run python -c "
from awslabs.amazon_bedrock_agentcore_mcp_server.server import mcp
tools = mcp._tool_manager.list_tools()
print(f'Tool count: {len(tools)}')
for t in tools:
    print(f'  - {t.name}')
assert len(tools) == 30, f'Expected 30, got {len(tools)}'
"

# Step 7: Opt-out verification — non-blocking
AGENTCORE_DISABLE_TOOLS=browser uv run python -c "
from awslabs.amazon_bedrock_agentcore_mcp_server.server import mcp
tools = mcp._tool_manager.list_tools()
print(f'Tool count: {len(tools)}')
assert len(tools) == 5, f'Expected 5, got {len(tools)}'
"

# Step 8: Opt-in verification — docs always-on
AGENTCORE_ENABLE_TOOLS=browser uv run python -c "
from awslabs.amazon_bedrock_agentcore_mcp_server.server import mcp
tools = mcp._tool_manager.list_tools()
print(f'Tool count: {len(tools)}')
assert len(tools) == 27, f'Expected 27 (2 always-on docs + 25 browser), got {len(tools)}'
"
```

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Existing tests break from server.py changes | Only `test_main.py` affected (2 tests). Fix: add lifespan assertion. All other 10 test files are safe (verified — they test utils/tools directly, never import server.py). |
| Browser import failure crashes entire server | `try/except ImportError` around browser import + registration. Server degrades to 5 core tools with clear log message instead of crashing. |
| Signal handler + finally double-cleanup | `BrowserConnectionManager.cleanup()` made idempotent with `_cleaned_up` guard. Signal handler captures `_browser_cm` via lambda default arg to avoid late-binding. |
| Too many tools confuse the model | Opt-out via `AGENTCORE_DISABLE_TOOLS` / `AGENTCORE_ENABLE_TOOLS` env vars. Case-insensitive, validates edge cases (empty commas, both vars set). |
| Import path rewriting misses something | Grep for old prefix `agentcore_browser_mcp_server` after migration; must return zero hits. Also check inline imports in test bodies (e.g., `test_unit_interaction.py` lines 176, 191, 224). |
| Heavier default install (~50MB playwright) | Acceptable tradeoff for discovery. Target user is a developer who wants AgentCore tools. Two-way door: can move to optional extras later. |
| Signal handler conflicts between primitives | Centralized in `server_lifespan()`. Primitive modules MUST NOT register their own signal handlers. One handler per signal, composes all primitives. |
| `fastmcp` vs `mcp[cli]` confusion | Removed `fastmcp>=2.14.0` (dead weight). All code uses `from mcp.server.fastmcp import FastMCP` from the `mcp[cli]` package. |
| PR too large to review | All browser source is copy+rewrite (no logic changes). Reviewers can diff against standalone server. |

---

## Resolved Questions

1. **`aws_client.py` placement**: Keep in `tools/browser/aws_client.py`. The module is 100% browser-specific — it imports `BrowserClient`, caches `BrowserClient` instances, and has a browser-specific integration source string. Code Interpreter would need its own client wrapper.

2. **Error handler placement**: Keep in `tools/browser/error_handler.py`. Every function takes a `SnapshotManager` and/or playwright `Page`. Browser-specific.

3. **Lifespan ownership**: `server.py` owns `FastMCP(lifespan=...)` construction (required by API). Browser module exports `register_browser_tools()` and `cleanup_stale_sessions()`. Signal handlers live in `server.py` only.

4. **Models**: Keep in `tools/browser/models.py`. Each primitive owns its models. No shared model directory needed yet.

5. **Signal handlers**: Centralized in `server_lifespan()`, not in the browser module. MCP SDK does NOT handle SIGTERM/SIGINT. Capture references via lambda default args. Make `cleanup()` idempotent with `_cleaned_up` guard. Cancel background task before cleanup in `finally`; signal handler calls cleanup directly (idempotent, so safe).

6. **`fastmcp>=2.14.0`**: Removed. Zero imports of standalone `fastmcp` package. All code uses `mcp[cli]`'s built-in FastMCP.

7. **`instructions` string**: Composed as a single constant in `server.py`. Forward-looking — references all primitives, browser tips ported verbatim from standalone. Read-only constructor param on FastMCP (no post-init mutation).

8. **Docs always-on**: `search_agentcore_docs` and `fetch_agentcore_doc` are registered unconditionally, regardless of `AGENTCORE_ENABLE_TOOLS` / `AGENTCORE_DISABLE_TOOLS`. They are the core functionality with zero external deps.

9. **`_is_primitive_enabled()` edge cases**: Case-insensitive comparison. Empty-after-split filtered with `if t.strip()`. Both vars set simultaneously → enable wins with logged warning.

10. **Import failure graceful degradation**: `try/except ImportError` around browser import. Server starts with 5 core tools instead of crashing. Clear error log tells the user what happened and how to fix it.

---

## Appendix A: Migration Checklist (File-by-File)

All source paths are relative to the browser standalone server:
`/Volumes/workplace/test-browser-mcp2/src/agentcore-browser-mcp-server/awslabs/agentcore_browser_mcp_server/`

All target paths are relative to:
`/Volumes/workplace/test-browser-mcp2/src/amazon-bedrock-agentcore-mcp-server/awslabs/amazon_bedrock_agentcore_mcp_server/tools/browser/`

### Import Rewrite Rule

Every file uses absolute imports like:
```python
from awslabs.agentcore_browser_mcp_server.browser.connection_manager import BrowserConnectionManager
from awslabs.agentcore_browser_mcp_server.tools.error_handler import error_with_snapshot
from awslabs.agentcore_browser_mcp_server.models.session import BrowserSessionResponse
```

These ALL become relative imports within `tools/browser/`:
```python
from .connection_manager import BrowserConnectionManager
from .error_handler import error_with_snapshot
from .models import BrowserSessionResponse
```

### New File: `__init__.py`

Write from scratch. Contains:
- Imports of all browser sub-modules
- `cleanup_stale_sessions(connection_manager, snapshot_manager)` background coroutine (ported from standalone `server.py:49-66`)
- `register_browser_tools(mcp)` — instantiates managers, creates tool group classes, calls `.register(mcp)` on each with per-group error context, returns `(connection_manager, snapshot_manager)`

Note: `__init__.py` does NOT manage lifespan, signal handlers, or the cleanup task. Those live in `server.py`'s `server_lifespan()`.

### Copied Files (10 source files)

| # | Source | Target | Import Changes | Code Changes |
|---|--------|--------|----------------|--------------|
| 1 | `browser/connection_manager.py` | `connection_manager.py` | `from .aws_client import get_browser_client` | **Add idempotent cleanup**: `self._cleaned_up = False` in `__init__`, guard at top of `cleanup()` |
| 2 | `browser/snapshot_manager.py` | `snapshot_manager.py` | None | None |
| 3 | `utils/aws_client.py` | `aws_client.py` | None | None |
| 4 | `models/session.py` | `models.py` | None | None |
| 5 | `tools/error_handler.py` | `error_handler.py` | `from .snapshot_manager import SnapshotManager` | None |
| 6 | `tools/session.py` | `session.py` | 4 rewrites: `.connection_manager`, `.snapshot_manager`, `.models`, `.aws_client` | None |
| 7 | `tools/navigation.py` | `navigation.py` | 3 rewrites: `.connection_manager`, `.snapshot_manager`, `.error_handler` | None |
| 8 | `tools/interaction.py` | `interaction.py` | 3 rewrites: `.connection_manager`, `.snapshot_manager`, `.error_handler` | None |
| 9 | `tools/observation.py` | `observation.py` | 3 rewrites: `.connection_manager`, `.snapshot_manager`, `.error_handler` | None |
| 10 | `tools/management.py` | `management.py` | 4 rewrites: `.connection_manager`, `.snapshot_manager`, `.error_handler`, `.navigation` | None |

### Modified File: `server.py`

Current (46 lines) -> Target (~90 lines). See Phase 3 for complete code with:
- `_is_primitive_enabled()` with case-insensitive comparison and edge case handling
- `AGENTCORE_MCP_INSTRUCTIONS` constant
- `server_lifespan()` with signal handlers (lambda default arg capture) and proper task cancellation
- `try/except ImportError` around browser import for graceful degradation
- Docs always-on, all other primitives opt-outable

### Browser `__init__.py` design

The browser module exports two things:
- `register_browser_tools(mcp)` — creates managers, registers 25 tools with per-group error context, returns (cm, sm)
- `cleanup_stale_sessions(cm, sm)` — background coroutine for stale session pruning

```python
# tools/browser/__init__.py
from .connection_manager import BrowserConnectionManager
from .snapshot_manager import SnapshotManager
from .session import BrowserSessionTools
from .navigation import NavigationTools
from .interaction import InteractionTools
from .observation import ObservationTools
from .management import ManagementTools
from loguru import logger

STALE_SESSION_CHECK_INTERVAL_S = 60

async def cleanup_stale_sessions(connection_manager, snapshot_manager):
    """Periodically prune stale Playwright connections."""
    # Ported from standalone server.py:49-66
    ...

def register_browser_tools(mcp):
    connection_manager = BrowserConnectionManager()
    snapshot_manager = SnapshotManager()
    groups = [
        ('session', BrowserSessionTools),
        ('navigation', NavigationTools),
        ('interaction', InteractionTools),
        ('observation', ObservationTools),
        ('management', ManagementTools),
    ]
    for name, cls in groups:
        try:
            cls(connection_manager, snapshot_manager).register(mcp)
        except Exception as e:
            raise RuntimeError(f'Failed to register browser {name} tools: {e}') from e
    logger.info('All browser tool groups registered successfully')
    return connection_manager, snapshot_manager
```

### Modified File: `pyproject.toml`

```diff
  dependencies = [
      "loguru>=0.7.0",
      "mcp[cli]>=1.23.0",
-     "fastmcp>=2.14.0",
      "pydantic>=2.10.6",
+     "bedrock-agentcore>=1.1.0,<2.0.0",
+     "playwright>=1.40.0",
  ]

  [tool.pytest.ini_options]
+ addopts = "-m 'not live and not local_browser'"
  markers = [
      "live: ...",
+     "local_browser: marks tests that launch a local Chromium browser",
      "asyncio: ...",
  ]
```

### Verification Grep

After all files are created, run:
```bash
grep -r "agentcore_browser_mcp_server" src/amazon-bedrock-agentcore-mcp-server/
```
Must return **zero results**. Any hit means a missed import rewrite.

---

## Appendix B: Test Strategy

### Existing Tests: Minimal Impact

All 11 existing test files are safe **except `test_main.py`** (2 tests affected).

| Test File | Status | Reason |
|-----------|--------|--------|
| `test_main.py` | **UPDATE** | Patches `server.mcp` — needs lifespan assertion added |
| `test_server.py` | Safe | Tests `search_agentcore_docs` / `fetch_agentcore_doc` directly |
| `test_tools.py` | Safe | Tests `manage_agentcore_*` functions directly |
| `test_init.py` | Safe | Tests `__version__` only |
| `test_doc_fetcher.py` | Safe | Tests utility functions only |
| `test_indexer.py` | Safe | Tests `IndexSearch` class only |
| `test_text_processor.py` | Safe | Tests utility functions only |
| `test_config.py` | Safe | Tests `Config` class only |
| `test_url_validator.py` | Safe | Tests `URLValidator` class only |
| `test_cache.py` | Safe | Tests cache functions only |
| `conftest.py` | Safe | Only sets env var fixtures |

**`test_main.py` fix**: Add `assert mcp.settings.lifespan is server_lifespan` to `test_main_function()`. Existing `mock_mcp.run.assert_called_once()` stays unchanged.

### Standalone `test_unit_server.py` Disposition

The standalone server's `test_unit_server.py` has 5 test classes. Each has a different fate:

| Class | Tests | Action | Destination | Notes |
|---|---|---|---|---|
| `TestServerLifespan` | 3 | **Rewrite** for unified lifespan | `test_unit_server_integration.py` | Test both `_browser_cm is not None` and `else: yield` branches |
| `TestToolRegistration` | 2 | **Drop** (tests standalone FastMCP instance name/lifespan) | — | |
| `TestMain` | 1 | **Drop** (browser has no `main()` in unified server) | — | |
| `TestCleanupStaleSessions` | 5 | **Rewrite** — signature changed | `test_unit_server_integration.py` | Function now takes `(cm, sm)` params instead of reading module globals. All 5 tests need parameter-passing rewrites, not just PATCH_BASE substitution. |
| `TestToolRegistrationError` | 1 | **Rewrite** — no `importlib.reload` | `test_unit_server_integration.py` | Test `register_browser_tools()` directly with a mock that raises, not module reload. |

### Browser Test Migration (8 files copied from standalone)

Each standalone test file maps 1:1 into `tests/browser/`. Changes per file:

1. **Update imports**: `from awslabs.agentcore_browser_mcp_server.tools.session import ...` -> `from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.session import ...`

2. **Update PATCH_BASE strings**: See Phase 4 mapping table above.

3. **Watch for inline imports in test bodies**: `test_unit_interaction.py` has 3 inline imports of `NAVIGATION_TIMEOUT_MS` from `awslabs.agentcore_browser_mcp_server.tools.navigation` at lines 176, 191, 224. These must also be rewritten.

4. **No logic changes**: All assertions, mocking patterns, and test structure stay identical.

| Source Test | Target | Key PATCH_BASE rewrites |
|-------------|--------|------------------------|
| `conftest.py` | `tests/browser/conftest.py` | `tools.session.get_browser_client` |
| `test_unit_session.py` | `tests/browser/test_unit_session.py` | `tools.session.get_browser_client`, `tools.session.BrowserConnectionManager` |
| `test_unit_connection.py` | `tests/browser/test_unit_connection.py` | `browser.connection_manager.*` → `tools.browser.connection_manager.*` |
| `test_unit_snapshot.py` | `tests/browser/test_unit_snapshot.py` | None (tests SnapshotManager directly) |
| `test_unit_interaction.py` | `tests/browser/test_unit_interaction.py` | `tools.interaction.*` → `tools.browser.interaction.*` + 3 inline imports |
| `test_unit_management.py` | `tests/browser/test_unit_management.py` | `tools.management.*` → `tools.browser.management.*` |
| `test_unit_error_handler.py` | `tests/browser/test_unit_error_handler.py` | `tools.error_handler.*` → `tools.browser.error_handler.*` |
| `test_unit_aws_client.py` | `tests/browser/test_unit_aws_client.py` | `utils.aws_client.*` → `tools.browser.aws_client.*` |
| `test_integ_browser_session.py` | `tests/browser/test_integ_browser_session.py` | `@pytest.mark.live` (skipped by default) |

### Browser conftest.py

```python
# tests/browser/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_ctx():
    ctx = MagicMock()
    ctx.error = AsyncMock()
    ctx.info = AsyncMock()
    return ctx

@pytest.fixture
def mock_browser_client(monkeypatch):
    client = MagicMock()
    client.data_plane_client = MagicMock()
    client.get_session = MagicMock()
    client.list_sessions = MagicMock()
    monkeypatch.setattr(
        'awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.session.get_browser_client',
        lambda *args, **kwargs: client,
    )
    return client
```

### New Test: `test_unit_observation.py` (write from scratch)

No source test exists. `observation.py` has 336 lines and 7 public methods with zero coverage. Budget **~22 tests** (not 15 — each method needs happy path + error path + edge case).

| Method | Happy path | Error path | Edge cases | Min tests |
|--------|-----------|------------|------------|-----------|
| `browser_snapshot` | capture + format | exception | missing page, selector param | 3 |
| `browser_take_screenshot` | capture + base64 | exception | full_page=True | 3 |
| `browser_wait_for` | text match, selector match | timeout, neither provided | error_with_snapshot | 4 |
| `browser_console_messages` | DOM results found | exception, no results | empty result list | 3 |
| `browser_network_requests` | entries found | exception, no entries | size=0 edge case | 3 |
| `browser_evaluate` | primitive result, complex result, None | exception | JSON serialization default=str | 4 |
| `BROWSER_DISABLE_EVALUATE` | env true → not registered | env false/unset → registered | | 2 |

### New Test: `test_unit_server_integration.py`

Tests the registration, lifespan, and opt-out glue. Covers:

1. **Browser registration**: Call `register_browser_tools(mock_mcp)`. Assert 25 tools registered.
2. **Per-group error context**: Mock one tool class `__init__` to raise. Verify `RuntimeError` message includes the group name.
3. **Cleanup stale sessions** (rewrite from standalone — 5 tests): Function now takes `(cm, sm)` as params. Pass mocks directly instead of patching module globals.
4. **Lifespan with browser enabled**: Rewrite from standalone — verify cleanup task starts, signal handlers registered (with lambda default arg capture), cleanup on exit.
5. **Lifespan with browser disabled**: Verify `else: yield` path — server starts cleanly when `_browser_cm is None`.
6. **Lifespan cleanup on exception**: Verify cleanup runs even when body raises.
7. **Import failure graceful degradation**: Mock browser import to raise `ImportError`. Verify server starts with 5 core tools, no crash.
8. **Tool count default**: Verify 30 tools (5 core + 25 browser) with no env vars.
9. **Opt-out blocklist**: Set `AGENTCORE_DISABLE_TOOLS=browser`. Assert only 5 core tools.
10. **Opt-in allowlist**: Set `AGENTCORE_ENABLE_TOOLS=browser`. Assert 27 tools (2 always-on docs + 25 browser).
11. **Docs always-on**: Set `AGENTCORE_ENABLE_TOOLS=browser` (without docs). Assert docs tools still present.
12. **Opt-out helper unit tests** for `_is_primitive_enabled()`:
    - Default (no env vars) → True
    - `AGENTCORE_DISABLE_TOOLS=browser` → `_is_primitive_enabled('browser')` returns False
    - `AGENTCORE_DISABLE_TOOLS=browser` → `_is_primitive_enabled('runtime')` returns True
    - `AGENTCORE_ENABLE_TOOLS=browser` → `_is_primitive_enabled('browser')` returns True
    - `AGENTCORE_ENABLE_TOOLS=browser` → `_is_primitive_enabled('runtime')` returns False
    - Both vars set → enable wins (with warning logged)
    - `AGENTCORE_ENABLE_TOOLS=,,,` → all enabled (empty-after-split)
    - Case insensitivity: `AGENTCORE_DISABLE_TOOLS=Browser` disables `browser`
    - Whitespace: `AGENTCORE_DISABLE_TOOLS= browser , runtime ` works correctly
    - Idempotent cleanup: call `cleanup()` twice, verify second call is no-op

### Test Count Summary

| Category | Files | Estimated Tests |
|----------|-------|----------------|
| Existing (unchanged except test_main.py) | 11 | ~81 |
| Browser unit (migrated from standalone) | 7 | ~203 |
| Browser observation (new, from scratch) | 1 | ~22 |
| Browser integration (migrated, @live, skipped by default) | 1 | ~50 |
| Server integration (new + rewritten) | 1 | ~25 |
| **Total** | **21** | **~381** |

> **Note**: Test counts are from actual source file inspection, not estimates. The migrated browser unit tests (203) include: session=24, connection=33, snapshot=35, interaction=70, management=28, error_handler=7, aws_client=6.
