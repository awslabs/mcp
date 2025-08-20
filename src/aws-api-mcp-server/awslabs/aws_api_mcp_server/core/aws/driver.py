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
import botocore.exceptions
from ..common.errors import (
    CliParsingError,
    CommandValidationError,
    MissingContextError,
)
from ..common.helpers import as_json
from ..common.models import Credentials, InterpretedProgram, IRTranslation
from ..parser.interpretation import interpret
from ..parser.parser import parse
from .regions import GLOBAL_SERVICE_REGIONS
from awslabs.aws_api_mcp_server.core.common.config import AWS_API_MCP_PROFILE_NAME
from botocore.exceptions import NoCredentialsError


def get_local_credentials(profile: str | None = None) -> Credentials:
    """Get the local credentials for AWS profile."""
    if profile is not None:
        session = boto3.Session(profile_name=profile)
    else:
        session = boto3.Session()
    aws_creds = session.get_credentials()

    if aws_creds is None:
        raise NoCredentialsError()

    return Credentials(
        access_key_id=aws_creds.access_key,
        secret_access_key=aws_creds.secret_key,
        session_token=aws_creds.token,
    )


def translate_cli_to_ir(cli_command: str) -> IRTranslation:
    """Translate the given CLI command to a Python program.

    The returned payload contains the final Python program
    if the translation was successful or reasons on why
    the translation could not happen.

    Failure reasons have two categories: syntactical (usually
    cased by LLM hallucinations) and validations (usually
    due to a lack of required parameters or invalid parameter
    values).

    Syntactical errors can be used for a refinement loop, while validations
    errors can be used to ask for more clarification from the end-user.
    """
    try:
        command = parse(cli_command)
    except (CliParsingError, CommandValidationError) as exc:
        return IRTranslation(validation_failures=[exc.as_failure()])
    except MissingContextError as exc:
        return IRTranslation(
            missing_context_failures=[exc.as_failure()],
            command_metadata=exc.command_metadata,
        )

    return IRTranslation(
        command=command,
        command_metadata=command.command_metadata,
    )


def interpret_command(
    cli_command: str,
    max_results: int | None = None,
) -> InterpretedProgram:
    """Interpret the CLI command.

    The interpretation validates the CLI command and translates it
    to an intermediate representation that can be interpreted.

    The response contains any validation errors found during
    validating the command, as well as any errors that occur during interpretation.
    """
    translation = translate_cli_to_ir(cli_command)

    if translation.command is None:
        return InterpretedProgram(translation=translation)

    region = translation.command.region
    if (
        translation.command.command_metadata.service_sdk_name in GLOBAL_SERVICE_REGIONS
        and region != GLOBAL_SERVICE_REGIONS[translation.command.command_metadata.service_sdk_name]
    ):
        region = GLOBAL_SERVICE_REGIONS[translation.command.command_metadata.service_sdk_name]

    credentials = get_local_credentials(
        profile=translation.command.profile or AWS_API_MCP_PROFILE_NAME
    )

    try:
        response = interpret(
            translation.command,
            access_key_id=credentials.access_key_id,
            secret_access_key=credentials.secret_access_key,
            session_token=credentials.session_token,
            region=region,
            client_side_filter=translation.command.client_side_filter,
            max_results=max_results,
        )
    except botocore.exceptions.ClientError as error:
        service_error = str(error)
        status_code = error.response['ResponseMetadata']['HTTPStatusCode']
        error_code = error.response['Error']['Code']
        return InterpretedProgram(
            translation=translation,
            service_error=service_error,
            status_code=status_code,
            error_code=error_code,
            region_name=region,
        )

    payload = as_json(response)
    if (
        translation.command.region is None
        and translation.command.service_name == 's3'
        and translation.command.operation_python_name == 'list_buckets'
    ):
        region = 'Global'

    if (
        translation.command.service_name == 's3'
        and translation.command.operation_python_name == 'get_bucket_location'
    ):
        region = response['LocationConstraint']

    return InterpretedProgram(
        translation=translation,
        response=payload,
        status_code=response['ResponseMetadata']['HTTPStatusCode'],
        region_name=region,
        pagination_token=response.get('pagination_token'),
    )
