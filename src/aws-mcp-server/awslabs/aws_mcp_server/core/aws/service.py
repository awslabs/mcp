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

import boto3
from ..common.constraints import (
    AllowEverything,
    Constraint,
    ValidationsConfiguration,
    verify_constraints_on_ir,
)
from ..common.errors import Failure
from ..common.models import Context as ContextAPIModel
from ..common.models import (
    Credentials,
    InterpretationMetadata,
    InterpretationResponse,
    InterpretedProgram,
    IRTranslation,
    ProgramClassificationMetadata,
    ProgramInterpretationResponse,
    ProgramValidationResponse,
    RequireConsentResponse,
)
from ..common.models import ValidationFailure as FailureAPIModel
from ..metadata.confirm_list import get_confirm_list
from ..metadata.read_only_operations_list import (
    ReadOnlyOperations,
)
from .driver import interpret_command as _interpret_command
from .token_manager import TokenManager
from botocore.exceptions import NoCredentialsError
from loguru import logger
from typing import Any, cast


confirm_list = get_confirm_list()
token_manager = TokenManager()


def get_local_credentials() -> Credentials:
    """Get the local credentials for AWS profile."""
    session = boto3.Session()
    aws_creds = session.get_credentials()

    if aws_creds is None:
        raise NoCredentialsError()
    return Credentials(
        access_key_id=aws_creds.access_key,
        secret_access_key=aws_creds.secret_key,
        session_token=aws_creds.token,
    )


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
    classification = (
        ProgramClassificationMetadata(**ir.classification.as_metadata())
        if ir.classification
        else None
    )

    # If command is invalid, we can't classify it properly
    failed_constraints = (
        []
        if ir.validation_or_translation_failures
        else verify_constraints_on_ir(ir, cast(list[Constraint], ValidationsConfiguration))
    )

    return ProgramValidationResponse(
        missing_context_failures=_to_missing_context_failures(ir.missing_context_failures),
        validation_failures=_to_validation_failures(ir.validation_or_translation_failures),
        classification=classification,
        failed_constraints=failed_constraints,
    )


def check_for_consent(
    cli_command: str,
    ir: IRTranslation,
    consent_token: str | None,
) -> RequireConsentResponse | None:
    """Check if the given command requires explicit user consent and handle consent logic."""
    if not ir.command_metadata:
        raise RuntimeError('IR is missing command_metadata')
    service_name = ir.command_metadata.service_sdk_name
    operation_name = ir.command_metadata.operation_sdk_name

    if confirm_list.has(service=service_name, operation=operation_name):
        logger.info('Checking consent token')

        # Check if a valid token was provided
        if consent_token is not None and token_manager.validate_token(consent_token, cli_command):
            # Valid token provided, proceed with operation
            logger.info('Valid consent token provided. Proceeding with operation.')
        # Check if there's a valid token for this command type, even if not provided
        elif consent_token is None and token_manager.has_valid_token_for_command(cli_command):
            # Found a valid previous token for this API
            logger.info(
                'Found previous valid token for command signature. Proceeding with operation.'
            )
        # No valid token provided or found for this command type
        else:
            if consent_token is not None:
                # Token was provided but is invalid, expired, or doesn't match
                logger.info(
                    'Invalid, expired token, or command signature mismatch. Generating new token.'
                )
                message_prefix = (
                    "Consent token expired, invalid, or doesn't match the command signature."
                )
            else:
                # No token was provided
                logger.info('User consent not found. Asking for consent.')
                message_prefix = ''

            # Generate a new token for this command
            new_token = token_manager.generate_token(cli_command)
            return RequireConsentResponse(
                status='consent_required',
                message=f"{message_prefix} This operation '{cli_command}' requires explicit consent. Ask user for consent, and then call again with consent token {new_token} if user gives consent to run action",
            )


def interpret_command(
    cli_command: str,
    credentials: Credentials,
    default_region: str,
    max_results: int | None = None,
    max_tokens: int | None = None,
    is_counting: bool | None = None,
) -> ProgramInterpretationResponse:
    """Interpret the given CLI command and return an interpretation response."""
    interpreted_program = _interpret_command(
        cli_command,
        access_key_id=credentials.access_key_id,
        secret_access_key=credentials.secret_access_key,
        session_token=credentials.session_token,
        constraints=[AllowEverything()],
        default_region=default_region,
        max_results=max_results,
        max_tokens=max_tokens,
        is_counting=is_counting,
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
