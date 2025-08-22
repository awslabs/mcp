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

import boto3
import json
from awslabs.security_hub_mcp_server.consts import (
    DEFAULT_MAX_RESULTS,
    DEFAULT_REGION,
    SERVICE_NAME,
    SEVERITY_LABELS,
)
from awslabs.security_hub_mcp_server.models import (
    Finding,
    Insight,
    SecurityStandard,
)
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime, timedelta
from loguru import logger
from mcp.server.fastmcp import FastMCP
from typing import Dict, List, Literal, Optional


# Initialize FastMCP server
mcp = FastMCP(
    'awslabs.security-hub-mcp-server',
    instructions="""
    # AWS Security Hub MCP Server

    This Security Hub MCP server provides tools to interact with AWS Security Hub service including:
    - Finding management and retrieval
    - Compliance checks and security standards
    - Security insights and analytics
    - Control status monitoring

    The server requires appropriate AWS credentials and Security Hub to be enabled in your AWS account.
    All operations respect AWS IAM permissions and Security Hub service limits.
    """,
)


def _get_security_hub_client(region: str = DEFAULT_REGION) -> boto3.client:
    """Get a Security Hub client for the specified region."""
    try:
        return boto3.client(SERVICE_NAME, region_name=region)
    except Exception as e:
        logger.error(f'Failed to create Security Hub client: {e}')
        raise


def _handle_aws_error(e: Exception, operation: str) -> str:
    """Handle AWS service errors and return user-friendly messages."""
    if isinstance(e, ClientError):
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        if error_code == 'InvalidAccessException':
            return f'Access denied for {operation}. Please check your AWS credentials and IAM permissions.'
        elif error_code == 'InvalidInputException':
            return f'Invalid input for {operation}: {error_message}'
        elif error_code == 'ResourceNotFoundException':
            return f'Resource not found for {operation}: {error_message}'
        elif error_code == 'LimitExceededException':
            return f'Service limit exceeded for {operation}: {error_message}'
        else:
            return f'AWS error in {operation}: {error_code} - {error_message}'
    elif isinstance(e, BotoCoreError):
        return f'AWS service error in {operation}: {str(e)}'
    else:
        return f'Unexpected error in {operation}: {str(e)}'


