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

"""EMR Troubleshooting tools for MCP server."""

import json
import os
import signal
import time
from typing import Callable, List, Optional, TypeVar

import boto3
from loguru import logger
from pydantic import Field

from awslabs.emr_troubleshooting_mcp_server.consts import (
    ATHENA_QUERY_TEMPLATES,
    DEFAULT_MAX_MATCHES,
    EMR_SDK_ISSUES_FILE,
    EMR_SERVICE_ISSUES_FILE,
    ERROR_EXCEPTION_FILE,
    HADOOP_HDFS_ISSUES_FILE,
    HADOOP_YARN_ISSUES_FILE,
    HBASE_ISSUES_FILE,
    HIVE_ISSUES_FILE,
    NO_MATCHES_MESSAGE,
    PRESTO_ISSUES_FILE,
    SPARK_ISSUES_FILE,
)
from awslabs.emr_troubleshooting_mcp_server.models import (
    EMRClusterAnalysisResponse,
    EMRIssue,
    EMRIssueOccurrence,
    EMRLogAnalysisResponse,
    EMRRecommendation,
    MatchedIssue,
)

# Maximum number of retry attempts for Athena queries
MAX_RETRY_ATTEMPTS = 3

# Type variable for generic function return type
T = TypeVar('T')


def run_with_timeout(func: Callable[..., T], args=None, kwargs=None, timeout=60) -> T:
    """Run a function with a timeout.

    Args:
        func: Function to run
        args: Function arguments
        kwargs: Function keyword arguments
        timeout: Timeout in seconds

    Returns:
        Result of the function

    Raises:
        TimeoutError: If the function times out

    """
    if args is None:
        args = ()
    if kwargs is None:
        kwargs = {}

    # Store the result
    result = None
    error = None

    # Define the timeout handler
    def timeout_handler(signum, frame):
        raise TimeoutError(f'Operation timed out after {timeout} seconds')

    # Set the timeout handler
    original_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)

    try:
        # Run the function
        result = func(*args, **kwargs)
    except Exception as e:
        error = e
    finally:
        # Cancel the alarm and restore the original handler
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)

    # Re-raise any error that occurred
    if error:
        raise error

    return result


