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
"""AWS Support MCP Server implementation."""

import argparse
import os
import sys
from awslabs.aws_support_mcp_server.client import SupportClient
from awslabs.aws_support_mcp_server.consts import (
    DEFAULT_ISSUE_TYPE,
    DEFAULT_LANGUAGE,
    DEFAULT_REGION,
)
from awslabs.aws_support_mcp_server.debug_helper import (
    diagnostics,
    get_diagnostics_report,
    track_errors,
    track_performance,
    track_request,
)
from awslabs.aws_support_mcp_server.errors import (
    create_error_response,
    handle_client_error,
    handle_general_error,
    handle_validation_error,
)
from awslabs.aws_support_mcp_server.formatters import (
    format_cases,
    format_communications,
    format_json_response,
    format_markdown_case_summary,
    format_markdown_services,
    format_markdown_severity_levels,
    format_services,
    format_severity_levels,
)
from awslabs.aws_support_mcp_server.models import (
    AddAttachmentsToSetResponse,
    AddCommunicationResponse,
    CreateCaseResponse,
    DescribeCasesResponse,
    ResolveCaseResponse,
    SupportCase,
)
from botocore.exceptions import ClientError
from fastmcp import Context, FastMCP
from loguru import logger
from pydantic import Field, ValidationError
from typing import Any, Dict, List, Optional


# Initialize the MCP server
mcp = FastMCP(
    'awslabs_support_mcp_server',
    instructions="""
    # AWS Support API MCP Server

    This MCP server provides tools for interacting with the AWS Support API, enabling AI assistants to create and manage support cases on behalf of users.

    ## Common Service Codes (use with create_support_case)

    Use these codes directly — only call describe_services if the service isn't listed here or you need category codes.

    | Service | service_code | Common Categories |
    |---------|-------------|-------------------|
    | EC2 (Linux) | amazon-elastic-compute-cloud-linux | general-guidance, using-aws |
    | EC2 (Windows) | amazon-elastic-compute-cloud-windows | general-guidance, using-aws |
    | S3 | amazon-simple-storage-service | general-guidance, using-aws |
    | RDS | amazon-relational-database-service | general-guidance, using-aws |
    | Lambda | aws-lambda | general-guidance, using-aws |
    | ECS | ec2-container-service | general-guidance, using-aws |
    | EKS | amazon-elastic-kubernetes-service | general-guidance, using-aws |
    | DynamoDB | amazon-dynamodb | general-guidance, using-aws |
    | CloudFormation | aws-cloudformation | general-guidance, using-aws |
    | IAM | aws-identity-and-access-management | general-guidance, using-aws |
    | VPC | amazon-virtual-private-cloud | general-guidance, using-aws |
    | CloudWatch | amazon-cloudwatch | general-guidance, using-aws |
    | Route 53 | amazon-route53 | general-guidance, using-aws |
    | ELB | elastic-load-balancing | general-guidance, using-aws |
    | SQS | amazon-simple-queue-service | general-guidance, using-aws |
    | SNS | amazon-simple-notification-service | general-guidance, using-aws |
    | CloudFront | amazon-cloudfront | general-guidance, using-aws |
    | ElastiCache | amazon-elasticache | general-guidance, using-aws |
    | Bedrock | amazon-bedrock | general-guidance, using-aws |
    | SageMaker | amazon-sagemaker | general-guidance, using-aws |
    | Account | account | general-guidance, using-aws |
    | Billing | billing | general-guidance, using-aws |

    NOTE: Service codes are NOT intuitive (e.g., ECS is `ec2-container-service`, not `amazon-ecs`).
    When unsure, call describe_services to search.

    ## Severity Quick Reference

    | Code | Name | When to use |
    |------|------|-------------|
    | low | General guidance | Development question or feature request |
    | normal | System impaired | Non-critical functions behaving abnormally |
    | high | Production system impaired | Important functions impaired, workaround exists |
    | urgent | Production system down | Business significantly impacted, no workaround |
    | critical | Business-critical system down | Business at risk, critical functions unavailable |

    ## Recommended Workflow for Creating a Case

    1. Match the user's issue to a service_code from the table above (or call **describe_services**)
    2. (Optional) Call **describe_create_case_options** to check support hours and language availability
    3. Pick severity based on the quick reference above
    4. (Optional) **add_attachments_to_set** → upload files, get `attachmentSetId`
    5. **create_support_case** → create the case

    ## Recommended Workflow for Managing a Case

    1. **describe_support_cases** → list/search cases
    2. **describe_communications** → read full conversation history
    3. **describe_attachment** → download attachments referenced in communications
    4. **add_communication_to_case** → reply (optionally with attachments via add_attachments_to_set)
    5. **resolve_support_case** → close the case when done

    ## Available Tools (11)

    | Tool | Purpose |
    |------|---------|
    | create_support_case | Create a new support case |
    | describe_support_cases | List/search existing cases |
    | describe_communications | Get full communication history for a case |
    | add_communication_to_case | Reply to a case |
    | resolve_support_case | Close a case |
    | describe_services | List AWS services and category codes |
    | describe_severity_levels | List severity levels |
    | describe_create_case_options | Check support hours and language availability for a service |
    | describe_supported_languages | List supported languages for a service/category |
    | add_attachments_to_set | Upload files for attachment |
    | describe_attachment | Download an attachment by ID |

    ## Attachment Workflow

    1. Call **add_attachments_to_set** with base64-encoded file data → returns `attachmentSetId`
    2. Pass `attachmentSetId` to **create_support_case** or **add_communication_to_case**
    3. To retrieve attachments, use **describe_communications** to find attachment IDs, then **describe_attachment** to download

    ## Attachment Guidelines

    - Each attachment must be less than 5MB
    - Attachment sets expire after 1 hour
    - The `data` field must be the raw file contents encoded as base64 exactly ONCE
    - Do NOT double-encode — the AWS SDK handles wire-level base64 encoding automatically
    - The server will reject data that appears to be double-encoded
    - Remove sensitive information before attaching
    """,
)

