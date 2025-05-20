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

"""AWS Support MCP Server implementation."""

import argparse
import os
import sys
from typing import Any, Dict, List, Optional, cast

from botocore.exceptions import ClientError
from fastmcp import Context, FastMCP
from loguru import logger
from pydantic import Field, ValidationError

from awslabs.aws_support_mcp_server.client import SupportClient
from awslabs.aws_support_mcp_server.consts import (
    DEFAULT_ISSUE_TYPE,
    DEFAULT_LANGUAGE,
    DEFAULT_REGION,
)
from awslabs.aws_support_mcp_server.errors import (
    handle_client_error,
    handle_general_error,
    handle_validation_error,
)
from awslabs.aws_support_mcp_server.debug_helper import diagnostics, track_performance, track_errors, track_request, get_diagnostics_report
from awslabs.aws_support_mcp_server.formatters import (
    format_cases,
    format_json_response,
    format_markdown_case_summary,
    format_markdown_services,
    format_markdown_severity_levels,
    format_services,
    format_severity_levels
)
from awslabs.aws_support_mcp_server.models import (
    CreateCaseRequest,
    CreateCaseResponse,
    DescribeCasesRequest,
    DescribeCasesResponse,
    AddCommunicationRequest,
    AddCommunicationResponse,
    ResolveCaseRequest,
    ResolveCaseResponse,
    AddCommunicationRequest,
    AddCommunicationResponse,
    CreateCaseRequest,
    CreateCaseResponse,
    DescribeCasesRequest,
    DescribeCasesResponse,
    ResolveCaseRequest,
    ResolveCaseResponse,
)


# Initialize the MCP server
mcp = FastMCP(
    "awslabs_support_mcp_server",
    instructions="""
    # AWS Support API MCP Server
    
    This MCP server provides tools for interacting with the AWS Support API, enabling AI assistants to create and manage support cases and check AWS service health on behalf of users.
    
    ## Available Tools
    
    ### create_support_case
    Create a new AWS Support case with specified subject, service code, category code, severity code, and communication body.
    
    **Example:**
    ```
    create_support_case(
        subject="EC2 instance not starting",
        service_code="amazon-elastic-compute-cloud-linux",
        category_code="using-aws",
        severity_code="urgent",
        communication_body="My EC2 instance i-1234567890abcdef0 is not starting."
    )
    ```
    
    ### describe_support_cases
    Retrieve information about existing support cases, with options to filter by case ID, date range, and include resolved cases.
    
    **Example:**
    ```
    describe_support_cases(
        include_resolved_cases=False,
        include_communications=True
    )
    ```
    
    ### add_communication_to_case
    Add a communication to an existing support case, providing updates or additional information.
    
    **Example:**
    ```
    add_communication_to_case(
        case_id="case-12345678910-2013-c4c1d2bf33c5cf47",
        communication_body="I've tried rebooting the instance but it's still not starting."
    )
    ```
    
    ### resolve_support_case
    Resolve an existing support case when the issue has been addressed.
    
    **Example:**
    ```
    resolve_support_case(
        case_id="case-12345678910-2013-c4c1d2bf33c5cf47"
    )
    ```

    ### describe_supported_languages
    Retrieve the list of supported languages for AWS Support cases. The server automatically detects the language
    of case content and uses it when appropriate.

    **Example:**
    ```python
    # Get list of supported languages
    describe_supported_languages()
    ```

    **Language Detection and Selection:**
    The server automatically detects the language of case content using the following process:
    1. Analyzes both subject and case body text
    2. Checks if detected language is supported for the specific:
       - Service code
       - Category code
       - Issue type
    3. Makes language selection:
       - If supported: Uses detected language
       - If not supported: Falls back to closest supported language or English

    **Example with Automatic Language Detection:**
    ```python
    # Server will detect language from content and use if supported
    create_support_case(
        subject="EC2インスタンスが起動しません",  # Japanese subject
        service_code="amazon-elastic-compute-cloud-linux",
        category_code="using-aws",
        severity_code="normal",
        communication_body="インスタンスID i-1234567890abcdef0 が起動しません。"  # Japanese body
    )
    # If Japanese is supported for EC2 technical cases, it will be used
    # If not, it will fall back to the default language (English)
    ```

    ### add_attachments_to_set
    Add one or more attachments to a new or existing attachment set. The attachment set can then be used when creating a case or adding communication to a case.
    
    **Example:**
    ```python
    # Add a single attachment to a new set
    add_attachments_to_set(
        attachments=[{
            "fileName": "error_log.txt",
            "data": "base64_encoded_content"  # Must be base64-encoded
        }]
    )

    # Add to existing set
    add_attachments_to_set(
        attachments=[{
            "fileName": "screenshot.png",
            "data": "base64_encoded_content"
        }],
        attachment_set_id="12345678-1234-1234-1234-123456789012"
    )

    
    ## Support Case Best Practices
    
    When creating a support case, consider the following best practices:
    1. Provide a clear and concise subject
    2. Include detailed information about the issue in the communication body
    3. Select the appropriate service, category, and severity level
    4. Include any relevant error messages or logs
    
    ## Additional Best Practices
    
    1. **Always check service and category codes**: Use the aws-services resource to get valid service and category codes before creating a case.
    2. **Choose the appropriate severity level**: Use the aws-severity-levels resource to understand the different severity levels and choose the appropriate one for the issue.
    3. **Provide detailed information**: Include relevant details in the communication body, such as resource IDs, error messages, and steps to reproduce the issue.
    4. **Check for existing cases**: Before creating a new case, check if there's an existing case for the same issue.    
    5. **Handle pagination**: When retrieving a large number of cases, use the next_token parameter to paginate through the results.    
    6. **Error handling**: Implement proper error handling to catch and handle exceptions from the AWS Support API.    
    7. **Rate limiting**: Be aware of API rate limits and implement exponential backoff and retry logic.

    ## Attachment Guidelines

    1. **File Size Limits**: Each attachment must be less than 5MB in size.
    2. **Attachment Set Expiry**: Attachment sets expire after 1 hour.
    3. **Base64 Encoding**: All attachment data must be base64-encoded.
    4. **Supported File Types**: Common file types like .txt, .log, .json, .yaml, .pdf, .png, .jpg.
    5. **Best Practices**:
       - Include relevant logs, configuration files, or screenshots
       - Use descriptive file names
       - Remove sensitive information before attaching
       - Consider compressing large text files
       - Verify file content is readable and not corrupted
       - Include context about what the attachment shows
       - Use attachment sets within their 1-hour expiry window
    """,
    dependencies=[
        "pydantic",
        "boto3"
    ],
)

