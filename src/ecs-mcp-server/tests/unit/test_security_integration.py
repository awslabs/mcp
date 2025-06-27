"""
Integration tests for the security features.
"""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from awslabs.ecs_mcp_server.utils.security import PERMISSION_NONE, secure_tool


@pytest.fixture
def mock_config():
    """Fixture for a mock configuration."""
    return {"allow-write": True, "allow-sensitive-data": True}


class TestSecurityIntegration:
    """Integration tests for the security features."""

    def test_secure_tool_with_pii(self, mock_config):
        """Test that secure_tool properly sanitizes PII in responses."""
        # Create a mock function that returns a response with PII
        mock_func = AsyncMock(
            return_value={
                "status": "success",
                "message": "Operation completed",
                "user": {
                    "email": "user@example.com",
                    "account_id": "123456789012",
                    "ip_address": "192.168.1.1",
                },
                "aws_key": "AKIAIOSFODNN7EXAMPLE",
                "alb_url": "http://my-app-123456789.us-east-1.elb.amazonaws.com",
            }
        )

        # Apply the secure_tool decorator
        secured_func = secure_tool(mock_config, PERMISSION_NONE, "test_tool")(mock_func)

        # Call the secured function using asyncio.run
        result = asyncio.run(secured_func())

        # Check that the function was called
        mock_func.assert_called_once()

        # Check that the response was sanitized
        assert "user@example.com" not in json.dumps(result)
        assert "123456789012" not in json.dumps(result)
        assert "192.168.1.1" not in json.dumps(result)
        assert "AKIAIOSFODNN7EXAMPLE" not in json.dumps(result)

        # Check that redacted markers are present
        assert "[REDACTED EMAIL]" in json.dumps(result)
        assert "[REDACTED AWS_ACCOUNT_ID]" in json.dumps(result)
        assert "[REDACTED IP_ADDRESS]" in json.dumps(result)
        assert "[REDACTED AWS_ACCESS_KEY]" in json.dumps(result)

        # Check that warnings were added for public endpoints
        assert "warnings" in result
        assert any("publicly accessible" in warning for warning in result["warnings"])

    def test_secure_tool_with_nested_pii(self, mock_config):
        """Test that secure_tool properly sanitizes nested PII in responses."""
        # Create a mock function that returns a response with nested PII
        mock_func = AsyncMock(
            return_value={
                "status": "success",
                "message": "Operation completed",
                "resources": [
                    {
                        "name": "resource1",
                        "owner": "user@example.com",
                        "details": {
                            "account_id": "123456789012",
                            "credentials": {"password": "password=secret123"},
                        },
                    },
                    {
                        "name": "resource2",
                        "ip_addresses": ["192.168.1.1", "10.0.0.1"],
                        "aws_key": "AKIAIOSFODNN7EXAMPLE",
                    },
                ],
            }
        )

        # Apply the secure_tool decorator
        secured_func = secure_tool(mock_config, PERMISSION_NONE, "test_tool")(mock_func)

        # Call the secured function using asyncio.run
        result = asyncio.run(secured_func())

        # Check that the function was called
        mock_func.assert_called_once()

        # Convert result to JSON string for easier searching
        result_json = json.dumps(result)

        # Check that the response was sanitized
        assert "user@example.com" not in result_json
        assert "123456789012" not in result_json
        assert "password=secret123" not in result_json
        assert "192.168.1.1" not in result_json
        assert "10.0.0.1" not in result_json
        assert "AKIAIOSFODNN7EXAMPLE" not in result_json

        # Check that redacted markers are present
        assert "[REDACTED EMAIL]" in result_json
        assert "[REDACTED AWS_ACCOUNT_ID]" in result_json
        assert "[REDACTED PASSWORD]" in result_json
        assert "[REDACTED IP_ADDRESS]" in result_json
        assert "[REDACTED AWS_ACCESS_KEY]" in result_json

        # Check that non-sensitive data is preserved
        assert result["status"] == "success"
        assert result["message"] == "Operation completed"
        assert result["resources"][0]["name"] == "resource1"
        assert result["resources"][1]["name"] == "resource2"

    def test_secure_tool_with_aws_client_response(self, mock_config):
        """Test that secure_tool properly handles AWS client responses with PII."""
        # Create a mock AWS client response with PII
        aws_response = {
            "Users": [
                {
                    "UserName": "admin",
                    "UserId": "AIDACKCEVSQ6C2EXAMPLE",
                    "Email": "admin@example.com",
                    "CreateDate": "2019-12-31T12:00:00Z",
                },
                {
                    "UserName": "user",
                    "UserId": "AIDACKCEVSQ6C2EXAMPLE2",
                    "Email": "user@example.com",
                    "CreateDate": "2020-01-01T12:00:00Z",
                },
            ],
            "IsTruncated": False,
        }

        # Create a mock function that returns the AWS response
        mock_func = AsyncMock(return_value=aws_response)

        # Apply the secure_tool decorator
        secured_func = secure_tool(mock_config, PERMISSION_NONE, "test_tool")(mock_func)

        # Call the secured function using asyncio.run
        result = asyncio.run(secured_func())

        # Check that the function was called
        mock_func.assert_called_once()

        # Convert result to JSON string for easier searching
        result_json = json.dumps(result)

        # Check that the response was sanitized
        assert "admin@example.com" not in result_json
        assert "user@example.com" not in result_json

        # Check that redacted markers are present
        assert "[REDACTED EMAIL]" in result_json

        # Check that non-sensitive data is preserved
        assert result["Users"][0]["UserName"] == "admin"
        assert result["Users"][1]["UserName"] == "user"
        assert result["IsTruncated"] is False
