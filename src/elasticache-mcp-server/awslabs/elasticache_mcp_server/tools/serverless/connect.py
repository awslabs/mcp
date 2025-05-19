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

"""Connect module for creating and configuring jump host EC2 instances to access ElastiCache serverless caches."""

from ...common.connection import EC2ConnectionManager, ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from botocore.exceptions import ClientError
from typing import Any, Dict, Tuple, Union


async def _configure_security_groups(
    serverless_cache_name: str,
    instance_id: str,
    ec2_client: Any = None,
    elasticache_client: Any = None,
) -> Tuple[bool, str, int]:
    """Configure security group rules to allow access from EC2 instance to ElastiCache serverless cache.

    Args:
        serverless_cache_name (str): Name of the ElastiCache serverless cache
        instance_id (str): ID of the EC2 instance
        ec2_client (Any, optional): EC2 client. If not provided, will get from connection manager
        elasticache_client (Any, optional): ElastiCache client. If not provided, will get from connection manager

    Returns:
        Tuple[bool, str, int]: Tuple containing (success status, vpc id, cache port)

    Raises:
        ValueError: If VPC compatibility check fails or required resources not found
    """
    if not ec2_client:
        ec2_client = EC2ConnectionManager.get_connection()
    if not elasticache_client:
        elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Get serverless cache details
    serverless_cache = elasticache_client.describe_serverless_caches(
        ServerlessCacheName=serverless_cache_name
    )['ServerlessCaches'][0]

    # Get cache VPC ID and subnet IDs
    cache_vpc_id = serverless_cache['VpcSecurityGroups'][0]['VpcId']
    cache_security_groups = serverless_cache['VpcSecurityGroups']
    if not cache_security_groups:
        raise ValueError(f'No security groups found for serverless cache {serverless_cache_name}')

    # Get cache port (default is 6379 for Redis)
    cache_port = 6379

    # Get EC2 instance details
    instance_info = ec2_client.describe_instances(InstanceIds=[instance_id])
    if not instance_info['Reservations']:
        raise ValueError(f'EC2 instance {instance_id} not found')

    instance = instance_info['Reservations'][0]['Instances'][0]
    instance_vpc_id = instance['VpcId']

    # Check VPC compatibility
    if instance_vpc_id != cache_vpc_id:
        raise ValueError(
            f'EC2 instance VPC ({instance_vpc_id}) does not match serverless cache VPC ({cache_vpc_id})'
        )

    # Get EC2 instance security groups
    instance_security_groups = [sg['GroupId'] for sg in instance['SecurityGroups']]
    if not instance_security_groups:
        raise ValueError(f'No security groups found for EC2 instance {instance_id}')

    # For each cache security group, ensure it allows inbound access from EC2 security groups
    for cache_sg in cache_security_groups:
        cache_sg_id = cache_sg['SecurityGroupId']
        cache_sg_info = ec2_client.describe_security_groups(GroupIds=[cache_sg_id])[
            'SecurityGroups'
        ][0]

        # Check existing rules
        existing_rules = cache_sg_info.get('IpPermissions', [])
        needs_rule = True

        for rule in existing_rules:
            if (
                rule.get('IpProtocol') == 'tcp'
                and rule.get('FromPort') == cache_port
                and rule.get('ToPort') == cache_port
            ):
                # Check if any EC2 security group is already allowed
                for group_pair in rule.get('UserIdGroupPairs', []):
                    if group_pair.get('GroupId') in instance_security_groups:
                        needs_rule = False
                        break
            if not needs_rule:
                break

        # Add rule if needed
        if needs_rule:
            ec2_client.authorize_security_group_ingress(
                GroupId=cache_sg_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': cache_port,
                        'ToPort': cache_port,
                        'UserIdGroupPairs': [
                            {
                                'GroupId': instance_security_groups[0],
                                'Description': f'Allow access from jump host {instance_id}',
                            }
                        ],
                    }
                ],
            )

    return True, cache_vpc_id, cache_port


@mcp.tool(name='connect-jump-host-serverless-cache')
@handle_exceptions
async def connect_jump_host_serverless(
    serverless_cache_name: str, instance_id: str
) -> Dict[str, Any]:
    """Configures an existing EC2 instance as a jump host to access an ElastiCache serverless cache.

    Args:
        serverless_cache_name (str): Name of the ElastiCache serverless cache to connect to
        instance_id (str): ID of the EC2 instance to use as jump host

    Returns:
        Dict[str, Any]: Dictionary containing connection details and configuration status

    Raises:
        ValueError: If VPC compatibility check fails or required resources not found
    """
    try:
        # Configure security groups using common function
        configured, vpc_id, cache_port = await _configure_security_groups(
            serverless_cache_name, instance_id
        )

        return {
            'Status': 'Success',
            'InstanceId': instance_id,
            'ServerlessCacheName': serverless_cache_name,
            'CachePort': cache_port,
            'VpcId': vpc_id,
            'SecurityGroupsConfigured': configured,
            'Message': 'Jump host connection configured successfully',
        }

    except Exception as e:
        raise ValueError(str(e))


