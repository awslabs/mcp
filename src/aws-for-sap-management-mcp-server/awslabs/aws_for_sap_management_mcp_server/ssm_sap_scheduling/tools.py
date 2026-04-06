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

"""SSM for SAP scheduling tools using Amazon EventBridge Scheduler."""

import json
import uuid
from awslabs.aws_for_sap_management_mcp_server.client_factory import get_aws_client
from awslabs.aws_for_sap_management_mcp_server.common import request_consent
from awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.models import (
    CreateScheduleResponse,
    DeleteScheduleResponse,
    ListSchedulesResponse,
    ScheduleDetail,
    UpdateScheduleStateResponse,
)
from botocore.exceptions import ClientError
from datetime import datetime
from loguru import logger
from mcp.server.fastmcp import Context
from mcp.shared.exceptions import McpError
from mcp.types import METHOD_NOT_FOUND
from pydantic import BaseModel, Field
from typing import Annotated, Any, Dict, List


# Mapping of SSM-SAP operations to EventBridge Scheduler target ARNs
_OPERATION_TARGET_ARNS = {
    'start_application': 'arn:aws:scheduler:::aws-sdk:ssmsap:startApplication',
    'stop_application': 'arn:aws:scheduler:::aws-sdk:ssmsap:stopApplication',
    'config_checks': 'arn:aws:scheduler:::aws-sdk:ssmsap:startConfigurationChecks',
}


def _determine_operation_type(target_arn: str) -> str:
    """Determine operation type from target ARN."""
    if 'startApplication' in target_arn:
        return 'Start Application'
    elif 'stopApplication' in target_arn:
        return 'Stop Application'
    elif 'startConfigurationChecks' in target_arn:
        return 'Configuration Checks'
    return 'Unknown'


def _generate_schedule_name(prefix: str, application_id: str) -> str:
    """Generate a unique schedule name."""
    max_len = 64 - len(prefix) - 10
    truncated = application_id[:max_len] if len(application_id) > max_len else application_id
    return f'{prefix}{truncated}-{uuid.uuid4().hex[:8]}'


def _ensure_scheduler_role(
    region: str | None = None,
    profile_name: str | None = None,
) -> str:
    """Ensure the EventBridge Scheduler execution role exists.

    Creates the role with AWSSystemsManagerForSAPFullAccess policy if it doesn't exist.

    Returns:
        ARN of the scheduler execution role.
    """
    role_name = 'EventBridgeSchedulerSSMSAPRole'

    try:
        iam_client = get_aws_client('iam', region_name=region, profile_name=profile_name)
    except Exception as e:
        logger.error(f'Failed to get IAM client: {e}')
        raise

    # Check if role exists
    try:
        response = iam_client.get_role(RoleName=role_name)
        return response['Role']['Arn']
    except ClientError as e:
        if e.response['Error']['Code'] != 'NoSuchEntity':
            logger.warning(f'Could not verify scheduler role: {e}')
            # Assume it exists and construct ARN
            sts = get_aws_client('sts', region_name=region, profile_name=profile_name)
            account_id = sts.get_caller_identity()['Account']
            return f'arn:aws:iam::{account_id}:role/{role_name}'

    # Create the role
    trust_policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Principal': {'Service': 'scheduler.amazonaws.com'},
                'Action': 'sts:AssumeRole',
            }
        ],
    }

    try:
        create_response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for EventBridge Scheduler to execute SSM SAP operations',
        )
        role_arn = create_response['Role']['Arn']
        logger.info(f'Created scheduler role: {role_arn}')

        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn='arn:aws:iam::aws:policy/AWSSystemsManagerForSAPFullAccess',
        )
        logger.info(f'Attached AWSSystemsManagerForSAPFullAccess to {role_name}')
        return role_arn
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            sts = get_aws_client('sts', region_name=region, profile_name=profile_name)
            account_id = sts.get_caller_identity()['Account']
            return f'arn:aws:iam::{account_id}:role/{role_name}'
        raise


