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
"""AWS Security Hub MCP Server implementation."""

import os
import sys
from datetime import datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP

from awslabs.aws_security_hub_mcp_server.consts import (
    DEFAULT_AWS_REGION,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_RESULTS,
    ENV_AWS_PROFILE,
    ENV_AWS_REGION,
    ENV_LOG_LEVEL,
    SEVERITY_WEIGHTS,
)
from awslabs.aws_security_hub_mcp_server.models import (
    ComplianceStatus,
    EnabledStandard,
    FindingStatistics,
    RecordState,
    SecurityControlDefinition,
    SecurityFinding,
    SecurityScore,
    SeverityLabel,
    WorkflowStatus,
)

# Set up logging
logger.remove()
logger.add(sys.stderr, level=os.getenv(ENV_LOG_LEVEL, DEFAULT_LOG_LEVEL))

# Configuration
AWS_PROFILE = os.getenv(ENV_AWS_PROFILE)
AWS_REGION = os.getenv(ENV_AWS_REGION, DEFAULT_AWS_REGION)
MAX_RESULTS = int(os.getenv("SECURITY_HUB_MAX_RESULTS", str(DEFAULT_MAX_RESULTS)))

mcp = FastMCP(
    "aws-security-hub",
    instructions="""
    # AWS Security Hub MCP Server

    This server provides tools to interact with AWS Security Hub for security findings analysis,
    standards management, and security posture monitoring using official AWS APIs.

    ## Best Practices

    - Use specific filters when querying findings to get relevant results
    - For large result sets, pagination is handled automatically
    - All tools use official AWS Security Hub APIs with verified data
    - Monitor security scores to track overall security improvements

    ## Tool Selection Guide

    ### Data Retrieval Tools
    - Use `get_security_findings` when: You need to retrieve and analyze specific security findings
    - Use `get_finding_statistics` when: You want aggregated data about security findings
    - Use `get_security_score` when: You need to track overall security posture
    - Use `get_enabled_standards` when: You want to see which security standards are enabled
    - Use `list_security_control_definitions` when: You need information about available security controls
    - Use `get_finding_history` when: You want to track changes to a specific finding over time
    - Use `describe_standards_controls` when: You need details about controls within a specific standard

    ### Report Generation Tools
    - Use `generate_security_report` when: You need a comprehensive security report with findings analysis, recommendations, and executive summary
    - Use `generate_compliance_report` when: You need a compliance-focused report analyzing standards adherence, control status, and compliance recommendations
    - Use `generate_security_trends_report` when: You need historical trend analysis to identify patterns, improvements, or deteriorations in security posture over time

    ## Report Tools Features

    ### Security Report
    - Executive summary with security score and findings breakdown
    - Detailed findings by severity level
    - Actionable security recommendations prioritized by risk
    - Security standards status and analysis
    - Customizable detail level and finding limits

    ### Compliance Report
    - Compliance percentage and standards analysis
    - Control-level compliance details
    - Compliance findings categorized by type (Configuration, Access Control, Monitoring, etc.)
    - Standards-specific compliance status and recommendations
    - Integration with AWS Config and Security Hub compliance data

    ### Security Trends Report
    - Historical analysis across multiple time periods (7, 14, 30, 90 days by default)
    - Trend analysis for severity levels, compliance status, and resource types
    - Security score progression over time
    - Actionable insights based on trend patterns
    - Statistical analysis and period comparisons
    - Uses only actual Security Hub data to prevent hallucination
    """,
    dependencies=[
        "boto3",
        "pydantic",
        "loguru",
    ],
)


def get_security_hub_client():
    """Get a configured Security Hub client."""
    try:
        session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
        return session.client("securityhub")
    except NoCredentialsError:
        logger.error("AWS credentials not found. Please configure your credentials.")
        raise
    except Exception as e:
        logger.error(f"Error creating Security Hub client: {e}")
        raise


def parse_finding(finding_data: dict[str, Any]) -> SecurityFinding:
    """Parse AWS Security Hub finding data into our model."""
    severity = finding_data.get("Severity", {})
    severity_label = severity.get("Label", "INFORMATIONAL")
    severity_score = severity.get("Normalized")

    workflow = finding_data.get("Workflow", {})
    workflow_status = workflow.get("Status", "NEW")

    compliance = finding_data.get("Compliance", {})
    compliance_status = compliance.get("Status") if compliance else None

    resources = finding_data.get("Resources", [])
    resource_type = resources[0].get("Type") if resources else None
    resource_id = resources[0].get("Id") if resources else None

    remediation = finding_data.get("Remediation", {})
    remediation_url = remediation.get("Recommendation", {}).get("Url") if remediation else None

    # Handle invalid enum values gracefully
    try:
        severity_enum = SeverityLabel(severity_label)
    except ValueError:
        severity_enum = SeverityLabel.INFORMATIONAL

    try:
        workflow_enum = WorkflowStatus(workflow_status)
    except ValueError:
        workflow_enum = WorkflowStatus.NEW

    try:
        record_state_enum = RecordState(finding_data.get("RecordState", "ACTIVE"))
    except ValueError:
        record_state_enum = RecordState.ACTIVE

    compliance_enum = None
    if compliance_status:
        try:
            compliance_enum = ComplianceStatus(compliance_status)
        except ValueError:
            compliance_enum = None

    return SecurityFinding(
        id=finding_data["Id"],
        product_arn=finding_data["ProductArn"],
        generator_id=finding_data["GeneratorId"],
        aws_account_id=finding_data["AwsAccountId"],
        region=finding_data["Region"],
        title=finding_data["Title"],
        description=finding_data["Description"],
        severity_label=severity_enum,
        severity_score=severity_score,
        workflow_status=workflow_enum,
        record_state=record_state_enum,
        compliance_status=compliance_enum,
        created_at=finding_data["CreatedAt"],
        updated_at=finding_data["UpdatedAt"],
        resource_type=resource_type,
        resource_id=resource_id,
        remediation_url=remediation_url,
        source_url=finding_data.get("SourceUrl"),
    )


