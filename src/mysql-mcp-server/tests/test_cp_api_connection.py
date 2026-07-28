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

"""Tests for internal_create_aurora_cluster (aurora-mysql engine, admin user, CW logs)."""

import pytest
from awslabs.mysql_mcp_server.connection.cp_api_connection import (
    internal_create_aurora_cluster,
    internal_create_serverless_cluster,  # backward-compat alias under test
)
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_rds_client():
    """Create a mock RDS client with standard responses."""
    client = MagicMock()

    client.create_db_cluster.return_value = {
        'DBCluster': {
            'DBClusterIdentifier': 'test-cluster',
            'Status': 'creating',
            'Engine': 'aurora-mysql',
            'Endpoint': 'test-cluster.cluster-xyz.us-east-1.rds.amazonaws.com',
            'MasterUsername': 'admin',
            'DbClusterResourceId': 'cluster-ABCD123',
            'MasterUserSecret': {'SecretArn': 'arn:aws:secretsmanager:us-east-1:123:secret:test'},
        }
    }

    # Waiter mocks
    cluster_waiter = MagicMock()
    cluster_waiter.wait = MagicMock()
    instance_waiter = MagicMock()
    instance_waiter.wait = MagicMock()

    def get_waiter(name):
        if name == 'db_cluster_available':
            return cluster_waiter
        elif name == 'db_instance_available':
            return instance_waiter
        return MagicMock()

    client.get_waiter = MagicMock(side_effect=get_waiter)

    client.create_db_instance.return_value = {
        'DBInstance': {
            'DBInstanceIdentifier': 'test-cluster-instance-1',
            'DBInstanceStatus': 'creating',
        }
    }

    client.describe_db_clusters.return_value = {
        'DBClusters': [
            {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'available',
                'Engine': 'aurora-mysql',
                'Endpoint': 'test-cluster.cluster-xyz.us-east-1.rds.amazonaws.com',
                'MasterUsername': 'admin',
                'DbClusterResourceId': 'cluster-ABCD123',
                'MasterUserSecret': {
                    'SecretArn': 'arn:aws:secretsmanager:us-east-1:123:secret:test'
                },
                'HttpEndpointEnabled': True,
            }
        ]
    }

    return client


