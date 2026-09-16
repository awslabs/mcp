# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for the PromQL client."""

import pytest
import requests
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client import (
    PromQLClient,
    _assert_aws_host,
    _validate_region,
)
from unittest.mock import MagicMock, patch


class TestPromQLClient:
    """Tests for PromQLClient."""

    def test_get_base_url(self):
        """Test base URL construction."""
        assert (
            PromQLClient._get_base_url('us-east-1')
            == 'https://monitoring.us-east-1.amazonaws.com/api/v1'
        )
        assert (
            PromQLClient._get_base_url('eu-west-1')
            == 'https://monitoring.eu-west-1.amazonaws.com/api/v1'
        )

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.SigV4Auth')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.requests.Session')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.Session')
    def test_make_request_success(self, mock_boto_session, mock_req_session, mock_sigv4):
        """Test successful request."""
        # Setup boto3 session mock
        mock_creds = MagicMock()
        mock_boto_session.return_value.get_credentials.return_value = mock_creds

        # Setup requests mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'success',
            'data': {'resultType': 'vector', 'result': []},
        }
        mock_response.raise_for_status = MagicMock()
        mock_req_session.return_value.__enter__.return_value.send.return_value = mock_response

        result = PromQLClient.make_request(
            endpoint='query',
            params={'query': 'up'},
            region='us-east-1',
        )

        assert result == {'resultType': 'vector', 'result': []}

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.SigV4Auth')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.requests.Session')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.Session')
    def test_make_request_api_error(self, mock_boto_session, mock_req_session, mock_sigv4):
        """Test API error response raises RuntimeError."""
        mock_creds = MagicMock()
        mock_boto_session.return_value.get_credentials.return_value = mock_creds

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'error',
            'error': 'bad query syntax',
        }
        mock_response.raise_for_status = MagicMock()
        mock_req_session.return_value.__enter__.return_value.send.return_value = mock_response

        with pytest.raises(RuntimeError, match='PromQL API error: bad query syntax'):
            PromQLClient.make_request(
                endpoint='query',
                params={'query': 'invalid{'},
                region='us-east-1',
            )

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.Session')
    def test_make_request_no_credentials(self, mock_boto_session):
        """Test missing credentials raises ValueError."""
        mock_boto_session.return_value.get_credentials.return_value = None

        with pytest.raises(ValueError, match='AWS credentials not found'):
            PromQLClient.make_request(
                endpoint='query',
                params={'query': 'up'},
                region='us-east-1',
            )

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.SigV4Auth')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.time_module.sleep')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.requests.Session')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.Session')
    def test_make_request_retry_on_network_error(
        self, mock_boto_session, mock_req_session, mock_sleep, mock_sigv4
    ):
        """Test retry logic on network errors."""
        mock_creds = MagicMock()
        mock_boto_session.return_value.get_credentials.return_value = mock_creds

        mock_req_session.return_value.__enter__.return_value.send.side_effect = (
            requests.ConnectionError('Connection refused')
        )

        with pytest.raises(requests.ConnectionError):
            PromQLClient.make_request(
                endpoint='query',
                params={'query': 'up'},
                region='us-east-1',
            )

        # Should have retried (sleep called MAX_RETRIES - 1 times)
        assert mock_sleep.call_count == 2

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.SigV4Auth')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.requests.Session')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.Session')
    def test_make_request_uses_profile(self, mock_boto_session, mock_req_session, mock_sigv4):
        """Test that profile_name is passed to boto3 Session."""
        mock_creds = MagicMock()
        mock_boto_session.return_value.get_credentials.return_value = mock_creds

        mock_response = MagicMock()
        mock_response.json.return_value = {'status': 'success', 'data': []}
        mock_response.raise_for_status = MagicMock()
        mock_req_session.return_value.__enter__.return_value.send.return_value = mock_response

        PromQLClient.make_request(
            endpoint='labels',
            params={},
            region='us-west-2',
            profile_name='my-profile',
        )

        mock_boto_session.assert_called_with(profile_name='my-profile', region_name='us-west-2')

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.SigV4Auth')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.time_module.sleep')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.requests.Session')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.Session')
    def test_make_request_retry_then_success(
        self, mock_boto_session, mock_req_session, mock_sleep, mock_sigv4
    ):
        """Test retry succeeds on second attempt."""
        mock_creds = MagicMock()
        mock_boto_session.return_value.get_credentials.return_value = mock_creds

        mock_response_ok = MagicMock()
        mock_response_ok.json.return_value = {'status': 'success', 'data': ['metric1']}
        mock_response_ok.raise_for_status = MagicMock()

        mock_req_session.return_value.__enter__.return_value.send.side_effect = [
            requests.ConnectionError('timeout'),
            mock_response_ok,
        ]

        result = PromQLClient.make_request(
            endpoint='labels',
            params={},
            region='us-east-1',
        )

        assert result == ['metric1']
        assert mock_sleep.call_count == 1


