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
