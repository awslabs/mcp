"""Comprehensive test suite for RDS cluster management functions defined in cp_api_connection.py."""

import pytest
from awslabs.postgres_mcp_server.connection.cp_api_connection import (
    internal_create_rds_client,
    internal_create_serverless_cluster,
    internal_get_cluster_properties,
)
from botocore.exceptions import ClientError, WaiterError
from typing import Dict, List, Optional
from unittest.mock import ANY, MagicMock, patch


# =============================================================================
# MOCK DATA FACTORIES
# =============================================================================


def create_mock_cluster_response(
    cluster_id: str = 'test-cluster',
    status: str = 'available',
    include_secret: bool = True,
    members: Optional[List[str]] = None,
) -> Dict:
    """Create a mock RDS cluster response."""
    cluster = {
        'DBCluster': {
            'DBClusterIdentifier': cluster_id,
            'DBClusterArn': f'arn:aws:rds:us-east-1:123456789012:cluster:{cluster_id}',
            'Status': status,
            'Endpoint': f'{cluster_id}.cluster-abc123.us-east-1.rds.amazonaws.com',
            'ReaderEndpoint': f'{cluster_id}.cluster-ro-abc123.us-east-1.rds.amazonaws.com',
            'Port': 5432,
            'Engine': 'aurora-postgresql',
            'EngineVersion': '15.3',
            'MasterUsername': 'postgres',
            'DatabaseName': 'postgres',
            'DBClusterMembers': [{'DBInstanceIdentifier': member} for member in (members or [])],
        }
    }

    if include_secret:
        cluster['DBCluster']['MasterUserSecret'] = {
            'SecretArn': f'arn:aws:secretsmanager:us-east-1:123456789012:secret:{cluster_id}-secret-abc123'
        }

    return cluster


def create_mock_instance_response(
    instance_id: str = 'test-instance', cluster_id: str = 'test-cluster', status: str = 'available'
) -> Dict:
    """Create a mock RDS instance response."""
    return {
        'DBInstance': {
            'DBInstanceIdentifier': instance_id,
            'DBInstanceArn': f'arn:aws:rds:us-east-1:123456789012:db:{instance_id}',
            'DBClusterIdentifier': cluster_id,
            'DBInstanceStatus': status,
            'Engine': 'aurora-postgresql',
            'DBInstanceClass': 'db.serverless',
        }
    }


def create_mock_tags(include_mcp: bool = True) -> Dict:
    """Create a mock tags response."""
    tags = [{'Key': 'Environment', 'Value': 'test'}]
    if include_mcp:
        tags.append({'Key': 'CreatedBy', 'Value': 'MCP'})
    return {'TagList': tags}


def create_client_error(error_code: str, message: str = 'Test error') -> ClientError:
    """Create a mock ClientError."""
    return ClientError(
        error_response={'Error': {'Code': error_code, 'Message': message}},
        operation_name='TestOperation',
    )


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_rds_client():
    """Create a mock RDS client with proper waiter handling."""
    client = MagicMock()

    # Setup default successful responses
    client.create_db_cluster.return_value = create_mock_cluster_response(status='creating')
    client.create_db_instance.return_value = create_mock_instance_response(status='creating')
    client.describe_db_clusters.return_value = {
        'DBClusters': [create_mock_cluster_response()['DBCluster']]
    }
    client.describe_db_instances.return_value = {
        'DBInstances': [create_mock_instance_response()['DBInstance']]
    }
    client.list_tags_for_resource.return_value = create_mock_tags()
    client.delete_db_cluster.return_value = {}
    client.delete_db_instance.return_value = {}

    # Setup waiters - create new mock for each waiter type
    def get_waiter_side_effect(waiter_name):
        mock_waiter = MagicMock()
        mock_waiter.wait.return_value = None
        mock_waiter.name = waiter_name
        return mock_waiter

    client.get_waiter.side_effect = get_waiter_side_effect

    return client


