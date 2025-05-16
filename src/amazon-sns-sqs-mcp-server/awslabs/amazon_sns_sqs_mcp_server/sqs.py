#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

"""Amazon SQS tools for the MCP server."""

from awslabs.amazon_sns_sqs_mcp_server.common import (
    MCP_SERVER_VERSION_TAG,
    validate_mcp_server_version_tag,
)
from awslabs.amazon_sns_sqs_mcp_server.consts import MCP_SERVER_VERSION
from awslabs.amazon_sns_sqs_mcp_server.generator import BOTO3_CLIENT_GETTER, AWSToolGenerator
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, Tuple


# override create_queue tool to tag resources
def create_queue_override(mcp: FastMCP, sqs_client_getter: BOTO3_CLIENT_GETTER, _: str):
    """Create an SQS queue with MCP server version tag."""

    @mcp.tool()
    def create_queue(
        queue_name: str,
        attributes: Dict[str, str] = {},
        tags: Dict[str, str] = {},
        region: str = 'us-east-1',
    ):
        create_params = {
            'QueueName': queue_name,
            'Attributes': attributes.copy(),  # Create a copy to avoid modifying the original
        }

        # Set FIFO queue attributes if name ends with .fifo
        if queue_name.endswith('.fifo'):
            create_params['Attributes']['FifoQueue'] = 'true'
            create_params['Attributes']['DeduplicationScope'] = 'messageGroup'
            create_params['Attributes']['FifoThroughputLimit'] = 'perMessageGroupId'

        # Add MCP server version tag
        tags_copy = tags.copy()
        tags_copy[MCP_SERVER_VERSION_TAG] = MCP_SERVER_VERSION

        create_params['tags'] = tags_copy

        sqs_client = sqs_client_getter(region)
        response = sqs_client.create_queue(**create_params)
        return response


# Define validator for SQS resources
def is_mutative_action_allowed(
    mcp: FastMCP, sqs_client: Any, kwargs: Dict[str, Any]
) -> Tuple[bool, str]:
    """Check if the SQS resource being mutated is tagged with mcp_server_version."""
    queue_url = kwargs.get('QueueUrl')
    if queue_url is None or queue_url == '':
        return False, 'QueueUrl is not passed to the tool'
    try:
        tags = sqs_client.list_queue_tags(QueueUrl=queue_url)
        tag_dict = tags.get('Tags', {})
        return validate_mcp_server_version_tag(tag_dict)
    except Exception as e:
        return False, str(e)


def register_sqs_tools(mcp: FastMCP, disallow_resource_creation: bool = False):
    """Register SQS tools with the MCP server."""
    # Generate SQS tools

    # List of operations to ignore
    operations_to_ignore = [
        # Common operations to ignore
        'close',
        'can_paginate',
        'generate_presigned_url',
        'untag_queue',
        'tag_queue',
        'get_waiter',
        'get_paginator',  # Currently not found in BOTO3
    ]

    # Create the tool configuration dictionary
    tool_configuration = {
        'add_permission': {'name_override': 'add_sqs_permission'},
        'remove_permission': {'name_override': 'remove_sqs_permission'},
        'create_queue': {'func_override': create_queue_override},
        'delete_queue': {'validator': is_mutative_action_allowed},
        'set_queue_attributes': {'validator': is_mutative_action_allowed},
        'send_message': {'validator': is_mutative_action_allowed},
        'receive_message': {'validator': is_mutative_action_allowed},
        'send_message_batch': {'validator': is_mutative_action_allowed},
        'delete_message': {'validator': is_mutative_action_allowed},
    }

    # Add all operations to ignore to the tool configuration
    for operation in operations_to_ignore:
        tool_configuration[operation] = {'ignore': True}
    if disallow_resource_creation:
        tool_configuration['create_queue'] = {'ignore': True}
        tool_configuration['delete_queue'] = {'ignore': True}

    sqs_generator = AWSToolGenerator(
        service_name='sqs',
        service_display_name='Amazon SQS',
        mcp=mcp,
        mcp_server_version=MCP_SERVER_VERSION,
        tool_configuration=tool_configuration,
        skip_param_documentation=True,
    )
    sqs_generator.generate()
