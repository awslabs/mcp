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
# ruff: noqa: D101, D102, D103
"""Tests for the EKSKnowledgeBaseHandler class."""

import pytest
from awslabs.eks_mcp_server.eks_kb_handler import EKSKnowledgeBaseHandler
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server."""
    return MagicMock()


class TestEKSKnowledgeBaseHandler:
    """Tests for the EKSKnowledgeBaseHandler class."""

    @pytest.mark.asyncio
    @patch('awslabs.eks_mcp_server.eks_kb_handler.AWSSigV4')
    async def test_search_eks_troubleshoot_guide_success(self, mock_aws_auth, mock_mcp):
        # Create a mock for AWSSigV4 to prevent AWS credential access
        mock_auth_instance = MagicMock()
        mock_aws_auth.return_value = mock_auth_instance

        handler = EKSKnowledgeBaseHandler(mock_mcp)
        expected_response = 'troubleshooting steps'
        with patch('awslabs.eks_mcp_server.eks_kb_handler.requests.post') as mock_post:
            mock_resp = MagicMock()
            mock_resp.text = expected_response
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            result = await handler.search_eks_troubleshoot_guide('test query')
            assert result == expected_response
            mock_post.assert_called_once()

            # Verify that AWSSigV4 was initialized with the correct parameters
            mock_aws_auth.assert_called_once_with('eks-mcpserver', region='us-west-2')

    @pytest.mark.asyncio
    @patch('awslabs.eks_mcp_server.eks_kb_handler.AWSSigV4')
    async def test_search_eks_troubleshoot_guide_error(self, mock_aws_auth, mock_mcp):
        # Create a mock for AWSSigV4 to prevent AWS credential access
        mock_auth_instance = MagicMock()
        mock_aws_auth.return_value = mock_auth_instance

        handler = EKSKnowledgeBaseHandler(mock_mcp)
        with patch('awslabs.eks_mcp_server.eks_kb_handler.requests.post') as mock_post:
            mock_post.side_effect = Exception('network error')
            result = await handler.search_eks_troubleshoot_guide('test query')
            assert 'Error: network error' in result
