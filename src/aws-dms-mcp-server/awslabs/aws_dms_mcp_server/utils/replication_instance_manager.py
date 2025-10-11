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

"""Replication Instance Manager.

Handles business logic for AWS DMS replication instance operations.
"""

from ..exceptions import DMSInvalidParameterException, DMSResourceNotFoundException
from .dms_client import DMSClient
from .response_formatter import ResponseFormatter
from loguru import logger
from typing import Any, Dict, List, Optional


class ReplicationInstanceManager:
    """Manager for replication instance operations."""

    def __init__(self, client: DMSClient):
        """Initialize replication instance manager.

        Args:
            client: DMS client wrapper
        """
        self.client = client
        logger.debug('Initialized ReplicationInstanceManager')

    def list_instances(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List replication instances with optional filtering.

        Args:
            filters: Optional filters for instance selection
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            Dictionary with instances list and pagination info
        """
        logger.info('Listing replication instances', filters=filters)

        # Build API parameters
        params: Dict[str, Any] = {'MaxRecords': max_results}

        if filters:
            params['Filters'] = filters

        if marker:
            params['Marker'] = marker

        # Call API
        response = self.client.call_api('describe_replication_instances', **params)

        # Format instances
        instances = response.get('ReplicationInstances', [])
        formatted_instances = [
            ResponseFormatter.format_instance(instance) for instance in instances
        ]

        result = {
            'success': True,
            'data': {'instances': formatted_instances, 'count': len(formatted_instances)},
            'error': None,
        }

        # Add pagination info
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        logger.info(f'Retrieved {len(formatted_instances)} replication instances')
        return result

    def create_instance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new replication instance.

        Args:
            params: Instance creation parameters

        Returns:
            Created instance details
        """
        logger.info(
            'Creating replication instance',
            identifier=params.get('replication_instance_identifier'),
        )

        # Validate required parameters
        required_params = ['ReplicationInstanceIdentifier', 'ReplicationInstanceClass']
        for param in required_params:
            if param not in params:
                raise DMSInvalidParameterException(
                    message=f'Missing required parameter: {param}',
                    details={'missing_param': param},
                )

        # Validate instance class
        instance_class = params.get('ReplicationInstanceClass', '')
        if not self.validate_instance_class(instance_class):
            raise DMSInvalidParameterException(
                message=f'Invalid instance class: {instance_class}',
                details={'invalid_class': instance_class},
            )

        # Call API
        response = self.client.call_api('create_replication_instance', **params)

        # Format response
        instance = response.get('ReplicationInstance', {})
        formatted_instance = ResponseFormatter.format_instance(instance)

        result = {
            'success': True,
            'data': {
                'instance': formatted_instance,
                'message': 'Replication instance creation initiated',
            },
            'error': None,
        }

        logger.info(f'Created replication instance: {formatted_instance.get("identifier")}')
        return result

    def get_instance_details(self, instance_arn: str) -> Dict[str, Any]:
        """Get detailed information about a specific instance.

        Args:
            instance_arn: Instance ARN

        Returns:
            Instance details
        """
        logger.info('Getting instance details', arn=instance_arn)

        # Filter by ARN
        filters = [{'Name': 'replication-instance-arn', 'Values': [instance_arn]}]

        # Call API
        response = self.client.call_api('describe_replication_instances', Filters=filters)

        instances = response.get('ReplicationInstances', [])

        if not instances:
            raise DMSResourceNotFoundException(
                message=f'Replication instance not found: {instance_arn}',
                details={'arn': instance_arn},
            )

        # Format and return first (should be only) instance
        formatted_instance = ResponseFormatter.format_instance(instances[0])

        return {'success': True, 'data': formatted_instance, 'error': None}

    def validate_instance_class(self, instance_class: str) -> bool:
        """Validate instance class is supported.

        Args:
            instance_class: Instance class to validate

        Returns:
            True if valid
        """
        # Common DMS instance classes
        valid_classes = [
            'dms.t2.micro',
            'dms.t2.small',
            'dms.t2.medium',
            'dms.t2.large',
            'dms.t3.micro',
            'dms.t3.small',
            'dms.t3.medium',
            'dms.t3.large',
            'dms.c4.large',
            'dms.c4.xlarge',
            'dms.c4.2xlarge',
            'dms.c4.4xlarge',
            'dms.c5.large',
            'dms.c5.xlarge',
            'dms.c5.2xlarge',
            'dms.c5.4xlarge',
            'dms.r4.large',
            'dms.r4.xlarge',
            'dms.r4.2xlarge',
            'dms.r4.4xlarge',
            'dms.r5.large',
            'dms.r5.xlarge',
            'dms.r5.2xlarge',
            'dms.r5.4xlarge',
        ]

        return instance_class in valid_classes

    def modify_instance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Modify replication instance.

        Args:
            params: Instance modification parameters

        Returns:
            Modified instance details
        """
        response = self.client.call_api('modify_replication_instance', **params)
        instance = ResponseFormatter.format_instance(response.get('ReplicationInstance', {}))
        return {
            'success': True,
            'data': {'instance': instance, 'message': 'Instance modified successfully'},
            'error': None,
        }

    def delete_instance(self, instance_arn: str) -> Dict[str, Any]:
        """Delete replication instance.

        Args:
            instance_arn: Instance ARN to delete

        Returns:
            Deleted instance details
        """
        response = self.client.call_api(
            'delete_replication_instance', ReplicationInstanceArn=instance_arn
        )
        instance = ResponseFormatter.format_instance(response.get('ReplicationInstance', {}))
        return {
            'success': True,
            'data': {'instance': instance, 'message': 'Instance deleted successfully'},
            'error': None,
        }

    def reboot_instance(self, instance_arn: str, force_failover: bool = False) -> Dict[str, Any]:
        """Reboot replication instance.

        Args:
            instance_arn: Instance ARN to reboot
            force_failover: Force failover to secondary AZ

        Returns:
            Rebooted instance details
        """
        response = self.client.call_api(
            'reboot_replication_instance',
            ReplicationInstanceArn=instance_arn,
            ForceFailover=force_failover,
        )
        instance = ResponseFormatter.format_instance(response.get('ReplicationInstance', {}))
        return {
            'success': True,
            'data': {'instance': instance, 'message': 'Instance reboot initiated'},
            'error': None,
        }

    def list_orderable_instances(
        self, max_results: int = 100, marker: Optional[str] = None
    ) -> Dict[str, Any]:
        """List orderable instance configurations.

        Args:
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            List of orderable instance configurations
        """
        params: Dict[str, Any] = {'MaxRecords': max_results}
        if marker:
            params['Marker'] = marker

        response = self.client.call_api('describe_orderable_replication_instances', **params)
        instances = response.get('OrderableReplicationInstances', [])

        result = {
            'success': True,
            'data': {'orderable_instances': instances, 'count': len(instances)},
            'error': None,
        }
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']
        return result

    def get_task_logs(
        self, instance_arn: str, max_results: int = 100, marker: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get task log metadata.

        Args:
            instance_arn: Instance ARN
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            List of task log metadata
        """
        params: Dict[str, Any] = {
            'ReplicationInstanceArn': instance_arn,
            'MaxRecords': max_results,
        }
        if marker:
            params['Marker'] = marker

        response = self.client.call_api('describe_replication_instance_task_logs', **params)
        logs = response.get('ReplicationInstanceTaskLogs', [])

        result = {'success': True, 'data': {'task_logs': logs, 'count': len(logs)}, 'error': None}
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']
        return result


# TODO: Add instance status monitoring
