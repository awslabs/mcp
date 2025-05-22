# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use
# this file except in compliance with the License. A copy of the License is
# located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an
# 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing permissions and
# limitations under the License.

"""Response formatting utilities for the AWS Support MCP Server."""

import json
from typing import Any, Dict, List, Optional

from awslabs.aws_support_mcp_server.consts import (
    CASE_SUMMARY_TEMPLATE,
    LANGUAGE_NAMES,
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
        case_id=case_data.get("caseId", ""),
        display_id=case_data.get("displayId"),
        subject=case_data.get("subject", ""),
        status=case_data.get("status", ""),
        service_code=case_data.get("serviceCode", ""),
        category_code=case_data.get("categoryCode", ""),
        severity_code=case_data.get("severityCode", ""),
        submitted_by=case_data.get("submittedBy", ""),
        time_created=case_data.get("timeCreated", ""),
        cc_email_addresses=case_data.get("ccEmailAddresses"),
        language=case_data.get("language"),
    )

    # Format recent communications if present and requested
    if include_communications and "recentCommunications" in case_data:
        recent_comms = case_data["recentCommunications"]
        communications = []

        for comm_data in recent_comms.get("communications", []):
            # Format attachments if present
            attachment_set = None
            if "attachmentSet" in comm_data:
                attachment_set = [
                    AttachmentDetails(
                        attachment_id=att.get("attachmentId", ""),
                        file_name=att.get("fileName", ""),
                    )
                    for att in comm_data["attachmentSet"]
                ]

            # Create a Communication model
            comm = Communication(
                body=comm_data.get("body", ""),
                case_id=comm_data.get("caseId"),
                submitted_by=comm_data.get("submittedBy"),
                time_created=comm_data.get("timeCreated"),
                attachment_set=attachment_set,
            )
            communications.append(comm)

        # Create a RecentCommunications model
        case.recent_communications = RecentCommunications(
            communications=communications,
            next_token=recent_comms.get("nextToken"),
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
    result = {"communications": [], "next_token": communications_data.get("nextToken")}

    for comm_data in communications_data.get("communications", []):
        # Format attachments if present
        attachment_set = None
        if "attachmentSet" in comm_data:
            attachment_set = [
                AttachmentDetails(
                    attachment_id=att.get("attachmentId", ""), file_name=att.get("fileName", "")
                )
                for att in comm_data["attachmentSet"]
            ]

        # Create a Communication model
        comm = Communication(
            body=comm_data.get("body", ""),
            case_id=comm_data.get("caseId"),
            submitted_by=comm_data.get("submittedBy"),
            time_created=comm_data.get("timeCreated"),
            attachment_set=attachment_set,
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


def format_markdown_supported_languages(languages: List[str]) -> str:
    """Format supported languages as Markdown.

    Args:
        languages: List of supported language codes

    Returns:
        Markdown formatted string
    """
    sections = ["# AWS Support Supported Languages\n"]
    sections.append("The following languages are supported for AWS Support cases:\n")
    sections.append("| Code | Language | Native Name |")
    sections.append("|------|----------|-------------|")

    # Sort languages by code
    languages.sort()

    for lang_code in languages:
        # Get language names, default to code if not in mapping
        names = LANGUAGE_NAMES.get(lang_code, (lang_code, lang_code))
        sections.append(f"| {lang_code} | {names[0]} | {names[1]} |")

    sections.extend(
        [
            "\n## Notes\n",
            "1. Language support may vary by:",
            "   - Service code",
            "   - Category code",
            "   - Issue type\n",
            "2. If a language is not supported for a specific combination, the system will:",
            "   - Fall back to the closest supported language, or",
            "   - Use English as the default language",
        ]
    )

    return "\n".join(sections)


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


def format_markdown_supported_languages(languages: List[Dict[str, Any]]) -> str:
    """Format supported languages as a Markdown summary.

    Args:
        languages: The list of supported languages

    Returns:
        A Markdown string
    """
    sections = ["# AWS Support Supported Languages\n"]

    for language in sorted(languages, key=lambda x: x.get("code", "")):
        code = language.get("code", "")
        name = language.get("name", "")
        native_name = language.get("nativeName", "")

        entry = f"- **{name}**"
        if native_name and native_name != name:
            entry += f" ({native_name})"
        entry += f" - `{code}`"
        sections.append(entry)

    return "\n".join(sections)
