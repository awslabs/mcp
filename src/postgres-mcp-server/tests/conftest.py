import pytest
from botocore.exceptions import ClientError
from enum import Enum
from typing import List


class MockException(Enum):
    """Mock exception type."""

    No = 'none'
    Client = 'client'
    Unexpected = 'unexpected'


class Mock_psycopg2_connection:
    """Mock implementation of psycopg2 connection for IAM auth testing."""

    def __init__(self, error: MockException = MockException.No):
        """Initialize mock psycopg2 connection.

        Args:
            error: Whether to simulate an error
        """
        self.error = error
        self._cursor = Mock_psycopg2_cursor(error)
        self._closed = False

    def cursor(self):
        """Get a cursor for the connection."""
        if self.error == MockException.Unexpected:
            raise Exception('Connection error')
        return self._cursor

    def set_session(self, readonly=False):
        """Set session properties."""
        if self.error == MockException.Client:
            raise Exception('Session error')
        # Mock implementation - just store the setting
        self._readonly = readonly

    def close(self):
        """Close the connection."""
        self._closed = True


class Mock_psycopg2_cursor:
    """Mock implementation of psycopg2 cursor for IAM auth testing."""

    def __init__(self, error: MockException = MockException.No):
        """Initialize mock cursor.

        Args:
            error: Whether to simulate an error
        """
        self.error = error
        self.description = None
        self._results = []

    def execute(self, sql, parameters=None):
        """Execute a SQL statement."""
        if self.error == MockException.Unexpected:
            raise Exception('Query execution error')
        if self.error == MockException.Client:
            raise Exception('Database error')

        # Mock successful execution - set up mock results
        self.description = [('column1',), ('column2',), ('column3',)]  # Mock column descriptions
        self._results = [('value1', 'value2', 'value3')]  # Mock row data

    def fetchall(self):
        """Fetch all results."""
        return self._results


class Mock_rds_client:
    """Mock implementation of RDS client for IAM auth token generation."""

    def __init__(self, error: MockException = MockException.No):
        """Initialize mock RDS client.

        Args:
            error: Whether to simulate an error
        """
        self.error = error

    def generate_db_auth_token(self, DBHostname, Port, DBUsername, Region):
        """Mock IAM auth token generation."""
        if self.error == MockException.Client:
            error_response = {
                'Error': {
                    'Code': 'AccessDeniedException',
                    'Message': 'User is not authorized to generate auth token',
                }
            }
            raise ClientError(error_response, operation_name='generate_db_auth_token')

        if self.error == MockException.Unexpected:
            raise Exception('Unexpected error generating auth token')

        return 'mock-iam-auth-token'


