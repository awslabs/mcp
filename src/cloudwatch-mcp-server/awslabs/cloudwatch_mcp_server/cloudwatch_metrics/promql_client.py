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

"""SigV4-signed HTTP client for CloudWatch PromQL endpoint."""

import re
import requests
import time as time_module
from awslabs.cloudwatch_mcp_server import MCP_SERVER_VERSION
from boto3 import Session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.loaders import create_loader
from botocore.regions import EndpointResolver
from loguru import logger
from os import getenv
from typing import Any, Dict, Optional
from urllib.parse import urlsplit


SERVICE_NAME = 'monitoring'
MAX_RETRIES = 3
RETRY_DELAY = 1
USER_AGENT = f'md/awslabs#mcp#cloudwatch-mcp-server#{MCP_SERVER_VERSION}'

# First-line syntactic gate: an AWS region is lowercase alphanumeric segments
# joined by single hyphens (e.g. us-east-1, cn-north-1, us-isob-east-1,
# eusc-de-east-1). Enforcing this shape rejects URL metacharacters (/, @, ., #,
# :, whitespace, uppercase, underscores) before the value is ever used to
# resolve an endpoint, so a caller-supplied region can never break out of the
# monitoring host and redirect a SigV4-signed request to an attacker-controlled
# endpoint. It intentionally does NOT enumerate partitions -- that is left to
# botocore below, the authoritative source.
_REGION_PATTERN = re.compile(r'[a-z]{2,}(?:-[a-z0-9]+)+')

# Authoritative partition metadata from botocore (already a dependency). The
# endpoint resolver maps a region to its real, partition-correct hostname, so
# the right DNS suffix is used everywhere -- amazonaws.com (aws, aws-us-gov),
# amazonaws.com.cn (aws-cn), c2s.ic.gov / sc2s.sgov.gov / cloud.adc-e.uk /
# csp.hci.ic.gov (the ISO partitions), amazonaws.eu (aws-eusc) -- and new
# partitions/regions are picked up automatically via botocore updates rather
# than a hardcoded list. _AWS_DNS_SUFFIXES is the set of AWS-owned suffixes used
# as an independent backstop when asserting a constructed host.
_ENDPOINT_DATA = create_loader().load_data('endpoints')
_ENDPOINT_RESOLVER = EndpointResolver(_ENDPOINT_DATA)
_AWS_DNS_SUFFIXES = frozenset(p['dnsSuffix'] for p in _ENDPOINT_DATA['partitions'])


def _validate_region(region: str) -> None:
    """Reject any region that is not a well-formed AWS region token.

    Raises:
        ValueError: If region is not a syntactically valid AWS region. This runs
            before any credential retrieval, SigV4 signing, or network I/O, so a
            malicious region fails closed and no signed request is ever emitted.
    """
    if not isinstance(region, str) or not _REGION_PATTERN.fullmatch(region):
        raise ValueError(f'Invalid AWS region: {region!r}')


def _resolve_monitoring_host(region: str) -> str:
    """Resolve the partition-correct CloudWatch (monitoring) hostname for a region.

    Uses botocore's endpoint resolver so every partition gets its real DNS suffix
    (e.g. monitoring.cn-north-1.amazonaws.com.cn, monitoring.us-iso-east-1.c2s.ic.gov).

    Raises:
        ValueError: If botocore does not recognize the region (e.g. a well-formed
            but non-existent region), so an unknown region fails closed.
    """
    resolved = _ENDPOINT_RESOLVER.construct_endpoint(SERVICE_NAME, region)
    if not resolved or not resolved.get('hostname'):
        raise ValueError(f'Unknown or unsupported AWS region: {region!r}')
    return resolved['hostname']


