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

"""Create Function tool for AWS AppSync MCP Server."""

from awslabs.aws_appsync_mcp_server.decorators import write_operation
from awslabs.aws_appsync_mcp_server.operations.create_function import create_function_operation
from mcp.types import ToolAnnotations
from pydantic import Field
from typing import Annotated, Dict, Optional


def register_create_function_tool(mcp):
    """Register the create_function tool with the MCP server."""

    @mcp.tool(
        name='create_function',
        description="""Creates a Function object for a GraphQL API.

        This operation creates a function for the specified GraphQL API. Functions
        are reusable pieces of resolver logic that can be attached to multiple fields
        in your GraphQL schema.
        """,
        annotations=ToolAnnotations(
            title='Create Function', readOnlyHint=False, destructiveHint=False, openWorldHint=False
        ),
    )
    @write_operation
    async def create_function(
        api_id: Annotated[str, Field(description='The GraphQL API ID')],
        name: Annotated[str, Field(description='The Function name')],
        data_source_name: Annotated[str, Field(description='The Function DataSource name')],
        description: Annotated[
            Optional[str], Field(description='The Function description')
        ] = None,
        request_mapping_template: Annotated[
            Optional[str], Field(description='The Function request mapping template')
        ] = None,
        response_mapping_template: Annotated[
            Optional[str], Field(description='The Function response mapping template')
        ] = None,
        function_version: Annotated[
            Optional[str],
            Field(
                description='The version of the request mapping template. Currently, the supported value is 2018-05-29'
            ),
        ] = None,
        sync_config: Annotated[
            Optional[Dict], Field(description='Describes a Sync configuration for a resolver')
        ] = None,
        max_batch_size: Annotated[
            Optional[int], Field(description='The maximum batching size for a resolver')
        ] = None,
        runtime: Annotated[
            Optional[Dict],
            Field(
                description='Describes a runtime used by an AWS AppSync pipeline resolver or AWS AppSync function'
            ),
        ] = None,
        code: Annotated[
            Optional[str],
            Field(
                description='The function code that contains the request and response functions'
            ),
        ] = None,
    ) -> Dict:
        """Creates a Function object for a GraphQL API.

        This operation creates a function for the specified GraphQL API. Functions
        are reusable pieces of resolver logic that can be attached to multiple fields
        in your GraphQL schema.

        Args:
            api_id: The GraphQL API ID.
            name: The Function name. Must be unique within the API.
            data_source_name: The Function DataSource name that this function will use.
            description: Optional description of the Function.
            request_mapping_template: The Function request mapping template. Functions support only the 2018-05-29 version of the request mapping template.
            response_mapping_template: The Function response mapping template.
            function_version: The version of the request mapping template. Currently, the supported value is 2018-05-29.
            sync_config: Describes a Sync configuration for a resolver. Specifies which Conflict Detection strategy and Resolution strategy to use when the resolver is invoked.
            max_batch_size: The maximum batching size for a resolver.
            runtime: Describes a runtime used by an AWS AppSync pipeline resolver or AWS AppSync function. Specifies the name and version of the runtime to use.
            code: The function code that contains the request and response functions. When code is used, the runtime is required.

        Returns:
            A dictionary containing information about the created function, including:
            - functionConfiguration: The Function object with details like name, ARN, data source, etc.

        Example response:
            {
                "functionConfiguration": {
                    "functionId": "FUNCTION_ID",
                    "functionArn": "arn:aws:appsync:us-east-1:123456789012:apis/graphqlapiid/functions/functionid",
                    "name": "MyFunction",
                    "description": "My function description",
                    "dataSourceName": "MyDataSource",
                    "requestMappingTemplate": "...",
                    "responseMappingTemplate": "...",
                    "functionVersion": "2018-05-29"
                }
            }
        """
        return await create_function_operation(
            api_id,
            name,
            data_source_name,
            description,
            request_mapping_template,
            response_mapping_template,
            function_version,
            sync_config,
            max_batch_size,
            runtime,
            code,
        )
