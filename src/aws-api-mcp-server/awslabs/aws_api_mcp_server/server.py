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
    check_security_policy,
    execute_awscli_customization,
    expand_regions_if_needed,
    get_help_document,
    interpret_command,
    request_consent,
    validate,
)
from .core.common.config import (
    DEFAULT_REGION,
    ENABLE_AGENT_SCRIPTS,
    ENDPOINT_SUGGEST_AWS_COMMANDS,
    FASTMCP_LOG_LEVEL,
    FILE_ACCESS_MODE,
    HOST,
    MAX_BATCH_COMMANDS,
    PORT,
    READ_ONLY_KEY,
    READ_OPERATIONS_ONLY_MODE,
    REQUIRE_MUTATION_CONSENT,
    STATELESS_HTTP,
    TRANSPORT,
    WORKING_DIRECTORY,
    FileAccessMode,
    get_server_auth,
)
from .core.common.errors import AwsApiMcpError, CommandValidationError
from .core.common.helpers import get_requests_session, validate_aws_region
from .core.common.models import (
    AwsCliAliasResponse,
    CallAWSResponse,
    Credentials,
    ProgramInterpretationResponse,
)
from .core.metadata.read_only_operations_list import ReadOnlyOperations, get_read_only_operations
from .core.security.policy import PolicyDecision
from .middleware.http_header_validation_middleware import HTTPHeaderValidationMiddleware
from botocore.exceptions import NoCredentialsError
from fastmcp import Context, FastMCP
from loguru import logger
from mcp.types import ToolAnnotations
from pathlib import Path
from pydantic import Field
from typing import Annotated, Any, Optional


logger.remove()
logger.add(sys.stderr, level=FASTMCP_LOG_LEVEL)

log_dir = Path.home() / '.aws' / 'aws-api-mcp'
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / 'aws-api-mcp-server.log'
logger.add(log_file, rotation='10 MB', retention='7 days')


server = FastMCP(
    name='AWS-API-MCP',
    instructions="""Run AWS CLI commands against the user's AWS account, with validation, security checks, and result handling.

Use this server for any task involving AWS resources or services (inspecting, querying, creating, modifying, or deleting them).

Tools:
- `call_aws` — execute a known AWS CLI command (the primary tool; supports batching independent commands).
- `suggest_aws_commands` — fallback that suggests CLI commands from a natural-language description; use only when unsure which command or parameters to use.""",
    auth=get_server_auth(),
    middleware=[HTTPHeaderValidationMiddleware()] if TRANSPORT == 'streamable-http' else [],
)
READ_OPERATIONS_INDEX: Optional[ReadOnlyOperations] = None

_FILE_ACCESS_MSGS = {
    FileAccessMode.UNRESTRICTED: f"File access is unrestricted so commands can reference files anywhere; use forward slashes (/) regardless of the system (e.g. 'c:/users/name/file.txt' or 'subdir/file.txt'); relative paths resolve from the working directory ({WORKING_DIRECTORY}).",
    FileAccessMode.NO_ACCESS: 'File access is disabled and commands with any local file reference will be rejected. S3 URIs (s3://...) and stdout redirect (-) remain allowed.',
    FileAccessMode.WORKDIR: f"Commands can only reference files within the working directory ({WORKING_DIRECTORY}); use forward slashes (/) regardless of the system (e.g. if working directory is 'c:/tmp/workdir', use 'c:/tmp/workdir/subdir/file.txt' or 'subdir/file.txt'); relative paths resolve from the working directory.",
}


