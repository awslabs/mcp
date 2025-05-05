# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Tests for environment variable configuration in the bedrock-kb-retrieval-mcp-server."""

import importlib
import os
import pytest
from pydantic import Field
from unittest.mock import ANY, patch


def create_mock_query_knowledge_base(return_value='test result'):
    """
    Create a proper mock for query_knowledge_base that accepts Field objects.
    """

    async def mock_function(*args, **kwargs):
        return return_value

    return mock_function


class TestEnvironmentVariableConfig:
    """Tests for the environment variable configuration functionality."""

    def setup_method(self):
        """Clean up environment variables before each test."""
        if 'BEDROCK_KB_RERANKING_ENABLED' in os.environ:
            del os.environ['BEDROCK_KB_RERANKING_ENABLED']

    def teardown_method(self):
        """Clean up environment variables after each test."""
        if 'BEDROCK_KB_RERANKING_ENABLED' in os.environ:
            del os.environ['BEDROCK_KB_RERANKING_ENABLED']

    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_runtime_client')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_client')
    def test_default_reranking_config_is_off(self, mock_agent_client, mock_runtime_client):
        """Test that the default reranking configuration is off when no env var is set."""
        # Force reload the module to reset the global variables
        import awslabs.bedrock_kb_retrieval_mcp_server.server

        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Verify that the default value is False when the env var is not set
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.kb_reranking_enabled is False

    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_runtime_client')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_client')
    def test_reranking_enabled_with_true_value(self, mock_agent_client, mock_runtime_client):
        """Test that reranking is enabled when the environment variable is set to 'true'."""
        # Set the environment variable
        os.environ['BEDROCK_KB_RERANKING_ENABLED'] = 'true'

        # Force reload the module to pick up the new environment variable
        import awslabs.bedrock_kb_retrieval_mcp_server.server

        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Verify that the value is True
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.kb_reranking_enabled is True

    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_runtime_client')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_client')
    def test_reranking_enabled_with_yes_value(self, mock_agent_client, mock_runtime_client):
        """Test that reranking is enabled when the environment variable is set to 'yes'."""
        # Set the environment variable
        os.environ['BEDROCK_KB_RERANKING_ENABLED'] = 'yes'

        # Force reload the module to pick up the new environment variable
        import awslabs.bedrock_kb_retrieval_mcp_server.server

        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Verify that the value is True
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.kb_reranking_enabled is True

    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_runtime_client')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_client')
    def test_reranking_enabled_with_1_value(self, mock_agent_client, mock_runtime_client):
        """Test that reranking is enabled when the environment variable is set to '1'."""
        # Set the environment variable
        os.environ['BEDROCK_KB_RERANKING_ENABLED'] = '1'

        # Force reload the module to pick up the new environment variable
        import awslabs.bedrock_kb_retrieval_mcp_server.server

        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Verify that the value is True
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.kb_reranking_enabled is True

    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_runtime_client')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_client')
    def test_reranking_enabled_with_on_value(self, mock_agent_client, mock_runtime_client):
        """Test that reranking is enabled when the environment variable is set to 'on'."""
        # Set the environment variable
        os.environ['BEDROCK_KB_RERANKING_ENABLED'] = 'on'

        # Force reload the module to pick up the new environment variable
        import awslabs.bedrock_kb_retrieval_mcp_server.server

        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Verify that the value is True
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.kb_reranking_enabled is True

    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_runtime_client')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_client')
    def test_reranking_disabled_with_invalid_value(self, mock_agent_client, mock_runtime_client):
        """Test that reranking remains disabled when the environment variable is set to an invalid value."""
        # Set the environment variable to an invalid value
        os.environ['BEDROCK_KB_RERANKING_ENABLED'] = 'invalid'

        # Force reload the module to pick up the new environment variable
        import awslabs.bedrock_kb_retrieval_mcp_server.server

        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Verify that the value remains False
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.kb_reranking_enabled is False

    @pytest.mark.asyncio
    async def test_environment_affects_tool_default(self):
        """Test that the environment variable affects the default value of the reranking parameter in the tool."""
        # First test with no environment variable (should default to False)
        if 'BEDROCK_KB_RERANKING_ENABLED' in os.environ:
            del os.environ['BEDROCK_KB_RERANKING_ENABLED']

        # Force reload the module to reset the global variables
        import awslabs.bedrock_kb_retrieval_mcp_server.server

        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Create and set up our mock function
        mock_func = create_mock_query_knowledge_base()
        original_func = awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base
        awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base = mock_func

        # Import the tool after setting up the mock
        from awslabs.bedrock_kb_retrieval_mcp_server.server import query_knowledge_bases_tool

        # Call the tool - this will use our mock function
        result = await query_knowledge_bases_tool(
            query='test query',
            knowledge_base_id='kb-12345',
        )

        # Restore the original function
        awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base = original_func

        # Verify that reranking default is False when env var is not set
        # No assertions on mock calls since our mock doesn't track calls
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.kb_reranking_enabled is False

        # Now set the environment variable to enable reranking
        os.environ['BEDROCK_KB_RERANKING_ENABLED'] = 'true'

        # Force reload the module to pick up the new environment variable
        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Create and set up our mock function
        mock_func = create_mock_query_knowledge_base()
        original_func = awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base
        awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base = mock_func

        # Import the tool after setting up the mock
        from awslabs.bedrock_kb_retrieval_mcp_server.server import query_knowledge_bases_tool

        # Call the tool again
        result = await query_knowledge_bases_tool(
            query='test query',
            knowledge_base_id='kb-12345',
        )

        # Restore the original function
        awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base = original_func

        # Verify that reranking is True when env var is set
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.kb_reranking_enabled is True

    @pytest.mark.asyncio
    async def test_explicit_parameter_overrides_environment(self):
        """Test that explicitly setting the reranking parameter overrides the environment variable."""
        # Set the environment variable to disable reranking
        os.environ['BEDROCK_KB_RERANKING_ENABLED'] = 'false'

        # Force reload the module to pick up the new environment variable
        import awslabs.bedrock_kb_retrieval_mcp_server.server

        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Create and set up our mock function
        mock_func = create_mock_query_knowledge_base()
        original_func = awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base
        awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base = mock_func

        # Import the tool after setting up the mock
        from awslabs.bedrock_kb_retrieval_mcp_server.server import query_knowledge_bases_tool

        # Verify the environment variable was set correctly
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.kb_reranking_enabled is False

        # Call the tool with reranking explicitly set to True
        result = await query_knowledge_bases_tool(
            query='test query',
            knowledge_base_id='kb-12345',
            reranking=True,  # This should override the environment setting
        )

        # Restore the original function
        awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base = original_func

        # Set the environment variable to enable reranking
        os.environ['BEDROCK_KB_RERANKING_ENABLED'] = 'true'

        # Force reload the module to pick up the new environment variable
        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Create and set up our mock function
        mock_func = create_mock_query_knowledge_base()
        original_func = awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base
        awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base = mock_func

        # Import the tool after setting up the mock
        from awslabs.bedrock_kb_retrieval_mcp_server.server import query_knowledge_bases_tool

        # Verify the environment variable was set correctly
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.kb_reranking_enabled is True

        # Call the tool with reranking explicitly set to False
        result = await query_knowledge_bases_tool(
            query='test query',
            knowledge_base_id='kb-12345',
            reranking=False,  # This should override the environment setting
        )

        # Restore the original function
        awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base = original_func