# Well-formed AWS regions spanning every partition, mapped to the
# partition-correct PromQL base URL. The DNS suffix differs by partition
# (amazonaws.com for aws/aws-us-gov, amazonaws.com.cn for China, and the ISO
# partitions' own suffixes), so these lock in that the endpoint builder is
# partition-aware and never assumes .amazonaws.com.
PARTITION_BASE_URLS = {
    'us-east-1': 'https://monitoring.us-east-1.amazonaws.com/api/v1',
    'eu-west-3': 'https://monitoring.eu-west-3.amazonaws.com/api/v1',
    'ap-southeast-5': 'https://monitoring.ap-southeast-5.amazonaws.com/api/v1',
    'mx-central-1': 'https://monitoring.mx-central-1.amazonaws.com/api/v1',
    'us-gov-west-1': 'https://monitoring.us-gov-west-1.amazonaws.com/api/v1',
    'us-gov-east-1': 'https://monitoring.us-gov-east-1.amazonaws.com/api/v1',
    'cn-north-1': 'https://monitoring.cn-north-1.amazonaws.com.cn/api/v1',
    'cn-northwest-1': 'https://monitoring.cn-northwest-1.amazonaws.com.cn/api/v1',
    'us-iso-east-1': 'https://monitoring.us-iso-east-1.c2s.ic.gov/api/v1',
    'us-isob-east-1': 'https://monitoring.us-isob-east-1.sc2s.sgov.gov/api/v1',
    'eu-isoe-west-1': 'https://monitoring.eu-isoe-west-1.cloud.adc-e.uk/api/v1',
    'us-isof-south-1': 'https://monitoring.us-isof-south-1.csp.hci.ic.gov/api/v1',
    'eusc-de-east-1': 'https://monitoring.eusc-de-east-1.amazonaws.eu/api/v1',
}

# Malformed / malicious region values that must be rejected. Several would
# otherwise break out of the monitoring host and cause a SigV4-signed request
# (carrying the server's AWS credentials) to be sent to an attacker-controlled
# endpoint (SOCCRE-24621).
MALICIOUS_REGIONS = [
    'evil.com/',
    'x.attacker.com/',
    'us-east-1/',
    'us-east-1/../..',
    'us-east-1.evil.com',
    'us-east-1@evil.com',
    '@evil.com',
    'US-EAST-1',
    '169.254.169.254',
    'monitoring.evil.com',
    'us-east-1#x',
    'us-east-1:443',
    'us-east-1\n',
    'localhost',
    'us_east_1',
    '',
]


