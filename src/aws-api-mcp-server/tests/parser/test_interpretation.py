import pytest
from awslabs.aws_api_mcp_server.core.parser.interpretation import (
    _execute_with_custom_retry,
    _should_retry_error,
)
from botocore.exceptions import ClientError, ConnectionError
from unittest.mock import MagicMock, Mock, patch


def create_client_error(status_code: int, error_code: str = 'TestError') -> ClientError:
    """Helper function to create a ClientError with specified status code."""
    error_response = {
        'Error': {'Code': error_code, 'Message': 'Test error message'},
        'ResponseMetadata': {'HTTPStatusCode': status_code},
    }
    return ClientError(error_response, 'test_operation')


class TestShouldRetryError:
    """Tests for _should_retry_error function - DR-A-3 compliant retry logic."""

    @pytest.mark.parametrize(
        'status_code',
        [400, 401, 403, 404, 409, 429, 499],
    )
    def test_4xx_errors_not_retried(self, status_code):
        """Test that 4xx client errors return False (no retry)."""
        error = create_client_error(status_code)
        assert _should_retry_error(error) is False

    def test_503_not_retried(self):
        """Test that 503 Service Unavailable returns False (DR-A-3 compliance)."""
        error = create_client_error(503)
        assert _should_retry_error(error) is False

    @pytest.mark.parametrize(
        'status_code',
        [500, 502, 504],
    )
    def test_other_5xx_errors_retried(self, status_code):
        """Test that other 5xx errors return True (allow retry)."""
        error = create_client_error(status_code)
        assert _should_retry_error(error) is True

    def test_connection_error_retried(self):
        """Test that ConnectionError returns True (allow retry)."""
        error = ConnectionError(error='Connection failed')
        assert _should_retry_error(error) is True

    def test_non_client_error_retried(self):
        """Test that non-ClientError exceptions return True (default behavior)."""
        error = ValueError('Test error')
        assert _should_retry_error(error) is True

    def test_generic_exception_retried(self):
        """Test that generic exceptions return True."""
        error = Exception('Generic error')
        assert _should_retry_error(error) is True


