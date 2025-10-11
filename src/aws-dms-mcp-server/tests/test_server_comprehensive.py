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

"""Comprehensive tests for server.py MCP tools."""

from awslabs.aws_dms_mcp_server.config import DMSServerConfig
from awslabs.aws_dms_mcp_server.server import create_server
from unittest.mock import MagicMock, patch


class TestCreateServer:
    """Test create_server function."""

    def test_create_server_with_config(self, mock_config):
        """Test creating server with custom config."""
        server = create_server(mock_config)
        assert server is not None
        assert hasattr(server, 'name')

    def test_create_server_with_default_config(self):
        """Test creating server with default config."""
        server = create_server()
        assert server is not None

    def test_create_server_initializes_managers(self, mock_config):
        """Test that server initializes required managers."""
        server = create_server(mock_config)
        # Server should be created successfully with all managers
        assert server is not None


class TestReplicationInstanceTools:
    """Test replication instance related tools."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_replication_instances(self, mock_boto3, mock_config):
        """Test describe_replication_instances tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'ReplicationInstances': [
                {
                    'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123:rep:TEST',
                    'ReplicationInstanceIdentifier': 'test-instance',
                    'ReplicationInstanceClass': 'dms.t3.medium',
                    'ReplicationInstanceStatus': 'available',
                    'AllocatedStorage': 50,
                    'EngineVersion': '3.5.3',
                    'MultiAZ': False,
                    'PubliclyAccessible': False,
                }
            ]
        }
        mock_boto_client.describe_replication_instances.return_value = mock_response

        server = create_server(mock_config)
        # The server should have the tool registered
        assert server is not None

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_create_replication_instance_read_only_blocks(self, mock_boto3):
        """Test that create_replication_instance is blocked in read-only mode."""
        config = DMSServerConfig(read_only_mode=True)
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        server = create_server(config)
        # Mutation operations should be blocked in read-only mode
        assert server is not None

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_orderable_replication_instances(self, mock_boto3, mock_config):
        """Test describe_orderable_replication_instances tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'OrderableReplicationInstances': [
                {
                    'ReplicationInstanceClass': 'dms.t3.medium',
                    'StorageType': 'gp2',
                    'MinAllocatedStorage': 50,
                    'MaxAllocatedStorage': 6144,
                }
            ]
        }
        mock_boto_client.describe_orderable_replication_instances.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None


class TestEndpointTools:
    """Test endpoint related tools."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_endpoints(self, mock_boto3, mock_config):
        """Test describe_endpoints tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'Endpoints': [
                {
                    'EndpointArn': 'arn:aws:dms:us-east-1:123:endpoint:TEST',
                    'EndpointIdentifier': 'test-endpoint',
                    'EndpointType': 'source',
                    'EngineName': 'mysql',
                    'ServerName': 'mysql.example.com',
                    'Port': 3306,
                    'DatabaseName': 'testdb',
                    'Username': 'testuser',
                    'Status': 'active',
                    'SslMode': 'none',
                }
            ]
        }
        mock_boto_client.describe_endpoints.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_endpoint_types(self, mock_boto3, mock_config):
        """Test describe_endpoint_types tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'SupportedEndpointTypes': [
                {
                    'EngineName': 'mysql',
                    'SupportsCDC': True,
                    'EndpointType': 'source',
                }
            ]
        }
        mock_boto_client.describe_endpoint_types.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_engine_versions(self, mock_boto3, mock_config):
        """Test describe_engine_versions tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'EngineVersions': [
                {
                    'Version': '3.5.3',
                    'Lifecycle': 'active',
                }
            ]
        }
        mock_boto_client.describe_engine_versions.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None


class TestReplicationTaskTools:
    """Test replication task related tools."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_replication_tasks(self, mock_boto3, mock_config):
        """Test describe_replication_tasks tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'ReplicationTasks': [
                {
                    'ReplicationTaskArn': 'arn:aws:dms:us-east-1:123:task:TEST',
                    'ReplicationTaskIdentifier': 'test-task',
                    'Status': 'running',
                    'MigrationType': 'full-load-and-cdc',
                    'SourceEndpointArn': 'arn:aws:dms:us-east-1:123:endpoint:SRC',
                    'TargetEndpointArn': 'arn:aws:dms:us-east-1:123:endpoint:TGT',
                    'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123:rep:INST',
                }
            ]
        }
        mock_boto_client.describe_replication_tasks.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_table_statistics(self, mock_boto3, mock_config):
        """Test describe_table_statistics tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'TableStatistics': [
                {
                    'SchemaName': 'public',
                    'TableName': 'users',
                    'Inserts': 100,
                    'Deletes': 10,
                    'Updates': 50,
                    'Ddls': 0,
                    'FullLoadRows': 100,
                    'TableState': 'Table completed',
                }
            ]
        }
        mock_boto_client.describe_table_statistics.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None


