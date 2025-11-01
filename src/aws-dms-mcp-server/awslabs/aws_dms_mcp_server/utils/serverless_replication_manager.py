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

"""Serverless Replication Manager.

Handles business logic for AWS DMS Serverless replication configuration operations.
"""

from .dms_client import DMSClient
from loguru import logger
from typing import Any, Dict, List, Optional


class ServerlessReplicationManager:
    """Manager for DMS Serverless replication operations."""

    def __init__(self, client: DMSClient):
        """Initialize serverless replication manager.

        Args:
            client: DMS client wrapper
        """
        self.client = client
        logger.debug('Initialized ServerlessReplicationManager')

    def create_replication_config(
        self,
        identifier: str,
        source_endpoint_arn: str,
        target_endpoint_arn: str,
        compute_config: Dict[str, Any],
        replication_type: str,
        table_mappings: str,
        replication_settings: Optional[str] = None,
        supplemental_settings: Optional[str] = None,
        resource_identifier: Optional[str] = None,
        tags: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Create a replication configuration for DMS Serverless.

        Args:
            identifier: Unique identifier
            source_endpoint_arn: Source endpoint ARN
            target_endpoint_arn: Target endpoint ARN
            compute_config: Compute configuration with replication units
            replication_type: Replication type (full-load, cdc, full-load-and-cdc)
            table_mappings: Table mappings JSON string
            replication_settings: Replication settings JSON
            supplemental_settings: Supplemental settings JSON
            resource_identifier: Optional resource identifier
            tags: Resource tags

        Returns:
            Created replication config details
        """
        logger.info('Creating replication config', identifier=identifier)

        params: Dict[str, Any] = {
            'ReplicationConfigIdentifier': identifier,
            'SourceEndpointArn': source_endpoint_arn,
            'TargetEndpointArn': target_endpoint_arn,
            'ComputeConfig': compute_config,
            'ReplicationType': replication_type,
            'TableMappings': table_mappings,
        }

        if replication_settings:
            params['ReplicationSettings'] = replication_settings
        if supplemental_settings:
            params['SupplementalSettings'] = supplemental_settings
        if resource_identifier:
            params['ResourceIdentifier'] = resource_identifier
        if tags:
            params['Tags'] = tags

        response = self.client.call_api('create_replication_config', **params)

        replication_config = response.get('ReplicationConfig', {})

        return {
            'success': True,
            'data': {
                'replication_config': replication_config,
                'message': 'Replication config created successfully',
            },
            'error': None,
        }

    def modify_replication_config(
        self,
        arn: str,
        identifier: Optional[str] = None,
        compute_config: Optional[Dict[str, Any]] = None,
        replication_type: Optional[str] = None,
        table_mappings: Optional[str] = None,
        replication_settings: Optional[str] = None,
        supplemental_settings: Optional[str] = None,
        source_endpoint_arn: Optional[str] = None,
        target_endpoint_arn: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Modify a replication configuration.

        Args:
            arn: Replication config ARN
            identifier: New identifier
            compute_config: New compute configuration
            replication_type: New replication type
            table_mappings: New table mappings
            replication_settings: New replication settings
            supplemental_settings: New supplemental settings
            source_endpoint_arn: New source endpoint ARN
            target_endpoint_arn: New target endpoint ARN

        Returns:
            Modified replication config details
        """
        logger.info('Modifying replication config', arn=arn)

        params: Dict[str, Any] = {'ReplicationConfigArn': arn}

        if identifier:
            params['ReplicationConfigIdentifier'] = identifier
        if compute_config:
            params['ComputeConfig'] = compute_config
        if replication_type:
            params['ReplicationType'] = replication_type
        if table_mappings:
            params['TableMappings'] = table_mappings
        if replication_settings:
            params['ReplicationSettings'] = replication_settings
        if supplemental_settings:
            params['SupplementalSettings'] = supplemental_settings
        if source_endpoint_arn:
            params['SourceEndpointArn'] = source_endpoint_arn
        if target_endpoint_arn:
            params['TargetEndpointArn'] = target_endpoint_arn

        response = self.client.call_api('modify_replication_config', **params)

        replication_config = response.get('ReplicationConfig', {})

        return {
            'success': True,
            'data': {
                'replication_config': replication_config,
                'message': 'Replication config modified successfully',
            },
            'error': None,
        }

    def delete_replication_config(self, arn: str) -> Dict[str, Any]:
        """Delete a replication configuration.

        Args:
            arn: Replication config ARN

        Returns:
            Deleted replication config details
        """
        logger.info('Deleting replication config', arn=arn)

        response = self.client.call_api('delete_replication_config', ReplicationConfigArn=arn)

        replication_config = response.get('ReplicationConfig', {})

        return {
            'success': True,
            'data': {
                'replication_config': replication_config,
                'message': 'Replication config deleted successfully',
            },
            'error': None,
        }

    def list_replication_configs(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List replication configurations.

        Args:
            filters: Optional filters
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            List of replication configs
        """
        logger.info('Listing replication configs', filters=filters)

        params: Dict[str, Any] = {'MaxRecords': max_results}

        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker

        response = self.client.call_api('describe_replication_configs', **params)

        configs = response.get('ReplicationConfigs', [])

        result = {
            'success': True,
            'data': {'replication_configs': configs, 'count': len(configs)},
            'error': None,
        }

        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        logger.info(f'Retrieved {len(configs)} replication configs')
        return result

    def list_replications(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List serverless replications (running instances of configs).

        Args:
            filters: Optional filters
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            List of replications
        """
        logger.info('Listing replications', filters=filters)

        params: Dict[str, Any] = {'MaxRecords': max_results}

        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker

        response = self.client.call_api('describe_replications', **params)

        replications = response.get('Replications', [])

        result = {
            'success': True,
            'data': {'replications': replications, 'count': len(replications)},
            'error': None,
        }

        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        logger.info(f'Retrieved {len(replications)} replications')
        return result

    def start_replication(
        self,
        arn: str,
        start_replication_type: str,
        cdc_start_time: Optional[str] = None,
        cdc_start_position: Optional[str] = None,
        cdc_stop_position: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start a serverless replication.

        Args:
            arn: Replication config ARN
            start_replication_type: Start type (start-replication, resume-processing, reload-target)
            cdc_start_time: CDC start time
            cdc_start_position: CDC start position
            cdc_stop_position: CDC stop position

        Returns:
            Started replication details
        """
        logger.info('Starting replication', arn=arn, start_type=start_replication_type)

        params: Dict[str, Any] = {
            'ReplicationConfigArn': arn,
            'StartReplicationType': start_replication_type,
        }

        if cdc_start_time:
            params['CdcStartTime'] = cdc_start_time
        if cdc_start_position:
            params['CdcStartPosition'] = cdc_start_position
        if cdc_stop_position:
            params['CdcStopPosition'] = cdc_stop_position

        response = self.client.call_api('start_replication', **params)

        replication = response.get('Replication', {})

        return {
            'success': True,
            'data': {
                'replication': replication,
                'message': f'Replication started with type: {start_replication_type}',
            },
            'error': None,
        }

    def stop_replication(self, arn: str) -> Dict[str, Any]:
        """Stop a running serverless replication.

        Args:
            arn: Replication config ARN

        Returns:
            Stopped replication details
        """
        logger.info('Stopping replication', arn=arn)

        response = self.client.call_api('stop_replication', ReplicationConfigArn=arn)

        replication = response.get('Replication', {})

        return {
            'success': True,
            'data': {'replication': replication, 'message': 'Replication stop initiated'},
            'error': None,
        }