@mcp.tool(name="get-security-findings")
async def get_security_findings(
    ctx: Context,
    severity_labels: list[SeverityLabel] | None = None,
    workflow_status: list[WorkflowStatus] | None = None,
    compliance_status: list[ComplianceStatus] | None = None,
    record_state: list[RecordState] | None = None,
    product_name: str | None = None,
    resource_type: str | None = None,
    days_back: int | None = 7,
    max_results: int | None = 50,
) -> list[SecurityFinding]:
    """Retrieve security findings from AWS Security Hub with filtering options.

    This tool allows you to query Security Hub findings with various filters to focus on
    specific security issues. You can filter by severity, workflow status, compliance status,
    and other attributes.

    Args:
        ctx: MCP context for logging and error handling
        severity_labels: Filter by severity levels
        workflow_status: Filter by workflow status
        compliance_status: Filter by compliance status
        record_state: Filter by record state
        product_name: Filter by product name
        resource_type: Filter by AWS resource type
        days_back: Number of days back to search
        max_results: Maximum number of findings to return

    Returns:
        List of SecurityFinding objects matching the filters
    """
    try:
        client = get_security_hub_client()

        # Build filters
        filters = {}

        if severity_labels:
            filters["SeverityLabel"] = [{"Value": label.value, "Comparison": "EQUALS"} for label in severity_labels]

        if workflow_status:
            filters["WorkflowStatus"] = [{"Value": status.value, "Comparison": "EQUALS"} for status in workflow_status]

        if compliance_status:
            filters["ComplianceStatus"] = [
                {"Value": status.value, "Comparison": "EQUALS"} for status in compliance_status
            ]

        if record_state:
            filters["RecordState"] = [{"Value": state.value, "Comparison": "EQUALS"} for state in record_state]

        if product_name:
            filters["ProductName"] = [{"Value": product_name, "Comparison": "EQUALS"}]

        if resource_type:
            filters["ResourceType"] = [{"Value": resource_type, "Comparison": "EQUALS"}]

        # Add time filter using DateRange format
        if days_back and days_back <= 365:  # Reasonable limit
            try:
                # Ensure days_back is an integer - MCP might pass it as string
                days_back_int = int(days_back) if isinstance(days_back, str) else days_back
                # Value must be an integer, not string
                filters["UpdatedAt"] = [{"DateRange": {"Value": days_back_int, "Unit": "DAYS"}}]
            except Exception as e:
                logger.warning(f"Could not add time filter: {e}")
                # Continue without time filter

        logger.info(f"Querying Security Hub findings with filters: {filters}")

        # Handle pagination to get all findings up to max_results
        all_findings = []
        next_token = None
        page_count = 0
        max_pages = 50  # Safety limit
        requested_max = max_results or 50

        while page_count < max_pages and len(all_findings) < requested_max:
            page_count += 1

            # Calculate how many results to request for this page
            remaining_needed = requested_max - len(all_findings)
            page_size = min(100, remaining_needed)  # AWS max is 100 per page

            # Prepare request parameters
            request_params = {"Filters": filters, "MaxResults": page_size}

            if next_token:
                request_params["NextToken"] = next_token

            logger.debug(f"Fetching page {page_count} of findings (requesting {page_size} results)...")
            response = client.get_findings(**request_params)

            page_findings = response.get("Findings", [])

            # Parse findings and add to results
            for finding_data in page_findings:
                if len(all_findings) >= requested_max:
                    break
                try:
                    finding = parse_finding(finding_data)
                    all_findings.append(finding)
                except Exception as e:
                    logger.warning(f"Error parsing finding {finding_data.get('Id', 'unknown')}: {e}")
                    continue

            # Check if there are more pages and if we need more results
            next_token = response.get("NextToken")
            if not next_token or len(all_findings) >= requested_max:
                break

            logger.debug(f"Page {page_count}: Got {len(page_findings)} findings, total so far: {len(all_findings)}")

        logger.info(f"Retrieved {len(all_findings)} security findings across {page_count} pages")
        return all_findings

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.error(f"AWS Security Hub error ({error_code}): {error_message}")
        raise Exception(f"Security Hub API error: {error_message}") from e
    except Exception as e:
        logger.error(f"Error retrieving security findings: {e}")
        raise


