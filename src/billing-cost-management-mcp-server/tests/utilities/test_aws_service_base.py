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

"""Tests for AWS service utilities.

This module contains unit tests for the aws_service_base.py module, including:
- Creating AWS clients with proper configuration
- JSON parsing and validation
- Date range calculations and validations
- AWS error handling and response formatting
- Response formatting utilities
"""

import pytest
from awslabs.billing_cost_management_mcp_server.utilities.aws_service_base import (
    __version__,
    create_aws_client,
    format_response,
    get_date_range,
    handle_aws_error,
    parse_json,
    validate_date_format,
)
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


class TestCreateAwsClient:
    """Tests for create_aws_client function."""

    @patch('boto3.Session')
    def test_client_creation_default_region(self, mock_session):
        """Test client creation with default region."""
        # Setup proper mocks
        mock_client = MagicMock()
        mock_session_instance = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        with patch.dict('os.environ', {'AWS_REGION': 'us-east-1'}, clear=True):
            create_aws_client('ce')

        # Assert with detailed validation
        mock_session.assert_called_once_with(region_name='us-east-1')
        mock_session_instance.client.assert_called_once()

        # Verify config parameters
        call_kwargs = mock_session_instance.client.call_args.kwargs
        assert 'config' in call_kwargs
        assert (
            call_kwargs['config'].user_agent_extra
            == f'awslabs/mcp/aws-finops-mcp-server/{__version__}'
        )

        # Verify service name
        service_arg = mock_session_instance.client.call_args.args[0]
        assert service_arg == 'ce'

    @patch('boto3.Session')
    def test_client_creation_custom_region(self, mock_session):
        """Test client creation with custom region."""
        # Setup
        mock_client = MagicMock()
        mock_session_instance = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Execute
        # Use one of the allowed services from aws_service_base.py
        create_aws_client('pricing', 'us-west-2')

        # Assert with detailed validation
        mock_session.assert_called_once_with(region_name='us-west-2')
        mock_session_instance.client.assert_called_once()

        # Verify service name
        service_arg = mock_session_instance.client.call_args.args[0]
        assert service_arg == 'pricing'

    @patch('boto3.Session')
    def test_client_creation_with_aws_profile(self, mock_session):
        """Test client creation with AWS_PROFILE environment variable."""
        # Setup
        mock_client = MagicMock()
        mock_session_instance = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Test with AWS_PROFILE set
        with patch.dict('os.environ', {'AWS_PROFILE': 'test-profile', 'AWS_REGION': 'us-east-1'}):
            # Use one of the allowed services from aws_service_base.py
            create_aws_client('sts')

        # Assert with detailed validation
        mock_session.assert_called_once_with(profile_name='test-profile', region_name='us-east-1')
        mock_session_instance.client.assert_called_once()


