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


"""Tests for EMR EC2 Steps Handler.

These tests verify the functionality of the EMR EC2 Steps Handler
including parameter validation, response formatting, AWS client interaction,
permissions checks, and error handling.
"""

import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_ec2_steps_handler import (
    EMREc2StepsHandler,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp import Context
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    ctx = MagicMock(spec=Context)
    ctx.request_id = 'test-request-id'
    return ctx


@pytest.fixture
def steps_handler_with_write_access():
    """Create an EMR steps handler with write access enabled."""
    mcp_mock = MagicMock()
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client'
    ) as mock_create_client:
        mock_emr_client = MagicMock()
        mock_create_client.return_value = mock_emr_client
        handler = EMREc2StepsHandler(mcp_mock, allow_write=True)
    return handler


@pytest.fixture
def steps_handler_without_write_access():
    """Create an EMR steps handler with write access disabled."""
    mcp_mock = MagicMock()
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client'
    ) as mock_create_client:
        mock_emr_client = MagicMock()
        mock_create_client.return_value = mock_emr_client
        handler = EMREc2StepsHandler(mcp_mock, allow_write=False)
    return handler


class TestEMRStepsHandlerInitialization:
    """Test EMR steps handler initialization and setup."""

    def test_handler_initialization(self):
        """Test that the handler initializes correctly."""
        mcp_mock = MagicMock()

        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client'
        ) as mock_create_client:
            mock_emr_client = MagicMock()
            mock_create_client.return_value = mock_emr_client

            handler = EMREc2StepsHandler(mcp_mock)

            mcp_mock.tool.assert_called_once()
            assert handler.allow_write is False
            assert handler.allow_sensitive_data_access is False
            mock_create_client.assert_called_once_with('emr')
            assert handler.emr_client is mock_emr_client


class TestWriteOperationsPermissions:
    """Test write operations permission requirements."""

    @pytest.mark.parametrize('operation', ['add-steps', 'cancel-steps'])
    async def test_write_operations_denied_without_permission(
        self, steps_handler_without_write_access, mock_context, operation
    ):
        """Test that write operations are denied without permissions."""
        result = await steps_handler_without_write_access.manage_aws_emr_ec2_steps(
            ctx=mock_context, operation=operation, cluster_id='j-12345ABCDEF'
        )

        assert result.isError is True
        assert any(
            f'Operation {operation} is not allowed without write access' in content.text
            for content in result.content
        )

    @pytest.mark.parametrize('operation', ['describe-step', 'list-steps'])
    async def test_read_operations_allowed_without_permission(
        self, steps_handler_without_write_access, mock_context, operation
    ):
        """Test that read operations are allowed without write permissions."""
        with patch.object(steps_handler_without_write_access, 'emr_client') as mock_emr_client:
            if operation == 'describe-step':
                mock_emr_client.describe_step.return_value = {'Step': {}}
                result = await steps_handler_without_write_access.manage_aws_emr_ec2_steps(
                    ctx=mock_context,
                    operation=operation,
                    cluster_id='j-12345ABCDEF',
                    step_id='s-12345ABCDEF',
                )
            elif operation == 'list-steps':
                mock_emr_client.list_steps.return_value = {'Steps': [], 'Marker': None}
                result = await steps_handler_without_write_access.manage_aws_emr_ec2_steps(
                    ctx=mock_context, operation=operation, cluster_id='j-12345ABCDEF'
                )

            # Check that the operation completed without permission errors
            if result.isError:
                # If there's an error, it shouldn't be about write access
                error_text = ' '.join(content.text for content in result.content)
                assert 'not allowed without write access' not in error_text
            else:
                assert result.isError is False