# Initialize the AWS Support client
try:
    support_client = SupportClient(
        region_name=os.environ.get('AWS_REGION', DEFAULT_REGION),
        profile_name=os.environ.get('AWS_PROFILE'),
    )
except Exception as e:
    logger.error(f'Failed to initialize AWS Support client: {str(e)}')
    raise


@mcp.resource(uri='resource://diagnostics', name='Diagnostics', mime_type='application/json')
async def diagnostics_resource() -> str:
    """Get diagnostics information about the server.

    This resource returns information about server performance, errors, and request counts.
    It's only available when the server is started with the --diagnostics flag.

    ## Example response structure:
    ```json
    {
        "diagnostics_enabled": true,
        "performance": {
            "aws_services_resource": {
                "count": 5,
                "avg_time": 0.234,
                "min_time": 0.123,
                "max_time": 0.345
            }
        },
        "errors": {
            "ClientError": 2,
            "ValidationError": 1
        },
        "requests": {
            "aws_services": 5,
            "create_support_case": 3
        }
    }
    ```
    """
    report = get_diagnostics_report()
    if not report.get('diagnostics_enabled', False):
        return format_json_response(
            {'error': 'Diagnostics not enabled. Start server with --diagnostics flag.'}
        )
    return format_json_response(report)


async def _create_support_case_logic(
    ctx: Context,
    subject: str,
    service_code: str,
    category_code: str,
    severity_code: str,
    communication_body: str,
    cc_email_addresses: Optional[List[str]] = None,
    language: str = DEFAULT_LANGUAGE,
    issue_type: str = DEFAULT_ISSUE_TYPE,
    attachment_set_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Business logic for creating a new AWS Support case."""
    try:
        # Create the case
        logger.info(f'Creating support case: {subject}')
        response = await support_client.create_case(
            subject=subject,
            service_code=service_code,
            severity_code=severity_code,
            category_code=category_code,
            communication_body=communication_body,
            cc_email_addresses=cc_email_addresses,
            language=language,
            issue_type=issue_type,
            attachment_set_id=attachment_set_id if attachment_set_id else None,
        )

        # Create a response model
        result = CreateCaseResponse(
            caseId=response['caseId'],
            status='success',
            message=f'Support case created successfully with ID: {response["caseId"]}',
        )

        return result.model_dump(by_alias=True)
    except ValidationError as e:
        return await handle_validation_error(ctx, e, 'create_support_case')
    except ClientError as e:
        return await handle_client_error(ctx, e, 'create_support_case')
    except Exception as e:
        return await handle_general_error(ctx, e, 'create_support_case')


@mcp.tool(name='create_support_case')
@track_performance
@track_errors
@track_request('create_support_case')
async def create_support_case(
    ctx: Context,
    subject: str = Field(..., description='The subject of the support case'),
    service_code: str = Field(
        ..., description='The code for the AWS service. Use describe_services get valid codes.'
    ),
    category_code: str = Field(
        ...,
        description='The category code for the issue. Use describe_services to get valid codes.',
    ),
    severity_code: str = Field(
        ...,
        description='The severity code: low, normal, high, urgent, or critical',
    ),
    communication_body: str = Field(..., description='The initial communication for the case'),
    cc_email_addresses: Optional[List[str]] = Field(
        None, description='Email addresses to CC on the case'
    ),
    language: str = Field(
        DEFAULT_LANGUAGE, description='The language of the case (ISO 639-1 code)'
    ),
    issue_type: str = Field(
        DEFAULT_ISSUE_TYPE,
        description='The type of issue: technical, account-and-billing, or service-limit',
    ),
    attachment_set_id: Optional[str] = Field(None, description='The ID of the attachment set'),
) -> Dict[str, Any]:
    """Create a new AWS Support case.

    ## Prerequisites
    1. **describe_services** → get valid `service_code` and `category_code` values
    2. (Optional) **describe_create_case_options** → check support hours and language availability
    3. (Optional) **describe_supported_languages** → check if your preferred language is supported

    Severity codes are: low, normal, high, urgent, critical. Pick based on impact — no need to call describe_severity_levels.

    ## Attaching files
    Call **add_attachments_to_set** first to upload files, then pass the returned
    `attachmentSetId` as the `attachment_set_id` parameter here.

    ## Example
    ```
    create_support_case(
        subject='EC2 instance not starting',
        service_code='amazon-elastic-compute-cloud-linux',
        category_code='using-aws',
        severity_code='urgent',
        communication_body='My EC2 instance i-1234567890abcdef0 is not starting.',
    )
    ```

    ## Severity Level Guidelines
    - low (General guidance): You have a general development question or want to request a feature.
    - normal (System impaired): Non-critical functions are behaving abnormally or you have a time-sensitive development question.
    - high (Production system impaired): Important functions are impaired but a workaround exists.
    - urgent (Production system down): Your business is significantly impacted and no workaround exists.
    - critical (Business-critical system down): Your business is at risk and critical functions are unavailable.
    """
    return await _create_support_case_logic(
        ctx,
        subject,
        service_code,
        category_code,
        severity_code,
        communication_body,
        cc_email_addresses,
        language,
        issue_type,
        attachment_set_id,
    )


async def _describe_support_cases_logic(
    ctx: Context,
    case_id_list: Optional[List[str]] = None,
    display_id: Optional[str] = None,
    after_time: Optional[str] = None,
    before_time: Optional[str] = None,
    include_resolved_cases: bool = False,
    include_communications: bool = True,
    language: str = DEFAULT_LANGUAGE,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    format: str = 'json',
) -> Dict[str, Any]:
    """Business logic for retrieving information about support cases."""
    try:
        # Retrieve the cases
        logger.info('Retrieving support cases')
        response = await support_client.describe_cases(
            case_id_list=case_id_list,
            display_id=display_id,
            after_time=after_time,
            before_time=before_time,
            include_resolved_cases=include_resolved_cases,
            include_communications=include_communications,
            language=language,
            next_token=next_token if next_token else None,
        )

        # Format the cases
        cases = format_cases(response.get('cases', []))

        # Create a response model
        result = DescribeCasesResponse(
            cases=[SupportCase(**case) for case in cases], nextToken=response.get('nextToken')
        )

        # Return the response in the requested format
        if format.lower() == 'markdown' and cases:
            # For markdown format, return a summary of the first case
            return {'markdown': format_markdown_case_summary(cases[0])}
        else:
            return result.model_dump()
    except ValidationError as e:
        return await handle_validation_error(ctx, e, 'describe_support_cases')
    except ClientError as e:
        return await handle_client_error(ctx, e, 'describe_support_cases')
    except Exception as e:
        return await handle_general_error(ctx, e, 'describe_support_cases')


@mcp.tool(name='describe_support_cases')
@track_performance
@track_errors
@track_request('describe_support_cases')
async def describe_support_cases(
    ctx: Context,
    case_id_list: Optional[List[str]] = Field(None, description='List of case IDs to retrieve'),
    display_id: Optional[str] = Field(None, description='The display ID of the case'),
    after_time: Optional[str] = Field(
        None, description='The start date for a filtered date search (ISO 8601 format)'
    ),
    before_time: Optional[str] = Field(
        None, description='The end date for a filtered date search (ISO 8601 format)'
    ),
    include_resolved_cases: bool = Field(
        False, description='Include resolved cases in the results'
    ),
    include_communications: bool = Field(
        True, description='Include communications in the results'
    ),
    language: str = Field(
        DEFAULT_LANGUAGE, description='The language of the case (ISO 639-1 code)'
    ),
    max_results: Optional[int] = Field(
        None, description='The maximum number of results to return'
    ),
    next_token: Optional[str] = Field(None, description='A resumption point for pagination'),
    format: str = Field('json', description='The format of the response (json or markdown)'),
) -> Dict[str, Any]:
    """Retrieve information about support cases.

    ## Usage
    - You can retrieve cases by ID, display ID, or date range
    - You can include or exclude resolved cases and communications
    - You can paginate through results using the next_token parameter
    - Use **describe_communications** to get the full communication history for a case

    ## Example
    ```
    describe_support_cases(
        case_id_list=['case-12345678910-2013-c4c1d2bf33c5cf47'], include_communications=True
    )
    ```

    ## Date Format
    Dates should be provided in ISO 8601 format (e.g., "2023-01-01T00:00:00Z")

    ## Response Format
    You can request the response in either JSON or Markdown format using the format parameter.
    """
    return await _describe_support_cases_logic(
        ctx,
        case_id_list,
        display_id,
        after_time,
        before_time,
        include_resolved_cases,
        include_communications,
        language,
        max_results,
        next_token,
        format,
    )


@mcp.tool(name='describe_severity_levels')
@track_performance
@track_errors
@track_request('describe_severity_levels')
async def describe_severity_levels(
    ctx: Context,
    language: str = Field(DEFAULT_LANGUAGE, description="The language code (e.g., 'en', 'ja')"),
    format: str = Field('json', description='The format of the response in markdown or json'),
) -> Dict[str, Any]:
    """Retrieve information about AWS Support severity levels. This tool provides details about the available severity levels for AWS Support cases, including their codes and descriptions.

    ## Usage
    - You can request the response in either JSON or Markdown format.
    - Use this information to determine the appropriate severity level for creating support cases.

    ## Example
    ```
    describe_severity_levels()
    describe_severity_levels(language='ja', format='markdown')
    ```
    ## Severity Level Guidelines
    - low (General guidance): You have a general development question or want to request a feature
    - normal (System impaired): Non-critical functions are behaving abnormally
    - high (Production system impaired): Important functions are impaired but a workaround exists
    - urgent (Production system down): Your business is significantly impacted; no workaround exists
    - critical (Business-critical system down): Your business is at risk; critical functions unavailable

    """
    try:
        logger.debug('Retrieving AWS severity levels')
        response = await support_client.describe_severity_levels(language=language)

        severity_levels = format_severity_levels(response.get('severityLevels', []))

        return (
            {'markdown': format_markdown_severity_levels(severity_levels)}
            if format.lower() == 'markdown'
            else severity_levels
        )
    except ClientError as e:
        return await handle_client_error(ctx, e, 'describe_severity_levels')
    except Exception as e:
        return await handle_general_error(ctx, e, 'describe_severity_levels')


async def _add_communication_to_case_logic(
    ctx: Context,
    case_id: str,
    communication_body: str,
    cc_email_addresses: Optional[List[str]] = None,
    attachment_set_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Business logic for adding communication to a support case."""
    try:
        # Add the communication
        logger.info(f'Adding communication to support case: {case_id}')
        response = await support_client.add_communication_to_case(
            case_id=case_id,
            communication_body=communication_body,
            cc_email_addresses=cc_email_addresses,
            attachment_set_id=attachment_set_id,
        )

        # Create a response model
        result = AddCommunicationResponse(
            result=response['result'],
            status='success',
            message=f'Communication added successfully to case: {case_id}',
        )

        return result.model_dump()
    except ValidationError as e:
        return await handle_validation_error(ctx, e, 'add_communication_to_case')
    except ClientError as e:
        return await handle_client_error(ctx, e, 'add_communication_to_case')
    except Exception as e:
        return await handle_general_error(ctx, e, 'add_communication_to_case')


@mcp.tool(name='add_communication_to_case')
@track_performance
@track_errors
@track_request('add_communication_to_case')
async def add_communication_to_case(
    ctx: Context,
    case_id: str = Field(..., description='The ID of the support case'),
    communication_body: str = Field(..., description='The text of the communication'),
    cc_email_addresses: Optional[List[str]] = Field(
        None, description='Email addresses to CC on the communication'
    ),
    attachment_set_id: Optional[str] = Field(None, description='The ID of the attachment set'),
) -> Dict[str, Any]:
    """Add communication to a support case.

    ## Usage
    - You must provide a valid case ID
    - You must provide a communication body
    - You can optionally CC email addresses on the communication

    ## Attaching files
    Call **add_attachments_to_set** first to upload files, then pass the returned
    `attachmentSetId` as the `attachment_set_id` parameter here.

    ## Example
    ```
    add_communication_to_case(
        case_id='case-12345678910-2013-c4c1d2bf33c5cf47',
        communication_body='Here is an update on my issue...',
    )
    ```
    """
    return await _add_communication_to_case_logic(
        ctx, case_id, communication_body, cc_email_addresses, attachment_set_id
    )


async def _resolve_support_case_logic(
    ctx: Context,
    case_id: str,
) -> Dict[str, Any]:
    """Business logic for resolving a support case."""
    try:
        # Resolve the case
        logger.info(f'Resolving support case: {case_id}')
        response = await support_client.resolve_case(case_id=case_id)

        # Create a response model
        result = ResolveCaseResponse(
            initialCaseStatus=response['initialCaseStatus'],
            finalCaseStatus=response['finalCaseStatus'],
            status='success',
            message=f'Support case resolved successfully: {case_id}',
        )

        return result.model_dump(by_alias=True)
    except ValidationError as e:
        return await handle_validation_error(ctx, e, 'resolve_support_case')
    except ClientError as e:
        return await handle_client_error(ctx, e, 'resolve_support_case')
    except Exception as e:
        return await handle_general_error(ctx, e, 'resolve_support_case')


@mcp.tool(name='resolve_support_case')
@track_performance
@track_errors
@track_request('resolve_support_case')
async def resolve_support_case(
    ctx: Context,
    case_id: str = Field(..., description='The ID of the support case'),
) -> Dict[str, Any]:
    """Resolve a support case.

    ## Usage
    - You must provide a valid case ID
    - The case must be in an open state to be resolved

    ## Example
    ```
    resolve_support_case(case_id='case-12345678910-2013-c4c1d2bf33c5cf47')
    ```
    """
    return await _resolve_support_case_logic(ctx, case_id)


@mcp.tool(name='describe_services')
@track_performance
@track_errors
@track_request('describe_services')
async def describe_services(
    ctx: Context,
    service_code_list: Optional[List[str]] = Field(
        None, description='Optional list of service codes to filter results'
    ),
    language: str = Field(
        DEFAULT_LANGUAGE,
        description="The language code (e.g., 'en' for English, 'ja' for Japanese)",
    ),
    format: str = Field('json', description='The format of the response (json or markdown)'),
) -> Dict[str, Any]:
    """Retrieve information about AWS services available for support cases.

    This tool provides details about AWS services, including their service codes,
    names, and categories. Use this information when creating support cases to
    ensure you're using valid service and category codes.

    ## Usage
    - You can optionally filter results by providing specific service codes
    - You can specify the language for the response
    - You can request the response in either JSON or Markdown format

    ## Example
    ```python
    # Get all services
    describe_services()

    # Get specific services
    describe_services(service_code_list=['amazon-elastic-compute-cloud-linux', 'amazon-s3'])

    # Get services in Japanese
    describe_services(language='ja')

    # Get services in Markdown format
    describe_services(format='markdown')
    ```

    ## Response Format
    The JSON response includes service codes, names, and their categories:
    ```json
    {
        "amazon-elastic-compute-cloud-linux": {
            "name": "Amazon Elastic Compute Cloud (Linux)",
            "categories": [
                {"code": "using-aws", "name": "Using AWS"}
            ]
        }
    }
    ```
    """
    try:
        # Retrieve services from the AWS Support API
        logger.debug('Retrieving AWS services')
        response = await support_client.describe_services(
            language=language, service_code_list=service_code_list
        )

        # Format the services data
        services = format_services(response.get('services', []))

        # Return the response in the requested format
        return (
            {'markdown': format_markdown_services(services)}
            if format.lower() == 'markdown'
            else services
        )
    except ClientError as e:
        return await handle_client_error(ctx, e, 'describe_services')
    except Exception as e:
        return await handle_general_error(ctx, e, 'describe_services')


# --- describe_communications ---


async def _describe_communications_logic(
    ctx: Context,
    case_id: str,
    after_time: Optional[str] = None,
    before_time: Optional[str] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Business logic for describing communications."""
    try:
        logger.info(f'Describing communications for case: {case_id}')
        response = await support_client.describe_communications(
            case_id=case_id,
            after_time=after_time,
            before_time=before_time,
            max_results=max_results,
            next_token=next_token,
        )
        return format_communications(response)
    except ClientError as e:
        return await handle_client_error(ctx, e, 'describe_communications')
    except Exception as e:
        return await handle_general_error(ctx, e, 'describe_communications')


@mcp.tool(name='describe_communications')
@track_performance
@track_errors
@track_request('describe_communications')
async def describe_communications(
    ctx: Context,
    case_id: str = Field(..., description='The ID of the support case'),
    after_time: Optional[str] = Field(None, description='Start date filter (ISO 8601 format)'),
    before_time: Optional[str] = Field(None, description='End date filter (ISO 8601 format)'),
    max_results: Optional[int] = Field(
        None, description='Maximum number of results to return (max 100)'
    ),
    next_token: Optional[str] = Field(None, description='Pagination token'),
) -> Dict[str, Any]:
    """Retrieve communications for a support case.

    ## Usage
    - Provide a case ID to get all communications for that case
    - Use date filters and pagination for large result sets
    - Communications may include attachment IDs — use **describe_attachment** to download them

    ## Example
    ```
    describe_communications(case_id='case-12345678910-2013-c4c1d2bf33c5cf47')
    ```
    """
    return await _describe_communications_logic(
        ctx, case_id, after_time, before_time, max_results, next_token
    )


# --- describe_supported_languages ---


async def _describe_supported_languages_logic(
    ctx: Context,
    service_code: str,
    category_code: str,
    issue_type: str = 'technical',
) -> Dict[str, Any]:
    """Business logic for describing supported languages."""
    try:
        logger.info(f'Describing supported languages for service: {service_code}')
        response = await support_client.describe_supported_languages(
            service_code=service_code,
            category_code=category_code,
            issue_type=issue_type,
        )
        return {'supportedLanguages': response.get('supportedLanguages', [])}
    except ClientError as e:
        return await handle_client_error(ctx, e, 'describe_supported_languages')
    except Exception as e:
        return await handle_general_error(ctx, e, 'describe_supported_languages')


@mcp.tool(name='describe_supported_languages')
@track_performance
@track_errors
@track_request('describe_supported_languages')
async def describe_supported_languages(
    ctx: Context,
    service_code: str = Field(..., description='The code for the AWS service'),
    category_code: str = Field(..., description='The category code for the issue'),
    issue_type: str = Field(
        'technical', description='The issue type: technical or customer-service'
    ),
) -> Dict[str, Any]:
    """Retrieve supported languages for a specific service and category.

    Returns a list of languages with their ISO 639-1 code and display name.
    Language support varies by service, category, and issue type.

    ## Usage
    - Call before creating a case in a non-English language to verify support
    - Requires service_code and category_code (get these from describe_services)

    ## Example
    ```
    describe_supported_languages(
        service_code='ec2-container-service',
        category_code='general-guidance',
        issue_type='technical',
    )
    ```
    """
    return await _describe_supported_languages_logic(ctx, service_code, category_code, issue_type)


# --- describe_create_case_options ---


async def _describe_create_case_options_logic(
    ctx: Context,
    service_code: str,
    language: str = DEFAULT_LANGUAGE,
    category_code: Optional[str] = None,
    issue_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Business logic for describing create case options."""
    try:
        logger.info(f'Describing create case options for service: {service_code}')
        response = await support_client.describe_create_case_options(
            service_code=service_code,
            language=language,
            category_code=category_code,
            issue_type=issue_type,
        )
        return {
            'communicationTypes': response.get('communicationTypes', []),
            'languageAvailability': response.get('languageAvailability', ''),
        }
    except ClientError as e:
        return await handle_client_error(ctx, e, 'describe_create_case_options')
    except Exception as e:
        return await handle_general_error(ctx, e, 'describe_create_case_options')


@mcp.tool(name='describe_create_case_options')
@track_performance
@track_errors
@track_request('describe_create_case_options')
async def describe_create_case_options(
    ctx: Context,
    service_code: str = Field(..., description='The code for the AWS service'),
    language: str = Field(DEFAULT_LANGUAGE, description='The language code (ISO 639-1)'),
    category_code: Optional[str] = Field(None, description='The category code for the issue'),
    issue_type: Optional[str] = Field(
        None, description='The issue type: technical or customer-service'
    ),
) -> Dict[str, Any]:
    """Retrieve supported hours and language availability for a service.

    Returns communication types (e.g., chat, phone, web) with their supported
    hours and any dates without support, plus language availability status.

    ## Usage
    - Check what support channels and hours are available before creating a case
    - languageAvailability will be: available, best_effort, or unavailable

    ## Example
    ```
    describe_create_case_options(service_code='ec2-container-service')
    ```
    """
    return await _describe_create_case_options_logic(
        ctx, service_code, language, category_code, issue_type
    )


# --- add_attachments_to_set ---


async def _add_attachments_to_set_logic(
    ctx: Context,
    attachments: List[Dict[str, str]],
    attachment_set_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Business logic for adding attachments to a set."""
    try:
        logger.info(f'Adding {len(attachments)} attachments to set')
        response = await support_client.add_attachments_to_set(
            attachments=attachments,
            attachment_set_id=attachment_set_id,
        )
        result = AddAttachmentsToSetResponse(
            attachmentSetId=response['attachmentSetId'],
            expiryTime=response['expiryTime'],
            status='success',
            message=f'Attachments added to set: {response["attachmentSetId"]}',
        )
        return result.model_dump(by_alias=True)
    except ValidationError as e:
        return await handle_validation_error(ctx, e, 'add_attachments_to_set')
    except ValueError as e:
        logger.error(f'Attachment validation error: {e}')
        await ctx.error(str(e))
        return create_error_response(str(e), status_code=400)
    except ClientError as e:
        return await handle_client_error(ctx, e, 'add_attachments_to_set')
    except Exception as e:
        return await handle_general_error(ctx, e, 'add_attachments_to_set')


@mcp.tool(name='add_attachments_to_set')
@track_performance
@track_errors
@track_request('add_attachments_to_set')
async def add_attachments_to_set(
    ctx: Context,
    attachments: List[Dict[str, str]] = Field(
        ...,
        description='List of attachments. Each must have "fileName" and "data" (base64-encoded).',
    ),
    attachment_set_id: Optional[str] = Field(
        None, description='Existing attachment set ID to append to. Omit to create a new set.'
    ),
) -> Dict[str, Any]:
    """Add attachments to a new or existing attachment set.

    ## Usage
    - Use before create_support_case or add_communication_to_case
    - Pass the returned attachmentSetId to those tools
    - Attachment sets expire after 1 hour; each file must be < 5MB
    - The `data` field must be the file contents as a base64-encoded string
    - The server decodes it to raw bytes before sending to AWS (the SDK handles wire encoding)
    - Do NOT double-encode: encode the raw file bytes to base64 exactly once

    ## Example
    ```
    add_attachments_to_set(
        attachments=[{'fileName': 'error.log', 'data': '<base64-encoded-file-contents>'}]
    )
    ```
    """
    return await _add_attachments_to_set_logic(ctx, attachments, attachment_set_id)


# --- describe_attachment ---


async def _describe_attachment_logic(
    ctx: Context,
    attachment_id: str,
) -> Dict[str, Any]:
    """Business logic for describing an attachment."""
    try:
        logger.info(f'Describing attachment: {attachment_id}')
        response = await support_client.describe_attachment(attachment_id=attachment_id)
        return {
            'attachment': response.get('attachment', {}),
        }
    except ClientError as e:
        return await handle_client_error(ctx, e, 'describe_attachment')
    except Exception as e:
        return await handle_general_error(ctx, e, 'describe_attachment')


@mcp.tool(name='describe_attachment')
@track_performance
@track_errors
@track_request('describe_attachment')
async def describe_attachment(
    ctx: Context,
    attachment_id: str = Field(
        ..., description='The ID of the attachment. Get IDs from describe_communications.'
    ),
) -> Dict[str, Any]:
    """Retrieve an attachment by ID.

    ## Usage
    - Get attachment IDs from describe_communications results
    - Returns the file name and base64-encoded content

    ## Example
    ```
    describe_attachment(attachment_id='attachment-id-from-communications')
    ```
    """
    return await _describe_attachment_logic(ctx, attachment_id)


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(description='AWS Support API MCP Server')
    parser.add_argument(
        '--log-file',
        type=str,
        help='Path to save the log file. If not provided with --debug, logs to stderr only',
    )
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    # Configure logging based on debug flag
    # First remove default loggers
    logger.remove()

    # Set up console logging with appropriate level
    log_level = 'DEBUG' if args.debug else 'INFO'
    logger.add(
        sys.stderr,
        level=log_level,
        format='<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
    )

    # Set up file logging if debug mode is enabled and log file path is provided
    if args.debug:
        # Configure enhanced logging format for debug mode
        diagnostics_format = '{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {thread}:{process} | {extra} - {message}'

        # Configure logger with extra diagnostic info
        logger.configure(extra={'diagnostics': True})

        # Enable diagnostics tracking
        diagnostics.enable()

        # Set up file logging if log file path is provided
        if args.log_file:
            log_file = os.path.abspath(args.log_file)
            # Create log directory if it doesn't exist
            log_dir = os.path.dirname(log_file)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                logger.info(f'Created log directory: {log_dir}')

            logger.add(
                log_file,
                level='DEBUG',
                rotation='10 MB',
                retention='1 week',
                format=diagnostics_format,
            )
            logger.info(f'AWS Support MCP Server starting up. Log file: {log_file}')

    logger.info(f'Debug mode: {args.debug}')

    if args.debug:
        # Enable more detailed error tracking and performance monitoring
        logger.debug('Enabling detailed performance tracking and error monitoring')
        # Hook into FastMCP debug mode where supported (API changed in v3).
        settings_obj: Any = getattr(mcp, 'settings', None)
        if settings_obj is not None and hasattr(settings_obj, 'debug'):
            setattr(settings_obj, 'debug', True)
        elif hasattr(mcp, 'debug'):
            setattr(mcp, 'debug', True)
        else:
            logger.debug('FastMCP debug setting not available on this version')
        # You could add more diagnostics setup here

    logger.debug('Starting awslabs_support_mcp_server MCP server')

    # Log the startup mode
    logger.info('Starting AWS Support MCP Server with stdio transport')
    # Run with stdio transport
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
