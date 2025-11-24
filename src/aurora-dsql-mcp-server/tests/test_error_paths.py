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

    # Mock the earlier checks to pass, so we can test transaction bypass detection
    with patch('awslabs.aurora_dsql_mcp_server.server.detect_mutating_keywords', return_value=[]):
        with patch('awslabs.aurora_dsql_mcp_server.server.check_sql_injection_risk', return_value=[]):
            with pytest.raises(Exception, match="bypass read-only transaction"):
                await readonly_query("SELECT 1; SELECT 2", ctx)

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
            mock_exec.side_effect = [None, psycopg.errors.ReadOnlySqlTransaction("write error")]

            with pytest.raises(Exception, match="does not support write"):
                await readonly_query("SELECT 1", ctx)


@pytest.mark.asyncio
async def test_transact_not_allowed():
    """Test transact when writes not allowed."""
    from awslabs.aurora_dsql_mcp_server import server

    ctx = MagicMock()
    ctx.error = AsyncMock()

    server.read_only = True

    with pytest.raises(Exception, match="not allow"):
        await server.transact(["INSERT INTO test VALUES (1)"], ctx)


@pytest.mark.asyncio
async def test_proxy_tool_timeout():
    """Test proxy tool timeout handling."""
    from awslabs.aurora_dsql_mcp_server.server import dsql_search_documentation
    import httpx

    ctx = MagicMock()
    ctx.error = AsyncMock()

    with patch('awslabs.aurora_dsql_mcp_server.server.httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.TimeoutException("timeout")
        )

        with pytest.raises(Exception, match="unavailable"):
            await dsql_search_documentation("test", ctx=ctx)
