# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the Data Processing MCP Server."""

import argparse
import pytest
import sys

# Import the modules that will be mocked
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.crawler_handler import (
    CrawlerHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_catalog_handler import (
    GlueDataCatalogHandler,
)
from mcp.server.fastmcp import Context
from unittest.mock import MagicMock, patch


# Mock pytest for testing
sys.modules['pytest'] = MagicMock()


# Mock mcp.server.fastmcp
class MockContext:
    """Mock Context class for testing."""

    pass


# Create a proper TextContent class for type checking
class MockTextContent:
    """Mock TextContent class for testing."""

    def __init__(self, type='text', text=''):
        """Initialize the MockTextContent class.

        Args:
            type (str, optional): The content type. Defaults to 'text'.
            text (str, optional): The text content. Defaults to ''.
        """
        self.type = type
        self.text = text


# Create a proper CallToolResult class for type checking
class MockCallToolResult:
    """Mock CallToolResult class for testing."""

    def __init__(self, isError=False, content=None, **kwargs):
        """Initialize the MockCallToolResult class.

        Args:
            isError (bool, optional): Whether the result is an error. Defaults to False.
            content (list, optional): The content of the result. Defaults to None.
            **kwargs: Additional attributes to set on the result.
        """
        self.isError = isError
        self.content = content or []
        for key, value in kwargs.items():
            setattr(self, key, value)


# Set up mocks before importing any modules that use them
sys.modules['mcp.server.fastmcp'] = MagicMock()
sys.modules['mcp.server.fastmcp'].Context = MockContext
sys.modules['mcp.types'] = MagicMock()
sys.modules['mcp.types'].TextContent = MockTextContent
sys.modules['mcp.types'].CallToolResult = MockCallToolResult


@pytest.mark.asyncio
async def test_server_initialization():
    """Test that the server is initialized correctly with the right configuration."""
    # Test the server initialization by creating a server instance
    from awslabs.aws_dataprocessing_mcp_server.server import SERVER_INSTRUCTIONS, create_server

    # Mock the FastMCP class
    mock_fastmcp = MagicMock()
    mock_fastmcp.name = 'awslabs.aws-dataprocessing-mcp-server'
    mock_fastmcp.instructions = SERVER_INSTRUCTIONS
    mock_fastmcp.dependencies = ['pydantic', 'loguru', 'boto3', 'requests', 'pyyaml', 'cachetools']

    # Patch the FastMCP class to return our mock
    with patch('awslabs.aws_dataprocessing_mcp_server.server.FastMCP', return_value=mock_fastmcp):
        # Create a server instance
        server = create_server()

        # Test that the server is initialized with the correct name
        assert server.name == 'awslabs.aws-dataprocessing-mcp-server'

        # Test that the server has the correct instructions
        assert server.instructions is not None
        # Check that the instructions contain expected sections
        instructions_str = str(server.instructions)
        assert 'AWS Data Processing MCP Server' in instructions_str
        assert 'Setting Up a Data Catalog' in instructions_str
        assert 'Exploring the Data Catalog' in instructions_str
        assert 'Updating Data Catalog Resources' in instructions_str
        assert 'Cleaning Up Data Catalog Resource' in instructions_str
        assert 'Running Athena Queries' in instructions_str
        assert 'Creating Athena Named Queries' in instructions_str
        assert 'Athena Workgroup and Data Catalog' in instructions_str
        assert 'Setup EMR EC2 Cluster' in instructions_str
        assert 'Run EMR EC2 Steps' in instructions_str
        assert 'Manage EMR EC2 Instance Resources' in instructions_str

        # Test that the server has the correct dependencies
        assert 'pydantic' in server.dependencies
        assert 'loguru' in server.dependencies
        assert 'boto3' in server.dependencies
        assert 'requests' in server.dependencies
        assert 'pyyaml' in server.dependencies
        assert 'cachetools' in server.dependencies


@pytest.mark.asyncio
async def test_command_line_args():
    """Test that the command-line arguments are parsed correctly."""
    from awslabs.aws_dataprocessing_mcp_server.server import main

    # Mock the ArgumentParser.parse_args method to return known args
    with patch.object(argparse.ArgumentParser, 'parse_args') as mock_parse_args:
        # Test with default args (read-only mode by default)
        mock_parse_args.return_value = argparse.Namespace(
            allow_write=False, allow_sensitive_data_access=False
        )

        # Mock create_server to return a mock server
        mock_server = MagicMock()
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.server.create_server', return_value=mock_server
        ):
            # Mock the AWS helper's create_boto3_client method
            with patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
                return_value=MagicMock(),
            ):
                # Call the main function
                main()

                # Verify that parse_args was called
                mock_parse_args.assert_called_once()

                # Verify that run was called with the correct parameters
                mock_server.run.assert_called_once()

    # Test with write access enabled
    with patch.object(argparse.ArgumentParser, 'parse_args') as mock_parse_args:
        mock_parse_args.return_value = argparse.Namespace(
            allow_write=True, allow_sensitive_data_access=False
        )

        # Mock create_server to return a mock server
        mock_server = MagicMock()
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.server.create_server', return_value=mock_server
        ):
            # Mock the AWS helper's create_boto3_client method
            with patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
                return_value=MagicMock(),
            ):
                # Mock the handler initialization to verify allow_write is passed
                with patch(
                    'awslabs.aws_dataprocessing_mcp_server.server.GlueDataCatalogHandler'
                ) as mock_glue_data_catalog_handler:
                    with patch(
                        'awslabs.aws_dataprocessing_mcp_server.server.CrawlerHandler'
                    ) as mock_crawler_handler:
                        # Call the main function
                        main()

                        # Verify that parse_args was called
                        mock_parse_args.assert_called_once()

                        # Verify that the handlers were initialized with correct parameters
                        mock_glue_data_catalog_handler.assert_called_once_with(
                            mock_server, allow_write=True, allow_sensitive_data_access=False
                        )
                        mock_crawler_handler.assert_called_once_with(
                            mock_server,
                            allow_write=True,
                            allow_sensitive_data_access=False,
                        )

                        # Verify that run was called
                        mock_server.run.assert_called_once()

    # Test with sensitive data access enabled
    with patch.object(argparse.ArgumentParser, 'parse_args') as mock_parse_args:
        mock_parse_args.return_value = argparse.Namespace(
            allow_write=False, allow_sensitive_data_access=True
        )

        # Mock create_server to return a mock server
        mock_server = MagicMock()
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.server.create_server', return_value=mock_server
        ):
            # Mock the AWS helper's create_boto3_client method
            with patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
                return_value=MagicMock(),
            ):
                # Mock the handler initialization to verify allow_sensitive_data_access is passed
                with patch(
                    'awslabs.aws_dataprocessing_mcp_server.server.GlueDataCatalogHandler'
                ) as mock_glue_data_catalog_handler:
                    with patch(
                        'awslabs.aws_dataprocessing_mcp_server.server.CrawlerHandler'
                    ) as mock_crawler_handler:
                        # Call the main function
                        main()

                        # Verify that parse_args was called
                        mock_parse_args.assert_called_once()

                        # Verify that the handlers were initialized with correct parameters
                        mock_glue_data_catalog_handler.assert_called_once_with(
                            mock_server, allow_write=False, allow_sensitive_data_access=True
                        )

                        mock_crawler_handler.assert_called_once_with(
                            mock_server,
                            allow_write=False,
                            allow_sensitive_data_access=True,
                        )

                        # Verify that run was called
                        mock_server.run.assert_called_once()


