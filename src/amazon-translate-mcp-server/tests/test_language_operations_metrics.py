"""Test cases for language operations metrics coverage improvements."""

import pytest
from awslabs.amazon_translate_mcp_server.language_operations import LanguageOperations
from unittest.mock import MagicMock


class TestLanguageOperationsMetrics:
    """Test cases for language operations metrics functionality."""

    def test_language_operations_get_language_metrics_access_denied(self):
        """Test get_language_metrics with access denied error."""
        from awslabs.amazon_translate_mcp_server.models import AuthenticationError
        from botocore.exceptions import ClientError

        mock_aws_client = MagicMock()
        ops = LanguageOperations(mock_aws_client)

        # Mock _retrieve_cloudwatch_metrics to raise AccessDenied error
        ops._retrieve_cloudwatch_metrics = MagicMock(
            side_effect=ClientError(
                {
                    'Error': {
                        'Code': 'AccessDenied',
                        'Message': 'Access denied to CloudWatch metrics',
                    }
                },
                'GetMetricStatistics',
            )
        )

        with pytest.raises(AuthenticationError):
            ops.get_language_metrics('en-es', '24h')

    def test_language_operations_get_language_metrics_unauthorized_operation(self):
        """Test get_language_metrics with unauthorized operation error."""
        from awslabs.amazon_translate_mcp_server.models import AuthenticationError
        from botocore.exceptions import ClientError

        mock_aws_client = MagicMock()
        ops = LanguageOperations(mock_aws_client)

        # Mock _retrieve_cloudwatch_metrics to raise UnauthorizedOperation error
        ops._retrieve_cloudwatch_metrics = MagicMock(
            side_effect=ClientError(
                {'Error': {'Code': 'UnauthorizedOperation', 'Message': 'Unauthorized operation'}},
                'GetMetricStatistics',
            )
        )

        with pytest.raises(AuthenticationError):
            ops.get_language_metrics('en-es', '24h')

    def test_language_operations_get_language_metrics_service_unavailable(self):
        """Test get_language_metrics with service unavailable error."""
        from awslabs.amazon_translate_mcp_server.models import ServiceUnavailableError
        from botocore.exceptions import ClientError

        mock_aws_client = MagicMock()
        ops = LanguageOperations(mock_aws_client)

        # Mock _retrieve_cloudwatch_metrics to raise ServiceUnavailable error
        ops._retrieve_cloudwatch_metrics = MagicMock(
            side_effect=ClientError(
                {
                    'Error': {
                        'Code': 'ServiceUnavailable',
                        'Message': 'Service temporarily unavailable',
                    }
                },
                'GetMetricStatistics',
            )
        )

        with pytest.raises(ServiceUnavailableError):
            ops.get_language_metrics('en-es', '24h')

    def test_language_operations_get_language_metrics_internal_failure(self):
        """Test get_language_metrics with internal failure error."""
        from awslabs.amazon_translate_mcp_server.models import ServiceUnavailableError
        from botocore.exceptions import ClientError

        mock_aws_client = MagicMock()
        ops = LanguageOperations(mock_aws_client)

        # Mock _retrieve_cloudwatch_metrics to raise InternalFailure error
        ops._retrieve_cloudwatch_metrics = MagicMock(
            side_effect=ClientError(
                {'Error': {'Code': 'InternalFailure', 'Message': 'Internal service failure'}},
                'GetMetricStatistics',
            )
        )

        with pytest.raises(ServiceUnavailableError):
            ops.get_language_metrics('en-es', '24h')

    def test_language_operations_get_language_metrics_generic_client_error(self):
        """Test get_language_metrics with generic client error."""
        from awslabs.amazon_translate_mcp_server.models import TranslateException
        from botocore.exceptions import ClientError

        mock_aws_client = MagicMock()
        ops = LanguageOperations(mock_aws_client)

        # Mock _retrieve_cloudwatch_metrics to raise generic client error
        ops._retrieve_cloudwatch_metrics = MagicMock(
            side_effect=ClientError(
                {'Error': {'Code': 'UnknownError', 'Message': 'Unknown error occurred'}},
                'GetMetricStatistics',
            )
        )

        with pytest.raises(TranslateException):
            ops.get_language_metrics('en-es', '24h')

    def test_language_operations_get_language_metrics_botocore_error(self):
        """Test get_language_metrics with botocore error."""
        from awslabs.amazon_translate_mcp_server.models import ServiceUnavailableError
        from botocore.exceptions import BotoCoreError

        mock_aws_client = MagicMock()
        ops = LanguageOperations(mock_aws_client)

        # Mock _retrieve_cloudwatch_metrics to raise BotoCoreError
        ops._retrieve_cloudwatch_metrics = MagicMock(side_effect=BotoCoreError())

        with pytest.raises(ServiceUnavailableError):
            ops.get_language_metrics('en-es', '24h')

    def test_language_operations_get_language_metrics_network_error(self):
        """Test get_language_metrics with network error."""
        from awslabs.amazon_translate_mcp_server.models import ServiceUnavailableError
        from botocore.exceptions import EndpointConnectionError

        mock_aws_client = MagicMock()
        ops = LanguageOperations(mock_aws_client)

        # Mock _retrieve_cloudwatch_metrics to raise EndpointConnectionError
        ops._retrieve_cloudwatch_metrics = MagicMock(
            side_effect=EndpointConnectionError(
                endpoint_url='https://cloudwatch.us-east-1.amazonaws.com'
            )
        )

        with pytest.raises(ServiceUnavailableError):
            ops.get_language_metrics('en-es', '24h')

    def test_language_operations_get_language_metrics_timeout_error(self):
        """Test get_language_metrics with timeout error."""
        from awslabs.amazon_translate_mcp_server.models import ServiceUnavailableError
        from botocore.exceptions import ReadTimeoutError

        mock_aws_client = MagicMock()
        ops = LanguageOperations(mock_aws_client)

        # Mock _retrieve_cloudwatch_metrics to raise ReadTimeoutError
        ops._retrieve_cloudwatch_metrics = MagicMock(
            side_effect=ReadTimeoutError(
                endpoint_url='https://cloudwatch.us-east-1.amazonaws.com', error='Read timeout'
            )
        )

        with pytest.raises(ServiceUnavailableError):
            ops.get_language_metrics('en-es', '24h')

    def test_language_operations_get_language_metrics_success_path(self):
        """Test get_language_metrics success path."""
        mock_aws_client = MagicMock()
        ops = LanguageOperations(mock_aws_client)

        # Mock CloudWatch client to return successful response
        mock_cloudwatch_client = MagicMock()
        mock_aws_client.get_cloudwatch_client.return_value = mock_cloudwatch_client

        # Mock the _retrieve_cloudwatch_metrics method to return test data
        ops._retrieve_cloudwatch_metrics = MagicMock(
            return_value={
                'translation_count': 10,
                'character_count': 250,
                'average_response_time': 0.5,
                'error_rate': 0.01,
            }
        )

        result = ops.get_language_metrics('en-es', '24h')

        # Check that result is a LanguageMetrics object with expected attributes
        assert hasattr(result, 'character_count')
        assert hasattr(result, 'translation_count')
        assert hasattr(result, 'error_rate')
        assert hasattr(result, 'average_response_time')
        assert result.character_count == 250
        assert result.translation_count == 10
