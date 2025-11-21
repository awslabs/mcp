"""Tests for error handling paths to improve coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import psycopg


@pytest.mark.asyncio
async def test_readonly_query_transaction_bypass_attempt():
    """Test that transaction bypass attempts are rejected."""
    from awslabs.aurora_dsql_mcp_server.server import readonly_query
    
    ctx = MagicMock()
    ctx.error = AsyncMock()
    
    with pytest.raises(Exception, match="transaction bypass"):
        await readonly_query("BEGIN; SELECT 1; COMMIT;", ctx)
    
    ctx.error.assert_called_once()


@pytest.mark.asyncio
async def test_readonly_query_write_error():
    """Test ReadOnlySqlTransaction error handling."""
    from awslabs.aurora_dsql_mcp_server.server import readonly_query
    
    ctx = MagicMock()
    ctx.error = AsyncMock()
    
    with patch('awslabs.aurora_dsql_mcp_server.server.get_connection') as mock_conn:
        mock_conn.return_value = AsyncMock()
        with patch('awslabs.aurora_dsql_mcp_server.server.execute_query') as mock_exec:
            mock_exec.side_effect = psycopg.errors.ReadOnlySqlTransaction("write error")
            
            with pytest.raises(Exception, match="write operation"):
                await readonly_query("SELECT 1", ctx)


@pytest.mark.asyncio
async def test_transact_not_allowed():
    """Test transact when writes not allowed."""
    from awslabs.aurora_dsql_mcp_server.server import transact, allow_writes
    
    ctx = MagicMock()
    ctx.error = AsyncMock()
    
    allow_writes.set(False)
    
    with pytest.raises(Exception, match="not allowed"):
        await transact(["INSERT INTO test VALUES (1)"], ctx)


@pytest.mark.asyncio
async def test_proxy_tool_timeout():
    """Test proxy tool timeout handling."""
    from awslabs.aurora_dsql_mcp_server.server import dsql_search_documentation
    
    ctx = MagicMock()
    ctx.error = AsyncMock()
    
    with patch('awslabs.aurora_dsql_mcp_server.server.httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=TimeoutError("timeout")
        )
        
        result = await dsql_search_documentation("test", ctx=ctx)
        assert "error" in result.lower() or "timeout" in result.lower()
