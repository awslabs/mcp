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

"""AWS Well-Architected Security Assessment Tool MCP Server"""

import argparse
import datetime
import os
import sys
from typing import Dict, List, Optional

import boto3
from botocore.config import Config
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field

from awslabs.well_architected_security_mcp_server import __version__
from awslabs.well_architected_security_mcp_server.consts import INSTRUCTIONS
from awslabs.well_architected_security_mcp_server.util.network_security import (
    check_network_security,
)
from awslabs.well_architected_security_mcp_server.util.resource_utils import (
    list_services_in_region,
)
from awslabs.well_architected_security_mcp_server.util.security_services import (
    check_access_analyzer,
    check_guard_duty,
    check_inspector,
    check_macie,
    check_security_hub,
    check_trusted_advisor,
    get_access_analyzer_findings,
    get_guardduty_findings,
    get_inspector_findings,
    get_macie_findings,
    get_securityhub_findings,
    get_trusted_advisor_findings,
)
from awslabs.well_architected_security_mcp_server.util.storage_security import (
    check_storage_encryption,
)

# User agent configuration for AWS API calls
USER_AGENT_CONFIG = Config(
    user_agent_extra=f"awslabs/mcp/well-architected-security-mcp-server/{__version__}"
)

# Set up AWS region and profile from environment variables
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_PROFILE = os.environ.get("AWS_PROFILE", "default")

# Remove default logger and add custom configuration
logger.remove()
logger.add(sys.stderr, level=os.getenv("FASTMCP_LOG_LEVEL", "DEBUG"))

# Initialize MCP Server
mcp = FastMCP(
    "well-architected-security-mcp-server",
    instructions=INSTRUCTIONS,
    dependencies=[
        "boto3",
        "requests",
        "beautifulsoup4",
        "pydantic",
        "loguru",
    ],
)

# Global shared components
security_pattern_catalog = None
rule_catalog = None

# Define Field singleton variables for parameter defaults
FIELD_AWS_REGION = Field(
    AWS_REGION, description="AWS region to check for security services status"
)
FIELD_AWS_PROFILE = Field(
    AWS_PROFILE,
    description="Optional AWS profile to use (defaults to AWS_PROFILE environment variable or 'default')",
)
FIELD_STORE_IN_CONTEXT_TRUE = Field(
    True, description="Whether to store results in context for access by other tools"
)
FIELD_DEBUG_TRUE = Field(
    True, description="Whether to include detailed debug information in the response"
)
FIELD_SECURITY_SERVICES = Field(
    ["guardduty", "inspector", "accessanalyzer", "securityhub", "trustedadvisor", "macie"],
    description="List of security services to check. Options: guardduty, inspector, accessanalyzer, securityhub, trustedadvisor, macie",
)
FIELD_ACCOUNT_ID = Field(
    None, description="Optional AWS account ID (defaults to caller's account)"
)
FIELD_MAX_FINDINGS = Field(100, description="Maximum number of findings to retrieve")
FIELD_SEVERITY_FILTER = Field(
    None,
    description="Optional severity filter (e.g., 'HIGH', 'CRITICAL', or for Trusted Advisor: 'ERROR', 'WARNING')",
)
FIELD_CHECK_ENABLED = Field(
    True, description="Whether to check if service is enabled before retrieving findings"
)
FIELD_DETAILED_FALSE = Field(
    False, description="Whether to return the full details of the stored security services data"
)
FIELD_STORAGE_SERVICES = Field(
    ["s3", "ebs", "rds", "dynamodb", "efs", "elasticache"],
    description="List of storage services to check. Options: s3, ebs, rds, dynamodb, efs, elasticache",
)
FIELD_INCLUDE_UNENCRYPTED_ONLY = Field(
    False, description="Whether to include only unencrypted resources in the results"
)
FIELD_SERVICE_FILTER = Field(
    None, description="Optional filter to limit results to a specific service (e.g., 's3', 'ec2')"
)
FIELD_NETWORK_SERVICES = Field(
    ["elb", "vpc", "apigateway", "cloudfront"],
    description="List of network services to check. Options: elb, vpc, apigateway, cloudfront",
)
FIELD_INCLUDE_NON_COMPLIANT_ONLY = Field(
    False, description="Whether to include only non-compliant resources in the results"
)

# Global context storage for sharing data between tool calls
context_storage = {}


