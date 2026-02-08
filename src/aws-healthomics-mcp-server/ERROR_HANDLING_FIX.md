# Error Handling Fix for AWS HealthOmics MCP Server

## Problem

The MCP server was "swallowing" errors by raising exceptions after calling `ctx.error()`. When tools raise exceptions, the MCP framework may not properly surface error details to the agent, preventing the agent from understanding and communicating issues to users.

### Example Issue
When `StartAHORun` encountered AWS ValidationException errors (e.g., "S3 object not found: s3://..."), the error was logged and passed to `ctx.error()`, but then the exception was raised, preventing the agent from receiving the error details as a tool result.

## Solution

### 1. Created Error Handling Utility

**File**: `awslabs/aws_healthomics_mcp_server/utils/error_utils.py`

```python
async def handle_tool_error(ctx: Context, error: Exception, operation: str) -> Dict[str, Any]:
    """Handle tool errors by logging and returning error information to the agent.

    Returns:
        Dictionary with 'error' key containing the error message
    """
```

This utility:
- Logs the error
- Calls `ctx.error()` to report to MCP framework
- **Returns** error dict instead of raising
- Ensures agents receive error details as tool results

### 2. Updated start_run Tool

**Before**:
```python
except Exception as e:
    error_message = f'AWS error starting run: {str(e)}'
    logger.error(error_message)
    await ctx.error(error_message)
    raise  # Agent doesn't see this!
```

**After**:
```python
except Exception as e:
    return await handle_tool_error(ctx, e, 'Error starting run')
```

### 3. Added Comprehensive Tests

**File**: `tests/test_error_utils.py`
- Tests error dict is returned
- Tests ctx.error() is called
- Tests exception details are preserved

**Updated**: `tests/test_workflow_execution.py`
- Updated all start_run error tests to verify error dict return
- Tests verify both ctx.error() call and returned error dict

## Pattern Comparison with Other MCP Servers

Analysis of other AWS MCP servers shows the correct pattern:

### ✅ Correct Pattern (Return Errors)
- `aws-location-mcp-server`: Returns `{'error': error_msg}`
- `billing-cost-management-mcp-server`: Returns `{'error': error_msg}`
- `lambda-tool-mcp-server`: Returns `error_message`

### ❌ Incorrect Pattern (Raise Errors)
- `aurora-dsql-mcp-server`: Raises exceptions
- `cloudwatch-mcp-server`: Raises exceptions
- `aws-healthomics-mcp-server`: Was raising (now fixed for start_run)

## Remaining Work

The following tools in aws-healthomics-mcp-server still raise after `ctx.error()`:

- `workflow_execution.py`: 18 remaining raises (start_run fixed)
- `ecr_tools.py`: 14 raises
- `workflow_analysis.py`: 12 raises
- `workflow_management.py`: 11 raises
- `codeconnections.py`: 10 raises
- `genomics_file_search.py`: 5 raises
- `troubleshooting.py`: 3 raises
- `helper_tools.py`: 1 raise

### Recommended Next Steps

1. Update remaining functions in `workflow_execution.py` to use `handle_tool_error()`
2. Update other tool files to use the error handling utility
3. Update corresponding tests to verify error dict returns
4. Consider adding a linting rule to prevent future `raise` after `ctx.error()`

## Benefits

1. **Agent Awareness**: Agents receive full error details as tool results
2. **Better UX**: Users get actionable error messages through the agent
3. **Consistency**: Follows pattern used by other AWS MCP servers
4. **Maintainability**: Centralized error handling logic
5. **Testability**: Clear contract for error returns

## Testing

All tests pass:
```bash
# Error utility tests
uv run pytest tests/test_error_utils.py -v
# 2 passed

# start_run tests
uv run pytest tests/test_workflow_execution.py -k "test_start_run" -v
# 13 passed
```
