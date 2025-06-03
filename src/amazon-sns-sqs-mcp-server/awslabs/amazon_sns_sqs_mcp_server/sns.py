# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
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

"""Amazon SNS tools for the MCP server."""

from awslabs.amazon_sns_sqs_mcp_server.common import (
    MCP_SERVER_VERSION_TAG,
    validate_mcp_server_version_tag,
)
from awslabs.amazon_sns_sqs_mcp_server.consts import MCP_SERVER_VERSION
from awslabs.amazon_sns_sqs_mcp_server.generator import BOTO3_CLIENT_GETTER, AWSToolGenerator
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List, Tuple


# override create_topic tool to tag resources
def create_topic_override(mcp: FastMCP, sns_client_getter: BOTO3_CLIENT_GETTER, _: str):
    """Create an SNS topic with MCP server version tag."""

    @mcp.tool()
    def create_topic(
        name: str,
        attributes: Dict[str, str] = {},
        tags: List[Dict[str, str]] = [],
        region: str = 'us-east-1',
    ):
        create_params = {
            'Name': name,
            'Attributes': attributes.copy(),  # Create a copy to avoid modifying the original
        }

        # Set FIFO topic attributes if name ends with .fifo
        if name.endswith('.fifo'):
            create_params['Attributes']['FifoTopic'] = 'true'
            create_params['Attributes']['FifoThroughputScope'] = 'MessageGroup'

        # Add MCP server version tag
        tags_copy = tags.copy()
        tags_copy.append({'Key': MCP_SERVER_VERSION_TAG, 'Value': MCP_SERVER_VERSION})

        create_params['Tags'] = tags_copy

        sns_client = sns_client_getter(region)
        response = sns_client.create_topic(**create_params)
        return response


# Define validator for SNS resources
def is_mutative_action_allowed(
    mcp: FastMCP, sns_client: Any, kwargs: Dict[str, Any]
) -> Tuple[bool, str]:
    """Check if the SNS resource being mutated is tagged with mcp_server_version."""
    # Check for TopicArn (used by most operations)
    resource_arn = kwargs.get('TopicArn')

    if resource_arn is None or resource_arn == '':
        return False, 'TopicArn is not passed to the tool'

    try:
        tags = sns_client.list_tags_for_resource(ResourceArn=resource_arn)
        tag_dict = {tag.get('Key'): tag.get('Value') for tag in tags.get('Tags', [])}
        return validate_mcp_server_version_tag(tag_dict)
    except Exception as e:
        return False, str(e)


# Define validator specifically for unsubscribe operation
def is_unsubscribe_allowed(
    mcp: FastMCP, sns_client: Any, kwargs: Dict[str, Any]
) -> Tuple[bool, str]:
    """Check if the SNS subscription being unsubscribed is from a tagged topic."""
    subscription_arn = kwargs.get('SubscriptionArn')

    if subscription_arn is None or subscription_arn == '':
        return False, 'SubscriptionArn is not passed to the tool'

    try:
        # Get subscription attributes to find the TopicArn
        attributes = sns_client.get_subscription_attributes(SubscriptionArn=subscription_arn)
        topic_arn = attributes.get('Attributes', {}).get('TopicArn')

        return is_mutative_action_allowed(mcp, sns_client, {'TopicArn': topic_arn})

    except Exception as e:
        return False, str(e)


def register_sns_tools(mcp: FastMCP, disallow_resource_creation: bool = False):
    """Register SNS tools with the MCP server."""
    # Generate SNS tools

    # List of operations to ignore
    operations_to_ignore = [
        # Common operations to ignore
        'close',
        'can_paginate',
        'generate_presigned_url',
        'untag_resource',
        'tag_resource',
        # A2P Related operations
        'create_sms_sandbox_phone_number',
        'delete_sms_sandbox_phone_number',
        'get_waiter',
        'set_sms_attributes',
        'create_platform_application',
        'create_platform_endpoint',
        'delete_endpoint',
        'delete_platform_application',
        'remove_permission',
        'set_endpoint_attributes',
        'set_platform_application_attributes',
    ]

    # Create the tool configuration dictionary
    tool_configuration = {
        'add_permission': {'name_override': 'add_sns_permission'},
        'remove_permission': {'name_override': 'remove_sns_permission'},
        'create_topic': {'func_override': create_topic_override},
        'delete_topic': {'validator': is_mutative_action_allowed},
        'set_topic_attributes': {'validator': is_mutative_action_allowed},
        'subscribe': {
            'validator': is_mutative_action_allowed,
            'documentation_override': 'Execute AWS SNS Subscribe. Ensure that you set correct permission policies if required.',
        },
        'unsubscribe': {'validator': is_unsubscribe_allowed},
        'confirm_subscription': {'validator': is_mutative_action_allowed},
        'publish': {'validator': is_mutative_action_allowed},
        'publish_batch': {'validator': is_mutative_action_allowed},
    }

    # Add all operations to ignore to the tool configuration
    for operation in operations_to_ignore:
        tool_configuration[operation] = {'ignore': True}

    if disallow_resource_creation:
        tool_configuration['create_topic'] = {'ignore': True}
        tool_configuration['delete_topic'] = {'ignore': True}

    sns_generator = AWSToolGenerator(
        service_name='sns',
        service_display_name='Amazon SNS',
        mcp=mcp,
        mcp_server_version=MCP_SERVER_VERSION,
        tool_configuration=tool_configuration,
        skip_param_documentation=True,
    )
    sns_generator.generate()
