import pytest
from botocore.exceptions import ClientError
from typing import List


class Mock_boto3_client:
    """Mock implementation of boto3 client for testing purposes."""

    def __init__(self, throw_client_error=False):
        """Initialize the mock boto3 client.

        Args:
            throw_client_error: Whether to simulate a client error
        """
        self._responses: List[dict] = []
        self.throw_client_error = throw_client_error
        self._current_response_index = 0

    def execute_statement(self, **kwargs) -> dict:
        """Mock implementation of execute_statement.

        Returns:
            dict: The mock response

        Raises:
            ClientError: If throw_client_error is True
            Exception: If no more mock responses are available
        """
        if self.throw_client_error:
            error_response = {
                'Error': {
                    'Code': 'AccessDeniedException',
                    'Message': 'User is not authorized to perform rds-data:ExecuteStatement',
                }
            }
            raise ClientError(error_response, operation_name='ExecuteStatement')

        if self._current_response_index < len(self._responses):
            response = self._responses[self._current_response_index]
            self._current_response_index += 1
            return response
        raise Exception('Mock_boto3_client.execute_statement mock response out of bound')

    def add_mock_response(self, response):
        """Add a mock response to be returned by execute_statement.

        Args:
            response: The mock response to add
        """
        self._responses.append(response)


class Mock_DBConnection:
    """Mock implementation of DBConnection for testing purposes."""

    def __init__(self, readonly, throw_client_error=False):
        """Initialize the mock DB connection.

        Args:
            readonly: Whether the connection should be read-only
            throw_client_error: Whether to simulate a client error
        """
        self.cluster_arn = 'dummy_cluster_arn'
        self.secret_arn = 'dummy_secret_arn'  # pragma: allowlist secret
        self.database = 'dummy_database'
        self.readonly = readonly
        self.throw_client_error = throw_client_error
        self._data_client = Mock_boto3_client(throw_client_error)

    @property
    def data_client(self):
        """Get the mock data client.

        Returns:
            Mock_boto3_client: The mock boto3 client
        """
        return self._data_client

    @property
    def readonly_query(self):
        """Get whether this connection is read-only.

        Returns:
            bool: True if the connection is read-only, False otherwise
        """
        return self.readonly


class DummyCtx:
    """Mock implementation of MCP context for testing purposes."""

    def error(self, message):
        """Raise a runtime error with the given message.

        Args:
            message: The error message to include in the runtime error
        """
        raise RuntimeError(f'MCP Tool Error: {message}')


@pytest.fixture
def mock_DBConnection():
    """Fixture that provides a mock DB connection for testing.

    Returns:
        Mock_DBConnection: A mock database connection
    """
    return Mock_DBConnection(readonly=True)
