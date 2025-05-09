import os
import pytest
from unittest.mock import MagicMock, patch


TEMP_ENV_VARS = {
    'NEPTUNE_ENDPOINT': 'neptune-db://fake:8182'
}


@pytest.fixture(scope="session", autouse=True)
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
def mock_boto3():
    """Create a mock boto3 module."""
    with patch('boto3.client') as mock_client, patch('boto3.Session') as mock_session:
        mock_neptunedb = MagicMock()
        mock_neptuneanalytics = MagicMock()

        mock_client.side_effect = lambda service, region_name=None: {
            'neptunedata': mock_neptunedb,
            'neptune-graph': mock_neptuneanalytics,
        }[service]

        mock_session_instance = MagicMock()
        mock_session_instance.client.side_effect = lambda service, region_name=None: {
            'neptunedata': mock_neptunedb,
            'neptune-graph': mock_neptuneanalytics,
        }[service]
        mock_session.return_value = mock_session_instance

        yield {
            'client': mock_client,
            'Session': mock_session,
            'neptunedata': mock_neptunedb,
            'neptune-graph': mock_neptuneanalytics,
        }
