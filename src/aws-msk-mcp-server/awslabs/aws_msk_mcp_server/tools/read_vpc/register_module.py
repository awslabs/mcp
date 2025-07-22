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

"""VPC Connection Information API Module.

This module provides functions to retrieve information about MSK VPC connections.
"""

import boto3
from .describe_vpc_connection import describe_vpc_connection
from awslabs.aws_msk_mcp_server import __version__
from botocore.config import Config
from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register_module(mcp: FastMCP) -> None:
    """Registers this tool with the mcp."""

    @mcp.tool(name='describe_vpc_connection')
    def describe_vpc_connection_tool(
        region: str = Field(..., description='AWS region'),
        vpc_connection_arn: str = Field(
            ..., description='The Amazon Resource Name (ARN) of the VPC connection'
        ),
    ):
        """Get detailed information about a VPC connection.

        This operation retrieves comprehensive details about a specific VPC connection for an MSK cluster.

        === INPUT PARAMETERS ===

        - vpc_connection_arn (str): The Amazon Resource Name (ARN) of the VPC connection to describe.
        - region (str): AWS region where the VPC connection is located.

        === OUTPUT (JSON) ===

        {
            "Authentication": {
                "Sasl": {
                    "Iam": {
                        "Enabled": true
                    }
                }
            },
            "ClientSubnets": ["subnet-abcd1234", "subnet-efgh5678"],
            "ClusterArn": "arn:aws:kafka:us-west-2:123456789012:cluster/cluster-name/abcd1234",
            "CreationTime": "2023-01-01T12:00:00.000Z",
            "SecurityGroups": ["sg-abcd1234"],
            "SubnetIds": ["subnet-1234abcd", "subnet-5678efgh"],
            "Tags": {
                "Name": "production-vpc-connection",
                "Environment": "Production"
            },
            "VpcConnectionArn": "arn:aws:kafka:us-west-2:123456789012:vpc-connection/connection-id",
            "VpcConnectionState": "ACTIVE",
            "VpcId": "vpc-abcd1234"
        }

        === NOTES ===

        - VPC connections allow clients in a specific VPC to access an MSK cluster.
        - The VpcConnectionState field indicates the current status (CREATING, AVAILABLE, DELETING, etc.).
        - Authentication settings show which authentication methods are enabled for this connection.
        - Security groups must allow traffic on the appropriate Kafka ports (9092, 9094, 2181).
        """
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )
        return describe_vpc_connection(vpc_connection_arn, client)
