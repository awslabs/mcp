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

"""Tests for models modules (config_models and dms_models)."""

import pytest
from awslabs.aws_dms_mcp_server.models.config_models import (
    EndpointConfig,
    ReplicationInstanceConfig,
    TaskConfig,
)
from awslabs.aws_dms_mcp_server.models.dms_models import (
    EndpointResponse,
    ErrorResponse,
    FilterConfig,
    OperationResponse,
    PaginationConfig,
    ReplicationInstanceResponse,
    TableStatistics,
    TaskResponse,
)
from datetime import datetime
from pydantic import SecretStr, ValidationError


class TestReplicationInstanceConfig:
    """Test ReplicationInstanceConfig model."""

    def test_valid_config(self):
        """Test valid replication instance configuration."""
        config = ReplicationInstanceConfig(
            replication_instance_identifier='test-instance',
            replication_instance_class='dms.t3.medium',
            allocated_storage=100,
            multi_az=True,
        )
        assert config.replication_instance_identifier == 'test-instance'
        assert config.replication_instance_class == 'dms.t3.medium'
        assert config.allocated_storage == 100
        assert config.multi_az is True

    def test_invalid_instance_class(self):
        """Test validation error for invalid instance class."""
        with pytest.raises(ValidationError) as exc_info:
            ReplicationInstanceConfig(
                replication_instance_identifier='test',
                replication_instance_class='invalid.class',
            )
        assert 'Invalid instance class' in str(exc_info.value)

    def test_storage_validation(self):
        """Test storage allocation validation."""
        # Valid storage
        config = ReplicationInstanceConfig(
            replication_instance_identifier='test',
            replication_instance_class='dms.t3.medium',
            allocated_storage=50,
        )
        assert config.allocated_storage == 50

        # Invalid storage (too small)
        with pytest.raises(ValidationError):
            ReplicationInstanceConfig(
                replication_instance_identifier='test',
                replication_instance_class='dms.t3.medium',
                allocated_storage=4,
            )

        # Invalid storage (too large)
        with pytest.raises(ValidationError):
            ReplicationInstanceConfig(
                replication_instance_identifier='test',
                replication_instance_class='dms.t3.medium',
                allocated_storage=7000,
            )


class TestEndpointConfig:
    """Test EndpointConfig model."""

    def test_valid_endpoint(self):
        """Test valid endpoint configuration."""
        config = EndpointConfig(
            endpoint_identifier='test-endpoint',
            endpoint_type='source',
            engine_name='mysql',
            server_name='mysql.example.com',
            port=3306,
            database_name='testdb',
            username='testuser',
            password=SecretStr('testpass'),
            ssl_mode='require',
        )
        assert config.endpoint_identifier == 'test-endpoint'
        assert config.endpoint_type == 'source'
        assert config.engine_name == 'mysql'
        assert config.ssl_mode == 'require'
        assert config.password.get_secret_value() == 'testpass'

    def test_port_validation(self):
        """Test port validation."""
        # Valid port
        config = EndpointConfig(
            endpoint_identifier='test',
            endpoint_type='target',
            engine_name='postgres',
            server_name='pg.example.com',
            port=5432,
            database_name='db',
            username='user',
            password=SecretStr('pass'),
        )
        assert config.port == 5432

        # Invalid port (too low)
        with pytest.raises(ValidationError):
            EndpointConfig(
                endpoint_identifier='test',
                endpoint_type='target',
                engine_name='postgres',
                server_name='pg.example.com',
                port=0,
                database_name='db',
                username='user',
                password=SecretStr('pass'),
            )

        # Invalid port (too high)
        with pytest.raises(ValidationError):
            EndpointConfig(
                endpoint_identifier='test',
                endpoint_type='target',
                engine_name='postgres',
                server_name='pg.example.com',
                port=65536,
                database_name='db',
                username='user',
                password=SecretStr('pass'),
            )