@mcp.tool(name="CheckSecurityServices")
async def check_security_services(
    ctx: Context,
    region: str = FIELD_AWS_REGION,
    services: List[str] = FIELD_SECURITY_SERVICES,
    account_id: Optional[str] = FIELD_ACCOUNT_ID,
    aws_profile: Optional[str] = FIELD_AWS_PROFILE,
    store_in_context: bool = FIELD_STORE_IN_CONTEXT_TRUE,
    debug: bool = FIELD_DEBUG_TRUE,
) -> Dict:
    """Verify if selected AWS security services are enabled in the specified region and account.

    This consolidated tool checks the status of multiple AWS security services in a single call,
    providing a comprehensive overview of your security posture.

    ## Response format
    Returns a dictionary with:
    - region: The region that was checked
    - services_checked: List of services that were checked
    - all_enabled: Boolean indicating if all specified services are enabled
    - service_statuses: Dictionary with detailed status for each service
    - summary: Summary of security recommendations

    ## AWS permissions required
    - guardduty:ListDetectors, guardduty:GetDetector (if checking GuardDuty)
    - inspector2:GetStatus (if checking Inspector)
    - accessanalyzer:ListAnalyzers (if checking Access Analyzer)
    - securityhub:DescribeHub (if checking Security Hub)
    - support:DescribeTrustedAdvisorChecks (if checking Trusted Advisor)
    """
    try:
        # Start timestamp for measuring execution time
        start_time = datetime.datetime.now()

        if debug:
            print(
                f"[DEBUG:CheckSecurityServices] Starting security services check for region: {region}"
            )
            print(f"[DEBUG:CheckSecurityServices] Services to check: {', '.join(services)}")
            print(f"[DEBUG:CheckSecurityServices] Using AWS profile: {aws_profile or 'default'}")

        # Use the provided AWS profile or default to 'default'
        profile_name = aws_profile or "default"

        # Create a session using the specified profile
        session = boto3.Session(profile_name=profile_name)

        # Initialize results
        results = {
            "region": region,
            "services_checked": services,
            "all_enabled": True,
            "service_statuses": {},
        }

        if debug:
            # Add debug info to the results
            results["debug_info"] = {
                "start_time": start_time.isoformat(),
                "aws_profile": profile_name,
                "service_details": {},
            }

        # Check each requested service
        for service_name in services:
            # Process status update
            service_start_time = datetime.datetime.now()
            print(f"Checking {service_name} status in {region}...")
            if debug:
                print(f"[DEBUG:CheckSecurityServices] Starting check for {service_name}")

            service_result = None

            # Call the appropriate check function based on service name
            if service_name.lower() == "guardduty":
                service_result = await check_guard_duty(region, session, ctx)
            elif service_name.lower() == "inspector":
                service_result = await check_inspector(region, session, ctx)
            elif service_name.lower() == "accessanalyzer":
                # Call the access analyzer check with additional debugging
                print(
                    f"[DEBUG:CheckSecurityServices] Calling check_access_analyzer for region {region}"
                )
                service_result = await check_access_analyzer(region, session, ctx)
                print(
                    f"[DEBUG:CheckSecurityServices] check_access_analyzer returned: enabled={service_result.get('enabled', False)}"
                )

                # If service_result says not enabled but analyzers are present, override the enabled flag
                analyzers = service_result.get("analyzers", [])
                if not service_result.get("enabled", False) and analyzers and len(analyzers) > 0:
                    print(
                        "[DEBUG:CheckSecurityServices] OVERRIDING: Access Analyzer has analyzers but reported as disabled. Setting enabled=True"
                    )
                    service_result["enabled"] = True
                    service_result["message"] = (
                        f"IAM Access Analyzer is enabled with {len(analyzers)} analyzer(s)."
                    )

                # Always log the analyzers we found
                analyzers = service_result.get("analyzers", [])
                if analyzers:
                    print(
                        f"[DEBUG:CheckSecurityServices] Access Analyzer check found {len(analyzers)} analyzers:"
                    )
                    for idx, analyzer in enumerate(analyzers):
                        print(
                            f"[DEBUG:CheckSecurityServices]   Analyzer {idx + 1}: name={analyzer.get('name')}, status={analyzer.get('status')}"
                        )
                else:
                    print("[DEBUG:CheckSecurityServices] Access Analyzer check found no analyzers")

            elif service_name.lower() == "securityhub":
                service_result = await check_security_hub(region, session, ctx)
            elif service_name.lower() == "trustedadvisor":
                service_result = await check_trusted_advisor(region, session, ctx)
            elif service_name.lower() == "macie":
                service_result = await check_macie(region, session, ctx)
            else:
                # Log warning
                print(f"WARNING: Unknown service: {service_name}. Skipping.")
                continue

            # Add service result to the output
            results["service_statuses"][service_name] = service_result

            # Update all_enabled flag
            if service_result and not service_result.get("enabled", False):
                results["all_enabled"] = False

            # Add debug info for this service if debug is enabled
            if debug:
                service_end_time = datetime.datetime.now()
                service_duration = (service_end_time - service_start_time).total_seconds()

                if "debug_info" in results and "service_details" in results["debug_info"]:
                    results["debug_info"]["service_details"][service_name] = {
                        "duration_seconds": service_duration,
                        "enabled": service_result.get("enabled", False)
                        if service_result
                        else False,
                        "timestamp": service_end_time.isoformat(),
                        "status": "success" if service_result else "error",
                    }

                print(
                    f"[DEBUG:CheckSecurityServices] {service_name} check completed in {service_duration:.2f} seconds"
                )

        # Generate summary based on results
        enabled_services = [
            name
            for name, status in results["service_statuses"].items()
            if status.get("enabled", False)
        ]
        disabled_services = [
            name
            for name, status in results["service_statuses"].items()
            if not status.get("enabled", False)
        ]

        summary = []
        if enabled_services:
            summary.append(f"Enabled services: {', '.join(enabled_services)}")

        if disabled_services:
            summary.append(f"Disabled services: {', '.join(disabled_services)}")
            summary.append("Consider enabling these services to improve your security posture.")

        results["summary"] = " ".join(summary)

        # Store results in context if requested
        if store_in_context:
            context_key = f"security_services_{region}"
            context_storage[context_key] = results
            print(f"Stored security services results in context with key: {context_key}")

        return results

    except Exception as e:
        # Log error
        print(f"ERROR: Error checking security services: {e}")
        return {
            "region": region,
            "services_checked": services,
            "all_enabled": False,
            "error": str(e),
            "message": "Error checking security services status.",
        }


