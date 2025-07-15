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

"""Constants for the RDS Control Plane MCP Server."""

# Version
MCP_SERVER_VERSION = '0.1.0'

# Confirmation strings for destructive operations
CONFIRM_STOP = 'CONFIRM_STOP'
CONFIRM_STOP_CLUSTER = 'CONFIRM_STOP'
CONFIRM_START = 'CONFIRM_START'
CONFIRM_REBOOT = 'CONFIRM_REBOOT'
CONFIRM_DELETE = 'CONFIRM_DELETE'
CONFIRM_DELETE_INSTANCE = (
    'You are about to delete DB instance {instance_id}. This operation cannot be undone.'
)
CONFIRM_FAILOVER = 'CONFIRM_FAILOVER'
CONFIRM_RESET = 'CONFIRM_RESET'

# Success messages
SUCCESS_STARTED = '{} has been started successfully.'
SUCCESS_STOPPED = '{} has been stopped successfully.'
SUCCESS_REBOOTED = '{} has been rebooted successfully.'
SUCCESS_CREATED = '{} has been created successfully.'
SUCCESS_MODIFIED = '{} has been modified successfully.'
SUCCESS_DELETED = '{} has been deleted successfully.'
SUCCESS_FAILED_OVER = '{} has been failed over successfully.'
SUCCESS_SNAPSHOT_CREATED = 'Snapshot {} has been created successfully.'
SUCCESS_RESTORED = '{} has been restored successfully.'

# Error messages
ERROR_READONLY_MODE = 'This operation is not allowed in read-only mode. Please run the server with --no-readonly to enable write operations.'
ERROR_CLIENT = 'Client error: {}. Please check the error details and try again.'
ERROR_UNEXPECTED = 'Unexpected error: {}. Please try again or check the logs for more information.'
ERROR_INVALID_PARAMETER = 'Invalid parameter: {}. Please check the parameter values and try again.'
ERROR_INVALID_PARAMS = 'Invalid parameters: {}. Please check the parameter values and try again.'
ERROR_RESOURCE_NOT_FOUND = 'Resource not found: {}. Please check that the resource exists and you have permission to access it.'
ERROR_MISSING_CONFIRMATION = 'Missing confirmation for destructive operation. Please provide the confirmation parameter with the required value.'

# Standard Confirmation Message
STANDARD_CONFIRMATION_MESSAGE = """
⚠️ WARNING: You are about to perform an operation that may have significant impact.

Please review the details below carefully before proceeding:

- Operation: {operation}
- Resource: {resource_type} '{identifier}'
- Risk Level: {risk_level}

This operation requires explicit confirmation.
To confirm, please call this function again with the confirmation parameter.
"""

# Engine port mapping
ENGINE_PORT_MAP = {
    'aurora': 3306,
    'aurora-mysql': 3306,
    'aurora-postgresql': 5432,
    'mysql': 3306,
    'postgres': 5432,
    'mariadb': 3306,
    'oracle': 1521,
    'sqlserver': 1433,
}