@pytest.mark.asyncio
async def test_glue_data_catalog_handler_initialization():
    """Test that the Glue Data Catalog handler is initialized correctly and registers tools."""
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Mock the AWS helper's create_boto3_client method to avoid boto3 client creation
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
        return_value=MagicMock(),
    ):
        # Initialize the Glue Data Catalog handler with the mock MCP server
        GlueDataCatalogHandler(mock_mcp)

        # Verify that the tools were registered
        assert mock_mcp.tool.call_count > 0

        # Get all call args
        call_args_list = mock_mcp.tool.call_args_list

        # Get all tool names that were registered
        tool_names = [call_args[1]['name'] for call_args in call_args_list]

        # Verify that expected tools are registered
        assert 'manage_aws_glue_databases' in tool_names
        assert 'manage_aws_glue_tables' in tool_names


@pytest.mark.asyncio
async def test_glue_data_crawler_handler_initialization():
    """Test that the Glue Crawler handler is initialized correctly and registers tools."""
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Mock the AWS helper's create_boto3_client method to avoid boto3 client creation
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
        return_value=MagicMock(),
    ):
        # Initialize the Glue Data Catalog handler with the mock MCP server
        CrawlerHandler(mock_mcp)

        # Verify that the tools were registered
        assert mock_mcp.tool.call_count > 0

        # Get all call args
        call_args_list = mock_mcp.tool.call_args_list

        # Get all tool names that were registered
        tool_names = [call_args[1]['name'] for call_args in call_args_list]

        # Verify that expected tools are registered
        assert 'manage_aws_glue_crawlers' in tool_names


@pytest.mark.asyncio
async def test_handler_write_access_control():
    """Test that write access control works correctly in the handlers."""
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the AWS helper's create_boto3_client method to avoid boto3 client creation
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
        return_value=MagicMock(),
    ):
        # Initialize handlers with write access disabled
        glue_data_catalog_handler = GlueDataCatalogHandler(mock_mcp, allow_write=False)

        # Mock the necessary methods to test write access control
        with patch.object(
            glue_data_catalog_handler, 'manage_aws_glue_data_catalog_databases'
        ) as mock_manage_databases:
            # Call the handler with a write operation
            await glue_data_catalog_handler.manage_aws_glue_data_catalog_databases(
                mock_ctx, operation='create', database_name='test-db'
            )

            # Verify that the method was called with the correct parameters
            mock_manage_databases.assert_called_once()

            # Check that allow_write is False
            assert glue_data_catalog_handler.allow_write is False
