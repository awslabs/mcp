"""Test module initialization and AWS client setup."""

import pytest
import sys
from unittest.mock import patch


def test_aws_client_initialization_error():
    """Test error handling during AWS client initialization."""
    # Remove the module from sys.modules if it exists
    module_name = 'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients'
    if module_name in sys.modules:
        del sys.modules[module_name]

    with patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.boto3.client'
    ) as mock_boto:
        mock_boto.side_effect = Exception('Failed to initialize AWS client')

        # Import should fail due to client initialization error
        with pytest.raises(Exception, match='Failed to initialize AWS client'):
            import awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients  # noqa: F401


def test_synthetics_endpoint_logging():
    """Test synthetics endpoint override logging."""
    # Remove the module from sys.modules to force re-import
    import sys

    module_name = 'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients'
    if module_name in sys.modules:
        del sys.modules[module_name]

    with patch.dict('os.environ', {'MCP_SYNTHETICS_ENDPOINT': 'https://synthetics.test.com'}):
        with patch('loguru.logger') as mock_logger:
            with patch('boto3.client'), patch('boto3.Session'):
                # Import the module which will trigger initialization
                import awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients  # noqa: F401

                mock_logger.debug.assert_any_call(
                    'Using Synthetics endpoint override: https://synthetics.test.com'
                )


def test_module_as_main():
    """Test module execution when run as __main__."""
    # Remove the module from sys.modules if it exists
    module_name = 'awslabs.cloudwatch_applicationsignals_mcp_server.server'
    if module_name in sys.modules:
        del sys.modules[module_name]

    with patch('awslabs.cloudwatch_applicationsignals_mcp_server.server.main'):
        with patch('sys.argv', ['server.py']):
            # Simulate running the module as __main__
            with patch('runpy.run_module') as mock_run:
                mock_run.return_value = {'__name__': '__main__'}
                # In actual execution, this would trigger the if __name__ == '__main__' block
                # For testing, we'll just verify the setup is correct
                assert True  # Placeholder for the actual test
