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

"""GlueDataQualityHandler for Data Processing MCP Server."""

from awslabs.aws_dataprocessing_mcp_server.core.glue_data_catalog.data_catalog_data_quality_manager import (
    DataCatalogDataQualityManager,
)
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent
from pydantic import Field
from typing import Annotated, List, Optional


class GlueDataQualityHandler:
    """Handler for Amazon Glue Data Quality operations."""

    def __init__(self, mcp, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the Glue Data Quality handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.data_catalog_data_quality_manager = DataCatalogDataQualityManager(
            self.allow_write, self.allow_sensitive_data_access
        )

        # Register tools
        self.mcp.tool(name='manage_aws_glue_data_quality')(self.manage_aws_glue_data_quality)

    async def manage_aws_glue_data_quality(
        self,
        ctx: Context,
        operation: Annotated[
            str,
            Field(
                description='Operation to perform: list-rulesets, get-ruleset, create-ruleset, update-ruleset, delete-ruleset, start-ruleset-evaluation-run, get-ruleset-evaluation-run, list-ruleset-evaluation-runs, get-data-quality-result, list-data-quality-results, or batch-get-data-quality-result. Choose "list-rulesets", "get-ruleset", "get-ruleset-evaluation-run", "list-ruleset-evaluation-runs", "get-data-quality-result", "list-data-quality-results", or "batch-get-data-quality-result" for read-only operations.',
            ),
        ],
        name: Annotated[
            Optional[str],
            Field(
                description='Name of the ruleset (required for get-ruleset, create-ruleset, update-ruleset, and delete-ruleset operations).',
            ),
        ] = None,
        ruleset: Annotated[
            Optional[str],
            Field(
                description='DQDL ruleset definition (required for create-ruleset, optional for update-ruleset).',
            ),
        ] = None,
        description: Annotated[
            Optional[str],
            Field(
                description='Description of the ruleset (for create-ruleset and update-ruleset operations).',
            ),
        ] = None,
        database_name: Annotated[
            Optional[str],
            Field(
                description='Name of the database containing the target table (required for start-ruleset-evaluation-run and list-ruleset-evaluation-runs; optional filter for list-rulesets and list-data-quality-results).',
            ),
        ] = None,
        table_name: Annotated[
            Optional[str],
            Field(
                description='Name of the target table (required for start-ruleset-evaluation-run and list-ruleset-evaluation-runs; optional filter for list-rulesets and list-data-quality-results).',
            ),
        ] = None,
        ruleset_names: Annotated[
            Optional[List[str]],
            Field(
                description='Names of the rulesets to evaluate (required for start-ruleset-evaluation-run operation).',
            ),
        ] = None,
        role: Annotated[
            Optional[str],
            Field(
                description='IAM role ARN that Glue assumes to run the evaluation (required for start-ruleset-evaluation-run operation).',
            ),
        ] = None,
        run_id: Annotated[
            Optional[str],
            Field(
                description='ID of the evaluation run (required for get-ruleset-evaluation-run operation).',
            ),
        ] = None,
        result_id: Annotated[
            Optional[str],
            Field(
                description='ID of the data quality result (required for get-data-quality-result operation).',
            ),
        ] = None,
        result_ids: Annotated[
            Optional[List[str]],
            Field(
                description='IDs of the data quality results to retrieve (required for batch-get-data-quality-result operation).',
            ),
        ] = None,
        max_results: Annotated[
            Optional[int],
            Field(
                description='Maximum number of results to return for list operations.',
            ),
        ] = None,
        next_token: Annotated[
            Optional[str],
            Field(description='A continuation token, if this is a continuation call.'),
        ] = None,
    ) -> CallToolResult:
        """Manage AWS Glue Data Quality rulesets, evaluation runs, and results.

        This tool provides operations for managing Data Quality Definition Language (DQDL)
        rulesets, running ruleset evaluations against Glue Data Catalog tables, and
        retrieving evaluation results and scores.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create-ruleset, update-ruleset, delete-ruleset, and start-ruleset-evaluation-run operations
        - Appropriate AWS permissions for Glue Data Quality operations
        - start-ruleset-evaluation-run requires an IAM role that Glue can assume to read the target table

        ## Operations
        - **list-rulesets**: List data quality rulesets, optionally filtered to a table
        - **get-ruleset**: Retrieve a specific ruleset's DQDL definition and metadata
        - **create-ruleset**: Create a new ruleset from a DQDL definition
        - **update-ruleset**: Update an existing ruleset's definition or description
        - **delete-ruleset**: Delete an existing ruleset
        - **start-ruleset-evaluation-run**: Evaluate one or more rulesets against a table
        - **get-ruleset-evaluation-run**: Get the status and result IDs of an evaluation run
        - **list-ruleset-evaluation-runs**: List evaluation runs for a table
        - **get-data-quality-result**: Get a single evaluation result, including its score and per-rule outcomes
        - **list-data-quality-results**: List evaluation result summaries, optionally filtered to a table
        - **batch-get-data-quality-result**: Get multiple evaluation results in a single call

        ## Usage Tips
        - Use list-rulesets or get-ruleset to check existing rulesets before creating
        - After start-ruleset-evaluation-run, poll get-ruleset-evaluation-run until Status is SUCCEEDED or FAILED, then use the returned result_ids with get-data-quality-result

        Args:
            ctx: MCP context
            operation: Operation to perform
            name: Name of the ruleset
            ruleset: DQDL ruleset definition
            description: Description of the ruleset
            database_name: Name of the database containing the target table
            table_name: Name of the target table
            ruleset_names: Names of the rulesets to evaluate
            role: IAM role ARN for the evaluation run
            run_id: ID of the evaluation run
            result_id: ID of the data quality result
            result_ids: IDs of the data quality results to retrieve
            max_results: Maximum number of results to return
            next_token: A continuation token, if this is a continuation call

        Returns:
            Union of response types specific to the operation performed
        """
        if operation not in [
            'list-rulesets',
            'get-ruleset',
            'create-ruleset',
            'update-ruleset',
            'delete-ruleset',
            'start-ruleset-evaluation-run',
            'get-ruleset-evaluation-run',
            'list-ruleset-evaluation-runs',
            'get-data-quality-result',
            'list-data-quality-results',
            'batch-get-data-quality-result',
        ]:
            error_message = (
                f'Invalid operation: {operation}. Must be one of: list-rulesets, get-ruleset, '
                'create-ruleset, update-ruleset, delete-ruleset, start-ruleset-evaluation-run, '
                'get-ruleset-evaluation-run, list-ruleset-evaluation-runs, get-data-quality-result, '
                'list-data-quality-results, batch-get-data-quality-result'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

        try:
            if not self.allow_write and operation in [
                'create-ruleset',
                'update-ruleset',
                'delete-ruleset',
                'start-ruleset-evaluation-run',
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                )

            if operation == 'list-rulesets':
                return await self.data_catalog_data_quality_manager.list_rulesets(
                    ctx=ctx,
                    database_name=database_name,
                    table_name=table_name,
                    max_results=max_results,
                    next_token=next_token,
                )

            elif operation == 'get-ruleset':
                if name is None:
                    raise ValueError('name is required for get-ruleset operation')
                return await self.data_catalog_data_quality_manager.get_ruleset(ctx=ctx, name=name)

            elif operation == 'create-ruleset':
                if name is None or ruleset is None:
                    raise ValueError('name and ruleset are required for create-ruleset operation')
                return await self.data_catalog_data_quality_manager.create_ruleset(
                    ctx=ctx,
                    name=name,
                    ruleset=ruleset,
                    description=description,
                    database_name=database_name,
                    table_name=table_name,
                )

            elif operation == 'update-ruleset':
                if name is None:
                    raise ValueError('name is required for update-ruleset operation')
                return await self.data_catalog_data_quality_manager.update_ruleset(
                    ctx=ctx, name=name, ruleset=ruleset, description=description
                )

            elif operation == 'delete-ruleset':
                if name is None:
                    raise ValueError('name is required for delete-ruleset operation')
                return await self.data_catalog_data_quality_manager.delete_ruleset(
                    ctx=ctx, name=name
                )

            elif operation == 'start-ruleset-evaluation-run':
                if (
                    database_name is None
                    or table_name is None
                    or not ruleset_names
                    or role is None
                ):
                    raise ValueError(
                        'database_name, table_name, ruleset_names, and role are required for '
                        'start-ruleset-evaluation-run operation'
                    )
                return await self.data_catalog_data_quality_manager.start_ruleset_evaluation_run(
                    ctx=ctx,
                    database_name=database_name,
                    table_name=table_name,
                    ruleset_names=ruleset_names,
                    role=role,
                )

            elif operation == 'get-ruleset-evaluation-run':
                if run_id is None:
                    raise ValueError('run_id is required for get-ruleset-evaluation-run operation')
                return await self.data_catalog_data_quality_manager.get_ruleset_evaluation_run(
                    ctx=ctx, run_id=run_id
                )

            elif operation == 'list-ruleset-evaluation-runs':
                if database_name is None or table_name is None:
                    raise ValueError(
                        'database_name and table_name are required for '
                        'list-ruleset-evaluation-runs operation'
                    )
                return await self.data_catalog_data_quality_manager.list_ruleset_evaluation_runs(
                    ctx=ctx,
                    database_name=database_name,
                    table_name=table_name,
                    max_results=max_results,
                    next_token=next_token,
                )

            elif operation == 'get-data-quality-result':
                if result_id is None:
                    raise ValueError('result_id is required for get-data-quality-result operation')
                return await self.data_catalog_data_quality_manager.get_data_quality_result(
                    ctx=ctx, result_id=result_id
                )

            elif operation == 'list-data-quality-results':
                return await self.data_catalog_data_quality_manager.list_data_quality_results(
                    ctx=ctx,
                    database_name=database_name,
                    table_name=table_name,
                    max_results=max_results,
                    next_token=next_token,
                )

            elif operation == 'batch-get-data-quality-result':
                if not result_ids:
                    raise ValueError(
                        'result_ids is required for batch-get-data-quality-result operation'
                    )
                return await self.data_catalog_data_quality_manager.batch_get_data_quality_result(
                    ctx=ctx, result_ids=result_ids
                )

            else:
                error_message = (
                    f'Invalid operation: {operation}. Must be one of: list-rulesets, get-ruleset, '
                    'create-ruleset, update-ruleset, delete-ruleset, start-ruleset-evaluation-run, '
                    'get-ruleset-evaluation-run, list-ruleset-evaluation-runs, get-data-quality-result, '
                    'list-data-quality-results, batch-get-data-quality-result'
                )
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_glue_data_quality: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
