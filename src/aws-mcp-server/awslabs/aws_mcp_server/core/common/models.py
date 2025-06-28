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

import dataclasses
import enum
from .command import IRCommand
from .command_metadata import CommandMetadata
from .errors import Failure
from pydantic import BaseModel, Field
from typing import Any


class ProgramValidationRequest(BaseModel):
    """The request structure for the validation endpoint."""

    cli_command: str
    """An AWS CLI command which will be validated"""


class Context(BaseModel):
    """Context for a validation or interpretation failure."""

    service: str | None
    operation: str | None
    operators: list[str] | None = None
    region: str | None = None
    args: list[str] | None = None
    parameters: list[str] | None = None


class ValidationFailure(BaseModel):
    """Represents a validation failure."""

    reason: str
    context: Context | None


class InterpretationMetadata(BaseModel):
    """Metadata for an interpretation, including service and operation details."""

    service: str | None
    service_full_name: str | None
    operation: str | None
    region_name: str | None = None


class ProgramClassificationMetadata(BaseModel):
    """The API type (management, data).

    Management refers to control plane operations in CloudTrail's parlance.
    Data refers to data plane operations in CloudTrail's parlance
    """

    api_type: str | None

    action_types: list[str] | None
    """The action type of the program

    The action type defines if the program is read-only or has updates
    or has creates etc.
    """


class ProgramValidationResponse(BaseModel):
    """Response for a program validation request."""

    validation_failures: list[ValidationFailure] | None
    missing_context_failures: list[ValidationFailure] | None
    classification: ProgramClassificationMetadata | None
    failed_constraints: list[str] | None = Field(None)

    @property
    def validation_failed(self) -> bool:
        """Return True if validation failed."""
        return (
            self.validation_failures is not None
            and len(self.validation_failures) > 0
            or self.failed_constraints is not None
            and len(self.failed_constraints) > 0
        )


class RequireConsentResponse(BaseModel):
    """Response indicating whether explicit user consent is required."""

    status: str
    message: str


class Credentials(BaseModel):
    """Credentials model.

    See structure in https://sdk.amazonaws.com/java/api/latest/software/amazon/awssdk/auth/credentials/AwsSessionCredentials.html
    """

    access_key_id: str
    secret_access_key: str
    session_token: str | None


class ProgramInterpretationRequest(BaseModel):
    """The request structure for the interpretation endpoint."""

    cli_command: str
    """An AWS CLI Command which will be validated and interpreted"""

    credentials: Credentials
    """Credentials that will be assumed to interpret the command"""

    default_region: str
    """Default region that will be used if provided cli command doesn't have region set"""

    max_results: int | None = Field(default=None)
    """Limit the number of results if the operation supports limiting"""

    max_tokens: int | None = Field(default=None)
    """Limit the number of results to the specified amount of LLM tokens if the operation supports limiting"""

    is_counting: bool | None = Field(default=None)
    """Support resource counting"""


class InterpretationResponse(BaseModel):
    """The response structure for the result of the interpretation."""

    error: str | None
    """Field containing service error on failures"""

    status_code: int | None = Field(default=None)
    """Field containing the status code of the underlying API call"""

    error_code: str | None = Field(default=None)
    """Field containing the error code of the underlying API call"""

    pagination_token: str | None = Field(default=None)
    """Field containing the pagination token returned by the underlying API call"""

    as_json: str | None = Field(default=None, alias='json')
    """Raw version of the response from interpreting the command"""


class ProgramInterpretationResponse(BaseModel):
    """Payload for the interpretation endpoint."""

    response: InterpretationResponse | None = Field(None)
    metadata: InterpretationMetadata | None = Field(default=None)
    validation_failures: list[ValidationFailure] | None = Field(default=None)
    missing_context_failures: list[ValidationFailure] | None = Field(default=None)
    failed_constraints: list[str] | None = Field(default=None)


class ActionType(enum.Enum):
    """Model an action type.

    Actions can be classified into multiple sub-actions, each with their
    own type. For instance, a single CLI command can be read-only (list, describe)
    or a mutation (create, delete, update). Multiple commands can have a mixture of action types.
    """

    READ_ONLY = 'read-only'
    MUTATING = 'mutating'
    UNKNOWN = 'unknown'


class ApiType(enum.Enum):
    """The API type of given action(management, data).

    Management refers to control plane operations in CloudTrail's parlance.
    Data refers to data plane operations in CloudTrail's parlance
    """

    MANAGEMENT = 'management'
    DATA = 'data'
    UNKNOWN = 'unknown'


@dataclasses.dataclass(frozen=True)
class CommandClassification:
    """The classification of a command in action types and api types."""

    action_types: list[ActionType]
    api_type: ApiType

    def as_metadata(self):
        """Return the classification as a metadata dictionary."""
        return {
            'api_type': self.api_type.value,
            'action_types': [action_type.value for action_type in self.action_types],
        }


UnknownClassification = CommandClassification(
    action_types=[ActionType.UNKNOWN], api_type=ApiType.UNKNOWN
)


@dataclasses.dataclass(frozen=True)
class IRTranslation:
    """Represents the results of validation and translation to intermediate representation."""

    """Contains a translated command if the validation was successful"""
    command: IRCommand | None = None

    """Contains a command metadata if translation was successful"""
    command_metadata: CommandMetadata | None = None

    """A Python program that was translated from a given CLI command"""
    program: str | None = None

    """The clasification for this command"""
    classification: CommandClassification | None = None

    """Validation reasons why the program could not be translated

    These are validation errors that occur due to the command parts
    being invalid or not acceptable (for instance, the AWS command
    does not exist or the parameters have been hallucinated).
    """
    validation_failures: list[Failure] | None = None

    """Reasons why the program could not be translated to the target language

    The command is valid but it require more details than what was provided
    (e.g. missing parameters)
    """
    missing_context_failures: list[Failure] | None = None

    unsupported_translation: Failure | None = None

    @property
    def validation_or_translation_failures(self) -> list[Failure] | None:
        """Return validation or translation failures, if any."""
        if self.unsupported_translation:
            return [self.unsupported_translation]
        return self.validation_failures

    def __eq__(self, other):
        """Return True if this IRTranslation is equal to another."""
        if not isinstance(other, IRTranslation):
            return False
        return (
            self.validation_failures == other.validation_failures
            and self.missing_context_failures == other.missing_context_failures
            and _normalize_program(self.program or '') == _normalize_program(other.program or '')
        )


@dataclasses.dataclass(frozen=True)
class InterpretedProgram:
    """Translation from CLI to intermediate representation."""

    translation: IRTranslation

    """The response as a json payload from interpreting the IR"""
    response: str | None = None

    """An underlying error response from interacting with the service"""
    service_error: str | None = None

    """The response status code from interacting with the service"""
    status_code: int | None = None

    """Error code from interacting with the service"""
    error_code: str | None = None

    """The pagination token returned by paginated APIs"""
    pagination_token: str | None = None

    """List of constraints that failed validation on the underlying intermediate representation"""
    failed_constraints: list[str] | None = None

    """The region where program is interpreted"""
    region_name: str | None = None

    @property
    def as_dict(self) -> dict[str, Any]:
        """Return the dataclass as a dictionary."""
        return dataclasses.asdict(self)


def _normalize_program(str) -> list[str]:
    return [line.strip() for line in str.splitlines() if line.strip()]
