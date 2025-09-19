import pytest
from awslabs.dynamodb_mcp_server.server import mysql_run_query


class TestMySQLIntegration:
    """Test MySQL integration functionality."""

    @pytest.mark.asyncio
    async def test_mysql_connection_and_query(self, monkeypatch):
        """Test MySQL connection initialization and query execution."""
        # Set environment variables using monkeypatch
        monkeypatch.setenv(
            'MYSQL_CLUSTER_ARN', 'arn:aws:rds:us-west-2:123456789012:cluster:test-cluster'
        )
        monkeypatch.setenv(
            'MYSQL_SECRET_ARN', 'arn:aws:secretsmanager:us-west-2:123456789012:secret:test-secret'
        )
        monkeypatch.setenv('MYSQL_DATABASE', 'test_database')
        monkeypatch.setenv('MYSQL_AWS_REGION', 'us-west-2')
        monkeypatch.setenv('MYSQL_READONLY', 'true')

        # Mock the MySQL functions using monkeypatch
        def mock_initialize(*args, **kwargs):
            return True

        async def mock_query(*args, **kwargs):
            return [{'id': 1, 'name': 'test'}]

        monkeypatch.setattr(
            'awslabs.dynamodb_mcp_server.server.DBConnectionSingleton.initialize', mock_initialize
        )
        monkeypatch.setattr('awslabs.dynamodb_mcp_server.server.mysql_query', mock_query)

        result = await mysql_run_query('SELECT * FROM users')

        assert result == [{'id': 1, 'name': 'test'}]

    @pytest.mark.asyncio
    async def test_mysql_missing_config(self, monkeypatch):
        """Test MySQL query when configuration is missing."""
        # Clear MySQL env vars using monkeypatch
        monkeypatch.delenv('MYSQL_CLUSTER_ARN', raising=False)
        monkeypatch.delenv('MYSQL_SECRET_ARN', raising=False)
        monkeypatch.delenv('MYSQL_DATABASE', raising=False)

        result = await mysql_run_query('SELECT * FROM users')
        assert 'error' in result[0]
        assert 'MySQL integration requires these environment variables' in result[0]['error']
