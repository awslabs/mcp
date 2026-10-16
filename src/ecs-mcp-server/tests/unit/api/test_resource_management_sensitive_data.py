"""
Unit tests for ALLOW_SENSITIVE_DATA enforcement in ecs_resource_management.

Validates which operations are treated as sensitive and that their responses are
redacted through ecs_api_operation when ALLOW_SENSITIVE_DATA is not enabled.
"""

import re
from unittest.mock import MagicMock, patch

import botocore.session
import pytest

from awslabs.ecs_mcp_server.api.resource_management import (
    SENSITIVE_DATA_OPERATIONS,
    SUPPORTED_ECS_OPERATIONS,
    ecs_api_operation,
)
from awslabs.ecs_mcp_server.utils.security import (
    _REFERENCE_FIELDS,
    _REFERENCE_LIST_FIELDS,
    _VALUE_LIST_FIELDS,
    REDACTED,
)

# Every member name in the ECS API model that looks like a secret or credential, classified.
# The redaction rule must cover the first group; the second group was reviewed and holds
# identifiers or pagination tokens, not secrets.
SECRET_LIKE_MEMBERS_REDACTED = {
    "credentialsParameter",
    "credentialSpecs",
    "repositoryCredentials",
    "secretOptions",
    "secrets",
    "tokenValue",
}
SECRET_LIKE_MEMBERS_NOT_SENSITIVE = {
    "clientToken",  # idempotency token supplied by the caller
    "fargateEphemeralStorageKmsKeyId",  # KMS key identifier
    "key",  # Tag.key
    "kmsKey",  # KMS key identifier
    "kmsKeyId",  # KMS key identifier
    "nextToken",  # pagination
    "s3KeyPrefix",  # log location prefix
    "tagKeys",  # UntagResource request
}
SECRET_LIKE_NAME = re.compile(r"secret|credential|password|token|key", re.IGNORECASE)


def _ecs_model():
    return botocore.session.get_session().get_service_model("ecs")


def _carries_sensitive_fields(shape, seen=frozenset()) -> bool:
    """Applies the production redaction rule to the botocore shape graph of one API response."""
    if shape is None or shape.name in seen:
        return False
    seen = seen | {shape.name}
    if shape.type_name == "structure":
        for name, member in shape.members.items():
            if name in _REFERENCE_FIELDS:
                return True
            if name in _REFERENCE_LIST_FIELDS and member.type_name == "list":
                return True
            if (
                name in _VALUE_LIST_FIELDS
                and member.type_name == "list"
                and member.member.type_name == "structure"
                and "value" in member.member.members
            ):
                return True
            if _carries_sensitive_fields(member, seen):
                return True
        return False
    if shape.type_name == "list":
        return _carries_sensitive_fields(shape.member, seen)
    if shape.type_name == "map":
        return _carries_sensitive_fields(shape.value, seen)
    return False


class TestSensitiveDataOperations:
    """Tests for the SENSITIVE_DATA_OPERATIONS set."""

    def test_sensitive_operations_set_contains_expected(self):
        """The set includes the operations that return task, container and service configuration."""
        for operation in (
            "DescribeTaskDefinition",
            "DescribeTasks",
            "DescribeExpressGatewayService",
            "RegisterTaskDefinition",
            "DeregisterTaskDefinition",
            "DeleteTaskDefinitions",
            "DescribeServices",
            "RunTask",
            "ExecuteCommand",
        ):
            assert operation in SENSITIVE_DATA_OPERATIONS

    def test_non_sensitive_operations_not_in_set(self):
        """Operations whose responses carry no configuration values are not in the set."""
        for operation in ("DescribeClusters", "ListClusters", "ListServices", "ListTasks"):
            assert operation not in SENSITIVE_DATA_OPERATIONS

    def test_sensitive_operations_are_supported(self):
        """Every sensitive operation is one the tool can actually execute."""
        assert SENSITIVE_DATA_OPERATIONS <= set(SUPPORTED_ECS_OPERATIONS)

    def test_sensitive_operations_match_ecs_api_model(self):
        """The set equals the supported operations whose response shape can carry a sensitive field.

        Derived from the botocore ECS model pinned in uv.lock. A botocore upgrade that adds a
        sensitive field to a supported operation's response fails this test on purpose: update
        SENSITIVE_DATA_OPERATIONS to match and the redaction follows automatically.
        """
        model = _ecs_model()

        expected = {
            operation
            for operation in SUPPORTED_ECS_OPERATIONS
            if operation in model.operation_names
            and _carries_sensitive_fields(model.operation_model(operation).output_shape)
        }

        assert SENSITIVE_DATA_OPERATIONS == expected

    def test_every_secret_like_field_in_the_model_is_classified(self):
        """Independent check of the rule itself, not just of the operation set.

        Every member of the ECS API model whose name suggests a secret or credential must either
        be redacted by the rule or be in the reviewed non-sensitive list. A new secret-bearing
        field in a botocore upgrade fails here until it is classified.
        """
        model = _ecs_model()

        secret_like_members = {}
        for shape_name in model.shape_names:
            shape = model.shape_for(shape_name)
            if shape.type_name != "structure":
                continue
            for member_name, member in shape.members.items():
                if SECRET_LIKE_NAME.search(member_name):
                    secret_like_members.setdefault(member_name, []).append(member)

        assert set(secret_like_members) == (
            SECRET_LIKE_MEMBERS_REDACTED | SECRET_LIKE_MEMBERS_NOT_SENSITIVE
        )
        for member_name in SECRET_LIKE_MEMBERS_REDACTED:
            for member in secret_like_members[member_name]:
                redacted = (
                    member_name in _REFERENCE_FIELDS
                    or (member_name in _REFERENCE_LIST_FIELDS and member.type_name == "list")
                    or _carries_sensitive_fields(member)
                )
                assert redacted, f"{member_name} ({member.name}) is not covered by the rule"