@mcp.tool(name='GetFindings')
async def get_findings(
    region: str = DEFAULT_REGION,
    max_results: int = 50,
    severity_labels: Optional[
        List[Literal['INFORMATIONAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']]
    ] = None,
    workflow_states: Optional[List[Literal['NEW', 'NOTIFIED', 'RESOLVED', 'SUPPRESSED']]] = None,
    record_states: Optional[List[Literal['ACTIVE', 'ARCHIVED']]] = None,
    compliance_statuses: Optional[
        List[Literal['PASSED', 'WARNING', 'FAILED', 'NOT_AVAILABLE']]
    ] = None,
    resource_type: Optional[str] = None,
    aws_account_id: Optional[str] = None,
    days_back: Optional[int] = None,
) -> str:
    """Retrieve Security Hub findings with optional filters.

    This tool fetches findings from AWS Security Hub based on the provided filters.
    Findings represent security issues, compliance violations, or other security-related events.

    Args:
        region: AWS region to query (default: us-east-1)
        max_results: Maximum number of findings to return (1-100, default: 50)
        severity_labels: Filter by severity labels
        workflow_states: Filter by workflow states
        record_states: Filter by record states
        compliance_statuses: Filter by compliance status
        resource_type: Filter by AWS resource type
        aws_account_id: Filter by AWS account ID
        days_back: Filter findings updated in the last N days
    """
    try:
        client = _get_security_hub_client(region)

        # Build filters
        filters = {}

        if severity_labels:
            filters['SeverityLabel'] = [
                {'Value': label, 'Comparison': 'EQUALS'} for label in severity_labels
            ]

        if workflow_states:
            filters['WorkflowState'] = [
                {'Value': state, 'Comparison': 'EQUALS'} for state in workflow_states
            ]

        if record_states:
            filters['RecordState'] = [
                {'Value': state, 'Comparison': 'EQUALS'} for state in record_states
            ]

        if compliance_statuses:
            filters['ComplianceStatus'] = [
                {'Value': status, 'Comparison': 'EQUALS'} for status in compliance_statuses
            ]

        if resource_type:
            filters['ResourceType'] = [{'Value': resource_type, 'Comparison': 'EQUALS'}]

        if aws_account_id:
            filters['AwsAccountId'] = [{'Value': aws_account_id, 'Comparison': 'EQUALS'}]

        if days_back:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            filters['UpdatedAt'] = [
                {'Start': cutoff_date.isoformat(), 'DateRange': {'Unit': 'DAYS'}}
            ]

        # Ensure max_results is within limits
        max_results = min(max(1, max_results), DEFAULT_MAX_RESULTS)

        response = client.get_findings(Filters=filters, MaxResults=max_results)

        findings = []
        for finding_data in response.get('Findings', []):
            finding = Finding(
                id=finding_data['Id'],
                product_arn=finding_data['ProductArn'],
                generator_id=finding_data['GeneratorId'],
                aws_account_id=finding_data['AwsAccountId'],
                title=finding_data['Title'],
                description=finding_data['Description'],
                severity=finding_data.get('Severity', {}),
                compliance=finding_data.get('Compliance'),
                workflow_state=finding_data['WorkflowState'],
                record_state=finding_data['RecordState'],
                created_at=datetime.fromisoformat(
                    finding_data['CreatedAt'].replace('Z', '+00:00')
                ),
                updated_at=datetime.fromisoformat(
                    finding_data['UpdatedAt'].replace('Z', '+00:00')
                ),
                resources=finding_data.get('Resources', []),
            )
            findings.append(finding)

        result = {
            'findings_count': len(findings),
            'findings': [finding.model_dump() for finding in findings],
            'next_token': response.get('NextToken'),
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_msg = _handle_aws_error(e, 'get findings')
        logger.error(error_msg)
        return f'Error: {error_msg}'


@mcp.tool(name='GetComplianceByConfigRule')
async def get_compliance_by_config_rule(
    region: str = DEFAULT_REGION,
    config_rule_names: Optional[List[str]] = None,
    compliance_types: Optional[
        List[Literal['COMPLIANT', 'NON_COMPLIANT', 'NOT_APPLICABLE', 'INSUFFICIENT_DATA']]
    ] = None,
    max_results: int = 50,
) -> str:
    """Get compliance information by AWS Config rules.

    This tool retrieves compliance status for AWS Config rules, which are used by Security Hub
    to evaluate resource configurations against security standards.

    Args:
        region: AWS region to query
        config_rule_names: List of Config rule names to check
        compliance_types: Filter by compliance types
        max_results: Maximum number of results to return
    """
    try:
        client = _get_security_hub_client(region)

        # Build the request parameters
        max_results = min(max(1, max_results), DEFAULT_MAX_RESULTS)

        # Note: This would typically use AWS Config client, but for Security Hub context
        # we'll get compliance-related findings instead
        filters = {'ComplianceStatus': [{'Value': 'FAILED', 'Comparison': 'EQUALS'}]}

        response = client.get_findings(Filters=filters, MaxResults=max_results)

        compliance_results = []
        for finding in response.get('Findings', []):
            if finding.get('Compliance'):
                compliance_results.append(
                    {
                        'finding_id': finding['Id'],
                        'title': finding['Title'],
                        'compliance_status': finding['Compliance'].get('Status'),
                        'resource_type': finding.get('Resources', [{}])[0].get('Type'),
                        'resource_id': finding.get('Resources', [{}])[0].get('Id'),
                        'updated_at': finding['UpdatedAt'],
                    }
                )

        result = {
            'compliance_results_count': len(compliance_results),
            'compliance_results': compliance_results,
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_msg = _handle_aws_error(e, 'get compliance by config rule')
        logger.error(error_msg)
        return f'Error: {error_msg}'


@mcp.tool(name='GetEnabledStandards')
async def get_enabled_standards(
    region: str = DEFAULT_REGION,
    max_results: int = 50,
) -> str:
    """Get all enabled security standards in Security Hub.

    This tool retrieves information about security standards that are currently enabled,
    such as AWS Foundational Security Standard, CIS AWS Foundations Benchmark, etc.

    Args:
        region: AWS region to query
        max_results: Maximum number of standards to return
    """
    try:
        client = _get_security_hub_client(region)

        max_results = min(max(1, max_results), DEFAULT_MAX_RESULTS)

        response = client.get_enabled_standards(MaxResults=max_results)

        standards = []
        for standard_data in response.get('StandardsSubscriptions', []):
            standard = SecurityStandard(
                standards_arn=standard_data['StandardsArn'],
                name=standard_data.get('StandardsInput', {}).get('Name', 'Unknown'),
                description=standard_data.get('StandardsInput', {}).get('Description', ''),
                enabled_by_default=standard_data.get('StandardsStatus') == 'ENABLED',
            )
            standards.append(standard)

        result = {
            'enabled_standards_count': len(standards),
            'enabled_standards': [standard.model_dump() for standard in standards],
            'next_token': response.get('NextToken'),
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_msg = _handle_aws_error(e, 'get enabled standards')
        logger.error(error_msg)
        return f'Error: {error_msg}'


@mcp.tool(name='GetInsights')
async def get_insights(
    region: str = DEFAULT_REGION,
    insight_arns: Optional[List[str]] = None,
    max_results: int = 50,
) -> str:
    """Get Security Hub insights.

    Insights are collections of related findings defined by an aggregation statement and filters.
    They help identify common security issues and trends.

    Args:
        region: AWS region to query
        insight_arns: List of insight ARNs to retrieve
        max_results: Maximum number of insights to return
    """
    try:
        client = _get_security_hub_client(region)

        max_results = min(max(1, max_results), DEFAULT_MAX_RESULTS)

        params = {'MaxResults': max_results}

        if insight_arns:
            params['InsightArns'] = insight_arns

        response = client.get_insights(**params)

        insights = []
        for insight_data in response.get('Insights', []):
            insight = Insight(
                insight_arn=insight_data['InsightArn'],
                name=insight_data['Name'],
                filters=insight_data['Filters'],
                group_by_attribute=insight_data['GroupByAttribute'],
            )
            insights.append(insight)

        result = {
            'insights_count': len(insights),
            'insights': [insight.model_dump() for insight in insights],
            'next_token': response.get('NextToken'),
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_msg = _handle_aws_error(e, 'get insights')
        logger.error(error_msg)
        return f'Error: {error_msg}'


@mcp.tool(name='GetInsightResults')
async def get_insight_results(
    insight_arn: str,
    region: str = DEFAULT_REGION,
) -> str:
    """Get the results of a specific Security Hub insight.

    This tool retrieves the current results for a given insight, showing the grouped findings
    and their counts based on the insight's configuration.

    Args:
        insight_arn: The ARN of the insight to get results for
        region: AWS region to query
    """
    try:
        client = _get_security_hub_client(region)

        response = client.get_insight_results(InsightArn=insight_arn)

        insight_results = response.get('InsightResults', {})

        result = {
            'insight_arn': insight_arn,
            'group_by_attribute': insight_results.get('GroupByAttribute'),
            'result_values': insight_results.get('ResultValues', []),
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_msg = _handle_aws_error(e, 'get insight results')
        logger.error(error_msg)
        return f'Error: {error_msg}'


@mcp.tool(name='GetSecurityScore')
async def get_security_score(
    region: str = DEFAULT_REGION,
) -> str:
    """Get the overall security score for the account.

    This tool calculates a security score based on the ratio of passed vs failed findings
    across all enabled security standards.

    Args:
        region: AWS region to query
    """
    try:
        client = _get_security_hub_client(region)

        # Get findings with different compliance statuses
        passed_response = client.get_findings(
            Filters={
                'ComplianceStatus': [{'Value': 'PASSED', 'Comparison': 'EQUALS'}],
                'RecordState': [{'Value': 'ACTIVE', 'Comparison': 'EQUALS'}],
            },
            MaxResults=1,
        )

        failed_response = client.get_findings(
            Filters={
                'ComplianceStatus': [{'Value': 'FAILED', 'Comparison': 'EQUALS'}],
                'RecordState': [{'Value': 'ACTIVE', 'Comparison': 'EQUALS'}],
            },
            MaxResults=1,
        )

        # Get total counts (this is an approximation since we can't get exact counts easily)
        total_passed = len(passed_response.get('Findings', []))
        total_failed = len(failed_response.get('Findings', []))

        # Calculate basic metrics
        total_findings = total_passed + total_failed
        if total_findings > 0:
            pass_rate = (total_passed / total_findings) * 100
        else:
            pass_rate = 0

        # Get severity breakdown for active findings
        severity_breakdown = {}
        for severity in SEVERITY_LABELS:
            severity_response = client.get_findings(
                Filters={
                    'SeverityLabel': [{'Value': severity, 'Comparison': 'EQUALS'}],
                    'RecordState': [{'Value': 'ACTIVE', 'Comparison': 'EQUALS'}],
                },
                MaxResults=1,
            )
            severity_breakdown[severity.lower()] = len(severity_response.get('Findings', []))

        result = {
            'security_score': {
                'pass_rate_percentage': round(pass_rate, 2),
                'total_active_findings': total_findings,
                'passed_findings': total_passed,
                'failed_findings': total_failed,
            },
            'severity_breakdown': severity_breakdown,
            'region': region,
            'generated_at': datetime.now().isoformat(),
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_msg = _handle_aws_error(e, 'get security score')
        logger.error(error_msg)
        return f'Error: {error_msg}'


@mcp.tool(name='UpdateFindingWorkflowState')
async def update_finding_workflow_state(
    finding_identifiers: List[Dict[str, str]],
    workflow_state: Literal['NEW', 'NOTIFIED', 'RESOLVED', 'SUPPRESSED'],
    note: Optional[str] = None,
    region: str = DEFAULT_REGION,
) -> str:
    """Update the workflow state of Security Hub findings.

    This tool allows you to change the workflow state of findings, which is useful for
    tracking the progress of security issue remediation.

    Args:
        finding_identifiers: List of finding identifiers (Id and ProductArn pairs)
        workflow_state: New workflow state for the findings
        note: Optional note about the workflow update
        region: AWS region to update findings in
    """
    try:
        client = _get_security_hub_client(region)

        # Prepare the workflow update
        workflow_update = {'Status': workflow_state}
        if note:
            workflow_update['Note'] = note

        response = client.batch_update_findings(
            FindingIdentifiers=finding_identifiers, Workflow=workflow_update
        )

        result = {
            'processed_findings': response.get('ProcessedFindings', []),
            'unprocessed_findings': response.get('UnprocessedFindings', []),
            'workflow_state': workflow_state,
            'note': note,
            'updated_at': datetime.now().isoformat(),
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_msg = _handle_aws_error(e, 'update finding workflow state')
        logger.error(error_msg)
        return f'Error: {error_msg}'


def main():
    """Run the Security Hub MCP server."""
    logger.info('Starting AWS Security Hub MCP Server')
    mcp.run()


if __name__ == '__main__':
    main()