@mcp.tool(name="get-finding-statistics")
async def get_finding_statistics(
    ctx: Context,
    group_by: str = "SeverityLabel",
    days_back: int | None = None,  # Remove default value to make it truly optional
) -> list[FindingStatistics]:
    """Get aggregated statistics about security findings grouped by specified attribute.

    This tool provides statistical analysis of your security findings, helping you understand
    the distribution and trends in your security posture.

    Args:
        ctx: MCP context for logging and error handling
        group_by: Attribute to group findings by
        days_back: Number of days back to analyze

    Returns:
        List of FindingStatistics objects with aggregated data
    """
    try:
        client = get_security_hub_client()

        # Build filters - simplified to avoid API parameter issues
        filters: dict[str, Any] = {"RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}]}

        # Only add time filter if days_back is reasonable and we can format it correctly
        if days_back and days_back <= 365:  # Reasonable limit
            try:
                # Ensure days_back is an integer - MCP might pass it as string
                days_back_int = int(days_back) if isinstance(days_back, str) else days_back
                # Use DateRange format - Value must be an integer, not string
                filters["UpdatedAt"] = [{"DateRange": {"Value": days_back_int, "Unit": "DAYS"}}]
            except Exception as e:
                logger.warning(f"Could not add time filter: {e}")
                # Continue without time filter

        logger.info(f"Getting finding statistics grouped by {group_by}")

        # Get ALL findings using pagination to ensure accurate statistics
        all_findings = []
        next_token = None
        page_count = 0
        max_pages = 20  # Safety limit to prevent infinite loops

        while page_count < max_pages:
            page_count += 1

            # Prepare request parameters
            request_params = {
                "Filters": filters,
                "MaxResults": 100,  # AWS maximum per page
            }

            if next_token:
                request_params["NextToken"] = next_token

            logger.debug(f"Fetching page {page_count} of findings...")
            response = client.get_findings(**request_params)

            page_findings = response.get("Findings", [])
            all_findings.extend(page_findings)

            # Check if there are more pages
            next_token = response.get("NextToken")
            if not next_token:
                break

            logger.debug(f"Page {page_count}: Got {len(page_findings)} findings, total so far: {len(all_findings)}")

        logger.info(f"Retrieved {len(all_findings)} total findings across {page_count} pages")

        # Group findings by the specified attribute
        groups = {}
        total_count = len(all_findings)

        for finding in all_findings:
            group_key = None

            if group_by == "SeverityLabel":
                group_key = finding.get("Severity", {}).get("Label", "UNKNOWN")
            elif group_by == "WorkflowStatus":
                group_key = finding.get("Workflow", {}).get("Status", "UNKNOWN")
            elif group_by == "ProductName":
                product_fields = finding.get("ProductFields", {})
                group_key = product_fields.get("aws/securityhub/ProductName", "UNKNOWN")
            elif group_by == "ResourceType":
                resources = finding.get("Resources", [])
                group_key = resources[0].get("Type", "UNKNOWN") if resources else "UNKNOWN"
            elif group_by == "ComplianceStatus":
                group_key = finding.get("Compliance", {}).get("Status", "UNKNOWN")
            elif group_by == "RecordState":
                group_key = finding.get("RecordState", "UNKNOWN")
            else:
                group_key = "UNKNOWN"

            groups[group_key] = groups.get(group_key, 0) + 1

        # Convert to statistics objects
        statistics = []
        for group_key, count in groups.items():
            percentage = (count / total_count * 100) if total_count > 0 else 0
            stat = FindingStatistics(group_key=group_key, count=count, percentage=round(percentage, 2))
            statistics.append(stat)

        # Sort by count descending
        statistics.sort(key=lambda x: x.count, reverse=True)

        logger.info(f"Generated statistics for {len(statistics)} groups from {total_count} findings")
        return statistics

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.error(f"AWS Security Hub error ({error_code}): {error_message}")
        raise Exception(f"Security Hub API error: {error_message}") from e
    except Exception as e:
        logger.error(f"Error retrieving finding statistics: {e}")
        raise


@mcp.tool(name="get-security-score")
async def get_security_score(
    ctx: Context,
) -> SecurityScore:
    """Retrieve the overall security score and security posture information.

    This tool provides an overview of your overall security posture based on
    Security Hub's security score calculation.

    Args:
        ctx: MCP context for logging and error handling

    Returns:
        SecurityScore object with current score and metrics
    """
    try:
        client = get_security_hub_client()

        logger.info("Calculating security score from findings data")

        # Get ALL active findings using pagination
        filters = {"RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}]}

        all_findings = []
        next_token = None
        page_count = 0
        max_pages = 20  # Safety limit to prevent infinite loops

        while page_count < max_pages:
            page_count += 1

            # Prepare request parameters
            request_params = {
                "Filters": filters,
                "MaxResults": 100,  # AWS maximum per page
            }

            if next_token:
                request_params["NextToken"] = next_token

            logger.debug(f"Fetching page {page_count} of findings for security score...")
            response = client.get_findings(**request_params)

            page_findings = response.get("Findings", [])
            all_findings.extend(page_findings)

            # Check if there are more pages
            next_token = response.get("NextToken")
            if not next_token:
                break

            logger.debug(f"Page {page_count}: Got {len(page_findings)} findings, total so far: {len(all_findings)}")

        total_findings = len(all_findings)
        logger.info(f"Retrieved {total_findings} total findings for security score calculation")

        # Count findings by severity
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFORMATIONAL": 0}

        control_findings = 0

        for finding in all_findings:
            severity = finding.get("Severity", {}).get("Label", "INFORMATIONAL")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            # Count control findings (findings from security standards)
            generator_id = finding.get("GeneratorId", "")
            if any(
                std in generator_id
                for std in ["aws-foundational-security-standard", "cis-aws-foundations-benchmark", "pci-dss"]
            ):
                control_findings += 1

        # Calculate a simple security score based on severity weights
        # This is a simplified calculation - AWS Security Hub uses a more complex algorithm
        total_weight = sum(severity_counts[sev] * weight for sev, weight in SEVERITY_WEIGHTS.items())
        max_possible_weight = total_findings * SEVERITY_WEIGHTS["CRITICAL"] if total_findings > 0 else 1

        # Invert the score so higher is better (fewer high-severity findings = higher score)
        current_score = max(0, 100 - (total_weight / max_possible_weight * 100)) if total_findings > 0 else 100

        security_score = SecurityScore(
            current_score=round(current_score, 2),
            max_score=100.0,
            score_date=datetime.utcnow().isoformat() + "Z",
            control_findings_count=control_findings,
            security_score_percentage=round(current_score, 2),
        )

        logger.info(f"Calculated security score: {current_score:.2f}/100 based on {total_findings} findings")
        return security_score

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.error(f"AWS Security Hub error ({error_code}): {error_message}")
        raise Exception(f"Security Hub API error: {error_message}") from e
    except Exception as e:
        logger.error(f"Error calculating security score: {e}")
        raise


@mcp.tool(name="get-enabled-standards")
async def get_enabled_standards(
    ctx: Context,
) -> list[EnabledStandard]:
    """Retrieve all enabled security standards in Security Hub.

    This tool provides information about which security standards are currently enabled
    in your Security Hub configuration, using the official GetEnabledStandards API.

    Args:
        ctx: MCP context for logging and error handling

    Returns:
        List of EnabledStandard objects with official standard information
    """
    try:
        client = get_security_hub_client()

        logger.info("Retrieving enabled security standards")

        # Get enabled standards using official API
        all_standards = []
        next_token = None
        page_count = 0
        max_pages = 10  # Safety limit

        while page_count < max_pages:
            page_count += 1

            # Prepare request parameters
            request_params = {"MaxResults": 100}

            if next_token:
                request_params["NextToken"] = next_token

            logger.debug(f"Fetching page {page_count} of enabled standards...")
            standards_response = client.get_enabled_standards(**request_params)

            # Get standard details for names and descriptions
            standards_details_response = client.describe_standards()
            standards_details = {std["StandardsArn"]: std for std in standards_details_response["Standards"]}

            page_standards = standards_response.get("StandardsSubscriptions", [])

            for standard in page_standards:
                standard_detail = standards_details.get(standard["StandardsArn"], {})

                enabled_standard = EnabledStandard(
                    standards_arn=standard["StandardsArn"],
                    standards_subscription_arn=standard["StandardsSubscriptionArn"],
                    standards_status=standard["StandardsStatus"],
                    standards_status_reason=str(standard.get("StandardsStatusReason", "")),
                    name=standard_detail.get("Name", "Unknown Standard"),
                    description=standard_detail.get("Description"),
                )
                all_standards.append(enabled_standard)

            # Check if there are more pages
            next_token = standards_response.get("NextToken")
            if not next_token:
                break

            logger.debug(f"Page {page_count}: Got {len(page_standards)} standards, total so far: {len(all_standards)}")

        logger.info(f"Retrieved {len(all_standards)} enabled standards")
        return all_standards

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.error(f"AWS Security Hub error ({error_code}): {error_message}")
        raise Exception(f"Security Hub API error: {error_message}") from e
    except Exception as e:
        logger.error(f"Error retrieving enabled standards: {e}")
        raise


@mcp.tool(name="list-security-control-definitions")
async def list_security_control_definitions(
    ctx: Context,
    standard_arn: str | None = None,
    max_results: int | None = 100,
) -> list[SecurityControlDefinition]:
    """List security control definitions available in Security Hub.

    This tool provides information about security controls using the official
    ListSecurityControlDefinitions API. Controls define the security checks
    that Security Hub performs.

    Args:
        ctx: MCP context for logging and error handling
        standard_arn: Optional filter for controls from a specific standard
        max_results: Maximum number of control definitions to return

    Returns:
        List of SecurityControlDefinition objects with official control information
    """
    try:
        client = get_security_hub_client()

        logger.info("Retrieving security control definitions")

        # Get control definitions using official API
        all_controls = []
        next_token = None
        page_count = 0
        max_pages = 20  # Safety limit
        requested_max = max_results or 100

        while page_count < max_pages and len(all_controls) < requested_max:
            page_count += 1

            # Calculate how many results to request for this page
            remaining_needed = requested_max - len(all_controls)
            page_size = min(100, remaining_needed)  # AWS max is 100 per page

            # Prepare request parameters
            request_params: dict[str, Any] = {"MaxResults": page_size}

            if next_token:
                request_params["NextToken"] = next_token

            if standard_arn:
                request_params["StandardsArn"] = standard_arn

            logger.debug(f"Fetching page {page_count} of control definitions...")
            response = client.list_security_control_definitions(**request_params)

            page_controls = response.get("SecurityControlDefinitions", [])

            for control in page_controls:
                if len(all_controls) >= requested_max:
                    break

                control_def = SecurityControlDefinition(
                    security_control_id=control["SecurityControlId"],
                    title=control["Title"],
                    description=control["Description"],
                    remediation_url=control.get("RemediationUrl"),
                    severity_rating=SeverityLabel(control["SeverityRating"]),
                    current_region_availability=control["CurrentRegionAvailability"],
                )
                all_controls.append(control_def)

            # Check if there are more pages and if we need more results
            next_token = response.get("NextToken")
            if not next_token or len(all_controls) >= requested_max:
                break

            logger.debug(f"Page {page_count}: Got {len(page_controls)} controls, total so far: {len(all_controls)}")

        logger.info(f"Retrieved {len(all_controls)} security control definitions")
        return all_controls

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.error(f"AWS Security Hub error ({error_code}): {error_message}")
        raise Exception(f"Security Hub API error: {error_message}") from e
    except Exception as e:
        logger.error(f"Error retrieving security control definitions: {e}")
        raise


@mcp.tool(name="get-finding-history")
async def get_finding_history(
    ctx: Context,
    finding_identifier: str,
    start_time: str | None = None,
    end_time: str | None = None,
    max_results: int | None = 100,
) -> list[dict]:
    """Get the history of changes for a specific security finding.

    This tool provides the change history for a finding using the official
    GetFindingHistory API, showing how the finding has evolved over time.

    Args:
        ctx: MCP context for logging and error handling
        finding_identifier: The finding ID to get history for
        start_time: Start time for history (ISO format, e.g., '2024-01-01T00:00:00Z')
        end_time: End time for history (ISO format, e.g., '2024-12-31T23:59:59Z')
        max_results: Maximum number of history records to return

    Returns:
        List of finding history records with timestamps and changes
    """
    try:
        client = get_security_hub_client()

        logger.info(f"Retrieving finding history for {finding_identifier}")

        # Get finding history using official API
        all_history = []
        next_token = None
        page_count = 0
        max_pages = 10  # Safety limit
        requested_max = max_results or 100

        while page_count < max_pages and len(all_history) < requested_max:
            page_count += 1

            # Calculate how many results to request for this page
            remaining_needed = requested_max - len(all_history)
            page_size = min(100, remaining_needed)  # AWS max is 100 per page

            # Prepare request parameters
            request_params = {
                "FindingIdentifier": {
                    "Id": finding_identifier,
                    "ProductArn": f"arn:aws:securityhub:{AWS_REGION}::product/aws/securityhub",
                },
                "MaxResults": page_size,
            }

            if next_token:
                request_params["NextToken"] = next_token

            if start_time:
                request_params["StartTime"] = start_time

            if end_time:
                request_params["EndTime"] = end_time

            logger.debug(f"Fetching page {page_count} of finding history...")
            response = client.get_finding_history(**request_params)

            page_history = response.get("Records", [])

            for record in page_history:
                if len(all_history) >= requested_max:
                    break

                # Convert datetime objects to strings for JSON serialization
                history_record = {
                    "finding_identifier": record.get("FindingIdentifier", {}),
                    "update_time": record.get("UpdateTime").isoformat() if record.get("UpdateTime") else None,
                    "finding_created": record.get("FindingCreated", False),
                    "update_source": record.get("UpdateSource", {}),
                    "updates": record.get("Updates", {}),
                }
                all_history.append(history_record)

            # Check if there are more pages and if we need more results
            next_token = response.get("NextToken")
            if not next_token or len(all_history) >= requested_max:
                break

            logger.debug(
                f"Page {page_count}: Got {len(page_history)} history records, total so far: {len(all_history)}"
            )

        logger.info(f"Retrieved {len(all_history)} finding history records")
        return all_history

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.error(f"AWS Security Hub error ({error_code}): {error_message}")
        raise Exception(f"Security Hub API error: {error_message}") from e
    except Exception as e:
        logger.error(f"Error retrieving finding history: {e}")
        raise


@mcp.tool(name="describe-standards-controls")
async def describe_standards_controls(
    ctx: Context,
    standards_subscription_arn: str,
    max_results: int | None = 100,
) -> list[dict]:
    """Describe the controls for a specific security standard subscription.

    This tool provides detailed information about the controls within a security
    standard using the official DescribeStandardsControls API.

    Args:
        ctx: MCP context for logging and error handling
        standards_subscription_arn: ARN of the standards subscription
        max_results: Maximum number of controls to return

    Returns:
        List of control information with status, severity, and details
    """
    try:
        client = get_security_hub_client()

        logger.info(f"Describing controls for standard: {standards_subscription_arn}")

        # Get controls using official API
        all_controls = []
        next_token = None
        page_count = 0
        max_pages = 10  # Safety limit
        requested_max = max_results or 100

        while page_count < max_pages and len(all_controls) < requested_max:
            page_count += 1

            # Calculate how many results to request for this page
            remaining_needed = requested_max - len(all_controls)
            page_size = min(100, remaining_needed)  # AWS max is 100 per page

            # Prepare request parameters
            request_params = {"StandardsSubscriptionArn": standards_subscription_arn, "MaxResults": page_size}

            if next_token:
                request_params["NextToken"] = next_token

            logger.debug(f"Fetching page {page_count} of controls...")
            response = client.describe_standards_controls(**request_params)

            page_controls = response.get("Controls", [])

            for control in page_controls:
                if len(all_controls) >= requested_max:
                    break

                # Convert datetime objects to strings for JSON serialization
                control_info = {
                    "standards_control_arn": control.get("StandardsControlArn"),
                    "control_id": control.get("ControlId"),
                    "title": control.get("Title"),
                    "description": control.get("Description"),
                    "remediation_url": control.get("RemediationUrl"),
                    "severity_rating": control.get("SeverityRating"),
                    "control_status": control.get("ControlStatus"),
                    "control_status_updated_at": control.get("ControlStatusUpdatedAt").isoformat()
                    if control.get("ControlStatusUpdatedAt")
                    else None,
                    "disabled_reason": control.get("DisabledReason"),
                    "related_requirements": control.get("RelatedRequirements", []),
                }
                all_controls.append(control_info)

            # Check if there are more pages and if we need more results
            next_token = response.get("NextToken")
            if not next_token or len(all_controls) >= requested_max:
                break

            logger.debug(f"Page {page_count}: Got {len(page_controls)} controls, total so far: {len(all_controls)}")

        logger.info(f"Retrieved {len(all_controls)} controls for standard")
        return all_controls

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.error(f"AWS Security Hub error ({error_code}): {error_message}")
        raise Exception(f"Security Hub API error: {error_message}") from e
    except Exception as e:
        logger.error(f"Error describing standards controls: {e}")
        raise


@mcp.tool(name="generate-security-report")
async def generate_security_report(
    ctx: Context,
    include_findings_details: bool = True,
    max_findings_per_severity: int = 10,
    days_back: int | None = None,
) -> dict:
    """Generate a comprehensive security report with findings analysis and recommendations.

    This tool creates a structured security report that includes security score, findings
    breakdown by severity, top vulnerabilities, and actionable recommendations.

    Args:
        ctx: MCP context for logging and error handling
        include_findings_details: Whether to include detailed findings information
        max_findings_per_severity: Maximum number of findings to include per severity level
        days_back: Optional number of days back to analyze (if not provided, analyzes all active findings)

    Returns:
        Dictionary containing comprehensive security report data
    """
    try:
        logger.info("Generating comprehensive security report")

        # Get security score
        security_score = await get_security_score(ctx)

        # Get finding statistics
        finding_stats = await get_finding_statistics(ctx, "SeverityLabel", days_back)

        # Get enabled standards
        enabled_standards = await get_enabled_standards(ctx)

        # Get detailed findings if requested
        findings_by_severity = {}
        if include_findings_details:
            # Get findings for each severity level
            for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                try:
                    findings = await get_security_findings(
                        ctx,
                        severity_labels=[SeverityLabel(severity)],
                        days_back=days_back,
                        max_results=max_findings_per_severity,
                    )
                    findings_by_severity[severity] = [
                        {
                            "id": f.id,
                            "title": f.title,
                            "description": f.description[:200] + "..." if len(f.description) > 200 else f.description,
                            "resource_type": f.resource_type,
                            "resource_id": f.resource_id,
                            "compliance_status": f.compliance_status.value if f.compliance_status else None,
                            "remediation_url": f.remediation_url,
                            "created_at": f.created_at,
                            "updated_at": f.updated_at,
                        }
                        for f in findings
                    ]
                except Exception as e:
                    logger.warning(f"Could not get {severity} findings: {e}")
                    findings_by_severity[severity] = []

        # Calculate total findings
        total_findings = sum(stat.count for stat in finding_stats)

        # Generate recommendations based on findings
        recommendations = []

        # Critical recommendations
        critical_count = next((stat.count for stat in finding_stats if stat.group_key == "CRITICAL"), 0)
        if critical_count > 0:
            recommendations.append(
                {
                    "priority": "CRITICAL",
                    "title": "Address Critical Security Vulnerabilities",
                    "description": f"You have {critical_count} critical security findings that require immediate attention.",
                    "action": "Review and remediate all critical findings within 24 hours",
                    "impact": "High - Critical vulnerabilities pose immediate security risks",
                }
            )

        # High severity recommendations
        high_count = next((stat.count for stat in finding_stats if stat.group_key == "HIGH"), 0)
        if high_count > 0:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "title": "Remediate High Severity Issues",
                    "description": f"You have {high_count} high severity security findings.",
                    "action": "Address high severity findings within 48-72 hours",
                    "impact": "Medium-High - Could lead to security breaches if exploited",
                }
            )

        # Config service recommendation
        config_missing = (
            any(
                "Config" in finding.get("title", "")
                for findings_list in findings_by_severity.values()
                for finding in findings_list
            )
            if include_findings_details
            else False
        )

        if config_missing or any(std.standards_status == "INCOMPLETE" for std in enabled_standards):
            recommendations.append(
                {
                    "priority": "HIGH",
                    "title": "Enable AWS Config Service",
                    "description": "AWS Config is not properly configured, preventing compliance monitoring.",
                    "action": "Enable AWS Config service and configure a configuration recorder",
                    "impact": "High - Required for compliance standards and security monitoring",
                }
            )

        # Generate security report
        report = {
            "report_metadata": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "account_id": "Unknown",  # Will be populated from findings if available
                "region": AWS_REGION,
                "report_type": "Security Report",
                "analysis_period_days": days_back,
            },
            "executive_summary": {
                "security_score": security_score.current_score,
                "security_score_percentage": security_score.security_score_percentage,
                "total_findings": total_findings,
                "findings_by_severity": {stat.group_key: stat.count for stat in finding_stats},
                "enabled_standards_count": len(enabled_standards),
                "incomplete_standards_count": sum(
                    1 for std in enabled_standards if std.standards_status == "INCOMPLETE"
                ),
            },
            "security_score_details": {
                "current_score": security_score.current_score,
                "max_score": security_score.max_score,
                "score_date": security_score.score_date,
                "control_findings_count": security_score.control_findings_count,
            },
            "findings_statistics": [
                {
                    "severity": stat.group_key,
                    "count": stat.count,
                    "percentage": stat.percentage,
                }
                for stat in finding_stats
            ],
            "enabled_standards": [
                {
                    "name": std.name,
                    "status": std.standards_status,
                    "status_reason": std.standards_status_reason,
                    "arn": std.standards_arn,
                }
                for std in enabled_standards
            ],
            "recommendations": recommendations,
        }

        # Add detailed findings if requested
        if include_findings_details:
            report["detailed_findings"] = findings_by_severity

        # Extract account ID from findings if available
        if include_findings_details and findings_by_severity:
            for findings_list in findings_by_severity.values():
                if findings_list:
                    # Extract account ID from the first finding's resource ID or ID
                    finding_id = findings_list[0].get("id", "")
                    if "::" in finding_id:
                        parts = finding_id.split(":")
                        if len(parts) >= 5:
                            report["report_metadata"]["account_id"] = parts[4]
                    break

        logger.info(
            f"Generated security report with {total_findings} findings across {len(finding_stats)} severity levels"
        )
        return report

    except Exception as e:
        logger.error(f"Error generating security report: {e}")
        raise


