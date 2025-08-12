# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for session management module."""

import pytest
from awslabs.ccapi_mcp_server.errors import ClientError
from awslabs.ccapi_mcp_server.impl.tools.session_management import (
    check_aws_credentials,
    check_environment_variables_impl,
    get_aws_profile_info,
    get_aws_session_info_impl,
)
from unittest.mock import MagicMock, patch


class TestSessionManagement:
    """Test session management functions."""

    def setup_method(self):
        """Set up test context."""
        from awslabs.ccapi_mcp_server.context import Context

        Context.initialize(False)

    @patch('awslabs.ccapi_mcp_server.impl.tools.session_management.get_aws_client')
    def test_check_aws_credentials_success(self, mock_client):
        """Test check_aws_credentials success path."""
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test',
            'UserId': 'AIDACKCEVSQ6C2EXAMPLE',
        }
        mock_client.return_value = mock_sts

        with patch(
            'awslabs.ccapi_mcp_server.impl.tools.session_management.environ'
        ) as mock_environ:
            mock_environ.get.side_effect = (
                lambda key, default='': {
                    'AWS_ACCESS_KEY_ID': 'AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
                    'AWS_SECRET_ACCESS_KEY': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
                    'AWS_REGION': 'us-east-1',
                    'AWS_PROFILE': 'default',
                }.get(key, default)
            )

            result = check_aws_credentials()
            assert result['valid'] is True
            assert result['account_id'] == '123456789012'
            assert result['credential_source'] == 'env'

    @patch('awslabs.ccapi_mcp_server.impl.tools.session_management.get_aws_client')
    def test_check_aws_credentials_profile(self, mock_client):
        """Test check_aws_credentials with profile."""
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test',
            'UserId': 'AIDACKCEVSQ6C2EXAMPLE',
        }
        mock_client.return_value = mock_sts

        with patch(
            'awslabs.ccapi_mcp_server.impl.tools.session_management.environ'
        ) as mock_environ:
            mock_environ.get.side_effect = lambda key, default='': {
                'AWS_REGION': 'us-east-1',
                'AWS_PROFILE': 'test-profile',
            }.get(key, default)

            result = check_aws_credentials()
            assert result['valid'] is True
            assert result['credential_source'] == 'profile'
            assert result['profile_auth_type'] == 'standard_profile'

    @patch('awslabs.ccapi_mcp_server.impl.tools.session_management.get_aws_client')
    def test_check_aws_credentials_error(self, mock_client):
        """Test check_aws_credentials with error."""
        mock_client.side_effect = Exception('AWS Error')

        result = check_aws_credentials()
        assert result['valid'] is False
        assert 'error' in result

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.session_management.check_aws_credentials')
    async def test_check_environment_variables_impl_success(self, mock_check):
        """Test check_environment_variables_impl success path."""
        mock_check.return_value = {
            'valid': True,
            'profile': 'default',
            'region': 'us-east-1',
            'environment_variables': {'AWS_PROFILE': 'default', 'AWS_REGION': 'us-east-1'},
        }

        workflow_store = {}
        result = await check_environment_variables_impl(workflow_store)

        assert result['properly_configured'] is True
        assert 'environment_token' in result
        assert len(workflow_store) == 1

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.session_management.check_aws_credentials')
    async def test_check_environment_variables_impl_invalid(self, mock_check):
        """Test check_environment_variables_impl with invalid credentials."""
        mock_check.return_value = {
            'valid': False,
            'error': 'Invalid credentials',
            'profile': '',
            'region': 'us-east-1',
            'environment_variables': {},
        }

        workflow_store = {}
        result = await check_environment_variables_impl(workflow_store)

        assert result['properly_configured'] is False
        assert 'environment_token' in result

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.session_management.check_aws_credentials')
    async def test_get_aws_session_info_impl_success(self, mock_check):
        """Test get_aws_session_info_impl success path."""
        mock_check.return_value = {
            'valid': True,
            'account_id': '123456789012',
            'region': 'us-east-1',
            'arn': 'arn:aws:iam::123456789012:user/test',
            'user_id': 'AIDACKCEVSQ6C2EXAMPLE',
            'profile': 'default',
            'credential_source': 'profile',
            'profile_auth_type': 'standard_profile',
        }

        workflow_store = {
            'env_token': {'type': 'environment', 'data': {'properly_configured': True}}
        }

        result = await get_aws_session_info_impl('env_token', workflow_store)

        assert result['credentials_valid'] is True
        assert result['account_id'] == '123456789012'
        assert 'credentials_token' in result

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.session_management.check_aws_credentials')
    async def test_get_aws_session_info_impl_with_env_credentials(self, mock_check):
        """Test get_aws_session_info_impl with environment credentials."""
        mock_check.return_value = {
            'valid': True,
            'account_id': '123456789012',
            'region': 'us-east-1',
            'arn': 'arn:aws:iam::123456789012:user/test',
            'user_id': 'AIDACKCEVSQ6C2EXAMPLE',
            'profile': '',
            'credential_source': 'env',
        }

        workflow_store = {
            'env_token': {'type': 'environment', 'data': {'properly_configured': True}}
        }

        with patch(
            'awslabs.ccapi_mcp_server.impl.tools.session_management.environ'
        ) as mock_environ:
            mock_environ.get.side_effect = (
                lambda key, default='': {
                    'AWS_ACCESS_KEY_ID': 'AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
                    'AWS_SECRET_ACCESS_KEY': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
                }.get(key, default)
            )

            result = await get_aws_session_info_impl('env_token', workflow_store)

            assert result['aws_auth_type'] == 'env'
            assert 'masked_credentials' in result

    @pytest.mark.asyncio
    async def test_get_aws_session_info_impl_invalid_token(self):
        """Test get_aws_session_info_impl with invalid token."""
        with pytest.raises(ClientError):
            await get_aws_session_info_impl('invalid', {})

    @pytest.mark.asyncio
    async def test_get_aws_session_info_impl_not_configured(self):
        """Test get_aws_session_info_impl with not configured environment."""
        workflow_store = {
            'env_token': {
                'type': 'environment',
                'data': {'properly_configured': False, 'error': 'Not configured'},
            }
        }

        with pytest.raises(ClientError):
            await get_aws_session_info_impl('env_token', workflow_store)

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.session_management.check_aws_credentials')
    async def test_get_aws_session_info_impl_invalid_credentials(self, mock_check):
        """Test get_aws_session_info_impl with invalid credentials."""
        mock_check.return_value = {'valid': False, 'error': 'Invalid credentials'}

        workflow_store = {
            'env_token': {'type': 'environment', 'data': {'properly_configured': True}}
        }

        with pytest.raises(ClientError):
            await get_aws_session_info_impl('env_token', workflow_store)

    @patch('awslabs.ccapi_mcp_server.impl.tools.session_management.get_aws_client')
    def test_get_aws_profile_info_success(self, mock_client):
        """Test get_aws_profile_info success path."""
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test',
        }
        mock_client.return_value = mock_sts

        with patch(
            'awslabs.ccapi_mcp_server.impl.tools.session_management.environ'
        ) as mock_environ:
            mock_environ.get.side_effect = lambda key, default='': {
                'AWS_PROFILE': 'test-profile',
                'AWS_REGION': 'us-east-1',
            }.get(key, default)

            result = get_aws_profile_info()
            assert result['profile'] == 'test-profile'
            assert result['account_id'] == '123456789012'
            assert result['using_env_vars'] is False

    @patch('awslabs.ccapi_mcp_server.impl.tools.session_management.get_aws_client')
    def test_get_aws_profile_info_with_env_vars(self, mock_client):
        """Test get_aws_profile_info with environment variables."""
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test',
        }
        mock_client.return_value = mock_sts

        with patch(
            'awslabs.ccapi_mcp_server.impl.tools.session_management.environ'
        ) as mock_environ:
            mock_environ.get.side_effect = (
                lambda key, default='': {
                    'AWS_ACCESS_KEY_ID': 'AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
                    'AWS_SECRET_ACCESS_KEY': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
                    'AWS_REGION': 'us-east-1',
                }.get(key, default)
            )

            result = get_aws_profile_info()
            assert result['using_env_vars'] is True

    @patch('awslabs.ccapi_mcp_server.impl.tools.session_management.get_aws_client')
    def test_get_aws_profile_info_error(self, mock_client):
        """Test get_aws_profile_info with error."""
        mock_client.side_effect = Exception('AWS Error')

        result = get_aws_profile_info()
        assert 'error' in result
