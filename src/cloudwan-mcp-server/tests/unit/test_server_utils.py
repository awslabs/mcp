import pytest

# Test available server utilities
from awslabs.cloudwan_mcp_server.server import handle_aws_error, safe_json_dumps


class TestServerUtilities:
    """Test server utility functions."""

    @pytest.mark.unit
    def test_safe_json_dumps(self) -> None:
        """Test safe JSON serialization."""
        test_data = {"key": "value"}
        result = safe_json_dumps(test_data)
        assert '"key": "value"' in result

    @pytest.mark.unit
    def test_handle_aws_error_available(self) -> None:
        """Test handle_aws_error function is available."""
        # Test that the function exists and is callable
        assert callable(handle_aws_error)