@mcp.tool(name="GetSecurityFindings")
async def get_security_findings(
    ctx: Context,
    region: str = FIELD_AWS_REGION,
    service: str = Field(
        ...,
        description="Security service to retrieve findings from ('guardduty', 'securityhub', 'inspector', 'accessanalyzer', 'trustedadvisor', 'macie')",
    ),
    max_findings: int = FIELD_MAX_FINDINGS,
    severity_filter: Optional[str] = FIELD_SEVERITY_FILTER,
    aws_profile: Optional[str] = FIELD_AWS_PROFILE,
    check_enabled: bool = FIELD_CHECK_ENABLED,
) -> Dict:
    """Retrieve security findings from AWS security services.

    This tool provides a consolidated interface to retrieve findings from various AWS security
    services, including GuardDuty, Security Hub, Inspector, IAM Access Analyzer, and Trusted Advisor.

    It first checks if the specified security service is enabled in the region (using data from
    a previous CheckSecurityServices call) and only retrieves findings if the service is enabled.

    ## Response format
    Returns a dictionary with:
    - service: The security service findings were retrieved from
    - enabled: Whether the service is enabled in the specified region
    - findings: List of findings from the service (if service is enabled)
    - summary: Summary statistics about the findings (if service is enabled)
    - message: Status message or error information

    ## AWS permissions required
    - Read permissions for the specified security service

    ## Note
    For optimal performance, run CheckSecurityServices with store_in_context=True
    before using this tool. Otherwise, it will need to check if the service is enabled first.
    """
    try:
        # Normalize service name
        service_name = service.lower()

        # Check if service is supported
        if service_name not in [
            "guardduty",
            "securityhub",
            "inspector",
            "accessanalyzer",
            "trustedadvisor",
            "macie",
        ]:
            raise ValueError(
                f"Unsupported security service: {service}. "
                + "Supported services are: guardduty, securityhub, inspector, accessanalyzer, trustedadvisor, macie"
            )

        # Get context key for security services data
        context_key = f"security_services_{region}"
        service_status = None

        # First check if we need to verify service is enabled
        if check_enabled:
            # Check if security services data is available in context
            if context_key in context_storage:
                print(f"Using stored security services data for region: {region}")
                security_data = context_storage[context_key]

                # Check if the requested service is in the stored data
                service_statuses = security_data.get("service_statuses", {})
                if service_name in service_statuses:
                    service_status = service_statuses[service_name]

                    # Check if service is enabled
                    if not service_status.get("enabled", False):
                        return {
                            "service": service_name,
                            "enabled": False,
                            "message": f"{service_name} is not enabled in region {region}. Please enable it before retrieving findings.",
                            "setup_instructions": service_status.get(
                                "setup_instructions", "No setup instructions available."
                            ),
                        }
                else:
                    print(
                        f"Service {service_name} not found in stored security services data. Will check directly."
                    )
            else:
                print(
                    f"No stored security services data found for region: {region}. Will check service status directly."
                )

        # Use the provided AWS profile or default to 'default'
        profile_name = aws_profile or "default"

        # Create a session using the specified profile
        session = boto3.Session(profile_name=profile_name)

        # Prepare filter criteria based on severity
        filter_criteria = None
        if severity_filter:
            if service_name == "guardduty":
                # GuardDuty uses numeric severity levels
                severity_mapping = {
                    "LOW": ["1", "2", "3"],
                    "MEDIUM": ["4", "5", "6"],
                    "HIGH": ["7", "8"],
                    "CRITICAL": ["8"],
                }
                if severity_filter.upper() in severity_mapping:
                    filter_criteria = {
                        "Criterion": {
                            "severity": {"Eq": severity_mapping[severity_filter.upper()]}
                        }
                    }
            elif service_name == "securityhub":
                filter_criteria = {
                    "SeverityLabel": [{"Comparison": "EQUALS", "Value": severity_filter.upper()}]
                }
            elif service_name == "inspector":
                filter_criteria = {
                    "severities": [{"comparison": "EQUALS", "value": severity_filter.upper()}]
                }
            elif service_name == "trustedadvisor":
                # For Trusted Advisor, severity maps to status (error, warning, ok)
                status_filter = [severity_filter.lower()]

        # Initialize result with default values
        result = {
            "service": service_name,
            "enabled": False,
            "message": f"Error retrieving {service_name} findings",
            "findings": [],
        }

        # Call appropriate service function based on service parameter
        if service_name == "guardduty":
            print(f"Retrieving GuardDuty findings from {region}...")
            result = await get_guardduty_findings(
                region, session, ctx, max_findings, filter_criteria
            )
        elif service_name == "securityhub":
            print(f"Retrieving Security Hub findings from {region}...")
            result = await get_securityhub_findings(
                region, session, ctx, max_findings, filter_criteria
            )
        elif service_name == "inspector":
            print(f"Retrieving Inspector findings from {region}...")
            result = await get_inspector_findings(
                region, session, ctx, max_findings, filter_criteria
            )
        elif service_name == "accessanalyzer":
            print(f"Retrieving IAM Access Analyzer findings from {region}...")
            result = await get_access_analyzer_findings(region, session, ctx)
        elif service_name == "trustedadvisor":
            print("Retrieving Trusted Advisor security checks with Error/Warning status...")
            # For Trusted Advisor, we'll focus on security category checks
            # Use the severity filter if provided, otherwise default to error and warning
            if severity_filter:
                status_filter = [severity_filter.lower()]
                print(f"Filtering Trusted Advisor checks by status: {status_filter}")
            else:
                status_filter = ["error", "warning"]
                print(f"Using default status filter for Trusted Advisor: {status_filter}")
            result = await get_trusted_advisor_findings(
                region,
                session,
                ctx,
                max_findings=max_findings,
                status_filter=status_filter,
                category_filter="security",
            )
        elif service_name == "macie":
            print(f"Retrieving Macie findings from {region}...")
            result = await get_macie_findings(region, session, ctx, max_findings, filter_criteria)

        # Add service info to result
        result["service"] = service_name

        # If the result indicates the service isn't enabled, store this information
        if not result.get("enabled", True) and context_key in context_storage:
            security_data = context_storage[context_key]
            service_statuses = security_data.get("service_statuses", {})
            if service_name not in service_statuses:
                service_statuses[service_name] = {"enabled": False}
                print(f"Updated context with status for {service_name}: not enabled")

        return result

    except Exception as e:
        # Log error
        print(f"ERROR: Error retrieving {service} findings: {e}")
        raise e