@mcp.tool(name="generate-compliance-report")
async def generate_compliance_report(
    ctx: Context,
    include_control_details: bool = True,
    days_back: int | None = None,
) -> dict:
    """Generate a compliance report based on Security Hub standards and control findings.

    This tool creates a structured compliance report that analyzes compliance status
    across enabled security standards, control findings, and provides compliance
    recommendations. Based on AWS Security Hub compliance data.

    Args:
        ctx: MCP context for logging and error handling
        include_control_details: Whether to include detailed control information
        days_back: Optional number of days back to analyze compliance findings

    Returns:
        Dictionary containing comprehensive compliance report data
    """
    try:
        logger.info("Generating comprehensive compliance report")

        # Get enabled standards
        enabled_standards = await get_enabled_standards(ctx)

        # Get compliance-related findings
        compliance_findings = await get_security_findings(
            ctx,
            compliance_status=[ComplianceStatus.FAILED],
            days_back=days_back,
            max_results=500,  # Get more findings for compliance analysis
        )

        # Get compliance statistics
        compliance_stats = await get_finding_statistics(ctx, "ComplianceStatus", days_back)

        # Analyze compliance by standard
        standards_compliance = {}
        control_details = {}

        for standard in enabled_standards:
            standard_name = standard.name
            standards_compliance[standard_name] = {
                "status": standard.standards_status,
                "status_reason": standard.standards_status_reason,
                "arn": standard.standards_arn,
                "subscription_arn": standard.standards_subscription_arn,
                "failed_controls": 0,
                "total_controls": 0,
                "compliance_percentage": 0,
            }

            # Get control details if requested
            if include_control_details:
                try:
                    controls = await describe_standards_controls(
                        ctx, standard.standards_subscription_arn, max_results=100
                    )

                    failed_controls = [c for c in controls if c.get("control_status") == "DISABLED"]
                    standards_compliance[standard_name]["failed_controls"] = len(failed_controls)
                    standards_compliance[standard_name]["total_controls"] = len(controls)

                    if len(controls) > 0:
                        compliance_percentage = ((len(controls) - len(failed_controls)) / len(controls)) * 100
                        standards_compliance[standard_name]["compliance_percentage"] = round(compliance_percentage, 2)

                    control_details[standard_name] = controls

                except Exception as e:
                    logger.warning(f"Could not get controls for {standard_name}: {e}")

        # Categorize compliance findings by type
        compliance_categories = {
            "Configuration": [],
            "Access Control": [],
            "Monitoring": [],
            "Encryption": [],
            "Network Security": [],
            "Other": [],
        }

        for finding in compliance_findings:
            title = finding.title.lower()
            if any(keyword in title for keyword in ["config", "configuration", "setting"]):
                compliance_categories["Configuration"].append(finding)
            elif any(keyword in title for keyword in ["iam", "access", "permission", "policy", "role"]):
                compliance_categories["Access Control"].append(finding)
            elif any(keyword in title for keyword in ["log", "monitor", "alarm", "cloudwatch", "cloudtrail"]):
                compliance_categories["Monitoring"].append(finding)
            elif any(keyword in title for keyword in ["encrypt", "kms", "ssl", "tls"]):
                compliance_categories["Encryption"].append(finding)
            elif any(keyword in title for keyword in ["vpc", "security group", "nacl", "network"]):
                compliance_categories["Network Security"].append(finding)
            else:
                compliance_categories["Other"].append(finding)

        # Generate compliance recommendations
        recommendations = []

        # Standards recommendations
        incomplete_standards = [std for std in enabled_standards if std.standards_status == "INCOMPLETE"]
        if incomplete_standards:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "category": "Standards Configuration",
                    "title": "Fix Incomplete Security Standards",
                    "description": f"{len(incomplete_standards)} security standards are incomplete and not providing full compliance monitoring.",
                    "standards_affected": [std.name for std in incomplete_standards],
                    "action": "Enable AWS Config service to allow standards to complete their setup",
                    "impact": "High - Incomplete standards cannot provide accurate compliance assessment",
                }
            )

        # Category-specific recommendations
        for category, findings in compliance_categories.items():
            if findings:
                recommendations.append(
                    {
                        "priority": "MEDIUM" if len(findings) < 10 else "HIGH",
                        "category": category,
                        "title": f"Address {category} Compliance Issues",
                        "description": f"{len(findings)} compliance findings in {category} category require attention.",
                        "action": f"Review and remediate {category.lower()} compliance findings",
                        "impact": f"Medium - {category} issues can affect overall compliance posture",
                    }
                )

        # Calculate overall compliance metrics
        total_compliance_findings = len(compliance_findings)
        total_findings = sum(stat.count for stat in compliance_stats) if compliance_stats else total_compliance_findings

        overall_compliance_percentage = 0
        if total_findings > 0:
            passed_findings = total_findings - total_compliance_findings
            overall_compliance_percentage = (passed_findings / total_findings) * 100

        # Generate compliance report
        report = {
            "report_metadata": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "account_id": "Unknown",
                "region": AWS_REGION,
                "report_type": "Compliance Report",
                "analysis_period_days": days_back,
            },
            "executive_summary": {
                "overall_compliance_percentage": round(overall_compliance_percentage, 2),
                "total_compliance_findings": total_compliance_findings,
                "enabled_standards_count": len(enabled_standards),
                "incomplete_standards_count": len(incomplete_standards),
                "compliance_categories_affected": len(
                    [cat for cat, findings in compliance_categories.items() if findings]
                ),
            },
            "standards_compliance": standards_compliance,
            "compliance_statistics": [
                {
                    "status": stat.group_key,
                    "count": stat.count,
                    "percentage": stat.percentage,
                }
                for stat in compliance_stats
            ]
            if compliance_stats
            else [],
            "compliance_findings_by_category": {
                category: len(findings) for category, findings in compliance_categories.items()
            },
            "recommendations": recommendations,
        }

        # Add detailed control information if requested
        if include_control_details and control_details:
            report["control_details"] = control_details

        # Add detailed findings by category
        if compliance_categories:
            report["detailed_findings_by_category"] = {
                category: [
                    {
                        "id": f.id,
                        "title": f.title,
                        "description": f.description[:200] + "..." if len(f.description) > 200 else f.description,
                        "resource_type": f.resource_type,
                        "resource_id": f.resource_id,
                        "severity": f.severity_label.value,
                        "remediation_url": f.remediation_url,
                        "updated_at": f.updated_at,
                    }
                    for f in findings[:5]  # Limit to top 5 per category
                ]
                for category, findings in compliance_categories.items()
                if findings
            }

        # Extract account ID from findings if available
        if compliance_findings:
            finding_id = compliance_findings[0].id
            if "::" in finding_id:
                parts = finding_id.split(":")
                if len(parts) >= 5:
                    report["report_metadata"]["account_id"] = parts[4]

        logger.info(
            f"Generated compliance report with {total_compliance_findings} compliance findings across {len(enabled_standards)} standards"
        )
        return report

    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        raise


