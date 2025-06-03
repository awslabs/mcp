# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
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

import base64
from awslabs.aws_serverless_mcp_server.utils.github import fetch_github_content
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict


# Define event source schemas for different runtimes
EVENT_SOURCE_SCHEMAS = {
    'nodejs': {
        'runtime': 'nodejs',
        'event_schema_repo_link': 'https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/aws-lambda/trigger',
        'repo_name': 'DefinitelyTyped/DefinitelyTyped',
        'path': 'types/aws-lambda/trigger',
        'event_sources': {
            'api-gw': 'api-gateway-proxy.d.ts',
            's3': 's3.d.ts',
            'sns': 'sns.d.ts',
            'dynamodb': 'dynamodb-stream-event.d.ts',
            'sqs': 'sqs.d.ts',
            'kinesis': 'kinesis-stream-event.d.ts',
            'eventbridge': 'cloudwatch-events.d.ts',
        },
    },
    'go': {
        'runtime': 'go',
        'event_schema_repo_link': 'https://github.com/aws/aws-lambda-go/tree/main/events',
        'repo_name': 'aws/aws-lambda-go',
        'path': 'events',
        'event_sources': {
            'api-gw': 'apigw.go',
            's3': 's3.go',
            'sns': 'sns.go',
            'dynamodb': 'dynamodb.go',
            'sqs': 'sqs.go',
            'kinesis': 'kinesis.go',
            'eventbridge': 'cloudwatch.go',
        },
    },
    'dotnet': {
        'runtime': 'dotnet',
        'event_schema_repo_link': 'https://github.com/aws/aws-lambda-dotnet/tree/master/Libraries/src',
        'repo_name': 'aws/aws-lambda-dotnet',
        'path': 'Libraries/src',
        'event_sources': {
            'api-gw': 'Amazon.Lambda.APIGatewayEvents/APIGatewayProxyRequest.cs',
            's3': 'Amazon.Lambda.S3Events/S3Event.cs',
            'sns': 'Amazon.Lambda.SNSEvents/SNSEvent.cs',
            'dynamodb': 'Amazon.Lambda.DynamoDBEvents/DynamoDBEvent.cs',
            'sqs': 'Amazon.Lambda.SQSEvents/SQSEvent.cs',
            'kinesis': 'Amazon.Lambda.KinesisEvents/KinesisEvent.cs',
            'eventbridge': 'Amazon.Lambda.EventBridgeEvents/EventBridgeEvent.cs',
        },
    },
    'rust': {
        'runtime': 'rust',
        'event_schema_repo_link': 'https://github.com/awslabs/aws-lambda-rust-runtime/tree/main/lambda-events/src/event',
        'repo_name': 'awslabs/aws-lambda-rust-runtime',
        'path': 'lambda-events/src/event',
        'event_sources': {
            'api-gw': 'apigw/mod.rs',
            's3': 's3/mod.rs',
            'sns': 'sns/mod.rs',
            'dynamodb': 'dynamodb/mod.rs',
            'sqs': 'sqs/mod.rs',
            'kinesis': 'kinesis/mod.rs',
            'eventbridge': 'eventbridge/mod.rs',
        },
    },
    'php': {
        'runtime': 'php',
        'event_schema_repo_link': 'https://github.com/brefphp/bref/tree/master/src/Event',
        'repo_name': 'brefphp/bref',
        'path': 'src/Event',
        'event_sources': {
            'api-gw': 'ApiGateway/ApiGatewayEvent.php',
            's3': 'S3/S3Event.php',
            'sns': 'Sns/SnsEvent.php',
            'dynamodb': 'DynamoDb/DynamoDbEvent.php',
            'sqs': 'Sqs/SqsEvent.php',
            'kinesis': 'Kinesis/KinesisEvent.php',
            'eventbridge': 'CloudWatch/CloudWatchEvent.php',
        },
    },
    'java': {
        'runtime': 'java',
        'event_schema_repo_link': 'https://github.com/aws/aws-lambda-java-libs/tree/main/aws-lambda-java-events/src/main/java/com/amazonaws/services/lambda/runtime/events',
        'repo_name': 'aws/aws-lambda-java-libs',
        'path': 'aws-lambda-java-events/src/main/java/com/amazonaws/services/lambda/runtime/events',
        'event_sources': {
            'api-gw': 'APIGatewayProxyRequestEvent.java',
            's3': 'S3Event.java',
            'sns': 'SNSEvent.java',
            'dynamodb': 'DynamoDBEvent.java',
            'sqs': 'SQSEvent.java',
            'kinesis': 'KinesisEvent.java',
            'eventbridge': 'CloudWatchEvent.java',
        },
    },
    'python': {
        'runtime': 'python',
        'event_schema_repo_link': 'https://github.com/aws-powertools/powertools-lambda-python/tree/develop/aws_lambda_powertools/utilities/data_classes',
        'repo_name': 'aws-powertools/powertools-lambda-python',
        'path': 'aws_lambda_powertools/utilities/data_classes',
        'event_sources': {
            'api-gw': 'api_gateway_proxy_event.py',
            's3': 's3_event.py',
            'sns': 'sns_event.py',
            'dynamodb': 'dynamodb_stream_event.py',
            'sqs': 'sqs_event.py',
            'kinesis': 'kinesis_stream_event.py',
            'eventbridge': 'event_bridge_event.py',
        },
    },
}


