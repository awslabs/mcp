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

"""Tests for CDK documentation tool."""

import pytest
from awslabs.aws_iac_mcp_server.knowledge_models import KnowledgeResult
from awslabs.aws_iac_mcp_server.tools.cdk_tools import search_cdk_documentation_tool
from unittest.mock import AsyncMock, patch


class TestSearchCDKDocumentation:
    """Test search_cdk_documentation_tool function."""

    @pytest.mark.asyncio
    async def test_search_cdk_documentation_success(self):
        """Test successful CDK documentation search."""
        mock_response = [
            KnowledgeResult(
                rank=1,
                title='AWS CDK Constructs',
                url='https://docs.aws.amazon.com/cdk/latest/guide/constructs.html',
                context='Learn about CDK constructs and how to use them.',
            )
        ]
        with patch(
            'awslabs.aws_iac_mcp_server.tools.cdk_tools.search_documentation',
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = mock_response

            result = await search_cdk_documentation_tool('constructs')

            assert len(result.knowledge_response) == 1
            assert result.knowledge_response[0].title == 'AWS CDK Constructs'
            assert result.next_step_guidance is not None
            mock_search.assert_called_once_with(
                search_phrase='constructs', topic='cdk_docs', limit=10
            )

    @pytest.mark.asyncio
    async def test_search_cdk_documentation_error(self):
        """Test CDK documentation search with error handling."""
        with patch(
            'awslabs.aws_iac_mcp_server.tools.cdk_tools.search_documentation',
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.side_effect = Exception('Network error')

            with pytest.raises(Exception, match='Network error'):
                await search_cdk_documentation_tool('constructs')
