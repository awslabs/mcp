"""Amazon SQS tools for the MCP server."""
from aws_service_mcp_generator.generator import BOTO3_CLIENT_GETTER, AWSToolGenerator
from awslabs.amazon_sns_sqs_mcp_server.common import (
    MCP_SERVER_VERSION_TAG,
    validate_mcp_server_version_tag,
)
from awslabs.amazon_sns_sqs_mcp_server.consts import MCP_SERVER_VERSION
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
        if queue_name.endswith(".fifo"):
            create_params['Attributes']["FifoQueue"] = "true"
            create_params["Attributes"]["DeduplicationScope"] = "messageGroup"
            create_params["Attributes"]["FifoThroughputLimit"] = "perMessageGroupId"

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


def register_sqs_tools(mcp: FastMCP):
    """Register SQS tools with the MCP server."""
    # Generate SQS tools
    sqs_generator = AWSToolGenerator(
        service_name='sqs',
        service_display_name='Amazon SQS',
        mcp=mcp,
        tool_configuration={
            'close': {'ignore': True},
            'can_paginate': {'ignore': True},
            'generate_presigned_url': {'ignore': True},
            'untag_queue': {'ignore': True},
            'tag_queue': {'ignore': True},
            'create_queue': {'func_override': create_queue_override},
            'delete_queue': {'validator': is_mutative_action_allowed},
            'set_queue_attributes': {'validator': is_mutative_action_allowed},
            'send_message': {'validator': is_mutative_action_allowed},
            'receive_message': {'validator': is_mutative_action_allowed},
            'send_message_batch': {'validator': is_mutative_action_allowed},
            'delete_message': {'validator': is_mutative_action_allowed},
        },
        skip_param_documentation=True
    )
    sqs_generator.generate()
