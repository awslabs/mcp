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

import contextlib
from ..aws.services import driver
from ..common.config import AWS_API_MCP_PROFILE_NAME, DEFAULT_REGION
from ..common.errors import AwsApiMcpError, Failure
from ..common.models import (
    AwsApiMcpServerErrorResponse,
    AwsCliAliasResponse,
    Consent,
    InterpretationMetadata,
    InterpretationResponse,
    InterpretedProgram,
    IRTranslation,
    ProgramInterpretationResponse,
    ProgramValidationResponse,
)
from ..common.models import Context as ContextAPIModel
from ..common.models import ValidationFailure as FailureAPIModel
from ..metadata.read_only_operations_list import (
    ReadOnlyOperations,
)
from ..parser.lexer import split_cli_command
from .driver import interpret_command as _interpret_command
from awslabs.aws_api_mcp_server.core.common.command import IRCommand
from awslabs.aws_api_mcp_server.core.common.helpers import operation_timer
from io import StringIO
from loguru import logger
from mcp.server.elicitation import AcceptedElicitation
from mcp.server.fastmcp import Context
from mcp.shared.exceptions import McpError
from mcp.types import METHOD_NOT_FOUND
from typing import Any


async def request_consent(cli_command: str, ctx: Context):
    """Request consent of the user using elicitation."""
    try:
        elicitation_result = await ctx.elicit(
            message=f"The CLI command '{cli_command}' requires explicit consent. Do you approve the execution of this command?",
            schema=Consent,
        )

        if (
            not isinstance(elicitation_result, AcceptedElicitation)
            or not elicitation_result.data.answer
        ):
            error_message = 'User rejected the execution of the command.'
            await ctx.error(error_message)
            raise AwsApiMcpError(error_message)
    except McpError as e:
        if e.error.code == METHOD_NOT_FOUND:
            error_message = 'Client does not support elicitation. Use a different client or update the server configuration.'
            logger.error(error_message)
            raise AwsApiMcpError(error_message)

        raise e


def is_operation_read_only(ir: IRTranslation, read_only_operations: ReadOnlyOperations):
    """Check if the operation in the IR is read-only."""
    if (
        not ir.command_metadata
        or not getattr(ir.command_metadata, 'service_sdk_name', None)
        or not getattr(ir.command_metadata, 'operation_sdk_name', None)
    ):
        raise RuntimeError(
            "failed to check if operation is allowed: translated command doesn't include service and operation name"
        )

    service_name = ir.command_metadata.service_sdk_name
    operation_name = ir.command_metadata.operation_sdk_name
    return read_only_operations.has(service=service_name, operation=operation_name)


def validate(ir: IRTranslation) -> ProgramValidationResponse:
    """Translate the given CLI command and return a validation response."""
    return ProgramValidationResponse(
        missing_context_failures=_to_missing_context_failures(ir.missing_context_failures),
        validation_failures=_to_validation_failures(ir.validation_or_translation_failures),
    )


def execute_awscli_customization(
    cli_command: str, ir_command: IRCommand
) -> AwsCliAliasResponse | AwsApiMcpServerErrorResponse:
    """Execute the given AWS CLI command."""
    args = split_cli_command(cli_command)[1:]

    # Identify if a profile was passed in already and insert the defined one otherwise
    if AWS_API_MCP_PROFILE_NAME and not any(elem == '--profile' for elem in args):
        args.extend(['--profile', AWS_API_MCP_PROFILE_NAME])

    try:
        stdout_capture = StringIO()
        stderr_capture = StringIO()

        with (
            contextlib.redirect_stdout(stdout_capture),
            contextlib.redirect_stderr(stderr_capture),
        ):
            with operation_timer(
                ir_command.service_name,
                ir_command.operation_name,
                ir_command.region or DEFAULT_REGION,
            ):
                driver.main(args)

        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()

        return AwsCliAliasResponse(response=stdout_output, error=stderr_output)
    except Exception as e:
        return AwsApiMcpServerErrorResponse(
            error=True,
            detail=f"Error while executing '{cli_command}': {e}",
        )


def interpret_command(
    cli_command: str,
    max_results: int | None = None,
) -> ProgramInterpretationResponse:
    """Interpret the given CLI command and return an interpretation response."""
    interpreted_program = _interpret_command(
        cli_command,
        max_results=max_results,
    )

    validation_failures = (
        []
        if not interpreted_program.translation.validation_or_translation_failures
        else interpreted_program.translation.validation_or_translation_failures
    )
    missing_context_failures = (
        []
        if not interpreted_program.translation.missing_context_failures
        else interpreted_program.translation.missing_context_failures
    )
    failed_constraints = interpreted_program.failed_constraints or []

    if (
        not validation_failures
        and not missing_context_failures
        and not interpreted_program.failed_constraints
    ):
        response = InterpretationResponse(
            json=interpreted_program.response,
            error=interpreted_program.service_error,
            status_code=interpreted_program.status_code,
            error_code=interpreted_program.error_code,
            pagination_token=interpreted_program.pagination_token,
        )
    else:
        response = None

    return ProgramInterpretationResponse(
        response=response,
        metadata=_ir_metadata(interpreted_program),
        validation_failures=_to_validation_failures(validation_failures),
        missing_context_failures=_to_missing_context_failures(missing_context_failures),
        failed_constraints=failed_constraints,
    )


def _ir_metadata(program: InterpretedProgram | None) -> InterpretationMetadata | None:
    if program and program.translation and program.translation.command:
        command = program.translation.command
        return InterpretationMetadata(
            service=command.service_name,
            service_full_name=command.service_full_name,
            operation=command.operation_name,
            region_name=program.region_name,
        )
    return None


def _to_missing_context_failures(
    failures: list[Failure] | None,
) -> list[FailureAPIModel] | None:
    if not failures:
        return None

    return [
        FailureAPIModel(reason=failure.reason, context=_to_context(failure.context))
        for failure in failures
    ]


def _to_validation_failures(failures: list[Failure] | None) -> list[FailureAPIModel] | None:
    if not failures:
        return None

    return [
        FailureAPIModel(reason=failure.reason, context=_to_context(failure.context))
        for failure in failures
    ]


def _to_context(context: dict[str, Any] | None) -> ContextAPIModel | None:
    if not context:
        return None

    return ContextAPIModel(
        service=context.get('service'),
        operation=context.get('operation'),
        operators=context.get('operators'),
        region=context.get('region'),
        args=context.get('args'),
        parameters=context.get('parameters'),
    )
