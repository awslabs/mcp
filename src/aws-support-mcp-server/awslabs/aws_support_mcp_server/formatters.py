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
"""Response formatting utilities for the AWS Support MCP Server."""

import json
from typing import Any, Dict, List, Optional

from awslabs.aws_support_mcp_server.consts import (
    CASE_SUMMARY_TEMPLATE,
)
from awslabs.aws_support_mcp_server.models import (
    AttachmentDetails,
    Category,
    Communication,
    RecentCommunications,
    Service,
    SeverityLevel,
    SupportCase,
)


def format_case(case_data: Dict[str, Any], include_communications: bool = True) -> Dict[str, Any]:
    """Format a support case for user display.

    Args:
        case_data: The raw case data from the AWS Support API
        include_communications: Whether to include communications in the response

    Returns:
        A formatted support case
    """
    # Create a SupportCase model from the raw data
    case = SupportCase(
        caseId=case_data.get("caseId", ""),
        displayId=case_data.get("displayId", None),
        subject=case_data.get("subject", ""),
        status=case_data.get("status", ""),
        serviceCode=case_data.get("serviceCode", ""),
        categoryCode=case_data.get("categoryCode", ""),
        severityCode=case_data.get("severityCode", ""),
        submittedBy=case_data.get("submittedBy", ""),
        timeCreated=case_data.get("timeCreated", ""),
        ccEmailAddresses=case_data.get("ccEmailAddresses"),
        language=case_data.get("language"),
        recentCommunications=None,  # Initialize as None, will be set later if needed
    )

    # Format recent communications if present and requested
    if include_communications and "recentCommunications" in case_data:
        recent_comms = case_data["recentCommunications"]
        communications = []

        for comm_data in recent_comms.get("communications", []):
            # Format attachments if present
            attachmentSet = None
            if "attachmentSet" in comm_data:
                attachmentSet = [
                    AttachmentDetails(
                        attachmentId=att.get("attachmentId", ""), fileName=att.get("fileName", "")
                    )
                    for att in comm_data.get("attachmentSet", [])
                ]

            # Create a Communication model
            comm = Communication(
                body=comm_data.get("body", ""),
                caseId=comm_data.get("caseId"),
                submittedBy=comm_data.get("submittedBy"),
                timeCreated=comm_data.get("timeCreated"),
                attachmentSet=attachmentSet,
            )
            communications.append(comm)

        # Create a RecentCommunications model
        case.recent_communications = RecentCommunications(
            communications=communications, nextToken=recent_comms.get("nextToken")
        )

    # Convert the model to a dictionary
    return case.model_dump()


def format_cases(
    cases_data: List[Dict[str, Any]], include_communications: bool = True
) -> List[Dict[str, Any]]:
    """Format multiple support cases for user display.

    Args:
        cases_data: The raw cases data from the AWS Support API
        include_communications: Whether to include communications in the response

    Returns:
        A list of formatted support cases
    """
    return [format_case(case, include_communications) for case in cases_data]


