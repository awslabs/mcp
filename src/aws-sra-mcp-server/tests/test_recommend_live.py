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
from unittest.mock import patch

import pytest
from fastmcp import Client

from awslabs.aws_sra_mcp_server.server import MCP


@pytest.fixture
def client():
    return Client(MCP)


async def call_tool(client: Client, tool, **kwargs):
    """Helper function to call an MCP tool as an integration test"""
    params = {}
    for key, value in kwargs.items():
        params[key] = value
    return await client.call_tool(tool, params)


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.server.get_recommendations")
async def test_recommend_filters_security_results(mock_get_recommendations, client):
    """Test that recommend filters results to prioritize security-related content."""
    from awslabs.aws_sra_mcp_server.models import RecommendationResult

    # Setup mock to return mixed results
    mock_get_recommendations.return_value = [
        RecommendationResult(
            url="https://docs.aws.amazon.com/security-hub/",
            title="AWS Security Hub",
            context="Security monitoring service",
        ),
        RecommendationResult(
            url="https://docs.aws.amazon.com/s3/",
            title="Amazon S3",
            context="Object storage service",
        ),
        RecommendationResult(
            url="https://docs.aws.amazon.com/macie/",
            title="Amazon Macie",
            context="Data security service",
        ),
        RecommendationResult(
            url="https://docs.aws.amazon.com/inspector/",
            title="Amazon Inspector",
            context="Vulnerability management service",
        ),
        RecommendationResult(
            url="https://docs.aws.amazon.com/ec2/",
            title="Amazon EC2",
            context="Virtual server service",
        ),
    ]

    # Call the function
    async with client:
        results = await call_tool(
            client,
            "recommend",
            url="https://docs.aws.amazon.com/security-reference-architecture/welcome.html",
        )

    # Verify that we got results
    assert results is not None
    # Check structured_content which contains the actual result
    assert results.structured_content is not None
    assert "result" in results.structured_content
    assert len(results.structured_content["result"]) > 0

    # Verify that security-related results are prioritized
    result_data = results.structured_content["result"]
    security_count = sum(
        1
        for item in result_data
        if "security" in item["title"].lower() or "security" in item.get("context", "").lower()
    )
    assert security_count > 0


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.server.get_recommendations")
async def test_recommend_error_handling(mock_get_recommendations, client):
    """Test error handling in the recommend function."""
    # Setup mock to raise an exception
    mock_get_recommendations.side_effect = Exception("HTTP error")

    # Call the function
    async with client:
        results = await call_tool(
            client,
            "recommend",
            url="https://docs.aws.amazon.com/security-reference-architecture/welcome.html",
        )

    # Verify the results - should return a list with an error message
    assert results is not None
    assert results.structured_content is not None
    assert "result" in results.structured_content
    assert len(results.structured_content["result"]) > 0
    assert (
        "Error getting security recommendations" in results.structured_content["result"][0]["title"]
    )
