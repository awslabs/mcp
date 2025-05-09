"""Amazon SNS tools for the MCP server."""
from aws_service_mcp_generator.generator import BOTO3_CLIENT_GETTER, AWSToolGenerator
from awslabs.amazon_sns_sqs_mcp_server.common import (
    MCP_SERVER_VERSION_TAG,
    validate_mcp_server_version_tag,
)
from awslabs.amazon_sns_sqs_mcp_server.consts import MCP_SERVER_VERSION
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
        if name.endswith(".fifo"):
            create_params['Attributes']["FifoTopic"] = "true"
            create_params['Attributes']["FifoThroughputScope"] = "MessageGroup"

        # Add MCP server version tag
        tags_copy = tags.copy()
        tags_copy.append({
            'Key': MCP_SERVER_VERSION_TAG,
            'Value': MCP_SERVER_VERSION
        })

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

        return is_mutative_action_allowed(mcp, sns_client, {"TopicArn": topic_arn})

    except Exception as e:
        return False, str(e)

def register_sns_tools(mcp: FastMCP):
    """Register SNS tools with the MCP server."""
    # Generate SNS tools
    sns_generator = AWSToolGenerator(
        service_name='sns',
        service_display_name='Amazon SNS',
        mcp=mcp, tool_configuration={
            'close': {'ignore': True},
            'can_paginate': {'ignore': True},
            'generate_presigned_url': {'ignore': True},
            'untag_resource': {'ignore': True},
            'tag_resource': {'ignore': True},
            'create_topic': {'func_override': create_topic_override},
            'delete_topic': {'validator': is_mutative_action_allowed},
            'set_topic_attributes': {'validator': is_mutative_action_allowed},
            'subscribe': {'validator': is_mutative_action_allowed, "documentation_override": "Execute AWS SNS Subscribe. Ensure that you set correct permission policies if required."},
            'unsubscribe': {'validator': is_unsubscribe_allowed},
            'confirm_subscription': {'validator': is_mutative_action_allowed},
            'publish': {'validator': is_mutative_action_allowed},
            'publish_batch': {'validator': is_mutative_action_allowed},
        },
            skip_param_documentation=True,
    )
    sns_generator.generate()
