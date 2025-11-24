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

"""Tests for deployment tool adapter."""

import json
import pytest
from unittest.mock import patch, MagicMock
from awslabs.aws_iac_mcp_server.tools.deployment_tools import troubleshoot_deployment


class TestDeploymentTools:
    """Test deployment tool adapter."""

    def test_troubleshoot_deployment_invalid_input(self):
        """Test deployment tool with invalid input (empty stack name)."""
        result = troubleshoot_deployment("", "us-east-1")
        
        # Result should be a string
        assert isinstance(result, str)
        
        # Should contain error message
        assert 'Invalid request' in result or 'error' in result.lower()
        
    def test_troubleshoot_deployment_valid_input_structure(self):
        """Test deployment tool returns properly structured response."""
        # Mock the boto3 client to avoid actual AWS calls
        with patch('awslabs.aws_iac_mcp_server.services.deployment_troubleshooter.boto3.client'):
            result = troubleshoot_deployment("test-stack", "us-east-1")
            
            # Result should be a string
            assert isinstance(result, str)
            
            # Should contain tool_response tags
            assert '<tool_response>' in result
            assert '</tool_response>' in result
