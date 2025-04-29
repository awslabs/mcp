import pytest
<<<<<<< HEAD
from botocore.exceptions import ClientError
from enum import Enum
from typing import List


class MockException(Enum):
    """Mock exception type."""

    No = 'none'
    Client = 'client'
    Unexpected = 'unexpected'


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
=======
from typing import List, Dict, Any
from botocore.exceptions import ClientError

class Mock_boto3_client:
    def __init__(self, throw_client_error = False):
        self._responses: List[dict] = []
        self.throw_client_error = throw_client_error
        self._current_response_index = 0

    def execute_statement(self, **kwargs) -> dict:
        if self.throw_client_error:
            error_response = {
                "Error": {
                    "Code": "AccessDeniedException",
                    "Message": "User is not authorized to perform rds-data:ExecuteStatement"
                }
            }
            raise ClientError(error_response, operation_name="ExecuteStatement")
>>>>>>> 725dba2 (create the v1 of postgres-mcp-server which supports NL2SQL)

        if self._current_response_index < len(self._responses):
            response = self._responses[self._current_response_index]
            self._current_response_index += 1
            return response
<<<<<<< HEAD
        raise Exception('Mock_boto3_client.execute_statement mock response out of bound')

    def add_mock_response(self, response):
        """Add a mock response to be returned by execute_statement.

        Args:
            response: The mock response to add
        """
        self._responses.append(response)


class Mock_DBConnection:
    """Mock implementation of DBConnection for testing purposes."""

    def __init__(self, readonly, error: MockException = MockException.No):
        """Initialize the mock DB connection.

        Args:
            readonly: Whether the connection should be read-only
            error: Mock exception if any
        """
        self.cluster_arn = 'dummy_cluster_arn'
        self.secret_arn = 'dummy_secret_arn'  # pragma: allowlist secret
        self.database = 'dummy_database'
        self.readonly = readonly
        self.error = error
        self._data_client = Mock_boto3_client(error)

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
=======
        raise Exception("Mock_boto3_client.execute_statement mock response out of bound")

    def add_mock_response(self, response):
        self._responses.append(response)

class Mock_DBConnection:
    def __init__(self, reaodnly, throw_client_error = False):
        self.cluster_arn = 'dummy_cluster_arn'
        self.secret_arn = 'dummy_secret_arn'
        self.database = 'dummy_database'
        self.reaodnly = reaodnly
        self.throw_client_error = throw_client_error
        self._data_client = Mock_boto3_client(throw_client_error)

    @property
    def data_client(self):
        return self._data_client
    
    @property
    def readonly_query(self):
        return self.reaodnly
    
class DummyCtx:
    def error(self, message):
        raise RuntimeError(f"MCP Tool Error: {message}")

@pytest.fixture
def mock_DBConnection():
    return Mock_DBConnection()
>>>>>>> 725dba2 (create the v1 of postgres-mcp-server which supports NL2SQL)
