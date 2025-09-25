"""
Additional pytest-style unit tests for security utilities to achieve 100% coverage.
"""

from unittest.mock import AsyncMock, patch

import pytest

from awslabs.ecs_mcp_server.utils.security import (
    PERMISSION_NONE,
    PERMISSION_SENSITIVE_DATA,
    PERMISSION_WRITE,
    SecurityError,
    check_permission,
    secure_tool,
)


class TestCheckPermission:
    """Tests for check_permission function."""

    def test_permission_write_allowed(self):
        """Test that write permission is allowed when configured."""
        config = {"allow-write": True}
        assert check_permission(config, PERMISSION_WRITE) is True

    def test_permission_write_denied(self):
        """Test that write permission is denied when not configured."""
        config = {"allow-write": False}
        with pytest.raises(SecurityError) as excinfo:
            check_permission(config, PERMISSION_WRITE)
        assert "Write operations are disabled" in str(excinfo.value)

        # Test with missing config key
        config = {}
        with pytest.raises(SecurityError) as excinfo:
            check_permission(config, PERMISSION_WRITE)
        assert "Write operations are disabled" in str(excinfo.value)

    def test_permission_sensitive_data_allowed(self):
        """Test that sensitive data permission is allowed when configured."""
        config = {"allow-sensitive-data": True}
        assert check_permission(config, PERMISSION_SENSITIVE_DATA) is True

    def test_permission_sensitive_data_denied(self):
        """Test that sensitive data permission is denied when not configured."""
        config = {"allow-sensitive-data": False}
        with pytest.raises(SecurityError) as excinfo:
            check_permission(config, PERMISSION_SENSITIVE_DATA)
        assert "Access to sensitive data is not allowed" in str(excinfo.value)

        # Test with missing config key
        config = {}
        with pytest.raises(SecurityError) as excinfo:
            check_permission(config, PERMISSION_SENSITIVE_DATA)
        assert "Access to sensitive data is not allowed" in str(excinfo.value)

    def test_permission_none(self):
        """Test that no permission check always passes."""
        config = {}
        assert check_permission(config, PERMISSION_NONE) is True


class TestSecureTool:
    """Tests for secure_tool decorator."""

    @pytest.mark.anyio
    async def test_secure_tool_allowed(self):
        """Test that secure_tool allows execution when permission is granted."""
        # Create a mock async function
        mock_func = AsyncMock(return_value={"status": "success"})

        # Create a config that allows the permission
        config = {"allow-write": True}

        # Apply the decorator
        decorated_func = secure_tool(config, PERMISSION_WRITE)(mock_func)

        # Call the decorated function
        result = await decorated_func(arg1="value1", arg2="value2")

        # Verify the original function was called with the correct arguments
        mock_func.assert_called_once_with(arg1="value1", arg2="value2")

        # Verify the result is the same as the original function's return value
        assert result == {"status": "success"}

    @pytest.mark.anyio
    async def test_secure_tool_denied(self):
        """Test that secure_tool denies execution when permission is not granted."""
        # Create a mock async function
        mock_func = AsyncMock(return_value={"status": "success"})

        # Create a config that denies the permission
        config = {"allow-write": False}

        # Apply the decorator
        decorated_func = secure_tool(config, PERMISSION_WRITE)(mock_func)

        # Call the decorated function
        result = await decorated_func(arg1="value1", arg2="value2")

        # Verify the original function was not called
        mock_func.assert_not_called()

        # Verify the result contains the error information
        assert "error" in result
        assert "status" in result
        assert result["status"] == "failed"
        assert "message" in result
        assert "Security validation failed" in result["message"]

    @pytest.mark.anyio
    async def test_secure_tool_with_tool_name(self):
        """Test that secure_tool uses the provided tool name in logs."""
        # Create a mock async function
        mock_func = AsyncMock(return_value={"status": "success"})

        # Create a config that denies the permission
        config = {"allow-write": False}

        # Apply the decorator with a custom tool name
        decorated_func = secure_tool(config, PERMISSION_WRITE, tool_name="custom_tool_name")(
            mock_func
        )

        # Call the decorated function
        with patch("awslabs.ecs_mcp_server.utils.security.logger") as mock_logger:
            await decorated_func(arg1="value1", arg2="value2")

            # Verify the logger was called with the custom tool name
            mock_logger.warning.assert_called_once()
            log_message = mock_logger.warning.call_args[0][0]
            assert "custom_tool_name" in log_message
