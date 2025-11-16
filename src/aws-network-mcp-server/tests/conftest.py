import os
import pytest
from unittest.mock import patch


TEMP_ENV_VARS = {
    'AWS_REGION': 'us-east-1',
    'AWS_DEFAULT_REGION': 'us-east-1',
}


@pytest.fixture(scope='session', autouse=True)
def tests_setup_and_teardown():
    """Mock environment and module variables for testing."""
    global TEMP_ENV_VARS
    # Will be executed before the first test
    old_environ = dict(os.environ)
    os.environ.update(TEMP_ENV_VARS)

    yield
    # Will be executed after the last test
    os.environ.clear()
    os.environ.update(old_environ)


@pytest.fixture
def mock_aws_credentials():
    """Fixture to mock AWS credentials environment variables."""
    with patch.dict(
        os.environ,
        {
            'AWS_ACCESS_KEY_ID': 'test-access-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret-key',  # pragma: allowlist secret
            'AWS_REGION': 'us-east-1',
        },
    ):
        yield


@pytest.fixture
def sample_eni_response():
    """Common ENI response fixture for all tests."""
    return {
        'NetworkInterfaceId': 'eni-12345678',
        'VpcId': 'vpc-12345678',
        'SubnetId': 'subnet-12345678',
        'PrivateIpAddress': '10.0.1.100',
        'Groups': [{'GroupId': 'sg-12345678', 'GroupName': 'test-sg'}],
        'InterfaceType': 'interface',
        'Status': 'in-use',
        'AvailabilityZone': 'us-east-1a',
    }


@pytest.fixture
def sample_vpc_response():
    """Common VPC response fixture for all tests."""
    return {
        'VpcId': 'vpc-12345678',
        'State': 'available',
        'CidrBlock': '10.0.0.0/16',
        'DhcpOptionsId': 'dopt-12345678',
        'InstanceTenancy': 'default',
        'IsDefault': False,
    }