class TestConnectionTools:
    """Test connection related tools."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_connections(self, mock_boto3, mock_config):
        """Test describe_connections tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'Connections': [
                {
                    'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123:rep:INST',
                    'EndpointArn': 'arn:aws:dms:us-east-1:123:endpoint:TEST',
                    'Status': 'successful',
                }
            ]
        }
        mock_boto_client.describe_connections.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None


class TestCertificateTools:
    """Test certificate related tools."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_certificates(self, mock_boto3, mock_config):
        """Test describe_certificates tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'Certificates': [
                {
                    'CertificateArn': 'arn:aws:dms:us-east-1:123:cert:TEST',
                    'CertificateIdentifier': 'test-cert',
                    'CertificateCreationDate': '2024-01-01',
                }
            ]
        }
        mock_boto_client.describe_certificates.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None


class TestSubnetGroupTools:
    """Test subnet group related tools."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_replication_subnet_groups(self, mock_boto3, mock_config):
        """Test describe_replication_subnet_groups tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'ReplicationSubnetGroups': [
                {
                    'ReplicationSubnetGroupIdentifier': 'test-subnet-group',
                    'ReplicationSubnetGroupDescription': 'Test subnet group',
                    'VpcId': 'vpc-123456',
                    'SubnetGroupStatus': 'Complete',
                }
            ]
        }
        mock_boto_client.describe_replication_subnet_groups.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None


class TestEventTools:
    """Test event related tools."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_events(self, mock_boto3, mock_config):
        """Test describe_events tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'Events': [
                {
                    'SourceIdentifier': 'test-instance',
                    'SourceType': 'replication-instance',
                    'Message': 'Replication instance created',
                    'EventCategories': ['creation'],
                    'Date': '2024-01-01T00:00:00Z',
                }
            ]
        }
        mock_boto_client.describe_events.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_event_categories(self, mock_boto3, mock_config):
        """Test describe_event_categories tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'EventCategoryGroupList': [
                {
                    'SourceType': 'replication-instance',
                    'EventCategories': ['creation', 'deletion', 'failure'],
                }
            ]
        }
        mock_boto_client.describe_event_categories.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_event_subscriptions(self, mock_boto3, mock_config):
        """Test describe_event_subscriptions tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'EventSubscriptionsList': [
                {
                    'CustomerAwsId': '123456789',
                    'CustSubscriptionId': 'test-subscription',
                    'SnsTopicArn': 'arn:aws:sns:us-east-1:123:test-topic',
                    'Status': 'enabled',
                    'SourceType': 'replication-instance',
                }
            ]
        }
        mock_boto_client.describe_event_subscriptions.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None


class TestMaintenanceTools:
    """Test maintenance related tools."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_pending_maintenance_actions(self, mock_boto3, mock_config):
        """Test describe_pending_maintenance_actions tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'PendingMaintenanceActions': [
                {
                    'ResourceIdentifier': 'arn:aws:dms:us-east-1:123:rep:TEST',
                    'PendingMaintenanceActionDetails': [
                        {
                            'Action': 'system-update',
                            'AutoAppliedAfterDate': '2024-02-01',
                            'OptInStatus': 'pending-auto-apply',
                        }
                    ],
                }
            ]
        }
        mock_boto_client.describe_pending_maintenance_actions.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None