@mcp.tool(name="GetStoredSecurityContext")
async def get_stored_security_context(
    ctx: Context,
    region: str = FIELD_AWS_REGION,
    detailed: bool = FIELD_DETAILED_FALSE,
) -> Dict:
    """Retrieve security services data that was stored in context from a previous CheckSecurityServices call.

    This tool allows you to access security service status data stored by the CheckSecurityServices tool
    without making additional AWS API calls. This is useful for workflows where you need to reference
    the security services status in subsequent steps.

    ## Response format
    Returns a dictionary with:
    - region: The region the data was stored for
    - available: Boolean indicating if data is available for the requested region
    - data: The stored security services data (if available and detailed=True)
    - summary: A summary of the stored data (if available)
    - timestamp: When the data was stored (if available)

    ## Note
    This tool requires that CheckSecurityServices was previously called with store_in_context=True
    for the requested region.
    """
    context_key = f"security_services_{region}"

    if context_key not in context_storage:
        print(f"No stored security services data found for region: {region}")
        return {
            "region": region,
            "available": False,
            "message": f"No security services data has been stored for region {region}. Call CheckSecurityServices with store_in_context=True first.",
        }

    stored_data = context_storage[context_key]

    # Prepare response
    response = {
        "region": region,
        "available": True,
        "summary": stored_data.get("summary", "No summary available"),
        "all_enabled": stored_data.get("all_enabled", False),
        "services_checked": stored_data.get("services_checked", []),
    }

    # Include full data if requested
    if detailed:
        response["data"] = stored_data

    print(f"Retrieved stored security services data for region: {region}")
    return response


