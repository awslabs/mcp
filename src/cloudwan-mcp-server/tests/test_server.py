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

"""Tests for CloudWAN MCP server."""

import json
import pytest
from unittest.mock import Mock, patch

from awslabs.cloudwan_mcp_server.server import (
    sanitize_error_message,
    handle_aws_error,
    safe_json_dumps,
    get_error_status_code,
)


class TestErrorHandling:
    """Test error handling utilities."""
    
    def test_sanitize_error_message(self):
        """Test sanitization of sensitive data."""
        # Test IP address sanitization
        assert sanitize_error_message("Error at 192.168.1.1") == "Error at [IP_REDACTED]"
        
        # Test AWS ARN sanitization
        arn = "arn:aws:s3:::123456789012:bucket/key"
        assert "[ARN_REDACTED]" in sanitize_error_message(arn)
        
        # Test access key sanitization
        assert sanitize_error_message("AccessKey=AKIAIOSFODNN7EXAMPLE") == "[ACCESS_KEY_REDACTED]"
    
    def test_get_error_status_code(self):
        """Test HTTP status code mapping."""
        from botocore.exceptions import ClientError
        
        # Test access denied
        error = ClientError(
            {"Error": {"Code": "AccessDenied"}},
            "TestOperation"
        )
        assert get_error_status_code(error) == 403
        
        # Test validation error
        error = ClientError(
            {"Error": {"Code": "ValidationException"}},
            "TestOperation"
        )
        assert get_error_status_code(error) == 400
        
        # Test ValueError
        assert get_error_status_code(ValueError("test")) == 400
        
        # Test generic exception
        assert get_error_status_code(Exception("test")) == 500
    
    def test_handle_aws_error(self):
        """Test AWS error handling."""
        from botocore.exceptions import ClientError
        
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "TestOperation"
        )
        
        result = handle_aws_error(error, "test_operation")
        parsed = json.loads(result)
        
        assert parsed["success"] is False
        assert "test_operation failed" in parsed["error"]
        assert parsed["error_code"] == "AccessDenied"
        assert parsed["http_status_code"] == 403
    
    def test_safe_json_dumps(self):
        """Test safe JSON serialization."""
        from datetime import datetime
        
        data = {
            "timestamp": datetime(2025, 1, 1, 0, 0, 0),
            "string": "test",
            "number": 42
        }
        
        result = safe_json_dumps(data)
        parsed = json.loads(result)
        
        assert parsed["timestamp"] == "2025-01-01T00:00:00"
        assert parsed["string"] == "test"
        assert parsed["number"] == 42


class TestServerInitialization:
    """Test server initialization."""
    
    @patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"})
    def test_aws_config_initialization(self):
        """Test AWS config initialization."""
        from awslabs.cloudwan_mcp_server.server import aws_config
        
        assert aws_config.default_region == "us-east-1"
        assert aws_config.profile is None or isinstance(aws_config.profile, str)