@server.tool(
    name='suggest_aws_commands',
    description="""Suggest AWS CLI commands from a natural-language description of a task. FALLBACK tool — use only when you are unsure which AWS service, operation, or parameters to use. When you already know the command, call 'call_aws' instead.

    Make each query map to a single CLI command: if a request needs several commands (e.g. create a security group, then a volume, then an instance), call this tool once per command. Include the goal, relevant service/parameters, and any constraints in the query.

    Examples:
    - "List all running EC2 instances in us-east-1"
    - "Create an S3 bucket with versioning and server-side encryption enabled"

    Returns: up to 10 candidate commands, each with a confidence score, required parameters, and a description.
    """,
    annotations=ToolAnnotations(
        title='Suggest AWS CLI commands', readOnlyHint=True, openWorldHint=False
    ),
)
async def suggest_aws_commands(
    query: Annotated[
        str,
        Field(
            description="A natural language description of what you want to do in AWS. Should be detailed enough to capture the user's intent and any relevant context.",
            max_length=2000,
        ),
    ],
    ctx: Context,
) -> dict[str, Any]:
    """Suggest AWS CLI commands based on the provided query."""
    logger.info('Suggesting AWS commands for query: {}', query)
    if not query.strip():
        error_message = 'Empty query provided'
        await ctx.error(error_message)
        raise AwsApiMcpError(error_message)
    try:
        with get_requests_session() as session:
            response = session.post(
                ENDPOINT_SUGGEST_AWS_COMMANDS,
                json={'query': query},
                timeout=30,
            )
            response.raise_for_status()
            suggestions = response.json().get('suggestions')
            logger.info(
                'Suggested commands: {}',
                [suggestion.get('command') for suggestion in suggestions],
            )
            return response.json()
    except Exception as e:
        logger.error('Error while suggesting commands: {}', str(e))
        error_message = 'Failed to execute tool due to internal error. Use your best judgement and existing knowledge to pick a command or point to relevant AWS Documentation.'
        await ctx.error(error_message)
        raise AwsApiMcpError(error_message)


