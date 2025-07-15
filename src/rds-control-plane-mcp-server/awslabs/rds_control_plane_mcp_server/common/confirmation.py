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
from ..constants import (
    OPERATION_IMPACTS,
    STANDARD_CONFIRMATION_MESSAGE,
)
from ..context import RDSContext
from .exceptions import ConfirmationRequiredException, ReadOnlyModeException
from functools import wraps
from inspect import iscoroutinefunction, signature
from mcp.server.fastmcp import Context as FastMCPContext
from typing import Any, Callable, Dict, Optional


# dictionary to store pending operations
# key: confirmation_token, value: (operation_type, params, expiration_time)
_pending_operations = {}


# expiration time for pending operations (in seconds)
EXPIRATION_TIME = 300  # 5 minutes


def generate_confirmation_token() -> str:
    """Generate a unique confirmation token.

    Returns:
        str: A unique confirmation token
    """
    return str(uuid.uuid4())


def add_pending_operation(operation_type: str, params: Dict[str, Any]) -> str:
    """Add a pending operation.

    Args:
        operation_type: The type of operation (e.g., 'delete_db_cluster')
        params: The parameters for the operation

    Returns:
        str: The confirmation token for the operation
    """
    token = generate_confirmation_token()
    expiration_time = time.time() + EXPIRATION_TIME
    _pending_operations[token] = (operation_type, params, expiration_time)
    return token


def get_pending_operation(token: str) -> Optional[tuple]:
    """Get a pending operation by its confirmation token.

    Args:
        token: The confirmation token

    Returns:
        Optional[tuple]: The operation type, parameters, and expiration time, or None if not found
    """
    # clean up expired operations
    cleanup_expired_operations()

    # return the operation if it exists
    return _pending_operations.get(token)


def remove_pending_operation(token: str) -> bool:
    """Remove a pending operation.

    Args:
        token: The confirmation token

    Returns:
        bool: True if the operation was removed, False otherwise
    """
    if token in _pending_operations:
        del _pending_operations[token]
        return True
    return False


def cleanup_expired_operations() -> None:
    """Clean up expired operations."""
    current_time = time.time()
    expired_tokens = [
        token
        for token, (_, _, expiration_time) in _pending_operations.items()
        if expiration_time < current_time
    ]
    for token in expired_tokens:
        del _pending_operations[token]


def get_operation_impact(operation: str) -> Dict[str, Any]:
    """Get detailed impact information for an operation.

    Args:
        operation: The operation name

    Returns:
        Dictionary with impact details
    """
    if operation in OPERATION_IMPACTS:
        return OPERATION_IMPACTS[operation]

    # default impact for unknown operations
    return {
        'risk': get_operation_risk_level(operation),
        'downtime': 'Unknown',
        'data_loss': 'Unknown',
        'reversible': 'Unknown',
        'estimated_time': 'Unknown',
    }


def get_operation_risk_level(operation: str) -> str:
    """Get the risk level for an operation.

    Args:
        operation: The operation name

    Returns:
        Risk level (low, high, or critical)
    """
    if operation in OPERATION_IMPACTS:
        return OPERATION_IMPACTS[operation]['risk']

    # default risk levels based on operation type
    if operation.startswith('delete_'):
        return 'critical'
    elif operation.startswith(('modify_', 'stop_', 'reboot_', 'failover_')):
        return 'high'
    else:
        return 'low'


def readonly_check(func: Callable) -> Callable:
    """Decorator to check if operation is allowed in readonly mode.

    This decorator automatically checks if the server is in readonly mode
    and blocks write operations. It determines the operation type from
    the function name.

    Args:
        func: The function to wrap

    Returns:
        The wrapped function that checks readonly mode
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any):
        ctx = kwargs.get('ctx')
        if not ctx:
            for arg in args:
                if isinstance(arg, FastMCPContext):
                    ctx = arg
                    break

        func_name = func.__name__.lower()
        is_read_operation = any(
            func_name.startswith(prefix) for prefix in ['describe', 'list', 'get', 'read']
        )

        if not is_read_operation and RDSContext.readonly_mode():
            raise ReadOnlyModeException(func.__name__)

        if iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)

    return wrapper


def require_confirmation(operation_type: str) -> Callable:
    """Decorator to require confirmation for destructive operations.

    This decorator handles the confirmation flow for operations that
    require explicit user confirmation before proceeding. It uses a
    standardized confirmation message from constants.py.

    Args:
        operation_type: The type of operation (e.g., 'delete_db_cluster')

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any):
            confirmation_token = kwargs.get('confirmation_token')

            if not confirmation_token:
                sig = signature(func)
                params = {}
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()

                for param_name, param_value in bound_args.arguments.items():
                    if param_name not in ['ctx', 'confirmation_token']:
                        params[param_name] = param_value

                impact = get_operation_impact(operation_type)

                resource_type = 'resource'
                identifier = 'unknown'

                if 'db_cluster_identifier' in params:
                    resource_type = 'DB cluster'
                    identifier = params['db_cluster_identifier']
                elif 'db_instance_identifier' in params:
                    resource_type = 'DB instance'
                    identifier = params['db_instance_identifier']
                elif 'db_snapshot_identifier' in params:
                    resource_type = 'DB snapshot'
                    identifier = params['db_snapshot_identifier']

                operation_name = operation_type.replace('_', ' ').title()

                warning_message = STANDARD_CONFIRMATION_MESSAGE.format(
                    operation=operation_name,
                    resource_type=resource_type,
                    identifier=identifier,
                    risk_level=impact.get('risk', 'Unknown'),
                )

                token = add_pending_operation(operation_type, params)
                raise ConfirmationRequiredException(
                    operation=operation_type,
                    confirmation_token=token,
                    warning_message=warning_message,
                    impact=impact,
                )
            pending_op = get_pending_operation(confirmation_token)
            if not pending_op:
                return {
                    'error': 'Invalid or expired confirmation token. Please request a new token by calling this function without a confirmation_token parameter.'
                }
            op_type, stored_params, _ = pending_op

            if op_type != operation_type:
                return {
                    'error': f'Invalid operation type. Expected "{operation_type}", got "{op_type}".'
                }

            sig = signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            for key in ['db_cluster_identifier', 'db_instance_identifier']:
                if key in stored_params and key in bound_args.arguments:
                    if stored_params[key] != bound_args.arguments[key]:
                        return {
                            'error': f'Parameter mismatch. The confirmation token is for a different {key}.'
                        }

            remove_pending_operation(confirmation_token)

            if iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)

        return wrapper

    return decorator
