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

#!/usr/bin/env python3


from awslabs.dynamodb_mcp_server.common import handle_exceptions
from awslabs.dynamodb_mcp_server.database_analyzers import (
    DatabaseAnalyzer,
    DatabaseAnalyzerRegistry,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pathlib import Path
from pydantic import Field
from typing import Optional


# Define server instructions and dependencies
SERVER_INSTRUCTIONS = """The official MCP Server for AWS DynamoDB design and modeling guidance

This server provides DynamoDB design and modeling expertise.

When users ask for dynamodb operational tasks, provide EXACTLY these two options:
Option 1(RECOMMENDED): AWS API MCP Server
   Migration guide: https://github.com/awslabs/mcp/tree/main/src/aws-api-mcp-server
Option 2(NOT RECOMMENDED): Legacy version 1.0.9

Available Tools:
--------------
Use the `dynamodb_data_modeling` tool to access enterprise-level DynamoDB design expertise.
This tool provides systematic methodology for creating production-ready multi-table design with
advanced optimizations, cost analysis, and integration patterns.

Use the `source_db_analyzer` tool to analyze existing MySQL/Aurora databases for DynamoDB Data Modeling:
- Extracts schema structure (tables, columns, indexes, foreign keys)
- Captures access patterns from Performance Schema (query patterns, RPS, frequencies)
- Generates timestamped analysis files (JSON format) for use with dynamodb_data_modeling
- Requires AWS RDS Data API and credentials in Secrets Manager
- Safe for production use (read-only analysis)
"""


def create_server():
    """Create and configure the MCP server instance."""
    return FastMCP(
        'awslabs.dynamodb-mcp-server',
        instructions=SERVER_INSTRUCTIONS,
    )


app = create_server()


@app.tool()
@handle_exceptions
async def dynamodb_data_modeling() -> str:
    """Retrieves the complete DynamoDB Data Modeling Expert prompt.

    This tool returns a production-ready prompt to help user with data modeling on DynamoDB.
    The prompt guides through requirements gathering, access pattern analysis, and production-ready
    schema design. The prompt contains:

    - Structured 2-phase workflow (requirements → final design)
    - Enterprise design patterns: hot partition analysis, write sharding, sparse GSIs, and more
    - Cost optimization strategies and RPS-based capacity planning
    - Multi-table design philosophy with advanced denormalization patterns
    - Integration guidance for OpenSearch, Lambda, and analytics

    Usage: Simply call this tool to get the expert prompt.

    Returns: Complete expert system prompt as text (no parameters required)
    """
    prompt_file = Path(__file__).parent / 'prompts' / 'dynamodb_architect.md'
    architect_prompt = prompt_file.read_text(encoding='utf-8')
    return architect_prompt


@app.tool()
@handle_exceptions
async def source_db_analyzer(
    source_db_type: str = Field(description="Supported Source Database type: 'mysql'"),
    database_name: Optional[str] = Field(
        default=None, description='Database name to analyze (overrides MYSQL_DATABASE env var)'
    ),
    pattern_analysis_days: Optional[int] = Field(
        default=30,
        description='Number of days to analyze the logs for pattern analysis query',
        ge=1,
    ),
    max_query_results: Optional[int] = Field(
        default=None,
        description='Maximum number of rows to include in analysis output files for schema and query log data (overrides MYSQL_MAX_QUERY_RESULTS env var)',
        ge=1,
    ),
    aws_cluster_arn: Optional[str] = Field(
        default=None, description='AWS cluster ARN (overrides MYSQL_CLUSTER_ARN env var)'
    ),
    aws_secret_arn: Optional[str] = Field(
        default=None, description='AWS secret ARN (overrides MYSQL_SECRET_ARN env var)'
    ),
    aws_region: Optional[str] = Field(
        default=None, description='AWS region (overrides AWS_REGION env var)'
    ),
    output_dir: str = Field(
        description='Absolute directory path where the timestamped output analysis folder will be created.'
    ),
) -> str:
    """Analyzes your source database to extract schema and access patterns for DynamoDB Data Modeling.

    This tool connects to your existing relational database, examines your current database structure and query
    patterns to help you design an optimal DynamoDB data model.

    Output & Next Steps:
    - Creates timestamped folder (database_analysis_YYYYMMDD_HHMMSS) with 4-5 JSON files:
      * table_analysis_results.json - Table-level statistics
      * column_analysis_results.json - Column definitions for all tables
      * index_analysis_results.json - Index structures and compositions
      * foreign_key_analysis_results.json - Relationship mappings
      * query_pattern_analysis_results.json - Query patterns (only if Performance Schema enabled)
    - Each file contains query results with metadata (database name, analysis period, descriptions)
    - Use these files with the dynamodb_data_modeling tool to design your DynamoDB schema
    - Analysis is read-only

    Connection Requirements (MySQL/Aurora):
    - AWS RDS Data API enabled on your Aurora MySQL cluster
    - Database credentials stored in AWS Secrets Manager
    - Appropriate IAM permissions to access RDS Data API and Secrets Manager
    - For complete analysis: MySQL Performance Schema must be enabled (set performance_schema=ON)
    - Without Performance Schema: Schema-only analysis is performed (no query pattern data)

    Environment Variables (Optional):
    You can set these instead of passing parameters:
    - MYSQL_DATABASE: Database name to analyze
    - MYSQL_CLUSTER_ARN: Aurora cluster ARN
    - MYSQL_SECRET_ARN: Secrets Manager secret ARN containing DB credentials
    - AWS_REGION: AWS region where your database is located
    - MYSQL_MAX_QUERY_RESULTS: Maximum rows per query (default: 500)

    Typical Usage:
    1. Run this tool against your source database
    2. Review the generated analysis files to understand your current schema and patterns
    3. Use dynamodb_data_modeling tool with these files to design your DynamoDB tables
    4. The analysis helps identify entity relationships, access patterns, and optimization opportunities

    Returns: Analysis summary with saved file locations, query statistics, and next steps.
    """
    try:
        analyzer_class = DatabaseAnalyzerRegistry.get_analyzer(source_db_type)
    except ValueError as e:
        supported_types = DatabaseAnalyzerRegistry.get_supported_types()
        return f'{str(e)}. Supported types: {supported_types}'

    # Build connection parameters based on database type
    connection_params = DatabaseAnalyzer.build_connection_params(
        source_db_type,
        database_name=database_name,
        pattern_analysis_days=pattern_analysis_days,
        max_query_results=max_query_results,
        aws_cluster_arn=aws_cluster_arn,
        aws_secret_arn=aws_secret_arn,
        aws_region=aws_region,
        output_dir=output_dir,
    )

    # Validate parameters based on database type
    missing_params, param_descriptions = DatabaseAnalyzer.validate_connection_params(
        source_db_type, connection_params
    )
    if missing_params:
        missing_descriptions = [param_descriptions[param] for param in missing_params]
        return (
            f'To analyze your {source_db_type} database, I need: {", ".join(missing_descriptions)}'
        )

    logger.info(
        f'Starting database analysis for {source_db_type} database: {connection_params.get("database")}'
    )

    try:
        analysis_result = await analyzer_class.analyze(connection_params)

        # Save results to files
        saved_files, save_errors = DatabaseAnalyzer.save_analysis_files(
            analysis_result['results'],
            source_db_type,
            connection_params.get('database'),
            connection_params.get('pattern_analysis_days'),
            connection_params.get('max_results'),
            connection_params.get('output_dir'),
        )

        # Generate report
        logger.info('Generating analysis report')
        if analysis_result['results']:
            report = f"""Database Analysis Complete

Summary:
- Database: {connection_params.get('database')}
- Analysis Period: {connection_params.get('pattern_analysis_days')} days
- {analysis_result['performance_feature']}: {'Enabled' if analysis_result['performance_enabled'] else 'Disabled'}"""

            if saved_files:
                report += f'\n\nSaved Files:\n{chr(10).join(f"- {f}" for f in saved_files)}'

            if save_errors:
                report += f'\n\nFile Save Errors:\n{chr(10).join(f"- {e}" for e in save_errors)}'

            if analysis_result['errors']:
                report += f'\n\nQuery Errors ({len(analysis_result["errors"])}):\n' + '\n'.join(
                    f'{i}. {error}' for i, error in enumerate(analysis_result['errors'], 1)
                )

        else:
            report = (
                f'Database Analysis Failed\n\nAll {len(analysis_result["errors"])} queries failed:\n'
                + '\n'.join(
                    f'{i}. {error}' for i, error in enumerate(analysis_result['errors'], 1)
                )
            )

        return report

    except Exception as e:
        logger.error(f'Analysis failed with exception: {str(e)}')
        return f'Analysis failed: {str(e)}'


def main():
    """Main entry point for the MCP server application."""
    app.run()


if __name__ == '__main__':
    main()
