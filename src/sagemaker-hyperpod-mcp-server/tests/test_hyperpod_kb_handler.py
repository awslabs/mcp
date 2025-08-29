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
# ruff: noqa: D101, D102, D103, E402
"""Tests for the HyperPodKnowledgeBaseHandler class."""

import pytest
import sys
from awslabs.sagemaker_hyperpod_mcp_server.consts import KB_AWS_REGION, KB_AWS_SERVICE
from unittest.mock import MagicMock, patch


# Mock the requests_auth_aws_sigv4 module
sys.modules['requests_auth_aws_sigv4'] = MagicMock()
from awslabs.sagemaker_hyperpod_mcp_server.hyperpod_kb_handler import (
    HyperPodKnowledgeBaseHandler,
)


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server."""
    return MagicMock()


class TestHyperPodKnowledgeBaseHandler:
    """Tests for the HyperPodKnowledgeBaseHandler class."""

    @pytest.mark.asyncio
    @patch('awslabs.sagemaker_hyperpod_mcp_server.hyperpod_kb_handler.AWSSigV4')
    async def test_search_hyperpod_knowledge_base_success(self, mock_aws_auth, mock_mcp):
        """Test successful search of HyperPod knowledge base."""
        # Create a mock for AWSSigV4 to prevent AWS credential access
        mock_auth_instance = MagicMock()
        mock_aws_auth.return_value = mock_auth_instance

        handler = HyperPodKnowledgeBaseHandler(mock_mcp)
        expected_response = 'troubleshooting steps'
        with patch(
            'awslabs.sagemaker_hyperpod_mcp_server.hyperpod_kb_handler.requests.post'
        ) as mock_post:
            mock_resp = MagicMock()
            mock_resp.text = expected_response
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            result = await handler.search_hyperpod_knowledge_base('test query')
            assert result == expected_response
            mock_post.assert_called_once()

            # Verify that AWSSigV4 was initialized with the correct parameters
            mock_aws_auth.assert_called_once_with(KB_AWS_SERVICE, region=KB_AWS_REGION)

    @pytest.mark.asyncio
    @patch('awslabs.sagemaker_hyperpod_mcp_server.hyperpod_kb_handler.AWSSigV4')
    async def test_search_hyperpod_knowledge_base_error(self, mock_aws_auth, mock_mcp):
        """Test error handling in search of HyperPod knowledge base."""
        # Create a mock for AWSSigV4 to prevent AWS credential access
        mock_auth_instance = MagicMock()
        mock_aws_auth.return_value = mock_auth_instance

        handler = HyperPodKnowledgeBaseHandler(mock_mcp)
        with patch(
            'awslabs.sagemaker_hyperpod_mcp_server.hyperpod_kb_handler.requests.post'
        ) as mock_post:
            mock_post.side_effect = Exception('network error')
            result = await handler.search_hyperpod_knowledge_base('test query')
            assert 'Error: network error' in result

    def test_init(self, mock_mcp):
        """Test initialization of the HyperPodKnowledgeBaseHandler."""
        HyperPodKnowledgeBaseHandler(mock_mcp)

        # Verify that the tool was registered with the MCP server
        mock_mcp.tool.assert_called_once()
        args, kwargs = mock_mcp.tool.call_args
        assert kwargs['name'] == 'search_hyperpod_knowledge_base'
