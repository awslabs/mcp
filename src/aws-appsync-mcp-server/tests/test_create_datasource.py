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

"""Tests for the create_datasource operation."""

import pytest
from awslabs.aws_appsync_mcp_server.operations.create_datasource import create_datasource_operation
from awslabs.aws_appsync_mcp_server.tools.create_datasource import register_create_datasource_tool
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_create_datasource_minimal():
    """Test create_datasource tool with minimal parameters."""
    mock_client = MagicMock()
    mock_response = {
        'dataSource': {
            'dataSourceArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/datasources/test-datasource',
            'name': 'test-datasource',
            'type': 'NONE',
        }
    }
    mock_client.create_data_source.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_datasource.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_datasource_operation(
            api_id='test-api-id', name='test-datasource', type='NONE'
        )

        mock_client.create_data_source.assert_called_once_with(
            apiId='test-api-id', name='test-datasource', type='NONE'
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_datasource_dynamodb():
    """Test create_datasource tool with DynamoDB configuration."""
    mock_client = MagicMock()
    mock_response = {
        'dataSource': {
            'dataSourceArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/datasources/test-dynamodb-ds',
            'name': 'test-dynamodb-ds',
            'description': 'DynamoDB data source',
            'type': 'AMAZON_DYNAMODB',
            'serviceRoleArn': 'arn:aws:iam::123456789012:role/AppSyncServiceRole',
            'dynamodbConfig': {'tableName': 'TestTable', 'awsRegion': 'us-east-1'},
        }
    }
    mock_client.create_data_source.return_value = mock_response

    dynamodb_config = {'tableName': 'TestTable', 'awsRegion': 'us-east-1'}

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_datasource.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_datasource_operation(
            api_id='test-api-id',
            name='test-dynamodb-ds',
            type='AMAZON_DYNAMODB',
            description='DynamoDB data source',
            service_role_arn='arn:aws:iam::123456789012:role/AppSyncServiceRole',
            dynamodb_config=dynamodb_config,
        )

        mock_client.create_data_source.assert_called_once_with(
            apiId='test-api-id',
            name='test-dynamodb-ds',
            type='AMAZON_DYNAMODB',
            description='DynamoDB data source',
            serviceRoleArn='arn:aws:iam::123456789012:role/AppSyncServiceRole',
            dynamodbConfig=dynamodb_config,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_datasource_lambda():
    """Test create_datasource tool with Lambda configuration."""
    mock_client = MagicMock()
    mock_response = {
        'dataSource': {
            'dataSourceArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/datasources/test-lambda-ds',
            'name': 'test-lambda-ds',
            'type': 'AWS_LAMBDA',
            'serviceRoleArn': 'arn:aws:iam::123456789012:role/AppSyncServiceRole',
            'lambdaConfig': {
                'lambdaFunctionArn': 'arn:aws:lambda:us-east-1:123456789012:function:TestFunction'
            },
        }
    }
    mock_client.create_data_source.return_value = mock_response

    lambda_config = {
        'lambdaFunctionArn': 'arn:aws:lambda:us-east-1:123456789012:function:TestFunction'
    }

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_datasource.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_datasource_operation(
            api_id='test-api-id',
            name='test-lambda-ds',
            type='AWS_LAMBDA',
            service_role_arn='arn:aws:iam::123456789012:role/AppSyncServiceRole',
            lambda_config=lambda_config,
        )

        mock_client.create_data_source.assert_called_once_with(
            apiId='test-api-id',
            name='test-lambda-ds',
            type='AWS_LAMBDA',
            serviceRoleArn='arn:aws:iam::123456789012:role/AppSyncServiceRole',
            lambdaConfig=lambda_config,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_datasource_http():
    """Test create_datasource tool with HTTP configuration."""
    mock_client = MagicMock()
    mock_response = {
        'dataSource': {
            'dataSourceArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/datasources/test-http-ds',
            'name': 'test-http-ds',
            'type': 'HTTP',
            'httpConfig': {
                'endpoint': 'https://api.example.com',
                'authorizationConfig': {'authorizationType': 'AWS_IAM'},
            },
        }
    }
    mock_client.create_data_source.return_value = mock_response

    http_config = {
        'endpoint': 'https://api.example.com',
        'authorizationConfig': {'authorizationType': 'AWS_IAM'},
    }

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_datasource.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_datasource_operation(
            api_id='test-api-id', name='test-http-ds', type='HTTP', http_config=http_config
        )

        mock_client.create_data_source.assert_called_once_with(
            apiId='test-api-id', name='test-http-ds', type='HTTP', httpConfig=http_config
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_datasource_elasticsearch():
    """Test create_datasource tool with Elasticsearch configuration."""
    mock_client = MagicMock()
    mock_response = {
        'dataSource': {
            'dataSourceArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/datasources/test-es-ds',
            'name': 'test-es-ds',
            'type': 'AMAZON_ELASTICSEARCH',
            'serviceRoleArn': 'arn:aws:iam::123456789012:role/AppSyncServiceRole',
            'elasticsearchConfig': {
                'endpoint': 'https://search-test-domain.us-east-1.es.amazonaws.com',
                'awsRegion': 'us-east-1',
            },
        }
    }
    mock_client.create_data_source.return_value = mock_response

    elasticsearch_config = {
        'endpoint': 'https://search-test-domain.us-east-1.es.amazonaws.com',
        'awsRegion': 'us-east-1',
    }

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_datasource.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_datasource_operation(
            api_id='test-api-id',
            name='test-es-ds',
            type='AMAZON_ELASTICSEARCH',
            service_role_arn='arn:aws:iam::123456789012:role/AppSyncServiceRole',
            elasticsearch_config=elasticsearch_config,
        )

        mock_client.create_data_source.assert_called_once_with(
            apiId='test-api-id',
            name='test-es-ds',
            type='AMAZON_ELASTICSEARCH',
            serviceRoleArn='arn:aws:iam::123456789012:role/AppSyncServiceRole',
            elasticsearchConfig=elasticsearch_config,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_datasource_opensearch():
    """Test create_datasource tool with OpenSearch configuration."""
    mock_client = MagicMock()
    mock_response = {
        'dataSource': {
            'dataSourceArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/datasources/test-os-ds',
            'name': 'test-os-ds',
            'type': 'AMAZON_OPENSEARCH_SERVICE',
            'serviceRoleArn': 'arn:aws:iam::123456789012:role/AppSyncServiceRole',
            'openSearchServiceConfig': {
                'endpoint': 'https://search-test-domain.us-east-1.aoss.amazonaws.com',
                'awsRegion': 'us-east-1',
            },
        }
    }
    mock_client.create_data_source.return_value = mock_response

    opensearch_config = {
        'endpoint': 'https://search-test-domain.us-east-1.aoss.amazonaws.com',
        'awsRegion': 'us-east-1',
    }

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_datasource.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_datasource_operation(
            api_id='test-api-id',
            name='test-os-ds',
            type='AMAZON_OPENSEARCH_SERVICE',
            service_role_arn='arn:aws:iam::123456789012:role/AppSyncServiceRole',
            open_search_service_config=opensearch_config,
        )

        mock_client.create_data_source.assert_called_once_with(
            apiId='test-api-id',
            name='test-os-ds',
            type='AMAZON_OPENSEARCH_SERVICE',
            serviceRoleArn='arn:aws:iam::123456789012:role/AppSyncServiceRole',
            openSearchServiceConfig=opensearch_config,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_datasource_relational_database():
    """Test create_datasource tool with relational database configuration."""
    mock_client = MagicMock()
    mock_response = {
        'dataSource': {
            'dataSourceArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/datasources/test-rds-ds',
            'name': 'test-rds-ds',
            'type': 'RELATIONAL_DATABASE',
            'serviceRoleArn': 'arn:aws:iam::123456789012:role/AppSyncServiceRole',
            'relationalDatabaseConfig': {
                'relationalDatabaseSourceType': 'RDS_HTTP_ENDPOINT',
                'rdsHttpEndpointConfig': {
                    'awsRegion': 'us-east-1',
                    'dbClusterIdentifier': 'test-cluster',
                    'awsSecretStoreArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret',  # pragma: allowlist secret
                },
            },
        }
    }
    mock_client.create_data_source.return_value = mock_response

    rds_config = {
        'relationalDatabaseSourceType': 'RDS_HTTP_ENDPOINT',
        'rdsHttpEndpointConfig': {
            'awsRegion': 'us-east-1',
            'dbClusterIdentifier': 'test-cluster',
            'awsSecretStoreArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret',  # pragma: allowlist secret
        },
    }

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_datasource.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_datasource_operation(
            api_id='test-api-id',
            name='test-rds-ds',
            type='RELATIONAL_DATABASE',
            service_role_arn='arn:aws:iam::123456789012:role/AppSyncServiceRole',
            relational_database_config=rds_config,
        )

        mock_client.create_data_source.assert_called_once_with(
            apiId='test-api-id',
            name='test-rds-ds',
            type='RELATIONAL_DATABASE',
            serviceRoleArn='arn:aws:iam::123456789012:role/AppSyncServiceRole',
            relationalDatabaseConfig=rds_config,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_datasource_eventbridge():
    """Test create_datasource tool with EventBridge configuration."""
    mock_client = MagicMock()
    mock_response = {
        'dataSource': {
            'dataSourceArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/datasources/test-eb-ds',
            'name': 'test-eb-ds',
            'type': 'AMAZON_EVENTBRIDGE',
            'serviceRoleArn': 'arn:aws:iam::123456789012:role/AppSyncServiceRole',
            'eventBridgeConfig': {
                'eventSourceArn': 'arn:aws:events:us-east-1:123456789012:event-bus/test-bus'
            },
        }
    }
    mock_client.create_data_source.return_value = mock_response

    eventbridge_config = {
        'eventSourceArn': 'arn:aws:events:us-east-1:123456789012:event-bus/test-bus'
    }

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_datasource.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_datasource_operation(
            api_id='test-api-id',
            name='test-eb-ds',
            type='AMAZON_EVENTBRIDGE',
            service_role_arn='arn:aws:iam::123456789012:role/AppSyncServiceRole',
            event_bridge_config=eventbridge_config,
        )

        mock_client.create_data_source.assert_called_once_with(
            apiId='test-api-id',
            name='test-eb-ds',
            type='AMAZON_EVENTBRIDGE',
            serviceRoleArn='arn:aws:iam::123456789012:role/AppSyncServiceRole',
            eventBridgeConfig=eventbridge_config,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_datasource_with_metrics():
    """Test create_datasource tool with metrics configuration."""
    mock_client = MagicMock()
    mock_response = {
        'dataSource': {
            'dataSourceArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/datasources/test-metrics-ds',
            'name': 'test-metrics-ds',
            'type': 'NONE',
            'metricsConfig': 'ENABLED',
        }
    }
    mock_client.create_data_source.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_datasource.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_datasource_operation(
            api_id='test-api-id', name='test-metrics-ds', type='NONE', metrics_config='ENABLED'
        )

        mock_client.create_data_source.assert_called_once_with(
            apiId='test-api-id', name='test-metrics-ds', type='NONE', metricsConfig='ENABLED'
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_datasource_full_configuration():
    """Test create_datasource tool with all optional parameters."""
    mock_client = MagicMock()
    mock_response = {
        'dataSource': {
            'dataSourceArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/datasources/test-full-ds',
            'name': 'test-full-ds',
            'description': 'Full configuration test',
            'type': 'AMAZON_DYNAMODB',
            'serviceRoleArn': 'arn:aws:iam::123456789012:role/AppSyncServiceRole',
            'dynamodbConfig': {
                'tableName': 'TestTable',
                'awsRegion': 'us-east-1',
                'useCallerCredentials': False,
            },
            'metricsConfig': 'ENABLED',
        }
    }
    mock_client.create_data_source.return_value = mock_response

    dynamodb_config = {
        'tableName': 'TestTable',
        'awsRegion': 'us-east-1',
        'useCallerCredentials': False,
    }

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_datasource.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_datasource_operation(
            api_id='test-api-id',
            name='test-full-ds',
            type='AMAZON_DYNAMODB',
            description='Full configuration test',
            service_role_arn='arn:aws:iam::123456789012:role/AppSyncServiceRole',
            dynamodb_config=dynamodb_config,
            metrics_config='ENABLED',
        )

        mock_client.create_data_source.assert_called_once_with(
            apiId='test-api-id',
            name='test-full-ds',
            type='AMAZON_DYNAMODB',
            description='Full configuration test',
            serviceRoleArn='arn:aws:iam::123456789012:role/AppSyncServiceRole',
            dynamodbConfig=dynamodb_config,
            metricsConfig='ENABLED',
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_datasource_invalid_service_role_arn():
    """Test create_datasource tool with invalid service role ARN."""
    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_datasource.get_appsync_client',
    ):
        with pytest.raises(ValueError, match='Invalid service role ARN format'):
            await create_datasource_operation(
                api_id='test-api-id',
                name='test-datasource',
                type='AMAZON_DYNAMODB',
                service_role_arn='invalid-arn-format',
            )


@pytest.mark.asyncio
async def test_create_datasource_valid_service_role_arn():
    """Test create_datasource tool with valid service role ARN format."""
    mock_client = MagicMock()
    mock_response = {
        'dataSource': {
            'dataSourceArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/datasources/test-datasource',
            'name': 'test-datasource',
            'type': 'AMAZON_DYNAMODB',
            'serviceRoleArn': 'arn:aws:iam::528863500574:role/service-role/appsync-ds-ddb-jn2N7IJN4EWi-NewModelNameTable',
        }
    }
    mock_client.create_data_source.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_datasource.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_datasource_operation(
            api_id='test-api-id',
            name='test-datasource',
            type='AMAZON_DYNAMODB',
            service_role_arn='arn:aws:iam::528863500574:role/service-role/appsync-ds-ddb-jn2N7IJN4EWi-NewModelNameTable',
        )

        mock_client.create_data_source.assert_called_once_with(
            apiId='test-api-id',
            name='test-datasource',
            type='AMAZON_DYNAMODB',
            serviceRoleArn='arn:aws:iam::528863500574:role/service-role/appsync-ds-ddb-jn2N7IJN4EWi-NewModelNameTable',
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_datasource_empty_response():
    """Test create_datasource tool with empty response from AWS."""
    mock_client = MagicMock()
    mock_response = {'dataSource': {}}
    mock_client.create_data_source.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_datasource.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_datasource_operation(
            api_id='test-api-id', name='test-datasource', type='NONE'
        )

        mock_client.create_data_source.assert_called_once_with(
            apiId='test-api-id', name='test-datasource', type='NONE'
        )
        assert result == mock_response


def test_register_create_datasource_tool():
    """Test that create_datasource tool is registered correctly."""
    mock_mcp = MagicMock()
    register_create_datasource_tool(mock_mcp)
    mock_mcp.tool.assert_called_once()


@pytest.mark.asyncio
async def test_create_datasource_tool_execution():
    """Test create_datasource tool execution through MCP."""
    from awslabs.aws_appsync_mcp_server.decorators import set_write_allowed

    mock_mcp = MagicMock()
    captured_func = None

    def capture_tool(**kwargs):
        def decorator(func):
            nonlocal captured_func
            captured_func = func
            return func

        return decorator

    mock_mcp.tool = capture_tool
    set_write_allowed(True)

    register_create_datasource_tool(mock_mcp)

    with patch(
        'awslabs.aws_appsync_mcp_server.tools.create_datasource.create_datasource_operation'
    ) as mock_op:
        mock_op.return_value = {'dataSource': {'name': 'test-ds'}}
        result = await captured_func('test-api', 'test-ds', 'NONE')
        mock_op.assert_called_once()
        assert result == {'dataSource': {'name': 'test-ds'}}