class TestExecuteWithCustomRetry:
    """Tests for _execute_with_custom_retry function."""

    def test_successful_operation_first_attempt(self):
        """Test that a successful operation returns immediately without retry."""
        mock_operation = Mock(return_value={'result': 'success'})

        result = _execute_with_custom_retry(mock_operation, param='value')

        assert result == {'result': 'success'}
        assert mock_operation.call_count == 1
        mock_operation.assert_called_once_with(param='value')

    @patch('awslabs.aws_api_mcp_server.core.parser.interpretation.time.sleep')
    def test_retry_on_500_error_then_success(self, mock_sleep):
        """Test that operation retries once on 500 error then succeeds."""
        mock_operation = Mock(
            side_effect=[
                create_client_error(500),
                {'result': 'success'},
            ]
        )

        result = _execute_with_custom_retry(mock_operation)

        assert result == {'result': 'success'}
        assert mock_operation.call_count == 2
        mock_sleep.assert_called_once_with(1)

    def test_no_retry_on_4xx_error(self):
        """Test that 4xx errors fail immediately without retry."""
        error_403 = create_client_error(403)
        mock_operation = Mock(side_effect=error_403)

        with pytest.raises(ClientError) as exc_info:
            _execute_with_custom_retry(mock_operation)

        assert exc_info.value == error_403
        assert mock_operation.call_count == 1

    def test_no_retry_on_503_error(self):
        """Test that 503 errors fail immediately without retry (DR-A-3 compliance)."""
        error_503 = create_client_error(503)
        mock_operation = Mock(side_effect=error_503)

        with pytest.raises(ClientError) as exc_info:
            _execute_with_custom_retry(mock_operation)

        assert exc_info.value == error_503
        assert mock_operation.call_count == 1

    @patch('awslabs.aws_api_mcp_server.core.parser.interpretation.time.sleep')
    def test_retry_delay_is_one_second(self, mock_sleep):
        """Test that retry delay is exactly 1 second."""
        mock_operation = Mock(
            side_effect=[
                create_client_error(500),
                {'result': 'success'},
            ]
        )

        _execute_with_custom_retry(mock_operation)

        mock_sleep.assert_called_once_with(1)

    @patch('awslabs.aws_api_mcp_server.core.parser.interpretation.time.sleep')
    def test_max_two_attempts(self, mock_sleep):
        """Test that operation only retries once (max 2 total attempts)."""
        error_500 = create_client_error(500)
        mock_operation = Mock(side_effect=error_500)

        with pytest.raises(ClientError):
            _execute_with_custom_retry(mock_operation)

        assert mock_operation.call_count == 2
        mock_sleep.assert_called_once_with(1)

    @patch('awslabs.aws_api_mcp_server.core.parser.interpretation.time.sleep')
    def test_retry_exhaustion_with_retryable_errors(self, mock_sleep):
        """Test that operation fails after max attempts with retryable errors."""
        error_500 = create_client_error(500)
        mock_operation = Mock(side_effect=[error_500, error_500])

        with pytest.raises(ClientError) as exc_info:
            _execute_with_custom_retry(mock_operation)

        assert exc_info.value == error_500
        assert mock_operation.call_count == 2

    @patch('awslabs.aws_api_mcp_server.core.parser.interpretation.time.sleep')
    def test_retry_with_connection_error(self, mock_sleep):
        """Test that connection errors are retried."""
        mock_operation = Mock(
            side_effect=[
                ConnectionError(error='Connection timeout'),
                {'result': 'success'},
            ]
        )

        result = _execute_with_custom_retry(mock_operation)

        assert result == {'result': 'success'}
        assert mock_operation.call_count == 2
        mock_sleep.assert_called_once_with(1)

    def test_operation_with_kwargs(self):
        """Test that operation kwargs are passed correctly."""
        mock_operation = Mock(return_value={'result': 'success'})

        result = _execute_with_custom_retry(
            mock_operation, bucket='my-bucket', key='my-key', body='data'
        )

        assert result == {'result': 'success'}
        mock_operation.assert_called_once_with(bucket='my-bucket', key='my-key', body='data')

    @patch('awslabs.aws_api_mcp_server.core.parser.interpretation.time.sleep')
    def test_retry_preserves_kwargs(self, mock_sleep):
        """Test that kwargs are preserved across retry attempts."""
        mock_operation = Mock(
            side_effect=[
                create_client_error(500),
                {'result': 'success'},
            ]
        )

        _execute_with_custom_retry(mock_operation, param1='value1', param2='value2')

        assert mock_operation.call_count == 2
        # Verify both calls had the same kwargs
        first_call = mock_operation.call_args_list[0]
        second_call = mock_operation.call_args_list[1]
        assert first_call == second_call

    @patch('awslabs.aws_api_mcp_server.core.parser.interpretation.time.sleep')
    def test_multiple_error_codes(self, mock_sleep):
        """Test retry behavior with different error codes across attempts."""
        mock_operation = Mock(
            side_effect=[
                create_client_error(502),  # Retryable
                {'result': 'success'},
            ]
        )

        result = _execute_with_custom_retry(mock_operation)

        assert result == {'result': 'success'}
        assert mock_operation.call_count == 2


