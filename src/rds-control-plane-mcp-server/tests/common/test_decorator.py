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

"""Tests for the decorator module in the RDS Control Plane MCP Server."""

import json
import pytest
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch

from awslabs.rds_control_plane_mcp_server.common.decorator import handle_exceptions
from awslabs.rds_control_plane_mcp_server.common.constants import ERROR_AWS_API, ERROR_UNEXPECTED


@pytest.mark.asyncio
async def test_handle_exceptions_success():
    """Test the handle_exceptions decorator with a successful function execution."""
    @handle_exceptions
    async def test_func():
        return {"result": "success"}
    
    result = await test_func()
    
    assert result == {"result": "success"}


@pytest.mark.asyncio
async def test_handle_exceptions_with_args():
    """Test the handle_exceptions decorator with function arguments."""
    @handle_exceptions
    async def test_func(arg1, arg2=None):
        return {"arg1": arg1, "arg2": arg2}
    
    result = await test_func("test", arg2="value")
    
    assert result == {"arg1": "test", "arg2": "value"}


@pytest.mark.asyncio
async def test_handle_exceptions_with_client_error():
    """Test the handle_exceptions decorator with a ClientError."""
    error_code = "AccessDenied"
    error_message = "User is not authorized"
    
    @handle_exceptions
    async def test_func():
        raise ClientError(
            {
                "Error": {
                    "Code": error_code,
                    "Message": error_message
                }
            },
            "TestOperation"
        )
    
    result = await test_func()
    
    result_dict = json.loads(result)
    assert "error" in result_dict
    assert "error_code" in result_dict
    assert "error_message" in result_dict
    assert "operation" in result_dict
    assert result_dict["error_code"] == error_code
    assert result_dict["error_message"] == error_message
    assert result_dict["operation"] == "test_func"
    assert ERROR_AWS_API.format(error_code) in result_dict["error"]


@pytest.mark.asyncio
async def test_handle_exceptions_with_general_exception():
    """Test the handle_exceptions decorator with a general exception."""
    error_message = "Unexpected runtime error"
    
    @handle_exceptions
    async def test_func():
        raise ValueError(error_message)
    
    result = await test_func()
    
    result_dict = json.loads(result)
    assert "error" in result_dict
    assert "error_type" in result_dict
    assert "error_message" in result_dict
    assert "operation" in result_dict
    assert result_dict["error_type"] == "ValueError"
    assert result_dict["error_message"] == error_message
    assert result_dict["operation"] == "test_func"
    assert ERROR_UNEXPECTED.format(error_message) in result_dict["error"]


@pytest.mark.asyncio
async def test_handle_exceptions_with_sync_function():
    """Test the handle_exceptions decorator with a synchronous function."""
    @handle_exceptions
    def sync_test_func():
        return {"result": "sync success"}
    
    result = await sync_test_func()
    
    assert result == {"result": "sync success"}


@pytest.mark.asyncio
async def test_handle_exceptions_with_sync_function_error():
    """Test the handle_exceptions decorator with a synchronous function that raises an exception."""
    error_message = "Sync function error"
    
    @handle_exceptions
    def sync_test_func():
        raise RuntimeError(error_message)
    
    result = await sync_test_func()
    
    result_dict = json.loads(result)
    assert "error" in result_dict
    assert "error_type" in result_dict
    assert result_dict["error_type"] == "RuntimeError"
    assert result_dict["error_message"] == error_message


@pytest.mark.asyncio
async def test_handle_exceptions_preserves_function_metadata():
    """Test that the handle_exceptions decorator preserves function metadata."""
    @handle_exceptions
    async def test_func():
        """Test function docstring."""
        return {"result": "success"}
    
    assert test_func.__name__ == "test_func"
    assert test_func.__doc__ == "Test function docstring."
    
    result = await test_func()
    assert result == {"result": "success"}


@pytest.mark.asyncio
@patch("loguru.logger.error")
@patch("loguru.logger.exception")
async def test_handle_exceptions_logging(mock_log_exception, mock_log_error):
    """Test that the handle_exceptions decorator properly logs errors."""
    @handle_exceptions
    async def client_error_func():
        raise ClientError(
            {
                "Error": {
                    "Code": "InvalidParameter",
                    "Message": "Invalid parameter value"
                }
            },
            "TestOperation"
        )
    
    await client_error_func()
    mock_log_error.assert_called_once()
    mock_log_exception.assert_not_called()
    mock_log_error.reset_mock()
    
    @handle_exceptions
    async def general_error_func():
        raise ValueError("Test error")
    
    await general_error_func()
    mock_log_exception.assert_called_once()
