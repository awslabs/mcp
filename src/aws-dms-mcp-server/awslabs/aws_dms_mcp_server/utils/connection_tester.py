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

"""Connection Tester.

Handles connection testing between replication instances and endpoints.
"""

import time
from .dms_client import DMSClient
from datetime import datetime, timedelta
from loguru import logger
from typing import Any, Dict, List, Optional


class ConnectionTester:
    """Manager for connection testing operations."""

    def __init__(self, client: DMSClient, enable_caching: bool = True):
        """Initialize connection tester.

        Args:
            client: DMS client wrapper
            enable_caching: Enable connection test result caching
        """
        self.client = client
        self.enable_caching = enable_caching
        self._cache: Dict[str, Dict[str, Any]] = {}
        logger.debug('Initialized ConnectionTester', caching=enable_caching)

    def test_connection(self, instance_arn: str, endpoint_arn: str) -> Dict[str, Any]:
        """Test connectivity between replication instance and endpoint.

        Args:
            instance_arn: Replication instance ARN
            endpoint_arn: Endpoint ARN

        Returns:
            Connection test results
        """
        logger.info('Testing connection', instance=instance_arn, endpoint=endpoint_arn)

        # Check cache
        cache_key = f'{instance_arn}:{endpoint_arn}'
        if self.enable_caching and cache_key in self._cache:
            cached_result = self._cache[cache_key]
            # Check if cache is still valid (5 minutes)
            cache_time = cached_result.get('_cached_at', datetime.utcnow())
            if datetime.utcnow() - cache_time < timedelta(minutes=5):
                logger.debug('Returning cached connection test result')
                # Remove internal cache timestamp before returning
                result = {k: v for k, v in cached_result.items() if k != '_cached_at'}
                return result

        # Initiate connection test
        response = self.client.call_api(
            'test_connection', ReplicationInstanceArn=instance_arn, EndpointArn=endpoint_arn
        )

        connection = response.get('Connection', {})

        # Poll for test completion (max 60 seconds)
        max_attempts = 12
        attempt = 0
        status = connection.get('Status', 'testing')

        while status == 'testing' and attempt < max_attempts:
            time.sleep(5)
            attempt += 1

            # Check connection status
            connections_response = self.client.call_api(
                'describe_connections',
                Filters=[
                    {'Name': 'endpoint-arn', 'Values': [endpoint_arn]},
                    {'Name': 'replication-instance-arn', 'Values': [instance_arn]},
                ],
            )

            connections = connections_response.get('Connections', [])
            if connections:
                connection = connections[0]
                status = connection.get('Status', 'testing')
                logger.debug(f'Connection test status: {status}', attempt=attempt)

        # Format result
        result = {
            'success': status == 'successful',
            'data': {
                'status': status,
                'replication_instance_arn': instance_arn,
                'endpoint_arn': endpoint_arn,
                'last_failure_message': connection.get('LastFailureMessage'),
                'endpoint_identifier': connection.get('EndpointIdentifier'),
                'replication_instance_identifier': connection.get('ReplicationInstanceIdentifier'),
            },
            'error': None,
        }

        if status != 'successful':
            result['error'] = {
                'message': connection.get('LastFailureMessage', 'Connection test failed'),
                'code': 'ConnectionTestFailed',
            }

        # Cache result if caching enabled
        if self.enable_caching:
            cached_result = result.copy()
            cached_result['_cached_at'] = datetime.utcnow()
            self._cache[cache_key] = cached_result
            logger.debug('Cached connection test result')

        logger.info(f'Connection test completed with status: {status}')
        return result

    def list_connection_tests(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List existing connection test results.

        Args:
            filters: Optional filters (by status, endpoint, etc.)
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            Dictionary with connection test results
        """
        logger.info('Listing connection tests', filters=filters)

        # Build API parameters
        params: Dict[str, Any] = {'MaxRecords': max_results}

        if filters:
            params['Filters'] = filters

        if marker:
            params['Marker'] = marker

        # Call API
        response = self.client.call_api('describe_connections', **params)

        # Format connections
        connections = response.get('Connections', [])
        formatted_connections = [
            {
                'endpoint_arn': conn.get('EndpointArn'),
                'endpoint_identifier': conn.get('EndpointIdentifier'),
                'replication_instance_arn': conn.get('ReplicationInstanceArn'),
                'replication_instance_identifier': conn.get('ReplicationInstanceIdentifier'),
                'status': conn.get('Status'),
                'last_failure_message': conn.get('LastFailureMessage'),
            }
            for conn in connections
        ]

        result = {
            'success': True,
            'data': {'connections': formatted_connections, 'count': len(formatted_connections)},
            'error': None,
        }

        # Add pagination info
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        logger.info(f'Retrieved {len(formatted_connections)} connection tests')
        return result

    def delete_connection(
        self, endpoint_arn: str, replication_instance_arn: str
    ) -> Dict[str, Any]:
        """Delete a connection between a replication instance and endpoint.

        Args:
            endpoint_arn: Endpoint ARN
            replication_instance_arn: Replication instance ARN

        Returns:
            Connection deletion result
        """
        logger.info(
            'Deleting connection', endpoint=endpoint_arn, instance=replication_instance_arn
        )

        # Call API
        response = self.client.call_api(
            'delete_connection',
            EndpointArn=endpoint_arn,
            ReplicationInstanceArn=replication_instance_arn,
        )

        connection = response.get('Connection', {})

        # Clear from cache if present
        cache_key = f'{replication_instance_arn}:{endpoint_arn}'
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.debug('Removed connection from cache')

        result = {
            'success': True,
            'data': {'connection': connection, 'message': 'Connection deleted successfully'},
            'error': None,
        }

        logger.info('Connection deleted successfully')
        return result

    def clear_cache(self) -> None:
        """Clear the connection test result cache."""
        logger.info('Clearing connection test cache', cached_items=len(self._cache))
        self._cache.clear()


# TODO: Add automatic cache expiration
# TODO: Add connection test retry logic
# TODO: Add connection health monitoring