@pytest.fixture
def mock_boto3_client(mock_rds_client):
    """Mock boto3.client to return our mock RDS client."""
    # NOTE: Change 'awslabs.postgres_mcp_server.connection.cp_api_connection' to actual module name
    with patch(
        'awslabs.postgres_mcp_server.connection.cp_api_connection.boto3.client',
        return_value=mock_rds_client,
    ) as mock:
        yield mock


@pytest.fixture
def mock_time_sleep():
    """Mock time.sleep to speed up tests."""
    # NOTE: Change 'awslabs.postgres_mcp_server.connection.cp_api_connection' to actual module name
    with patch('awslabs.postgres_mcp_server.connection.cp_api_connection.time.sleep') as mock:
        yield mock


@pytest.fixture
def mock_logger():
    """Mock loguru logger."""
    # NOTE: Change 'awslabs.postgres_mcp_server.connection.cp_api_connection' to actual module name
    with patch('awslabs.postgres_mcp_server.connection.cp_api_connection.logger') as mock:
        yield mock


@pytest.fixture
def mock_print():
    """Mock print to avoid cluttering test output."""
    with patch('builtins.print') as mock:
        yield mock


# =============================================================================
# TESTS FOR: internal_create_rds_client
# =============================================================================


class TestInternalCreateRdsClient:
    """Tests for internal_create_rds_client function."""

    @patch('awslabs.postgres_mcp_server.connection.cp_api_connection.boto3.client')
    def test_create_rds_client_standard(self, mock_boto3_client):
        """Test creating standard RDS client."""
        internal_create_rds_client(region='us-west-2')

        mock_boto3_client.assert_called_once_with('rds', region_name='us-west-2', config=ANY)


# =============================================================================
# TESTS FOR: internal_get_cluster_properties
# =============================================================================