class TestParseJson:
    """Tests for parse_json function."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON string."""
        # Setup
        json_str = '{"name": "test", "value": 42}'

        # Execute
        result = parse_json(json_str, 'test_param')

        # Assert
        assert result == {'name': 'test', 'value': 42}

    def test_parse_none_json(self):
        """Test parsing None JSON string."""
        # Execute
        result = parse_json(None, 'test_param')

        # Assert
        assert result is None

    def test_parse_empty_json(self):
        """Test parsing empty JSON string."""
        # Execute
        result = parse_json('', 'test_param')

        # Assert
        assert result is None

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON string."""
        # Setup
        json_str = '{"name": "test", value: 42}'

        # Execute and Assert
        with pytest.raises(ValueError) as excinfo:
            parse_json(json_str, 'test_param')

        assert 'Invalid JSON format for test_param parameter' in str(excinfo.value)


class TestDateFunctions:
    """Tests for date-related functions."""

    def test_get_date_range_with_defaults(self):
        """Test getting date range with defaults."""
        # Setup
        today = datetime.now().strftime('%Y-%m-%d')
        days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        # Execute
        start, end = get_date_range()

        # Assert
        assert start == days_ago
        assert end == today

    def test_get_date_range_with_custom_dates(self):
        """Test getting date range with custom dates."""
        # Execute
        start, end = get_date_range('2023-01-01', '2023-12-31')

        # Assert
        assert start == '2023-01-01'
        assert end == '2023-12-31'

    def test_get_date_range_with_custom_start_only(self):
        """Test getting date range with custom start date only."""
        # Setup
        today = datetime.now().strftime('%Y-%m-%d')

        # Execute
        start, end = get_date_range('2023-01-01')

        # Assert
        assert start == '2023-01-01'
        assert end == today

    def test_get_date_range_with_custom_days_ago(self):
        """Test getting date range with custom days ago."""
        # Setup
        today = datetime.now().strftime('%Y-%m-%d')
        days_ago = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

        # Execute
        start, end = get_date_range(default_days_ago=10)

        # Assert
        assert start == days_ago
        assert end == today

    def test_validate_date_format_valid(self):
        """Test validating valid date format."""
        # Execute and Assert
        assert validate_date_format('2023-01-01') is True

    def test_validate_date_format_invalid_format(self):
        """Test validating invalid date format."""
        # Execute and Assert
        assert validate_date_format('01/01/2023') is False

    def test_validate_date_format_invalid_date(self):
        """Test validating invalid date."""
        # Execute and Assert
        assert validate_date_format('2023-02-30') is False

    def test_validate_date_format_none(self):
        """Test validating None date."""
        # Execute and Assert
        assert validate_date_format(None) is False

    def test_validate_date_format_empty(self):
        """Test validating empty date."""
        # Execute and Assert
        assert validate_date_format('') is False


class TestHandleAwsError:
    """Tests for handle_aws_error function."""

    @pytest.mark.asyncio
    async def test_handle_client_error(self):
        """Test handling AWS client error."""
        # Setup
        ctx = AsyncMock()

        # Properly create a ClientError with correct structure
        from botocore.exceptions import ClientError

        error_response = {
            'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Resource not found'}
        }
        error = ClientError(error_response, 'ListItems')

        # Execute
        result = await handle_aws_error(ctx, error, 'ListItems', 'DynamoDB')

        # Assert with detailed validation
        ctx.error.assert_called_once()
        error_msg = ctx.error.call_args.args[0]
        assert "Error in DynamoDB operation 'ListItems'" in error_msg
        assert 'ResourceNotFoundException' in error_msg

        # Verify response structure
        assert result['status'] == 'error'
        assert result['error_type'] == 'ResourceNotFoundException'
        assert result['service'] == 'DynamoDB'
        assert result['operation'] == 'ListItems'
        assert result['message'] == 'Resource not found'

    @pytest.mark.asyncio
    async def test_handle_value_error(self):
        """Test handling ValueError."""
        # Setup
        ctx = AsyncMock()
        error = ValueError('Invalid parameter')

        # Execute
        result = await handle_aws_error(ctx, error, 'ParseInput', 'InputProcessor')

        # Assert with detailed validation
        ctx.warning.assert_called_once()
        error_msg = ctx.warning.call_args.args[0]
        assert "Error in InputProcessor operation 'ParseInput'" in error_msg
        assert 'Invalid parameter' in error_msg

        # Verify response structure
        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert result['service'] == 'InputProcessor'
        assert result['operation'] == 'ParseInput'
        assert result['message'] == 'Invalid parameter'

    @pytest.mark.asyncio
    async def test_handle_generic_error(self):
        """Test handling generic error."""
        # Setup
        ctx = AsyncMock()
        error = Exception('Unexpected error')

        # Execute
        result = await handle_aws_error(ctx, error, 'ProcessData', 'DataService')

        # Assert with detailed validation
        ctx.error.assert_called_once()
        error_msg = ctx.error.call_args.args[0]
        assert "Error in DataService operation 'ProcessData'" in error_msg
        assert 'Unexpected error' in error_msg

        # Verify response structure
        assert result['status'] == 'error'
        assert result['error_type'] == 'unknown_exception'
        assert result['service'] == 'DataService'
        assert result['operation'] == 'ProcessData'
        assert result['message'] == 'Unexpected error'

    @pytest.mark.asyncio
    async def test_handle_boto_core_error(self):
        """Test handling BotoCoreError."""
        # Setup
        ctx = AsyncMock()
        from botocore.exceptions import BotoCoreError

        error = BotoCoreError()
        error.fmt = 'Connection error'

        # Execute
        result = await handle_aws_error(ctx, error, 'Connect', 'EC2')

        # Assert with detailed validation
        ctx.error.assert_called_once()
        error_msg = ctx.error.call_args.args[0]
        assert "Error in EC2 operation 'Connect'" in error_msg

        # Verify response structure
        assert result['status'] == 'error'
        assert result['error_type'] == 'aws_connection_error'
        assert result['service'] == 'EC2'
        assert result['operation'] == 'Connect'
        assert result['message'] == 'AWS service connection error: BotoCoreError'


class TestFormatResponse:
    """Tests for format_response function."""

    def test_format_success_response(self):
        """Test formatting success response."""
        # Setup
        data = {'items': [1, 2, 3]}

        # Execute
        result = format_response('success', data)

        # Assert with comprehensive validation
        assert result['status'] == 'success'
        assert result['data'] == data
        assert 'message' not in result
        assert len(result.keys()) == 2  # Only status and data keys should be present

    def test_format_success_response_with_message(self):
        """Test formatting success response with message."""
        # Setup
        data = {'items': [1, 2, 3]}
        message = 'Operation completed successfully'

        # Execute
        result = format_response('success', data, message)

        # Assert with comprehensive validation
        assert result['status'] == 'success'
        assert result['data'] == data
        assert result['message'] == message
        assert len(result.keys()) == 3  # status, data, and message keys should be present

    def test_format_error_response(self):
        """Test formatting error response."""
        # Setup
        data = {'error_details': 'Invalid input'}
        message = 'Operation failed'

        # Execute
        result = format_response('error', data, message)

        # Assert with comprehensive validatio
        assert result['status'] == 'error'
        assert result['data'] == data
        assert result['message'] == message
        assert len(result.keys()) == 3  # status, data, and message keys should be present
