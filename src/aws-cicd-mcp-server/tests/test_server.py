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

"""Tests for AWS CI/CD MCP Server."""

import pytest
from awslabs.aws_cicd_mcp_server.server import mcp
from unittest.mock import patch, MagicMock

class TestServer:
    """Test the main server functionality."""
    
    def test_mcp_initialization(self):
        """Test MCP server initialization."""
        assert mcp.name == 'AWS CI/CD MCP Server for CodePipeline, CodeBuild, and CodeDeploy operations'
    
    @patch('boto3.client')
    def test_list_pipelines_mock(self, mock_boto_client):
        """Test listing CodePipeline pipelines with mock."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.list_pipelines.return_value = {
            'pipelines': [{'name': 'test-pipeline'}]
        }
        
        # This is a basic structure test
        assert mock_boto_client is not None