class GetLambdaEventSchemasTool:
    """Tool to get AWS Lambda event schemas for different event sources and programming languages."""

    def __init__(self, mcp: FastMCP):
        """Initialize the GetLambdaEventSchemas tool."""
        mcp.tool(name='get_lambda_event_schemas')(self.get_lambda_event_schemas)

    async def get_lambda_event_schemas(
        self,
        ctx: Context,
        event_source: str = Field(
            description='Event source (e.g., api-gw, s3, sqs, sns, kinesis, eventbridge, dynamodb)'
        ),
        runtime: str = Field(
            description='Programming language for the schema references (e.g., go, nodejs, python, java)'
        ),
    ) -> Dict[str, Any]:
        """Returns AWS Lambda event schemas for different event sources (e.g. s3, sns, apigw) and programming languages.

        When a event source triggers a Lambda function, the request payload comes in a specific format.
        Each Lambda event source defines its own schema and language-specific types, which should be used in
        the Lambda function handler to correctly parse the event data. If you cannot find a schema for your event source, you can directly parse
        the event data as a JSON object. For EventBridge events, you must use the list_registries, search_schema, and describe_schema
        tools to access the schema registry directly, get schema definitions, and generate code processing logic.

        Returns:
            Dict: Lambda event schema source code file for the request runtime and event source
        """
        # Check if runtime is supported
        if runtime not in EVENT_SOURCE_SCHEMAS:
            available_runtimes = ', '.join(EVENT_SOURCE_SCHEMAS.keys())
            return {
                'success': False,
                'message': f"Event source schemas for '{runtime}' not found. Available runtimes: {available_runtimes}.",
                'error': f'Unsupported runtime: {runtime}',
            }

        schemas_for_runtime = EVENT_SOURCE_SCHEMAS[runtime]

        # Check if event source is supported
        if event_source not in schemas_for_runtime['event_sources']:
            return {
                'success': False,
                'message': (
                    f"Event source '{event_source}' not found for runtime '{runtime}'. "
                    f'This tool only indexes a subset of event sources. '
                    f'Query the schema repository {schemas_for_runtime["event_schema_repo_link"]} for complete list of event sources.'
                ),
                'error': f'Unsupported event source: {event_source}',
            }
        schema_file = schemas_for_runtime['event_sources'][event_source]

        try:
            # Fetch schema content from GitHub
            github_url = f'https://api.github.com/repos/{schemas_for_runtime["repo_name"]}/contents/{schemas_for_runtime["path"]}/{schema_file}'
            schema_content = fetch_github_content(github_url)

            # Decode content from base64
            decoded_content = base64.b64decode(schema_content['content']).decode('utf-8')

            # Build response
            return {
                'eventSource': event_source,
                'runtime': runtime,
                'content': decoded_content,
                'schemaReferences': {
                    'repoLink': schemas_for_runtime['event_schema_repo_link'],
                    'filePath': f'{schemas_for_runtime["path"]}/{schema_file}',
                },
            }
        except Exception as e:
            error_msg = f'Could not fetch schema content from GitHub: {str(e)}'
            logger.error(error_msg)
            return {
                'success': False,
                'message': f'Failed to fetch serverless templates: {str(e)}',
                'error': str(e),
            }
