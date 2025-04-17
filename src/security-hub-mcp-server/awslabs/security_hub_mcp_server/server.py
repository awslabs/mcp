"""awslabs Security Hub MCP Server implementation."""

import argparse
import boto3
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


@mcp.tool(name='get_findings')
async def get_findings(
    region: str,
    aws_account_id: str = None,
    severity: str = None,
    max_results: int = 100,
) -> Optional[List[Dict]]:
    """Get findings from the Security Hub service.

    Args:
        region (str): the AWS region to in which to query the SecurityHub service
        aws_account_id (str): (optional) filter the findings to the specified AWS account id
        severity (str): (optional) filter the findings to the specified finding severity
        max_results (int): (optional) the maximum number of finding results to return; note the maximum
        number of results supported by the SecurityHub service is 100

    Returns:
        List containing the Security Hub findings for the query; each finding is a dictionary.
    """
    security_hub = boto3.Session(profile_name=profile_name).client(
        'securityhub', region_name=region
    )
    filters = {}
    if aws_account_id:
        filters['AwsAccountId'] = [{'Value': aws_account_id, 'Comparison': 'EQUALS'}]

    if severity:
        filters['SeverityLabel'] = [{'Value': severity, 'Comparison': 'EQUALS'}]

    findings = []
    paginator = security_hub.get_paginator('get_findings')
    query_params = {
        'Filters': filters,
        'MaxResults': min(max_results, 100),
    }
    response_iterator = paginator.paginate(**query_params)
    for page in response_iterator:
        if 'Findings' in page:
            findings.extend(page['Findings'])

    logger.info(f'Found {len(findings)} findings: {findings}')
    return {'Findings': findings}


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
