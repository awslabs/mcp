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

"""Tests for search CloudFormation documentation tool."""

import pytest
from awslabs.aws_iac_mcp_server.knowledge_models import KnowledgeResult
from awslabs.aws_iac_mcp_server.tools.cdk_tools import search_cloudformation_documentation_tool
from unittest.mock import AsyncMock, patch


class TestSearchCloudFormationDocumentation:
    """Test search_cloudformation_documentation_tool function."""

    @pytest.mark.asyncio
    async def test_search_cloudformation_documentation_success(self):
        """Test successful CloudFormation documentation search."""
        mock_response = [
            KnowledgeResult(
                rank=1,
                title='AWS::Lambda::Function',
                url='https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-lambda-function.html',
                context='Creates a Lambda function resource.',
            )
        ]
        with patch(
            'awslabs.aws_iac_mcp_server.tools.cdk_tools.search_documentation',
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = mock_response

            result = await search_cloudformation_documentation_tool('AWS::Lambda::Function')

            assert len(result.knowledge_response) == 1
            assert result.knowledge_response[0].title == 'AWS::Lambda::Function'
            assert result.next_step_guidance is None
            mock_search.assert_called_once_with(
                search_phrase='AWS::Lambda::Function', topic='cloudformation', limit=10
            )

    @pytest.mark.asyncio
    async def test_search_cloudformation_documentation_error(self):
        """Test CloudFormation documentation search with error handling."""
        with patch(
            'awslabs.aws_iac_mcp_server.tools.cdk_tools.search_documentation',
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.side_effect = Exception('Search failed')
            with pytest.raises(Exception, match='Search failed'):
                await search_cloudformation_documentation_tool('test')