@mcp.tool(name="CheckStorageEncryption")
async def check_storage_encryption_tool(
    ctx: Context,
    region: str = FIELD_AWS_REGION,
    services: List[str] = FIELD_STORAGE_SERVICES,
    include_unencrypted_only: bool = FIELD_INCLUDE_UNENCRYPTED_ONLY,
    aws_profile: Optional[str] = FIELD_AWS_PROFILE,
    store_in_context: bool = FIELD_STORE_IN_CONTEXT_TRUE,
) -> Dict:
    """Check if AWS storage resources have encryption enabled.

    This tool identifies storage resources using Resource Explorer and checks if they
    are properly configured for data protection at rest according to AWS Well-Architected
    Framework Security Pillar best practices.

    ## Response format
    Returns a dictionary with:
    - region: The region that was checked
    - resources_checked: Total number of storage resources checked
    - compliant_resources: Number of resources with proper encryption
    - non_compliant_resources: Number of resources without proper encryption
    - compliance_by_service: Breakdown of compliance by service type
    - resource_details: Details about each resource checked
    - recommendations: Recommendations for improving data protection at rest

    ## AWS permissions required
    - resource-explorer-2:ListResources
    - Read permissions for each storage service being analyzed (s3:GetEncryptionConfiguration, etc.)
    """
    try:
        print(f"Starting storage encryption check for region: {region}")
        print(f"Services to check: {', '.join(services)}")
        print(f"Using AWS profile: {aws_profile or 'default'}")

        # Use the provided AWS profile or default to 'default'
        profile_name = aws_profile or "default"

        # Create a session using the specified profile
        session = boto3.Session(profile_name=profile_name)

        # Call the storage security utility function
        results = await check_storage_encryption(
            region, services, session, ctx, include_unencrypted_only
        )

        # Store results in context if requested
        if store_in_context:
            context_key = f"storage_encryption_{region}"
            context_storage[context_key] = results
        return results

    except Exception as e:
        # Log error
        print(f"ERROR: Error checking storage encryption: {e}")
        return {
            "region": region,
            "services_checked": services,
            "error": str(e),
            "message": "Error checking storage encryption status.",
        }


@mcp.tool(name="ListServicesInRegion")
async def list_services_in_region_tool(
    ctx: Context,
    region: str = FIELD_AWS_REGION,
    aws_profile: Optional[str] = FIELD_AWS_PROFILE,
    store_in_context: bool = FIELD_STORE_IN_CONTEXT_TRUE,
) -> Dict:
    """List all AWS services being used in a specific region.

    This tool identifies which AWS services are actively being used in the specified region
    by discovering resources through AWS Resource Explorer or direct API calls.

    ## Response format
    Returns a dictionary with:
    - region: The region that was checked
    - services: List of AWS services being used in the region
    - service_counts: Dictionary mapping service names to resource counts
    - total_resources: Total number of resources found across all services

    ## AWS permissions required
    - resource-explorer-2:Search (if Resource Explorer is set up)
    - Read permissions for various AWS services
    """
    print(f"Starting service discovery for region: {region}")
    print(f"Using AWS profile: {aws_profile or 'default'}")

    # Use the provided AWS profile or default to 'default'
    profile_name = aws_profile or "default"

    # Create a session using the specified profile
    session = boto3.Session(profile_name=profile_name)

    # Initialize results with default values
    results = {"region": region, "services": [], "service_counts": {}, "total_resources": 0}

    try:
        # First try using Resource Explorer method
        print(f"Attempting to discover services using Resource Explorer in {region}...")
        results = await list_services_in_region(region, session, ctx)

    except Exception as e:
        # If Resource Explorer method fails, log the error and try alternative method
        print(f"Resource Explorer method failed: {e}")
        print("Falling back to alternative service discovery method...")

        return {
            "region": region,
            "error": f"Discovery methods failed. Primary error: {str(e)}.",
            "message": f"Error listing services in region {region}.",
            "services": [],
            "service_counts": {},
            "total_resources": 0,
        }

    # Store results in context if requested
    if store_in_context:
        context_key = f"services_in_region_{region}"
        context_storage[context_key] = results
    return results