# Operation impacts - used to inform users about the potential impact of operations
OPERATION_IMPACTS = {
    'create_db_cluster': {
        'risk': 'low',
        'downtime': 'None',
        'data_loss': 'None',
        'reversible': 'Yes - can be deleted',
        'estimated_time': '5-10 minutes',
    },
    'modify_db_cluster': {
        'risk': 'medium',
        'downtime': 'Varies based on changes and apply_immediately setting',
        'data_loss': 'None expected',
        'reversible': 'Yes - can be modified again',
        'estimated_time': '5-30 minutes',
    },
    'delete_db_cluster': {
        'risk': 'critical',
        'downtime': 'Complete',
        'data_loss': 'Complete unless final snapshot is created',
        'reversible': 'No - unless restored from backup',
        'estimated_time': '5-10 minutes',
    },
    'start_db_cluster': {
        'risk': 'low',
        'downtime': 'None',
        'data_loss': 'None',
        'reversible': 'Yes - can be stopped again',
        'estimated_time': '3-8 minutes',
    },
    'stop_db_cluster': {
        'risk': 'high',
        'downtime': 'Complete until started again',
        'data_loss': 'None',
        'reversible': 'Yes - can be started again',
        'estimated_time': '3-8 minutes',
    },
    'reboot_db_cluster': {
        'risk': 'high',
        'downtime': 'Brief interruption',
        'data_loss': 'None expected',
        'reversible': 'Not applicable',
        'estimated_time': '2-5 minutes',
    },
    'failover_db_cluster': {
        'risk': 'high',
        'downtime': 'Brief interruption',
        'data_loss': 'Uncommitted transactions may be lost',
        'reversible': 'Yes - can failover again',
        'estimated_time': '1-3 minutes',
    },
    'create_db_instance': {
        'risk': 'low',
        'downtime': 'None',
        'data_loss': 'None',
        'reversible': 'Yes - can be deleted',
        'estimated_time': '5-10 minutes',
    },
    'modify_db_instance': {
        'risk': 'medium',
        'downtime': 'Varies based on changes and apply_immediately setting',
        'data_loss': 'None expected',
        'reversible': 'Yes - can be modified again',
        'estimated_time': '5-30 minutes',
    },
    'delete_db_instance': {
        'risk': 'critical',
        'downtime': 'Complete',
        'data_loss': 'Complete unless final snapshot is created',
        'reversible': 'No - unless restored from backup',
        'estimated_time': '5-10 minutes',
    },
    'start_db_instance': {
        'risk': 'low',
        'downtime': 'None',
        'data_loss': 'None',
        'reversible': 'Yes - can be stopped again',
        'estimated_time': '3-8 minutes',
    },
    'stop_db_instance': {
        'risk': 'high',
        'downtime': 'Complete until started again',
        'data_loss': 'None',
        'reversible': 'Yes - can be started again',
        'estimated_time': '3-8 minutes',
    },
    'reboot_db_instance': {
        'risk': 'high',
        'downtime': 'Brief interruption',
        'data_loss': 'None expected',
        'reversible': 'Not applicable',
        'estimated_time': '1-3 minutes',
    },
    'create_db_snapshot': {
        'risk': 'low',
        'downtime': 'None',
        'data_loss': 'None',
        'reversible': 'Yes - can be deleted',
        'estimated_time': 'Varies with database size',
    },
    'delete_db_snapshot': {
        'risk': 'high',
        'downtime': 'None',
        'data_loss': 'Snapshot will be permanently deleted',
        'reversible': 'No',
        'estimated_time': '1-5 minutes',
    },
    'restore_db_cluster_from_snapshot': {
        'risk': 'medium',
        'downtime': 'None (new cluster)',
        'data_loss': 'None',
        'reversible': 'Yes - can be deleted',
        'estimated_time': '10-30 minutes',
    },
    'restore_db_instance_from_snapshot': {
        'risk': 'medium',
        'downtime': 'None (new instance)',
        'data_loss': 'None',
        'reversible': 'Yes - can be deleted',
        'estimated_time': '10-30 minutes',
    },
    'restore_db_cluster_to_point_in_time': {
        'risk': 'medium',
        'downtime': 'None (new cluster)',
        'data_loss': 'None',
        'reversible': 'Yes - can be deleted',
        'estimated_time': '10-30 minutes',
    },
    'restore_db_instance_to_point_in_time': {
        'risk': 'medium',
        'downtime': 'None (new instance)',
        'data_loss': 'None',
        'reversible': 'Yes - can be deleted',
        'estimated_time': '10-30 minutes',
    },
    'modify_db_cluster_parameter_group': {
        'risk': 'medium',
        'downtime': 'Depends on parameters (may require reboot)',
        'data_loss': 'None expected',
        'reversible': 'Yes - can be modified again',
        'estimated_time': '1-5 minutes',
    },
    'modify_db_parameter_group': {
        'risk': 'medium',
        'downtime': 'Depends on parameters (may require reboot)',
        'data_loss': 'None expected',
        'reversible': 'Yes - can be modified again',
        'estimated_time': '1-5 minutes',
    },
    'reset_db_cluster_parameter_group': {
        'risk': 'high',
        'downtime': 'Depends on parameters (may require reboot)',
        'data_loss': 'None expected',
        'reversible': 'Yes - can be modified again',
        'estimated_time': '1-5 minutes',
    },
    'reset_db_parameter_group': {
        'risk': 'high',
        'downtime': 'Depends on parameters (may require reboot)',
        'data_loss': 'None expected',
        'reversible': 'Yes - can be modified again',
        'estimated_time': '1-5 minutes',
    },
}
