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
"""Tests for the get_lambda_event_schemas module."""

import base64
import pytest
from awslabs.aws_serverless_mcp_server.tools.guidance.get_lambda_event_schemas import (
    GetLambdaEventSchemasTool,
)
from unittest.mock import AsyncMock, MagicMock, Mock, patch


class TestGetLambdaEventSchemas:
    """Tests for the get_lambda_event_schemas function."""

    @pytest.mark.asyncio
    async def test_get_lambda_event_schemas_api_gateway(self):
        """Test getting Lambda event schemas for API Gateway."""
        # Mock the fetch_github_content function
        mock_content_dict = """
        {
            "version": "2.0",
            "routeKey": "$default",
            "rawPath": "/path/to/resource",
            "headers": {
            "Header1": "value1",
            "Header2": "value2"
            },
            "requestContext": {
            "accountId": "000000000000",
            "apiId": "api-id",
            "domainName": "id.execute-api.us-east-1.amazonaws.com",
            "domainPrefix": "id"
            },
            "body": "Hello from Lambda!"
        }
        """
        mock_content = base64.b64encode(mock_content_dict.encode('utf-8'))

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.guidance.get_lambda_event_schemas.fetch_github_content',
            new_callable=Mock,
        ) as mock_fetch:
            mock_fetch.return_value = {'content': mock_content}
            # Call the function
            result = await GetLambdaEventSchemasTool(MagicMock()).get_lambda_event_schemas(
                AsyncMock(), event_source='api-gw', runtime='nodejs'
            )

            # Verify the result
            assert 'content' in result

            # Verify fetch_github_content was called
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_lambda_event_schemas_s3(self):
        """Test getting Lambda event schemas for S3."""
        # Mock the fetch_github_content function
        mock_content = """
        {
            "Records": [
                {
                    "eventVersion": "2.1",
                    "eventSource": "aws:s3",
                    "awsRegion": "us-east-1",
                    "eventTime": "2019-09-03T19:37:27.192Z",
                    "eventName": "ObjectCreated:Put",
                    "s3": {
                        "bucket": {
                            "name": "example-bucket",
                            "arn": "arn:aws:s3:::example-bucket"
                        },
                        "object": {
                            "key": "example-key",
                            "size": 1024
                        }
                    }
                }
            ]
        }
        """
        mock_content_base64 = base64.b64encode(mock_content.encode('utf-8'))

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.guidance.get_lambda_event_schemas.fetch_github_content',
            new_callable=Mock,
        ) as mock_fetch:
            mock_fetch.return_value = {'content': mock_content_base64}

            # Call the function
            result = await GetLambdaEventSchemasTool(MagicMock()).get_lambda_event_schemas(
                AsyncMock(), event_source='s3', runtime='python'
            )

            # Verify the result
            assert 'content' in result

            # Verify fetch_github_content was called
            mock_fetch.assert_called_once()
            # No need to check URL, just verify it was called

    @pytest.mark.asyncio
    async def test_get_lambda_event_schemas_dynamodb(self):
        """Test getting Lambda event schemas for DynamoDB."""
        # Mock the fetch_github_content function
        mock_content = """
        {
            "Records": [
                {
                    "eventID": "1",
                    "eventVersion": "1.1",
                    "dynamodb": {
                        "Keys": {
                            "Id": {
                                "N": "101"
                            }
                        },
                        "NewImage": {
                            "Message": {
                                "S": "New item!"
                            },
                            "Id": {
                                "N": "101"
                            }
                        },
                        "SequenceNumber": "111",
                        "SizeBytes": 26,
                        "StreamViewType": "NEW_AND_OLD_IMAGES"
                    },
                    "awsRegion": "us-west-2",
                    "eventName": "INSERT",
                    "eventSourceARN": "arn:aws:dynamodb:us-west-2:account-id:table/ExampleTableWithStream/stream/2015-06-27T00:48:05.899",
                    "eventSource": "aws:dynamodb"
                }
            ]
        }
        """
        mock_content_base64 = base64.b64encode(mock_content.encode('utf-8'))

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.guidance.get_lambda_event_schemas.fetch_github_content',
            new_callable=Mock,
        ) as mock_fetch:
            mock_fetch.return_value = {'content': mock_content_base64}

            # Call the function
            result = await GetLambdaEventSchemasTool(MagicMock()).get_lambda_event_schemas(
                AsyncMock(), event_source='dynamodb', runtime='java'
            )

            # Verify the result
            assert 'content' in result

            # Verify fetch_github_content was called
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_lambda_event_schemas_fetch_error(self):
        """Test getting Lambda event schemas with fetch error."""
        # Mock the fetch_github_content function to return None (error)
        with patch(
            'awslabs.aws_serverless_mcp_server.tools.guidance.get_lambda_event_schemas.fetch_github_content',
            new_callable=Mock,
        ) as mock_fetch:
            mock_fetch.side_effect = ValueError('Could not fetch content')

            # Call the function
            result = await GetLambdaEventSchemasTool(MagicMock()).get_lambda_event_schemas(
                AsyncMock(), event_source='api-gw', runtime='nodejs'
            )

            # Verify the result contains fallback information
            assert 'success' in result
            assert result['success'] is False

            # Verify fetch_github_content was called
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_lambda_event_schemas_unsupported_event_source(self):
        """Test getting Lambda event schemas for unsupported event source."""
        # Call the function
        result = await GetLambdaEventSchemasTool(MagicMock()).get_lambda_event_schemas(
            AsyncMock(), event_source='unsupported-source', runtime='nodejs'
        )

        assert 'success' in result
        assert result['success'] is False

    @pytest.mark.asyncio
    async def test_get_lambda_event_schemas_unsupported_runtime(self):
        """Test getting Lambda event schemas for unsupported runtime."""
        # Call the function
        result = await GetLambdaEventSchemasTool(MagicMock()).get_lambda_event_schemas(
            AsyncMock(), event_source='api-gw', runtime='unsupported-runtime'
        )

        assert 'success' in result
        assert result['success'] is False
