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

"""Endpoint Manager.

Handles business logic for AWS DMS endpoint operations.
"""

from ..exceptions import DMSInvalidParameterException
from .dms_client import DMSClient
from .response_formatter import ResponseFormatter
from loguru import logger
from typing import Any, Dict, List, Optional, Tuple


class EndpointManager:
    """Manager for endpoint operations."""

    def __init__(self, client: DMSClient):
        """Initialize endpoint manager.

        Args:
            client: DMS client wrapper
        """
        self.client = client
        logger.debug('Initialized EndpointManager')

    def list_endpoints(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List endpoints with optional filtering.

        Args:
            filters: Optional filters for endpoint selection
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            Dictionary with endpoints list
        """
        logger.info('Listing endpoints', filters=filters)

        # Build API parameters
        params: Dict[str, Any] = {'MaxRecords': max_results}

        if filters:
            params['Filters'] = filters

        if marker:
            params['Marker'] = marker

        # Call API
        response = self.client.call_api('describe_endpoints', **params)

        # Format endpoints
        endpoints = response.get('Endpoints', [])
        formatted_endpoints = [
            ResponseFormatter.format_endpoint(endpoint) for endpoint in endpoints
        ]

        result = {
            'success': True,
            'data': {'endpoints': formatted_endpoints, 'count': len(formatted_endpoints)},
            'error': None,
        }

        # Add pagination info
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        logger.info(f'Retrieved {len(formatted_endpoints)} endpoints')
        return result

    def create_endpoint(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new database endpoint.

        Args:
            params: Endpoint creation parameters

        Returns:
            Created endpoint details
        """
        identifier = params.get('EndpointIdentifier', 'unknown')
        logger.info('Creating endpoint', identifier=identifier)

        # Validate required parameters
        required_params = [
            'EndpointIdentifier',
            'EndpointType',
            'EngineName',
            'ServerName',
            'Port',
            'DatabaseName',
            'Username',
        ]
        for param in required_params:
            if param not in params:
                raise DMSInvalidParameterException(
                    message=f'Missing required parameter: {param}',
                    details={'missing_param': param},
                )

        # Validate endpoint configuration
        is_valid, error_msg = self.validate_endpoint_config(params)
        if not is_valid:
            raise DMSInvalidParameterException(
                message=f'Invalid endpoint configuration: {error_msg}',
                details={'validation_error': error_msg},
            )

        # Mask password in logs
        safe_params = {k: v if k != 'Password' else '***MASKED***' for k, v in params.items()}
        logger.debug('Creating endpoint with params', params=safe_params)

        # Call API
        response = self.client.call_api('create_endpoint', **params)

        # Format response
        endpoint = response.get('Endpoint', {})
        formatted_endpoint = ResponseFormatter.format_endpoint(endpoint)

        result = {
            'success': True,
            'data': {
                'endpoint': formatted_endpoint,
                'message': 'Endpoint created successfully',
                'security_note': 'Password is stored securely in AWS DMS',
            },
            'error': None,
        }

        logger.info(f'Created endpoint: {formatted_endpoint.get("identifier")}')
        return result

    def validate_endpoint_config(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate endpoint configuration.

        Args:
            config: Endpoint configuration

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate endpoint type
        endpoint_type = config.get('EndpointType', '')
        if endpoint_type not in ['source', 'target']:
            return False, f"Invalid endpoint type: {endpoint_type}. Must be 'source' or 'target'"

        # Validate engine name
        engine = config.get('EngineName', '').lower()
        supported_engines = [
            'mysql',
            'postgres',
            'postgresql',
            'oracle',
            'sqlserver',
            'mariadb',
            'aurora',
            'aurora-postgresql',
            'redshift',
            's3',
            'dynamodb',
            'mongodb',
            'sybase',
            'db2',
            'azuredb',
        ]
        if engine not in supported_engines:
            return False, f'Unsupported engine: {engine}'

        # Validate port range
        port = config.get('Port')
        if port and (port < 1 or port > 65535):
            return False, f'Invalid port: {port}. Must be between 1 and 65535'

        # Validate SSL mode
        ssl_mode = config.get('SslMode', 'none')
        valid_ssl_modes = ['none', 'require', 'verify-ca', 'verify-full']
        if ssl_mode not in valid_ssl_modes:
            return False, f'Invalid SSL mode: {ssl_mode}. Must be one of {valid_ssl_modes}'

        # Engine-specific validation
        default_ports = self.get_engine_settings(engine).get('default_port')
        if port and default_ports and port != default_ports:
            logger.warning(
                f'Non-standard port {port} for engine {engine} (default: {default_ports})'
            )

        return True, ''

    def get_engine_settings(self, engine: str) -> Dict[str, Any]:
        """Get default settings for a database engine.

        Args:
            engine: Database engine name

        Returns:
            Engine-specific default settings
        """
        engine = engine.lower()

        engine_defaults = {
            'mysql': {'default_port': 3306, 'ssl_supported': True, 'requires_server_name': True},
            'mariadb': {'default_port': 3306, 'ssl_supported': True, 'requires_server_name': True},
            'postgres': {
                'default_port': 5432,
                'ssl_supported': True,
                'requires_server_name': True,
            },
            'postgresql': {
                'default_port': 5432,
                'ssl_supported': True,
                'requires_server_name': True,
            },
            'oracle': {'default_port': 1521, 'ssl_supported': True, 'requires_server_name': True},
            'sqlserver': {
                'default_port': 1433,
                'ssl_supported': True,
                'requires_server_name': True,
            },
            'aurora': {'default_port': 3306, 'ssl_supported': True, 'requires_server_name': True},
            'aurora-postgresql': {
                'default_port': 5432,
                'ssl_supported': True,
                'requires_server_name': True,
            },
            'redshift': {
                'default_port': 5439,
                'ssl_supported': True,
                'requires_server_name': True,
            },
            's3': {'default_port': None, 'ssl_supported': True, 'requires_server_name': False},
            'dynamodb': {
                'default_port': None,
                'ssl_supported': True,
                'requires_server_name': False,
            },
            'mongodb': {
                'default_port': 27017,
                'ssl_supported': True,
                'requires_server_name': True,
            },
        }

        return engine_defaults.get(
            engine, {'default_port': None, 'ssl_supported': False, 'requires_server_name': True}
        )

    def delete_endpoint(self, endpoint_arn: str) -> Dict[str, Any]:
        """Delete a database endpoint.

        Args:
            endpoint_arn: Endpoint ARN to delete

        Returns:
            Dictionary with deletion confirmation
        """
        logger.info('Deleting endpoint', endpoint_arn=endpoint_arn)

        # Call API
        response = self.client.call_api('delete_endpoint', EndpointArn=endpoint_arn)

        # Format response
        endpoint = response.get('Endpoint', {})
        formatted_endpoint = ResponseFormatter.format_endpoint(endpoint)

        result = {
            'success': True,
            'data': {'endpoint': formatted_endpoint, 'message': 'Endpoint deleted successfully'},
            'error': None,
        }

        logger.info(f'Deleted endpoint: {formatted_endpoint.get("identifier")}')
        return result

    def modify_endpoint(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Modify an endpoint configuration.

        Args:
            params: Endpoint modification parameters

        Returns:
            Modified endpoint details
        """
        endpoint_arn = params.get('EndpointArn', 'unknown')
        logger.info('Modifying endpoint', endpoint_arn=endpoint_arn)

        # Mask password in logs if present
        safe_params = {k: v if k != 'Password' else '***MASKED***' for k, v in params.items()}
        logger.debug('Modifying endpoint with params', params=safe_params)

        # Call API
        response = self.client.call_api('modify_endpoint', **params)

        # Format response
        endpoint = response.get('Endpoint', {})
        formatted_endpoint = ResponseFormatter.format_endpoint(endpoint)

        result = {
            'success': True,
            'data': {'endpoint': formatted_endpoint, 'message': 'Endpoint modified successfully'},
            'error': None,
        }

        logger.info(f'Modified endpoint: {formatted_endpoint.get("identifier")}')
        return result

    def get_endpoint_settings(
        self, engine_name: str, max_results: int = 100, marker: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get valid endpoint settings for a database engine.

        Args:
            engine_name: Database engine name
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            Dictionary with endpoint settings
        """
        logger.info('Getting endpoint settings', engine=engine_name)

        # Build API parameters
        params: Dict[str, Any] = {'EngineName': engine_name, 'MaxRecords': max_results}

        if marker:
            params['Marker'] = marker

        # Call API
        response = self.client.call_api('describe_endpoint_settings', **params)

        # Format settings
        settings = response.get('EndpointSettings', [])

        result = {
            'success': True,
            'data': {'endpoint_settings': settings, 'count': len(settings), 'engine': engine_name},
            'error': None,
        }

        # Add pagination info
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        logger.info(f'Retrieved {len(settings)} endpoint settings for {engine_name}')
        return result

    def list_endpoint_types(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List supported endpoint types.

        Args:
            filters: Optional filters
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            Dictionary with endpoint types
        """
        logger.info('Listing endpoint types')

        # Build API parameters
        params: Dict[str, Any] = {'MaxRecords': max_results}

        if filters:
            params['Filters'] = filters

        if marker:
            params['Marker'] = marker

        # Call API
        response = self.client.call_api('describe_endpoint_types', **params)

        # Get endpoint types
        endpoint_types = response.get('SupportedEndpointTypes', [])

        result = {
            'success': True,
            'data': {'endpoint_types': endpoint_types, 'count': len(endpoint_types)},
            'error': None,
        }

        # Add pagination info
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        logger.info(f'Retrieved {len(endpoint_types)} endpoint types')
        return result

    def list_engine_versions(
        self,
        engine_name: Optional[str] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List available DMS engine versions.

        Args:
            engine_name: Optional engine name filter
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            Dictionary with engine versions
        """
        logger.info('Listing engine versions', engine=engine_name)

        # Build API parameters
        params: Dict[str, Any] = {'MaxRecords': max_results}

        if engine_name:
            params['Filters'] = [{'Name': 'engine-name', 'Values': [engine_name]}]

        if marker:
            params['Marker'] = marker

        # Call API
        response = self.client.call_api('describe_engine_versions', **params)

        # Get engine versions
        engine_versions = response.get('EngineVersions', [])

        result = {
            'success': True,
            'data': {'engine_versions': engine_versions, 'count': len(engine_versions)},
            'error': None,
        }

        # Add pagination info
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        logger.info(f'Retrieved {len(engine_versions)} engine versions')
        return result

    def refresh_schemas(self, endpoint_arn: str, instance_arn: str) -> Dict[str, Any]:
        """Refresh schema definitions for an endpoint.

        Args:
            endpoint_arn: Endpoint ARN
            instance_arn: Replication instance ARN

        Returns:
            Refresh status
        """
        logger.info('Refreshing schemas', endpoint_arn=endpoint_arn)

        # Call API
        response = self.client.call_api(
            'refresh_schemas', EndpointArn=endpoint_arn, ReplicationInstanceArn=instance_arn
        )

        # Format response
        refresh_status = response.get('RefreshSchemasStatus', {})

        result = {
            'success': True,
            'data': {
                'refresh_status': refresh_status,
                'endpoint_arn': endpoint_arn,
                'message': 'Schema refresh initiated',
            },
            'error': None,
        }

        logger.info(f'Initiated schema refresh for endpoint: {endpoint_arn}')
        return result

    def list_schemas(
        self, endpoint_arn: str, max_results: int = 100, marker: Optional[str] = None
    ) -> Dict[str, Any]:
        """List database schemas for an endpoint.

        Args:
            endpoint_arn: Endpoint ARN
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            Dictionary with schema list
        """
        logger.info('Listing schemas', endpoint_arn=endpoint_arn)

        # Build API parameters
        params: Dict[str, Any] = {'EndpointArn': endpoint_arn, 'MaxRecords': max_results}

        if marker:
            params['Marker'] = marker

        # Call API
        response = self.client.call_api('describe_schemas', **params)

        # Get schemas
        schemas = response.get('Schemas', [])

        result = {
            'success': True,
            'data': {'schemas': schemas, 'count': len(schemas), 'endpoint_arn': endpoint_arn},
            'error': None,
        }

        # Add pagination info
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        logger.info(f'Retrieved {len(schemas)} schemas for endpoint')
        return result

    def get_refresh_status(self, endpoint_arn: str) -> Dict[str, Any]:
        """Get schema refresh status for an endpoint.

        Args:
            endpoint_arn: Endpoint ARN

        Returns:
            Refresh status details
        """
        logger.info('Getting refresh schemas status', endpoint_arn=endpoint_arn)

        # Call API
        response = self.client.call_api(
            'describe_refresh_schemas_status', EndpointArn=endpoint_arn
        )

        # Format response
        refresh_status = response.get('RefreshSchemasStatus', {})

        result = {
            'success': True,
            'data': {
                'refresh_status': refresh_status,
                'endpoint_arn': endpoint_arn,
                'status': refresh_status.get('Status', 'unknown'),
            },
            'error': None,
        }

        logger.info(f'Retrieved refresh status for endpoint: {endpoint_arn}')
        return result


# TODO: Add Secrets Manager integration
