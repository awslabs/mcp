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

"""Confirmation and permission management for the RDS Control Plane MCP Server."""

import time
import uuid
from functools import wraps
from inspect import iscoroutinefunction, signature
from loguru import logger
from typing import Any, Callable, Dict, Optional, Tuple


# Expiration time for pending operations (in seconds)
EXPIRATION_TIME = 300  # 5 minutes

STANDARD_CONFIRMATION_MESSAGE = """
WARNING: You are about to perform an operation that may have significant impact.

Please review the details below carefully before proceeding:

- Operation: {operation}
- Resource: {resource_type} '{identifier}'
- Risk Level: {risk_level}

This operation requires explicit confirmation.
To confirm, please call this function again with the confirmation parameter.
"""

# Operation impacts - used to inform users about the potential impact of operations
OPERATION_IMPACTS = {
    'DeleteDBCluster': {
        'risk': 'critical',
        'downtime': 'Complete',
        'data_loss': 'Complete unless final snapshot is created',
        'reversible': 'No - unless restored from backup',
        'estimated_time': '5-10 minutes',
    },
    'DeleteDBInstance': {
        'risk': 'critical',
        'downtime': 'Complete',
        'data_loss': 'Complete unless final snapshot is created',
        'reversible': 'No - unless restored from backup',
        'estimated_time': '5-10 minutes',
    },
    'ChangeDBClusterStatus': {
        'risk': 'high',
        'downtime': 'Varies by action (complete for stop, brief for reboot)',
        'data_loss': 'None expected',
        'reversible': 'Yes - can change status again',
        'estimated_time': '2-8 minutes',
    },
    'ChangeDBInstanceStatus': {
        'risk': 'high',
        'downtime': 'Varies by action (complete for stop, brief for reboot)',
        'data_loss': 'None expected',
        'reversible': 'Yes - can change status again',
        'estimated_time': '2-8 minutes',
    },
    'FailoverDBCluster': {
        'risk': 'high',
        'downtime': 'Brief interruption',
        'data_loss': 'Uncommitted transactions may be lost',
        'reversible': 'Yes - can failover again',
        'estimated_time': '1-3 minutes',
    },
}

RESOURCE_MAPPINGS = {
    'db_cluster_identifier': 'DB cluster',
    'db_instance_identifier': 'DB instance',
    'db_snapshot_identifier': 'DB snapshot',
}

# dictionary to store pending operations
# key: confirmation_token, value: (operation_type, params, expiration_time)
_pending_operations = {}


def _get_operation_impact(operation: str) -> Dict[str, Any]:
    """Get detailed impact information for an operation.

    Args:
        operation: The operation name
    Returns:
        Dictionary with impact details
    Raises:
        ValueError: If operation is not defined in OPERATION_IMPACTS
    """
    if operation not in OPERATION_IMPACTS:
        raise ValueError(f"Operation '{operation}' is not defined in OPERATION_IMPACTS")

    return OPERATION_IMPACTS[operation]


def _get_resource_info(params: Dict[str, Any]) -> Tuple[str, str]:
    """Extract resource type and identifier from parameters."""
    for param_name, resource_type in RESOURCE_MAPPINGS.items():
        if param_name in params and params[param_name]:
            return resource_type, params[param_name]
    return 'resource', 'unknown'


def _cleanup_expired_operations() -> None:
    """Remove expired operations from the pending operations dictionary."""
    current_time = time.time()
    expired_tokens = [
        token
        for token, (_, _, expiration_time) in _pending_operations.items()
        if expiration_time < current_time
    ]
    for token in expired_tokens:
        del _pending_operations[token]


def _validate_confirmation_token(
    token: str, operation_type: str, params: Dict[str, Any]
) -> Optional[Dict[str, str]]:
    """Validate a confirmation token.

    Args:
        token: The confirmation token to validate
        operation_type: The expected operation type
        params: The current operation parameters

    Returns:
        Error dict if validation fails, None if validation succeeds
    """
    # Validate token
    pending_op = _pending_operations.get(token)
    if not pending_op:
        return {
            'error': 'Invalid or expired confirmation token. Please request a new token by calling this tool without the confirmation token set.'
        }

    op_type, stored_params, _ = pending_op

    # Validate operation type
    if op_type != operation_type:
        return {'error': f'Invalid operation type. Expected "{operation_type}", got "{op_type}".'}

    # Validate resource identifiers
    for key in ['db_cluster_identifier', 'db_instance_identifier', 'db_snapshot_identifier']:
        if key in stored_params and key in params and stored_params[key] != params[key]:
            return {
                'error': f'Parameter mismatch. The confirmation token is for a different {key}.'
            }

    return None


def require_confirmation(operation_type: str) -> Callable:
    """Decorator to require confirmation for destructive operations.

    Args:
        operation_type: The type of operation (e.g., 'DeleteDBCluster')

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any):
            confirmation_token = kwargs.get('confirmation_token')

            _cleanup_expired_operations()

            sig = signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            params = {}
            for param_name, param_value in bound_args.arguments.items():
                if param_name not in ['ctx', 'confirmation_token']:
                    params[param_name] = param_value

            if not confirmation_token:
                impact = _get_operation_impact(operation_type)
                resource_type, identifier = _get_resource_info(params)
                operation_name = operation_type.replace('_', ' ').title()

                token = str(uuid.uuid4())
                _pending_operations[token] = (
                    operation_type,
                    params,
                    time.time() + EXPIRATION_TIME,
                )

                warning_message = STANDARD_CONFIRMATION_MESSAGE.format(
                    operation=operation_name,
                    resource_type=resource_type,
                    identifier=identifier,
                    risk_level=impact.get('risk', 'Unknown'),
                )

                logger.info(f'Confirmation required for operation: {operation_type}')
                return {
                    'requires_confirmation': True,
                    'warning': warning_message,
                    'impact': impact,
                    'confirmation_token': token,
                    'message': 'To confirm, please call this function again with the confirmation_token parameter set to this token.',
                }

            error = _validate_confirmation_token(confirmation_token, operation_type, params)
            if error:
                return error

            # Remove the pending operation
            del _pending_operations[confirmation_token]

            # Execute the function
            if iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)

        return wrapper

    return decorator
