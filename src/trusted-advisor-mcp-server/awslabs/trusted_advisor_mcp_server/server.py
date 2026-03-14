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
"""AWS Trusted Advisor MCP Server implementation."""

import asyncio
import os
import sys
from awslabs.trusted_advisor_mcp_server.client import TrustedAdvisorClient
from awslabs.trusted_advisor_mcp_server.formatters import (
    format_checks_list,
    format_cost_optimization_summary,
    format_lifecycle_update_result,
    format_organization_recommendations,
    format_recommendation_detail,
    format_recommendations_list,
    format_security_summary,
    format_service_limits_summary,
)
from botocore.exceptions import ClientError
from fastmcp import Context, FastMCP
from loguru import logger
from pydantic import Field
from typing import Optional


# Configure logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))


# Initialize the MCP server
mcp = FastMCP(
    'awslabs_trusted_advisor_mcp_server',
    instructions="""
    # AWS Trusted Advisor MCP Server

    This MCP server provides tools for accessing AWS Trusted Advisor recommendations,
    enabling AI assistants to help users optimize their AWS infrastructure across cost,
    performance, security, fault tolerance, service limits, and operational excellence.

    ## Important Notes
    - Requires AWS Business, Enterprise On-Ramp, or Enterprise Support plan.
    - The Trusted Advisor API is a global service accessed through us-east-1.
    - Organization-level tools require management account or delegated admin access.
    - The update_recommendation_lifecycle tool modifies recommendation state - use with care.

    ## Available Tools

    ### list_trusted_advisor_checks
    List all available checks with optional filtering by pillar or AWS service.
    Use this to discover what checks are available.

    ### list_recommendations
    List current recommendations (findings) with optional filtering by status, pillar, or date.
    This is the primary tool for seeing what Trusted Advisor has found.

    ### get_recommendation
    Get detailed information about a specific recommendation including all affected resources.
    Use this after identifying a recommendation from list_recommendations.

    ### get_cost_optimization_summary
    Get a summary of all cost optimization recommendations with total estimated monthly savings.
    Best for answering "How can I reduce my AWS bill?"

    ### get_security_summary
    Get a summary of all security recommendations including active warnings and errors.
    Best for answering "What security issues does my account have?"

    ### get_service_limits_summary
    Get a summary of services approaching or exceeding their limits.
    Best for answering "Am I hitting any service limits?"

    ### update_recommendation_lifecycle
    Update the lifecycle stage of a recommendation (e.g., dismiss, mark in progress).
    This is a write operation - confirm with the user before executing.

    ### list_organization_recommendations
    List recommendations across all accounts in AWS Organizations.
    Requires management account or delegated administrator access.

    ## Best Practices
    1. Start with list_recommendations to get an overview, then drill into specific items.
    2. Use summary tools (cost, security, service limits) for quick overviews.
    3. Always confirm before using update_recommendation_lifecycle.
    4. For organization-wide analysis, use list_organization_recommendations.
    """,
)

# Initialize the AWS Trusted Advisor client
try:
    ta_client = TrustedAdvisorClient(
        region_name=os.environ.get('AWS_REGION', 'us-east-1'),
        profile_name=os.environ.get('AWS_PROFILE'),
    )
except Exception as e:
    logger.error(f'Failed to initialize Trusted Advisor client: {str(e)}')
    raise


@mcp.tool(name='list_trusted_advisor_checks')
async def list_trusted_advisor_checks(
    ctx: Context,
    pillar: Optional[str] = Field(
        None,
        description='Filter by Well-Architected pillar: cost_optimizing, performance, security, '
        'fault_tolerance, operational_excellence, or service_limits',
    ),
    aws_service: Optional[str] = Field(
        None, description='Filter by AWS service name (e.g., Amazon EC2, Amazon S3)'
    ),
    language: str = Field('en', description='Language code for descriptions (default: en)'),
) -> str:
    """List all available Trusted Advisor checks with optional filtering.

    Returns a formatted list of all checks grouped by pillar, including check names,
    descriptions, and associated AWS services.

    ## Example
    ```
    list_trusted_advisor_checks(pillar="security")
    list_trusted_advisor_checks(aws_service="Amazon EC2")
    ```
    """
    try:
        checks = await ta_client.list_checks(
            pillar=pillar, aws_service=aws_service, language=language
        )
        return format_checks_list(checks)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f'Error listing checks: {error_code} - {error_message}')
        return f'Error listing Trusted Advisor checks: {error_code} - {error_message}'
    except Exception as e:
        logger.error(f'Unexpected error listing checks: {str(e)}')
        return f'Error listing Trusted Advisor checks: {str(e)}'


