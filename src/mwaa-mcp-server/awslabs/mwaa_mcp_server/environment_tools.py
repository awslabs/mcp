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

"""MWAA environment management tools for the MWAA MCP Server."""

import json
import re
from awslabs.mwaa_mcp_server.aws_client import get_mwaa_client
from awslabs.mwaa_mcp_server.consts import ENVIRONMENT_NAME_PATTERN
from botocore.exceptions import BotoCoreError, ClientError
from loguru import logger
from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent
from pydantic import Field
from typing import Optional


class EnvironmentTools:
    """Handler for MWAA environment management operations.

    Provides tools for listing, describing, creating, updating, and deleting
    MWAA environments via the AWS MWAA API.
    """

    def __init__(self, mcp, allow_write: bool = False):
        """Initialize the environment tools handler.

        Args:
            mcp: The MCP server instance.
            allow_write: Whether to enable write access (default: False).
        """
        self.mcp = mcp
        self.allow_write = allow_write

        self.mcp.tool(name='list-environments')(self.list_environments)
        self.mcp.tool(name='get-environment')(self.get_environment)
        self.mcp.tool(name='create-environment')(self.create_environment)
        self.mcp.tool(name='update-environment')(self.update_environment)
        self.mcp.tool(name='delete-environment')(self.delete_environment)

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

    async def list_environments(
        self,
        ctx: Context,
        region: Optional[str] = Field(
            default=None,
            description='AWS region. Defaults to AWS_REGION env var or us-east-1.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name. Falls back to AWS_PROFILE env var.',
        ),
    ) -> CallToolResult:
        """List all MWAA environments in the specified region.

        Returns a list of environment names available in your AWS account for the given region.
        Use get-environment to retrieve detailed information about a specific environment.

        IMPORTANT: Use this tool instead of 'aws mwaa list-environments' CLI command.

        Args:
            ctx: The MCP context.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult with list of environment names.
        """
        try:
            logger.info('Listing MWAA environments')
            client = get_mwaa_client(region_name=region, profile_name=profile_name)

            environments = []
            paginator = client.get_paginator('list_environments')
            for page in paginator.paginate():
                environments.extend(page.get('Environments', []))

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Found {len(environments)} MWAA environment(s)',
                    ),
                    TextContent(
                        type='text',
                        text=json.dumps({'environments': environments}),
                    ),
                ],
            )
        except ClientError as e:
            error_message = f'AWS API error listing environments: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error listing environments: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def get_environment(
        self,
        ctx: Context,
        environment_name: str = Field(
            ...,
            description='Name of the MWAA environment to describe (1-80 characters).',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region. Defaults to AWS_REGION env var or us-east-1.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name. Falls back to AWS_PROFILE env var.',
        ),
    ) -> CallToolResult:
        """Get detailed information about an MWAA environment.

        Returns comprehensive details including environment status, Airflow version,
        execution role, network configuration, logging settings, and more.

        IMPORTANT: Use this tool instead of 'aws mwaa get-environment' CLI command.

        Args:
            ctx: The MCP context.
            environment_name: Name of the MWAA environment.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult with environment details.
        """
        try:
            self._validate_environment_name(environment_name)
            logger.info(f'Getting MWAA environment: {environment_name}')
            client = get_mwaa_client(region_name=region, profile_name=profile_name)

            response = client.get_environment(Name=environment_name)
            environment = response.get('Environment', {})

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Environment details for: {environment_name}',
                    ),
                    TextContent(
                        type='text',
                        text=json.dumps(environment, default=str),
                    ),
                ],
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
            error_message = f'AWS API error getting environment: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error getting environment: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def create_environment(
        self,
        ctx: Context,
        environment_name: str = Field(
            ...,
            description='Name for the new MWAA environment (1-80 characters).',
        ),
        dag_s3_path: str = Field(
            ...,
            description='Relative path to the DAGs folder in the S3 bucket (e.g., "dags/").',
        ),
        execution_role_arn: str = Field(
            ...,
            description='ARN of the IAM execution role for the environment.',
        ),
        source_bucket_arn: str = Field(
            ...,
            description='ARN of the S3 bucket containing DAGs and plugins.',
        ),
        network_configuration: dict = Field(
            ...,
            description=(
                'Network configuration with SecurityGroupIds (list of VPC security group IDs) '
                'and SubnetIds (list of VPC subnet IDs, minimum 2 in different AZs).'
            ),
        ),
        airflow_version: Optional[str] = Field(
            default=None,
            description='Apache Airflow version (e.g., "2.8.1"). Defaults to latest.',
        ),
        environment_class: Optional[str] = Field(
            default=None,
            description='Environment class: "mw1.small", "mw1.medium", or "mw1.large".',
        ),
        max_workers: Optional[int] = Field(
            default=None,
            description='Maximum number of workers for auto-scaling.',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region. Defaults to AWS_REGION env var or us-east-1.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name. Falls back to AWS_PROFILE env var.',
        ),
    ) -> CallToolResult:
        """Create a new MWAA environment.

        Creates an Amazon MWAA environment with the specified configuration. This operation
        is asynchronous — the environment status will be CREATING until ready.

        Requires the --allow-write flag.

        Args:
            ctx: The MCP context.
            environment_name: Name for the new environment.
            dag_s3_path: S3 path to the DAGs folder.
            execution_role_arn: IAM execution role ARN.
            source_bucket_arn: S3 bucket ARN for DAGs and plugins.
            network_configuration: VPC network configuration.
            airflow_version: Optional Airflow version.
            environment_class: Optional environment size class.
            max_workers: Optional maximum worker count.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult with the created environment ARN.
        """
        try:
            self._check_write_access()
            self._validate_environment_name(environment_name)
            logger.info(f'Creating MWAA environment: {environment_name}')
            client = get_mwaa_client(region_name=region, profile_name=profile_name)

            kwargs: dict = {
                'Name': environment_name,
                'DagS3Path': dag_s3_path,
                'ExecutionRoleArn': execution_role_arn,
                'SourceBucketArn': source_bucket_arn,
                'NetworkConfiguration': network_configuration,
            }
            if airflow_version is not None:
                kwargs['AirflowVersion'] = airflow_version
            if environment_class is not None:
                kwargs['EnvironmentClass'] = environment_class
            if max_workers is not None:
                kwargs['MaxWorkers'] = max_workers

            response = client.create_environment(**kwargs)

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Environment creation initiated: {environment_name}',
                    ),
                    TextContent(
                        type='text',
                        text=json.dumps({'arn': response.get('Arn', '')}, default=str),
                    ),
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
            error_message = f'AWS API error creating environment: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error creating environment: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def update_environment(
        self,
        ctx: Context,
        environment_name: str = Field(
            ...,
            description='Name of the MWAA environment to update.',
        ),
        airflow_version: Optional[str] = Field(
            default=None,
            description='New Apache Airflow version.',
        ),
        environment_class: Optional[str] = Field(
            default=None,
            description='New environment class: "mw1.small", "mw1.medium", or "mw1.large".',
        ),
        max_workers: Optional[int] = Field(
            default=None,
            description='New maximum number of workers.',
        ),
        dag_s3_path: Optional[str] = Field(
            default=None,
            description='New relative path to the DAGs folder in S3.',
        ),
        execution_role_arn: Optional[str] = Field(
            default=None,
            description='New IAM execution role ARN.',
        ),
        source_bucket_arn: Optional[str] = Field(
            default=None,
            description='New S3 bucket ARN.',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region. Defaults to AWS_REGION env var or us-east-1.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name. Falls back to AWS_PROFILE env var.',
        ),
    ) -> CallToolResult:
        """Update an existing MWAA environment.

        Updates the specified MWAA environment configuration. Only provided parameters
        will be updated. This operation is asynchronous.

        Requires the --allow-write flag.

        Args:
            ctx: The MCP context.
            environment_name: Name of the environment to update.
            airflow_version: Optional new Airflow version.
            environment_class: Optional new environment class.
            max_workers: Optional new max workers.
            dag_s3_path: Optional new DAG S3 path.
            execution_role_arn: Optional new execution role ARN.
            source_bucket_arn: Optional new source bucket ARN.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult with the update confirmation.
        """
        try:
            self._check_write_access()
            self._validate_environment_name(environment_name)
            logger.info(f'Updating MWAA environment: {environment_name}')
            client = get_mwaa_client(region_name=region, profile_name=profile_name)

            kwargs: dict = {'Name': environment_name}
            if airflow_version is not None:
                kwargs['AirflowVersion'] = airflow_version
            if environment_class is not None:
                kwargs['EnvironmentClass'] = environment_class
            if max_workers is not None:
                kwargs['MaxWorkers'] = max_workers
            if dag_s3_path is not None:
                kwargs['DagS3Path'] = dag_s3_path
            if execution_role_arn is not None:
                kwargs['ExecutionRoleArn'] = execution_role_arn
            if source_bucket_arn is not None:
                kwargs['SourceBucketArn'] = source_bucket_arn

            response = client.update_environment(**kwargs)

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Environment update initiated: {environment_name}',
                    ),
                    TextContent(
                        type='text',
                        text=json.dumps({'arn': response.get('Arn', '')}, default=str),
                    ),
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
            error_message = f'AWS API error updating environment: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error updating environment: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def delete_environment(
        self,
        ctx: Context,
        environment_name: str = Field(
            ...,
            description='Name of the MWAA environment to delete.',
        ),
        region: Optional[str] = Field(
            default=None,
            description='AWS region. Defaults to AWS_REGION env var or us-east-1.',
        ),
        profile_name: Optional[str] = Field(
            default=None,
            description='AWS CLI profile name. Falls back to AWS_PROFILE env var.',
        ),
    ) -> CallToolResult:
        """Delete an MWAA environment.

        Permanently deletes the specified MWAA environment and all associated resources.
        This operation is irreversible and asynchronous.

        Requires the --allow-write flag.

        Args:
            ctx: The MCP context.
            environment_name: Name of the environment to delete.
            region: AWS region override.
            profile_name: AWS CLI profile name override.

        Returns:
            CallToolResult confirming deletion was initiated.
        """
        try:
            self._check_write_access()
            self._validate_environment_name(environment_name)
            logger.info(f'Deleting MWAA environment: {environment_name}')
            client = get_mwaa_client(region_name=region, profile_name=profile_name)

            client.delete_environment(Name=environment_name)

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Environment deletion initiated: {environment_name}',
                    ),
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
            error_message = f'AWS API error deleting environment: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        except BotoCoreError as e:
            error_message = f'AWS SDK error deleting environment: {e}'
            logger.error(error_message)
            await ctx.error(error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