@mcp.tool(name="generate-security-trends-report")
async def generate_security_trends_report(
    ctx: Context,
    analysis_periods: list[int] | None = None,
    trend_categories: list[str] | None = None,
    include_detailed_analysis: bool = True,
) -> dict:
    """Generate a security trends analysis report based on historical Security Hub data.

    This tool analyzes security findings trends over multiple time periods to identify
    patterns, improvements, or deteriorations in security posture. Uses only actual
    Security Hub data to prevent hallucination.

    Args:
        ctx: MCP context for logging and error handling
        analysis_periods: List of days back to analyze (e.g., [7, 14, 30, 90] for weekly, bi-weekly, monthly, quarterly)
        trend_categories: Categories to analyze trends for (severity, compliance, standards, resource_types)
        include_detailed_analysis: Whether to include detailed trend breakdowns and insights

    Returns:
        Dictionary containing comprehensive security trends analysis with historical data points
    """
    try:
        logger.info("Generating security trends analysis report")

        # Default analysis periods: 7, 14, 30, 90 days (weekly, bi-weekly, monthly, quarterly)
        if not analysis_periods:
            analysis_periods = [7, 14, 30, 90]

        # Default trend categories
        if not trend_categories:
            trend_categories = ["severity", "compliance", "standards", "resource_types"]

        # Collect data for each time period
        trend_data = {}
        security_scores = {}

        for period in analysis_periods:
            period_key = f"{period}_days"
            logger.info(f"Collecting data for {period} days back")

            try:
                # Get security score for this period
                # Note: Security score calculation uses all active findings, so we'll collect
                # findings for the specific period to calculate a period-specific score
                period_findings = await get_security_findings(
                    ctx,
                    days_back=period,
                    max_results=1000,  # Get more findings for accurate trend analysis
                )

                # Calculate period-specific metrics
                total_findings = len(period_findings)
                severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFORMATIONAL": 0}
                compliance_counts = {"PASSED": 0, "FAILED": 0, "WARNING": 0, "NOT_AVAILABLE": 0}
                resource_types = {}

                for finding in period_findings:
                    # Count by severity
                    severity = finding.severity_label.value
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1

                    # Count by compliance status
                    if finding.compliance_status:
                        compliance_status = finding.compliance_status.value
                        compliance_counts[compliance_status] = compliance_counts.get(compliance_status, 0) + 1

                    # Count by resource type
                    if finding.resource_type:
                        resource_types[finding.resource_type] = resource_types.get(finding.resource_type, 0) + 1

                # Calculate period security score using the same algorithm as get_security_score
                from awslabs.aws_security_hub_mcp_server.consts import SEVERITY_WEIGHTS

                total_weight = sum(severity_counts[sev] * weight for sev, weight in SEVERITY_WEIGHTS.items())
                max_possible_weight = total_findings * SEVERITY_WEIGHTS["CRITICAL"] if total_findings > 0 else 1
                period_security_score = (
                    max(0, 100 - (total_weight / max_possible_weight * 100)) if total_findings > 0 else 100
                )

                trend_data[period_key] = {
                    "period_days": period,
                    "total_findings": total_findings,
                    "security_score": round(period_security_score, 2),
                    "severity_breakdown": severity_counts,
                    "compliance_breakdown": compliance_counts,
                    "top_resource_types": dict(sorted(resource_types.items(), key=lambda x: x[1], reverse=True)[:10]),
                    "data_collection_timestamp": datetime.utcnow().isoformat() + "Z",
                }

                security_scores[period_key] = period_security_score

            except Exception as e:
                logger.warning(f"Could not collect complete data for {period} days: {e}")
                trend_data[period_key] = {"period_days": period, "error": str(e), "data_available": False}

        # Get current standards status for context
        try:
            enabled_standards = await get_enabled_standards(ctx)
        except Exception as e:
            logger.warning(f"Could not get standards data: {e}")
            enabled_standards = []

        # Analyze trends
        trend_analysis = {}

        if "severity" in trend_categories:
            trend_analysis["severity_trends"] = analyze_severity_trends(trend_data, analysis_periods)

        if "compliance" in trend_categories:
            trend_analysis["compliance_trends"] = analyze_compliance_trends(trend_data, analysis_periods)

        if "standards" in trend_categories:
            trend_analysis["standards_status"] = {
                "enabled_count": len(enabled_standards),
                "incomplete_count": sum(1 for std in enabled_standards if std.standards_status == "INCOMPLETE"),
                "standards_details": [
                    {"name": std.name, "status": std.standards_status, "status_reason": std.standards_status_reason}
                    for std in enabled_standards
                ],
            }

        if "resource_types" in trend_categories:
            trend_analysis["resource_type_trends"] = analyze_resource_type_trends(trend_data, analysis_periods)

        # Generate insights and recommendations
        insights = generate_trend_insights(trend_data, security_scores, analysis_periods)

        # Build the comprehensive report
        report = {
            "report_metadata": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "report_type": "Security Trends Analysis",
                "analysis_periods_days": analysis_periods,
                "trend_categories_analyzed": trend_categories,
                "region": AWS_REGION,
            },
            "executive_summary": {
                "analysis_period_range": f"{min(analysis_periods)} to {max(analysis_periods)} days",
                "data_points_collected": len([p for p in trend_data.values() if p.get("data_available", True)]),
                "current_security_score": security_scores.get(f"{min(analysis_periods)}_days", 0),
                "trend_direction": determine_overall_trend_direction(security_scores, analysis_periods),
                "key_insights_count": len(insights.get("key_insights", [])),
            },
            "historical_data_points": trend_data,
            "trend_analysis": trend_analysis,
            "insights_and_recommendations": insights,
        }

        # Add detailed analysis if requested
        if include_detailed_analysis:
            report["detailed_trend_analysis"] = generate_detailed_trend_analysis(trend_data, analysis_periods)

        logger.info(f"Generated security trends report analyzing {len(analysis_periods)} time periods")
        return report

    except Exception as e:
        logger.error(f"Error generating security trends report: {e}")
        raise