@mcp.tool(name='list_recommendations')
async def list_recommendations(
    ctx: Context,
    status: Optional[str] = Field(
        None, description='Filter by status: ok, warning, or error'
    ),
    pillar: Optional[str] = Field(
        None,
        description='Filter by Well-Architected pillar: cost_optimizing, performance, security, '
        'fault_tolerance, operational_excellence, or service_limits',
    ),
    after_last_updated_at: Optional[str] = Field(
        None,
        description='Filter to recommendations updated after this ISO 8601 datetime '
        '(e.g., 2024-01-01T00:00:00Z)',
    ),
    aws_service: Optional[str] = Field(
        None, description='Filter by AWS service name (e.g., Amazon EC2)'
    ),
) -> str:
    """List current Trusted Advisor recommendations for the account.

    Returns recommendations with their status, pillar, resource counts, and estimated savings.
    Use filters to narrow results by status (ok/warning/error), pillar, or date.

    ## Example
    ```
    list_recommendations(status="warning", pillar="security")
    list_recommendations(after_last_updated_at="2024-01-01T00:00:00Z")
    ```
    """
    try:
        recommendations = await ta_client.list_recommendations(
            status=status,
            pillar=pillar,
            after_last_updated_at=after_last_updated_at,
            aws_service=aws_service,
        )
        return format_recommendations_list(recommendations)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f'Error listing recommendations: {error_code} - {error_message}')
        return f'Error listing recommendations: {error_code} - {error_message}'
    except Exception as e:
        logger.error(f'Unexpected error listing recommendations: {str(e)}')
        return f'Error listing recommendations: {str(e)}'


@mcp.tool(name='get_recommendation')
async def get_recommendation(
    ctx: Context,
    recommendation_identifier: str = Field(
        ..., description='The ARN or ID of the recommendation to retrieve'
    ),
) -> str:
    """Get detailed information about a specific Trusted Advisor recommendation.

    Returns full recommendation details including description, lifecycle stage,
    resource aggregates, estimated savings, and a list of all affected resources.

    ## Example
    ```
    get_recommendation(
        recommendation_identifier="arn:aws:trustedadvisor::123456789012:recommendation/abc123"
    )
    ```
    """
    try:
        recommendation, resources = await asyncio.gather(
            ta_client.get_recommendation(recommendation_identifier),
            ta_client.list_recommendation_resources(recommendation_identifier),
        )
        return format_recommendation_detail(recommendation, resources)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f'Error getting recommendation: {error_code} - {error_message}')
        return f'Error getting recommendation: {error_code} - {error_message}'
    except Exception as e:
        logger.error(f'Unexpected error getting recommendation: {str(e)}')
        return f'Error getting recommendation: {str(e)}'


@mcp.tool(name='get_cost_optimization_summary')
async def get_cost_optimization_summary(ctx: Context) -> str:
    """Summarize all cost optimization recommendations with total estimated monthly savings.

    Aggregates all active cost optimization recommendations (warnings and errors),
    calculates total estimated monthly and annual savings, and returns recommendations
    sorted by savings amount.

    ## Example
    ```
    get_cost_optimization_summary()
    ```
    """
    try:
        # Fetch both warning and error cost optimization recommendations
        warnings, errors = await asyncio.gather(
            ta_client.list_recommendations(pillar='cost_optimizing', status='warning'),
            ta_client.list_recommendations(pillar='cost_optimizing', status='error'),
        )
        all_recommendations = warnings + errors
        return format_cost_optimization_summary(all_recommendations)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f'Error getting cost optimization summary: {error_code} - {error_message}')
        return f'Error getting cost optimization summary: {error_code} - {error_message}'
    except Exception as e:
        logger.error(f'Unexpected error getting cost optimization summary: {str(e)}')
        return f'Error getting cost optimization summary: {str(e)}'


@mcp.tool(name='get_security_summary')
async def get_security_summary(ctx: Context) -> str:
    """Summarize all security recommendations including active warnings and errors.

    Returns counts by status (ok/warning/error) and lists all active security issues
    sorted by severity. Use this for a quick security posture assessment.

    ## Example
    ```
    get_security_summary()
    ```
    """
    try:
        recommendations = await ta_client.list_recommendations(pillar='security')
        return format_security_summary(recommendations)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f'Error getting security summary: {error_code} - {error_message}')
        return f'Error getting security summary: {error_code} - {error_message}'
    except Exception as e:
        logger.error(f'Unexpected error getting security summary: {str(e)}')
        return f'Error getting security summary: {str(e)}'


