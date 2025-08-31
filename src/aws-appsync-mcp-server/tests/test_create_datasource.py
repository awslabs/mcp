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

"""Unit tests for create_datasource operation."""

import pytest
from awslabs.aws_appsync_mcp_server.operations.create_datasource import (
    _validate_http_config,
    _validate_service_role_arn,
    create_datasource_operation,
)
from unittest.mock import patch


class TestValidateServiceRoleArn:
    """Test service role ARN validation."""

    def test_valid_arn(self):
        """Test valid ARN format."""
        assert _validate_service_role_arn('arn:aws:iam::123456789012:role/MyRole')

    def test_invalid_arn_format(self):
        """Test invalid ARN formats."""
        assert not _validate_service_role_arn('invalid-arn')
        assert not _validate_service_role_arn('arn:aws:iam::invalid:role/MyRole')


class TestValidateHttpConfig:
    """Test HTTP configuration validation."""

    def test_valid_https_endpoint(self):
        """Test valid HTTPS endpoint."""
        config = {'endpoint': 'https://api.example.com'}
        _validate_http_config(config)  # Should not raise

    def test_localhost_blocked(self):
        """Test localhost endpoints are blocked."""
        configs = [
            {'endpoint': 'https://localhost:8080'},
            {'endpoint': 'https://127.0.0.1:8080'},
        ]
        for config in configs:
            with pytest.raises(ValueError, match='localhost or private IP'):
                _validate_http_config(config)

    def test_private_ips_blocked(self):
        """Test private IP ranges are blocked."""
        configs = [
            {'endpoint': 'https://10.0.0.1'},
            {'endpoint': 'https://192.168.1.1'},
            {'endpoint': 'https://172.16.0.1'},
        ]
        for config in configs:
            with pytest.raises(ValueError, match='localhost or private IP'):
                _validate_http_config(config)

    def test_http_protocol_rejected(self):
        """Test HTTP protocol is rejected."""
        config = {'endpoint': 'http://api.example.com'}
        with pytest.raises(ValueError, match='must use HTTPS'):
            _validate_http_config(config)

    def test_empty_endpoint(self):
        """Test empty endpoint is rejected."""
        config = {'endpoint': ''}
        with pytest.raises(ValueError, match='must use HTTPS'):
            _validate_http_config(config)


class TestCreateDatasourceOperation:
    """Test create_datasource_operation function."""

    @patch('awslabs.aws_appsync_mcp_server.operations.create_datasource.get_appsync_client')
    @pytest.mark.asyncio
    async def test_create_datasource_success(self, mock_client):
        """Test successful datasource creation."""
        mock_client.return_value.create_data_source.return_value = {'dataSource': {'name': 'test'}}

        result = await create_datasource_operation(
            'api123',
            'test-ds',
            'HTTP',
            description='test desc',
            service_role_arn='arn:aws:iam::123456789012:role/test',
            http_config={'endpoint': 'https://api.example.com'},
            dynamodb_config={'tableName': 'test'},
            lambda_config={'functionArn': 'arn:aws:lambda:us-east-1:123456789012:function:test'},
            metrics_config='ENABLED',
        )
        assert result == {'dataSource': {'name': 'test'}}
        mock_client.return_value.create_data_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_service_role_arn(self):
        """Test invalid service role ARN raises error."""
        with pytest.raises(ValueError, match='Invalid service role ARN'):
            await create_datasource_operation(
                'api123', 'test-ds', 'HTTP', service_role_arn='invalid'
            )

    @pytest.mark.asyncio
    async def test_invalid_http_config(self):
        """Test invalid HTTP config raises error."""
        with pytest.raises(ValueError, match='must use HTTPS'):
            await create_datasource_operation(
                'api123', 'test-ds', 'HTTP', http_config={'endpoint': 'http://test.com'}
            )

    @patch('awslabs.aws_appsync_mcp_server.operations.create_datasource.get_appsync_client')
    @pytest.mark.asyncio
    async def test_all_optional_params(self, mock_client):
        """Test with all optional parameters."""
        mock_client.return_value.create_data_source.return_value = {'dataSource': {}}

        await create_datasource_operation(
            'api123',
            'test-ds',
            'HTTP',
            elasticsearch_config={'endpoint': 'test'},
            open_search_service_config={'endpoint': 'test'},
            relational_database_config={'cluster': 'test'},
            event_bridge_config={'eventSourceArn': 'test'},
        )
        mock_client.return_value.create_data_source.assert_called_once()
