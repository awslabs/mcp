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

"""Utility functions for source database analyzer."""

import os
from awslabs.dynamodb_mcp_server.common import validate_path_within_directory
from awslabs.dynamodb_mcp_server.db_analyzer.base_plugin import DatabasePlugin
from awslabs.dynamodb_mcp_server.markdown_formatter import MarkdownFormatter
from datetime import datetime
from loguru import logger
from typing import Any, Dict, List, Tuple


DEFAULT_ANALYSIS_DAYS = 30
DEFAULT_MAX_QUERY_RESULTS = 500


def resolve_and_validate_path(file_path: str, base_dir: str, path_type: str) -> str:
    """Resolve and validate file path within base directory."""
    if not os.path.isabs(file_path):
        resolved = os.path.join(base_dir, file_path.lstrip('./'))
    else:
        resolved = file_path
    return validate_path_within_directory(resolved, base_dir, path_type)


DEFAULT_MYSQL_PORT = 3306


def build_connection_params(source_db_type: str, **kwargs) -> Dict[str, Any]:
    """Build connection parameters for database analysis.

    Args:
        source_db_type: Type of source database (e.g., 'mysql')
        **kwargs: Connection parameters (aws_cluster_arn, aws_secret_arn, hostname, port, etc.)

    Returns:
        Dictionary of connection parameters

    Raises:
        ValueError: If database type is not supported
    """
    if source_db_type == 'mysql':
        user_provided_dir = kwargs.get('output_dir')

        # Validate user-provided directory
        if not os.path.isabs(user_provided_dir):
            raise ValueError(f'Output directory must be an absolute path: {user_provided_dir}')
        if not os.path.isdir(user_provided_dir) or not os.access(user_provided_dir, os.W_OK):
            raise ValueError(
                f'Output directory does not exist or is not writable: {user_provided_dir}'
            )
        output_dir = user_provided_dir

        # Validate port parameter
        port_value = kwargs.get('port') or os.getenv('MYSQL_PORT', str(DEFAULT_MYSQL_PORT))
        port = int(port_value) if str(port_value).isdigit() else DEFAULT_MYSQL_PORT

        # Determine connection method
        # Priority: explicit args > env vars, and cluster_arn > hostname within each level
        cluster_arn = kwargs.get('aws_cluster_arn')
        hostname = kwargs.get('hostname')

        if cluster_arn:
            # Explicit cluster_arn - use RDS Data API-based access
            hostname = None
        elif hostname:
            # Explicit hostname - use connection-based access
            cluster_arn = None
        else:
            # Fall back to env vars with same precedence
            cluster_arn = os.getenv('MYSQL_CLUSTER_ARN')
            hostname = os.getenv('MYSQL_HOSTNAME') if not cluster_arn else None

        return {
            'cluster_arn': cluster_arn,
            'secret_arn': kwargs.get('aws_secret_arn') or os.getenv('MYSQL_SECRET_ARN'),
            'database': kwargs.get('database_name') or os.getenv('MYSQL_DATABASE'),
            'region': kwargs.get('aws_region') or os.getenv('AWS_REGION'),
            'hostname': hostname,
            'port': port,
            'max_results': kwargs.get('max_query_results')
            or int(os.getenv('MYSQL_MAX_QUERY_RESULTS', str(DEFAULT_MAX_QUERY_RESULTS))),
            'pattern_analysis_days': kwargs.get('pattern_analysis_days', DEFAULT_ANALYSIS_DAYS),
            'output_dir': output_dir,
        }
    raise ValueError(f'Unsupported database type: {source_db_type}')