class TestEcsApiOperationSensitiveData:
    """Integration tests for ALLOW_SENSITIVE_DATA enforcement in ecs_api_operation."""

    @staticmethod
    def _task_definition_response():
        return {
            "taskDefinition": {
                "family": "my-app",
                "containerDefinitions": [
                    {
                        "name": "app",
                        "environment": [{"name": "DB_PASS", "value": "p@ssw0rd"}],
                        "secrets": [
                            {"name": "TOKEN", "valueFrom": "arn:aws:ssm:us-east-1:123:param/x"}
                        ],
                        "logConfiguration": {
                            "logDriver": "splunk",
                            "secretOptions": [
                                {
                                    "name": "splunk-token",
                                    "valueFrom": "arn:aws:ssm:us-east-1:123:param/splunk",
                                }
                            ],
                        },
                    }
                ],
            }
        }

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
    async def test_describe_task_definition_redacted_when_sensitive_data_disabled(
        self, mock_get_client, mock_get_config
    ):
        """DescribeTaskDefinition response is redacted when ALLOW_SENSITIVE_DATA=false."""
        mock_get_config.return_value = {"allow-write": False, "allow-sensitive-data": False}
        mock_ecs = MagicMock()
        mock_ecs.describe_task_definition.return_value = self._task_definition_response()
        mock_get_client.return_value = mock_ecs

        result = await ecs_api_operation(
            api_operation="DescribeTaskDefinition",
            api_params={"taskDefinition": "my-app:1"},
        )

        container = result["taskDefinition"]["containerDefinitions"][0]
        assert container["environment"] == [{"name": "DB_PASS", "value": REDACTED}]
        assert container["secrets"] == [{"name": "TOKEN", "valueFrom": REDACTED}]
        assert container["logConfiguration"]["secretOptions"] == [
            {"name": "splunk-token", "valueFrom": REDACTED}
        ]
        assert container["logConfiguration"]["logDriver"] == "splunk"

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.config.get_config")
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_task_definition_not_redacted_when_sensitive_data_enabled(
        self, mock_get_client, mock_get_config
    ):
        """DescribeTaskDefinition response is returned in full when ALLOW_SENSITIVE_DATA=true."""
        mock_get_config.return_value = {"allow-write": False, "allow-sensitive-data": True}
        mock_ecs = MagicMock()
        mock_ecs.describe_task_definition.return_value = self._task_definition_response()
        mock_get_client.return_value = mock_ecs

        result = await ecs_api_operation(
            api_operation="DescribeTaskDefinition",
            api_params={"taskDefinition": "my-app:1"},
        )

        assert result == self._task_definition_response()

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.config.get_config")
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_tasks_redacted_when_sensitive_data_disabled(
        self, mock_get_client, mock_get_config
    ):
        """DescribeTasks response is redacted when ALLOW_SENSITIVE_DATA=false."""
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
        assert task["containers"][0]["environment"][0]["value"] == REDACTED
        assert task["overrides"]["containerOverrides"][0]["environment"][0]["value"] == REDACTED

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.config.get_config")
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_express_gateway_service_redacted_when_sensitive_data_disabled(
        self, mock_get_client, mock_get_config
    ):
        """DescribeExpressGatewayService response is redacted when ALLOW_SENSITIVE_DATA=false."""
        mock_get_config.return_value = {"allow-write": False, "allow-sensitive-data": False}
        mock_ecs = MagicMock()
        mock_ecs.describe_express_gateway_service.return_value = self._express_service_response()
        mock_get_client.return_value = mock_ecs

        result = await ecs_api_operation(
            api_operation="DescribeExpressGatewayService",
            api_params={"serviceArn": "arn:aws:ecs:us-east-1:123456789012:service/prod/my-api"},
        )

        container = result["service"]["activeConfigurations"][0]["primaryContainer"]
        assert container["environment"] == [{"name": "DB_PASS", "value": REDACTED}]
        assert container["secrets"] == [{"name": "TOKEN", "valueFrom": REDACTED}]
        assert container["image"] == "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-api:1"
        assert container["containerPort"] == 8080
        assert result["service"]["status"] == "ACTIVE"

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.config.get_config")
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_express_gateway_service_not_redacted_when_sensitive_data_enabled(
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

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.config.get_config")
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_write_operation_response_redacted_when_sensitive_data_disabled(
        self, mock_get_client, mock_get_config
    ):
        """A write operation echoing a task definition is redacted regardless of ALLOW_WRITE."""
        mock_get_config.return_value = {"allow-write": True, "allow-sensitive-data": False}
        mock_ecs = MagicMock()
        mock_ecs.deregister_task_definition.return_value = self._task_definition_response()
        mock_get_client.return_value = mock_ecs

        result = await ecs_api_operation(
            api_operation="DeregisterTaskDefinition",
            api_params={"taskDefinition": "my-app:1"},
        )

        container = result["taskDefinition"]["containerDefinitions"][0]
        assert container["environment"] == [{"name": "DB_PASS", "value": REDACTED}]
        assert container["secrets"] == [{"name": "TOKEN", "valueFrom": REDACTED}]
        mock_ecs.deregister_task_definition.assert_called_once_with(taskDefinition="my-app:1")

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.config.get_config")
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_non_sensitive_describe_not_affected(self, mock_get_client, mock_get_config):
        """Non-sensitive Describe operations pass through unmodified."""
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

        assert result["clusters"][0]["clusterName"] == "test"
        assert result["clusters"][0]["status"] == "ACTIVE"
