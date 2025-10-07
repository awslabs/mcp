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

"""Maintenance Manager.

Handles business logic for AWS DMS maintenance and tagging operations.
"""

from .dms_client import DMSClient
from loguru import logger
from typing import Any, Dict, List, Optional


class MaintenanceManager:
    """Manager for maintenance and resource tagging operations."""

    def __init__(self, client: DMSClient):
        """Initialize maintenance manager.

        Args:
            client: DMS client wrapper
        """
        self.client = client
        logger.debug('Initialized MaintenanceManager')

    def apply_pending_maintenance_action(
        self, resource_arn: str, apply_action: str, opt_in_type: str
    ) -> Dict[str, Any]:
        """Apply a pending maintenance action to a resource.

        Args:
            resource_arn: Resource ARN
            apply_action: Maintenance action to apply
            opt_in_type: When to apply (immediate, next-maintenance, undo-opt-in)

        Returns:
            Resource with pending maintenance actions
        """
        logger.info(
            'Applying pending maintenance action', resource_arn=resource_arn, action=apply_action
        )

        response = self.client.call_api(
            'apply_pending_maintenance_action',
            ReplicationInstanceArn=resource_arn,
            ApplyAction=apply_action,
            OptInType=opt_in_type,
        )

        resource = response.get('ResourcePendingMaintenanceActions', {})

        return {
            'success': True,
            'data': {
                'resource': resource,
                'message': f"Maintenance action '{apply_action}' applied with opt-in type '{opt_in_type}'",
            },
            'error': None,
        }

    def list_pending_maintenance_actions(
        self,
        resource_arn: Optional[str] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List pending maintenance actions for DMS resources.

        Args:
            resource_arn: Optional resource ARN to filter
            filters: Optional filters
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            List of resources with pending maintenance
        """
        logger.info('Listing pending maintenance actions')

        params: Dict[str, Any] = {'MaxRecords': max_results}

        if resource_arn:
            params['ReplicationInstanceArn'] = resource_arn
        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker

        response = self.client.call_api('describe_pending_maintenance_actions', **params)

        pending_actions = response.get('PendingMaintenanceActions', [])

        result = {
            'success': True,
            'data': {
                'pending_maintenance_actions': pending_actions,
                'count': len(pending_actions),
            },
            'error': None,
        }

        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        logger.info(f'Retrieved {len(pending_actions)} resources with pending maintenance')
        return result

    def get_account_attributes(self) -> Dict[str, Any]:
        """Get DMS account attributes and quotas.

        Returns:
            Account attributes including resource quotas
        """
        logger.info('Getting account attributes')

        response = self.client.call_api('describe_account_attributes')

        account_quotas = response.get('AccountQuotas', [])
        unique_account_identifier = response.get('UniqueAccountIdentifier')

        return {
            'success': True,
            'data': {
                'account_quotas': account_quotas,
                'unique_account_identifier': unique_account_identifier,
                'count': len(account_quotas),
            },
            'error': None,
        }

    def add_tags(self, resource_arn: str, tags: List[Dict[str, str]]) -> Dict[str, Any]:
        """Add tags to a DMS resource.

        Args:
            resource_arn: Resource ARN to tag
            tags: List of tags to add

        Returns:
            Operation result
        """
        logger.info('Adding tags to resource', resource_arn=resource_arn, tag_count=len(tags))

        self.client.call_api('add_tags_to_resource', ResourceArn=resource_arn, Tags=tags)

        return {
            'success': True,
            'data': {
                'resource_arn': resource_arn,
                'tags_added': len(tags),
                'message': 'Tags added successfully',
            },
            'error': None,
        }

    def remove_tags(self, resource_arn: str, tag_keys: List[str]) -> Dict[str, Any]:
        """Remove tags from a DMS resource.

        Args:
            resource_arn: Resource ARN
            tag_keys: List of tag keys to remove

        Returns:
            Operation result
        """
        logger.info(
            'Removing tags from resource', resource_arn=resource_arn, key_count=len(tag_keys)
        )

        self.client.call_api(
            'remove_tags_from_resource', ResourceArn=resource_arn, TagKeys=tag_keys
        )

        return {
            'success': True,
            'data': {
                'resource_arn': resource_arn,
                'tags_removed': len(tag_keys),
                'message': 'Tags removed successfully',
            },
            'error': None,
        }

    def list_tags(self, resource_arn: str) -> Dict[str, Any]:
        """List tags for a DMS resource.

        Args:
            resource_arn: Resource ARN

        Returns:
            List of resource tags
        """
        logger.info('Listing tags for resource', resource_arn=resource_arn)

        response = self.client.call_api('list_tags_for_resource', ResourceArn=resource_arn)

        tags = response.get('TagList', [])

        return {
            'success': True,
            'data': {'resource_arn': resource_arn, 'tags': tags, 'count': len(tags)},
            'error': None,
        }
