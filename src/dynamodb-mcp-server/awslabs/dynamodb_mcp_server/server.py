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

import json
import os
from awslabs.aws_api_mcp_server.server import call_aws
from awslabs.dynamodb_mcp_server.common import handle_exceptions
from awslabs.dynamodb_mcp_server.database_analyzers import (
    DatabaseAnalyzer,
    DatabaseAnalyzerRegistry,
)
from awslabs.dynamodb_mcp_server.model_validation_utils import (
    create_validation_resources,
    get_user_working_directory,
    get_validation_result_transform_prompt,
    setup_dynamodb_local,
)
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pathlib import Path
from pydantic import Field
from typing import Optional


DATA_MODEL_JSON_FILE = 'dynamodb_data_model.json'
DATA_MODEL_VALIDATION_RESULT_JSON_FILE = 'dynamodb_model_validation.json'
# Define server instructions and dependencies
SERVER_INSTRUCTIONS = """The official MCP Server for AWS DynamoDB design and modeling guidance

This server provides DynamoDB design and modeling expertise.

Available Tools:
--------------
Use the `dynamodb_data_modeling` tool to access enterprise-level DynamoDB design expertise.
This tool provides systematic methodology for creating multi-table design with
advanced optimizations, cost analysis, and integration patterns.

Use the `source_db_analyzer` tool to analyze existing MySQL/Aurora databases for DynamoDB Data Modeling:
- Extracts schema structure (tables, columns, indexes, foreign keys)
- Captures access patterns from Performance Schema (query patterns, RPS, frequencies)
- Generates timestamped analysis files (JSON format) for use with dynamodb_data_modeling
- Requires AWS RDS Data API and credentials in Secrets Manager
- Safe for production use (read-only analysis)

Use the `execute_dynamodb_command` tool to execute AWS CLI DynamoDB commands:
- Executes AWS CLI commands that start with 'aws dynamodb'
- Supports both DynamoDB local (with endpoint-url) and AWS DynamoDB
- Automatically configures fake credentials for DynamoDB local
- Returns command execution results or error responses

Use the `dynamodb_data_model_validation` tool to validate your DynamoDB data model:
- Loads and validates dynamodb_data_model.json structure (checks required keys: tables, items, access_patterns)
- Sets up DynamoDB Local environment automatically (tries containers first: Docker/Podman/Finch/nerdctl, falls back to Java)
- Cleans up existing tables from previous validation runs
- Creates tables and inserts test data from your model specification
- Tests all defined access patterns by executing their AWS CLI implementations
- Saves detailed validation results to dynamodb_model_validation.json with pattern responses
- Transforms results to markdown format for comprehensive review
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

    This tool returns a prompt to help user with data modeling on DynamoDB.
    The prompt guides through requirements gathering, access pattern analysis, and
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
    - Creates timestamped folder (database_analysis_YYYYMMDD_HHMMSS) with Markdown analysis files
    - CRITICAL: Immediately read manifest.md from the timestamped folder - it lists all analysis files
    - The manifest includes summary statistics, links to all analysis files, and skipped queries
    - Read ALL analysis files listed in the manifest to understand the complete database structure
    - Files for skipped queries explain why they were skipped (e.g., Performance Schema disabled)
    - Use these analysis files with the dynamodb_data_modeling tool to design your DynamoDB schema

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
            analysis_result.get('performance_enabled', True),
            analysis_result.get('skipped_queries', []),
        )

        # Generate report
        logger.info('Generating analysis report')
        if analysis_result['results']:
            report_sections = []

            # Header section
            report_sections.append('Database Analysis Complete')
            report_sections.append('')

            # Summary section
            summary_lines = [
                'Summary:',
                f'- Database: {connection_params.get("database")}',
                f'- Analysis Period: {connection_params.get("pattern_analysis_days")} days',
                '**CRITICAL: Read ALL Analysis Files**',
                '',
                'Follow these steps IN ORDER:',
                '',
            ]
            report_sections.extend(summary_lines)

            # Add workflow section
            workflow_lines = [
                '1. Read manifest.md from the timestamped analysis directory',
                '   - Lists all generated analysis files by category',
                '   - Shows which queries succeeded/skipped and why',
                '',
                '2. Read EVERY file listed in the manifest (both schema and performance sections)',
                '   - You MUST read all files, even those marked as SKIPPED',
                '   - Skipped files explain why queries failed (e.g., Performance Schema disabled)',
                '   - Each file contains critical information for data modeling',
                '',
                '3. After reading all files, use dynamodb_data_modeling tool',
                '   - Extract entities and relationships from schema files',
                '   - Identify access patterns from performance files',
                '   - Document findings in dynamodb_requirement.md',
            ]
            report_sections.extend(workflow_lines)

            if saved_files:
                report_sections.append('')
                report_sections.append('Generated Analysis Files (Read All):')
                report_sections.extend(f'- {f}' for f in saved_files)

            if save_errors:
                report_sections.append('')
                report_sections.append('File Save Errors:')
                report_sections.extend(f'- {e}' for e in save_errors)

            report = '\n'.join(report_sections)

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


@app.tool()
@handle_exceptions
async def execute_dynamodb_command(
    command: str = Field(description="AWS CLI DynamoDB command (must start with 'aws dynamodb')"),
    endpoint_url: Optional[str] = Field(default=None, description='DynamoDB endpoint URL'),
    ctx: Optional[Context] = Field(default=None, description='Execution context'),
):
    """Execute AWSCLI DynamoDB commands.

    Args:
        command: AWS CLI command string (e.g., "aws dynamodb query --table-name MyTable")
        endpoint_url: DynamoDB endpoint URL
        ctx: Execution context

    Returns:
        AWS CLI command execution results or error response
    """
    # Validate command starts with 'aws dynamodb'
    if not command.strip().startswith('aws dynamodb'):
        raise ValueError("Command must start with 'aws dynamodb'")

    # Configure environment with fake AWS credentials if endpoint_url is present
    if endpoint_url:
        os.environ['AWS_ACCESS_KEY_ID'] = 'AKIAIOSFODNN7EXAMPLE'  # pragma: allowlist secret
        os.environ['AWS_SECRET_ACCESS_KEY'] = (
            'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'  # pragma: allowlist secret
        )
        os.environ['AWS_DEFAULT_REGION'] = os.environ.get('AWS_REGION', 'us-east-1')
        command += f' --endpoint-url {endpoint_url}'

    try:
        return await call_aws(command, ctx)
    except Exception as e:
        return e


async def execute_access_patterns(
    access_patterns, endpoint_url: Optional[str] = None, ctx: Optional[Context] = None
) -> dict:
    """Execute all data model validation access patterns operations.

    Args:
        access_patterns: List of access patterns to test
        endpoint_url: DynamoDB endpoint URL
        ctx: Execution context

    Returns:
        Dictionary with all execution results
    """
    try:
        results = []
        for pattern in access_patterns:
            if 'implementation' not in pattern:
                results.append(pattern)
                continue

            command = pattern['implementation']
            result = await execute_dynamodb_command(command, endpoint_url, ctx)
            results.append(
                {
                    'pattern_id': pattern.get('pattern'),
                    'description': pattern.get('description'),
                    'dynamodb_operation': pattern.get('dynamodb_operation'),
                    'command': command,
                    'response': result if isinstance(result, dict) else str(result),
                }
            )

        validation_response = {'validation_response': results}

        user_dir = get_user_working_directory()
        output_file = os.path.join(user_dir, DATA_MODEL_VALIDATION_RESULT_JSON_FILE)
        with open(output_file, 'w') as f:
            json.dump(validation_response, f, indent=2)

        return validation_response
    except Exception as e:
        logger.error(f'Failed to execute access patterns validation: {e}')
        return {'validation_response': [], 'error': str(e)}


@app.tool()
@handle_exceptions
async def dynamodb_data_model_validation(
    ctx: Optional[Context] = Field(default=None, description='Execution context'),
) -> str:
    """Validates and tests DynamoDB data models against DynamoDB Local.

    Use this tool to validate, test, and verify your DynamoDB data model after completing the design phase.
    This tool automatically checks that all access patterns work correctly by executing them against a local
    DynamoDB instance.

    WHEN TO USE:
    - After completing data model design with dynamodb_data_modeling tool
    - When user asks to "validate", "test", "check", or "verify" their DynamoDB data model
    - To ensure all access patterns execute correctly before deploying to production

    WHAT IT DOES:
    1. If dynamodb_data_model.json doesn't exist:
       - Returns complete JSON generation guide from json_generation_guide.md
       - Follow the guide to create the JSON file with tables, items, and access_patterns
       - Call this tool again after creating the JSON to validate

    2. If dynamodb_data_model.json exists:
       - Validates the JSON structure (checks for required keys: tables, items, access_patterns)
       - Sets up DynamoDB Local environment (Docker/Podman/Finch/nerdctl or Java fallback)
       - Cleans up existing tables from previous validation runs
       - Creates tables and inserts test data from your model specification
       - Tests all defined access patterns by executing their AWS CLI implementations
       - Saves detailed validation results to dynamodb_model_validation.json
       - Transforms results to markdown format for comprehensive review

    Args:
        ctx: Execution context

    Returns:
        JSON generation guide (if file missing) or validation results with transformation prompt (if file exists)
    """
    try:
        # Step 1: Get current working directory reliably
        user_dir = get_user_working_directory()
        data_model_path = os.path.join(user_dir, DATA_MODEL_JSON_FILE)

        if not os.path.exists(data_model_path):
            # Return the JSON generation guide to help users create the required file
            guide_path = Path(__file__).parent / 'prompts' / 'json_generation_guide.md'
            try:
                json_guide = guide_path.read_text(encoding='utf-8')
                return f"""Error: {data_model_path} not found in your working directory.

