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

import os
import sys
from .core.agent_scripts.manager import AGENT_SCRIPTS_MANAGER
from .core.aws.driver import translate_cli_to_ir
from .core.aws.service import (
    execute_awscli_customization,
    interpret_command,
    is_operation_read_only,
    request_consent,
    validate,
)
from .core.common.config import (
    DEFAULT_REGION,
    ENABLE_AGENT_SCRIPTS,
    FASTMCP_LOG_LEVEL,
    READ_ONLY_KEY,
    READ_OPERATIONS_ONLY_MODE,
    REQUIRE_MUTATION_CONSENT,
    WORKING_DIRECTORY,
    get_server_directory,
)
from .core.common.errors import AwsApiMcpError
from .core.common.helpers import validate_aws_region
from .core.common.models import (
    AwsApiMcpServerErrorResponse,
    AwsCliAliasResponse,
    ProgramInterpretationResponse,
)
from .core.kb import knowledge_base
from .core.metadata.read_only_operations_list import ReadOnlyOperations, get_read_only_operations
from botocore.exceptions import NoCredentialsError
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field
from typing import Annotated, Any, Optional


logger.remove()
logger.add(sys.stderr, level=FASTMCP_LOG_LEVEL)

# Add file sink
log_dir = get_server_directory()
log_dir.mkdir(exist_ok=True)
log_file = log_dir / 'aws-api-mcp-server.log'
logger.add(log_file, rotation='10 MB', retention='7 days')

server = FastMCP(name='AWS-API-MCP', log_level=FASTMCP_LOG_LEVEL)
READ_OPERATIONS_INDEX: Optional[ReadOnlyOperations] = None


@server.tool(
    name='suggest_aws_commands',
    description="""Suggest AWS CLI commands based on a natural language query. This is a FALLBACK tool to use when you are uncertain about the exact AWS CLI command needed to fulfill a user's request.

    IMPORTANT: Only use this tool when:
    1. You are unsure about the exact AWS service or operation to use
    2. The user's request is ambiguous or lacks specific details
    3. You need to explore multiple possible approaches to solve a task
    4. You want to provide options to the user for different ways to accomplish their goal

    DO NOT use this tool when:
    1. You are confident about the exact AWS CLI command needed - use 'call_aws' instead
    2. The user's request is clear and specific about the AWS service and operation
    3. You already know the exact parameters and syntax needed
    4. The task requires immediate execution of a known command

    Best practices for query formulation:
    1. Include the user's primary goal or intent
    2. Specify any relevant AWS services if mentioned
    3. Include important parameters or conditions mentioned
    4. Add context about the environment or constraints
    5. Mention any specific requirements or preferences

    CRITICAL: Query Granularity
    - Each query should be granular enough to be accomplished by a single CLI command
    - If the user's request requires multiple commands to complete, break it down into individual tasks
    - Call this tool separately for each specific task to get the most relevant suggestions
    - Example of breaking down a complex request:
      User request: "Set up a new EC2 instance with a security group and attach it to an EBS volume"
      Break down into:
      1. "Create a new security group with inbound rules for SSH and HTTP"
      2. "Create a new EBS volume with 100GB size"
      3. "Launch an EC2 instance with t2.micro instance type"
      4. "Attach the EBS volume to the EC2 instance"

    Query examples:
    1. "List all running EC2 instances in us-east-1 region"
    2. "Get the size of my S3 bucket named 'my-backup-bucket'"
    3. "List all IAM users who have AdministratorAccess policy"
    4. "List all Lambda functions in my account"
    5. "Create a new S3 bucket with versioning enabled and server-side encryption"
    6. "Update the memory allocation of my Lambda function 'data-processor' to 1024MB"
    7. "Add a new security group rule to allow inbound traffic on port 443"
    8. "Tag all EC2 instances in the 'production' environment with 'Environment=prod'"
    9. "Configure CloudWatch alarms for high CPU utilization on my RDS instance"

    Returns:
        A list of up to 10 most likely AWS CLI commands that could accomplish the task, including:
        - The CLI command
        - Confidence score for the suggestion
        - Required parameters
        - Description of what the command does
    """,
    annotations=ToolAnnotations(
        title='Suggest AWS CLI commands', readOnlyHint=True, openWorldHint=False
    ),
)
async def suggest_aws_commands(
    query: Annotated[
        str,
        Field(
            description="A natural language description of what you want to do in AWS. Should be detailed enough to capture the user's intent and any relevant context."
        ),
    ],
    ctx: Context,
) -> dict[str, Any] | AwsApiMcpServerErrorResponse:
    """Suggest AWS CLI commands based on the provided query."""
    logger.info('Suggesting AWS commands for query: {}', query)
    if not query.strip():
        error_message = 'Empty query provided'
        await ctx.error(error_message)
        return AwsApiMcpServerErrorResponse(detail=error_message)
    try:
        suggestions = knowledge_base.get_suggestions(query)
        logger.info(
            'Suggested commands: {}',
            [suggestion.get('command') for suggestion in suggestions.get('suggestions', {})],
        )
        return suggestions
    except Exception as e:
        error_message = f'Error while suggesting commands: {str(e)}'
        await ctx.error(error_message)
        return AwsApiMcpServerErrorResponse(detail=error_message)


