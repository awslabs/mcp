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

"""Common Resource handler for the Data Processing MCP Server."""

import json
import os
from awslabs.aws_dataprocessing_mcp_server.models.common_resource_models import (
    AddInlinePolicyResponse,
    AnalyzeS3UsageResponse,
    CreateRoleResponse,
    ListS3BucketsResponse,
    PolicySummary,
    RoleDescriptionResponse,
    RoleSummary,
    ServiceRolesResponse,
    UploadToS3Response,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from botocore.exceptions import ClientError
from datetime import datetime
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional, Union


class CommonResourceHandler:
    """Handler for AWS Common Resource operations in the Data Processing MCP Server.

    This class provides tools for managing IAM roles and policies, S3 buckets and objects,
    including describing roles with their attached policies, adding inline permissions
    to policies, creating roles with specific trust relationships for data processing
    services like Glue, EMR, and Athena, and managing S3 resources.
    """

    def __init__(self, mcp, allow_write: bool = False):
        """Initialize the Common Resource handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
        """
        self.mcp = mcp
        self.iam_client = AwsHelper.create_boto3_client('iam')
        self.s3_client = AwsHelper.create_boto3_client('s3')
        self.allow_write = allow_write

        # Register IAM tools
        self.mcp.tool(name='add_inline_policy')(self.add_inline_policy)
        self.mcp.tool(name='get_policies_for_role')(self.get_policies_for_role)
        self.mcp.tool(name='create_data_processing_role')(self.create_data_processing_role)
        self.mcp.tool(name='get_roles_for_service')(self.get_roles_for_service)

        # Register S3 tools
        self.mcp.tool(name='list_s3_buckets')(self.list_s3_buckets)
        self.mcp.tool(name='upload_to_s3')(self.upload_to_s3)
        self.mcp.tool(name='analyze_s3_usage_for_data_processing')(
            self.analyze_s3_usage_for_data_processing
        )

    # ============================================================================
    # IAM Operations
    # ============================================================================

    async def get_policies_for_role(
        self,
        ctx: Context,
        role_name: Annotated[
            str,
            Field(
                description='Name of the IAM role to get policies for. The role must exist in your AWS account.',
            ),
        ],
    ) -> RoleDescriptionResponse:
        """Get all policies attached to an IAM role.

        This tool retrieves all policies associated with an IAM role, providing a comprehensive view
        of the role's permissions and trust relationships. It helps you understand the current
        permissions, identify missing or excessive permissions, troubleshoot data processing issues,
        and verify trust relationships for service roles.

        ## Requirements
        - The role must exist in your AWS account
        - Valid AWS credentials with permissions to read IAM role information

        ## Response Information
        The response includes role ARN, assume role policy document (trust relationships),
        role description, managed policies with their documents, and inline policies with
        their documents.

        ## Usage Tips
        - Use this tool before adding new permissions to understand existing access
        - Check the assume role policy to verify which services or roles can assume this role
        - Look for overly permissive policies that might pose security risks
        - Use with add_inline_policy to implement least-privilege permissions
        - For Glue jobs, ensure the role has access to required data sources and targets
        - For EMR clusters, verify EC2 instance profile permissions
        - For Athena queries, check S3 bucket access permissions

        Args:
            ctx: The MCP context
            role_name: Name of the IAM role to get policies for

        Returns:
            RoleDescriptionResponse: Detailed information about the role's policies
        """
        try:
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Common Resource Handler - Tool: get_policies_for_role - Operation: describe role policies for {role_name}',
            )

            # Get role details
            role_response = self.iam_client.get_role(RoleName=role_name)
            role = role_response['Role']

            # Get attached managed policies
            managed_policies = self._get_managed_policies(ctx, role_name)

            # Get inline policies
            inline_policies = self._get_inline_policies(ctx, role_name)

            # Parse the assume role policy document if it's a string, otherwise use it directly
            if isinstance(role['AssumeRolePolicyDocument'], str):
                assume_role_policy_document = json.loads(role['AssumeRolePolicyDocument'])
            else:
                assume_role_policy_document = role['AssumeRolePolicyDocument']

            # Create the response
            return RoleDescriptionResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully retrieved details for IAM role: {role_name}',
                    )
                ],
                role_arn=role['Arn'],
                assume_role_policy_document=assume_role_policy_document,
                description=role.get('Description'),
                managed_policies=managed_policies,
                inline_policies=inline_policies,
            )
        except Exception as e:
            error_message = f'Failed to describe IAM role: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            # Return a response with error status
            return RoleDescriptionResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                role_arn='',
                assume_role_policy_document={},
                description=None,
                managed_policies=[],
                inline_policies=[],
            )

    async def add_inline_policy(
        self,
        ctx: Context,
        policy_name: Annotated[
            str,
            Field(
                description='Name of the inline policy to create. Must be unique within the role.',
            ),
        ],
        role_name: Annotated[
            str,
            Field(
                description='Name of the IAM role to add the policy to. The role must exist.',
            ),
        ],
        permissions: Annotated[
            Union[Dict[str, Any], List[Dict[str, Any]]],
            Field(
                description="""Permissions to include in the policy as IAM policy statements in JSON format.
            Can be either a single statement object or an array of statement objects.""",
            ),
        ],
    ) -> AddInlinePolicyResponse:
        """Add a new inline policy to an IAM role.

        This tool creates a new inline policy with the specified permissions and adds it to an IAM role.
        Inline policies are embedded within the role and cannot be attached to multiple roles. Commonly used
        for granting data processing services access to AWS resources, enabling Glue jobs to access data sources,
        and configuring permissions for CloudWatch logging and S3 access.

        ## Requirements
        - The server must be run with the `--allow-write` flag
        - The role must exist in your AWS account
        - The policy name must be unique within the role
        - You cannot modify existing policies with this tool

        ## Permission Format
        The permissions parameter can be either a single policy statement or a list of statements.

        ### Single Statement Example
        ```json
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:PutObject"],
            "Resource": "arn:aws:s3:::example-bucket/*"
        }
        ```

        ## Common Data Processing Permission Examples

        ### Glue Job Permissions
        ```json
        {
            "Effect": "Allow",
            "Action": [
                "glue:*",
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "iam:PassRole"
            ],
            "Resource": "*"
        }
        ```

        ### EMR Cluster Permissions
        ```json
        {
            "Effect": "Allow",
            "Action": [
                "elasticmapreduce:*",
                "ec2:DescribeInstances",
                "ec2:DescribeSecurityGroups",
                "s3:ListBucket",
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": "*"
        }
        ```

        ### Athena Query Permissions
        ```json
        {
            "Effect": "Allow",
            "Action": [
                "athena:*",
                "glue:GetDatabase",
                "glue:GetTable",
                "glue:GetPartition",
                "s3:GetObject",
                "s3:ListBucket",
                "s3:PutObject"
            ],
            "Resource": "*"
        }
        ```

        ## Usage Tips
        - Follow the principle of least privilege by granting only necessary permissions
        - Use specific resources rather than "*" whenever possible
        - Consider using conditions to further restrict permissions
        - Group related permissions into logical policies with descriptive names

        Args:
            ctx: The MCP context
            policy_name: Name of the new inline policy to create
            role_name: Name of the role to add the policy to
            permissions: Permissions to include in the policy (in JSON format)

        Returns:
            AddInlinePolicyResponse: Information about the created policy
        """
        try:
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f"Common Resource Handler - Tool: add_inline_policy - Operation: add inline policy '{policy_name}' to role '{role_name}'",
            )

            # Check if write access is disabled
            if not self.allow_write:
                error_message = 'Adding inline policies requires --allow-write flag'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return AddInlinePolicyResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    policy_name=policy_name,
                    role_name=role_name,
                    permissions_added={},
                )

            # Create the inline policy
            return self._create_inline_policy(ctx, role_name, policy_name, permissions)

        except Exception as e:
            error_message = f'Failed to create inline policy: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            # Return a response with error status
            return AddInlinePolicyResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                policy_name=policy_name,
                role_name=role_name,
                permissions_added={},
            )

    async def create_data_processing_role(
        self,
        ctx: Context,
        role_name: Annotated[
            str,
            Field(
                description='Name of the IAM role to create. Must be unique within your AWS account.',
            ),
        ],
        service_type: Annotated[
            str,
            Field(
                description="Type of data processing service: 'glue', 'emr', or 'athena'.",
            ),
        ],
        description: Annotated[
            Optional[str],
            Field(
                description='Optional description for the IAM role.',
            ),
        ] = None,
        managed_policy_arns: Annotated[
            Optional[List[str]],
            Field(
                description='Optional list of managed policy ARNs to attach to the role.',
            ),
        ] = None,
        inline_policy: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='Optional inline policy to add to the role.',
            ),
        ] = None,
    ) -> CreateRoleResponse:
        """Create a new IAM role for data processing services.

        This tool creates a new IAM role with the appropriate trust relationship for the specified
        data processing service (Glue, EMR, or Athena). It can also attach managed policies and
        add an inline policy to the role.

        ## Requirements
        - The server must be run with the `--allow-write` flag
        - The role name must be unique within your AWS account
        - Valid AWS credentials with permissions to create IAM roles

        ## Service Types
        - **glue**: Creates a role that can be assumed by the Glue service
        - **emr**: Creates a role that can be assumed by the EMR service
        - **athena**: Creates a role that can be assumed by the Athena service

        ## Common Managed Policies. add these policies
        - Glue: 'arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole'
        - EMR: 'arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole'
        - Athena: 'arn:aws:iam::aws:policy/service-role/AmazonAthenaFullAccess'

        ## Usage Tips
        - Always provide a descriptive name and description for the role
        - Attach only the necessary managed policies to follow least privilege
        - Use inline policies for custom permissions specific to your use case
        - Consider adding S3 access permissions for data sources and targets

        Args:
            ctx: The MCP context
            role_name: Name of the IAM role to create
            service_type: Type of data processing service
            description: Optional description for the IAM role
            managed_policy_arns: Optional list of managed policy ARNs to attach
            inline_policy: Optional inline policy to add to the role

        Returns:
            CreateRoleResponse: Information about the created role
        """
        try:
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f"Common Resource Handler - Tool: create_data_processing_role - Operation: create role '{role_name}' for service '{service_type}'",
            )

            # Check if write access is disabled
            if not self.allow_write:
                error_message = 'Creating roles requires --allow-write flag'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return CreateRoleResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    role_name=role_name,
                    role_arn='',
                )

            # Validate service type
            if service_type not in ['glue', 'emr', 'athena']:
                error_message = (
                    f'Invalid service type: {service_type}. Must be one of: glue, emr, athena'
                )
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return CreateRoleResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    role_name=role_name,
                    role_arn='',
                )

            # Create the trust relationship based on service type
            trust_relationship = self._get_trust_relationship_for_service(service_type)

            # Create the role
            log_with_request_id(
                ctx, LogLevel.INFO, f'Creating IAM role: {role_name} for {service_type}'
            )

            create_role_params = {
                'RoleName': role_name,
                'AssumeRolePolicyDocument': json.dumps(trust_relationship),
            }

            if description:
                create_role_params['Description'] = description

            role_response = self.iam_client.create_role(**create_role_params)
            role_arn = role_response['Role']['Arn']

            # Attach managed policies if provided
            if managed_policy_arns:
                for policy_arn in managed_policy_arns:
                    log_with_request_id(
                        ctx,
                        LogLevel.INFO,
                        f'Attaching managed policy {policy_arn} to role {role_name}',
                    )
                    self.iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)

            # Add inline policy if provided
            if inline_policy:
                policy_name = f'{role_name}-inline-policy'
                log_with_request_id(
                    ctx,
                    LogLevel.INFO,
                    f'Adding inline policy {policy_name} to role {role_name}',
                )
                policy_document = {
                    'Version': '2012-10-17',
                    'Statement': (
                        inline_policy if isinstance(inline_policy, list) else [inline_policy]
                    ),
                }
                self.iam_client.put_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name,
                    PolicyDocument=json.dumps(policy_document),
                )

            return CreateRoleResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully created IAM role {role_name} for {service_type}',
                    )
                ],
                role_name=role_name,
                role_arn=role_arn,
            )

        except Exception as e:
            error_message = f'Failed to create IAM role: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            # Return a response with error status
            return CreateRoleResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                role_name=role_name,
                role_arn='',
            )

    async def get_roles_for_service(
        self,
        ctx: Context,
        service_type: Annotated[
            str,
            Field(
                description="Type of data processing service: 'glue', 'emr', 'athena', or other AWS service name.",
            ),
        ],
    ) -> ServiceRolesResponse:
        """Get all IAM roles that can be assumed by a specific AWS service.

        This tool retrieves all IAM roles in your AWS account that have a trust relationship
        with the specified service. It helps you identify which roles can be used for services
        like Glue jobs, EMR clusters, or Athena queries, making it easier to select the appropriate
        role when creating these resources.

        ## Service Types
        Common service types include:
        - **glue**: AWS Glue service (glue.amazonaws.com)
        - **emr**: Amazon EMR service (elasticmapreduce.amazonaws.com)
        - **athena**: Amazon Athena service (athena.amazonaws.com)
        - You can also specify other AWS service principals

        ## Response Information
        The response includes a list of roles that can be assumed by the specified service,
        with details such as role name, ARN, description, creation date, and the full
        assume role policy document.

        ## Usage Tips
        - Use this tool to find existing roles before creating new ones
        - Verify that roles have the necessary permissions for your use case
        - For Glue jobs, look for roles with AWSGlueServiceRole or similar policies
        - For EMR clusters, look for roles with AmazonElasticMapReduceRole or similar policies
        - For Athena queries, look for roles with AmazonAthenaFullAccess or similar policies

        Args:
            ctx: The MCP context
            service_type: Type of data processing service

        Returns:
            ServiceRolesResponse: List of roles that can be assumed by the specified service
        """
        try:
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f"Common Resource Handler - Tool: get_roles_for_service - Operation: list roles for service '{service_type}'",
            )

            # Map service type to service principal
            service_principal = self._get_service_principal(service_type)

            # List all roles
            roles = []
            paginator = self.iam_client.get_paginator('list_roles')

            for page in paginator.paginate():
                for role in page.get('Roles', []):
                    # Parse the assume role policy document
                    if isinstance(role.get('AssumeRolePolicyDocument'), str):
                        assume_role_policy_document = json.loads(role['AssumeRolePolicyDocument'])
                    else:
                        assume_role_policy_document = role.get('AssumeRolePolicyDocument', {})

                    # Check if the role can be assumed by the specified service
                    if self._can_be_assumed_by_service(
                        assume_role_policy_document, service_principal
                    ):
                        roles.append(
                            RoleSummary(
                                role_name=role['RoleName'],
                                role_arn=role['Arn'],
                                description=role.get('Description'),
                                create_date=role['CreateDate'].isoformat(),
                                assume_role_policy_document=assume_role_policy_document,
                            )
                        )

            return ServiceRolesResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully retrieved {len(roles)} roles for service: {service_type}',
                    )
                ],
                service_type=service_type,
                roles=roles,
            )
        except Exception as e:
            error_message = f'Failed to list IAM roles for service {service_type}: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            # Return a response with error status
            return ServiceRolesResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                service_type=service_type,
                roles=[],
            )

    # ============================================================================
    # S3 Operations
    # ============================================================================

    async def list_s3_buckets(
        self,
        ctx: Context,
        region: Annotated[
            Optional[str],
            Field(
                description='AWS region to filter buckets by (defaults to AWS_REGION environment variable)',
            ),
        ] = None,
    ) -> ListS3BucketsResponse:
        """List S3 buckets that have 'glue' in their name and are in the specified region.

        This tool helps identify S3 buckets commonly used for data processing workflows,
        particularly those related to AWS Glue operations. It provides usage statistics
        and idle time information to help with resource management.

        ## Requirements
        - Valid AWS credentials with permissions to list S3 buckets
        - S3:ListAllMyBuckets permission

        ## Response Information
        The response includes bucket name, creation date, region, object count,
        last modified date, and idle time analysis.

        ## Usage Tips
        - Use this tool to find existing data processing buckets before creating new ones
        - Monitor idle buckets that haven't been accessed for 90+ days
        - Verify bucket regions match your data processing service regions
        - Check object counts to understand bucket usage patterns

        Args:
            ctx: The MCP context
            region: AWS region to filter buckets by

        Returns:
            ListS3BucketsResponse: Information about matching S3 buckets
        """
        try:
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                "Common Resource Handler - Tool: list_s3_buckets - Operation: list S3 buckets with 'glue' in name",
            )

            # Use provided region or get from environment variable
            aws_region = region or os.getenv('AWS_REGION', 'us-east-1')

            # Get all buckets
            response = self.s3_client.list_buckets()
            buckets = response['Buckets']

            # Initialize result
            result = (
                f"Looking for S3 buckets with 'glue' in their name in region {aws_region}:\n\n"
            )

            # Track matching buckets
            matching_buckets = []
            bucket_details = []

            # Process each bucket
            for bucket in buckets:
                bucket_name = bucket['Name']
                creation_date = bucket['CreationDate'].strftime('%Y-%m-%d')

                # Check if bucket name contains 'glue'
                if 'glue' in bucket_name.lower():
                    try:
                        # Get bucket location
                        location_response = self.s3_client.get_bucket_location(Bucket=bucket_name)
                        location = location_response.get('LocationConstraint', 'us-east-1')
                        if location is None:  # us-east-1 returns None
                            location = 'us-east-1'

                        # Check if bucket is in the specified region
                        if location.lower() == aws_region.lower():
                            matching_buckets.append(bucket)

                            # Get bucket objects (limited to 1000 for performance)
                            objects_response = self.s3_client.list_objects_v2(
                                Bucket=bucket_name, MaxKeys=1000
                            )
                            object_count = objects_response.get('KeyCount', 0)

                            # Check if truncated (more than 1000 objects)
                            if objects_response.get('IsTruncated', False):
                                object_count = f'{object_count}+ (truncated)'

                            # Get last modified date of most recent object if any objects exist
                            last_modified = 'N/A'
                            if (
                                object_count
                                and 'Contents' in objects_response
                                and objects_response['Contents']
                            ):
                                # Sort by last modified date in descending order
                                sorted_objects = sorted(
                                    objects_response['Contents'],
                                    key=lambda x: x['LastModified'],
                                    reverse=True,
                                )
                                last_modified = sorted_objects[0]['LastModified'].strftime(
                                    '%Y-%m-%d'
                                )

                            # Calculate idle time
                            if last_modified != 'N/A':
                                last_modified_date = datetime.strptime(last_modified, '%Y-%m-%d')
                                idle_days = (datetime.now() - last_modified_date).days
                                idle_status = f'{idle_days} days'

                                # Highlight idle buckets
                                if idle_days > 90:
                                    idle_status += ' (IDLE > 90 days)'
                            else:
                                idle_status = 'N/A'

                            # Store bucket details
                            bucket_info = {
                                'name': bucket_name,
                                'creation_date': creation_date,
                                'region': location,
                                'object_count': str(object_count),
                                'last_modified': last_modified,
                                'idle_status': idle_status,
                            }
                            bucket_details.append(bucket_info)

                            # Add bucket info to result
                            result += f'Bucket: {bucket_name}\n'
                            result += f'  Created: {creation_date}\n'
                            result += f'  Region: {location}\n'
                            result += f'  Objects: {object_count}\n'
                            result += f'  Last Modified: {last_modified}\n'
                            result += f'  Idle Time: {idle_status}\n\n'

                    except ClientError as e:
                        result += f'Bucket: {bucket_name}\n'
                        result += f'  Created: {creation_date}\n'
                        result += f'  Error getting details: {str(e)}\n\n'

            # Add summary
            if matching_buckets:
                result += f"Found {len(matching_buckets)} buckets with 'glue' in their name in region {aws_region}."
            else:
                result += f"No buckets found with 'glue' in their name in region {aws_region}."

            return ListS3BucketsResponse(
                isError=False,
                content=[TextContent(type='text', text=result)],
                region=aws_region,
                bucket_count=len(matching_buckets),
                buckets=bucket_details,
            )

        except ClientError as e:
            error_message = f'AWS Error: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return ListS3BucketsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                region=region or 'unknown',
                bucket_count=0,
                buckets=[],
            )
        except Exception as e:
            error_message = f'Error: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return ListS3BucketsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                region=region or 'unknown',
                bucket_count=0,
                buckets=[],
            )

    async def upload_to_s3(
        self,
        ctx: Context,
        code_content: Annotated[
            str,
            Field(
                description='String containing Python code to upload',
            ),
        ],
        bucket_name: Annotated[
            str,
            Field(
                description='Name of the S3 bucket',
            ),
        ],
        s3_key: Annotated[
            str,
            Field(
                description='S3 object key (path within the bucket)',
            ),
        ],
        make_public: Annotated[
            bool,
            Field(
                description='Whether to make the file publicly accessible (default: False)',
            ),
        ] = False,
    ) -> UploadToS3Response:
        """Upload Python code content directly to an S3 bucket using putObject.

        This tool uploads Python code content directly to an S3 bucket, commonly used
        for storing Glue job scripts, EMR step scripts, or other data processing code.
        The uploaded file can be referenced by data processing services.

        ## Requirements
        - The server must be run with the `--allow-write` flag
        - Valid AWS credentials with permissions to write to the specified S3 bucket
        - The bucket must exist and be accessible

        ## Usage Tips
        - Use descriptive S3 keys that include version information or timestamps
        - Store scripts in organized folder structures (e.g., glue-jobs/, emr-steps/)
        - Consider using versioning on the S3 bucket for script history
        - The returned S3 URI can be used directly in Glue job configurations

        Args:
            ctx: The MCP context
            code_content: String containing Python code to upload
            bucket_name: Name of the S3 bucket
            s3_key: S3 object key (path within the bucket)
            make_public: Whether to make the file publicly accessible

        Returns:
            UploadToS3Response: Information about the uploaded file
        """
        try:
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Common Resource Handler - Tool: upload_to_s3 - Operation: upload code to {bucket_name}/{s3_key}',
            )

            # Check if write access is disabled
            if not self.allow_write:
                error_message = 'Uploading to S3 requires --allow-write flag'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return UploadToS3Response(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    s3_uri='',
                    bucket_name=bucket_name,
                    s3_key=s3_key,
                )

            # Check if bucket exists
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    error_message = f"Bucket '{bucket_name}' does not exist"
                elif e.response['Error']['Code'] == '403':
                    error_message = f"Access denied to bucket '{bucket_name}'"
                else:
                    error_message = f'Error checking bucket: {str(e)}'

                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return UploadToS3Response(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    s3_uri='',
                    bucket_name=bucket_name,
                    s3_key=s3_key,
                )

            # Upload code content using putObject
            self.s3_client.put_object(
                Body=code_content,
                Bucket=bucket_name,
                Key=s3_key,
                ContentType='text/x-python',
            )

            # Make public if requested
            if make_public:
                self.s3_client.put_object_acl(Bucket=bucket_name, Key=s3_key, ACL='public-read')

            # Get bucket location for constructing the proper S3 URI
            location_response = self.s3_client.get_bucket_location(Bucket=bucket_name)
            region = location_response.get('LocationConstraint', 'us-east-1')
            if region is None:  # us-east-1 returns None
                region = 'us-east-1'

            # Construct S3 URIs
            s3_uri = f's3://{bucket_name}/{s3_key}'

            result = 'Python code uploaded successfully!\n\n'
            result += f'S3 URI: {s3_uri}\n'
            result += f'Region: {region}\n'

            return UploadToS3Response(
                isError=False,
                content=[TextContent(type='text', text=result)],
                s3_uri=s3_uri,
                bucket_name=bucket_name,
                s3_key=s3_key,
            )

        except ClientError as e:
            error_message = f'AWS Error: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return UploadToS3Response(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                s3_uri='',
                bucket_name=bucket_name,
                s3_key=s3_key,
            )
        except Exception as e:
            error_message = f'Error: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return UploadToS3Response(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                s3_uri='',
                bucket_name=bucket_name,
                s3_key=s3_key,
            )

    async def analyze_s3_usage_for_data_processing(
        self,
        ctx: Context,
        bucket_name: Annotated[
            Optional[str],
            Field(
                description='Optional specific bucket to analyze (None for all buckets)',
            ),
        ] = None,
    ) -> AnalyzeS3UsageResponse:
        """Analyze S3 bucket usage patterns for data processing services (Glue, EMR, Athena).

        This tool helps identify which buckets are actively used by data processing services
        and which ones might be idle or underutilized.

        Args:
            ctx: The MCP context
            bucket_name: Optional specific bucket to analyze (None for all buckets)

        Returns:
            AnalyzeS3UsageResponse: Analysis report of S3 usage patterns
        """
        try:
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                'Common Resource Handler - Tool: analyze_s3_usage_for_data_processing - Operation: analyze S3 usage',
            )

            # Create necessary clients
            glue_client = AwsHelper.create_boto3_client('glue')
            athena_client = AwsHelper.create_boto3_client('athena')
            emr_client = AwsHelper.create_boto3_client('emr')

            # Get buckets to analyze
            if bucket_name:
                try:
                    # Check if specific bucket exists
                    self.s3_client.head_bucket(Bucket=bucket_name)
                    buckets = [{'Name': bucket_name}]
                except ClientError:
                    error_message = f"Bucket '{bucket_name}' does not exist or is not accessible"
                    return AnalyzeS3UsageResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        analysis_summary='',
                        service_usage={},
                    )
            else:
                # Get all buckets
                response = self.s3_client.list_buckets()
                buckets = response['Buckets']

            # Initialize result
            result = 'S3 Usage Analysis for Data Processing Services\n'
            result += f'{"=" * 50}\n\n'

            # Track service usage
            service_usage = {
                'glue': [],
                'athena': [],
                'emr': [],
                'idle': [],
                'unknown': [],
            }

            # Analyze each bucket
            for bucket in buckets:
                bucket_name_res: str = bucket['Name']
                result += f'Analyzing bucket: {bucket_name_res}\n'

                # Initialize bucket usage flags
                usage = {
                    'glue': False,
                    'athena': False,
                    'emr': False,
                    'last_activity': None,
                }

                # Check Glue connections and crawlers for this bucket
                try:
                    # Check Glue connections
                    connections = glue_client.get_connections()
                    for conn in connections.get('ConnectionList', []):
                        conn_props = conn.get('ConnectionProperties', {})
                        if 'JDBC_CONNECTION_URL' in conn_props:
                            if bucket_name_res in (conn_props['JDBC_CONNECTION_URL'] or ''):
                                usage['glue'] = True
                                break

                    # Check Glue crawlers
                    crawlers = glue_client.get_crawlers()
                    for crawler in crawlers.get('Crawlers', []):
                        targets = crawler.get('Targets', {})
                        s3_targets = targets.get('S3Targets', [])
                        for target in s3_targets:
                            target_path = target.get('Path', '') or ''
                            if bucket_name_res in target_path:
                                usage['glue'] = True
                                break

                    # Check Glue jobs
                    jobs = glue_client.get_jobs()
                    for job in jobs.get('Jobs', []):
                        if 'DefaultArguments' in job:
                            for arg_key, arg_value in job['DefaultArguments'].items():
                                if isinstance(arg_value, str) and bucket_name_res in arg_value:
                                    usage['glue'] = True
                                    break
                except Exception as e:
                    result += f'  Error checking Glue usage: {str(e)}\n'

                # Check Athena workgroups for this bucket
                try:
                    workgroups = athena_client.list_work_groups()
                    for wg in workgroups.get('WorkGroups', []):
                        wg_name = wg['Name']
                        try:
                            wg_config = athena_client.get_work_group(WorkGroup=wg_name)
                            output_location = (
                                wg_config.get('WorkGroup', {})
                                .get('Configuration', {})
                                .get('ResultConfiguration', {})
                                .get('OutputLocation', '')
                            )
                            if bucket_name_res in output_location:
                                usage['athena'] = True
                                break
                        except Exception as e:
                            # Log the specific error and continue to next workgroup
                            result += (
                                f'    Warning: Could not check workgroup {wg_name}: {str(e)}\n'
                            )
                            continue
                except Exception as e:
                    result += f'  Error checking Athena usage: {str(e)}\n'

                # Check EMR clusters for this bucket
                try:
                    clusters = emr_client.list_clusters(ClusterStates=['RUNNING', 'WAITING'])
                    for cluster in clusters.get('Clusters', []):
                        cluster_id = cluster['Id']
                        try:
                            cluster_info = emr_client.describe_cluster(ClusterId=cluster_id)
                            log_uri = cluster_info.get('Cluster', {}).get('LogUri', '')
                            if bucket_name_res in log_uri:
                                usage['emr'] = True
                                break
                        except Exception as e:
                            # Log the specific error and continue to next cluster
                            result += (
                                f'    Warning: Could not check cluster {cluster_id}: {str(e)}\n'
                            )
                            continue
                except Exception as e:
                    result += f'  Error checking EMR usage: {str(e)}\n'

                # Get last modified date of most recent object
                try:
                    objects_response = self.s3_client.list_objects_v2(
                        Bucket=bucket_name_res, MaxKeys=1
                    )
                    if objects_response.get('KeyCount', 0) > 0 and 'Contents' in objects_response:
                        last_modified = objects_response['Contents'][0]['LastModified']
                        usage['last_activity'] = last_modified

                        # Calculate idle time
                        idle_days = (
                            datetime.now().replace(tzinfo=None)
                            - last_modified.replace(tzinfo=None)
                        ).days
                        result += f'  Last activity: {last_modified.strftime("%Y-%m-%d")} ({idle_days} days ago)\n'
                    else:
                        result += '  No objects found in bucket\n'
                except Exception as e:
                    result += f'  Error checking last activity: {str(e)}\n'

                # Determine bucket category
                if usage['glue']:
                    result += '  ✅ Used by AWS Glue\n'
                    service_usage['glue'].append(bucket_name_res)
                if usage['athena']:
                    result += '  ✅ Used by Amazon Athena\n'
                    service_usage['athena'].append(bucket_name_res)
                if usage['emr']:
                    result += '  ✅ Used by Amazon EMR\n'
                    service_usage['emr'].append(bucket_name_res)

                if not (usage['glue'] or usage['athena'] or usage['emr']):
                    # Check bucket name for hints
                    bucket_name_lower = bucket_name_res.lower()
                    if any(keyword in bucket_name_lower for keyword in ['glue', 'etl', 'crawler']):
                        result += (
                            '  ⚠️ Likely Glue bucket (based on name) but no active usage detected\n'
                        )
                        service_usage['glue'].append(bucket_name_res)
                    elif any(keyword in bucket_name_lower for keyword in ['athena', 'query']):
                        result += '  ⚠️ Likely Athena bucket (based on name) but no active usage detected\n'
                        service_usage['athena'].append(bucket_name_res)
                    elif any(
                        keyword in bucket_name_lower for keyword in ['emr', 'hadoop', 'spark']
                    ):
                        result += (
                            '  ⚠️ Likely EMR bucket (based on name) but no active usage detected\n'
                        )
                        service_usage['emr'].append(bucket_name_res)
                    else:
                        # Check if idle (no activity for 90+ days)
                        if (
                            usage['last_activity']
                            and (
                                datetime.now().replace(tzinfo=None)
                                - usage['last_activity'].replace(tzinfo=None)
                            ).days
                            > 90
                        ):
                            result += '  ⚠️ IDLE: No data processing service usage detected and no activity for 90+ days\n'
                            service_usage['idle'].append(bucket_name_res)
                        else:
                            result += '  ℹ️ No data processing service usage detected\n'
                            service_usage['unknown'].append(bucket_name_res)

                result += '\n'

            # Summary section
            result += f'\nSummary\n{"=" * 50}\n'
            result += f'Total buckets analyzed: {len(buckets)}\n\n'

            result += 'Glue Buckets:\n'
            for b in service_usage['glue']:
                result += f'  - {b}\n'

            result += '\nAthena Buckets:\n'
            for b in service_usage['athena']:
                result += f'  - {b}\n'

            result += '\nEMR Buckets:\n'
            for b in service_usage['emr']:
                result += f'  - {b}\n'

            result += '\nIdle Buckets (potential cleanup candidates):\n'
            for b in service_usage['idle']:
                result += f'  - {b}\n'

            return AnalyzeS3UsageResponse(
                isError=False,
                content=[TextContent(type='text', text=result)],
                analysis_summary=result,
                service_usage=service_usage,
            )

        except ClientError as e:
            error_message = f'AWS Error: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return AnalyzeS3UsageResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                analysis_summary='',
                service_usage={},
            )
        except Exception as e:
            error_message = f'Error: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return AnalyzeS3UsageResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                analysis_summary='',
                service_usage={},
            )

    # ============================================================================
    # Helper Methods
    # ============================================================================

    def _get_trust_relationship_for_service(self, service_type: str) -> Dict[str, Any]:
        """Get the trust relationship policy document for a specific service.

        Args:
            service_type: Type of data processing service (glue, emr, or athena)

        Returns:
            Dict[str, Any]: Trust relationship policy document
        """
        service_principals = {
            'glue': 'glue.amazonaws.com',
            'emr': 'elasticmapreduce.amazonaws.com',
            'athena': 'athena.amazonaws.com',
        }

        return {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'Service': service_principals[service_type]},
                    'Action': 'sts:AssumeRole',
                }
            ],
        }

    def _get_managed_policies(self, ctx, role_name):
        """Get managed policies attached to a role.

        Args:
            ctx: The MCP context
            role_name: Name of the IAM role

        Returns:
            List of PolicySummary objects
        """
        managed_policies = []
        managed_policies_response = self.iam_client.list_attached_role_policies(RoleName=role_name)

        for policy in managed_policies_response.get('AttachedPolicies', []):
            policy_arn = policy['PolicyArn']
            policy_details = self.iam_client.get_policy(PolicyArn=policy_arn)['Policy']

            # Get the policy version details to get the policy document
            policy_version = None
            try:
                policy_version_response = self.iam_client.get_policy_version(
                    PolicyArn=policy_arn,
                    VersionId=policy_details.get('DefaultVersionId', 'v1'),
                )
                policy_version = policy_version_response.get('PolicyVersion', {})
            except Exception as e:
                log_with_request_id(
                    ctx, LogLevel.WARNING, f'Failed to get policy version: {str(e)}'
                )

            managed_policies.append(
                PolicySummary(
                    policy_type='Managed',
                    description=policy_details.get('Description'),
                    policy_document=(policy_version.get('Document') if policy_version else None),
                )
            )

        return managed_policies

    def _get_inline_policies(self, ctx, role_name):
        """Get inline policies embedded in a role.

        Args:
            ctx: The MCP context
            role_name: Name of the IAM role

        Returns:
            List of PolicySummary objects
        """
        inline_policies = []
        inline_policies_response = self.iam_client.list_role_policies(RoleName=role_name)

        for policy_name in inline_policies_response.get('PolicyNames', []):
            policy_response = self.iam_client.get_role_policy(
                RoleName=role_name, PolicyName=policy_name
            )

            inline_policies.append(
                PolicySummary(
                    policy_type='Inline',
                    description=None,
                    policy_document=policy_response.get('PolicyDocument'),
                )
            )

        return inline_policies

    def _create_inline_policy(self, ctx, role_name, policy_name, permissions):
        """Create a new inline policy with the specified permissions.

        Args:
            ctx: The MCP context
            role_name: Name of the role
            policy_name: Name of the new policy to create
            permissions: Permissions to include in the policy

        Returns:
            AddInlinePolicyResponse: Information about the created policy
        """
        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Creating new inline policy {policy_name} in role {role_name}',
        )

        # Check if the policy already exists
        try:
            self.iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
            # If we get here, the policy exists
            error_message = f'Policy {policy_name} already exists in role {role_name}. Cannot modify existing policies.'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return AddInlinePolicyResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                policy_name=policy_name,
                role_name=role_name,
                permissions_added={},
            )
        except self.iam_client.exceptions.NoSuchEntityException:
            # Policy doesn't exist, we can create it
            pass

        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Entity not present a new inline policy {policy_name} will be added to role {role_name}',
        )

        # Create a new policy document
        policy_document = {'Version': '2012-10-17', 'Statement': []}

        # Add the permissions to the policy document
        self._add_permissions_to_document(policy_document, permissions)

        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'policy_document added for {role_name}',
        )

        # Create the policy
        self.iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document),
        )

        return AddInlinePolicyResponse(
            isError=False,
            content=[
                TextContent(
                    type='text',
                    text=f'Successfully created new inline policy {policy_name} in role {role_name}',
                )
            ],
            policy_name=policy_name,
            role_name=role_name,
            permissions_added=permissions,
        )

    def _get_service_principal(self, service_type: str) -> str:
        """Get the service principal for a specific service type.

        Args:
            service_type: Type of data processing service

        Returns:
            str: Service principal
        """
        # Common service principals
        service_principals = {
            'glue': 'glue.amazonaws.com',
            'emr': 'elasticmapreduce.amazonaws.com',
            'athena': 'athena.amazonaws.com',
            'lambda': 'lambda.amazonaws.com',
            'ec2': 'ec2.amazonaws.com',
            'ecs': 'ecs.amazonaws.com',
            'eks': 'eks.amazonaws.com',
            's3': 's3.amazonaws.com',
            'sagemaker': 'sagemaker.amazonaws.com',
            'cloudformation': 'cloudformation.amazonaws.com',
            'codebuild': 'codebuild.amazonaws.com',
            'codepipeline': 'codepipeline.amazonaws.com',
            'states': 'states.amazonaws.com',
        }

        # Return the service principal if it exists in the mapping, otherwise use the service type as is
        return service_principals.get(service_type.lower(), f'{service_type}.amazonaws.com')

    def _can_be_assumed_by_service(
        self, assume_role_policy_document: Dict[str, Any], service_principal: str
    ) -> bool:
        """Check if a role can be assumed by a specific service.

        Args:
            assume_role_policy_document: Assume role policy document
            service_principal: Service principal to check

        Returns:
            bool: True if the role can be assumed by the service, False otherwise
        """
        # Check if the policy document has statements
        if not assume_role_policy_document or 'Statement' not in assume_role_policy_document:
            return False

        # Check each statement
        for statement in assume_role_policy_document['Statement']:
            # Only process Allow statements
            if statement.get('Effect') != 'Allow':
                continue

            # Check if the statement allows the sts:AssumeRole action
            action = statement.get('Action', [])
            has_assume_role_action = False

            if isinstance(action, str):
                has_assume_role_action = action == 'sts:AssumeRole'
            elif isinstance(action, list):
                has_assume_role_action = 'sts:AssumeRole' in action

            if not has_assume_role_action:
                continue

            # Check if the statement allows the service principal
            principal = statement.get('Principal', {})
            if 'Service' in principal:
                service = principal['Service']
                if isinstance(service, str):
                    if service == service_principal:
                        return True
                elif isinstance(service, list):
                    if service_principal in service:
                        return True

        return False

    def _add_permissions_to_document(self, policy_document, permissions):
        """Add permissions to a policy document.

        Args:
            policy_document: Policy document to modify
            permissions: Permissions to add
        """
        if isinstance(permissions, dict):
            # Single statement
            policy_document['Statement'].append(permissions)
        elif isinstance(permissions, list):
            # Multiple statements
            policy_document['Statement'].extend(permissions)