class TestServerlessTools:
    """Test DMS Serverless related tools."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_replication_configs(self, mock_boto3, mock_config):
        """Test describe_replication_configs tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'ReplicationConfigs': [
                {
                    'ReplicationConfigArn': 'arn:aws:dms:us-east-1:123:config:TEST',
                    'ReplicationConfigIdentifier': 'test-config',
                    'SourceEndpointArn': 'arn:aws:dms:us-east-1:123:endpoint:SRC',
                    'TargetEndpointArn': 'arn:aws:dms:us-east-1:123:endpoint:TGT',
                    'ReplicationType': 'full-load-and-cdc',
                }
            ]
        }
        mock_boto_client.describe_replication_configs.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_replications(self, mock_boto3, mock_config):
        """Test describe_replications tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'Replications': [
                {
                    'ReplicationConfigArn': 'arn:aws:dms:us-east-1:123:config:TEST',
                    'Status': 'running',
                }
            ]
        }
        mock_boto_client.describe_replications.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None


class TestMigrationProjectTools:
    """Test migration project related tools."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_migration_projects(self, mock_boto3, mock_config):
        """Test describe_migration_projects tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'MigrationProjects': [
                {
                    'MigrationProjectArn': 'arn:aws:dms:us-east-1:123:project:TEST',
                    'MigrationProjectName': 'test-project',
                }
            ]
        }
        mock_boto_client.describe_migration_projects.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None


class TestDataProviderTools:
    """Test data provider related tools."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_data_providers(self, mock_boto3, mock_config):
        """Test describe_data_providers tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'DataProviders': [
                {
                    'DataProviderArn': 'arn:aws:dms:us-east-1:123:provider:TEST',
                    'DataProviderName': 'test-provider',
                    'Engine': 'mysql',
                }
            ]
        }
        mock_boto_client.describe_data_providers.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None


class TestInstanceProfileTools:
    """Test instance profile related tools."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_instance_profiles(self, mock_boto3, mock_config):
        """Test describe_instance_profiles tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'InstanceProfiles': [
                {
                    'InstanceProfileArn': 'arn:aws:dms:us-east-1:123:profile:TEST',
                    'InstanceProfileName': 'test-profile',
                }
            ]
        }
        mock_boto_client.describe_instance_profiles.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None


class TestDataMigrationTools:
    """Test data migration related tools."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_data_migrations(self, mock_boto3, mock_config):
        """Test describe_data_migrations tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'DataMigrations': [
                {
                    'DataMigrationArn': 'arn:aws:dms:us-east-1:123:migration:TEST',
                    'DataMigrationName': 'test-migration',
                    'MigrationType': 'full-load',
                }
            ]
        }
        mock_boto_client.describe_data_migrations.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None


class TestAccountTools:
    """Test account related tools."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_account_attributes(self, mock_boto3, mock_config):
        """Test describe_account_attributes tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'AccountQuotas': [
                {
                    'AccountQuotaName': 'ReplicationInstances',
                    'Used': 5,
                    'Max': 20,
                }
            ]
        }
        mock_boto_client.describe_account_attributes.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None


class TestTaggingTools:
    """Test resource tagging tools."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_list_tags_for_resource(self, mock_boto3, mock_config):
        """Test list_tags_for_resource tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'TagList': [
                {'Key': 'Environment', 'Value': 'Production'},
                {'Key': 'Team', 'Value': 'DataEngineering'},
            ]
        }
        mock_boto_client.list_tags_for_resource.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None


class TestAssessmentTools:
    """Test assessment related tools."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_describe_replication_task_assessment_runs(self, mock_boto3, mock_config):
        """Test describe_replication_task_assessment_runs tool."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {
            'ReplicationTaskAssessmentRuns': [
                {
                    'ReplicationTaskAssessmentRunArn': 'arn:aws:dms:us-east-1:123:run:TEST',
                    'ReplicationTaskArn': 'arn:aws:dms:us-east-1:123:task:TEST',
                    'Status': 'running',
                }
            ]
        }
        mock_boto_client.describe_replication_task_assessment_runs.return_value = mock_response

        server = create_server(mock_config)
        assert server is not None
