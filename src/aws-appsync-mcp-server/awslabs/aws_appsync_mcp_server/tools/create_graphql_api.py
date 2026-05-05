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

"""Create GraphQL API tool for AWS AppSync MCP Server."""

from awslabs.aws_appsync_mcp_server.decorators import write_operation
from awslabs.aws_appsync_mcp_server.operations.create_graphql_api import (
    create_graphql_api_operation,
)
from mcp.types import ToolAnnotations
from pydantic import Field
from typing import Annotated, Dict, List, Optional


def register_create_graphql_api_tool(mcp):
    """Register the create_graphql_api tool with the MCP server."""

    @mcp.tool(
        name='create_graphql_api',
        description="""Creates a GraphQL API.

        This operation creates a new GraphQL API with the specified configuration.
        The API will be created with the authentication type and other settings provided.
        Supports various authentication types including API_KEY, AWS_IAM, AMAZON_COGNITO_USER_POOLS,
        OPENID_CONNECT, and AWS_LAMBDA.

        When authentication_type is API_KEY, an API key is automatically created with a 7-day expiry.
        """,
        annotations=ToolAnnotations(
            title='Create GraphQL API',
            readOnlyHint=False,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    @write_operation
    async def create_graphql_api(
        name: Annotated[str, Field(description='A user-supplied name for the GraphQL API')],
        authentication_type: Annotated[
            str,
            Field(
                description='The authentication type: API_KEY, AWS_IAM, AMAZON_COGNITO_USER_POOLS, OPENID_CONNECT, AWS_LAMBDA'
            ),
        ],
        log_config: Annotated[
            Optional[Dict], Field(description='The Amazon CloudWatch Logs configuration')
        ] = None,
        user_pool_config: Annotated[
            Optional[Dict], Field(description='The Amazon Cognito user pool configuration')
        ] = None,
        open_id_connect_config: Annotated[
            Optional[Dict], Field(description='The OpenID Connect configuration')
        ] = None,
        tags: Annotated[Optional[Dict[str, str]], Field(description='A TagMap object')] = None,
        additional_authentication_providers: Annotated[
            Optional[List[Dict]],
            Field(description='A list of additional authentication providers'),
        ] = None,
        xray_enabled: Annotated[
            Optional[bool], Field(description='A flag indicating whether to enable X-Ray tracing')
        ] = None,
        lambda_authorizer_config: Annotated[
            Optional[Dict],
            Field(description='Configuration for AWS Lambda function authorization'),
        ] = None,
        visibility: Annotated[
            Optional[str],
            Field(
                description='Sets the value of the GraphQL API to public (GLOBAL) or private (PRIVATE)'
            ),
        ] = None,
        api_type: Annotated[
            Optional[str],
            Field(
                description='The value that indicates whether the GraphQL API is a standard API (GRAPHQL) or merged API (MERGED)'
            ),
        ] = None,
        merged_api_execution_role_arn: Annotated[
            Optional[str],
            Field(
                description='The Identity and Access Management service role ARN for a merged API'
            ),
        ] = None,
        owner_contact: Annotated[
            Optional[str], Field(description='The owner contact information for an API resource')
        ] = None,
        introspection_config: Annotated[
            Optional[str],
            Field(
                description='Sets the value of the GraphQL API to enable (ENABLED) or disable (DISABLED) introspection'
            ),
        ] = None,
        query_depth_limit: Annotated[
            Optional[int],
            Field(description='The maximum depth a query can have in a single request'),
        ] = None,
        resolver_count_limit: Annotated[
            Optional[int],
            Field(
                description='The maximum number of resolvers that can be invoked in a single request'
            ),
        ] = None,
        enhanced_metrics_config: Annotated[
            Optional[Dict], Field(description='The enhancedMetricsConfig object')
        ] = None,
    ) -> Dict:
        """Creates a GraphQL API.

        This operation creates a new GraphQL API with the specified configuration.
        The API will be created with the authentication type and other settings provided.
        When authentication_type is API_KEY, an API key is automatically created with a 7-day expiry.

        Args:
            name: A user-supplied name for the GraphQL API.
            authentication_type: The authentication type for the GraphQL API. Valid values are:
                - API_KEY: The API will use API keys for authentication
                - AWS_IAM: The API will use AWS IAM for authentication
                - AMAZON_COGNITO_USER_POOLS: The API will use Amazon Cognito user pools
                - OPENID_CONNECT: The API will use OpenID Connect
                - AWS_LAMBDA: The API will use AWS Lambda for authentication
            log_config: Optional CloudWatch Logs configuration.
            user_pool_config: Optional Amazon Cognito user pool configuration.
            open_id_connect_config: Optional OpenID Connect configuration.
            tags: Optional map of tags to assign to the API resource.
            additional_authentication_providers: Optional list of additional authentication providers.
            xray_enabled: Optional flag to enable X-Ray tracing for the GraphQL API.
            lambda_authorizer_config: Optional AWS Lambda function authorization configuration.
            visibility: Optional visibility setting (GLOBAL or PRIVATE).
            api_type: Optional API type (GRAPHQL or MERGED).
            merged_api_execution_role_arn: Optional IAM role ARN for merged API execution.
            owner_contact: Optional owner contact information.
            introspection_config: Optional introspection setting (ENABLED or DISABLED).
            query_depth_limit: Optional maximum query depth limit.
            resolver_count_limit: Optional maximum resolver count limit.
            enhanced_metrics_config: Optional enhanced metrics configuration.

        Returns:
            A dictionary containing information about the created GraphQL API, including:
            - graphqlApi: The GraphQL API object with details like apiId, name, etc.
            - apiKey: (Only when authentication_type is API_KEY) The auto-generated API key with 7-day expiry

        Example response for API_KEY authentication with the apiKey config ommitted:
            {
                "graphqlApi": {
                    "name": "my-graphql-api",
                    "apiId": "abcdefghijklmnopqrstuvwxyz",
                    "authenticationType": "API_KEY",
                    "arn": "arn:aws:appsync:us-east-1:123456789012:apis/abcdefghijklmnopqrstuvwxyz",
                    "uris": {
                        "GRAPHQL": "https://abcdefghijklmnopqrstuvwxyz.appsync-api.us-east-1.amazonaws.com/graphql"
                    },
                    "tags": {},
                    "creationTime": "2024-01-01T00:00:00Z",
                    "xrayEnabled": false
                }
            }
        """
        return await create_graphql_api_operation(
            name=name,
            authentication_type=authentication_type,
            log_config=log_config,
            user_pool_config=user_pool_config,
            open_id_connect_config=open_id_connect_config,
            tags=tags,
            additional_authentication_providers=additional_authentication_providers,
            xray_enabled=xray_enabled,
            lambda_authorizer_config=lambda_authorizer_config,
            visibility=visibility,
            api_type=api_type,
            merged_api_execution_role_arn=merged_api_execution_role_arn,
            owner_contact=owner_contact,
            introspection_config=introspection_config,
            query_depth_limit=query_depth_limit,
            resolver_count_limit=resolver_count_limit,
            enhanced_metrics_config=enhanced_metrics_config,
        )
