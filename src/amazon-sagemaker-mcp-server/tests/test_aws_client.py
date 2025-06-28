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

"""Tests for AWS client utilities."""

import os
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.config import Config
from botocore.exceptions import NoCredentialsError

from awslabs.amazon_sagemaker_mcp_server.utils.aws_client import (
    get_aws_config,
    get_session,
    get_sagemaker_client,
    get_sagemaker_runtime_client,
    validate_aws_credentials,
    get_current_region,
    get_account_id,
)


class TestAWSConfig:
    """Test AWS configuration utilities."""

    def test_get_aws_config(self):
        """Test AWS configuration creation."""
        config = get_aws_config()
        
        assert isinstance(config, Config)
        assert config.retries['max_attempts'] == 3
        assert config.retries['mode'] == 'adaptive'
        assert config.max_pool_connections == 50
        assert 'MCP/SagemakerServer' in config.user_agent_extra


class TestSessionCreation:
    """Test AWS session creation."""

    def test_get_session_with_explicit_credentials(self):
        """Test session creation with explicit credentials."""
        os.environ['AWS_ACCESS_KEY_ID'] = 'test-key'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'test-secret'
        os.environ['AWS_SESSION_TOKEN'] = 'test-token'
        os.environ['AWS_REGION'] = 'us-west-2'
        
        with patch('boto3.Session') as mock_session:
            get_session()
            mock_session.assert_called_once_with(
                aws_access_key_id='test-key',
                aws_secret_access_key='test-secret',
                aws_session_token='test-token',
                region_name='us-west-2'
            )

    def test_get_session_with_profile(self):
        """Test session creation with AWS profile."""
        # Clear explicit credentials first
        for var in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']:
            if var in os.environ:
                del os.environ[var]
        
        os.environ['AWS_PROFILE'] = 'test-profile'
        os.environ['AWS_REGION'] = 'eu-west-1'
        
        with patch('boto3.Session') as mock_session:
            get_session()
            mock_session.assert_called_once_with(
                profile_name='test-profile',
                region_name='eu-west-1'
            )

    def test_get_session_default(self):
        """Test default session creation."""
        # Clear all AWS environment variables
        for var in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_PROFILE']:
            if var in os.environ:
                del os.environ[var]
        
        with patch('boto3.Session') as mock_session:
            get_session()
            mock_session.assert_called_once_with(region_name='us-east-1')

    def test_get_session_with_custom_region(self):
        """Test session creation with custom region."""
        # Clear all AWS environment variables except region
        for var in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_PROFILE']:
            if var in os.environ:
                del os.environ[var]
        
        os.environ['AWS_REGION'] = 'ap-southeast-1'
        
        with patch('boto3.Session') as mock_session:
            get_session()
            mock_session.assert_called_once_with(region_name='ap-southeast-1')


class TestClientCreation:
    """Test AWS client creation."""

    @patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_session')
    @patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_aws_config')
    def test_get_sagemaker_client(self, mock_config, mock_session):
        """Test SageMaker client creation."""
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance
        
        get_sagemaker_client()
        
        mock_session_instance.client.assert_called_once_with('sagemaker', config=mock_config_instance)

    @patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_session')
    @patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_aws_config')
    def test_get_sagemaker_runtime_client(self, mock_config, mock_session):
        """Test SageMaker Runtime client creation."""
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance
        
        get_sagemaker_runtime_client()
        
        mock_session_instance.client.assert_called_once_with('sagemaker-runtime', config=mock_config_instance)


class TestCredentialValidation:
    """Test AWS credential validation."""

    @patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_session')
    @patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_aws_config')
    def test_validate_aws_credentials_success(self, mock_config, mock_session):
        """Test successful credential validation."""
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_sts_client = MagicMock()
        mock_session_instance.client.return_value = mock_sts_client
        mock_sts_client.get_caller_identity.return_value = {'Account': '123456789012'}
        
        result = validate_aws_credentials()
        
        assert result is True
        mock_sts_client.get_caller_identity.assert_called_once()

    @patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_session')
    @patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_aws_config')
    def test_validate_aws_credentials_failure(self, mock_config, mock_session):
        """Test failed credential validation."""
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_sts_client = MagicMock()
        mock_session_instance.client.return_value = mock_sts_client
        mock_sts_client.get_caller_identity.side_effect = NoCredentialsError()
        
        result = validate_aws_credentials()
        
        assert result is False


class TestUtilityFunctions:
    """Test utility functions."""

    @patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_session')
    def test_get_current_region(self, mock_session):
        """Test getting current region."""
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = 'us-west-2'
        mock_session.return_value = mock_session_instance
        
        region = get_current_region()
        
        assert region == 'us-west-2'

    @patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_session')
    def test_get_current_region_default(self, mock_session):
        """Test getting current region with default fallback."""
        mock_session_instance = MagicMock()
        mock_session_instance.region_name = None
        mock_session.return_value = mock_session_instance
        
        region = get_current_region()
        
        assert region == 'us-east-1'

    @patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_session')
    @patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_aws_config')
    def test_get_account_id_success(self, mock_config, mock_session):
        """Test successful account ID retrieval."""
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_sts_client = MagicMock()
        mock_session_instance.client.return_value = mock_sts_client
        mock_sts_client.get_caller_identity.return_value = {'Account': '123456789012'}
        
        account_id = get_account_id()
        
        assert account_id == '123456789012'

    @patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_session')
    @patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_aws_config')
    def test_get_account_id_failure(self, mock_config, mock_session):
        """Test failed account ID retrieval."""
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_sts_client = MagicMock()
        mock_session_instance.client.return_value = mock_sts_client
        mock_sts_client.get_caller_identity.side_effect = Exception('API Error')
        
        account_id = get_account_id()
        
        assert account_id is None


class TestIntegration:
    """Integration tests for AWS client utilities."""

    def test_client_creation_integration(self):
        """Test that client creation functions work together."""
        with patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_session') as mock_session:
            with patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_aws_config') as mock_config:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_config_instance = MagicMock()
                mock_config.return_value = mock_config_instance
                
                # Test available client creation functions
                clients = [
                    get_sagemaker_client,
                    get_sagemaker_runtime_client,
                ]
                
                for client_func in clients:
                    client_func()
                
                # Verify session was called for each client
                assert mock_session.call_count == len(clients)
                assert mock_config.call_count == len(clients)


class TestErrorHandling:
    """Test error handling in AWS client utilities."""

    def test_session_creation_with_missing_credentials(self):
        """Test session creation when some credentials are missing."""
        # Set only access key, missing secret key
        os.environ['AWS_ACCESS_KEY_ID'] = 'test-key'
        if 'AWS_SECRET_ACCESS_KEY' in os.environ:
            del os.environ['AWS_SECRET_ACCESS_KEY']
        
        with patch('boto3.Session') as mock_session:
            get_session()
            # Should fall back to default session since credentials are incomplete
            mock_session.assert_called_once_with(region_name='us-east-1')

    def test_validate_credentials_with_generic_exception(self):
        """Test credential validation with generic exception."""
        with patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_session') as mock_session:
            with patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_aws_config'):
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_sts_client = MagicMock()
                mock_session_instance.client.return_value = mock_sts_client
                mock_sts_client.get_caller_identity.side_effect = Exception('Generic error')
                
                result = validate_aws_credentials()
                assert result is False
