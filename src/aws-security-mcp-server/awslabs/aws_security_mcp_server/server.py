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

#!/usr/bin/env python3
"""AWS Security MCP Server.

MCP Server for integrating with AWS Security services including GuardDuty and Security Hub.
"""

import asyncio
import os
from typing import Any

import boto3
from loguru import logger
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

try:
    from .consts import (
        DEFAULT_AWS_PROFILE,
        ERROR_AWS_CONNECTION,
        ERROR_GUARDDUTY_RETRIEVAL,
        ERROR_NO_DETECTORS,
        ERROR_SECURITYHUB_RETRIEVAL,
        LOG_FORMAT,
        SERVER_NAME,
        TOOL_HEALTH_CHECK,
        TOOL_LIST_GUARDDUTY_FINDINGS,
        TOOL_LIST_SECURITYHUB_FINDINGS,
    )
    from .models import (
        FindingsData,
        GuardDutyFinding,
        HealthCheckData,
        McpResponse,
        ResponseStatus,
        SecurityHubFinding,
        ServiceName,
    )
except ImportError:
    # Fallback for direct execution
    from consts import (
        DEFAULT_AWS_PROFILE,
        ERROR_AWS_CONNECTION,
        ERROR_GUARDDUTY_RETRIEVAL,
        ERROR_NO_DETECTORS,
        ERROR_SECURITYHUB_RETRIEVAL,
        LOG_FORMAT,
        SERVER_NAME,
        TOOL_HEALTH_CHECK,
        TOOL_LIST_GUARDDUTY_FINDINGS,
        TOOL_LIST_SECURITYHUB_FINDINGS,
    )
    from models import (
        FindingsData,
        GuardDutyFinding,
        HealthCheckData,
        McpResponse,
        ResponseStatus,
        SecurityHubFinding,
        ServiceName,
    )

# Configure logging to file only (never stdout for MCP)
logger.remove()
logger.add("aws_security_mcp.log", format=LOG_FORMAT, level="INFO")

# Initialize MCP server
app = Server(SERVER_NAME)

# AWS profile support
AWS_PROFILE = os.environ.get("AWS_PROFILE", DEFAULT_AWS_PROFILE)


