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

"""GlueEtlJobsHandler for Data Processing MCP Server."""

import os
from awslabs.dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from awslabs.dataprocessing_mcp_server.models.glue_models import (
    CreateWorkflowResponse,
    DeleteWorkflowResponse,
    GetWorkflowResponse,
    ListWorkflowsResponse,
    StartWorkflowRunResponse,
    CreateTriggerResponse,
    DeleteTriggerResponse,
    GetTriggerResponse,
    GetTriggersResponse,
    StartTriggerResponse,
    StopTriggerResponse,
)

from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field, BaseModel
from typing import Dict, List, Optional, Tuple, Union, cast, Any
from botocore.exceptions import ClientError


class GlueWorkflowAndTriggerHandler:
    """Handler for Amazon Glue ETL Jobs operations."""

    def __init__(
        self, mcp, allow_write: bool = False, allow_sensitive_data_access: bool = False
    ):
        """Initialize the Glue ETL Jobs handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.glue_client = AwsHelper.create_boto3_client("glue")

        # Register tools
        self.mcp.tool(name="manage_aws_glue_workflows")(self.manage_aws_glue_workflows)
        self.mcp.tool(name="manage_aws_glue_triggers")(self.manage_aws_glue_triggers)

    async def manage_aws_glue_workflows(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: create-workflow, delete-workflow, get-workflow, list-workflows, start-workflow-run. Choose "get-workflow" or "list-workflows" for read-only operations when write access is disabled.',
        ),
        workflow_name: Optional[str] = Field(
            None,
            description="Name of the workflow (required for all operations except list-workflows).",
        ),
        workflow_definition: Optional[Dict[str, Any]] = Field(
            None,
            description="Workflow definition for create-workflow operation.",
        ),
        max_results: Optional[int] = Field(
            None,
            description="Maximum number of results to return for list-workflows operation.",
        ),
        next_token: Optional[str] = Field(
            None,
            description="Pagination token for list-workflows operation.",
        ),
    ) -> Union[
        CreateWorkflowResponse,
        DeleteWorkflowResponse,
        GetWorkflowResponse,
        ListWorkflowsResponse,
        StartWorkflowRunResponse,
    ]:
        """Manage AWS Glue workflows to orchestrate complex ETL activities.

        This tool allows you to create, delete, retrieve, list, and start AWS Glue workflows.
        Workflows help you design and visualize complex ETL activities as a series of dependent
        jobs and crawlers, making it easier to manage and monitor your data processing pipelines.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create-workflow, delete-workflow, and start-workflow-run operations
        - Appropriate AWS permissions for Glue workflow operations

        ## Operations
        - **create-workflow**: Create a new workflow with optional description, default run properties, tags, and max concurrent runs
        - **delete-workflow**: Delete an existing workflow by name
        - **get-workflow**: Retrieve detailed information about a specific workflow with optional graph inclusion
        - **list-workflows**: List all workflows with pagination support
        - **start-workflow-run**: Start a workflow run with optional run properties

        ## Example
        ```python
        # Create a new workflow
        manage_aws_glue_workflows(
            operation="create-workflow",
            workflow_name="my-etl-workflow",
            workflow_definition={
                "Description": "ETL workflow for daily data processing",
                "DefaultRunProperties": {"ENV": "production"},
                "MaxConcurrentRuns": 1
            }
        )

        # Start a workflow run
        manage_aws_glue_workflows(
            operation="start-workflow-run",
            workflow_name="my-etl-workflow",
            workflow_definition={
                "run_properties": {"EXECUTION_DATE": "2023-06-19"}
            }
        )
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            workflow_name: Name of the workflow
            workflow_definition: Workflow definition for create-workflow operation
            max_results: Maximum number of results to return for list-workflows operation
            next_token: Pagination token for list-workflows operation

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            if not self.allow_write and operation not in [
                "get-workflow",
                "list-workflows",
            ]:
                error_message = (
                    f"Operation {operation} is not allowed without write access"
                )
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                if operation == "create-workflow":
                    return CreateWorkflowResponse(
                        isError=True,
                        content=[TextContent(type="text", text=error_message)],
                        workflow_name="",
                    )
                elif operation == "delete-workflow":
                    return DeleteWorkflowResponse(
                        isError=True,
                        content=[TextContent(type="text", text=error_message)],
                        workflow_name="",
                    )
                elif operation == "start-workflow-run":
                    return StartWorkflowRunResponse(
                        isError=True,
                        content=[TextContent(type="text", text=error_message)],
                        workflow_name="",
                        run_id="",
                    )

            if operation == "create-workflow":
                if workflow_name is None or workflow_definition is None:
                    raise ValueError(
                        "workflow_name and workflow_definition are required for create-workflow operation"
                    )

                # Create the workflow
                # Extract specific parameters from workflow_definition
                params = {}
                if "Description" in workflow_definition:
                    params["Description"] = workflow_definition.get("Description")
                if "DefaultRunProperties" in workflow_definition:
                    params["DefaultRunProperties"] = workflow_definition.get(
                        "DefaultRunProperties"
                    )

                # Add MCP management tags
                resource_tags = AwsHelper.prepare_resource_tags("GlueWorkflow")

                # Merge user-provided tags with MCP tags
                if "Tags" in workflow_definition:
                    user_tags = workflow_definition.get("Tags", {})
                    merged_tags = user_tags.copy()
                    merged_tags.update(resource_tags)
                    params["Tags"] = merged_tags
                else:
                    params["Tags"] = resource_tags

                if "MaxConcurrentRuns" in workflow_definition:
                    params["MaxConcurrentRuns"] = workflow_definition.get(
                        "MaxConcurrentRuns"
                    )

                response = self.glue_client.create_workflow(
                    Name=workflow_name, **params
                )

                return CreateWorkflowResponse(
                    isError=False,
                    content=cast(
                        List[TextContent],
                        [
                            TextContent(
                                type="text",
                                text=f"Successfully created workflow {workflow_name}",
                            )
                        ],
                    ),
                    workflow_name=workflow_name,
                )

            elif operation == "delete-workflow":
                if workflow_name is None:
                    raise ValueError(
                        "workflow_name is required for delete-workflow operation"
                    )

                # First check if the workflow is managed by MCP
                try:
                    # Get the workflow to check if it's managed by MCP
                    response = self.glue_client.get_workflow(Name=workflow_name)
                    workflow = response.get("Workflow", {})
                    tags = workflow.get("Tags", {})

                    # Construct the ARN for the workflow
                    region = AwsHelper.get_aws_region() or "us-east-1"
                    account_id = AwsHelper.get_aws_account_id()
                    workflow_arn = (
                        f"arn:aws:glue:{region}:{account_id}:workflow/{workflow_name}"
                    )

                    # Check if the workflow is managed by MCP
                    if not AwsHelper.is_resource_mcp_managed(
                        self.glue_client, workflow_arn, {}
                    ):
                        error_message = f"Cannot delete workflow {workflow_name} - it is not managed by the MCP server (missing required tags)"
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return DeleteWorkflowResponse(
                            isError=True,
                            content=[TextContent(type="text", text=error_message)],
                            workflow_name=workflow_name,
                        )
                except ClientError as e:
                    if e.response["Error"]["Code"] == "EntityNotFoundException":
                        error_message = f"Workflow {workflow_name} not found"
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return DeleteWorkflowResponse(
                            isError=True,
                            content=[TextContent(type="text", text=error_message)],
                            workflow_name=workflow_name,
                        )
                    else:
                        raise e

                # Delete the workflow
                self.glue_client.delete_workflow(Name=workflow_name)

                return DeleteWorkflowResponse(
                    isError=False,
                    content=cast(
                        List[TextContent],
                        [
                            TextContent(
                                type="text",
                                text=f"Successfully deleted workflow {workflow_name}",
                            )
                        ],
                    ),
                    workflow_name=workflow_name,
                )

            elif operation == "get-workflow":
                if workflow_name is None:
                    raise ValueError(
                        "workflow_name is required for get-workflow operation"
                    )

                # Get the workflow
                params = {"Name": workflow_name}

                # Add optional parameter
                if (
                    workflow_definition is not None
                    and isinstance(workflow_definition, dict)
                    and "include_graph" in workflow_definition
                    and workflow_definition["include_graph"]
                ):
                    params["IncludeGraph"] = workflow_definition["include_graph"]

                response = self.glue_client.get_workflow(**params)

                return GetWorkflowResponse(
                    isError=False,
                    content=cast(
                        List[TextContent],
                        [
                            TextContent(
                                type="text",
                                text=f"Successfully retrieved workflow {workflow_name}",
                            )
                        ],
                    ),
                    workflow_name=workflow_name,
                    workflow_details=response.get("Workflow", {}),
                )

            elif operation == "list-workflows":
                # Prepare parameters
                params: Dict[str, Any] = {}
                if max_results is not None:
                    params["MaxResults"] = max_results
                if next_token is not None:
                    params["NextToken"] = next_token

                # Get workflows
                response = self.glue_client.list_workflows(**params)
                
                # Convert workflow names to dictionary format
                workflow_names = response.get("Workflows", [])
                workflows = [{"Name": name} for name in workflow_names]

                return ListWorkflowsResponse(
                    isError=False,
                    content=cast(
                        List[TextContent],
                        [
                            TextContent(
                                type="text", text="Successfully retrieved workflows"
                            )
                        ],
                    ),
                    workflows=workflows,
                    next_token=response.get("NextToken"),
                )

            elif operation == "start-workflow-run":
                if workflow_name is None:
                    raise ValueError(
                        "workflow_name is required for start-workflow-run operation"
                    )

                # First check if the workflow is managed by MCP
                try:
                    # Get the workflow to check if it's managed by MCP
                    response = self.glue_client.get_workflow(Name=workflow_name)
                    workflow = response.get("Workflow", {})
                    tags = workflow.get("Tags", {})

                    # Construct the ARN for the workflow
                    region = AwsHelper.get_aws_region() or "us-east-1"
                    account_id = AwsHelper.get_aws_account_id()
                    workflow_arn = (
                        f"arn:aws:glue:{region}:{account_id}:workflow/{workflow_name}"
                    )

                    # Check if the workflow is managed by MCP
                    if not AwsHelper.is_resource_mcp_managed(
                        self.glue_client, workflow_arn, {}
                    ):
                        error_message = f"Cannot start workflow run for {workflow_name} - it is not managed by the MCP server (missing required tags)"
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return StartWorkflowRunResponse(
                            isError=True,
                            content=[TextContent(type="text", text=error_message)],
                            workflow_name=workflow_name,
                            run_id="",
                        )
                except ClientError as e:
                    if e.response["Error"]["Code"] == "EntityNotFoundException":
                        error_message = f"Workflow {workflow_name} not found"
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return StartWorkflowRunResponse(
                            isError=True,
                            content=[TextContent(type="text", text=error_message)],
                            workflow_name=workflow_name,
                            run_id="",
                        )
                    else:
                        raise e

                # Start workflow run
                params = {"Name": workflow_name}

                # Add optional run properties if provided
                if (
                    workflow_definition is not None
                    and isinstance(workflow_definition, dict)
                    and "run_properties" in workflow_definition
                    and workflow_definition["run_properties"]
                ):
                    params["RunProperties"] = workflow_definition["run_properties"]

                response = self.glue_client.start_workflow_run(**params)

                return StartWorkflowRunResponse(
                    isError=False,
                    content=cast(
                        List[TextContent],
                        [
                            TextContent(
                                type="text",
                                text=f"Successfully started workflow run for {workflow_name}",
                            )
                        ],
                    ),
                    workflow_name=workflow_name,
                    run_id=response.get("RunId", ""),
                )

            else:
                error_message = f"Invalid operation: {operation}. Must be one of: create-workflow, delete-workflow, get-workflow, list-workflows, start-workflow-run"
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetWorkflowResponse(
                    isError=True,
                    content=cast(
                        List[TextContent],
                        [TextContent(type="text", text=error_message)],
                    ),
                    workflow_name=workflow_name or "",
                    workflow_details={},
                )

        except ValueError as e:
            log_with_request_id(
                ctx, LogLevel.ERROR, f"Parameter validation error: {str(e)}"
            )
            raise
        except Exception as e:
            error_message = f"Error in manage_aws_glue_workflows: {str(e)}"
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetWorkflowResponse(
                isError=True,
                content=cast(
                    List[TextContent],
                    [TextContent(type="text", text=error_message)],
                ),
                workflow_name=workflow_name or "",
                workflow_details={},
            )

    async def manage_aws_glue_triggers(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: create-trigger, delete-trigger, get-trigger, get-triggers, start-trigger, stop-trigger. Choose "get-trigger" or "get-triggers" for read-only operations when write access is disabled.',
        ),
        trigger_name: Optional[str] = Field(
            None,
            description="Name of the trigger (required for all operations except get-triggers).",
        ),
        trigger_definition: Optional[Dict[str, Any]] = Field(
            None,
            description="Trigger definition for create-trigger operation.",
        ),
        max_results: Optional[int] = Field(
            None,
            description="Maximum number of results to return for get-triggers operation.",
        ),
        next_token: Optional[str] = Field(
            None,
            description="Pagination token for get-triggers operation.",
        ),
    ) -> Union[
        CreateTriggerResponse,
        DeleteTriggerResponse,
        GetTriggerResponse,
        GetTriggersResponse,
        StartTriggerResponse,
        StopTriggerResponse,
    ]:
        """Manage AWS Glue triggers to automate workflow and job execution.

        This tool allows you to create, delete, retrieve, list, start, and stop AWS Glue triggers.
        Triggers define the conditions that automatically start jobs or workflows, enabling
        scheduled or event-based execution of your ETL processes.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create-trigger, delete-trigger, start-trigger, and stop-trigger operations
        - Appropriate AWS permissions for Glue trigger operations

        ## Operations
        - **create-trigger**: Create a new trigger with specified type (SCHEDULED, CONDITIONAL, ON_DEMAND, EVENT) and actions
        - **delete-trigger**: Delete an existing trigger by name
        - **get-trigger**: Retrieve detailed information about a specific trigger
        - **get-triggers**: List all triggers with pagination support
        - **start-trigger**: Activate a trigger to begin monitoring for its firing conditions
        - **stop-trigger**: Deactivate a trigger to pause its monitoring

        ## Trigger Types
        - **SCHEDULED**: Time-based triggers that run on a cron schedule
        - **CONDITIONAL**: Event-based triggers that run when specified conditions are met
        - **ON_DEMAND**: Manually activated triggers
        - **EVENT**: EventBridge event-based triggers

        ## Example
        ```python
        # Create a scheduled trigger
        manage_aws_glue_triggers(
            operation="create-trigger",
            trigger_name="daily-etl-trigger",
            trigger_definition={
                "Type": "SCHEDULED",
                "Schedule": "cron(0 12 * * ? *)",  # Run daily at 12:00 UTC
                "Actions": [
                    {
                        "JobName": "process-daily-data"
                    }
                ],
                "Description": "Trigger for daily ETL job",
                "StartOnCreation": True
            }
        )

        # Create a conditional trigger
        manage_aws_glue_triggers(
            operation="create-trigger",
            trigger_name="data-arrival-trigger",
            trigger_definition={
                "Type": "CONDITIONAL",
                "Actions": [
                    {
                        "JobName": "process-new-data"
                    }
                ],
                "Predicate": {
                    "Conditions": [
                        {
                            "LogicalOperator": "EQUALS",
                            "JobName": "crawl-new-data",
                            "State": "SUCCEEDED"
                        }
                    ]
                },
                "Description": "Trigger that runs when data crawling completes"
            }
        )
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            trigger_name: Name of the trigger
            trigger_definition: Trigger definition for create-trigger operation
            max_results: Maximum number of results to return for get-triggers operation
            next_token: Pagination token for get-triggers operation

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            if not self.allow_write and operation not in [
                "get-trigger",
                "get-triggers",
            ]:
                error_message = (
                    f"Operation {operation} is not allowed without write access"
                )
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                if operation == "create-trigger":
                    return CreateTriggerResponse(
                        isError=True,
                        content=cast(
                            List[TextContent],
                            [TextContent(type="text", text=error_message)],
                        ),
                        trigger_name="",
                    )
                elif operation == "delete-trigger":
                    return DeleteTriggerResponse(
                        isError=True,
                        content=cast(
                            List[TextContent],
                            [TextContent(type="text", text=error_message)],
                        ),
                        trigger_name="",
                    )
                elif operation == "start-trigger":
                    return StartTriggerResponse(
                        isError=True,
                        content=cast(
                            List[TextContent],
                            [TextContent(type="text", text=error_message)],
                        ),
                        trigger_name="",
                    )
                elif operation == "stop-trigger":
                    return StopTriggerResponse(
                        isError=True,
                        content=cast(
                            List[TextContent],
                            [TextContent(type="text", text=error_message)],
                        ),
                        trigger_name="",
                    )
                else:
                    return GetTriggerResponse(
                        isError=True,
                        content=cast(
                            List[TextContent],
                            [TextContent(type="text", text=error_message)],
                        ),
                        trigger_name="",
                        trigger_details={},
                    )

            if operation == "create-trigger":
                if trigger_name is None or trigger_definition is None:
                    raise ValueError(
                        "trigger_name and trigger_definition are required for create-trigger operation"
                    )

                # Create the trigger
                # Extract specific parameters from trigger_definition
                params = {
                    "Name": trigger_name,
                    "Type": trigger_definition.get("Type"),
                    "Actions": trigger_definition.get("Actions"),
                }

                # Add optional parameters if provided
                if "WorkflowName" in trigger_definition:
                    params["WorkflowName"] = trigger_definition.get("WorkflowName")
                if "Schedule" in trigger_definition:
                    params["Schedule"] = trigger_definition.get("Schedule")
                if "Predicate" in trigger_definition:
                    params["Predicate"] = trigger_definition.get("Predicate")
                if "Description" in trigger_definition:
                    params["Description"] = trigger_definition.get("Description")
                if "StartOnCreation" in trigger_definition:
                    params["StartOnCreation"] = trigger_definition.get(
                        "StartOnCreation"
                    )

                # Add MCP management tags
                resource_tags = AwsHelper.prepare_resource_tags("GlueTrigger")

                # Merge user-provided tags with MCP tags
                if "Tags" in trigger_definition:
                    user_tags = trigger_definition.get("Tags", {})
                    merged_tags = user_tags.copy()
                    merged_tags.update(resource_tags)
                    params["Tags"] = merged_tags
                else:
                    params["Tags"] = resource_tags

                if "EventBatchingCondition" in trigger_definition:
                    params["EventBatchingCondition"] = trigger_definition.get(
                        "EventBatchingCondition"
                    )

                response = self.glue_client.create_trigger(**params)

                return CreateTriggerResponse(
                    isError=False,
                    content=cast(
                        List[TextContent],
                        [
                            TextContent(
                                type="text",
                                text=f"Successfully created trigger {trigger_name}",
                            )
                        ],
                    ),
                    trigger_name=trigger_name,
                )

            elif operation == "delete-trigger":
                if trigger_name is None:
                    raise ValueError(
                        "trigger_name is required for delete-trigger operation"
                    )

                # First check if the trigger is managed by MCP
                try:
                    # Get the trigger to check if it's managed by MCP
                    response = self.glue_client.get_trigger(Name=trigger_name)
                    trigger = response.get("Trigger", {})
                    tags = trigger.get("Tags", {})

                    # Construct the ARN for the trigger
                    region = AwsHelper.get_aws_region() or "us-east-1"
                    account_id = AwsHelper.get_aws_account_id()
                    trigger_arn = (
                        f"arn:aws:glue:{region}:{account_id}:trigger/{trigger_name}"
                    )

                    # Check if the trigger is managed by MCP
                    if not AwsHelper.is_resource_mcp_managed(
                        self.glue_client, trigger_arn, {}
                    ):
                        error_message = f"Cannot delete trigger {trigger_name} - it is not managed by the MCP server (missing required tags)"
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return DeleteTriggerResponse(
                            isError=True,
                            content=[TextContent(type="text", text=error_message)],
                            trigger_name=trigger_name,
                        )
                except ClientError as e:
                    if e.response["Error"]["Code"] == "EntityNotFoundException":
                        error_message = f"Trigger {trigger_name} not found"
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return DeleteTriggerResponse(
                            isError=True,
                            content=[TextContent(type="text", text=error_message)],
                            trigger_name=trigger_name,
                        )
                    else:
                        raise e

                # Delete the trigger
                self.glue_client.delete_trigger(Name=trigger_name)

                return DeleteTriggerResponse(
                    isError=False,
                    content=cast(
                        List[TextContent],
                        [
                            TextContent(
                                type="text",
                                text=f"Successfully deleted trigger {trigger_name}",
                            )
                        ],
                    ),
                    trigger_name=trigger_name,
                )

            elif operation == "get-trigger":
                if trigger_name is None:
                    raise ValueError(
                        "trigger_name is required for get-trigger operation"
                    )

                # Get the trigger
                params = {"Name": trigger_name}

                response = self.glue_client.get_trigger(**params)

                return GetTriggerResponse(
                    isError=False,
                    content=cast(
                        List[TextContent],
                        [
                            TextContent(
                                type="text",
                                text=f"Successfully retrieved trigger {trigger_name}",
                            )
                        ],
                    ),
                    trigger_name=trigger_name,
                    trigger_details=response.get("Trigger", {}),
                )

            elif operation == "get-triggers":
                # Prepare parameters
                params: Dict[str, Any] = {}
                if max_results is not None:
                    params["MaxResults"] = max_results
                if next_token is not None:
                    params["NextToken"] = next_token

                # Get triggers
                response = self.glue_client.get_triggers(**params)

                return GetTriggersResponse(
                    isError=False,
                    content=cast(
                        List[TextContent],
                        [
                            TextContent(
                                type="text", text="Successfully retrieved triggers"
                            )
                        ],
                    ),
                    triggers=response.get("Triggers", []),
                    next_token=response.get("NextToken"),
                )

            elif operation == "start-trigger":
                if trigger_name is None:
                    raise ValueError(
                        "trigger_name is required for start-trigger operation"
                    )

                # First check if the trigger is managed by MCP
                try:
                    # Get the trigger to check if it's managed by MCP
                    response = self.glue_client.get_trigger(Name=trigger_name)
                    trigger = response.get("Trigger", {})
                    tags = trigger.get("Tags", {})

                    # Construct the ARN for the trigger
                    region = AwsHelper.get_aws_region() or "us-east-1"
                    account_id = AwsHelper.get_aws_account_id()
                    trigger_arn = (
                        f"arn:aws:glue:{region}:{account_id}:trigger/{trigger_name}"
                    )

                    # Check if the trigger is managed by MCP
                    if not AwsHelper.is_resource_mcp_managed(
                        self.glue_client, trigger_arn, {}
                    ):
                        error_message = f"Cannot start trigger {trigger_name} - it is not managed by the MCP server (missing required tags)"
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return StartTriggerResponse(
                            isError=True,
                            content=[TextContent(type="text", text=error_message)],
                            trigger_name=trigger_name,
                        )
                except ClientError as e:
                    if e.response["Error"]["Code"] == "EntityNotFoundException":
                        error_message = f"Trigger {trigger_name} not found"
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return StartTriggerResponse(
                            isError=True,
                            content=[TextContent(type="text", text=error_message)],
                            trigger_name=trigger_name,
                        )
                    else:
                        raise e

                # Start trigger
                self.glue_client.start_trigger(Name=trigger_name)

                return StartTriggerResponse(
                    isError=False,
                    content=cast(
                        List[TextContent],
                        [
                            TextContent(
                                type="text",
                                text=f"Successfully started trigger {trigger_name}",
                            )
                        ],
                    ),
                    trigger_name=trigger_name,
                )

            elif operation == "stop-trigger":
                if trigger_name is None:
                    raise ValueError(
                        "trigger_name is required for stop-trigger operation"
                    )

                # First check if the trigger is managed by MCP
                try:
                    # Get the trigger to check if it's managed by MCP
                    response = self.glue_client.get_trigger(Name=trigger_name)
                    trigger = response.get("Trigger", {})
                    tags = trigger.get("Tags", {})

                    # Construct the ARN for the trigger
                    region = AwsHelper.get_aws_region() or "us-east-1"
                    account_id = AwsHelper.get_aws_account_id()
                    trigger_arn = (
                        f"arn:aws:glue:{region}:{account_id}:trigger/{trigger_name}"
                    )

                    # Check if the trigger is managed by MCP
                    if not AwsHelper.is_resource_mcp_managed(
                        self.glue_client, trigger_arn, {}
                    ):
                        error_message = f"Cannot stop trigger {trigger_name} - it is not managed by the MCP server (missing required tags)"
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return StopTriggerResponse(
                            isError=True,
                            content=[TextContent(type="text", text=error_message)],
                            trigger_name=trigger_name,
                        )
                except ClientError as e:
                    if e.response["Error"]["Code"] == "EntityNotFoundException":
                        error_message = f"Trigger {trigger_name} not found"
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return StopTriggerResponse(
                            isError=True,
                            content=[TextContent(type="text", text=error_message)],
                            trigger_name=trigger_name,
                        )
                    else:
                        raise e

                # Stop trigger
                self.glue_client.stop_trigger(Name=trigger_name)

                return StopTriggerResponse(
                    isError=False,
                    content=cast(
                        List[TextContent],
                        [
                            TextContent(
                                type="text",
                                text=f"Successfully stopped trigger {trigger_name}",
                            )
                        ],
                    ),
                    trigger_name=trigger_name,
                )

            else:
                error_message = f"Invalid operation: {operation}. Must be one of: create-trigger, delete-trigger, get-trigger, get-triggers, start-trigger, stop-trigger"
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetTriggerResponse(
                    isError=True,
                    content=cast(
                        List[TextContent],
                        [TextContent(type="text", text=error_message)],
                    ),
                    trigger_name=trigger_name or "",
                    trigger_details={},
                )

        except ValueError as e:
            log_with_request_id(
                ctx, LogLevel.ERROR, f"Parameter validation error: {str(e)}"
            )
            raise
        except Exception as e:
            error_message = f"Error in manage_aws_glue_triggers: {str(e)}"
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetTriggerResponse(
                isError=True,
                content=cast(
                    List[TextContent],
                    [TextContent(type="text", text=error_message)],
                ),
                trigger_name=trigger_name or "",
                trigger_details={},
            )
