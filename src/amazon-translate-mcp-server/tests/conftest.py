import os
import pytest
from unittest.mock import MagicMock, patch


TEMP_ENV_VARS = {
    'AWS_REGION': 'us-east-1',
    'FASTMCP_LOG_LEVEL': 'ERROR',  # Reduce logging noise in tests
}


@pytest.fixture(scope='session', autouse=True)
def tests_setup_and_teardown():
    """Mock environment variables for testing."""
    global TEMP_ENV_VARS
    # Will be executed before the first test
    old_environ = dict(os.environ)
    os.environ.update(TEMP_ENV_VARS)

    yield
    # Will be executed after the last test
    os.environ.clear()
    os.environ.update(old_environ)


@pytest.fixture
def mock_boto3():
    """Create a mock boto3 module."""
    with patch('boto3.client') as mock_client, patch('boto3.Session') as mock_session:
        mock_translate = MagicMock()
        mock_s3 = MagicMock()
        mock_sts = MagicMock()
        mock_cloudwatch = MagicMock()

        mock_client.side_effect = lambda service, region_name=None, **kwargs: {
            'translate': mock_translate,
            's3': mock_s3,
            'sts': mock_sts,
            'cloudwatch': mock_cloudwatch,
        }[service]

        mock_session_instance = MagicMock()
        mock_session_instance.client.side_effect = lambda service, region_name=None, **kwargs: {
            'translate': mock_translate,
            's3': mock_s3,
            'sts': mock_sts,
            'cloudwatch': mock_cloudwatch,
        }[service]
        mock_session.return_value = mock_session_instance

        yield {
            'client': mock_client,
            'Session': mock_session,
            'translate': mock_translate,
            's3': mock_s3,
            'sts': mock_sts,
            'cloudwatch': mock_cloudwatch,
        }