@mcp.tool(name="CheckNetworkSecurity")
async def check_network_security_tool(
    ctx: Context,
    region: str = FIELD_AWS_REGION,
    services: List[str] = FIELD_NETWORK_SERVICES,
    include_non_compliant_only: bool = FIELD_INCLUDE_NON_COMPLIANT_ONLY,
    aws_profile: Optional[str] = FIELD_AWS_PROFILE,
    store_in_context: bool = FIELD_STORE_IN_CONTEXT_TRUE,
) -> Dict:
    """Check if AWS network resources are configured for secure data-in-transit.

    This tool identifies network resources using Resource Explorer and checks if they
    are properly configured for data protection in transit according to AWS Well-Architected
    Framework Security Pillar best practices.

    ## Response format
    Returns a dictionary with:
    - region: The region that was checked
    - resources_checked: Total number of network resources checked
    - compliant_resources: Number of resources with proper in-transit protection
    - non_compliant_resources: Number of resources without proper in-transit protection
    - compliance_by_service: Breakdown of compliance by service type
    - resource_details: Details about each resource checked
    - recommendations: Recommendations for improving data protection in transit

    ## AWS permissions required
    - resource-explorer-2:ListResources
    - Read permissions for each network service being analyzed (elb:DescribeLoadBalancers, etc.)
    """
    try:
        print(f"Starting network security check for region: {region}")
        print(f"Services to check: {', '.join(services)}")
        print(f"Using AWS profile: {aws_profile or 'default'}")

        # Use the provided AWS profile or default to 'default'
        profile_name = aws_profile or "default"

        # Create a session using the specified profile
        session = boto3.Session(profile_name=profile_name)

        # Call the network security utility function
        results = await check_network_security(
            region, services, session, ctx, include_non_compliant_only
        )

        # Store results in context if requested
        if store_in_context:
            context_key = f"network_security_{region}"
            context_storage[context_key] = results
        return results

    except Exception as e:
        # Log error
        print(f"ERROR: Error checking network security: {e}")
        return {
            "region": region,
            "services_checked": services,
            "error": str(e),
            "message": "Error checking network security status.",
        }


@mcp.prompt(name="wa-sec-check-findings")
async def security_assessment_precheck(ctx: Context) -> str:
    """Provides guidance on using CheckSecurityServices and GetSecurityFindings tools in sequence
    for a comprehensive AWS security assessment.

    This prompt explains the recommended workflow for assessing AWS security services and findings:
    1. First, check which security services are enabled using CheckSecurityServices
    2. Then, retrieve findings from the enabled services using GetSecurityFindings

    Following this sequence ensures efficient API usage and provides a structured approach to security assessment.
    """
    return """
# AWS Security Assessment Workflow Guide

This guide will help you assess your AWS security posture by checking which security services are enabled and retrieving findings from those services.

## Step 1: Check Security Services Status

First, use the `CheckSecurityServices` tool to determine which AWS security services are enabled in your account:

```python
result = await use_mcp_tool(
    server_name="well-architected-security-mcp-server",
    tool_name="CheckSecurityServices",
    arguments={
        "region": "us-east-1",  # Specify your AWS region
        "services": ["guardduty", "inspector", "accessanalyzer", "securityhub", "trustedadvisor"],
        "aws_profile": "default",  # Optional: specify your AWS profile
        "store_in_context": True  # Important: store results for later use
    }
)
```

This will check the status of each security service and store the results in context for later use.

## Step 2: Analyze the Results

Review the results to see which services are enabled:

```python
enabled_services = []
for service, status in result['service_statuses'].items():
    if status.get('enabled', False):
        enabled_services.append(service)
        print(f"✅ {service} is enabled")
    else:
        print(f"❌ {service} is not enabled")
```

## Step 3: Retrieve Findings from Enabled Services

For each enabled service, use the `GetSecurityFindings` tool to retrieve findings:

```python
for service in enabled_services:
    findings = await use_mcp_tool(
        server_name="well-architected-security-mcp-server",
        tool_name="GetSecurityFindings",
        arguments={
            "region": "us-east-1",  # Use the same region as in Step 1
            "service": service,
            "max_findings": 100,  # Adjust as needed
            "severity_filter": "HIGH",  # Optional: filter by severity
            "check_enabled": True  # Verify service is enabled before retrieving findings
        }
    )

    # Process the findings
    if findings.get('findings'):
        print(f"Found {len(findings['findings'])} {service} findings")
        # Analyze findings here
```

## Step 4: Summarize Security Posture

After retrieving findings from all enabled services, summarize the security posture:

```python
total_findings = 0
findings_by_service = {}

for service in enabled_services:
    # Get findings count for each service
    # Implement your summary logic here
```

## Best Practices

1. Always run `CheckSecurityServices` first with `store_in_context=True`
2. Use `GetSecurityFindings` only for services that are enabled
3. Consider filtering findings by severity to focus on high-risk issues first
4. For large environments, process findings in batches

By following this workflow, you'll efficiently assess your AWS security posture and identify potential security issues.
"""


