# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Connection management tools for DocumentDB MCP Server."""

import uuid
from datetime import datetime, timedelta
from loguru import logger
from pydantic import Field
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from typing import Annotated, Any, Dict
from urllib.parse import parse_qs, urlparse


class ConnectionInfo:
    """Stores information about a DocumentDB connection."""

    def __init__(self, connection_string: str, client: MongoClient):
        """Initialize a ConnectionInfo object.

        Args:
            connection_string: The connection string used to connect to DocumentDB
            client: The MongoDB client instance connected to DocumentDB
        """
        self.connection_string = connection_string
        self.client = client
        self.connection_id = str(uuid.uuid4())
        self.last_used = datetime.now()


class DocumentDBConnection:
    """Manages connections to DocumentDB."""

    # Connection pool mapped by connection_id
    _connections = {}

    # Idle timeout in minutes (connections unused for this long will be closed)
    _idle_timeout = 30

    @classmethod
    def create_connection(cls, connection_string: str) -> ConnectionInfo:
        """Create a new connection to DocumentDB.

        Args:
            connection_string: DocumentDB connection string
                Example: "mongodb://username:password@docdb-cluster.cluster-xyz.us-west-2.docdb.amazonaws.com:27017/?tls=true&tlsCAFile=global-bundle.pem&retryWrites=false"  # pragma: allowlist secret

        Returns:
            ConnectionInfo containing the connection ID and client
        """
        logger.info('Creating new DocumentDB connection')
        DocumentDBConnection.validate_retry_writes_false(connection_string)
        client = MongoClient(connection_string)

        # Test connection
        try:
            client.admin.command('ping')
            logger.info('Connected successfully to DocumentDB')
        except (ConnectionFailure, OperationFailure) as e:
            logger.error(f'Failed to connect to DocumentDB: {str(e)}')
            raise

        # Store connection info
        connection_info = ConnectionInfo(connection_string, client)
        cls._connections[connection_info.connection_id] = connection_info

        return connection_info

    @classmethod
    def get_connection(cls, connection_id: str) -> MongoClient:
        """Get an existing connection by ID.

        Args:
            connection_id: The connection ID returned by create_connection

        Returns:
            An active pymongo client connected to DocumentDB

        Raises:
            ValueError: If the connection ID is not found
        """
        if connection_id not in cls._connections:
            raise ValueError(f'Connection ID {connection_id} not found. You must connect first.')

        # Update last used timestamp
        connection_info = cls._connections[connection_id]
        connection_info.last_used = datetime.now()

        return connection_info.client

    @classmethod
    def close_connection(cls, connection_id: str) -> None:
        """Close a specific connection by ID.

        Args:
            connection_id: The connection ID to close

        Raises:
            ValueError: If the connection ID is not found
        """
        if connection_id not in cls._connections:
            raise ValueError(f'Connection ID {connection_id} not found')

        logger.info(f'Closing DocumentDB connection {connection_id}')
        connection_info = cls._connections[connection_id]
        connection_info.client.close()
        del cls._connections[connection_id]

    @classmethod
    def close_idle_connections(cls) -> None:
        """Close connections that have been idle for longer than the timeout."""
        now = datetime.now()
        idle_threshold = now - timedelta(minutes=cls._idle_timeout)

        idle_connections = [
            conn_id
            for conn_id, info in cls._connections.items()
            if info.last_used < idle_threshold
        ]

        for conn_id in idle_connections:
            logger.info(f'Closing idle DocumentDB connection {conn_id}')
            cls._connections[conn_id].client.close()
            del cls._connections[conn_id]

    @classmethod
    def close_all_connections(cls) -> None:
        """Close all open connections."""
        for conn_id, conn_info in list(cls._connections.items()):
            logger.info(f'Closing DocumentDB connection {conn_id}')
            conn_info.client.close()
        cls._connections.clear()

    @staticmethod
    def validate_retry_writes_false(conn_str: str) -> None:
        """Validate that retryWrites=false is specified in the connection string.

        DocumentDB requires retryWrites=false to be set in the connection string.
        This method ensures this setting is present to avoid potential data consistency issues.

        Args:
            conn_str: The connection string to validate

        Raises:
            ValueError: If retryWrites is missing or set to a value other than 'false'
        """
        parsed = urlparse(conn_str)
        query_params = parse_qs(parsed.query)

        retry_value = query_params.get('retryWrites', [None])[0]

        if retry_value is None:
            raise ValueError("Connection string is missing 'retryWrites=false'.")

        if retry_value.lower() != 'false':
            raise ValueError(f"Invalid retryWrites value: '{retry_value}'. Expected 'false'.")


async def connect(
    connection_string: Annotated[
        str,
        Field(
            description='DocumentDB connection string. Example: "mongodb://user:pass@docdb-cluster.cluster-xyz.us-west-2.docdb.amazonaws.com:27017/?tls=true&tlsCAFile=global-bundle.pem"'  # pragma: allowlist secret
        ),
    ],
) -> Dict[str, Any]:
    """Connect to an AWS DocumentDB cluster.

    This tool establishes and validates a connection to DocumentDB.
    The returned connection_id can be used with other tools instead of providing
    the full connection string each time.

    Returns:
        Dict[str, Any]: Connection details including connection_id and available databases
    """
    try:
        # Create connection and get connection info
        connection_info = DocumentDBConnection.create_connection(connection_string)
        client = connection_info.client

        # List available databases
        databases = client.list_database_names()

        return {
            'connection_id': connection_info.connection_id,
            'message': 'Successfully connected to DocumentDB',
            'databases': databases,
        }
    except Exception as e:
        logger.error(f'Error connecting to DocumentDB: {str(e)}')
        raise ValueError(f'Failed to connect to DocumentDB: {str(e)}')


async def disconnect(
    connection_id: Annotated[
        str, Field(description='The connection ID returned by the connect tool')
    ],
) -> Dict[str, Any]:
    """Close a connection to DocumentDB.

    This tool closes a previously established connection to DocumentDB.

    Returns:
        Dict[str, Any]: Confirmation of successful disconnection
    """
    try:
        DocumentDBConnection.close_connection(connection_id)
        return {'success': True, 'message': f'Successfully closed connection {connection_id}'}
    except ValueError as e:
        logger.error(f'Error disconnecting from DocumentDB: {str(e)}')
        raise ValueError(str(e))
    except Exception as e:
        logger.error(f'Error disconnecting from DocumentDB: {str(e)}')
        raise ValueError(f'Failed to disconnect from DocumentDB: {str(e)}')
