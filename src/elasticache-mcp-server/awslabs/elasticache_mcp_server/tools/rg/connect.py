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

"""Connect module for creating and configuring jump host EC2 instances to access ElastiCache replication groups."""

from ...common.connection import EC2ConnectionManager, ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from ...context import Context
from botocore.exceptions import ClientError
from typing import Any, Dict, Optional, Tuple, Union


async def _configure_security_groups(
    replication_group_id: str,
    instance_id: str,
    ec2_client: Any = None,
    elasticache_client: Any = None,
) -> Tuple[bool, str, int]:
    """Configure security group rules to allow access from EC2 instance to ElastiCache replication group.

    Args:
        replication_group_id (str): ID of the ElastiCache replication group
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

    # Get replication group details
    replication_group = elasticache_client.describe_replication_groups(
        ReplicationGroupId=replication_group_id
    )['ReplicationGroups'][0]

    # Get first cluster details (MemberClusters doesn't have notion of primary cluster)
    if not replication_group['MemberClusters']:
        raise ValueError(f'No clusters found in replication group {replication_group_id}')

    first_cluster_id = replication_group['MemberClusters'][0]

    # Get cache cluster VPC ID from first cluster
    first_cluster = elasticache_client.describe_cache_clusters(
        CacheClusterId=first_cluster_id, ShowCacheNodeInfo=True
    )['CacheClusters'][0]

    # Get subnet group name from first cluster
    subnet_group_name = first_cluster.get('CacheSubnetGroupName')
    if not subnet_group_name:
        raise ValueError(f'No cache subnet group found for cluster {first_cluster_id}')

    # Get VPC ID from subnet group
    try:
        cache_subnet_group = elasticache_client.describe_cache_subnet_groups(
            CacheSubnetGroupName=subnet_group_name
        )['CacheSubnetGroups'][0]
    except Exception as e:
        raise ValueError(f'Failed to get cache subnet group {subnet_group_name}: {str(e)}')
    cache_vpc_id = cache_subnet_group['VpcId']

    # Get EC2 instance details
    instance_info = ec2_client.describe_instances(InstanceIds=[instance_id])
    if not instance_info['Reservations']:
        raise ValueError(f'EC2 instance {instance_id} not found')

    instance = instance_info['Reservations'][0]['Instances'][0]
    instance_vpc_id = instance['VpcId']

    # Check VPC compatibility
    if instance_vpc_id != cache_vpc_id:
        raise ValueError(
            f'EC2 instance VPC ({instance_vpc_id}) does not match replication group VPC ({cache_vpc_id})'
        )

    # Get cache cluster port from first node
    cache_port = first_cluster['CacheNodes'][0]['Endpoint']['Port']

    # Get cache cluster security groups from all member clusters
    cache_security_groups = set()
    for member in replication_group['MemberClusters']:
        cluster = elasticache_client.describe_cache_clusters(
            CacheClusterId=member, ShowCacheNodeInfo=True
        )['CacheClusters'][0]
        for sg in cluster.get('SecurityGroups', []):
            cache_security_groups.add(sg['SecurityGroupId'])

    if not cache_security_groups:
        raise ValueError(f'No security groups found for replication group {replication_group_id}')

    # Get EC2 instance security groups
    instance_security_groups = [sg['GroupId'] for sg in instance['SecurityGroups']]
    if not instance_security_groups:
        raise ValueError(f'No security groups found for EC2 instance {instance_id}')

    # For each cache security group, ensure it allows inbound access from EC2 security groups
    for cache_sg_id in cache_security_groups:
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


@mcp.tool(name='connect-jump-host-replication-group')
@handle_exceptions
async def connect_jump_host_rg(replication_group_id: str, instance_id: str) -> Dict[str, Any]:
    """Configures an existing EC2 instance as a jump host to access an ElastiCache replication group.

    Args:
        replication_group_id (str): ID of the ElastiCache replication group to connect to
        instance_id (str): ID of the EC2 instance to use as jump host

    Returns:
        Dict[str, Any]: Dictionary containing connection details and configuration status

    Raises:
        ValueError: If VPC compatibility check fails or required resources not found
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        raise ValueError(
            'You have configured this tool in readonly mode. To make this change you will have to update your configuration.'
        )

    try:
        # Configure security groups using common function
        configured, vpc_id, cache_port = await _configure_security_groups(
            replication_group_id, instance_id
        )

        return {
            'Status': 'Success',
            'InstanceId': instance_id,
            'ReplicationGroupId': replication_group_id,
            'CachePort': cache_port,
            'VpcId': vpc_id,
            'SecurityGroupsConfigured': configured,
            'Message': 'Jump host connection configured successfully',
        }

    except Exception as e:
        raise ValueError(str(e))


