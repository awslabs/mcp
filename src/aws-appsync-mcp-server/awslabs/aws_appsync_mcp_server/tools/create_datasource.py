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

"""Create Data Source tool for AWS AppSync MCP Server."""

from awslabs.aws_appsync_mcp_server.decorators import write_operation
from awslabs.aws_appsync_mcp_server.operations.create_datasource import create_datasource_operation
from mcp.types import ToolAnnotations
from pydantic import Field
from typing import Annotated, Dict, Optional


def register_create_datasource_tool(mcp):
    """Register the create_datasource tool with the MCP server."""

    @mcp.tool(
        name='create_datasource',
        description="""Creates a DataSource object for a GraphQL API.

        This operation creates a data source for the specified GraphQL API. Data sources
        connect your GraphQL API to various backend services like DynamoDB, Lambda,
        HTTP endpoints, and more.
        """,
        annotations=ToolAnnotations(
            title='Create Data Source',
            readOnlyHint=False,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    @write_operation
    async def create_datasource(
        api_id: Annotated[
            str, Field(description='The API ID for the GraphQL API for the DataSource')
        ],
        name: Annotated[str, Field(description='A user-supplied name for the DataSource')],
        type: Annotated[
            str,
            Field(
                description='The type of the DataSource. Valid values: AWS_LAMBDA, AMAZON_DYNAMODB, AMAZON_ELASTICSEARCH, HTTP, NONE, RELATIONAL_DATABASE, AMAZON_EVENTBRIDGE, AMAZON_OPENSEARCH_SERVICE'
            ),
        ],
        description: Annotated[
            Optional[str], Field(description='A description of the DataSource')
        ] = None,
        service_role_arn: Annotated[
            Optional[str],
            Field(
                description='The AWS IAM service role ARN for the data source. Format: arn:aws:iam::ACCOUNT-ID:role/ROLE-NAME'
            ),
        ] = None,
        dynamodb_config: Annotated[
            Optional[Dict], Field(description='Amazon DynamoDB settings')
        ] = None,
        lambda_config: Annotated[Optional[Dict], Field(description='AWS Lambda settings')] = None,
        elasticsearch_config: Annotated[
            Optional[Dict], Field(description='Amazon OpenSearch Service settings')
        ] = None,
        open_search_service_config: Annotated[
            Optional[Dict], Field(description='Amazon OpenSearch Service settings')
        ] = None,
        http_config: Annotated[Optional[Dict], Field(description='HTTP endpoint settings')] = None,
        relational_database_config: Annotated[
            Optional[Dict], Field(description='Relational database settings')
        ] = None,
        event_bridge_config: Annotated[
            Optional[Dict], Field(description='Amazon EventBridge settings')
        ] = None,
        metrics_config: Annotated[
            Optional[str],
            Field(
                description='Enables or disables enhanced DataSource metrics. Valid values: ENABLED, DISABLED'
            ),
        ] = None,
    ) -> Dict:
        """Creates a DataSource object for a GraphQL API.

        This operation creates a data source for the specified GraphQL API. Data sources
        connect your GraphQL API to various backend services like DynamoDB, Lambda,
        HTTP endpoints, and more.

        Args:
            api_id: The API ID for the GraphQL API for the DataSource.
            name: A user-supplied name for the DataSource.
            type: The type of the DataSource. Valid values are:
                  - AWS_LAMBDA: AWS Lambda function
                  - AMAZON_DYNAMODB: Amazon DynamoDB table
                  - AMAZON_ELASTICSEARCH: Amazon OpenSearch Service domain
                  - HTTP: HTTP endpoint
                  - NONE: Local resolver
                  - RELATIONAL_DATABASE: Relational database
                  - AMAZON_EVENTBRIDGE: Amazon EventBridge
                  - AMAZON_OPENSEARCH_SERVICE: Amazon OpenSearch Service
            description: Optional description of the DataSource.
            service_role_arn: The AWS IAM service role ARN for the data source.
                              Must be in format: arn:aws:iam::ACCOUNT-ID:role/ROLE-NAME
                              Example: arn:aws:iam::123456789012:role/service-role/AppSyncServiceRole
            dynamodb_config: Amazon DynamoDB settings including table name, region, etc.
            lambda_config: AWS Lambda settings including function ARN.
            elasticsearch_config: Amazon OpenSearch Service settings including endpoint and region.
            open_search_service_config: Amazon OpenSearch Service settings.
            http_config: HTTP endpoint settings including endpoint and authorization config.
            relational_database_config: Relational database settings including RDS HTTP endpoint config.
            event_bridge_config: Amazon EventBridge settings including event source ARN.
            metrics_config: Enables or disables enhanced DataSource metrics (ENABLED or DISABLED).

        Returns:
            A dictionary containing information about the created data source, including:
            - dataSource: The DataSource object with details like name, type, ARN, etc.

        Example response:
            {
                "dataSource": {
                    "dataSourceArn": "arn:aws:appsync:us-east-1:123456789012:apis/graphqlapiid/datasources/datasourcename",
                    "name": "MyDataSource",
                    "description": "My data source description",
                    "type": "AMAZON_DYNAMODB",
                    "serviceRoleArn": "arn:aws:iam::123456789012:role/MyServiceRole",
                    "dynamodbConfig": {
                        "tableName": "MyTable",
                        "awsRegion": "us-east-1"
                    }
                }
            }
        """
        return await create_datasource_operation(
            api_id,
            name,
            type,
            description,
            service_role_arn,
            dynamodb_config,
            lambda_config,
            elasticsearch_config,
            open_search_service_config,
            http_config,
            relational_database_config,
            event_bridge_config,
            metrics_config,
        )