class TestPromQLClientRegionValidation:
    """Region validation / SSRF guard tests for PromQLClient (SOCCRE-24621)."""

    @pytest.mark.parametrize('region', list(PARTITION_BASE_URLS))
    def test_get_base_url_is_partition_aware(self, region):
        """Regions across every AWS partition build the partition-correct URL."""
        assert PromQLClient._get_base_url(region) == PARTITION_BASE_URLS[region]

    def test_get_base_url_rejects_region_in_no_known_partition(self):
        """A region whose prefix matches no AWS partition is rejected.

        A region that DOES match a partition regex (e.g. a not-yet-launched
        region in an existing geo like ``us-east-999``) is intentionally accepted
        so newly launched regions work before botocore is updated. Such a name
        still yields an AWS-owned host under the correct partition suffix (the
        SSRF guard holds) and merely fails to resolve at DNS.
        """
        with pytest.raises(ValueError):
            PromQLClient._get_base_url('zz-zzz-9')

    def test_get_base_url_accepts_regex_matched_region_in_known_geo(self):
        """Regions matching a partition regex are accepted (forward-compat).

        They still build an AWS-owned host under that partition's suffix.
        """
        assert (
            PromQLClient._get_base_url('us-east-999')
            == 'https://monitoring.us-east-999.amazonaws.com/api/v1'
        )

    @pytest.mark.parametrize('region', MALICIOUS_REGIONS)
    def test_get_base_url_rejects_malicious_region(self, region):
        """Malformed/malicious regions raise ValueError before URL construction."""
        with pytest.raises(ValueError):
            PromQLClient._get_base_url(region)

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.SigV4Auth')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.requests.Session')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.Session')
    @pytest.mark.parametrize('region', [r for r in MALICIOUS_REGIONS if r] + ['zz-zzz-9'])
    def test_make_request_rejects_region_before_signing(
        self, mock_boto_session, mock_req_session, mock_sigv4, region
    ):
        """A rejected region fails closed before any credential/sign/network op.

        Proves the ValueError is raised before boto3 Session creation, SigV4
        signing, and the HTTP send — so no signed credential material is ever
        emitted — and that it is not swallowed by the retry loop. The empty
        string is excluded here because make_request defaults a falsy region to
        AWS_REGION/us-east-1 before validation (still covered by _get_base_url).
        """
        with pytest.raises(ValueError):
            PromQLClient.make_request(
                endpoint='query',
                params={'query': 'up'},
                region=region,
            )

        mock_boto_session.assert_not_called()
        mock_sigv4.assert_not_called()
        mock_req_session.assert_not_called()


class TestPromQLHostAssertion:
    """Direct tests for the _assert_aws_host backstop and _validate_region edges."""

    @pytest.mark.parametrize(
        'url',
        [
            'http://monitoring.us-east-1.amazonaws.com/api/v1',  # not https
            'https://monitoring.us-east-1.amazonaws.com@evil.com/api/v1',  # userinfo (@)
            'https://evil.com/api/v1',  # host not under a known AWS suffix
            'https://monitoring.evilamazonaws.com/api/v1',  # suffix not preceded by a dot
            'https://monitoring.us-east-1.amazonaws.com:8443/api/v1',  # unexpected port
        ],
    )
    def test_assert_aws_host_rejects_non_aws(self, url):
        """The backstop refuses to sign a request to a non-AWS/altered host."""
        with pytest.raises(ValueError, match='non-AWS host'):
            _assert_aws_host(url)

    def test_assert_aws_host_rejects_malformed_authority(self):
        """A malformed port makes urlsplit().port raise, which is caught and re-raised."""
        with pytest.raises(ValueError, match='Invalid authority'):
            _assert_aws_host('https://monitoring.us-east-1.amazonaws.com:notaport/api/v1')

    @pytest.mark.parametrize(
        'url',
        [
            'https://monitoring.us-east-1.amazonaws.com/api/v1',
            'https://monitoring.us-east-1.amazonaws.com:443/api/v1',  # explicit standard port
            'https://monitoring.cn-north-1.amazonaws.com.cn/api/v1',  # China suffix
            'https://monitoring.us-iso-east-1.c2s.ic.gov/api/v1',  # ISO suffix
        ],
    )
    def test_assert_aws_host_accepts_known_aws_hosts(self, url):
        """Legitimate per-partition AWS hosts pass the assertion (no raise)."""
        _assert_aws_host(url)

    def test_validate_region_rejects_non_string(self):
        """A non-string region is rejected without a regex match attempt."""
        with pytest.raises(ValueError):
            _validate_region(None)  # type: ignore[arg-type]
