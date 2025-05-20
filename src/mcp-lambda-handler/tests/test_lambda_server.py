import pytest
from awslabs.mcp_lambda_handler import MCPLambdaHandler

def test_handler_instantiation():
    handler = MCPLambdaHandler(name="test-server", version="0.1.0")
    assert handler.name == "test-server"
    assert handler.version == "0.1.0" 