#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
# because boto3 client doesn't have any type hinting
import boto3
import botocore.session
import inspect
import os
import sys
from botocore.exceptions import ClientError
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Annotated, Any, Callable, Dict, List


# Defining type alias
BOTO3_CLIENT_GETTER = Callable[[str], Any]
OVERRIDE_FUNC_TYPE = Callable[[FastMCP, BOTO3_CLIENT_GETTER, str], None]
VALIDATOR = Callable[[FastMCP, Any, Dict[str, Any]], tuple[bool, str | None]]


class AWSToolGenerator:
    """Generic AWS Service Tool that can be used for any AWS service."""

    def __init__(
        self,
        service_name: str,
        service_display_name: str,
        mcp: FastMCP,
        tool_configuration: Dict[str, Dict[str, Any]] | None = None,
        skip_param_documentation: bool = False,
    ):
        """Initialize the AWS Service Tool.

        Args:
            service_name: The AWS service name (e.g., 'sns', 'sqs')
            service_display_name: Display name for the service (defaults to uppercase of service_name)
            mcp: The MCP server instance
            tool_configuration: Configuration for each tool
            skip_param_documentation: If True, parameter documentation will be skipped

        """
        self.service_name = service_name
        self.service_display_name = service_display_name or service_name.upper()
        self.mcp = mcp
        self.clients: Dict[str, Any] = {}
        self.tool_configuration = tool_configuration or {}
        self.skip_param_documentation = skip_param_documentation
        self.__validate_tool_configuration()

    def generate(self):
        """Augment the MCP server with tools derived from the boto3 client and tool configurations."""
        self.__register_operations()

    def get_mcp(self):
        """Return the MCP server instance."""
        return self.mcp

    def __register_operations(self):
        for operation in self.__get_operations():
            if operation not in self.tool_configuration:
                func = self.__create_operation_function(operation)
                if func is not None:
                    self.mcp.tool(description=func.__doc__)(func)
            else:
                config = self.tool_configuration[operation]
                if config.get('ignore'):
                    continue
                if config.get('func_override') is not None:
                    func_override = config.get('func_override')
                    if func_override is not None:  # Extra check to satisfy type checker
                        self.__handle_function_override(operation, func_override)
                    continue
                func = self.__create_operation_function(
                    operation,
                    config.get('name_override'),
                    config.get('documentation_override'),
                    config.get('validator'),
                )
                if func is not None:
                    self.mcp.tool(description=func.__doc__)(func)
                continue

    def __get_client(self, region: str = 'us-east-1') -> Any:
        """Get or create a service client for the specified region."""
        client_key = f'{self.service_name}_{region}'
        if client_key not in self.clients:
            aws_profile = os.environ.get('AWS_PROFILE', 'default')
            self.clients[client_key] = boto3.Session(
                profile_name=aws_profile, region_name=region
            ).client(self.service_name)
        return self.clients[client_key]

    def __get_operations(self) -> List[str]:
        """Get all available operations from boto3 for this service."""
        default_client = self.__get_client()
        operations = [
            op
            for op in dir(default_client)
            if not op.startswith('_') and callable(getattr(default_client, op))
        ]
        return sorted(operations)

    def __handle_function_override(
        self, operation: str, func_override: OVERRIDE_FUNC_TYPE
    ) -> None:
        """Handle overriding the behaviour of an operation by invoking user provided function. It will pass a boto3 client (default to us-east-1), current MCP server, and the current operation."""

        # A getter for the boto3 client
        def boto3_client_getter(region: str, service_name: str = self.service_name):
            aws_profile = os.environ.get('AWS_PROFILE', 'default')
            return boto3.Session(profile_name=aws_profile, region_name=region).client(service_name)

        func_override(self.mcp, boto3_client_getter, operation)

    def __create_operation_function(
        self,
        operation: str,
        name_override: str | None = None,
        documentation_override: str | None = None,
        validator: VALIDATOR | None = None,
    ) -> Callable | None:
        """Create a function for a specific service operation."""
        # Get information about parameters and their types
        parameters = []
        type_conversion = {
            'string': str,
            'boolean': bool,
            'integer': int,
            'map': dict[Any, Any],
        }
        try:
            input_parameters = self.__get_operation_input_parameters(operation)
            for param_tuple in input_parameters:
                param_name = param_tuple[0]
                param_type = param_tuple[1]
                param_is_required = param_tuple[2]
                param_documentation = param_tuple[3]
                if param_is_required:
                    parameters.insert(
                        0,
                        inspect.Parameter(
                            name=param_name,
                            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                            annotation=type_conversion.get(param_type, str),
                        ),
                    )
                else:
                    parameters.append(
                        inspect.Parameter(
                            name=param_name,
                            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                            annotation=Annotated[
                                type_conversion.get(param_type, str) | None,
                                Field(description=param_documentation),
                            ],
                            default=None,
                        )
                    )
            # Add region to dynamically change region such that one MCP server can interact with multiple region
            parameters.append(
                inspect.Parameter(
                    name='region',
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=Annotated[str, Field(description='AWS region')],
                    default='us-east-1',
                )
            )
        except Exception:
            print(
                f'operation model for: {operation} not found, skipping tool creation',
                file=sys.stderr,
            )
            return None

        # Function template
        async def operation_function(*args, **kwargs) -> Dict[str, Any]:
            bound_args = operation_function.__signature__.bind(*args, **kwargs)
            bound_args.apply_defaults()
            try:
                # getting the client that correspond to the region
                client = self.__get_client(bound_args.arguments['region'])
                method = getattr(client, operation)
                kwargs = {k: v for k, v in bound_args.arguments.items() if v is not None}
                del kwargs['region']  # region is not a valid argument to the boto3 API
                if validator is not None:
                    status, msg = validator(self.mcp, client, kwargs)
                    if status is False:
                        return {'error': msg}
                response = method(**kwargs)
                if 'ResponseMetadata' in response:
                    del response['ResponseMetadata']
                return response
            except ClientError as e:
                error_message = e.response.get('Error', {}).get('Message', str(e))
                return {'error': error_message, 'code': e.response.get('Error', {}).get('Code')}
            except Exception as e:
                return {'error': str(e)}

        # Set function metadata
        operation_function.__name__ = (
            name_override if name_override is not None else f'{operation}'
        )
        # Set docstring of the tool which is used as part of the prompt for the LLM
        tool_description = (
            (f'Execute the AWS {self.service_display_name} `{operation}` operation.')
            if documentation_override is None
            else documentation_override
        )
        operation_function.__doc__ = tool_description
        sig = inspect.Signature(parameters)
        operation_function.__signature__ = sig

        return operation_function

    def __get_operation_input_parameters(
        self, operation_name: str
    ) -> List[tuple[str, str, bool, str]]:
        """Return a list of input parameter names for a given operation."""
        session = botocore.session.get_session()
        service_model = session.get_service_model(self.service_name)
        op_model = service_model.operation_model(self.__snake_to_camel(operation_name))
        input_shape = op_model.input_shape
        if not input_shape:
            return []
        res = []
        for param_name in input_shape.members.keys():
            param_shape = input_shape.members[param_name]
            # Skip documentation if flag is set
            if self.skip_param_documentation:
                param_documentation = ('',)
            else:
                param_documentation = (getattr(param_shape, 'documentation', ''),)
            is_required = param_name in input_shape.required_members
            res.append((param_name, param_shape.type_name, is_required, param_documentation))
        return res

    def __snake_to_camel(self, snake_str: str) -> str:
        return ''.join(word.capitalize() for word in snake_str.split('_'))

    # TODO: Rewrite this validation logic. It is messy
    def __validate_tool_configuration(self):
        for operation, configuration in self.tool_configuration.items():
            if (
                configuration.get('ignore') is True
                and configuration.get('func_override') is not None
            ):
                raise ValueError(
                    f'For tool {operation}, cannot specify both ignore=True and a function override'
                )
            if configuration.get('ignore') is True and (
                configuration.get('documentation_override') is not None
                and configuration.get('documentation_override') != ''
            ):
                raise ValueError(
                    f'For tool {operation}, cannot specify both ignore=True and a documentation override'
                )
            if (
                configuration.get('func_override') is not None
                and configuration.get('documentation_override') is not None
                and configuration.get('documentation_override') != ''
            ):
                raise ValueError(
                    f'For tool {operation}, cannot specify both func_override and a documentation override'
                )
            if (
                configuration.get('func_override') is None
                and configuration.get('name_override') is None
                and configuration.get('documentation_override') is None
                and configuration.get('ignore') is None
                and configuration.get('validator') is None
            ):
                raise ValueError(f'For tool {operation}, cannot specify empty override')