def analyze_severity_trends(trend_data: dict, periods: list[int]) -> dict:
    """Analyze trends in security finding severity over time."""
    severity_trends = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": [], "INFORMATIONAL": []}

    for period in sorted(periods):
        period_key = f"{period}_days"
        if period_key in trend_data and trend_data[period_key].get("data_available", True):
            severity_breakdown = trend_data[period_key].get("severity_breakdown", {})
            for severity in severity_trends.keys():
                severity_trends[severity].append({"period_days": period, "count": severity_breakdown.get(severity, 0)})

    # Calculate trend direction for each severity
    trend_directions = {}
    for severity, data_points in severity_trends.items():
        if len(data_points) >= 2:
            recent_count = data_points[0]["count"]  # Shortest period (most recent)
            older_count = data_points[-1]["count"]  # Longest period

            if recent_count > older_count:
                trend_directions[severity] = "increasing"
            elif recent_count < older_count:
                trend_directions[severity] = "decreasing"
            else:
                trend_directions[severity] = "stable"
        else:
            trend_directions[severity] = "insufficient_data"

    return {"severity_data_points": severity_trends, "trend_directions": trend_directions}


def analyze_compliance_trends(trend_data: dict, periods: list[int]) -> dict:
    """Analyze trends in compliance status over time."""
    compliance_trends = {"PASSED": [], "FAILED": [], "WARNING": [], "NOT_AVAILABLE": []}

    for period in sorted(periods):
        period_key = f"{period}_days"
        if period_key in trend_data and trend_data[period_key].get("data_available", True):
            compliance_breakdown = trend_data[period_key].get("compliance_breakdown", {})
            total_compliance_findings = sum(compliance_breakdown.values())

            for status in compliance_trends.keys():
                count = compliance_breakdown.get(status, 0)
                percentage = (count / total_compliance_findings * 100) if total_compliance_findings > 0 else 0

                compliance_trends[status].append(
                    {"period_days": period, "count": count, "percentage": round(percentage, 2)}
                )

    return {
        "compliance_data_points": compliance_trends,
        "compliance_score_trend": calculate_compliance_score_trend(compliance_trends),
    }