def validate_connection_params(
    source_db_type: str, connection_params: Dict[str, Any]
) -> Tuple[List[str], Dict[str, str]]:
    """Validate connection parameters for database type.

    Args:
        source_db_type: Type of source database
        connection_params: Dictionary of connection parameters

    Returns:
        Tuple of (missing_params, param_descriptions)
    """
    if source_db_type == 'mysql':
        missing_params = []
        param_descriptions = {}
        cluster_arn = connection_params.get('cluster_arn')
        hostname = connection_params.get('hostname')

        # Check for either RDS Data API-based or connection-based access
        has_rds_data_api = bool(isinstance(cluster_arn, str) and cluster_arn.strip())
        has_connection_based = bool(isinstance(hostname, str) and hostname.strip())

        # Check that we have a connection method
        if not has_rds_data_api and not has_connection_based:
            missing_params.append('cluster_arn OR hostname')
            param_descriptions['cluster_arn OR hostname'] = (
                'Required: Either aws_cluster_arn (for RDS Data API-based access) '
                'OR hostname (for connection-based access)'
            )

        # Check common required parameters
        common_required_params = ['secret_arn', 'database', 'region']
        for param in common_required_params:
            if not connection_params.get(param) or (
                isinstance(connection_params[param], str)
                and connection_params[param].strip() == ''
            ):
                missing_params.append(param)
        param_descriptions.update(
            {
                'secret_arn': 'Secrets Manager secret ARN containing DB credentials',  # pragma: allowlist secret
                'database': 'Database name to analyze',
                'region': 'AWS region where your database instance and Secrets Manager are located',
            }
        )
        return missing_params, param_descriptions
    return [], {}


def save_analysis_files(
    results: Dict[str, Any],
    source_db_type: str,
    database: str,
    pattern_analysis_days: int,
    max_results: int,
    output_dir: str,
    plugin: DatabasePlugin,
    performance_enabled: bool = True,
    skipped_queries: List[str] = None,
) -> Tuple[List[str], List[str]]:
    """Save analysis results to Markdown files using MarkdownFormatter.

    Args:
        results: Dictionary of query results
        source_db_type: Type of source database
        database: Database name
        pattern_analysis_days: Number of days to analyze the logs for pattern analysis query
        max_results: Maximum results per query
        output_dir: Absolute directory path where the timestamped output folder will be created
        plugin: DatabasePlugin instance for getting query definitions (REQUIRED)
        performance_enabled: Whether performance schema is enabled
        skipped_queries: List of query names that were skipped during analysis

    Returns:
        Tuple of (saved_files, save_errors)
    """
    if plugin is None:
        raise ValueError('plugin parameter is required and cannot be None')

    saved_files = []
    save_errors = []

    logger.info(f'save_analysis_files called with {len(results) if results else 0} results')

    if not results:
        logger.warning('No results to save - returning empty lists')
        return saved_files, save_errors

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    analysis_folder = os.path.join(output_dir, f'database_analysis_{timestamp}')
    logger.info(f'Creating analysis folder: {analysis_folder}')

    try:
        os.makedirs(analysis_folder, exist_ok=True)
        logger.info(f'Created folder at: {analysis_folder}')
    except OSError as e:
        logger.error(f'Failed to create analysis folder: {str(e)}')
        save_errors.append(f'Failed to create folder {analysis_folder}: {str(e)}')
        return saved_files, save_errors

    # Prepare metadata for MarkdownFormatter
    metadata = {
        'database': database,
        'source_db_type': source_db_type,
        'analysis_period': f'{pattern_analysis_days} days',
        'max_query_results': max_results,
        'performance_enabled': performance_enabled,
        'skipped_queries': skipped_queries or [],
    }

    # Use MarkdownFormatter to generate files
    try:
        formatter = MarkdownFormatter(results, metadata, analysis_folder, plugin=plugin)
        generated_files, generation_errors = formatter.generate_all_files()
        saved_files = generated_files

        # Convert error tuples to error strings
        if generation_errors:
            for query_name, error_msg in generation_errors:
                save_errors.append(f'{query_name}: {error_msg}')

        logger.info(
            f'Successfully generated {len(saved_files)} Markdown files with {len(save_errors)} errors'
        )
    except Exception as e:
        logger.error(f'Failed to generate Markdown files: {str(e)}')
        save_errors.append(f'Failed to generate Markdown files: {str(e)}')

    return saved_files, save_errors


def generate_query_file(
    plugin,
    database_name: str,
    max_results: int,
    query_output_file: str,
    output_dir: str,
    source_db_type: str,
) -> str:
    """Generate SQL query file for self-service mode."""
    if not database_name:
        return 'database_name is required for self-service mode to generate queries.'

    resolved_query_file = resolve_and_validate_path(
        query_output_file, output_dir, 'query output file'
    )

    query_dir = os.path.dirname(resolved_query_file)
    if query_dir and not os.path.exists(query_dir):
        os.makedirs(query_dir, exist_ok=True)

    output_file = plugin.write_queries_to_file(database_name, max_results, resolved_query_file)

    return f"""SQL queries have been written to: {output_file}

Next Steps:
1. Run these queries against your {source_db_type} database
2. Save the results to a text file (pipe-separated format)
3. Call this tool again with:
   - execution_mode='self_service'
   - result_input_file='<path_to_your_results_file>'
   - Same database_name and output_dir

Example commands:
- MySQL: mysql -u user -p -D {database_name} --table < {output_file} > results.txt
- PostgreSQL: psql -d {database_name} -f {output_file} > results.txt
- SQL Server: sqlcmd -d {database_name} -i {output_file} -o results.txt

IMPORTANT for MySQL: The --table flag is required to produce pipe-separated output that can be parsed correctly.

After running queries, provide the results file path to continue analysis."""


