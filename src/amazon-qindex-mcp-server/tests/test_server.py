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
    AttributeFilter,
    ContentSource,
    RetrieverContentSource,
    assume_role_with_identity_context,
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
    async def test_create_token_with_iam_parameter_validation(self, mocker):
        """Test parameter validation."""
        # Mock boto3 session and clients
        mock_session = mocker.Mock()
        mock_sts_client = mocker.Mock()
        mock_sso_client = mocker.Mock()

        # Set up mock returns
        mock_session.client.side_effect = [mock_sts_client, mock_sso_client]

        # Configure mock to raise ValueError for empty parameters
        mock_sso_client.create_token_with_iam.side_effect = ValueError('Invalid parameters')

        # Mock boto3.Session
        mocker.patch('boto3.Session', return_value=mock_session)

        # Test with empty strings
        with pytest.raises(ValueError):
            await create_token_with_iam(
                idc_application_arn='', redirect_uri='', code='', idc_region='', role_arn=''
            )


class TestSearchRelevantContent:
    """Tests for the SearchRelevantContent functionality."""

    @pytest.mark.asyncio
    async def test_search_relevant_content_success(self, mocker):
        """Test successful content search."""
        # Create proper Pydantic model instances
        content_source = ContentSource(
            retriever=RetrieverContentSource(retrieverId='test-retriever')
        )
        attribute_filter = AttributeFilter(andAllFilters=[])
        test_data = {
            'application_id': 'test-app-123',
            'query_text': 'test query',
            'attribute_filter': attribute_filter,  # Pydantic model instance
            'content_source': content_source,  # Pydantic model instance
            'max_results': 50,
            'next_token': 'next-page-token',
            'qbuiness_region': 'us-east-1',
            'aws_access_key_id': 'test-key-id',
            'aws_secret_access_key': 'test-secret-key',  # pragma: allowlist secret
            'aws_session_token': 'test-session-token',
        }
        # Mock QBusinessClient
        mock_client = mocker.Mock()
        mock_response = {
            'nextToken': 'next-token',
            'relevantContent': [
                {
                    'content': 'test content',
                    'documentId': 'doc-123',
                    'documentTitle': 'Test Document',
                }
            ],
        }
        mock_client.search_relevant_content.return_value = mock_response
        # Mock the QBusinessClient constructor
        mocker.patch(
            'awslabs.amazon_qindex_mcp_server.server.QBusinessClient', return_value=mock_client
        )
        # Call the tool function directly
        from awslabs.amazon_qindex_mcp_server.server import search_relevant_content

        response = await search_relevant_content(**test_data)
        assert response == mock_response
        mock_client.search_relevant_content.assert_called_once()


class TestServerErrorHandling:
    """Tests for server error handling scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_parameters(self):
        """Test handling of invalid parameters."""
        from awslabs.amazon_qindex_mcp_server.server import search_relevant_content

        with pytest.raises(ValueError):
            await search_relevant_content(
                application_id=None, query_text='test', qbuiness_region='us-east-1'
            )

    @pytest.mark.asyncio
    async def test_missing_credentials(self, mocker):
        """Test handling of missing AWS credentials."""
        from awslabs.amazon_qindex_mcp_server.server import search_relevant_content

        # Mock QBusinessClient to prevent actual AWS calls
        mock_client = mocker.Mock()
        mocker.patch(
            'awslabs.amazon_qindex_mcp_server.server.QBusinessClient', return_value=mock_client
        )

        # Create a mock request without credentials
        with pytest.raises(ValueError) as exc_info:
            await search_relevant_content(
                application_id='test-app',
                query_text='test',
                qbuiness_region='us-east-1',
                aws_access_key_id=None,
                aws_secret_access_key=None,
                aws_session_token=None,
            )

        assert 'Missing AWS credentials' in str(exc_info.value)


class TestClientConfiguration:
    """Tests for client configuration and initialization."""

    def test_context_initialization(self):
        """Test context initialization."""
        context = mcp.get_context()
        assert context is not None

    @pytest.mark.asyncio
    async def test_context_handling(self, mocker):
        """Test context handling."""
        mock_session = mocker.Mock()
        mocker.patch('boto3.Session', return_value=mock_session)
        context = mcp.get_context()
        assert context is not None

    def test_context_error_handling(self):
        """Test context error handling."""
        context = mcp.get_context()
        assert context is not None


class TestAssumeRoleWithIdentityContext:
    """Tests for the assume_role_with_identity_context MCP tool."""

    TEST_DATA = {
        'role_arn': 'arn:aws:iam::123456789012:role/test-role',
        'identity_context': 'test-context',
        'idc_region': 'us-west-2',
        'role_session_name': 'test-session',
    }

    @pytest.mark.asyncio
    async def test_assume_role_with_identity_context_success(self, mocker):
        """Test successful role assumption with identity context."""
        mock_session = mocker.Mock()
        mock_sts_client = mocker.Mock()

        mock_assume_role_response = {
            'Credentials': {
                'AccessKeyId': 'test_access_key',
                'SecretAccessKey': 'test_secret_key',  # pragma: allowlist secret
                'SessionToken': 'test_session_token',
                'Expiration': '2025-06-09T00:00:00Z',
            },
            'AssumedRoleUser': {'AssumedRoleId': 'test_role_id', 'Arn': 'test_role_arn'},
        }

        mock_session.client.return_value = mock_sts_client
        mock_sts_client.assume_role.return_value = mock_assume_role_response
        mocker.patch('boto3.Session', return_value=mock_session)

        response = await assume_role_with_identity_context(**self.TEST_DATA)

        assert response == mock_assume_role_response
        mock_sts_client.assume_role.assert_called_once_with(
            RoleArn=self.TEST_DATA['role_arn'],
            RoleSessionName=self.TEST_DATA['role_session_name'],
            ProvidedContexts=[
                {
                    'ProviderArn': 'arn:aws:iam::aws:contextProvider/IdentityCenter',
                    'ContextAssertion': self.TEST_DATA['identity_context'],
                }
            ],
            Tags=[{'Key': 'qbusiness-dataaccessor:ExternalId', 'Value': 'Test-Tenant'}],
        )

    @pytest.mark.asyncio
    async def test_assume_role_with_identity_context_error(self, mocker):
        """Test error handling in role assumption."""
        mock_session = mocker.Mock()
        mock_session.client.side_effect = Exception('AWS Error')
        mocker.patch('boto3.Session', return_value=mock_session)

        with pytest.raises(ValueError) as exc_info:
            await assume_role_with_identity_context(**self.TEST_DATA)
        assert 'AWS Error' in str(exc_info.value)


class TestMainFunction:
    """Tests for the main() function."""

    def test_main(self, mocker):
        """Test main function."""
        mock_mcp = mocker.Mock()
        mocker.patch('awslabs.amazon_qindex_mcp_server.server.mcp', mock_mcp)

        from awslabs.amazon_qindex_mcp_server.server import main

        main()

        mock_mcp.run.assert_called_once_with()