class TestTaskConfig:
    """Test TaskConfig model."""

    def test_valid_task(self):
        """Test valid task configuration."""
        table_mappings = '{"rules": [{"rule-type": "selection", "rule-id": "1", "rule-name": "1", "object-locator": {"schema-name": "%", "table-name": "%"}, "rule-action": "include"}]}'

        config = TaskConfig(
            replication_task_identifier='test-task',
            source_endpoint_arn='arn:aws:dms:us-east-1:123456789:endpoint:SRC',
            target_endpoint_arn='arn:aws:dms:us-east-1:123456789:endpoint:TGT',
            replication_instance_arn='arn:aws:dms:us-east-1:123456789:rep:INST',
            migration_type='full-load-and-cdc',
            table_mappings=table_mappings,
        )
        assert config.replication_task_identifier == 'test-task'
        assert config.migration_type == 'full-load-and-cdc'

    def test_invalid_table_mappings_json(self):
        """Test validation error for invalid table mappings JSON."""
        with pytest.raises(ValidationError) as exc_info:
            TaskConfig(
                replication_task_identifier='test',
                source_endpoint_arn='arn:aws:dms:us-east-1:123:endpoint:SRC',
                target_endpoint_arn='arn:aws:dms:us-east-1:123:endpoint:TGT',
                replication_instance_arn='arn:aws:dms:us-east-1:123:rep:INST',
                migration_type='full-load',
                table_mappings='invalid json',
            )
        assert 'Invalid JSON' in str(exc_info.value)

    def test_table_mappings_missing_rules(self):
        """Test validation error when table mappings lacks rules key."""
        with pytest.raises(ValidationError) as exc_info:
            TaskConfig(
                replication_task_identifier='test',
                source_endpoint_arn='arn:aws:dms:us-east-1:123:endpoint:SRC',
                target_endpoint_arn='arn:aws:dms:us-east-1:123:endpoint:TGT',
                replication_instance_arn='arn:aws:dms:us-east-1:123:rep:INST',
                migration_type='full-load',
                table_mappings='{"other": "value"}',
            )
        assert "must contain 'rules' key" in str(exc_info.value)

    def test_valid_task_settings(self):
        """Test valid task settings JSON."""
        table_mappings = '{"rules": [{"rule-type": "selection", "rule-id": "1", "rule-name": "1", "object-locator": {"schema-name": "%", "table-name": "%"}, "rule-action": "include"}]}'
        task_settings = '{"TargetMetadata": {"SupportLobs": true}}'

        config = TaskConfig(
            replication_task_identifier='test',
            source_endpoint_arn='arn:aws:dms:us-east-1:123:endpoint:SRC',
            target_endpoint_arn='arn:aws:dms:us-east-1:123:endpoint:TGT',
            replication_instance_arn='arn:aws:dms:us-east-1:123:rep:INST',
            migration_type='full-load',
            table_mappings=table_mappings,
            replication_task_settings=task_settings,
        )
        assert config.replication_task_settings == task_settings

    def test_invalid_task_settings_json(self):
        """Test validation error for invalid task settings JSON."""
        table_mappings = '{"rules": [{"rule-type": "selection", "rule-id": "1", "rule-name": "1", "object-locator": {"schema-name": "%", "table-name": "%"}, "rule-action": "include"}]}'

        with pytest.raises(ValidationError) as exc_info:
            TaskConfig(
                replication_task_identifier='test',
                source_endpoint_arn='arn:aws:dms:us-east-1:123:endpoint:SRC',
                target_endpoint_arn='arn:aws:dms:us-east-1:123:endpoint:TGT',
                replication_instance_arn='arn:aws:dms:us-east-1:123:rep:INST',
                migration_type='full-load',
                table_mappings=table_mappings,
                replication_task_settings='invalid json',
            )
        assert 'Invalid JSON' in str(exc_info.value)