def analyze_resource_type_trends(trend_data: dict, periods: list[int]) -> dict:
    """Analyze trends in resource types with security findings."""
    all_resource_types = set()

    # Collect all resource types across periods
    for period in periods:
        period_key = f"{period}_days"
        if period_key in trend_data and trend_data[period_key].get("data_available", True):
            resource_types = trend_data[period_key].get("top_resource_types", {})
            all_resource_types.update(resource_types.keys())

    # Track trends for top resource types
    resource_trends = {}
    for resource_type in list(all_resource_types)[:10]:  # Top 10 resource types
        resource_trends[resource_type] = []

        for period in sorted(periods):
            period_key = f"{period}_days"
            if period_key in trend_data and trend_data[period_key].get("data_available", True):
                resource_types = trend_data[period_key].get("top_resource_types", {})
                count = resource_types.get(resource_type, 0)

                resource_trends[resource_type].append({"period_days": period, "findings_count": count})

    return {
        "resource_type_data_points": resource_trends,
        "most_affected_resources": identify_most_affected_resources(resource_trends),
    }


def calculate_compliance_score_trend(compliance_trends: dict) -> list:
    """Calculate overall compliance score trend over time."""
    compliance_scores = []

    if "PASSED" in compliance_trends and "FAILED" in compliance_trends:
        for i in range(len(compliance_trends["PASSED"])):
            passed_count = compliance_trends["PASSED"][i]["count"]
            failed_count = compliance_trends["FAILED"][i]["count"]
            total_count = passed_count + failed_count

            if total_count > 0:
                compliance_score = (passed_count / total_count) * 100
                compliance_scores.append(
                    {
                        "period_days": compliance_trends["PASSED"][i]["period_days"],
                        "compliance_score": round(compliance_score, 2),
                    }
                )

    return compliance_scores


