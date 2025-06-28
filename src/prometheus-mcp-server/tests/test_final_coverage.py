"""Final coverage test for remaining gaps."""

import pytest
from unittest.mock import patch, MagicMock
from awslabs.prometheus_mcp_server.server import PrometheusClient


class TestFinalCoverage:
    """Cover remaining gaps."""

    @pytest.mark.asyncio
    async def test_make_request_max_retries_reached(self):
        """Test max retries exceeded."""
        with patch('boto3.Session') as mock_session, \
             patch('requests.Session') as mock_req_session, \
             patch('time.sleep'), \
             patch('awslabs.prometheus_mcp_server.server.SigV4Auth'):
            
            mock_creds = MagicMock()
            mock_creds.access_key = 'test_key'
            mock_session.return_value.get_credentials.return_value = mock_creds
            
            # All requests fail
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = Exception('Network error')
            mock_req_session.return_value.__enter__.return_value.send.return_value = mock_response
            
            with pytest.raises(Exception, match='Network error'):
                await PrometheusClient.make_request(
                    prometheus_url='https://test.com',
                    endpoint='query',
                    max_retries=2,
                    retry_delay=1
                )