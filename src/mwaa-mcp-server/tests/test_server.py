"""Tests for MWAA MCP Server."""

import pytest
from unittest.mock import Mock, patch

from awslabs.mwaa_mcp_server.tools import MWAATools


@pytest.fixture
def mock_boto_client():
    """Mock boto3 MWAA client."""
    with patch("awslabs.mwaa_mcp_server.tools.boto3") as mock_boto:
        mock_client = Mock()
        mock_boto.client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mwaa_tools(mock_boto_client):
    """Create MWAATools instance with mocked client."""
    with patch.dict("os.environ", {"MWAA_MCP_READONLY": "false"}):
        tools = MWAATools()
        tools.mwaa_client = mock_boto_client
        return tools


@pytest.fixture
def readonly_tools(mock_boto_client):
    """Create MWAATools instance in read-only mode."""
    with patch.dict("os.environ", {"MWAA_MCP_READONLY": "true"}):
        tools = MWAATools()
        tools.mwaa_client = mock_boto_client
        return tools


class TestListEnvironments:
    """Test listing MWAA environments."""

    @pytest.mark.asyncio
    async def test_list_environments(self, mwaa_tools, mock_boto_client):
        mock_boto_client.list_environments.return_value = {
            "Environments": ["test-env-1", "test-env-2"]
        }
        mock_boto_client.get_environment.return_value = {
            "Environment": {
                "Name": "test-env-1",
                "Status": "AVAILABLE",
                "Arn": "arn:aws:airflow:us-east-1:123456789012:environment/test-env-1",
                "CreatedAt": "2024-01-01T00:00:00Z",
            }
        }

        result = await mwaa_tools.list_environments()

        assert "Environments" in result
        assert len(result["Environments"]) == 2
        mock_boto_client.list_environments.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_environments_with_max_results(self, mwaa_tools, mock_boto_client):
        mock_boto_client.list_environments.return_value = {"Environments": ["test-env-1"]}
        mock_boto_client.get_environment.return_value = {
            "Environment": {
                "Name": "test-env-1",
                "Status": "AVAILABLE",
                "Arn": "arn:aws:airflow:us-east-1:123456789012:environment/test-env-1",
                "CreatedAt": "2024-01-01T00:00:00Z",
            }
        }

        result = await mwaa_tools.list_environments(max_results=1)

        assert "Environments" in result
        mock_boto_client.list_environments.assert_called_once_with(MaxResults=1)

    @pytest.mark.asyncio
    async def test_list_environments_caps_max_results_at_25(self, mwaa_tools, mock_boto_client):
        mock_boto_client.list_environments.return_value = {"Environments": []}

        await mwaa_tools.list_environments(max_results=100)

        mock_boto_client.list_environments.assert_called_once_with(MaxResults=25)


class TestGetEnvironment:
    """Test getting environment details."""

    @pytest.mark.asyncio
    async def test_get_environment(self, mwaa_tools, mock_boto_client):
        mock_env = {
            "Name": "test-env",
            "Status": "AVAILABLE",
            "Arn": "arn:aws:airflow:us-east-1:123456789012:environment/test-env",
            "WebserverUrl": "https://test.airflow.region.amazonaws.com",
            "ExecutionRoleArn": "arn:aws:iam::123456789012:role/airflow-execution-role",
            "NetworkConfiguration": {
                "SubnetIds": ["subnet-123", "subnet-456"],
                "SecurityGroupIds": ["sg-123"],
            },
        }
        mock_boto_client.get_environment.return_value = {"Environment": mock_env}

        result = await mwaa_tools.get_environment("test-env")

        assert "Environment" in result
        assert result["Environment"]["Name"] == "test-env"
        assert result["Environment"]["Status"] == "AVAILABLE"
        mock_boto_client.get_environment.assert_called_once_with(Name="test-env")

    @pytest.mark.asyncio
    async def test_get_environment_not_found(self, mwaa_tools, mock_boto_client):
        from botocore.exceptions import ClientError

        mock_boto_client.get_environment.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Environment not found"}},
            "GetEnvironment",
        )

        result = await mwaa_tools.get_environment("non-existent")

        assert "error" in result
        assert "ResourceNotFoundException" in result["error"]


class TestReadonlyMode:
    """Test read-only mode restrictions."""

    @pytest.mark.asyncio
    async def test_create_environment_blocked(self, readonly_tools):
        with pytest.raises(PermissionError, match="not allowed in read-only mode"):
            await readonly_tools.create_environment(
                name="test",
                dag_s3_path="s3://bucket/dags",
                execution_role_arn="arn:aws:iam::123456789012:role/test",
                network_configuration={},
                source_bucket_arn="arn:aws:s3:::bucket",
            )

    @pytest.mark.asyncio
    async def test_update_environment_blocked(self, readonly_tools):
        with pytest.raises(PermissionError, match="not allowed in read-only mode"):
            await readonly_tools.update_environment(name="test")

    @pytest.mark.asyncio
    async def test_delete_environment_blocked(self, readonly_tools):
        with pytest.raises(PermissionError, match="not allowed in read-only mode"):
            await readonly_tools.delete_environment("test")

    @pytest.mark.asyncio
    async def test_trigger_dag_run_blocked(self, readonly_tools):
        with pytest.raises(PermissionError, match="not allowed in read-only mode"):
            await readonly_tools.trigger_dag_run("env", "dag_id")


