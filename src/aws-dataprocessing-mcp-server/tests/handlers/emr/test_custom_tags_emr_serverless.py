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

"""Tests for the CUSTOM_TAGS environment variable functionality in EMR Serverless handlers."""

import os
import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_serverless_application_handler import (
    EMRServerlessApplicationHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_serverless_job_run_handler import (
    EMRServerlessJobRunHandler,
)
from awslabs.aws_dataprocessing_mcp_server.utils.consts import (
    CUSTOM_TAGS_ENV_VAR,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestCustomTagsEmrServerless:
    """Tests for the CUSTOM_TAGS environment variable functionality in EMR Serverless handlers."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock MCP server."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock Context."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def application_handler_with_write_access(self, mock_mcp):
        """Create an EMRServerlessApplicationHandler instance with write access enabled."""
        # Mock the AWS helper's create_boto3_client method to avoid boto3 client creation
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=MagicMock(),
        ):
            handler = EMRServerlessApplicationHandler(mock_mcp, allow_write=True)
            return handler

    @pytest.fixture
    def job_run_handler_with_write_access(self, mock_mcp):
        """Create an EMRServerlessJobRunHandler instance with write access enabled."""
        # Mock the AWS helper's create_boto3_client method to avoid boto3 client creation
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=MagicMock(),
        ):
            handler = EMRServerlessJobRunHandler(mock_mcp, allow_write=True)
            return handler

    @pytest.mark.asyncio
    async def test_create_application_with_custom_tags_enabled(
        self, application_handler_with_write_access, mock_ctx
    ):
        """Test that create application operation respects CUSTOM_TAGS when enabled."""
        # Mock the manage_aws_emr_serverless_applications method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.application_id = 'app-12345ABCDEF'
        mock_response.name = 'Test Application'
        mock_response.operation = 'create-application'
        application_handler_with_write_access.manage_aws_emr_serverless_applications = AsyncMock(
            return_value=mock_response
        )

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = (
                await application_handler_with_write_access.manage_aws_emr_serverless_applications(
                    mock_ctx,
                    operation='create-application',
                    name='Test Application',
                    release_label='emr-7.9.0',
                    type='Spark',
                    initial_capacity={
                        'DRIVER': {'workerCount': 1},
                        'EXECUTOR': {'workerCount': 2},
                    },
                    maximum_capacity={'DRIVER': {'cpu': '2 vCPU', 'memory': '4 GB'}},
                    auto_start_configuration={'enabled': True},
                    auto_stop_configuration={'enabled': True, 'idleTimeoutMinutes': 15},
                    network_configuration={'subnetIds': ['subnet-12345']},
                    tags={'Environment': 'Test', 'Project': 'UnitTest'},
                )
            )

            # Verify that the method was called with the correct parameters
            application_handler_with_write_access.manage_aws_emr_serverless_applications.assert_called_once()

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.application_id == 'app-12345ABCDEF'
            assert result.name == 'Test Application'

    @pytest.mark.asyncio
    async def test_update_application_with_custom_tags_enabled(
        self, application_handler_with_write_access, mock_ctx
    ):
        """Test that update application operation respects CUSTOM_TAGS when enabled."""
        # Mock the manage_aws_emr_serverless_applications method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.application_id = 'app-12345ABCDEF'
        mock_response.operation = 'update-application'
        application_handler_with_write_access.manage_aws_emr_serverless_applications = AsyncMock(
            return_value=mock_response
        )

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = (
                await application_handler_with_write_access.manage_aws_emr_serverless_applications(
                    mock_ctx,
                    operation='update-application',
                    application_id='app-12345ABCDEF',
                    name='Updated Application',
                    initial_capacity={'DRIVER': {'workerCount': 2}},
                    maximum_capacity={'DRIVER': {'cpu': '4 vCPU', 'memory': '8 GB'}},
                )
            )

            # Verify that the method was called with the correct parameters
            application_handler_with_write_access.manage_aws_emr_serverless_applications.assert_called_once()

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.application_id == 'app-12345ABCDEF'

    @pytest.mark.asyncio
    async def test_delete_application_with_custom_tags_enabled(
        self, application_handler_with_write_access, mock_ctx
    ):
        """Test that delete application operation respects CUSTOM_TAGS when enabled."""
        # Mock the manage_aws_emr_serverless_applications method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.application_id = 'app-12345ABCDEF'
        mock_response.operation = 'delete-application'
        application_handler_with_write_access.manage_aws_emr_serverless_applications = AsyncMock(
            return_value=mock_response
        )

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = (
                await application_handler_with_write_access.manage_aws_emr_serverless_applications(
                    mock_ctx,
                    operation='delete-application',
                    application_id='app-12345ABCDEF',
                )
            )

            # Verify that the method was called with the correct parameters
            application_handler_with_write_access.manage_aws_emr_serverless_applications.assert_called_once()

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.application_id == 'app-12345ABCDEF'

    @pytest.mark.asyncio
    async def test_get_application_with_custom_tags_enabled(
        self, application_handler_with_write_access, mock_ctx
    ):
        """Test that get application operation respects CUSTOM_TAGS when enabled."""
        # Mock the manage_aws_emr_serverless_applications method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.application = {
            'applicationId': 'app-12345ABCDEF',
            'name': 'Test Application',
            'state': 'CREATED',
        }
        mock_response.operation = 'get-application'
        application_handler_with_write_access.manage_aws_emr_serverless_applications = AsyncMock(
            return_value=mock_response
        )

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = (
                await application_handler_with_write_access.manage_aws_emr_serverless_applications(
                    mock_ctx,
                    operation='get-application',
                    application_id='app-12345ABCDEF',
                )
            )

            # Verify that the method was called with the correct parameters
            application_handler_with_write_access.manage_aws_emr_serverless_applications.assert_called_once()

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.application['applicationId'] == 'app-12345ABCDEF'
            assert result.application['name'] == 'Test Application'

    @pytest.mark.asyncio
    async def test_list_applications_with_custom_tags_enabled(
        self, application_handler_with_write_access, mock_ctx
    ):
        """Test that list applications operation respects CUSTOM_TAGS when enabled."""
        # Mock the manage_aws_emr_serverless_applications method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.applications = [
            {'applicationId': 'app-12345ABCDEF', 'name': 'App 1', 'state': 'CREATED'},
            {'applicationId': 'app-67890GHIJKL', 'name': 'App 2', 'state': 'STARTED'},
        ]
        mock_response.count = 2
        mock_response.operation = 'list-applications'
        application_handler_with_write_access.manage_aws_emr_serverless_applications = AsyncMock(
            return_value=mock_response
        )

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = (
                await application_handler_with_write_access.manage_aws_emr_serverless_applications(
                    mock_ctx,
                    operation='list-applications',
                    states=['CREATED', 'STARTED'],
                )
            )

            # Verify that the method was called with the correct parameters
            application_handler_with_write_access.manage_aws_emr_serverless_applications.assert_called_once()

            # Verify that the result is the expected response
            assert result == mock_response
            assert len(result.applications) == 2
            assert result.count == 2

    @pytest.mark.asyncio
    async def test_start_application_with_custom_tags_enabled(
        self, application_handler_with_write_access, mock_ctx
    ):
        """Test that start application operation respects CUSTOM_TAGS when enabled."""
        # Mock the manage_aws_emr_serverless_applications method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.application_id = 'app-12345ABCDEF'
        mock_response.operation = 'start-application'
        application_handler_with_write_access.manage_aws_emr_serverless_applications = AsyncMock(
            return_value=mock_response
        )

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = (
                await application_handler_with_write_access.manage_aws_emr_serverless_applications(
                    mock_ctx,
                    operation='start-application',
                    application_id='app-12345ABCDEF',
                )
            )

            # Verify that the method was called with the correct parameters
            application_handler_with_write_access.manage_aws_emr_serverless_applications.assert_called_once()

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.application_id == 'app-12345ABCDEF'

    @pytest.mark.asyncio
    async def test_stop_application_with_custom_tags_enabled(
        self, application_handler_with_write_access, mock_ctx
    ):
        """Test that stop application operation respects CUSTOM_TAGS when enabled."""
        # Mock the manage_aws_emr_serverless_applications method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.application_id = 'app-12345ABCDEF'
        mock_response.operation = 'stop-application'
        application_handler_with_write_access.manage_aws_emr_serverless_applications = AsyncMock(
            return_value=mock_response
        )

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = (
                await application_handler_with_write_access.manage_aws_emr_serverless_applications(
                    mock_ctx,
                    operation='stop-application',
                    application_id='app-12345ABCDEF',
                )
            )

            # Verify that the method was called with the correct parameters
            application_handler_with_write_access.manage_aws_emr_serverless_applications.assert_called_once()

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.application_id == 'app-12345ABCDEF'

    @pytest.mark.asyncio
    async def test_start_job_run_with_custom_tags_enabled(
        self, job_run_handler_with_write_access, mock_ctx
    ):
        """Test that start job run operation respects CUSTOM_TAGS when enabled."""
        # Mock the manage_aws_emr_serverless_job_runs method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.job_run_id = 'job-12345ABCDEF'
        mock_response.application_id = 'app-12345ABCDEF'
        mock_response.operation = 'start-job-run'
        job_run_handler_with_write_access.manage_aws_emr_serverless_job_runs = AsyncMock(
            return_value=mock_response
        )

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await job_run_handler_with_write_access.manage_aws_emr_serverless_job_runs(
                mock_ctx,
                operation='start-job-run',
                application_id='app-12345ABCDEF',
                execution_role_arn='arn:aws:iam::123456789012:role/EMRServerlessRole',
                job_driver={'sparkSubmit': {'entryPoint': 's3://bucket/script.py'}},
                name='Test Job Run',
                configuration_overrides={
                    'applicationConfiguration': [
                        {'classification': 'spark-defaults', 'properties': {'key': 'value'}}
                    ],
                    'monitoringConfiguration': {
                        's3MonitoringConfiguration': {'logUri': 's3://bucket/logs/'}
                    },
                },
                tags={'Environment': 'Test', 'Project': 'UnitTest'},
            )

            # Verify that the method was called with the correct parameters
            job_run_handler_with_write_access.manage_aws_emr_serverless_job_runs.assert_called_once()

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.job_run_id == 'job-12345ABCDEF'
            assert result.application_id == 'app-12345ABCDEF'

    @pytest.mark.asyncio
    async def test_get_job_run_with_custom_tags_enabled(
        self, job_run_handler_with_write_access, mock_ctx
    ):
        """Test that get job run operation respects CUSTOM_TAGS when enabled."""
        # Mock the manage_aws_emr_serverless_job_runs method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.job_run = {
            'jobRunId': 'job-12345ABCDEF',
            'applicationId': 'app-12345ABCDEF',
            'state': 'RUNNING',
        }
        mock_response.operation = 'get-job-run'
        job_run_handler_with_write_access.manage_aws_emr_serverless_job_runs = AsyncMock(
            return_value=mock_response
        )

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await job_run_handler_with_write_access.manage_aws_emr_serverless_job_runs(
                mock_ctx,
                operation='get-job-run',
                application_id='app-12345ABCDEF',
                job_run_id='job-12345ABCDEF',
            )

            # Verify that the method was called with the correct parameters
            job_run_handler_with_write_access.manage_aws_emr_serverless_job_runs.assert_called_once()

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.job_run['jobRunId'] == 'job-12345ABCDEF'
            assert result.job_run['applicationId'] == 'app-12345ABCDEF'

    @pytest.mark.asyncio
    async def test_cancel_job_run_with_custom_tags_enabled(
        self, job_run_handler_with_write_access, mock_ctx
    ):
        """Test that cancel job run operation respects CUSTOM_TAGS when enabled."""
        # Mock the manage_aws_emr_serverless_job_runs method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.job_run_id = 'job-12345ABCDEF'
        mock_response.application_id = 'app-12345ABCDEF'
        mock_response.operation = 'cancel-job-run'
        job_run_handler_with_write_access.manage_aws_emr_serverless_job_runs = AsyncMock(
            return_value=mock_response
        )

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await job_run_handler_with_write_access.manage_aws_emr_serverless_job_runs(
                mock_ctx,
                operation='cancel-job-run',
                application_id='app-12345ABCDEF',
                job_run_id='job-12345ABCDEF',
            )

            # Verify that the method was called with the correct parameters
            job_run_handler_with_write_access.manage_aws_emr_serverless_job_runs.assert_called_once()

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.job_run_id == 'job-12345ABCDEF'
            assert result.application_id == 'app-12345ABCDEF'

    @pytest.mark.asyncio
    async def test_list_job_runs_with_custom_tags_enabled(
        self, job_run_handler_with_write_access, mock_ctx
    ):
        """Test that list job runs operation respects CUSTOM_TAGS when enabled."""
        # Mock the manage_aws_emr_serverless_job_runs method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.job_runs = [
            {'jobRunId': 'job-12345ABCDEF', 'state': 'RUNNING'},
            {'jobRunId': 'job-67890GHIJKL', 'state': 'SUCCESS'},
        ]
        mock_response.count = 2
        mock_response.operation = 'list-job-runs'
        job_run_handler_with_write_access.manage_aws_emr_serverless_job_runs = AsyncMock(
            return_value=mock_response
        )

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await job_run_handler_with_write_access.manage_aws_emr_serverless_job_runs(
                mock_ctx,
                operation='list-job-runs',
                application_id='app-12345ABCDEF',
                states=['RUNNING', 'SUCCESS'],
            )

            # Verify that the method was called with the correct parameters
            job_run_handler_with_write_access.manage_aws_emr_serverless_job_runs.assert_called_once()

            # Verify that the result is the expected response
            assert result == mock_response
            assert len(result.job_runs) == 2
            assert result.count == 2

    @pytest.mark.asyncio
    async def test_get_dashboard_for_job_run_with_custom_tags_enabled(
        self, job_run_handler_with_write_access, mock_ctx
    ):
        """Test that get dashboard for job run operation respects CUSTOM_TAGS when enabled."""
        # Mock the manage_aws_emr_serverless_job_runs method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.url = (
            'https://console.aws.amazon.com/emr/serverless/dashboard/job-12345ABCDEF'
        )
        mock_response.operation = 'get-dashboard-for-job-run'
        job_run_handler_with_write_access.manage_aws_emr_serverless_job_runs = AsyncMock(
            return_value=mock_response
        )

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await job_run_handler_with_write_access.manage_aws_emr_serverless_job_runs(
                mock_ctx,
                operation='get-dashboard-for-job-run',
                application_id='app-12345ABCDEF',
                job_run_id='job-12345ABCDEF',
            )

            # Verify that the method was called with the correct parameters
            job_run_handler_with_write_access.manage_aws_emr_serverless_job_runs.assert_called_once()

            # Verify that the result is the expected response
            assert result == mock_response
            assert (
                result.url
                == 'https://console.aws.amazon.com/emr/serverless/dashboard/job-12345ABCDEF'
            )
