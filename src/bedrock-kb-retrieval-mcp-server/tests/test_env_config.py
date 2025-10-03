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
        if 'RERANK_MODEL_ARN' in os.environ:
            del os.environ['RERANK_MODEL_ARN']

    def teardown_method(self):
        """Clean up environment variables after each test."""
        if 'RERANK_MODEL_ARN' in os.environ:
            del os.environ['RERANK_MODEL_ARN']

    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_runtime_client')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_client')
    def test_default_reranking_config_is_off(self, mock_agent_client, mock_runtime_client):
        """Test that the default reranking configuration is off when no ARN is set."""
        # Force reload the module to reset the global variables
        import awslabs.bedrock_kb_retrieval_mcp_server.server

        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Verify that the default value is None when the env var is not set
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.rerank_model_arn is None

    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_runtime_client')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_client')
    def test_reranking_enabled_with_arn_value(self, mock_agent_client, mock_runtime_client):
        """Test that reranking is enabled when the RERANK_MODEL_ARN is set."""
        # Set the environment variable
        os.environ['RERANK_MODEL_ARN'] = 'arn:aws:bedrock:us-west-2::foundation-model/amazon.rerank-v1:0'

        # Force reload the module to pick up the new environment variable
        import awslabs.bedrock_kb_retrieval_mcp_server.server

        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Verify that the ARN is set
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.rerank_model_arn == 'arn:aws:bedrock:us-west-2::foundation-model/amazon.rerank-v1:0'


    @pytest.mark.asyncio
    async def test_environment_affects_tool_behavior(self):
        """Test that the RERANK_MODEL_ARN environment variable affects the tool behavior."""
        # First test with no environment variable (should default to None)
        if 'RERANK_MODEL_ARN' in os.environ:
            del os.environ['RERANK_MODEL_ARN']

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

        # Verify that ARN is None when env var is not set
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.rerank_model_arn is None

        # Now set the environment variable
        os.environ['RERANK_MODEL_ARN'] = 'arn:aws:bedrock:us-west-2::foundation-model/amazon.rerank-v1:0'

        # Force reload the module to pick up the new environment variable
        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Create and set up our mock function
        mock_func = create_mock_query_knowledge_base()
        original_func = awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base
        awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base = mock_func

        # Import the tool after setting up the mock
        from awslabs.bedrock_kb_retrieval_mcp_server.server import query_knowledge_bases_tool

        # Call the tool again
        await query_knowledge_bases_tool(
            query='test query',
            knowledge_base_id='kb-12345',
        )

        # Restore the original function
        awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base = original_func

        # Verify that ARN is set when env var is provided
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.rerank_model_arn == 'arn:aws:bedrock:us-west-2::foundation-model/amazon.rerank-v1:0'

