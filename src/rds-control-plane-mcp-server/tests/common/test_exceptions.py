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

"""Tests for the exceptions module in the RDS Control Plane MCP Server."""

import json
import pytest
from awslabs.rds_control_plane_mcp_server.common.decorators.handle_exceptions import (
    handle_exceptions,
)
from botocore.exceptions import ClientError
from unittest.mock import patch


class TestHandleExceptionsDecorator:
    """Test the handle_exceptions decorator."""

    @pytest.mark.asyncio
    async def test_successful_async_function(self):
        """Test decorator with successful async function execution."""

        @handle_exceptions
        async def test_func():
            return {'result': 'success'}

        result = await test_func()
        assert result == {'result': 'success'}

    @pytest.mark.asyncio
    async def test_successful_sync_function(self):
        """Test decorator with successful sync function execution."""

        @handle_exceptions
        def test_func():
            return {'result': 'sync success'}

        result = await test_func()
        assert result == {'result': 'sync success'}

    @pytest.mark.asyncio
    async def test_function_with_arguments(self):
        """Test decorator preserves function arguments."""

        @handle_exceptions
        async def test_func(arg1, arg2=None):
            return {'arg1': arg1, 'arg2': arg2}

        result = await test_func('test', arg2='value')
        assert result == {'arg1': 'test', 'arg2': 'value'}

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self):
        """Test decorator preserves function metadata."""

        @handle_exceptions
        async def test_func():
            """Test function docstring."""
            return {'result': 'success'}

        assert test_func.__name__ == 'test_func'
        assert test_func.__doc__ == 'Test function docstring.'


class TestClientErrorHandling:
    """Test ClientError exception handling."""

    @pytest.mark.asyncio
    async def test_client_error_response_format(self):
        """Test ClientError produces correct JSON response format."""
        error_code = 'AccessDenied'
        error_message = 'User is not authorized'

        @handle_exceptions
        async def test_func():
            raise ClientError(
                {'Error': {'Code': error_code, 'Message': error_message}}, 'TestOperation'
            )

        result = await test_func()
        result_dict = result  # Already a dict, not JSON string

        assert 'Client error:' in result_dict['error']
        assert result_dict['error_code'] == error_code
        assert result_dict['error_message'] == error_message
        assert result_dict['operation'] == 'test_func'

    @pytest.mark.asyncio
    @patch('awslabs.rds_control_plane_mcp_server.common.decorators.handle_exceptions.logger.error')
    async def test_client_error_logging(self, mock_log_error):
        """Test ClientError is properly logged."""

        @handle_exceptions
        async def test_func():
            raise ClientError(
                {'Error': {'Code': 'InvalidParameter', 'Message': 'Invalid value'}},
                'TestOperation',
            )

        await test_func()
        mock_log_error.assert_called_once()


class TestGeneralExceptionHandling:
    """Test general exception handling."""

    @pytest.mark.asyncio
    async def test_general_exception_response_format(self):
        """Test general exceptions produce correct JSON response format."""
        error_message = 'Unexpected runtime error'

        @handle_exceptions
        async def test_func():
            raise ValueError(error_message)

        result = await test_func()
        result_dict = result  # Already a dict, not JSON string

        assert 'Unexpected error:' in result_dict['error']
        assert result_dict['error_type'] == 'ValueError'
        assert result_dict['error_message'] == error_message
        assert result_dict['operation'] == 'test_func'

    @pytest.mark.asyncio
    @patch('awslabs.rds_control_plane_mcp_server.common.decorators.handle_exceptions.logger.exception')
    async def test_general_exception_logging(self, mock_log_exception):
        """Test general exceptions are properly logged."""

        @handle_exceptions
        async def test_func():
            raise ValueError('Test error')

        await test_func()
        mock_log_exception.assert_called_once()
