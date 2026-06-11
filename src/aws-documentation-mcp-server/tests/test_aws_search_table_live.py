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
"""Live tests for the search_table tool in the AWS Documentation MCP server."""

import pytest
from awslabs.aws_documentation_mcp_server.server_aws import (
    search_table as search_table_global,
)
from tests.constants import TEST_USER_AGENT
from unittest.mock import patch


class MockContext:
    """Mock context for testing."""

    async def error(self, message):
        """Mock error method."""
        print(f'Error: {message}')


@pytest.mark.asyncio
@pytest.mark.live
async def test_search_table_bedrock_quotas():
    """Test searching the Bedrock quotas table for a specific model."""
    url = 'https://docs.aws.amazon.com/general/latest/gr/bedrock.html'
    section_title = 'Amazon Bedrock service quotas'
    query = 'Titan Text Embeddings V2'
    ctx = MockContext()

    with patch(
        'awslabs.aws_documentation_mcp_server.server_aws.DEFAULT_USER_AGENT',
        TEST_USER_AGENT,
    ):
        result = await search_table_global(
            ctx, url=url, section_title=section_title, query=query, max_rows=20
        )

        assert result is not None
        assert result.tables_with_matches >= 1
        assert result.query == query
        assert any('Titan Text Embeddings V2' in str(r.rows) for r in result.results)


@pytest.mark.asyncio
@pytest.mark.live
async def test_search_table_iam_ec2_actions():
    """Test searching the IAM Service Authorization Reference for EC2 actions."""
    url = 'https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonec2.html'
    section_title = 'Actions defined by Amazon EC2'
    query = 'RunInstances'
    ctx = MockContext()

    with patch(
        'awslabs.aws_documentation_mcp_server.server_aws.DEFAULT_USER_AGENT',
        TEST_USER_AGENT,
    ):
        result = await search_table_global(
            ctx, url=url, section_title=section_title, query=query, max_rows=20
        )

        assert result is not None
        assert result.tables_with_matches >= 1
        assert any('RunInstances' in str(r.rows) for r in result.results)


@pytest.mark.asyncio
@pytest.mark.live
async def test_search_table_no_matches():
    """Test that a query with no matches returns empty rows."""
    url = 'https://docs.aws.amazon.com/general/latest/gr/bedrock.html'
    section_title = 'Amazon Bedrock service quotas'
    query = 'xyznonexistentquota123'
    ctx = MockContext()

    with patch(
        'awslabs.aws_documentation_mcp_server.server_aws.DEFAULT_USER_AGENT',
        TEST_USER_AGENT,
    ):
        result = await search_table_global(
            ctx, url=url, section_title=section_title, query=query, max_rows=20
        )

        assert result is not None
        assert result.tables_with_matches == 0
        assert result.results == []
        assert result.hint is not None


@pytest.mark.asyncio
@pytest.mark.live
async def test_read_sections_truncates_large_table():
    """Test that read_sections truncates the Bedrock quotas table."""
    from awslabs.aws_documentation_mcp_server.server_aws import (
        read_sections as read_sections_global,
    )

    url = 'https://docs.aws.amazon.com/general/latest/gr/bedrock.html'
    section_titles = ['Amazon Bedrock service quotas']
    ctx = MockContext()

    with patch(
        'awslabs.aws_documentation_mcp_server.server_aws.DEFAULT_USER_AGENT',
        TEST_USER_AGENT,
    ):
        result = await read_sections_global(ctx, url=url, section_titles=section_titles)

        assert 'Table truncated' in result
        assert 'search_table' in result
        # Should NOT contain hundreds of rows
        row_count = result.count('\n|')
        assert row_count < 30  # truncated to preview rows, not 437


@pytest.mark.asyncio
@pytest.mark.live
async def test_search_table_multi_table_section():
    """Test searching across multiple tables in EC2 Service quotas section."""
    url = 'https://docs.aws.amazon.com/general/latest/gr/ec2-service.html'
    section_title = 'Service quotas'
    query = 'ImportImage'
    ctx = MockContext()

    with patch(
        'awslabs.aws_documentation_mcp_server.server_aws.DEFAULT_USER_AGENT',
        TEST_USER_AGENT,
    ):
        result = await search_table_global(
            ctx, url=url, section_title=section_title, query=query, max_rows=20
        )

        assert result is not None
        assert result.tables_searched > 1  # Multiple tables in this section
        assert result.tables_with_matches >= 1
        # ImportImage is in the VM Import/Export table, not the main EC2 table
        assert any('ImportImage' in str(r.rows) for r in result.results)
