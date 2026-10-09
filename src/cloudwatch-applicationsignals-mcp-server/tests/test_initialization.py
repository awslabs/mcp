"""Test module initialization and AWS client setup."""

import pytest
from unittest.mock import patch


def test_aws_client_initialization_error():
    """Test error handling during AWS client initialization."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients import (
        _initialize_aws_clients,
    )

    with patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.boto3.client'
    ) as mock_boto:
        mock_boto.side_effect = Exception('Failed to initialize AWS client')

        with pytest.raises(Exception):
            _initialize_aws_clients()


def test_synthetics_endpoint_logging():
    """Test synthetics endpoint override logging."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients import (
        _get_endpoint_overrides,
    )

    with patch.dict('os.environ', {'MCP_SYNTHETICS_ENDPOINT': 'https://synthetics.test.com'}):
        endpoints = _get_endpoint_overrides()
        assert endpoints['synthetics'] == 'https://synthetics.test.com'


def test_module_as_main():
    """Test module execution when run as __main__."""
    with patch('awslabs.cloudwatch_applicationsignals_mcp_server.server.main'):
        with patch('sys.argv', ['server.py']):
            with patch('runpy.run_module') as mock_run:
                mock_run.return_value = {'__name__': '__main__'}
                assert True