class TestAddSteps:
    """Test add-steps operation."""

    async def test_add_steps_success(self, steps_handler_with_write_access, mock_context):
        """Test successful add-steps operation."""
        with patch.object(steps_handler_with_write_access, 'emr_client') as mock_emr_client:
            mock_emr_client.add_job_flow_steps.return_value = {
                'StepIds': ['s-12345ABCDEF', 's-67890GHIJKL']
            }

            steps = [
                {
                    'Name': 'Test Step 1',
                    'ActionOnFailure': 'CONTINUE',
                    'HadoopJarStep': {'Jar': 'command-runner.jar', 'Args': ['echo', 'hello']},
                },
                {
                    'Name': 'Test Step 2',
                    'ActionOnFailure': 'TERMINATE_CLUSTER',
                    'HadoopJarStep': {'Jar': 'command-runner.jar', 'Args': ['echo', 'world']},
                },
            ]

            result = await steps_handler_with_write_access.manage_aws_emr_ec2_steps(
                ctx=mock_context,
                operation='add-steps',
                cluster_id='j-12345ABCDEF',
                steps=steps,
            )

            mock_emr_client.add_job_flow_steps.assert_called_once_with(
                JobFlowId='j-12345ABCDEF', Steps=steps
            )

            assert result.isError is False
            assert result.cluster_id == 'j-12345ABCDEF'
            assert result.step_ids == ['s-12345ABCDEF', 's-67890GHIJKL']
            assert result.count == 2

    async def test_add_steps_with_execution_role(
        self, steps_handler_with_write_access, mock_context
    ):
        """Test add-steps with ExecutionRoleArn."""
        with patch.object(steps_handler_with_write_access, 'emr_client') as mock_emr_client:
            mock_emr_client.add_job_flow_steps.return_value = {'StepIds': ['s-12345ABCDEF']}

            steps = [
                {
                    'Name': 'Test Step',
                    'ActionOnFailure': 'CONTINUE',
                    'HadoopJarStep': {'Jar': 'command-runner.jar', 'Args': ['echo', 'hello']},
                    'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/EMRStepRole',
                }
            ]

            result = await steps_handler_with_write_access.manage_aws_emr_ec2_steps(
                ctx=mock_context,
                operation='add-steps',
                cluster_id='j-12345ABCDEF',
                steps=steps,
            )

            mock_emr_client.add_job_flow_steps.assert_called_once_with(
                JobFlowId='j-12345ABCDEF',
                Steps=steps,
                ExecutionRoleArn='arn:aws:iam::123456789012:role/EMRStepRole',
            )

            assert result.isError is False

    async def test_add_steps_missing_steps_parameter(
        self, steps_handler_with_write_access, mock_context
    ):
        """Test add-steps with missing steps parameter raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            await steps_handler_with_write_access.manage_aws_emr_ec2_steps(
                ctx=mock_context, operation='add-steps', cluster_id='j-12345ABCDEF'
            )
        assert 'steps is required for add-steps operation' in str(excinfo.value)


class TestCancelSteps:
    """Test cancel-steps operation."""

    async def test_cancel_steps_success(self, steps_handler_with_write_access, mock_context):
        """Test successful cancel-steps operation."""
        with patch.object(steps_handler_with_write_access, 'emr_client') as mock_emr_client:
            mock_emr_client.cancel_steps.return_value = {
                'CancelStepsInfoList': [
                    {'StepId': 's-12345ABCDEF', 'Status': 'SUBMITTED', 'Reason': 'User request'}
                ]
            }

            result = await steps_handler_with_write_access.manage_aws_emr_ec2_steps(
                ctx=mock_context,
                operation='cancel-steps',
                cluster_id='j-12345ABCDEF',
                step_ids=['s-12345ABCDEF'],
            )

            mock_emr_client.cancel_steps.assert_called_once_with(
                ClusterId='j-12345ABCDEF', StepIds=['s-12345ABCDEF']
            )

            assert result.isError is False
            assert result.cluster_id == 'j-12345ABCDEF'
            assert result.count == 1

    async def test_cancel_steps_with_cancellation_option(
        self, steps_handler_with_write_access, mock_context
    ):
        """Test cancel-steps with cancellation option."""
        with patch.object(steps_handler_with_write_access, 'emr_client') as mock_emr_client:
            mock_emr_client.cancel_steps.return_value = {'CancelStepsInfoList': []}

            result = await steps_handler_with_write_access.manage_aws_emr_ec2_steps(
                ctx=mock_context,
                operation='cancel-steps',
                cluster_id='j-12345ABCDEF',
                step_ids=['s-12345ABCDEF'],
                step_cancellation_option='TERMINATE_PROCESS',
            )

            mock_emr_client.cancel_steps.assert_called_once_with(
                ClusterId='j-12345ABCDEF',
                StepIds=['s-12345ABCDEF'],
                StepCancellationOption='TERMINATE_PROCESS',
            )

            assert result.isError is False

    async def test_cancel_steps_missing_step_ids(
        self, steps_handler_with_write_access, mock_context
    ):
        """Test cancel-steps with missing step_ids parameter raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            await steps_handler_with_write_access.manage_aws_emr_ec2_steps(
                ctx=mock_context, operation='cancel-steps', cluster_id='j-12345ABCDEF'
            )
        assert 'step_ids is required for cancel-steps operation' in str(excinfo.value)

    async def test_cancel_steps_invalid_step_id(
        self, steps_handler_with_write_access, mock_context
    ):
        """Test cancel-steps with invalid step ID."""
        with pytest.raises(ValueError) as excinfo:
            await steps_handler_with_write_access.manage_aws_emr_ec2_steps(
                ctx=mock_context,
                operation='cancel-steps',
                cluster_id='j-12345ABCDEF',
                step_ids=[123],  # Invalid non-string step ID
            )
        assert 'Invalid step ID: 123. Must be a string.' in str(excinfo.value)