class EMRTroubleshootingTools:
    """EMR troubleshooting tools for MCP server."""

    def __init__(self):
        """Initialize with knowledge base data."""
        self.known_issues = self._load_known_issues()
        self.issue_map = {issue.id: issue for issue in self.known_issues}
        logger.info(f'Loaded {len(self.known_issues)} known EMR issues')

    def _load_known_issues(self) -> List[EMRIssue]:
        """Load known issues from JSON files."""
        known_issues = []

        # List of issue files to load
        issue_files = [
            SPARK_ISSUES_FILE,
            HADOOP_YARN_ISSUES_FILE,
            HADOOP_HDFS_ISSUES_FILE,
            HIVE_ISSUES_FILE,
            HBASE_ISSUES_FILE,
            PRESTO_ISSUES_FILE,
            EMR_SERVICE_ISSUES_FILE,
            EMR_SDK_ISSUES_FILE,
            ERROR_EXCEPTION_FILE,
        ]

        # Load each file if it exists
        for file_path in issue_files:
            try:
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        # Each line is a separate JSON object
                        for line in f:
                            try:
                                issue_data = json.loads(line.strip())
                                issue = EMRIssue(**issue_data)
                                known_issues.append(issue)
                            except json.JSONDecodeError:
                                logger.warning(f'Invalid JSON in {file_path}: {line}')
                            except Exception as e:
                                logger.warning(f'Error processing issue in {file_path}: {e}')
                else:
                    logger.warning(f'Issue file not found: {file_path}')
            except Exception as e:
                logger.error(f'Error loading issue file {file_path}: {e}')

        return known_issues

    def _create_recommendations(
        self, matched_issues: List[MatchedIssue]
    ) -> List[EMRRecommendation]:
        """Create recommendations based on matched issues."""
        recommendations = []

        for matched_issue in matched_issues:
            issue = matched_issue.issue
            recommendation = EMRRecommendation(
                issue_id=issue.id,
                summary=f'Fix for {issue.summary}',
                description=issue.description,
                knowledge_center_links=issue.knowledge_center_links,
            )
            recommendations.append(recommendation)

        return recommendations

    def _match_issues_in_log(
        self, log_content: str, max_matches: int = DEFAULT_MAX_MATCHES
    ) -> List[MatchedIssue]:
        """Match known issues in the log content."""
        matched_issues = []
        matched_issue_ids = set()

        # Skip if log content is empty
        if not log_content or not log_content.strip():
            return matched_issues

        # Process each known issue
        for issue in self.known_issues:
            # Skip if we've already matched the maximum number of issues
            if len(matched_issues) >= max_matches:
                break

            # Skip if we've already matched this issue
            if issue.id in matched_issue_ids:
                continue

            # Check each keyword for this issue
            matched_patterns = []
            for keyword in issue.keywords:
                # Use simple string matching for keywords
                if keyword.lower() in log_content.lower():
                    matched_patterns.append(keyword)

            # If we matched any keywords, add this issue to the results
            if matched_patterns:
                matched_issue = MatchedIssue(
                    issue=issue,
                    matched_patterns=matched_patterns,
                    confidence=0.9,  # Default confidence
                )
                matched_issues.append(matched_issue)
                matched_issue_ids.add(issue.id)

        return matched_issues[:max_matches]

    def register(self, mcp):
        """Register all EMR troubleshooting tools with the MCP server."""

        @mcp.tool(name='analyze_emr_logs')
        async def analyze_emr_logs_tool(
            log_content: str = Field(
                ...,
                description=(
                    'EMR log content to analyze for known issues. '
                    'Provide raw log text from EMR cluster components '
                    '(Spark, YARN, Hadoop, etc.). The tool will search '
                    'for patterns matching curated EMR issues and recommendations.'
                ),
            ),
        ) -> EMRLogAnalysisResponse:
            """Analyze EMR logs for known issues and recommendations.

            This tool performs searchs against a
            comprehensive knowledge base of curated EMR issues across
            multiple big data frameworks.
            It's useful for quick analysis of directly provided EMR logs.

            ## Usage Examples
            - Analyze Spark driver logs for OutOfMemoryError issues
            - Check YARN logs for container killed errors
            - Identify common Hadoop HDFS issues in namenode logs

            ## Response Format
            The response includes matched issues with:
            - Issue summary and detailed description
            - Matched patterns found in the logs
            - Confidence score for each match
            - Links to AWS Knowledge Center articles when available
            - Recommendations for remediation steps
            """
            return await self.analyze_emr_logs(log_content)

        @mcp.tool(name='analyze_emr_cluster_logs')
        async def analyze_emr_cluster_logs_tool(
            cluster_id: str = Field(
                ...,
                description=(
                    'EMR cluster ID to analyze (e.g., j-12FTFQ3AGIYQ4). '
                    'Must be a valid cluster with logging enabled to S3. '
                    "The tool will connect to the cluster's S3 logs and "
                    'perform Athena queries to identify known issues.'
                ),
            ),
            region: Optional[str] = Field(
                default=None,
                description=(
                    'AWS region where the cluster is located. If not '
                    'provided, uses AWS_DEFAULT_REGION environment '
                    'variable or defaults to us-east-1.'
                ),
            ),
            time_window: int = Field(
                default=300,
                description=(
                    'Time window in seconds to analyze logs '
                    '(default: 300 = 5 minutes). Range: 30-300 seconds.'
                ),
                ge=30,
                le=300,
            ),
        ) -> EMRClusterAnalysisResponse:
            """Analyze EMR cluster logs using Amazon Athena.

            This tool connects to an EMR cluster's logs in S3 and runs
            Athena queries to identify known issues based on
            a comprehensive knowledge base of curated EMR issues.

            ## Prerequisites
            - EMR cluster with logging enabled to S3
            - AWS credentials with permissions for EMR, Athena, and S3
            - Athena query result location configured

            ## Response Format
            The response includes detailed findings with:
            - Issue summary and description
            - Component classification (Spark, YARN, Hadoop, etc.)
            - Occurrence count and sample log evidence
            - AWS Knowledge Center links when available for additional guidance
            """
            return await self.analyze_emr_cluster_logs(cluster_id, region, time_window)

    async def analyze_emr_logs(self, log_content: str) -> EMRLogAnalysisResponse:
        """Analyze EMR logs for known issues and provide recommendations.

        Args:
            log_content: EMR log content to analyze

        Returns:
            EMRLogAnalysisResponse: Analysis results with matched issues

        """
        try:
            # Validate input
            if not log_content or not log_content.strip():
                return EMRLogAnalysisResponse(
                    matched_issues=[],
                    summary='No log content provided for analysis.',
                    total_matches=0,
                )

            # Match issues in the log content
            matched_issues = self._match_issues_in_log(log_content)

            # Determine summary based on matches
            if not matched_issues:
                summary = NO_MATCHES_MESSAGE
            elif len(matched_issues) == 1:
                summary = f'Found 1 known issue: {matched_issues[0].issue.summary}'
            else:
                titles = [issue.issue.summary for issue in matched_issues]
                summary = f'Found {len(matched_issues)} known issues: {", ".join(titles)}'

            # Return response
            return EMRLogAnalysisResponse(
                matched_issues=matched_issues,
                summary=summary,
                total_matches=len(matched_issues),
            )

        except Exception as e:
            logger.error(f'Error analyzing EMR logs: {str(e)}')
            # Return empty response on error
            return EMRLogAnalysisResponse(
                matched_issues=[],
                summary=f'Error analyzing logs: {str(e)}',
                total_matches=0,
            )

    async def analyze_emr_cluster_logs(
        self, cluster_id: str, region: Optional[str] = None, time_window: int = 3600
    ) -> EMRClusterAnalysisResponse:
        """Analyze EMR cluster logs using Athena.

        This tool connects to an EMR cluster's logs in S3 and runs Athena
        queries to identify known issues based on the knowledge base
        patterns.

        Prerequisites:
        1. An AWS account with appropriate permissions
        2. EMR cluster with logging enabled to S3

        Args:
            cluster_id: EMR cluster ID to analyze
            region: AWS region (defaults to environment variable)
            time_window: Time window in seconds to analyze (default: 300)

        Returns:
            EMRClusterAnalysisResponse: Analysis results with matched issues

        """
        start_time = time.time()

        try:
            # Set up AWS region
            region = region or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

            # Create AWS clients
            emr_client = boto3.client('emr', region_name=region)

            # Get cluster log location
            cluster_info = emr_client.describe_cluster(ClusterId=cluster_id)
            log_uri = cluster_info['Cluster'].get('LogUri')

            if not log_uri:
                return EMRClusterAnalysisResponse(
                    status='FAILED',
                    source_type='cluster',
                    source_id=cluster_id,
                    issues_found=0,
                    results=[],
                    error='Cluster does not have logging enabled',
                )

            # Ensure log_uri ends with /
            if not log_uri.endswith('/'):
                log_uri += '/'

            # Add cluster ID to path
            log_uri += f'{cluster_id}/'

            # Convert s3n:// to s3:// for Athena compatibility
            if log_uri.startswith('s3n://'):
                log_uri = log_uri.replace('s3n://', 's3://')

            # Run Athena analysis
            results = self._run_athena_analysis(
                log_location=log_uri,
                session_id=(f'cluster_{cluster_id}_{int(time.time())}'),
                region=region,
            )

            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)

            return EMRClusterAnalysisResponse(
                status='SUCCEEDED',
                source_type='cluster',
                source_id=cluster_id,
                issues_found=len(results),
                total_occurrences=sum(r.occurrence_count for r in results),
                results=results,
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            logger.error(f'Error analyzing EMR cluster logs: {e}')
            execution_time_ms = int((time.time() - start_time) * 1000)

            return EMRClusterAnalysisResponse(
                status='FAILED',
                source_type='cluster',
                source_id=cluster_id,
                issues_found=0,
                results=[],
                execution_time_ms=execution_time_ms,
                error=str(e),
            )

    def _get_or_create_bucket(self, region: str) -> str:
        """Get or create an S3 bucket for Athena results."""
        account_id = boto3.client('sts').get_caller_identity()['Account']
        bucket_name = f'emr-log-analysis-{account_id}-{region}'.lower()

        s3_client = boto3.client('s3', region_name=region)

        try:
            s3_client.head_bucket(Bucket=bucket_name)
        except Exception:
            if region == 'us-east-1':
                s3_client.create_bucket(Bucket=bucket_name)
            else:
                s3_client.create_bucket(
                    Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region}
                )

        return bucket_name

    def _run_athena_analysis(
        self, log_location: str, session_id: str, region: str
    ) -> List[EMRIssueOccurrence]:
        """Run Athena analysis on EMR logs using knowledge base."""
        logger.info(f'Running Athena analysis for session {session_id}')
        logger.info(f'Log location: {log_location}')

        try:
            athena_client = boto3.client('athena', region_name=region)
            database_name = f'emr_analysis_{session_id.replace("-", "_")}'
            result_location = f's3://{self._get_or_create_bucket(region)}/athena-results/'

            self._setup_athena_database(athena_client, database_name, result_location)
            logs_table, kb_table = self._create_athena_tables(
                athena_client, database_name, result_location, log_location, region, session_id
            )
            analysis_results = self._run_keyword_analysis(
                athena_client, database_name, result_location, logs_table, kb_table
            )
            results = self._process_analysis_results(analysis_results)
            self._cleanup_athena_database(athena_client, database_name, result_location)

            return results[:10]

        except Exception as e:
            logger.error(f'Error in Athena analysis: {e}')
            return []

    def _setup_athena_database(self, athena_client, database_name: str, result_location: str):
        """Create Athena database for analysis."""
        self._execute_athena_query(
            athena_client,
            f'CREATE DATABASE IF NOT EXISTS {database_name}',
            database_name,
            result_location,
        )

    def _create_athena_tables(
        self,
        athena_client,
        database_name: str,
        result_location: str,
        log_location: str,
        region: str,
        session_id: str,
    ) -> tuple:
        """Create logs and knowledge base tables."""
        # Create logs table
        logs_table = f'{database_name}.emr_logs'
        create_logs_query = ATHENA_QUERY_TEMPLATES['create_logs_table'].format(
            table_name=logs_table, logs_location=log_location
        )
        logger.info(f'Creating logs table: {logs_table}')
        self._execute_athena_query(
            athena_client, create_logs_query, database_name, result_location
        )

        # Create knowledge base table
        kb_location = self._upload_knowledge_base_to_s3(region, session_id)
        kb_table = f'{database_name}.known_issues'
        create_kb_query = ATHENA_QUERY_TEMPLATES['create_kb_table'].format(
            table_name=kb_table, kb_location=kb_location
        )
        logger.info(f'Creating knowledge base table: {kb_table}')
        self._execute_athena_query(athena_client, create_kb_query, database_name, result_location)

        return (logs_table, kb_table)

    def _run_keyword_analysis(
        self,
        athena_client,
        database_name: str,
        result_location: str,
        logs_table: str,
        kb_table: str,
    ):
        """Run keyword matching analysis query."""
        analysis_query = ATHENA_QUERY_TEMPLATES['keyword_matching_analysis'].format(
            logs_table=logs_table, kb_table=kb_table
        )
        logger.info('Running keyword matching analysis')
        return self._execute_athena_query(
            athena_client, analysis_query, database_name, result_location, return_results=True
        )

    def _process_analysis_results(self, analysis_results) -> List[EMRIssueOccurrence]:
        """Process Athena results into EMRIssueOccurrence objects."""
        if not analysis_results or 'ResultSet' not in analysis_results:
            return []

        rows = analysis_results['ResultSet'].get('Rows', [])
        issue_groups = self._group_results_by_issue(rows)
        return self._convert_to_issue_occurrences(issue_groups)

    def _group_results_by_issue(self, rows) -> dict:
        """Group analysis results by issue_id and matched_keyword."""
        issue_groups = {}
        for row in rows[1:]:  # Skip header
            data = row.get('Data', [])
            if len(data) >= 4:
                issue_id = data[0].get('VarCharValue', '')
                matched_keyword = data[1].get('VarCharValue', '')
                log_data = data[2].get('VarCharValue', '')

                key = (issue_id, matched_keyword)
                if key not in issue_groups:
                    issue_groups[key] = {
                        'issue_id': issue_id,
                        'matched_keyword': matched_keyword,
                        'count': 0,
                        'sample_logs': [],
                    }

                issue_groups[key]['count'] += 1
                if len(issue_groups[key]['sample_logs']) < 3:
                    issue_groups[key]['sample_logs'].append(log_data[:200])

        return issue_groups

    def _convert_to_issue_occurrences(self, issue_groups: dict) -> List[EMRIssueOccurrence]:
        """Convert grouped results to EMRIssueOccurrence objects."""
        results = []
        for group_data in issue_groups.values():
            issue_details = self._get_issue_details(group_data['issue_id'])
            results.append(
                EMRIssueOccurrence(
                    issue_id=group_data['issue_id'],
                    issue_summary=issue_details['summary'],
                    issue_description=issue_details['description'],
                    component=issue_details['component'],
                    matched_keyword=group_data['matched_keyword'],
                    occurrence_count=group_data['count'],
                    sample_data=group_data['sample_logs'],
                    knowledge_center_links=issue_details['links'],
                )
            )

        results.sort(key=lambda x: x.occurrence_count, reverse=True)
        return results

    def _get_issue_details(self, issue_id: str) -> dict:
        """Get issue details from knowledge base."""
        for known_issue in self.known_issues:
            if known_issue.id == issue_id:
                component = 'EMR'
                if known_issue.id.startswith('spark-'):
                    component = 'Spark'
                elif known_issue.id.startswith('yarn-'):
                    component = 'YARN'
                elif known_issue.id.startswith('hadoop-'):
                    component = 'Hadoop'
                elif known_issue.id.startswith('hive-'):
                    component = 'Hive'
                elif known_issue.id.startswith('hbase-'):
                    component = 'HBase'
                elif known_issue.id.startswith('presto-'):
                    component = 'Presto'

                return {
                    'summary': known_issue.summary,
                    'description': known_issue.description,
                    'component': component,
                    'links': known_issue.knowledge_center_links,
                }

        return {
            'summary': 'Pattern Detected in EMR Logs',
            'description': ('A pattern was detected in the EMR logs that matches a known issue.'),
            'component': 'EMR',
            'links': [],
        }

    def _cleanup_athena_database(self, athena_client, database_name: str, result_location: str):
        """Clean up temporary Athena database."""
        try:
            self._execute_athena_query(
                athena_client, f'DROP DATABASE {database_name} CASCADE', 'default', result_location
            )
            logger.info(f'Cleaned up temporary database: {database_name}')
        except Exception as e:
            logger.warning(f'Failed to clean up database {database_name}: {e}')

    def _upload_knowledge_base_to_s3(self, region: str, session_id: str, timeout: int = 60) -> str:
        """Upload knowledge base JSON files to S3 for Athena analysis.

        Args:
            region: AWS region
            session_id: Unique session identifier
            timeout: Operation timeout in seconds

        Returns:
            S3 URI for the uploaded knowledge base

        Raises:
            TimeoutError: If the operation times out
            RuntimeError: If the upload fails

        """
        start_time = time.time()
        logger.info(f'Uploading knowledge base to S3 with {timeout}s timeout')

        try:
            bucket_name = self._get_or_create_bucket(region)
            s3_client = boto3.client('s3', region_name=region)

            # Create S3 prefix for knowledge base
            kb_prefix = f'knowledge-base/{session_id}/'

            # Combine all knowledge base files into single JSONL format
            all_issues = []
            for issue in self.known_issues:
                # Check for timeout during processing
                if (time.time() - start_time) > timeout:
                    raise TimeoutError(f'Knowledge base prep timed out after {timeout} seconds')

                issue_dict = {
                    'id': issue.id,
                    'summary': issue.summary,
                    'description': issue.description,
                    'keywords': issue.keywords,
                    'knowledge_center_links': issue.knowledge_center_links,
                }
                all_issues.append(json.dumps(issue_dict))

            # Upload combined knowledge base
            kb_content = '\n'.join(all_issues)
            s3_key = f'{kb_prefix}known_issues.json'

            # Check for timeout before upload
            if (time.time() - start_time) > timeout:
                raise TimeoutError(f'Knowledge base upload timed out after {timeout} seconds')

            s3_client.put_object(Bucket=bucket_name, Key=s3_key, Body=kb_content.encode('utf-8'))

            elapsed_time = time.time() - start_time
            logger.info(
                f'Uploaded knowledge base to s3://{bucket_name}/{s3_key} in {elapsed_time:.2f}s'
            )
            return f's3://{bucket_name}/{kb_prefix}'

        except TimeoutError as e:
            logger.error(f'S3 upload operation timed out: {str(e)}')
            raise
        except Exception as e:
            logger.error(f'Error uploading knowledge base to S3: {str(e)}')
            raise RuntimeError(f'Failed to upload knowledge base to S3: {str(e)}')

    def _execute_athena_query(
        self,
        athena_client,
        query: str,
        database: str,
        result_location: str,
        return_results: bool = False,
        timeout: int = None,
    ):
        """Execute an Athena query and optionally return results.

        Args:
            athena_client: Boto3 Athena client
            query: SQL query to execute
            database: Athena database name
            result_location: S3 location for query results
            return_results: Whether to return query results
            timeout: Query timeout in seconds (defaults to ATHENA_TIMEOUT)

        Returns:
            Query response or results if return_results is True

        Raises:
            RuntimeError: If query fails or times out

        """
        from .consts import ATHENA_TIMEOUT

        # Use provided timeout or default from constants
        timeout = timeout or ATHENA_TIMEOUT
        logger.info(f'Executing Athena query in database {database} with {timeout}s timeout')
        logger.debug(f'Query: {query}')

        # Start query execution
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': database},
            ResultConfiguration={'OutputLocation': result_location},
        )

        query_execution_id = response['QueryExecutionId']
        logger.info(f'Started Athena query: {query_execution_id}')

        # Wait for query to complete with timeout
        start_time = time.time()
        attempt = 0

        while (time.time() - start_time) < timeout:
            response = athena_client.get_query_execution(QueryExecutionId=query_execution_id)

            status = response['QueryExecution']['Status']['State']

            if status == 'SUCCEEDED':
                elapsed_time = time.time() - start_time
                logger.info(
                    f'Query {query_execution_id} completed successfully in {elapsed_time:.2f}s'
                )
                if return_results:
                    return athena_client.get_query_results(QueryExecutionId=query_execution_id)
                return response
            elif status in ['FAILED', 'CANCELLED']:
                error_msg = response['QueryExecution']['Status'].get(
                    'StateChangeReason', 'Unknown error'
                )
                logger.error(f'Query {query_execution_id} failed: {error_msg}')
                raise RuntimeError(f'Athena query failed: {error_msg}')

            # Check if we've reached max attempts
            if attempt >= MAX_RETRY_ATTEMPTS:
                logger.warning(
                    f'Reached maximum retry attempts ({MAX_RETRY_ATTEMPTS}) for query {query_execution_id}'
                )
                break

            # Wait with exponential backoff
            sleep_time = min(2 * (1.2**attempt), 10)
            time.sleep(sleep_time)
            attempt += 1

        # If we get here, the query timed out
        elapsed_time = time.time() - start_time
        logger.error(f'Query {query_execution_id} timed out after {elapsed_time:.2f}s')

        # Try to cancel the query
        try:
            athena_client.stop_query_execution(QueryExecutionId=query_execution_id)
            logger.info(f'Cancelled timed out query: {query_execution_id}')
        except Exception as e:
            logger.warning(f'Failed to cancel query {query_execution_id}: {e}')

        raise RuntimeError(f'Query {query_execution_id} timed out after {timeout} seconds')