# Initialize the AWS Support client
try:
    support_client = SupportClient(
        region_name=os.environ.get("AWS_REGION", DEFAULT_REGION),
        profile_name=os.environ.get("AWS_PROFILE"),
    )
except Exception as e:
    logger.error(f"Failed to initialize AWS Support client: {str(e)}")
    raise



@mcp.resource(uri="resource://diagnostics", name="Diagnostics", mime_type="application/json")
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
    if not report.get("diagnostics_enabled", False):
        return format_json_response({"error": "Diagnostics not enabled. Start server with --diagnostics flag."})
    return format_json_response(report)


@track_performance
@track_errors
@track_request("create_support_case")
@mcp.tool(name="create_support_case")
async def create_support_case(
        ctx: Context,
        subject: str = Field(
            ..., description="The subject of the support case"
        ),
        service_code: str = Field(
            ..., description="The code for the AWS service. Use describe_services get valid codes."
        ),
        category_code: str = Field(
            ..., description="The category code for the issue. Use describe_services to get valid codes."
        ),
        severity_code: str = Field(
            ..., description="The severity code for the issue. Use describe_severity_levels to get valid codes."
        ),
        communication_body: str = Field(
            ..., description="The initial communication for the case"
        ),
        cc_email_addresses: Optional[List[str]] = Field(
            None, description="Email addresses to CC on the case"
        ),
        language: str = Field(
            DEFAULT_LANGUAGE, description="The language of the case (ISO 639-1 code)"
        ),
        issue_type: str = Field(
            DEFAULT_ISSUE_TYPE, description="The type of issue: technical, account-and-billing, or service-limit"
        ),
        attachment_set_id: Optional[str] = Field(
            None, description="The ID of the attachment set"
        ),
) -> Dict[str, Any]:
    """Create a new AWS Support case.

    ## Usage Requirements
    - You must provide a clear subject and detailed communication body

    ## Example
    ```
    create_support_case(
        subject="EC2 instance not starting",
        service_code="amazon-elastic-compute-cloud-linux",
        category_code="using-aws",
        severity_code="urgent",
        communication_body="My EC2 instance i-1234567890abcdef0 is not starting."
    )
    ```

    ## Severity Level Guidelines
    - low (General guidance): You have a general development question or want to request a feature.
    - normal (System impaired): Non-critical functions are behaving abnormally or you have a time-sensitive development question.
    - high (Production system impaired): Important functions are impaired but a workaround exists.
    - urgent (Production system down): Your business is significantly impacted and no workaround exists.
    - critical (Business-critical system down): Your business is at risk and critical functions are unavailable.
    """
    try:
        # Create a request model
        request = CreateCaseRequest(
            subject=subject,
            service_code=service_code,
            category_code=category_code,
            severity_code=severity_code,
            communication_body=communication_body,
            cc_email_addresses=cc_email_addresses,
            language=language,
            issue_type=issue_type,
            attachment_set_id=attachment_set_id,
        )

        # Create the case
        logger.info(f"Creating support case: {subject}")
        response = await support_client.create_case(
            **request.to_api_params()
        )

        # Create a response model
        result = CreateCaseResponse(
            case_id=response["caseId"],
            status="success",
            message=f"Support case created successfully with ID: {response['caseId']}"
        )

        return result.model_dump()
    except ValidationError as e:
        return await handle_validation_error(ctx, e, "create_support_case")
    except ClientError as e:
        return await handle_client_error(ctx, e, "create_support_case")
    except Exception as e:
        return await handle_general_error(ctx, e, "create_support_case")