def parse_results_and_generate_analysis(
    plugin,
    result_input_file: str,
    output_dir: str,
    database_name: str,
    pattern_analysis_days: int,
    max_results: int,
    source_db_type: str,
) -> str:
    """Parse query results and generate analysis files."""
    resolved_result_file = validate_path_within_directory(
        result_input_file, output_dir, 'result input file'
    )
    if not os.path.exists(resolved_result_file):
        raise FileNotFoundError(f'Result file not found: {resolved_result_file}')

    logger.info(f'Parsing query results from: {resolved_result_file}')
    results = plugin.parse_results_from_file(resolved_result_file)

    if not results:
        return f'No query results found in file: {resolved_result_file}. Please check the file format.'

    saved_files, save_errors = save_analysis_files(
        results,
        source_db_type,
        database_name,
        pattern_analysis_days or 30,
        max_results,
        output_dir,
        plugin,
        performance_enabled=True,
        skipped_queries=[],
    )

    return build_analysis_report(
        saved_files, save_errors, database_name, result_input_file, is_self_service=True
    )


async def execute_managed_analysis(plugin, connection_params: dict, source_db_type: str) -> str:
    """Execute managed mode analysis via AWS RDS Data API."""
    analysis_result = await plugin.execute_managed_mode(connection_params)

    saved_files, save_errors = save_analysis_files(
        analysis_result['results'],
        source_db_type,
        connection_params.get('database'),
        connection_params.get('pattern_analysis_days'),
        connection_params.get('max_results'),
        connection_params.get('output_dir'),
        plugin,
        analysis_result.get('performance_enabled', True),
        analysis_result.get('skipped_queries', []),
    )

    if analysis_result['results']:
        return build_analysis_report(
            saved_files,
            save_errors,
            connection_params.get('database'),
            None,
            is_self_service=False,
            analysis_period=connection_params.get('pattern_analysis_days'),
        )
    else:
        return build_failure_report(analysis_result['errors'])


def build_analysis_report(
    saved_files: list,
    save_errors: list,
    database_name: str,
    source_file: str = None,
    is_self_service: bool = False,
    analysis_period: int = None,
) -> str:
    """Build analysis completion report."""
    mode = 'Self-Service Mode' if is_self_service else 'Managed Mode'
    report = [f'Database Analysis Complete ({mode})', '']

    summary = ['Summary:', f'- Database: {database_name}']
    if source_file:
        summary.append(f'- Source: {source_file}')
    if analysis_period:
        summary.append(f'- Analysis Period: {analysis_period} days')
    summary.extend(
        ['**CRITICAL: Read ALL Analysis Files**', '', 'Follow these steps IN ORDER:', '']
    )
    report.extend(summary)

    workflow = [
        '1. Read manifest.md from the timestamped analysis directory',
        '   - Lists all generated analysis files by category',
        '',
        '2. Read EVERY file listed in the manifest',
        '   - Each file contains critical information for data modeling',
        '',
        '3. After reading all files, use dynamodb_data_modeling tool',
        '   - Extract entities and relationships from schema files',
        '   - Identify access patterns from performance files',
        '   - Document findings in dynamodb_requirement.md',
    ]
    report.extend(workflow)

    if saved_files:
        report.extend(['', 'Generated Analysis Files (Read All):'])
        report.extend(f'- {f}' for f in saved_files)

    if save_errors:
        report.extend(['', 'File Save Errors:'])
        report.extend(f'- {e}' for e in save_errors)

    return '\n'.join(report)


def build_failure_report(errors: list) -> str:
    """Build failure report when all queries fail."""
    return f'Database Analysis Failed\n\nAll {len(errors)} queries failed:\n' + '\n'.join(
        f'{i}. {error}' for i, error in enumerate(errors, 1)
    )
