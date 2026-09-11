"""
Unit tests for ALLOW_SENSITIVE_DATA enforcement in ecs_resource_management.

Validates that DescribeTaskDefinition and DescribeTasks responses are sanitized
when ALLOW_SENSITIVE_DATA is not enabled.
"""

from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.api.resource_management import (
    SENSITIVE_DATA_OPERATIONS,
    _sanitize_sensitive_response,
    ecs_api_operation,
)


class TestSensitiveDataOperations:
    """Tests for SENSITIVE_DATA_OPERATIONS enforcement."""

    def test_sensitive_operations_set_contains_expected(self):
        """Verify the sensitive operations set includes the known sensitive APIs."""
        assert "DescribeTaskDefinition" in SENSITIVE_DATA_OPERATIONS
        assert "DescribeTasks" in SENSITIVE_DATA_OPERATIONS
        assert "DescribeExpressGatewayService" in SENSITIVE_DATA_OPERATIONS

    def test_non_sensitive_operations_not_in_set(self):
        """Verify non-sensitive Describe/List operations are not in the set."""
        assert "DescribeClusters" not in SENSITIVE_DATA_OPERATIONS
        assert "DescribeServices" not in SENSITIVE_DATA_OPERATIONS
        assert "ListClusters" not in SENSITIVE_DATA_OPERATIONS