class Mock_boto3_client:
    """Mock implementation of boto3 client for testing purposes."""

    def __init__(self, error: MockException = MockException.No):
        """Initialize the mock boto3 client.

        Args:
            error: Whether to simulate an error
        """
        self._responses: List[dict] = []
        self.error = error
        self._current_response_index = 0

    def begin_transaction(self, **kwargs) -> dict:
        """Mock implementation of begin_transaction.

        Returns:
            dict: The mock response

        Raises:
            ClientError
            Exception
        """
        if self.error == MockException.Client:
            error_response = {
                'Error': {
                    'Code': 'AccessDeniedException',
                    'Message': 'User is not authorized to perform rds-data:begin_transaction',
                }
            }
            raise ClientError(error_response, operation_name='begin_transaction')

        if self.error == MockException.Unexpected:
            error_response = {
                'Error': {
                    'Code': 'UnexpectedException',
                    'Message': 'UnexpectedException',
                }
            }
            raise Exception(error_response)

        return {'transactionId': 'txt-id-xxxxx'}

    def commit_transaction(self, **kwargs) -> dict:
        """Mock implementation of commit_transaction.

        Returns:
            dict: The mock response

        Raises:
            ClientError
            Exception
        """
        if self.error == MockException.Client:
            error_response = {
                'Error': {
                    'Code': 'AccessDeniedException',
                    'Message': 'User is not authorized to perform rds-data:begin_transaction',
                }
            }
            raise ClientError(error_response, operation_name='commit_transaction')

        if self.error == MockException.Unexpected:
            error_response = {
                'Error': {
                    'Code': 'UnexpectedException',
                    'Message': 'UnexpectedException',
                }
            }
            raise Exception(error_response)

        return {'transactionStatus': 'txt status'}

    def rollback_transaction(self, **kwargs) -> dict:
        """Mock implementation of rollback_transaction.

        Returns:
            dict: The mock response

        Raises:
            ClientError
            Exception
        """
        if self.error == MockException.Client:
            error_response = {
                'Error': {
                    'Code': 'AccessDeniedException',
                    'Message': 'User is not authorized to perform rds-data:begin_transaction',
                }
            }
            raise ClientError(error_response, operation_name='rollback_transaction')

        if self.error == MockException.Unexpected:
            error_response = {
                'Error': {
                    'Code': 'UnexpectedException',
                    'Message': 'UnexpectedException',
                }
            }
            raise Exception(error_response)

        return {'transactionStatus': 'txt status'}

    def execute_statement(self, **kwargs) -> dict:
        """Mock implementation of execute_statement.

        Returns:
            dict: The mock response

        Raises:
            ClientError
            Exception
        """
        if self.error == MockException.Client:
            error_response = {
                'Error': {
                    'Code': 'AccessDeniedException',
                    'Message': 'User is not authorized to perform rds-data:begin_transaction',
                }
            }
            raise ClientError(error_response, operation_name='execute_statement')

        if self.error == MockException.Unexpected:
            error_response = {
                'Error': {
                    'Code': 'UnexpectedException',
                    'Message': 'UnexpectedException',
                }
            }
            raise Exception(error_response)

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

    def __init__(
        self, readonly, auth_mode='secrets-manager', error: MockException = MockException.No
    ):
        """Initialize the mock DB connection.

        Args:
            readonly: Whether the connection should be read-only
            auth_mode: Authentication mode ('secrets-manager' or 'iam-db-auth')
            error: Mock exception if any
        """
        self.auth_mode = auth_mode
        self.cluster_arn = 'dummy_cluster_arn'
        self.secret_arn = 'dummy_secret_arn'  # pragma: allowlist secret
        self.db_user = 'dummy_user'
        self.db_host = 'dummy-host.cluster-xxx.us-east-1.rds.amazonaws.com'
        self.db_port = 5432
        self.database = 'dummy_database'
        self.region = 'us-east-1'
        self.readonly = readonly
        self.error = error

        if auth_mode == 'secrets-manager':
            self._data_client = Mock_boto3_client(error)
        else:  # iam-db-auth
            self._rds_client = Mock_rds_client(error)

    @property
    def data_client(self):
        """Get the mock data client.

        Returns:
            Mock_boto3_client: The mock boto3 client
        """
        return self._data_client

    @property
    def rds_client(self):
        """Get the mock RDS client.

        Returns:
            Mock_rds_client: The mock RDS client
        """
        return self._rds_client

    @property
    def readonly_query(self):
        """Get whether this connection is read-only.

        Returns:
            bool: True if the connection is read-only, False otherwise
        """
        return self.readonly

    async def generate_auth_token(self):
        """Mock IAM auth token generation."""
        if self.error == MockException.Client:
            error_response = {
                'Error': {
                    'Code': 'AccessDeniedException',
                    'Message': 'User is not authorized to generate auth token',
                }
            }
            raise ClientError(error_response, operation_name='generate_db_auth_token')

        if self.error == MockException.Unexpected:
            raise Exception('Unexpected error generating auth token')

        return 'mock-iam-auth-token'

    async def get_direct_connection(self):
        """Mock direct PostgreSQL connection."""
        if self.error == MockException.Client:
            raise Exception('Connection failed')
        if self.error == MockException.Unexpected:
            raise Exception('Unexpected connection error')

        return Mock_psycopg2_connection(self.error)


class DummyCtx:
    """Mock implementation of MCP context for testing purposes."""

    async def error(self, message):
        """Mock MCP ctx.error with the given message.

        Args:
            message: The error message
        """
        # Do nothing because MCP ctx.error doesn't throw exception
        pass


@pytest.fixture
def mock_DBConnection():
    """Fixture that provides a mock DB connection for testing.

    Returns:
        Mock_DBConnection: A mock database connection
    """
    return Mock_DBConnection(readonly=True)
