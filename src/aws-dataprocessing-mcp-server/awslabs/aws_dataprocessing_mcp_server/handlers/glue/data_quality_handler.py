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

"""DataQualityHandler for Data Processing MCP Server."""

import time
from awslabs.aws_dataprocessing_mcp_server.models.glue_models import (
    DataQualityEvaluationRunResponse,
    DataQualityRecommendationRunResponse,
    DataQualityRulesetResponse,
    DataQualityMetricsResponse,
    RulesetSummary,
    EvaluationRunSummary,
    RecommendationRunSummary,
    DataQualityResult,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional, Union


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
        self.glue_client = AwsHelper.create_boto3_client('glue')

        # Register tools
        self.mcp.tool(name='manage_aws_glue_data_quality_rulesets')(
            self.manage_aws_glue_data_quality_rulesets
        )
        self.mcp.tool(name='manage_aws_glue_data_quality_evaluation_runs')(
            self.manage_aws_glue_data_quality_evaluation_runs
        )
        self.mcp.tool(name='manage_aws_glue_data_quality_recommendation_runs')(
            self.manage_aws_glue_data_quality_recommendation_runs
        )
        self.mcp.tool(name='manage_aws_glue_data_quality_metrics')(
            self.manage_aws_glue_data_quality_metrics
        )

    async def manage_aws_glue_data_quality_rulesets(
        self,
        ctx: Context,
        operation: Annotated[
            str,
            Field(
                description='Operation to perform: create-ruleset, get-ruleset, list-rulesets, update-ruleset, delete-ruleset, append-ruleset, get-table-rulesets. Choose read operations when write access is disabled.',
            ),
        ],
        ruleset_name: Annotated[
            Optional[str],
            Field(
                description='Name of the data quality ruleset (required for create-ruleset, get-ruleset, update-ruleset, delete-ruleset, append-ruleset operations).',
            ),
        ] = None,
        database_name: Annotated[
            Optional[str],
            Field(
                description='Name of the Glue database (required for create-ruleset and get-table-rulesets operations).',
            ),
        ] = None,
        table_name: Annotated[
            Optional[str],
            Field(
                description='Name of the table (required for create-ruleset and get-table-rulesets operations).',
            ),
        ] = None,
        catalog_id: Annotated[
            Optional[str],
            Field(
                description='Catalog ID (optional, defaults to caller account).',
            ),
        ] = None,
        ruleset_definition: Annotated[
            Optional[str],
            Field(
                description='DQDL ruleset definition (required for create-ruleset and update-ruleset operations). For append-ruleset, provide the new rules to add to the existing ruleset.',
            ),
        ] = None,
        description: Annotated[
            Optional[str],
            Field(
                description='Description of the ruleset (optional for create-ruleset operation).',
            ),
        ] = None,
        tags: Annotated[
            Optional[Dict[str, str]],
            Field(
                description='Tags to apply to the ruleset (optional for create-ruleset operation).',
            ),
        ] = None,
    ) -> Union[DataQualityRulesetResponse, TextContent]:
        """Manage AWS Glue Data Quality rulesets.

        This tool allows you to create, retrieve, list, update, delete, and append data quality rulesets,
        as well as get rulesets associated with specific tables.

        Args:
            ctx: The MCP context
            operation: The operation to perform
            ruleset_name: Name of the ruleset
            database_name: Name of the database
            table_name: Name of the table
            catalog_id: Catalog ID
            ruleset_definition: DQDL ruleset definition
            description: Description of the ruleset
            tags: Tags for the ruleset

        Returns:
            DataQualityRulesetResponse or TextContent with operation results
        """
        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Managing Glue data quality rulesets with operation: {operation}',
        )

        try:
            if operation == 'create-ruleset':
                return await self._create_ruleset(
                    ctx, ruleset_name, database_name, table_name, ruleset_definition,
                    catalog_id, description, tags
                )
            elif operation == 'get-ruleset':
                return await self._get_ruleset(ctx, ruleset_name)
            elif operation == 'list-rulesets':
                return await self._list_rulesets(ctx, database_name, table_name)
            elif operation == 'update-ruleset':
                return await self._update_ruleset(ctx, ruleset_name, ruleset_definition, description)
            elif operation == 'delete-ruleset':
                return await self._delete_ruleset(ctx, ruleset_name)
            elif operation == 'append-ruleset':
                return await self._append_ruleset(ctx, ruleset_name, ruleset_definition)
            elif operation == 'get-table-rulesets':
                return await self._get_table_rulesets(ctx, database_name, table_name, catalog_id)
            else:
                error_msg = f'Unsupported operation: {operation}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return TextContent(type='text', text=error_msg)

        except Exception as e:
            error_msg = f'Error managing data quality rulesets: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)
            return TextContent(type='text', text=error_msg)

    async def manage_aws_glue_data_quality_evaluation_runs(
        self,
        ctx: Context,
        operation: Annotated[
            str,
            Field(
                description='Operation to perform: start-evaluation-run, get-evaluation-run, list-evaluation-runs, cancel-evaluation-run. Choose read operations when write access is disabled.',
            ),
        ],
        database_name: Annotated[
            Optional[str],
            Field(
                description='Name of the Glue database (required for start-evaluation-run and list-evaluation-runs operations).',
            ),
        ] = None,
        table_name: Annotated[
            Optional[str],
            Field(
                description='Name of the table (required for start-evaluation-run and list-evaluation-runs operations).',
            ),
        ] = None,
        catalog_id: Annotated[
            Optional[str],
            Field(
                description='Catalog ID (optional, defaults to caller account).',
            ),
        ] = None,
        ruleset_names: Annotated[
            Optional[List[str]],
            Field(
                description='List of ruleset names to evaluate (required for start-evaluation-run operation).',
            ),
        ] = None,
        run_id: Annotated[
            Optional[str],
            Field(
                description='Run ID (required for get-evaluation-run and cancel-evaluation-run operations).',
            ),
        ] = None,
        role_arn: Annotated[
            Optional[str],
            Field(
                description='IAM role ARN for the evaluation run (required for start-evaluation-run operation).',
            ),
        ] = None,
        number_of_workers: Annotated[
            Optional[int],
            Field(
                description='Number of workers for the evaluation run (optional, defaults to 5).',
            ),
        ] = None,
        timeout: Annotated[
            Optional[int],
            Field(
                description='Timeout in minutes for the evaluation run (optional, defaults to 2880).',
            ),
        ] = None,
    ) -> Union[DataQualityEvaluationRunResponse, TextContent]:
        """Manage AWS Glue Data Quality evaluation runs.

        This tool allows you to start, retrieve, list, and cancel data quality evaluation runs.

        Args:
            ctx: The MCP context
            operation: The operation to perform
            database_name: Name of the database
            table_name: Name of the table
            catalog_id: Catalog ID
            ruleset_names: List of ruleset names
            run_id: Run ID
            role_arn: IAM role ARN
            number_of_workers: Number of workers
            timeout: Timeout in minutes

        Returns:
            DataQualityEvaluationRunResponse or TextContent with operation results
        """
        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Managing Glue data quality evaluation runs with operation: {operation}',
        )

        try:
            if operation == 'start-evaluation-run':
                return await self._start_evaluation_run(
                    ctx, database_name, table_name, ruleset_names, role_arn,
                    catalog_id, number_of_workers, timeout
                )
            elif operation == 'get-evaluation-run':
                return await self._get_evaluation_run(ctx, run_id)
            elif operation == 'list-evaluation-runs':
                return await self._list_evaluation_runs(ctx, database_name, table_name, catalog_id)
            elif operation == 'cancel-evaluation-run':
                return await self._cancel_evaluation_run(ctx, run_id)
            else:
                error_msg = f'Unsupported operation: {operation}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return TextContent(type='text', text=error_msg)

        except Exception as e:
            error_msg = f'Error managing data quality evaluation runs: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)
            return TextContent(type='text', text=error_msg)

    async def manage_aws_glue_data_quality_recommendation_runs(
        self,
        ctx: Context,
        operation: Annotated[
            str,
            Field(
                description='Operation to perform: start-recommendation-run, get-recommendation-run, cancel-recommendation-run. Choose read operations when write access is disabled.',
            ),
        ],
        database_name: Annotated[
            Optional[str],
            Field(
                description='Name of the Glue database (required for start-recommendation-run operation).',
            ),
        ] = None,
        table_name: Annotated[
            Optional[str],
            Field(
                description='Name of the table (required for start-recommendation-run operation).',
            ),
        ] = None,
        catalog_id: Annotated[
            Optional[str],
            Field(
                description='Catalog ID (optional, defaults to caller account).',
            ),
        ] = None,
        run_id: Annotated[
            Optional[str],
            Field(
                description='Run ID (required for get-recommendation-run and cancel-recommendation-run operations).',
            ),
        ] = None,
        role_arn: Annotated[
            Optional[str],
            Field(
                description='IAM role ARN for the recommendation run (required for start-recommendation-run operation).',
            ),
        ] = None,
        created_ruleset_name: Annotated[
            Optional[str],
            Field(
                description='Name for the created ruleset (optional for start-recommendation-run operation).',
            ),
        ] = None,
        number_of_workers: Annotated[
            Optional[int],
            Field(
                description='Number of workers for the recommendation run (optional, defaults to 5).',
            ),
        ] = None,
        timeout: Annotated[
            Optional[int],
            Field(
                description='Timeout in minutes for the recommendation run (optional, defaults to 2880).',
            ),
        ] = None,
    ) -> Union[DataQualityRecommendationRunResponse, TextContent]:
        """Manage AWS Glue Data Quality recommendation runs.

        This tool allows you to start, retrieve, and cancel data quality rule recommendation runs.

        Args:
            ctx: The MCP context
            operation: The operation to perform
            database_name: Name of the database
            table_name: Name of the table
            catalog_id: Catalog ID
            run_id: Run ID
            role_arn: IAM role ARN
            created_ruleset_name: Name for created ruleset
            number_of_workers: Number of workers
            timeout: Timeout in minutes

        Returns:
            DataQualityRecommendationRunResponse or TextContent with operation results
        """
        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Managing Glue data quality recommendation runs with operation: {operation}',
        )

        try:
            if operation == 'start-recommendation-run':
                return await self._start_recommendation_run(
                    ctx, database_name, table_name, role_arn, catalog_id,
                    created_ruleset_name, number_of_workers, timeout
                )
            elif operation == 'get-recommendation-run':
                return await self._get_recommendation_run(ctx, run_id)
            elif operation == 'cancel-recommendation-run':
                return await self._cancel_recommendation_run(ctx, run_id)
            else:
                error_msg = f'Unsupported operation: {operation}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return TextContent(type='text', text=error_msg)

        except Exception as e:
            error_msg = f'Error managing data quality recommendation runs: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)
            return TextContent(type='text', text=error_msg)

    async def manage_aws_glue_data_quality_metrics(
        self,
        ctx: Context,
        operation: Annotated[
            str,
            Field(
                description='Operation to perform: get-result, list-results. Choose these operations to retrieve data quality metrics and results.',
            ),
        ],
        result_id: Annotated[
            Optional[str],
            Field(
                description='Result ID (required for get-result operation).',
            ),
        ] = None,
        database_name: Annotated[
            Optional[str],
            Field(
                description='Name of the Glue database (optional for list-results operation).',
            ),
        ] = None,
        table_name: Annotated[
            Optional[str],
            Field(
                description='Name of the table (optional for list-results operation).',
            ),
        ] = None,
        catalog_id: Annotated[
            Optional[str],
            Field(
                description='Catalog ID (optional, defaults to caller account).',
            ),
        ] = None,
    ) -> Union[DataQualityMetricsResponse, TextContent]:
        """Manage AWS Glue Data Quality metrics and results.

        This tool allows you to retrieve data quality results and metrics from evaluation runs.

        Args:
            ctx: The MCP context
            operation: The operation to perform
            result_id: Result ID
            database_name: Name of the database
            table_name: Name of the table
            catalog_id: Catalog ID

        Returns:
            DataQualityMetricsResponse or TextContent with operation results
        """
        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Managing Glue data quality metrics with operation: {operation}',
        )

        try:
            if operation == 'get-result':
                return await self._get_data_quality_result(ctx, result_id)
            elif operation == 'list-results':
                return await self._list_data_quality_results(ctx, database_name, table_name, catalog_id)
            else:
                error_msg = f'Unsupported operation: {operation}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return TextContent(type='text', text=error_msg)

        except Exception as e:
            error_msg = f'Error managing data quality metrics: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)
            return TextContent(type='text', text=error_msg)

    # Private implementation methods

    async def _create_ruleset(
        self,
        ctx: Context,
        ruleset_name: str,
        database_name: str,
        table_name: str,
        ruleset_definition: str,
        catalog_id: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> DataQualityRulesetResponse:
        """Create a new data quality ruleset."""
        if not self.allow_write:
            raise ValueError('Write access is required for create-ruleset operation')

        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Creating data quality ruleset: {ruleset_name} for table {database_name}.{table_name}',
        )

        # Add timestamp to ruleset name to ensure uniqueness
        timestamped_name = f"{ruleset_name}_{time.strftime('%Y%m%d_%H%M%S')}"
        
        # Prepare target table
        target_table = {
            'TableName': table_name,
            'DatabaseName': database_name,
        }
        if catalog_id:
            target_table['CatalogId'] = catalog_id

        # Prepare request parameters
        create_params = {
            'Name': timestamped_name,
            'Ruleset': ruleset_definition,
            'TargetTable': target_table,
        }

        if description:
            create_params['Description'] = description

        # Add MCP management tags
        ruleset_tags = AwsHelper.prepare_resource_tags('DataQualityRuleset', tags)
        
        if ruleset_tags:
            create_params['Tags'] = ruleset_tags

        response = self.glue_client.create_data_quality_ruleset(**create_params)

        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Successfully created data quality ruleset: {timestamped_name}',
        )

        return DataQualityRulesetResponse(
            ruleset_name=timestamped_name,
            description=description or '',
            ruleset_definition=ruleset_definition,
            target_table=f"{database_name}.{table_name}",
            status='CREATED',
            message=f'Data quality ruleset {timestamped_name} created successfully',
        )

    async def _get_ruleset(self, ctx: Context, ruleset_name: str) -> DataQualityRulesetResponse:
        """Get details of a data quality ruleset."""
        log_with_request_id(ctx, LogLevel.INFO, f'Getting data quality ruleset: {ruleset_name}')

        response = self.glue_client.get_data_quality_ruleset(Name=ruleset_name)

        target_table = response.get('TargetTable', {})
        table_name = f"{target_table.get('DatabaseName', '')}.{target_table.get('TableName', '')}"

        return DataQualityRulesetResponse(
            ruleset_name=response.get('Name', ''),
            description=response.get('Description', ''),
            ruleset_definition=response.get('Ruleset', ''),
            target_table=table_name,
            created_on=str(response.get('CreatedOn', '')),
            last_modified_on=str(response.get('LastModifiedOn', '')),
            status='RETRIEVED',
            message=f'Data quality ruleset {ruleset_name} retrieved successfully',
        )

    async def _list_rulesets(
        self,
        ctx: Context,
        database_name: Optional[str] = None,
        table_name: Optional[str] = None,
    ) -> DataQualityRulesetResponse:
        """List data quality rulesets."""
        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Listing data quality rulesets for {database_name}.{table_name}' if database_name and table_name else 'Listing all data quality rulesets',
        )

        list_params = {}
        
        # Add filter if table is specified
        if database_name and table_name:
            list_params['Filter'] = {
                'TargetTable': {
                    'DatabaseName': database_name,
                    'TableName': table_name,
                }
            }

        response = self.glue_client.list_data_quality_rulesets(**list_params)
        rulesets = response.get('Rulesets', [])

        ruleset_summaries = []
        for ruleset in rulesets:
            target_table = ruleset.get('TargetTable', {})
            table_name_full = f"{target_table.get('DatabaseName', '')}.{target_table.get('TableName', '')}"
            
            ruleset_summaries.append(RulesetSummary(
                name=ruleset.get('Name', ''),
                description=ruleset.get('Description', ''),
                target_table=table_name_full,
                created_on=str(ruleset.get('CreatedOn', '')),
                last_modified_on=str(ruleset.get('LastModifiedOn', '')),
            ))

        return DataQualityRulesetResponse(
            rulesets=ruleset_summaries,
            ruleset_count=len(ruleset_summaries),
            status='LISTED',
            message=f'Found {len(ruleset_summaries)} data quality rulesets',
        )

    async def _update_ruleset(
        self,
        ctx: Context,
        ruleset_name: str,
        ruleset_definition: str,
        description: Optional[str] = None,
    ) -> DataQualityRulesetResponse:
        """Update an existing data quality ruleset."""
        if not self.allow_write:
            raise ValueError('Write access is required for update-ruleset operation')

        log_with_request_id(ctx, LogLevel.INFO, f'Updating data quality ruleset: {ruleset_name}')

        update_params = {
            'Name': ruleset_name,
            'Ruleset': ruleset_definition,
        }

        if description:
            update_params['Description'] = description

        response = self.glue_client.update_data_quality_ruleset(**update_params)

        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Successfully updated data quality ruleset: {ruleset_name}',
        )

        return DataQualityRulesetResponse(
            ruleset_name=ruleset_name,
            description=description or '',
            ruleset_definition=ruleset_definition,
            status='UPDATED',
            message=f'Data quality ruleset {ruleset_name} updated successfully',
        )

    async def _delete_ruleset(self, ctx: Context, ruleset_name: str) -> DataQualityRulesetResponse:
        """Delete a data quality ruleset."""
        if not self.allow_write:
            raise ValueError('Write access is required for delete-ruleset operation')

        log_with_request_id(ctx, LogLevel.INFO, f'Deleting data quality ruleset: {ruleset_name}')

        # Check if ruleset exists first
        try:
            self.glue_client.get_data_quality_ruleset(Name=ruleset_name)
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                error_msg = f'Ruleset {ruleset_name} not found'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                raise ValueError(error_msg)
            raise

        response = self.glue_client.delete_data_quality_ruleset(Name=ruleset_name)

        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Successfully deleted data quality ruleset: {ruleset_name}',
        )

        return DataQualityRulesetResponse(
            ruleset_name=ruleset_name,
            status='DELETED',
            message=f'Data quality ruleset {ruleset_name} deleted successfully',
        )

    async def _append_ruleset(
        self, 
        ctx: Context, 
        ruleset_name: str, 
        new_rules: str
    ) -> DataQualityRulesetResponse:
        """Append new rules to an existing data quality ruleset."""
        if not self.allow_write:
            raise ValueError('Write access is required for append-ruleset operation')

        log_with_request_id(ctx, LogLevel.INFO, f'Appending rules to data quality ruleset: {ruleset_name}')

        try:
            # Get the current ruleset content
            ruleset_detail = self.glue_client.get_data_quality_ruleset(Name=ruleset_name)
            current_rules = ruleset_detail.get('Ruleset', '')
            
            if not current_rules:
                raise ValueError(f'Ruleset {ruleset_name} has no existing rules to append to')

            # Parse the current DQDL format and append new rules
            # DQDL format is: Rules = [ rule1, rule2, ... ]
            # We need to remove the closing ']' and add new rules with proper formatting
            if current_rules.strip().endswith(']'):
                # Remove the closing bracket and any trailing whitespace
                base_rules = current_rules.rstrip().rstrip(']').rstrip()
                
                # Add comma if there are existing rules (not just "Rules = [")
                if not base_rules.strip().endswith('['):
                    base_rules += ','
                
                # Append new rules with proper formatting
                updated_rules = f"{base_rules}\n    {new_rules}\n]"
            else:
                # If the current rules don't end with ']', assume they're malformed
                # Try to append anyway by adding the new rules
                updated_rules = f"{current_rules.rstrip()},\n    {new_rules}"

            # Update the ruleset with the combined rules
            response = self.glue_client.update_data_quality_ruleset(
                Name=ruleset_name,
                Ruleset=updated_rules
            )

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully appended rules to data quality ruleset: {ruleset_name}',
            )

            return DataQualityRulesetResponse(
                ruleset_name=ruleset_name,
                ruleset_definition=updated_rules,
                status='APPENDED',
                message=f'Successfully appended new rules to data quality ruleset {ruleset_name}',
            )

        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                error_msg = f'Ruleset {ruleset_name} not found'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                raise ValueError(error_msg)
            raise

    async def _get_table_rulesets(
        self,
        ctx: Context,
        database_name: str,
        table_name: str,
        catalog_id: Optional[str] = None,
    ) -> DataQualityRulesetResponse:
        """Get data quality rulesets for a specific table."""
        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Getting data quality rulesets for table {database_name}.{table_name}',
        )

        # Prepare filter for the table
        target_table_filter = {
            'DatabaseName': database_name,
            'TableName': table_name,
        }
        if catalog_id:
            target_table_filter['CatalogId'] = catalog_id

        response = self.glue_client.list_data_quality_rulesets(
            Filter={'TargetTable': target_table_filter}
        )

        rulesets = response.get('Rulesets', [])
        ruleset_summaries = []

        for ruleset in rulesets:
            # Get detailed ruleset information
            try:
                ruleset_detail = self.glue_client.get_data_quality_ruleset(
                    Name=ruleset.get('Name')
                )
                
                ruleset_summaries.append(RulesetSummary(
                    name=ruleset.get('Name', ''),
                    description=ruleset.get('Description', ''),
                    target_table=f"{database_name}.{table_name}",
                    created_on=str(ruleset.get('CreatedOn', '')),
                    last_modified_on=str(ruleset.get('LastModifiedOn', '')),
                    ruleset_definition=ruleset_detail.get('Ruleset', ''),
                    rule_count=len(ruleset_detail.get('Ruleset', '').splitlines()) if ruleset_detail.get('Ruleset') else 0,
                ))
            except ClientError as e:
                log_with_request_id(
                    ctx,
                    LogLevel.WARNING,
                    f'Could not get details for ruleset {ruleset.get("Name")}: {str(e)}',
                )
                ruleset_summaries.append(RulesetSummary(
                    name=ruleset.get('Name', ''),
                    description=ruleset.get('Description', ''),
                    target_table=f"{database_name}.{table_name}",
                    created_on=str(ruleset.get('CreatedOn', '')),
                    last_modified_on=str(ruleset.get('LastModifiedOn', '')),
                    error='Error retrieving ruleset details',
                ))

        return DataQualityRulesetResponse(
            rulesets=ruleset_summaries,
            ruleset_count=len(ruleset_summaries),
            target_table=f"{database_name}.{table_name}",
            status='RETRIEVED',
            message=f'Found {len(ruleset_summaries)} rulesets for table {database_name}.{table_name}',
        )

    async def _start_evaluation_run(
        self,
        ctx: Context,
        database_name: str,
        table_name: str,
        ruleset_names: List[str],
        role_arn: Optional[str] = None,
        catalog_id: Optional[str] = None,
        number_of_workers: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> DataQualityEvaluationRunResponse:
        """Start a data quality evaluation run."""
        if not self.allow_write:
            raise ValueError('Write access is required for start-evaluation-run operation')

        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Starting data quality evaluation run for {database_name}.{table_name}',
        )

        # Prepare data source
        data_source = {
            'GlueTable': {
                'DatabaseName': database_name,
                'TableName': table_name,
            }
        }
        if catalog_id:
            data_source['GlueTable']['CatalogId'] = catalog_id

        # Validate required parameters
        if not role_arn:
            raise ValueError('role_arn parameter is required for data quality evaluation runs')

        # Prepare request parameters
        run_params = {
            'DataSource': data_source,
            'Role': role_arn,
            'RulesetNames': ruleset_names,
        }

        # Use provided values or sensible defaults
        run_params['NumberOfWorkers'] = number_of_workers or 5
        run_params['Timeout'] = timeout or 2880  # 48 hours default

        response = self.glue_client.start_data_quality_ruleset_evaluation_run(**run_params)
        run_id = response.get('RunId')

        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Successfully started evaluation run with ID: {run_id}',
        )

        return DataQualityEvaluationRunResponse(
            run_id=run_id,
            status='STARTED',
            database_name=database_name,
            table_name=table_name,
            ruleset_names=ruleset_names,
            message=f'Data quality evaluation run {run_id} started successfully',
        )

    async def _get_evaluation_run(self, ctx: Context, run_id: str) -> DataQualityEvaluationRunResponse:
        """Get details of a data quality evaluation run."""
        if not self.allow_sensitive_data_access:
            raise ValueError('Sensitive data access is required for get-evaluation-run operation')

        log_with_request_id(ctx, LogLevel.INFO, f'Getting data quality evaluation run: {run_id}')

        response = self.glue_client.get_data_quality_ruleset_evaluation_run(RunId=run_id)

        data_source = response.get('DataSource', {}).get('GlueTable', {})
        database_name = data_source.get('DatabaseName', '')
        table_name = data_source.get('TableName', '')

        return DataQualityEvaluationRunResponse(
            run_id=run_id,
            status=response.get('Status', ''),
            database_name=database_name,
            table_name=table_name,
            ruleset_names=response.get('RulesetNames', []),
            role_arn=response.get('Role', ''),
            number_of_workers=response.get('NumberOfWorkers'),
            timeout=response.get('Timeout'),
            started_on=str(response.get('StartedOn', '')),
            completed_on=str(response.get('CompletedOn', '')),
            execution_time=response.get('ExecutionTime'),
            result_ids=response.get('ResultIds', []),
            error_string=response.get('ErrorString', ''),
            message=f'Data quality evaluation run {run_id} retrieved successfully',
        )

    async def _list_evaluation_runs(
        self,
        ctx: Context,
        database_name: Optional[str] = None,
        table_name: Optional[str] = None,
        catalog_id: Optional[str] = None,
    ) -> DataQualityEvaluationRunResponse:
        """List data quality evaluation runs."""
        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Listing data quality evaluation runs for {database_name}.{table_name}' if database_name and table_name else 'Listing all evaluation runs',
        )

        list_params = {}
        
        # Add filter if table is specified
        if database_name and table_name:
            data_source_filter = {
                'GlueTable': {
                    'DatabaseName': database_name,
                    'TableName': table_name,
                }
            }
            if catalog_id:
                data_source_filter['GlueTable']['CatalogId'] = catalog_id
            
            list_params['Filter'] = {'DataSource': data_source_filter}

        response = self.glue_client.list_data_quality_ruleset_evaluation_runs(**list_params)
        runs = response.get('Runs', [])

        evaluation_runs = []
        for run in runs:
            data_source = run.get('DataSource', {}).get('GlueTable', {})
            db_name = data_source.get('DatabaseName', '')
            tbl_name = data_source.get('TableName', '')
            
            evaluation_runs.append(EvaluationRunSummary(
                run_id=run.get('RunId', ''),
                status=run.get('Status', ''),
                database_name=db_name,
                table_name=tbl_name,
                started_on=str(run.get('StartedOn', '')),
                completed_on=str(run.get('CompletedOn', '')),
                execution_time=run.get('ExecutionTime'),
            ))

        return DataQualityEvaluationRunResponse(
            evaluation_runs=evaluation_runs,
            run_count=len(evaluation_runs),
            status='LISTED',
            message=f'Found {len(evaluation_runs)} evaluation runs',
        )

    async def _cancel_evaluation_run(self, ctx: Context, run_id: str) -> DataQualityEvaluationRunResponse:
        """Cancel a data quality evaluation run."""
        if not self.allow_write:
            raise ValueError('Write access is required for cancel-evaluation-run operation')

        log_with_request_id(ctx, LogLevel.INFO, f'Cancelling data quality evaluation run: {run_id}')

        response = self.glue_client.cancel_data_quality_ruleset_evaluation_run(RunId=run_id)

        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Successfully cancelled evaluation run: {run_id}',
        )

        return DataQualityEvaluationRunResponse(
            run_id=run_id,
            status='CANCELLED',
            message=f'Data quality evaluation run {run_id} cancelled successfully',
        )

    async def _start_recommendation_run(
        self,
        ctx: Context,
        database_name: str,
        table_name: str,
        role_arn: Optional[str] = None,
        catalog_id: Optional[str] = None,
        created_ruleset_name: Optional[str] = None,
        number_of_workers: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> DataQualityRecommendationRunResponse:
        """Start a data quality rule recommendation run."""
        if not self.allow_write:
            raise ValueError('Write access is required for start-recommendation-run operation')

        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Starting data quality recommendation run for {database_name}.{table_name}',
        )

        # Prepare data source
        data_source = {
            'GlueTable': {
                'DatabaseName': database_name,
                'TableName': table_name,
            }
        }
        if catalog_id:
            data_source['GlueTable']['CatalogId'] = catalog_id

        # Validate required parameters
        if not role_arn:
            raise ValueError('role_arn parameter is required for data quality recommendation runs')

        # Prepare request parameters
        run_params = {
            'DataSource': data_source,
            'Role': role_arn,
        }

        if created_ruleset_name:
            # Add timestamp to ensure uniqueness
            timestamped_name = f"{created_ruleset_name}_{time.strftime('%Y%m%d_%H%M%S')}"
            run_params['CreatedRulesetName'] = timestamped_name

        # Use provided values or sensible defaults
        run_params['NumberOfWorkers'] = number_of_workers or 5
        run_params['Timeout'] = timeout or 2880  # 48 hours default

        response = self.glue_client.start_data_quality_rule_recommendation_run(**run_params)
        run_id = response.get('RunId')

        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Successfully started recommendation run with ID: {run_id}',
        )

        return DataQualityRecommendationRunResponse(
            run_id=run_id,
            status='STARTED',
            database_name=database_name,
            table_name=table_name,
            created_ruleset_name=run_params.get('CreatedRulesetName'),
            message=f'Data quality recommendation run {run_id} started successfully',
        )

    async def _get_recommendation_run(self, ctx: Context, run_id: str) -> DataQualityRecommendationRunResponse:
        """Get details of a data quality recommendation run."""
        if not self.allow_sensitive_data_access:
            raise ValueError('Sensitive data access is required for get-recommendation-run operation')

        log_with_request_id(ctx, LogLevel.INFO, f'Getting data quality recommendation run: {run_id}')

        response = self.glue_client.get_data_quality_rule_recommendation_run(RunId=run_id)

        data_source = response.get('DataSource', {}).get('GlueTable', {})
        database_name = data_source.get('DatabaseName', '')
        table_name = data_source.get('TableName', '')

        # Count recommended rules if available
        recommended_ruleset = response.get('RecommendedRuleset', '')
        recommendation_count = len(recommended_ruleset.splitlines()) if recommended_ruleset else 0

        return DataQualityRecommendationRunResponse(
            run_id=run_id,
            status=response.get('Status', ''),
            database_name=database_name,
            table_name=table_name,
            role_arn=response.get('Role', ''),
            number_of_workers=response.get('NumberOfWorkers'),
            timeout=response.get('Timeout'),
            started_on=str(response.get('StartedOn', '')),
            completed_on=str(response.get('CompletedOn', '')),
            execution_time=response.get('ExecutionTime'),
            created_ruleset_name=response.get('CreatedRulesetName'),
            recommended_ruleset=recommended_ruleset,
            recommendation_count=recommendation_count,
            error_string=response.get('ErrorString', ''),
            message=f'Data quality recommendation run {run_id} retrieved successfully',
        )

    async def _cancel_recommendation_run(self, ctx: Context, run_id: str) -> DataQualityRecommendationRunResponse:
        """Cancel a data quality recommendation run."""
        if not self.allow_write:
            raise ValueError('Write access is required for cancel-recommendation-run operation')

        log_with_request_id(ctx, LogLevel.INFO, f'Cancelling data quality recommendation run: {run_id}')

        response = self.glue_client.cancel_data_quality_rule_recommendation_run(RunId=run_id)

        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Successfully cancelled recommendation run: {run_id}',
        )

        return DataQualityRecommendationRunResponse(
            run_id=run_id,
            status='CANCELLED',
            message=f'Data quality recommendation run {run_id} cancelled successfully',
        )

    async def _get_data_quality_result(self, ctx: Context, result_id: str) -> DataQualityMetricsResponse:
        """Get data quality result details."""
        if not self.allow_sensitive_data_access:
            raise ValueError('Sensitive data access is required for get-result operation')

        log_with_request_id(ctx, LogLevel.INFO, f'Getting data quality result: {result_id}')

        response = self.glue_client.get_data_quality_result(ResultId=result_id)

        rule_results = response.get('RuleResults', [])
        data_quality_results = []

        for rule_result in rule_results:
            data_quality_results.append(DataQualityResult(
                name=rule_result.get('Name', ''),
                description=rule_result.get('Description', ''),
                evaluation_message=rule_result.get('EvaluationMessage', ''),
                result=rule_result.get('Result', ''),
            ))

        return DataQualityMetricsResponse(
            result_id=result_id,
            ruleset_name=response.get('RulesetName', ''),
            evaluation_context=response.get('EvaluationContext', ''),
            started_on=str(response.get('StartedOn', '')),
            completed_on=str(response.get('CompletedOn', '')),
            job_name=response.get('JobName', ''),
            job_run_id=response.get('JobRunId', ''),
            ruleset_evaluation_run_id=response.get('RulesetEvaluationRunId', ''),
            data_source=response.get('DataSource', {}),
            role_arn=response.get('Role', ''),
            score=response.get('Score'),
            rule_results=data_quality_results,
            result_count=len(data_quality_results),
            message=f'Data quality result {result_id} retrieved successfully',
        )

    async def _list_data_quality_results(
        self,
        ctx: Context,
        database_name: Optional[str] = None,
        table_name: Optional[str] = None,
        catalog_id: Optional[str] = None,
    ) -> DataQualityMetricsResponse:
        """List data quality results for evaluation runs."""
        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Listing data quality results for {database_name}.{table_name}' if database_name and table_name else 'Listing all data quality results',
        )

        # First get evaluation runs to find result IDs
        list_params = {}
        
        if database_name and table_name:
            data_source_filter = {
                'GlueTable': {
                    'DatabaseName': database_name,
                    'TableName': table_name,
                }
            }
            if catalog_id:
                data_source_filter['GlueTable']['CatalogId'] = catalog_id
            
            list_params['Filter'] = {'DataSource': data_source_filter}

        response = self.glue_client.list_data_quality_ruleset_evaluation_runs(**list_params)
        runs = response.get('Runs', [])

        all_result_ids = []
        for run in runs:
            run_id = run.get('RunId')
            if run_id:
                try:
                    run_details = self.glue_client.get_data_quality_ruleset_evaluation_run(RunId=run_id)
                    result_ids = run_details.get('ResultIds', [])
                    all_result_ids.extend(result_ids)
                except ClientError as e:
                    log_with_request_id(
                        ctx,
                        LogLevel.WARNING,
                        f'Could not get result IDs for run {run_id}: {str(e)}',
                    )

        return DataQualityMetricsResponse(
            result_ids=all_result_ids,
            result_count=len(all_result_ids),
            message=f'Found {len(all_result_ids)} data quality results',
        )