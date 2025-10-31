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

"""HyperPod stack handler for the HyperPod MCP Server."""

import json
import yaml  # type: ignore
from awslabs.sagemaker_hyperpod_mcp_server.aws_helper import AwsHelper
from awslabs.sagemaker_hyperpod_mcp_server.consts import (
    CAPABILITY_AUTO_EXPAND,
    CFN_CAPABILITY_IAM,
    CFN_CAPABILITY_NAMED_IAM,
    CFN_ON_FAILURE_DELETE,
    CFN_STACK_TAG_KEY,
    CFN_STACK_TAG_VALUE,
    CLUSTER_ORCHESTRATORS,
    HYPERPOD_CFN_TEMPLATE_URL_EKS,
    HYPERPOD_CFN_TEMPLATE_URL_SLURM,
    STACK_DELETE_OPERATION,
    STACK_DEPLOY_OPERATION,
    STACK_DESCRIBE_OPERATION,
    STACK_NOT_OWNED_ERROR_TEMPLATE,
    STACK_OPERATIONS,
    SUPPORTED_REGIONS,
)
from awslabs.sagemaker_hyperpod_mcp_server.logging_helper import LogLevel, log_with_request_id
from awslabs.sagemaker_hyperpod_mcp_server.models import (
    DeleteStackResponse,
    DeployStackResponse,
    DescribeStackResponse,
)
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field, validate_call
from typing import Dict, List, Optional, Tuple, Union
from yaml.loader import SafeLoader  # type: ignore


# Custom YAML loader for CloudFormation templates
class CloudFormationLoader(SafeLoader):
    """Custom YAML loader that handles CloudFormation intrinsic functions."""

    pass


# Add constructors for CloudFormation intrinsic functions
def construct_cfn_tag(loader, tag_suffix, node):
    """Generic constructor for CloudFormation intrinsic functions."""
    if isinstance(node, yaml.ScalarNode):
        return {tag_suffix: loader.construct_scalar(node)}
    elif isinstance(node, yaml.SequenceNode):
        return {tag_suffix: loader.construct_sequence(node)}
    elif isinstance(node, yaml.MappingNode):
        return {tag_suffix: loader.construct_mapping(node)}
    else:
        return None


# Register constructors for common CloudFormation intrinsic functions
for tag in [
    'Ref',
    'Condition',
    'GetAtt',
    'Equals',
    'If',
    'Not',
    'And',
    'Or',
    'FindInMap',
    'Base64',
    'Join',
    'Sub',
    'Select',
    'Split',
    'ImportValue',
    'GetAZs',
    'Transform',
    'ForEach',
]:
    CloudFormationLoader.add_constructor(
        f'!{tag}', lambda loader, node, tag=tag: construct_cfn_tag(loader, tag, node)
    )


