# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

import pytest
from awslabs.cdk_mcp_server.core.server import main, mcp
from unittest.mock import patch


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
