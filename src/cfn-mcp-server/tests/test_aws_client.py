# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the cfn MCP Server."""

import pytest
from awslabs.cfn_mcp_server.aws_client import get_aws_client
from awslabs.cfn_mcp_server.errors import ClientError
from unittest.mock import patch


@pytest.mark.asyncio
class TestClient:
    """Tests on the aws_client module."""

    @patch('awslabs.cfn_mcp_server.aws_client.session')
    @patch('awslabs.cfn_mcp_server.aws_client.environ')
    async def test_happy_path(self, mock_environ, mock_session):
        """Testing happy path."""
        client = {}
        mock_session.client.return_value = client

        result = get_aws_client('cloudcontrol', 'us-east-1')

        assert result == client

    @patch('awslabs.cfn_mcp_server.aws_client.session')
    @patch('awslabs.cfn_mcp_server.aws_client.environ')
    async def test_happy_path_no_region(self, mock_environ, mock_session):
        """Testing no region."""
        client = {}
        mock_session.client.return_value = client
        mock_environ.get.return_value = 'us-east-1'

        result = get_aws_client('cloudcontrol')

        assert result == client

    @patch('awslabs.cfn_mcp_server.aws_client.session')
    @patch('awslabs.cfn_mcp_server.aws_client.environ')
    async def test_expired_token(self, mock_environ, mock_session):
        """Testing token is expired."""
        mock_session.client.side_effect = Exception('ExpiredToken')
        mock_environ.get.return_value = 'us-east-1'

        with pytest.raises(ClientError):
            get_aws_client('cloudcontrol')

    @patch('awslabs.cfn_mcp_server.aws_client.session')
    @patch('awslabs.cfn_mcp_server.aws_client.environ')
    async def test_no_providers(self, mock_environ, mock_session):
        """Testing no providers given."""
        mock_session.client.side_effect = Exception('NoCredentialProviders')
        mock_environ.get.return_value = 'us-east-1'

        with pytest.raises(ClientError):
            get_aws_client('cloudcontrol')

    @patch('awslabs.cfn_mcp_server.aws_client.session')
    @patch('awslabs.cfn_mcp_server.aws_client.environ')
    async def test_other_error(self, mock_environ, mock_session):
        """Testing error."""
        mock_session.client.side_effect = Exception('UNRELATED')
        mock_environ.get.return_value = 'us-east-1'

        with pytest.raises(ClientError):
            get_aws_client('cloudcontrol')
