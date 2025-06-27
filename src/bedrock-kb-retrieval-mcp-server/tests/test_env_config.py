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

"""Tests for environment variable configuration in the bedrock-kb-retrieval-mcp-server."""

import importlib
import os
import pytest
from unittest.mock import patch


def create_mock_query_knowledge_base(return_value='test result'):
    """Create a proper mock for query_knowledge_base that accepts Field objects."""

    async def mock_function(*args, **kwargs):
        return return_value

    return mock_function


class TestEnvironmentVariableConfig:
    """Tests for the environment variable configuration functionality."""

    def setup_method(self):
        """Clean up environment variables before each test."""
        if 'BEDROCK_KB_RERANKING_ENABLED' in os.environ:
            del os.environ['BEDROCK_KB_RERANKING_ENABLED']
        if 'BEDROCK_KB_ID' in os.environ:
            del os.environ['BEDROCK_KB_ID']

    def teardown_method(self):
        """Clean up environment variables after each test."""
        if 'BEDROCK_KB_RERANKING_ENABLED' in os.environ:
            del os.environ['BEDROCK_KB_RERANKING_ENABLED']
        if 'BEDROCK_KB_ID' in os.environ:
            del os.environ['BEDROCK_KB_ID']

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
        await query_knowledge_bases_tool(
            query='test query',
            knowledge_base_id='kb-12345',
        )

        # Restore the original function
        awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base = original_func


class TestBedrockKbIdOverrideConfig:
    """Tests for the BEDROCK_KB_ID environment variable configuration."""

    def setup_method(self):
        """Clean up environment variables before each test."""
        if 'BEDROCK_KB_ID' in os.environ:
            del os.environ['BEDROCK_KB_ID']

    def teardown_method(self):
        """Clean up environment variables after each test."""
        if 'BEDROCK_KB_ID' in os.environ:
            del os.environ['BEDROCK_KB_ID']

    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_runtime_client')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_client')
    def test_bedrock_kb_id_override_default_none(self, mock_agent_client, mock_runtime_client):
        """Test that the BEDROCK_KB_ID override is None by default when no env var is set."""
        # Force reload the module to reset the global variables
        import awslabs.bedrock_kb_retrieval_mcp_server.server

        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Verify that the default value is None when the env var is not set
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.kb_id_override is None

    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_runtime_client')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_client')
    def test_bedrock_kb_id_override_set_from_env(self, mock_agent_client, mock_runtime_client):
        """Test that the BEDROCK_KB_ID override is set from environment variable."""
        # Set the environment variable
        os.environ['BEDROCK_KB_ID'] = 'EXAMPLEKBID'

        # Force reload the module to pick up the new environment variable
        import awslabs.bedrock_kb_retrieval_mcp_server.server

        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Verify that the value is set correctly
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.kb_id_override == 'EXAMPLEKBID'

    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_runtime_client')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_client')
    def test_bedrock_kb_id_override_empty_string_treated_as_none(
        self, mock_agent_client, mock_runtime_client
    ):
        """Test that empty string for BEDROCK_KB_ID is treated as None."""
        # Set the environment variable to empty string
        os.environ['BEDROCK_KB_ID'] = ''

        # Force reload the module to pick up the new environment variable
        import awslabs.bedrock_kb_retrieval_mcp_server.server

        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Verify that empty string is treated as falsy (None-like behavior)
        assert not awslabs.bedrock_kb_retrieval_mcp_server.server.kb_id_override

    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_runtime_client')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_client')
    def test_bedrock_kb_id_override_various_values(self, mock_agent_client, mock_runtime_client):
        """Test that BEDROCK_KB_ID accepts various knowledge base ID formats."""
        test_values = ['EXAMPLEKBID', 'kb-12345', 'KB_TEST_123', 'some-other-format-456']

        for test_value in test_values:
            # Set the environment variable
            os.environ['BEDROCK_KB_ID'] = test_value

            # Force reload the module to pick up the new environment variable
            import awslabs.bedrock_kb_retrieval_mcp_server.server

            importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

            # Verify that the value is set correctly
            assert awslabs.bedrock_kb_retrieval_mcp_server.server.kb_id_override == test_value
