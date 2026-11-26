# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Connection management tools for DocumentDB MCP Server."""

import threading
from awslabs.documentdb_mcp_server.config import serverConfig
from awslabs.documentdb_mcp_server.errors import (
    CONNECTION_ERROR_MESSAGE,
    SafeToolError,
    redact,
)
from loguru import logger
from pymongo import MongoClient
from pymongo.errors import ConfigurationError
from pymongo.uri_parser import parse_uri
from urllib.parse import parse_qs, urlparse


class DocumentDBConnection:
    """Manages the single operator-configured connection to DocumentDB."""

    # The single pymongo client, created lazily from the operator-configured
    # connection string.
    _client = None

    _lock = threading.Lock()

    @classmethod
    def _connect(cls) -> MongoClient:
        """Build and verify a new client from the operator-configured connection string.

        Returns:
            A new, verified pymongo client.

        Raises:
            SafeToolError: If the connection string is invalid or the initial
                connection fails. The message never includes the cluster endpoint
                or driver diagnostics; those are logged server-side.
        """
        logger.info('Creating DocumentDB connection from operator configuration')
        # get_client() only calls this once a connection string is configured.
        conn_str = serverConfig.connection_string or ''
        # Validate here as well as in main(), so a path that sets the connection
        # string without going through main() is still checked.
        cls.validate_retry_writes_false(conn_str)

        try:
            client = MongoClient(conn_str)
        except Exception as e:
            # pymongo raises InvalidURI/ConfigurationError/ValueError from the
            # constructor; keep the detail out of the client-facing message.
            logger.error(
                f'Failed to create DocumentDB client: {type(e).__name__}: {redact(str(e))}'
            )
            raise SafeToolError(CONNECTION_ERROR_MESSAGE) from None

        try:
            client.admin.command('ping')
            logger.info('Connected successfully to DocumentDB')
        except Exception as e:
            logger.error(f'Failed to connect to DocumentDB: {type(e).__name__}: {redact(str(e))}')
            client.close()
            raise SafeToolError(CONNECTION_ERROR_MESSAGE) from None
        return client

    @classmethod
    def get_client(cls) -> MongoClient:
        """Return the operator-configured DocumentDB client, creating it if needed.

        Returns:
            A pymongo client connected to the configured DocumentDB.

        Raises:
            SafeToolError: If no connection string has been configured (fail closed),
                or the connection cannot be established.
        """
        if not serverConfig.connection_string:
            raise SafeToolError(
                'DocumentDB connection is not configured. Start the server with '
                '--connection-string (or set DOCUMENTDB_CONNECTION_STRING) to the '
                'cluster endpoint this server should connect to.'
            )

        if cls._client is None:
            with cls._lock:
                # Double-checked: another thread may have built it while we waited.
                if cls._client is None:
                    cls._client = cls._connect()

        return cls._client

    @classmethod
    def close(cls) -> None:
        """Close the DocumentDB connection if one is open."""
        with cls._lock:
            if cls._client is not None:
                logger.info('Closing DocumentDB connection')
                cls._client.close()
                cls._client = None

    @staticmethod
    def validate_retry_writes_false(conn_str: str) -> None:
        """Validate that retryWrites=false is specified in the connection string.

        DocumentDB requires retryWrites=false to be set in the connection string.
        This method ensures this setting is present to avoid potential data consistency issues.

        Args:
            conn_str: The connection string to validate

        Raises:
            SafeToolError: If retryWrites is missing or set to a value other than 'false'
        """
        parsed = urlparse(conn_str)
        query_params = parse_qs(parsed.query)

        retry_value = query_params.get('retryWrites', [None])[0]

        if retry_value is None:
            raise SafeToolError("Connection string is missing 'retryWrites=false'.")

        if retry_value.lower() != 'false':
            raise SafeToolError(f"Invalid retryWrites value: '{retry_value}'. Expected 'false'.")

    @classmethod
    def validate_connection_string(cls, conn_str: str) -> None:
        """Validate the operator's connection string at startup.

        Parses the URI with pymongo's own parser, then checks retryWrites=false.
        No network connection is made. mongodb+srv:// URIs are not parsed here,
        because parsing them requires a DNS lookup; they are validated on first
        connection instead.

        Args:
            conn_str: The connection string to validate

        Raises:
            SafeToolError: If the URI cannot be parsed or retryWrites is not 'false'.
                The message never includes the URI or its credentials.
        """
        if not conn_str.lower().startswith('mongodb+srv://'):
            try:
                parse_uri(conn_str)
            except (ConfigurationError, ValueError) as e:
                raise SafeToolError(
                    f'Connection string could not be parsed: {redact(str(e))}'
                ) from None
        cls.validate_retry_writes_false(conn_str)
