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

"""Response Formatter.

Provides consistent response formatting across all MCP tools.
"""

from datetime import datetime
from typing import Any, Dict, Optional


class ResponseFormatter:
    """Utility class for formatting API responses consistently."""

    @staticmethod
    def format_instance(instance: Dict[str, Any]) -> Dict[str, Any]:
        """Format replication instance for response.

        Args:
            instance: Raw instance data from AWS API

        Returns:
            Formatted instance dictionary
        """
        formatted = {
            'arn': instance.get('ReplicationInstanceArn'),
            'identifier': instance.get('ReplicationInstanceIdentifier'),
            'class': instance.get('ReplicationInstanceClass'),
            'status': instance.get('ReplicationInstanceStatus'),
            'allocated_storage': instance.get('AllocatedStorage'),
            'engine_version': instance.get('EngineVersion'),
            'multi_az': instance.get('MultiAZ', False),
            'publicly_accessible': instance.get('PubliclyAccessible', False),
            'availability_zone': instance.get('AvailabilityZone'),
        }

        # Format timestamps
        if instance.get('InstanceCreateTime'):
            formatted['instance_create_time'] = ResponseFormatter.format_timestamp(
                instance['InstanceCreateTime']
            )

        # Simplify VPC security groups
        if instance.get('VpcSecurityGroups'):
            formatted['vpc_security_groups'] = [
                {'id': sg.get('VpcSecurityGroupId'), 'status': sg.get('Status')}
                for sg in instance['VpcSecurityGroups']
            ]

        return formatted

    @staticmethod
    def format_endpoint(endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """Format endpoint for response.

        Args:
            endpoint: Raw endpoint data from AWS API

        Returns:
            Formatted endpoint dictionary
        """
        formatted = {
            'arn': endpoint.get('EndpointArn'),
            'identifier': endpoint.get('EndpointIdentifier'),
            'type': endpoint.get('EndpointType'),
            'engine': endpoint.get('EngineName'),
            'server_name': endpoint.get('ServerName'),
            'port': endpoint.get('Port'),
            'database_name': endpoint.get('DatabaseName'),
            'username': endpoint.get('Username'),
            'status': endpoint.get('Status'),
            'ssl_mode': endpoint.get('SslMode', 'none'),
        }

        # Mask password if present
        if endpoint.get('Password'):
            formatted['password'] = '***MASKED***'

        # Optional fields
        if endpoint.get('CertificateArn'):
            formatted['certificate_arn'] = endpoint.get('CertificateArn')

        # Format timestamps
        if endpoint.get('EndpointCreateTime'):
            formatted['endpoint_create_time'] = ResponseFormatter.format_timestamp(
                endpoint['EndpointCreateTime']
            )

        return formatted

    @staticmethod
    def format_task(task: Dict[str, Any]) -> Dict[str, Any]:
        """Format replication task for response.

        Args:
            task: Raw task data from AWS API

        Returns:
            Formatted task dictionary
        """
        formatted = {
            'arn': task.get('ReplicationTaskArn'),
            'identifier': task.get('ReplicationTaskIdentifier'),
            'status': task.get('Status'),
            'migration_type': task.get('MigrationType'),
            'source_endpoint_arn': task.get('SourceEndpointArn'),
            'target_endpoint_arn': task.get('TargetEndpointArn'),
            'replication_instance_arn': task.get('ReplicationInstanceArn'),
            'table_mappings': task.get('TableMappings'),
        }

        # Format task statistics
        if task.get('ReplicationTaskStats'):
            stats = task['ReplicationTaskStats']
            formatted['stats'] = {
                'full_load_progress_percent': stats.get('FullLoadProgressPercent', 0),
                'elapsed_time_millis': stats.get('ElapsedTimeMillis', 0),
                'tables_loaded': stats.get('TablesLoaded', 0),
                'tables_loading': stats.get('TablesLoading', 0),
                'tables_queued': stats.get('TablesQueued', 0),
                'tables_errored': stats.get('TablesErrored', 0),
            }

        # Format timestamps
        if task.get('ReplicationTaskCreationDate'):
            formatted['task_create_time'] = ResponseFormatter.format_timestamp(
                task['ReplicationTaskCreationDate']
            )
        if task.get('ReplicationTaskStartDate'):
            formatted['start_time'] = ResponseFormatter.format_timestamp(
                task['ReplicationTaskStartDate']
            )
        if task.get('StopDate'):
            formatted['stop_time'] = ResponseFormatter.format_timestamp(task['StopDate'])

        return formatted

    @staticmethod
    def format_table_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
        """Format table statistics for response.

        Args:
            stats: Raw table statistics from AWS API

        Returns:
            Formatted statistics dictionary
        """
        formatted = {
            'schema_name': stats.get('SchemaName'),
            'table_name': stats.get('TableName'),
            'inserts': stats.get('Inserts', 0),
            'deletes': stats.get('Deletes', 0),
            'updates': stats.get('Updates', 0),
            'ddls': stats.get('Ddls', 0),
            'full_load_rows': stats.get('FullLoadRows', 0),
            'full_load_error_rows': stats.get('FullLoadErrorRows', 0),
            'full_load_condtnl_chk_failed_rows': stats.get('FullLoadCondtnlChkFailedRows', 0),
            'table_state': stats.get('TableState', 'Unknown'),
        }

        # Calculate completion percentage
        total_rows = stats.get('FullLoadRows', 0)
        error_rows = stats.get('FullLoadErrorRows', 0)
        if total_rows > 0:
            success_rows = total_rows - error_rows
            formatted['completion_percent'] = round((success_rows / total_rows) * 100, 2)
        else:
            formatted['completion_percent'] = 0.0

        # Format timestamps
        if stats.get('FullLoadStartTime'):
            formatted['full_load_start_time'] = ResponseFormatter.format_timestamp(
                stats['FullLoadStartTime']
            )
        if stats.get('FullLoadEndTime'):
            formatted['full_load_end_time'] = ResponseFormatter.format_timestamp(
                stats['FullLoadEndTime']
            )
        if stats.get('LastUpdateTime'):
            formatted['last_update_time'] = ResponseFormatter.format_timestamp(
                stats['LastUpdateTime']
            )

        # Validation statistics
        if stats.get('ValidationPendingRecords') is not None:
            formatted['validation_pending_records'] = stats.get('ValidationPendingRecords')
        if stats.get('ValidationFailedRecords') is not None:
            formatted['validation_failed_records'] = stats.get('ValidationFailedRecords')
        if stats.get('ValidationSuspendedRecords') is not None:
            formatted['validation_suspended_records'] = stats.get('ValidationSuspendedRecords')
        if stats.get('ValidationState'):
            formatted['validation_state'] = stats.get('ValidationState')

        return formatted

    @staticmethod
    def format_error(error: Exception) -> Dict[str, Any]:
        """Format exception for error response.

        Args:
            error: Exception to format

        Returns:
            Formatted error dictionary
        """
        from ..exceptions import DMSMCPException

        error_dict = {
            'success': False,
            'error': {
                'message': str(error),
                'type': error.__class__.__name__,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
            },
            'data': None,
        }

        # Add details for custom exceptions
        if isinstance(error, DMSMCPException):
            if error.details:
                error_dict['error']['details'] = error.details
            if error.suggested_action:
                error_dict['error']['suggested_action'] = error.suggested_action

        return error_dict

    @staticmethod
    def format_timestamp(dt: Optional[datetime]) -> Optional[str]:
        """Format datetime to ISO 8601 string.

        Args:
            dt: Datetime object or None

        Returns:
            ISO 8601 formatted string or None
        """
        return dt.isoformat() + 'Z' if dt else None


# TODO: Add field mapping configuration
# TODO: Add custom serializers for complex types
# TODO: Add pagination metadata formatting
