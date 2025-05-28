import pytest
from awslabs.dynamodb_mcp_server import server


@pytest.mark.asyncio
async def test_delete_table_blocked_by_readonly(monkeypatch):
    """Test that delete_table is blocked if DDB-MCP-READONLY is set to true."""
    # Set the environment variable to simulate read-only mode
    monkeypatch.setenv('DDB-MCP-READONLY', 'true')

    # Call delete_table and expect an error
    result = await server.delete_table(table_name='TestTable', region_name='us-west-2')
    assert 'error' in result
    assert 'DDB-MCP-READONLY' in result['error']