class TestDescribeStep:
    """Test describe-step operation."""

    async def test_describe_step_success(self, steps_handler_with_write_access, mock_context):
        """Test successful describe-step operation."""
        with patch.object(steps_handler_with_write_access, 'emr_client') as mock_emr_client:
            mock_emr_client.describe_step.return_value = {
                'Step': {
                    'Id': 's-12345ABCDEF',
                    'Name': 'Test Step',
                    'Status': {'State': 'COMPLETED'},
                }
            }

            result = await steps_handler_with_write_access.manage_aws_emr_ec2_steps(
                ctx=mock_context,
                operation='describe-step',
                cluster_id='j-12345ABCDEF',
                step_id='s-12345ABCDEF',
            )

            mock_emr_client.describe_step.assert_called_once_with(
                ClusterId='j-12345ABCDEF', StepId='s-12345ABCDEF'
            )

            assert result.isError is False
            assert result.cluster_id == 'j-12345ABCDEF'
            assert result.step['Id'] == 's-12345ABCDEF'

    async def test_describe_step_missing_step_id(
        self, steps_handler_with_write_access, mock_context
    ):
        """Test describe-step with missing step_id parameter."""
        try:
            result = await steps_handler_with_write_access.manage_aws_emr_ec2_steps(
                ctx=mock_context, operation='describe-step', cluster_id='j-12345ABCDEF'
            )

            assert result.isError is True
            error_text = ' '.join(content.text for content in result.content)
            assert (
                'step_id is required for describe-step operation' in error_text
                or 'Error in manage_aws_emr_ec2_steps' in error_text
            )
        except Exception as e:
            # ValidationError from pydantic is expected when step field is missing
            assert 'ValidationError' in str(type(e)) or 'step_id is required' in str(e)


class TestListSteps:
    """Test list-steps operation."""

    async def test_list_steps_success(self, steps_handler_with_write_access, mock_context):
        """Test successful list-steps operation."""
        with patch.object(steps_handler_with_write_access, 'emr_client') as mock_emr_client:
            mock_emr_client.list_steps.return_value = {
                'Steps': [{'Id': 's-12345ABCDEF', 'Name': 'Test Step'}],
                'Marker': 'next-marker',
            }

            result = await steps_handler_with_write_access.manage_aws_emr_ec2_steps(
                ctx=mock_context, operation='list-steps', cluster_id='j-12345ABCDEF'
            )

            # Verify results without checking mock calls
            assert result.isError is False
            assert result.cluster_id == 'j-12345ABCDEF'
            assert result.count == 1
            assert result.marker == 'next-marker'

    async def test_list_steps_with_filters(self, steps_handler_with_write_access, mock_context):
        """Test list-steps with filters."""
        with patch.object(steps_handler_with_write_access, 'emr_client') as mock_emr_client:
            mock_emr_client.list_steps.return_value = {'Steps': [], 'Marker': None}

            result = await steps_handler_with_write_access.manage_aws_emr_ec2_steps(
                ctx=mock_context,
                operation='list-steps',
                cluster_id='j-12345ABCDEF',
                step_states=['RUNNING', 'COMPLETED'],
                step_ids=['s-12345ABCDEF'],
                marker='prev-marker',
            )

            mock_emr_client.list_steps.assert_called_once_with(
                ClusterId='j-12345ABCDEF',
                StepStates=['RUNNING', 'COMPLETED'],
                StepIds=['s-12345ABCDEF'],
                Marker='prev-marker',
            )

            assert result.isError is False

    async def test_list_steps_invalid_step_state(
        self, steps_handler_with_write_access, mock_context
    ):
        """Test list-steps with invalid step state."""
        try:
            result = await steps_handler_with_write_access.manage_aws_emr_ec2_steps(
                ctx=mock_context,
                operation='list-steps',
                cluster_id='j-12345ABCDEF',
                step_states=[123],  # Invalid non-string state
            )

            assert result.isError is True
            error_text = ' '.join(content.text for content in result.content)
            assert (
                'Invalid step state: 123. Must be a string.' in error_text
                or 'Error in manage_aws_emr_ec2_steps' in error_text
            )
        except Exception as e:
            # ValidationError is expected for invalid data
            assert 'ValidationError' in str(type(e)) or 'Invalid step state' in str(e)


class TestErrorHandling:
    """Test error handling scenarios."""

    async def test_invalid_operation(self, steps_handler_with_write_access, mock_context):
        """Test invalid operation returns error."""
        result = await steps_handler_with_write_access.manage_aws_emr_ec2_steps(
            ctx=mock_context, operation='invalid-operation', cluster_id='j-12345ABCDEF'
        )

        assert result.isError is True
        assert any('Invalid operation' in content.text for content in result.content)

    async def test_aws_client_error(self, steps_handler_with_write_access, mock_context):
        """Test handling of AWS client errors."""
        with patch.object(steps_handler_with_write_access, 'emr_client') as mock_emr_client:
            mock_emr_client.list_steps.side_effect = ClientError(
                error_response={
                    'Error': {'Code': 'ValidationException', 'Message': 'Invalid cluster'}
                },
                operation_name='ListSteps',
            )

            result = await steps_handler_with_write_access.manage_aws_emr_ec2_steps(
                ctx=mock_context, operation='list-steps', cluster_id='j-12345ABCDEF'
            )

            assert result.isError is True
            error_text = ' '.join(content.text for content in result.content)
            # Check for either error message format
            assert (
                'Error in manage_aws_emr_ec2_steps' in error_text
                or 'ValidationException' in error_text
            )
