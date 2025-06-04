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

"""EKS stack handler for the EKS MCP Server."""

import os
import yaml
from awslabs.eks_mcp_server.aws_helper import AwsHelper
from awslabs.eks_mcp_server.consts import (
    CFN_CAPABILITY_IAM,
    CFN_ON_FAILURE_DELETE,
    CFN_STACK_NAME_TEMPLATE,
    CFN_STACK_TAG_KEY,
    CFN_STACK_TAG_VALUE,
    DELETE_OPERATION,
    DEPLOY_OPERATION,
    DESCRIBE_OPERATION,
    GENERATE_OPERATION,
    STACK_NOT_OWNED_ERROR_TEMPLATE,
)
from awslabs.eks_mcp_server.logging_helper import LogLevel, log_with_request_id
from awslabs.eks_mcp_server.models import (
    DeleteStackResponse,
    DeployStackResponse,
    DescribeStackResponse,
    GenerateTemplateResponse,
)
from mcp.server.fastmcp import Context
from mcp.types import EmbeddedResource, ImageContent, TextContent
from pydantic import Field
from typing import Any, Dict, List, Optional, Tuple, Union, cast


class EksStackHandler:
    """Handler for Amazon EKS CloudFormation stack operations.

    This class provides tools for creating, managing, and deleting CloudFormation
    stacks for EKS clusters.
    """

    def __init__(self, mcp, allow_write: bool = False):
        """Initialize the EKS stack handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write

        # Register tools
        self.mcp.tool(name='manage_eks_stacks')(self.manage_eks_stacks)

    def _ensure_stack_ownership(
        self, ctx: Context, stack_name: str, operation: str
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Ensure that a stack exists and was created by this tool.

        Args:
            ctx: The MCP context
            stack_name: Name of the stack to verify
            operation: Operation being performed (for error messages)

        Returns:
            Tuple of (success, stack_details, error_message)
            - success: True if the stack exists and was created by this tool
            - stack_details: Stack details if the stack exists, None otherwise
            - error_message: Error message if the stack doesn't exist or wasn't created by this tool, None if successful
        """
        try:
            # Create CloudFormation client
            cfn_client = AwsHelper.create_boto3_client('cloudformation')

            # Get stack details
            stack_details = cfn_client.describe_stacks(StackName=stack_name)
            stack = stack_details['Stacks'][0]

            # Verify the stack was created by our tool
            tags = stack.get('Tags', [])
            is_our_stack = False
            for tag in tags:
                if tag.get('Key') == CFN_STACK_TAG_KEY and tag.get('Value') == CFN_STACK_TAG_VALUE:
                    is_our_stack = True
                    break

            if not is_our_stack:
                error_message = STACK_NOT_OWNED_ERROR_TEMPLATE.format(
                    stack_name=stack_name, tool_name=CFN_STACK_TAG_VALUE, operation=operation
                )
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return False, stack, error_message

            return True, stack, None
        except Exception as e:
            if 'does not exist' in str(e):
                error_message = f'Stack {stack_name} not found or cannot be accessed: {str(e)}'
            else:
                error_message = f'Error verifying stack ownership: {str(e)}'

            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return False, None, error_message

    async def manage_eks_stacks(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: generate, deploy, describe, or delete. Choose "describe" for read-only operations when write access is disabled.',
        ),
        template_file: Optional[str] = Field(
            None,
            description="""Absolute path for the CloudFormation template (for generate and deploy operations).
            IMPORTANT: Assistant must provide the full absolute path to the template file, as the MCP client and server might not run from the same location.""",
        ),
        cluster_name: Optional[str] = Field(
            None,
            description="""Name of the EKS cluster (for generate, deploy, describe and delete operations).
            This name will be used to derive the CloudFormation stack name and will be embedded in the cluster resources.""",
        ),
    ) -> Union[
        GenerateTemplateResponse, DeployStackResponse, DescribeStackResponse, DeleteStackResponse
    ]:
        """Manage EKS CloudFormation stacks with both read and write operations.

        This tool provides operations for managing EKS CloudFormation stacks, including creating templates,
        deploying stacks, retrieving stack information, and deleting stacks. It serves as the primary
        mechanism for creating and managing EKS clusters through CloudFormation, enabling standardized
        cluster creation, configuration updates, and resource cleanup.

        IMPORTANT: Use this tool instead of 'aws eks create-cluster', 'aws eks delete-cluster',
        'eksctl create cluster', 'eksctl delete cluster', or similar CLI commands.

        IMPORTANT: Use this tool's standardized templates for creating EKS clusters with proper VPC configuration,
        networking, security groups, and EKS auto mode. DO NOT create EKS clusters by generating CloudFormation
        templates from scratch.

        ## Requirements
        - The server must be run with the `--allow-write` flag for generate, deploy, and delete operations
        - For deploy and delete operations, the stack must have been created by this tool
        - For template_file parameter, the path must be absolute and accessible to the server

        ## Operations
        - **generate**: Create a CloudFormation template at the specified absolute path with the cluster name embedded
        - **deploy**: Deploy a CloudFormation template from the specified absolute path (creates a new stack or updates an existing one)
        - **describe**: Get detailed information about a CloudFormation stack for a specific cluster
        - **delete**: Delete a CloudFormation stack for the specified cluster

        ## Response Information
        The response type varies based on the operation:
        - generate: Returns GenerateTemplateResponse with the template path
        - deploy: Returns DeployStackResponse with stack name, ARN, and cluster name
        - describe: Returns DescribeStackResponse with stack details, outputs, and status
        - delete: Returns DeleteStackResponse with stack name, ID, and cluster name

        ## Usage Tips
        - Use the describe operation first to check if a cluster already exists
        - For safety, this tool will only modify or delete stacks that it created
        - Stack creation typically takes 15-20 minutes to complete
        - Use absolute paths for template files (e.g., '/home/user/templates/eks-template.yaml')
        - The cluster name is used to derive the CloudFormation stack name

        Args:
            ctx: MCP context
            operation: Operation to perform (generate, deploy, describe, or delete)
            template_file: Absolute path for the CloudFormation template (for generate and deploy operations)
            cluster_name: Name of the EKS cluster (for all operations)

        Returns:
            Union[GenerateTemplateResponse, DeployStackResponse, DescribeStackResponse, DeleteStackResponse]:
            Response specific to the operation performed
        """
        try:
            # Check if write access is disabled and trying to perform a mutating operation
            if not self.allow_write and operation not in [
                DESCRIBE_OPERATION,
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                # Return appropriate response type based on operation
                if operation == GENERATE_OPERATION:
                    return GenerateTemplateResponse(
                        isError=True,
                        content=cast(
                            List[Union[TextContent, ImageContent, EmbeddedResource]],
                            [TextContent(type='text', text=error_message)],
                        ),
                        template_path='',
                    )
                elif operation == DEPLOY_OPERATION:
                    return DeployStackResponse(
                        isError=True,
                        content=cast(
                            List[Union[TextContent, ImageContent, EmbeddedResource]],
                            [TextContent(type='text', text=error_message)],
                        ),
                        stack_name='',
                        stack_arn='',
                        cluster_name=cluster_name or '',
                    )
                elif operation == DELETE_OPERATION:
                    return DeleteStackResponse(
                        isError=True,
                        content=cast(
                            List[Union[TextContent, ImageContent, EmbeddedResource]],
                            [TextContent(type='text', text=error_message)],
                        ),
                        stack_name='',
                        stack_id='',
                        cluster_name=cluster_name or '',
                    )
                else:  # Default to describe operation
                    return DescribeStackResponse(
                        isError=True,
                        content=cast(
                            List[Union[TextContent, ImageContent, EmbeddedResource]],
                            [TextContent(type='text', text=error_message)],
                        ),
                        stack_name='',
                        stack_id='',
                        cluster_name=cluster_name or '',
                        creation_time='',
                        stack_status='',
                        outputs={},
                    )

            if operation == GENERATE_OPERATION:
                if template_file is None:
                    raise ValueError('template_file is required for generate operation')
                if cluster_name is None:
                    raise ValueError('cluster_name is required for generate operation')
                return await self._generate_template(
                    ctx=ctx, template_path=template_file, cluster_name=cluster_name
                )

            elif operation == DEPLOY_OPERATION:
                if template_file is None:
                    raise ValueError('template_file is required for deploy operation')
                if cluster_name is None:
                    raise ValueError('cluster_name is required for deploy operation')

                # Derive stack name from cluster name
                stack_name = CFN_STACK_NAME_TEMPLATE.format(cluster_name=cluster_name)
                return await self._deploy_stack(
                    ctx=ctx,
                    template_file=template_file,
                    stack_name=stack_name,
                    cluster_name=cluster_name,
                )

            elif operation == DESCRIBE_OPERATION:
                if cluster_name is None:
                    raise ValueError('cluster_name is required for describe operation')

                # Derive stack name from cluster name
                stack_name = CFN_STACK_NAME_TEMPLATE.format(cluster_name=cluster_name)
                return await self._describe_stack(
                    ctx=ctx, stack_name=stack_name, cluster_name=cluster_name
                )

            elif operation == DELETE_OPERATION:
                if cluster_name is None:
                    raise ValueError('cluster_name is required for delete operation')

                # Derive stack name from cluster name
                stack_name = CFN_STACK_NAME_TEMPLATE.format(cluster_name=cluster_name)
                return await self._delete_stack(
                    ctx=ctx, stack_name=stack_name, cluster_name=cluster_name
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: generate, deploy, describe, delete'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                # Default to DescribeStackResponse for invalid operations
                return DescribeStackResponse(
                    isError=True,
                    content=cast(
                        List[Union[TextContent, ImageContent, EmbeddedResource]],
                        [TextContent(type='text', text=error_message)],
                    ),
                    stack_name='',
                    stack_id='',
                    cluster_name=cluster_name or '',
                    creation_time='',
                    stack_status='',
                    outputs={},
                )
        except ValueError as e:
            # Re-raise ValueError for parameter validation errors
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_eks_stacks: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            # Default to DescribeStackResponse for general exceptions
            return DescribeStackResponse(
                isError=True,
                content=cast(
                    List[Union[TextContent, ImageContent, EmbeddedResource]],
                    [TextContent(type='text', text=error_message)],
                ),
                stack_name='',
                stack_id='',
                cluster_name=cluster_name or '',
                creation_time='',
                stack_status='',
                outputs={},
            )

    async def _generate_template(
        self, ctx: Context, template_path: str, cluster_name: str
    ) -> GenerateTemplateResponse:
        """Generate a CloudFormation template at the specified path with the cluster name embedded.

        The template creates a complete EKS environment including:
        - A dedicated VPC with public and private subnets across two availability zones
        - Internet Gateway and NAT Gateways for outbound connectivity
        - Security groups for cluster communication
        - IAM roles for the EKS cluster and worker nodes
        - An EKS cluster in Auto Mode with:
          - Compute configuration for automatic node management
          - Kubernetes network configuration with elastic load balancing
          - Block storage configuration
          - API authentication mode
        """
        try:
            # Get the source template path
            source_template_path = os.path.join(
                os.path.dirname(__file__), 'templates', 'eks-templates', 'eks-with-vpc.yaml'
            )

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(template_path), exist_ok=True)

            # Read the template
            with open(source_template_path, 'r') as source_file:
                template_content = source_file.read()

            # Parse the template as YAML
            template_yaml = yaml.safe_load(template_content)

            # Modify the template to set the cluster name directly
            # Find the ClusterName parameter and set its default value
            if 'Parameters' in template_yaml and 'ClusterName' in template_yaml['Parameters']:
                template_yaml['Parameters']['ClusterName']['Default'] = cluster_name

            # Remove checkov metadata from the EKS cluster resource
            if 'Resources' in template_yaml and 'EksCluster' in template_yaml['Resources']:
                self._remove_checkov_metadata(template_yaml['Resources']['EksCluster'])

            # Convert back to YAML
            modified_template = yaml.dump(template_yaml, default_flow_style=False)

            # Write the modified template to the destination
            with open(template_path, 'w') as dest_file:
                dest_file.write(modified_template)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Generated CloudFormation template at {template_path} with cluster name {cluster_name}',
            )

            return GenerateTemplateResponse(
                isError=False,
                content=cast(
                    List[Union[TextContent, ImageContent, EmbeddedResource]],
                    [
                        TextContent(
                            type='text',
                            text=f'CloudFormation template generated at {template_path} with cluster name {cluster_name}',
                        )
                    ],
                ),
                template_path=template_path,
            )
        except Exception as e:
            error_message = f'Failed to generate template: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return GenerateTemplateResponse(
                isError=True,
                content=cast(
                    List[Union[TextContent, ImageContent, EmbeddedResource]],
                    [TextContent(type='text', text=error_message or 'Unknown error')],
                ),
                template_path='',
            )

    async def _deploy_stack(
        self, ctx: Context, template_file: str, stack_name: str, cluster_name: str
    ) -> DeployStackResponse:
        """Deploy a CloudFormation stack from the specified template file."""
        try:
            # Create CloudFormation client
            cfn_client = AwsHelper.create_boto3_client('cloudformation')

            # Read the template
            with open(template_file, 'r') as template_file_obj:
                template_body = template_file_obj.read()

            # Check if the stack already exists and verify ownership
            stack_exists = False
            try:
                success, stack, error_message = self._ensure_stack_ownership(
                    ctx, stack_name, 'update'
                )
                if stack:
                    stack_exists = True
                    if not success:
                        return DeployStackResponse(
                            isError=True,
                            content=cast(
                                List[Union[TextContent, ImageContent, EmbeddedResource]],
                                [TextContent(type='text', text=error_message or 'Unknown error')],
                            ),
                            stack_name=stack_name,
                            stack_arn='',
                            cluster_name=cluster_name,
                        )
            except Exception:
                # Stack doesn't exist, we'll create it
                stack_exists = False

            # Create or update the stack
            if stack_exists:
                log_with_request_id(
                    ctx,
                    LogLevel.INFO,
                    f'Updating CloudFormation stack {stack_name} for EKS cluster {cluster_name}',
                )

                response = cfn_client.update_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Capabilities=[CFN_CAPABILITY_IAM],
                    Tags=[{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}],
                )

                operation_text = 'update'
            else:
                log_with_request_id(
                    ctx,
                    LogLevel.INFO,
                    f'Creating CloudFormation stack {stack_name} for EKS cluster {cluster_name}',
                )

                response = cfn_client.create_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Capabilities=[CFN_CAPABILITY_IAM],
                    OnFailure=CFN_ON_FAILURE_DELETE,
                    Tags=[{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}],
                )

                operation_text = 'creation'

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'CloudFormation stack {operation_text} initiated. Stack ARN: {response["StackId"]}',
            )

            return DeployStackResponse(
                isError=False,
                content=cast(
                    List[Union[TextContent, ImageContent, EmbeddedResource]],
                    [
                        TextContent(
                            type='text',
                            text=f'CloudFormation stack {operation_text} initiated. Stack {operation_text} is in progress and typically takes 15-20 minutes to complete.',
                        )
                    ],
                ),
                stack_name=stack_name,
                stack_arn=response['StackId'],
                cluster_name=cluster_name,
            )
        except Exception as e:
            error_message = f'Failed to deploy stack: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return DeployStackResponse(
                isError=True,
                content=cast(
                    List[Union[TextContent, ImageContent, EmbeddedResource]],
                    [TextContent(type='text', text=error_message or 'Unknown error')],
                ),
                stack_name=stack_name,
                stack_arn='',
                cluster_name=cluster_name,
            )

    async def _describe_stack(
        self, ctx: Context, stack_name: str, cluster_name: str
    ) -> DescribeStackResponse:
        """Describe a CloudFormation stack."""
        try:
            # Verify stack ownership
            success, stack, error_message = self._ensure_stack_ownership(
                ctx, stack_name, 'describe'
            )
            if not success:
                # Prepare error response with available stack details
                stack_id = ''
                creation_time = ''
                stack_status = ''

                if stack:
                    stack_id = stack['StackId']
                    creation_time = stack['CreationTime'].isoformat()
                    stack_status = stack['StackStatus']

                return DescribeStackResponse(
                    isError=True,
                    content=cast(
                        List[Union[TextContent, ImageContent, EmbeddedResource]],
                        [TextContent(type='text', text=error_message or 'Unknown error')],
                    ),
                    stack_name=stack_name,
                    stack_id=stack_id,
                    cluster_name=cluster_name,
                    creation_time=creation_time,
                    stack_status=stack_status,
                    outputs={},
                )

            # Extract outputs
            outputs = {}
            if stack and 'Outputs' in stack:
                for output in stack['Outputs']:
                    if 'OutputKey' in output and 'OutputValue' in output:
                        outputs[output['OutputKey']] = output['OutputValue']

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Described CloudFormation stack {stack_name} for EKS cluster {cluster_name}',
            )

            # Safely extract stack details
            stack_id = ''
            creation_time = ''
            stack_status = ''

            if stack:
                stack_id = stack.get('StackId', '')

                # Safely handle creation time
                if 'CreationTime' in stack:
                    creation_time_obj = stack['CreationTime']
                    if hasattr(creation_time_obj, 'isoformat'):
                        creation_time = creation_time_obj.isoformat()
                    else:
                        creation_time = str(creation_time_obj)

                stack_status = stack.get('StackStatus', '')

            return DescribeStackResponse(
                isError=False,
                content=cast(
                    List[Union[TextContent, ImageContent, EmbeddedResource]],
                    [
                        TextContent(
                            type='text',
                            text=f'Successfully described CloudFormation stack {stack_name} for EKS cluster {cluster_name}',
                        )
                    ],
                ),
                stack_name=stack_name,
                stack_id=stack_id,
                cluster_name=cluster_name,
                creation_time=creation_time,
                stack_status=stack_status,
                outputs=outputs,
            )
        except Exception as e:
            error_message = f'Failed to describe stack: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return DescribeStackResponse(
                isError=True,
                content=cast(
                    List[Union[TextContent, ImageContent, EmbeddedResource]],
                    [TextContent(type='text', text=error_message or 'Unknown error')],
                ),
                stack_name=stack_name,
                stack_id='',
                cluster_name=cluster_name,
                creation_time='',
                stack_status='',
                outputs={},
            )

    def _remove_checkov_metadata(self, resource: Dict[str, Any]) -> None:
        """Remove checkov metadata from a resource and clean up empty Metadata sections.

        Args:
            resource: The resource dictionary to process
        """
        if 'Metadata' in resource:
            # Check if there's checkov metadata
            if 'checkov' in resource['Metadata']:
                # Remove only the checkov metadata
                del resource['Metadata']['checkov']

                # If Metadata is now empty, remove it entirely
                if not resource['Metadata']:
                    del resource['Metadata']

    async def _delete_stack(
        self, ctx: Context, stack_name: str, cluster_name: str
    ) -> DeleteStackResponse:
        """Delete a CloudFormation stack."""
        try:
            # Create CloudFormation client
            cfn_client = AwsHelper.create_boto3_client('cloudformation')

            # Verify stack ownership
            success, stack, error_message = self._ensure_stack_ownership(ctx, stack_name, 'delete')
            if not success:
                # Prepare error response with available stack details
                stack_id = ''
                if stack:
                    stack_id = stack['StackId']

                return DeleteStackResponse(
                    isError=True,
                    content=cast(
                        List[Union[TextContent, ImageContent, EmbeddedResource]],
                        [TextContent(type='text', text=error_message or 'Unknown error')],
                    ),
                    stack_name=stack_name,
                    stack_id=stack_id,
                    cluster_name=cluster_name,
                )

            # Safely extract stack ID
            stack_id = ''
            if stack and 'StackId' in stack:
                stack_id = stack['StackId']

            # Delete the stack
            cfn_client.delete_stack(StackName=stack_name)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Initiated deletion of CloudFormation stack {stack_name} for EKS cluster {cluster_name}',
            )

            return DeleteStackResponse(
                isError=False,
                content=cast(
                    List[Union[TextContent, ImageContent, EmbeddedResource]],
                    [
                        TextContent(
                            type='text',
                            text=f'Initiated deletion of CloudFormation stack {stack_name} for EKS cluster {cluster_name}. Deletion is in progress.',
                        )
                    ],
                ),
                stack_name=stack_name,
                stack_id=stack_id,
                cluster_name=cluster_name,
            )
        except Exception as e:
            error_message = f'Failed to delete stack: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return DeleteStackResponse(
                isError=True,
                content=cast(
                    List[Union[TextContent, ImageContent, EmbeddedResource]],
                    [TextContent(type='text', text=error_message or 'Unknown error')],
                ),
                stack_name=stack_name,
                stack_id='',
                cluster_name=cluster_name,
            )
