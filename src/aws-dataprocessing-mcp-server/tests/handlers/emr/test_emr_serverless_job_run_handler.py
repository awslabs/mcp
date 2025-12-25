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

"""Comprehensive tests for EMRServerlessJobRunHandler."""

import json
import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_serverless_job_run_handler import (
    EMRServerlessJobRunHandler,
)
from botocore.exceptions import ClientError
from mcp.types import CallToolResult, TextContent
from unittest.mock import MagicMock, patch


class TestEMRServerlessJobRunHandler:
    """Comprehensive test suite for EMR Serverless Job Run Handler."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock MCP server."""
        return MagicMock()

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock context."""
        ctx = MagicMock()
        ctx.session = {'request_id': 'test-request-123'}
        return ctx

    @pytest.fixture
    def mock_emr_serverless_client(self):
        """Create a mock EMR Serverless client."""
        return MagicMock()

    @pytest.fixture
    def handler_read_only(self, mock_mcp):
        """Create handler with read-only access."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client'
        ) as mock_create_client:
            mock_create_client.return_value = MagicMock()
            handler = EMRServerlessJobRunHandler(mock_mcp, allow_write=False)
            return handler

    @pytest.fixture
    def handler_with_write(self, mock_mcp):
        """Create handler with write access."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client'
        ) as mock_create_client:
            mock_create_client.return_value = MagicMock()
            handler = EMRServerlessJobRunHandler(mock_mcp, allow_write=True)
            return handler

    def extract_data_from_result(self, result: CallToolResult) -> dict:
        """Helper function to extract structured data from MCP result."""
        if (
            len(result.content) >= 2
            and isinstance(result.content[1], TextContent)
            and result.content[1].text
        ):
            return json.loads(result.content[1].text)
        return {}

    # Start Job Run Tests
    @pytest.mark.asyncio
    async def test_start_job_run_success(self, handler_with_write, mock_ctx):
        """Test successful job run start."""
        # Mock AWS response
        mock_response = {
            'jobRunId': 'job-12345abcdefghijkl',
            'arn': 'arn:aws:emr-serverless:us-east-1:123456789012:job-run/app-12345abcdef/job-12345abcdefghijkl',
        }
        handler_with_write.emr_serverless_client.start_job_run.return_value = mock_response

        # Mock tag preparation
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags'
        ) as mock_prepare_tags:
            mock_prepare_tags.return_value = {
                'MCP-Managed': 'true',
                'MCP-CreatedBy': 'aws-dataprocessing-mcp-server',
            }

            result = await handler_with_write.manage_aws_emr_serverless_job_runs(
                ctx=mock_ctx,
                operation='start-job-run',
                application_id='app-12345abcdef',
                execution_role_arn='arn:aws:iam::123456789012:role/EMRServerlessRole',
                job_driver={
                    'sparkSubmit': {
                        'entryPoint': 's3://my-bucket/spark-job.py',
                        'entryPointArguments': ['--input', 's3://input-bucket/data/'],
                        'sparkSubmitParameters': '--conf spark.executor.memory=2g',
                    }
                },
                name='test-spark-job-run',
                client_token='job-run-token-123',
                configuration_overrides={
                    'applicationConfiguration': [
                        {
                            'classification': 'spark-defaults',
                            'properties': {
                                'spark.sql.adaptive.enabled': 'true',
                                'spark.sql.adaptive.coalescePartitions.enabled': 'true',
                            },
                        }
                    ],
                    'monitoringConfiguration': {
                        's3MonitoringConfiguration': {
                            'logUri': 's3://my-bucket/logs/',
                            'encryptionKeyArn': 'arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012',
                        },
                        'managedPersistenceMonitoringConfiguration': {'enabled': True},
                        'cloudWatchLoggingConfiguration': {
                            'enabled': True,
                            'logGroupName': '/aws/emr-serverless/job-runs',
                            'logStreamNamePrefix': 'spark-job',
                        },
                    },
                },
                tags={'Environment': 'test', 'Project': 'mcp', 'JobType': 'etl'},
            )

        # Verify result
        assert not result.isError
        assert len(result.content) == 2
        assert (
            'Successfully started job run job-12345abcdefghijkl on application app-12345abcdef with MCP management tags'
            in result.content[0].text
        )

        data = self.extract_data_from_result(result)
        assert data['job_run_id'] == 'job-12345abcdefghijkl'
        assert data['application_id'] == 'app-12345abcdef'
        assert (
            data['arn']
            == 'arn:aws:emr-serverless:us-east-1:123456789012:job-run/app-12345abcdef/job-12345abcdefghijkl'
        )
        assert data['operation'] == 'start-job-run'

        # Verify AWS API was called with correct parameters
        call_args = handler_with_write.emr_serverless_client.start_job_run.call_args
        assert call_args[1]['applicationId'] == 'app-12345abcdef'
        assert (
            call_args[1]['executionRoleArn'] == 'arn:aws:iam::123456789012:role/EMRServerlessRole'
        )
        assert call_args[1]['name'] == 'test-spark-job-run'
        assert call_args[1]['clientToken'] == 'job-run-token-123'
        assert 'MCP-Managed' in call_args[1]['tags']
        assert 'Environment' in call_args[1]['tags']

    @pytest.mark.asyncio
    async def test_start_job_run_missing_required_params(self, handler_with_write, mock_ctx):
        """Test start job run with missing required parameters."""
        result = await handler_with_write.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='start-job-run',
            # Missing application_id, execution_role_arn, and job_driver
        )

        assert result.isError
        assert (
            'application_id, execution_role_arn, and job_driver are required'
            in result.content[0].text
        )

    @pytest.mark.asyncio
    async def test_start_job_run_write_access_denied(self, handler_read_only, mock_ctx):
        """Test start job run without write access."""
        result = await handler_read_only.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='start-job-run',
            application_id='app-12345abcdef',
            execution_role_arn='arn:aws:iam::123456789012:role/EMRServerlessRole',
            job_driver={'sparkSubmit': {'entryPoint': 's3://bucket/job.py'}},
        )

        assert result.isError
        assert 'not allowed without write access' in result.content[0].text

    @pytest.mark.asyncio
    async def test_start_job_run_aws_error(self, handler_with_write, mock_ctx):
        """Test start job run with AWS service error."""
        # Mock AWS error
        handler_with_write.emr_serverless_client.start_job_run.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Application not found'}},
            'StartJobRun',
        )

        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags'
        ) as mock_prepare_tags:
            mock_prepare_tags.return_value = {'MCP-Managed': 'true'}

            result = await handler_with_write.manage_aws_emr_serverless_job_runs(
                ctx=mock_ctx,
                operation='start-job-run',
                application_id='app-nonexistent',
                execution_role_arn='arn:aws:iam::123456789012:role/EMRServerlessRole',
                job_driver={'sparkSubmit': {'entryPoint': 's3://bucket/job.py'}},
            )

        assert result.isError
        assert 'Application not found' in result.content[0].text

    # Get Job Run Tests
    @pytest.mark.asyncio
    async def test_get_job_run_success(self, handler_read_only, mock_ctx):
        """Test successful job run retrieval."""
        mock_response = {
            'jobRun': {
                'jobRunId': 'job-12345abcdefghijkl',
                'applicationId': 'app-12345abcdef',
                'name': 'test-spark-job-run',
                'arn': 'arn:aws:emr-serverless:us-east-1:123456789012:job-run/app-12345abcdef/job-12345abcdefghijkl',
                'executionRoleArn': 'arn:aws:iam::123456789012:role/EMRServerlessRole',
                'state': 'RUNNING',
                'stateDetails': '',
                'releaseLabel': 'emr-7.0.0',
                'type': 'Spark',
                'createdAt': '2023-11-15T10:30:00Z',
                'updatedAt': '2023-11-15T10:35:00Z',
                'executionTimeoutMinutes': 60,
                'jobDriver': {
                    'sparkSubmit': {
                        'entryPoint': 's3://my-bucket/spark-job.py',
                        'entryPointArguments': ['--input', 's3://input-bucket/data/'],
                    }
                },
                'configurationOverrides': {
                    'applicationConfiguration': [
                        {
                            'classification': 'spark-defaults',
                            'properties': {'spark.sql.adaptive.enabled': 'true'},
                        }
                    ]
                },
                'totalResourceUtilization': {
                    'vCPUHour': 2.5,
                    'memoryGBHour': 10.0,
                    'storageGBHour': 50.0,
                },
                'networkConfiguration': {
                    'subnetIds': ['subnet-12345'],
                    'securityGroupIds': ['sg-security1'],
                },
                'totalExecutionDurationSeconds': 300,
                'tags': {'Environment': 'test', 'MCP-Managed': 'true'},
            }
        }
        handler_read_only.emr_serverless_client.get_job_run.return_value = mock_response

        result = await handler_read_only.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='get-job-run',
            application_id='app-12345abcdef',
            job_run_id='job-12345abcdefghijkl',
        )

        assert not result.isError
        assert (
            'Successfully retrieved job run job-12345abcdefghijkl details'
            in result.content[0].text
        )

        data = self.extract_data_from_result(result)
        assert data['job_run']['jobRunId'] == 'job-12345abcdefghijkl'
        assert data['job_run']['applicationId'] == 'app-12345abcdef'
        assert data['job_run']['name'] == 'test-spark-job-run'
        assert data['job_run']['state'] == 'RUNNING'
        assert data['operation'] == 'get-job-run'

    @pytest.mark.asyncio
    async def test_get_job_run_missing_params(self, handler_read_only, mock_ctx):
        """Test get job run without required parameters."""
        result = await handler_read_only.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='get-job-run',
            # Missing application_id and job_run_id
        )

        assert result.isError
        assert 'application_id and job_run_id are required' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_job_run_not_found(self, handler_read_only, mock_ctx):
        """Test get job run when job run doesn't exist."""
        handler_read_only.emr_serverless_client.get_job_run.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Job run not found'}},
            'GetJobRun',
        )

        result = await handler_read_only.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='get-job-run',
            application_id='app-12345abcdef',
            job_run_id='job-nonexistent',
        )

        assert result.isError
        assert 'Job run not found' in result.content[0].text

    # Cancel Job Run Tests
    @pytest.mark.asyncio
    async def test_cancel_job_run_success(self, handler_with_write, mock_ctx):
        """Test successful job run cancellation."""
        # Mock AWS API call - the cancel operation doesn't return anything meaningful
        handler_with_write.emr_serverless_client.cancel_job_run.return_value = {}

        result = await handler_with_write.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='cancel-job-run',
            application_id='app-12345abcdef',
            job_run_id='job-12345abcdefghijkl',
        )

        assert not result.isError
        assert (
            'Successfully cancelled job run job-12345abcdefghijkl on application app-12345abcdef'
            in result.content[0].text
        )

        data = self.extract_data_from_result(result)
        assert data['job_run_id'] == 'job-12345abcdefghijkl'
        assert data['application_id'] == 'app-12345abcdef'
        assert data['operation'] == 'cancel-job-run'

    @pytest.mark.asyncio
    async def test_cancel_job_run_validation_error(self, handler_with_write, mock_ctx):
        """Test cancel job run with validation error."""
        handler_with_write.emr_serverless_client.cancel_job_run.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'ValidationException',
                    'Message': 'Job run is already in terminal state',
                }
            },
            'CancelJobRun',
        )

        result = await handler_with_write.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='cancel-job-run',
            application_id='app-12345abcdef',
            job_run_id='job-12345abcdefghijkl',
        )

        assert result.isError
        assert 'Job run is already in terminal state' in result.content[0].text

    # List Job Runs Tests
    @pytest.mark.asyncio
    async def test_list_job_runs_success(self, handler_read_only, mock_ctx):
        """Test successful job runs listing."""
        mock_response = {
            'jobRuns': [
                {
                    'id': 'job-12345abcdefghijkl',
                    'name': 'spark-job-1',
                    'applicationId': 'app-12345abcdef',
                    'arn': 'arn:aws:emr-serverless:us-east-1:123456789012:job-run/app-12345abcdef/job-12345abcdefghijkl',
                    'executionRoleArn': 'arn:aws:iam::123456789012:role/EMRServerlessRole',
                    'state': 'RUNNING',
                    'type': 'Spark',
                    'releaseLabel': 'emr-7.0.0',
                    'createdAt': '2023-11-15T10:30:00Z',
                    'updatedAt': '2023-11-15T10:35:00Z',
                },
                {
                    'id': 'job-67890mnopqrstuvw',
                    'name': 'hive-job-1',
                    'applicationId': 'app-67890ghijkl',
                    'arn': 'arn:aws:emr-serverless:us-east-1:123456789012:job-run/app-67890ghijkl/job-67890mnopqrstuvw',
                    'executionRoleArn': 'arn:aws:iam::123456789012:role/EMRServerlessRole',
                    'state': 'SUCCESS',
                    'type': 'Hive',
                    'releaseLabel': 'emr-6.15.0',
                    'createdAt': '2023-11-14T09:20:00Z',
                    'updatedAt': '2023-11-14T10:45:00Z',
                },
            ],
            'nextToken': 'next-job-runs-token',
        }
        handler_read_only.emr_serverless_client.list_job_runs.return_value = mock_response

        result = await handler_read_only.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='list-job-runs',
            application_id='app-12345abcdef',
            max_results=50,
            states=['RUNNING', 'SUCCESS'],
        )

        assert not result.isError
        assert 'Successfully listed EMR Serverless job runs' in result.content[0].text

        data = self.extract_data_from_result(result)
        assert len(data['job_runs']) == 2
        assert data['count'] == 2
        assert data['next_token'] == 'next-job-runs-token'
        assert data['operation'] == 'list-job-runs'
        assert data['job_runs'][0]['name'] == 'spark-job-1'
        assert data['job_runs'][1]['name'] == 'hive-job-1'

    @pytest.mark.asyncio
    async def test_list_job_runs_with_pagination(self, handler_read_only, mock_ctx):
        """Test list job runs with pagination."""
        mock_response = {
            'jobRuns': [
                {
                    'id': 'job-next-page',
                    'name': 'next-page-job',
                    'applicationId': 'app-12345abcdef',
                    'state': 'PENDING',
                    'type': 'Spark',
                },
            ],
        }
        handler_read_only.emr_serverless_client.list_job_runs.return_value = mock_response

        result = await handler_read_only.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='list-job-runs',
            application_id='app-12345abcdef',
            next_token='previous-job-runs-token',
            max_results=10,
        )

        assert not result.isError
        data = self.extract_data_from_result(result)
        assert len(data['job_runs']) == 1
        assert data['job_runs'][0]['name'] == 'next-page-job'

        # Verify pagination parameters were passed correctly
        call_args = handler_read_only.emr_serverless_client.list_job_runs.call_args
        assert call_args[1]['nextToken'] == 'previous-job-runs-token'
        assert call_args[1]['maxResults'] == 10

    @pytest.mark.asyncio
    async def test_list_job_runs_missing_application_id(self, handler_read_only, mock_ctx):
        """Test list job runs without application ID."""
        result = await handler_read_only.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='list-job-runs',
        )

        assert result.isError
        assert 'application_id is required' in result.content[0].text

    # Get Dashboard for Job Run Tests
    @pytest.mark.asyncio
    async def test_get_dashboard_for_job_run_success(self, handler_read_only, mock_ctx):
        """Test successful dashboard URL retrieval."""
        # Mock AWS response
        mock_response = {
            'url': 'https://console.aws.amazon.com/emr/serverless/applications/app-12345abcdef/job-runs/job-12345abcdefghijkl'
        }
        handler_read_only.emr_serverless_client.get_dashboard_for_job_run.return_value = (
            mock_response
        )

        result = await handler_read_only.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='get-dashboard-for-job-run',
            application_id='app-12345abcdef',
            job_run_id='job-12345abcdefghijkl',
        )

        assert not result.isError
        assert (
            'Successfully retrieved dashboard URL for job run job-12345abcdefghijkl'
            in result.content[0].text
        )

        data = self.extract_data_from_result(result)
        expected_url = 'https://console.aws.amazon.com/emr/serverless/applications/app-12345abcdef/job-runs/job-12345abcdefghijkl'
        assert data['url'] == expected_url
        assert data['operation'] == 'get-dashboard-for-job-run'

    @pytest.mark.asyncio
    async def test_get_dashboard_for_job_run_missing_params(self, handler_read_only, mock_ctx):
        """Test get dashboard without required parameters."""
        result = await handler_read_only.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='get-dashboard-for-job-run',
        )

        assert result.isError
        assert 'application_id and job_run_id are required' in result.content[0].text

    # Comprehensive Job Driver Types Tests
    @pytest.mark.asyncio
    async def test_start_job_run_spark_sql_driver(self, handler_with_write, mock_ctx):
        """Test start job run with Spark SQL job driver."""
        mock_response = {
            'jobRunId': 'job-sql123456789abc',
            'arn': 'arn:aws:emr-serverless:us-east-1:123456789012:job-run/app-12345abcdef/job-sql123456789abc',
        }
        handler_with_write.emr_serverless_client.start_job_run.return_value = mock_response

        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags'
        ) as mock_prepare_tags:
            mock_prepare_tags.return_value = {'MCP-Managed': 'true'}

            result = await handler_with_write.manage_aws_emr_serverless_job_runs(
                ctx=mock_ctx,
                operation='start-job-run',
                application_id='app-12345abcdef',
                execution_role_arn='arn:aws:iam::123456789012:role/EMRServerlessRole',
                job_driver={
                    'sparkSql': {
                        'entryPoint': 's3://my-bucket/query.sql',
                        'sparkSqlParameters': '--conf spark.sql.warehouse.dir=s3://warehouse/',
                    }
                },
                name='spark-sql-job',
            )

        assert not result.isError
        data = self.extract_data_from_result(result)
        assert data['job_run_id'] == 'job-sql123456789abc'

        # Verify job driver was passed correctly
        call_args = handler_with_write.emr_serverless_client.start_job_run.call_args
        assert 'sparkSql' in call_args[1]['jobDriver']
        assert call_args[1]['jobDriver']['sparkSql']['entryPoint'] == 's3://my-bucket/query.sql'

    @pytest.mark.asyncio
    async def test_start_job_run_hive_driver(self, handler_with_write, mock_ctx):
        """Test start job run with Hive job driver."""
        mock_response = {
            'jobRunId': 'job-hive123456789abc',
            'arn': 'arn:aws:emr-serverless:us-east-1:123456789012:job-run/app-12345abcdef/job-hive123456789abc',
        }
        handler_with_write.emr_serverless_client.start_job_run.return_value = mock_response

        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags'
        ) as mock_prepare_tags:
            mock_prepare_tags.return_value = {'MCP-Managed': 'true'}

            result = await handler_with_write.manage_aws_emr_serverless_job_runs(
                ctx=mock_ctx,
                operation='start-job-run',
                application_id='app-12345abcdef',
                execution_role_arn='arn:aws:iam::123456789012:role/EMRServerlessRole',
                job_driver={
                    'hive': {
                        'query': 's3://my-bucket/hive-query.hql',
                        'initQueryFile': 's3://my-bucket/init.hql',
                        'parameters': '--hiveconf hive.exec.dynamic.partition=true',
                    }
                },
                name='hive-job',
            )

        assert not result.isError
        data = self.extract_data_from_result(result)
        assert data['job_run_id'] == 'job-hive123456789abc'

        # Verify job driver was passed correctly
        call_args = handler_with_write.emr_serverless_client.start_job_run.call_args
        assert 'hive' in call_args[1]['jobDriver']
        assert call_args[1]['jobDriver']['hive']['query'] == 's3://my-bucket/hive-query.hql'

    # Comprehensive Configuration Tests
    @pytest.mark.asyncio
    async def test_start_job_run_comprehensive_config(self, handler_with_write, mock_ctx):
        """Test start job run with comprehensive configuration."""
        mock_response = {
            'jobRunId': 'job-comprehensive123',
            'arn': 'arn:aws:emr-serverless:us-east-1:123456789012:job-run/app-12345abcdef/job-comprehensive123',
        }
        handler_with_write.emr_serverless_client.start_job_run.return_value = mock_response

        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags'
        ) as mock_prepare_tags:
            mock_prepare_tags.return_value = {'MCP-Managed': 'true'}

            result = await handler_with_write.manage_aws_emr_serverless_job_runs(
                ctx=mock_ctx,
                operation='start-job-run',
                application_id='app-12345abcdef',
                execution_role_arn='arn:aws:iam::123456789012:role/EMRServerlessRole',
                job_driver={
                    'sparkSubmit': {
                        'entryPoint': 's3://my-bucket/comprehensive-job.py',
                        'entryPointArguments': [
                            '--input',
                            's3://input/',
                            '--output',
                            's3://output/',
                        ],
                        'sparkSubmitParameters': '--conf spark.sql.adaptive.enabled=true --conf spark.executor.memory=4g',
                    }
                },
                name='comprehensive-job-run',
                client_token='comprehensive-token-456',
                execution_timeout_minutes=120,
                configuration_overrides={
                    'applicationConfiguration': [
                        {
                            'classification': 'spark-defaults',
                            'properties': {
                                'spark.sql.adaptive.enabled': 'true',
                                'spark.sql.adaptive.coalescePartitions.enabled': 'true',
                                'spark.sql.adaptive.skewJoin.enabled': 'true',
                                'spark.serializer': 'org.apache.spark.serializer.KryoSerializer',
                            },
                        },
                        {
                            'classification': 'spark-hive-site',
                            'properties': {
                                'javax.jdo.option.ConnectionURL': 'jdbc:mysql://hostname/hive_metastore',
                            },
                        },
                    ],
                    'monitoringConfiguration': {
                        's3MonitoringConfiguration': {
                            'logUri': 's3://comprehensive-bucket/logs/',
                            'encryptionKeyArn': 'arn:aws:kms:us-east-1:123456789012:key/comprehensive-key',
                        },
                        'managedPersistenceMonitoringConfiguration': {
                            'enabled': True,
                            'encryptionKeyArn': 'arn:aws:kms:us-east-1:123456789012:key/persistence-key',
                        },
                        'cloudWatchLoggingConfiguration': {
                            'enabled': True,
                            'logGroupName': '/aws/emr-serverless/comprehensive',
                            'logStreamNamePrefix': 'comprehensive-job',
                            'encryptionKeyArn': 'arn:aws:kms:us-east-1:123456789012:key/cloudwatch-key',
                        },
                        'prometheusMonitoringConfiguration': {
                            'remoteWriteUrl': 'https://prometheus.example.com:9090/api/v1/remote_write',
                        },
                    },
                },
                mode='STREAMING',
                retry_policy={
                    'maxAttempts': 3,
                    'maxFailedAttemptsPerHour': 2,
                },
                tags={
                    'Environment': 'production',
                    'Team': 'data-engineering',
                    'CostCenter': '12345',
                    'Application': 'comprehensive-job',
                },
            )

        assert not result.isError
        data = self.extract_data_from_result(result)
        assert data['job_run_id'] == 'job-comprehensive123'

        # Verify comprehensive parameters were passed correctly
        call_args = handler_with_write.emr_serverless_client.start_job_run.call_args
        assert call_args[1]['applicationId'] == 'app-12345abcdef'
        assert (
            call_args[1]['executionRoleArn'] == 'arn:aws:iam::123456789012:role/EMRServerlessRole'
        )
        assert call_args[1]['name'] == 'comprehensive-job-run'
        assert call_args[1]['executionTimeoutMinutes'] == 120
        assert call_args[1]['mode'] == 'STREAMING'
        assert 'retryPolicy' in call_args[1]
        assert call_args[1]['retryPolicy']['maxAttempts'] == 3
        assert 'configurationOverrides' in call_args[1]
        assert 'applicationConfiguration' in call_args[1]['configurationOverrides']
        assert 'monitoringConfiguration' in call_args[1]['configurationOverrides']

    # Edge Cases and Error Handling Tests
    @pytest.mark.asyncio
    async def test_invalid_operation(self, handler_read_only, mock_ctx):
        """Test invalid operation."""
        result = await handler_read_only.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='invalid-operation',
        )

        assert result.isError
        assert 'Invalid operation' in result.content[0].text

    @pytest.mark.asyncio
    async def test_concurrent_modification_error(self, handler_with_write, mock_ctx):
        """Test handling of concurrent modification errors."""
        handler_with_write.emr_serverless_client.cancel_job_run.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'ConflictException',
                    'Message': 'Job run is being cancelled by another process',
                }
            },
            'CancelJobRun',
        )

        result = await handler_with_write.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='cancel-job-run',
            application_id='app-12345abcdef',
            job_run_id='job-12345abcdefghijkl',
        )

        assert result.isError
        assert 'Job run is being cancelled by another process' in result.content[0].text

    @pytest.mark.asyncio
    async def test_throttling_error(self, handler_read_only, mock_ctx):
        """Test handling of AWS throttling errors."""
        handler_read_only.emr_serverless_client.list_job_runs.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}, 'ListJobRuns'
        )

        result = await handler_read_only.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='list-job-runs',
            application_id='app-12345abcdef',
        )

        assert result.isError
        assert 'Rate exceeded' in result.content[0].text

    @pytest.mark.asyncio
    async def test_generic_exception_handling(self, handler_read_only, mock_ctx):
        """Test handling of generic exceptions."""
        handler_read_only.emr_serverless_client.get_job_run.side_effect = Exception(
            'Unexpected error occurred'
        )

        result = await handler_read_only.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='get-job-run',
            application_id='app-12345abcdef',
            job_run_id='job-12345abcdefghijkl',
        )

        assert result.isError
        assert 'Error in manage_aws_emr_serverless_job_runs' in result.content[0].text
        assert 'Unexpected error occurred' in result.content[0].text

    # Resource Utilization Tests
    @pytest.mark.asyncio
    async def test_get_job_run_with_resource_utilization(self, handler_read_only, mock_ctx):
        """Test get job run with detailed resource utilization."""
        mock_response = {
            'jobRun': {
                'jobRunId': 'job-resource-utilization',
                'applicationId': 'app-12345abcdef',
                'name': 'resource-heavy-job',
                'state': 'SUCCESS',
                'totalResourceUtilization': {
                    'vCPUHour': 45.75,
                    'memoryGBHour': 182.5,
                    'storageGBHour': 500.0,
                },
                'billedResourceUtilization': {
                    'vCPUHour': 48.0,
                    'memoryGBHour': 192.0,
                    'storageGBHour': 500.0,
                },
                'totalExecutionDurationSeconds': 2700,  # 45 minutes
                'queuedDurationMilliseconds': 5000,  # 5 seconds
                'attempt': 1,
                'attemptCreatedAt': '2023-11-15T10:30:00Z',
                'attemptUpdatedAt': '2023-11-15T11:15:00Z',
            }
        }
        handler_read_only.emr_serverless_client.get_job_run.return_value = mock_response

        result = await handler_read_only.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='get-job-run',
            application_id='app-12345abcdef',
            job_run_id='job-resource-utilization',
        )

        assert not result.isError
        data = self.extract_data_from_result(result)
        assert data['job_run']['totalResourceUtilization']['vCPUHour'] == 45.75
        assert data['job_run']['billedResourceUtilization']['vCPUHour'] == 48.0
        assert data['job_run']['totalExecutionDurationSeconds'] == 2700

    # Date Range Filtering Tests
    @pytest.mark.asyncio
    async def test_list_job_runs_with_date_range(self, handler_read_only, mock_ctx):
        """Test list job runs with date range filtering."""
        from datetime import datetime, timezone

        mock_response = {
            'jobRuns': [
                {
                    'id': 'job-recent-12345',
                    'name': 'recent-job',
                    'applicationId': 'app-12345abcdef',
                    'state': 'SUCCESS',
                    'createdAt': '2023-11-15T10:30:00Z',
                    'updatedAt': '2023-11-15T11:15:00Z',
                },
            ],
        }
        handler_read_only.emr_serverless_client.list_job_runs.return_value = mock_response

        created_after = datetime(2023, 11, 15, 0, 0, 0, tzinfo=timezone.utc)
        created_before = datetime(2023, 11, 16, 0, 0, 0, tzinfo=timezone.utc)

        result = await handler_read_only.manage_aws_emr_serverless_job_runs(
            ctx=mock_ctx,
            operation='list-job-runs',
            application_id='app-12345abcdef',
            created_at_after=created_after,
            created_at_before=created_before,
        )

        assert not result.isError
        data = self.extract_data_from_result(result)
        assert len(data['job_runs']) == 1
        assert data['job_runs'][0]['name'] == 'recent-job'

        # Verify date parameters were passed correctly
        call_args = handler_read_only.emr_serverless_client.list_job_runs.call_args
        assert call_args[1]['createdAtAfter'] == created_after
        assert call_args[1]['createdAtBefore'] == created_before
