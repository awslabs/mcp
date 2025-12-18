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

import boto3
import json
import time
import traceback
from awslabs.postgres_mcp_server import __user_agent__
from botocore.config import Config
from botocore.exceptions import ClientError
from loguru import logger
from typing import Any, Dict, Optional


def internal_create_rds_client(region: str):
    """Create an RDS client with custom user agent configuration."""
    return boto3.client('rds', region_name=region, config=Config(user_agent_extra=__user_agent__))


def internal_get_instance_properties(target_endpoint: str, region: str) -> Dict[str, Any]:
    """Retrieve RDS instance properties from AWS."""
    rds_client = internal_create_rds_client(region=region)
    paginator = rds_client.get_paginator('describe_db_instances')

    # Iterate through all instances
    try:
        for page in paginator.paginate():
            for instance in page['DBInstances']:
                endpoint = instance.get('Endpoint', {}).get('Address')
                if endpoint == target_endpoint:
                    return instance
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(
            f'AWS error fetching all instances in region:{region} '
            f'{error_code} - {e.response["Error"]["Message"]}'
        )
        raise
    except Exception as e:
        logger.error(
            f'Error fetchingall instances in region:{region}.  Error: {type(e).__name__}: {e}'
        )
        raise

    not_found_error = (
        f"AWS error fetching instance by endpoint: '{target_endpoint}' in region:{region}"
    )
    logger.error(not_found_error)
    raise ValueError(not_found_error)


def internal_get_cluster_properties(cluster_identifier: str, region: str) -> Dict[str, Any]:
    """Retrieve RDS cluster properties from AWS.

    Args:
        cluster_identifier: RDS cluster identifier
        region: AWS region (e.g., 'us-east-1')

    Returns:
        Dict[str, Any]: Cluster properties from AWS RDS API

    Raises:
        ValueError: If cluster_identifier or region is empty
        ClientError: If AWS API call fails (cluster not found, access denied, etc.)
        NoCredentialsError: If AWS credentials not configured

    Example:
        >>> props = internal_get_cluster_properties('my-cluster', 'us-east-1')
        >>> print(props['Status'])
    """
    # Input validation
    if not cluster_identifier or not region:
        raise ValueError('cluster_identifier and region are required')

    logger.info(f"Fetching properties for cluster '{cluster_identifier}' in '{region}' ")

    try:
        rds_client = internal_create_rds_client(region)
        response = rds_client.describe_db_clusters(DBClusterIdentifier=cluster_identifier)

        # Safely extract cluster properties
        clusters = response.get('DBClusters', [])
        if not clusters:
            raise ValueError(f"Cluster '{cluster_identifier}' not found in region '{region}'")

        cluster_properties = clusters[0]

        # Log summary only
        logger.info(
            f"Retrieved cluster '{cluster_identifier}': "
            f'Status={cluster_properties.get("Status")}, '
            f'Engine={cluster_properties.get("Engine")}'
        )

        # Full properties at debug level
        logger.debug(
            f'Cluster properties: {json.dumps(cluster_properties, indent=2, default=str)}'
        )

        return cluster_properties

    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(
            f"AWS error fetching cluster '{cluster_identifier}': "
            f'{error_code} - {e.response["Error"]["Message"]}'
        )
        raise
    except Exception as e:
        logger.error(f'Error fetching cluster properties: {type(e).__name__}: {e}')
        raise


