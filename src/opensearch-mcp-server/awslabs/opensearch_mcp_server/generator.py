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
import botocore.session
import inspect
import os
import sys
from botocore.config import Config
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
        mcp_server_version: str,
        tool_configuration: Dict[str, Dict[str, Any]] | None = None,
        skip_param_documentation: bool = False,
    ):
        """Initialize the AWS Service Tool.

        Args:
            service_name: The AWS service name (e.g., 'opensearch', 'opensearchserverless')
            service_display_name: Display name for the service (defaults to uppercase of service_name)
            mcp: The MCP server instance
            mcp_server_version: The mcp server version used which will be passed in to the boto3 clients
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
        self.config = Config(
            user_agent_extra=f'awslabs/mcp/{self.service_name}/{mcp_server_version}'
        )

    def generate(self):
        """Augment the MCP server with tools derived from the boto3 client and tool configurations."""
        self.__register_operations()

    def get_mcp(self):
        """Return the MCP server instance."""
        return self.mcp

    def __register_operations(self):
        for operation in self.__get_operations():
            config = self.tool_configuration.get(operation)
            if config is None or not config.get('supported', False):
                continue
            func = self.__create_operation_function(
                operation, config.get('name_override'), config.get('documentation_override')
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
            ).client(service_name=self.service_name, config=self.config)
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

    def __create_operation_function(
        self,
        operation: str,
        name_override: str | None = None,
        documentation_override: str | None = None,
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
                param_documentation = ''
            else:
                param_documentation = getattr(param_shape, 'documentation', '')
            is_required = param_name in input_shape.required_members
            res.append((param_name, param_shape.type_name, is_required, param_documentation))
        return res

    def __snake_to_camel(self, snake_str: str) -> str:
        return ''.join(word.capitalize() for word in snake_str.split('_'))

    def __validate_tool_configuration(self):
        for operation, configuration in self.tool_configuration.items():
            if configuration.get('supported', False) is False:
                raise ValueError(f'Tool {operation} is not supported')
