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

"""awslabs Security Hub MCP Server implementation."""

import boto3
import json
import logging
import os
from enum import Enum
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Dict, List, Optional


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    'awslabs.security-hub-mcp-server',
    instructions="""Use this server to analyze findings in AWS Security Hub.""",
    dependencies=[
        'pydantic',
    ],
)

profile_name = os.getenv('AWS_PROFILE', 'default')
logger.info(f'Using AWS profile {profile_name}')


class Severity(str, Enum):
    """Security Hub Severity levels as defined in the Security Hub API.

    See: https://docs.aws.amazon.com/securityhub/1.0/APIReference/API_Severity.html

    Attributes:
        INFORMATIONAL: Informational severity level
        LOW: Low severity level
        MEDIUM: Medium severity level
        HIGH: High severity level
        CRITICAL: Critical severity level
    """

    INFORMATIONAL = 'INFORMATIONAL'
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'


class WorkflowStatus(str, Enum):
    """Security Hub Workflow Status options as defined in the Security Hub API.

    See: https://docs.aws.amazon.com/securityhub/1.0/APIReference/API_Workflow.html

    Attributes:
        NEW: The initial state of a finding, before it is reviewed.
        NOTIFIED: Indicates that the resource owner has been notified about the security issue.
        RESOLVED: The finding was reviewed and remediated and is now considered resolved.
        SUPPRESSED: The finding will not be reviewed again and will not be acted upon.
    """

    NEW = 'NEW'
    NOTIFIED = 'NOTIFIED'
    RESOLVED = 'RESOLVED'
    SUPPRESSED = 'SUPPRESSED'


async def get_findings(
    region: str,
    aws_account_id: Optional[str] = None,
    severity: Optional[str] = None,
    workflow_status: Optional[str] = None,
    custom_filters: Optional[dict] = None,
    max_results: Optional[int] = None,
) -> Optional[List[Dict]]:
    """Get findings from the Security Hub service.

    Args:
        region (str): the AWS region to in which to query the SecurityHub service
        aws_account_id (str): (optional) filter the findings to the specified AWS account id
        severity (str): (optional) filter the findings to the specified finding severity (INFORMATIONAL, LOW, MEDIUM, HIGH, CRITICAL)
        workflow_status (str): (optional) filter the findings to the specified workflow status (NEW, NOTIFIED, RESOLVED, SUPPRESSED)
        custom_filters (str): (optional) A dictionary of additional Security Hub filters
                       Example: {"ResourceType": [{"Comparison": "EQUALS", "Value": "AwsAccount"}]}
                       See AWS Security Hub GetFindings API documentation for all available filters.
        max_results (int): (optional) the maximum number of finding results to return

    Returns:
        List containing the Security Hub findings for the query; each finding is a dictionary.
    """
    # Resolve string severity to Severity enum
    severity_enum = None
    if severity is not None:
        try:
            severity_enum = Severity(severity.upper())
        except ValueError:
            return [
                {
                    'error': f'Invalid severity ({severity}). Must be one of: {", ".join([s.value for s in Severity])}'
                }
            ]

    # Resolve string workflow_status to WorkflowStatus enum
    workflow_status_enum = None
    if workflow_status:
        try:
            workflow_status_enum = WorkflowStatus(workflow_status.upper())
        except ValueError:
            return [
                {
                    'error': f'Invalid workflow status ({workflow_status}). Must be one of: {", ".join([w.value for w in WorkflowStatus])}'
                }
            ]

    security_hub = boto3.Session(profile_name=profile_name).client(
        'securityhub', region_name=region
    )

    # Start with basic filters from individual parameters
    filters = {}
    if aws_account_id:
        filters['AwsAccountId'] = [{'Value': aws_account_id, 'Comparison': 'EQUALS'}]

    if severity_enum:
        filters['SeverityLabel'] = [{'Value': severity_enum.value, 'Comparison': 'EQUALS'}]

    if workflow_status_enum:
        filters['WorkflowStatus'] = [{'Value': workflow_status_enum.value, 'Comparison': 'EQUALS'}]

    # Add custom filters on top of standard filters
    if custom_filters:
        try:
            if not isinstance(custom_filters, dict):
                return [{'error': 'custom_filters must be a JSON object'}]
            logger.debug(f'Applying custom filters: {custom_filters}')
            filters.update(custom_filters)
        except json.JSONDecodeError as e:
            logger.warning(f'Invalid custom filters JSON: {e}')
            return [{'error': f'Invalid JSON in custom_filters parameter: {str(e)}'}]

    findings = []
    paginator = security_hub.get_paginator('get_findings')
    query_params = {
        'Filters': filters,
    }
    if max_results is not None and max_results > 0:
        query_params['MaxResults'] = max_results

    logger.info(f'Getting SecurityHub findings with params: {query_params}')

    response_iterator = paginator.paginate(**query_params)
    for page in response_iterator:
        if 'Findings' in page:
            findings.extend(page['Findings'])

    # Apply max_results rules to findings if specified
    if max_results is not None and max_results > 0:
        if len(findings) == max_results:
            logger.warning(
                f'Maximum results ({max_results}) reached. Some findings may be truncated.'
            )

        logger.info(f'Found {len(findings)} findings')
        if len(findings) > max_results:
            # security hub can return more findings than requested; trim to max_results
            findings = findings[:max_results]

    return findings


