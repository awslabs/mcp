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

import argparse
import botocore.serialize
import re
from ..aws.regions import GLOBAL_SERVICE_REGIONS
from ..aws.services import (
    driver,
    get_operation_filters,
    session,
)
from ..common.command import IRCommand
from ..common.command_metadata import CommandMetadata
from ..common.errors import (
    AwsMcpError,
    CommandValidationError,
    DeniedGlobalArgumentsError,
    ExpectedArgumentError,
    InvalidChoiceForParameterError,
    InvalidCustomCommandError,
    InvalidParametersReceivedError,
    InvalidServiceError,
    InvalidServiceOperationError,
    InvalidTypeForParameterError,
    InvalidUseOfS3ServiceError,
    MalformedFilterError,
    MissingOperationError,
    MissingRequiredParametersError,
    MisspelledParametersError,
    ParameterSchemaValidationError,
    ParameterValidationErrorRecord,
    RequestSerializationError,
    ShortHandParserError,
    UnknownArgumentsError,
    UnknownFiltersError,
    UnsupportedFilterError,
)
from .custom_validators.botocore_param_validator import BotoCoreParamValidator
from .custom_validators.ec2_validator import validate_ec2_parameter_values
from .custom_validators.ssm_validator import perform_ssm_validations
from .lexer import split_cli_command
from argparse import Namespace
from awscli.argparser import ArgTableArgParser, CommandAction, MainArgParser
from awscli.argprocess import ParamError
from awscli.arguments import BaseCLIArgument, CLIArgument
from awscli.clidriver import ServiceCommand
from awscli.customizations.commands import BasicCommand
from botocore.exceptions import ParamValidationError, UndefinedModelAttributeError
from botocore.model import OperationModel, ServiceModel
from collections.abc import Generator
from difflib import SequenceMatcher
from typing import Any, NamedTuple, cast


ARN_PATTERN = re.compile(
    r'^(arn:(?:aws|aws-cn|aws-us-gov):[\w\d-]+:([\w\d-]*):\d{0,12}:[\w\d-]*\/?[\w\d-]*)(\/.*)?.*$'
)

# These are subcommands for `aws` which are not actual services.
# They are not ServiceCommand instances. The other example of a non-ServiceCommand
# is the fake "s3" service, which is handled properly.
_denied_custom_services = frozenset({'configure', 'history'})

_excluded_optional_params = frozenset(
    {
        '--cli-input-json',
        '--generate-cli-skeleton',
        '--dry-run',
        '--no-dry-run',
    }
)

NARGS_ONE_ARGUMENT = None
NARGS_OPTIONAL = '?'
NARGS_ONE_OR_MORE = '+'

# Map nargs (number of time arguments can appear from argparse point of view)
# to the corresponding error. These are implicitly defined in argparse.
_nargs_errors = {
    NARGS_ONE_ARGUMENT: 'expected one argument',
    NARGS_OPTIONAL: 'expected at most one argument',
    NARGS_ONE_OR_MORE: 'expected at least one argument',
}

ALLOWED_FILTER_KEYS_SUBSETS = {
    frozenset({'Name', 'Values'}): 'Name',
    frozenset({'Key', 'Values'}): 'Key',
    frozenset({'key', 'value'}): 'key',
}


class ParsedOperationArgs(NamedTuple):
    """Named tuple to store parsed operation arguments and their classification."""

    operation_args: Namespace
    supported_args: list[str]
    given_args: list[str]
    missing_parameters: list[str]
    unknown_parameters: list[str]
    unknown_args: list[str]


def _on_error_in_argparse(message: str):
    raise AwsMcpError(message)