@track_performance
@track_errors
@track_request("describe_support_cases")
@mcp.tool(name="describe_support_cases")
async def describe_support_cases(
        ctx: Context,
        case_id_list: Optional[List[str]] = Field(
            None, description="List of case IDs to retrieve"
        ),
        display_id: Optional[str] = Field(
            None, description="The display ID of the case"
        ),
        after_time: Optional[str] = Field(
            None, description="The start date for a filtered date search (ISO 8601 format)"
        ),
        before_time: Optional[str] = Field(
            None, description="The end date for a filtered date search (ISO 8601 format)"
        ),
        include_resolved_cases: bool = Field(
            False, description="Include resolved cases in the results"
        ),
        include_communications: bool = Field(
            True, description="Include communications in the results"
        ),
        language: str = Field(
            DEFAULT_LANGUAGE, description="The language of the case (ISO 639-1 code)"
        ),
        max_results: Optional[int] = Field(
            None, description="The maximum number of results to return"
        ),
        next_token: Optional[str] = Field(
            None, description="A resumption point for pagination"
        ),
        format: str = Field(
            "json", description="The format of the response (json or markdown)"
        ),
) -> Dict[str, Any]:
    """Retrieve information about support cases.

    ## Usage
    - You can retrieve cases by ID, display ID, or date range
    - You can include or exclude resolved cases and communications
    - You can paginate through results using the next_token parameter

    ## Example
    ```
    describe_support_cases(
        case_id_list=["case-12345678910-2013-c4c1d2bf33c5cf47"],
        include_communications=True
    )
    ```

    ## Date Format
    Dates should be provided in ISO 8601 format (e.g., "2023-01-01T00:00:00Z")

    ## Response Format
    You can request the response in either JSON or Markdown format using the format parameter.
    """
    try:
        # Create a request model
        request = DescribeCasesRequest(
            case_id_list=case_id_list,
            display_id=display_id,
            after_time=after_time,
            before_time=before_time,
            include_resolved_cases=include_resolved_cases,
            include_communications=include_communications,
            language=language,
            max_results=max_results,
            next_token=next_token,
        )

        # Retrieve the cases
        logger.info("Retrieving support cases")
        response = await support_client.describe_cases(
            **request.to_api_params()
        )

        # Format the cases
        cases = format_cases(response.get("cases", []))

        # Create a response model
        result = DescribeCasesResponse(
            cases=cases,
            next_token=response.get("nextToken")
        )

        # Return the response in the requested format
        if format.lower() == "markdown" and cases:
            # For markdown format, return a summary of the first case
            return {"markdown": format_markdown_case_summary(cases[0])}
        else:
            return result.model_dump()
    except ValidationError as e:
        return await handle_validation_error(ctx, e, "describe_support_cases")
    except ClientError as e:
        return await handle_client_error(ctx, e, "describe_support_cases")
    except Exception as e:
        return await handle_general_error(ctx, e, "describe_support_cases")


