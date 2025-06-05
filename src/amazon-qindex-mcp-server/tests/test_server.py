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

"""Tests for the amazon-qindex MCP Server."""

import pytest
from awslabs.amazon_qindex_mcp_server.server import (
    authorize_qindex,
    create_token_with_iam,
    mcp,
)


class TestMCPServer:
    """Tests for the MCP server configuration."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mcp = mcp

    def test_server_initialization(self):
        """Test MCP server initialization."""
        assert mcp.name == 'awslabs.amazon-qindex-mcp-server'
        assert 'pydantic' in mcp.dependencies
        assert 'loguru' in mcp.dependencies
        assert 'boto3' in mcp.dependencies

    @pytest.mark.asyncio
    async def test_tool_registration(self):
        """Test MCP tool registration."""
        # Test that the tools are registered with the MCP server
        tools = await mcp.list_tools()

        # Check for all required tools using the same tools list
        assert any(tool.name == 'AuthorizeQIndex' for tool in tools)
        assert any(tool.name == 'CreateTokenWithIAM' for tool in tools)
        assert any(tool.name == 'AssumeRoleWithIdentityContext' for tool in tools)
        assert any(tool.name == 'SearchRelevantContent' for tool in tools)


class TestAuthorizeQIndex:
    """Tests for the authorize_qindex MCP tool."""

    TEST_DATA = {
        'idc_region': 'us-west-2',
        'isv_redirect_url': 'https://example.com/callback',
        'oauth_state': 'random_state_123',
        'idc_application_arn': 'arn:aws:idc::123456789012:application/abcd1234',
    }

    @pytest.mark.asyncio
    async def test_authorize_qindex_success(self):
        """Test successful authorize call."""
        expected_url = (
            f'https://oidc.{self.TEST_DATA["idc_region"]}.amazonaws.com/authorize'
            f'?response_type=code'
            f'&redirect_uri={self.TEST_DATA["isv_redirect_url"]}'
            f'&state={self.TEST_DATA["oauth_state"]}'
            f'&client_id={self.TEST_DATA["idc_application_arn"]}'
        )

        with pytest.raises(ValueError) as exc_info:
            await authorize_qindex(
                idc_region=self.TEST_DATA['idc_region'],
                isv_redirect_url=self.TEST_DATA['isv_redirect_url'],
                oauth_state=self.TEST_DATA['oauth_state'],
                idc_application_arn=self.TEST_DATA['idc_application_arn'],
            )

        assert expected_url in str(exc_info.value)


class TestCreateTokenWithIAM:
    """Tests for the create_token_with_iam MCP tool."""

    TEST_DATA = {
        'idc_application_arn': 'arn:aws:idc::123456789012:application/abcd1234',
        'redirect_uri': 'https://example.com/callback',
        'code': 'test_auth_code',
        'idc_region': 'us-west-2',
        'role_arn': 'arn:aws:iam::123456789012:role/test-role',
    }

    MOCK_TOKEN_RESPONSE = {
        'accessToken': 'test_access_token',
        'tokenType': 'Bearer',
        'expiresIn': 3600,
        'refreshToken': 'test_refresh_token',
        'idToken': 'test_id_token',
    }

    @pytest.mark.asyncio
    async def test_create_token_with_iam_success(self, mocker):
        """Test successful token creation with IAM."""
        # Mock boto3 session and clients
        mock_session = mocker.Mock()
        mock_sts_client = mocker.Mock()
        mock_sso_client = mocker.Mock()

        # Mock assume_role response
        mock_assume_role_response = {
            'Credentials': {
                'AccessKeyId': 'test_access_key',
                'SecretAccessKey': 'test_secret_key',  # pragma: allowlist secret
                'SessionToken': 'test_session_token',
            }
        }

        # Set up mock returns
        mock_session.client.side_effect = [mock_sts_client, mock_sso_client]
        mock_sts_client.assume_role.return_value = mock_assume_role_response
        mock_sso_client.create_token_with_iam.return_value = self.MOCK_TOKEN_RESPONSE

        # Mock boto3.Session
        mocker.patch('boto3.Session', return_value=mock_session)

        response = await create_token_with_iam(
            idc_application_arn=self.TEST_DATA['idc_application_arn'],
            redirect_uri=self.TEST_DATA['redirect_uri'],
            code=self.TEST_DATA['code'],
            idc_region=self.TEST_DATA['idc_region'],
            role_arn=self.TEST_DATA['role_arn'],
        )

        # Verify the response
        assert response == self.MOCK_TOKEN_RESPONSE

        # Verify assume_role was called correctly
        mock_sts_client.assume_role.assert_called_once_with(
            RoleArn=self.TEST_DATA['role_arn'],
            RoleSessionName='automated-session',
            Tags=[{'Key': 'qbusiness-dataaccessor:ExternalId', 'Value': 'Test-Tenant'}],
        )

        # Verify create_token_with_iam was called correctly
        mock_sso_client.create_token_with_iam.assert_called_once_with(
            clientId=self.TEST_DATA['idc_application_arn'],
            redirectUri=self.TEST_DATA['redirect_uri'],
            grantType='authorization_code',
            code=self.TEST_DATA['code'],
        )

    @pytest.mark.asyncio
    async def test_create_token_with_iam_error(self, mocker):
        """Test error handling in token creation."""
        # Mock boto3 session to raise an exception
        mock_session = mocker.Mock()
        mock_session.client.side_effect = Exception('AWS Error')
        mocker.patch('boto3.Session', return_value=mock_session)

        with pytest.raises(ValueError) as exc_info:
            await create_token_with_iam(**self.TEST_DATA)

        assert 'AWS Error' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_token_with_iam_parameter_validation(self):
        """Test parameter validation."""
        # Test with missing parameters
        with pytest.raises(TypeError):
            await create_token_with_iam()

        # Test with empty strings
        with pytest.raises(ValueError):
            await create_token_with_iam(
                idc_application_arn='', redirect_uri='', code='', idc_region='', role_arn=''
            )
