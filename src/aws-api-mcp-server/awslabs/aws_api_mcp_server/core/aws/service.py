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
import re
import sys
from ..aws.regions import get_active_regions
from ..aws.services import get_awscli_driver
from ..common.config import AWS_API_MCP_PROFILE_NAME, DEFAULT_REGION
from ..common.errors import AwsApiMcpError, Failure
from ..common.help_command import generate_help_document
from ..common.models import (
    AwsCliAliasResponse,
    Consent,
    Credentials,
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
from ..security.policy import PolicyDecision, SecurityPolicy
from .driver import interpret_command as _interpret_command
from awslabs.aws_api_mcp_server.core.common.command import IRCommand
from awslabs.aws_api_mcp_server.core.common.helpers import as_json, operation_timer
from contextvars import ContextVar
from fastmcp import Context
from fastmcp.server.elicitation import AcceptedElicitation
from io import StringIO
from loguru import logger
from mcp.shared.exceptions import McpError
from mcp.types import METHOD_NOT_FOUND
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Thread-safe awscli output capture
#
# The awscli CLIDriver writes output through two independent sinks:
#   1. Formatters (JSON/Text/Table) via awscli.compat.get_stdout_text_writer()
#   2. Customizations (S3, etc.) via awscli.customizations.utils.uni_print()
#   3. Error handling via awscli.compat.get_stderr_text_writer() and
#      awscli.clidriver.get_stderr_text_writer (local binding)
#
# We monkey-patch these to check a ContextVar. When a capture buffer is active,
# output goes there; otherwise it falls through to the original implementation.
# This is thread-safe unlike contextlib.redirect_stdout which swaps sys.stdout.
# ---------------------------------------------------------------------------

_capture_stdout: ContextVar[Optional[StringIO]] = ContextVar(
    '_awscli_capture_stdout', default=None
)
_capture_stderr: ContextVar[Optional[StringIO]] = ContextVar(
    '_awscli_capture_stderr', default=None
)
_awscli_patched = False


def _install_awscli_output_patch() -> None:
    """Monkey-patch awscli output sinks to use ContextVar-based capture. Idempotent."""
    global _awscli_patched
    if _awscli_patched:
        return

    import awscli.clidriver
    import awscli.compat
    import awscli.customizations.cloudformation.deploy
    import awscli.customizations.codeartifact.login
    import awscli.customizations.eks.get_token
    import awscli.customizations.eks.update_kubeconfig
    import awscli.customizations.emrcontainers.update_role_trust_policy
    import awscli.customizations.globalargs
    import awscli.customizations.logs.startlivetail
    import awscli.customizations.paginate
    import awscli.customizations.rds
    import awscli.customizations.s3.results
    import awscli.customizations.s3.subcommands
    import awscli.customizations.s3.syncstrategy.caseconflict
    import awscli.customizations.scalarparse
    import awscli.customizations.utils

    # --- Save originals ---
    original_get_stdout = awscli.compat.get_stdout_text_writer
    original_get_stderr = awscli.compat.get_stderr_text_writer
    original_uni_print = awscli.customizations.utils.uni_print

    # --- Patched functions ---
    def patched_get_stdout_text_writer():
        buf = _capture_stdout.get()
        return buf if buf is not None else original_get_stdout()

    def patched_get_stderr_text_writer():
        buf = _capture_stderr.get()
        return buf if buf is not None else original_get_stderr()

    def patched_uni_print(statement, out_file=None):
        stdout_buf = _capture_stdout.get()
        stderr_buf = _capture_stderr.get()
        if stdout_buf is not None:
            if out_file is None or out_file is sys.stdout:
                stdout_buf.write(statement)
                stdout_buf.flush()
            elif out_file is sys.stderr and stderr_buf is not None:
                stderr_buf.write(statement)
                stderr_buf.flush()
            else:
                original_uni_print(statement, out_file)
        else:
            original_uni_print(statement, out_file)

    # --- Apply patches ---
    awscli.compat.get_stdout_text_writer = patched_get_stdout_text_writer
    awscli.compat.get_stderr_text_writer = patched_get_stderr_text_writer

    # Modules with local binding of get_stdout_text_writer
    awscli.customizations.cloudformation.deploy.get_stdout_text_writer = (
        patched_get_stdout_text_writer
    )
    awscli.customizations.logs.startlivetail.get_stdout_text_writer = (
        patched_get_stdout_text_writer
    )

    # Modules with local binding of get_stderr_text_writer
    awscli.clidriver.get_stderr_text_writer = patched_get_stderr_text_writer

    # uni_print on canonical module
    awscli.customizations.utils.uni_print = patched_uni_print

    # Modules with local binding of uni_print
    awscli.customizations.s3.subcommands.uni_print = patched_uni_print
    awscli.customizations.s3.results.uni_print = patched_uni_print
    awscli.customizations.s3.syncstrategy.caseconflict.uni_print = patched_uni_print
    awscli.customizations.cloudformation.deploy.uni_print = patched_uni_print
    awscli.customizations.rds.uni_print = patched_uni_print
    awscli.customizations.globalargs.uni_print = patched_uni_print
    awscli.customizations.eks.get_token.uni_print = patched_uni_print
    awscli.customizations.eks.update_kubeconfig.uni_print = patched_uni_print
    awscli.customizations.emrcontainers.update_role_trust_policy.uni_print = patched_uni_print
    awscli.customizations.paginate.uni_print = patched_uni_print
    awscli.customizations.scalarparse.uni_print = patched_uni_print
    awscli.customizations.codeartifact.login.uni_print = patched_uni_print

    _awscli_patched = True


@contextlib.contextmanager
def _capture_awscli_output():
    """Context manager for thread-safe awscli output capture.

    Uses ContextVars so concurrent threads/tasks each get independent buffers.
    """
    _install_awscli_output_patch()
    stdout_buf = StringIO()
    stderr_buf = StringIO()
    stdout_token = _capture_stdout.set(stdout_buf)
    stderr_token = _capture_stderr.set(stderr_buf)
    try:
        yield stdout_buf, stderr_buf
    finally:
        _capture_stdout.reset(stdout_token)
        _capture_stderr.reset(stderr_token)


async def request_consent(cli_command: str, ctx: Context):
    """Request consent of the user using elicitation."""
    try:
        elicitation_result = await ctx.elicit(
            message=f"The CLI command '{cli_command}' requires explicit consent. Do you approve the execution of this command?",
            response_type=Consent,
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


def check_security_policy(
    ir: IRTranslation, read_only_operations: ReadOnlyOperations, ctx: Context
) -> PolicyDecision:
    """Check security policy for the given command and return decision."""

    def is_read_only_func(service: str, operation: str) -> bool:
        return read_only_operations.has(service=service, operation=operation)

    policy = SecurityPolicy(ctx)

    # First check if this matches a customization
    customization_decision = policy.check_customization(ir, is_read_only_func)
    if customization_decision is not None:
        return customization_decision

    # If no customization matches, check individual operation
    if (
        not ir.command_metadata
        or not getattr(ir.command_metadata, 'service_sdk_name', None)
        or not getattr(ir.command_metadata, 'operation_sdk_name', None)
    ):
        return PolicyDecision.ELICIT if policy.supports_elicitation else PolicyDecision.DENY

    service_name = ir.command_metadata.service_sdk_name
    operation_name = ir.command_metadata.operation_sdk_name
    is_read_only = is_operation_read_only(ir, read_only_operations)

    return policy.determine_policy_effect(service_name, operation_name, is_read_only)


def validate(ir: IRTranslation) -> ProgramValidationResponse:
    """Translate the given CLI command and return a validation response."""
    return ProgramValidationResponse(
        missing_context_failures=_to_missing_context_failures(ir.missing_context_failures),
        validation_failures=_to_validation_failures(ir.validation_or_translation_failures),
    )


async def get_help_document(
    cli_command: str,
    ctx: Context,
) -> ProgramInterpretationResponse:
    """Get help command response."""
    args = split_cli_command(cli_command)[1:]
    service_name = args[0]
    operation_name = args[1]
    help_document = generate_help_document(service_name, operation_name)
    if help_document is None:
        error_message = 'Failed to generate help document'
        await ctx.error(error_message)
        raise AwsApiMcpError(error_message)
    return ProgramInterpretationResponse(
        response=InterpretationResponse(json=as_json(help_document), status_code=200, error=None)
    )


def execute_awscli_customization(
    cli_command: str,
    ir_command: IRCommand,
    credentials: Credentials | None = None,
    default_region_override: str | None = None,
) -> AwsCliAliasResponse:
    """Execute the given AWS CLI command.

    Uses ContextVar-based output capture instead of contextlib.redirect_stdout
    which is not thread-safe.
    """
    args = split_cli_command(cli_command)[1:]

    # Identify if a profile was passed in already and insert the defined one otherwise
    if AWS_API_MCP_PROFILE_NAME and not any(elem == '--profile' for elem in args):
        args.extend(['--profile', AWS_API_MCP_PROFILE_NAME])

    try:
        with _capture_awscli_output() as (stdout_buf, stderr_buf):
            with operation_timer(
                ir_command.service_name,
                ir_command.operation_name,
                ir_command.region or default_region_override or DEFAULT_REGION,
            ):
                driver = get_awscli_driver(credentials)
                driver.main(args)

        stdout_output = stdout_buf.getvalue()
        stderr_output = stderr_buf.getvalue()

        if not stdout_output and stderr_output:
            raise Exception(stderr_output)

        return AwsCliAliasResponse(response=stdout_output, error=stderr_output)
    except Exception as e:
        raise AwsApiMcpError(f"Error while executing '{cli_command}': {e}")


def interpret_command(
    cli_command: str,
    max_results: int | None = None,
    credentials: Credentials | None = None,
    default_region_override: str | None = None,
) -> ProgramInterpretationResponse:
    """Interpret the given CLI command and return an interpretation response."""
    interpreted_program = _interpret_command(
        cli_command,
        max_results=max_results,
        credentials=credentials,
        default_region_override=default_region_override,
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


def expand_regions_if_needed(cli_command: str) -> list[str]:
    """Expand `--region *` wildcard with available regions."""
    region_wildcard = re.compile(r'--region\s+\*(?=\s|$)')
    if not region_wildcard.search(cli_command):
        return [cli_command]
    match = re.search(r'--profile\s+(?!--)(\S+)', cli_command)
    profile_name = match.group(1) if match else AWS_API_MCP_PROFILE_NAME
    active_regions = get_active_regions(profile_name)
    return [region_wildcard.sub(f'--region {region}', cli_command) for region in active_regions]
