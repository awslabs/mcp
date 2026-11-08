"""Final coverage test for remaining gaps."""

import pytest
import requests
from awslabs.prometheus_mcp_server.server import PrometheusClient
from unittest.mock import MagicMock, patch


class TestFinalCoverage:
    """Cover remaining gaps."""

    @pytest.mark.asyncio
    async def test_make_request_max_retries_reached(self):
        """Test max retries exceeded."""
        with (
            patch('boto3.Session') as mock_session,
            patch('requests.Session') as mock_req_session,
            patch('asyncio.sleep'),
            patch('awslabs.prometheus_mcp_server.server.SigV4Auth'),
        ):
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
                    retry_delay=1,
                )

    @pytest.mark.asyncio
    @pytest.mark.parametrize('status_code', [400, 422])
    async def test_make_request_bad_request_not_retried(self, status_code):
        """A 400/422 with a Prometheus error body raises RuntimeError after one request."""
        with (
            patch('boto3.Session') as mock_session,
            patch('requests.Session') as mock_req_session,
            patch('awslabs.prometheus_mcp_server.server.SigV4Auth'),
        ):
            mock_session.return_value.get_credentials.return_value = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = status_code
            mock_response.raise_for_status.side_effect = requests.HTTPError(
                f'{status_code} Client Error'
            )
            mock_response.json.return_value = {
                'status': 'error',
                'errorType': 'bad_data',
                'error': "1:5: parse error: unexpected right parenthesis ')'",
            }
            send = mock_req_session.return_value.__enter__.return_value.send
            send.return_value = mock_response

            with pytest.raises(RuntimeError, match='1:5: parse error'):
                await PrometheusClient.make_request(
                    prometheus_url='https://test.com', endpoint='query', max_retries=3
                )
            assert send.call_count == 1
