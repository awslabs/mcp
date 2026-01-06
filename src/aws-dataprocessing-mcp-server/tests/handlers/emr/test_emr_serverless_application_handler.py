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

"""Comprehensive tests for EMRServerlessApplicationHandler."""

import json
import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_serverless_application_handler import (
    EMRServerlessApplicationHandler,
)
from botocore.exceptions import ClientError
from mcp.types import CallToolResult
from unittest.mock import MagicMock, patch


class TestEMRServerlessApplicationHandler:
    """Comprehensive test suite for EMR Serverless Application Handler."""

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
            handler = EMRServerlessApplicationHandler(mock_mcp, allow_write=False)
            return handler

    @pytest.fixture
    def handler_with_write(self, mock_mcp):
        """Create handler with write access."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client'
        ) as mock_create_client:
            mock_create_client.return_value = MagicMock()
            handler = EMRServerlessApplicationHandler(mock_mcp, allow_write=True)
            return handler

    def extract_data_from_result(self, result: CallToolResult) -> dict:
        """Helper function to extract structured data from MCP result."""
        if (
            len(result.content) >= 2
            and hasattr(result.content[1], 'text')
            and result.content[1].text
        ):
            return json.loads(result.content[1].text)
        return {}

    # Create Application Tests
    @pytest.mark.asyncio
    async def test_create_application_success(self, handler_with_write, mock_ctx):
        """Test successful application creation."""
        # Mock AWS response
        mock_response = {
            'applicationId': 'app-12345abcdef',
            'name': 'test-spark-app',
            'arn': 'arn:aws:emr-serverless:us-east-1:123456789012:application/app-12345abcdef',
        }
        handler_with_write.emr_serverless_client.create_application.return_value = mock_response

        # Mock tag preparation
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags'
        ) as mock_prepare_tags:
            mock_prepare_tags.return_value = {
                'MCP-Managed': 'true',
                'MCP-CreatedBy': 'aws-dataprocessing-mcp-server',
            }

            result = await handler_with_write.manage_aws_emr_serverless_applications(
                ctx=mock_ctx,
                operation='create-application',
                name='test-spark-app',
                release_label='emr-7.0.0',
                type='Spark',
                client_token='test-token-123',
                initial_capacity={
                    'DRIVER': {
                        'workerCount': 1,
                        'workerConfiguration': {'cpu': '2 vCPU', 'memory': '4 GB'},
                    },
                    'EXECUTOR': {
                        'workerCount': 4,
                        'workerConfiguration': {'cpu': '2 vCPU', 'memory': '4 GB'},
                    },
                },
                maximum_capacity={'DRIVER': {'cpu': '2 vCPU', 'memory': '4 GB'}},
                auto_start_configuration={'enabled': True},
                auto_stop_configuration={'enabled': True, 'idleTimeoutMinutes': 15},
                tags={'Environment': 'test', 'Project': 'mcp'},
            )

        # Verify result
        assert not result.isError
        assert len(result.content) == 2
        assert 'Successfully created EMR Serverless application' in result.content[0].text

        data = self.extract_data_from_result(result)
        assert data['application_id'] == 'app-12345abcdef'
        assert data['name'] == 'test-spark-app'
        assert (
            data['arn']
            == 'arn:aws:emr-serverless:us-east-1:123456789012:application/app-12345abcdef'
        )
        assert data['operation'] == 'create-application'

        # Verify AWS API was called with correct parameters
        call_args = handler_with_write.emr_serverless_client.create_application.call_args
        assert call_args[1]['name'] == 'test-spark-app'
        assert call_args[1]['releaseLabel'] == 'emr-7.0.0'
        assert call_args[1]['type'] == 'Spark'
        assert call_args[1]['clientToken'] == 'test-token-123'
        assert 'MCP-Managed' in call_args[1]['tags']
        assert 'Environment' in call_args[1]['tags']

    @pytest.mark.asyncio
    async def test_create_application_missing_required_params(self, handler_with_write, mock_ctx):
        """Test create application with missing required parameters."""
        result = await handler_with_write.manage_aws_emr_serverless_applications(
            ctx=mock_ctx,
            operation='create-application',
            # Missing name, release_label, and type
        )

        assert result.isError
        assert 'name, release_label, and type are required' in result.content[0].text

    @pytest.mark.asyncio
    async def test_create_application_write_access_denied(self, handler_read_only, mock_ctx):
        """Test create application without write access."""
        result = await handler_read_only.manage_aws_emr_serverless_applications(
            ctx=mock_ctx,
            operation='create-application',
            name='test-app',
            release_label='emr-7.0.0',
            type='Spark',
        )

        assert result.isError
        assert 'not allowed without write access' in result.content[0].text

    @pytest.mark.asyncio
    async def test_create_application_aws_error(self, handler_with_write, mock_ctx):
        """Test create application with AWS service error."""
        # Mock AWS error
        handler_with_write.emr_serverless_client.create_application.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid release label'}},
            'CreateApplication',
        )

        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags'
        ) as mock_prepare_tags:
            mock_prepare_tags.return_value = {'MCP-Managed': 'true'}

            result = await handler_with_write.manage_aws_emr_serverless_applications(
                ctx=mock_ctx,
                operation='create-application',
                name='test-app',
                release_label='invalid-label',
                type='Spark',
            )

        assert result.isError
        assert 'Invalid release label' in result.content[0].text

    # Get Application Tests
    @pytest.mark.asyncio
    async def test_get_application_success(self, handler_read_only, mock_ctx):
        """Test successful application retrieval."""
        mock_response = {
            'application': {
                'applicationId': 'app-12345abcdef',
                'name': 'test-spark-app',
                'arn': 'arn:aws:emr-serverless:us-east-1:123456789012:application/app-12345abcdef',
                'releaseLabel': 'emr-7.0.0',
                'type': 'Spark',
                'state': 'CREATED',
                'stateDetails': '',
                'initialCapacity': {
                    'DRIVER': {
                        'workerCount': 1,
                        'workerConfiguration': {'cpu': '2 vCPU', 'memory': '4 GB'},
                    },
                },
                'maximumCapacity': {'DRIVER': {'cpu': '2 vCPU', 'memory': '4 GB'}},
                'createdAt': '2023-11-15T10:30:00Z',
                'updatedAt': '2023-11-15T10:30:00Z',
                'tags': {'Environment': 'test', 'MCP-Managed': 'true'},
            }
        }
        handler_read_only.emr_serverless_client.get_application.return_value = mock_response

        result = await handler_read_only.manage_aws_emr_serverless_applications(
            ctx=mock_ctx,
            operation='get-application',
            application_id='app-12345abcdef',
        )

        assert not result.isError
        assert 'Successfully retrieved EMR Serverless application' in result.content[0].text

        data = self.extract_data_from_result(result)
        assert data['application']['applicationId'] == 'app-12345abcdef'
        assert data['application']['name'] == 'test-spark-app'
        assert data['application']['state'] == 'CREATED'
        assert data['operation'] == 'get-application'

    @pytest.mark.asyncio
    async def test_get_application_missing_id(self, handler_read_only, mock_ctx):
        """Test get application without application ID."""
        result = await handler_read_only.manage_aws_emr_serverless_applications(
            ctx=mock_ctx,
            operation='get-application',
        )

        assert result.isError
        assert 'application_id is required' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_application_not_found(self, handler_read_only, mock_ctx):
        """Test get application when application doesn't exist."""
        handler_read_only.emr_serverless_client.get_application.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Application not found'}},
            'GetApplication',
        )

        result = await handler_read_only.manage_aws_emr_serverless_applications(
            ctx=mock_ctx,
            operation='get-application',
            application_id='app-nonexistent',
        )

        assert result.isError
        assert 'Application not found' in result.content[0].text

    # Update Application Tests
    @pytest.mark.asyncio
    async def test_update_application_success(self, handler_with_write, mock_ctx):
        """Test successful application update."""
        # Mock MCP verification
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.verify_emr_serverless_application_managed_by_mcp'
        ) as mock_verify:
            mock_verify.return_value = {'is_valid': True}

            mock_response = {
                'application': {
                    'applicationId': 'app-12345abcdef',
                    'name': 'updated-spark-app',
                    'state': 'CREATED',
                }
            }
            handler_with_write.emr_serverless_client.update_application.return_value = (
                mock_response
            )

            result = await handler_with_write.manage_aws_emr_serverless_applications(
                ctx=mock_ctx,
                operation='update-application',
                application_id='app-12345abcdef',
                name='updated-spark-app',
                client_token='update-token-123',
                initial_capacity={
                    'EXECUTOR': {
                        'workerCount': 8,
                        'workerConfiguration': {'cpu': '4 vCPU', 'memory': '8 GB'},
                    },
                },
            )

        assert not result.isError
        assert 'Successfully updated EMR Serverless application' in result.content[0].text

        data = self.extract_data_from_result(result)
        assert data['application']['applicationId'] == 'app-12345abcdef'
        assert data['application']['name'] == 'updated-spark-app'
        assert data['operation'] == 'update-application'

    @pytest.mark.asyncio
    async def test_update_application_not_managed_by_mcp(self, handler_with_write, mock_ctx):
        """Test update application not managed by MCP."""
        # Mock MCP verification failure
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.verify_emr_serverless_application_managed_by_mcp'
        ) as mock_verify:
            mock_verify.return_value = {
                'is_valid': False,
                'error_message': 'Application is not managed by MCP or MCP tags are missing',
            }

            result = await handler_with_write.manage_aws_emr_serverless_applications(
                ctx=mock_ctx,
                operation='update-application',
                application_id='app-12345abcdef',
                name='updated-app',
            )

        assert result.isError
        assert 'Cannot update application' in result.content[0].text
        assert 'not managed by MCP' in result.content[0].text

    # Delete Application Tests
    @pytest.mark.asyncio
    async def test_delete_application_success(self, handler_with_write, mock_ctx):
        """Test successful application deletion."""
        # Mock MCP verification
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.verify_emr_serverless_application_managed_by_mcp'
        ) as mock_verify:
            mock_verify.return_value = {'is_valid': True}

            # Mock delete response (returns nothing)
            handler_with_write.emr_serverless_client.delete_application.return_value = None

            result = await handler_with_write.manage_aws_emr_serverless_applications(
                ctx=mock_ctx,
                operation='delete-application',
                application_id='app-12345abcdef',
            )

        assert not result.isError
        assert 'Successfully deleted EMR Serverless application' in result.content[0].text

        data = self.extract_data_from_result(result)
        assert data['application_id'] == 'app-12345abcdef'
        assert data['operation'] == 'delete-application'

    @pytest.mark.asyncio
    async def test_delete_application_validation_error(self, handler_with_write, mock_ctx):
        """Test delete application with validation error."""
        # Mock MCP verification
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.verify_emr_serverless_application_managed_by_mcp'
        ) as mock_verify:
            mock_verify.return_value = {'is_valid': True}

            handler_with_write.emr_serverless_client.delete_application.side_effect = ClientError(
                {
                    'Error': {
                        'Code': 'ValidationException',
                        'Message': 'Application must be in STOPPED state',
                    }
                },
                'DeleteApplication',
            )

            result = await handler_with_write.manage_aws_emr_serverless_applications(
                ctx=mock_ctx,
                operation='delete-application',
                application_id='app-12345abcdef',
            )

        assert result.isError
        assert 'Application must be in STOPPED state' in result.content[0].text

    # List Applications Tests
    @pytest.mark.asyncio
    async def test_list_applications_success(self, handler_read_only, mock_ctx):
        """Test successful applications listing."""
        mock_response = {
            'applications': [
                {
                    'id': 'app-12345abcdef',
                    'name': 'spark-app-1',
                    'arn': 'arn:aws:emr-serverless:us-east-1:123456789012:application/app-12345abcdef',
                    'releaseLabel': 'emr-7.0.0',
                    'type': 'Spark',
                    'state': 'CREATED',
                    'createdAt': '2023-11-15T10:30:00Z',
                    'updatedAt': '2023-11-15T10:30:00Z',
                },
                {
                    'id': 'app-67890ghijkl',
                    'name': 'hive-app-1',
                    'arn': 'arn:aws:emr-serverless:us-east-1:123456789012:application/app-67890ghijkl',
                    'releaseLabel': 'emr-6.15.0',
                    'type': 'Hive',
                    'state': 'STARTED',
                    'createdAt': '2023-11-14T09:20:00Z',
                    'updatedAt': '2023-11-15T08:15:00Z',
                },
            ],
            'nextToken': 'next-page-token',
        }
        handler_read_only.emr_serverless_client.list_applications.return_value = mock_response

        result = await handler_read_only.manage_aws_emr_serverless_applications(
            ctx=mock_ctx,
            operation='list-applications',
            max_results=50,
            states=['CREATED', 'STARTED'],
        )

        assert not result.isError
        assert 'Successfully listed EMR Serverless applications' in result.content[0].text

        data = self.extract_data_from_result(result)
        assert len(data['applications']) == 2
        assert data['count'] == 2
        assert data['next_token'] == 'next-page-token'
        assert data['operation'] == 'list-applications'
        assert data['applications'][0]['name'] == 'spark-app-1'
        assert data['applications'][1]['name'] == 'hive-app-1'

    @pytest.mark.asyncio
    async def test_list_applications_with_pagination(self, handler_read_only, mock_ctx):
        """Test list applications with pagination."""
        mock_response = {
            'applications': [
                {
                    'id': 'app-next-page',
                    'name': 'next-page-app',
                    'releaseLabel': 'emr-7.0.0',
                    'type': 'Spark',
                    'state': 'CREATED',
                },
            ],
        }
        handler_read_only.emr_serverless_client.list_applications.return_value = mock_response

        result = await handler_read_only.manage_aws_emr_serverless_applications(
            ctx=mock_ctx,
            operation='list-applications',
            next_token='previous-page-token',
            max_results=10,
        )

        assert not result.isError
        data = self.extract_data_from_result(result)
        assert len(data['applications']) == 1
        assert data['applications'][0]['name'] == 'next-page-app'

        # Verify pagination parameters were passed correctly
        call_args = handler_read_only.emr_serverless_client.list_applications.call_args
        assert call_args[1]['nextToken'] == 'previous-page-token'
        assert call_args[1]['maxResults'] == 10

    # Start/Stop Application Tests
    @pytest.mark.asyncio
    async def test_start_application_success(self, handler_with_write, mock_ctx):
        """Test successful application start."""
        # Mock MCP verification
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.verify_emr_serverless_application_managed_by_mcp'
        ) as mock_verify:
            mock_verify.return_value = {'is_valid': True}

            handler_with_write.emr_serverless_client.start_application.return_value = None

            result = await handler_with_write.manage_aws_emr_serverless_applications(
                ctx=mock_ctx,
                operation='start-application',
                application_id='app-12345abcdef',
            )

        assert not result.isError
        assert 'Successfully started EMR Serverless application' in result.content[0].text

        data = self.extract_data_from_result(result)
        assert data['application_id'] == 'app-12345abcdef'
        assert data['operation'] == 'start-application'

    @pytest.mark.asyncio
    async def test_stop_application_success(self, handler_with_write, mock_ctx):
        """Test successful application stop."""
        # Mock MCP verification
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.verify_emr_serverless_application_managed_by_mcp'
        ) as mock_verify:
            mock_verify.return_value = {'is_valid': True}

            handler_with_write.emr_serverless_client.stop_application.return_value = None

            result = await handler_with_write.manage_aws_emr_serverless_applications(
                ctx=mock_ctx,
                operation='stop-application',
                application_id='app-12345abcdef',
            )

        assert not result.isError
        assert 'Successfully stopped EMR Serverless application' in result.content[0].text

        data = self.extract_data_from_result(result)
        assert data['application_id'] == 'app-12345abcdef'
        assert data['operation'] == 'stop-application'

    # Edge Cases and Error Handling Tests
    @pytest.mark.asyncio
    async def test_invalid_operation(self, handler_read_only, mock_ctx):
        """Test invalid operation."""
        result = await handler_read_only.manage_aws_emr_serverless_applications(
            ctx=mock_ctx,
            operation='invalid-operation',
        )

        assert result.isError
        assert 'Invalid operation' in result.content[0].text

    @pytest.mark.asyncio
    async def test_create_application_with_comprehensive_config(
        self, handler_with_write, mock_ctx
    ):
        """Test create application with comprehensive configuration."""
        mock_response = {
            'applicationId': 'app-comprehensive',
            'name': 'comprehensive-app',
            'arn': 'arn:aws:emr-serverless:us-east-1:123456789012:application/app-comprehensive',
        }
        handler_with_write.emr_serverless_client.create_application.return_value = mock_response

        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags'
        ) as mock_prepare_tags:
            mock_prepare_tags.return_value = {'MCP-Managed': 'true'}

            result = await handler_with_write.manage_aws_emr_serverless_applications(
                ctx=mock_ctx,
                operation='create-application',
                name='comprehensive-app',
                release_label='emr-7.0.0',
                type='Spark',
                client_token='comprehensive-token',
                initial_capacity={
                    'DRIVER': {
                        'workerCount': 1,
                        'workerConfiguration': {
                            'cpu': '4 vCPU',
                            'memory': '8 GB',
                            'disk': '20 GB',
                        },
                    },
                    'EXECUTOR': {
                        'workerCount': 10,
                        'workerConfiguration': {
                            'cpu': '4 vCPU',
                            'memory': '8 GB',
                            'disk': '20 GB',
                        },
                    },
                },
                maximum_capacity={
                    'DRIVER': {'cpu': '4 vCPU', 'memory': '8 GB'},
                    'EXECUTOR': {'cpu': '40 vCPU', 'memory': '80 GB'},
                },
                auto_start_configuration={'enabled': True},
                auto_stop_configuration={'enabled': True, 'idleTimeoutMinutes': 30},
                network_configuration={
                    'subnetIds': ['subnet-12345', 'subnet-67890'],
                    'securityGroupIds': ['sg-security1', 'sg-security2'],
                },
                architecture='X86_64',
                image_configuration={
                    'imageUri': '123456789012.dkr.ecr.us-east-1.amazonaws.com/custom-spark:latest',
                    'resolvedImageDigest': 'sha256:abcdef123456',
                },
                worker_type_specifications={
                    'DRIVER': {
                        'imageConfiguration': {
                            'imageUri': '123456789012.dkr.ecr.us-east-1.amazonaws.com/driver:latest'
                        }
                    },
                    'EXECUTOR': {
                        'imageConfiguration': {
                            'imageUri': '123456789012.dkr.ecr.us-east-1.amazonaws.com/executor:latest'
                        }
                    },
                },
                runtime_configuration=[
                    {
                        'classification': 'spark-defaults',
                        'properties': {
                            'spark.sql.adaptive.enabled': 'true',
                            'spark.sql.adaptive.coalescePartitions.enabled': 'true',
                        },
                    }
                ],
                monitoring_configuration={
                    's3MonitoringConfiguration': {'logUri': 's3://my-bucket/logs/'},
                    'managedPersistenceMonitoringConfiguration': {'enabled': True},
                    'cloudWatchLoggingConfiguration': {
                        'enabled': True,
                        'logGroupName': '/aws/emr-serverless/applications',
                    },
                },
                interactive_configuration={
                    'studioEnabled': True,
                    'livyEndpointEnabled': True,
                },
                scheduler_configuration={
                    'maxConcurrentRuns': 5,
                    'queueTimeoutMinutes': 60,
                },
                identity_center_configuration={
                    'instanceArn': 'arn:aws:sso:::instance/ssoins-1234567890abcdef',
                    'permissionSetArn': 'arn:aws:sso:::permissionSet/ssoins-1234567890abcdef/ps-abcdef1234567890',
                },
                tags={
                    'Environment': 'production',
                    'Team': 'data-engineering',
                    'CostCenter': '12345',
                },
            )

        assert not result.isError
        data = self.extract_data_from_result(result)
        assert data['application_id'] == 'app-comprehensive'
        assert data['name'] == 'comprehensive-app'

        # Verify all parameters were passed correctly
        call_args = handler_with_write.emr_serverless_client.create_application.call_args
        assert call_args[1]['name'] == 'comprehensive-app'
        assert call_args[1]['releaseLabel'] == 'emr-7.0.0'
        assert call_args[1]['type'] == 'Spark'
        assert call_args[1]['architecture'] == 'X86_64'
        assert 'imageConfiguration' in call_args[1]
        assert 'workerTypeSpecifications' in call_args[1]
        assert 'runtimeConfiguration' in call_args[1]
        assert 'monitoringConfiguration' in call_args[1]
        assert 'interactiveConfiguration' in call_args[1]
        assert 'schedulerConfiguration' in call_args[1]
        assert 'identityCenterConfiguration' in call_args[1]

    @pytest.mark.asyncio
    async def test_concurrent_modification_error(self, handler_with_write, mock_ctx):
        """Test handling of concurrent modification errors."""
        # Mock MCP verification
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.verify_emr_serverless_application_managed_by_mcp'
        ) as mock_verify:
            mock_verify.return_value = {'is_valid': True}

            handler_with_write.emr_serverless_client.update_application.side_effect = ClientError(
                {
                    'Error': {
                        'Code': 'ConflictException',
                        'Message': 'Application is being updated by another process',
                    }
                },
                'UpdateApplication',
            )

            result = await handler_with_write.manage_aws_emr_serverless_applications(
                ctx=mock_ctx,
                operation='update-application',
                application_id='app-12345abcdef',
                name='updated-name',
            )

        assert result.isError
        assert 'Application is being updated by another process' in result.content[0].text

    @pytest.mark.asyncio
    async def test_throttling_error(self, handler_read_only, mock_ctx):
        """Test handling of AWS throttling errors."""
        handler_read_only.emr_serverless_client.list_applications.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'ListApplications',
        )

        result = await handler_read_only.manage_aws_emr_serverless_applications(
            ctx=mock_ctx,
            operation='list-applications',
        )

        assert result.isError
        assert 'Rate exceeded' in result.content[0].text

    @pytest.mark.asyncio
    async def test_generic_exception_handling(self, handler_read_only, mock_ctx):
        """Test handling of generic exceptions."""
        handler_read_only.emr_serverless_client.get_application.side_effect = Exception(
            'Unexpected error occurred'
        )

        result = await handler_read_only.manage_aws_emr_serverless_applications(
            ctx=mock_ctx,
            operation='get-application',
            application_id='app-12345abcdef',
        )

        assert result.isError
        assert 'Error in manage_aws_emr_serverless_applications' in result.content[0].text
        assert 'Unexpected error occurred' in result.content[0].text
