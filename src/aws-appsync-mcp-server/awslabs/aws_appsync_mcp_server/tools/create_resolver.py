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

"""Create Resolver tool for AWS AppSync MCP Server."""

from awslabs.aws_appsync_mcp_server.decorators import write_operation
from awslabs.aws_appsync_mcp_server.operations.create_resolver import create_resolver_operation
from mcp.types import ToolAnnotations
from pydantic import Field
from typing import Annotated, Dict, Optional


def register_create_resolver_tool(mcp):
    """Register the create_resolver tool with the MCP server."""

    @mcp.tool(
        name='create_resolver',
        description="""Creates a resolver for a GraphQL field in an AppSync API.

        A resolver is the bridge between your GraphQL schema and your data sources.
        It defines how to fetch or modify data for a specific field in your schema.
        Resolvers can be unit resolvers (attached to a single data source) or
        pipeline resolvers (composed of multiple functions).
        """,
        annotations=ToolAnnotations(
            title='Create Resolver', readOnlyHint=False, destructiveHint=False, openWorldHint=False
        ),
    )
    @write_operation
    async def create_resolver(
        api_id: Annotated[str, Field(description='The API ID for the GraphQL API')],
        type_name: Annotated[
            str, Field(description='The name of the type (e.g., Query, Mutation, Subscription)')
        ],
        field_name: Annotated[
            str, Field(description='The name of the field to attach the resolver to')
        ],
        data_source_name: Annotated[
            Optional[str],
            Field(description='The name of the data source (required for unit resolvers)'),
        ] = None,
        request_mapping_template: Annotated[
            Optional[str],
            Field(description='The request mapping template in VTL (Velocity Template Language)'),
        ] = None,
        response_mapping_template: Annotated[
            Optional[str],
            Field(description='The response mapping template in VTL (Velocity Template Language)'),
        ] = None,
        kind: Annotated[
            Optional[str], Field(description='The resolver kind: UNIT or PIPELINE')
        ] = None,
        pipeline_config: Annotated[
            Optional[Dict],
            Field(description='Pipeline configuration for PIPELINE resolvers with functions list'),
        ] = None,
        sync_config: Annotated[
            Optional[Dict], Field(description='Sync configuration for conflict resolution')
        ] = None,
        caching_config: Annotated[
            Optional[Dict], Field(description='Caching configuration for the resolver')
        ] = None,
        max_batch_size: Annotated[
            Optional[int], Field(description='Maximum batch size for batch operations')
        ] = None,
        runtime: Annotated[
            Optional[Dict], Field(description='Runtime configuration (name and runtimeVersion)')
        ] = None,
        code: Annotated[
            Optional[str],
            Field(description='The resolver code for JavaScript/TypeScript resolvers'),
        ] = None,
        metrics_config: Annotated[
            Optional[str], Field(description='Metrics configuration: ENABLED or DISABLED')
        ] = None,
    ) -> Dict:
        """Creates a resolver for a GraphQL field in an AppSync API.

        A resolver is the bridge between your GraphQL schema and your data sources.
        It defines how to fetch or modify data for a specific field in your schema.

        Args:
            api_id: The API ID for the GraphQL API.
            type_name: The name of the type (e.g., Query, Mutation, Subscription).
            field_name: The name of the field to attach the resolver to.
            data_source_name: Optional name of the data source (required for unit resolvers).
            request_mapping_template: Optional request mapping template in VTL.
            response_mapping_template: Optional response mapping template in VTL.
            kind: Optional resolver kind (UNIT or PIPELINE).
            pipeline_config: Optional pipeline configuration for PIPELINE resolvers.
            sync_config: Optional sync configuration for conflict resolution.
            caching_config: Optional caching configuration for the resolver.
            max_batch_size: Optional maximum batch size for batch operations.
            runtime: Optional runtime configuration for JavaScript/TypeScript resolvers.
            code: Optional resolver code for JavaScript/TypeScript resolvers.
            metrics_config: Optional metrics configuration (ENABLED or DISABLED).

        Returns:
            A dictionary containing information about the created resolver, including:
            - resolver: The resolver configuration with details like type name, field name,
              data source name, mapping templates, etc.

        Example response:
            {
                "resolver": {
                    "typeName": "Query",
                    "fieldName": "getUser",
                    "dataSourceName": "UserTable",
                    "resolverArn": "arn:aws:appsync:us-east-1:123456789012:apis/abcdefghijklmnopqrstuvwxyz/types/Query/resolvers/getUser",
                    "requestMappingTemplate": "...",
                    "responseMappingTemplate": "...",
                    "kind": "UNIT"
                }
            }
        """
        return await create_resolver_operation(
            api_id,
            type_name,
            field_name,
            data_source_name,
            request_mapping_template,
            response_mapping_template,
            kind,
            pipeline_config,
            sync_config,
            caching_config,
            max_batch_size,
            runtime,
            code,
            metrics_config,
        )
