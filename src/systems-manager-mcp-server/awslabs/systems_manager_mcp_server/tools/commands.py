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

"""AWS Systems Manager Commands MCP tools."""

import boto3
import json
from awslabs.systems_manager_mcp_server.context import Context
from awslabs.systems_manager_mcp_server.errors import log_error
from botocore.exceptions import ClientError
from mcp.types import CallToolResult
from pydantic import Field
from typing import Optional


def register_tools(mcp):
    """Register all command tools with the provided MCP instance."""

    def _get_ssm_client(region=None, profile=None):
        """Get SSM client with optional region and profile."""
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        return session.client('ssm', region_name=region)

    @mcp.tool()
    def send_command(
        document_name: str = Field(description='The name of the Systems Manager document to run'),
        instance_ids: Optional[str] = Field(
            None, description='Comma-separated list of instance IDs where the command should run'
        ),
        targets: Optional[str] = Field(
            None,
            description='JSON string of search criteria that targets instances using key-value pairs',
        ),
        document_version: Optional[str] = Field(
            None, description='The SSM document version to use'
        ),
        parameters: Optional[str] = Field(
            None, description='JSON string of required and optional parameters for the document'
        ),
        timeout_seconds: Optional[int] = Field(
            None, description='Timeout in seconds for the command execution'
        ),
        comment: Optional[str] = Field(
            None, description='User-specified information about the command'
        ),
        max_concurrency: Optional[str] = Field(
            None, description='Maximum number of instances to run the command simultaneously'
        ),
        max_errors: Optional[str] = Field(
            None, description='Maximum number of errors allowed without the command failing'
        ),
        output_s3_region: Optional[str] = Field(
            None, description='AWS region where the S3 bucket is located for command output'
        ),
        output_s3_bucket_name: Optional[str] = Field(
            None, description='S3 bucket name for storing command output'
        ),
        output_s3_key_prefix: Optional[str] = Field(
            None, description='S3 key prefix for organizing command output files'
        ),
        service_role_arn: Optional[str] = Field(
            None, description='IAM service role ARN for the command execution'
        ),
        notification_config: Optional[str] = Field(
            None, description='JSON string of notification configuration for command status'
        ),
        cloudwatch_output_config: Optional[str] = Field(
            None, description='JSON string of CloudWatch Logs configuration for command output'
        ),
        alarm_configuration: Optional[str] = Field(
            None,
            description='JSON string of CloudWatch alarm configuration to stop command execution',
        ),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """Send a command to EC2 instances or on-premises servers."""
        if Context.is_readonly():
            return CallToolResult(
                content=[
                    {'type': 'text', 'text': 'Cannot send command: Server is in read-only mode'}
                ],
                isError=True,
            )

        try:
            # Parse instance IDs if provided
            parsed_instance_ids = None
            if instance_ids:
                parsed_instance_ids = [id.strip() for id in instance_ids.split(',')]

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

            # Parse JSON notification config if provided
            parsed_notification_config = None
            if notification_config:
                try:
                    parsed_notification_config = json.loads(notification_config)
                except json.JSONDecodeError as e:
                    return CallToolResult(
                        content=[
                            {
                                'type': 'text',
                                'text': f'Invalid JSON in notification_config: {str(e)}',
                            }
                        ],
                        isError=True,
                    )

            # Parse JSON CloudWatch output config if provided
            parsed_cloudwatch_output_config = None
            if cloudwatch_output_config:
                try:
                    parsed_cloudwatch_output_config = json.loads(cloudwatch_output_config)
                except json.JSONDecodeError as e:
                    return CallToolResult(
                        content=[
                            {
                                'type': 'text',
                                'text': f'Invalid JSON in cloudwatch_output_config: {str(e)}',
                            }
                        ],
                        isError=True,
                    )

            # Parse JSON alarm configuration if provided
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

            if parsed_instance_ids:
                request_params['InstanceIds'] = parsed_instance_ids
            if parsed_targets:
                request_params['Targets'] = parsed_targets
            if document_version:
                request_params['DocumentVersion'] = document_version
            if parsed_parameters:
                request_params['Parameters'] = parsed_parameters
            if timeout_seconds:
                request_params['TimeoutSeconds'] = timeout_seconds
            if comment:
                request_params['Comment'] = comment
            if max_concurrency:
                request_params['MaxConcurrency'] = max_concurrency
            if max_errors:
                request_params['MaxErrors'] = max_errors
            if output_s3_region:
                request_params['OutputS3Region'] = output_s3_region
            if output_s3_bucket_name:
                request_params['OutputS3BucketName'] = output_s3_bucket_name
            if output_s3_key_prefix:
                request_params['OutputS3KeyPrefix'] = output_s3_key_prefix
            if service_role_arn:
                request_params['ServiceRoleArn'] = service_role_arn
            if parsed_notification_config:
                request_params['NotificationConfig'] = parsed_notification_config
            if parsed_cloudwatch_output_config:
                request_params['CloudWatchOutputConfig'] = parsed_cloudwatch_output_config
            if parsed_alarm_configuration:
                request_params['AlarmConfiguration'] = parsed_alarm_configuration

            # Call AWS API
            ssm_client = _get_ssm_client(region, profile)
            response = ssm_client.send_command(**request_params)

            command = response['Command']
            output = '✅ Command sent successfully\n\n'
            output += '**Command Details:**\n'
            output += f'- Command ID: {command["CommandId"]}\n'
            output += f'- Document Name: {command["DocumentName"]}\n'
            output += f'- Status: {command["Status"]}\n'
            output += f'- Requested Date: {command["RequestedDateTime"]}\n'

            if command.get('InstanceIds'):
                output += f'- Target Instances: {", ".join(command["InstanceIds"])}\n'
            if command.get('Targets'):
                output += f'- Targets: {len(command["Targets"])} target groups\n'

            return CallToolResult(content=[{'type': 'text', 'text': output}])

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'send command')

    @mcp.tool()
    def get_command_invocation(
        command_id: str = Field(description='The parent command ID of the invocation'),
        instance_id: str = Field(
            description='The ID of the managed instance targeted by the command'
        ),
        plugin_name: Optional[str] = Field(
            None, description='The name of the plugin for detailed results'
        ),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """Get detailed results of a command invocation on a specific instance."""
        try:
            # Build request parameters
            request_params = {'CommandId': command_id, 'InstanceId': instance_id}

            if plugin_name:
                request_params['PluginName'] = plugin_name

            # Call AWS API
            ssm_client = _get_ssm_client(region, profile)
            response = ssm_client.get_command_invocation(**request_params)

            output = '✅ Command invocation retrieved successfully\n\n'
            output += '**Command Invocation Details:**\n'
            output += f'- Command ID: {response["CommandId"]}\n'
            output += f'- Instance ID: {response["InstanceId"]}\n'
            output += f'- Document Name: {response["DocumentName"]}\n'
            output += f'- Status: {response["Status"]}\n'

            if response.get('ExecutionStartDateTime'):
                output += f'- Start Time: {response["ExecutionStartDateTime"]}\n'
            if response.get('ExecutionEndDateTime'):
                output += f'- End Time: {response["ExecutionEndDateTime"]}\n'
            if response.get('ExecutionElapsedTime'):
                output += f'- Elapsed Time: {response["ExecutionElapsedTime"]}\n'
            if response.get('ResponseCode'):
                output += f'- Response Code: {response["ResponseCode"]}\n'

            if response.get('StandardOutputContent'):
                output += (
                    f'\n**Standard Output:**\n```\n{response["StandardOutputContent"]}\n```\n'
                )

            if response.get('StandardErrorContent'):
                output += f'\n**Standard Error:**\n```\n{response["StandardErrorContent"]}\n```\n'

            return CallToolResult(content=[{'type': 'text', 'text': output}])

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'get command invocation')

    @mcp.tool()
    def list_commands(
        command_id: Optional[str] = Field(
            None, description='If provided, lists only the specified command'
        ),
        instance_id: Optional[str] = Field(
            None, description='Lists commands issued against this instance ID'
        ),
        max_results: Optional[int] = Field(50, description='Maximum number of results to return'),
        next_token: Optional[str] = Field(
            None, description='Token to retrieve the next set of results'
        ),
        filters: Optional[str] = Field(
            None, description='JSON array of filters to limit the results'
        ),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """List commands with optional filtering."""
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

            if command_id:
                request_params['CommandId'] = command_id
            if instance_id:
                request_params['InstanceId'] = instance_id
            if max_results:
                request_params['MaxResults'] = max_results
            if next_token:
                request_params['NextToken'] = next_token
            if parsed_filters:
                request_params['Filters'] = parsed_filters

            # Call AWS API
            ssm_client = _get_ssm_client(region, profile)
            response = ssm_client.list_commands(**request_params)

            commands = response['Commands']

            if not commands:
                return CallToolResult(
                    content=[{'type': 'text', 'text': 'No commands found matching the criteria.'}]
                )

            output = '✅ Commands retrieved successfully\n\n'
            output += '**Commands:**\n'

            for command in commands:
                output += f'- **{command["CommandId"]}**\n'
                output += f'  - Document: {command["DocumentName"]}\n'
                output += f'  - Status: {command["Status"]}\n'
                output += f'  - Requested: {command["RequestedDateTime"]}\n'

                if command.get('InstanceIds'):
                    output += f'  - Instances: {", ".join(command["InstanceIds"][:3])}'
                    if len(command['InstanceIds']) > 3:
                        output += f' (+{len(command["InstanceIds"]) - 3} more)'
                    output += '\n'

                if command.get('Comment'):
                    output += f'  - Comment: {command["Comment"]}\n'
                output += '\n'

            # Add NextToken if present
            if response.get('NextToken'):
                output += f'**Next Token:** {response["NextToken"]}\n'

            return CallToolResult(content=[{'type': 'text', 'text': output}])

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'list commands')

    @mcp.tool()
    def cancel_command(
        command_id: str = Field(description='The ID of the command to cancel'),
        instance_ids: Optional[str] = Field(
            None, description='Comma-separated list of instance IDs to cancel the command on'
        ),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """Cancel a command execution."""
        if Context.is_readonly():
            return CallToolResult(
                content=[
                    {'type': 'text', 'text': 'Cannot cancel command: Server is in read-only mode'}
                ],
                isError=True,
            )

        try:
            # Parse instance IDs if provided
            parsed_instance_ids = None
            if instance_ids:
                parsed_instance_ids = [id.strip() for id in instance_ids.split(',')]

            # Build request parameters
            request_params = {'CommandId': command_id}

            if parsed_instance_ids:
                request_params['InstanceIds'] = parsed_instance_ids

            # Call AWS API
            ssm_client = _get_ssm_client(region, profile)
            ssm_client.cancel_command(**request_params)

            return CallToolResult(
                content=[{'type': 'text', 'text': '✅ Command cancelled successfully'}]
            )

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'cancel command')
