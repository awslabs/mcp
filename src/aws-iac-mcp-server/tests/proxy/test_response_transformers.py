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

import json
import pytest
from awslabs.aws_iac_mcp_server.proxy.response_transformers import (
    parse_read_result,
    transform_read_result,
)
from mcp.types import TextContent
from unittest.mock import AsyncMock, MagicMock


class TestTransformReadResult:
    """Test cases for transform_read_result function."""

    def test_transformer_creation(self):
        """Test that transformer function is created."""
        guidance = 'Use search_cdk_samples for code examples'
        transformer = transform_read_result(guidance)

        assert callable(transformer)

    @pytest.mark.asyncio
    async def test_transformer_execution(self):
        """Test transformer execution with valid result."""
        guidance = 'Use search_cdk_samples for code examples'
        transformer = transform_read_result(guidance)

        mock_result = MagicMock()
        mock_result.isError = False
        mock_content = TextContent(
            type='text',
            text=json.dumps({'content': {'result': 'This is the complete documentation content'}}),
        )
        mock_result.content = [mock_content]

        # Mock forward to return our mock result
        from unittest.mock import patch

        with patch(
            'awslabs.aws_iac_mcp_server.proxy.response_transformers.forward',
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await transformer(url='test', start_index=0, max_length=10000)
            result_dict = json.loads(result)

            assert 'knowledge_response' in result_dict
            assert 'next_step_guidance' in result_dict
            assert result_dict['next_step_guidance'] == guidance
            assert len(result_dict['knowledge_response']) == 1
            assert result_dict['knowledge_response'][0]['context'] == (
                'This is the complete documentation content'
            )
            assert result_dict['knowledge_response'][0]['rank'] == 1


class TestParseReadResult:
    """Test cases for parse_read_result function."""

    def test_parse_valid_result(self):
        """Test parsing valid result."""
        mock_result = MagicMock()
        mock_result.isError = False
        mock_content = TextContent(
            type='text', text=json.dumps({'content': {'result': 'Documentation content'}})
        )
        mock_result.content = [mock_content]

        results = parse_read_result(mock_result)

        assert len(results) == 1
        assert results[0].rank == 1
        assert results[0].context == 'Documentation content'

    def test_parse_error_result(self):
        """Test parsing error result."""
        mock_result = MagicMock()
        mock_result.isError = True
        mock_result.content = 'Error occurred'

        with pytest.raises(Exception, match='Tool call returned an error'):
            parse_read_result(mock_result)

    def test_parse_empty_content(self):
        """Test parsing empty content."""
        mock_result = MagicMock()
        mock_result.isError = False
        mock_result.content = []

        with pytest.raises(Exception, match='Empty response from tool'):
            parse_read_result(mock_result)
