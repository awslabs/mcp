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

"""Tests for response_formatter module."""

from awslabs.aws_dms_mcp_server.exceptions.dms_exceptions import DMSMCPException
from awslabs.aws_dms_mcp_server.utils.response_formatter import ResponseFormatter
from datetime import datetime


class TestResponseFormatter:
    """Test ResponseFormatter utility class."""

    def test_format_instance(self):
        """Test formatting replication instance response."""
        instance_data = {
            'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123:rep:TEST',
            'ReplicationInstanceIdentifier': 'test-instance',
            'ReplicationInstanceClass': 'dms.t3.medium',
            'ReplicationInstanceStatus': 'available',
            'AllocatedStorage': 50,
            'EngineVersion': '3.5.3',
            'MultiAZ': True,
            'PubliclyAccessible': False,
            'AvailabilityZone': 'us-east-1a',
        }

        formatted = ResponseFormatter.format_instance(instance_data)

        assert formatted['arn'] == 'arn:aws:dms:us-east-1:123:rep:TEST'
        assert formatted['identifier'] == 'test-instance'
        assert formatted['class'] == 'dms.t3.medium'
        assert formatted['status'] == 'available'
        assert formatted['multi_az'] is True
        assert formatted['publicly_accessible'] is False

    def test_format_instance_with_timestamp(self):
        """Test formatting instance with creation timestamp."""
        create_time = datetime(2024, 1, 1, 12, 0, 0)
        instance_data = {
            'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123:rep:TEST',
            'ReplicationInstanceIdentifier': 'test-instance',
            'ReplicationInstanceClass': 'dms.t3.medium',
            'ReplicationInstanceStatus': 'available',
            'AllocatedStorage': 50,
            'EngineVersion': '3.5.3',
            'InstanceCreateTime': create_time,
        }

        formatted = ResponseFormatter.format_instance(instance_data)
        assert 'instance_create_time' in formatted
        assert formatted['instance_create_time'].endswith('Z')

    def test_format_instance_with_vpc_security_groups(self):
        """Test formatting instance with VPC security groups."""
        instance_data = {
            'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123:rep:TEST',
            'ReplicationInstanceIdentifier': 'test-instance',
            'ReplicationInstanceClass': 'dms.t3.medium',
            'ReplicationInstanceStatus': 'available',
            'AllocatedStorage': 50,
            'EngineVersion': '3.5.3',
            'VpcSecurityGroups': [
                {'VpcSecurityGroupId': 'sg-123', 'Status': 'active'},
                {'VpcSecurityGroupId': 'sg-456', 'Status': 'active'},
            ],
        }

        formatted = ResponseFormatter.format_instance(instance_data)
        assert 'vpc_security_groups' in formatted
        assert len(formatted['vpc_security_groups']) == 2
        assert formatted['vpc_security_groups'][0]['id'] == 'sg-123'

    def test_format_endpoint(self):
        """Test formatting endpoint response."""
        endpoint_data = {
            'EndpointArn': 'arn:aws:dms:us-east-1:123:endpoint:TEST',
            'EndpointIdentifier': 'test-endpoint',
            'EndpointType': 'source',
            'EngineName': 'mysql',
            'ServerName': 'mysql.example.com',
            'Port': 3306,
            'DatabaseName': 'testdb',
            'Username': 'testuser',
            'Status': 'active',
            'SslMode': 'require',
        }

        formatted = ResponseFormatter.format_endpoint(endpoint_data)

        assert formatted['arn'] == 'arn:aws:dms:us-east-1:123:endpoint:TEST'
        assert formatted['identifier'] == 'test-endpoint'
        assert formatted['type'] == 'source'
        assert formatted['engine'] == 'mysql'
        assert formatted['port'] == 3306

    def test_format_endpoint_masks_password(self):
        """Test that endpoint password is masked."""
        endpoint_data = {
            'EndpointArn': 'arn:aws:dms:us-east-1:123:endpoint:TEST',
            'EndpointIdentifier': 'test-endpoint',
            'EndpointType': 'source',
            'EngineName': 'mysql',
            'ServerName': 'mysql.example.com',
            'Port': 3306,
            'DatabaseName': 'testdb',
            'Username': 'testuser',
            'Password': 'secretpassword123',  # pragma: allowlist secret
            'Status': 'active',
        }

        formatted = ResponseFormatter.format_endpoint(endpoint_data)
        assert formatted['password'] == '***MASKED***'

    def test_format_endpoint_with_certificate(self):
        """Test formatting endpoint with SSL certificate."""
        endpoint_data = {
            'EndpointArn': 'arn:aws:dms:us-east-1:123:endpoint:TEST',
            'EndpointIdentifier': 'test-endpoint',
            'EndpointType': 'source',
            'EngineName': 'mysql',
            'ServerName': 'mysql.example.com',
            'Port': 3306,
            'DatabaseName': 'testdb',
            'Username': 'testuser',
            'Status': 'active',
            'CertificateArn': 'arn:aws:dms:us-east-1:123:cert:TEST',
        }

        formatted = ResponseFormatter.format_endpoint(endpoint_data)
        assert formatted['certificate_arn'] == 'arn:aws:dms:us-east-1:123:cert:TEST'

    def test_format_endpoint_with_timestamp(self):
        """Test formatting endpoint with creation timestamp."""
        create_time = datetime(2024, 1, 1, 12, 0, 0)
        endpoint_data = {
            'EndpointArn': 'arn:aws:dms:us-east-1:123:endpoint:TEST',
            'EndpointIdentifier': 'test-endpoint',
            'EndpointType': 'source',
            'EngineName': 'mysql',
            'ServerName': 'mysql.example.com',
            'Port': 3306,
            'DatabaseName': 'testdb',
            'Username': 'testuser',
            'Status': 'active',
            'EndpointCreateTime': create_time,
        }

        formatted = ResponseFormatter.format_endpoint(endpoint_data)
        assert 'endpoint_create_time' in formatted
        assert formatted['endpoint_create_time'].endswith('Z')

    def test_format_task(self):
        """Test formatting task response."""
        task_data = {
            'ReplicationTaskArn': 'arn:aws:dms:us-east-1:123:task:TEST',
            'ReplicationTaskIdentifier': 'test-task',
            'Status': 'running',
            'MigrationType': 'full-load-and-cdc',
            'SourceEndpointArn': 'arn:aws:dms:us-east-1:123:endpoint:SRC',
            'TargetEndpointArn': 'arn:aws:dms:us-east-1:123:endpoint:TGT',
            'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123:rep:INST',
            'TableMappings': '{}',
        }

        formatted = ResponseFormatter.format_task(task_data)

        assert formatted['arn'] == 'arn:aws:dms:us-east-1:123:task:TEST'
        assert formatted['identifier'] == 'test-task'
        assert formatted['status'] == 'running'
        assert formatted['migration_type'] == 'full-load-and-cdc'

    def test_format_task_with_stats(self):
        """Test formatting task with statistics."""
        task_data = {
            'ReplicationTaskArn': 'arn:aws:dms:us-east-1:123:task:TEST',
            'ReplicationTaskIdentifier': 'test-task',
            'Status': 'running',
            'MigrationType': 'full-load',
            'SourceEndpointArn': 'arn:aws:dms:us-east-1:123:endpoint:SRC',
            'TargetEndpointArn': 'arn:aws:dms:us-east-1:123:endpoint:TGT',
            'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123:rep:INST',
            'ReplicationTaskStats': {
                'FullLoadProgressPercent': 75,
                'ElapsedTimeMillis': 120000,
                'TablesLoaded': 5,
                'TablesLoading': 2,
                'TablesQueued': 3,
                'TablesErrored': 0,
            },
        }

        formatted = ResponseFormatter.format_task(task_data)
        assert 'stats' in formatted
        assert formatted['stats']['full_load_progress_percent'] == 75
        assert formatted['stats']['tables_loaded'] == 5

    def test_format_task_with_timestamps(self):
        """Test formatting task with timestamps."""
        create_time = datetime(2024, 1, 1, 12, 0, 0)
        start_time = datetime(2024, 1, 1, 13, 0, 0)
        stop_time = datetime(2024, 1, 1, 14, 0, 0)

        task_data = {
            'ReplicationTaskArn': 'arn:aws:dms:us-east-1:123:task:TEST',
            'ReplicationTaskIdentifier': 'test-task',
            'Status': 'stopped',
            'MigrationType': 'full-load',
            'SourceEndpointArn': 'arn:aws:dms:us-east-1:123:endpoint:SRC',
            'TargetEndpointArn': 'arn:aws:dms:us-east-1:123:endpoint:TGT',
            'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123:rep:INST',
            'ReplicationTaskCreationDate': create_time,
            'ReplicationTaskStartDate': start_time,
            'StopDate': stop_time,
        }

        formatted = ResponseFormatter.format_task(task_data)
        assert 'task_create_time' in formatted
        assert 'start_time' in formatted
        assert 'stop_time' in formatted

    def test_format_table_stats(self):
        """Test formatting table statistics."""
        stats_data = {
            'SchemaName': 'public',
            'TableName': 'users',
            'Inserts': 100,
            'Deletes': 10,
            'Updates': 50,
            'Ddls': 0,
            'FullLoadRows': 100,
            'FullLoadErrorRows': 5,
            'FullLoadCondtnlChkFailedRows': 2,
            'TableState': 'Table completed',
        }

        formatted = ResponseFormatter.format_table_stats(stats_data)

        assert formatted['schema_name'] == 'public'
        assert formatted['table_name'] == 'users'
        assert formatted['inserts'] == 100
        assert formatted['full_load_rows'] == 100
        assert formatted['completion_percent'] == 95.0

    def test_format_table_stats_with_timestamps(self):
        """Test formatting table stats with timestamps."""
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 13, 0, 0)
        update_time = datetime(2024, 1, 1, 14, 0, 0)

        stats_data = {
            'SchemaName': 'public',
            'TableName': 'users',
            'Inserts': 100,
            'Deletes': 0,
            'Updates': 0,
            'Ddls': 0,
            'FullLoadRows': 100,
            'TableState': 'Table completed',
            'FullLoadStartTime': start_time,
            'FullLoadEndTime': end_time,
            'LastUpdateTime': update_time,
        }

        formatted = ResponseFormatter.format_table_stats(stats_data)
        assert 'full_load_start_time' in formatted
        assert 'full_load_end_time' in formatted
        assert 'last_update_time' in formatted

    def test_format_table_stats_with_validation(self):
        """Test formatting table stats with validation data."""
        stats_data = {
            'SchemaName': 'public',
            'TableName': 'users',
            'Inserts': 100,
            'Deletes': 0,
            'Updates': 0,
            'Ddls': 0,
            'FullLoadRows': 100,
            'TableState': 'Table completed',
            'ValidationPendingRecords': 5,
            'ValidationFailedRecords': 2,
            'ValidationSuspendedRecords': 1,
            'ValidationState': 'pending',
        }

        formatted = ResponseFormatter.format_table_stats(stats_data)
        assert formatted['validation_pending_records'] == 5
        assert formatted['validation_failed_records'] == 2
        assert formatted['validation_suspended_records'] == 1
        assert formatted['validation_state'] == 'pending'

    def test_format_table_stats_zero_rows(self):
        """Test formatting table stats with zero rows."""
        stats_data = {
            'SchemaName': 'public',
            'TableName': 'empty_table',
            'Inserts': 0,
            'Deletes': 0,
            'Updates': 0,
            'Ddls': 0,
            'FullLoadRows': 0,
            'TableState': 'Table completed',
        }

        formatted = ResponseFormatter.format_table_stats(stats_data)
        assert formatted['completion_percent'] == 0.0

    def test_format_error_generic_exception(self):
        """Test formatting generic exception."""
        error = Exception('Test error')
        formatted = ResponseFormatter.format_error(error)

        assert formatted['success'] is False
        assert formatted['error']['message'] == 'Test error'
        assert formatted['error']['type'] == 'Exception'
        assert 'timestamp' in formatted['error']
        assert formatted['data'] is None

    def test_format_error_dms_exception(self):
        """Test formatting DMSMCPException."""
        details = {'resource_id': '123'}
        error = DMSMCPException('DMS error', details=details, suggested_action='Fix it')
        formatted = ResponseFormatter.format_error(error)

        assert formatted['success'] is False
        assert 'DMS error' in formatted['error']['message']
        assert formatted['error']['details'] == details
        assert formatted['error']['suggested_action'] == 'Fix it'

    def test_format_timestamp(self):
        """Test formatting timestamp to ISO 8601."""
        dt = datetime(2024, 1, 1, 12, 30, 45)
        formatted = ResponseFormatter.format_timestamp(dt)

        assert formatted is not None
        assert formatted.endswith('Z')
        assert '2024-01-01' in formatted

    def test_format_timestamp_none(self):
        """Test formatting None timestamp."""
        formatted = ResponseFormatter.format_timestamp(None)
        assert formatted is None