def internal_create_serverless_cluster(
    region: str,
    cluster_identifier: str,
    engine_version: str,
    database_name: str,
    master_username: str = 'postgres',
    min_capacity: float = 0.5,
    max_capacity: float = 4,
    enable_cloudwatch_logs: bool = True,
) -> Dict[str, Any]:
    """Create an Aurora PostgreSQL cluster with a single writer instance.

    Credentials are automatically managed by AWS Secrets Manager.

    Args:
        region: region of the cluster
        cluster_identifier: Name of the Aurora cluster
        engine_version: PostgreSQL engine version (e.g., '15.3', '14.7')
        database_name: Name of the default database
        master_username: Master username for the database
        min_capacity: minimum ACU capacity
        max_capacity: maximum ACU capacity
        enable_cloudwatch_logs: Enable CloudWatch logs export

    Returns:
        Dictionary containing cluster information and secret ARN
    """
    if not region:
        raise ValueError('region is required')
    if not cluster_identifier:
        raise ValueError('cluster_identifier is required')
    if not engine_version:
        raise ValueError('engine_version is required')
    if not database_name:
        raise ValueError('database_name is required')

    rds_client = internal_create_rds_client(region=region)

    # Add default tags
    tags = []
    tags.append({'Key': 'CreatedBy', 'Value': 'MCP'})

    # Prepare CloudWatch logs
    enable_cloudwatch_logs_exports = []
    if enable_cloudwatch_logs:
        enable_cloudwatch_logs_exports = ['postgresql']

    try:
        # Create the Aurora cluster
        logger.info(
            f'Creating Aurora PostgreSQL cluster:{cluster_identifier} '
            f'region:{region} engine_version:{engine_version} database_name:{database_name} '
            f'master_username:{master_username}'
        )

        cluster_params = {
            'DBClusterIdentifier': cluster_identifier,
            'Engine': 'aurora-postgresql',
            'EngineVersion': engine_version,
            'MasterUsername': master_username,
            'DatabaseName': database_name,
            'ManageMasterUserPassword': True,  # Enable Secrets Manager integration
            'Tags': tags,
            'DeletionProtection': False,  # Set to True for production
            'CopyTagsToSnapshot': True,
            'EnableHttpEndpoint': True,  # Enable for Data API if needed
            'EnableCloudwatchLogsExports': enable_cloudwatch_logs_exports,
        }

        cluster_params['ServerlessV2ScalingConfiguration'] = {
            'MinCapacity': min_capacity,
            'MaxCapacity': max_capacity,
        }

        # Create the cluster
        cluster_create_start_time = time.time()
        cluster_response = rds_client.create_db_cluster(**cluster_params)

        cluster_info = cluster_response['DBCluster']
        logger.info(
            f'Cluster {cluster_identifier} creation call started successfully. Status: {cluster_info["Status"]}'
        )

        # Wait for cluster to be available
        logger.info('Waiting for cluster to become available...')
        waiter = rds_client.get_waiter('db_cluster_available')
        waiter.wait(
            DBClusterIdentifier=cluster_identifier, WaiterConfig={'Delay': 5, 'MaxAttempts': 120}
        )

        logger.info(f'Cluster {cluster_identifier} is now available')
        cluster_create_stop_time = time.time()
        elapsed_time = cluster_create_stop_time - cluster_create_start_time
        logger.info(f'Cluster creation {cluster_identifier} took {elapsed_time:.2f} seconds')

        # Create the writer instance
        instance_identifier = f'{cluster_identifier}-instance-1'
        logger.info(f'Creating writer instance: {instance_identifier}')

        instance_params = {
            'DBInstanceIdentifier': instance_identifier,
            'DBInstanceClass': 'db.serverless',
            'Engine': 'aurora-postgresql',
            'DBClusterIdentifier': cluster_identifier,
            'PubliclyAccessible': False,  # Set to True if needed
            'Tags': tags,
            'CopyTagsToSnapshot': True,
        }

        instance_create_start_time = time.time()
        rds_client.create_db_instance(**instance_params)

        logger.info(f'Writer instance {instance_identifier} created successfully')

        # Wait for instance to be available
        logger.info(f'Waiting for instance {instance_identifier} to become available...')
        instance_waiter = rds_client.get_waiter('db_instance_available')
        instance_waiter.wait(
            DBInstanceIdentifier=instance_identifier,
            WaiterConfig={
                'Delay': 1,  # check every  seconds
                'MaxAttempts': 1800,  # Try up to 1800 time = 30 mins
            },
        )

        logger.info(f'Instance {instance_identifier} is now available')
        instance_create_stop_time = time.time()
        elapsed_time = instance_create_stop_time - instance_create_start_time
        logger.info(f'Instance creation {instance_identifier} took {elapsed_time:.2f} seconds')

        # Get the final cluster details including the secret ARN
        final_cluster = rds_client.describe_db_clusters(DBClusterIdentifier=cluster_identifier)[
            'DBClusters'
        ][0]

        return final_cluster

    except ClientError as e:
        logger.error(
            f"AWS error creating serverless cluster '{cluster_identifier}': "
            f'{e.response["Error"]["Code"]} - {e.response["Error"]["Message"]}'
        )
        raise
    except Exception as e:
        logger.error(
            f"Error creating serverless cluster '{cluster_identifier}': {type(e).__name__}: {e}"
        )
        raise