@mcp.tool(name='get_service_limits_summary')
async def get_service_limits_summary(ctx: Context) -> str:
    """Summarize service limit recommendations for services approaching or exceeding limits.

    Returns a list of services that are approaching (warning) or have exceeded (error)
    their AWS service limits, along with affected resource counts.

    ## Example
    ```
    get_service_limits_summary()
    ```
    """
    try:
        warnings, errors = await asyncio.gather(
            ta_client.list_recommendations(pillar='service_limits', status='warning'),
            ta_client.list_recommendations(pillar='service_limits', status='error'),
        )
        all_recommendations = warnings + errors
        return format_service_limits_summary(all_recommendations)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f'Error getting service limits summary: {error_code} - {error_message}')
        return f'Error getting service limits summary: {error_code} - {error_message}'
    except Exception as e:
        logger.error(f'Unexpected error getting service limits summary: {str(e)}')
        return f'Error getting service limits summary: {str(e)}'


@mcp.tool(name='update_recommendation_lifecycle')
async def update_recommendation_lifecycle(
    ctx: Context,
    recommendation_identifier: str = Field(
        ..., description='The ARN or ID of the recommendation to update'
    ),
    lifecycle_stage: str = Field(
        ...,
        description='The new lifecycle stage: pending_response, in_progress, dismissed, or resolved',
    ),
    update_reason: Optional[str] = Field(
        None, description='The reason for the lifecycle update'
    ),
) -> str:
    """Update the lifecycle stage of a Trusted Advisor recommendation.

    **WARNING: This is a write operation that modifies the recommendation state.**
    Always confirm the action with the user before executing.

    Valid lifecycle stages:
    - pending_response: Awaiting response from the account owner
    - in_progress: Currently being addressed
    - dismissed: Recommendation has been dismissed
    - resolved: The issue has been resolved

    ## Example
    ```
    update_recommendation_lifecycle(
        recommendation_identifier="arn:aws:trustedadvisor::123456789012:recommendation/abc123",
        lifecycle_stage="dismissed",
        update_reason="This is expected behavior for our use case"
    )
    ```
    """
    valid_stages = {'pending_response', 'in_progress', 'dismissed', 'resolved'}
    if lifecycle_stage not in valid_stages:
        return (
            f'Invalid lifecycle stage: {lifecycle_stage}. '
            f'Must be one of: {", ".join(sorted(valid_stages))}'
        )

    try:
        await ta_client.update_recommendation_lifecycle(
            recommendation_identifier=recommendation_identifier,
            lifecycle_stage=lifecycle_stage,
            update_reason=update_reason,
        )
        return format_lifecycle_update_result(
            recommendation_identifier, lifecycle_stage, update_reason
        )
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(
            f'Error updating recommendation lifecycle: {error_code} - {error_message}'
        )
        return f'Error updating recommendation lifecycle: {error_code} - {error_message}'
    except Exception as e:
        logger.error(f'Unexpected error updating recommendation lifecycle: {str(e)}')
        return f'Error updating recommendation lifecycle: {str(e)}'


@mcp.tool(name='list_organization_recommendations')
async def list_organization_recommendations(
    ctx: Context,
    status: Optional[str] = Field(
        None, description='Filter by status: ok, warning, or error'
    ),
    pillar: Optional[str] = Field(
        None,
        description='Filter by Well-Architected pillar: cost_optimizing, performance, security, '
        'fault_tolerance, operational_excellence, or service_limits',
    ),
    aws_service: Optional[str] = Field(
        None, description='Filter by AWS service name'
    ),
    after_last_updated_at: Optional[str] = Field(
        None,
        description='Filter to recommendations updated after this ISO 8601 datetime',
    ),
) -> str:
    """List recommendations from Trusted Advisor Priority across AWS Organizations.

    **Requires Trusted Advisor Priority to be enabled on the management account.**
    Trusted Advisor Priority is available to AWS Enterprise Support customers and
    must be activated by your AWS Technical Account Manager (TAM). It is separate
    from the standard Organizational view in the Trusted Advisor console.

    If Priority is not enabled, this tool returns an empty list. To check eligibility,
    contact your TAM or visit the Trusted Advisor Priority section in the AWS console.

    **Requires management account or delegated administrator access.**

    ## Example
    ```
    list_organization_recommendations(status="warning", pillar="security")
    ```
    """
    try:
        recommendations = await ta_client.list_organization_recommendations(
            status=status,
            pillar=pillar,
            aws_service=aws_service,
            after_last_updated_at=after_last_updated_at,
        )
        return format_organization_recommendations(recommendations)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        if error_code == 'AccessDeniedException':
            return (
                'Access denied. The list_organization_recommendations tool requires '
                'management account or delegated administrator access in AWS Organizations. '
                f'Details: {error_message}'
            )
        logger.error(
            f'Error listing organization recommendations: {error_code} - {error_message}'
        )
        return f'Error listing organization recommendations: {error_code} - {error_message}'
    except Exception as e:
        logger.error(f'Unexpected error listing organization recommendations: {str(e)}')
        return f'Error listing organization recommendations: {str(e)}'


