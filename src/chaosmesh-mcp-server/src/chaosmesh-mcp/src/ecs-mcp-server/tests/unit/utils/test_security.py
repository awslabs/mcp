"""
Pytest-style unit tests for security utilities.
"""

import json
import os
from unittest.mock import patch

import pytest

from awslabs.ecs_mcp_server.utils.security import (
    ValidationError,
    validate_app_name,
    validate_cloudformation_template,
    validate_file_path,
)


class TestValidateAppName:
    """Tests for validate_app_name function."""

    def test_valid_app_name(self):
        """Test that valid application names pass validation."""
        # Test various valid app names
        valid_names = ["myapp", "my-app", "my_app", "app123", "123app", "MY-APP-123"]

        for name in valid_names:
            assert validate_app_name(name) is True

    def test_invalid_app_name(self):
        """Test that invalid application names fail validation."""
        # Test various invalid app names
        invalid_names = [
            "my app",  # Contains space
            "my.app",  # Contains period
            "my/app",  # Contains slash
            "my\\app",  # Contains backslash
            "my$app",  # Contains dollar sign
            "my@app",  # Contains at sign
            "my:app",  # Contains colon
            "my;app",  # Contains semicolon
            'my"app',  # Contains quote
            "my'app",  # Contains apostrophe
            "my`app",  # Contains backtick
            "my!app",  # Contains exclamation mark
            "my#app",  # Contains hash
            "my%app",  # Contains percent
            "my^app",  # Contains caret
            "my&app",  # Contains ampersand
            "my*app",  # Contains asterisk
            "my(app)",  # Contains parentheses
            "my+app",  # Contains plus
            "my=app",  # Contains equals
            "my{app}",  # Contains braces
            "my[app]",  # Contains brackets
            "my|app",  # Contains pipe
            "my<app>",  # Contains angle brackets
            "my?app",  # Contains question mark
            "my,app",  # Contains comma
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError) as excinfo:
                validate_app_name(name)
            assert "contains invalid characters" in str(excinfo.value)


class TestValidateFilePath:
    """Tests for validate_file_path function."""

    def test_valid_file_path(self, tmp_path):
        """Test that valid file paths pass validation."""
        # Create a temporary file
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test content")

        # Validate the file path
        result = validate_file_path(str(test_file))

        # Check that the result is the absolute path to the file
        assert result == os.path.abspath(str(test_file))

    def test_nonexistent_file_path(self):
        """Test that nonexistent file paths fail validation."""
        with pytest.raises(ValidationError) as excinfo:
            validate_file_path("/path/to/nonexistent/file.txt")
        assert "does not exist" in str(excinfo.value)

    def test_directory_traversal_attempts(self, tmp_path):
        """Test that directory traversal attempts fail validation."""
        # Create a temporary file
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test content")

        # Test various directory traversal attempts
        traversal_attempts = [
            f"{test_file}/../../../etc/passwd",
            f"{test_file}/../../..",
            "../../../etc/passwd",
            "..\\..\\..\\Windows\\System32\\config\\SAM",  # Windows example
        ]

        for path in traversal_attempts:
            with pytest.raises(ValidationError) as excinfo:
                validate_file_path(path)
            assert "suspicious traversal patterns" in str(excinfo.value) or "does not exist" in str(
                excinfo.value
            )


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
