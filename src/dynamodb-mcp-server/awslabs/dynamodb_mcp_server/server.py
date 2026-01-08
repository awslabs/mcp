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

"""DynamoDB MCP Server for data modeling and database analysis."""

import json
import os
from awslabs.aws_api_mcp_server.server import call_aws
from awslabs.dynamodb_mcp_server.common import handle_exceptions
from awslabs.dynamodb_mcp_server.db_analyzer import analyzer_utils
from awslabs.dynamodb_mcp_server.db_analyzer.plugin_registry import PluginRegistry
from awslabs.dynamodb_mcp_server.model_validation_utils import (
    create_validation_resources,
    get_validation_result_transform_prompt,
    setup_dynamodb_local,
)
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pathlib import Path
from pydantic import Field
from typing import Any, Dict, List, Optional


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

Use the `source_db_analyzer` tool to analyze existing databases for DynamoDB Data Modeling:
- Supports MySQL, PostgreSQL, and SQL Server
- Two execution modes:
  * SELF_SERVICE: Generate SQL queries, user runs them, tool parses results
  * MANAGED: Direct database connection (MySQL supports RDS Data API or connection-based access)

Managed Analysis Workflow:
- Extracts schema structure (tables, columns, indexes, foreign keys)
- Captures access patterns from query logs (when available)
- Generates timestamped analysis files (Markdown format) for use with dynamodb_data_modeling
- Safe for production use (read-only analysis)

Self-Service Mode Workflow:
1. User selects database type (mysql/postgresql/sqlserver)
2. Tool generates SQL queries to file
3. User runs queries against their database
4. User provides result file path
5. Tool generates analysis markdown files

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
    source_db_type: str = Field(
        description="Database type: 'mysql', 'postgresql', or 'sqlserver'"
    ),
    database_name: Optional[str] = Field(
        default=None,
        description='Database name to analyze. REQUIRED for self_service. Env: MYSQL_DATABASE.',
    ),
    execution_mode: str = Field(
        default='self_service',
        description=(
            "'self_service': generates SQL for user to run, then parses results. "
            "'managed' (MySQL only): RDS Data API-based access (aws_cluster_arn) "
            'or Connection-based access (hostname+port).'
        ),
    ),
    queries_file_path: Optional[str] = Field(
        default=None,
        description='[self_service] Output path for generated SQL queries (Step 1).',
    ),
    query_result_file_path: Optional[str] = Field(
        default=None,
        description='[self_service] Path to query results file for parsing (Step 2).',
    ),
    pattern_analysis_days: Optional[int] = Field(
        default=30,
        description='Days of query logs to analyze. Default: 30.',
        ge=1,
    ),
    max_query_results: Optional[int] = Field(
        default=None,
        description='Max rows per query. Default: 500. Env: MYSQL_MAX_QUERY_RESULTS.',
        ge=1,
    ),
    aws_cluster_arn: Optional[str] = Field(
        default=None,
        description='[managed/RDS Data API-based] Aurora cluster ARN. Use this OR hostname, not both. Env: MYSQL_CLUSTER_ARN.',
    ),
    aws_secret_arn: Optional[str] = Field(
        default=None,
        description='[managed] Secrets Manager ARN for DB credentials. REQUIRED. Env: MYSQL_SECRET_ARN.',
    ),
    aws_region: Optional[str] = Field(
        default=None,
        description='[managed] AWS region. REQUIRED. Env: AWS_REGION.',
    ),
    hostname: Optional[str] = Field(
        default=None,
        description='[managed/connection-based] MySQL hostname. Use this OR aws_cluster_arn, not both. Env: MYSQL_HOSTNAME.',
    ),
    port: Optional[int] = Field(
        default=None,
        description='[managed/connection-based] MySQL port. Default: 3306. Env: MYSQL_PORT.',
    ),
    output_dir: str = Field(
        description='Absolute path for output folder. Must exist and be writable. REQUIRED.',
    ),
) -> str:
    """Analyzes source database to extract schema and access patterns for DynamoDB modeling.

    WHEN TO USE: Call this tool when the user selects "Existing Database Analysis" option
    after invoking the `dynamodb_data_modeling` tool. This extracts schema and query patterns
    from an existing relational database to accelerate DynamoDB data model design.

    IMPORTANT: Always ask the user which execution mode they prefer before calling this tool.

    Execution Modes:
    - self_service: Generates SQL queries for user to run manually, then parses their results.
    - managed (MySQL only): Database connection via RDS Data API or hostname.

    Supported Databases: MySQL, PostgreSQL, SQL Server

    Output: Generates analysis files (schema structure, access patterns, relationships) in
    Markdown format. These files feed into the DynamoDB data modeling workflow to inform
    table design, GSI selection, and access pattern mapping.

    Returns: Analysis summary with file locations and next steps.
    """
    # Validate execution mode
    if execution_mode not in ['managed', 'self_service']:
        return f'Invalid execution_mode: {execution_mode}. Must be "self_service" or "managed".'

    # Get plugin for database type
    try:
        plugin = PluginRegistry.get_plugin(source_db_type)
    except ValueError as e:
        return f'{str(e)}. Supported types: {PluginRegistry.get_supported_types()}'

    # Managed mode only supports MySQL
    if execution_mode == 'managed' and source_db_type != 'mysql':
        return (
            f'Managed mode is not supported for {source_db_type}. Use self_service mode instead.'
        )

    max_results = max_query_results or 500

    # Self-service mode - Step 1: Generate queries
    if execution_mode == 'self_service' and queries_file_path and not query_result_file_path:
        try:
            return analyzer_utils.generate_query_file(
                plugin, database_name, max_results, queries_file_path, output_dir, source_db_type
            )
        except Exception as e:
            logger.error(f'Failed to write queries: {str(e)}')
            return f'Failed to write queries: {str(e)}'

    # Self-service mode - Step 2: Parse results and generate analysis
    if execution_mode == 'self_service' and query_result_file_path:
        try:
            return analyzer_utils.parse_results_and_generate_analysis(
                plugin,
                query_result_file_path,
                output_dir,
                database_name,
                pattern_analysis_days,
                max_results,
                source_db_type,
            )
        except FileNotFoundError as e:
            logger.error(f'Query Result file not found: {str(e)}')
            return str(e)
        except Exception as e:
            logger.error(f'Analysis failed: {str(e)}')
            return f'Analysis failed: {str(e)}'

    # Managed analysis mode
    if execution_mode == 'managed':
        connection_params = analyzer_utils.build_connection_params(
            source_db_type,
            database_name=database_name,
            pattern_analysis_days=pattern_analysis_days,
            max_query_results=max_results,
            aws_cluster_arn=aws_cluster_arn,
            aws_secret_arn=aws_secret_arn,
            aws_region=aws_region,
            hostname=hostname,
            port=port,
            output_dir=output_dir,
        )

        # Validate parameters
        missing_params, param_descriptions = analyzer_utils.validate_connection_params(
            source_db_type, connection_params
        )
        if missing_params:
            missing_descriptions = [param_descriptions[param] for param in missing_params]
            return f'To analyze your {source_db_type} database, I need: {", ".join(missing_descriptions)}'

        logger.info(
            f'Starting managed analysis for {source_db_type}: {connection_params.get("database")}'
        )

        try:
            return await analyzer_utils.execute_managed_analysis(
                plugin, connection_params, source_db_type
            )
        except NotImplementedError as e:
            logger.error(f'Managed mode not supported: {str(e)}')
            return str(e)
        except Exception as e:
            logger.error(f'Analysis failed: {str(e)}')
            return f'Analysis failed: {str(e)}'

    # Invalid mode combination
    return 'Invalid parameter combination. For self-service mode, provide either queries_file_path (to generate queries) or query_result_file_path (to parse results).'