@mcp.tool(name='get-ssh-tunnel-command-replication-group')
@handle_exceptions
async def get_ssh_tunnel_command_rg(
    replication_group_id: str, instance_id: str
) -> Dict[str, Union[str, int]]:
    """Generates an SSH tunnel command to connect to an ElastiCache replication group through an EC2 jump host.

    Args:
        replication_group_id (str): ID of the ElastiCache replication group to connect to
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

        # Get replication group details
        replication_group = elasticache_client.describe_replication_groups(
            ReplicationGroupId=replication_group_id
        )['ReplicationGroups'][0]

        # Use the ConfigurationEndpoint for the SSH tunnel
        if 'ConfigurationEndpoint' not in replication_group:
            raise ValueError(
                f'No ConfigurationEndpoint found for replication group {replication_group_id}'
            )

        endpoint = replication_group['ConfigurationEndpoint']['Address']
        port = replication_group['ConfigurationEndpoint']['Port']

        # Generate a single SSH tunnel command
        ssh_command = (
            f'ssh -i "{key_name}.pem" -fN -l {user} -L {port}:{endpoint}:{port} {public_dns} -v'
        )

        return {
            'command': ssh_command,
            'keyName': key_name,
            'user': user,
            'jumpHostDns': public_dns,
            'localPort': port,
            'remoteEndpoint': endpoint,
            'remotePort': port,
        }

    except Exception as e:
        raise ValueError(str(e))


@mcp.tool(name='create-jump-host-replication-group')
@handle_exceptions
async def create_jump_host_rg(
    replication_group_id: str,
    key_name: str,
    subnet_id: Optional[str] = None,
    security_group_id: Optional[str] = None,
    instance_type: str = 't3.small',
) -> Dict[str, Any]:
    """Creates an EC2 jump host instance to access an ElastiCache replication group via SSH tunnel.

    Args:
        replication_group_id (str): ID of the ElastiCache replication group to connect to
        key_name (str): Name of the EC2 key pair to use for SSH access
        subnet_id (str, optional): ID of the subnet to launch the EC2 instance in (must be public).
            If not provided and replication group uses default VPC, will auto-select a default subnet.
        security_group_id (str, optional): ID of the security group to assign to the EC2 instance.
            If not provided and replication group uses default VPC, will use the default security group.
        instance_type (str, optional): EC2 instance type. Defaults to "t3.small"

    Returns:
        Dict[str, Any]: Dictionary containing the created EC2 instance details

    Raises:
        ValueError: If subnet is not public or VPC compatibility check fails
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        raise ValueError(
            'You have configured this tool in readonly mode. To make this change you will have to update your configuration.'
        )

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

        # Get replication group details
        replication_group = elasticache_client.describe_replication_groups(
            ReplicationGroupId=replication_group_id
        )['ReplicationGroups'][0]

        # Get first cluster details (MemberClusters doesn't have notion of primary cluster)
        if not replication_group['MemberClusters']:
            raise ValueError(f'No clusters found in replication group {replication_group_id}')

        first_cluster_id = replication_group['MemberClusters'][0]

        # Get VPC details from first cluster
        first_cluster = elasticache_client.describe_cache_clusters(
            CacheClusterId=first_cluster_id, ShowCacheNodeInfo=True
        )['CacheClusters'][0]

        cache_subnet_group = elasticache_client.describe_cache_subnet_groups(
            CacheSubnetGroupName=first_cluster['CacheSubnetGroupName']
        )['CacheSubnetGroups'][0]
        cache_vpc_id = cache_subnet_group['VpcId']

        # Check if replication group is in default VPC
        vpcs = ec2_client.describe_vpcs(VpcIds=[cache_vpc_id])['Vpcs']
        cache_vpc = vpcs[0] if vpcs else None
        is_default_vpc = cache_vpc and cache_vpc.get('IsDefault', False)

        # Auto-select subnet if not provided and replication group is in default VPC
        if not subnet_id and is_default_vpc:
            # Get default subnets in the default VPC
            subnets = ec2_client.describe_subnets(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [cache_vpc_id]},
                    {'Name': 'default-for-az', 'Values': ['true']},
                ]
            )['Subnets']

            if subnets:
                # Pick the first available default subnet
                subnet_id = subnets[0]['SubnetId']
            else:
                # Fallback to any public subnet in the VPC
                all_subnets = ec2_client.describe_subnets(
                    Filters=[{'Name': 'vpc-id', 'Values': [cache_vpc_id]}]
                )['Subnets']

                for subnet in all_subnets:
                    if subnet.get('MapPublicIpOnLaunch', False):
                        subnet_id = subnet['SubnetId']
                        break

        # Auto-select security group if not provided and replication group is in default VPC
        if not security_group_id and is_default_vpc:
            # Get the default security group for the VPC
            security_groups = ec2_client.describe_security_groups(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [cache_vpc_id]},
                    {'Name': 'group-name', 'Values': ['default']},
                ]
            )['SecurityGroups']

            if security_groups:
                security_group_id = security_groups[0]['GroupId']

        # Validate required parameters after auto-selection
        if not subnet_id:
            raise ValueError(
                'subnet_id is required. Either provide a subnet_id or ensure the replication group is in the default VPC with default subnets available.'
            )

        if not security_group_id:
            raise ValueError(
                'security_group_id is required. Either provide a security_group_id or ensure the replication group is in the default VPC.'
            )

        # Get subnet details and verify it's public
        subnet_response = ec2_client.describe_subnets(SubnetIds=[subnet_id])
        subnet = subnet_response['Subnets'][0]
        subnet_vpc_id = subnet['VpcId']

        # Check VPC compatibility
        if subnet_vpc_id != cache_vpc_id:
            raise ValueError(
                f'Subnet VPC ({subnet_vpc_id}) does not match replication group VPC ({cache_vpc_id})'
            )

        # Check if subnet is public by looking for route to internet gateway
        # or if it's a default subnet in the default VPC (which are automatically public)
        route_tables = ec2_client.describe_route_tables(
            Filters=[{'Name': 'association.subnet-id', 'Values': [subnet_id]}]
        )['RouteTables']

        # If no explicit route table association, check main route table
        if not route_tables:
            route_tables = ec2_client.describe_route_tables(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [subnet_vpc_id]},
                    {'Name': 'association.main', 'Values': ['true']},
                ]
            )['RouteTables']

        # Check for route to internet gateway
        is_public = False
        for rt in route_tables:
            for route in rt.get('Routes', []):
                if route.get('GatewayId', '').startswith('igw-'):
                    is_public = True
                    break
            if is_public:
                break

        # If not found via route table, check if it's a default subnet in default VPC
        if not is_public:
            # Check if this is the default VPC
            vpcs = ec2_client.describe_vpcs(VpcIds=[subnet_vpc_id])['Vpcs']
            vpc = vpcs[0] if vpcs else None

            if vpc and vpc.get('IsDefault', False):
                # In default VPC, check if this is a default subnet
                # Default subnets have MapPublicIpOnLaunch set to True
                if subnet.get('DefaultForAz', False) or subnet.get('MapPublicIpOnLaunch', False):
                    is_public = True

        if not is_public:
            raise ValueError(
                f'Subnet {subnet_id} is not public (no route to internet gateway found and not a default subnet in default VPC). '
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
                        {'Key': 'Name', 'Value': f'ElastiCache-JumpHost-{replication_group_id}'}
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
            replication_group_id,
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
            'ReplicationGroupId': replication_group_id,
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