class TestSanitizeSensitiveResponse:
    """Tests for _sanitize_sensitive_response function."""

    def test_describe_task_definition_redacts_env_values(self):
        """Environment variable values are redacted but names preserved."""
        response = {
            "taskDefinition": {
                "family": "my-app",
                "containerDefinitions": [
                    {
                        "name": "app",
                        "environment": [
                            {"name": "DB_HOST", "value": "prod-db.example.com"},
                            {"name": "API_KEY", "value": "super-secret-key-123"},
                        ],
                    }
                ],
            }
        }

        result = _sanitize_sensitive_response(response, "DescribeTaskDefinition")

        containers = result["taskDefinition"]["containerDefinitions"]
        assert containers[0]["environment"][0]["name"] == "DB_HOST"
        assert containers[0]["environment"][0]["value"] == "[REDACTED]"
        assert containers[0]["environment"][1]["name"] == "API_KEY"
        assert containers[0]["environment"][1]["value"] == "[REDACTED]"

    def test_describe_task_definition_redacts_secrets(self):
        """Secrets valueFrom ARNs are redacted but names preserved."""
        response = {
            "taskDefinition": {
                "family": "my-app",
                "containerDefinitions": [
                    {
                        "name": "app",
                        "environment": [],
                        "secrets": [
                            {
                                "name": "DB_PASSWORD",
                                "valueFrom": (
                                    "arn:aws:secretsmanager:us-east-1:"
                                    "123456789012:secret:prod/db-pass"
                                ),
                            },
                            {
                                "name": "API_TOKEN",
                                "valueFrom": (
                                    "arn:aws:ssm:us-east-1:123456789012:parameter/prod/token"
                                ),
                            },
                        ],
                    }
                ],
            }
        }

        result = _sanitize_sensitive_response(response, "DescribeTaskDefinition")

        secrets = result["taskDefinition"]["containerDefinitions"][0]["secrets"]
        assert secrets[0]["name"] == "DB_PASSWORD"
        assert secrets[0]["valueFrom"] == "[REDACTED]"
        assert secrets[1]["name"] == "API_TOKEN"
        assert secrets[1]["valueFrom"] == "[REDACTED]"

    def test_describe_task_definition_preserves_non_sensitive_fields(self):
        """Non-sensitive fields like family, image, cpu are preserved."""
        response = {
            "taskDefinition": {
                "family": "my-app",
                "revision": 5,
                "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/my-app:5",
                "containerDefinitions": [
                    {
                        "name": "app",
                        "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:latest",
                        "cpu": 256,
                        "memory": 512,
                        "environment": [],
                    }
                ],
            }
        }

        result = _sanitize_sensitive_response(response, "DescribeTaskDefinition")

        task_def = result["taskDefinition"]
        assert task_def["family"] == "my-app"
        assert task_def["revision"] == 5
        container = task_def["containerDefinitions"][0]
        assert container["image"] == "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:latest"
        assert container["cpu"] == 256

    def test_describe_tasks_redacts_container_env(self):
        """DescribeTasks container environment values are redacted."""
        response = {
            "tasks": [
                {
                    "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/cluster/task-id",
                    "containers": [
                        {
                            "name": "app",
                            "environment": [
                                {"name": "SECRET_VAR", "value": "secret-value"},
                            ],
                        }
                    ],
                    "overrides": {"containerOverrides": []},
                }
            ]
        }

        result = _sanitize_sensitive_response(response, "DescribeTasks")

        container = result["tasks"][0]["containers"][0]
        assert container["environment"][0]["name"] == "SECRET_VAR"
        assert container["environment"][0]["value"] == "[REDACTED]"

    def test_describe_tasks_redacts_override_env(self):
        """DescribeTasks container override environment values are redacted."""
        response = {
            "tasks": [
                {
                    "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/cluster/task-id",
                    "containers": [],
                    "overrides": {
                        "containerOverrides": [
                            {
                                "name": "app",
                                "environment": [
                                    {"name": "OVERRIDE_SECRET", "value": "override-value"},
                                ],
                            }
                        ]
                    },
                }
            ]
        }

        result = _sanitize_sensitive_response(response, "DescribeTasks")

        override = result["tasks"][0]["overrides"]["containerOverrides"][0]
        assert override["environment"][0]["name"] == "OVERRIDE_SECRET"
        assert override["environment"][0]["value"] == "[REDACTED]"

    def test_sanitize_does_not_mutate_original(self):
        """Sanitization returns a new dict without mutating the original."""
        response = {
            "taskDefinition": {
                "containerDefinitions": [
                    {"name": "app", "environment": [{"name": "KEY", "value": "original"}]}
                ]
            }
        }

        _sanitize_sensitive_response(response, "DescribeTaskDefinition")

        # Original should be unchanged
        assert (
            response["taskDefinition"]["containerDefinitions"][0]["environment"][0]["value"]
            == "original"
        )

    def test_describe_task_definition_without_task_definition_key(self):
        """A response with no taskDefinition (e.g. an error shape) is returned unchanged."""
        response = {"status": "error", "error": "Task definition not found"}

        assert _sanitize_sensitive_response(response, "DescribeTaskDefinition") == response

    def test_describe_express_gateway_service_redacts_every_active_configuration(self):
        """Each active configuration's primaryContainer has its env values and secrets redacted."""

        def configuration(revision, password):
            return {
                "serviceRevisionArn": (
                    f"arn:aws:ecs:us-east-1:123456789012:service-revision/prod/my-api/{revision}"
                ),
                "cpu": "1024",
                "primaryContainer": {
                    "image": f"123456789012.dkr.ecr.us-east-1.amazonaws.com/my-api:{revision}",
                    "containerPort": 8080,
                    "environment": [{"name": "DB_PASS", "value": password}],
                    "secrets": [
                        {
                            "name": "TOKEN",
                            "valueFrom": "arn:aws:ssm:us-east-1:123456789012:parameter/token",
                        }
                    ],
                },
            }

        response = {
            "service": {
                "serviceName": "my-api",
                "activeConfigurations": [
                    configuration(1, "old-pass"),
                    configuration(2, "new-pass"),
                ],
            }
        }

        result = _sanitize_sensitive_response(response, "DescribeExpressGatewayService")

        for revision, sanitized in enumerate(result["service"]["activeConfigurations"], start=1):
            container = sanitized["primaryContainer"]
            assert container["environment"] == [{"name": "DB_PASS", "value": "[REDACTED]"}]
            assert container["secrets"] == [{"name": "TOKEN", "valueFrom": "[REDACTED]"}]
            assert container["image"].endswith(f":{revision}")
            assert container["containerPort"] == 8080
            assert sanitized["cpu"] == "1024"
        assert result["service"]["serviceName"] == "my-api"
        # Original is untouched
        assert response["service"]["activeConfigurations"][1]["primaryContainer"][
            "environment"
        ] == [{"name": "DB_PASS", "value": "new-pass"}]

    def test_describe_express_gateway_service_without_service_key(self):
        """A response with no service (e.g. an error shape) is returned unchanged."""
        response = {"status": "error", "error": "Service not found"}

        assert _sanitize_sensitive_response(response, "DescribeExpressGatewayService") == response

    def test_describe_express_gateway_service_configuration_without_primary_container(self):
        """An active configuration with no primaryContainer is returned unchanged."""
        response = {
            "service": {
                "serviceName": "my-api",
                "activeConfigurations": [{"serviceRevisionArn": "arn:rev/1", "cpu": "512"}],
            }
        }

        assert _sanitize_sensitive_response(response, "DescribeExpressGatewayService") == response