@mcp.tool(name='get_findings')
async def get_findings_tool(
    region: str = Field(
        ..., description='The AWS region to in which to query the SecurityHub service'
    ),
    aws_account_id: Optional[str] = Field(
        default=None,
        description="""(optional) Filter the findings to the specified AWS account id""",
    ),
    severity: Optional[str] = Field(
        default=None,
        description="""(optional) Filter the findings to the specified finding severity (INFORMATIONAL, LOW, MEDIUM, HIGH, CRITICAL)""",
    ),
    workflow_status: Optional[str] = Field(
        default=None,
        description="""(optional) Filter the findings to the specified workflow status (NEW, NOTIFIED, RESOLVED, SUPPRESSED)""",
    ),
    custom_filters: Optional[dict] = Field(
        default=None,
        description="""(optional) A dictionary of additional Security Hub filters
                       Example: {"ResourceType": [{"Comparison": "EQUALS", "Value": "AwsAccount"}]}
                       See AWS Security Hub GetFindings API documentation for all available filters.""",
    ),
    max_results: Optional[int] = Field(
        default=None, description="""(optional) The maximum number of finding results to return"""
    ),
) -> Optional[List[Dict]]:
    """Get findings from the Security Hub service.

    Examples:
        # Get all HIGH severity findings in us-east-1
        get_findings(region="us-east-1", severity="HIGH")

        # Get findings with a custom resource type filter
        get_findings(
            region="us-east-1",
            custom_filters={'ResourceType': [{'Comparison': 'EQUALS', 'Value': 'AwsAccount'}]}
        )

        # Combine basic and custom filters
        get_findings(
            region="us-east-1",
            severity="HIGH",
            custom_filters='{"ResourceType": [{"Comparison": "EQUALS", "Value": "AwsAccount"}]}'
        )

    Args:
        region (str): the AWS region to in which to query the SecurityHub service
        aws_account_id (str): (optional) filter the findings to the specified AWS account id
        severity (str): (optional) filter the findings to the specified finding severity (INFORMATIONAL, LOW, MEDIUM, HIGH, CRITICAL)
        workflow_status (str): (optional) filter the findings to the specified workflow status (NEW, NOTIFIED, RESOLVED, SUPPRESSED)
        custom_filters (str): (optional) A dictionary of additional Security Hub filters
                       Example: {"ResourceType": [{"Comparison": "EQUALS", "Value": "AwsAccount"}]}
                       See AWS Security Hub GetFindings API documentation for all available filters.
        max_results (int): (optional) the maximum number of finding results to return

    Returns:
        List containing the Security Hub findings for the query; each finding is a dictionary.
    """
    return await get_findings(
        region=region,
        aws_account_id=aws_account_id,
        severity=severity,
        workflow_status=workflow_status,
        custom_filters=custom_filters,
        max_results=max_results,
    )


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()
