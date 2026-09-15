"""
Pytest-style unit tests for security utilities.
"""

import json
import os
from unittest.mock import patch

import pytest

from awslabs.ecs_mcp_server.utils.security import (
    REDACTED,
    ValidationError,
    redact_container_definition,
    redact_task_definition,
    validate_app_name,
    validate_cloudformation_template,
)


class TestValidateAppName:
    """Tests for validate_app_name function with AWS ECS/ECR requirements."""

    def test_valid_app_names(self):
        """Test that valid application names pass validation."""
        # Valid names that comply with AWS ECS/ECR requirements
        valid_names = [
            "myapp",  # Simple lowercase
            "my-app",  # Lowercase with hyphen
            "app123",  # Alphanumeric lowercase
            "123app",  # Starting with digit
            "a",  # Single character
            "web-service-api",  # Multiple hyphens (non-consecutive)
            "my-app-v2",  # Complex valid name
            "x" * 20,  # Maximum length (20 characters)
        ]

        for name in valid_names:
            assert validate_app_name(name) is True

    def test_empty_name(self):
        """Test that empty name fails validation."""
        with pytest.raises(ValidationError) as excinfo:
            validate_app_name("")
        assert "cannot be empty" in str(excinfo.value)

    def test_non_string_input(self):
        """Test that non-string input fails validation."""
        invalid_inputs = [None, 123, [], {}]

        for invalid_input in invalid_inputs:
            with pytest.raises(ValidationError) as excinfo:
                validate_app_name(invalid_input)
            assert "must be a string" in str(excinfo.value)

    def test_length_constraints(self):
        """Test length validation (1-20 characters)."""
        # Test too long
        long_name = "a" * 21  # 21 characters
        with pytest.raises(ValidationError) as excinfo:
            validate_app_name(long_name)
        assert "must be 1-20 characters long" in str(excinfo.value)
        assert "current length: 21" in str(excinfo.value)

    def test_uppercase_letters_rejected(self):
        """Test that uppercase letters are rejected."""
        uppercase_names = [
            "MY-APP-123",  # All uppercase
            "My-App",  # Mixed case
            "myApp",  # CamelCase
            "web-Service",  # Single uppercase
        ]

        for name in uppercase_names:
            with pytest.raises(ValidationError) as excinfo:
                validate_app_name(name)
            assert "contains invalid characters" in str(excinfo.value)

    def test_invalid_characters(self):
        """Test that invalid characters are rejected."""
        invalid_names = [
            "my_app",  # Underscore (was previously allowed)
            "my app",  # Space
            "my.app",  # Period
            "my/app",  # Slash
            "my\\app",  # Backslash
            "my$app",  # Dollar sign
            "my@app",  # At sign
            "my:app",  # Colon
            "my;app",  # Semicolon
            'my"app',  # Quote
            "my'app",  # Apostrophe
            "my`app",  # Backtick
            "my!app",  # Exclamation mark
            "my#app",  # Hash
            "my%app",  # Percent
            "my^app",  # Caret
            "my&app",  # Ampersand
            "my*app",  # Asterisk
            "my(app)",  # Parentheses
            "my+app",  # Plus
            "my=app",  # Equals
            "my{app}",  # Braces
            "my[app]",  # Brackets
            "my|app",  # Pipe
            "my<app>",  # Angle brackets
            "my?app",  # Question mark
            "my,app",  # Comma
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError) as excinfo:
                validate_app_name(name)
            assert "contains invalid characters" in str(excinfo.value)

    def test_hyphen_placement_rules(self):
        """Test hyphen placement validation."""
        # Starting with hyphen
        with pytest.raises(ValidationError) as excinfo:
            validate_app_name("-myapp")
        assert "contains invalid characters" in str(excinfo.value)

        # Ending with hyphen
        with pytest.raises(ValidationError) as excinfo:
            validate_app_name("myapp-")
        assert "contains invalid characters" in str(excinfo.value)

        # Consecutive hyphens
        with pytest.raises(ValidationError) as excinfo:
            validate_app_name("my--app")
        assert "contains invalid characters" in str(excinfo.value)

    def test_valid_hyphen_usage(self):
        """Test that valid hyphen usage passes."""
        valid_hyphen_names = [
            "my-app",
            "web-service-api",
            "app-v2-prod",
            "a-b-c-d-e",
        ]

        for name in valid_hyphen_names:
            assert validate_app_name(name) is True

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Minimum length
        assert validate_app_name("a") is True
        assert validate_app_name("1") is True

        # Maximum length
        assert validate_app_name("a" * 20) is True

        # All digits
        assert validate_app_name("123456") is True

        # Mixed alphanumeric with hyphens
        assert validate_app_name("web123-api456") is True


