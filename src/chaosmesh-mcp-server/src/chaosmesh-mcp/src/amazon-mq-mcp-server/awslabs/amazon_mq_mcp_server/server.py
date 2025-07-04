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
import argparse
from awslabs.amazon_mq_mcp_server.aws_service_mcp_generator import (
    BOTO3_CLIENT_GETTER,
    AWSToolGenerator,
)
from awslabs.amazon_mq_mcp_server.consts import MCP_SERVER_VERSION
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List


# override create_broker tool to tag resources
def create_broker_override(mcp: FastMCP, mq_client_getter: BOTO3_CLIENT_GETTER, _: str):
    """Create a ActiveMQ or RabbitMQ broker on AmazonMQ."""

    @mcp.tool()
    def create_broker(
        broker_name: str,
        engine_type: str,
        engine_version: str,
        host_instance_type: str,
        deployment_mode: str,
        publicly_accessible: bool,
        auto_minor_version_upgrade: bool,
        users: List[Dict[str, str]],
        region: str = 'us-east-1',
    ):
        """Create a ActiveMQ or RabbitMQ broker on AmazonMQ."""
        create_params = {
            'BrokerName': broker_name,
            'EngineType': engine_type,
            'EngineVersion': engine_version,
            'HostInstanceType': host_instance_type,
            'DeploymentMode': deployment_mode,
            'PubliclyAccessible': publicly_accessible,
            'AutoMinorVersionUpgrade': auto_minor_version_upgrade,
            'Users': users,
            'Tags': {
                'mcp_server_version': MCP_SERVER_VERSION,
            },
        }
        mq_client = mq_client_getter(region)
        response = mq_client.create_broker(**create_params)
        return response


# override create_configuration tool to tag resources
def create_configuration_override(mcp: FastMCP, mq_client_getter: BOTO3_CLIENT_GETTER, _: str):
    """Create configuration for AmazonMQ broker."""

    @mcp.tool()
    def create_configuration(
        region: str, authentication_strategy: str, engine_type: str, engine_version: str, name: str
    ):
        """Create configuration for AmazonMQ broker."""
        create_params = {
            'AuthenticationStrategy': authentication_strategy,
            'EngineType': engine_type,
            'EngineVersion': engine_version,
            'Name': name,
            'Tags': {
                'mcp_server_version': MCP_SERVER_VERSION,
            },
        }
        mq_client = mq_client_getter(region)
        response = mq_client.create_configuration(**create_params)
        return response


# Define validator such that only resource tagged with mcp_server_version can be mutated
def allow_mutative_action_only_on_tagged_resource(
    mcp: FastMCP, mq_client: Any, kwargs: Dict[str, Any]
) -> tuple[bool, str]:
    """Check if the resource being mutated is tagged with mcp_server_version."""
    broker_id = kwargs.get('BrokerId')
    if broker_id is None or broker_id == '':
        return False, 'BrokerId is not passed to the tool'
    try:
        broker_info = mq_client.describe_broker(BrokerId=broker_id)
        tags = broker_info.get('Tags')
        if 'mcp_server_version' not in tags:
            return False, 'mutating a resource without the mcp_server_version tag is not allowed'
        return True, ''
    except Exception as e:
        return False, str(e)


# instantiate base server
mcp = FastMCP(
    'awslabs.amazon-mq-mcp-server',
    instructions="""Manage RabbitMQ and ActiveMQ message brokers on AmazonMQ.""",
    dependencies=['pydantic', 'boto3'],
)


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Model Context Protocol (MCP) server for Lambda'
    )
    parser.add_argument(
        '--allow-resource-creation',
        action='store_true',
        help='Hide tools that create resources on user AWS account',
    )
    args = parser.parse_args()

    tool_configuration = {
        'close': {'ignore': True},
        'can_paginate': {'ignore': True},
        'generate_presigned_url': {'ignore': True},
        'create_tags': {'ignore': True},
        'create_user': {'ignore': True},
        'delete_broker': {'validator': allow_mutative_action_only_on_tagged_resource},
        'delete_configuration': {'validator': allow_mutative_action_only_on_tagged_resource},
        'delete_tags': {'ignore': True},
        'delete_user': {'ignore': True},
        'get_paginator': {'ignore': True},
        'get_waiter': {'ignore': True},
        'promote': {'validator': allow_mutative_action_only_on_tagged_resource},
        'reboot_broker': {'validator': allow_mutative_action_only_on_tagged_resource},
        'update_broker': {'validator': allow_mutative_action_only_on_tagged_resource},
        'update_configuration': {'validator': allow_mutative_action_only_on_tagged_resource},
        'update_user': {'ignore': True},
    }
    tool_configuration['create_broker'] = (
        {'ignore': True}
        if not args.allow_resource_creation
        else {'func_override': create_broker_override}
    )
    tool_configuration['create_configuration'] = (
        {'ignore': True}
        if not args.allow_resource_creation
        else {'func_override': create_configuration_override}
    )

    generator = AWSToolGenerator(
        service_name='mq',
        service_display_name='AmazonMQ',
        mcp=mcp,
        tool_configuration=tool_configuration,
    )
    generator.generate()

    mcp.run()


if __name__ == '__main__':
    main()