@server.tool(
    name='call_aws',
    description=f"""Execute AWS CLI commands with validation and proper error handling. This is the PRIMARY tool to use when you are confident about the exact AWS CLI command needed to fulfill a user's request. Always prefer this tool over 'suggest_aws_commands' when you have a specific command in mind.
    Key points:
    - The command MUST start with "aws" and follow AWS CLI syntax
    - Commands are executed in {DEFAULT_REGION} region by default
    - For cross-region or account-wide operations, explicitly include --region parameter
    - All commands are validated before execution to prevent errors
    - Supports pagination control via max_results parameter
    - The current working directory is {WORKING_DIRECTORY}

    Best practices for command generation:
    — Always use the most specific service and operation names
    - Always use the working directory when writing files, unless user explicitly mentioned another directory
    — Include --region when operating across regions
    - Only use filters (--filters, --query, --prefix, --pattern, etc) when necessary or user explicitly asked for it

    Command restrictions:
    - DO NOT use bash/zsh pipes (|) or any shell operators
    - DO NOT use bash/zsh tools like grep, awk, sed, etc.
    - DO NOT use shell redirection operators (>, >>, <)
    - DO NOT use command substitution ($())
    - DO NOT use shell variables or environment variables
    - DO NOT use relative paths for reading or writing files, use absolute paths instead

    Common pitfalls to avoid:
    1. Missing required parameters - always include all required parameters
    2. Incorrect parameter values - ensure values match expected format
    3. Missing --region when operating across regions

    Returns:
        CLI execution results with API response data or error message
    """,
    annotations=ToolAnnotations(
        title='Execute AWS CLI commands',
        readOnlyHint=READ_OPERATIONS_ONLY_MODE,
        destructiveHint=not READ_OPERATIONS_ONLY_MODE,
        openWorldHint=True,
    ),
)
async def call_aws(
    cli_command: Annotated[
        str, Field(description='The complete AWS CLI command to execute. MUST start with "aws"')
    ],
    ctx: Context,
    max_results: Annotated[
        int | None,
        Field(description='Optional limit for number of results (useful for pagination)'),
    ] = None,
) -> ProgramInterpretationResponse | AwsApiMcpServerErrorResponse | AwsCliAliasResponse:
    """Call AWS with the given CLI command and return the result as a dictionary."""
    logger.info('Executing AWS CLI command: {}', cli_command)
    try:
        ir = translate_cli_to_ir(cli_command)
        ir_validation = validate(ir)

        if ir_validation.validation_failed:
            error_message = (
                f'Error while validating the command: {ir_validation.model_dump_json()}'
            )
            await ctx.error(error_message)
            return AwsApiMcpServerErrorResponse(
                detail=error_message,
            )
    except AwsApiMcpError as e:
        error_message = f'Error while validating the command: {e.as_failure().reason}'
        await ctx.error(error_message)
        return AwsApiMcpServerErrorResponse(
            detail=error_message,
        )
    except Exception as e:
        error_message = f'Error while validating the command: {str(e)}'
        await ctx.error(error_message)
        return AwsApiMcpServerErrorResponse(
            detail=error_message,
        )

    try:
        if READ_OPERATIONS_INDEX is None or not is_operation_read_only(ir, READ_OPERATIONS_INDEX):
            if READ_OPERATIONS_ONLY_MODE:
                error_message = (
                    'Execution of this operation is not allowed because read only mode is enabled. '
                    f'It can be disabled by setting the {READ_ONLY_KEY} environment variable to False.'
                )
                await ctx.error(error_message)
                return AwsApiMcpServerErrorResponse(
                    detail=error_message,
                )
            elif REQUIRE_MUTATION_CONSENT:
                await request_consent(cli_command, ctx)

        if ir.command and ir.command.is_awscli_customization:
            response: AwsCliAliasResponse | AwsApiMcpServerErrorResponse = (
                execute_awscli_customization(cli_command, ir.command)
            )
            if isinstance(response, AwsApiMcpServerErrorResponse):
                await ctx.error(response.detail)
            return response

        return interpret_command(
            cli_command=cli_command,
            max_results=max_results,
        )
    except NoCredentialsError:
        error_message = (
            'Error while executing the command: No AWS credentials found. '
            "Please configure your AWS credentials using 'aws configure' "
            'or set appropriate environment variables.'
        )
        await ctx.error(error_message)
        return AwsApiMcpServerErrorResponse(
            detail=error_message,
        )
    except AwsApiMcpError as e:
        error_message = f'Error while executing the command: {e.as_failure().reason}'
        await ctx.error(error_message)
        return AwsApiMcpServerErrorResponse(
            detail=error_message,
        )
    except Exception as e:
        error_message = f'Error while executing the command: {str(e)}'
        await ctx.error(error_message)
        return AwsApiMcpServerErrorResponse(
            detail=error_message,
        )


