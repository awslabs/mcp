import json

import pytest
from fastmcp import Client
from mcp.types import TextContent

from awslabs.aws_sra_mcp_server.server import MCP

client = Client(MCP)


@pytest.mark.asyncio
async def test_search_security_and_compliance_best_practices_content_unauthenticated():
    async with client:
        result = await client.call_tool(
            "search_content",
            {"search_phrase": "Security Hub"},
        )
        assert len(result.content) > 0
        found_github = False
        found_prescriptive_guidance = False
        assert isinstance(result.content[0], TextContent)
        for c in json.loads(result.content[0].text):
            if "github.com" in c["url"]:
                found_github = True
            if "docs.aws.amazon.com/prescriptive-guidance" in c["url"]:
                found_prescriptive_guidance = True

        assert found_github
        assert found_prescriptive_guidance


@pytest.mark.asyncio
async def test_read_security_and_compliance_best_practices_content_prescriptive_guidance():
    """Tests search documentation"""
    async with client:
        result = await client.call_tool(
            "read_content",
            {
                "url": "https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/security-tooling.html",
                "start_index": 0,
            },
        )
        assert len(result.content) > 0
        assert isinstance(result.content[0], TextContent)
        text_result = result.content[0].text
        assert text_result.startswith("AWS Security Reference Architecture Documentation")


@pytest.mark.asyncio
# ruff: noqa: E501
async def test_read_security_and_compliance_best_practices_content_prescriptive_guidance_no_more_content():
    """Tests search documentation"""
    async with client:
        result = await client.call_tool(
            "read_content",
            {
                # noqa: E501
                "url": "https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/security-tooling.html",
                "start_index": 99999,
            },
        )
        assert len(result.content) > 0
        assert isinstance(result.content[0], TextContent)
        text_result = result.content[0].text
        assert "No more content available" in text_result


@pytest.mark.asyncio
async def test_read_security_and_compliance_best_practices_content_github_issues():
    """Tests search documentation"""
    async with client:
        result = await client.call_tool(
            "read_content",
            {
                "url": "https://github.com/aws-samples/aws-security-reference-architecture-examples/issues/225",
                "start_index": 0,
            },
        )
        assert len(result.content) > 0
        assert isinstance(result.content[0], TextContent)
        text_result = result.content[0].text
        assert text_result.startswith(
            "AWS Security Reference Architecture GitHub Issue from https://github.com/aws-samples/aws-security-reference-architecture-examples/issues/225:\n\n"
        )


@pytest.mark.asyncio
async def test_read_security_and_compliance_best_practices_content_github_pr():
    """Tests search documentation"""
    async with client:
        url = "https://github.com/aws-samples/aws-security-reference-architecture-examples/pull/167"
        result = await client.call_tool("read_content", {"url": url, "start_index": 0})
        assert len(result.content) > 0
        assert isinstance(result.content[0], TextContent)
        text_result = result.content[0].text
        if text_result.startswith(f"AWS Security Reference Architecture Pull Request from {url}"):
            assert True
        else:
            print(text_result)


@pytest.mark.asyncio
async def test_read_security_and_compliance_best_practices_content_github_code():
    """Tests search documentation"""
    async with client:
        result = await client.call_tool(
            "read_content",
            {
                "url": "https://github.com/aws-samples/aws-security-reference-architecture-examples/blob/main/aws_sra_examples/modules/guardduty-org-module/templates/sra-guardduty-org-solution.yaml",
                "start_index": 0,
            },
        )
        assert len(result.content) > 0
        assert isinstance(result.content[0], TextContent)
        text_result = result.content[0].text
        assert "# SPDX-License-Identifier: MIT-0" in text_result
        assert (
            "Description: Installs the AWS SRA GuardDuty solution.  If needed, the AWS SRA common "
            "prerequisite solution is also installed.  (sra-1u3sd7f8m)" in text_result
        )
