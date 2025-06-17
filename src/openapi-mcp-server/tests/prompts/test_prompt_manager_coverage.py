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

"""Tests to improve coverage for prompt_manager.py."""

import pytest
from unittest.mock import Mock, patch


@pytest.mark.asyncio
async def test_generate_prompts_invalid_http_method():
    """Test that invalid HTTP methods are skipped during prompt generation."""
    from awslabs.openapi_mcp_server.prompts.prompt_manager import MCPPromptManager

    # Mock server and OpenAPI spec with invalid HTTP method
    mock_server = Mock()
    api_name = 'test_api'
    openapi_spec = {
        'paths': {
            '/test': {
                'trace': {  # Invalid HTTP method (not in allowed list)
                    'operationId': 'traceTest',
                    'summary': 'Trace test endpoint',
                },
                'get': {  # Valid HTTP method
                    'operationId': 'getTest',
                    'summary': 'Get test endpoint',
                },
            }
        }
    }

    with patch(
        'awslabs.openapi_mcp_server.prompts.prompt_manager.create_operation_prompt'
    ) as mock_create:
        mock_create.return_value = True

        manager = MCPPromptManager()
        await manager.generate_prompts(mock_server, api_name, openapi_spec)

        # Should only be called once for the valid 'get' method, not for 'trace'
        assert mock_create.call_count == 1

        # Verify it was called with the 'get' operation
        call_args = mock_create.call_args[1]
        assert call_args['method'] == 'get'
        assert call_args['operation_id'] == 'getTest'


@pytest.mark.asyncio
async def test_generate_prompts_missing_operation_id():
    """Test that operations without operationId are skipped."""
    from awslabs.openapi_mcp_server.prompts.prompt_manager import MCPPromptManager

    # Mock server and OpenAPI spec with missing operationId
    mock_server = Mock()
    api_name = 'test_api'
    openapi_spec = {
        'paths': {
            '/test': {
                'get': {
                    # Missing operationId
                    'summary': 'Get test endpoint without operationId'
                },
                'post': {
                    'operationId': 'postTest',  # Has operationId
                    'summary': 'Post test endpoint',
                },
            }
        }
    }

    with patch(
        'awslabs.openapi_mcp_server.prompts.prompt_manager.create_operation_prompt'
    ) as mock_create:
        mock_create.return_value = True

        manager = MCPPromptManager()
        await manager.generate_prompts(mock_server, api_name, openapi_spec)

        # Should only be called once for the operation with operationId
        assert mock_create.call_count == 1

        # Verify it was called with the 'post' operation that has operationId
        call_args = mock_create.call_args[1]
        assert call_args['method'] == 'post'
        assert call_args['operation_id'] == 'postTest'


def test_register_api_resource_handler_exception_handling():
    """Test exception handling in register_api_resource_handler."""
    from awslabs.openapi_mcp_server.prompts.prompt_manager import MCPPromptManager

    # Mock server that raises exception during registration
    mock_server = Mock()
    mock_server.register_resource_handler.side_effect = Exception('Registration failed')

    api_name = 'test_api'
    mock_client = Mock()

    with patch('awslabs.openapi_mcp_server.prompts.prompt_manager.logger') as mock_logger:
        manager = MCPPromptManager()
        # This should not raise an exception, but should log a warning
        manager.register_api_resource_handler(mock_server, api_name, mock_client)

        # Verify the warning was logged
        mock_logger.warning.assert_called_with(
            'Failed to register resource handler: Registration failed'
        )


def test_register_api_resource_handler_no_server():
    """Test register_api_resource_handler when server is None."""
    from awslabs.openapi_mcp_server.prompts.prompt_manager import MCPPromptManager

    api_name = 'test_api'
    mock_client = Mock()

    with patch('awslabs.openapi_mcp_server.prompts.prompt_manager.logger') as mock_logger:
        manager = MCPPromptManager()
        # Call with None server
        manager.register_api_resource_handler(None, api_name, mock_client)

        # Should log debug message about storing locally
        resource_uri = f'api://{api_name}/'
        mock_logger.debug.assert_called_with(f'Stored resource handler locally for {resource_uri}')


def test_register_api_resource_handler_successful_registration():
    """Test successful resource handler registration with debug logging."""
    from awslabs.openapi_mcp_server.prompts.prompt_manager import MCPPromptManager

    # Mock server that succeeds
    mock_server = Mock()
    mock_server.register_resource_handler.return_value = None  # Success

    api_name = 'test_api'
    mock_client = Mock()

    with patch('awslabs.openapi_mcp_server.prompts.prompt_manager.logger') as mock_logger:
        manager = MCPPromptManager()
        manager.register_api_resource_handler(mock_server, api_name, mock_client)

        # Verify successful registration was logged
        resource_uri = f'api://{api_name}/'
        mock_logger.debug.assert_called_with(f'Registered resource handler for {resource_uri}')

        # Verify the handler was actually registered
        mock_server.register_resource_handler.assert_called_once()
