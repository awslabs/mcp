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

"""Airflow REST API tools for the MWAA MCP Server via invoke_rest_api."""

import json
import re
from awslabs.mwaa_mcp_server.aws_client import get_mwaa_client
from awslabs.mwaa_mcp_server.consts import (
    CONNECTION_SENSITIVE_FIELDS,
    CONNECTIONS_PATH,
    DAG_PATH,
    DAG_RUN_PATH,
    DAG_RUNS_PATH,
    DAG_SOURCE_PATH,
    DAGS_PATH,
    ENVIRONMENT_NAME_PATTERN,
    IMPORT_ERRORS_PATH,
    TASK_INSTANCE_PATH,
    TASK_INSTANCES_PATH,
    TASK_LOGS_PATH,
    VARIABLES_PATH,
)
from botocore.exceptions import BotoCoreError, ClientError
from loguru import logger
from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent
from pydantic import Field
from typing import Optional


class AirflowTools:
    """Handler for Airflow REST API operations via MWAA invoke_rest_api.

    All Airflow operations are proxied through the AWS-native invoke_rest_api,
    which handles authentication securely without exposing tokens.
    """

    def __init__(self, mcp, allow_write: bool = False):
        """Initialize the Airflow tools handler.

        Args:
            mcp: The MCP server instance.
            allow_write: Whether to enable write access (default: False).
        """
        self.mcp = mcp
        self.allow_write = allow_write

        # Read tools
        self.mcp.tool(name='list-dags')(self.list_dags)
        self.mcp.tool(name='get-dag')(self.get_dag)
        self.mcp.tool(name='get-dag-source')(self.get_dag_source)
        self.mcp.tool(name='list-dag-runs')(self.list_dag_runs)
        self.mcp.tool(name='get-dag-run')(self.get_dag_run)
        self.mcp.tool(name='list-task-instances')(self.list_task_instances)
        self.mcp.tool(name='get-task-instance')(self.get_task_instance)
        self.mcp.tool(name='get-task-logs')(self.get_task_logs)
        self.mcp.tool(name='list-connections')(self.list_connections)
        self.mcp.tool(name='list-variables')(self.list_variables)
        self.mcp.tool(name='get-import-errors')(self.get_import_errors)

        # Write tools
        self.mcp.tool(name='trigger-dag-run')(self.trigger_dag_run)
        self.mcp.tool(name='pause-dag')(self.pause_dag)
        self.mcp.tool(name='unpause-dag')(self.unpause_dag)

    def _check_write_access(self) -> None:
        """Check if write access is enabled.

        Raises:
            PermissionError: If write access is not enabled.
        """
        if not self.allow_write:
            raise PermissionError(
                'Write operations require the --allow-write flag. '
                'Restart the server with --allow-write to enable mutations.'
            )

    def _resolve_environment(
        self,
        environment_name: Optional[str],
        region: Optional[str] = None,
        profile_name: Optional[str] = None,
    ) -> str:
        """Resolve the environment name, auto-selecting if only one exists.

        Args:
            environment_name: Explicit environment name, or None to auto-detect.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            The resolved environment name.

        Raises:
            ValueError: If no environments found or multiple found without explicit name.
        """
        if environment_name:
            return environment_name

        client = get_mwaa_client(region_name=region, profile_name=profile_name)
        response = client.list_environments()
        envs = response.get('Environments', [])

        if len(envs) == 0:
            raise ValueError('No MWAA environments found in this region.')
        if len(envs) == 1:
            logger.info(f'Auto-selected environment: {envs[0]}')
            return envs[0]

        env_list = '\n'.join(f'  - {e}' for e in envs)
        raise ValueError(f'Multiple MWAA environments found. Please specify one:\n{env_list}')

    @staticmethod
    def _validate_environment_name(name: str) -> None:
        """Validate an MWAA environment name.

        Args:
            name: The environment name to validate.

        Raises:
            ValueError: If the name is invalid.
        """
        if not re.match(ENVIRONMENT_NAME_PATTERN, name):
            raise ValueError(
                f'Invalid environment name: {name}. '
                'Must be 1-80 characters, start with a letter, '
                'and contain only alphanumeric characters, hyphens, and underscores.'
            )

    @staticmethod
    def _sanitize_path_param(value: str, param_name: str) -> str:
        """Sanitize a path parameter to prevent path traversal.

        Args:
            value: The parameter value.
            param_name: Name of the parameter (for error messages).

        Returns:
            The sanitized value.

        Raises:
            ValueError: If the value contains path traversal characters.
        """
        if '..' in value or '/' in value or '\\' in value:
            raise ValueError(
                f'Invalid {param_name}: must not contain path traversal characters '
                f'("..", "/", "\\"). Got: {value}'
            )
        return value

    async def _invoke_airflow_api(
        self,
        environment_name: str,
        method: str,
        path: str,
        body: Optional[dict] = None,
        query_parameters: Optional[dict] = None,
        region: Optional[str] = None,
        profile_name: Optional[str] = None,
    ) -> dict:
        """Invoke an Airflow REST API endpoint via MWAA invoke_rest_api.

        The AWS invoke_rest_api handles API version routing internally,
        so paths should not include /api/v1 or /api/v2 prefixes.

        Args:
            environment_name: Name of the MWAA environment.
            method: HTTP method (GET, POST, PATCH, PUT, DELETE).
            path: Airflow REST API path (e.g. '/dags' or '/dags/{dag_id}/dagRuns').
            body: Optional request body.
            query_parameters: Optional query parameters.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            The API response as a dictionary.
        """
        self._validate_environment_name(environment_name)
        client = get_mwaa_client(region_name=region, profile_name=profile_name)

        kwargs: dict = {
            'Name': environment_name,
            'Method': method,
            'Path': path,
        }
        if body is not None:
            kwargs['Body'] = body
        if query_parameters is not None:
            kwargs['QueryParameters'] = query_parameters

        response = client.invoke_rest_api(**kwargs)

        rest_api_response = response.get('RestApiResponse', {})
        return rest_api_response

    @staticmethod
    def _redact_connections(response: dict) -> dict:
        """Redact sensitive fields from connection responses.

        Args:
            response: The API response containing connection data.

        Returns:
            The response with sensitive fields redacted.
        """
        connections = response.get('connections', [])
        for conn in connections:
            for field in CONNECTION_SENSITIVE_FIELDS:
                if field in conn:
                    conn[field] = '***REDACTED***'
        return response

    async def list_dags(
        self,
        ctx: Context,
        environment_name: Optional[str] = Field(
            default=None,
            description='Name of the MWAA environment. If omitted and only one environment exists, it is used automatically.',
        ),
        limit: Optional[int] = Field(
            default=None,
            description='Maximum number of DAGs to return.',
        ),
        offset: Optional[int] = Field(
            default=None,
            description='Number of DAGs to skip for pagination.',
        ),
        paused: Optional[bool] = Field(
            default=None,
            description='Filter by paused status.',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region override.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name override.',
        ),
    ) -> CallToolResult:
        """List all DAGs in an MWAA environment.

        Returns a list of DAGs with their metadata including DAG ID, description,
        schedule interval, paused status, and more.

        Args:
            ctx: The MCP context.
            environment_name: Name of the MWAA environment.
            limit: Maximum number of results.
            offset: Pagination offset.
            paused: Filter by paused status.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult with the list of DAGs.
        """
        try:
            environment_name = self._resolve_environment(environment_name, region, profile_name)
            query_params: dict = {}
            if limit is not None:
                query_params['limit'] = str(limit)
            if offset is not None:
                query_params['offset'] = str(offset)
            if paused is not None:
                query_params['paused'] = str(paused).lower()

            response = await self._invoke_airflow_api(
                environment_name=environment_name,
                method='GET',
                path=DAGS_PATH,
                query_parameters=query_params or None,
                region=region,
                profile_name=profile_name,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text='DAG listing retrieved successfully'),
                    TextContent(type='text', text=json.dumps(response, default=str)),
                ],
            )
        except (ValueError, PermissionError) as e:
            error_message = str(e)
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except ClientError as e:
            error_message = f'AWS API error listing DAGs: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error listing DAGs: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def get_dag(
        self,
        ctx: Context,
        environment_name: Optional[str] = Field(
            default=None,
            description='Name of the MWAA environment. If omitted and only one environment exists, it is used automatically.',
        ),
        dag_id: str = Field(
            ...,
            description='The DAG ID to retrieve.',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region override.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name override.',
        ),
    ) -> CallToolResult:
        """Get details of a specific DAG.

        Returns detailed information about a DAG including its schedule, owners,
        tags, and configuration.

        Args:
            ctx: The MCP context.
            environment_name: Name of the MWAA environment.
            dag_id: The DAG identifier.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult with DAG details.
        """
        try:
            environment_name = self._resolve_environment(environment_name, region, profile_name)
            self._sanitize_path_param(dag_id, 'dag_id')
            path = DAG_PATH.format(dag_id=dag_id)

            response = await self._invoke_airflow_api(
                environment_name=environment_name,
                method='GET',
                path=path,
                region=region,
                profile_name=profile_name,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=f'DAG details for: {dag_id}'),
                    TextContent(type='text', text=json.dumps(response, default=str)),
                ],
            )
        except (ValueError, PermissionError) as e:
            error_message = str(e)
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except ClientError as e:
            error_message = f'AWS API error getting DAG: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error getting DAG: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def get_dag_source(
        self,
        ctx: Context,
        environment_name: Optional[str] = Field(
            default=None,
            description='Name of the MWAA environment. If omitted and only one environment exists, it is used automatically.',
        ),
        file_token: str = Field(
            ...,
            description='The file token from the DAG details (obtained from get-dag).',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region override.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name override.',
        ),
    ) -> CallToolResult:
        """Get the source code of a DAG file.

        Returns the Python source code of a DAG file using the file token
        obtained from the get-dag tool response.

        Args:
            ctx: The MCP context.
            environment_name: Name of the MWAA environment.
            file_token: The file token from DAG details.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult with the DAG source code.
        """
        try:
            environment_name = self._resolve_environment(environment_name, region, profile_name)
            self._sanitize_path_param(file_token, 'file_token')
            path = DAG_SOURCE_PATH.format(file_token=file_token)

            response = await self._invoke_airflow_api(
                environment_name=environment_name,
                method='GET',
                path=path,
                region=region,
                profile_name=profile_name,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text='DAG source retrieved successfully'),
                    TextContent(type='text', text=json.dumps(response, default=str)),
                ],
            )
        except (ValueError, PermissionError) as e:
            error_message = str(e)
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except ClientError as e:
            error_message = f'AWS API error getting DAG source: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error getting DAG source: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def list_dag_runs(
        self,
        ctx: Context,
        environment_name: Optional[str] = Field(
            default=None,
            description='Name of the MWAA environment. If omitted and only one environment exists, it is used automatically.',
        ),
        dag_id: str = Field(
            ...,
            description='The DAG ID to list runs for.',
        ),
        limit: Optional[int] = Field(
            default=None,
            description='Maximum number of DAG runs to return.',
        ),
        offset: Optional[int] = Field(
            default=None,
            description='Number of DAG runs to skip for pagination.',
        ),
        state: Optional[str] = Field(
            default=None,
            description='Filter by run state (e.g., "success", "failed", "running").',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region override.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name override.',
        ),
    ) -> CallToolResult:
        """List DAG runs for a specific DAG.

        Returns a list of DAG runs with their execution dates, states, and run IDs.

        Args:
            ctx: The MCP context.
            environment_name: Name of the MWAA environment.
            dag_id: The DAG identifier.
            limit: Maximum number of results.
            offset: Pagination offset.
            state: Filter by run state.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult with the list of DAG runs.
        """
        try:
            environment_name = self._resolve_environment(environment_name, region, profile_name)
            self._sanitize_path_param(dag_id, 'dag_id')
            path = DAG_RUNS_PATH.format(dag_id=dag_id)

            query_params: dict = {}
            if limit is not None:
                query_params['limit'] = str(limit)
            if offset is not None:
                query_params['offset'] = str(offset)
            if state is not None:
                query_params['state'] = state

            response = await self._invoke_airflow_api(
                environment_name=environment_name,
                method='GET',
                path=path,
                query_parameters=query_params or None,
                region=region,
                profile_name=profile_name,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=f'DAG runs for: {dag_id}'),
                    TextContent(type='text', text=json.dumps(response, default=str)),
                ],
            )
        except (ValueError, PermissionError) as e:
            error_message = str(e)
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except ClientError as e:
            error_message = f'AWS API error listing DAG runs: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error listing DAG runs: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def get_dag_run(
        self,
        ctx: Context,
        environment_name: Optional[str] = Field(
            default=None,
            description='Name of the MWAA environment. If omitted and only one environment exists, it is used automatically.',
        ),
        dag_id: str = Field(
            ...,
            description='The DAG ID.',
        ),
        dag_run_id: str = Field(
            ...,
            description='The DAG run ID.',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region override.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name override.',
        ),
    ) -> CallToolResult:
        """Get details of a specific DAG run.

        Returns detailed information about a DAG run including its state, execution date,
        start date, end date, and configuration.

        Args:
            ctx: The MCP context.
            environment_name: Name of the MWAA environment.
            dag_id: The DAG identifier.
            dag_run_id: The DAG run identifier.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult with DAG run details.
        """
        try:
            environment_name = self._resolve_environment(environment_name, region, profile_name)
            self._sanitize_path_param(dag_id, 'dag_id')
            self._sanitize_path_param(dag_run_id, 'dag_run_id')
            path = DAG_RUN_PATH.format(dag_id=dag_id, dag_run_id=dag_run_id)

            response = await self._invoke_airflow_api(
                environment_name=environment_name,
                method='GET',
                path=path,
                region=region,
                profile_name=profile_name,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=f'DAG run details for: {dag_id}/{dag_run_id}'),
                    TextContent(type='text', text=json.dumps(response, default=str)),
                ],
            )
        except (ValueError, PermissionError) as e:
            error_message = str(e)
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except ClientError as e:
            error_message = f'AWS API error getting DAG run: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error getting DAG run: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def list_task_instances(
        self,
        ctx: Context,
        environment_name: Optional[str] = Field(
            default=None,
            description='Name of the MWAA environment. If omitted and only one environment exists, it is used automatically.',
        ),
        dag_id: str = Field(
            ...,
            description='The DAG ID.',
        ),
        dag_run_id: str = Field(
            ...,
            description='The DAG run ID.',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region override.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name override.',
        ),
    ) -> CallToolResult:
        """List task instances for a specific DAG run.

        Returns all task instances within a DAG run, including their states,
        start/end times, and execution details.

        Args:
            ctx: The MCP context.
            environment_name: Name of the MWAA environment.
            dag_id: The DAG identifier.
            dag_run_id: The DAG run identifier.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult with the list of task instances.
        """
        try:
            environment_name = self._resolve_environment(environment_name, region, profile_name)
            self._sanitize_path_param(dag_id, 'dag_id')
            self._sanitize_path_param(dag_run_id, 'dag_run_id')
            path = TASK_INSTANCES_PATH.format(dag_id=dag_id, dag_run_id=dag_run_id)

            response = await self._invoke_airflow_api(
                environment_name=environment_name,
                method='GET',
                path=path,
                region=region,
                profile_name=profile_name,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Task instances for: {dag_id}/{dag_run_id}',
                    ),
                    TextContent(type='text', text=json.dumps(response, default=str)),
                ],
            )
        except (ValueError, PermissionError) as e:
            error_message = str(e)
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except ClientError as e:
            error_message = f'AWS API error listing task instances: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error listing task instances: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def get_task_instance(
        self,
        ctx: Context,
        environment_name: Optional[str] = Field(
            default=None,
            description='Name of the MWAA environment. If omitted and only one environment exists, it is used automatically.',
        ),
        dag_id: str = Field(
            ...,
            description='The DAG ID.',
        ),
        dag_run_id: str = Field(
            ...,
            description='The DAG run ID.',
        ),
        task_id: str = Field(
            ...,
            description='The task ID.',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region override.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name override.',
        ),
    ) -> CallToolResult:
        """Get details of a specific task instance.

        Returns detailed information about a task instance including its state,
        start/end dates, duration, try number, and execution details.

        Args:
            ctx: The MCP context.
            environment_name: Name of the MWAA environment.
            dag_id: The DAG identifier.
            dag_run_id: The DAG run identifier.
            task_id: The task identifier.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult with task instance details.
        """
        try:
            environment_name = self._resolve_environment(environment_name, region, profile_name)
            self._sanitize_path_param(dag_id, 'dag_id')
            self._sanitize_path_param(dag_run_id, 'dag_run_id')
            self._sanitize_path_param(task_id, 'task_id')
            path = TASK_INSTANCE_PATH.format(dag_id=dag_id, dag_run_id=dag_run_id, task_id=task_id)

            response = await self._invoke_airflow_api(
                environment_name=environment_name,
                method='GET',
                path=path,
                region=region,
                profile_name=profile_name,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Task instance details for: {dag_id}/{dag_run_id}/{task_id}',
                    ),
                    TextContent(type='text', text=json.dumps(response, default=str)),
                ],
            )
        except (ValueError, PermissionError) as e:
            error_message = str(e)
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except ClientError as e:
            error_message = f'AWS API error getting task instance: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error getting task instance: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def get_task_logs(
        self,
        ctx: Context,
        environment_name: Optional[str] = Field(
            default=None,
            description='Name of the MWAA environment. If omitted and only one environment exists, it is used automatically.',
        ),
        dag_id: str = Field(
            ...,
            description='The DAG ID.',
        ),
        dag_run_id: str = Field(
            ...,
            description='The DAG run ID.',
        ),
        task_id: str = Field(
            ...,
            description='The task ID.',
        ),
        try_number: int = Field(
            ...,
            description='The task try number (starts at 1).',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region override.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name override.',
        ),
    ) -> CallToolResult:
        """Get logs for a specific task instance try.

        Returns the execution logs for a task instance at a specific try number.
        Useful for debugging failed or problematic task executions.

        Args:
            ctx: The MCP context.
            environment_name: Name of the MWAA environment.
            dag_id: The DAG identifier.
            dag_run_id: The DAG run identifier.
            task_id: The task identifier.
            try_number: The try number (starts at 1).
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult with the task logs.
        """
        try:
            environment_name = self._resolve_environment(environment_name, region, profile_name)
            self._sanitize_path_param(dag_id, 'dag_id')
            self._sanitize_path_param(dag_run_id, 'dag_run_id')
            self._sanitize_path_param(task_id, 'task_id')
            path = TASK_LOGS_PATH.format(
                dag_id=dag_id,
                dag_run_id=dag_run_id,
                task_id=task_id,
                try_number=try_number,
            )

            response = await self._invoke_airflow_api(
                environment_name=environment_name,
                method='GET',
                path=path,
                region=region,
                profile_name=profile_name,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Task logs for: {dag_id}/{dag_run_id}/{task_id} (try {try_number})',
                    ),
                    TextContent(type='text', text=json.dumps(response, default=str)),
                ],
            )
        except (ValueError, PermissionError) as e:
            error_message = str(e)
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except ClientError as e:
            error_message = f'AWS API error getting task logs: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error getting task logs: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def list_connections(
        self,
        ctx: Context,
        environment_name: Optional[str] = Field(
            default=None,
            description='Name of the MWAA environment. If omitted and only one environment exists, it is used automatically.',
        ),
        limit: Optional[int] = Field(
            default=None,
            description='Maximum number of connections to return.',
        ),
        offset: Optional[int] = Field(
            default=None,
            description='Number of connections to skip for pagination.',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region override.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name override.',
        ),
    ) -> CallToolResult:
        """List Airflow connections in an MWAA environment.

        Returns a list of connections with sensitive fields (password, extra) redacted.

        Args:
            ctx: The MCP context.
            environment_name: Name of the MWAA environment.
            limit: Maximum number of results.
            offset: Pagination offset.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult with the list of connections (passwords redacted).
        """
        try:
            environment_name = self._resolve_environment(environment_name, region, profile_name)
            query_params: dict = {}
            if limit is not None:
                query_params['limit'] = str(limit)
            if offset is not None:
                query_params['offset'] = str(offset)

            response = await self._invoke_airflow_api(
                environment_name=environment_name,
                method='GET',
                path=CONNECTIONS_PATH,
                query_parameters=query_params or None,
                region=region,
                profile_name=profile_name,
            )

            response = self._redact_connections(response)

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text='Connections retrieved (sensitive fields redacted)',
                    ),
                    TextContent(type='text', text=json.dumps(response, default=str)),
                ],
            )
        except (ValueError, PermissionError) as e:
            error_message = str(e)
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except ClientError as e:
            error_message = f'AWS API error listing connections: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error listing connections: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def list_variables(
        self,
        ctx: Context,
        environment_name: Optional[str] = Field(
            default=None,
            description='Name of the MWAA environment. If omitted and only one environment exists, it is used automatically.',
        ),
        limit: Optional[int] = Field(
            default=None,
            description='Maximum number of variables to return.',
        ),
        offset: Optional[int] = Field(
            default=None,
            description='Number of variables to skip for pagination.',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region override.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name override.',
        ),
    ) -> CallToolResult:
        """List Airflow variables in an MWAA environment.

        Returns a list of Airflow variables with their keys and values.

        Args:
            ctx: The MCP context.
            environment_name: Name of the MWAA environment.
            limit: Maximum number of results.
            offset: Pagination offset.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult with the list of variables.
        """
        try:
            environment_name = self._resolve_environment(environment_name, region, profile_name)
            query_params: dict = {}
            if limit is not None:
                query_params['limit'] = str(limit)
            if offset is not None:
                query_params['offset'] = str(offset)

            response = await self._invoke_airflow_api(
                environment_name=environment_name,
                method='GET',
                path=VARIABLES_PATH,
                query_parameters=query_params or None,
                region=region,
                profile_name=profile_name,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text='Variables retrieved successfully'),
                    TextContent(type='text', text=json.dumps(response, default=str)),
                ],
            )
        except (ValueError, PermissionError) as e:
            error_message = str(e)
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except ClientError as e:
            error_message = f'AWS API error listing variables: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error listing variables: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def get_import_errors(
        self,
        ctx: Context,
        environment_name: Optional[str] = Field(
            default=None,
            description='Name of the MWAA environment. If omitted and only one environment exists, it is used automatically.',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region override.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name override.',
        ),
    ) -> CallToolResult:
        """Get DAG import errors in an MWAA environment.

        Returns a list of import/parsing errors for DAG files. Useful for diagnosing
        why DAGs are not appearing or are broken.

        Args:
            ctx: The MCP context.
            environment_name: Name of the MWAA environment.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult with import errors.
        """
        try:
            environment_name = self._resolve_environment(environment_name, region, profile_name)
            response = await self._invoke_airflow_api(
                environment_name=environment_name,
                method='GET',
                path=IMPORT_ERRORS_PATH,
                region=region,
                profile_name=profile_name,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text='Import errors retrieved successfully'),
                    TextContent(type='text', text=json.dumps(response, default=str)),
                ],
            )
        except (ValueError, PermissionError) as e:
            error_message = str(e)
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except ClientError as e:
            error_message = f'AWS API error getting import errors: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error getting import errors: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def trigger_dag_run(
        self,
        ctx: Context,
        environment_name: Optional[str] = Field(
            default=None,
            description='Name of the MWAA environment. If omitted and only one environment exists, it is used automatically.',
        ),
        dag_id: str = Field(
            ...,
            description='The DAG ID to trigger.',
        ),
        conf: Optional[dict] = Field(
            default=None,
            description='Optional JSON configuration to pass to the DAG run.',
        ),
        logical_date: Optional[str] = Field(
            default=None,
            description='Optional logical date for the DAG run (ISO 8601 format).',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region override.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name override.',
        ),
    ) -> CallToolResult:
        """Trigger a new DAG run.

        Creates a new DAG run for the specified DAG. Optionally pass configuration
        and a logical date.

        Requires the --allow-write flag.

        Args:
            ctx: The MCP context.
            environment_name: Name of the MWAA environment.
            dag_id: The DAG identifier to trigger.
            conf: Optional configuration dict for the DAG run.
            logical_date: Optional logical date in ISO 8601 format.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult with the triggered DAG run details.
        """
        try:
            self._check_write_access()
            environment_name = self._resolve_environment(environment_name, region, profile_name)
            self._sanitize_path_param(dag_id, 'dag_id')
            path = DAG_RUNS_PATH.format(dag_id=dag_id)

            body: dict = {}
            if conf is not None:
                body['conf'] = conf
            if logical_date is not None:
                body['logical_date'] = logical_date

            response = await self._invoke_airflow_api(
                environment_name=environment_name,
                method='POST',
                path=path,
                body=body or None,
                region=region,
                profile_name=profile_name,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=f'DAG run triggered for: {dag_id}'),
                    TextContent(type='text', text=json.dumps(response, default=str)),
                ],
            )
        except PermissionError as e:
            error_message = str(e)
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except ValueError as e:
            error_message = str(e)
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except ClientError as e:
            error_message = f'AWS API error triggering DAG run: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error triggering DAG run: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def pause_dag(
        self,
        ctx: Context,
        environment_name: Optional[str] = Field(
            default=None,
            description='Name of the MWAA environment. If omitted and only one environment exists, it is used automatically.',
        ),
        dag_id: str = Field(
            ...,
            description='The DAG ID to pause.',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region override.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name override.',
        ),
    ) -> CallToolResult:
        """Pause a DAG.

        Sets the DAG's paused status to true, preventing new scheduled runs.

        Requires the --allow-write flag.

        Args:
            ctx: The MCP context.
            environment_name: Name of the MWAA environment.
            dag_id: The DAG identifier to pause.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult confirming the DAG was paused.
        """
        try:
            self._check_write_access()
            environment_name = self._resolve_environment(environment_name, region, profile_name)
            self._sanitize_path_param(dag_id, 'dag_id')
            path = DAG_PATH.format(dag_id=dag_id)

            response = await self._invoke_airflow_api(
                environment_name=environment_name,
                method='PATCH',
                path=path,
                body={'is_paused': True},
                region=region,
                profile_name=profile_name,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=f'DAG paused: {dag_id}'),
                    TextContent(type='text', text=json.dumps(response, default=str)),
                ],
            )
        except PermissionError as e:
            error_message = str(e)
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except ValueError as e:
            error_message = str(e)
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except ClientError as e:
            error_message = f'AWS API error pausing DAG: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error pausing DAG: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def unpause_dag(
        self,
        ctx: Context,
        environment_name: Optional[str] = Field(
            default=None,
            description='Name of the MWAA environment. If omitted and only one environment exists, it is used automatically.',
        ),
        dag_id: str = Field(
            ...,
            description='The DAG ID to unpause.',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region override.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name override.',
        ),
    ) -> CallToolResult:
        """Unpause a DAG.

        Sets the DAG's paused status to false, allowing scheduled runs to resume.

        Requires the --allow-write flag.

        Args:
            ctx: The MCP context.
            environment_name: Name of the MWAA environment.
            dag_id: The DAG identifier to unpause.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult confirming the DAG was unpaused.
        """
        try:
            self._check_write_access()
            environment_name = self._resolve_environment(environment_name, region, profile_name)
            self._sanitize_path_param(dag_id, 'dag_id')
            path = DAG_PATH.format(dag_id=dag_id)

            response = await self._invoke_airflow_api(
                environment_name=environment_name,
                method='PATCH',
                path=path,
                body={'is_paused': False},
                region=region,
                profile_name=profile_name,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=f'DAG unpaused: {dag_id}'),
                    TextContent(type='text', text=json.dumps(response, default=str)),
                ],
            )
        except PermissionError as e:
            error_message = str(e)
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except ValueError as e:
            error_message = str(e)
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except ClientError as e:
            error_message = f'AWS API error unpausing DAG: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error unpausing DAG: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