@track_performance
@track_errors
@track_request("describe_severity_levels")
@mcp.tool(name="describe_severity_levels")
async def describe_severity_levels(
        ctx: Context,
        format: str = Field(
            "json",
            description="The format of the response in markdown or json"
        ),
) -> Dict[str, Any]:
    """Retrieve information about AWS Support severity levels. This tool provides details about the available severity levels for AWS Support cases, including their codes and descriptions.

    ## Usage
    - You can request the response in either JSON or Markdown format.
    - Use this information to determine the appropriate severity level for creating support cases.
    - Use this information when crafting queries for Describe Cases.

    ## Example
    ```
    # Get severity levels in JSON format
    describe_severity_levels()

    # Get severity levels in Markdown format
    describe_severity_levels(format="markdown")
    ```
    ## Severity Level Guidelines
    - low (General guidance): You have a general development question or want to request a feature
    - normal (System impaired): Non-critical functions are behaving abnormally
    - high (Production system impaired): Important functions are impaired but a workaround exists
    - urgent (Production system down): Your business is significantly impacted; no workaround exists
    - critical (Business-critical system down): Your business is at risk; critical functions unavailable

    """
    try:
        # Retrieve severity levels from the AWS Support API
        logger.debug("Retrieving AWS severity levels")
        response = await support_client.describe_severity_levels()

        # Format the severity levels data
        severity_levels = format_severity_levels(response.get("severityLevels", []))

        # Return the response in the requested format
        return {"markdown": format_markdown_severity_levels(severity_levels)} if format.lower() == "markdown" else severity_levels
    except ClientError as e:
        return await handle_client_error(ctx, e, "describe_severity_levels")
    except Exception as e:
        return await handle_general_error(ctx, e, "describe_severity_levels")



@track_performance
@track_errors
@track_request("add_communication_to_case")
@mcp.tool(name="add_communication_to_case")
async def add_communication_to_case(
        ctx: Context,
        case_id: str = Field(
            ..., description="The ID of the support case"
        ),
        communication_body: str = Field(
            ..., description="The text of the communication"
        ),
        cc_email_addresses: Optional[List[str]] = Field(
            None, description="Email addresses to CC on the communication"
        ),
        attachment_set_id: Optional[str] = Field(
            None, description="The ID of the attachment set"
        ),
) -> Dict[str, Any]:
    """Add communication to a support case.

    ## Usage
    - You must provide a valid case ID
    - You must provide a communication body
    - You can optionally CC email addresses on the communication
    - You can optionally attach files using an attachment set ID

    ## Example
    ```
    add_communication_to_case(
        case_id="case-12345678910-2013-c4c1d2bf33c5cf47",
        communication_body="Here is an update on my issue..."
    )
    ```
    """
    try:
        # Create a request model
        request = AddCommunicationRequest(
            case_id=case_id,
            communication_body=communication_body,
            cc_email_addresses=cc_email_addresses,
            attachment_set_id=attachment_set_id,
        )

        # Add the communication
        logger.info(f"Adding communication to support case: {case_id}")
        response = await support_client.add_communication_to_case(
            **request.to_api_params()
        )

        # Create a response model
        result = AddCommunicationResponse(
            result=response["result"],
            status="success",
            message=f"Communication added successfully to case: {case_id}"
        )

        return result.model_dump()
    except ValidationError as e:
        return await handle_validation_error(ctx, e, "add_communication_to_case")
    except ClientError as e:
        return await handle_client_error(ctx, e, "add_communication_to_case")
    except Exception as e:
        return await handle_general_error(ctx, e, "add_communication_to_case")