@mcp.prompt(name="wa-sec-check-storage")
async def check_storage_security_prompt(ctx: Context) -> str:
    """Provides guidance on checking AWS storage resources for proper encryption and security configuration.

    This prompt explains the recommended workflow for assessing storage security:
    1. First, identify available storage services in the target region
    2. Then, check if these storage resources have encryption enabled
    3. Finally, analyze the results and implement recommended remediation steps

    This approach helps ensure data protection at rest according to AWS Well-Architected Framework
    Security Pillar best practices.
    """
    return """
# AWS Storage Security Assessment Guide

This guide will help you assess the security of your AWS storage resources by checking for proper encryption and security configurations.

## Step 1: Identify Available Storage Services

First, determine which storage services are available in your target region:

```python
# Option 1: List all services in the region
services_result = await use_mcp_tool(
    server_name="well-architected-security-mcp-server",
    tool_name="ListServicesInRegion",
    arguments={
        "region": "us-east-1",  # Specify your AWS region
        "aws_profile": "default",  # Optional: specify your AWS profile
        "store_in_context": True  # Store results for later use
    }
)

# Option 2: List resource types (alternative approach)
resource_types = await use_mcp_tool(
    server_name="well-architected-security-mcp-server",
    tool_name="ListResourceTypes",
    arguments={
        "region": "us-east-1",  # Specify your AWS region
        "aws_profile": "default",  # Optional: specify your AWS profile
        "store_in_context": True  # Store results for later use
    }
)
```

## Step 2: Filter for Storage Services

Next, filter the results to focus on storage services:

```python
# Define storage services to check
storage_services = ['s3', 'ebs', 'rds', 'dynamodb', 'efs', 'elasticache']

# Filter available services to include only storage services
available_storage_services = []

# If using ListServicesInRegion result
if 'services' in services_result:
    available_storage_services = [s for s in services_result['services'] if s in storage_services]

# If using ListResourceTypes result
if 'storage_services' in resource_types:
    available_storage_services = resource_types['storage_services']

print(f"Available storage services: {', '.join(available_storage_services)}")
```

## Step 3: Check Storage Encryption

Now, check if your storage resources have encryption enabled:

```python
encryption_result = await use_mcp_tool(
    server_name="well-architected-security-mcp-server",
    tool_name="CheckStorageEncryption",
    arguments={
        "region": "us-east-1",  # Specify your AWS region
        "services": available_storage_services,  # Use the filtered list from Step 2
        "include_unencrypted_only": False,  # Set to True to focus only on unencrypted resources
        "aws_profile": "default",  # Optional: specify your AWS profile
        "store_in_context": True  # Store results for later use
    }
)
```

## Step 4: Analyze the Results

Review the encryption check results:

```python
# Get overall compliance statistics
total_resources = encryption_result['resources_checked']
compliant_resources = encryption_result['compliant_resources']
non_compliant_resources = encryption_result['non_compliant_resources']

print(f"Total resources checked: {total_resources}")
print(f"Compliant resources: {compliant_resources} ({(compliant_resources/total_resources)*100:.1f}% if total_resources > 0 else 0}%)")
print(f"Non-compliant resources: {non_compliant_resources} ({(non_compliant_resources/total_resources)*100:.1f}% if total_resources > 0 else 0}%)")

# Review compliance by service
for service, stats in encryption_result['compliance_by_service'].items():
    service_total = stats['resources_checked']
    service_compliant = stats['compliant_resources']
    service_non_compliant = stats['non_compliant_resources']

    if service_total > 0:
        compliance_rate = (service_compliant / service_total) * 100
        print(f"{service}: {compliance_rate:.1f}% compliant ({service_compliant}/{service_total})")
```

## Step 5: Review Non-Compliant Resources

Examine the details of non-compliant resources:

```python
# List all non-compliant resources
print("\\nNon-compliant resources:")
for resource in encryption_result['resource_details']:
    if not resource.get('compliant', True):
        print(f"- {resource['type']}: {resource['name']}")
        print(f"  Issues: {', '.join(resource['issues'])}")
        print(f"  Remediation: {', '.join(resource['remediation'])}")
```

## Step 6: Implement Recommendations

Review and implement the recommended remediation steps:

```python
print("\\nRecommendations:")
for recommendation in encryption_result['recommendations']:
    print(f"- {recommendation}")
```

## Best Practices for Storage Security

1. **Enable encryption by default** for all storage services
2. **Use customer-managed KMS keys** for sensitive data rather than AWS-managed keys
3. **Implement key rotation policies** for all customer-managed KMS keys
4. **Block public access** for S3 buckets at the account level
5. **Enable bucket key** for S3 buckets to reduce KMS API calls and costs
6. **Audit encryption settings regularly** to ensure continued compliance

By following this workflow, you'll efficiently assess your AWS storage security posture and identify resources that need encryption or security improvements.
"""


