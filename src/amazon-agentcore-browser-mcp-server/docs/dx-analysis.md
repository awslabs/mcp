# Browser MCP Server DX Analysis

Analysis of developer experience issues affecting LLM agents (the primary consumers of this MCP server). All findings below have been fixed in the accompanying code changes.

## Issue 1: Inconsistent Error Handling (Severity: Critical)

**Problem**: Some tools catch exceptions and return error strings (giving agents a recovery path), while others call `ctx.error()` + `raise`, which surfaces as an opaque MCP-layer error that kills the interaction.

**Affected tools before fix**:
- `navigation.py`: All 3 tools raised on error
- `observation.py`: 5 of 6 tools raised on error (`browser_wait_for` was the exception, correctly returning error + snapshot)
- `management.py`: `browser_tabs`, `browser_close`, `browser_resize` all raised on error
- `interaction.py`: `browser_press_key` and `browser_handle_dialog` raised on error (inconsistent with sibling tools `browser_click`, `browser_type`, etc. which returned errors)

**Rule applied**: Page-facing tools catch all exceptions and return error text + snapshot. Session-lifecycle tools (`start_browser_session`, `stop_browser_session`, etc.) continue to raise since there is no page to snapshot.

**Before**:
```python
except Exception as e:
    error_msg = f'Error navigating to {url}: {e}'
    logger.error(error_msg)
    await ctx.error(error_msg)
    raise  # Agent sees: MCP error, no page context, no recovery path
```

**After**:
```python
except Exception as e:
    error_msg = f'Error navigating to {url}: {e}'
    logger.error(error_msg)
    try:
        snapshot = await self._snapshot_manager.capture(page, session_id)
        return f'{error_msg}\n\nCurrent page:\n{snapshot}'
    except Exception:
        return error_msg  # Fallback if snapshot also fails
```

## Issue 2: Missing Snapshots on State-Changing Operations (Severity: High)

**Problem**: Several tools that change page state did not return snapshots, leaving the agent blind to the result of its action.

**Affected tools**:
- `browser_tabs` action="new": Returned only text like `Opened new tab [2]: Title - url`. Agent had no idea what the new page looked like.
- `browser_tabs` action="close": Returned only `Closed tab [1]: Title. 1 tab(s) remaining.` Agent did not know what the remaining active tab showed.
- `browser_close`: Returned only `Closed page: Title (url)`. Agent did not see the remaining tab.

**Fix**: Added snapshot capture for all state-changing tab/close operations.

## Issue 3: Private State Access in management.py (Severity: Medium)

**Problem**: `management.py` accessed `self._connection_manager._connections.get(session_id)` directly in two places (lines 87 and 177). This breaks encapsulation and will break if the internal data structure changes.

**Fix**: Added public `get_browser(session_id)` and `get_context(session_id)` methods to `BrowserConnectionManager` following the same pattern as the existing `get_page()` method. Updated `management.py` to use these.

## Issue 4: Deprecated `profile_name` Parameter (Severity: Medium)

**Problem**: All 4 session tools still accepted a `profile_name` parameter marked as deprecated. This clutters the tool schema that LLM agents see, wasting tokens on every tool call and potentially confusing agents into providing a value.

**Fix**: Removed `profile_name` from `start_browser_session`, `get_browser_session`, `stop_browser_session`, and `list_browser_sessions`. Also removed the deprecation warning block in `start_browser_session`.

## Issue 5: Inconsistent RefNotFoundError Messages (Severity: Low)

**Problem**: `browser_select_option` and `browser_hover` used a terse error message on ref-not-found (`Error: ref "e5" not found.`), while `browser_click`, `browser_type`, and `browser_upload_file` used a more helpful message that told the agent what to do next.

**Before**: `Error: ref "e5" not found.`
**After**: `Error: ref "e5" not found in current page. Take a new snapshot or use a ref from below.`

## Issue 6: Missing Hover Settle Wait (Severity: Low)

**Problem**: `browser_hover` took a snapshot immediately after hovering, before tooltips or dropdown menus had time to appear. This made the snapshot useless for its primary purpose (revealing hover-triggered content).

**Fix**: Added `await _wait_for_settled(page, timeout_ms=2000)` after `locator.hover()`. Uses a shorter timeout (2s vs default 5s) since hover effects are typically fast.

## Issue 7: browser_resize Snapshot Outside Try Block (Severity: Low)

**Problem**: In `browser_resize`, the snapshot capture was outside the try/except block. If `set_viewport_size` succeeded but snapshot capture failed, the error would propagate as an unhandled exception.

**Fix**: Moved snapshot capture inside the try block alongside the viewport resize.

## Summary of Changes by File

| File | Changes |
|------|---------|
| `browser/connection_manager.py` | Added `get_browser()` and `get_context()` public methods |
| `tools/navigation.py` | Error handling: catch-and-return with snapshot for all 3 tools |
| `tools/interaction.py` | `press_key`/`handle_dialog` error handling, RefNotFoundError messages, hover settle wait |
| `tools/observation.py` | Error handling: return error strings for all 5 tools |
| `tools/management.py` | Public API migration, snapshots on new/close/resize, error handling |
| `tools/session.py` | Removed `profile_name` from all 4 tools |
| `tests/test_unit_management.py` | Updated to use public API, assert snapshots in returns |
| `tests/test_unit_interaction.py` | Updated `test_evaluate_error` to expect return instead of raise |
