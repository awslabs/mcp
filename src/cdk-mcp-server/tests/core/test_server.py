import pytest
from unittest.mock import patch, MagicMock
from awslabs.cdk_mcp_server.core.server import mcp, main


def test_mcp_server_initialization():
    """Test MCP server initialization."""
    # Check server name
    assert mcp.name == 'AWS CDK MCP Server'
    
    # Check dependencies
    assert 'pydantic' in mcp.dependencies
    assert 'aws-lambda-powertools' in mcp.dependencies
    assert 'httpx' in mcp.dependencies

@pytest.mark.asyncio
async def test_mcp_server_tool_registration():
    """Test MCP server tool registration."""
    # Get all registered tools
    tools = await mcp.list_tools()
    
    # Check CDK tools
    assert any(t.name == 'CDKGeneralGuidance' for t in tools)
    assert any(t.name == 'ExplainCDKNagRule' for t in tools)
    assert any(t.name == 'CheckCDKNagSuppressions' for t in tools)
    
    # Check Bedrock tools
    assert any(t.name == 'GenerateBedrockAgentSchema' for t in tools)
    
    # Check Solutions Constructs tools
    assert any(t.name == 'GetAwsSolutionsConstructPattern' for t in tools)
    
    # Check GenAI CDK Constructs tools
    assert any(t.name == 'SearchGenAICDKConstructs' for t in tools)
    
    # Check Lambda tools
    assert any(t.name == 'LambdaLayerDocumentationProvider' for t in tools)


@patch('awslabs.cdk_mcp_server.core.server.mcp.run')
def test_main_with_default_args(mock_run):
    """Test main function with default arguments."""
    with patch('sys.argv', ['server.py']):
        main()
        mock_run.assert_called_once_with()


@patch('awslabs.cdk_mcp_server.core.server.mcp.run')
def test_main_with_sse_args(mock_run):
    """Test main function with SSE transport arguments."""
    with patch('sys.argv', ['server.py', '--sse', '--port', '9999']):
        main()
        assert mcp.settings.port == 9999
        mock_run.assert_called_once_with(transport='sse') 