class ArgTableParser(ArgTableArgParser):
    """Parser for argument tables, supporting AWS CLI command metadata."""

    def parse_operation_args(self, command_metadata: CommandMetadata, args: list[str]):
        """Parse known arguments using the provided command metadata and argument list."""
        self.command_metadata = command_metadata
        operation_args, unknown_args = super().parse_known_args(args)

        supported_args = [
            action.option_strings[0] for action in self._actions if action.option_strings
        ]

        missing_parameters = list(self._identify_missing_parameters(operation_args))

        return ParsedOperationArgs(
            operation_args=operation_args,
            supported_args=supported_args,
            given_args=args,
            missing_parameters=missing_parameters,
            unknown_parameters=[
                param
                for param in unknown_args
                if param.startswith('-')
                and param not in supported_args
                and not any(arg.startswith(param) for arg in supported_args if self.allow_abbrev)
            ],
            unknown_args=[param for param in unknown_args if not param.startswith('-')],
        )

    def _check_if_misspelled(self, service, operation, supported_args, unknown_args):
        for unknown_arg in unknown_args:
            if unknown_arg.startswith('--'):
                for supported_arg in supported_args:
                    similarity = SequenceMatcher(None, supported_arg, unknown_arg).ratio()
                    if similarity >= 0.8:
                        raise MisspelledParametersError(
                            service=service,
                            operation=operation,
                            unknown_parameter=unknown_arg,
                            existing_parameter=supported_arg,
                        )

    def error(self, message):  # type: ignore[override]
        """Handle errors during argument parsing."""
        # Skip throwing errors to collate all fields that are missing/not recognized
        pass

    def _identify_missing_parameters(self, operation_args: Namespace) -> Generator[str]:
        required_args = {
            action.option_strings[0]
            for action in self._actions
            if action.option_strings and action.required
        }
        for name, value in vars(operation_args).items():
            if value is None:
                cli_param = f'--{name.replace("_", "-")}'
                if cli_param in required_args:
                    yield cli_param

    def _get_value(self, action, arg_string):
        try:
            return super()._get_value(action, arg_string)
        except argparse.ArgumentError as exc:
            raise InvalidTypeForParameterError(action.option_strings[0], action.type) from exc  # type: ignore

    def _match_argument(self, action, arg_strings_pattern):
        try:
            return super()._match_argument(action, arg_strings_pattern)
        except argparse.ArgumentError as exc:
            msg: str = _fetch_error_from_number_of_args(action.nargs)  # type: ignore
            raise ExpectedArgumentError(
                action.option_strings[0], msg, self.command_metadata
            ) from exc


def _fetch_error_from_number_of_args(nargs: str) -> str:
    return cast(str, _nargs_errors.get(nargs))


class GlobalArgParser(MainArgParser):
    """Parser for global AWS CLI arguments."""

    def _check_value(self, action, value):
        """Check if the value is valid for the given action."""
        if action.choices is not None and value not in action.choices:
            if action.dest == 'command':
                # This service does not exist. The command table contains service aliases
                # as well (e.g. `s3` is not an actual "service" in the underlying model, `s3api` is.
                raise InvalidServiceError(value)
            raise InvalidChoiceForParameterError(action.dest, value)
        return super()._check_value(action, value)

    # Overwrite _build's parent method as it automatically injects a `version` action in the
    # parser. Version actions print the current version and then exit the program, which is
    # not what we want.
    def _build(self, command_table, version_string, argument_table):
        for argument_name in argument_table:
            argument = argument_table[argument_name]
            argument.add_to_parser(self)
        self.add_argument('--version')
        self.add_argument('command', action=CommandAction, command_table=command_table)

    @staticmethod
    def get_parser():
        """Return a new instance of GlobalArgParser."""
        return GlobalArgParser(
            command_table,
            session.user_agent(),
            cli_data.get('description', None),
            driver._get_argument_table(),
            prog='aws',
        )

    def error(self, message):  # type: ignore[override]
        """Handle errors in global argument parsing."""
        _on_error_in_argparse(message)


command_table = driver._get_command_table()
cli_data = driver._get_cli_data()
parser = GlobalArgParser.get_parser()
driver._add_aliases(command_table, parser)


def parse(cli_command: str) -> IRCommand:
    """Parse a CLI command string into an IRCommand object."""
    tokens = split_cli_command(cli_command)
    # Strip `aws`
    tokens = tokens[1:]
    global_args, remaining = parser.parse_known_args(tokens)
    service_command = command_table[global_args.command]

    # Not all commands have parsers as some of them are "aliases" to existing services
    if isinstance(service_command, ServiceCommand):
        return _handle_service_command(service_command, global_args, remaining)

    return _handle_custom_command(service_command)


