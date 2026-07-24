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

"""Data quality manager for AWS Glue Data Catalog operations.

This module provides functionality for managing AWS Glue Data Quality rulesets,
evaluation runs, and results.
"""

import json
from awslabs.aws_dataprocessing_mcp_server.models.data_catalog_models import (
    BatchGetDataQualityResultData,
    CreateDataQualityRulesetData,
    DataQualityResult,
    DataQualityRulesetSummary,
    DeleteDataQualityRulesetData,
    GetDataQualityResultData,
    GetDataQualityRulesetData,
    GetDataQualityRulesetEvaluationRunData,
    ListDataQualityResultsData,
    ListDataQualityRulesetEvaluationRunsData,
    ListDataQualityRulesetsData,
    StartDataQualityRulesetEvaluationRunData,
    UpdateDataQualityRulesetData,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent
from typing import Any, Dict, List, Optional


def _isoformat_or_none(value: Any) -> Optional[str]:
    """Convert a datetime-like value to an ISO string, or return None."""
    return value.isoformat() if hasattr(value, 'isoformat') else value


class DataCatalogDataQualityManager:
    """Manager for AWS Glue Data Quality operations.

    This class provides methods for managing data quality rulesets, running
    ruleset evaluations, and retrieving data quality results for tables in the
    AWS Glue Data Catalog.
    """

    def __init__(self, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the Data Catalog Data Quality Manager.

        Args:
            allow_write: Whether to enable write operations (create/update/delete ruleset, start evaluation run)
            allow_sensitive_data_access: Whether to allow access to sensitive data
        """
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.glue_client = AwsHelper.create_boto3_client('glue')

    async def list_rulesets(
        self,
        ctx: Context,
        database_name: Optional[str] = None,
        table_name: Optional[str] = None,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> CallToolResult:
        """List AWS Glue Data Quality rulesets, optionally filtered to a table.

        Args:
            ctx: MCP context containing request information
            database_name: Optional database name to filter rulesets by target table
            table_name: Optional table name to filter rulesets by target table (requires database_name)
            max_results: Optional maximum number of results to return
            next_token: Optional pagination token for retrieving the next set of results

        Returns:
            ListDataQualityRulesetsResponse with the list of rulesets
        """
        try:
            kwargs: Dict[str, Any] = {}
            if database_name and table_name:
                kwargs['TargetTable'] = {'DatabaseName': database_name, 'TableName': table_name}
            if max_results:
                kwargs['MaxResults'] = max_results
            if next_token:
                kwargs['NextToken'] = next_token

            response = self.glue_client.list_data_quality_rulesets(**kwargs)
            rulesets = response.get('Rulesets', [])
            next_token_response = response.get('NextToken', None)

            log_with_request_id(
                ctx, LogLevel.INFO, f'Successfully listed {len(rulesets)} data quality rulesets'
            )

            success_message = f'Successfully listed {len(rulesets)} data quality rulesets'
            data = ListDataQualityRulesetsData(
                rulesets=[
                    DataQualityRulesetSummary(
                        name=ruleset.get('Name', ''),
                        description=ruleset.get('Description'),
                        target_table=ruleset.get('TargetTable'),
                        created_on=_isoformat_or_none(ruleset.get('CreatedOn')),
                        last_modified_on=_isoformat_or_none(ruleset.get('LastModifiedOn')),
                        rule_count=ruleset.get('RuleCount'),
                    )
                    for ruleset in rulesets
                ],
                count=len(rulesets),
                next_token=next_token_response,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_message),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = (
                f'Failed to list data quality rulesets: {error_code} - '
                f'{e.response["Error"]["Message"]}'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def get_ruleset(self, ctx: Context, name: str) -> CallToolResult:
        """Get an AWS Glue Data Quality ruleset by name.

        Args:
            ctx: MCP context containing request information
            name: Name of the ruleset to retrieve

        Returns:
            GetDataQualityRulesetResponse with the ruleset details
        """
        try:
            response = self.glue_client.get_data_quality_ruleset(Name=name)

            log_with_request_id(
                ctx, LogLevel.INFO, f'Successfully retrieved data quality ruleset: {name}'
            )

            success_message = f'Successfully retrieved data quality ruleset: {name}'
            data = GetDataQualityRulesetData(
                name=response.get('Name', name),
                description=response.get('Description'),
                ruleset=response.get('Ruleset'),
                target_table=response.get('TargetTable'),
                created_on=_isoformat_or_none(response.get('CreatedOn')),
                last_modified_on=_isoformat_or_none(response.get('LastModifiedOn')),
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_message),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = (
                f'Failed to get data quality ruleset {name}: {error_code} - '
                f'{e.response["Error"]["Message"]}'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def create_ruleset(
        self,
        ctx: Context,
        name: str,
        ruleset: str,
        description: Optional[str] = None,
        database_name: Optional[str] = None,
        table_name: Optional[str] = None,
    ) -> CallToolResult:
        """Create an AWS Glue Data Quality ruleset.

        Args:
            ctx: MCP context containing request information
            name: Name of the ruleset to create
            ruleset: DQDL ruleset definition
            description: Optional description of the ruleset
            database_name: Optional database name of the ruleset's target table
            table_name: Optional table name of the ruleset's target table

        Returns:
            CreateDataQualityRulesetResponse with the result of the operation
        """
        try:
            kwargs: Dict[str, Any] = {'Name': name, 'Ruleset': ruleset}
            if description:
                kwargs['Description'] = description
            if database_name and table_name:
                kwargs['TargetTable'] = {'DatabaseName': database_name, 'TableName': table_name}

            self.glue_client.create_data_quality_ruleset(**kwargs)

            log_with_request_id(
                ctx, LogLevel.INFO, f'Successfully created data quality ruleset: {name}'
            )

            success_message = f'Successfully created data quality ruleset: {name}'
            data = CreateDataQualityRulesetData(name=name)

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_message),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = (
                f'Failed to create data quality ruleset {name}: {error_code} - '
                f'{e.response["Error"]["Message"]}'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def update_ruleset(
        self,
        ctx: Context,
        name: str,
        ruleset: Optional[str] = None,
        description: Optional[str] = None,
    ) -> CallToolResult:
        """Update an AWS Glue Data Quality ruleset.

        Args:
            ctx: MCP context containing request information
            name: Name of the ruleset to update
            ruleset: Optional new DQDL ruleset definition
            description: Optional new description of the ruleset

        Returns:
            UpdateDataQualityRulesetResponse with the result of the operation
        """
        try:
            kwargs: Dict[str, Any] = {'Name': name}
            if ruleset:
                kwargs['Ruleset'] = ruleset
            if description:
                kwargs['Description'] = description

            self.glue_client.update_data_quality_ruleset(**kwargs)

            log_with_request_id(
                ctx, LogLevel.INFO, f'Successfully updated data quality ruleset: {name}'
            )

            success_message = f'Successfully updated data quality ruleset: {name}'
            data = UpdateDataQualityRulesetData(name=name)

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_message),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = (
                f'Failed to update data quality ruleset {name}: {error_code} - '
                f'{e.response["Error"]["Message"]}'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def delete_ruleset(self, ctx: Context, name: str) -> CallToolResult:
        """Delete an AWS Glue Data Quality ruleset.

        Args:
            ctx: MCP context containing request information
            name: Name of the ruleset to delete

        Returns:
            DeleteDataQualityRulesetResponse with the result of the operation
        """
        try:
            self.glue_client.delete_data_quality_ruleset(Name=name)

            log_with_request_id(
                ctx, LogLevel.INFO, f'Successfully deleted data quality ruleset: {name}'
            )

            success_message = f'Successfully deleted data quality ruleset: {name}'
            data = DeleteDataQualityRulesetData(name=name)

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_message),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = (
                f'Failed to delete data quality ruleset {name}: {error_code} - '
                f'{e.response["Error"]["Message"]}'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def start_ruleset_evaluation_run(
        self,
        ctx: Context,
        database_name: str,
        table_name: str,
        ruleset_names: List[str],
        role: str,
    ) -> CallToolResult:
        """Start an AWS Glue Data Quality ruleset evaluation run against a table.

        Args:
            ctx: MCP context containing request information
            database_name: Name of the database containing the table to evaluate
            table_name: Name of the table to evaluate
            ruleset_names: Names of the rulesets to evaluate against the table
            role: IAM role ARN Glue assumes to run the evaluation

        Returns:
            StartDataQualityRulesetEvaluationRunResponse with the started run ID
        """
        try:
            response = self.glue_client.start_data_quality_ruleset_evaluation_run(
                DataSource={'GlueTable': {'DatabaseName': database_name, 'TableName': table_name}},
                Role=role,
                RulesetNames=ruleset_names,
            )
            run_id = response['RunId']

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully started data quality ruleset evaluation run {run_id} for table {database_name}.{table_name}',
            )

            success_message = f'Successfully started data quality ruleset evaluation run {run_id} for table {database_name}.{table_name}'
            data = StartDataQualityRulesetEvaluationRunData(run_id=run_id)

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_message),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = (
                f'Failed to start data quality ruleset evaluation run for table '
                f'{database_name}.{table_name}: {error_code} - {e.response["Error"]["Message"]}'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def get_ruleset_evaluation_run(self, ctx: Context, run_id: str) -> CallToolResult:
        """Get the status and results of an AWS Glue Data Quality ruleset evaluation run.

        Args:
            ctx: MCP context containing request information
            run_id: ID of the evaluation run to retrieve

        Returns:
            GetDataQualityRulesetEvaluationRunResponse with the run details
        """
        try:
            response = self.glue_client.get_data_quality_ruleset_evaluation_run(RunId=run_id)

            log_with_request_id(
                ctx, LogLevel.INFO, f'Successfully retrieved data quality evaluation run: {run_id}'
            )

            success_message = f'Successfully retrieved data quality evaluation run: {run_id}'
            data = GetDataQualityRulesetEvaluationRunData(
                run_id=run_id,
                status=response.get('Status'),
                ruleset_names=response.get('RulesetNames', []),
                result_ids=response.get('ResultIds', []),
                started_on=_isoformat_or_none(response.get('StartedOn')),
                completed_on=_isoformat_or_none(response.get('CompletedOn')),
                error_string=response.get('ErrorString'),
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_message),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = (
                f'Failed to get data quality evaluation run {run_id}: {error_code} - '
                f'{e.response["Error"]["Message"]}'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def list_ruleset_evaluation_runs(
        self,
        ctx: Context,
        database_name: str,
        table_name: str,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> CallToolResult:
        """List AWS Glue Data Quality ruleset evaluation runs for a table.

        Args:
            ctx: MCP context containing request information
            database_name: Name of the database containing the table
            table_name: Name of the table to list evaluation runs for
            max_results: Optional maximum number of results to return
            next_token: Optional pagination token for retrieving the next set of results

        Returns:
            ListDataQualityRulesetEvaluationRunsResponse with the list of evaluation runs
        """
        try:
            kwargs: Dict[str, Any] = {
                'DataSource': {
                    'GlueTable': {'DatabaseName': database_name, 'TableName': table_name}
                }
            }
            if max_results:
                kwargs['MaxResults'] = max_results
            if next_token:
                kwargs['NextToken'] = next_token

            response = self.glue_client.list_data_quality_ruleset_evaluation_runs(**kwargs)
            runs = response.get('Runs', [])
            next_token_response = response.get('NextToken', None)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully listed {len(runs)} data quality evaluation runs for table {database_name}.{table_name}',
            )

            success_message = f'Successfully listed {len(runs)} data quality evaluation runs for table {database_name}.{table_name}'
            data = ListDataQualityRulesetEvaluationRunsData(
                runs=runs,
                count=len(runs),
                next_token=next_token_response,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_message),
                    TextContent(type='text', text=json.dumps(data.model_dump(), default=str)),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = (
                f'Failed to list data quality evaluation runs for table '
                f'{database_name}.{table_name}: {error_code} - {e.response["Error"]["Message"]}'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def get_data_quality_result(self, ctx: Context, result_id: str) -> CallToolResult:
        """Get an AWS Glue Data Quality evaluation result by ID.

        Args:
            ctx: MCP context containing request information
            result_id: ID of the data quality result to retrieve

        Returns:
            GetDataQualityResultResponse with the result details
        """
        try:
            response = self.glue_client.get_data_quality_result(ResultId=result_id)

            log_with_request_id(
                ctx, LogLevel.INFO, f'Successfully retrieved data quality result: {result_id}'
            )

            success_message = f'Successfully retrieved data quality result: {result_id}'
            data = GetDataQualityResultData(
                result=DataQualityResult(
                    result_id=response.get('ResultId', result_id),
                    score=response.get('Score'),
                    started_on=_isoformat_or_none(response.get('StartedOn')),
                    completed_on=_isoformat_or_none(response.get('CompletedOn')),
                    rule_results=response.get('RuleResults', []),
                )
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_message),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = (
                f'Failed to get data quality result {result_id}: {error_code} - '
                f'{e.response["Error"]["Message"]}'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def list_data_quality_results(
        self,
        ctx: Context,
        database_name: Optional[str] = None,
        table_name: Optional[str] = None,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> CallToolResult:
        """List AWS Glue Data Quality evaluation results, optionally filtered to a table.

        Args:
            ctx: MCP context containing request information
            database_name: Optional database name to filter results by table
            table_name: Optional table name to filter results by table (requires database_name)
            max_results: Optional maximum number of results to return
            next_token: Optional pagination token for retrieving the next set of results

        Returns:
            ListDataQualityResultsResponse with the list of results
        """
        try:
            kwargs: Dict[str, Any] = {}
            if database_name and table_name:
                kwargs['Filter'] = {
                    'DataSource': {
                        'GlueTable': {'DatabaseName': database_name, 'TableName': table_name}
                    }
                }
            if max_results:
                kwargs['MaxResults'] = max_results
            if next_token:
                kwargs['NextToken'] = next_token

            response = self.glue_client.list_data_quality_results(**kwargs)
            results = response.get('Results', [])
            next_token_response = response.get('NextToken', None)

            log_with_request_id(
                ctx, LogLevel.INFO, f'Successfully listed {len(results)} data quality results'
            )

            success_message = f'Successfully listed {len(results)} data quality results'
            data = ListDataQualityResultsData(
                results=results,
                count=len(results),
                next_token=next_token_response,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_message),
                    TextContent(type='text', text=json.dumps(data.model_dump(), default=str)),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = (
                f'Failed to list data quality results: {error_code} - '
                f'{e.response["Error"]["Message"]}'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def batch_get_data_quality_result(
        self, ctx: Context, result_ids: List[str]
    ) -> CallToolResult:
        """Get multiple AWS Glue Data Quality evaluation results in a single call.

        Args:
            ctx: MCP context containing request information
            result_ids: IDs of the data quality results to retrieve

        Returns:
            BatchGetDataQualityResultResponse with the found results and any not found
        """
        try:
            response = self.glue_client.batch_get_data_quality_result(ResultIds=result_ids)
            results = response.get('Results', [])
            results_not_found = response.get('ResultsNotFound', [])

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully retrieved {len(results)} of {len(result_ids)} data quality results',
            )

            success_message = (
                f'Successfully retrieved {len(results)} of {len(result_ids)} data quality results'
            )
            data = BatchGetDataQualityResultData(
                results=[
                    DataQualityResult(
                        result_id=result.get('ResultId', ''),
                        score=result.get('Score'),
                        started_on=_isoformat_or_none(result.get('StartedOn')),
                        completed_on=_isoformat_or_none(result.get('CompletedOn')),
                        rule_results=result.get('RuleResults', []),
                    )
                    for result in results
                ],
                results_not_found=results_not_found,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_message),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = (
                f'Failed to batch get data quality results: {error_code} - '
                f'{e.response["Error"]["Message"]}'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