class TestValidateCloudFormationTemplate:
    """Tests for validate_cloudformation_template function."""

    @pytest.fixture
    def valid_template_file(self, tmp_path):
        """Create a valid CloudFormation template file."""
        template = {
            "Resources": {
                "MyBucket": {"Type": "AWS::S3::Bucket", "Properties": {"BucketName": "my-bucket"}}
            }
        }

        template_file = tmp_path / "valid_template.json"
        template_file.write_text(json.dumps(template))

        return template_file

    @pytest.fixture
    def invalid_json_template_file(self, tmp_path):
        """Create an invalid JSON CloudFormation template file."""
        template_file = tmp_path / "invalid_json_template.json"
        template_file.write_text("This is not valid JSON")

        return template_file

    @pytest.fixture
    def non_dict_template_file(self, tmp_path):
        """Create a CloudFormation template file that is valid JSON but not a dictionary."""
        # Create a JSON array instead of a JSON object
        template = ["item1", "item2", "item3"]

        template_file = tmp_path / "non_dict_template.json"
        template_file.write_text(json.dumps(template))

        return template_file

    @pytest.fixture
    def empty_resources_template_file(self, tmp_path):
        """Create a CloudFormation template file with empty Resources section."""
        template = {"Resources": {}}

        template_file = tmp_path / "empty_resources_template.json"
        template_file.write_text(json.dumps(template))

        return template_file

    @pytest.fixture
    def missing_resources_template_file(self, tmp_path):
        """Create a CloudFormation template file with missing Resources section."""
        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": "Template with missing Resources section",
        }

        template_file = tmp_path / "missing_resources_template.json"
        template_file.write_text(json.dumps(template))

        return template_file

    @pytest.fixture
    def invalid_resources_type_template_file(self, tmp_path):
        """Create a CloudFormation template file with invalid Resources type."""
        template = {"Resources": "This should be an object, not a string"}

        template_file = tmp_path / "invalid_resources_type_template.json"
        template_file.write_text(json.dumps(template))

        return template_file

    def test_valid_template(self, valid_template_file):
        """Test that a valid CloudFormation template passes validation."""
        assert validate_cloudformation_template(str(valid_template_file)) is True

    def test_invalid_json_template(self, invalid_json_template_file):
        """Test that an invalid JSON CloudFormation template fails validation."""
        with pytest.raises(ValidationError) as excinfo:
            validate_cloudformation_template(str(invalid_json_template_file))
        assert "Invalid JSON" in str(excinfo.value)

    def test_non_dict_template(self, non_dict_template_file):
        """Test that a CloudFormation template that is not a dictionary fails validation."""
        with pytest.raises(ValidationError) as excinfo:
            validate_cloudformation_template(str(non_dict_template_file))
        assert "CloudFormation template must be a JSON object" in str(excinfo.value)

    def test_empty_resources_template(self, empty_resources_template_file):
        """Test that a CloudFormation template with empty Resources section fails validation."""
        with pytest.raises(ValidationError) as excinfo:
            validate_cloudformation_template(str(empty_resources_template_file))
        assert "must define at least one resource" in str(excinfo.value)

    def test_missing_resources_template(self, missing_resources_template_file):
        """Test that a CloudFormation template with missing Resources section fails validation."""
        with pytest.raises(ValidationError) as excinfo:
            validate_cloudformation_template(str(missing_resources_template_file))
        assert "must contain a 'Resources' section" in str(excinfo.value)

    def test_invalid_resources_type_template(self, invalid_resources_type_template_file):
        """Test that a CloudFormation template with invalid Resources type fails validation."""
        with pytest.raises(ValidationError) as excinfo:
            validate_cloudformation_template(str(invalid_resources_type_template_file))
        assert "'Resources' section must be a JSON object" in str(excinfo.value)

    def test_nonexistent_template_file(self):
        """Test that a nonexistent template file fails validation."""
        with pytest.raises(ValidationError) as excinfo:
            validate_cloudformation_template("/path/to/nonexistent/template.json")
        assert "does not exist" in str(excinfo.value)

    @patch("awslabs.ecs_mcp_server.utils.security.open", side_effect=IOError("Permission denied"))
    def test_unreadable_template_file(self, mock_open_func, valid_template_file):
        """Test that an unreadable template file fails validation."""
        with pytest.raises(ValidationError) as excinfo:
            validate_cloudformation_template(str(valid_template_file))
        assert "Failed to read template file" in str(excinfo.value)

    def test_template_file_in_sensitive_directory(self):
        """Test that a template path inside a sensitive directory fails validation."""
        sensitive_template = os.path.join(os.path.expanduser("~"), ".aws", "template.json")

        with pytest.raises(ValidationError) as excinfo:
            validate_cloudformation_template(sensitive_template)
        assert "sensitive directory" in str(excinfo.value)