def setup_aurora_iam_policy_for_current_user(
    db_user: str, cluster_resource_id: str, cluster_region: str
) -> Optional[str]:
    """Create or update IAM policy for Aurora access.

    Maintains one policy per user, adding new clusters as they're created.

    ⚠️  If running as assumed role, this will attempt to attach the policy to
        the BASE ROLE (not the session). This requires iam:AttachRolePolicy permission.

    Args:
        db_user: PostgreSQL username (must have rds_iam role granted in database)
        cluster_resource_id: The DBI resource ID (e.g., 'cluster-ABCD123XYZ')
        cluster_region: AWS region where the Aurora cluster is located

    Returns:
        Policy ARN if successful, None otherwise

    Raises:
        ValueError: If running as federated user, root, or invalid identity
        boto3 exceptions: For AWS API errors (except AccessDenied on attach)
    """
    # Validate inputs
    if not db_user or not isinstance(db_user, str):
        raise ValueError('db_user must be a non-empty string')
    if not cluster_resource_id or not isinstance(cluster_resource_id, str):
        raise ValueError('cluster_resource_id must be a non-empty string')
    if not cluster_region or not isinstance(cluster_region, str):
        raise ValueError('cluster_region must be a non-empty string')

    # Initialize clients
    sts = boto3.client('sts', config=Config(user_agent_extra=__user_agent__))
    iam = boto3.client('iam', config=Config(user_agent_extra=__user_agent__))

    # 1. Get current IAM identity
    try:
        identity = sts.get_caller_identity()
        account_id = identity['Account']
        arn = identity['Arn']
        user_id = identity['UserId']

        logger.info('Current Identity:')
        logger.info(f'  ARN: {arn}')
        logger.info(f'  Account: {account_id}')
        logger.info(f'  UserID: {user_id}')

    except Exception as e:
        logger.error(f'❌ Error getting caller identity: {e}')
        raise

    # ============================================================================
    # 🔵 MODIFIED: Extract base role from assumed role session
    # ============================================================================
    # 2. Extract username/role from ARN and determine identity type
    current_user = None
    current_role = None
    identity_type = None

    if ':user/' in arn:
        # Standard IAM user: arn:aws:iam::123456789012:user/username
        current_user = arn.split(':user/')[-1].split('/')[-1]
        identity_type = 'user'
        logger.info('  Type: IAM User')
        logger.info(f'  Username: {current_user}')

    elif ':assumed-role/' in arn:
        # 🔵 MODIFIED: Extract BASE ROLE name from assumed role session
        # Assumed role ARN: arn:aws:sts::123456789012:assumed-role/RoleName/session-name
        # We want to extract "RoleName" (the base role)
        parts = arn.split(':assumed-role/')[-1].split('/')
        current_role = parts[0]  # This is the BASE ROLE name
        session_name = parts[1] if len(parts) > 1 else 'unknown'

        identity_type = 'role'
        logger.info('  Type: Assumed Role Session')
        logger.info(f'  Base Role: {current_role}')
        logger.info(f'  Session Name: {session_name}')
        logger.info(f'  → Will attach policy to base role: {current_role}')
        logger.warning(
            f"⚠️  Policy will be attached to role '{current_role}'\n"
            f'   This will grant Aurora access to ALL users/services that assume this role.'
        )

    elif ':federated-user/' in arn:
        logger.error('  Type: Federated User')
        raise ValueError(
            'Cannot attach policies to federated users.\n'
            'Please use the parent IAM user or role instead.'
        )

    elif ':root' in arn:
        logger.error('  Type: Root User')
        raise ValueError(
            'Cannot (and should not) attach policies to root user.\n'
            'Please use an IAM user instead.'
        )

    else:
        raise ValueError(f'Unexpected ARN format: {arn}')

    # 3. Prepare new resource ARN
    policy_name = f'AuroraIAMAuth-{db_user}'
    policy_arn = f'arn:aws:iam::{account_id}:policy/{policy_name}'

    new_resource_arn = (
        f'arn:aws:rds-db:{cluster_region}:{account_id}:dbuser:{cluster_resource_id}/{db_user}'
    )

    logger.info('\nPolicy Configuration:')
    logger.info(f'  Policy Name: {policy_name}')
    logger.info(f'  New Resource: {new_resource_arn}')
    logger.info(f'  Cluster Region: {cluster_region}')
    logger.info(f'  Cluster Resource ID: {cluster_resource_id}')

    # 4. Create or update policy

    try:
        # Try to get existing policy
        existing_policy = iam.get_policy(PolicyArn=policy_arn)
        logger.info(f'\n✓ Policy already exists: {policy_name}')

        # Get current policy document
        policy_version = iam.get_policy_version(
            PolicyArn=policy_arn, VersionId=existing_policy['Policy']['DefaultVersionId']
        )

        current_doc = policy_version['PolicyVersion']['Document']
        current_resources = current_doc['Statement'][0]['Resource']

        # Normalize to list (could be string or list)
        if isinstance(current_resources, str):
            current_resources = [current_resources]

        logger.info(f'  Current resources in policy: {len(current_resources)}')
        for idx, res in enumerate(current_resources, 1):
            logger.info(f'    {idx}. {res}')

        # Check if new resource already exists
        if new_resource_arn in current_resources:
            logger.info('\n✓ Cluster already included in policy - no update needed')
        else:
            # Add new resource to the list
            current_resources.append(new_resource_arn)
            logger.info('\n→ Adding new cluster to policy...')

            # Create updated policy document
            updated_doc = {
                'Version': '2012-10-17',
                'Statement': [
                    {'Effect': 'Allow', 'Action': 'rds-db:connect', 'Resource': current_resources}
                ],
            }

            # Handle AWS policy version limits (max 5 versions per policy)
            versions = iam.list_policy_versions(PolicyArn=policy_arn)['Versions']
            logger.info(f'  Current policy versions: {len(versions)}/5')

            if len(versions) >= 5:
                # Find oldest non-default version to delete
                non_default_versions = [v for v in versions if not v['IsDefaultVersion']]
                if non_default_versions:
                    oldest_version = sorted(non_default_versions, key=lambda v: v['CreateDate'])[0]
                    logger.info(
                        f'  Deleting oldest version: {oldest_version["VersionId"]} (created {oldest_version["CreateDate"]})'
                    )
                    iam.delete_policy_version(
                        PolicyArn=policy_arn, VersionId=oldest_version['VersionId']
                    )

            # Create new policy version
            new_version = iam.create_policy_version(
                PolicyArn=policy_arn,
                PolicyDocument=json.dumps(updated_doc, indent=2),
                SetAsDefault=True,
            )

            logger.info('✓ Successfully updated policy')
            logger.info(f'  New version: {new_version["PolicyVersion"]["VersionId"]}')
            logger.info(f'  Total resources now: {len(current_resources)}')

    except iam.exceptions.NoSuchEntityException:
        # Policy doesn't exist - create new one
        logger.info("\nPolicy doesn't exist, creating new policy...")

        policy_document = {
            'Version': '2012-10-17',
            'Statement': [
                {'Effect': 'Allow', 'Action': 'rds-db:connect', 'Resource': [new_resource_arn]}
            ],
        }

        try:
            policy_response = iam.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document, indent=2),
                Description=f'IAM authentication for Aurora PostgreSQL user {db_user} across all clusters',
            )
            policy_arn = policy_response['Policy']['Arn']
            logger.info(f'✓ Successfully created new policy: {policy_name}')
            logger.info(f'  Policy ARN: {policy_arn}')

        except iam.exceptions.EntityAlreadyExistsException:
            logger.info('✓ Policy was just created by another process')

        except Exception as e:
            logger.error(f'\n❌ Error creating policy: {e}')
            raise

    except Exception as e:
        logger.error(f'\n❌ Error checking/updating policy: {e}')
        trace_msg = traceback.format_exc()
        logger.error(f'Traceback: {trace_msg}')
        raise

    # ============================================================================
    # 🔵 MODIFIED: Attach to base role with better error handling
    # ============================================================================
    # 5. Attach policy to current user OR base role
    try:
        if identity_type == 'user':
            # IAM User - attach directly
            attached_policies = iam.list_attached_user_policies(UserName=current_user)
            already_attached = any(
                p['PolicyArn'] == policy_arn for p in attached_policies['AttachedPolicies']
            )

            if already_attached:
                logger.info(f'\n✓ Policy already attached to user: {current_user}')
            else:
                iam.attach_user_policy(UserName=current_user, PolicyArn=policy_arn)
                logger.info(f'\n✓ Successfully attached policy to user: {current_user}')

            # Display summary
            logger.info(f'\nAttached policies for user {current_user}:')
            attached_policies = iam.list_attached_user_policies(UserName=current_user)
            for policy in attached_policies['AttachedPolicies']:
                marker = '  → ' if policy['PolicyArn'] == policy_arn else '    '
                logger.info(f'{marker}{policy["PolicyName"]}')

        elif identity_type == 'role':
            # 🔵 MODIFIED: Attach to BASE ROLE (not session)
            logger.info(f'\n→ Attempting to attach policy to base role: {current_role}')

            try:
                # Check if already attached to the base role
                attached_policies = iam.list_attached_role_policies(RoleName=current_role)
                already_attached = any(
                    p['PolicyArn'] == policy_arn for p in attached_policies['AttachedPolicies']
                )

                if already_attached:
                    logger.info(f'\n✓ Policy already attached to role: {current_role}')
                else:
                    # Attach to the BASE ROLE
                    iam.attach_role_policy(RoleName=current_role, PolicyArn=policy_arn)
                    logger.info(f'\n✓ Successfully attached policy to role: {current_role}')
                    logger.warning(
                        f"⚠️  All users/services assuming role '{current_role}' now have Aurora access"
                    )

                # Display summary
                logger.info(f'\nAttached policies for role {current_role}:')
                attached_policies = iam.list_attached_role_policies(RoleName=current_role)
                for policy in attached_policies['AttachedPolicies']:
                    marker = '  → ' if policy['PolicyArn'] == policy_arn else '    '
                    logger.info(f'{marker}{policy["PolicyName"]}')

            except iam.exceptions.AccessDeniedException:
                # 🔵 MODIFIED: Graceful handling of permission denied
                logger.error(f"\n❌ Access Denied: Cannot attach policy to role '{current_role}'")
                logger.error("   Your session does not have 'iam:AttachRolePolicy' permission")
                logger.info(f'\n✓ Policy created successfully: {policy_arn}')
                logger.info('   But could not be attached automatically.')
                logger.info('\n📋 MANUAL STEPS REQUIRED:')
                logger.info('\n Option 1: Have an administrator attach the policy to the role')
                logger.info('   aws iam attach-role-policy \\')
                logger.info(f'     --role-name {current_role} \\')
                logger.info(f'     --policy-arn {policy_arn}')
                logger.info('\n Option 2: Attach to your individual IAM user (if you have one)')
                logger.info('   aws iam attach-user-policy \\')
                logger.info('     --user-name YOUR_IAM_USERNAME \\')
                logger.info(f'     --policy-arn {policy_arn}')
                logger.info('\n Option 3: Grant the role permission to attach policies')
                logger.info(
                    f"   (Admin needs to add iam:AttachRolePolicy to role '{current_role}')"
                )

                # Return policy ARN even though not attached
                return policy_arn

            except iam.exceptions.NoSuchEntityException:
                logger.error(f"\n❌ Role '{current_role}' not found")
                logger.error("   This is unexpected - the role should exist since you're using it")
                raise

        return policy_arn

    except iam.exceptions.NoSuchEntityException:
        entity_name = current_user if identity_type == 'user' else current_role
        entity_type = 'User' if identity_type == 'user' else 'Role'
        logger.error(f"\n❌ Error: {entity_type} '{entity_name}' not found")
        raise

    except iam.exceptions.LimitExceededException:
        entity_name = current_user if identity_type == 'user' else current_role
        entity_type = 'user' if identity_type == 'user' else 'role'
        logger.error(
            f"\n❌ Error: Managed policy limit exceeded for {entity_type} '{entity_name}'"
        )
        logger.error('Maximum 10 managed policies can be attached to a user or role')
        logger.error('Consider using inline policies or consolidating existing policies')
        raise

    except Exception as e:
        logger.error(f'\n❌ Error attaching policy: {e}')
        trace_msg = traceback.format_exc()
        logger.error(f'Traceback: {trace_msg}')
        raise