@mcp.tool(name='get_account_score')
async def get_account_score(ctx: Context) -> str:
    """Calculate an overall health score (0-100) for the AWS account based on Trusted Advisor checks.

    The score is calculated across all pillars (security, cost, performance, fault_tolerance,
    service_limits, operational_excellence). Each OK check contributes positively; warnings
    and errors reduce the score. Errors are weighted 3x more than warnings.

    For AWS Organizations management accounts, also returns per-pillar breakdown so you can
    see which area needs the most attention.

    ## Example
    ```
    get_account_score()
    ```
    """
    try:
        pillars = [
            'security', 'cost_optimizing', 'performance',
            'fault_tolerance', 'service_limits', 'operational_excellence'
        ]

        total_ok = 0
        total_warning = 0
        total_error = 0
        pillar_scores = {}

        # Fetch all pillar data in parallel (6 pillars × 3 statuses = 18 calls)
        tasks = []
        for pillar in pillars:
            for status in ('ok', 'warning', 'error'):
                tasks.append(ta_client.list_recommendations(pillar=pillar, status=status))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, pillar in enumerate(pillars):
            ok_result = results[i * 3]
            warning_result = results[i * 3 + 1]
            error_result = results[i * 3 + 2]

            if (
                isinstance(ok_result, Exception)
                or isinstance(warning_result, Exception)
                or isinstance(error_result, Exception)
            ):
                pillar_scores[pillar] = {'score': None, 'ok': 0, 'warning': 0, 'error': 0}
                continue

            ok = len(ok_result)
            warning = len(warning_result)
            error = len(error_result)
            total = ok + warning + error

            if total > 0:
                # Errors count 3x, warnings 1x
                penalty = (error * 3) + warning
                max_penalty = total * 3
                pillar_score = max(0, round(100 * (1 - penalty / max_penalty)))
            else:
                pillar_score = 100

            pillar_scores[pillar] = {
                'score': pillar_score,
                'ok': ok,
                'warning': warning,
                'error': error,
            }
            total_ok += ok
            total_warning += warning
            total_error += error

        total = total_ok + total_warning + total_error
        if total > 0:
            penalty = (total_error * 3) + total_warning
            max_penalty = total * 3
            overall_score = max(0, round(100 * (1 - penalty / max_penalty)))
        else:
            overall_score = 100

        # Build output
        grade = (
            'A' if overall_score >= 90 else
            'B' if overall_score >= 75 else
            'C' if overall_score >= 60 else
            'D' if overall_score >= 40 else 'F'
        )

        lines = [
            f'## AWS Trusted Advisor Account Score',
            f'',
            f'Overall Score: {overall_score}/100  (Grade: {grade})',
            f'',
            f'Total checks: {total}  |  ✅ OK: {total_ok}  |  ⚠️ Warning: {total_warning}  |  🔴 Error: {total_error}',
            f'',
            f'### Pillar Breakdown',
        ]

        pillar_labels = {
            'security': 'Security',
            'cost_optimizing': 'Cost Optimization',
            'performance': 'Performance',
            'fault_tolerance': 'Fault Tolerance',
            'service_limits': 'Service Limits',
            'operational_excellence': 'Operational Excellence',
        }

        for pillar, data in pillar_scores.items():
            label = pillar_labels.get(pillar, pillar)
            if data['score'] is None:
                lines.append(f'- {label}: N/A')
            else:
                bar = '█' * (data['score'] // 10) + '░' * (10 - data['score'] // 10)
                lines.append(
                    f'- {label}: {data["score"]}/100  [{bar}]  ',
                )
                lines.append(
                    f'  ✅ {data["ok"]}  ⚠️ {data["warning"]}  🔴 {data["error"]}',
                )

        lines.append('')
        if overall_score >= 90:
            lines.append('Your account is in great shape. Keep it up.')
        elif overall_score >= 75:
            lines.append('Good overall, but a few issues worth addressing.')
        elif overall_score >= 60:
            lines.append('Several findings need attention. Review warnings and errors.')
        else:
            lines.append('Significant issues detected. Prioritize error items immediately.')

        return chr(10).join(lines)

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f'Error calculating account score: {error_code} - {error_message}')
        return f'Error calculating account score: {error_code} - {error_message}'
    except Exception as e:
        logger.error(f'Unexpected error calculating account score: {str(e)}')
        return f'Error calculating account score: {str(e)}'

def main():
    """Run the MCP server."""
    logger.debug('Starting awslabs_trusted_advisor_mcp_server MCP server')
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