def _assert_aws_host(url: str) -> None:
    """Assert a constructed URL targets an AWS endpoint before it is signed/sent.

    Backstop for _validate_region / _resolve_monitoring_host: even if those were
    somehow bypassed or the URL template changed, refuse to attach SigV4
    credentials to a host that is not under a known AWS-owned DNS suffix.

    Raises:
        ValueError: If the URL is not https, carries userinfo (@), uses an
            unexpected port, or its host is not under a known AWS DNS suffix.
    """
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError:
        raise ValueError(f'Invalid authority in PromQL URL: {parsed.netloc!r}')
    host = parsed.hostname
    host_ok = host is not None and any(
        host == suffix or host.endswith('.' + suffix) for suffix in _AWS_DNS_SUFFIXES
    )
    if parsed.scheme != 'https' or '@' in parsed.netloc or not host_ok or port not in (None, 443):
        raise ValueError(f'Refusing to sign request for non-AWS host: {parsed.netloc!r}')


class PromQLClient:
    """Client for CloudWatch PromQL HTTP API with SigV4 authentication."""

    @staticmethod
    def _get_base_url(region: str) -> str:
        """Get the CloudWatch PromQL base URL for a region.

        Raises:
            ValueError: If region is malformed or not a recognized AWS region.
        """
        _validate_region(region)
        hostname = _resolve_monitoring_host(region)
        base_url = f'https://{hostname}/api/v1'
        _assert_aws_host(base_url)
        return base_url

    @staticmethod
    def make_request(
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
        region: Optional[str] = None,
        profile_name: Optional[str] = None,
    ) -> Any:
        """Make a SigV4-signed request to the CloudWatch PromQL API.

        Args:
            endpoint: API endpoint path (e.g., 'query', 'query_range', 'labels')
            params: Query parameters
            region: AWS region (defaults to AWS_REGION env or us-east-1)
            profile_name: AWS profile (defaults to AWS_PROFILE env)

        Returns:
            The 'data' portion of the Prometheus-compatible JSON response

        Raises:
            ValueError: If credentials are missing or parameters are invalid
            RuntimeError: If the API returns an error status
            requests.RequestException: On network/HTTP errors
        """
        if profile_name is None:
            profile_name = getenv('AWS_PROFILE', None)
        region = region or getenv('AWS_REGION') or 'us-east-1'

        base_url = PromQLClient._get_base_url(region)
        url = f'{base_url}/{endpoint.lstrip("/")}'

        # Re-assert the fully-assembled URL (with endpoint appended) targets an
        # AWS host before entering the sign/send loop, so a bad host fails closed
        # and is never signed. Kept outside the loop below because the loop's
        # `except (requests.RequestException, ValueError)` would otherwise
        # swallow-and-retry this ValueError instead of surfacing it.
        _assert_aws_host(url)

        retry_count = 0
        last_exception: Optional[Exception] = None

        while retry_count < MAX_RETRIES:
            try:
                session = Session(profile_name=profile_name, region_name=region)
                credentials = session.get_credentials()
                if not credentials:
                    raise ValueError('AWS credentials not found')

                # Build and sign the request
                aws_request = AWSRequest(method='GET', url=url, params=params or {})
                SigV4Auth(credentials, SERVICE_NAME, region).add_auth(aws_request)

                # Send via requests
                headers = dict(aws_request.headers)
                headers['User-Agent'] = requests.utils.default_user_agent() + ' ' + USER_AGENT
                prepared = requests.Request(
                    method='GET',
                    url=aws_request.url,
                    headers=headers,
                    params=params or {},
                ).prepare()

                with requests.Session() as req_session:
                    logger.debug(
                        f'PromQL request to {url} (attempt {retry_count + 1}/{MAX_RETRIES})'
                    )
                    response = req_session.send(prepared)
                    response.raise_for_status()
                    data = response.json()

                if data.get('status') != 'success':
                    error_msg = data.get('error', 'Unknown error')
                    raise RuntimeError(f'PromQL API error: {error_msg}')

                return data['data']

            except (requests.RequestException, ValueError) as e:
                last_exception = e
                retry_count += 1
                if retry_count < MAX_RETRIES:
                    delay = RETRY_DELAY * (2 ** (retry_count - 1))
                    logger.warning(f'PromQL request failed: {e}. Retrying in {delay}s...')
                    time_module.sleep(delay)
                else:
                    logger.error(f'PromQL request failed after {MAX_RETRIES} attempts: {e}')
                    raise

        if last_exception:
            raise last_exception
        return None  # pragma: no cover