@track_performance
@track_errors
@track_request("resolve_support_case")
@mcp.tool(name="resolve_support_case")
async def resolve_support_case(
        ctx: Context,
        case_id: str = Field(
            ..., description="The ID of the support case"
        ),
) -> Dict[str, Any]:
    """Resolve a support case.

    ## Usage
    - You must provide a valid case ID
    - The case must be in an open state to be resolved

    ## Example
    ```
    resolve_support_case(
        case_id="case-12345678910-2013-c4c1d2bf33c5cf47"
    )
    ```
    """
    try:
        # Create a request model
        request = ResolveCaseRequest(
            case_id=case_id,
        )

        # Resolve the case
        logger.info(f"Resolving support case: {case_id}")
        response = await support_client.resolve_case(
            **request.to_api_params()
        )

        # Create a response model
        result = ResolveCaseResponse(
            initial_case_status=response["initialCaseStatus"],
            final_case_status=response["finalCaseStatus"],
            status="success",
            message=f"Support case resolved successfully: {case_id}"
        )

        return result.model_dump()
    except ValidationError as e:
        return await handle_validation_error(ctx, e, "resolve_support_case")
    except ClientError as e:
        return await handle_client_error(ctx, e, "resolve_support_case")
    except Exception as e:
        return await handle_general_error(ctx, e, "resolve_support_case")


@track_performance
@track_errors
@track_request("describe_services")
@mcp.tool(name="describe_services")
async def describe_services(
        ctx: Context,
        service_code_list: Optional[List[str]] = Field(
            None,
            description="Optional list of service codes to filter results"
        ),
        language: str = Field(
            DEFAULT_LANGUAGE,
            description="The language code (e.g., 'en' for English, 'ja' for Japanese)"
        ),
        format: str = Field(
            "json",
            description="The format of the response (json or markdown)"
        )
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
    describe_services(
        service_code_list=["amazon-elastic-compute-cloud-linux", "amazon-s3"]
    )

    # Get services in Japanese
    describe_services(language="ja")

    # Get services in Markdown format
    describe_services(format="markdown")
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
        logger.debug("Retrieving AWS services")
        response = await support_client.describe_services(
            language=language,
            service_code_list=service_code_list
        )

        # Format the services data
        services = format_services(response.get("services", []))

        # Return the response in the requested format
        return {"markdown": format_markdown_services(services)} if format.lower() == "markdown" else services
    except ClientError as e:
        return await handle_client_error(ctx, e, "describe_services")
    except Exception as e:
        return await handle_general_error(ctx, e, "describe_services")


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(description="AWS Support API MCP Server")
    parser.add_argument(
        "--log-file", type=str, help="Path to save the log file. If not provided with --debug, logs to stderr only"
    )
    parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    parser.add_argument(
        "--port", type=int, default=8888, help="Port to run the server on"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )

    args = parser.parse_args()

    # Configure logging based on debug flag
    # First remove default loggers
    logger.remove()

    # Set up console logging with appropriate level
    log_level = "DEBUG" if args.debug else "INFO"
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # Set up file logging if debug mode is enabled and log file path is provided
    if args.debug:
        # Configure enhanced logging format for debug mode
        diagnostics_format = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {thread}:{process} | {extra} - {message}"

        # Configure logger with extra diagnostic info
        logger.configure(extra={"diagnostics": True})

        # Enable diagnostics tracking
        diagnostics.enable()

        # Set up file logging if log file path is provided
        if args.log_file:
            log_file = os.path.abspath(args.log_file)
            # Create log directory if it doesn't exist
            log_dir = os.path.dirname(log_file)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                logger.info(f"Created log directory: {log_dir}")

            logger.add(
                log_file,
                level="DEBUG",
                rotation="10 MB",
                retention="1 week",
                format=diagnostics_format
            )
            logger.info(f"AWS Support MCP Server starting up. Log file: {log_file}")


    logger.info(f"Debug mode: {args.debug}")


    if args.debug:
        # Enable more detailed error tracking and performance monitoring
        logger.debug("Enabling detailed performance tracking and error monitoring")
        # Hook into FastMCP to track performance
        mcp.settings.debug = True
        # You could add more diagnostics setup here

    logger.debug('Starting awslabs_support_mcp_server MCP server')

    # Log the startup mode
    if args.sse:
        logger.info(f"Starting AWS Support MCP Server on 0.0.0.0:{args.port} with SSE transport")
        # Run with SSE transport
        mcp.settings.port = args.port
        mcp.run(transport="sse")
    else:
        logger.info("Starting AWS Support MCP Server with stdio transport")
        # Run with stdio transport
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
