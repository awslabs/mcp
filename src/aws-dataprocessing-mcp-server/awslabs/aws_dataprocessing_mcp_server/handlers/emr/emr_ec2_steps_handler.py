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

"""EMREc2StepsHandler for Data Processing MCP Server."""

from awslabs.aws_dataprocessing_mcp_server.models.emr_models import (
    AddStepsResponse,
    AddStepsResponseModel,
    CancelStepsResponse,
    CancelStepsResponseModel,
    DescribeStepResponse,
    DescribeStepResponseModel,
    ListStepsResponse,
    ListStepsResponseModel,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional, Union


class EMREc2StepsHandler:
    """Handler for Amazon EMR EC2 Steps operations."""

    def __init__(self, mcp, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the EMR EC2 Steps handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.emr_client = AwsHelper.create_boto3_client('emr')

        # Register tools
        self.mcp.tool(name='manage_aws_emr_ec2_steps')(self.manage_aws_emr_ec2_steps)

    async def manage_aws_emr_ec2_steps(
        self,
        ctx: Context,
        operation: Annotated[
            str,
            Field(
                description='Operation to perform: add-steps, cancel-steps, describe-step, list-steps. Choose read-only operations when write access is disabled.',
            ),
        ],
        cluster_id: Annotated[
            str,
            Field(
                description='ID of the EMR cluster.',
            ),
        ],
        step_id: Annotated[
            Optional[str],
            Field(
                description='ID of the EMR step (required for describe-step).',
            ),
        ] = None,
        step_ids: Annotated[
            Optional[List[str]],
            Field(
                description='List of EMR step IDs (required for cancel-steps, optional for list-steps).',
            ),
        ] = None,
        steps: Annotated[
            Optional[List[Dict[str, Any]]],
            Field(
                description='List of steps to add to the cluster (required for add-steps). Each step should include Name, ActionOnFailure, and HadoopJarStep.',
            ),
        ] = None,
        step_states: Annotated[
            Optional[List[str]],
            Field(
                description='The step state filters to apply when listing steps (optional for list-steps). Valid values: PENDING, CANCEL_PENDING, RUNNING, COMPLETED, CANCELLED, FAILED, INTERRUPTED.',
            ),
        ] = None,
        marker: Annotated[
            Optional[str],
            Field(
                description='The pagination token for list-steps operation.',
            ),
        ] = None,
        step_cancellation_option: Annotated[
            Optional[str],
            Field(
                description='Option for canceling steps. Valid values: SEND_INTERRUPT, TERMINATE_PROCESS. Default is SEND_INTERRUPT.',
            ),
        ] = None,
    ) -> Union[
        AddStepsResponse,
        CancelStepsResponse,
        DescribeStepResponse,
        ListStepsResponse,
    ]:
        """Manage AWS EMR EC2 steps for processing data on EMR clusters.

        This tool provides comprehensive operations for managing EMR steps, which are units of work
        submitted to an EMR cluster for execution. Steps typically consist of Hadoop or Spark jobs
        that process and analyze data.

        ## Requirements
        - The server must be run with the `--allow-write` flag for add-steps and cancel-steps operations
        - Appropriate AWS permissions for EMR step operations

        ## Operations
        - **add-steps**: Add new steps to a running EMR cluster (max 256 steps per job flow)
        - **cancel-steps**: Cancel pending or running steps on an EMR cluster (EMR 4.8.0+ except 5.0.0)
        - **describe-step**: Get detailed information about a specific step's configuration and status
        - **list-steps**: List and filter steps for an EMR cluster with pagination support

        ## Usage Tips
        - Each step consists of a JAR file, its main class, and arguments
        - Steps are executed in the order listed and must exit with zero code to be considered complete
        - For cancel-steps, you can specify SEND_INTERRUPT (default) or TERMINATE_PROCESS as cancellation option
        - When listing steps, filter by step states: PENDING, CANCEL_PENDING, RUNNING, COMPLETED, CANCELLED, FAILED, INTERRUPTED
        - For large result sets, use pagination with marker parameter

        ## Example
        ```
        # Add a Spark step to process data
        {
            'operation': 'add-steps',
            'cluster_id': 'j-2AXXXXXXGAPLF',
            'steps': [
                {
                    'Name': 'Spark Data Processing',
                    'ActionOnFailure': 'CONTINUE',
                    'HadoopJarStep': {
                        'Jar': 'command-runner.jar',
                        'Args': [
                            'spark-submit',
                            '--class',
                            'com.example.SparkProcessor',
                            's3://mybucket/myapp.jar',
                            'arg1',
                            'arg2',
                        ],
                    },
                }
            ],
        }
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            cluster_id: ID of the EMR cluster
            step_id: ID of the EMR step
            step_ids: List of EMR step IDs
            steps: List of steps to add to the cluster
            step_states: The step state filters to apply when listing steps
            marker: The pagination token for list-steps operation
            step_cancellation_option: Option for canceling steps (SEND_INTERRUPT or TERMINATE_PROCESS)

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            if not self.allow_write and operation in [
                'add-steps',
                'cancel-steps',
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                if operation == 'add-steps':
                    model = AddStepsResponseModel(
                        cluster_id=cluster_id,
                        step_ids=[],
                        count=0,
                        operation='add',
                    )
                    return AddStepsResponse.create(
                        is_error=True,
                        content=[TextContent(type='text', text=error_message)],
                        model=model,
                    )
                elif operation == 'cancel-steps':
                    model = CancelStepsResponseModel(
                        cluster_id=cluster_id,
                        step_cancellation_info=[],
                        count=0,
                        operation='cancel',
                    )
                    return CancelStepsResponse.create(
                        is_error=True,
                        content=[TextContent(type='text', text=error_message)],
                        model=model,
                    )

            if operation == 'add-steps':
                if steps is None:
                    raise ValueError('steps is required for add-steps operation')

                actual_steps: List[Dict[str, Any]] = steps

                params = {
                    'JobFlowId': cluster_id,
                    'Steps': actual_steps,
                }

                for step in steps:
                    if 'ExecutionRoleArn' in step:
                        params['ExecutionRoleArn'] = step['ExecutionRoleArn']
                        break

                # Add steps to the cluster
                response = self.emr_client.add_job_flow_steps(**params)

                step_ids_list = response.get('StepIds', [])
                steps_count = len(actual_steps)
                model = AddStepsResponseModel(
                    cluster_id=cluster_id,
                    step_ids=step_ids_list,
                    count=len(step_ids_list),
                    operation='add',
                )
                return AddStepsResponse.create(
                    is_error=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully added {steps_count} steps to EMR cluster {cluster_id}',
                        )
                    ],
                    model=model,
                )

            elif operation == 'cancel-steps':
                if step_ids is None:
                    raise ValueError('step_ids is required for cancel-steps operation')

                for step_id in step_ids:
                    if not isinstance(step_id, str):
                        raise ValueError(f'Invalid step ID: {step_id}. Must be a string.')

                params = {
                    'ClusterId': cluster_id,
                    'StepIds': list(step_ids),
                }

                if step_cancellation_option is not None:
                    if step_cancellation_option in [
                        'SEND_INTERRUPT',
                        'TERMINATE_PROCESS',
                    ]:
                        params['StepCancellationOption'] = step_cancellation_option

                # Cancel steps
                response = self.emr_client.cancel_steps(**params)

                step_cancellation_info = response.get('CancelStepsInfoList', [])
                step_ids_count = len(step_ids) if step_ids is not None else 0
                model = CancelStepsResponseModel(
                    cluster_id=cluster_id,
                    step_cancellation_info=step_cancellation_info,
                    count=len(step_cancellation_info),
                    operation='cancel',
                )
                return CancelStepsResponse.create(
                    is_error=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully initiated cancellation for {step_ids_count} steps on EMR cluster {cluster_id}',
                        )
                    ],
                    model=model,
                )

            elif operation == 'describe-step':
                if step_id is None:
                    raise ValueError('step_id is required for describe-step operation')

                # Describe step
                response = self.emr_client.describe_step(
                    ClusterId=cluster_id,
                    StepId=step_id,
                )

                model = DescribeStepResponseModel(
                    cluster_id=cluster_id,
                    step=response.get('Step', {}),
                    operation='describe',
                )
                return DescribeStepResponse.create(
                    is_error=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully described step {step_id} on EMR cluster {cluster_id}',
                        )
                    ],
                    model=model,
                )

            elif operation == 'list-steps':
                params: Dict[str, Any] = {'ClusterId': cluster_id}

                if marker is not None:
                    params['Marker'] = marker

                if step_states is not None and isinstance(step_states, list):
                    for state in step_states:
                        if not isinstance(state, str):
                            raise ValueError(f'Invalid step state: {state}. Must be a string.')
                    params['StepStates'] = step_states

                if step_ids is not None and isinstance(step_ids, list):
                    for step_id in step_ids:
                        if not isinstance(step_id, str):
                            raise ValueError(f'Invalid step ID: {step_id}. Must be a string.')
                    params['StepIds'] = step_ids

                response = self.emr_client.list_steps(**params)
                steps = response.get('Steps', [])
                model = ListStepsResponseModel(
                    cluster_id=cluster_id,
                    steps=steps or [],
                    count=len(steps or []),
                    marker=response.get('Marker'),
                    operation='list',
                )
                return ListStepsResponse.create(
                    is_error=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully listed steps for EMR cluster {cluster_id}',
                        )
                    ],
                    model=model,
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: add-steps, cancel-steps, describe-step, list-steps'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                model = DescribeStepResponseModel(
                    cluster_id=cluster_id,
                    step={},
                    operation='describe',
                )
                return DescribeStepResponse.create(
                    is_error=True,
                    content=[TextContent(type='text', text=error_message)],
                    model=model,
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_emr_ec2_steps: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            model = DescribeStepResponseModel(
                cluster_id=cluster_id,
                step={},
                operation='describe',
            )
            return DescribeStepResponse.create(
                is_error=True,
                content=[TextContent(type='text', text=error_message)],
                model=model,
            )
