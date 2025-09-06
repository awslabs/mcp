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

from __future__ import annotations

import dataclasses
from .command_metadata import CommandMetadata
from argparse import FileType
from collections.abc import Callable, Iterable, Set
from typing import Any


VALIDATION_ERROR_STATUS_CODE = 400
INVALID_BUCKET_NAME_ERROR_CODE = 'InvalidBucketName'


@dataclasses.dataclass(frozen=True)
class Failure:
    """Represents a failure with a reason and optional context."""

    reason: str
    context: dict[str, Any] | None = None


class AwsApiMcpError(Exception):
    """Base class for all errors thrown by this library."""

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(reason=str(self))


class CliParsingError(AwsApiMcpError):
    """Thrown when the CLI parsing fails."""


class CommandValidationError(AwsApiMcpError):
    """Thrown when the command validation fails.

    For example, we want to differentiate between invalid
    commands (e.g. hallucinations) and missing parameters
    (clarification).
    """


class MissingContextError(AwsApiMcpError):
    """Thrown when required context has not been found (e.g. missing parameters and values)."""

    def __init__(self, message: str, command_metadata: CommandMetadata) -> None:
        """Initialize MissingContextError with a message and command metadata."""
        self.command_metadata = command_metadata
        super().__init__(message)


class ProhibitedOperatorsError(CliParsingError):
    """Thrown when the CLI command contains prohibited operators."""

    _message = 'The CLI command contains prohibited operators: {}'

    def __init__(self, operators: list[str]):
        """Initialize ProhibitedOperatorsError with a list of operators."""
        message = self._message.format(operators)
        self._operators = operators
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(reason=str(self), context={'operators': self._operators})


class InvalidChoiceForParameterError(CliParsingError):
    """Thrown when a parameter receives an invalid choice."""

    _message = 'The parameter {parameter!r} received an invalid choice: {choice!r}'

    def __init__(self, parameter: str, choice: str):
        """Initialize InvalidChoiceForParameterError with parameter and choice."""
        message = self._message.format(parameter=parameter, choice=choice)
        self._parameter = parameter
        self._choice = choice
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(
            reason=str(self), context={'parameter': self._parameter, 'choice': self._choice}
        )


class ServiceNotAllowedError(CliParsingError):
    """Thrown when the given service name is explicitely not allowed."""

    _message = 'The given service name is not allowed: {}'

    def __init__(self, service: str):
        """Initialize ServiceNotAllowedError with the service name."""
        message = self._message.format(service)
        self._service = service
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(reason=str(self), context={'service': self._service})


class OperationNotAllowedError(CliParsingError):
    """Thrown when the given operation for a service is explicitely not allowed."""

    _message = 'The given operation is not allowed: {} {}'

    def __init__(self, service: str, operation: str):
        """Initialize OperationNotAllowedError with the service and operation name."""
        message = self._message.format(service, operation)
        self._service = service
        self._operation = operation
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(
            reason=str(self), context={'service': self._service, 'operation': self._operation}
        )


class InvalidServiceError(CliParsingError):
    """Thrown when the given service name does not exist."""

    _message = 'The given service name does not exist: {}'

    def __init__(self, service: str):
        """Initialize InvalidServiceError with the service name."""
        message = self._message.format(service)
        self._service = service
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(reason=str(self), context={'service': self._service})