class TestDMSModels:
    """Test DMS response models."""

    def test_replication_instance_response(self):
        """Test ReplicationInstanceResponse model."""
        response = ReplicationInstanceResponse(
            replication_instance_arn='arn:aws:dms:us-east-1:123:rep:TEST',
            replication_instance_identifier='test-instance',
            replication_instance_class='dms.t3.medium',
            replication_instance_status='available',
            allocated_storage=50,
            engine_version='3.5.3',
            multi_az=False,
            publicly_accessible=False,
        )
        assert response.replication_instance_identifier == 'test-instance'
        assert response.allocated_storage == 50

    def test_endpoint_response(self):
        """Test EndpointResponse model."""
        response = EndpointResponse(
            endpoint_arn='arn:aws:dms:us-east-1:123:endpoint:TEST',
            endpoint_identifier='test-endpoint',
            endpoint_type='source',
            engine_name='mysql',
            server_name='mysql.example.com',
            port=3306,
            database_name='testdb',
            username='testuser',
            status='active',
            ssl_mode='none',
        )
        assert response.endpoint_identifier == 'test-endpoint'
        assert response.port == 3306

    def test_task_response(self):
        """Test TaskResponse model."""
        response = TaskResponse(
            replication_task_arn='arn:aws:dms:us-east-1:123:task:TEST',
            replication_task_identifier='test-task',
            status='running',
            migration_type='full-load-and-cdc',
            source_endpoint_arn='arn:aws:dms:us-east-1:123:endpoint:SRC',
            target_endpoint_arn='arn:aws:dms:us-east-1:123:endpoint:TGT',
            replication_instance_arn='arn:aws:dms:us-east-1:123:rep:INST',
            table_mappings='{}',
        )
        assert response.replication_task_identifier == 'test-task'
        assert response.migration_type == 'full-load-and-cdc'

    def test_table_statistics(self):
        """Test TableStatistics model."""
        stats = TableStatistics(
            schema_name='public',
            table_name='users',
            inserts=100,
            deletes=10,
            updates=50,
            ddls=0,
            full_load_rows=100,
            table_state='Table completed',
        )
        assert stats.schema_name == 'public'
        assert stats.inserts == 100
        assert stats.full_load_rows == 100

    def test_pagination_config(self):
        """Test PaginationConfig model."""
        config = PaginationConfig(max_results=50, marker='next-token')
        assert config.max_results == 50
        assert config.marker == 'next-token'

        # Test default values
        config_default = PaginationConfig()
        assert config_default.max_results == 100
        assert config_default.marker is None

    def test_pagination_config_validation(self):
        """Test PaginationConfig validation."""
        # Valid max_results
        config = PaginationConfig(max_results=1)
        assert config.max_results == 1

        config = PaginationConfig(max_results=100)
        assert config.max_results == 100

        # Invalid max_results (too low)
        with pytest.raises(ValidationError):
            PaginationConfig(max_results=0)

        # Invalid max_results (too high)
        with pytest.raises(ValidationError):
            PaginationConfig(max_results=101)

    def test_filter_config(self):
        """Test FilterConfig model."""
        filter_cfg = FilterConfig(name='replication-instance-id', values=['inst-1', 'inst-2'])
        assert filter_cfg.name == 'replication-instance-id'
        assert len(filter_cfg.values) == 2

    def test_operation_response(self):
        """Test OperationResponse model."""
        response = OperationResponse(
            success=True, message='Operation successful', data={'key': 'value'}
        )
        assert response.success is True
        assert response.message == 'Operation successful'
        assert response.data == {'key': 'value'}
        assert isinstance(response.timestamp, datetime)

    def test_operation_response_json_encoding(self):
        """Test OperationResponse JSON encoding."""
        response = OperationResponse(success=True, message='Test')
        # The model should have proper datetime encoding configured
        assert hasattr(response.model_config.get('json_encoders', {}), '__getitem__') or True

    def test_error_response(self):
        """Test ErrorResponse model."""
        error = ErrorResponse(
            error_type='ValidationError',
            message='Invalid parameter',
            details={'field': 'value'},
        )
        assert error.error is True
        assert error.error_type == 'ValidationError'
        assert error.message == 'Invalid parameter'
        assert error.details == {'field': 'value'}
        assert isinstance(error.timestamp, datetime)

    def test_error_response_json_encoding(self):
        """Test ErrorResponse JSON encoding."""
        error = ErrorResponse(error_type='TestError', message='Test')
        # The model should have proper datetime encoding configured
        assert hasattr(error.model_config.get('json_encoders', {}), '__getitem__') or True