def _handle_service_command(
    service_command: ServiceCommand,
    global_args: argparse.Namespace,
    remaining: list[str],
):
    if not remaining:
        raise MissingOperationError()

    service = service_command.name
    command_table = service_command._get_command_table()

    operation = remaining[0]
    operation_command = command_table.get(operation)
    if not operation_command:
        # This command is not supported for this service
        raise InvalidServiceOperationError(service, operation)
    if not hasattr(operation_command, '_operation_model'):
        raise InvalidCustomCommandError(service, operation)
    command_metadata = CommandMetadata(
        service_sdk_name=service_command.service_model.service_name,
        service_full_sdk_name=_service_full_name(service_command.service_model),
        operation_sdk_name=operation_command._operation_model.name,
        has_streaming_output=operation_command._operation_model.has_streaming_output,
    )
    _validate_global_args(service, global_args)
    region = getattr(global_args, 'region', None)

    service_parser = service_command._create_parser()
    service_args, service_remaining = service_parser.parse_known_args(remaining)
    operation_parser = ArgTableParser(operation_command.arg_table)
    parsed_args = operation_parser.parse_operation_args(command_metadata, service_remaining)
    _handle_invalid_parameters(command_metadata, service, operation, parsed_args)

    try:
        parameters = operation_command._build_call_parameters(
            parsed_args.operation_args, operation_command.arg_table
        )
    except ParamError as exc:
        raise ShortHandParserError(exc.cli_name, exc.message) from exc
    except Exception as exc:
        raise CommandValidationError(exc) from exc

    _validate_filters(
        service_command.service_model.service_name,
        operation,
        operation_command._operation_model,
        parameters,
    )

    _validate_parameters(parameters, operation_command.arg_table)

    arn_region = _fetch_region_from_arn(parameters)
    global_args.region = region or arn_region
    if (
        command_metadata.service_sdk_name in GLOBAL_SERVICE_REGIONS
        and global_args.region != GLOBAL_SERVICE_REGIONS[command_metadata.service_sdk_name]
    ):
        global_args.region = GLOBAL_SERVICE_REGIONS[command_metadata.service_sdk_name]

    _validate_request_serialization(
        operation,
        service_command.service_model,
        operation_command._operation_model,
        parameters,
    )

    _run_custom_validations(
        service_command.service_model.service_name,
        operation,
        parameters,
    )
    return _construct_command(
        command_metadata=command_metadata,
        global_args=global_args,
        parameters=parameters,
    )


def _handle_custom_command(
    service_command: BasicCommand,
):
    if service_command.name in _denied_custom_services:
        raise InvalidServiceError(service_command.name)
    if service_command.name == 's3':
        # S3 commands boil down to Python classes which result in multiple S3 API calls
        # We cannot deterministically translate these to single S3 API calls.
        raise InvalidUseOfS3ServiceError(service_command.name)
    raise NotImplementedError('Not implemented yet')


def _handle_invalid_parameters(
    command_metadata: CommandMetadata,
    service: str,
    operation: str,
    parsed_args: ParsedOperationArgs,
):
    # Exclude a set of parameters that are not supported
    supported_parameters_with_exclusions = (
        set(parsed_args.supported_args) - _excluded_optional_params
    )

    if parsed_args.unknown_parameters:
        raise InvalidParametersReceivedError(
            service=service,
            operation=operation,
            invalid_parameters=sorted(parsed_args.unknown_parameters),
            correct_parameters=sorted(supported_parameters_with_exclusions),
        )
    if parsed_args.missing_parameters:
        raise MissingRequiredParametersError(
            service=service,
            operation=operation,
            parameters=parsed_args.missing_parameters,
            command_metadata=command_metadata,
        )
    if parsed_args.unknown_args:
        raise UnknownArgumentsError(
            service=service,
            operation=operation,
            unknown_args=parsed_args.unknown_args,
        )