class MissingOperationError(CliParsingError):
    """Thrown when the supplied command does not include an operation."""

    _message = (
        'Supplied command does not include an operation. '
        "Supply a command in format 'aws service operation'."
    )

    def __init__(self):
        """Initialize MissingOperationError."""
        super().__init__(self._message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(reason=str(self))


class InvalidServiceOperationError(CliParsingError):
    """Thrown when the operation for a service does not exist."""

    _message = 'The operation {operation!r} for service {service!r} does not exist.'

    def __init__(self, service: str, operation: str):
        """Initialize InvalidServiceOperationError with service and operation."""
        message = self._message.format(operation=operation, service=service)
        self._operation = operation
        self._service = service
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(
            reason=str(self), context={'service': self._service, 'operation': self._operation}
        )


class InvalidParametersReceivedError(CommandValidationError):
    """Thrown when the operation receives parameters it does not support."""

    _message = (
        'The operation {operation!r} for service {service!r} received '
        'parameters that it does not support: [{hallucinated_params!r}]. '
        'The correct parameters for this operation are [{params!r}].'
    )

    def __init__(
        self,
        service: str,
        operation: str,
        invalid_parameters: Iterable[str],
        correct_parameters: Iterable[str],
    ):
        """Initialize InvalidParametersReceivedError with details."""
        message = self._message.format(
            operation=operation,
            service=service,
            hallucinated_params=', '.join(invalid_parameters),
            params=', '.join(correct_parameters),
        )
        self._invalid_parameters = invalid_parameters
        self._correct_parameters = correct_parameters
        self._service = service
        self._operation = operation
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(
            reason=str(self),
            context={
                'service': self._service,
                'operation': self._operation,
                'invalid_parameters': self._invalid_parameters,
                'correct_parameters': self._correct_parameters,
            },
        )


class MissingRequiredParametersError(MissingContextError):
    """Thrown when required parameters are missing for a service operation."""

    _message = (
        'The following parameters are missing for service {service!r} '
        'and operation {operation!r}: {parameters!r}'
    )

    def __init__(
        self,
        service: str,
        operation: str,
        parameters: list[str],
        command_metadata: CommandMetadata,
    ):
        """Initialize MissingRequiredParametersError with details."""
        message = self._message.format(
            operation=operation, service=service, parameters=', '.join(parameters)
        )
        self._operation = operation
        self._service = service
        self._parameters = parameters
        super().__init__(message, command_metadata)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(
            reason=str(self),
            context={
                'service': self._service,
                'operation': self._operation,
                'parameters': self._parameters,
            },
        )


class MisspelledParametersError(CommandValidationError):
    """Thrown when an unknown parameter is similar to an existing one (possible typo)."""

    _message = (
        'Unknown parameter {unknown_parameter!r} for {service!r} and operation {operation!r}, '
        'did you mean {existing_parameter!r}?'
    )

    def __init__(
        self, service: str, operation: str, unknown_parameter: str, existing_parameter: str
    ):
        """Initialize MisspelledParametersError with details."""
        message = self._message.format(
            service=service,
            operation=operation,
            unknown_parameter=unknown_parameter,
            existing_parameter=existing_parameter,
        )
        self._unknown_parameter = unknown_parameter
        self._existing_parameter = existing_parameter
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(
            reason=str(self),
            context={
                'unknown_parameter': self._unknown_parameter,
                'existing_parameter': self._existing_parameter,
            },
        )


class UnknownArgumentsError(CommandValidationError):
    """Thrown when the operation receives unknown extra arguments."""

    _message = (
        'The operation {operation!r} for service {service!r} received '
        'unknown extra arguments: {unknown_args!r}. '
        'These arguments are not supported, so they should be removed.'
    )

    def __init__(
        self,
        service: str,
        operation: str,
        unknown_args: Iterable[str],
    ):
        """Initialize UnknownArgumentsError with details."""
        message = self._message.format(
            operation=operation,
            service=service,
            unknown_args=unknown_args,
        )
        self._unknown_args = unknown_args
        self._service = service
        self._operation = operation
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(
            reason=str(self),
            context={
                'service': self._service,
                'operation': self._operation,
                'unknown_args': self._unknown_args,
            },
        )


class DeniedGlobalArgumentsError(CommandValidationError):
    """Thrown when a global argument is denied for a service."""

    _message = 'The following global argument for service {service!r} cannot be set: {args!r}'

    def __init__(self, service: str, args: list[str]):
        """Initialize DeniedGlobalArgumentsError with service and denied args."""
        message = self._message.format(service=service, args=', '.join(args))
        self._args = args
        self._service = service
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(
            reason=str(self),
            context={
                'service': self._service,
                'args': self._args,
            },
        )


class UnknownFiltersError(CommandValidationError):
    """Thrown when invalid filters are provided for a service."""

    _message = 'The following filters are invalid for the {service!r}: {filters!r}'

    def __init__(self, service: str, filters: list[str]):
        """Initialize UnknownFiltersError with service and invalid filters."""
        message = self._message.format(service=service, filters=', '.join(filters))
        self._filters = filters
        self._service = service
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(
            reason=str(self),
            context={
                'service': self._service,
                'filters': self._filters,
            },
        )


class UnsupportedFilterError(CommandValidationError):
    """Thrown when a filter key combination is not supported."""

    _message = 'The following filter key combination is not currently supported: {keys!r}'

    def __init__(self, service: str, operation: str, keys: Set[str]):
        """Initialize UnsupportedFilterError with service, operation, and keys."""
        message = self._message.format(keys=sorted(keys))
        self._keys = keys
        self._operation = operation
        self._service = service
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(
            reason=str(self),
            context={
                'service': self._service,
                'operation': self._operation,
                'keys': sorted(self._keys),
            },
        )


class MalformedFilterError(CommandValidationError):
    """Thrown when filter keys do not match expected keys."""

    _message = "Filter keys {keys!r} don't match expected keys: {expected_keys!r}"

    def __init__(self, service: str, operation: str, keys: Set[str], expected_keys: Set[str]):
        """Initialize MalformedFilterError with details."""
        message = self._message.format(keys=sorted(keys), expected_keys=sorted(expected_keys))
        self._service = service
        self._operation = operation
        self._keys = frozenset(keys)
        self._expected_keys = frozenset(expected_keys)
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(
            reason=str(self),
            context={
                'service': self._service,
                'operation': self._operation,
                'keys': sorted(self._keys),
                'expected_keys': sorted(self._expected_keys),
            },
        )


class InvalidTypeForParameterError(CommandValidationError):
    """Thrown when a parameter receives an invalid type."""

    _message = 'The parameter {parameter!r} received an invalid type, must be of type {type!r}'

    def __init__(self, parameter: str, param_type: Callable[[str], Any] | FileType | None):
        """Initialize InvalidTypeForParameterError with parameter and type."""
        message = self._message.format(parameter=parameter, type=param_type)
        self._parameter = parameter
        self._param_type = param_type
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(
            reason=str(self), context={'parameter': self._parameter, 'type': self._param_type}
        )


class ExpectedArgumentError(MissingContextError):
    """Thrown when a required argument is missing or invalid."""

    _message = 'Failed handling {parameter!r}: {msg!r}'

    def __init__(self, parameter: str, msg: str, command_metadata: CommandMetadata):
        """Initialize ExpectedArgumentError with parameter, message, and metadata."""
        message = self._message.format(parameter=parameter, msg=msg)
        self._parameter = parameter
        self._msg = msg
        super().__init__(message, command_metadata)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(reason=str(self), context={'parameter': self._parameter, 'msg': self._msg})


class ShortHandParserError(CommandValidationError):
    """Thrown when there is an error parsing a shorthand parameter."""

    _message = "Error parsing parameter '{param}': {msg}"

    def __init__(self, parameter: str, msg: str):
        """Initialize ShortHandParserError with parameter and message."""
        message = self._message.format(param=parameter, msg=msg)
        self._parameter = parameter
        self._msg = msg
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(reason=str(self), context={'parameter': self._parameter, 'msg': self._msg})


@dataclasses.dataclass(frozen=True)
class ParameterValidationErrorRecord:
    """Record for parameter validation errors."""

    parameter: str
    reason: str

    def format_message(self):
        """Format the error message for this parameter validation error."""
        return f'The parameter {self.parameter!r} received an invalid input: {self.reason}'


class ParameterSchemaValidationError(CommandValidationError):
    """Thrown when parameter schema validation fails."""

    def __init__(self, errors: Iterable[ParameterValidationErrorRecord]):
        """Initialize ParameterSchemaValidationError with a list of errors."""
        message = '\n'.join(e.format_message() for e in errors)
        self._parameters = [e.parameter for e in errors]
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(reason=str(self), context={'parameters': self._parameters})


class RequestSerializationError(CommandValidationError):
    """Thrown when there is an error serializing a request."""

    _message = 'Error serializing request: {msg}'

    def __init__(self, service: str, operation: str, msg: str):
        """Initialize RequestSerializationError with service, operation, and message."""
        message = self._message.format(msg=msg)
        self._service = service
        self._operation = operation
        self._msg = msg
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(
            reason=str(self),
            context={'service': self._service, 'operation': self._operation, 'msg': self._msg},
        )


class ClientSideFilterError(CommandValidationError):
    """Thrown when JMESPATH expression of the client-side filter could not be parsed."""

    _message = "Error parsing client-side filter '{client_side_query}': {msg}"

    def __init__(self, service: str, operation: str, client_side_query: str, msg: str):
        """Initialize ClientSideFilterError with details."""
        message = self._message.format(client_side_query=client_side_query, msg=msg)
        self._service = service
        self._operation = operation
        self._client_side_query = client_side_query
        self._msg = msg
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(
            reason=str(self),
            context={
                'service': self._service,
                'operation': self._operation,
                'client_side_query': self._client_side_query,
                'msg': self._msg,
            },
        )


class FileParameterError(CommandValidationError):
    """Thrown when file parameters have validation issues (streaming files, relative paths, etc.)."""

    _message = (
        'Invalid file parameter {file_path!r} for service {service!r} and operation {operation!r}: {reason}. '
        'Please provide a valid file path.'
    )

    def __init__(self, service: str, operation: str, file_path: str, reason: str):
        """Initialize FileParameterError with service, operation, file path, and reason."""
        message = self._message.format(
            service=service, operation=operation, file_path=file_path, reason=reason
        )
        self._service = service
        self._operation = operation
        self._file_path = file_path
        self._reason = reason
        super().__init__(message)

    def as_failure(self) -> Failure:
        """Return a Failure object representing this error."""
        return Failure(
            reason=str(self),
            context={
                'service': self._service,
                'operation': self._operation,
                'file_path': self._file_path,
                'reason': self._reason,
            },
        )