class TestInternalGetClusterProperties:
    """Tests for internal_get_cluster_properties function."""

    def test_get_cluster_properties_empty_cluster_id_raises_error(self):
        """Test that empty cluster_identifier raises ValueError."""
        with pytest.raises(ValueError, match='cluster_identifier and region are required'):
            internal_get_cluster_properties('', 'us-east-1')

    def test_get_cluster_properties_empty_region_raises_error(self):
        """Test that empty region raises ValueError."""
        with pytest.raises(ValueError, match='cluster_identifier and region are required'):
            internal_get_cluster_properties('test-cluster', '')

    @patch('awslabs.postgres_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_get_cluster_properties_empty_response(self, mock_create_client):
        """Test handling of empty DBClusters list."""
        mock_rds_client = MagicMock()
        mock_create_client.return_value = mock_rds_client
        mock_rds_client.describe_db_clusters.return_value = {'DBClusters': []}

        with pytest.raises(ValueError, match="Cluster 'test-cluster' not found"):
            internal_get_cluster_properties('test-cluster', 'us-east-1')

    @patch('awslabs.postgres_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_get_cluster_properties_success(self, mock_create_client):
        """Test successfully retrieving cluster properties."""
        # Setup mock
        mock_rds_client = MagicMock()
        mock_create_client.return_value = mock_rds_client
        mock_rds_client.describe_db_clusters.return_value = {
            'DBClusters': [
                {
                    'DBClusterIdentifier': 'test-cluster',
                    'Status': 'available',
                    'Engine': 'aurora-postgresql',
                }
            ]
        }

        # Execute
        result = internal_get_cluster_properties('test-cluster', 'us-west-2')

        # Verify
        assert result['DBClusterIdentifier'] == 'test-cluster'
        assert result['Status'] == 'available'
        mock_create_client.assert_called_once_with('us-west-2')
        mock_rds_client.describe_db_clusters.assert_called_once_with(
            DBClusterIdentifier='test-cluster'
        )

    @patch('awslabs.postgres_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_get_cluster_properties_client_error(self, mock_create_client):
        """Test handling of AWS ClientError."""
        mock_rds_client = MagicMock()
        mock_create_client.return_value = mock_rds_client
        mock_rds_client.describe_db_clusters.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'DescribeDBClusters'
        )

        with pytest.raises(ClientError):
            internal_get_cluster_properties('test-cluster', 'us-west-2')


# =============================================================================
# TESTS FOR: internal_create_serverless_cluster
# =============================================================================


class TestInternalCreateServerlessCluster:
    """Tests for internal_create_serverless_cluster function."""

    def test_missing_region_raises_error(self):
        """Test that missing region raises ValueError."""
        with pytest.raises(ValueError, match='region is required'):
            internal_create_serverless_cluster(
                region='',
                cluster_identifier='test-cluster',
                engine_version='17.5',
                database_name='testdb',
            )

    def test_missing_cluster_identifier_raises_error(self):
        """Test that missing cluster_identifier raises ValueError."""
        with pytest.raises(ValueError, match='cluster_identifier is required'):
            internal_create_serverless_cluster(
                region='us-east-1',
                cluster_identifier='',
                engine_version='17.5',
                database_name='testdb',
            )

    def test_missing_engine_version_raises_error(self):
        """Test that missing engine_version raises ValueError."""
        with pytest.raises(ValueError, match='engine_version is required'):
            internal_create_serverless_cluster(
                region='us-east-1',
                cluster_identifier='test-cluster',
                engine_version='',
                database_name='testdb',
            )

    def test_missing_database_name_raises_error(self):
        """Test that missing database_name raises ValueError."""
        with pytest.raises(ValueError, match='database_name is required'):
            internal_create_serverless_cluster(
                region='us-east-1',
                cluster_identifier='test-cluster',
                engine_version='17.5',
                database_name='',
            )

    def test_successful_cluster_creation(
        self, mock_boto3_client, mock_rds_client, mock_logger, mock_print
    ):
        """Test successful cluster and instance creation."""
        # Execute
        result = internal_create_serverless_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='15.3',
            database_name='testdb',
            master_username='admin',
            min_capacity=0.5,
            max_capacity=1.0,
            enable_cloudwatch_logs=True,
        )

        # Verify the function returns a dictionary (cluster object)
        assert isinstance(result, dict)
        assert result['DBClusterIdentifier'] == 'test-cluster'
        assert result['DBClusterArn'] == 'arn:aws:rds:us-east-1:123456789012:cluster:test-cluster'

        # Verify MasterUserSecret is present in the response
        assert 'MasterUserSecret' in result
        assert 'SecretArn' in result['MasterUserSecret']

        # Verify boto3.client was called correctly
        mock_boto3_client.assert_called_once_with('rds', region_name='us-east-1', config=ANY)

        # Verify create_db_cluster was called with correct params
        mock_rds_client.create_db_cluster.assert_called_once()
        cluster_call_kwargs = mock_rds_client.create_db_cluster.call_args[1]

        assert cluster_call_kwargs['DBClusterIdentifier'] == 'test-cluster'
        assert cluster_call_kwargs['Engine'] == 'aurora-postgresql'
        assert cluster_call_kwargs['EngineVersion'] == '15.3'
        assert cluster_call_kwargs['MasterUsername'] == 'admin'
        assert cluster_call_kwargs['DatabaseName'] == 'testdb'
        assert cluster_call_kwargs['ManageMasterUserPassword'] is True
        assert cluster_call_kwargs['EnableCloudwatchLogsExports'] == ['postgresql']
        assert cluster_call_kwargs['ServerlessV2ScalingConfiguration'] == {
            'MinCapacity': 0.5,
            'MaxCapacity': 1.0,
        }
        assert any(
            tag['Key'] == 'CreatedBy' and tag['Value'] == 'MCP'
            for tag in cluster_call_kwargs['Tags']
        )

        # Verify waiter was called for cluster
        assert any(
            call_args[0][0] == 'db_cluster_available'
            for call_args in mock_rds_client.get_waiter.call_args_list
        )

        # Verify create_db_instance was called
        mock_rds_client.create_db_instance.assert_called_once()
        instance_call_kwargs = mock_rds_client.create_db_instance.call_args[1]

        assert instance_call_kwargs['DBInstanceIdentifier'] == 'test-cluster-instance-1'
        assert instance_call_kwargs['DBInstanceClass'] == 'db.serverless'
        assert instance_call_kwargs['Engine'] == 'aurora-postgresql'
        assert instance_call_kwargs['DBClusterIdentifier'] == 'test-cluster'

        # Verify waiter was called for instance
        assert any(
            call_args[0][0] == 'db_instance_available'
            for call_args in mock_rds_client.get_waiter.call_args_list
        )

        # Verify describe_db_clusters was called to get final details
        mock_rds_client.describe_db_clusters.assert_called_with(DBClusterIdentifier='test-cluster')

        # Verify logging
        assert mock_logger.info.call_count > 0

    def test_cloudwatch_logs_disabled(self, mock_boto3_client, mock_rds_client, mock_print):
        """Test cluster creation with CloudWatch logs disabled."""
        internal_create_serverless_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='15.3',
            database_name='testdb',
            master_username='testuser',
            min_capacity=0.5,
            max_capacity=1.0,
            enable_cloudwatch_logs=False,
        )

        cluster_call_kwargs = mock_rds_client.create_db_cluster.call_args[1]
        assert cluster_call_kwargs['EnableCloudwatchLogsExports'] == []

    def test_cluster_creation_fails(self, mock_boto3_client, mock_rds_client, mock_print):
        """Test handling of cluster creation failure."""
        # Setup mock to raise error
        mock_rds_client.create_db_cluster.side_effect = create_client_error(
            'InvalidParameterValue', 'Invalid engine version'
        )

        # Execute and verify exception
        with pytest.raises(ClientError) as exc_info:
            internal_create_serverless_cluster(
                region='us-east-1',
                cluster_identifier='test-cluster',
                engine_version='invalid',
                database_name='testdb',
                master_username='admin',
                min_capacity=0.5,
                max_capacity=1.0,
            )

        assert exc_info.value.response['Error']['Code'] == 'InvalidParameterValue'

        # Verify instance creation was not attempted
        mock_rds_client.create_db_instance.assert_not_called()

    def test_cluster_waiter_timeout(self, mock_boto3_client, mock_rds_client, mock_print):
        """Test handling of cluster waiter timeout."""

        # Setup waiter to raise timeout error
        def get_waiter_side_effect(waiter_name):
            mock_waiter = MagicMock()
            if waiter_name == 'db_cluster_available':
                mock_waiter.wait.side_effect = WaiterError(
                    name='db_cluster_available', reason='Max attempts exceeded', last_response={}
                )
            else:
                mock_waiter.wait.return_value = None
            return mock_waiter

        mock_rds_client.get_waiter.side_effect = get_waiter_side_effect

        with pytest.raises(WaiterError):
            internal_create_serverless_cluster(
                region='us-east-1',
                cluster_identifier='test-cluster',
                engine_version='15.3',
                database_name='testdb',
                master_username='admin',
                min_capacity=0.5,
                max_capacity=1.0,
            )

        # Verify instance creation was not attempted
        mock_rds_client.create_db_instance.assert_not_called()

    def test_instance_creation_fails(self, mock_boto3_client, mock_rds_client, mock_print):
        """Test handling of instance creation failure after successful cluster creation."""
        # Setup instance creation to fail
        mock_rds_client.create_db_instance.side_effect = create_client_error(
            'InvalidParameterCombination', 'Invalid instance configuration'
        )

        with pytest.raises(ClientError) as exc_info:
            internal_create_serverless_cluster(
                region='us-east-1',
                cluster_identifier='test-cluster',
                engine_version='15.3',
                database_name='testdb',
                master_username='admin',
                min_capacity=0.5,
                max_capacity=1.0,
            )

        assert exc_info.value.response['Error']['Code'] == 'InvalidParameterCombination'

        # Verify cluster was created but instance failed
        mock_rds_client.create_db_cluster.assert_called_once()
        mock_rds_client.create_db_instance.assert_called_once()

    def test_instance_waiter_timeout(self, mock_boto3_client, mock_rds_client, mock_print):
        """Test handling of instance waiter timeout."""

        # Setup waiters - cluster succeeds, instance times out
        def get_waiter_side_effect(waiter_name):
            mock_waiter = MagicMock()
            if waiter_name == 'db_cluster_available':
                mock_waiter.wait.return_value = None
            elif waiter_name == 'db_instance_available':
                mock_waiter.wait.side_effect = WaiterError(
                    name='db_instance_available', reason='Max attempts exceeded', last_response={}
                )
            return mock_waiter

        mock_rds_client.get_waiter.side_effect = get_waiter_side_effect

        with pytest.raises(WaiterError):
            internal_create_serverless_cluster(
                region='us-east-1',
                cluster_identifier='test-cluster',
                engine_version='15.3',
                database_name='testdb',
                master_username='admin',
                min_capacity=0.5,
                max_capacity=1.0,
            )

        # Verify both cluster and instance were created
        mock_rds_client.create_db_cluster.assert_called_once()
        mock_rds_client.create_db_instance.assert_called_once()

    def test_no_secret_arn_in_response(self, mock_boto3_client, mock_rds_client, mock_print):
        """Test handling when MasterUserSecret is not in response."""
        # Setup response without secret
        mock_rds_client.describe_db_clusters.return_value = {
            'DBClusters': [create_mock_cluster_response(include_secret=False)['DBCluster']]
        }

        result = internal_create_serverless_cluster(
            region='us-east-1',
            cluster_identifier='test-cluster',
            engine_version='15.3',
            database_name='testdb',
            master_username='admin',
            min_capacity=0.5,
            max_capacity=1.0,
        )

        # Verify the function returns a dictionary (cluster object)
        assert isinstance(result, dict)
        assert result['DBClusterArn'] == 'arn:aws:rds:us-east-1:123456789012:cluster:test-cluster'
        # Verify MasterUserSecret is not in the response
        assert 'MasterUserSecret' not in result

    def test_unexpected_exception(self, mock_boto3_client, mock_rds_client, mock_print):
        """Test handling of unexpected exceptions."""
        mock_rds_client.create_db_cluster.side_effect = Exception('Unexpected error')

        with pytest.raises(Exception) as exc_info:
            internal_create_serverless_cluster(
                region='us-east-1',
                cluster_identifier='test-cluster',
                engine_version='15.3',
                database_name='testdb',
                master_username='admin',
                min_capacity=0.5,
                max_capacity=1.0,
            )

        assert 'Unexpected error' in str(exc_info.value)


