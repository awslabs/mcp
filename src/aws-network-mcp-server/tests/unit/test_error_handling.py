import pytest
from awslabs.aws_network_mcp_server.utils import exceptions

class TestErrorHandling:
    """Validate error handling standardization across all tools."""
    
    ERROR_SCENARIOS = [
        ("invalid_id_format", exceptions.ValidationError),
        ("nonexistent_resource", exceptions.ResourceNotFoundError),
        ("unauthorized_access", exceptions.NetworkResourceError)
    ]
    
    @pytest.mark.parametrize("scenario,expected_error", ERROR_SCENARIOS)
    def test_standard_error_messages(self, mcp_test_client, scenario, expected_error):
        """Verify consistent error message structure across all tools."""
        for tool_name in mcp_test_client.list_tools():
            with pytest.raises(expected_error) as exc_info:
                mcp_test_client.execute_tool(tool_name, {scenario: True})
                
            assert 'could not be accessed' in str(exc_info.value)
            assert 'Error:' in str(exc_info.value)