class TestInternalCreateServerlessCluster:
    """Tests for internal_create_aurora_cluster."""

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_creates_aurora_mysql_cluster(self, mock_create_client, mock_rds_client):
        """Should create an aurora-mysql cluster."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
        )

        create_call = mock_rds_client.create_db_cluster.call_args[1]
        assert create_call['Engine'] == 'aurora-mysql'
        assert create_call['DBClusterIdentifier'] == 'test-cluster'
        assert create_call['EngineVersion'] == '8.0'
        assert create_call['DatabaseName'] == 'testdb'

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_default_admin_user(self, mock_create_client, mock_rds_client):
        """Should use 'admin' as default primary username."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
        )

        create_call = mock_rds_client.create_db_cluster.call_args[1]
        assert create_call['MasterUsername'] == 'admin'

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_custom_admin_user(self, mock_create_client, mock_rds_client):
        """Should accept custom primary username."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
            master_username='myadmin',
        )

        create_call = mock_rds_client.create_db_cluster.call_args[1]
        assert create_call['MasterUsername'] == 'myadmin'

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_cloudwatch_logs_enabled(self, mock_create_client, mock_rds_client):
        """Should enable CloudWatch logs with audit, error, general, slowquery."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
            enable_cloudwatch_logs=True,
        )

        create_call = mock_rds_client.create_db_cluster.call_args[1]
        assert create_call['EnableCloudwatchLogsExports'] == [
            'audit',
            'error',
            'general',
            'slowquery',
        ]

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_cloudwatch_logs_disabled(self, mock_create_client, mock_rds_client):
        """Should not enable CloudWatch logs when disabled."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
            enable_cloudwatch_logs=False,
        )

        create_call = mock_rds_client.create_db_cluster.call_args[1]
        assert create_call['EnableCloudwatchLogsExports'] == []

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_managed_credentials(self, mock_create_client, mock_rds_client):
        """Should enable ManageMasterUserPassword."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
        )

        create_call = mock_rds_client.create_db_cluster.call_args[1]
        assert create_call['ManageMasterUserPassword'] is True

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_http_endpoint_enabled(self, mock_create_client, mock_rds_client):
        """Should enable HTTP endpoint (Data API)."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
        )

        create_call = mock_rds_client.create_db_cluster.call_args[1]
        assert create_call['EnableHttpEndpoint'] is True

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_serverless_v2_scaling(self, mock_create_client, mock_rds_client):
        """Should configure ServerlessV2 scaling."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
            min_capacity=0.5,
            max_capacity=4,
        )

        create_call = mock_rds_client.create_db_cluster.call_args[1]
        assert create_call['ServerlessV2ScalingConfiguration'] == {
            'MinCapacity': 0.5,
            'MaxCapacity': 4,
        }

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_creates_writer_instance(self, mock_create_client, mock_rds_client):
        """Should create a db.serverless writer instance."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
        )

        instance_call = mock_rds_client.create_db_instance.call_args[1]
        assert instance_call['DBInstanceIdentifier'] == 'test-cluster-instance-1'
        assert instance_call['DBInstanceClass'] == 'db.serverless'
        assert instance_call['Engine'] == 'aurora-mysql'
        assert instance_call['DBClusterIdentifier'] == 'test-cluster'
        assert instance_call['PubliclyAccessible'] is False

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_waits_for_cluster_and_instance(self, mock_create_client, mock_rds_client):
        """Should wait for both cluster and instance to become available."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
        )

        # Should have called get_waiter twice
        assert mock_rds_client.get_waiter.call_count == 2

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_returns_final_cluster_info(self, mock_create_client, mock_rds_client):
        """Should return the final cluster properties."""
        mock_create_client.return_value = mock_rds_client

        result = internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
        )

        assert result['DBClusterIdentifier'] == 'test-cluster'
        assert result['Status'] == 'available'
        mock_rds_client.describe_db_clusters.assert_called()

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_tags_include_created_by_mcp(self, mock_create_client, mock_rds_client):
        """Should tag resources with CreatedBy=MCP."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
        )

        create_call = mock_rds_client.create_db_cluster.call_args[1]
        tags = create_call['Tags']
        assert any(t['Key'] == 'CreatedBy' and t['Value'] == 'MCP' for t in tags)

    def test_missing_region_raises(self):
        """Should raise ValueError if region is empty."""
        with pytest.raises(ValueError, match='region is required'):
            internal_create_aurora_cluster(
                region='',
                cluster_identifier='test-cluster',
                engine_version='8.0',
                database_name='testdb',
            )

    def test_missing_cluster_identifier_raises(self):
        """Should raise ValueError if cluster_identifier is empty."""
        with pytest.raises(ValueError, match='cluster_identifier is required'):
            internal_create_aurora_cluster(
                region='us-east-1',
                cluster_identifier='',
                engine_version='8.0',
                database_name='testdb',
            )

    def test_missing_engine_version_raises(self):
        """Should raise ValueError if engine_version is empty."""
        with pytest.raises(ValueError, match='engine_version is required'):
            internal_create_aurora_cluster(
                region='us-east-1',
                cluster_identifier='test-cluster',
                engine_version='',
                database_name='testdb',
            )

    def test_missing_database_name_raises(self):
        """Should raise ValueError if database_name is empty."""
        with pytest.raises(ValueError, match='database_name is required'):
            internal_create_aurora_cluster(
                region='us-east-1',
                cluster_identifier='test-cluster',
                engine_version='8.0',
                database_name='',
            )


class TestCustomVPCParameters:
    """Tests for db_subnet_group_name and vpc_security_group_ids.

    Regression tests for the InvalidSubnet failure in accounts without
    default VPC subnets (most production and corporate AWS accounts).
    """

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_default_omits_network_params(self, mock_create_client, mock_rds_client):
        """Omitting network params should not pass them to RDS.

        Preserves the original default-VPC behavior: when neither is set,
        neither parameter is forwarded and RDS falls back to default subnets.
        Regression: passing None or [] as actual keys caused AWS to reject
        the request with InvalidParameterCombination.
        """
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
        )

        params = mock_rds_client.create_db_cluster.call_args[1]
        assert 'DBSubnetGroupName' not in params
        assert 'VpcSecurityGroupIds' not in params

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_passes_subnet_group_name(self, mock_create_client, mock_rds_client):
        """A supplied subnet group name should be forwarded to RDS."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
            db_subnet_group_name='my-private-subnets',
        )

        params = mock_rds_client.create_db_cluster.call_args[1]
        assert params['DBSubnetGroupName'] == 'my-private-subnets'

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_passes_vpc_security_group_ids(self, mock_create_client, mock_rds_client):
        """A supplied security group list should be forwarded to RDS."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
            vpc_security_group_ids=['sg-0123abcd', 'sg-0456efgh'],
        )

        params = mock_rds_client.create_db_cluster.call_args[1]
        assert params['VpcSecurityGroupIds'] == ['sg-0123abcd', 'sg-0456efgh']

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_passes_both_together(self, mock_create_client, mock_rds_client):
        """Both network parameters should be forwarded when supplied together."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
            db_subnet_group_name='prod-subnets',
            vpc_security_group_ids=['sg-prod'],
        )

        params = mock_rds_client.create_db_cluster.call_args[1]
        assert params['DBSubnetGroupName'] == 'prod-subnets'
        assert params['VpcSecurityGroupIds'] == ['sg-prod']

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_empty_list_is_ignored(self, mock_create_client, mock_rds_client):
        """An empty security-group list should be treated as "not set"."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
            vpc_security_group_ids=[],
        )

        params = mock_rds_client.create_db_cluster.call_args[1]
        assert 'VpcSecurityGroupIds' not in params


class TestClusterTypeSelection:
    """Tests for the cluster_type / db_instance_class selection (Concern 2).

    create_cluster now supports both Serverless v2 (default, db.serverless writer)
    and Provisioned (fixed instance class). These tests pin the branching behavior
    in create_db_cluster and create_db_instance call params, plus the validation
    rules that prevent mismatched configurations.
    """

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_default_is_serverless_v2(self, mock_create_client, mock_rds_client):
        """Default cluster_type='serverless_v2' preserves existing behavior."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
        )

        cluster_call = mock_rds_client.create_db_cluster.call_args[1]
        assert 'ServerlessV2ScalingConfiguration' in cluster_call

        instance_call = mock_rds_client.create_db_instance.call_args[1]
        assert instance_call['DBInstanceClass'] == 'db.serverless'

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_provisioned_uses_chosen_instance_class(self, mock_create_client, mock_rds_client):
        """Provisioned clusters pass the chosen instance class to create_db_instance."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
            cluster_type='provisioned',
            db_instance_class='db.r6g.large',
        )

        instance_call = mock_rds_client.create_db_instance.call_args[1]
        assert instance_call['DBInstanceClass'] == 'db.r6g.large'

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_provisioned_omits_serverless_scaling(self, mock_create_client, mock_rds_client):
        """Provisioned clusters do not include ServerlessV2ScalingConfiguration."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
            cluster_type='provisioned',
            db_instance_class='db.r6g.large',
        )

        cluster_call = mock_rds_client.create_db_cluster.call_args[1]
        assert 'ServerlessV2ScalingConfiguration' not in cluster_call

    def test_invalid_cluster_type_raises(self):
        """An unknown cluster_type value should raise ValueError."""
        with pytest.raises(ValueError, match='cluster_type'):
            internal_create_aurora_cluster(
                region='us-east-1',
                cluster_identifier='test-cluster',
                engine_version='8.0',
                database_name='testdb',
                cluster_type='unsupported',
            )

    def test_serverless_with_provisioned_class_raises(self):
        """Serverless v2 + non-serverless instance class is rejected."""
        with pytest.raises(ValueError, match='Serverless v2'):
            internal_create_aurora_cluster(
                region='us-east-1',
                cluster_identifier='test-cluster',
                engine_version='8.0',
                database_name='testdb',
                cluster_type='serverless_v2',
                db_instance_class='db.r6g.large',
            )

    def test_provisioned_with_db_serverless_raises(self):
        """Provisioned + db.serverless is rejected."""
        with pytest.raises(ValueError, match='Provisioned'):
            internal_create_aurora_cluster(
                region='us-east-1',
                cluster_identifier='test-cluster',
                engine_version='8.0',
                database_name='testdb',
                cluster_type='provisioned',
                db_instance_class='db.serverless',
            )

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.logger')
    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_provisioned_t_class_warns(self, mock_create_client, mock_logger, mock_rds_client):
        """Provisioned + burstable t-class succeeds but emits a warning log."""
        mock_create_client.return_value = mock_rds_client

        internal_create_aurora_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='8.0',
            database_name='testdb',
            cluster_type='provisioned',
            db_instance_class='db.t3.medium',
        )

        warning_calls = [c.args[0] for c in mock_logger.warning.call_args_list]
        assert any('burstable t-class' in msg for msg in warning_calls)
        instance_call = mock_rds_client.create_db_instance.call_args[1]
        assert instance_call['DBInstanceClass'] == 'db.t3.medium'