@mcp.prompt(name="wa-sec-check-network")
async def check_network_security_prompt(ctx: Context) -> str:
    """Provides guidance on checking AWS network resources for proper in-transit security configuration.

    This prompt explains the recommended workflow for assessing network security:
    1. First, identify available network services in the target region
    2. Then, check if these network resources have proper in-transit security measures
    3. Finally, analyze the results and implement recommended remediation steps

    This approach helps ensure data protection in transit according to AWS Well-Architected Framework
    Security Pillar best practices.
    """
    return """
# AWS Network Security Assessment Guide

This guide will help you assess the security of your AWS network resources by checking for proper in-transit security configurations.

## Step 1: Identify Available Network Services

First, determine which network services are available in your target region:

```python
# Option 1: List all services in the region
services_result = await use_mcp_tool(
    server_name="well-architected-security-mcp-server",
    tool_name="ListServicesInRegion",
    arguments={
        "region": "us-east-1",  # Specify your AWS region
        "aws_profile": "default",  # Optional: specify your AWS profile
        "store_in_context": True  # Store results for later use
    }
)

# Option 2: List resource types (alternative approach)
resource_types = await use_mcp_tool(
    server_name="well-architected-security-mcp-server",
    tool_name="ListResourceTypes",
    arguments={
        "region": "us-east-1",  # Specify your AWS region
        "aws_profile": "default",  # Optional: specify your AWS profile
        "store_in_context": True  # Store results for later use
    }
)
```

## Step 2: Filter for Network Services

Next, filter the results to focus on network services:

```python
# Define network services to check
network_services = ['elb', 'vpc', 'apigateway', 'cloudfront']

# Filter available services to include only network services
available_network_services = []

# If using ListServicesInRegion result
if 'services' in services_result:
    available_network_services = [s for s in services_result['services'] if s in network_services]

# If using ListResourceTypes result
if 'network_services' in resource_types:
    available_network_services = resource_types['network_services']

print(f"Available network services: {', '.join(available_network_services)}")
```

## Step 3: Check Network Security

Now, check if your network resources have proper in-transit security measures:

```python
network_result = await use_mcp_tool(
    server_name="well-architected-security-mcp-server",
    tool_name="CheckNetworkSecurity",
    arguments={
        "region": "us-east-1",  # Specify your AWS region
        "services": available_network_services,  # Use the filtered list from Step 2
        "include_non_compliant_only": False,  # Set to True to focus only on non-compliant resources
        "aws_profile": "default",  # Optional: specify your AWS profile
        "store_in_context": True  # Store results for later use
    }
)
```

## Step 4: Analyze the Results

Review the network security check results:

```python
# Get overall compliance statistics
total_resources = network_result['resources_checked']
compliant_resources = network_result['compliant_resources']
non_compliant_resources = network_result['non_compliant_resources']

print(f"Total resources checked: {total_resources}")
print(f"Compliant resources: {compliant_resources} ({(compliant_resources/total_resources)*100:.1f}% if total_resources > 0 else 0}%)")
print(f"Non-compliant resources: {non_compliant_resources} ({(non_compliant_resources/total_resources)*100:.1f}% if total_resources > 0 else 0}%)")

# Review compliance by service
for service, stats in network_result['compliance_by_service'].items():
    service_total = stats['resources_checked']
    service_compliant = stats['compliant_resources']
    service_non_compliant = stats['non_compliant_resources']

    if service_total > 0:
        compliance_rate = (service_compliant / service_total) * 100
        print(f"{service}: {compliance_rate:.1f}% compliant ({service_compliant}/{service_total})")
```

## Step 5: Review Non-Compliant Resources

Examine the details of non-compliant resources:

```python
# List all non-compliant resources
print("\\nNon-compliant resources:")
for resource in network_result['resource_details']:
    if not resource.get('compliant', True):
        print(f"- {resource['type']}: {resource['name']}")
        print(f"  Issues: {', '.join(resource['issues'])}")
        print(f"  Remediation: {', '.join(resource['remediation'])}")
```

## Step 6: Implement Recommendations

Review and implement the recommended remediation steps:

```python
print("\\nRecommendations:")
for recommendation in network_result['recommendations']:
    print(f"- {recommendation}")
```

## Best Practices for Network Security

1. **Use HTTPS/TLS** for all public-facing endpoints
2. **Configure security policies** to use modern TLS versions (TLS 1.2 or later)
3. **Implement strict security headers** for web applications
4. **Use AWS Certificate Manager (ACM)** for managing SSL/TLS certificates
5. **Enable VPC Flow Logs** to monitor network traffic
6. **Implement network segmentation** using security groups and NACLs
7. **Use AWS WAF** to protect web applications from common exploits
8. **Regularly audit network security configurations** to ensure continued compliance

By following this workflow, you'll efficiently assess your AWS network security posture and identify resources that need security improvements for data in transit.
"""


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(description="AWS Security Pillar MCP Server")
    parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    parser.add_argument("--port", type=int, default=8888, help="Port to run the server on")

    args = parser.parse_args()

    logger.info("Starting AWS Security Pillar MCP Server")

    # Run server with appropriate transport
    if args.sse:
        logger.info(f"Running MCP server with SSE transport on port {args.port}")
        mcp.settings.port = args.port
        mcp.run(transport="sse")
    else:
        logger.info("Running MCP server with default transport")
        mcp.run()


if __name__ == "__main__":
    main()