class TestInterpretIntegration:
    """Integration tests for interpret function with retry logic."""

    @patch('awslabs.aws_api_mcp_server.core.parser.interpretation.boto3')
    @patch('awslabs.aws_api_mcp_server.core.parser.interpretation.time.sleep')
    def test_non_paginated_operation_with_retry(self, mock_sleep, mock_boto3):
        """Test full flow through interpret() for non-paginated operation with retry."""
        from awslabs.aws_api_mcp_server.core.common.command import IRCommand
        from awslabs.aws_api_mcp_server.core.common.command_metadata import CommandMetadata
        from awslabs.aws_api_mcp_server.core.parser.interpretation import interpret

        # Setup mock client
        mock_client = MagicMock()
        mock_client.can_paginate.return_value = False
        mock_boto3.client.return_value = mock_client

        # Setup operation to fail once then succeed
        mock_operation = Mock(
            side_effect=[
                create_client_error(500),
                {'result': 'success', 'ResponseMetadata': {'HTTPStatusCode': 200}},
            ]
        )
        mock_client.describe_instances = mock_operation

        # Create IR command
        command_metadata = CommandMetadata(
            service_sdk_name='ec2',
            service_full_sdk_name='Amazon Elastic Compute Cloud',
            operation_sdk_name='DescribeInstances',
            has_streaming_output=False,
        )
        ir = IRCommand(
            command_metadata=command_metadata,
            parameters={},
            region='us-east-1',
        )

        # Execute
        result = interpret(
            ir=ir,
            access_key_id='test_key',
            secret_access_key='test_secret',  # pragma: allowlist secret
            session_token=None,
            region='us-east-1',
        )

        # Verify retry occurred
        assert result == {'result': 'success', 'ResponseMetadata': {'HTTPStatusCode': 200}}
        assert mock_operation.call_count == 2
        mock_sleep.assert_called_once_with(1)

    @patch('awslabs.aws_api_mcp_server.core.parser.interpretation.boto3')
    def test_non_paginated_operation_no_retry_on_503(self, mock_boto3):
        """Test that 503 errors don't retry (DR-A-3 compliance)."""
        from awslabs.aws_api_mcp_server.core.common.command import IRCommand
        from awslabs.aws_api_mcp_server.core.common.command_metadata import CommandMetadata
        from awslabs.aws_api_mcp_server.core.parser.interpretation import interpret

        # Setup mock client
        mock_client = MagicMock()
        mock_client.can_paginate.return_value = False
        mock_boto3.client.return_value = mock_client

        # Setup operation to fail with 503
        error_503 = create_client_error(503)
        mock_operation = Mock(side_effect=error_503)
        mock_client.describe_instances = mock_operation

        # Create IR command
        command_metadata = CommandMetadata(
            service_sdk_name='ec2',
            service_full_sdk_name='Amazon Elastic Compute Cloud',
            operation_sdk_name='DescribeInstances',
            has_streaming_output=False,
        )
        ir = IRCommand(
            command_metadata=command_metadata,
            parameters={},
            region='us-east-1',
        )

        # Execute and verify no retry
        with pytest.raises(ClientError):
            interpret(
                ir=ir,
                access_key_id='test_key',
                secret_access_key='test_secret',  # pragma: allowlist secret
                session_token=None,
                region='us-east-1',
            )

        # Verify only one attempt (no retry)
        assert mock_operation.call_count == 1

    @patch('awslabs.aws_api_mcp_server.core.parser.interpretation.build_result')
    @patch('awslabs.aws_api_mcp_server.core.parser.interpretation.boto3')
    @patch('awslabs.aws_api_mcp_server.core.parser.interpretation.time.sleep')
    def test_paginated_operation_with_retry(self, mock_sleep, mock_boto3, mock_build_result):
        """Test full flow through interpret() for paginated operation with retry."""
        from awslabs.aws_api_mcp_server.core.common.command import IRCommand
        from awslabs.aws_api_mcp_server.core.common.command_metadata import CommandMetadata
        from awslabs.aws_api_mcp_server.core.parser.interpretation import interpret

        # Setup mock client and paginator
        mock_client = MagicMock()
        mock_client.can_paginate.return_value = True
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_boto3.client.return_value = mock_client

        # Setup build_result to fail once then succeed
        mock_build_result.side_effect = [
            create_client_error(500),
            {'Items': ['item1', 'item2'], 'ResponseMetadata': {'HTTPStatusCode': 200}},
        ]

        # Create IR command
        command_metadata = CommandMetadata(
            service_sdk_name='dynamodb',
            service_full_sdk_name='Amazon DynamoDB',
            operation_sdk_name='Scan',
            has_streaming_output=False,
        )
        ir = IRCommand(
            command_metadata=command_metadata,
            parameters={'TableName': 'test-table'},
            region='us-east-1',
        )

        # Execute
        result = interpret(
            ir=ir,
            access_key_id='test_key',
            secret_access_key='test_secret',  # pragma: allowlist secret
            session_token=None,
            region='us-east-1',
        )

        # Verify retry occurred for pagination
        assert result == {'Items': ['item1', 'item2'], 'ResponseMetadata': {'HTTPStatusCode': 200}}
        assert mock_build_result.call_count == 2
        mock_sleep.assert_called_once_with(1)