class TestRedactTaskDefinition:
    """Tests for redact_task_definition."""

    @staticmethod
    def _task_definition():
        return {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/my-app:5",
            "family": "my-app",
            "revision": 5,
            "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
            "containerDefinitions": [
                {
                    "name": "app",
                    "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:latest",
                    "cpu": 256,
                    "environment": [
                        {"name": "DB_HOST", "value": "prod-db.example.com"},
                        {"name": "DB_PASSWORD", "value": "super-secret-password"},
                    ],
                    "secrets": [
                        {
                            "name": "API_KEY",
                            "valueFrom": (
                                "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/api-key"
                            ),
                        },
                        {
                            "name": "API_TOKEN",
                            "valueFrom": "arn:aws:ssm:us-east-1:123456789012:parameter/prod/token",
                        },
                    ],
                },
                {
                    "name": "sidecar",
                    "image": "public.ecr.aws/aws-observability/aws-otel-collector:latest",
                    "environment": [{"name": "LOG_LEVEL", "value": "debug"}],
                },
            ],
        }

    def test_redacts_environment_values_and_keeps_names(self):
        """Environment variable values are redacted for every container; names are kept."""
        result = redact_task_definition(self._task_definition())

        app, sidecar = result["containerDefinitions"]
        assert app["environment"] == [
            {"name": "DB_HOST", "value": REDACTED},
            {"name": "DB_PASSWORD", "value": REDACTED},
        ]
        assert sidecar["environment"] == [{"name": "LOG_LEVEL", "value": REDACTED}]

    def test_redacts_secret_references_and_keeps_names(self):
        """Secret valueFrom ARNs are redacted; secret names are kept."""
        result = redact_task_definition(self._task_definition())

        assert result["containerDefinitions"][0]["secrets"] == [
            {"name": "API_KEY", "valueFrom": REDACTED},
            {"name": "API_TOKEN", "valueFrom": REDACTED},
        ]

    def test_redacted_output_contains_no_sensitive_values(self):
        """No environment value or secret ARN survives anywhere in the redacted output."""
        serialized = json.dumps(redact_task_definition(self._task_definition()))

        assert "super-secret-password" not in serialized
        assert "prod-db.example.com" not in serialized
        assert "secretsmanager" not in serialized
        assert "arn:aws:ssm" not in serialized

    def test_preserves_non_sensitive_fields(self):
        """Fields needed for troubleshooting are left untouched."""
        original = self._task_definition()
        result = redact_task_definition(original)

        assert result["taskDefinitionArn"] == original["taskDefinitionArn"]
        assert result["family"] == "my-app"
        assert result["revision"] == 5
        assert result["executionRoleArn"] == original["executionRoleArn"]
        assert (
            result["containerDefinitions"][0]["image"]
            == (original["containerDefinitions"][0]["image"])
        )
        assert result["containerDefinitions"][0]["cpu"] == 256
        assert [c["name"] for c in result["containerDefinitions"]] == ["app", "sidecar"]

    def test_does_not_mutate_input(self):
        """The caller's task definition is left exactly as it was."""
        original = self._task_definition()
        snapshot = json.loads(json.dumps(original))

        redact_task_definition(original)

        assert original == snapshot

    def test_container_without_secrets_gains_no_secrets_key(self):
        """A container that declares no secrets is not given an empty secrets list."""
        result = redact_task_definition(self._task_definition())

        assert "secrets" not in result["containerDefinitions"][1]

    @pytest.mark.parametrize(
        "task_definition",
        [
            {},
            {"family": "no-containers"},
            {"containerDefinitions": []},
            {"containerDefinitions": [{"name": "bare"}]},
            {"containerDefinitions": [{"name": "empty", "environment": [], "secrets": []}]},
        ],
    )
    def test_handles_task_definitions_without_sensitive_fields(self, task_definition):
        """Task definitions with no environment or secrets are returned unchanged."""
        assert redact_task_definition(task_definition) == task_definition


class TestRedactContainerDefinition:
    """Tests for redact_container_definition."""

    @staticmethod
    def _primary_container():
        return {
            "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-api:1",
            "containerPort": 8080,
            "command": ["node", "server.js"],
            "environment": [{"name": "DB_PASSWORD", "value": "super-secret-password"}],
            "secrets": [
                {
                    "name": "API_KEY",
                    "valueFrom": (
                        "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/api-key"
                    ),
                }
            ],
        }

    def test_redacts_environment_values_and_secret_references(self):
        """Values and secret ARNs are redacted; names are kept."""
        result = redact_container_definition(self._primary_container())

        assert result["environment"] == [{"name": "DB_PASSWORD", "value": REDACTED}]
        assert result["secrets"] == [{"name": "API_KEY", "valueFrom": REDACTED}]

    def test_preserves_non_sensitive_fields(self):
        """Image, port and command are left untouched."""
        original = self._primary_container()
        result = redact_container_definition(original)

        assert result["image"] == original["image"]
        assert result["containerPort"] == 8080
        assert result["command"] == ["node", "server.js"]

    def test_does_not_mutate_input(self):
        """The caller's container definition is left exactly as it was."""
        original = self._primary_container()
        snapshot = json.loads(json.dumps(original))

        redact_container_definition(original)

        assert original == snapshot

    @pytest.mark.parametrize(
        "container",
        [
            {},
            {"image": "nginx:latest"},
            {"image": "nginx:latest", "environment": [], "secrets": []},
        ],
    )
    def test_handles_containers_without_sensitive_fields(self, container):
        """Containers with no environment or secrets are returned unchanged."""
        assert redact_container_definition(container) == container
