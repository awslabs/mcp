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
access to sensitive customer data, including:
- Database connection passwords
- Query results containing customer data
- Interactive session execution outputs
- Job run details and logs

The flag is enforced two ways, and which one applies depends on the response:

- Operations whose entire response *is* customer content are refused outright,
  since filtering would leave nothing meaningful. Athena get-query-results and
  Glue get-entity-records are in this group.
- Operations returning records that mix operational metadata with customer
  content answer with the metadata and omit those fields. EMR steps, Glue job
  runs, Glue statements and EMR Serverless job runs are in this group.

For the second group, the singular and list forms of an operation must behave
identically, since the AWS APIs behind them return the same records. Filtering
only the singular form would make the flag mean different things depending on
which form was called, which is what this suite guards against.
"""

import json
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


# An EMR step whose filtered fields all carry the same marker, so any one of them
# surviving the filter is caught by a single substring check. Shared by the
# describe-step and list-steps cases so both forms are asserted against identical
# input.
FLAG_ONLY = 'FLAG-ONLY-VALUE'

STEP_WITH_FILTERED_FIELDS = {
    'Id': 's-456',
    'Name': 'nightly-etl',
    'ActionOnFailure': 'CONTINUE',
    'Config': {
        'Jar': 's3://bucket/etl.jar',
        'MainClass': 'com.acme.Load',
        'Args': ['spark-submit', '--conf', f'spark.sql.warehouse.dir={FLAG_ONLY}'],
        'Properties': {'acme.env': FLAG_ONLY},
    },
    'Status': {
        'State': 'FAILED',
        'StateChangeReason': {'Code': 'STEP_FAILED', 'Message': f'connect failed {FLAG_ONLY}'},
        'FailureDetails': {'Reason': 'error', 'Message': f'row rejected {FLAG_ONLY}'},
        'Timeline': {'StartDateTime': '2026-01-01T00:00:00Z'},
    },
}


def assert_step_is_filtered(step):
    """Assert a step record has the filtered fields removed and the rest kept."""
    assert FLAG_ONLY not in json.dumps(step)
    assert 'Args' not in step['Config']
    assert 'Properties' not in step['Config']
    assert 'Message' not in step['Status']['StateChangeReason']
    assert 'FailureDetails' not in step['Status']
    # Identity and state survive, which is the point of filtering rather than refusing
    assert step['Id'] == 's-456'
    assert step['Name'] == 'nightly-etl'
    assert step['Status']['State'] == 'FAILED'
    assert step['Status']['StateChangeReason']['Code'] == 'STEP_FAILED'
    assert step['Config']['Jar'] == 's3://bucket/etl.jar'


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

            assert result.is_error is False

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

            assert result.is_error is False

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

            assert result.is_error is False

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
            assert result.is_error is True
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
            assert result.is_error is False

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
            assert result.is_error is True
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
            assert result.is_error is False

    @pytest.mark.asyncio
    async def test_glue_get_statement_omits_output_without_flag(self, mock_ctx, mock_glue_client):
        """Test that Glue get-statement omits Code and Output.Data without the flag."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            mcp = MagicMock()
            handler = GlueInteractiveSessionsHandler(
                mcp, allow_write=True, allow_sensitive_data_access=False
            )

            mock_glue_client.get_statement.return_value = {
                'Statement': {
                    'Id': 1,
                    'State': 'COMPLETED',
                    'Progress': 1.0,
                    'Code': f"spark.read.jdbc(url='...{FLAG_ONLY}')",
                    'Output': {
                        'Data': {'TextPlain': FLAG_ONLY},
                        'Status': 'ok',
                        'ExecutionCount': 3,
                        'Traceback': [f'line with {FLAG_ONLY}'],
                    },
                }
            }

            result = await handler.manage_aws_glue_statements(
                mock_ctx, operation='get-statement', session_id='test-session', statement_id=1
            )

            # The call now succeeds; the sensitive fields are omitted from the record
            assert result.is_error is False
            statement = json.loads(result.content[1].text)['statement']
            assert 'Code' not in statement
            assert 'Data' not in statement['Output']
            assert 'Traceback' not in statement['Output']
            # Operational metadata is retained so callers can still see execution state
            assert statement['Id'] == 1
            assert statement['State'] == 'COMPLETED'
            assert statement['Output']['Status'] == 'ok'
            # And the caller is told fields were withheld rather than left to guess
            assert '--allow-sensitive-data-access' in result.content[0].text

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
            assert result.is_error is False

    # ==================== MEDIUM: Job Output Protection Tests ====================

    @pytest.mark.asyncio
    async def test_glue_get_job_run_omits_arguments_without_flag(self, mock_ctx, mock_glue_client):
        """Test that Glue get-job-run omits Arguments and ErrorMessage without the flag."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            mcp = MagicMock()
            handler = GlueEtlJobsHandler(mcp, allow_write=False, allow_sensitive_data_access=False)

            mock_glue_client.get_job_run.return_value = {
                'JobRun': {
                    'Id': 'jr_123',
                    'JobName': 'test-job',
                    'JobRunState': 'FAILED',
                    'Arguments': {'--conf': FLAG_ONLY, '--target': 'sales'},
                    'ErrorMessage': f'connect failed for user svc_etl {FLAG_ONLY}',
                    'StateDetail': f'detail {FLAG_ONLY}',
                }
            }

            result = await handler.manage_aws_glue_jobs(
                mock_ctx, operation='get-job-run', job_name='test-job', job_run_id='jr_123'
            )

            assert result.is_error is False
            job_run = json.loads(result.content[1].text)['job_run_details']
            assert 'Arguments' not in job_run
            assert 'ErrorMessage' not in job_run
            assert 'StateDetail' not in job_run
            assert FLAG_ONLY not in json.dumps(job_run)
            # Run identity and state are retained
            assert job_run['Id'] == 'jr_123'
            assert job_run['JobRunState'] == 'FAILED'
            assert '--allow-sensitive-data-access' in result.content[0].text

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
            assert result.is_error is False

    @pytest.mark.asyncio
    async def test_emr_serverless_get_job_run_omits_driver_without_flag(
        self, mock_ctx, mock_emr_serverless_client
    ):
        """Test that EMR Serverless get-job-run omits jobDriver and stateDetails without the flag."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_emr_serverless_client,
        ):
            mcp = MagicMock()
            handler = EMRServerlessJobRunHandler(
                mcp, allow_write=False, allow_sensitive_data_access=False
            )

            mock_emr_serverless_client.get_job_run.return_value = {
                'jobRun': {
                    'jobRunId': 'jr-456',
                    'applicationId': 'app-123',
                    'state': 'FAILED',
                    'stateDetails': f'driver failed: {FLAG_ONLY}',
                    'jobDriver': {
                        'sparkSubmit': {
                            'sparkSubmitParameters': f'--conf spark.key={FLAG_ONLY}',
                        }
                    },
                    'configurationOverrides': {'applicationConfiguration': [FLAG_ONLY]},
                    'tags': {'owner': FLAG_ONLY},
                }
            }

            result = await handler.manage_aws_emr_serverless_job_runs(
                mock_ctx,
                operation='get-job-run',
                application_id='app-123',
                job_run_id='jr-456',
            )

            assert result.is_error is False
            job_run = json.loads(result.content[1].text)['job_run']
            assert 'stateDetails' not in job_run
            assert 'jobDriver' not in job_run
            assert 'configurationOverrides' not in job_run
            assert 'tags' not in job_run
            assert FLAG_ONLY not in json.dumps(job_run)
            assert job_run['jobRunId'] == 'jr-456'
            assert job_run['state'] == 'FAILED'
            assert '--allow-sensitive-data-access' in result.content[0].text

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
            assert result.is_error is False

    @pytest.mark.asyncio
    async def test_emr_describe_step_omits_args_without_flag(self, mock_ctx, mock_emr_client):
        """Test that EMR EC2 describe-step omits step args and failure text without the flag."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_emr_client,
        ):
            mcp = MagicMock()
            handler = EMREc2StepsHandler(mcp, allow_write=False, allow_sensitive_data_access=False)

            mock_emr_client.describe_step.return_value = {'Step': STEP_WITH_FILTERED_FIELDS}

            result = await handler.manage_aws_emr_ec2_steps(
                mock_ctx, operation='describe-step', cluster_id='j-123', step_id='s-456'
            )

            assert result.is_error is False
            step = json.loads(result.content[1].text)['step']
            assert_step_is_filtered(step)
            assert '--allow-sensitive-data-access' in result.content[0].text

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
            assert result.is_error is False

    # ==================== Read-Only Operations Should Still Work ====================

    @pytest.mark.asyncio
    async def test_athena_list_query_executions_not_blocked(self, mock_ctx, mock_athena_client):
        """Test that list-query-executions is NOT blocked.

        Unlike the list operations gated below, Athena ListQueryExecutions returns only
        QueryExecutionIds - no query text, results, or error detail - so it is genuinely
        metadata-only and stays available without the flag.
        """
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
            assert result.is_error is False

    # ==================== List Operations Must Match Their Singular Sibling ====================
    #
    # Regression coverage for the case where the flag was enforced on a singular read
    # operation but not on the list operation returning the same records. Glue
    # ListStatements returns full Statement records (including Output.Data), EMR ListSteps
    # returns StepSummary records (Config.Args, Status.StateChangeReason) and Glue
    # GetJobRuns returns full JobRun records (Arguments, ErrorMessage), so filtering only
    # the singular operation would leave the control bypassable by asking for the plural.

    @pytest.mark.asyncio
    async def test_glue_list_statements_omits_output_without_flag(
        self, mock_ctx, mock_glue_client
    ):
        """Test that list-statements omits Code and Output.Data without the flag."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            mcp = MagicMock()
            handler = GlueInteractiveSessionsHandler(
                mcp, allow_write=True, allow_sensitive_data_access=False
            )

            mock_glue_client.list_statements.return_value = {
                'Statements': [
                    {
                        'Id': 1,
                        'State': 'COMPLETED',
                        'Code': FLAG_ONLY,
                        'Output': {'Data': {'TextPlain': FLAG_ONLY}, 'Status': 'ok'},
                    }
                ],
            }

            result = await handler.manage_aws_glue_statements(
                mock_ctx, operation='list-statements', session_id='test-session'
            )

            # Must match get-statement: same records, so the same fields are withheld
            assert result.is_error is False
            statements = json.loads(result.content[1].text)['statements']
            assert FLAG_ONLY not in json.dumps(statements)
            assert 'Code' not in statements[0]
            assert 'Data' not in statements[0]['Output']
            assert statements[0]['State'] == 'COMPLETED'
            assert '--allow-sensitive-data-access' in result.content[0].text

    @pytest.mark.asyncio
    async def test_glue_list_statements_allowed_with_flag(self, mock_ctx, mock_glue_client):
        """Test that list-statements succeeds when allow_sensitive_data_access=True."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            mcp = MagicMock()
            handler = GlueInteractiveSessionsHandler(
                mcp, allow_write=True, allow_sensitive_data_access=True
            )

            mock_glue_client.list_statements.return_value = {
                'Statements': [
                    {
                        'Id': 1,
                        'State': 'COMPLETED',
                        'Output': {'Data': {'TextPlain': 'result data'}},
                    }
                ],
            }

            result = await handler.manage_aws_glue_statements(
                mock_ctx, operation='list-statements', session_id='test-session'
            )

            # Verify operation was allowed
            mock_glue_client.list_statements.assert_called_once()
            assert result.is_error is False

    @pytest.mark.asyncio
    async def test_glue_get_job_runs_omits_arguments_without_flag(
        self, mock_ctx, mock_glue_client
    ):
        """Test that Glue get-job-runs omits Arguments and ErrorMessage without the flag."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            mcp = MagicMock()
            handler = GlueEtlJobsHandler(mcp, allow_write=False, allow_sensitive_data_access=False)

            mock_glue_client.get_job_runs.return_value = {
                'JobRuns': [
                    {
                        'Id': 'jr_123',
                        'JobName': 'test-job',
                        'JobRunState': 'FAILED',
                        'Arguments': {'--conf': FLAG_ONLY},
                        'ErrorMessage': f'failed {FLAG_ONLY}',
                    }
                ],
            }

            result = await handler.manage_aws_glue_jobs(
                mock_ctx, operation='get-job-runs', job_name='test-job'
            )

            # Must match get-job-run: same JobRun records, so the same fields are withheld
            assert result.is_error is False
            job_runs = json.loads(result.content[1].text)['job_runs']
            assert FLAG_ONLY not in json.dumps(job_runs)
            assert 'Arguments' not in job_runs[0]
            assert 'ErrorMessage' not in job_runs[0]
            assert job_runs[0]['Id'] == 'jr_123'
            assert job_runs[0]['JobRunState'] == 'FAILED'
            assert '--allow-sensitive-data-access' in result.content[0].text

    @pytest.mark.asyncio
    async def test_glue_get_job_runs_allowed_with_flag(self, mock_ctx, mock_glue_client):
        """Test that Glue get-job-runs succeeds when allow_sensitive_data_access=True."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            mcp = MagicMock()
            handler = GlueEtlJobsHandler(mcp, allow_write=False, allow_sensitive_data_access=True)

            mock_glue_client.get_job_runs.return_value = {
                'JobRuns': [
                    {
                        'Id': 'jr_123',
                        'JobName': 'test-job',
                        'JobRunState': 'FAILED',
                        'Arguments': {'--conf': 'spark.sql.shuffle.partitions=10'},
                        'ErrorMessage': 'job failed',
                    }
                ]
            }

            result = await handler.manage_aws_glue_jobs(
                mock_ctx, operation='get-job-runs', job_name='test-job'
            )

            # Verify operation was allowed
            mock_glue_client.get_job_runs.assert_called_once()
            assert result.is_error is False

    @pytest.mark.asyncio
    async def test_emr_list_steps_omits_args_without_flag(self, mock_ctx, mock_emr_client):
        """Test that EMR EC2 list-steps omits step args and failure text without the flag."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_emr_client,
        ):
            mcp = MagicMock()
            handler = EMREc2StepsHandler(mcp, allow_write=False, allow_sensitive_data_access=False)

            mock_emr_client.list_steps.return_value = {
                'Steps': [STEP_WITH_FILTERED_FIELDS],
                'Marker': None,
            }

            result = await handler.manage_aws_emr_ec2_steps(
                mock_ctx, operation='list-steps', cluster_id='j-123'
            )

            # Must match describe-step: same fixture in, same fields withheld
            assert result.is_error is False
            steps = json.loads(result.content[1].text)['steps']
            assert_step_is_filtered(steps[0])
            assert '--allow-sensitive-data-access' in result.content[0].text

    @pytest.mark.asyncio
    async def test_emr_list_steps_allowed_with_flag(self, mock_ctx, mock_emr_client):
        """Test that EMR EC2 list-steps succeeds when allow_sensitive_data_access=True."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_emr_client,
        ):
            mcp = MagicMock()
            handler = EMREc2StepsHandler(mcp, allow_write=False, allow_sensitive_data_access=True)

            mock_emr_client.list_steps.return_value = {
                'Steps': [
                    {
                        'Id': 's-456',
                        'Name': 'Test Step',
                        'Status': {'State': 'COMPLETED'},
                        'Config': {'Args': ['spark-submit', 'script.py']},
                    }
                ]
            }

            result = await handler.manage_aws_emr_ec2_steps(
                mock_ctx, operation='list-steps', cluster_id='j-123'
            )

            # Verify operation was allowed
            mock_emr_client.list_steps.assert_called_once()
            assert result.is_error is False

    @pytest.mark.asyncio
    async def test_emr_serverless_list_job_runs_omits_state_details_without_flag(
        self, mock_ctx, mock_emr_serverless_client
    ):
        """Test that EMR Serverless list-job-runs omits stateDetails without the flag."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_emr_serverless_client,
        ):
            mcp = MagicMock()
            handler = EMRServerlessJobRunHandler(
                mcp, allow_write=False, allow_sensitive_data_access=False
            )

            mock_emr_serverless_client.list_job_runs.return_value = {
                'jobRuns': [
                    {
                        'id': 'jr-456',
                        'applicationId': 'app-123',
                        'state': 'FAILED',
                        'stateDetails': f'driver failed: {FLAG_ONLY}',
                    }
                ],
                'nextToken': None,
            }

            result = await handler.manage_aws_emr_serverless_job_runs(
                mock_ctx, operation='list-job-runs', application_id='app-123'
            )

            # Must match get-job-run: stateDetails is the field it is filtered on
            assert result.is_error is False
            job_runs = json.loads(result.content[1].text)['job_runs']
            assert FLAG_ONLY not in json.dumps(job_runs)
            assert 'stateDetails' not in job_runs[0]
            assert job_runs[0]['id'] == 'jr-456'
            assert job_runs[0]['state'] == 'FAILED'
            assert '--allow-sensitive-data-access' in result.content[0].text

    @pytest.mark.asyncio
    async def test_emr_serverless_list_job_runs_allowed_with_flag(
        self, mock_ctx, mock_emr_serverless_client
    ):
        """Test that EMR Serverless list-job-runs succeeds when allow_sensitive_data_access=True."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_emr_serverless_client,
        ):
            mcp = MagicMock()
            handler = EMRServerlessJobRunHandler(
                mcp, allow_write=False, allow_sensitive_data_access=True
            )

            mock_emr_serverless_client.list_job_runs.return_value = {
                'jobRuns': [
                    {
                        'id': 'jr-456',
                        'applicationId': 'app-123',
                        'state': 'FAILED',
                        'stateDetails': 'job failed',
                    }
                ]
            }

            result = await handler.manage_aws_emr_serverless_job_runs(
                mock_ctx, operation='list-job-runs', application_id='app-123'
            )

            # Verify operation was allowed
            mock_emr_serverless_client.list_job_runs.assert_called_once()
            assert result.is_error is False
