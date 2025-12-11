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

import logging
import os
from awslabs.dynamodb_mcp_server.database_analysis_queries import (
    get_performance_queries,
    get_query_descriptions,
    get_schema_queries,
)
from datetime import datetime
from typing import Any, Dict, List, Tuple


# Configure logger
logger = logging.getLogger(__name__)


class MarkdownFormatter:
    """Formats database analysis results into LLM-optimized Markdown files."""

    def __init__(self, results: Dict[str, Any], metadata: Dict[str, Any], output_dir: str):
        """Initialize formatter with analysis results.

        Args:
            results: Dictionary of query results from DatabaseAnalyzer
            metadata: Analysis metadata (database name, dates, etc.)
            output_dir: Directory where Markdown files will be saved
        """
        self.results = results
        self.metadata = metadata
        self.output_dir = output_dir
        self.file_registry: List[str] = []  # Track generated files for manifest
        self.skipped_queries: Dict[str, str] = {}  # Track skipped queries and reasons
        self.errors: List[Tuple[str, str]] = []  # Track errors (query_name, error_message)

    def _format_as_markdown_table(self, data: List[Dict[str, Any]]) -> str:
        """Format query result data as Markdown table.

        Args:
            data: List of row dictionaries

        Returns:
            Markdown table string
        """
        try:
            # Handle empty data gracefully (catches None, empty list, etc.)
            if not data:
                logger.warning('No data provided to format as Markdown table')
                return 'No data returned'

            # Ensure data is a list
            if not isinstance(data, list):
                logger.error(f'Data is not a list, got type: {type(data)}')
                return 'Error: Invalid data format'

            # Get column names from first row
            first_row = data[0]
            if not isinstance(first_row, dict):
                logger.error(f'First row is not a dictionary, got type: {type(first_row)}')
                return 'Error: Invalid data structure'

            if not first_row:
                logger.warning('First row is empty dictionary')
                return 'No columns available'

            columns = list(first_row.keys())

            # Build header row
            header = '| ' + ' | '.join(columns) + ' |'
            separator = '|' + '|'.join([' --- ' for _ in columns]) + '|'

            # Build data rows
            rows = []
            for row_idx, row in enumerate(data):
                try:
                    if not isinstance(row, dict):
                        logger.warning(f'Row {row_idx} is not a dictionary, skipping')
                        continue

                    formatted_values = []
                    for col in columns:
                        value = row.get(col)

                        # Handle null values
                        if value is None:
                            formatted_values.append('NULL')
                        # Format numbers with appropriate precision
                        elif isinstance(value, float):
                            # Use 2 decimal places for floats
                            formatted_values.append(f'{value:.2f}')
                        elif isinstance(value, (int, bool)):
                            formatted_values.append(str(value))
                        else:
                            # Convert to string and escape pipe characters
                            formatted_values.append(str(value).replace('|', '\\|'))

                    rows.append('| ' + ' | '.join(formatted_values) + ' |')
                except Exception as e:
                    logger.error(f'Error formatting row {row_idx}: {str(e)}')
                    # Continue processing remaining rows
                    continue

            # If no rows were successfully formatted
            if not rows:
                logger.error('No rows could be formatted successfully')
                return 'Error: Unable to format data rows'

            # Combine all parts
            table = '\n'.join([header, separator] + rows)
            return table

        except Exception as e:
            logger.error(f'Unexpected error in _format_as_markdown_table: {str(e)}')
            return f'Error: Unable to format data - {str(e)}'

    def _generate_query_file(self, query_name: str, query_result: Dict[str, Any]) -> str:
        """Generate Markdown file for a single query result.

        Args:
            query_name: Name of the query
            query_result: Query result data

        Returns:
            Path to generated file, or empty string if file generation failed
        """
        try:
            # Create filename from query name
            filename = f'{query_name}.md'
            file_path = os.path.join(self.output_dir, filename)

            # Extract query description and data
            description = query_result.get('description', 'No description available')
            data = query_result.get('data', [])

            # Build file content
            content_parts = []

            # Add query description header
            title = query_name.replace('_', ' ').title()
            content_parts.append(f'# {title}\n')
            content_parts.append(f'**Query Description**: {description}\n')

            # Add generation timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            content_parts.append(f'**Generated**: {timestamp}\n')

            # Add results section
            content_parts.append('## Results\n')

            # Format data as Markdown table
            table = self._format_as_markdown_table(data)
            content_parts.append(table)

            # Add row count footer
            row_count = len(data) if data and isinstance(data, list) else 0
            content_parts.append(f'\n**Total Rows**: {row_count}')

            # Combine all parts
            content = '\n'.join(content_parts)

            # Save file to output directory
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return file_path
            except OSError as e:
                error_msg = f'Failed to write file {file_path}: {str(e)}'
                logger.error(error_msg)
                self.errors.append((query_name, error_msg))
                return ''

        except Exception as e:
            error_msg = f'Unexpected error generating file for {query_name}: {str(e)}'
            logger.error(error_msg)
            self.errors.append((query_name, error_msg))
            return ''

    def _generate_skipped_query_file(self, query_name: str, reason: str) -> str:
        """Generate informational file for a skipped query.

        Args:
            query_name: Name of the skipped query
            reason: Reason why the query was skipped

        Returns:
            Path to generated file, or empty string if file generation failed
        """
        try:
            # Create filename from query name
            filename = f'{query_name}.md'
            file_path = os.path.join(self.output_dir, filename)

            # Build file content
            content_parts = []

            # Add query description header
            title = query_name.replace('_', ' ').title()
            content_parts.append(f'# {title}\n')

            # Add generation timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            content_parts.append(f'**Generated**: {timestamp}\n')

            # Add skipped status
            content_parts.append('## Status\n')
            content_parts.append('**Query Skipped**\n')

            # Add reason
            content_parts.append('## Reason\n')
            content_parts.append(f'{reason}\n')

            # Add informational note
            content_parts.append('## Note\n')
            content_parts.append('This query was not executed during the analysis. ')
            content_parts.append('No data is available for this query result.')

            # Combine all parts
            content = '\n'.join(content_parts)

            # Save file to output directory
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return file_path
            except OSError as e:
                error_msg = f'Failed to write skipped query file {file_path}: {str(e)}'
                logger.error(error_msg)
                self.errors.append((query_name, error_msg))
                return ''

        except Exception as e:
            error_msg = (
                f'Unexpected error generating skipped query file for {query_name}: {str(e)}'
            )
            logger.error(error_msg)
            self.errors.append((query_name, error_msg))
            return ''

    def _generate_manifest(self) -> None:
        """Generate manifest.md with links to all files."""
        try:
            manifest_path = os.path.join(self.output_dir, 'manifest.md')

            content_parts = []

            # Add title
            content_parts.append('# Database Analysis Manifest\n')

            # Add metadata section
            content_parts.append('## Metadata')
            database_name = self.metadata.get('database', 'Unknown')
            content_parts.append(f'- **Database**: {database_name}')

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            content_parts.append(f'- **Generated**: {timestamp}')

            analysis_period = self.metadata.get('analysis_period', 'N/A')
            content_parts.append(f'- **Analysis Period**: {analysis_period}')

            performance_enabled = self.metadata.get('performance_enabled', True)
            performance_status = 'Enabled' if performance_enabled else 'Disabled'
            content_parts.append(f'- **Performance Schema**: {performance_status}\n')

            # Get query categories and descriptions from database_analysis_queries
            schema_queries = get_schema_queries()
            performance_queries = get_performance_queries()
            query_descriptions = get_query_descriptions()

            # Add Query Results Files section
            content_parts.append('## Query Results Files\n')

            # Add Schema Queries section
            content_parts.append('### Schema Queries')
            for query_name in schema_queries:
                filename = f'{query_name}.md'
                description = query_descriptions.get(query_name, 'No description')

                # Check if query was skipped
                if query_name in self.skipped_queries:
                    reason = self.skipped_queries[query_name]
                    content_parts.append(
                        f'- [{query_name.replace("_", " ").title()}](./{filename}) - **SKIPPED**: {reason}'
                    )
                else:
                    content_parts.append(
                        f'- [{query_name.replace("_", " ").title()}](./{filename}) - {description}'
                    )

            content_parts.append('')  # Empty line between sections

            # Add Performance Queries section
            content_parts.append('### Performance Queries')
            for query_name in performance_queries:
                filename = f'{query_name}.md'
                description = query_descriptions.get(query_name, 'No description')

                # Check if query was skipped
                if query_name in self.skipped_queries:
                    reason = self.skipped_queries[query_name]
                    content_parts.append(
                        f'- [{query_name.replace("_", " ").title()}](./{filename}) - **SKIPPED**: {reason}'
                    )
                else:
                    content_parts.append(
                        f'- [{query_name.replace("_", " ").title()}](./{filename}) - {description}'
                    )

            content_parts.append('')  # Empty line before skipped queries

            # Add skipped queries section if any
            if self.skipped_queries:
                content_parts.append('## Skipped Queries\n')
                content_parts.append('The following queries were not executed:\n')
                for query_name, reason in self.skipped_queries.items():
                    content_parts.append(f'- **{query_name.replace("_", " ").title()}**: {reason}')
                content_parts.append('')  # Empty line after skipped queries

            # Add summary statistics
            content_parts.append('## Summary Statistics')

            # Calculate statistics from results
            total_tables = 0
            total_columns = 0
            total_indexes = 0
            total_foreign_keys = 0
            total_queries = 0
            total_procedures = 0
            total_triggers = 0

            # Extract statistics from query results
            if 'comprehensive_table_analysis' in self.results:
                table_data = self.results['comprehensive_table_analysis'].get('data', [])
                total_tables = len(table_data) if table_data else 0

            if 'column_analysis' in self.results:
                column_data = self.results['column_analysis'].get('data', [])
                total_columns = len(column_data) if column_data else 0

            if 'comprehensive_index_analysis' in self.results:
                index_data = self.results['comprehensive_index_analysis'].get('data', [])
                total_indexes = len(index_data) if index_data else 0

            if 'foreign_key_analysis' in self.results:
                fk_data = self.results['foreign_key_analysis'].get('data', [])
                total_foreign_keys = len(fk_data) if fk_data else 0

            if 'all_queries_stats' in self.results:
                query_data = self.results['all_queries_stats'].get('data', [])
                total_queries = len(query_data) if query_data else 0
                # Count stored procedures from all_queries_stats (source_type = 'PROCEDURE')
                total_procedures = (
                    sum(1 for row in query_data if row.get('source_type') == 'PROCEDURE')
                    if query_data
                    else 0
                )

            if 'triggers_stats' in self.results:
                trigger_data = self.results['triggers_stats'].get('data', [])
                total_triggers = len(trigger_data) if trigger_data else 0

            # Add statistics
            content_parts.append(f'- **Total Tables**: {total_tables}')
            content_parts.append(f'- **Total Columns**: {total_columns}')
            content_parts.append(f'- **Total Indexes**: {total_indexes}')
            content_parts.append(f'- **Total Foreign Keys**: {total_foreign_keys}')
            content_parts.append(f'- **Query Patterns Analyzed**: {total_queries}')
            content_parts.append(f'- **Stored Procedures**: {total_procedures}')
            content_parts.append(f'- **Triggers**: {total_triggers}')

            # Add errors section if any errors occurred
            if self.errors:
                content_parts.append('\n## Errors')
                content_parts.append(
                    f'\n{len(self.errors)} error(s) occurred during file generation:\n'
                )
                for query_name, error_msg in self.errors:
                    content_parts.append(f'- **{query_name}**: {error_msg}')

            # Combine all parts
            content = '\n'.join(content_parts)

            # Save manifest file
            try:
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except OSError as e:
                error_msg = f'Failed to write manifest file {manifest_path}: {str(e)}'
                logger.error(error_msg)
                self.errors.append(('manifest', error_msg))

        except Exception as e:
            error_msg = f'Unexpected error generating manifest: {str(e)}'
            logger.error(error_msg)
            self.errors.append(('manifest', error_msg))

    def generate_all_files(self) -> Tuple[List[str], List[Tuple[str, str]]]:
        """Generate all Markdown files and manifest.

        Returns:
            Tuple of (list of generated file paths, list of errors)
            Errors are tuples of (query_name, error_message)
        """
        try:
            # Create output directory structure
            try:
                os.makedirs(self.output_dir, exist_ok=True)
            except OSError as e:
                error_msg = f'Failed to create output directory {self.output_dir}: {str(e)}'
                logger.error(error_msg)
                self.errors.append(('directory_creation', error_msg))
                return [], self.errors

            # Get all expected queries from centralized definitions
            schema_queries = get_schema_queries()
            performance_queries = get_performance_queries()
            expected_queries = schema_queries + performance_queries

            # Check if performance schema is disabled
            performance_enabled = self.metadata.get('performance_enabled', True)

            # Get list of skipped queries from metadata
            metadata_skipped_queries = self.metadata.get('skipped_queries', [])

            # Iterate through all expected queries
            for query_name in expected_queries:
                try:
                    # Check if query result exists in results dictionary
                    if query_name in self.results:
                        query_result = self.results[query_name]

                        # Check if the result has data or is valid
                        if query_result and isinstance(query_result, dict):
                            # Generate one file per query result
                            file_path = self._generate_query_file(query_name, query_result)
                            # Only add to registry if file was successfully created
                            if file_path:
                                self.file_registry.append(file_path)
                        else:
                            # Result exists but is invalid
                            reason = 'Query result is invalid or empty'
                            self.skipped_queries[query_name] = reason
                            file_path = self._generate_skipped_query_file(query_name, reason)
                            # Only add to registry if file was successfully created
                            if file_path:
                                self.file_registry.append(file_path)
                    else:
                        # Query result does not exist
                        # Determine reason for skipping
                        if query_name in metadata_skipped_queries:
                            # Query was explicitly marked as skipped by analyzer
                            if query_name in performance_queries and not performance_enabled:
                                reason = 'Performance schema is disabled. This query requires performance_schema to be enabled.'
                            else:
                                reason = 'Query was skipped during analysis'
                        elif query_name in performance_queries and not performance_enabled:
                            reason = 'Performance schema is disabled. This query requires performance_schema to be enabled.'
                        else:
                            reason = 'Query was not executed or failed during analysis'

                        self.skipped_queries[query_name] = reason
                        file_path = self._generate_skipped_query_file(query_name, reason)
                        # Only add to registry if file was successfully created
                        if file_path:
                            self.file_registry.append(file_path)

                except Exception as e:
                    # Log error and continue processing remaining files
                    error_msg = f'Error processing query {query_name}: {str(e)}'
                    logger.error(error_msg)
                    self.errors.append((query_name, error_msg))
                    # Continue to next query
                    continue

            # Generate manifest file
            self._generate_manifest()

            # Log summary
            logger.info(
                f'File generation complete. Generated {len(self.file_registry)} files with {len(self.errors)} errors'
            )

            # Return list of generated file paths and errors
            return self.file_registry, self.errors

        except Exception as e:
            error_msg = f'Critical error in generate_all_files: {str(e)}'
            logger.error(error_msg)
            self.errors.append(('generate_all_files', error_msg))
            return self.file_registry, self.errors
