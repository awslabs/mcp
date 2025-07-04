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
AWS utility functions.
"""

import logging
import os
from typing import Any, Dict, List

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def get_aws_config() -> Config:
    """
    Gets AWS config with user-agent tag.

    Returns:
        Config object with user-agent tag
    """
    return Config(user_agent_extra="awslabs/mcp/ecs-mcp-server/0.1.0")


# Dictionary to store clients for reuse
_aws_clients = {}


async def get_aws_client(service_name: str):
    """
    Gets an AWS service client.

    Parameters
    ----------
    service_name : str
        The name of the AWS service (e.g., 'ecs', 's3', 'ec2')

    Returns
    -------
    A boto3 client for the specified service
    """
    # Use client from cache if available
    if service_name in _aws_clients:
        return _aws_clients[service_name]

    # Create new client if not in cache
    region = os.environ.get("AWS_REGION", "us-east-1")
    profile = os.environ.get("AWS_PROFILE", "default")
    logger.info(f"Using AWS profile: {profile} and region: {region}")

    client = boto3.client(service_name, region_name=region, config=get_aws_config())

    # Cache the client for reuse
    _aws_clients[service_name] = client

    return client


async def get_aws_account_id() -> str:
    """Gets the AWS account ID."""
    sts = await get_aws_client("sts")
    response = sts.get_caller_identity()  # Removed await since boto3 methods are not coroutines
    return response["Account"]


async def get_default_vpc_and_subnets(ec2_client=None) -> Dict[str, Any]:
    """
    Gets the default VPC and subnets.

    Parameters
    ----------
    ec2_client : boto3.client, optional
        EC2 client to use. If not provided, a new client will be created.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing VPC ID, subnet IDs, and route table IDs
    """
    ec2 = ec2_client or await get_aws_client("ec2")

    # Get default VPC
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])  # Removed await

    if not vpcs["Vpcs"]:
        raise ValueError("No default VPC found. Please specify a VPC ID.")

    vpc_id = vpcs["Vpcs"][0]["VpcId"]

    # Get public subnets in the default VPC
    subnets = ec2.describe_subnets(  # Removed await
        Filters=[
            {"Name": "vpc-id", "Values": [vpc_id]},
            {"Name": "map-public-ip-on-launch", "Values": ["true"]},
        ]
    )

    if not subnets["Subnets"]:
        # Fallback to all subnets in the VPC
        subnets = ec2.describe_subnets(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )  # Removed await

    subnet_ids = [subnet["SubnetId"] for subnet in subnets["Subnets"]]

    # Get route tables for the VPC
    route_tables = ec2.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )  # Removed await

    # Find the main route table
    main_route_tables = [
        rt["RouteTableId"]
        for rt in route_tables["RouteTables"]
        if any(assoc.get("Main", False) for assoc in rt.get("Associations", []))
    ]

    # If no main route table is found, use all route tables
    if not main_route_tables:
        route_table_ids = [rt["RouteTableId"] for rt in route_tables["RouteTables"]]
    else:
        route_table_ids = main_route_tables

    return {"vpc_id": vpc_id, "subnet_ids": subnet_ids, "route_table_ids": route_table_ids}


async def create_ecr_repository(repository_name: str) -> Dict[str, Any]:
    """Creates an ECR repository if it doesn't exist."""
    ecr = await get_aws_client("ecr")

    try:
        # Check if repository exists
        response = ecr.describe_repositories(repositoryNames=[repository_name])  # Removed await
        return response["repositories"][0]
    except ClientError as e:
        # Check if the error is RepositoryNotFoundException
        if e.response["Error"]["Code"] == "RepositoryNotFoundException":
            # Create repository if it doesn't exist
            response = ecr.create_repository(  # Removed await
                repositoryName=repository_name,
                imageScanningConfiguration={"scanOnPush": True},
                encryptionConfiguration={"encryptionType": "AES256"},
            )
            return response["repository"]
        else:
            # Re-raise other ClientErrors
            raise


async def assume_ecr_role(role_arn: str) -> Dict[str, Any]:
    """
    Assumes the ECR push/pull role.

    Args:
        role_arn: ARN of the ECR push/pull role to assume

    Returns:
        Dict containing temporary credentials
    """
    sts = await get_aws_client("sts")

    logger.info(f"Assuming role: {role_arn}")
    response = sts.assume_role(RoleArn=role_arn, RoleSessionName="ECSMCPServerECRSession")

    return {
        "aws_access_key_id": response["Credentials"]["AccessKeyId"],
        "aws_secret_access_key": response["Credentials"]["SecretAccessKey"],
        "aws_session_token": response["Credentials"]["SessionToken"],
    }


async def get_aws_client_with_role(service_name: str, role_arn: str):
    """
    Gets an AWS service client using a specific role.

    Args:
        service_name: AWS service name
        role_arn: ARN of the role to assume

    Returns:
        AWS service client with role credentials
    """
    credentials = await assume_ecr_role(role_arn)
    region = os.environ.get("AWS_REGION", "us-east-1")

    logger.info(f"Creating {service_name} client with assumed role: {role_arn}")
    return boto3.client(
        service_name,
        region_name=region,
        aws_access_key_id=credentials["aws_access_key_id"],
        aws_secret_access_key=credentials["aws_secret_access_key"],
        aws_session_token=credentials["aws_session_token"],
        config=get_aws_config(),
    )


async def get_ecr_login_password(role_arn: str) -> str:
    """
    Gets ECR login password for Docker authentication.

    Args:
        role_arn: ARN of the ECR push/pull role to use

    Returns:
        ECR login password for Docker authentication

    Raises:
        ValueError: If role_arn is not provided
    """
    if not role_arn:
        raise ValueError("role_arn is required for ECR authentication")

    ecr = await get_aws_client_with_role("ecr", role_arn)
    logger.info(f"Getting ECR login password using role: {role_arn}")

    response = ecr.get_authorization_token()  # Removed await

    if not response["authorizationData"]:
        raise ValueError("Failed to get ECR authorization token")

    auth_data = response["authorizationData"][0]
    token = auth_data["authorizationToken"]

    # Token is base64 encoded username:password
    import base64

    decoded = base64.b64decode(token).decode("utf-8")
    username, password = decoded.split(":")

    return password


async def get_route_tables_for_vpc(vpc_id: str, ec2_client=None) -> List[str]:
    """
    Gets route tables for a specific VPC.

    Parameters
    ----------
    vpc_id : str
        ID of the VPC to get route tables for
    ec2_client : boto3.client, optional
        EC2 client to use. If not provided, a new client will be created.

    Returns
    -------
    List[str]
        List of route table IDs
    """
    ec2 = ec2_client or await get_aws_client("ec2")

    # Get route tables for the VPC
    route_tables = ec2.describe_route_tables(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])

    # Find the main route table
    main_route_tables = [
        rt["RouteTableId"]
        for rt in route_tables["RouteTables"]
        if any(assoc.get("Main", False) for assoc in rt.get("Associations", []))
    ]

    # If no main route table is found, use all route tables
    if not main_route_tables:
        route_table_ids = [rt["RouteTableId"] for rt in route_tables["RouteTables"]]
    else:
        route_table_ids = main_route_tables

    return route_table_ids
