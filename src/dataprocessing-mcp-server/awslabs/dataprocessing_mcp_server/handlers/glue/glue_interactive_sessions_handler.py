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

"""GlueInteractiveSessionsHandler for Data Processing MCP Server."""

import os
from awslabs.dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from awslabs.dataprocessing_mcp_server.models.glue_models import (
    CreateSessionResponse,
    DeleteSessionResponse,
    GetSessionResponse,
    ListSessionsResponse,
    StopSessionResponse,
    RunStatementResponse,
    CancelStatementResponse,
    GetStatementResponse,
    ListStatementsResponse,
)

from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field, BaseModel
from typing import Dict, List, Optional, Tuple, Union, cast, Any
from botocore.exceptions import ClientError


class GlueInteractiveSessionsHandler:
    """Handler for Amazon Glue Interactive Sessions operations."""

    def __init__(
        self, mcp, allow_write: bool = False, allow_sensitive_data_access: bool = False
    ):
        """Initialize the Glue Interactive Sessions handler.

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
        self.mcp.tool(name="manage_aws_glue_sessions")(self.manage_aws_glue_sessions)
        self.mcp.tool(name="manage_aws_glue_statements")(
            self.manage_aws_glue_statements
        )

    async def manage_aws_glue_sessions(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: create-session, delete-session, get-session, list-sessions, stop-session. Choose "get-session" or "list-sessions" for read-only operations when write access is disabled.',
        ),
        session_id: Optional[str] = Field(
            None,
            description="ID of the session (required for delete-session, get-session, and stop-session operations).",
        ),
        description: Optional[str] = Field(
            None,
            description="Description of the session (optional for create-session operation).",
        ),
        role: Optional[str] = Field(
            None,
            description="IAM Role ARN (required for create-session operation).",
        ),
        command: Optional[Dict[str, str]] = Field(
            None,
            description="Session command with Name (e.g., 'glueetl', 'gluestreaming') and optional PythonVersion (required for create-session operation).",
        ),
        timeout: Optional[int] = Field(
            None,
            description="Number of minutes before session times out (optional for create-session operation).",
        ),
        idle_timeout: Optional[int] = Field(
            None,
            description="Number of minutes when idle before session times out (optional for create-session operation).",
        ),
        default_arguments: Optional[Dict[str, str]] = Field(
            None,
            description="Map of key-value pairs for session arguments (optional for create-session operation).",
        ),
        connections: Optional[Dict[str, List[str]]] = Field(
            None,
            description="Connections to use for the session (optional for create-session operation).",
        ),
        max_capacity: Optional[float] = Field(
            None,
            description="Number of Glue data processing units (DPUs) to allocate (optional for create-session operation).",
        ),
        number_of_workers: Optional[int] = Field(
            None,
            description="Number of workers to use for the session (optional for create-session operation).",
        ),
        worker_type: Optional[str] = Field(
            None,
            description="Type of predefined worker (G.1X, G.2X, G.4X, G.8X, Z.2X) (optional for create-session operation).",
        ),
        security_configuration: Optional[str] = Field(
            None,
            description="Name of the SecurityConfiguration structure (optional for create-session operation).",
        ),
        glue_version: Optional[str] = Field(
            None,
            description="Glue version to use (must be greater than 2.0) (optional for create-session operation).",
        ),
        tags: Optional[Dict[str, str]] = Field(
            None,
            description="Map of key-value pairs (tags) for the session (optional for create-session operation).",
        ),
        request_origin: Optional[str] = Field(
            None,
            description="Origin of the request (optional for all operations).",
        ),
        max_results: Optional[int] = Field(
            None,
            description="Maximum number of results to return for list-sessions operation.",
        ),
        next_token: Optional[str] = Field(
            None,
            description="Pagination token for list-sessions operation.",
        ),
    ) -> Union[
        CreateSessionResponse,
        DeleteSessionResponse,
        GetSessionResponse,
        ListSessionsResponse,
        StopSessionResponse,
    ]:
        """Manage AWS Glue Interactive Sessions for running Spark and Ray workloads.

        This tool provides operations for creating and managing Glue Interactive Sessions, which
        enable interactive development and execution of Spark ETL scripts and Ray applications.
        Interactive sessions provide a responsive environment for data exploration, debugging,
        and iterative development.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create-session, delete-session, and stop-session operations
        - Appropriate AWS permissions for Glue Interactive Session operations

        ## Operations
        - **create-session**: Create a new interactive session with specified configuration
        - **delete-session**: Delete an existing interactive session
        - **get-session**: Retrieve detailed information about a specific session
        - **list-sessions**: List all interactive sessions with optional filtering
        - **stop-session**: Stop a running interactive session

        ## Example
        ```python
        # Create a new Spark ETL session
        {
          "operation": "create-session",
          "session_id": "my-spark-session",
          "role": "arn:aws:iam::123456789012:role/GlueInteractiveSessionRole",
          "command": {
            "Name": "glueetl",
            "PythonVersion": "3"
          },
          "glue_version": "3.0"
        }
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            session_id: ID of the session
            description: Description of the session
            role: IAM Role ARN
            command: Session command configuration
            timeout: Number of minutes before session times out
            idle_timeout: Number of minutes when idle before session times out
            default_arguments: Map of key-value pairs for session arguments
            connections: Connections to use for the session
            max_capacity: Number of Glue DPUs to allocate
            number_of_workers: Number of workers to use
            worker_type: Type of predefined worker
            security_configuration: Name of the SecurityConfiguration structure
            glue_version: Glue version to use
            tags: Map of key-value pairs (tags) for the session
            request_origin: Origin of the request
            max_results: Maximum number of results to return
            next_token: Pagination token

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            if not self.allow_write and operation not in [
                "get-session",
                "list-sessions",
            ]:
                error_message = (
                    f"Operation {operation} is not allowed without write access"
                )
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                if operation == "create-session":
                    return CreateSessionResponse(
                        isError=True,
                        content=[TextContent(type="text", text=error_message)],
                        session_id="",
                        session=None,
                    )
                elif operation == "delete-session":
                    return DeleteSessionResponse(
                        isError=True,
                        content=[TextContent(type="text", text=error_message)],
                        session_id="",
                    )
                elif operation == "stop-session":
                    return StopSessionResponse(
                        isError=True,
                        content=[TextContent(type="text", text=error_message)],
                        session_id="",
                    )

            if operation == "create-session":
                if not role or not command:
                    raise ValueError(
                        "role and command are required for create-session operation"
                    )

                # Prepare create session parameters
                create_params = {
                    "Id": session_id,
                    "Role": role,
                    "Command": command,
                }

                # Add optional parameters if provided
                if description:
                    create_params["Description"] = description
                if timeout:
                    create_params["Timeout"] = timeout
                if idle_timeout:
                    create_params["IdleTimeout"] = idle_timeout
                if default_arguments:
                    create_params["DefaultArguments"] = default_arguments
                if connections:
                    create_params["Connections"] = connections
                if max_capacity:
                    create_params["MaxCapacity"] = max_capacity
                if number_of_workers:
                    create_params["NumberOfWorkers"] = number_of_workers
                if worker_type:
                    create_params["WorkerType"] = worker_type
                if security_configuration:
                    create_params["SecurityConfiguration"] = security_configuration
                if glue_version:
                    create_params["GlueVersion"] = glue_version

                # Add MCP management tags
                resource_tags = AwsHelper.prepare_resource_tags("GlueSession")

                # Merge user-provided tags with MCP tags
                if tags:
                    merged_tags = tags.copy()
                    merged_tags.update(resource_tags)
                    create_params["Tags"] = merged_tags
                else:
                    create_params["Tags"] = resource_tags

                if request_origin:
                    create_params["RequestOrigin"] = request_origin

                # Create the session
                response = self.glue_client.create_session(**create_params)

                return CreateSessionResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type="text",
                            text=f"Successfully created session {response.get('Session', {}).get('Id', '')}",
                        )
                    ],
                    session_id=response.get("Session", {}).get("Id", ""),
                    session=response.get("Session", {}),
                )

            elif operation == "delete-session":
                if session_id is None:
                    raise ValueError(
                        "session_id is required for delete-session operation"
                    )

                # First check if the session is managed by MCP
                try:
                    # Get the session to check if it's managed by MCP
                    get_params = {"Id": session_id}
                    if request_origin:
                        get_params["RequestOrigin"] = request_origin

                    response = self.glue_client.get_session(**get_params)
                    session = response.get("Session", {})
                    tags = session.get("Tags", {})

                    # Construct the ARN for the session
                    region = AwsHelper.get_aws_region() or "us-east-1"
                    account_id = AwsHelper.get_aws_account_id()
                    session_arn = (
                        f"arn:aws:glue:{region}:{account_id}:session/{session_id}"
                    )

                    # Check if the session is managed by MCP
                    if not AwsHelper.is_resource_mcp_managed(
                        self.glue_client, session_arn, {}
                    ):
                        error_message = f"Cannot delete session {session_id} - it is not managed by the MCP server (missing required tags)"
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return DeleteSessionResponse(
                            isError=True,
                            content=[TextContent(type="text", text=error_message)],
                            session_id=session_id,
                            operation="delete-session",
                        )
                except ClientError as e:
                    if e.response["Error"]["Code"] == "EntityNotFoundException":
                        error_message = f"Session {session_id} not found"
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return DeleteSessionResponse(
                            isError=True,
                            content=[TextContent(type="text", text=error_message)],
                            session_id=session_id,
                            operation="delete-session",
                        )
                    else:
                        raise e

                # Prepare delete session parameters
                delete_params = {"Id": session_id}
                if request_origin:
                    delete_params["RequestOrigin"] = request_origin

                # Delete the session
                response = self.glue_client.delete_session(**delete_params)

                return DeleteSessionResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type="text",
                            text=f"Successfully deleted session {session_id}",
                        )
                    ],
                    session_id=session_id,
                    operation="delete-session",
                )

            elif operation == "get-session":
                if session_id is None:
                    raise ValueError("session_id is required for get-session operation")

                # Prepare get session parameters
                get_params = {"Id": session_id}
                if request_origin:
                    get_params["RequestOrigin"] = request_origin

                # Get the session
                response = self.glue_client.get_session(**get_params)

                return GetSessionResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type="text",
                            text=f"Successfully retrieved session {session_id}",
                        )
                    ],
                    session_id=session_id,
                    session=response.get("Session", {}),
                )

            elif operation == "list-sessions":
                # Prepare list sessions parameters
                params: Dict[str, Any] = {}
                if max_results is not None:
                    params["MaxResults"] = str(max_results)
                if next_token is not None:
                    params["NextToken"] = next_token
                if tags:
                    params["Tags"] = tags
                if request_origin:
                    params["RequestOrigin"] = request_origin

                # List sessions
                response = self.glue_client.list_sessions(**params)

                return ListSessionsResponse(
                    isError=False,
                    content=[
                        TextContent(type="text", text="Successfully retrieved sessions")
                    ],
                    sessions=response.get("Sessions", []),
                    ids=response.get("Ids", []),
                    next_token=response.get("NextToken"),
                    count=len(response.get("Sessions", [])),
                )

            elif operation == "stop-session":
                if session_id is None:
                    raise ValueError(
                        "session_id is required for stop-session operation"
                    )

                # First check if the session is managed by MCP
                try:
                    # Get the session to check if it's managed by MCP
                    get_params = {"Id": session_id}
                    if request_origin:
                        get_params["RequestOrigin"] = request_origin

                    response = self.glue_client.get_session(**get_params)
                    session = response.get("Session", {})
                    tags = session.get("Tags", {})

                    # Construct the ARN for the session
                    region = AwsHelper.get_aws_region() or "us-east-1"
                    account_id = AwsHelper.get_aws_account_id()
                    session_arn = (
                        f"arn:aws:glue:{region}:{account_id}:session/{session_id}"
                    )

                    # Check if the session is managed by MCP
                    if not AwsHelper.is_resource_mcp_managed(
                        self.glue_client, session_arn, {}
                    ):
                        error_message = f"Cannot stop session {session_id} - it is not managed by the MCP server (missing required tags)"
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return StopSessionResponse(
                            isError=True,
                            content=[TextContent(type="text", text=error_message)],
                            session_id=session_id,
                        )
                except ClientError as e:
                    if e.response["Error"]["Code"] == "EntityNotFoundException":
                        error_message = f"Session {session_id} not found"
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return StopSessionResponse(
                            isError=True,
                            content=[TextContent(type="text", text=error_message)],
                            session_id=session_id,
                        )
                    else:
                        raise e

                # Prepare stop session parameters
                stop_params = {"Id": session_id}
                if request_origin:
                    stop_params["RequestOrigin"] = request_origin

                # Stop the session
                response = self.glue_client.stop_session(**stop_params)

                return StopSessionResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type="text",
                            text=f"Successfully stopped session {session_id}",
                        )
                    ],
                    session_id=session_id,
                )

            else:
                error_message = f"Invalid operation: {operation}. Must be one of: create-session, delete-session, get-session, list-sessions, stop-session"
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetSessionResponse(
                    isError=True,
                    content=[TextContent(type="text", text=error_message)],
                    session_id=session_id or "",
                    session={},
                )

        except ValueError as e:
            log_with_request_id(
                ctx, LogLevel.ERROR, f"Parameter validation error: {str(e)}"
            )
            raise
        except Exception as e:
            error_message = f"Error in manage_aws_glue_sessions: {str(e)}"
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetSessionResponse(
                isError=True,
                content=[TextContent(type="text", text=error_message)],
                session_id=session_id or "",
                session={},
            )

    async def manage_aws_glue_statements(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: run-statement, cancel-statement, get-statement, list-statements. Choose "get-statement" or "list-statements" for read-only operations when write access is disabled.',
        ),
        session_id: str = Field(
            ...,
            description="ID of the session (required for all operations).",
        ),
        statement_id: Optional[int] = Field(
            None,
            description="ID of the statement (required for cancel-statement and get-statement operations).",
        ),
        code: Optional[str] = Field(
            None,
            description="Code to execute for run-statement operation (up to 68000 characters).",
        ),
        request_origin: Optional[str] = Field(
            None,
            description="Origin of the request (optional for all operations).",
        ),
        max_results: Optional[int] = Field(
            None,
            description="Maximum number of results to return for list-statements operation.",
        ),
        next_token: Optional[str] = Field(
            None,
            description="Pagination token for list-statements operation.",
        ),
    ) -> Union[
        RunStatementResponse,
        CancelStatementResponse,
        GetStatementResponse,
        ListStatementsResponse,
    ]:
        """Manage AWS Glue Interactive Session Statements for executing code and retrieving results.

        This tool provides operations for executing code, canceling running statements, and retrieving
        results within Glue Interactive Sessions. It enables interactive data processing, exploration,
        and analysis using Spark or Ray in AWS Glue.

        ## Requirements
        - The server must be run with the `--allow-write` flag for run-statement and cancel-statement operations
        - Appropriate AWS permissions for Glue Interactive Session Statement operations
        - A valid session ID is required for all operations

        ## Operations
        - **run-statement**: Execute code in an interactive session and get a statement ID
        - **cancel-statement**: Cancel a running statement by ID
        - **get-statement**: Retrieve detailed information and results of a specific statement
        - **list-statements**: List all statements in a session with their status

        ## Example
        ```python
        # Run a PySpark statement in a session
        {
          "operation": "run-statement",
          "session_id": "my-spark-session",
          "code": "df = spark.read.csv('s3://my-bucket/data.csv', header=True)\ndf.show(5)"
        }
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            session_id: ID of the session
            statement_id: ID of the statement
            code: Code to execute for run-statement operation
            request_origin: Origin of the request
            max_results: Maximum number of results to return
            next_token: Pagination token

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            if not self.allow_write and operation not in [
                "get-statement",
                "list-statements",
            ]:
                error_message = (
                    f"Operation {operation} is not allowed without write access"
                )
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                if operation == "run-statement":
                    return RunStatementResponse(
                        isError=True,
                        content=[TextContent(type="text", text=error_message)],
                        session_id="",
                        statement_id=0,
                    )
                elif operation == "cancel-statement":
                    return CancelStatementResponse(
                        isError=True,
                        content=[TextContent(type="text", text=error_message)],
                        session_id="",
                        statement_id=0,
                    )

            if operation == "run-statement":
                if code is None:
                    raise ValueError("code is required for run-statement operation")

                # Prepare run statement parameters
                run_params = {
                    "SessionId": session_id,
                    "Code": code,
                }
                if request_origin:
                    run_params["RequestOrigin"] = request_origin

                # Run the statement
                response = self.glue_client.run_statement(**run_params)

                return RunStatementResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type="text",
                            text=f"Successfully ran statement in session {session_id}",
                        )
                    ],
                    session_id=session_id,
                    statement_id=response.get("Id", 0),
                )

            elif operation == "cancel-statement":
                if statement_id is None:
                    raise ValueError(
                        "statement_id is required for cancel-statement operation"
                    )

                # Prepare cancel statement parameters
                cancel_params = {
                    "SessionId": session_id,
                    "Id": statement_id,
                }
                if request_origin:
                    cancel_params["RequestOrigin"] = request_origin

                # Cancel the statement
                self.glue_client.cancel_statement(**cancel_params)

                return CancelStatementResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type="text",
                            text=f"Successfully canceled statement {statement_id} in session {session_id}",
                        )
                    ],
                    session_id=session_id,
                    statement_id=statement_id,
                )

            elif operation == "get-statement":
                if statement_id is None:
                    raise ValueError(
                        "statement_id is required for get-statement operation"
                    )

                # Prepare get statement parameters
                get_params = {
                    "SessionId": session_id,
                    "Id": statement_id,
                }
                if request_origin:
                    get_params["RequestOrigin"] = request_origin

                # Get the statement
                response = self.glue_client.get_statement(**get_params)

                return GetStatementResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type="text",
                            text=f"Successfully retrieved statement {statement_id} in session {session_id}",
                        )
                    ],
                    session_id=session_id,
                    statement_id=statement_id,
                    statement=response.get("Statement", {}),
                )

            elif operation == "list-statements":
                # Prepare list statements parameters
                params = {"SessionId": session_id}
                if max_results is not None:
                    params["MaxResults"] = str(max_results)
                if next_token is not None:
                    params["NextToken"] = next_token
                if request_origin:
                    params["RequestOrigin"] = request_origin

                # List statements
                response = self.glue_client.list_statements(**params)

                return ListStatementsResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type="text",
                            text=f"Successfully retrieved statements for session {session_id}",
                        )
                    ],
                    session_id=session_id,
                    statements=response.get("Statements", []),
                    next_token=response.get("NextToken"),
                    count=len(response.get("Statements", [])),
                )

            else:
                error_message = f"Invalid operation: {operation}. Must be one of: run-statement, cancel-statement, get-statement, list-statements"
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetStatementResponse(
                    isError=True,
                    content=[TextContent(type="text", text=error_message)],
                    session_id=session_id,
                    statement_id=statement_id or 0,
                    statement={},
                )

        except ValueError as e:
            log_with_request_id(
                ctx, LogLevel.ERROR, f"Parameter validation error: {str(e)}"
            )
            raise
        except Exception as e:
            error_message = f"Error in manage_aws_glue_statements: {str(e)}"
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetStatementResponse(
                isError=True,
                content=[TextContent(type="text", text=error_message)],
                session_id=session_id,
                statement_id=statement_id or 0,
                statement={},
            )