def _validate_global_args(service: str, global_args: argparse.Namespace):
    denied_args = []
    if global_args.debug:
        denied_args.append('--debug')
    if global_args.endpoint_url:
        denied_args.append('--endpoint-url')
    if not global_args.verify_ssl:
        denied_args.append('--no-verify-ssl')
    if not global_args.sign_request:
        denied_args.append('--no-sign-request')
    if denied_args:
        raise DeniedGlobalArgumentsError(service, sorted(denied_args))


def _validate_parameters(
    parameters: dict[str, Any],
    arg_table: dict[str, BaseCLIArgument],
) -> None:
    validator = BotoCoreParamValidator()
    param_name_to_arg = {
        arg._serialized_name: arg for arg in arg_table.values() if isinstance(arg, CLIArgument)
    }
    errors = []
    for key, value in parameters.items():
        cli_argument = param_name_to_arg.get(key)
        if not cli_argument or not cli_argument.argument_model:
            continue
        report = validator.validate(value, cli_argument.argument_model)
        if report.has_errors():
            errors.append(
                ParameterValidationErrorRecord(cli_argument.cli_name, report.generate_report())
            )
    if errors:
        raise ParameterSchemaValidationError(errors)


def _validate_filters(
    service: str, operation: str, operation_model: OperationModel, parameters: dict[str, Any]
):
    if 'Filters' not in parameters:
        return

    filters = parameters['Filters']
    known_filters = get_operation_filters(operation_model)

    filter_name_key = None
    for allowed_keys_subset, name_key in ALLOWED_FILTER_KEYS_SUBSETS.items():
        if allowed_keys_subset.issubset(known_filters.filter_keys):
            filter_name_key = name_key

    if filter_name_key is None:
        raise UnsupportedFilterError(service, operation, known_filters.filter_keys)

    unknown_filters = []
    for filter_element in filters:
        filter_element_key_set = filter_element.keys()
        if filter_element_key_set != known_filters.filter_keys:
            raise MalformedFilterError(
                service, operation, filter_element_key_set, known_filters.filter_keys
            )

        filter_name = filter_element.get(filter_name_key)
        if not known_filters.allows_filter(filter_name):
            unknown_filters.append(filter_name)

    if unknown_filters:
        raise UnknownFiltersError(service, sorted(unknown_filters))


def _run_custom_validations(service: str, operation: str, parameters: dict[str, Any]):
    if service == 'ssm':
        perform_ssm_validations(operation, parameters)
    if service == 'ec2':
        validate_ec2_parameter_values(parameters)


def _validate_request_serialization(
    operation: str,
    service_model: ServiceModel,
    operation_model: OperationModel,
    parameters: dict[str, Any],
):
    validated_parameters = parameters.copy()
    validated_parameters.pop('PaginationConfig', None)

    # Parameter validation has been done, just serialize
    serializer = botocore.serialize.create_serializer(
        service_model.metadata['protocol'], include_validation=False
    )
    try:
        serializer.serialize_to_request(validated_parameters, operation_model)
    except ParamValidationError as err:
        raise RequestSerializationError(
            str(service_model.service_name), operation, str(err)
        ) from err


def _fetch_region_from_arn(parameters: dict[str, Any]) -> str | None:
    for param_value in parameters.values():
        if isinstance(param_value, str):
            m = ARN_PATTERN.match(param_value)
            if m and m.groups()[1]:
                return m.groups()[1]
    return None


def _construct_command(
    command_metadata: CommandMetadata,
    global_args: argparse.Namespace,
    parameters: dict[str, Any],
) -> IRCommand:
    # Verify the service actually exists in this region
    region = getattr(global_args, 'region', None)
    if region is None:
        region = _fetch_region_from_arn(parameters)
    client_side_query = getattr(global_args, 'query', None)

    return IRCommand(
        command_metadata=command_metadata,
        parameters=parameters,
        region=region,
        client_side_query=client_side_query,
    )


def _service_full_name(service_model: ServiceModel) -> str | None:
    try:
        return service_model._get_metadata_property('serviceFullName')
    except UndefinedModelAttributeError:
        return None
