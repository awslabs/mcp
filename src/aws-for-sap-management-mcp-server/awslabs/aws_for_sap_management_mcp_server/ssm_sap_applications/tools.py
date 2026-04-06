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

"""SSM for SAP application management tools for MCP server."""

import asyncio
from awslabs.aws_for_sap_management_mcp_server.client_factory import get_aws_client
from awslabs.aws_for_sap_management_mcp_server.common import format_client_error, format_datetime, request_consent
from awslabs.aws_for_sap_management_mcp_server.ssm_sap_applications.models import (
    ApplicationDetail,
    ApplicationSummary,
    CascadeStopDetail,
    ComponentDetail,
    ListApplicationsResponse,
    OperationDetail,
    RegisterApplicationResponse,
    StartStopApplicationResponse,
)
from botocore.exceptions import ClientError
from loguru import logger
from mcp.server.fastmcp import Context
from mcp.shared.exceptions import McpError
from mcp.types import METHOD_NOT_FOUND
from pydantic import BaseModel, Field
from typing import Annotated, Any, Dict, List


class SSMSAPApplicationTools:
    """SSM for SAP application management tools."""

    def __init__(self):
        """Initialize the SSM for SAP application tools."""
        pass

    def register(self, mcp):
        """Register all SSM for SAP application tools with the MCP server."""
        mcp.tool(name='list_applications')(self.list_applications)
        mcp.tool(name='get_application')(self.get_application)
        mcp.tool(name='get_component')(self.get_component)
        mcp.tool(name='get_operation')(self.get_operation)
        mcp.tool(name='register_application')(self.register_application)
        mcp.tool(name='start_application')(self.start_application)
        mcp.tool(name='stop_application')(self.stop_application)

    async def list_applications(
        self,
        ctx: Context,
        region: Annotated[
            str | None,
            Field(
                description='AWS region to query. Defaults to AWS_REGION environment variable or us-east-1.'
            ),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(
                description='AWS CLI Profile Name to use. Falls back to AWS_PROFILE env var.'
            ),
        ] = None,
    ) -> ListApplicationsResponse:
        """List all SAP applications registered with AWS Systems Manager for SAP.

        Returns a list of all SAP applications (HANA and SAP_ABAP) in the specified region.

        Args:
            ctx: MCP context object.
            region: AWS region to query.
            profile_name: AWS CLI profile name.

        Returns:
            ListApplicationsResponse with application summaries.
        """
        try:
            client = get_aws_client('ssm-sap', region_name=region, profile_name=profile_name)
            apps = []
            response = client.list_applications()
            for app in response.get('Applications', []):
                apps.append(
                    ApplicationSummary(
                        id=app.get('Id', ''),
                        type=app.get('Type', 'UNKNOWN'),
                        arn=app.get('Arn'),
                        discovery_status=app.get('DiscoveryStatus'),
                    )
                )
            # Handle pagination
            while response.get('NextToken'):
                response = client.list_applications(NextToken=response['NextToken'])
                for app in response.get('Applications', []):
                    apps.append(
                        ApplicationSummary(
                            id=app.get('Id', ''),
                            type=app.get('Type', 'UNKNOWN'),
                            arn=app.get('Arn'),
                            discovery_status=app.get('DiscoveryStatus'),
                        )
                    )
            return ListApplicationsResponse(
                applications=apps,
                message=f'Found {len(apps)} application(s)',
            )
        except Exception as e:
            logger.error(f'Error listing applications: {e}')
            return ListApplicationsResponse(message=f'Error: {str(e)}')

    async def get_application(
        self,
        ctx: Context,
        application_id: Annotated[
            str,
            Field(description='The unique identifier of the SAP application.'),
        ],
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> ApplicationDetail:
        """Get detailed metadata for a specific SAP application.

        Retrieves application status, discovery status, type, and component information.

        Status values: ACTIVATED | STARTING | STOPPED | STOPPING | FAILED | REGISTERING | DELETING | UNKNOWN
        Discovery status values: SUCCESS | REGISTRATION_FAILED | REFRESH_FAILED | REGISTERING | DELETING

        Args:
            ctx: MCP context object.
            application_id: The application ID.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            ApplicationDetail with full application metadata.
        """
        try:
            client = get_aws_client('ssm-sap', region_name=region, profile_name=profile_name)
            response = client.get_application(ApplicationId=application_id)
            app = response.get('Application', {})

            # Get components
            components = []
            try:
                comp_response = client.list_components(ApplicationId=application_id)
                for comp in comp_response.get('Components', []):
                    comp_id = comp.get('ComponentId', '')
                    try:
                        detail = client.get_component(
                            ApplicationId=application_id, ComponentId=comp_id
                        ).get('Component', {})
                        components.append({
                            'component_id': comp_id,
                            'component_type': detail.get('ComponentType', 'UNKNOWN'),
                            'status': detail.get('Status', 'UNKNOWN'),
                            'sid': detail.get('Sid'),
                        })
                    except Exception as ce:
                        components.append({
                            'component_id': comp_id,
                            'error': str(ce),
                        })
            except Exception as e:
                logger.warning(f'Error listing components: {e}')

            return ApplicationDetail(
                id=app.get('Id', application_id),
                type=app.get('Type', 'UNKNOWN'),
                arn=app.get('Arn'),
                status=app.get('Status', 'UNKNOWN'),
                discovery_status=app.get('DiscoveryStatus', 'UNKNOWN'),
                status_message=app.get('StatusMessage'),
                components=components if components else None,
                associated_application_arns=app.get('AssociatedApplicationArns'),
                last_updated=format_datetime(app.get('LastUpdatedTime')),
            )
        except ClientError as e:
            return ApplicationDetail(
                id=application_id,
                type='UNKNOWN',
                status='ERROR',
                discovery_status='ERROR',
                status_message=format_client_error(e),
            )
        except Exception as e:
            logger.error(f'Error getting application: {e}')
            return ApplicationDetail(
                id=application_id,
                type='UNKNOWN',
                status='ERROR',
                discovery_status='ERROR',
                status_message=str(e),
            )

    async def get_component(
        self,
        ctx: Context,
        application_id: Annotated[
            str,
            Field(description='The unique identifier of the SAP application.'),
        ],
        component_id: Annotated[
            str,
            Field(description='The unique identifier of the component.'),
        ],
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> ComponentDetail:
        """Get detailed health status for a specific component of an SAP application.

        Component types: HANA | HANA_NODE | ABAP | ASCS | ERS | APP | DIALOG | WEBDISP | WD
        Component status: ACTIVATED | STARTING | STOPPED | STOPPING | FAILED | REGISTERING | DELETING | UNKNOWN

        Args:
            ctx: MCP context object.
            application_id: The application ID.
            component_id: The component ID.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            ComponentDetail with component metadata.
        """
        try:
            client = get_aws_client('ssm-sap', region_name=region, profile_name=profile_name)
            response = client.get_component(
                ApplicationId=application_id, ComponentId=component_id
            )
            comp = response.get('Component', {})

            hosts = []
            for host in comp.get('Hosts', []):
                hosts.append({
                    'hostname': host.get('HostName'),
                    'host_ip': host.get('HostIp'),
                    'host_role': host.get('HostRole'),
                    'ec2_instance_id': host.get('EC2InstanceId') or host.get('InstanceId'),
                    'os_version': host.get('OsVersion'),
                })

            return ComponentDetail(
                component_id=component_id,
                component_type=comp.get('ComponentType', 'UNKNOWN'),
                status=comp.get('Status', 'UNKNOWN'),
                sid=comp.get('Sid'),
                hosts=hosts if hosts else None,
            )
        except Exception as e:
            logger.error(f'Error getting component: {e}')
            return ComponentDetail(
                component_id=component_id,
                component_type='UNKNOWN',
                status='ERROR',
            )

    async def get_operation(
        self,
        ctx: Context,
        operation_id: Annotated[
            str,
            Field(description='The unique identifier of the operation.'),
        ],
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> OperationDetail:
        """Get the details of an SSM for SAP operation.

        Use this to check the status of async operations like register, start, or stop.

        Args:
            ctx: MCP context object.
            operation_id: The operation ID.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            OperationDetail with operation metadata.
        """
        try:
            client = get_aws_client('ssm-sap', region_name=region, profile_name=profile_name)
            response = client.get_operation(OperationId=operation_id)
            op = response.get('Operation', {})
            return OperationDetail(
                id=op.get('Id', operation_id),
                type=op.get('Type'),
                status=op.get('Status', 'UNKNOWN'),
                start_time=format_datetime(op.get('StartTime')),
                end_time=format_datetime(op.get('EndTime')),
                status_message=op.get('StatusMessage'),
            )
        except Exception as e:
            logger.error(f'Error getting operation: {e}')
            return OperationDetail(
                id=operation_id,
                status='ERROR',
                status_message=str(e),
            )

    async def register_application(
        self,
        ctx: Context,
        application_id: Annotated[
            str,
            Field(description='Unique identifier for the application (e.g., "MyHanaApp").'),
        ],
        application_type: Annotated[
            str,
            Field(description="Application type: 'HANA' or 'SAP_ABAP'."),
        ],
        sid: Annotated[
            str,
            Field(description='SAP System ID (3 characters, e.g., "HDB", "S4H").'),
        ],
        sap_instance_number: Annotated[
            str,
            Field(description='Two-digit instance number (e.g., "00", "01").'),
        ],
        instances: Annotated[
            List[str],
            Field(description='List of EC2 instance IDs (e.g., ["i-0123456789abcdef0"]).'),
        ],
        credentials: Annotated[
            List[Dict[str, str]] | None,
            Field(
                description='Credential configurations: [{"CredentialType": "ADMIN", "DatabaseName": "<SID>/<DB>", "SecretId": "<ARN>"}]'
            ),
        ] = None,
        database_arn: Annotated[
            str | None,
            Field(description='ARN of HANA database. REQUIRED for SAP_ABAP type only.'),
        ] = None,
        tags: Annotated[
            Dict[str, str] | None,
            Field(description='Tags to apply to the application.'),
        ] = None,
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> RegisterApplicationResponse:
        """Register an SAP application with AWS Systems Manager for SAP.

        For HANA applications, provide the HANA database details.
        For SAP_ABAP applications, you must first register the HANA database and provide its ARN.

        Args:
            ctx: MCP context object.
            application_id: Unique application identifier.
            application_type: HANA or SAP_ABAP.
            sid: SAP System ID (3 chars).
            sap_instance_number: Two-digit instance number.
            instances: List of EC2 instance IDs.
            credentials: Optional credential configurations.
            database_arn: Required for SAP_ABAP only.
            tags: Optional tags.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            RegisterApplicationResponse with registration status.
        """
        try:
            if application_type not in ('HANA', 'SAP_ABAP'):
                return RegisterApplicationResponse(
                    status='error',
                    message="application_type must be 'HANA' or 'SAP_ABAP'",
                )
            if application_type == 'SAP_ABAP' and not database_arn:
                return RegisterApplicationResponse(
                    status='error',
                    message='database_arn is required for SAP_ABAP applications.',
                )
            if len(sid) != 3:
                return RegisterApplicationResponse(
                    status='error', message='SID must be exactly 3 characters'
                )
            if len(sap_instance_number) != 2 or not sap_instance_number.isdigit():
                return RegisterApplicationResponse(
                    status='error',
                    message='sap_instance_number must be 2 digits (e.g., "00")',
                )
            if not instances:
                return RegisterApplicationResponse(
                    status='error', message='At least one EC2 instance ID is required'
                )

            client = get_aws_client('ssm-sap', region_name=region, profile_name=profile_name)
            params: Dict[str, Any] = {
                'ApplicationId': application_id,
                'ApplicationType': application_type,
                'Sid': sid,
                'SapInstanceNumber': sap_instance_number,
                'Instances': instances,
            }
            if credentials:
                params['Credentials'] = credentials
            if application_type == 'SAP_ABAP' and database_arn:
                params['DatabaseArn'] = database_arn
            if tags:
                params['Tags'] = tags

            response = client.register_application(**params)
            return RegisterApplicationResponse(
                status='success',
                message=f"Application '{application_id}' registered successfully",
                application_id=response.get('ApplicationId', application_id),
                application_arn=response.get('ApplicationArn'),
                operation_id=response.get('OperationId'),
            )
        except ClientError as e:
            return RegisterApplicationResponse(
                status='error',
                message=format_client_error(e),
                application_id=application_id,
            )
        except Exception as e:
            logger.error(f'Error registering application: {e}')
            return RegisterApplicationResponse(
                status='error', message=str(e), application_id=application_id
            )

    async def start_application(
        self,
        ctx: Context,
        application_id: Annotated[
            str,
            Field(description='The ID of the application to start.'),
        ],
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> StartStopApplicationResponse:
        """Start an SAP application registered with AWS Systems Manager for SAP.

        Args:
            ctx: MCP context object.
            application_id: The application ID.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            StartStopApplicationResponse with operation status.
        """
        try:
            await request_consent(
                f"Start SAP application '{application_id}'.",
                'I understand this will start my SAP application.',
                ctx,
            )
        except ValueError as e:
            return StartStopApplicationResponse(
                status='error',
                message=str(e),
                application_id=application_id,
            )

        try:
            client = get_aws_client('ssm-sap', region_name=region, profile_name=profile_name)
            response = client.start_application(ApplicationId=application_id)
            return StartStopApplicationResponse(
                status='success',
                message=f"Start operation initiated for '{application_id}'",
                operation_id=response.get('OperationId'),
                application_id=application_id,
            )
        except ClientError as e:
            return StartStopApplicationResponse(
                status='error',
                message=format_client_error(e),
                application_id=application_id,
            )
        except Exception as e:
            logger.error(f'Error starting application: {e}')
            return StartStopApplicationResponse(
                status='error', message=str(e), application_id=application_id
            )

    async def stop_application(
        self,
        ctx: Context,
        application_id: Annotated[
            str,
            Field(description='The ID of the application to stop.'),
        ],
        include_ec2_instance_shutdown: Annotated[
            bool,
            Field(description='If True, also shutdown the EC2 instances. Default: False.'),
        ] = False,
        stop_connected_entity: Annotated[
            str | None,
            Field(description="Connected entity to stop. Valid values: 'DBMS'."),
        ] = None,
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> StartStopApplicationResponse:
        """Stop an SAP application registered with AWS Systems Manager for SAP.

        For HANA applications with associated NetWeaver (SAP_ABAP) applications,
        this tool can optionally stop the NetWeaver applications first before
        stopping the HANA database.

        Args:
            ctx: MCP context object.
            application_id: The application ID.
            include_ec2_instance_shutdown: Whether to also shutdown EC2 instances.
            stop_connected_entity: Connected entity to stop (e.g., 'DBMS').
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            StartStopApplicationResponse with operation status.
        """
        if stop_connected_entity and stop_connected_entity not in ('DBMS',):
            return StartStopApplicationResponse(
                status='error',
                message=f"Invalid stop_connected_entity: '{stop_connected_entity}'. Valid: ['DBMS']",
                application_id=application_id,
            )

        # Check application type and discover associated NetWeaver apps
        associated_nw_apps: List[str] = []
        try:
            client = get_aws_client('ssm-sap', region_name=region, profile_name=profile_name)
            app_response = client.get_application(ApplicationId=application_id)
            app = app_response.get('Application', {})
            app_type = app.get('Type', 'UNKNOWN')

            if app_type == 'HANA':
                for arn in app.get('AssociatedApplicationArns', []):
                    # Extract app ID from ARN
                    assoc_id = arn.split('/')[-1] if '/' in arn else None
                    if not assoc_id:
                        continue
                    # Confirm it's a NetWeaver app via GetApplication
                    try:
                        assoc_resp = client.get_application(ApplicationId=assoc_id)
                        assoc_app = assoc_resp.get('Application', {})
                        if assoc_app.get('Type') == 'SAP_ABAP':
                            associated_nw_apps.append(assoc_id)
                    except Exception as e:
                        logger.warning(f'Could not verify associated app {assoc_id}: {e}')
        except Exception as e:
            return StartStopApplicationResponse(
                status='error',
                message=f'Failed to retrieve application details: {e}',
                application_id=application_id,
            )

        # Build consent dialog dynamically
        cascade_stop = False
        ec2_warning = ' EC2 instances will also be shut down.' if include_ec2_instance_shutdown else ''

        if associated_nw_apps:
            nw_list = ', '.join(associated_nw_apps)
            try:
                ConsentModel = type(
                    'Consent',
                    (BaseModel,),
                    {
                        '__annotations__': {
                            'stop_associated_apps_first': bool,
                            'acknowledge': bool,
                        },
                        'stop_associated_apps_first': Field(
                            default=False,
                            description=(
                                f'Stop associated NetWeaver application(s) [{nw_list}] '
                                'before stopping the HANA database. Recommended to avoid data inconsistency.'
                            )
                        ),
                        'acknowledge': Field(
                            description=(
                                'I understand this will stop my SAP application. '
                                'This will cause downtime and may affect dependent systems and users.'
                            )
                        ),
                    },
                )

                elicitation_result = await ctx.elicit(
                    message=(
                        f"Stop HANA application '{application_id}'.{ec2_warning}\n\n"
                        f'Associated NetWeaver application(s) found: {nw_list}\n\n'
                        'Please review and acknowledge the risk before proceeding.'
                    ),
                    schema=ConsentModel,
                )

                if elicitation_result.action != 'accept' or not elicitation_result.data.acknowledge:
                    return StartStopApplicationResponse(
                        status='error',
                        message='User rejected the operation.',
                        application_id=application_id,
                    )
                cascade_stop = elicitation_result.data.stop_associated_apps_first
            except McpError as e:
                if e.error.code == METHOD_NOT_FOUND:
                    return StartStopApplicationResponse(
                        status='error',
                        message='Client does not support elicitation. Cannot proceed without user confirmation.',
                        application_id=application_id,
                    )
                raise e
        else:
            # No associated apps — standard consent
            try:
                await request_consent(
                    f"Stop SAP application '{application_id}'.{ec2_warning}",
                    'I understand this will stop my SAP application. '
                    'This will cause downtime and may affect dependent systems and users.',
                    ctx,
                )
            except ValueError as e:
                return StartStopApplicationResponse(
                    status='error',
                    message=str(e),
                    application_id=application_id,
                )

        # Stop associated NetWeaver apps first if requested
        cascade_details: List[CascadeStopDetail] = []
        if cascade_stop and associated_nw_apps:
            for nw_app_id in associated_nw_apps:
                try:
                    stop_resp = client.stop_application(ApplicationId=nw_app_id)
                    op_id = stop_resp.get('OperationId')
                    nw_start_time = None
                    nw_end_time = None
                    nw_status = 'UNKNOWN'
                    if op_id:
                        for _ in range(120):  # Max ~10 minutes
                            await asyncio.sleep(5)
                            op_resp = client.get_operation(OperationId=op_id)
                            op = op_resp.get('Operation', {})
                            nw_status = op.get('Status', '')
                            nw_start_time = str(op.get('StartTime', ''))
                            nw_end_time = str(op.get('EndTime', ''))
                            if nw_status in ('SUCCESS', 'ERROR'):
                                if nw_status == 'ERROR':
                                    cascade_details.append(CascadeStopDetail(
                                        application_id=nw_app_id,
                                        application_type='SAP_ABAP',
                                        operation_id=op_id,
                                        status='ERROR',
                                        start_time=nw_start_time,
                                        end_time=nw_end_time,
                                    ))
                                    return StartStopApplicationResponse(
                                        status='error',
                                        message=f"Failed to stop associated NetWeaver app '{nw_app_id}': {op.get('StatusMessage', 'Unknown error')}",
                                        application_id=application_id,
                                        associated_app_stop_details=cascade_details,
                                    )
                                cascade_details.append(CascadeStopDetail(
                                    application_id=nw_app_id,
                                    application_type='SAP_ABAP',
                                    operation_id=op_id,
                                    status='SUCCESS',
                                    start_time=nw_start_time,
                                    end_time=nw_end_time,
                                ))
                                break
                        else:
                            cascade_details.append(CascadeStopDetail(
                                application_id=nw_app_id,
                                application_type='SAP_ABAP',
                                operation_id=op_id,
                                status='TIMED_OUT',
                            ))
                            return StartStopApplicationResponse(
                                status='error',
                                message=f"Timed out waiting for NetWeaver app '{nw_app_id}' to stop.",
                                application_id=application_id,
                                associated_app_stop_details=cascade_details,
                            )
                except ClientError as e:
                    cascade_details.append(CascadeStopDetail(
                        application_id=nw_app_id,
                        application_type='SAP_ABAP',
                        operation_id=None,
                        status='ERROR',
                    ))
                    return StartStopApplicationResponse(
                        status='error',
                        message=f"Error stopping NetWeaver app '{nw_app_id}': {e.response['Error']['Message']}",
                        application_id=application_id,
                        associated_app_stop_details=cascade_details,
                    )

        # Now stop the target application
        try:
            params: Dict[str, Any] = {'ApplicationId': application_id}
            if include_ec2_instance_shutdown:
                params['IncludeEc2InstanceShutdown'] = True
            if stop_connected_entity:
                params['StopConnectedEntity'] = stop_connected_entity

            response = client.stop_application(**params)
            message = f"Stop operation initiated for '{application_id}'"
            if cascade_details:
                stopped_names = ', '.join(d.application_id for d in cascade_details)
                message += f" (after successfully stopping associated app(s): {stopped_names})"
            return StartStopApplicationResponse(
                status='success',
                message=message,
                operation_id=response.get('OperationId'),
                application_id=application_id,
                associated_app_stop_details=cascade_details if cascade_details else None,
            )
        except ClientError as e:
            return StartStopApplicationResponse(
                status='error',
                message=format_client_error(e),
                application_id=application_id,
            )
        except Exception as e:
            logger.error(f'Error stopping application: {e}')
            return StartStopApplicationResponse(
                status='error', message=str(e), application_id=application_id
            )
