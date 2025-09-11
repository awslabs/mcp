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

"""AWS Systems Manager Automation MCP tools."""

import boto3
import json
from awslabs.systems_manager_mcp_server.context import Context
from awslabs.systems_manager_mcp_server.errors import log_error
from botocore.exceptions import ClientError
from mcp.types import CallToolResult
from pydantic import Field
from typing import Optional


def register_tools(mcp):
    """Register all automation tools with the provided MCP instance."""

    def _get_ssm_client(region=None, profile=None):
        """Get SSM client with optional region and profile."""
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        return session.client('ssm', region_name=region)

    @mcp.tool()
    def start_automation_execution(
        document_name: str = Field(description='The name of the SSM document to run'),
        document_version: Optional[str] = Field(
            None, description='The version of the automation document to use'
        ),
        parameters: Optional[str] = Field(
            None, description='JSON string of execution parameters (key-value pairs)'
        ),
        mode: Optional[str] = Field('Auto', description='The execution mode (Auto, Interactive)'),
        targets: Optional[str] = Field(
            None, description='JSON string of target resources for rate-controlled execution'
        ),
        target_maps: Optional[str] = Field(
            None, description='JSON string of document parameters to target resources mapping'
        ),
        target_parameter_name: Optional[str] = Field(
            None, description='The name of the parameter used as the target resource'
        ),
        target_locations: Optional[str] = Field(
            None, description='JSON string of AWS Regions and accounts combinations'
        ),
        max_concurrency: Optional[str] = Field(
            None, description='Maximum number of targets to run in parallel'
        ),
        max_errors: Optional[str] = Field(
            None, description='Maximum number of errors allowed before stopping'
        ),
        alarm_configuration: Optional[str] = Field(
            None, description='JSON string of CloudWatch alarm configuration'
        ),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """Start an automation execution to run CloudOps workflows."""
        if Context.is_readonly():
            return CallToolResult(
                content=[
                    {
                        'type': 'text',
                        'text': 'Cannot start automation execution: Server is in read-only mode',
                    }
                ],
                isError=True,
            )

        try:
            # Parse JSON parameters if provided
            parsed_parameters = None
            if parameters:
                try:
                    parsed_parameters = json.loads(parameters)
                except json.JSONDecodeError as e:
                    return CallToolResult(
                        content=[
                            {'type': 'text', 'text': f'Invalid JSON in parameters: {str(e)}'}
                        ],
                        isError=True,
                    )

            # Parse JSON targets if provided
            parsed_targets = None
            if targets:
                try:
                    parsed_targets = json.loads(targets)
                except json.JSONDecodeError as e:
                    return CallToolResult(
                        content=[{'type': 'text', 'text': f'Invalid JSON in targets: {str(e)}'}],
                        isError=True,
                    )

            # Parse JSON target_maps if provided
            parsed_target_maps = None
            if target_maps:
                try:
                    parsed_target_maps = json.loads(target_maps)
                except json.JSONDecodeError as e:
                    return CallToolResult(
                        content=[
                            {'type': 'text', 'text': f'Invalid JSON in target_maps: {str(e)}'}
                        ],
                        isError=True,
                    )

            # Parse JSON target_locations if provided
            parsed_target_locations = None
            if target_locations:
                try:
                    parsed_target_locations = json.loads(target_locations)
                except json.JSONDecodeError as e:
                    return CallToolResult(
                        content=[
                            {'type': 'text', 'text': f'Invalid JSON in target_locations: {str(e)}'}
                        ],
                        isError=True,
                    )

            # Parse JSON alarm_configuration if provided
            parsed_alarm_configuration = None
            if alarm_configuration:
                try:
                    parsed_alarm_configuration = json.loads(alarm_configuration)
                except json.JSONDecodeError as e:
                    return CallToolResult(
                        content=[
                            {
                                'type': 'text',
                                'text': f'Invalid JSON in alarm_configuration: {str(e)}',
                            }
                        ],
                        isError=True,
                    )

            # Build request parameters
            request_params = {'DocumentName': document_name}

            if document_version:
                request_params['DocumentVersion'] = document_version
            if parsed_parameters:
                request_params['Parameters'] = parsed_parameters
            if mode:
                request_params['Mode'] = mode
            if parsed_targets:
                request_params['Targets'] = parsed_targets
            if parsed_target_maps:
                request_params['TargetMaps'] = parsed_target_maps
            if target_parameter_name:
                request_params['TargetParameterName'] = target_parameter_name
            if parsed_target_locations:
                request_params['TargetLocations'] = parsed_target_locations
            if max_concurrency:
                request_params['MaxConcurrency'] = max_concurrency
            if max_errors:
                request_params['MaxErrors'] = max_errors
            if parsed_alarm_configuration:
                request_params['AlarmConfiguration'] = parsed_alarm_configuration

            # Call AWS API
            ssm_client = _get_ssm_client(region, profile)
            response = ssm_client.start_automation_execution(**request_params)

            return CallToolResult(
                content=[
                    {
                        'type': 'text',
                        'text': f'✅ Automation execution started successfully\n\nAutomation Execution ID: {response["AutomationExecutionId"]}',
                    }
                ]
            )

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'start automation execution')

    @mcp.tool()
    def get_automation_execution(
        automation_execution_id: str = Field(
            description='The unique identifier for the automation execution'
        ),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """Get details of an automation execution."""
        try:
            ssm_client = _get_ssm_client(region, profile)
            response = ssm_client.get_automation_execution(
                AutomationExecutionId=automation_execution_id
            )

            execution = response['AutomationExecution']

            # Format the execution details
            output = '✅ Automation execution retrieved successfully\n\n'
            output += '**Automation Execution Details:**\n'
            output += f'- Execution ID: {execution["AutomationExecutionId"]}\n'
            output += f'- Document Name: {execution["DocumentName"]}\n'
            output += f'- Document Version: {execution.get("DocumentVersion", "N/A")}\n'
            output += f'- Status: {execution["AutomationExecutionStatus"]}\n'
            output += f'- Start Time: {execution.get("ExecutionStartTime", "N/A")}\n'
            output += f'- End Time: {execution.get("ExecutionEndTime", "N/A")}\n'

            if execution.get('FailureMessage'):
                output += f'- Failure Message: {execution["FailureMessage"]}\n'

            if execution.get('StepExecutions'):
                output += f'\n**Step Executions ({len(execution["StepExecutions"])}):**\n'
                for i, step in enumerate(execution['StepExecutions'][:5]):  # Show first 5 steps
                    output += f'  {i + 1}. {step["StepName"]}: {step["StepStatus"]}\n'
                if len(execution['StepExecutions']) > 5:
                    output += f'  ... and {len(execution["StepExecutions"]) - 5} more steps\n'

            return CallToolResult(content=[{'type': 'text', 'text': output}])

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'get automation execution')

    @mcp.tool()
    def stop_automation_execution(
        automation_execution_id: str = Field(
            description='The execution ID of the automation to stop'
        ),
        stop_type: Optional[str] = Field(
            'Complete', description='The stop type (Complete, Cancel)'
        ),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """Stop a running automation execution."""
        if Context.is_readonly():
            return CallToolResult(
                content=[
                    {
                        'type': 'text',
                        'text': 'Cannot stop automation execution: Server is in read-only mode',
                    }
                ],
                isError=True,
            )

        try:
            ssm_client = _get_ssm_client(region, profile)
            ssm_client.stop_automation_execution(
                AutomationExecutionId=automation_execution_id, Type=stop_type
            )

            return CallToolResult(
                content=[{'type': 'text', 'text': '✅ Automation execution stopped successfully'}]
            )

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'stop automation execution')

    @mcp.tool()
    def describe_automation_executions(
        filters: Optional[str] = Field(
            None, description='JSON string of filters to limit results'
        ),
        max_results: Optional[int] = Field(50, description='Maximum number of results to return'),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """List automation executions with optional filtering."""
        try:
            # Parse JSON filters if provided
            parsed_filters = None
            if filters:
                try:
                    parsed_filters = json.loads(filters)
                except json.JSONDecodeError as e:
                    return CallToolResult(
                        content=[{'type': 'text', 'text': f'Invalid JSON in filters: {str(e)}'}],
                        isError=True,
                    )

            # Build request parameters
            request_params = {}
            if parsed_filters:
                request_params['Filters'] = parsed_filters
            if max_results:
                request_params['MaxResults'] = max_results

            ssm_client = _get_ssm_client(region, profile)
            response = ssm_client.describe_automation_executions(**request_params)

            executions = response['AutomationExecutionMetadataList']

            if not executions:
                return CallToolResult(
                    content=[
                        {
                            'type': 'text',
                            'text': 'No automation executions found matching the criteria.',
                        }
                    ]
                )

            output = '✅ Automation executions retrieved successfully\n\n'
            output += '**Automation Executions:**\n'

            for execution in executions:
                output += f'- **{execution["AutomationExecutionId"]}**\n'
                output += f'  - Document: {execution["DocumentName"]}\n'
                output += f'  - Status: {execution["AutomationExecutionStatus"]}\n'
                output += f'  - Start Time: {execution.get("ExecutionStartTime", "N/A")}\n'
                if execution.get('FailureMessage'):
                    output += f'  - Failure: {execution["FailureMessage"]}\n'
                output += '\n'

            return CallToolResult(content=[{'type': 'text', 'text': output}])

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'describe automation executions')

    @mcp.tool()
    def send_automation_signal(
        automation_execution_id: str = Field(
            description='The unique identifier for the automation execution'
        ),
        signal_type: str = Field(
            description='The type of signal (Approve, Reject, StartStep, StopStep, Resume)'
        ),
        payload: Optional[str] = Field(
            None, description='JSON string of data sent with the signal'
        ),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """Send a signal to an automation execution (for interactive automations)."""
        if Context.is_readonly():
            return CallToolResult(
                content=[
                    {
                        'type': 'text',
                        'text': 'Cannot send automation signal: Server is in read-only mode',
                    }
                ],
                isError=True,
            )

        try:
            # Parse JSON payload if provided
            parsed_payload = None
            if payload:
                try:
                    parsed_payload = json.loads(payload)
                except json.JSONDecodeError as e:
                    return CallToolResult(
                        content=[{'type': 'text', 'text': f'Invalid JSON in payload: {str(e)}'}],
                        isError=True,
                    )

            # Build request parameters
            request_params = {
                'AutomationExecutionId': automation_execution_id,
                'SignalType': signal_type,
            }
            if parsed_payload:
                request_params['Payload'] = parsed_payload

            ssm_client = _get_ssm_client(region, profile)
            ssm_client.send_automation_signal(**request_params)

            return CallToolResult(
                content=[{'type': 'text', 'text': '✅ Automation signal sent successfully'}]
            )

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'send automation signal')
