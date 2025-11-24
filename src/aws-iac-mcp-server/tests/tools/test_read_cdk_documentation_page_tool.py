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

"""Tests for read CDK documentation page tool."""

import pytest
from awslabs.aws_iac_mcp_server.knowledge_models import KnowledgeResult
from awslabs.aws_iac_mcp_server.tools.cdk_tools import read_cdk_documentation_page_tool
from unittest.mock import AsyncMock, patch


class TestReadCDKDocumentationPage:
    """Test read_cdk_documentation_page_tool function."""

    @pytest.mark.asyncio
    async def test_read_cdk_documentation_page_success(self):
        """Test successful CDK documentation page read."""
        mock_response = [
            KnowledgeResult(
                rank=1,
                title='CDK Documentation',
                url='https://docs.aws.amazon.com/cdk/test.html',
                context='Full documentation content here...',
            )
        ]
        with patch(
            'awslabs.aws_iac_mcp_server.tools.cdk_tools.read_documentation',
            new_callable=AsyncMock,
        ) as mock_read:
            mock_read.return_value = mock_response

            result = await read_cdk_documentation_page_tool(
                'https://docs.aws.amazon.com/cdk/test.html'
            )

            assert len(result.knowledge_response) == 1
            assert result.knowledge_response[0].context == 'Full documentation content here...'
            assert result.next_step_guidance is not None
            mock_read.assert_called_once_with(
                url='https://docs.aws.amazon.com/cdk/test.html', start_index=0
            )

    @pytest.mark.asyncio
    async def test_read_cdk_documentation_page_with_start_index(self):
        """Test CDK documentation page read with start index."""
        with patch(
            'awslabs.aws_iac_mcp_server.tools.cdk_tools.read_documentation',
            new_callable=AsyncMock,
        ) as mock_read:
            mock_read.return_value = []

            await read_cdk_documentation_page_tool(
                'https://docs.aws.amazon.com/cdk/test.html', 100
            )

            mock_read.assert_called_once_with(
                url='https://docs.aws.amazon.com/cdk/test.html', start_index=100
            )

    @pytest.mark.asyncio
    async def test_read_cdk_documentation_page_error(self):
        """Test CDK documentation page read with error handling."""
        with patch(
            'awslabs.aws_iac_mcp_server.tools.cdk_tools.read_documentation',
            new_callable=AsyncMock,
        ) as mock_read:
            mock_read.side_effect = Exception('Read failed')

            with pytest.raises(Exception, match='Read failed'):
                await read_cdk_documentation_page_tool('https://docs.aws.amazon.com/cdk/test.html')