class SSMSAPSchedulingTools:
    """SSM for SAP scheduling tools using Amazon EventBridge Scheduler."""

    def __init__(self):
        """Initialize the scheduling tools."""
        pass

    def register(self, mcp):
        """Register all scheduling tools with the MCP server."""
        mcp.tool(name='schedule_config_checks')(self.schedule_config_checks)
        mcp.tool(name='schedule_start_application')(self.schedule_start_application)
        mcp.tool(name='schedule_stop_application')(self.schedule_stop_application)
        mcp.tool(name='list_app_schedules')(self.list_app_schedules)
        mcp.tool(name='delete_schedule')(self.delete_schedule)
        mcp.tool(name='update_schedule_state')(self.update_schedule_state)
        mcp.tool(name='get_schedule_details')(self.get_schedule_details)

    async def schedule_config_checks(
        self,
        ctx: Context,
        application_id: Annotated[
            str,
            Field(description='The unique identifier of the SAP application.'),
        ],
        schedule_expression: Annotated[
            str,
            Field(
                description='Schedule expression. Examples: "rate(7 days)", "cron(0 9 ? * MON *)".'
            ),
        ],
        check_ids: Annotated[
            List[str] | None,
            Field(description='Optional list of specific configuration check IDs to run.'),
        ] = None,
        schedule_name: Annotated[
            str | None,
            Field(description='Optional custom name for the schedule. Auto-generated if not provided.'),
        ] = None,
        timezone_str: Annotated[
            str | None,
            Field(description='Timezone for cron expressions (e.g., "America/New_York"). Default: UTC.'),
        ] = None,
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> CreateScheduleResponse:
        """Schedule recurring configuration checks using Amazon EventBridge Scheduler.

        Creates an EventBridge schedule that periodically triggers SSM for SAP
        configuration checks against the specified application.

        Args:
            ctx: MCP context object.
            application_id: The application ID.
            schedule_expression: Rate or cron expression.
            check_ids: Optional specific check IDs.
            schedule_name: Optional custom schedule name.
            timezone_str: Timezone for cron expressions.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            CreateScheduleResponse with schedule details.
        """
        try:
            await request_consent(
                f"Schedule recurring configuration checks for SAP application '{application_id}' "
                f"with expression '{schedule_expression}'.",
                'I understand this will create a schedule that automatically runs configuration checks '
                'against my SAP application on a recurring basis.',
                ctx,
            )
        except ValueError as e:
            return CreateScheduleResponse(
                status='error',
                message=str(e),
                schedule_name=schedule_name or _generate_schedule_name('ssmsap-cc-', application_id),
                schedule_arn=None,
                application_id=application_id,
                schedule_expression=schedule_expression,
            )

        return await self._create_schedule(
            operation='config_checks',
            application_id=application_id,
            schedule_expression=schedule_expression,
            schedule_name=schedule_name or _generate_schedule_name('ssmsap-cc-', application_id),
            description=f'Scheduled configuration checks for SAP application {application_id}',
            extra_input={'ConfigurationCheckIds': check_ids} if check_ids else {},
            timezone_str=timezone_str,
            region=region,
            profile_name=profile_name,
        )

    async def schedule_start_application(
        self,
        ctx: Context,
        application_id: Annotated[
            str,
            Field(description='The unique identifier of the SAP application to start.'),
        ],
        schedule_expression: Annotated[
            str,
            Field(
                description='Schedule expression. Examples: "cron(0 8 ? * MON-FRI *)" for weekdays at 8 AM, "rate(12 hours)".'
            ),
        ],
        schedule_name: Annotated[
            str | None,
            Field(description='Optional custom name. Auto-generated if not provided.'),
        ] = None,
        description: Annotated[
            str | None,
            Field(description='Optional description for the schedule.'),
        ] = None,
        start_date: Annotated[
            str | None,
            Field(description='Optional start date in ISO format (e.g., "2026-01-15T00:00:00Z").'),
        ] = None,
        end_date: Annotated[
            str | None,
            Field(description='Optional end date in ISO format.'),
        ] = None,
        timezone_str: Annotated[
            str | None,
            Field(description='Timezone for cron expressions. Default: UTC.'),
        ] = None,
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> CreateScheduleResponse:
        """Schedule automatic start of an SAP application using EventBridge Scheduler.

        Useful for starting SAP systems at the beginning of business hours or
        cost optimization by starting dev/test systems only when needed.

        Args:
            ctx: MCP context object.
            application_id: The application ID.
            schedule_expression: Rate or cron expression.
            schedule_name: Optional custom schedule name.
            description: Optional description.
            start_date: Optional start date (ISO format).
            end_date: Optional end date (ISO format).
            timezone_str: Timezone for cron expressions.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            CreateScheduleResponse with schedule details.
        """
        try:
            await request_consent(
                f"Schedule automatic START for SAP application '{application_id}' "
                f"with expression '{schedule_expression}'.",
                'I understand this will create a schedule that automatically starts my SAP application.',
                ctx,
            )
        except ValueError as e:
            return CreateScheduleResponse(
                status='error',
                message=str(e),
                schedule_name=schedule_name or _generate_schedule_name('ssmsap-start-', application_id),
                schedule_arn=None,
                application_id=application_id,
                schedule_expression=schedule_expression,
            )

        return await self._create_schedule(
            operation='start_application',
            application_id=application_id,
            schedule_expression=schedule_expression,
            schedule_name=schedule_name or _generate_schedule_name('ssmsap-start-', application_id),
            description=description or f'Scheduled start for SAP application {application_id}',
            start_date=start_date,
            end_date=end_date,
            timezone_str=timezone_str,
            region=region,
            profile_name=profile_name,
        )

    async def schedule_stop_application(
        self,
        ctx: Context,
        application_id: Annotated[
            str,
            Field(description='The unique identifier of the SAP application to stop.'),
        ],
        schedule_expression: Annotated[
            str,
            Field(
                description='Schedule expression. Examples: "cron(0 20 ? * MON-FRI *)" for weekdays at 8 PM.'
            ),
        ],
        include_ec2_instance_shutdown: Annotated[
            bool,
            Field(description='If True, also shutdown EC2 instances. Default: False.'),
        ] = False,
        stop_connected_entity: Annotated[
            str | None,
            Field(description="Connected entity to stop. Valid values: 'DBMS'."),
        ] = None,
        schedule_name: Annotated[
            str | None,
            Field(description='Optional custom name. Auto-generated if not provided.'),
        ] = None,
        description: Annotated[
            str | None,
            Field(description='Optional description for the schedule.'),
        ] = None,
        start_date: Annotated[
            str | None,
            Field(description='Optional start date in ISO format.'),
        ] = None,
        end_date: Annotated[
            str | None,
            Field(description='Optional end date in ISO format.'),
        ] = None,
        timezone_str: Annotated[
            str | None,
            Field(description='Timezone for cron expressions. Default: UTC.'),
        ] = None,
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> CreateScheduleResponse:
        """Schedule automatic stop of an SAP application using EventBridge Scheduler.

        Useful for stopping SAP systems at end of business hours or cost optimization
        by stopping dev/test systems overnight/weekends.

        Args:
            ctx: MCP context object.
            application_id: The application ID.
            schedule_expression: Rate or cron expression.
            include_ec2_instance_shutdown: Whether to also shutdown EC2 instances.
            stop_connected_entity: Connected entity to stop (e.g., 'DBMS').
            schedule_name: Optional custom schedule name.
            description: Optional description.
            start_date: Optional start date (ISO format).
            end_date: Optional end date (ISO format).
            timezone_str: Timezone for cron expressions.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            CreateScheduleResponse with schedule details.
        """
        extra_input: Dict[str, Any] = {}
        if include_ec2_instance_shutdown:
            extra_input['IncludeEc2InstanceShutdown'] = True
        if stop_connected_entity:
            extra_input['StopConnectedEntity'] = stop_connected_entity

        ec2_warning = ' EC2 instances will also be shut down.' if include_ec2_instance_shutdown else ''
        try:
            await request_consent(
                f"Schedule automatic STOP for SAP application '{application_id}' "
                f"with expression '{schedule_expression}'.{ec2_warning}",
                'I understand this will create a schedule that automatically stops my SAP application. '
                'This will cause downtime and may affect dependent systems and users.',
                ctx,
            )
        except ValueError as e:
            return CreateScheduleResponse(
                status='error',
                message=str(e),
                schedule_name=schedule_name or _generate_schedule_name('ssmsap-stop-', application_id),
                schedule_arn=None,
                application_id=application_id,
                schedule_expression=schedule_expression,
            )

        return await self._create_schedule(
            operation='stop_application',
            application_id=application_id,
            schedule_expression=schedule_expression,
            schedule_name=schedule_name or _generate_schedule_name('ssmsap-stop-', application_id),
            description=description or f'Scheduled stop for SAP application {application_id}',
            extra_input=extra_input,
            start_date=start_date,
            end_date=end_date,
            timezone_str=timezone_str,
            region=region,
            profile_name=profile_name,
        )

    async def _create_schedule(
        self,
        operation: str,
        application_id: str,
        schedule_expression: str,
        schedule_name: str,
        description: str,
        extra_input: Dict[str, Any] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        timezone_str: str | None = None,
        region: str | None = None,
        profile_name: str | None = None,
    ) -> CreateScheduleResponse:
        """Internal helper to create an EventBridge schedule."""
        target_arn = _OPERATION_TARGET_ARNS.get(operation)
        if not target_arn:
            return CreateScheduleResponse(
                status='error',
                message=f'Unknown operation: {operation}',
                schedule_name=schedule_name,
                application_id=application_id,
                schedule_expression=schedule_expression,
            )

        input_payload: Dict[str, Any] = {'ApplicationId': application_id}
        if extra_input:
            input_payload.update(extra_input)

        try:
            role_arn = _ensure_scheduler_role(region=region, profile_name=profile_name)
            scheduler = get_aws_client('scheduler', region_name=region, profile_name=profile_name)

            params: Dict[str, Any] = {
                'Name': schedule_name,
                'ScheduleExpression': schedule_expression,
                'Target': {
                    'Arn': target_arn,
                    'Input': json.dumps(input_payload),
                    'RoleArn': role_arn,
                },
                'FlexibleTimeWindow': {'Mode': 'OFF'},
                'Description': description,
            }
            if timezone_str:
                params['ScheduleExpressionTimezone'] = timezone_str
            if start_date:
                params['StartDate'] = datetime.fromisoformat(
                    start_date.replace('Z', '+00:00')
                )
            if end_date:
                params['EndDate'] = datetime.fromisoformat(
                    end_date.replace('Z', '+00:00')
                )

            response = scheduler.create_schedule(**params)
            return CreateScheduleResponse(
                status='success',
                message='Schedule created successfully',
                schedule_name=schedule_name,
                schedule_arn=response.get('ScheduleArn'),
                application_id=application_id,
                schedule_expression=schedule_expression,
            )
        except ClientError as e:
            return CreateScheduleResponse(
                status='error',
                message=f'{e.response["Error"]["Code"]}: {e.response["Error"]["Message"]}',
                schedule_name=schedule_name,
                application_id=application_id,
                schedule_expression=schedule_expression,
            )
        except Exception as e:
            logger.error(f'Error creating schedule: {e}')
            return CreateScheduleResponse(
                status='error',
                message=str(e),
                schedule_name=schedule_name,
                application_id=application_id,
                schedule_expression=schedule_expression,
            )

    async def list_app_schedules(
        self,
        ctx: Context,
        application_id: Annotated[
            str,
            Field(description='The unique identifier of the SAP application.'),
        ],
        include_disabled: Annotated[
            bool,
            Field(description='If True, include disabled schedules. Default: True.'),
        ] = True,
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> ListSchedulesResponse:
        """List all EventBridge Scheduler schedules for a specific SAP application.

        Scans all schedules and filters to those targeting the given application ID.

        Args:
            ctx: MCP context object.
            application_id: The application ID.
            include_disabled: Whether to include disabled schedules.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            ListSchedulesResponse with matching schedules.
        """
        try:
            scheduler = get_aws_client('scheduler', region_name=region, profile_name=profile_name)

            all_schedules = []
            paginator = scheduler.get_paginator('list_schedules')
            for page in paginator.paginate():
                all_schedules.extend(page.get('Schedules', []))

            matching: List[ScheduleDetail] = []
            for summary in all_schedules:
                name = summary['Name']
                try:
                    detail = scheduler.get_schedule(Name=name)
                    target = detail.get('Target', {})
                    try:
                        input_data = json.loads(target.get('Input', '{}'))
                    except (json.JSONDecodeError, TypeError):
                        continue

                    if input_data.get('ApplicationId') != application_id:
                        continue

                    state = detail.get('State', 'UNKNOWN')
                    if not include_disabled and state == 'DISABLED':
                        continue

                    target_arn = target.get('Arn', '')
                    matching.append(
                        ScheduleDetail(
                            schedule_name=name,
                            schedule_arn=detail.get('Arn'),
                            state=state,
                            schedule_expression=detail.get('ScheduleExpression', ''),
                            operation_type=_determine_operation_type(target_arn),
                            description=detail.get('Description'),
                            timezone=detail.get('ScheduleExpressionTimezone', 'UTC'),
                        )
                    )
                except Exception as e:
                    logger.warning(f'Error processing schedule {name}: {e}')

            enabled = sum(1 for s in matching if s.state == 'ENABLED')
            return ListSchedulesResponse(
                application_id=application_id,
                total_schedules=len(matching),
                enabled_count=enabled,
                disabled_count=len(matching) - enabled,
                schedules=matching,
            )
        except Exception as e:
            logger.error(f'Error listing schedules: {e}')
            return ListSchedulesResponse(
                application_id=application_id,
            )

    async def delete_schedule(
        self,
        ctx: Context,
        schedule_name: Annotated[
            str,
            Field(description='The name of the schedule to delete.'),
        ],
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> DeleteScheduleResponse:
        """Delete an EventBridge Scheduler schedule.

        Args:
            ctx: MCP context object.
            schedule_name: The schedule name.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            DeleteScheduleResponse with deletion status.
        """
        try:
            await request_consent(
                f"Delete EventBridge schedule '{schedule_name}'. This action cannot be undone.",
                'I understand this will permanently delete the schedule. '
                'Any automated operations tied to this schedule will stop running.',
                ctx,
            )
        except ValueError as e:
            return DeleteScheduleResponse(
                status='error',
                message=str(e),
                schedule_name=schedule_name,
            )

        try:
            scheduler = get_aws_client('scheduler', region_name=region, profile_name=profile_name)
            scheduler.delete_schedule(Name=schedule_name)
            return DeleteScheduleResponse(
                status='success',
                message=f"Schedule '{schedule_name}' deleted successfully",
                schedule_name=schedule_name,
            )
        except ClientError as e:
            return DeleteScheduleResponse(
                status='error',
                message=f'{e.response["Error"]["Code"]}: {e.response["Error"]["Message"]}',
                schedule_name=schedule_name,
            )
        except Exception as e:
            logger.error(f'Error deleting schedule: {e}')
            return DeleteScheduleResponse(
                status='error', message=str(e), schedule_name=schedule_name
            )

    async def update_schedule_state(
        self,
        ctx: Context,
        schedule_name: Annotated[
            str,
            Field(description='The name of the schedule to update.'),
        ],
        enabled: Annotated[
            bool,
            Field(description='True to enable, False to disable.'),
        ],
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> UpdateScheduleStateResponse:
        """Enable or disable an EventBridge Scheduler schedule.

        Args:
            ctx: MCP context object.
            schedule_name: The schedule name.
            enabled: True to enable, False to disable.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            UpdateScheduleStateResponse with new state.
        """
        new_state = 'ENABLED' if enabled else 'DISABLED'
        action_word = 'enable' if enabled else 'disable'
        try:
            await request_consent(
                f"{'Enable' if enabled else 'Disable'} EventBridge schedule '{schedule_name}'.",
                f'I understand this will {action_word} the schedule. '
                + (
                    'Enabling it will resume automated operations on my SAP application.'
                    if enabled
                    else 'Disabling it will pause automated operations until re-enabled.'
                ),
                ctx,
            )
        except ValueError as e:
            return UpdateScheduleStateResponse(
                status='error',
                message=str(e),
                schedule_name=schedule_name,
                new_state=new_state,
            )

        try:
            scheduler = get_aws_client('scheduler', region_name=region, profile_name=profile_name)
            detail = scheduler.get_schedule(Name=schedule_name)
            current_state = detail.get('State')

            if current_state == new_state:
                return UpdateScheduleStateResponse(
                    status='no_change',
                    message=f"Schedule '{schedule_name}' is already {new_state}",
                    schedule_name=schedule_name,
                    previous_state=current_state,
                    new_state=new_state,
                )

            scheduler.update_schedule(
                Name=schedule_name,
                ScheduleExpression=detail.get('ScheduleExpression'),
                Target=detail.get('Target'),
                FlexibleTimeWindow=detail.get('FlexibleTimeWindow'),
                State=new_state,
            )
            return UpdateScheduleStateResponse(
                status='success',
                message=f"Schedule '{schedule_name}' has been {new_state.lower()}",
                schedule_name=schedule_name,
                previous_state=current_state,
                new_state=new_state,
            )
        except ClientError as e:
            return UpdateScheduleStateResponse(
                status='error',
                message=f'{e.response["Error"]["Code"]}: {e.response["Error"]["Message"]}',
                schedule_name=schedule_name,
                new_state=new_state,
            )
        except Exception as e:
            logger.error(f'Error updating schedule state: {e}')
            return UpdateScheduleStateResponse(
                status='error',
                message=str(e),
                schedule_name=schedule_name,
                new_state=new_state,
            )

    async def get_schedule_details(
        self,
        ctx: Context,
        schedule_name: Annotated[
            str,
            Field(description='The name of the schedule to retrieve.'),
        ],
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> Dict[str, Any]:
        """Get detailed information about a specific EventBridge Scheduler schedule.

        Args:
            ctx: MCP context object.
            schedule_name: The schedule name.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            Dictionary with full schedule details including target, expression, and state.
        """
        try:
            scheduler = get_aws_client('scheduler', region_name=region, profile_name=profile_name)
            detail = scheduler.get_schedule(Name=schedule_name)

            target = detail.get('Target', {})
            target_arn = target.get('Arn', '')
            try:
                input_data = json.loads(target.get('Input', '{}'))
            except (json.JSONDecodeError, TypeError):
                input_data = {}

            return {
                'status': 'success',
                'schedule_name': schedule_name,
                'schedule_arn': detail.get('Arn'),
                'state': detail.get('State'),
                'schedule_expression': detail.get('ScheduleExpression'),
                'timezone': detail.get('ScheduleExpressionTimezone', 'UTC'),
                'operation_type': _determine_operation_type(target_arn),
                'description': detail.get('Description', ''),
                'target_arn': target_arn,
                'target_role_arn': target.get('RoleArn'),
                'input': input_data,
                'creation_date': str(detail.get('CreationDate', '')),
                'last_modified': str(detail.get('LastModificationDate', '')),
            }
        except ClientError as e:
            code = e.response['Error']['Code']
            if code == 'ResourceNotFoundException':
                return {'status': 'error', 'message': f"Schedule '{schedule_name}' not found"}
            return {'status': 'error', 'message': f'{code}: {e.response["Error"]["Message"]}'}
        except Exception as e:
            logger.error(f'Error getting schedule details: {e}')
            return {'status': 'error', 'message': str(e)}
