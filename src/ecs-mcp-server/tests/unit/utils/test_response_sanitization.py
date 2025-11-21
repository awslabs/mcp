"""
Tests for the response sanitization framework.
"""

from awslabs.ecs_mcp_server.utils.security import ResponseSanitizer


class TestResponseSanitizer:
    """Tests for the ResponseSanitizer class."""

    def test_sanitize_string(self):
        """Test sanitizing a string."""
        # Test AWS access key
        text = "My access key is AKIAIOSFODNN7EXAMPLE"
        sanitized = ResponseSanitizer._sanitize_string(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in sanitized
        assert "[REDACTED AWS_ACCESS_KEY]" in sanitized

        # Test AWS secret key
        text = "My secret key is wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        sanitized = ResponseSanitizer._sanitize_string(text)
        assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in sanitized
        assert "[REDACTED AWS_SECRET_KEY]" in sanitized

        # Test password
        text = "password=mysecretpassword"
        sanitized = ResponseSanitizer._sanitize_string(text)
        assert "password=mysecretpassword" not in sanitized
        assert "[REDACTED PASSWORD]" in sanitized

        # Test IP address
        text = "Server IP: 192.168.1.1"
        sanitized = ResponseSanitizer._sanitize_string(text)
        assert "192.168.1.1" not in sanitized
        assert "[REDACTED IP_ADDRESS]" in sanitized

    def test_sanitize_dict(self):
        """Test sanitizing a dictionary."""
        data = {
            "status": "success",
            "message": "Operation completed",
            "access_key": "AKIAIOSFODNN7EXAMPLE",
            "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "server": {"ip": "192.168.1.1", "password": "password=mysecretpassword"},
        }

        sanitized = ResponseSanitizer.sanitize(data)

        # Check that allowed fields are preserved
        assert sanitized["status"] == "success"
        assert sanitized["message"] == "Operation completed"

        # Check that sensitive data is redacted
        assert "AKIAIOSFODNN7EXAMPLE" not in str(sanitized)
        assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in str(sanitized)
        assert "192.168.1.1" not in str(sanitized)
        assert "mysecretpassword" not in str(sanitized)

        # Check that redacted markers are present
        assert "[REDACTED AWS_ACCESS_KEY]" in str(sanitized)
        assert "[REDACTED AWS_SECRET_KEY]" in str(sanitized)
        assert "[REDACTED IP_ADDRESS]" in str(sanitized)
        assert "[REDACTED PASSWORD]" in str(sanitized)

    def test_sanitize_list(self):
        """Test sanitizing a list."""
        data = [
            "AKIAIOSFODNN7EXAMPLE",
            {"secret": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"},
            ["192.168.1.1", "password=mysecretpassword"],
        ]

        sanitized = ResponseSanitizer.sanitize(data)

        # Check that sensitive data is redacted
        assert "AKIAIOSFODNN7EXAMPLE" not in str(sanitized)
        assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in str(sanitized)
        assert "192.168.1.1" not in str(sanitized)
        assert "mysecretpassword" not in str(sanitized)

        # Check that redacted markers are present
        assert "[REDACTED AWS_ACCESS_KEY]" in str(sanitized)
        assert "[REDACTED AWS_SECRET_KEY]" in str(sanitized)
        assert "[REDACTED IP_ADDRESS]" in str(sanitized)
        assert "[REDACTED PASSWORD]" in str(sanitized)

    def test_add_public_endpoint_warning(self):
        """Test adding warnings for public endpoints."""
        # Test with ALB URL
        data = {
            "status": "success",
            "alb_url": "http://my-app-123456789.us-east-1.elb.amazonaws.com",
        }

        result = ResponseSanitizer.add_public_endpoint_warning(data)

        # Check that warning is added
        assert "warnings" in result
        assert isinstance(result["warnings"], list)
        assert any("publicly accessible" in warning for warning in result["warnings"])

        # Test without ALB URL
        data = {"status": "success", "message": "Operation completed"}

        result = ResponseSanitizer.add_public_endpoint_warning(data)

        # Check that no warning is added
        assert "warnings" not in result or not any(
            "publicly accessible" in warning for warning in result.get("warnings", [])
        )

        # Test with existing warnings
        data = {
            "status": "success",
            "alb_url": "http://my-app-123456789.us-east-1.elb.amazonaws.com",
            "warnings": ["Existing warning"],
        }

        result = ResponseSanitizer.add_public_endpoint_warning(data)

        # Check that warning is added to existing warnings
        assert "warnings" in result
        assert isinstance(result["warnings"], list)
        assert len(result["warnings"]) == 2
        assert "Existing warning" in result["warnings"]
        assert any("publicly accessible" in warning for warning in result["warnings"])

    def test_context_aware_exemption_build_and_push_tool(self):
        """Test that exempt fields are not sanitized for build_and_push_image_to_ecr tool."""
        data = {
            "repository_uri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
            "image_tag": "1700000000",
            "full_image_uri": (
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo:1700000000"
            ),
            "status": "success",
        }

        # Sanitize with tool_name="build_and_push_image_to_ecr"
        sanitized = ResponseSanitizer.sanitize(data, tool_name="build_and_push_image_to_ecr")

        # Exempt fields should NOT be sanitized
        assert (
            sanitized["repository_uri"]
            == "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo"
        )
        assert sanitized["image_tag"] == "1700000000"
        assert (
            sanitized["full_image_uri"]
            == "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo:1700000000"
        )
        assert sanitized["status"] == "success"

        # AWS account ID should NOT be redacted in exempt fields
        assert "123456789012" in sanitized["repository_uri"]
        assert "123456789012" in sanitized["full_image_uri"]
        assert "[REDACTED" not in sanitized["repository_uri"]
        assert "[REDACTED" not in sanitized["full_image_uri"]

    def test_context_aware_exemption_without_tool_name(self):
        """Test that fields are sanitized when no tool_name is provided."""
        data = {
            "repository_uri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
            "image_tag": "1700000000",
            "full_image_uri": (
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo:1700000000"
            ),
            "status": "success",
        }

        # Sanitize without tool_name
        sanitized = ResponseSanitizer.sanitize(data)

        # AWS account IDs should be redacted
        assert "123456789012" not in str(sanitized["repository_uri"])
        assert "123456789012" not in str(sanitized["full_image_uri"])
        assert "[REDACTED AWS_ACCOUNT_ID]" in sanitized["repository_uri"]
        assert "[REDACTED AWS_ACCOUNT_ID]" in sanitized["full_image_uri"]

        # Phone pattern (epoch timestamp) should be redacted
        assert "1700000000" not in sanitized["image_tag"]
        assert "[REDACTED PHONE]" in sanitized["image_tag"]

    def test_context_aware_exemption_wrong_tool(self):
        """Test that fields are sanitized when tool_name doesn't match."""
        data = {
            "repository_uri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
            "image_tag": "1700000000",
            "full_image_uri": (
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo:1700000000"
            ),
            "status": "success",
        }

        # Sanitize with different tool_name
        sanitized = ResponseSanitizer.sanitize(data, tool_name="some_other_tool")

        # AWS account IDs should be redacted for non-exempt tools
        assert "123456789012" not in str(sanitized["repository_uri"])
        assert "123456789012" not in str(sanitized["full_image_uri"])
        assert "[REDACTED AWS_ACCOUNT_ID]" in sanitized["repository_uri"]

    def test_context_aware_exemption_nested_data(self):
        """Test that exemptions work with nested data structures."""
        data = {
            "status": "success",
            "result": {
                "repository_uri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
                "image_tag": "1700000000",
                "nested": {
                    "full_image_uri": (
                        "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo:1700000000"
                    )
                },
            },
        }

        # Sanitize with build_and_push_image_to_ecr tool
        sanitized = ResponseSanitizer.sanitize(data, tool_name="build_and_push_image_to_ecr")

        # Top-level exempt fields should be preserved
        assert "123456789012" in sanitized["result"]["repository_uri"]
        assert "1700000000" == sanitized["result"]["image_tag"]

        # Nested exempt fields should also be preserved
        assert "123456789012" in sanitized["result"]["nested"]["full_image_uri"]

    def test_context_aware_exemption_only_specified_fields(self):
        """Test that only specified fields are exempt, not all fields."""
        data = {
            "repository_uri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
            "image_tag": "1700000000",
            "some_other_field": "Account ID is 123456789012 and timestamp 1700000000",
        }

        # Sanitize with build_and_push_image_to_ecr tool
        sanitized = ResponseSanitizer.sanitize(data, tool_name="build_and_push_image_to_ecr")

        # Exempt fields should NOT be sanitized
        assert "123456789012" in sanitized["repository_uri"]
        assert "1700000000" == sanitized["image_tag"]

        # Non-exempt fields SHOULD be sanitized
        assert "123456789012" not in sanitized["some_other_field"]
        assert "[REDACTED AWS_ACCOUNT_ID]" in sanitized["some_other_field"]
        assert "1700000000" not in sanitized["some_other_field"]
        assert "[REDACTED PHONE]" in sanitized["some_other_field"]
