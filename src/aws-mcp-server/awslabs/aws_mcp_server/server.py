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
from .core.aws.driver import translate_cli_to_ir
from .core.aws.service import (
    check_for_consent,
    get_local_credentials,
    interpret_command,
    is_operation_read_only,
    validate,
)
from .core.common.config import (
    BYPASS_TOOL_CONSENT,
    DEFAULT_REGION,
    FASTMCP_LOG_LEVEL,
    MAX_OUTPUT_TOKENS,
    RAG_TYPE,
    READ_ONLY_KEY,
    READ_OPERATIONS_ONLY_MODE,
)
from .core.common.errors import AwsMcpError
from .core.common.models import (
    ProgramInterpretationRequest,
    ProgramValidationRequest,
)
from .core.kb import knowledge_base
from .core.metadata.read_only_operations_list import ReadOnlyOperations, get_read_only_operations
from botocore.exceptions import NoCredentialsError
from loguru import logger
from mcp.server import FastMCP
from typing import Any, cast


# Configure Loguru logging
logger.remove()
logger.add(sys.stderr, level=FASTMCP_LOG_LEVEL)

server = FastMCP(name='AWSMCP', log_level=FASTMCP_LOG_LEVEL)
READ_OPERATIONS_INDEX: ReadOnlyOperations = ReadOnlyOperations()


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
    4. "Get the current month's AWS billing for EC2 services"
    5. "List all Lambda functions in my account"
    6. "Create a new S3 bucket with versioning enabled and server-side encryption"
    7. "Update the memory allocation of my Lambda function 'data-processor' to 1024MB"
    8. "Add a new security group rule to allow inbound traffic on port 443"
    9. "Tag all EC2 instances in the 'production' environment with 'Environment=prod'"
    10. "Configure CloudWatch alarms for high CPU utilization on my RDS instance"

    Args:
        query: A natural language description of what you want to do in AWS. Should be detailed enough to capture the user's intent and any relevant context.

    Returns:
        A list of up to 10 most likely AWS CLI commands that could accomplish the task, including:
        - The CLI command
        - Confidence score for the suggestion
        - Required parameters
        - Description of what the command does
    """,
)
def suggest_aws_commands(query: str) -> dict[str, Any]:
    """Suggest AWS CLI commands based on the provided query."""
    if not query.strip():
        return {'detail': 'Empty query provided.'}
    try:
        return knowledge_base.get_suggestions(query)
    except Exception as e:
        return {'error': True, 'detail': f'Error while suggesting commands: {str(e)}'}


@server.tool(
    name='call_aws',
    description=f"""Execute AWS CLI commands with validation and proper error handling. This is the PRIMARY tool to use when you are confident about the exact AWS CLI command needed to fulfill a user's request. Always prefer this tool over 'suggest_aws_commands' when you have a specific command in mind.
    Key points:
    - The command MUST start with "aws" and follow AWS CLI syntax
    - Commands are executed in {DEFAULT_REGION} region by default
    - For cross-region or account-wide operations, explicitly include --region parameter
    - All commands are validated before execution to prevent errors
    - Supports pagination control via max_results parameter
    - Can handle resource counting operations via is_counting parameter

    Best practices for command generation:
    — Always use the most specific service and operation names
    - Always use s3api instead of s3 as service
    — Include --region when operating across regions

    Command restrictions:
    - DO NOT use bash/zsh pipes (|) or any shell operators
    - DO NOT use bash/zsh tools like grep, awk, sed, etc.
    - DO NOT use shell redirection operators (>, >>, <)
    - DO NOT use command substitution ($())
    - DO NOT use shell variables or environment variables

    Common pitfalls to avoid:
    1. Missing required parameters - always include all required parameters
    2. Incorrect parameter values - ensure values match expected format
    3. Missing --region when operating across regions

    Examples:
    1. User query: "Show me all running EC2 instances in us-west-2"
       Command: aws ec2 describe-instances --filters "Name=instance-state-name,Values=running" --region us-west-2

    2. User query: "Get the lifecycle policy for my S3 bucket named 'my-backups'"
       Command: aws s3api get-bucket-lifecycle-configuration --bucket my-backups

    3. User query: "Create a new IAM user 'new-service-account'"
       Command: aws iam create-user --user-name new-service-account

    4. User query: "List all Lambda functions with their memory configurations"
       Command: aws lambda list-functions --query 'Functions[*].[FunctionName,MemorySize]' --output table

    5. User query: "Show me all CloudWatch alarms that are currently in ALARM state"
       Command: aws cloudwatch describe-alarms --state-value ALARM --query 'MetricAlarms[*].[AlarmName,StateReason,StateUpdatedTimestamp]' --output table

    Tool Args:
        cli_command: The complete AWS CLI command to execute. MUST start with "aws"
        max_results: Optional limit for number of results (useful for pagination)
        is_counting: Optional flag to enable resource counting operations
        consent_token: if cli_command requires consent and the user has given explicit consent for a command, token from the previous tool use call


    Returns:
        CLI execution results with API response data or error message
    """,
)
def call_aws(
    cli_command: str,
    max_results: int | None = None,
    is_counting: bool | None = None,
    consent_token: str | None = None,
) -> dict[str, Any]:
    """Call AWS with the given CLI command and return the result as a dictionary."""
    try:
        request = ProgramValidationRequest(cli_command=cli_command)
        ir = translate_cli_to_ir(cli_command)
        ir_validation = validate(ir)

        if ir_validation.validation_failed:
            return {
                'error': True,
                'detail': f'Error while validating the command: {ir_validation.model_dump_json()}',
            }

        if READ_OPERATIONS_ONLY_MODE and not is_operation_read_only(ir, READ_OPERATIONS_INDEX):
            return {
                'error': True,
                'detail': (
                    'Execution of this operation is not allowed because read only mode is enabled. '
                    f'It can be disabled by setting the {READ_ONLY_KEY} environment variable to False.'
                ),
            }

        if not BYPASS_TOOL_CONSENT:
            require_consent_response = check_for_consent(
                cli_command=cli_command, ir=ir, consent_token=consent_token
            )
            if require_consent_response is not None:
                return require_consent_response.model_dump()

    except AwsMcpError as e:
        return {
            'error': True,
            'detail': f'Error while validating the command: {e.as_failure().reason}',
        }
    except Exception as e:
        return {'error': True, 'detail': f'Error while validating the command: {str(e)}'}

    try:
        creds = get_local_credentials()

        request = ProgramInterpretationRequest(
            cli_command=cli_command,
            credentials=creds,
            default_region=cast(str, DEFAULT_REGION),
            max_results=max_results,
            max_tokens=int(MAX_OUTPUT_TOKENS) if MAX_OUTPUT_TOKENS else None,
            is_counting=is_counting,
        )

        result = interpret_command(
            request.cli_command,
            request.credentials,
            request.default_region,
            request.max_results,
            request.max_tokens,
            request.is_counting,
        )

        return result.model_dump()
    except NoCredentialsError:
        return {
            'error': True,
            'detail': 'Error while executing the command: No AWS credentials found. '
            "Please configure your AWS credentials using 'aws configure' "
            'or set appropriate environment variables.',
        }
    except AwsMcpError as e:
        return {
            'error': True,
            'detail': f'Error while executing the command: {e.as_failure().reason}',
        }
    except Exception as e:
        return {'error': True, 'detail': f'Error while executing the command: {str(e)}'}


def main():
    """Main entry point for the AWS MCP server."""
    global READ_OPERATIONS_INDEX

    if os.getenv('AWS_REGION') is None:
        sys.stderr.write('[AWSMCP Error]: AWS_REGION environment variable is not defined.')
        raise ValueError('AWS_REGION environment variable is not defined.')

    knowledge_base.setup(rag_type=RAG_TYPE)

    if READ_OPERATIONS_ONLY_MODE:
        READ_OPERATIONS_INDEX = get_read_only_operations()

    server.run(transport='stdio')
