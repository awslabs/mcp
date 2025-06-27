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

"""Prometheus client for making API requests with AWS SigV4 authentication."""

import boto3
import json
import logging
import requests
import time
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional

from awslabs.prometheus_mcp_server.consts import (
    DEFAULT_AWS_REGION,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    DEFAULT_SERVICE_NAME,
)

# Configure logging
logger = logging.getLogger('prometheus-mcp-server')

# Global configuration
config = {}


async def make_prometheus_request(
    method: str,
    path: str,
    base_url: Optional[str] = None,
    region: Optional[str] = None,
    profile: Optional[str] = None,
    params: Optional[Dict[str, str]] = None,
    retry_delay: Optional[int] = None,
    max_retries: Optional[int] = None,
) -> Dict[str, Any]:
    """Make a request to the Prometheus API with AWS SigV4 authentication.

    Args:
        method: HTTP method (GET, POST, etc.).
        path: API path.
        base_url: Base URL for the Prometheus API.
        region: AWS region.
        profile: AWS profile name.
        params: Query parameters.
        retry_delay: Delay between retry attempts in seconds.
        max_retries: Maximum number of retry attempts.

    Returns:
        Dict[str, Any]: Response from the Prometheus API.

    Raises:
        Exception: If the request fails after all retry attempts.
    """
    from requests_aws4auth import AWS4Auth

    # Use global config if parameters are not provided
    url = base_url or config.get('prometheus_url')
    if not url:
        raise ValueError('Prometheus URL is required')

    aws_region = region or config.get('aws_region')
    if not aws_region:
        raise ValueError('AWS region is required')

    aws_profile = profile or config.get('aws_profile')
    service_name = config.get('service_name', DEFAULT_SERVICE_NAME)
    retry_delay_seconds = retry_delay or config.get('retry_delay', DEFAULT_RETRY_DELAY)
    max_retry_attempts = max_retries or config.get('max_retries', DEFAULT_MAX_RETRIES)

    # Create AWS session
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    credentials = session.get_credentials()
    if not credentials:
        raise ValueError('No AWS credentials found')

    # Create AWS SigV4 auth
    auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        aws_region,
        service_name,
        session_token=credentials.token,
    )

    # Construct full URL
    full_url = f'{url.rstrip("/")}/{path.lstrip("/")}'

    # Make request with retries
    retries = 0
    while True:
        try:
            response = requests.request(
                method,
                full_url,
                auth=auth,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            retries += 1
            if retries > max_retry_attempts:
                raise Exception(f'Request failed after {max_retry_attempts} attempts: {e}')

            # Exponential backoff
            delay = retry_delay_seconds * (2 ** (retries - 1))
            logger.warning(f'Request failed, retrying in {delay} seconds: {e}')
            time.sleep(delay)
        except json.JSONDecodeError as e:
            raise Exception(f'Failed to parse response as JSON: {e}')


class PrometheusConnection:
    """Handles Prometheus connection testing."""

    @staticmethod
    async def test_connection(
        prometheus_url: str, region: str = DEFAULT_AWS_REGION, profile: Optional[str] = None
    ) -> bool:
        """Test the connection to Prometheus.

        Args:
            prometheus_url: The Prometheus URL to test
            region: AWS region to use
            profile: AWS profile to use

        Returns:
            bool: True if connection is successful, False otherwise
        """
        logger.info('Testing Prometheus connection...')
        try:
            # Use the make_prometheus_request function
            await make_prometheus_request(
                method='GET',
                path='label/__name__/values',
                base_url=prometheus_url,
                region=region,
                profile=profile,
                params={},
                retry_delay=DEFAULT_RETRY_DELAY,
                max_retries=DEFAULT_MAX_RETRIES,
            )
            logger.info('Successfully connected to Prometheus!')
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'AccessDeniedException':
                logger.error('ERROR: Access denied when connecting to Prometheus')
                logger.error(
                    'Please check that your AWS credentials have the following permissions:'
                )
                logger.error('  - aps:QueryMetrics')
                logger.error('  - aps:GetLabels')
                logger.error('  - aps:GetMetricMetadata')
            elif error_code == 'ResourceNotFoundException':
                logger.error('ERROR: Prometheus workspace not found')
                logger.error(
                    f'Please verify the workspace ID in your Prometheus URL: {prometheus_url}'
                )
            else:
                logger.error(f'ERROR: AWS API error when connecting to Prometheus: {error_code}')
                logger.error(f'Details: {str(e)}')
            return False
        except requests.RequestException as e:
            logger.error(f'ERROR: Network error when connecting to Prometheus: {str(e)}')
            logger.error('Please check your network connection and Prometheus URL')
            return False
        except Exception as e:
            logger.error(f'ERROR: Error connecting to Prometheus: {str(e)}')
            logger.error('Common issues:')
            logger.error('1. Incorrect Prometheus URL')
            logger.error('2. Missing or incorrect AWS region')
            logger.error('3. Invalid AWS credentials or insufficient permissions')
            return False