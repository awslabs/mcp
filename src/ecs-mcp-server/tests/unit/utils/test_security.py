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
    redact_sensitive_fields,
    redact_unless_sensitive_data_allowed,
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


class TestRedactSensitiveFields:
    """Tests for redact_sensitive_fields."""

    ARN_SM = "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/api-key"
    ARN_SSM = "arn:aws:ssm:us-east-1:123456789012:parameter/prod/token"
    ARN_S3 = "arn:aws:s3:::my-bucket/app.env"

    @classmethod
    def _task_definition(cls):
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
                    "command": ["node", "server.js"],
                    "environment": [
                        {"name": "DB_HOST", "value": "prod-db.example.com"},
                        {"name": "DB_PASSWORD", "value": "super-secret-password"},
                    ],
                    "environmentFiles": [{"value": cls.ARN_S3, "type": "s3"}],
                    "secrets": [{"name": "API_KEY", "valueFrom": cls.ARN_SM}],
                    "repositoryCredentials": {"credentialsParameter": cls.ARN_SM},
                    "logConfiguration": {
                        "logDriver": "splunk",
                        "options": {"splunk-url": "https://splunk.example.com"},
                        "secretOptions": [{"name": "splunk-token", "valueFrom": cls.ARN_SSM}],
                    },
                    "resourceRequirements": [{"type": "GPU", "value": "1"}],
                    "dockerLabels": {"team": "ecs"},
                    "credentialSpecs": ["credentialspec:arn:aws:s3:::my-bucket/gmsa-credspec.json"],
                },
                {
                    "name": "sidecar",
                    "image": "public.ecr.aws/aws-observability/aws-otel-collector:latest",
                    "environment": [{"name": "LOG_LEVEL", "value": "debug"}],
                },
            ],
            "volumes": [
                {
                    "name": "share",
                    "fsxWindowsFileServerVolumeConfiguration": {
                        "fileSystemId": "fs-0123456789abcdef0",
                        "rootDirectory": "share",
                        "authorizationConfig": {
                            "credentialsParameter": cls.ARN_SM,
                            "domain": "corp",
                        },
                    },
                }
            ],
            "tags": [{"key": "Environment", "value": "production"}],
        }

    def test_redacts_every_secret_bearing_field_of_a_task_definition(self):
        """Values, file locations, secret and credential references are all redacted."""
        result = redact_sensitive_fields(self._task_definition())

        app, sidecar = result["containerDefinitions"]
        assert app["environment"] == [
            {"name": "DB_HOST", "value": REDACTED},
            {"name": "DB_PASSWORD", "value": REDACTED},
        ]
        assert app["environmentFiles"] == [{"value": REDACTED, "type": "s3"}]
        assert app["secrets"] == [{"name": "API_KEY", "valueFrom": REDACTED}]
        assert app["repositoryCredentials"] == {"credentialsParameter": REDACTED}
        assert app["logConfiguration"]["secretOptions"] == [
            {"name": "splunk-token", "valueFrom": REDACTED}
        ]
        assert app["credentialSpecs"] == [REDACTED]
        assert sidecar["environment"] == [{"name": "LOG_LEVEL", "value": REDACTED}]
        assert result["volumes"][0]["fsxWindowsFileServerVolumeConfiguration"][
            "authorizationConfig"
        ] == {"credentialsParameter": REDACTED, "domain": "corp"}

    def test_no_sensitive_value_survives_anywhere(self):
        """Serialising the result shows none of the original secrets or references."""
        serialized = json.dumps(redact_sensitive_fields(self._task_definition()))

        for needle in (
            "super-secret-password",
            "prod-db.example.com",
            self.ARN_SM,
            self.ARN_SSM,
            self.ARN_S3,
            "gmsa-credspec",
        ):
            assert needle not in serialized

    def test_keeps_names_and_non_sensitive_values(self):
        """Names, images, commands, log options, tags and resource requirements are untouched."""
        original = self._task_definition()
        result = redact_sensitive_fields(original)

        app = result["containerDefinitions"][0]
        assert result["taskDefinitionArn"] == original["taskDefinitionArn"]
        assert result["executionRoleArn"] == original["executionRoleArn"]
        assert app["image"] == original["containerDefinitions"][0]["image"]
        assert app["command"] == ["node", "server.js"]
        assert app["logConfiguration"]["logDriver"] == "splunk"
        assert app["logConfiguration"]["options"] == {"splunk-url": "https://splunk.example.com"}
        assert app["dockerLabels"] == {"team": "ecs"}
        # "value" is only sensitive under environment / environmentFiles
        assert app["resourceRequirements"] == [{"type": "GPU", "value": "1"}]
        assert result["tags"] == [{"key": "Environment", "value": "production"}]
        assert [c["name"] for c in result["containerDefinitions"]] == ["app", "sidecar"]

    def test_redacts_express_gateway_service_response(self):
        """The primaryContainer of every active configuration is redacted."""
        response = {
            "service": {
                "serviceName": "my-api",
                "status": "ACTIVE",
                "activeConfigurations": [
                    {
                        "serviceRevisionArn": "arn:rev/1",
                        "cpu": "1024",
                        "primaryContainer": {
                            "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-api:1",
                            "containerPort": 8080,
                            "environment": [{"name": "DB_PASS", "value": "p@ssw0rd"}],
                            "secrets": [{"name": "TOKEN", "valueFrom": self.ARN_SSM}],
                            "repositoryCredentials": {"credentialsParameter": self.ARN_SM},
                        },
                    }
                ],
            }
        }

        result = redact_sensitive_fields(response)

        container = result["service"]["activeConfigurations"][0]["primaryContainer"]
        assert container["environment"] == [{"name": "DB_PASS", "value": REDACTED}]
        assert container["secrets"] == [{"name": "TOKEN", "valueFrom": REDACTED}]
        assert container["repositoryCredentials"] == {"credentialsParameter": REDACTED}
        assert container["containerPort"] == 8080
        assert result["service"]["status"] == "ACTIVE"

    def test_redacts_task_overrides_and_service_connect_log_secrets(self):
        """Container overrides (tasks) and Service Connect log secrets (services) are covered."""
        response = {
            "tasks": [
                {
                    "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/c/1",
                    "overrides": {
                        "containerOverrides": [
                            {
                                "name": "app",
                                "environment": [{"name": "OVERRIDE", "value": "override-val"}],
                                "environmentFiles": [{"value": self.ARN_S3, "type": "s3"}],
                            }
                        ]
                    },
                }
            ],
            "services": [
                {
                    "serviceName": "svc",
                    "deployments": [
                        {
                            "serviceConnectConfiguration": {
                                "logConfiguration": {
                                    "logDriver": "awsfirelens",
                                    "secretOptions": [{"name": "apikey", "valueFrom": self.ARN_SM}],
                                }
                            }
                        }
                    ],
                }
            ],
        }

        result = redact_sensitive_fields(response)

        override = result["tasks"][0]["overrides"]["containerOverrides"][0]
        assert override["environment"] == [{"name": "OVERRIDE", "value": REDACTED}]
        assert override["environmentFiles"] == [{"value": REDACTED, "type": "s3"}]
        log_config = result["services"][0]["deployments"][0]["serviceConnectConfiguration"][
            "logConfiguration"
        ]
        assert log_config == {
            "logDriver": "awsfirelens",
            "secretOptions": [{"name": "apikey", "valueFrom": REDACTED}],
        }

    def test_does_not_mutate_input(self):
        """The caller's structure is left exactly as it was."""
        original = self._task_definition()
        snapshot = json.loads(json.dumps(original))

        redact_sensitive_fields(original)

        assert original == snapshot

    def test_only_redacts_fields_that_are_present(self):
        """No keys are invented: an item without value or valueFrom stays as it is."""
        data = {
            "containerDefinitions": [
                {"name": "bare"},
                {"environment": [{"name": "NO_VALUE"}], "secrets": [{"name": "NO_REF"}]},
            ]
        }

        assert redact_sensitive_fields(data) == data

    @pytest.mark.parametrize(
        "data",
        [
            {},
            [],
            {"family": "no-containers"},
            {"containerDefinitions": []},
            {"containerDefinitions": [{"name": "empty", "environment": [], "secrets": []}]},
            {"status": "error", "error": "Task definition not found"},
            "not-a-structure",
            None,
        ],
    )
    def test_returns_structures_without_sensitive_fields_unchanged(self, data):
        """Anything with no sensitive field, including non-dict input, is returned as is."""
        assert redact_sensitive_fields(data) == data

    def test_redacts_execute_command_session_token(self):
        """The ExecuteCommand session token is redacted; the session id and stream URL are kept."""
        response = {
            "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/c/1",
            "interactive": True,
            "session": {
                "sessionId": "ecs-execute-command-0123456789abcdef0",
                "streamUrl": "wss://ssmmessages.us-east-1.amazonaws.com/v1/data-channel/ecs-execute",
                "tokenValue": "AAEAAd0S3cr3tT0k3n",
            },
        }

        result = redact_sensitive_fields(response)

        assert result["session"] == {
            "sessionId": "ecs-execute-command-0123456789abcdef0",
            "streamUrl": "wss://ssmmessages.us-east-1.amazonaws.com/v1/data-channel/ecs-execute",
            "tokenValue": REDACTED,
        }
        assert result["interactive"] is True