async def _execute_dynamodb_command(
    command: str,
    endpoint_url: Optional[str] = None,
):
    """Execute AWS CLI DynamoDB commands (internal use only).

    Args:
        command: AWS CLI command string (must start with 'aws dynamodb')
        endpoint_url: DynamoDB endpoint URL for local testing

    Returns:
        AWS CLI command execution results or error response

    Raises:
        ValueError: If command doesn't start with 'aws dynamodb'
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
        return await call_aws(command, Context())
    except Exception as e:
        return e


@app.tool()
@handle_exceptions
async def dynamodb_data_model_validation(
    workspace_dir: str = Field(description='Absolute path of the workspace directory'),
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
        workspace_dir: Absolute path of the workspace directory

    Returns:
        JSON generation guide (if file missing) or validation results with transformation prompt (if file exists)
    """
    try:
        # Step 1: Get current working directory reliably
        data_model_path = os.path.join(workspace_dir, DATA_MODEL_JSON_FILE)

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
        await _execute_access_patterns(
            workspace_dir, data_model.get('access_patterns', []), endpoint_url
        )

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


async def _execute_access_patterns(
    workspace_dir: str,
    access_patterns: List[Dict[str, Any]],
    endpoint_url: Optional[str] = None,
) -> dict:
    """Execute all data model validation access patterns operations.

    Args:
        workspace_dir: Absolute path of the workspace directory
        access_patterns: List of access patterns to test
        endpoint_url: DynamoDB endpoint URL

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
            result = await _execute_dynamodb_command(command, endpoint_url)
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

        output_file = os.path.join(workspace_dir, DATA_MODEL_VALIDATION_RESULT_JSON_FILE)
        with open(output_file, 'w') as f:
            json.dump(validation_response, f, indent=2)

        return validation_response
    except Exception as e:
        logger.error(f'Failed to execute access patterns validation: {e}')
        return {'validation_response': [], 'error': str(e)}


if __name__ == '__main__':
    main()