class TestEcsApiOperationSensitiveData:
    """Integration tests for ALLOW_SENSITIVE_DATA enforcement in ecs_api_operation."""

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.config.get_config")
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_task_definition_sanitized_when_sensitive_data_disabled(
        self, mock_get_client, mock_get_config
    ):
        """DescribeTaskDefinition response is sanitized when ALLOW_SENSITIVE_DATA=false."""
        mock_get_config.return_value = {"allow-write": False, "allow-sensitive-data": False}

        mock_ecs = MagicMock()
        mock_ecs.describe_task_definition.return_value = {
            "taskDefinition": {
                "family": "my-app",
                "containerDefinitions": [
                    {
                        "name": "app",
                        "environment": [{"name": "DB_PASS", "value": "p@ssw0rd"}],
                        "secrets": [
                            {"name": "TOKEN", "valueFrom": "arn:aws:ssm:us-east-1:123:param/x"}
                        ],
                    }
                ],
            }
        }
        mock_get_client.return_value = mock_ecs

        result = await ecs_api_operation(
            api_operation="DescribeTaskDefinition",
            api_params={"taskDefinition": "my-app:1"},
        )

        container = result["taskDefinition"]["containerDefinitions"][0]
        assert container["environment"][0]["value"] == "[REDACTED]"
        assert container["secrets"][0]["valueFrom"] == "[REDACTED]"

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.config.get_config")
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_task_definition_not_sanitized_when_sensitive_data_enabled(
        self, mock_get_client, mock_get_config
    ):
        """DescribeTaskDefinition response is NOT sanitized when ALLOW_SENSITIVE_DATA=true."""
        mock_get_config.return_value = {"allow-write": False, "allow-sensitive-data": True}

        mock_ecs = MagicMock()
        mock_ecs.describe_task_definition.return_value = {
            "taskDefinition": {
                "family": "my-app",
                "containerDefinitions": [
                    {
                        "name": "app",
                        "environment": [{"name": "DB_PASS", "value": "p@ssw0rd"}],
                    }
                ],
            }
        }
        mock_get_client.return_value = mock_ecs

        result = await ecs_api_operation(
            api_operation="DescribeTaskDefinition",
            api_params={"taskDefinition": "my-app:1"},
        )

        container = result["taskDefinition"]["containerDefinitions"][0]
        assert container["environment"][0]["value"] == "p@ssw0rd"

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.config.get_config")
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_tasks_sanitized_when_sensitive_data_disabled(
        self, mock_get_client, mock_get_config
    ):
        """DescribeTasks response is sanitized when ALLOW_SENSITIVE_DATA=false."""
        mock_get_config.return_value = {"allow-write": False, "allow-sensitive-data": False}

        mock_ecs = MagicMock()
        mock_ecs.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "arn:aws:ecs:us-east-1:123:task/cluster/id",
                    "containers": [
                        {
                            "name": "app",
                            "environment": [{"name": "SECRET", "value": "my-secret"}],
                        }
                    ],
                    "overrides": {
                        "containerOverrides": [
                            {
                                "name": "app",
                                "environment": [{"name": "OVERRIDE", "value": "override-val"}],
                            }
                        ]
                    },
                }
            ]
        }
        mock_get_client.return_value = mock_ecs

        result = await ecs_api_operation(
            api_operation="DescribeTasks",
            api_params={"cluster": "my-cluster", "tasks": ["task-1"]},
        )

        task = result["tasks"][0]
        assert task["containers"][0]["environment"][0]["value"] == "[REDACTED]"
        assert task["overrides"]["containerOverrides"][0]["environment"][0]["value"] == "[REDACTED]"

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.config.get_config")
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_non_sensitive_describe_not_affected(self, mock_get_client, mock_get_config):
        """Non-sensitive Describe operations are not affected by ALLOW_SENSITIVE_DATA."""
        mock_get_config.return_value = {"allow-write": False, "allow-sensitive-data": False}

        mock_ecs = MagicMock()
        mock_ecs.describe_clusters.return_value = {
            "clusters": [{"clusterName": "test", "status": "ACTIVE"}]
        }
        mock_get_client.return_value = mock_ecs

        result = await ecs_api_operation(
            api_operation="DescribeClusters",
            api_params={"clusters": ["test"]},
        )

        # Should pass through unmodified
        assert result["clusters"][0]["clusterName"] == "test"
        assert result["clusters"][0]["status"] == "ACTIVE"

    @staticmethod
    def _express_service_response():
        return {
            "service": {
                "serviceName": "my-api",
                "serviceArn": "arn:aws:ecs:us-east-1:123456789012:service/prod/my-api",
                "status": "ACTIVE",
                "activeConfigurations": [
                    {
                        "serviceRevisionArn": (
                            "arn:aws:ecs:us-east-1:123456789012:service-revision/prod/my-api/1"
                        ),
                        "cpu": "1024",
                        "memory": "2048",
                        "primaryContainer": {
                            "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-api:1",
                            "containerPort": 8080,
                            "environment": [{"name": "DB_PASS", "value": "p@ssw0rd"}],
                            "secrets": [
                                {
                                    "name": "TOKEN",
                                    "valueFrom": "arn:aws:ssm:us-east-1:123456789012:parameter/x",
                                }
                            ],
                        },
                    }
                ],
            }
        }

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.config.get_config")
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_express_gateway_service_sanitized_when_sensitive_data_disabled(
        self, mock_get_client, mock_get_config
    ):
        """DescribeExpressGatewayService response is sanitized when ALLOW_SENSITIVE_DATA=false."""
        mock_get_config.return_value = {"allow-write": False, "allow-sensitive-data": False}

        mock_ecs = MagicMock()
        mock_ecs.describe_express_gateway_service.return_value = self._express_service_response()
        mock_get_client.return_value = mock_ecs

        result = await ecs_api_operation(
            api_operation="DescribeExpressGatewayService",
            api_params={"serviceArn": "arn:aws:ecs:us-east-1:123456789012:service/prod/my-api"},
        )

        container = result["service"]["activeConfigurations"][0]["primaryContainer"]
        assert container["environment"] == [{"name": "DB_PASS", "value": "[REDACTED]"}]
        assert container["secrets"] == [{"name": "TOKEN", "valueFrom": "[REDACTED]"}]
        assert container["image"] == "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-api:1"
        assert container["containerPort"] == 8080
        assert result["service"]["status"] == "ACTIVE"

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.config.get_config")
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_express_gateway_service_not_sanitized_when_sensitive_data_enabled(
        self, mock_get_client, mock_get_config
    ):
        """DescribeExpressGatewayService response is left intact when ALLOW_SENSITIVE_DATA=true."""
        mock_get_config.return_value = {"allow-write": False, "allow-sensitive-data": True}

        mock_ecs = MagicMock()
        mock_ecs.describe_express_gateway_service.return_value = self._express_service_response()
        mock_get_client.return_value = mock_ecs

        result = await ecs_api_operation(
            api_operation="DescribeExpressGatewayService",
            api_params={"serviceArn": "arn:aws:ecs:us-east-1:123456789012:service/prod/my-api"},
        )

        assert result == self._express_service_response()
