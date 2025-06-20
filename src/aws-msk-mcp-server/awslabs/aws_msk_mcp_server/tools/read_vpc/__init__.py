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

"""
VPC Connection Information API Module

This module provides functions to retrieve information about MSK VPC connections.
"""

import boto3
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .describe_vpc_connection import describe_vpc_connection


def register_module(mcp: FastMCP) -> None:
    @mcp.tool(name='describe_vpc_connection')
    def describe_vpc_connection_tool(
        region: str = Field(..., description='AWS region'),
        vpc_connection_arn: str = Field(
            ..., description='The Amazon Resource Name (ARN) of the VPC connection'
        ),
    ):
        """
        Get detailed information about a VPC connection.

        Args:
            vpc_connection_arn (str): The Amazon Resource Name (ARN) of the VPC connection
            region (str): AWS region

        Returns:
            dict: Information about the VPC connection including:
                - Authentication: Authentication settings for the VPC connection
                - ClientSubnets: List of client subnet IDs
                - ClusterArn: The Amazon Resource Name (ARN) of the cluster
                - CreationTime: The time when the VPC connection was created
                - SecurityGroups: List of security group IDs
                - SubnetIds: List of subnet IDs
                - Tags: Tags attached to the VPC connection
                - VpcConnectionArn: The Amazon Resource Name (ARN) of the VPC connection
                - VpcConnectionState: The state of the VPC connection
                - VpcId: The ID of the VPC
        """
        # Create a boto3 client
        client = boto3.client('kafka', region_name=region)
        return describe_vpc_connection(vpc_connection_arn, client)