class TestBackwardCompatAlias:
    """Legacy alias must forward to the new function during deprecation.

    The legacy name internal_create_serverless_cluster must keep working
    for one deprecation window. It MUST forward to the new function and emit
    a DeprecationWarning so external callers can migrate.
    """

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_alias_forwards_to_new_function(self, mock_create_client, mock_rds_client):
        """Legacy name forwards args/kwargs and returns the new function's result."""
        mock_create_client.return_value = mock_rds_client

        with pytest.warns(DeprecationWarning, match='internal_create_aurora_cluster'):
            result = internal_create_serverless_cluster(
                region='us-east-1',
                cluster_identifier='test-cluster',
                engine_version='8.0',
                database_name='testdb',
            )

        # Same return shape as the new function
        assert result['DBClusterIdentifier'] == 'test-cluster'
        # Confirms the underlying call still happened
        mock_rds_client.create_db_cluster.assert_called_once()

    def test_alias_validates_inputs_like_new_function(self):
        """Validation errors from the new function propagate through the alias."""
        with pytest.warns(DeprecationWarning):
            with pytest.raises(ValueError, match='region is required'):
                internal_create_serverless_cluster(
                    region='',
                    cluster_identifier='test-cluster',
                    engine_version='8.0',
                    database_name='testdb',
                )