# =============================================================================
# TESTS FOR: setup_aurora_iam_policy_for_current_user
# =============================================================================


class TestSetupAuroraIamPolicy:
    """Tests for setup_aurora_iam_policy_for_current_user function."""

    @pytest.fixture
    def mock_sts_client(self):
        """Mock STS client."""
        from botocore.exceptions import ClientError

        with patch('boto3.client') as mock_client:
            mock_sts = MagicMock()
            mock_iam = MagicMock()

            # Mock IAM exceptions
            class MockIAMExceptions:
                NoSuchEntityException = type('NoSuchEntityException', (ClientError,), {})
                EntityAlreadyExistsException = type(
                    'EntityAlreadyExistsException', (ClientError,), {}
                )

            mock_iam.exceptions = MockIAMExceptions()

            def client_factory(service_name, **kwargs):
                if service_name == 'sts':
                    return mock_sts
                elif service_name == 'iam':
                    return mock_iam
                return MagicMock()

            mock_client.side_effect = client_factory
            yield mock_sts, mock_iam

    def test_iam_user_identity(self, mock_sts_client):
        """Test policy setup for IAM user identity."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_sts_client

        # Mock IAM user identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/testuser',
            'UserId': 'AIDAI123456789EXAMPLE',
        }

        # Mock policy doesn't exist
        mock_iam.get_policy.side_effect = mock_iam.exceptions.NoSuchEntityException(
            {'Error': {'Code': 'NoSuchEntity'}}, 'GetPolicy'
        )

        # Mock policy creation
        mock_iam.create_policy.return_value = {
            'Policy': {'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-dbuser'}
        }

        # Mock policy attachment
        mock_iam.attach_user_policy.return_value = {}

        setup_aurora_iam_policy_for_current_user(
            db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
        )

        # Verify policy was created
        assert mock_iam.create_policy.called
        create_call = mock_iam.create_policy.call_args
        assert create_call[1]['PolicyName'] == 'AuroraIAMAuth-dbuser'

        # Verify policy was attached to user
        mock_iam.attach_user_policy.assert_called_once()
        attach_call = mock_iam.attach_user_policy.call_args
        assert attach_call[1]['UserName'] == 'testuser'

    def test_assumed_role_identity(self, mock_sts_client):
        """Test policy setup for assumed role identity."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_sts_client

        # Mock assumed role identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/MyRole/session-name',
            'UserId': 'AROAI123456789EXAMPLE:session-name',
        }

        # Mock policy doesn't exist
        mock_iam.get_policy.side_effect = mock_iam.exceptions.NoSuchEntityException(
            {'Error': {'Code': 'NoSuchEntity'}}, 'GetPolicy'
        )

        # Mock policy creation
        mock_iam.create_policy.return_value = {
            'Policy': {'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-dbuser'}
        }

        # Mock policy attachment
        mock_iam.attach_role_policy.return_value = {}

        setup_aurora_iam_policy_for_current_user(
            db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
        )

        # Verify policy was attached to base role (not session)
        mock_iam.attach_role_policy.assert_called_once()
        attach_call = mock_iam.attach_role_policy.call_args
        assert attach_call[1]['RoleName'] == 'MyRole'

    def test_federated_user_raises_error(self, mock_sts_client):
        """Test that federated user identity raises ValueError."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_sts_client

        # Mock federated user identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:federated-user/feduser',
            'UserId': 'FEDUSER123',
        }

        with pytest.raises(ValueError, match='Cannot attach policies to federated users'):
            setup_aurora_iam_policy_for_current_user(
                db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
            )

    def test_root_user_raises_error(self, mock_sts_client):
        """Test that root user identity raises ValueError."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_sts_client

        # Mock root user identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:root',
            'UserId': '123456789012',
        }

        with pytest.raises(ValueError, match='Cannot .* attach policies to root user'):
            setup_aurora_iam_policy_for_current_user(
                db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
            )

    def test_invalid_db_user_raises_error(self, mock_sts_client):
        """Test that invalid db_user raises ValueError."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        with pytest.raises(ValueError, match='db_user must be a non-empty string'):
            setup_aurora_iam_policy_for_current_user(
                db_user='', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
            )

    def test_invalid_cluster_resource_id_raises_error(self, mock_sts_client):
        """Test that invalid cluster_resource_id raises ValueError."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        with pytest.raises(ValueError, match='cluster_resource_id must be a non-empty string'):
            setup_aurora_iam_policy_for_current_user(
                db_user='dbuser', cluster_resource_id='', cluster_region='us-east-1'
            )

    def test_invalid_cluster_region_raises_error(self, mock_sts_client):
        """Test that invalid cluster_region raises ValueError."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        with pytest.raises(ValueError, match='cluster_region must be a non-empty string'):
            setup_aurora_iam_policy_for_current_user(
                db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region=''
            )

    def test_policy_update_adds_new_resource(self, mock_sts_client):
        """Test that existing policy is updated with new resource."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_sts_client

        # Mock IAM user identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/testuser',
            'UserId': 'AIDAI123456789EXAMPLE',
        }

        # Mock existing policy
        mock_iam.get_policy.return_value = {
            'Policy': {
                'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-dbuser',
                'DefaultVersionId': 'v1',
            }
        }

        # Mock existing policy document with one resource
        mock_iam.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': 'rds-db:connect',
                            'Resource': [
                                'arn:aws:rds-db:us-east-1:123456789012:dbuser:cluster-OLD123/dbuser'
                            ],
                        }
                    ],
                }
            }
        }

        # Mock policy versions (less than 5)
        mock_iam.list_policy_versions.return_value = {
            'Versions': [{'VersionId': 'v1', 'IsDefaultVersion': True, 'CreateDate': '2024-01-01'}]
        }

        # Mock policy version creation
        mock_iam.create_policy_version.return_value = {'PolicyVersion': {'VersionId': 'v2'}}

        setup_aurora_iam_policy_for_current_user(
            db_user='dbuser', cluster_resource_id='cluster-NEW456', cluster_region='us-east-1'
        )

        # Verify new policy version was created
        assert mock_iam.create_policy_version.called
        create_call = mock_iam.create_policy_version.call_args

        # Parse the policy document
        import json

        policy_doc = json.loads(create_call[1]['PolicyDocument'])
        resources = policy_doc['Statement'][0]['Resource']

        # Verify both old and new resources are present
        assert len(resources) == 2
        assert 'cluster-OLD123' in str(resources)
        assert 'cluster-NEW456' in str(resources)

    def test_policy_already_includes_resource(self, mock_sts_client):
        """Test that no update occurs if resource already exists in policy."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_sts_client

        # Mock IAM user identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/testuser',
            'UserId': 'AIDAI123456789EXAMPLE',
        }

        # Mock existing policy
        mock_iam.get_policy.return_value = {
            'Policy': {
                'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-dbuser',
                'DefaultVersionId': 'v1',
            }
        }

        # Mock policy document that already includes the resource
        mock_iam.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': 'rds-db:connect',
                            'Resource': [
                                'arn:aws:rds-db:us-east-1:123456789012:dbuser:cluster-ABC123/dbuser'
                            ],
                        }
                    ],
                }
            }
        }

        setup_aurora_iam_policy_for_current_user(
            db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
        )

        # Verify no new policy version was created
        mock_iam.create_policy_version.assert_not_called()

    def test_policy_version_limit_deletes_oldest(self, mock_sts_client):
        """Test that oldest version is deleted when limit is reached."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_sts_client

        # Mock IAM user identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/testuser',
            'UserId': 'AIDAI123456789EXAMPLE',
        }

        # Mock existing policy
        mock_iam.get_policy.return_value = {
            'Policy': {
                'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-dbuser',
                'DefaultVersionId': 'v5',
            }
        }

        # Mock existing policy document
        mock_iam.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': 'rds-db:connect',
                            'Resource': [
                                'arn:aws:rds-db:us-east-1:123456789012:dbuser:cluster-OLD/dbuser'
                            ],
                        }
                    ],
                }
            }
        }

        # Mock 5 policy versions (at limit)
        from datetime import datetime

        mock_iam.list_policy_versions.return_value = {
            'Versions': [
                {'VersionId': 'v1', 'IsDefaultVersion': False, 'CreateDate': datetime(2024, 1, 1)},
                {'VersionId': 'v2', 'IsDefaultVersion': False, 'CreateDate': datetime(2024, 1, 2)},
                {'VersionId': 'v3', 'IsDefaultVersion': False, 'CreateDate': datetime(2024, 1, 3)},
                {'VersionId': 'v4', 'IsDefaultVersion': False, 'CreateDate': datetime(2024, 1, 4)},
                {'VersionId': 'v5', 'IsDefaultVersion': True, 'CreateDate': datetime(2024, 1, 5)},
            ]
        }

        # Mock policy version creation
        mock_iam.create_policy_version.return_value = {'PolicyVersion': {'VersionId': 'v6'}}

        setup_aurora_iam_policy_for_current_user(
            db_user='dbuser', cluster_resource_id='cluster-NEW', cluster_region='us-east-1'
        )

        # Verify oldest version was deleted
        mock_iam.delete_policy_version.assert_called_once()
        delete_call = mock_iam.delete_policy_version.call_args
        assert delete_call[1]['VersionId'] == 'v1'  # Oldest non-default version
