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

"""Tool for creating a CloudWatch Logs log group."""

from ...common.connection import CloudWatchLogsConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from ...context import Context
from typing import Any, Dict, Optional


@mcp.tool(name='create-log-group')
@handle_exceptions
async def create_log_group(
    log_group_name: str,
    kms_key_id: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    log_group_class: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new CloudWatch Logs log group.

    Args:
        log_group_name: The name of the log group to create
        kms_key_id: The Amazon Resource Name (ARN) of the KMS key to use for encryption
        tags: The key-value pairs to use for the tags
        log_group_class: Specify one of the following classes:
            STANDARD - Standard log events (default)
            INFREQUENT_ACCESS - Infrequent Access log events

    Returns:
        Dict containing success message or error details
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        raise ValueError(
            'You have configured this tool in readonly mode. To make this change you will have to update your configuration.'
        )

    client = CloudWatchLogsConnectionManager.get_connection()

    # Build request parameters
    params: Dict[str, Any] = {
        'logGroupName': log_group_name,
    }

    # Add optional parameters
    if kms_key_id:
        params['kmsKeyId'] = kms_key_id
    if tags:
        params['tags'] = tags
    if log_group_class:
        params['logGroupClass'] = log_group_class

    # Make API call
    client.create_log_group(**params)
    return {'message': f'Successfully created log group: {log_group_name}'}
