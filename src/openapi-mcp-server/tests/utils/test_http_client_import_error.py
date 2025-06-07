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

"""Tests for http_client ImportError handling and logging."""

import sys
from unittest.mock import patch, MagicMock
import pytest


def test_http_client_header_masking_debug_logging():
    """Test debug logging with header masking in HttpClientFactory."""
    from awslabs.openapi_mcp_server.utils.http_client import HttpClientFactory
    
    with patch('awslabs.openapi_mcp_server.utils.http_client.logger') as mock_logger:
        # Test with Authorization header containing Bearer token
        headers = {
            'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token',
            'Content-Type': 'application/json',
            'X-API-Key': 'secret-api-key-12345'
        }
        
        factory = HttpClientFactory()
        client = factory.create_client(base_url="https://api.example.com", headers=headers)
        
        # Verify debug logging was called with masked headers
        mock_logger.debug.assert_called()
        
        # Get the actual call arguments - should be the call with "Creating client with headers:"
        debug_calls = [call for call in mock_logger.debug.call_args_list if 'Creating client with headers:' in str(call)]
        assert len(debug_calls) > 0
        
        call_args = debug_calls[0][0][0]
        
        # Verify the log message contains masked values for Authorization header only
        assert 'Bearer eyJhbGc' in call_args  # Partial token shown
        assert 'application/json' in call_args  # Content-Type not masked
        # Note: X-API-Key is not masked in the current implementation - only Authorization header is masked


def test_http_client_header_masking_non_bearer_auth():
    """Test header masking for non-Bearer authorization headers."""
    from awslabs.openapi_mcp_server.utils.http_client import HttpClientFactory
    
    with patch('awslabs.openapi_mcp_server.utils.http_client.logger') as mock_logger:
        # Test with Basic auth header
        headers = {
            'Authorization': 'Basic dXNlcjpwYXNzd29yZA==',
            'Content-Type': 'application/json'
        }
        
        factory = HttpClientFactory()
        client = factory.create_client(base_url="https://api.example.com", headers=headers)
        
        # Verify debug logging was called
        mock_logger.debug.assert_called()
        
        # Get the actual call arguments - should be the call with "Creating client with headers:"
        debug_calls = [call for call in mock_logger.debug.call_args_list if 'Creating client with headers:' in str(call)]
        assert len(debug_calls) > 0
        
        call_args = debug_calls[0][0][0]
        
        # Verify Basic auth is completely masked
        assert '[MASKED]' in call_args
        assert 'dXNlcjpwYXNzd29yZA==' not in call_args


def test_http_client_no_sensitive_headers():
    """Test header logging when no sensitive headers are present."""
    from awslabs.openapi_mcp_server.utils.http_client import HttpClientFactory
    
    with patch('awslabs.openapi_mcp_server.utils.http_client.logger') as mock_logger:
        # Test with only non-sensitive headers
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'test-client/1.0'
        }
        
        factory = HttpClientFactory()
        client = factory.create_client(base_url="https://api.example.com", headers=headers)
        
        # Verify debug logging was called
        mock_logger.debug.assert_called()
        
        # Get the actual call arguments - should be the call with "Creating client with headers:"
        debug_calls = [call for call in mock_logger.debug.call_args_list if 'Creating client with headers:' in str(call)]
        assert len(debug_calls) > 0
        
        call_args = debug_calls[0][0][0]
        
        # Verify no masking occurred for non-sensitive headers
        assert 'application/json' in call_args
        assert 'test-client/1.0' in call_args
        assert '[MASKED]' not in call_args
