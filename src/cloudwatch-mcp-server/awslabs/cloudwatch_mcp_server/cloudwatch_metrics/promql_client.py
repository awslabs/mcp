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

import requests
import time as time_module
from awslabs.cloudwatch_mcp_server import MCP_SERVER_VERSION
from boto3 import Session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from loguru import logger
from os import getenv
from typing import Any, Dict, Optional


SERVICE_NAME = 'monitoring'
MAX_RETRIES = 3
RETRY_DELAY = 1
USER_AGENT = f'md/awslabs#mcp#cloudwatch-mcp-server#{MCP_SERVER_VERSION}'


class PromQLClient:
    """Client for CloudWatch PromQL HTTP API with SigV4 authentication."""

    @staticmethod
    def _get_base_url(region: str) -> str:
        """Get the CloudWatch PromQL base URL for a region."""
        return f'https://monitoring.{region}.amazonaws.com/api/v1'

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