@mcp.tool(name='get-ssh-tunnel-command-serverless-cache')
@handle_exceptions
async def get_ssh_tunnel_command_serverless(
    serverless_cache_name: str, instance_id: str
) -> Dict[str, Union[str, int]]:
    """Generates an SSH tunnel command to connect to an ElastiCache serverless cache through an EC2 jump host.

    Args:
        serverless_cache_name (str): Name of the ElastiCache serverless cache to connect to
        instance_id (str): ID of the EC2 instance to use as jump host

    Returns:
        Dict[str, Union[str, int]]: Dictionary containing the SSH tunnel command and related details

    Raises:
        ValueError: If required resources not found or information cannot be retrieved
    """
    # Get AWS clients
    ec2_client = EC2ConnectionManager.get_connection()
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    try:
        # Get EC2 instance details
        instance_info = ec2_client.describe_instances(InstanceIds=[instance_id])
        if not instance_info['Reservations']:
            raise ValueError(f'EC2 instance {instance_id} not found')

        instance = instance_info['Reservations'][0]['Instances'][0]

        # Get instance key name and public DNS
        key_name = instance.get('KeyName')
        if not key_name:
            raise ValueError(f'No key pair associated with EC2 instance {instance_id}')

        public_dns = instance.get('PublicDnsName')
        if not public_dns:
            raise ValueError(f'No public DNS name found for EC2 instance {instance_id}')

        # Get instance platform details to determine user
        platform = instance.get('Platform', '')
        user = 'ec2-user'  # Default for Amazon Linux
        if platform.lower() == 'windows':
            raise ValueError('Windows instances are not supported for SSH tunneling')
        elif 'ubuntu' in instance.get('ImageId', '').lower():
            user = 'ubuntu'

        # Get serverless cache details
        serverless_cache = elasticache_client.describe_serverless_caches(
            ServerlessCacheName=serverless_cache_name
        )['ServerlessCaches'][0]

        # Get cache endpoint and port (default port is 6379 for Redis)
        cache_endpoint = serverless_cache['Endpoint']['Address']
        cache_port = 6379

        # Generate SSH tunnel command
        ssh_command = (
            f'ssh -i "{key_name}.pem" -fN -l {user} '
            f'-L {cache_port}:{cache_endpoint}:{cache_port} {public_dns} -v'
        )

        return {
            'command': ssh_command,
            'keyName': key_name,
            'user': user,
            'localPort': cache_port,
            'cacheEndpoint': cache_endpoint,
            'cachePort': cache_port,
            'jumpHostDns': public_dns,
        }

    except Exception as e:
        raise ValueError(str(e))