def format_communications(communications_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format communications for user display.

    Args:
        communications_data: The raw communications data from the AWS Support API

    Returns:
        A dictionary with formatted communications
    """
    result = {"communications": [], "nextToken": communications_data.get("nextToken")}

    for comm_data in communications_data.get("communications", []):
        # Format attachments if present
        attachmentSet = None
        if "attachmentSet" in comm_data and comm_data["attachmentSet"]:
            attachmentSet = [
                AttachmentDetails(
                    attachmentId=att.get("attachmentId", ""), fileName=att.get("fileName", "")
                )
                for att in comm_data.get("attachmentSet", [])
            ]

        # Create a Communication model
        comm = Communication(
            body=comm_data.get("body", ""),
            caseId=comm_data.get("caseId"),
            submittedBy=comm_data.get("submittedBy"),
            timeCreated=comm_data.get("timeCreated"),
            attachmentSet=attachmentSet,
        )

        # Convert the model to a dictionary
        result["communications"].append(comm.model_dump())

    return result


def format_services(services_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Format services for user display.

    Args:
        services_data: The raw services data from the AWS Support API

    Returns:
        A dictionary of formatted services
    """
    result = {}

    for service_data in services_data:
        # Create a Service model
        service = Service(
            code=service_data.get("code", ""),
            name=service_data.get("name", ""),
            categories=[
                Category(code=cat.get("code", ""), name=cat.get("name", ""))
                for cat in service_data.get("categories", [])
            ],
        )

        # Add the service to the result dictionary
        result[service.code] = service.model_dump()

    return result


def format_severity_levels(severity_levels_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Format severity levels for user display.

    Args:
        severity_levels_data: The raw severity levels data from the AWS Support API

    Returns:
        A dictionary of formatted severity levels
    """
    result = {}

    for severity_data in severity_levels_data:
        # Create a SeverityLevel model
        severity = SeverityLevel(
            code=severity_data.get("code", ""),
            name=severity_data.get("name", ""),
        )

        # Add the severity level to the result dictionary
        result[severity.code] = severity.model_dump()

    return result


def format_json_response(data: Any, indent: Optional[int] = 2) -> str:
    """Format a response as a JSON string.

    Args:
        data: The data to format
        indent: Number of spaces for indentation (default: 2)

    Returns:
        A JSON string
    """
    return json.dumps(data, indent=indent)


def format_markdown_case_summary(case: Dict[str, Any]) -> str:
    """Format a support case as a Markdown summary.

    Args:
        case: The formatted case data

    Returns:
        A Markdown string
    """
    case_details = [
        f"- **Case ID**: {case['caseId']}",
        f"- **Display ID**: {case.get('displayId', 'N/A')}",
        f"- **Subject**: {case['subject']}",
        f"- **Status**: {case['status']}",
        f"- **Service**: {case['serviceCode']}",
        f"- **Category**: {case['categoryCode']}",
        f"- **Severity**: {case['severityCode']}",
        f"- **Created By**: {case['submittedBy']}",
        f"- **Created On**: {case['timeCreated']}",
    ]

    markdown = CASE_SUMMARY_TEMPLATE.format(case_details="\n".join(case_details))

    if case.get("recentCommunications"):
        markdown += "\n## Recent Communications\n\n"
        for comm in case["recentCommunications"].get("communications", []):
            comm_header = f"### {comm['submittedBy']} - {comm['timeCreated']}"
            comm_body = comm["body"]
            markdown += f"{comm_header}\n\n{comm_body}\n\n"

            if comm.get("attachmentSet"):
                markdown += "**Attachments**:\n\n"
                attachments = [
                    f"- {att['fileName']} (ID: {att['attachmentId']})"
                    for att in comm["attachmentSet"]
                ]
                markdown += "\n".join(attachments) + "\n\n"
    return markdown


def format_markdown_services(services: Dict[str, Any]) -> str:
    """Format services as a Markdown summary.

    Args:
        services: The formatted services data

    Returns:
        A Markdown string
    """
    sections = ["# AWS Services\n"]

    for code, service in sorted(services.items()):
        section = [f"## {service['name']} (`{code}`)\n"]

        if service.get("categories"):
            section.append("### Categories\n")
            categories = [
                f"- {category['name']} (`{category['code']}`)"
                for category in sorted(service["categories"], key=lambda x: x["name"])
            ]
            section.extend(categories + [""])

        sections.extend(section)

    return "\n".join(sections)


def format_markdown_severity_levels(severity_levels: Dict[str, Any]) -> str:
    """Format severity levels as a Markdown summary.

    Args:
        severity_levels: The formatted severity levels data

    Returns:
        A Markdown string
    """
    sections = ["# AWS Support Severity Levels\n"]

    for code, severity in sorted(severity_levels.items()):
        sections.append(f"- **{severity['name']}** (`{code}`)")

    return "\n".join(sections)
