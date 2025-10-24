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

"""Subnet Group Manager.

Handles business logic for AWS DMS replication subnet group operations.
"""

from ..exceptions import DMSInvalidParameterException
from .dms_client import DMSClient
from loguru import logger
from typing import Any, Dict, List, Optional


class SubnetGroupManager:
    """Manager for replication subnet group operations."""

    def __init__(self, client: DMSClient):
        """Initialize subnet group manager.

        Args:
            client: DMS client wrapper
        """
        self.client = client
        logger.debug('Initialized SubnetGroupManager')

    def create_subnet_group(
        self,
        identifier: str,
        description: str,
        subnet_ids: List[str],
        tags: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Create a replication subnet group.

        Args:
            identifier: Unique identifier for the subnet group
            description: Subnet group description
            subnet_ids: List of subnet IDs
            tags: Resource tags

        Returns:
            Created subnet group details
        """
        logger.info('Creating replication subnet group', identifier=identifier)

        if not subnet_ids or len(subnet_ids) == 0:
            raise DMSInvalidParameterException(
                message='At least one subnet ID is required', details={'parameter': 'subnet_ids'}
            )

        params: Dict[str, Any] = {
            'ReplicationSubnetGroupIdentifier': identifier,
            'ReplicationSubnetGroupDescription': description,
            'SubnetIds': subnet_ids,
        }

        if tags:
            params['Tags'] = tags

        response = self.client.call_api('create_replication_subnet_group', **params)

        subnet_group = response.get('ReplicationSubnetGroup', {})

        return {
            'success': True,
            'data': {
                'subnet_group': subnet_group,
                'message': 'Replication subnet group created successfully',
            },
            'error': None,
        }

    def modify_subnet_group(
        self,
        identifier: str,
        description: Optional[str] = None,
        subnet_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Modify a replication subnet group.

        Args:
            identifier: Subnet group identifier
            description: New description
            subnet_ids: New list of subnet IDs

        Returns:
            Modified subnet group details
        """
        logger.info('Modifying replication subnet group', identifier=identifier)

        params: Dict[str, Any] = {'ReplicationSubnetGroupIdentifier': identifier}

        if description:
            params['ReplicationSubnetGroupDescription'] = description
        if subnet_ids:
            if len(subnet_ids) == 0:
                raise DMSInvalidParameterException(
                    message='At least one subnet ID is required',
                    details={'parameter': 'subnet_ids'},
                )
            params['SubnetIds'] = subnet_ids

        response = self.client.call_api('modify_replication_subnet_group', **params)

        subnet_group = response.get('ReplicationSubnetGroup', {})

        return {
            'success': True,
            'data': {
                'subnet_group': subnet_group,
                'message': 'Replication subnet group modified successfully',
            },
            'error': None,
        }

    def list_subnet_groups(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List replication subnet groups.

        Args:
            filters: Optional filters for subnet group selection
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            List of subnet groups
        """
        logger.info('Listing replication subnet groups', filters=filters)

        params: Dict[str, Any] = {'MaxRecords': max_results}

        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker

        response = self.client.call_api('describe_replication_subnet_groups', **params)

        subnet_groups = response.get('ReplicationSubnetGroups', [])

        result = {
            'success': True,
            'data': {'subnet_groups': subnet_groups, 'count': len(subnet_groups)},
            'error': None,
        }

        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        logger.info(f'Retrieved {len(subnet_groups)} replication subnet groups')
        return result

    def delete_subnet_group(self, identifier: str) -> Dict[str, Any]:
        """Delete a replication subnet group.

        Args:
            identifier: Subnet group identifier to delete

        Returns:
            Deletion result
        """
        logger.info('Deleting replication subnet group', identifier=identifier)

        self.client.call_api(
            'delete_replication_subnet_group', ReplicationSubnetGroupIdentifier=identifier
        )

        return {
            'success': True,
            'data': {
                'message': 'Replication subnet group deleted successfully',
                'identifier': identifier,
            },
            'error': None,
        }
