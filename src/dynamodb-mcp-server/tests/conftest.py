import pytest


@pytest.fixture
def mysql_env_setup(monkeypatch):
    """Set up MySQL environment variables for testing."""
    monkeypatch.setenv(
        'MYSQL_CLUSTER_ARN', 'arn:aws:rds:us-west-2:123456789012:cluster:test-cluster'
    )
    monkeypatch.setenv(
        'MYSQL_SECRET_ARN', 'arn:aws:secretsmanager:us-west-2:123456789012:secret:test-secret'
    )
    monkeypatch.setenv('MYSQL_DATABASE', 'employees')
    monkeypatch.setenv('AWS_REGION', 'us-west-2')


@pytest.fixture
def mock_mysql_functions(monkeypatch):
    """Mock MySQL connection and query functions."""

    def mock_initialize(*args, **kwargs):
        return True

    async def mock_query(*args, **kwargs):
        return [{'id': 1, 'name': 'test'}]

    monkeypatch.setattr(
        'awslabs.dynamodb_mcp_server.server.DBConnectionSingleton.initialize', mock_initialize
    )
    monkeypatch.setattr('awslabs.dynamodb_mcp_server.server.mysql_query', mock_query)