def get_boto3_session() -> boto3.Session:
    """Get boto3 session with profile support."""
    return boto3.Session(profile_name=AWS_PROFILE)


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name=TOOL_HEALTH_CHECK,
            description="Check server health status and AWS connectivity",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name=TOOL_LIST_GUARDDUTY_FINDINGS,
            description="List GuardDuty findings with IDs, threat types, and severity",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name=TOOL_LIST_SECURITYHUB_FINDINGS,
            description="List Security Hub findings with title, severity, resource and workflow status",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle MCP tool calls."""
    logger.info(f"Tool called: {name}")

    try:
        if name == TOOL_HEALTH_CHECK:
            return await health_check()
        elif name == TOOL_LIST_GUARDDUTY_FINDINGS:
            return await list_guardduty_findings()
        elif name == TOOL_LIST_SECURITYHUB_FINDINGS:
            return await list_securityhub_findings()
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        raise


async def health_check() -> list[TextContent]:
    """Check server health and AWS connectivity."""
    try:
        session = get_boto3_session()
        sts = session.client("sts")
        identity = sts.get_caller_identity()

        data = HealthCheckData(
            aws_account=identity.get("Account", "unknown"),
            aws_user_arn=identity.get("Arn", "unknown"),
            aws_profile=AWS_PROFILE,
        )

        response = McpResponse(
            status=ResponseStatus.SUCCESS,
            service=ServiceName.AWS_STS,
            data=data.model_dump(),
        )

        logger.info(f"Health check successful for account: {data.aws_account}")
        return [TextContent(type="text", text=response.model_dump_json(indent=2))]

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        error_response = McpResponse(
            status=ResponseStatus.ERROR,
            service=ServiceName.AWS_STS,
            data={"message": f"{ERROR_AWS_CONNECTION}: {str(e)}"},
        )
        return [TextContent(type="text", text=error_response.model_dump_json(indent=2))]


async def list_guardduty_findings() -> list[TextContent]:
    """List GuardDuty findings with IDs, threat types, and severity."""
    try:
        session = get_boto3_session()
        guardduty = session.client("guardduty")

        # Get detectors
        detectors_response = guardduty.list_detectors()
        detector_ids = detectors_response.get("DetectorIds", [])

        if not detector_ids:
            data = FindingsData(findings=[], total_count=0, message=ERROR_NO_DETECTORS)
            response = McpResponse(
                status=ResponseStatus.SUCCESS,
                service=ServiceName.GUARDDUTY,
                data=data.model_dump(),
            )
            return [TextContent(type="text", text=response.model_dump_json(indent=2))]

        all_findings = []

        # Get findings for each detector
        for detector_id in detector_ids:
            findings_response = guardduty.list_findings(DetectorId=detector_id)
            finding_ids = findings_response.get("FindingIds", [])

            if finding_ids:
                details_response = guardduty.get_findings(
                    DetectorId=detector_id, FindingIds=finding_ids
                )

                for finding in details_response.get("Findings", []):
                    finding_model = GuardDutyFinding(
                        id=finding.get("Id", ""),
                        type=finding.get("Type", ""),
                        severity=finding.get("Severity", 0.0),
                    )
                    all_findings.append(finding_model.model_dump())

        data = FindingsData(findings=all_findings, total_count=len(all_findings))
        response = McpResponse(
            status=ResponseStatus.SUCCESS,
            service=ServiceName.GUARDDUTY,
            data=data.model_dump(),
        )

        logger.info(f"Retrieved {len(all_findings)} GuardDuty findings")
        return [TextContent(type="text", text=response.model_dump_json(indent=2))]

    except Exception as e:
        logger.error(f"GuardDuty findings retrieval failed: {e}")
        error_response = McpResponse(
            status=ResponseStatus.ERROR,
            service=ServiceName.GUARDDUTY,
            data={"message": f"{ERROR_GUARDDUTY_RETRIEVAL}: {str(e)}"},
        )
        return [TextContent(type="text", text=error_response.model_dump_json(indent=2))]


async def list_securityhub_findings() -> list[TextContent]:
    """List Security Hub findings with title, severity, resource and workflow status."""
    try:
        session = get_boto3_session()
        securityhub = session.client("securityhub")

        response = securityhub.get_findings()
        findings = response.get("Findings", [])

        formatted_findings = []
        for finding in findings:
            resources = finding.get("Resources", [])
            resource_info = resources[0].get("Id", "N/A") if resources else "N/A"

            finding_model = SecurityHubFinding(
                title=finding.get("Title", "N/A"),
                severity=finding.get("Severity", {}).get("Label", "N/A"),
                resource=resource_info,
                workflow_status=finding.get("Workflow", {}).get("Status", "N/A"),
            )
            formatted_findings.append(finding_model.model_dump())

        data = FindingsData(findings=formatted_findings, total_count=len(formatted_findings))
        response = McpResponse(
            status=ResponseStatus.SUCCESS,
            service=ServiceName.SECURITY_HUB,
            data=data.model_dump(),
        )

        logger.info(f"Retrieved {len(formatted_findings)} Security Hub findings")
        return [TextContent(type="text", text=response.model_dump_json(indent=2))]

    except Exception as e:
        logger.error(f"Security Hub findings retrieval failed: {e}")
        error_response = McpResponse(
            status=ResponseStatus.ERROR,
            service=ServiceName.SECURITY_HUB,
            data={"message": f"{ERROR_SECURITYHUB_RETRIEVAL}: {str(e)}"},
        )
        return [TextContent(type="text", text=error_response.model_dump_json(indent=2))]


async def main() -> None:
    """Main entry point for the MCP server."""
    logger.info(f"Starting {SERVER_NAME} with AWS profile: {AWS_PROFILE}")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def cli_main() -> None:
    """CLI entry point wrapper."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