@mcp.tool(name='create-jump-host-serverless-cache')
@handle_exceptions
async def create_jump_host_serverless(
    serverless_cache_name: str,
    subnet_id: str,
    security_group_id: str,
    key_name: str,
    instance_type: str = 't3.small',
) -> Dict[str, Any]:
    """Creates an EC2 jump host instance to access an ElastiCache serverless cache via SSH tunnel.

    Args:
        serverless_cache_name (str): Name of the ElastiCache serverless cache to connect to
        subnet_id (str): ID of the subnet to launch the EC2 instance in (must be public)
        security_group_id (str): ID of the security group to assign to the EC2 instance
        key_name (str): Name of the EC2 key pair to use for SSH access
        instance_type (str, optional): EC2 instance type. Defaults to "t3.small"

    Returns:
        Dict[str, Any]: Dictionary containing the created EC2 instance details

    Raises:
        ValueError: If subnet is not public or VPC compatibility check fails
    """
    # Get AWS clients from connection managers
    ec2_client = EC2ConnectionManager.get_connection()
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    try:
        # Validate key_name
        if not key_name:
            raise ValueError(
                'key_name is required. Use CreateKeyPair or ImportKeyPair EC2 APIs to create/import an SSH key pair.'
            )

        # Verify key pair exists
        key_pairs = ec2_client.describe_key_pairs(KeyNames=[key_name])
        if not key_pairs.get('KeyPairs'):
            return {
                'error': f"Key pair '{key_name}' not found. Use CreateKeyPair or ImportKeyPair EC2 APIs to create/import an SSH key pair."
            }

        # Get serverless cache details to find its VPC
        serverless_cache = elasticache_client.describe_serverless_caches(
            ServerlessCacheName=serverless_cache_name
        )['ServerlessCaches'][0]

        cache_vpc_id = serverless_cache['VpcSecurityGroups'][0]['VpcId']

        # Get subnet details and verify it's public
        subnet_response = ec2_client.describe_subnets(SubnetIds=[subnet_id])
        subnet = subnet_response['Subnets'][0]
        subnet_vpc_id = subnet['VpcId']

        # Check VPC compatibility
        if subnet_vpc_id != cache_vpc_id:
            raise ValueError(
                f'Subnet VPC ({subnet_vpc_id}) does not match serverless cache VPC ({cache_vpc_id})'
            )

        # Check if subnet is public by looking for route to internet gateway
        route_tables = ec2_client.describe_route_tables(
            Filters=[{'Name': 'association.subnet-id', 'Values': [subnet_id]}]
        )['RouteTables']

        is_public = False
        for rt in route_tables:
            for route in rt.get('Routes', []):
                if route.get('GatewayId', '').startswith('igw-'):
                    is_public = True
                    break
            if is_public:
                break

        # Raise error if no route to internet gateway found
        if not is_public:
            raise ValueError(
                f'Subnet {subnet_id} is not public (no route to internet gateway found). '
                'The subnet must be public to allow SSH access to the jump host.'
            )

        # Use Amazon Linux 2023 AMI
        images = ec2_client.describe_images(
            Filters=[
                {'Name': 'name', 'Values': ['al2023-ami-2023.*-x86_64']},
                {'Name': 'owner-alias', 'Values': ['amazon']},
            ]
        )
        ami_id = sorted(images['Images'], key=lambda x: x['CreationDate'], reverse=True)[0][
            'ImageId'
        ]

        # Verify and update security group rules for SSH access
        security_group = ec2_client.describe_security_groups(GroupIds=[security_group_id])[
            'SecurityGroups'
        ][0]

        # Check if port 22 is already open
        has_ssh_rule = False
        for rule in security_group.get('IpPermissions', []):
            if (
                rule.get('IpProtocol') == 'tcp'
                and rule.get('FromPort') == 22
                and rule.get('ToPort') == 22
                and any(
                    ip_range.get('CidrIp') == '0.0.0.0/0' for ip_range in rule.get('IpRanges', [])
                )
            ):
                has_ssh_rule = True
                break

        # Add SSH rule if it doesn't exist
        if not has_ssh_rule:
            ec2_client.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [
                            {'CidrIp': '0.0.0.0/0', 'Description': 'SSH access from anywhere'}
                        ],
                    }
                ],
            )

        # Launch EC2 instance
        instance = ec2_client.run_instances(
            ImageId=ami_id,
            InstanceType=instance_type,
            KeyName=key_name,
            MaxCount=1,
            MinCount=1,
            NetworkInterfaces=[
                {
                    'SubnetId': subnet_id,
                    'DeviceIndex': 0,
                    'AssociatePublicIpAddress': True,
                    'Groups': [security_group_id],
                }
            ],
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': f'ElastiCache-JumpHost-{serverless_cache_name}'}
                    ],
                }
            ],
        )

        # Wait for instance to be running and get its public IP
        waiter = ec2_client.get_waiter('instance_running')
        instance_id = instance['Instances'][0]['InstanceId']
        waiter.wait(InstanceIds=[instance_id])

        instance_info = ec2_client.describe_instances(InstanceIds=[instance_id])
        public_ip = instance_info['Reservations'][0]['Instances'][0]['PublicIpAddress']

        # Configure security groups using common function
        configured, vpc_id, cache_port = await _configure_security_groups(
            serverless_cache_name,
            instance_id,
            ec2_client=ec2_client,
            elasticache_client=elasticache_client,
        )

        return {
            'InstanceId': instance_id,
            'PublicIpAddress': public_ip,
            'InstanceType': instance_type,
            'SubnetId': subnet_id,
            'SecurityGroupId': security_group_id,
            'ServerlessCacheName': serverless_cache_name,
            'SecurityGroupsConfigured': configured,
            'CachePort': cache_port,
            'VpcId': vpc_id,
        }

    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidKeyPair.NotFound':
            return {
                'error': f"Key pair '{key_name}' not found. Use CreateKeyPair or ImportKeyPair EC2 APIs to create/import an SSH key pair."
            }
        return {'error': str(e)}
    except Exception as e:
        return {'error': str(e)}
