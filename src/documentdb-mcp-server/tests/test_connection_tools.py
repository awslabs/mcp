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
"""Tests for DocumentDB MCP Server connection management."""

import pytest
import threading
import time
from awslabs.documentdb_mcp_server.config import serverConfig
from awslabs.documentdb_mcp_server.connection_tools import DocumentDBConnection
from pymongo.errors import ConnectionFailure


class TestGetClient:
    """Tests for the operator-configured DocumentDBConnection.get_client()."""

    def test_get_client_creates_and_caches(self, patch_client):
        """Test that get_client creates a client and caches it for reuse."""
        # Arrange
        mock_client = patch_client()

        # Act
        client1 = DocumentDBConnection.get_client()
        client2 = DocumentDBConnection.get_client()

        # Assert - same cached client is returned, and it is the mock
        assert client1 is mock_client
        assert client2 is mock_client
        assert DocumentDBConnection._client is mock_client

    def test_get_client_builds_once_and_reuses(self, patch_client, monkeypatch):
        """Test the client is built once and reused without re-pinging on each call."""
        # Arrange - count how many times MongoClient is constructed
        mock_client = patch_client()
        calls = {'construct': 0}
        real_ctor = mock_client

        def counting_ctor(*args, **kwargs):
            calls['construct'] += 1
            return real_ctor

        monkeypatch.setattr(
            'awslabs.documentdb_mcp_server.connection_tools.MongoClient', counting_ctor
        )

        # Act - multiple calls
        first = DocumentDBConnection.get_client()
        second = DocumentDBConnection.get_client()
        third = DocumentDBConnection.get_client()

        # Assert - same cached client, built exactly once (no per-call rebuild)
        assert first is mock_client
        assert second is mock_client
        assert third is mock_client
        assert calls['construct'] == 1

    def test_get_client_concurrent_builds_once(self, patch_client, monkeypatch):
        """Test concurrent cold-start callers build at most one client (lock guard).

        Uses a deliberately slow constructor and a barrier so all threads reach
        the check-and-set together; without the lock this would build N clients.
        """
        # Arrange
        mock_client = patch_client()
        DocumentDBConnection._client = None
        calls = {'construct': 0}
        counter_lock = threading.Lock()

        def slow_ctor(*args, **kwargs):
            with counter_lock:
                calls['construct'] += 1
            time.sleep(0.05)  # widen the race window
            return mock_client

        monkeypatch.setattr(
            'awslabs.documentdb_mcp_server.connection_tools.MongoClient', slow_ctor
        )

        n = 8
        barrier = threading.Barrier(n)
        results = []
        results_lock = threading.Lock()

        def worker():
            barrier.wait()  # release all threads simultaneously
            client = DocumentDBConnection.get_client()
            with results_lock:
                results.append(client)

        threads = [threading.Thread(target=worker) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert - exactly one client built, all callers got the same instance
        assert calls['construct'] == 1
        assert len(results) == n
        assert all(c is mock_client for c in results)

    def test_get_client_not_configured(self):
        """Test that get_client fails closed when no connection string is configured."""
        # Arrange - ensure nothing configured
        DocumentDBConnection._client = None
        original = serverConfig.connection_string
        serverConfig.connection_string = None

        try:
            # Act/Assert
            with pytest.raises(ValueError, match='connection is not configured'):
                DocumentDBConnection.get_client()
        finally:
            serverConfig.connection_string = original

    def test_get_client_connection_failure(self, patch_client):
        """Test that a connection (ping) failure is propagated."""
        # Arrange
        patch_client(raise_on_connect=ConnectionFailure('Connection refused'))

        # Act/Assert
        with pytest.raises(ConnectionFailure):
            DocumentDBConnection.get_client()

    def test_close(self, patch_client):
        """Test closing the connection resets the cached client."""
        # Arrange
        mock_client = patch_client()
        DocumentDBConnection.get_client()
        assert DocumentDBConnection._client is mock_client

        # Act
        DocumentDBConnection.close()

        # Assert
        assert DocumentDBConnection._client is None

    def test_close_when_no_client(self):
        """Test that close is a no-op when no client is open."""
        # Arrange
        DocumentDBConnection._client = None

        # Act - should not raise
        DocumentDBConnection.close()

        # Assert
        assert DocumentDBConnection._client is None


class TestValidateRetryWritesFalse:
    """Tests for the retryWrites=false validation."""

    def test_valid(self):
        """Test a connection string with retryWrites=false passes."""
        # Act/Assert - should not raise
        DocumentDBConnection.validate_retry_writes_false(
            'mongodb://example.com:27017/?retryWrites=false'
        )

    def test_missing_retry_writes(self):
        """Test a connection string missing retryWrites is rejected."""
        with pytest.raises(ValueError, match="missing 'retryWrites=false'"):
            DocumentDBConnection.validate_retry_writes_false('mongodb://example.com:27017/')

    def test_invalid_retry_writes(self):
        """Test a connection string with retryWrites=true is rejected."""
        with pytest.raises(ValueError, match='Invalid retryWrites value'):
            DocumentDBConnection.validate_retry_writes_false(
                'mongodb://example.com:27017/?retryWrites=true'
            )