class HyperPodStackHandler:
    """Handler for Amazon HyperPod CloudFormation stack operations.

    This class provides tools for creating, managing, and deleting CloudFormation
    stacks for HyperPod clusters.
    """

    def __init__(self, mcp, allow_write: bool = False):
        """Initialize the HyperPod stack handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write

        # Register tools
        self.mcp.tool(name='manage_hyperpod_stacks')(self.manage_hyperpod_stacks)

    @validate_call
    def _ensure_stack_ownership(
        self,
        ctx: Context,
        stack_name: str,
        region_name: SUPPORTED_REGIONS,
        operation: str,
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Ensure that a stack exists and was created by this tool.

        Args:
            ctx: The MCP context
            stack_name: Name of the stack to verify
            region_name: region to perform the API call in
            operation: Operation being performed (for error messages)

        Returns:
            Tuple of (success, stack_details, error_message)
            - success: True if the stack exists and was created by this tool
            - stack_details: Stack details if the stack exists, None otherwise
            - error_message: Error message if the stack doesn't exist or wasn't created by this tool, None if successful
        """
        try:
            # Create CloudFormation client
            cfn_client = AwsHelper.create_boto3_client('cloudformation', region_name)

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

    @validate_call
    async def manage_hyperpod_stacks(
        self,
        ctx: Context,
        operation: STACK_OPERATIONS = Field(
            description='Operation to perform: deploy, describe, or delete. Choose "describe" for read-only operations when write access is disabled.',
        ),
        region_name: SUPPORTED_REGIONS = Field(
            description='AWS region name. Default is us-east-1.',
        ),
        stack_name: str = Field(
            description='Name of the CloudFormation stack (for deploy, describe and delete operations).',
        ),
        cluster_orchestrator: CLUSTER_ORCHESTRATORS = Field(
            'eks',
            description='Cluster orchestrator type. Must be either "eks" or "slurm". Default is "eks".',
        ),
        params_file: Optional[str] = Field(
            None,
            description="""Absolute path for the CloudFormation template parameters(for deploy operations).
            IMPORTANT: Assistant must provide the full absolute path to the template file, as the MCP client and server might not run from the same location.""",
        ),
        profile_name: Optional[str] = Field(
            None,
            description='AWS profile name. If not provided, uses the default profile.',
        ),
    ) -> Union[
        'DeployStackResponse',
        'DescribeStackResponse',
        'DeleteStackResponse',
    ]:
        r"""Manage SageMaker HyperPod Cluster through CloudFormation stacks.

        This tool provides operations for managing HyperPod CloudFormation stacks, including creating parameters for cloudformation template,
        deploying stacks, retrieving hyperpod stack and deployment information, and deleting hyperpod stacks. It serves as the primary
        mechanism for creating and managing HyperPod clusters through CloudFormation, enabling standardized
        cluster creation, configuration updates, and resource cleanup.

        ## Notes
        - Tell user about the working directory which is the current directory. The tool will use directory to store all required files for the user.
        - After you asked a question, do NOT do anything until you got the user response, do NOT run manage_hyperpod_stacks yet
        - Use this tool instead of direct AWS CLI commands for creating and managing HyperPod resources.
        - Use this tool's standardized parameters for creating HyperPod clusters with proper configuration.
        - DO NOT create HyperPod clusters by generating CloudFormation templates from scratch.
        - when user asks to create a hyperpod cluster, NEVER ask to check what HyperPod clusters the user currently have
        - CRITICAL: when user asks to delete a hyperpod cluster, NEVER ask how user's hyperpod cluster was created, just proceed with 'delete' operation. The corresponding Cloudformation stack name should be in this format: "<HyperPodClusterName>-stack". If no such stack exists, then the hyperpod cluster might not be created via the MCP tools here.

        ## Parameter Collection Process
            IMPORTANT: ALWAYS first ask for ALL operation-specific REQUIRED parameters from the user BEFORE making any tool calls. NEVER assume or generate parameter values.
            IMPORTANT: ALWAYS ask one question at a time.

            For 'deploy' operation:
                - region_name: REQUIRED: ask user to region of deployment. Limit user input to the major US region. Ensure this argument matches the AvailabilityZoneIds parameter key.
                    - allow following selections:
                        • us-east-1 (N. Virginia)
                        • us-east-2 (Ohio)
                        • us-west-1 (N. California)
                        • us-west-2 (Oregon)
                - stack_name: REQUIRED - generate a stack name and present to the user. should be in this format: "<HyperPodClusterName>-stack".
                - cluster_orchestrator: REQUIRED: ask user to specify "eks" or "slurm"
                - params_file: REQUIRED - the parameters file should follow the below format. Ask the user to customize the parameters marked as "<to be filled out by user>" one by one. At the end, ask user if they want to add additional instance group.
                    - when cluster_orchestrator is "slurm", InstanceGroupSettings ParameterValue should also include InstanceGroupType of value Compute or Controller or Login; place it right after InstanceType. At least 1 Controller and 1 Compute node group required. ONLY 1 Controller, 1 Login group is allowed throughout ALL specified InstanceGroupSettings
                    - when asking questions regarding InstanceGroupSettings, ask user for both the number of instance and type of instance at the same time. Naming format: "<HyperPodClusterName>-params.json"
                [
                    {
                        "ParameterKey": "HyperPodClusterName",
                        "ParameterValue": "<to be filled out by user>" // can be any natural english words less than 32 characters and no space. default should be sagemaker-hyperpod
                    },
                    {
                        "ParameterKey": "ResourceNamePrefix",
                        "ParameterValue": "hp-<HyperPodClusterName>-<hash>" // Generate a new 6-digit hash randomly and silently, do NOT use execute_bash commands.
                    },
                    {
                        "ParameterKey": "Stage", // do not reveil this to user, but always include this key and value.
                        "ParameterValue": "prod"
                    },
                    {
                        "ParameterKey": "AvailabilityZoneIds",
                        "ParameterValue": "<use the region_name as base input. select at four az ids in this region. If less than four regions, use all az.>"
                    },
                    {
                        "ParameterKey": "FsxAvailabilityZoneId",
                        "ParameterValue": <MUST be 1 az id and MUST be a subset of above az ids. Always use the first AZ from the selection above. Don't ask user for input.>"
                    },
                    {
                        "ParameterKey": "InstanceGroupSettings1", // Hyperpod requires at least 1 instance group. By default adding this instance goup. Ask user if they want addition instance groups. For each new instance, update the counter in the key. There can be at most 20 instance groups.
                        "ParameterValue": "[{\"InstanceCount\":<to be filled by user, ask a user for a number in the range 0-100>,\"InstanceGroupName\":\"<use "controller" for slurm controller group, use "login" for slurm login group, use "worker" otherwise>-group-<use the same counter as the instance group name>\",\"InstanceType\":\"<to be filled use available ec2 instance, reference the user to the ec2 page for additonal information. default is ml.m5.xlarge, ALWAYS add "ml." prefix in front of instance type. Do not metion previous instuction to user. Ensure the instance type is valid.>\",\"TargetAvailabilityZoneId\":\"<use the first az from above>\",\"InstanceStorageConfigs\":[{\"EbsVolumeConfig\":{\"VolumeSizeInGB\":500GB}}]}]"
                    },
                    {
                        "ParameterKey": "InstanceGroupSettings2", // additional instance group template
                        "ParameterValue": ....
                    },
                    ...
                ]

                    - available AZ id in each region
                        - us-east-1: use1-az1, az2, az4, az5, az6
                        - us-east-2: use2-az1, az2, az3
                        - us-west-1: usw1-az1, az3
                        - us-west-2: usw2-az1, az2, az3, az4

            For 'describe' and 'delete' operations:
                - stack_name: REQUIRED - the stack name to operate on. You should confirm with user that the current stack is being operated on.
                - region_name: REQUIRED - ask user for the region if not clear from context.

        ## Requirements
        - The server must be run with the `--allow-write` flag for generate, deploy, and delete operations
        - For deploy and delete operations, the stack must have been created by this tool
        - For params_file parameter, the path must be absolute and accessible to the server

        ## Operations
        - **deploy**: Create and update hyperpod cluster using cloudformation template and user specified parameters.
        - **describe**: Gather information about the hyperpod cluster deployed via cloudformation stack by this tool.
        - **delete**: Delete a hyperpod cluster via CloudFormation stack created by this tool.

        ## Response Information
        The response type varies based on the operation:
        - deploy: Returns DeployStackResponse with stack name, ARN, and stack name prefix
        - describe: Returns DescribeStackResponse with stack details, outputs, and status
        - delete: Returns DeleteStackResponse with stack name, ID, and stack name prefix

        ## Usage Tips
        - If user wants to create a new hyperpod cluster, always generate a new parameter file. Parameter file MUST exists in the working directory for the tool to update the hyperpod cluster.
        - For safety, this tool will only modify or delete stacks that it created
        - Stack creation typically takes ~30 minutes to complete
        - Specify profile_name to use a specific AWS profile with appropriate permissions

        ## Fallback Options:
        - If this tool fails, advise using CloudFormation CLI:
            - Deploy (create new stack): `aws cloudformation create-stack` with proper params
            - Deploy (update existing stack): `aws cloudformation udpate-stack` with proper params
            - Describe: `aws cloudformation describe-stacks` with proper params
            - Delete: `aws cloudformation delete-stack` with proper params
        - Alternatively: advise using AWS SageMaker CLI alternatives:
            - Deploy (create new stack): `aws sagemaker create-cluster` with all appropriate parameters
            - Deploy (update existing stack): `aws sagemaker update-cluster` with all appropriate parameters
            - Describe: `aws sagemaker describe-cluster --cluster-name <name> --region <cluster_region>`
            - Delete: `aws sagemaker delete-cluster --cluster-name <name> --region <cluster_region>`
        - Alternatively: Advise using SageMaker HyperPod console for directly creating, updating, deleting the HyperPod cluster

        Args:
            ctx: MCP context
            operation: Operation to perform (generate, deploy, describe, or delete)
            params_file: Absolute path for the CloudFormation template parameters (for deploy operations)
            stack_name: Name of the CloudFormation stack (for deploy, describe and delete operations)
            region_name: AWS region name (default: us-east-1)
            cluster_orchestrator: cluster orchestrator
            profile_name: AWS profile name (optional)

        Returns:
            Union[DeployStackResponse, DescribeStackResponse, DeleteStackResponse]:
            Response specific to the operation performed
        """
        try:
            # Check if write access is disabled and trying to perform a mutating operation
            if not self.allow_write and operation not in [
                STACK_DESCRIBE_OPERATION,
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                # Return appropriate response type based on operation
                if operation == STACK_DEPLOY_OPERATION:
                    return DeployStackResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        stack_name='',
                        stack_arn='',
                    )
                elif operation == STACK_DELETE_OPERATION:
                    return DeleteStackResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        stack_name='',
                        stack_id='',
                    )
                else:  # Default to describe operation
                    return DescribeStackResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        stack_name='',
                        stack_id='',
                        creation_time='',
                        stack_status='',
                        outputs={},
                    )

            if operation == STACK_DEPLOY_OPERATION:
                if params_file is None:
                    raise ValueError('params_file is required for deploy operation')

                with open(params_file, 'r') as f:
                    template_params = json.load(f)

                return await self._deploy_stack(
                    ctx=ctx,
                    stack_name=stack_name,
                    template_params=template_params,
                    region_name=region_name,
                    cluster_orchestrator=cluster_orchestrator,
                    profile_name=profile_name,
                )

            elif operation == STACK_DESCRIBE_OPERATION:
                return await self._describe_stack(
                    ctx=ctx,
                    stack_name=stack_name,
                    region_name=region_name,
                    profile_name=profile_name,
                )

            elif operation == STACK_DELETE_OPERATION:
                return await self._delete_stack(
                    ctx=ctx,
                    stack_name=stack_name,
                    region_name=region_name,
                    profile_name=profile_name,
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: generate, deploy, describe, delete'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                # Default to DescribeStackResponse for invalid operations
                return DescribeStackResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    stack_name='',
                    stack_id='',
                    creation_time='',
                    stack_status='',
                    outputs={},
                )
        except ValueError as e:
            # Re-raise ValueError for parameter validation errors
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_hyperpod_stacks: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            # Default to DescribeStackResponse for general exceptions
            return DescribeStackResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                stack_name='',
                stack_id='',
                creation_time='',
                stack_status='',
                outputs={},
            )

    async def _deploy_stack(
        self,
        ctx: Context,
        template_params: List[dict],
        stack_name: str,
        region_name: SUPPORTED_REGIONS,
        cluster_orchestrator: CLUSTER_ORCHESTRATORS,
        profile_name: Optional[str] = None,
    ) -> 'DeployStackResponse':
        """Deploy a CloudFormation stack from the specified template file."""
        try:
            # Determine template URL based on cluster orchestrator
            if cluster_orchestrator == 'eks':
                template_url = HYPERPOD_CFN_TEMPLATE_URL_EKS
            elif cluster_orchestrator == 'slurm':
                template_url = HYPERPOD_CFN_TEMPLATE_URL_SLURM
            else:
                # This should not happen due to type validation, but adding for safety
                error_message = f'Invalid cluster_orchestrator: {cluster_orchestrator}. Must be either "eks" or "slurm".'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return DeployStackResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message or 'Unknown error')],
                    stack_name=stack_name,
                    stack_arn='',
                )
            # Create CloudFormation client
            cfn_client = AwsHelper.create_boto3_client('cloudformation', region_name=region_name)

            # Check if the stack already exists and verify ownership
            stack_exists = False
            try:
                success, stack, error_message = self._ensure_stack_ownership(
                    ctx, stack_name, region_name, 'describe'
                )
                if stack:
                    stack_exists = True
                    if not success:
                        return DeployStackResponse(
                            isError=True,
                            content=[
                                TextContent(type='text', text=error_message or 'Unknown error')
                            ],
                            stack_name=stack_name,
                            stack_arn='',
                        )
            except Exception:
                # Stack doesn't exist, we'll create it
                stack_exists = False

            if stack_exists:
                log_with_request_id(
                    ctx,
                    LogLevel.INFO,
                    f'Updating CloudFormation stack {stack_name} for HyperPod Cluster',
                )

                response = cfn_client.update_stack(
                    StackName=stack_name,
                    TemplateURL=template_url,
                    Parameters=template_params,
                    Capabilities=[
                        CFN_CAPABILITY_IAM,
                        CFN_CAPABILITY_NAMED_IAM,
                        CAPABILITY_AUTO_EXPAND,
                    ],
                    Tags=[{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}],
                )

                operation_text = 'update'
            else:
                log_with_request_id(
                    ctx,
                    LogLevel.INFO,
                    f'Creating CloudFormation stack {stack_name} for HyperPod cluster',
                )

                response = cfn_client.create_stack(
                    StackName=stack_name,
                    TemplateURL=template_url,
                    Parameters=template_params,
                    Capabilities=[
                        CFN_CAPABILITY_IAM,
                        CFN_CAPABILITY_NAMED_IAM,
                        CAPABILITY_AUTO_EXPAND,
                    ],
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
                content=[
                    TextContent(
                        type='text',
                        text=f'CloudFormation stack {operation_text} initiated. Stack {operation_text} is in progress and typically takes ~30 minutes to complete.',
                    )
                ],
                stack_name=stack_name,
                stack_arn=response['StackId'],
            )
        except Exception as e:
            error_message = f'Failed to deploy stack: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return DeployStackResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message or 'Unknown error')],
                stack_name=stack_name,
                stack_arn='',
            )

    async def _describe_stack(
        self,
        ctx: Context,
        stack_name: str,
        region_name: SUPPORTED_REGIONS,
        profile_name: Optional[str] = None,
    ) -> 'DescribeStackResponse':
        """Describe a CloudFormation stack."""
        try:
            # Verify stack ownership
            success, stack, error_message = self._ensure_stack_ownership(
                ctx, stack_name, region_name, 'describe'
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
                    content=[TextContent(type='text', text=error_message or 'Unknown error')],
                    stack_name=stack_name,
                    stack_id=stack_id,
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
                f'Described CloudFormation stack {stack_name} for HyperPod cluster',
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
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully described CloudFormation stack {stack_name} for HyperPod stack',
                    )
                ],
                stack_name=stack_name,
                stack_id=stack_id,
                creation_time=creation_time,
                stack_status=stack_status,
                outputs=outputs,
            )
        except Exception as e:
            error_message = f'Failed to describe stack: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return DescribeStackResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message or 'Unknown error')],
                stack_name=stack_name,
                stack_id='',
                creation_time='',
                stack_status='',
                outputs={},
            )

    async def _delete_stack(
        self,
        ctx: Context,
        stack_name: str,
        region_name: SUPPORTED_REGIONS,
        profile_name: Optional[str] = None,
    ) -> 'DeleteStackResponse':
        """Delete a CloudFormation stack."""
        try:
            # Create CloudFormation client
            cfn_client = AwsHelper.create_boto3_client('cloudformation', region_name)

            # Verify stack ownership
            success, stack, error_message = self._ensure_stack_ownership(
                ctx, stack_name, region_name, 'delete'
            )
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'_ensure_stack_ownership {stack_name} {stack} {error_message}',
            )
            if not success:
                # Prepare error response with available stack details
                stack_id = ''
                if stack:
                    stack_id = stack['StackId']

                return DeleteStackResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message or 'Unknown error')],
                    stack_name=stack_name,
                    stack_id=stack_id,
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
                f'Initiated deletion of CloudFormation stack {stack_name} for HyperPod stack',
            )

            return DeleteStackResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Initiated deletion of CloudFormation stack {stack_name} for HyperPod stack. Deletion is in progress.',
                    )
                ],
                stack_name=stack_name,
                stack_id=stack_id,
            )
        except Exception as e:
            error_message = f'Failed to delete stack: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return DeleteStackResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message or 'Unknown error')],
                stack_name=stack_name,
                stack_id='',
            )