def identify_most_affected_resources(resource_trends: dict) -> list:
    """Identify resources with the most security findings."""
    resource_totals = {}

    for resource_type, data_points in resource_trends.items():
        if data_points:
            # Use the most recent data point (shortest period)
            recent_count = data_points[0]["findings_count"]
            resource_totals[resource_type] = recent_count

    # Sort by count and return top 5
    sorted_resources = sorted(resource_totals.items(), key=lambda x: x[1], reverse=True)
    return [{"resource_type": resource, "findings_count": count} for resource, count in sorted_resources[:5]]


def generate_trend_insights(trend_data: dict, security_scores: dict, periods: list[int]) -> dict:
    """Generate actionable insights from trend analysis."""
    insights = {"key_insights": [], "recommendations": [], "trend_summary": {}}

    # Analyze security score trend
    if len(security_scores) >= 2:
        sorted_periods = sorted(periods)
        recent_score = security_scores.get(f"{sorted_periods[0]}_days", 0)
        older_score = security_scores.get(f"{sorted_periods[-1]}_days", 0)

        score_change = recent_score - older_score

        if abs(score_change) > 5:  # Significant change threshold
            if score_change > 0:
                insights["key_insights"].append(
                    {
                        "type": "security_score_improvement",
                        "message": f"Security score improved by {score_change:.1f} points over {sorted_periods[-1]} days",
                        "impact": "positive",
                    }
                )
                insights["recommendations"].append(
                    {
                        "priority": "MEDIUM",
                        "title": "Maintain Security Improvements",
                        "description": "Continue current security practices that led to score improvement",
                        "action": "Document and standardize successful security practices",
                    }
                )
            else:
                insights["key_insights"].append(
                    {
                        "type": "security_score_decline",
                        "message": f"Security score declined by {abs(score_change):.1f} points over {sorted_periods[-1]} days",
                        "impact": "negative",
                    }
                )
                insights["recommendations"].append(
                    {
                        "priority": "HIGH",
                        "title": "Address Security Score Decline",
                        "description": "Investigate and address factors causing security score deterioration",
                        "action": "Review recent changes and implement corrective measures",
                    }
                )

    # Analyze finding volume trends
    recent_period = f"{sorted(periods)[0]}_days"
    older_period = f"{sorted(periods)[-1]}_days"

    if recent_period in trend_data and older_period in trend_data:
        recent_total = trend_data[recent_period].get("total_findings", 0)
        older_total = trend_data[older_period].get("total_findings", 0)

        if recent_total > older_total * 1.2:  # 20% increase threshold
            insights["key_insights"].append(
                {
                    "type": "findings_volume_increase",
                    "message": f"Security findings increased by {((recent_total - older_total) / older_total * 100):.1f}% over time",
                    "impact": "negative",
                }
            )
        elif recent_total < older_total * 0.8:  # 20% decrease threshold
            insights["key_insights"].append(
                {
                    "type": "findings_volume_decrease",
                    "message": f"Security findings decreased by {((older_total - recent_total) / older_total * 100):.1f}% over time",
                    "impact": "positive",
                }
            )

    insights["trend_summary"] = {
        "analysis_periods": periods,
        "data_quality": "high" if all(p.get("data_available", True) for p in trend_data.values()) else "partial",
        "trend_reliability": "high" if len(periods) >= 3 else "medium",
    }

    return insights


def determine_overall_trend_direction(security_scores: dict, periods: list[int]) -> str:
    """Determine the overall trend direction based on security scores."""
    if len(security_scores) < 2:
        return "insufficient_data"

    sorted_periods = sorted(periods)
    recent_score = security_scores.get(f"{sorted_periods[0]}_days", 0)
    older_score = security_scores.get(f"{sorted_periods[-1]}_days", 0)

    score_change = recent_score - older_score

    if score_change > 2:
        return "improving"
    elif score_change < -2:
        return "declining"
    else:
        return "stable"


def generate_detailed_trend_analysis(trend_data: dict, periods: list[int]) -> dict:
    """Generate detailed trend analysis with statistical insights."""
    detailed_analysis = {"statistical_summary": {}, "period_comparisons": [], "data_quality_assessment": {}}

    # Statistical summary
    security_scores = []
    total_findings = []

    for period in sorted(periods):
        period_key = f"{period}_days"
        if period_key in trend_data and trend_data[period_key].get("data_available", True):
            security_scores.append(trend_data[period_key].get("security_score", 0))
            total_findings.append(trend_data[period_key].get("total_findings", 0))

    if security_scores:
        detailed_analysis["statistical_summary"] = {
            "security_score_stats": {
                "min": min(security_scores),
                "max": max(security_scores),
                "average": round(sum(security_scores) / len(security_scores), 2),
                "range": max(security_scores) - min(security_scores),
            },
            "findings_volume_stats": {
                "min": min(total_findings),
                "max": max(total_findings),
                "average": round(sum(total_findings) / len(total_findings), 2),
                "total_range": max(total_findings) - min(total_findings),
            },
        }

    # Period comparisons
    for i, period in enumerate(sorted(periods)[:-1]):
        current_period = f"{period}_days"
        next_period = f"{sorted(periods)[i + 1]}_days"

        if (
            current_period in trend_data
            and next_period in trend_data
            and trend_data[current_period].get("data_available", True)
            and trend_data[next_period].get("data_available", True)
        ):
            current_score = trend_data[current_period].get("security_score", 0)
            next_score = trend_data[next_period].get("security_score", 0)

            detailed_analysis["period_comparisons"].append(
                {
                    "comparison": f"{period} days vs {sorted(periods)[i + 1]} days",
                    "security_score_change": round(current_score - next_score, 2),
                    "findings_change": (
                        trend_data[current_period].get("total_findings", 0)
                        - trend_data[next_period].get("total_findings", 0)
                    ),
                }
            )

    # Data quality assessment
    available_periods = sum(1 for p in trend_data.values() if p.get("data_available", True))
    detailed_analysis["data_quality_assessment"] = {
        "periods_with_data": available_periods,
        "total_periods_requested": len(periods),
        "data_completeness_percentage": round((available_periods / len(periods)) * 100, 2),
        "reliability_score": "high" if available_periods >= len(periods) * 0.8 else "medium",
    }

    return detailed_analysis


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == "__main__":
    main()
