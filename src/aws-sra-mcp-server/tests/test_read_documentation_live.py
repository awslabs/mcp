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

import os
from unittest.mock import patch

import pytest
from fastmcp import Client
from mcp.types import TextContent

from awslabs.aws_sra_mcp_server.server import MCP
from awslabs.aws_sra_mcp_server.util import extract_content_from_html


@pytest.fixture
def client():
    return Client(MCP)


async def call_tool(client: Client, tool, **kwargs):
    """Helper function to call an MCP tool as an integration test"""
    result = await client.call_tool(tool, kwargs)
    # Extract the text content from the result
    if hasattr(result, "content") and len(result.content) > 0:
        assert isinstance(result.content[0], TextContent)
        return result.content[0].text
    return result


def test_extract_content_from_html_with_sample():
    """Test extract_content_from_html with a sample HTML file."""
    # Get the path to the sample HTML file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sample_path = os.path.join(current_dir, "resources", "sra_sample.html")

    # Read the sample HTML file
    with open(sample_path, "r") as f:
        html_content = f.read()

    # Extract content
    result = extract_content_from_html(html_content)

    # Verify the result
    assert "AWS Security Reference Architecture (AWS SRA)" in result
    assert "holistic set of guidelines" in result
    assert "Security Tooling Account" in result
    assert "Log Archive Account" in result
    assert "AWS Identity and Access Management (IAM)" in result

    # Verify that footer content is not included
    assert "© 2023, Amazon Web Services" not in result


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.server.read_documentation_html")
async def test_read_documentation_with_pagination(mock_read_impl, client):
    """Test read_documentation with pagination."""

    # Setup mock to return different content for different start indices
    async def mock_impl(ctx, url, max_length, start_index, session_uuid):
        if start_index == 0:
            return (
                "AWS Security Reference Architecture Documentation from "
                "https://docs.aws.amazon.com/test.html:\n\nPart 1\n\n<e>Content truncated. Call "
                "the read_documentation tool with start_index=6 to get more content.</e>"
            )
        elif start_index == 6:
            return (
                "AWS Security Reference Architecture Documentation from "
                "https://docs.aws.amazon.com/test.html:\n\nPart 2\n\n<e>Content truncated. Call "
                "the read_documentation tool with start_index=12 to get more content.</e>"
            )
        else:
            return (
                "AWS Security Reference Architecture Documentation from "
                "https://docs.aws.amazon.com/test.html:\n\nPart 3"
            )

    mock_read_impl.side_effect = mock_impl

    async with client:
        # First call with start_index=0
        result1 = await call_tool(
            client,
            "read_content",
            url="https://docs.aws.amazon.com/test.html",
            max_length=10,
            start_index=0,
        )
        assert isinstance(result1, str)
        assert "Part 1" in result1
        assert "start_index=6" in result1

        # Second call with start_index=6
        result2 = await call_tool(
            client,
            "read_content",
            url="https://docs.aws.amazon.com/test.html",
            max_length=10,
            start_index=6,
        )
        assert isinstance(result2, str)
        assert "Part 2" in result2
        assert "start_index=12" in result2

        # Third call with start_index=12
        result3 = await call_tool(
            client,
            "read_content",
            url="https://docs.aws.amazon.com/test.html",
            max_length=10,
            start_index=12,
        )
        assert isinstance(result3, str)
        assert "Part 3" in result3
        assert "Content truncated" not in result3
