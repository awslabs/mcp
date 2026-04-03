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

"""Create Data Source operation for AWS AppSync MCP Server."""

import ipaddress
import re
from awslabs.aws_appsync_mcp_server.helpers import get_appsync_client, handle_exceptions
from typing import Any, Dict, Optional
from urllib.parse import urlparse


def _validate_service_role_arn(arn: str) -> bool:
    """Validate IAM service role ARN format."""
    arn_pattern = r'^arn:aws:iam::[0-9]{12}:role/.*$'
    return bool(re.match(arn_pattern, arn))


def _is_private_ip(ip_str: str) -> bool:
    """Check if IP address is private/internal using ipaddress module."""
    try:
        ip = ipaddress.ip_address(ip_str)
        # Treat any non-globally-routable address as private/internal, including
        # private, loopback, link-local, unspecified, reserved, multicast, etc.
        return not ip.is_global
    except ValueError:
        return False


def _validate_http_config(http_config: Dict) -> None:
    """Validate HTTP configuration for security."""
    endpoint = http_config.get('endpoint', '')

    # Require HTTPS
    if not endpoint.startswith('https://'):
        raise ValueError('HTTP endpoint must use HTTPS protocol')

    # Parse URL and extract hostname
    try:
        parsed = urlparse(endpoint)
        hostname = parsed.hostname
        if not hostname:
            raise ValueError('Invalid endpoint URL')
    except Exception:
        raise ValueError('Invalid endpoint URL')

    # Block localhost patterns
    if hostname.lower() in ('localhost', 'localhost.localdomain'):
        raise ValueError('HTTP endpoint cannot target localhost or private IP ranges')

    # Try to parse as IP address (standard IPv4/IPv6 string forms)
    if _is_private_ip(hostname):
        raise ValueError('HTTP endpoint cannot target localhost or private IP ranges')

    # Block numeric IPs in various encodings (check specific patterns before general)
    if re.match(r'^0x[0-9a-fA-F]+$', hostname):  # Hex encoding
        raise ValueError('HTTP endpoint cannot use numeric IP encoding')
    if re.match(r'^0[0-7]+$', hostname):  # Octal encoding
        raise ValueError('HTTP endpoint cannot use numeric IP encoding')
    if re.match(r'^[0-9]+$', hostname):  # Decimal encoding
        raise ValueError('HTTP endpoint cannot use numeric IP encoding')


@handle_exceptions
async def create_datasource_operation(
    api_id: str,
    name: str,
    type: str,
    description: Optional[str] = None,
    service_role_arn: Optional[str] = None,
    dynamodb_config: Optional[Dict] = None,
    lambda_config: Optional[Dict] = None,
    elasticsearch_config: Optional[Dict] = None,
    open_search_service_config: Optional[Dict] = None,
    http_config: Optional[Dict] = None,
    relational_database_config: Optional[Dict] = None,
    event_bridge_config: Optional[Dict] = None,
    metrics_config: Optional[str] = None,
) -> Dict:
    """Execute create_data_source operation."""
    # Validate service role ARN if provided
    if service_role_arn and not _validate_service_role_arn(service_role_arn):
        raise ValueError(f'Invalid service role ARN format: {service_role_arn}')

    # Validate HTTP configuration if provided
    if http_config:
        _validate_http_config(http_config)

    client = get_appsync_client()

    params: Dict[str, Any] = {'apiId': api_id, 'name': name, 'type': type}

    if description is not None:
        params['description'] = description
    if service_role_arn is not None:
        params['serviceRoleArn'] = service_role_arn
    if dynamodb_config is not None:
        params['dynamodbConfig'] = dynamodb_config
    if lambda_config is not None:
        params['lambdaConfig'] = lambda_config
    if elasticsearch_config is not None:
        params['elasticsearchConfig'] = elasticsearch_config
    if open_search_service_config is not None:
        params['openSearchServiceConfig'] = open_search_service_config
    if http_config is not None:
        params['httpConfig'] = http_config
    if relational_database_config is not None:
        params['relationalDatabaseConfig'] = relational_database_config
    if event_bridge_config is not None:
        params['eventBridgeConfig'] = event_bridge_config
    if metrics_config is not None:
        params['metricsConfig'] = metrics_config

    response = client.create_data_source(**params)
    return {'dataSource': response.get('dataSource', {})}
