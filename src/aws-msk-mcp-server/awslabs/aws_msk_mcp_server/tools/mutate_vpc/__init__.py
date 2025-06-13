"""
VPC Connection Management API Module

This module provides functions to manage VPC connections for MSK clusters.
"""

import boto3
from mcp.server.fastmcp import FastMCP

from .create_vpc_connection import create_vpc_connection
from .delete_vpc_connection import delete_vpc_connection
from .reject_client_vpc_connection import reject_client_vpc_connection


def register_module(mcp: FastMCP) -> None:
    @mcp.tool(name="create_vpc_connection")
    def create_vpc_connection_tool(
        region,
        cluster_arn,
        vpc_id,
        subnet_ids,
        security_groups,
        authentication_type=None,
        client_subnets=None,
        tags=None,
    ):
        """
        Create a VPC connection for an MSK cluster.

        Args:
            cluster_arn (str): The Amazon Resource Name (ARN) of the cluster
            vpc_id (str): The ID of the VPC to connect to
            subnet_ids (list): A list of subnet IDs for the client VPC connection
                Example: ["subnet-1234abcd", "subnet-5678efgh"]
            security_groups (list): A list of security group IDs for the client VPC connection
                Example: ["sg-1234abcd", "sg-5678efgh"]
            authentication_type (str, optional): The authentication type for the VPC connection (e.g., 'IAM')
            client_subnets (list, optional): A list of client subnet IDs for the VPC connection
                Example: ["subnet-abcd1234", "subnet-efgh5678"]
            tags (dict, optional): A map of tags to attach to the VPC connection
                Example: {"Environment": "Production", "Owner": "DataTeam"}
            region (str): AWS region

        Returns:
            dict: Information about the created VPC connection including:
                - VpcConnectionArn (str): The Amazon Resource Name (ARN) of the VPC connection
                - VpcConnectionState (str): The state of the VPC connection (e.g., CREATING, AVAILABLE)
                - ClusterArn (str): The Amazon Resource Name (ARN) of the cluster
                - Authentication (dict, optional): Authentication settings for the VPC connection
                - CreationTime (datetime): The time when the VPC connection was created
                - VpcId (str): The ID of the VPC

        Note:
            After creating a VPC connection, you should follow up with a tag_resource tool call
            to add the "MCP Generated" tag to the created resource.
            Example:
            tag_resource_tool(resource_arn=response["VpcConnectionArn"], tags={"MCP Generated": "true"})
        """
        # Create a boto3 client
        client = boto3.client("kafka", region_name=region)
        return create_vpc_connection(
            cluster_arn=cluster_arn,
            vpc_id=vpc_id,
            subnet_ids=subnet_ids,
            security_groups=security_groups,
            client=client,
            authentication_type=authentication_type,
            client_subnets=client_subnets,
            tags=tags,
        )

    @mcp.tool(name="delete_vpc_connection")
    def delete_vpc_connection_tool(region, vpc_connection_arn):
        """
        Delete a VPC connection for an MSK cluster.

        Args:
            vpc_connection_arn (str): The Amazon Resource Name (ARN) of the VPC connection to delete
            region (str): AWS region

        Returns:
            dict: Information about the deleted VPC connection including:
                - VpcConnectionArn (str): The Amazon Resource Name (ARN) of the VPC connection
                - VpcConnectionState (str): The state of the VPC connection (should be DELETING)
                - ClusterArn (str): The Amazon Resource Name (ARN) of the cluster
        """
        # Create a boto3 client
        client = boto3.client("kafka", region_name=region)
        return delete_vpc_connection(vpc_connection_arn=vpc_connection_arn, client=client)

    @mcp.tool(name="reject_client_vpc_connection")
    def reject_client_vpc_connection_tool(region, cluster_arn, vpc_connection_arn):
        """
        Reject a client VPC connection request for an MSK cluster.

        Args:
            cluster_arn (str): The Amazon Resource Name (ARN) of the cluster
            vpc_connection_arn (str): The Amazon Resource Name (ARN) of the VPC connection to reject
            region (str): AWS region

        Returns:
            dict: Information about the rejected VPC connection including:
                - VpcConnectionArn (str): The Amazon Resource Name (ARN) of the VPC connection
                - VpcConnectionState (str): The state of the VPC connection (should be REJECTED)
                - ClusterArn (str): The Amazon Resource Name (ARN) of the cluster
        """
        # Create a boto3 client
        client = boto3.client("kafka", region_name=region)
        return reject_client_vpc_connection(
            cluster_arn=cluster_arn, vpc_connection_arn=vpc_connection_arn, client=client
        )
