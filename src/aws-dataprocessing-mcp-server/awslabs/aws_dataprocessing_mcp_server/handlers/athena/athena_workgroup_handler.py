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

from awslabs.aws_dataprocessing_mcp_server.models.athena_models import (
    CreateWorkGroupResponse,
    DeleteWorkGroupResponse,
    GetWorkGroupResponse,
    ListWorkGroupsResponse,
    UpdateWorkGroupResponse,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Any, Dict, Optional, Union


class AthenaWorkGroupHandler:
    """Handler for Amazon Athena WorkGroup operations."""

    def __init__(self, mcp, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the Athena WorkGroup handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.athena_client = AwsHelper.create_boto3_client('athena')

        # Register tools
        self.mcp.tool(name='manage_aws_athena_workgroups')(self.manage_aws_athena_workgroups)

    async def manage_aws_athena_workgroups(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: create-work-group, delete-work-group, get-work-group, list-work-groups, update-work-group. Choose read-only operations when write access is disabled.',
        ),
        name: Optional[str] = Field(
            None,
            description='Name of the workgroup (required for create-work-group, delete-work-group, get-work-group, update-work-group).',
        ),
        description: Optional[str] = Field(
            None,
            description='Description of the workgroup (optional for create-work-group and update-work-group).',
        ),
        configuration: Optional[Dict[str, Any]] = Field(
            None,
            description='Configuration for the workgroup, including result configuration, enforcement options, etc. (optional for create-work-group and update-work-group).',
        ),
        state: Optional[str] = Field(
            None,
            description='State of the workgroup: ENABLED or DISABLED (optional for create-work-group and update-work-group).',
        ),
        tags: Optional[Dict[str, str]] = Field(
            None,
            description="Tags for the workgroup (optional for create-work-group). Example {'ResourceType': 'Workgroup'}",
        ),
        recursive_delete_option: Optional[bool] = Field(
            None,
            description='Whether to recursively delete the workgroup and its contents (optional for delete-work-group).',
        ),
        max_results: Optional[int] = Field(
            None,
            description='Maximum number of results to return for list-work-groups operation.',
        ),
        next_token: Optional[str] = Field(
            None,
            description='Pagination token for list-work-groups operation.',
        ),
    ) -> Union[
        CreateWorkGroupResponse,
        DeleteWorkGroupResponse,
        GetWorkGroupResponse,
        ListWorkGroupsResponse,
        UpdateWorkGroupResponse,
    ]:
        """Manage AWS Athena workgroups with both read and write operations.

        This tool provides operations for managing Athena workgroups, including creating,
        retrieving, listing, updating, and deleting workgroups. Workgroups allow you to
        isolate queries for different user groups and control query execution settings.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create-work-group, delete-work-group, and update-work-group operations
        - Appropriate AWS permissions for Athena workgroup operations

        ## Operations
        - **create-work-group**: Create a new workgroup
        - **delete-work-group**: Delete an existing workgroup
        - **get-work-group**: Get information about a single workgroup
        - **list-work-groups**: List all workgroups
        - **update-work-group**: Update an existing workgroup

        ## Usage Tips
        - Use workgroups to isolate different user groups and control costs
        - Configure workgroup settings to enforce query limits and output locations
        - Use tags to organize and track workgroups

        Args:
            ctx: MCP context
            operation: Operation to perform
            name: Name of the workgroup
            description: Description of the workgroup
            configuration: Configuration for the workgroup
            state: State of the workgroup (ENABLED or DISABLED)
            tags: Tags for the workgroup
            recursive_delete_option: Whether to recursively delete the workgroup
            max_results: Maximum number of results to return
            next_token: Pagination token

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            if not self.allow_write and operation in [
                'create-work-group',
                'delete-work-group',
                'update-work-group',
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                if operation == 'create-work-group':
                    return CreateWorkGroupResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        work_group_name='',
                        operation='create-work-group',
                    )
                elif operation == 'delete-work-group':
                    return DeleteWorkGroupResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        work_group_name='',
                        operation='delete-work-group',
                    )
                elif operation == 'update-work-group':
                    return UpdateWorkGroupResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        work_group_name='',
                        operation='update-work-group',
                    )

            if operation == 'create-work-group':
                if name is None:
                    raise ValueError('name is required for create-work-group operation')

                # Prepare parameters
                params = {'Name': name}

                if description is not None:
                    params['Description'] = description

                if configuration is not None:
                    params['Configuration'] = configuration

                if state is not None:
                    params['State'] = state

                # Add MCP management tags
                resource_tags = AwsHelper.prepare_resource_tags('AthenaWorkgroup', tags)
                aws_tags = AwsHelper.convert_tags_to_aws_format(resource_tags)
                params['Tags'] = aws_tags

                # Create workgroup
                self.athena_client.create_work_group(**params)

                return CreateWorkGroupResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully created Athena workgroup {name} with MCP management tags',
                        )
                    ],
                    work_group_name=name,
                    operation='create-work-group',
                )

            elif operation == 'delete-work-group':
                if name is None:
                    raise ValueError('name is required for delete-work-group operation')

                # Verify that the workgroup is managed by MCP before deleting
                workgroup_tags = AwsHelper.get_resource_tags_athena_workgroup(
                    self.athena_client, name
                )
                if not AwsHelper.verify_resource_managed_by_mcp(workgroup_tags):
                    error_message = f'Cannot delete workgroup {name} - it is not managed by the MCP server (missing required tags)'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return DeleteWorkGroupResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        work_group_name=name,
                        operation='delete-work-group',
                    )

                # Prepare parameters
                params = {'WorkGroup': name}

                if recursive_delete_option is not None:
                    params['RecursiveDeleteOption'] = recursive_delete_option

                # Delete workgroup
                self.athena_client.delete_work_group(**params)

                return DeleteWorkGroupResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully deleted MCP-managed Athena workgroup {name}',
                        )
                    ],
                    work_group_name=name,
                    operation='delete-work-group',
                )

            elif operation == 'get-work-group':
                if name is None:
                    raise ValueError('name is required for get-work-group operation')

                # Get workgroup
                response = self.athena_client.get_work_group(WorkGroup=name)

                return GetWorkGroupResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully retrieved workgroup {name}',
                        )
                    ],
                    work_group=response.get('WorkGroup', {}),
                    operation='get-work-group',
                )

            elif operation == 'list-work-groups':
                # Prepare parameters
                params: Dict[str, Any] = {}
                if max_results is not None:
                    params['MaxResults'] = max_results
                if next_token is not None:
                    params['NextToken'] = next_token

                # List workgroups
                response = self.athena_client.list_work_groups(**params)

                work_groups = response.get('WorkGroups', [])
                return ListWorkGroupsResponse(
                    isError=False,
                    content=[TextContent(type='text', text='Successfully listed workgroups')],
                    work_groups=work_groups,
                    count=len(work_groups),
                    next_token=response.get('NextToken'),
                    operation='list-work-groups',
                )

            elif operation == 'update-work-group':
                if name is None:
                    raise ValueError('name is required for update-work-group operation')

                # Verify that the workgroup is managed by MCP before deleting
                workgroup_tags = AwsHelper.get_resource_tags_athena_workgroup(
                    self.athena_client, name
                )
                if not AwsHelper.verify_resource_managed_by_mcp(workgroup_tags):
                    error_message = f'Cannot update workgroup {name} - it is not managed by the MCP server (missing required tags)'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return UpdateWorkGroupResponse(
                        isError=True,
                        content=[
                            TextContent(
                                type='text',
                                text=error_message,
                            )
                        ],
                        work_group_name=name,
                        operation='update-work-group',
                    )

                # Prepare parameters
                params = {'WorkGroup': name}

                if description is not None:
                    params['Description'] = description

                if configuration is not None:
                    params['ConfigurationUpdates'] = configuration

                if state is not None:
                    params['State'] = state

                # Update workgroup
                self.athena_client.update_work_group(**params)

                return UpdateWorkGroupResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully updated workgroup {name}',
                        )
                    ],
                    work_group_name=name,
                    operation='update-work-group',
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: create-work-group, delete-work-group, get-work-group, list-work-groups, update-work-group'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetWorkGroupResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    work_group={},
                    operation='get-work-group',
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_athena_workgroups: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetWorkGroupResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                work_group={},
                operation='get-work-group',
            )