@server.tool(
    name='call_aws',
    description=f"""Execute an AWS CLI command (or a batch of them) with validation and error handling. This is the PRIMARY tool when you know the command you need; prefer it over 'suggest_aws_commands'.

    Rules:
    - The command MUST start with "aws" and follow AWS CLI syntax.
    - Runs in {DEFAULT_REGION} by default; pass --region for other regions, or `--region *` to run across all enabled regions (do NOT emit one command per region).
    - No shell features: no pipes (|), redirects (>, <), substitution ($()), env vars, or tools like grep/awk/sed.
    - Use --query/--filters/--prefix only when needed or explicitly requested.
    - When writing files, use the working directory unless the user specified another.
    - {_FILE_ACCESS_MSGS[FILE_ACCESS_MODE]}

    Batch mode: pass a list of independent commands to run them together — prefer this whenever you have more than one command (e.g. the same operation over many resources). Max {MAX_BATCH_COMMANDS} per call.
        call_aws(cli_command=["aws s3api get-bucket-website --bucket b1", "aws s3api get-bucket-website --bucket b2"])

    Returns: CLI execution results with API response data, or an error message per command.
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
        str | list[str],
        Field(description='A single command or a list of complete AWS CLI commands to execute'),
    ],
    ctx: Context,
    max_results: Annotated[
        int | None,
        Field(description='Optional limit for number of results (useful for pagination)'),
    ] = None,
) -> list[CallAWSResponse]:
    """Call AWS with the given CLI command and return the result as a dictionary."""
    commands = [cli_command] if isinstance(cli_command, str) else cli_command

    if len(commands) > MAX_BATCH_COMMANDS:
        raise AwsApiMcpError(
            f'Number of batch commands exceeds the maximum limit of {MAX_BATCH_COMMANDS}.'
        )

    results = []
    for cmd in commands:
        try:
            expanded_commands = expand_regions_if_needed(cmd)
        except Exception as e:
            results.append(CallAWSResponse(cli_command=cmd, error=str(e)))
        else:
            for expanded_cmd in expanded_commands:
                results.append(await _execute_single_command(expanded_cmd, ctx, max_results))
    return results


async def _execute_single_command(
    cmd: str, ctx: Context, max_results: int | None
) -> CallAWSResponse:
    try:
        response = await call_aws_helper(cmd, ctx, max_results, None)
        return CallAWSResponse(cli_command=cmd, response=response)
    except Exception as e:
        return CallAWSResponse(cli_command=cmd, error=str(e))


async def call_aws_helper(
    cli_command: Annotated[
        str, Field(description='The complete AWS CLI command to execute. MUST start with "aws"')
    ],
    ctx: Context,
    max_results: Annotated[
        int | None,
        Field(description='Optional limit for number of results (useful for pagination)'),
    ] = None,
    credentials: Credentials | None = None,
    default_region: str | None = None,
) -> ProgramInterpretationResponse | AwsCliAliasResponse:
    """Helper function that actually calls aws."""
    try:
        ir = translate_cli_to_ir(cli_command)
        ir_validation = validate(ir)

        if not ir.command or ir_validation.validation_failed:
            error_message = (
                f'Error while validating the command: {ir_validation.model_dump_json()}'
            )
            await ctx.error(error_message)
            raise CommandValidationError(error_message)
    except AwsApiMcpError as e:
        await ctx.error(e.as_failure().reason)
        raise
    except Exception as e:
        error_message = f'Error while validating the command: {str(e)}'
        await ctx.error(error_message)
        raise AwsApiMcpError(error_message)

    logger.info(
        'Attempting to execute AWS CLI command: aws {} {} *parameters redacted*',
        ir.command.service_name,
        ir.command.operation_cli_name,
    )

    try:
        # Check security policy
        if READ_OPERATIONS_INDEX is not None:
            policy_decision = check_security_policy(ir, READ_OPERATIONS_INDEX, ctx)

            if policy_decision == PolicyDecision.DENY:
                error_message = 'Execution of this operation is denied by security policy.'
                await ctx.error(error_message)
                raise AwsApiMcpError(error_message)
            elif policy_decision == PolicyDecision.ELICIT:
                await request_consent(cli_command, ctx)
        else:
            if READ_OPERATIONS_ONLY_MODE:
                error_message = (
                    'Execution of this operation is not allowed because read only mode is enabled. '
                    f'It can be disabled by setting the {READ_ONLY_KEY} environment variable to False.'
                )
                await ctx.error(error_message)
                raise AwsApiMcpError(error_message)
            elif REQUIRE_MUTATION_CONSENT:
                await request_consent(cli_command, ctx)

        if ir.command and ir.command.is_help_operation:
            return await get_help_document(cli_command, ctx)

        if ir.command and ir.command.is_awscli_customization:
            return execute_awscli_customization(
                cli_command,
                ir.command,
                credentials=credentials,
                default_region_override=default_region,
            )

        return interpret_command(
            cli_command=cli_command,
            max_results=max_results,
            credentials=credentials,
            default_region_override=default_region,
        )
    except NoCredentialsError:
        error_message = (
            'Error while executing the command: No AWS credentials found. '
            "Please configure your AWS credentials using 'aws configure' "
            'or set appropriate environment variables.'
        )
        await ctx.error(error_message)
        raise AwsApiMcpError(error_message)
    except AwsApiMcpError as e:
        await ctx.error(e.as_failure().reason)
        raise
    except Exception as e:
        error_message = f'Error while executing the command: {str(e)}'
        await ctx.error(error_message)
        raise AwsApiMcpError(error_message)


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
    ) -> str:
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
            raise AwsApiMcpError(error_message)


def main():
    """Main entry point for the AWS API MCP server."""
    global READ_OPERATIONS_INDEX

    os.chdir(WORKING_DIRECTORY)
    logger.info(f'CWD: {os.getcwd()}')

    if DEFAULT_REGION is None:
        error_message = 'AWS_REGION environment variable is not defined.'
        logger.error(error_message)
        raise ValueError(error_message)

    validate_aws_region(DEFAULT_REGION)
    logger.info('AWS_REGION: {}', DEFAULT_REGION)

    # Always load read operations index for security policy checking
    try:
        READ_OPERATIONS_INDEX = get_read_only_operations()
    except Exception as e:
        logger.warning('Failed to load read operations index: {}', e)
        READ_OPERATIONS_INDEX = None

    if TRANSPORT == 'stdio':
        server.run(
            transport=TRANSPORT,
        )
    else:  # streamable-http or other HTTP transports
        server.run(
            transport=TRANSPORT,
            host=HOST,
            port=PORT,
            stateless_http=STATELESS_HTTP,
        )


if __name__ == '__main__':
    main()