class TestRedactUnlessSensitiveDataAllowed:
    """Tests for redact_unless_sensitive_data_allowed."""

    DATA = {"containerDefinitions": [{"environment": [{"name": "SECRET", "value": "s3cret"}]}]}

    def test_redacts_when_flag_unset(self, monkeypatch):
        """Shipped default: the data is redacted."""
        monkeypatch.delenv("ALLOW_SENSITIVE_DATA", raising=False)

        result = redact_unless_sensitive_data_allowed(self.DATA)

        assert result["containerDefinitions"][0]["environment"][0]["value"] == REDACTED
        assert self.DATA["containerDefinitions"][0]["environment"][0]["value"] == "s3cret"

    def test_returns_data_unchanged_when_flag_enabled(self, monkeypatch):
        """With ALLOW_SENSITIVE_DATA=true the data is returned as is."""
        monkeypatch.setenv("ALLOW_SENSITIVE_DATA", "true")

        assert redact_unless_sensitive_data_allowed(self.DATA) is self.DATA

    @pytest.mark.parametrize("allowed", [False, True])
    def test_uses_the_supplied_config_over_the_environment(self, allowed, monkeypatch):
        """An explicit config wins over whatever the environment says."""
        monkeypatch.setenv("ALLOW_SENSITIVE_DATA", "false" if allowed else "true")

        result = redact_unless_sensitive_data_allowed(self.DATA, {"allow-sensitive-data": allowed})

        expected = "s3cret" if allowed else REDACTED
        assert result["containerDefinitions"][0]["environment"][0]["value"] == expected
