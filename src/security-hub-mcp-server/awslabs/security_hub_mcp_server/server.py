"""awslabs Security Hub MCP Server implementation."""

import argparse
import boto3
import json
import logging
import os
from mcp.server.fastmcp import FastMCP
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

VALID_SEVERITIES = ['INFORMATIONAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
VALID_WORKFLOW_STATUSES = ['NEW', 'NOTIFIED', 'RESOLVED', 'SUPPRESSED']


@mcp.tool(name='get_findings')
async def get_findings(
    region: str,
    aws_account_id: str = None,
    severity: str = None,
    workflow_status: str = None,
    custom_filters: dict = None,
    max_results: int = 100,
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
        custom_filters (str): (optional) JSON string of additional Security Hub filters
                             Example: '{"ResourceType": [{"Comparison": "EQUALS", "Value": "AwsAccount"}]}'
                             See AWS Security Hub GetFindings API documentation for all available filters
        max_results (int): (optional) the maximum number of finding results to return; note the maximum
        number of results supported by the SecurityHub service is 100

    Returns:
        List containing the Security Hub findings for the query; each finding is a dictionary.
    """
    if severity and severity.upper() not in VALID_SEVERITIES:
        return [
            {
                'error': f'Invalid severity ({severity}). Must be one of: {", ".join(VALID_SEVERITIES)}'
            }
        ]

    if workflow_status and workflow_status.upper() not in VALID_WORKFLOW_STATUSES:
        return [
            {
                'error': f'Invalid workflow status ({workflow_status}). Must be one of: {", ".join(VALID_WORKFLOW_STATUSES)}'
            }
        ]

    security_hub = boto3.Session(profile_name=profile_name).client(
        'securityhub', region_name=region
    )

    # Start with basic filters from individual parameters
    filters = {}
    if aws_account_id:
        filters['AwsAccountId'] = [{'Value': aws_account_id, 'Comparison': 'EQUALS'}]

    if severity:
        filters['SeverityLabel'] = [{'Value': severity.upper(), 'Comparison': 'EQUALS'}]

    # Add custom filters from JSON string
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
        'MaxResults': min(max_results, 100),
    }

    logger.info(f'Getting SecurityHub findings with params: {query_params}')

    response_iterator = paginator.paginate(**query_params)
    for page in response_iterator:
        if 'Findings' in page:
            findings.extend(page['Findings'])

    # Log warning if maximum results reached
    if len(findings) == max_results:
        logger.warning(f'Maximum results ({max_results}) reached. Some findings may be truncated.')

    logger.info(f'Found {len(findings)} findings')
    if len(findings) > max_results:
        # security hub can return more findings than requested; trim to max_results
        findings = findings[:max_results]

    return findings


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='A Model Context Protocol (MCP) server for Security Hub'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':
    main()
