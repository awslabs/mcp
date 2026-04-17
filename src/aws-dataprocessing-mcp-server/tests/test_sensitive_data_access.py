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

"""Tests for sensitive data access controls.

This module tests that the --allow-sensitive-data-access flag properly restricts
access to operations that expose sensitive customer data, including:
- Database connection passwords
- Query results containing customer data
- Interactive session execution outputs
- Job run details and logs
"""

import pytest
from awslabs.aws_dataprocessing_mcp_server.core.glue_data_catalog.data_catalog_handler import (
    DataCatalogManager,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.athena.athena_query_handler import (
    AthenaQueryHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_ec2_steps_handler import (
    EMREc2StepsHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_serverless_job_run_handler import (
    EMRServerlessJobRunHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_etl_handler import (
    GlueEtlJobsHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.interactive_sessions_handler import (
    GlueInteractiveSessionsHandler,
)
from unittest.mock import MagicMock, patch


class TestSensitiveDataAccess:
    """Tests for sensitive data access controls."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock Context."""
        mock = MagicMock()
        mock.request_id = 'test-request-id'
        return mock

    @pytest.fixture
    def mock_glue_client(self):
        """Create a mock Glue client."""
        return MagicMock()

    @pytest.fixture
    def mock_athena_client(self):
        """Create a mock Athena client."""
        return MagicMock()

    @pytest.fixture
    def mock_emr_client(self):
        """Create a mock EMR client."""
        return MagicMock()

    @pytest.fixture
    def mock_emr_serverless_client(self):
        """Create a mock EMR Serverless client."""
        return MagicMock()

    # ==================== CRITICAL: Connection Password Tests ====================

    @pytest.mark.asyncio
    async def test_get_connection_enforces_hide_password_when_flag_disabled(
        self, mock_ctx, mock_glue_client
    ):
        """Test that get_connection enforces hide_password=True when allow_sensitive_data_access=False."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            # Create manager WITHOUT allow_sensitive_data_access
            manager = DataCatalogManager(allow_write=False, allow_sensitive_data_access=False)

            mock_glue_client.get_connection.return_value = {
                'Connection': {
                    'Name': 'test-conn',
                    'ConnectionType': 'JDBC',
                    'ConnectionProperties': {'JDBC_CONNECTION_URL': 'jdbc:mysql://localhost'},
                }
            }

            # User tries to pass hide_password=False, but it should be enforced to True
            result = await manager.get_connection(
                mock_ctx, connection_name='test-conn', hide_password=False
            )

            # Verify that HidePassword=True was enforced
            mock_glue_client.get_connection.assert_called_once()
            call_args = mock_glue_client.get_connection.call_args[1]
            assert call_args['HidePassword'] is True, 'HidePassword should be enforced to True'

            assert result.isError is False

    @pytest.mark.asyncio
    async def test_get_connection_respects_hide_password_when_flag_enabled(
        self, mock_ctx, mock_glue_client
    ):
        """Test that get_connection respects user's hide_password choice when allow_sensitive_data_access=True."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            # Create manager WITH allow_sensitive_data_access
            manager = DataCatalogManager(allow_write=False, allow_sensitive_data_access=True)

            mock_glue_client.get_connection.return_value = {
                'Connection': {
                    'Name': 'test-conn',
                    'ConnectionType': 'JDBC',
                    'ConnectionProperties': {
                        'JDBC_CONNECTION_URL': 'jdbc:mysql://localhost',
                        'PASSWORD': 'secret123',  # pragma: allowlist secret
                    },
                }
            }

            # User passes hide_password=False and it should be honored
            result = await manager.get_connection(
                mock_ctx, connection_name='test-conn', hide_password=False
            )

            # Verify that HidePassword=False was honored
            mock_glue_client.get_connection.assert_called_once()
            call_args = mock_glue_client.get_connection.call_args[1]
            assert 'HidePassword' not in call_args or call_args['HidePassword'] is False, (
                'HidePassword should be False when flag enabled'
            )

            assert result.isError is False

    @pytest.mark.asyncio
    async def test_list_connections_enforces_hide_password_when_flag_disabled(
        self, mock_ctx, mock_glue_client
    ):
        """Test that list_connections enforces hide_password=True when allow_sensitive_data_access=False."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            manager = DataCatalogManager(allow_write=False, allow_sensitive_data_access=False)

            mock_glue_client.get_connections.return_value = {'ConnectionList': []}

            # User tries to pass hide_password=False, but it should be enforced to True
            result = await manager.list_connections(mock_ctx, hide_password=False)

            # Verify that HidePassword=True was enforced
            mock_glue_client.get_connections.assert_called_once()
            call_args = mock_glue_client.get_connections.call_args[1]
            assert call_args['HidePassword'] is True, 'HidePassword should be enforced to True'

            assert result.isError is False

    # ==================== HIGH: Query Result Protection Tests ====================

    @pytest.mark.asyncio
    async def test_get_entity_records_blocked_without_flag(self, mock_ctx, mock_glue_client):
        """Test that get_entity_records is blocked when allow_sensitive_data_access=False."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            manager = DataCatalogManager(allow_write=False, allow_sensitive_data_access=False)

            result = await manager.get_entity_records(
                mock_ctx, connection_name='test-conn', entity_name='Account', limit=10
            )

            # Verify operation was blocked
            mock_glue_client.get_entity_records.assert_not_called()
            assert result.isError is True
            assert 'requires --allow-sensitive-data-access flag' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_entity_records_allowed_with_flag(self, mock_ctx, mock_glue_client):
        """Test that get_entity_records succeeds when allow_sensitive_data_access=True."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            manager = DataCatalogManager(allow_write=False, allow_sensitive_data_access=True)

            mock_glue_client.get_entity_records.return_value = {
                'Records': [{'Id': '001', 'Name': 'Test'}],
                'NextToken': None,
            }

            result = await manager.get_entity_records(
                mock_ctx, connection_name='test-conn', entity_name='Account', limit=10
            )

            # Verify operation was allowed
            mock_glue_client.get_entity_records.assert_called_once()
            assert result.isError is False

    @pytest.mark.asyncio
    async def test_athena_get_query_results_blocked_without_flag(
        self, mock_ctx, mock_athena_client
    ):
        """Test that Athena get-query-results is blocked when allow_sensitive_data_access=False."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_athena_client,
        ):
            mcp = MagicMock()
            handler = AthenaQueryHandler(mcp, allow_write=False, allow_sensitive_data_access=False)

            result = await handler.manage_aws_athena_queries(
                mock_ctx, operation='get-query-results', query_execution_id='test-query-id'
            )

            # Verify operation was blocked
            mock_athena_client.get_query_results.assert_not_called()
            assert result.isError is True
            assert 'requires --allow-sensitive-data-access flag' in result.content[0].text

    @pytest.mark.asyncio
    async def test_athena_get_query_results_allowed_with_flag(self, mock_ctx, mock_athena_client):
        """Test that Athena get-query-results succeeds when allow_sensitive_data_access=True."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_athena_client,
        ):
            mcp = MagicMock()
            handler = AthenaQueryHandler(mcp, allow_write=False, allow_sensitive_data_access=True)

            mock_athena_client.get_query_results.return_value = {
                'ResultSet': {'Rows': []},
                'NextToken': None,
            }

            result = await handler.manage_aws_athena_queries(
                mock_ctx, operation='get-query-results', query_execution_id='test-query-id'
            )

            # Verify operation was allowed
            mock_athena_client.get_query_results.assert_called_once()
            assert result.isError is False

    @pytest.mark.asyncio
    async def test_glue_get_statement_blocked_without_flag(self, mock_ctx, mock_glue_client):
        """Test that Glue get-statement is blocked when allow_sensitive_data_access=False."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            mcp = MagicMock()
            handler = GlueInteractiveSessionsHandler(
                mcp, allow_write=True, allow_sensitive_data_access=False
            )

            result = await handler.manage_aws_glue_statements(
                mock_ctx, operation='get-statement', session_id='test-session', statement_id=1
            )

            # Verify operation was blocked
            mock_glue_client.get_statement.assert_not_called()
            assert result.isError is True
            assert 'requires --allow-sensitive-data-access flag' in result.content[0].text

    @pytest.mark.asyncio
    async def test_glue_get_statement_allowed_with_flag(self, mock_ctx, mock_glue_client):
        """Test that Glue get-statement succeeds when allow_sensitive_data_access=True."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            mcp = MagicMock()
            handler = GlueInteractiveSessionsHandler(
                mcp, allow_write=True, allow_sensitive_data_access=True
            )

            mock_glue_client.get_statement.return_value = {
                'Statement': {
                    'Id': 1,
                    'State': 'COMPLETED',
                    'Output': {'Data': {'TextPlain': 'result data'}},
                }
            }

            result = await handler.manage_aws_glue_statements(
                mock_ctx, operation='get-statement', session_id='test-session', statement_id=1
            )

            # Verify operation was allowed
            mock_glue_client.get_statement.assert_called_once()
            assert result.isError is False

    # ==================== MEDIUM: Job Output Protection Tests ====================

    @pytest.mark.asyncio
    async def test_glue_get_job_run_blocked_without_flag(self, mock_ctx, mock_glue_client):
        """Test that Glue get-job-run is blocked when allow_sensitive_data_access=False."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            mcp = MagicMock()
            handler = GlueEtlJobsHandler(mcp, allow_write=False, allow_sensitive_data_access=False)

            result = await handler.manage_aws_glue_jobs(
                mock_ctx, operation='get-job-run', job_name='test-job', job_run_id='jr_123'
            )

            # Verify operation was blocked
            mock_glue_client.get_job_run.assert_not_called()
            assert result.isError is True
            assert 'requires --allow-sensitive-data-access flag' in result.content[0].text

    @pytest.mark.asyncio
    async def test_glue_get_job_run_allowed_with_flag(self, mock_ctx, mock_glue_client):
        """Test that Glue get-job-run succeeds when allow_sensitive_data_access=True."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            mcp = MagicMock()
            handler = GlueEtlJobsHandler(mcp, allow_write=False, allow_sensitive_data_access=True)

            mock_glue_client.get_job_run.return_value = {
                'JobRun': {'Id': 'jr_123', 'JobName': 'test-job', 'JobRunState': 'SUCCEEDED'}
            }

            result = await handler.manage_aws_glue_jobs(
                mock_ctx, operation='get-job-run', job_name='test-job', job_run_id='jr_123'
            )

            # Verify operation was allowed
            mock_glue_client.get_job_run.assert_called_once()
            assert result.isError is False

    @pytest.mark.asyncio
    async def test_emr_serverless_get_job_run_blocked_without_flag(
        self, mock_ctx, mock_emr_serverless_client
    ):
        """Test that EMR Serverless get-job-run is blocked when allow_sensitive_data_access=False."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_emr_serverless_client,
        ):
            mcp = MagicMock()
            handler = EMRServerlessJobRunHandler(
                mcp, allow_write=False, allow_sensitive_data_access=False
            )

            result = await handler.manage_aws_emr_serverless_job_runs(
                mock_ctx,
                operation='get-job-run',
                application_id='app-123',
                job_run_id='jr-456',
            )

            # Verify operation was blocked
            mock_emr_serverless_client.get_job_run.assert_not_called()
            assert result.isError is True
            assert 'requires --allow-sensitive-data-access flag' in result.content[0].text

    @pytest.mark.asyncio
    async def test_emr_serverless_get_job_run_allowed_with_flag(
        self, mock_ctx, mock_emr_serverless_client
    ):
        """Test that EMR Serverless get-job-run succeeds when allow_sensitive_data_access=True."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_emr_serverless_client,
        ):
            mcp = MagicMock()
            handler = EMRServerlessJobRunHandler(
                mcp, allow_write=False, allow_sensitive_data_access=True
            )

            mock_emr_serverless_client.get_job_run.return_value = {
                'jobRun': {'jobRunId': 'jr-456', 'applicationId': 'app-123', 'state': 'SUCCESS'}
            }

            result = await handler.manage_aws_emr_serverless_job_runs(
                mock_ctx,
                operation='get-job-run',
                application_id='app-123',
                job_run_id='jr-456',
            )

            # Verify operation was allowed
            mock_emr_serverless_client.get_job_run.assert_called_once()
            assert result.isError is False

    @pytest.mark.asyncio
    async def test_emr_describe_step_blocked_without_flag(self, mock_ctx, mock_emr_client):
        """Test that EMR EC2 describe-step is blocked when allow_sensitive_data_access=False."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_emr_client,
        ):
            mcp = MagicMock()
            handler = EMREc2StepsHandler(mcp, allow_write=False, allow_sensitive_data_access=False)

            result = await handler.manage_aws_emr_ec2_steps(
                mock_ctx, operation='describe-step', cluster_id='j-123', step_id='s-456'
            )

            # Verify operation was blocked
            mock_emr_client.describe_step.assert_not_called()
            assert result.isError is True
            assert 'requires --allow-sensitive-data-access flag' in result.content[0].text

    @pytest.mark.asyncio
    async def test_emr_describe_step_allowed_with_flag(self, mock_ctx, mock_emr_client):
        """Test that EMR EC2 describe-step succeeds when allow_sensitive_data_access=True."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_emr_client,
        ):
            mcp = MagicMock()
            handler = EMREc2StepsHandler(mcp, allow_write=False, allow_sensitive_data_access=True)

            mock_emr_client.describe_step.return_value = {
                'Step': {
                    'Id': 's-456',
                    'Name': 'Test Step',
                    'Status': {'State': 'COMPLETED'},
                    'Config': {'Args': ['spark-submit', 'script.py']},
                }
            }

            result = await handler.manage_aws_emr_ec2_steps(
                mock_ctx, operation='describe-step', cluster_id='j-123', step_id='s-456'
            )

            # Verify operation was allowed
            mock_emr_client.describe_step.assert_called_once()
            assert result.isError is False

    # ==================== Read-Only Operations Should Still Work ====================

    @pytest.mark.asyncio
    async def test_athena_list_query_executions_not_blocked(self, mock_ctx, mock_athena_client):
        """Test that list-query-executions is NOT blocked (only get-query-results is sensitive)."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_athena_client,
        ):
            mcp = MagicMock()
            handler = AthenaQueryHandler(mcp, allow_write=False, allow_sensitive_data_access=False)

            mock_athena_client.list_query_executions.return_value = {
                'QueryExecutionIds': ['qe-123', 'qe-456'],
            }

            result = await handler.manage_aws_athena_queries(
                mock_ctx, operation='list-query-executions'
            )

            # Verify operation was allowed (list operations show IDs, not data)
            mock_athena_client.list_query_executions.assert_called_once()
            assert result.isError is False

    @pytest.mark.asyncio
    async def test_glue_list_statements_not_blocked(self, mock_ctx, mock_glue_client):
        """Test that list-statements is NOT blocked (only get-statement with output is sensitive)."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            mcp = MagicMock()
            handler = GlueInteractiveSessionsHandler(
                mcp, allow_write=True, allow_sensitive_data_access=False
            )

            mock_glue_client.list_statements.return_value = {
                'Statements': [{'Id': 1, 'State': 'COMPLETED'}],
            }

            result = await handler.manage_aws_glue_statements(
                mock_ctx, operation='list-statements', session_id='test-session'
            )

            # Verify operation was allowed (list operations show status, not output data)
            mock_glue_client.list_statements.assert_called_once()
            assert result.isError is False
