import pytest
from botocore.exceptions import ClientError
from enum import Enum
from typing import Any, Dict, List, Optional


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

    async def execute_query(
        self, sql: str, parameters: Optional[List[Dict[str, Any]]] = None
    ) -> dict:
        """Execute a SQL query.

        Args:
            sql: The SQL query to execute
            parameters: Optional parameters for the query

        Returns:
            dict: Query results with column metadata and records
        """
        if self.error == MockException.Client:
            error_response = {
                'Error': {
                    'Code': 'AccessDeniedException',
                    'Message': 'User is not authorized to perform rds-data:execute_statement',
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

        # Use the data_client to execute the statement
        if self.readonly:
            # Begin read-only transaction
            tx_id = self.data_client.begin_transaction()['transactionId']

            # Set transaction to read-only
            self.data_client.execute_statement(
                sql='SET TRANSACTION READ ONLY', transactionId=tx_id
            )

            # Execute the query
            result = self.data_client.execute_statement(
                sql=sql, parameters=parameters, transactionId=tx_id
            )

            # Commit the transaction
            self.data_client.commit_transaction(transactionId=tx_id)
            return result
        else:
            # Execute the query directly
            return self.data_client.execute_statement(sql=sql, parameters=parameters)


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


# Mock classes for psycopg testing


class MockConnectionPool:
    """Mock implementation of psycopg_pool.AsyncConnectionPool for testing purposes."""

    def __init__(
        self,
        conninfo=None,
        min_size=1,
        max_size=10,
        timeout=15.0,
        max_idle=60.0,
        reconnect_timeout=5.0,
    ):
        """Initialize the mock connection pool.

        Args:
            conninfo: Connection info string
            min_size: Minimum pool size
            max_size: Maximum pool size
            timeout: Connection timeout in seconds
            max_idle: Maximum idle time in seconds
            reconnect_timeout: Reconnection timeout in seconds
        """
        self.conninfo = conninfo
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout
        self.max_idle = max_idle
        self.reconnect_timeout = reconnect_timeout
        self.size = 0
        self.idle = 0
        self._open = False
        self._connections = []

    async def open(self, wait=True, timeout=15.0):
        """Open the connection pool asynchronously.

        Args:
            wait: Whether to wait for connections to be established
            timeout: Timeout in seconds

        Returns:
            None
        """
        self._open = True
        self.size = self.min_size
        self.idle = self.min_size
        return None

    async def close(self):
        """Close the connection pool asynchronously.

        Returns:
            None
        """
        self._open = False
        self.size = 0
        self.idle = 0
        return None

    async def connection(self, timeout=15.0):
        """Get a connection from the pool asynchronously.

        Args:
            timeout: Timeout in seconds

        Returns:
            ConnectionContext: A context manager for a connection
        """

        # Mock async context manager for connection
        class ConnectionContext:
            def __init__(self, pool):
                self.pool = pool
                self.pool.idle -= 1

            async def __aenter__(self):
                return MockAsyncConnection()

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                self.pool.idle += 1
                return False

        return ConnectionContext(self)


class MockConnection:
    """Mock implementation of psycopg.Connection for testing purposes."""

    def __init__(self):
        """Initialize the mock connection."""
        pass

    def transaction(self):
        """Start a transaction.

        Returns:
            TransactionContext: A context manager for a transaction
        """

        # Mock context manager for transaction
        class TransactionContext:
            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

        return TransactionContext()

    def cursor(self):
        """Get a cursor.

        Returns:
            CursorContext: A context manager for a cursor
        """

        # Mock context manager for cursor
        class CursorContext:
            def __init__(self):
                self.description = [('column1',), ('column2',)]
                self.rowcount = 0

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

            def execute(self, query, params=None):
                """Execute a query.

                Args:
                    query: The SQL query to execute
                    params: Query parameters

                Returns:
                    None
                """
                self.rowcount = 1
                return None

            def fetchall(self):
                """Fetch all rows.

                Returns:
                    list: List of rows
                """
                return [('value1', 'value2')]

        return CursorContext()


class MockAsyncConnection:
    """Mock implementation of psycopg.AsyncConnection for testing purposes."""

    def __init__(self):
        """Initialize the mock async connection."""
        pass

    async def transaction(self):
        """Start a transaction asynchronously.

        Returns:
            AsyncTransactionContext: An async context manager for a transaction
        """

        # Mock async context manager for transaction
        class AsyncTransactionContext:
            async def __aenter__(self):
                return None

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        return AsyncTransactionContext()

    async def execute(self, query, params=None):
        """Execute a query asynchronously.

        Args:
            query: The SQL query to execute
            params: Query parameters

        Returns:
            AsyncCursorResult: A mock cursor result
        """

        class AsyncCursorResult:
            def __init__(self):
                self.description = [('column1',), ('column2',)]
                self.rowcount = 1

            async def fetchall(self):
                """Fetch all rows asynchronously.

                Returns:
                    list: List of rows
                """
                return [('value1', 'value2')]

        return AsyncCursorResult()


class Mock_PsycopgPoolConnection:
    """Mock implementation of PsycopgPoolConnection for testing purposes."""

    def __init__(
        self,
        host,
        port,
        database,
        readonly,
        secret_arn,
        region,
        min_size=1,
        max_size=10,
        is_test=False,
    ):
        """Initialize the mock PsycopgPoolConnection.

        Args:
            host: Database host
            port: Database port
            database: Database name
            readonly: Whether the connection is read-only
            secret_arn: Secret ARN
            region: AWS region
            min_size: Minimum pool size
            max_size: Maximum pool size
            is_test: Whether this is a test connection
        """
        self.host = host
        self.port = port
        self.database = database
        self.readonly = readonly
        self.secret_arn = secret_arn  # pragma: allowlist secret
        self.region = region
        self.min_size = min_size
        self.max_size = max_size
        self.is_test = is_test
        self.pool = MockConnectionPool(
            conninfo=f'host={host} port={port} dbname={database} user=test_user password=test_password',
            min_size=min_size,
            max_size=max_size,
            timeout=15.0,
            max_idle=60.0,
            reconnect_timeout=5.0,
        )

    @property
    def readonly_query(self):
        """Get whether this connection is read-only.

        Returns:
            bool: True if the connection is read-only, False otherwise
        """
        return self.readonly

    async def execute_query(
        self, sql: str, parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute a SQL query.

        Args:
            sql: The SQL query to execute
            parameters: Query parameters

        Returns:
            dict: Query results
        """
        # Mock response similar to RDS Data API format
        return {
            'columnMetadata': [{'name': 'column1'}, {'name': 'column2'}],
            'records': [[{'stringValue': 'value1'}, {'stringValue': 'value2'}]],
        }

    async def close(self):
        """Close the connection.

        Returns:
            None
        """
        if hasattr(self, 'pool'):
            await self.pool.close()

    async def check_connection_health(self):
        """Check the connection health.

        Returns:
            bool: True if the connection is healthy, False otherwise
        """
        return True

    def get_pool_stats(self):
        """Get pool statistics.

        Returns:
            dict: Pool statistics
        """
        return {
            'size': self.pool.size,
            'min_size': self.pool.min_size,
            'max_size': self.pool.max_size,
            'idle': self.pool.idle,
        }


@pytest.fixture
def mock_PsycopgPoolConnection():
    """Fixture that provides a mock PsycopgPoolConnection for testing.

    Returns:
        Mock_PsycopgPoolConnection: A mock PsycopgPoolConnection
    """
    return Mock_PsycopgPoolConnection(
        host='localhost',
        port=5432,
        database='test_db',
        readonly=True,
        secret_arn='test_secret_arn',  # pragma: allowlist secret
        region='us-east-1',
        is_test=True,
    )
