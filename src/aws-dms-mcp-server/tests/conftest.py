"""Pytest configuration and fixtures for AWS DMS MCP Server tests."""

import pytest
from awslabs.aws_dms_mcp_server.config import DMSServerConfig
from awslabs.aws_dms_mcp_server.utils.dms_client import DMSClient
from unittest.mock import MagicMock, Mock


@pytest.fixture
def mock_config():
    """Provide a test configuration.

    Returns:
        DMSServerConfig with test settings
    """
    return DMSServerConfig(
        aws_region='us-east-1',
        read_only_mode=False,
        log_level='DEBUG',
        enable_connection_caching=False,
    )


@pytest.fixture
def mock_dms_client(mock_config):
    """Provide a mocked DMS client.

    Returns:
        Mocked DMSClient instance
    """
    client = Mock(spec=DMSClient)
    client.config = mock_config
    return client


@pytest.fixture
def mock_boto3_client():
    """Provide a mocked boto3 DMS client.

    Returns:
        Mocked boto3 client
    """
    client = MagicMock()
    # TODO: Add common mock responses
    return client


@pytest.fixture
def sample_instance_response():
    """Provide sample replication instance response.

    Returns:
        Dictionary with sample instance data
    """
    return {
        'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789:rep:TEST',
        'ReplicationInstanceIdentifier': 'test-instance',
        'ReplicationInstanceClass': 'dms.t3.medium',
        'ReplicationInstanceStatus': 'available',
        'AllocatedStorage': 50,
        'EngineVersion': '3.5.3',
        'MultiAZ': False,
        'PubliclyAccessible': False,
    }


@pytest.fixture
def sample_endpoint_response():
    """Provide sample endpoint response.

    Returns:
        Dictionary with sample endpoint data
    """
    return {
        'EndpointArn': 'arn:aws:dms:us-east-1:123456789:endpoint:TEST',
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


@pytest.fixture
def sample_task_response():
    """Provide sample replication task response.

    Returns:
        Dictionary with sample task data
    """
    return {
        'ReplicationTaskArn': 'arn:aws:dms:us-east-1:123456789:task:TEST',
        'ReplicationTaskIdentifier': 'test-task',
        'Status': 'running',
        'MigrationType': 'full-load-and-cdc',
        'SourceEndpointArn': 'arn:aws:dms:us-east-1:123456789:endpoint:SRC',
        'TargetEndpointArn': 'arn:aws:dms:us-east-1:123456789:endpoint:TGT',
        'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789:rep:INST',
    }


# TODO: Add fixtures for table statistics
# TODO: Add fixtures for connection test results
# TODO: Add fixtures for error responses
# TODO: Add moto AWS service mocking setup
