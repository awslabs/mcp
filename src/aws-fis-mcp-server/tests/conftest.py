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

"""Test fixtures for AWS FIS MCP server tests."""

# Import the server module to patch its components
import awslabs.aws_fis_mcp_server.server as server_module
import boto3
import pytest
from mcp.server.fastmcp import Context
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_aws_clients():
    """Create mock AWS clients for testing."""
    mock_aws_fis = MagicMock()
    mock_s3 = MagicMock()
    mock_resource_explorer = MagicMock()
    mock_cloudformation = MagicMock()
    mock_aws_config_client = MagicMock()

    with (
        patch.object(server_module, 'aws_fis', mock_aws_fis),
        patch.object(server_module, 's3', mock_s3),
        patch.object(server_module, 'resource_explorer', mock_resource_explorer),
        patch.object(server_module, 'cloudformation', mock_cloudformation),
        patch.object(server_module, 'aws_config_client', mock_aws_config_client),
        patch.object(server_module, 'allow_writes', True),  # Enable writes for testing
    ):
        yield {
            'aws_fis': mock_aws_fis,
            's3': mock_s3,
            'resource_explorer': mock_resource_explorer,
            'cloudformation': mock_cloudformation,
            'aws_config_client': mock_aws_config_client,
        }


@pytest.fixture
def mock_context():
    """Create a mock Context for testing."""
    mock_ctx = MagicMock(spec=Context)

    with patch.object(server_module, 'Context', mock_ctx):
        yield mock_ctx


@pytest.fixture
def mock_boto3_session():
    """Mock boto3 session for testing."""
    mock_session = MagicMock(spec=boto3.Session)

    with patch.object(boto3, 'Session', return_value=mock_session):
        yield mock_session