# EXPERIMENTAL: Agent scripts tool - only registered if ENABLE_AGENT_SCRIPTS is True
if ENABLE_AGENT_SCRIPTS:

    @server.tool(
        name='get_execution_plan',
        description=f"""Get the execution plan for a compiled AWS workflow. This tool provides structured, step-by-step guidance for accomplishing a complex task with AWS.
        When a user request matches a plan intent, you MUST always call this tool to get an execution plan instead of attempting to come up with you own, since the procedures returned by this tool are more robust, and properly tested.

        Below you can find the list of available scripts in the format <script_name> : <description>
        {AGENT_SCRIPTS_MANAGER.pretty_print_scripts()}
        INSTRUCTIONS:
        - Call this tool with the specific script_name when user requests match the above patterns
        - The returned plan contains detailed, tested procedures that you MUST follow exactly
        - Do NOT attempt to create your own procedures for these tasks - use the provided plans
        - Execute ALL steps in the plan without skipping any
        - If plan instructions contradict each other, ask the user for guidance

        Returns:
            - Detailed script plan with step-by-step instructions for the requested task.
        """,
        annotations=ToolAnnotations(
            title='Get structured execution plans for complex tasks',
            readOnlyHint=True,
            openWorldHint=False,
        ),
    )
    async def get_execution_plan(
        script_name: Annotated[str, Field(description='Name of the script to get the plan for')],
        ctx: Context,
    ) -> str | AwsApiMcpServerErrorResponse:
        """Retrieve full script content given a script name."""
        try:
            script = AGENT_SCRIPTS_MANAGER.get_script(script_name)

            if not script:
                error_message = f'Script {script_name} not found'
                logger.error(error_message)
                raise ValueError(error_message)

            logger.info(f'Retrieved script plan for {script_name}.')
            return script.content

        except Exception as e:
            error_message = f'Error while retrieving execution plan: {str(e)}'
            await ctx.error(error_message)
            return AwsApiMcpServerErrorResponse(detail=error_message)


def main():
    """Main entry point for the AWS API MCP server."""
    global READ_OPERATIONS_INDEX

    if not os.path.isabs(WORKING_DIRECTORY):
        error_message = 'AWS_API_MCP_WORKING_DIR must be an absolute path.'
        logger.error(error_message)
        raise ValueError(error_message)

    os.makedirs(WORKING_DIRECTORY, exist_ok=True)
    os.chdir(WORKING_DIRECTORY)
    logger.info(f'CWD: {os.getcwd()}')

    if DEFAULT_REGION is None:
        error_message = 'AWS_REGION environment variable is not defined.'
        logger.error(error_message)
        raise ValueError(error_message)

    validate_aws_region(DEFAULT_REGION)
    logger.info('AWS_REGION: {}', DEFAULT_REGION)

    try:
        knowledge_base.setup()
    except Exception as e:
        error_message = f'Error while setting up the knowledge base: {str(e)}'
        logger.error(error_message)
        raise RuntimeError(error_message)

    if READ_OPERATIONS_ONLY_MODE or REQUIRE_MUTATION_CONSENT:
        READ_OPERATIONS_INDEX = get_read_only_operations()

    server.run(transport='stdio')


if __name__ == '__main__':
    main()