class TestTokenCreation:
    """Test CLI and web login token creation."""

    @pytest.mark.asyncio
    async def test_create_cli_token(self, mwaa_tools, mock_boto_client):
        mock_boto_client.create_cli_token.return_value = {
            "CliToken": "test-token-123",
            "WebServerHostname": "test.airflow.region.amazonaws.com",
        }

        result = await mwaa_tools.create_cli_token("test-env")

        assert result["CliToken"] == "test-token-123"
        assert "WebServerHostname" in result
        mock_boto_client.create_cli_token.assert_called_once_with(Name="test-env")

    @pytest.mark.asyncio
    async def test_create_web_login_token(self, mwaa_tools, mock_boto_client):
        mock_boto_client.create_web_login_token.return_value = {
            "WebToken": "web-token-123",
            "WebServerHostname": "test.airflow.region.amazonaws.com",
            "IamIdentity": "arn:aws:iam::123456789012:user/test",
        }

        result = await mwaa_tools.create_web_login_token("test-env")

        assert result["WebToken"] == "web-token-123"
        assert "WebServerHostname" in result
        assert "IamIdentity" in result


class TestAirflowApiTools:
    """Test Airflow REST API tool wrappers."""

    @pytest.mark.asyncio
    async def test_list_dags(self, mwaa_tools, mock_boto_client):
        mock_boto_client.invoke_rest_api.return_value = {
            "RestApiResponse": {"dags": [], "total_entries": 0},
            "RestApiStatusCode": 200,
        }

        result = await mwaa_tools.list_dags("test-env")

        mock_boto_client.invoke_rest_api.assert_called_once()
        call_args = mock_boto_client.invoke_rest_api.call_args
        assert call_args.kwargs["Name"] == "test-env"
        assert call_args.kwargs["Method"] == "GET"

    @pytest.mark.asyncio
    async def test_get_dag(self, mwaa_tools, mock_boto_client):
        mock_boto_client.invoke_rest_api.return_value = {
            "RestApiResponse": {"dag_id": "test_dag"},
            "RestApiStatusCode": 200,
        }

        result = await mwaa_tools.get_dag("test-env", "test_dag")

        call_args = mock_boto_client.invoke_rest_api.call_args
        assert "/dags/test_dag" in call_args.kwargs["Path"]

    @pytest.mark.asyncio
    async def test_trigger_dag_run(self, mwaa_tools, mock_boto_client):
        mock_boto_client.invoke_rest_api.return_value = {
            "RestApiResponse": {"dag_run_id": "manual__test"},
            "RestApiStatusCode": 200,
        }

        result = await mwaa_tools.trigger_dag_run("test-env", "test_dag", dag_run_id="manual__test")

        call_args = mock_boto_client.invoke_rest_api.call_args
        assert call_args.kwargs["Method"] == "POST"
        assert "/dags/test_dag/dagRuns" in call_args.kwargs["Path"]

    @pytest.mark.asyncio
    async def test_get_task_logs(self, mwaa_tools, mock_boto_client):
        mock_boto_client.invoke_rest_api.return_value = {
            "RestApiResponse": {"content": "log output"},
            "RestApiStatusCode": 200,
        }

        result = await mwaa_tools.get_task_logs("test-env", "dag1", "run1", "task1", 2)

        call_args = mock_boto_client.invoke_rest_api.call_args
        assert "/logs/2" in call_args.kwargs["Path"]

    @pytest.mark.asyncio
    async def test_get_task_logs_defaults_to_try_1(self, mwaa_tools, mock_boto_client):
        mock_boto_client.invoke_rest_api.return_value = {
            "RestApiResponse": {"content": "log output"},
            "RestApiStatusCode": 200,
        }

        result = await mwaa_tools.get_task_logs("test-env", "dag1", "run1", "task1")

        call_args = mock_boto_client.invoke_rest_api.call_args
        assert "/logs/1" in call_args.kwargs["Path"]

    @pytest.mark.asyncio
    async def test_list_connections(self, mwaa_tools, mock_boto_client):
        mock_boto_client.invoke_rest_api.return_value = {
            "RestApiResponse": {"connections": []},
            "RestApiStatusCode": 200,
        }

        result = await mwaa_tools.list_connections("test-env")

        call_args = mock_boto_client.invoke_rest_api.call_args
        assert "/connections" in call_args.kwargs["Path"]

    @pytest.mark.asyncio
    async def test_list_variables(self, mwaa_tools, mock_boto_client):
        mock_boto_client.invoke_rest_api.return_value = {
            "RestApiResponse": {"variables": []},
            "RestApiStatusCode": 200,
        }

        result = await mwaa_tools.list_variables("test-env")

        call_args = mock_boto_client.invoke_rest_api.call_args
        assert "/variables" in call_args.kwargs["Path"]

    @pytest.mark.asyncio
    async def test_get_import_errors(self, mwaa_tools, mock_boto_client):
        mock_boto_client.invoke_rest_api.return_value = {
            "RestApiResponse": {"import_errors": []},
            "RestApiStatusCode": 200,
        }

        result = await mwaa_tools.get_import_errors("test-env")

        call_args = mock_boto_client.invoke_rest_api.call_args
        assert "/dags/importErrors" in call_args.kwargs["Path"]
