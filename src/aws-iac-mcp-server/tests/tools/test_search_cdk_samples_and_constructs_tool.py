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

"""Tests for search CDK samples and constructs tool."""

import pytest
from awslabs.aws_iac_mcp_server.knowledge_models import KnowledgeResult
from awslabs.aws_iac_mcp_server.tools.iac_tools import search_cdk_samples_and_constructs_tool
from unittest.mock import AsyncMock, patch


class TestSearchCDKSamplesAndConstructs:
    """Test search_cdk_samples_and_constructs_tool function."""

    @pytest.mark.asyncio
    async def test_search_cdk_samples_and_constructs_success(self):
        """Test successful CDK samples and constructs search."""
        mock_response = [
            KnowledgeResult(
                rank=1,
                title='Lambda Function Example',
                url='https://docs.aws.amazon.com/cdk/samples/lambda.html',
                context='Example of creating Lambda function with CDK.',
            )
        ]
        with patch(
            'awslabs.aws_iac_mcp_server.tools.iac_tools.search_documentation',
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = mock_response

            result = await search_cdk_samples_and_constructs_tool('lambda')

            assert len(result.knowledge_response) == 1
            assert result.knowledge_response[0].title == 'Lambda Function Example'
            assert result.next_step_guidance is not None
            mock_search.assert_called_once_with(
                search_phrase='lambda typescript', topic='cdk_constructs', limit=10
            )

    @pytest.mark.asyncio
    async def test_search_cdk_samples_and_constructs_with_language(self):
        """Test CDK samples and constructs search with language parameter."""
        with patch(
            'awslabs.aws_iac_mcp_server.tools.iac_tools.search_documentation',
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await search_cdk_samples_and_constructs_tool('s3', 'python')

            mock_search.assert_called_once_with(
                search_phrase='s3 python', topic='cdk_constructs', limit=10
            )

    @pytest.mark.asyncio
    async def test_search_cdk_samples_and_constructs_error(self):
        """Test CDK samples and constructs search with error handling."""
        with patch(
            'awslabs.aws_iac_mcp_server.tools.iac_tools.search_documentation',
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.side_effect = Exception('Search failed')

            with pytest.raises(Exception, match='Search failed'):
                await search_cdk_samples_and_constructs_tool('test')
