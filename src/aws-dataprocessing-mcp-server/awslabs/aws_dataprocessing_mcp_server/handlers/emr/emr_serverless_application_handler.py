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

"""EMRServerlessApplicationHandler for Data Processing MCP Server."""

import json
from awslabs.aws_dataprocessing_mcp_server.models.emr_models import (
    CreateApplicationData,
    DeleteApplicationData,
    GetApplicationData,
    ListApplicationsData,
    StartApplicationData,
    StopApplicationData,
    UpdateApplicationData,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.consts import (
    EMR_SERVERLESS_APPLICATION_RESOURCE_TYPE,
)
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional


class EMRServerlessApplicationHandler:
    """Handler for Amazon EMR Serverless Application operations."""

    def __init__(self, mcp, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the EMR Serverless Application handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.emr_serverless_client = AwsHelper.create_boto3_client('emr-serverless')

        # Register tools
        self.mcp.tool(name='manage_aws_emr_serverless_applications')(
            self.manage_aws_emr_serverless_applications
        )

    def _create_error_response(self, operation: str, error_message: str):
        """Create appropriate error response based on operation type."""
        return CallToolResult(
            isError=True,
            content=[TextContent(type='text', text=error_message)],
        )

    async def manage_aws_emr_serverless_applications(
        self,
        ctx: Context,
        operation: Annotated[
            str,
            Field(
                description='Operation to perform: create-application, get-application, update-application, delete-application, list-applications, start-application, stop-application. Choose read-only operations when write access is disabled.',
            ),
        ],
        application_id: Annotated[
            Optional[str],
            Field(
                description='ID of the EMR Serverless application (required for get-application, update-application, delete-application, start-application, stop-application).',
            ),
        ] = None,
        name: Annotated[
            Optional[str],
            Field(
                description='Name of the EMR Serverless application (optional for create-application).',
            ),
        ] = None,
        release_label: Annotated[
            Optional[str],
            Field(
                description='The Amazon EMR release associated with the application (required for create-application). Format: emr-x.x.x',
            ),
        ] = None,
        type: Annotated[
            Optional[str],
            Field(
                description='The type of application, such as Spark or Hive (required for create-application).',
            ),
        ] = None,
        client_token: Annotated[
            Optional[str],
            Field(
                description='The client idempotency token (required for create-application and update-application).',
            ),
        ] = None,
        initial_capacity: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='The capacity to initialize when the application is created/updated (optional).',
            ),
        ] = None,
        maximum_capacity: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='The maximum capacity to allocate (optional).',
            ),
        ] = None,
        tags: Annotated[
            Optional[Dict[str, str]],
            Field(
                description='The tags assigned to the application (optional).',
            ),
        ] = None,
        auto_start_configuration: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='The configuration for an application to automatically start on job submission (optional).',
            ),
        ] = None,
        auto_stop_configuration: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='The configuration for an application to automatically stop after idle time (optional).',
            ),
        ] = None,
        network_configuration: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='The network configuration for customer VPC connectivity (optional).',
            ),
        ] = None,
        architecture: Annotated[
            Optional[str],
            Field(
                description='The CPU architecture of an application: ARM64 or X86_64 (optional).',
            ),
        ] = None,
        image_configuration: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='The image configuration for all worker types (optional).',
            ),
        ] = None,
        worker_type_specifications: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='The key-value pairs that specify worker type specifications (optional).',
            ),
        ] = None,
        runtime_configuration: Annotated[
            Optional[List[Dict[str, Any]]],
            Field(
                description='The Configuration specifications for the application (optional).',
            ),
        ] = None,
        monitoring_configuration: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='The configuration setting for monitoring (optional).',
            ),
        ] = None,
        interactive_configuration: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='The interactive configuration object (optional).',
            ),
        ] = None,
        scheduler_configuration: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='The scheduler configuration for batch and streaming jobs (optional).',
            ),
        ] = None,
        identity_center_configuration: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='The IAM Identity Center configuration (optional).',
            ),
        ] = None,
        next_token: Annotated[
            Optional[str],
            Field(
                description='The token for the next set of application results (optional for list-applications).',
            ),
        ] = None,
        max_results: Annotated[
            Optional[int],
            Field(
                description='The maximum number of applications that can be listed (optional for list-applications).',
            ),
        ] = None,
        states: Annotated[
            Optional[List[str]],
            Field(
                description='An optional filter for application states (optional for list-applications).',
            ),
        ] = None,
    ) -> CallToolResult:
        """Manage AWS EMR Serverless applications with comprehensive control over application lifecycle.

        This tool provides operations for managing Amazon EMR Serverless applications,
        including creating, configuring, monitoring, updating, starting, stopping, and deleting applications.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create-application, update-application,
          delete-application, start-application, and stop-application operations
        - Appropriate AWS permissions for EMR Serverless application operations

        ## Operations
        - **create-application**: Create a new EMR Serverless application
        - **get-application**: Get detailed information about a specific application
        - **update-application**: Update an existing application configuration
        - **delete-application**: Delete an application (must be in stopped or created state)
        - **list-applications**: List all EMR Serverless applications with optional filtering
        - **start-application**: Start a specified application and initialize capacity
        - **stop-application**: Stop a specified application and release capacity

        ## Example
        ```
        # Create a basic EMR Serverless Spark application
        {
            'operation': 'create-application',
            'name': 'MySparkApp',
            'release_label': 'emr-7.0.0',
            'type': 'Spark',
            'client_token': 'unique-token-123',
            'auto_start_configuration': {'enabled': True},
            'auto_stop_configuration': {'enabled': True, 'idleTimeoutMinutes': 15},
        }
        ```

        ## Usage Tips
        - Use list-applications to find application IDs before performing operations on specific applications
        - Check application state before performing operations that require specific states
        - For large result sets, use pagination with next_token parameter
        - Applications must be stopped before they can be deleted

        Args:
            ctx: MCP context
            operation: Operation to perform
            application_id: ID of the EMR Serverless application
            name: Name of the EMR Serverless application
            release_label: The Amazon EMR release associated with the application
            type: The type of application, such as Spark or Hive
            client_token: The client idempotency token
            initial_capacity: The capacity to initialize when the application is created/updated
            maximum_capacity: The maximum capacity to allocate
            tags: The tags assigned to the application
            auto_start_configuration: The configuration for automatic start
            auto_stop_configuration: The configuration for automatic stop
            network_configuration: The network configuration for VPC connectivity
            architecture: The CPU architecture of the application
            image_configuration: The image configuration for all worker types
            worker_type_specifications: The worker type specifications
            runtime_configuration: The Configuration specifications
            monitoring_configuration: The monitoring configuration
            interactive_configuration: The interactive configuration
            scheduler_configuration: The scheduler configuration
            identity_center_configuration: The IAM Identity Center configuration
            next_token: The token for pagination
            max_results: The maximum number of results
            states: Filter for application states

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'EMR Serverless Application Handler - Tool: manage_aws_emr_serverless_applications - Operation: {operation}',
            )

            if not self.allow_write and operation in [
                'create-application',
                'update-application',
                'delete-application',
                'start-application',
                'stop-application',
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return self._create_error_response(operation, error_message)

            if operation == 'create-application':
                # Check required parameters
                missing_params = []
                if name is None:
                    missing_params.append('name')
                if release_label is None:
                    missing_params.append('release_label')
                if type is None:
                    missing_params.append('type')

                if missing_params:
                    error_message = 'name, release_label, and type are required for create-application operation'
                    return self._create_error_response(operation, error_message)

                # Prepare parameters
                params: Dict[str, Any] = {
                    'name': name,
                    'releaseLabel': release_label,
                    'type': type,
                }

                if client_token is not None:
                    params['clientToken'] = client_token
                if initial_capacity is not None:
                    params['initialCapacity'] = initial_capacity
                if maximum_capacity is not None:
                    params['maximumCapacity'] = maximum_capacity
                if auto_start_configuration is not None:
                    params['autoStartConfiguration'] = auto_start_configuration
                if auto_stop_configuration is not None:
                    params['autoStopConfiguration'] = auto_stop_configuration
                if network_configuration is not None:
                    params['networkConfiguration'] = network_configuration
                if architecture is not None:
                    params['architecture'] = architecture
                if image_configuration is not None:
                    params['imageConfiguration'] = image_configuration
                if worker_type_specifications is not None:
                    params['workerTypeSpecifications'] = worker_type_specifications
                if runtime_configuration is not None:
                    params['runtimeConfiguration'] = runtime_configuration
                if monitoring_configuration is not None:
                    params['monitoringConfiguration'] = monitoring_configuration
                if interactive_configuration is not None:
                    params['interactiveConfiguration'] = interactive_configuration
                if scheduler_configuration is not None:
                    params['schedulerConfiguration'] = scheduler_configuration
                if identity_center_configuration is not None:
                    params['identityCenterConfiguration'] = identity_center_configuration

                # Add MCP management tags
                resource_tags = AwsHelper.prepare_resource_tags(
                    EMR_SERVERLESS_APPLICATION_RESOURCE_TYPE
                )
                if tags:
                    resource_tags.update(tags)
                params['tags'] = resource_tags

                # Create application
                response = self.emr_serverless_client.create_application(**params)

                success_message = f'Successfully created EMR Serverless application {response.get("name", "")} with MCP management tags'
                data = CreateApplicationData(
                    application_id=response.get('applicationId', ''),
                    name=response.get('name', ''),
                    arn=response.get('arn', ''),
                    operation='create-application',
                )

                return CallToolResult(
                    isError=False,
                    content=[
                        TextContent(type='text', text=success_message),
                        TextContent(type='text', text=json.dumps(data.model_dump())),
                    ],
                )

            elif operation == 'get-application':
                if application_id is None:
                    error_message = 'application_id is required for get-application operation'
                    return self._create_error_response(operation, error_message)

                # Get application
                response = self.emr_serverless_client.get_application(applicationId=application_id)

                success_message = (
                    f'Successfully retrieved EMR Serverless application {application_id}'
                )
                data = GetApplicationData(
                    application=response.get('application', {}),
                    operation='get-application',
                )

                return CallToolResult(
                    isError=False,
                    content=[
                        TextContent(type='text', text=success_message),
                        TextContent(type='text', text=json.dumps(data.model_dump())),
                    ],
                )

            elif operation == 'update-application':
                if application_id is None:
                    error_message = 'application_id is required for update-application operation'
                    return self._create_error_response(operation, error_message)

                # Verify that the application is managed by MCP
                verification_result = AwsHelper.verify_emr_serverless_application_managed_by_mcp(
                    self.emr_serverless_client,
                    application_id,
                    EMR_SERVERLESS_APPLICATION_RESOURCE_TYPE,
                )

                if not verification_result['is_valid']:
                    error_message = f'Cannot update application {application_id}: {verification_result["error_message"]}'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return self._create_error_response(operation, error_message)

                # Prepare parameters
                params: Dict[str, Any] = {
                    'applicationId': application_id,
                }

                if client_token is not None:
                    params['clientToken'] = client_token
                if name is not None:
                    params['name'] = name
                if initial_capacity is not None:
                    params['initialCapacity'] = initial_capacity
                if maximum_capacity is not None:
                    params['maximumCapacity'] = maximum_capacity
                if auto_start_configuration is not None:
                    params['autoStartConfiguration'] = auto_start_configuration
                if auto_stop_configuration is not None:
                    params['autoStopConfiguration'] = auto_stop_configuration
                if network_configuration is not None:
                    params['networkConfiguration'] = network_configuration
                if architecture is not None:
                    params['architecture'] = architecture
                if image_configuration is not None:
                    params['imageConfiguration'] = image_configuration
                if worker_type_specifications is not None:
                    params['workerTypeSpecifications'] = worker_type_specifications
                if interactive_configuration is not None:
                    params['interactiveConfiguration'] = interactive_configuration
                if release_label is not None:
                    params['releaseLabel'] = release_label
                if runtime_configuration is not None:
                    params['runtimeConfiguration'] = runtime_configuration
                if monitoring_configuration is not None:
                    params['monitoringConfiguration'] = monitoring_configuration
                if scheduler_configuration is not None:
                    params['schedulerConfiguration'] = scheduler_configuration
                if identity_center_configuration is not None:
                    params['identityCenterConfiguration'] = identity_center_configuration

                # Update application
                response = self.emr_serverless_client.update_application(**params)

                success_message = (
                    f'Successfully updated EMR Serverless application {application_id}'
                )
                data = UpdateApplicationData(
                    application=response.get('application', {}),
                    operation='update-application',
                )

                return CallToolResult(
                    isError=False,
                    content=[
                        TextContent(type='text', text=success_message),
                        TextContent(type='text', text=json.dumps(data.model_dump())),
                    ],
                )

            elif operation == 'delete-application':
                if application_id is None:
                    error_message = 'application_id is required for delete-application operation'
                    return self._create_error_response(operation, error_message)

                # Verify that the application is managed by MCP
                verification_result = AwsHelper.verify_emr_serverless_application_managed_by_mcp(
                    self.emr_serverless_client,
                    application_id,
                    EMR_SERVERLESS_APPLICATION_RESOURCE_TYPE,
                )

                if not verification_result['is_valid']:
                    error_message = f'Cannot delete application {application_id}: {verification_result["error_message"]}'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return self._create_error_response(operation, error_message)

                # Delete application
                self.emr_serverless_client.delete_application(applicationId=application_id)

                success_message = (
                    f'Successfully deleted EMR Serverless application {application_id}'
                )
                data = DeleteApplicationData(
                    application_id=application_id,
                    operation='delete-application',
                )

                return CallToolResult(
                    isError=False,
                    content=[
                        TextContent(type='text', text=success_message),
                        TextContent(type='text', text=json.dumps(data.model_dump())),
                    ],
                )

            elif operation == 'list-applications':
                # Prepare parameters
                params: Dict[str, Any] = {}
                if next_token is not None:
                    params['nextToken'] = next_token
                if max_results is not None:
                    params['maxResults'] = max_results
                if states is not None:
                    params['states'] = states

                # List applications
                response = self.emr_serverless_client.list_applications(**params)

                applications = response.get('applications', [])
                success_message = 'Successfully listed EMR Serverless applications'
                data = ListApplicationsData(
                    applications=applications,
                    count=len(applications),
                    next_token=response.get('nextToken'),
                    operation='list-applications',
                )

                return CallToolResult(
                    isError=False,
                    content=[
                        TextContent(type='text', text=success_message),
                        TextContent(type='text', text=json.dumps(data.model_dump())),
                    ],
                )

            elif operation == 'start-application':
                if application_id is None:
                    error_message = 'application_id is required for start-application operation'
                    return self._create_error_response(operation, error_message)

                # Verify that the application is managed by MCP
                verification_result = AwsHelper.verify_emr_serverless_application_managed_by_mcp(
                    self.emr_serverless_client,
                    application_id,
                    EMR_SERVERLESS_APPLICATION_RESOURCE_TYPE,
                )

                if not verification_result['is_valid']:
                    error_message = f'Cannot start application {application_id}: {verification_result["error_message"]}'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return self._create_error_response(operation, error_message)

                # Start application
                self.emr_serverless_client.start_application(applicationId=application_id)

                success_message = (
                    f'Successfully started EMR Serverless application {application_id}'
                )
                data = StartApplicationData(
                    application_id=application_id,
                    operation='start-application',
                )

                return CallToolResult(
                    isError=False,
                    content=[
                        TextContent(type='text', text=success_message),
                        TextContent(type='text', text=json.dumps(data.model_dump())),
                    ],
                )

            elif operation == 'stop-application':
                if application_id is None:
                    error_message = 'application_id is required for stop-application operation'
                    return self._create_error_response(operation, error_message)

                # Verify that the application is managed by MCP
                verification_result = AwsHelper.verify_emr_serverless_application_managed_by_mcp(
                    self.emr_serverless_client,
                    application_id,
                    EMR_SERVERLESS_APPLICATION_RESOURCE_TYPE,
                )

                if not verification_result['is_valid']:
                    error_message = f'Cannot stop application {application_id}: {verification_result["error_message"]}'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return self._create_error_response(operation, error_message)

                # Stop application
                self.emr_serverless_client.stop_application(applicationId=application_id)

                success_message = (
                    f'Successfully stopped EMR Serverless application {application_id}'
                )
                data = StopApplicationData(
                    application_id=application_id,
                    operation='stop-application',
                )

                return CallToolResult(
                    isError=False,
                    content=[
                        TextContent(type='text', text=success_message),
                        TextContent(type='text', text=json.dumps(data.model_dump())),
                    ],
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: create-application, get-application, update-application, delete-application, list-applications, start-application, stop-application'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return self._create_error_response('get-application', error_message)

        except ValueError as e:
            error_message = str(e)
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return self._create_error_response(operation, error_message)
        except Exception as e:
            error_message = f'Error in manage_aws_emr_serverless_applications: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return self._create_error_response(operation, error_message)
