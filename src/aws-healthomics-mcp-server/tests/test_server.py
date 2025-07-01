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
"""Tests for the aws-healthomics MCP Server."""

from awslabs.aws_healthomics_mcp_server.server import mcp


def test_server_initialization():
    """Test that the MCP server initializes correctly."""
    # Arrange & Act
    server = mcp

    # Assert
    assert server is not None
    assert server.name == 'awslabs.aws-healthomics-mcp-server'
    assert server.instructions is not None
    assert 'AWS HealthOmics MCP Server' in server.instructions


def test_server_has_required_tools():
    """Test that the server has all required tools registered."""
    # Arrange
    expected_tools = [
        'ListAHOWorkflows',
        'CreateAHOWorkflow',
        'GetAHOWorkflow',
        'CreateAHOWorkflowVersion',
        'ListAHOWorkflowVersions',
        'StartAHORun',
        'ListAHORuns',
        'GetAHORun',
        'ListAHORunTasks',
        'GetAHORunTask',
        'GetAHORunLogs',
        'GetAHORunManifestLogs',
        'GetAHORunEngineLogs',
        'GetAHOTaskLogs',
        'AnalyzeAHORunPerformance',
        'DiagnoseAHORunFailure',
        'PackageAHOWorkflow',
        'GetAHOSupportedRegions',
    ]

    # Act
    server = mcp

    # Assert
    assert server is not None

    # Verify all expected tools are mentioned in the server instructions
    instructions = server.instructions
    assert instructions is not None
    for tool_name in expected_tools:
        assert f'**{tool_name}**' in instructions, (
            f'Tool {tool_name} not found in server instructions'
        )

    # Verify server has the expected dependencies
    expected_dependencies = ['boto3', 'pydantic', 'loguru']
    for dep in expected_dependencies:
        assert dep in server.dependencies