{json_guide}"""
            except FileNotFoundError:
                return f'Error: {data_model_path} not found. Please generate your data model with dynamodb_data_modeling tool first.'

        # Step 2: Load and validate JSON structure
        logger.info('Loading data model configuration')
        try:
            with open(data_model_path, 'r') as f:
                data_model = json.load(f)
        except json.JSONDecodeError as e:
            return f'Error: Invalid JSON in {data_model_path}: {str(e)}'

        # Validate required structure
        required_keys = ['tables', 'items', 'access_patterns']
        missing_keys = [key for key in required_keys if key not in data_model]
        if missing_keys:
            return f'Error: Missing required keys in data model: {missing_keys}'

        # Step 3: Setup DynamoDB Local
        logger.info('Setting up DynamoDB Local environment')
        endpoint_url = setup_dynamodb_local()

        # Step 4: Create resources
        logger.info('Creating validation resources')
        create_validation_resources(data_model, endpoint_url)

        # Step 5: Execute access patterns
        logger.info('Executing access patterns')
        await execute_access_patterns(data_model.get('access_patterns', []), endpoint_url, ctx)

        # Step 6: Transform validation results to markdown
        return get_validation_result_transform_prompt()

    except FileNotFoundError as e:
        logger.error(f'File not found: {e}')
        return f'Error: Required file not found: {str(e)}'
    except Exception as e:
        logger.error(f'Data model validation failed: {e}')
        return f'Data model validation failed: {str(e)}. Please check your data model JSON structure and try again.'


def main():
    """Main entry point for the MCP server application."""
    app.run()


if __name__ == '__main__':
    main()
