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

"""Unit tests for AWS Client Manager.

This module contains comprehensive tests for the AWSClientManager class,
including credential validation, client creation, error handling, and
session management functionality.
"""

import os
import pytest
from awslabs.amazon_translate_mcp_server.aws_client import AWSClientManager
from awslabs.amazon_translate_mcp_server.exceptions import (
    AuthenticationError,
    ServiceUnavailableError,
)
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    NoCredentialsError,
    PartialCredentialsError,
    ProfileNotFound,
)
from unittest.mock import Mock, patch


class TestAWSClientManager:
    """Test cases for AWSClientManager class."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock boto3 session."""
        with patch('awslabs.amazon_translate_mcp_server.aws_client.boto3.Session') as mock:
            session_instance = Mock()
            session_instance.region_name = 'us-east-1'
            mock.return_value = session_instance
            yield session_instance

    @pytest.fixture
    def mock_sts_client(self):
        """Create a mock STS client for credential validation."""
        client = Mock()
        client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test-user',
            'UserId': 'AIDACKCEVSQ6C2EXAMPLE',
        }
        return client

    @pytest.fixture
    def clean_env(self):
        """Clean environment variables before each test."""
        env_vars = [
            'AWS_REGION',
            'AWS_DEFAULT_REGION',
            'AWS_PROFILE',
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'AWS_SESSION_TOKEN',
        ]
        original_values = {}

        for var in env_vars:
            original_values[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]

        yield

        # Restore original values
        for var, value in original_values.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]

    def test_init_with_explicit_parameters(self, mock_session, mock_sts_client, clean_env):
        """Test initialization with explicit parameters."""
        mock_session.client.return_value = mock_sts_client

        manager = AWSClientManager(
            region_name='us-west-2',
            profile_name='test-profile',
            aws_access_key_id='AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
            aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
            aws_session_token='test-session-token-example',  # pragma: allowlist secret
            max_pool_connections=25,
            retries=5,
            timeout=30,
        )

        assert manager._region_name == 'us-west-2'
        assert manager._profile_name == 'test-profile'
        assert manager._aws_access_key_id == 'AKIAIOSFODNN7EXAMPLE'
        assert (
            manager._aws_secret_access_key == 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        )  # pragma: allowlist secret
        assert manager._aws_session_token == 'test-session-token-example'

        # Verify STS call was made for credential validation
        mock_sts_client.get_caller_identity.assert_called_once()

    def test_init_with_environment_variables(self, mock_session, mock_sts_client, clean_env):
        """Test initialization with environment variables."""
        os.environ['AWS_REGION'] = 'eu-west-1'
        os.environ['AWS_PROFILE'] = 'env-profile'
        os.environ['AWS_ACCESS_KEY_ID'] = 'AKIAIOSFODNN7EXAMPLE'  # pragma: allowlist secret
        os.environ['AWS_SECRET_ACCESS_KEY'] = (
            'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'  # pragma: allowlist secret
        )
        os.environ['AWS_SESSION_TOKEN'] = 'test-session-token-example'  # pragma: allowlist secret

        mock_session.client.return_value = mock_sts_client

        manager = AWSClientManager()

        assert manager._region_name == 'eu-west-1'
        assert manager._profile_name == 'env-profile'
        assert manager._aws_access_key_id == 'AKIAIOSFODNN7EXAMPLE'
        assert (
            manager._aws_secret_access_key == 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        )  # pragma: allowlist secret
        assert manager._aws_session_token == 'test-session-token-example'

    def test_init_with_aws_default_region(self, mock_session, mock_sts_client, clean_env):
        """Test initialization with AWS_DEFAULT_REGION fallback."""
        os.environ['AWS_DEFAULT_REGION'] = 'ap-southeast-1'

        mock_session.client.return_value = mock_sts_client

        manager = AWSClientManager()

        assert manager._region_name == 'ap-southeast-1'

    def test_init_no_credentials_error(self, clean_env):
        """Test initialization failure with no credentials."""
        with patch('awslabs.amazon_translate_mcp_server.aws_client.boto3.Session') as mock_session:
            mock_session.side_effect = NoCredentialsError()

            with pytest.raises(AuthenticationError) as exc_info:
                AWSClientManager()

            assert 'AWS credentials not found' in str(exc_info.value)
            assert exc_info.value.error_code == 'AUTH_ERROR'

    def test_init_partial_credentials_error(self, clean_env):
        """Test initialization failure with partial credentials."""
        with patch('awslabs.amazon_translate_mcp_server.aws_client.boto3.Session') as mock_session:
            mock_session.side_effect = PartialCredentialsError(
                provider='env', cred_var='AWS_SECRET_ACCESS_KEY'
            )

            with pytest.raises(AuthenticationError) as exc_info:
                AWSClientManager()

            assert 'AWS credentials not found or incomplete' in str(exc_info.value)

    def test_init_profile_not_found_error(self, clean_env):
        """Test initialization failure with profile not found."""
        with patch('awslabs.amazon_translate_mcp_server.aws_client.boto3.Session') as mock_session:
            mock_session.side_effect = ProfileNotFound(profile='nonexistent-profile')

            with pytest.raises(AuthenticationError) as exc_info:
                AWSClientManager(profile_name='nonexistent-profile')

            assert "AWS profile 'nonexistent-profile' not found" in str(exc_info.value)

    def test_credential_validation_success(self, mock_session, mock_sts_client, clean_env):
        """Test successful credential validation."""
        mock_session.client.return_value = mock_sts_client

        AWSClientManager()

        # Validation should have been called during initialization
        mock_sts_client.get_caller_identity.assert_called_once()

    def test_credential_validation_access_denied(self, mock_session, clean_env):
        """Test credential validation with access denied error."""
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='GetCallerIdentity',
        )
        mock_session.client.return_value = mock_sts_client

        with pytest.raises(AuthenticationError) as exc_info:
            AWSClientManager()

        assert 'Invalid AWS credentials' in str(exc_info.value)
        assert exc_info.value.details['error_code'] == 'AccessDenied'

    def test_credential_validation_signature_error(self, mock_session, clean_env):
        """Test credential validation with signature error."""
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'SignatureDoesNotMatch', 'Message': 'Invalid signature'}
            },
            operation_name='GetCallerIdentity',
        )
        mock_session.client.return_value = mock_sts_client

        with pytest.raises(AuthenticationError) as exc_info:
            AWSClientManager()

        assert 'Invalid AWS credentials' in str(exc_info.value)
        assert exc_info.value.details['error_code'] == 'SignatureDoesNotMatch'

    def test_get_translate_client_success(self, mock_session, mock_sts_client, clean_env):
        """Test successful creation of Translate client."""
        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = {'Languages': []}

        mock_session.client.side_effect = [mock_sts_client, mock_translate_client]

        manager = AWSClientManager()
        client = manager.get_translate_client()

        assert client == mock_translate_client
        mock_translate_client.list_languages.assert_called_once_with(
            DisplayLanguageCode='en', MaxResults=1
        )

    def test_get_s3_client_success(self, mock_session, mock_sts_client, clean_env):
        """Test successful creation of S3 client."""
        mock_s3_client = Mock()
        mock_s3_client.list_buckets.return_value = {'Buckets': []}

        mock_session.client.side_effect = [mock_sts_client, mock_s3_client]

        manager = AWSClientManager()
        client = manager.get_s3_client()

        assert client == mock_s3_client
        mock_s3_client.list_buckets.assert_called_once()

    def test_get_cloudwatch_client_success(self, mock_session, mock_sts_client, clean_env):
        """Test successful creation of CloudWatch client."""
        mock_cw_client = Mock()
        mock_cw_client.list_metrics.return_value = {'Metrics': []}

        mock_session.client.side_effect = [mock_sts_client, mock_cw_client]

        manager = AWSClientManager()
        client = manager.get_cloudwatch_client()

        assert client == mock_cw_client
        mock_cw_client.list_metrics.assert_called_once_with()

    def test_client_caching(self, mock_session, mock_sts_client, clean_env):
        """Test that clients are cached properly."""
        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = {'Languages': []}

        mock_session.client.side_effect = [mock_sts_client, mock_translate_client]

        manager = AWSClientManager()

        # First call should create the client
        client1 = manager.get_translate_client()

        # Second call should return cached client
        client2 = manager.get_translate_client()

        assert client1 == client2
        assert mock_session.client.call_count == 2  # STS + Translate

    def test_client_access_denied_error(self, mock_session, mock_sts_client, clean_env):
        """Test client creation with access denied error during connectivity test."""
        mock_translate_client = Mock()
        mock_translate_client.list_languages.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='ListLanguages',
        )

        mock_session.client.side_effect = [mock_sts_client, mock_translate_client]

        manager = AWSClientManager()

        # Access denied during connectivity test should not raise an error
        # The client should be created successfully and cached
        client = manager.get_translate_client()
        assert client == mock_translate_client

    def test_client_service_unavailable_error(self, mock_session, mock_sts_client, clean_env):
        """Test client creation with service unavailable error."""
        mock_translate_client = Mock()
        mock_translate_client.list_languages.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}
            },
            operation_name='ListLanguages',
        )

        mock_session.client.side_effect = [mock_sts_client, mock_translate_client]

        manager = AWSClientManager()

        with pytest.raises(ServiceUnavailableError) as exc_info:
            manager.get_translate_client()

        assert 'AWS service temporarily unavailable' in str(exc_info.value)
        assert exc_info.value.details['service'] == 'translate'

    def test_client_creation_error(self, mock_session, mock_sts_client, clean_env):
        """Test client creation with ClientError during client creation."""
        mock_session.client.side_effect = [
            mock_sts_client,
            ClientError(
                error_response={'Error': {'Code': 'InvalidRegion', 'Message': 'Invalid region'}},
                operation_name='CreateClient',
            ),
        ]

        manager = AWSClientManager()

        with pytest.raises(ServiceUnavailableError) as exc_info:
            manager.get_translate_client()

        assert 'AWS service temporarily unavailable' in str(exc_info.value)
        assert exc_info.value.details['service'] == 'translate'
        assert exc_info.value.details['error_code'] == 'InvalidRegion'

    def test_client_botocore_error(self, mock_session, mock_sts_client, clean_env):
        """Test client creation with BotoCore error."""
        mock_session.client.side_effect = [mock_sts_client, BotoCoreError()]

        manager = AWSClientManager()

        with pytest.raises(ServiceUnavailableError) as exc_info:
            manager.get_translate_client()

        assert 'BotoCore error' in str(exc_info.value)
        assert exc_info.value.details['service'] == 'translate'

    def test_validate_credentials_method(self, mock_session, mock_sts_client, clean_env):
        """Test the validate_credentials method."""
        mock_session.client.return_value = mock_sts_client

        manager = AWSClientManager()

        # Should return True for valid credentials
        assert manager.validate_credentials() is True

        # Mock credential validation failure
        mock_sts_client.get_caller_identity.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='GetCallerIdentity',
        )

        # Should return False for invalid credentials
        assert manager.validate_credentials() is False

    def test_refresh_credentials(self, mock_session, mock_sts_client, clean_env):
        """Test credential refresh functionality."""
        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = {'Languages': []}

        mock_session.client.side_effect = [
            mock_sts_client,  # Initial STS call
            mock_translate_client,  # Initial translate client
            mock_sts_client,  # Refresh STS call
        ]

        manager = AWSClientManager()

        # Create a client to populate cache
        manager.get_translate_client()
        assert len(manager._clients) == 1

        # Refresh credentials should clear cache
        manager.refresh_credentials()
        assert len(manager._clients) == 0

    def test_get_region(self, mock_session, mock_sts_client, clean_env):
        """Test getting current region."""
        mock_session.region_name = 'us-west-2'
        mock_session.client.return_value = mock_sts_client

        manager = AWSClientManager()

        assert manager.get_region() == 'us-west-2'

    def test_get_account_id(self, mock_session, mock_sts_client, clean_env):
        """Test getting current account ID."""
        mock_sts_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test-user',
        }
        mock_session.client.return_value = mock_sts_client

        manager = AWSClientManager()

        assert manager.get_account_id() == '123456789012'

    def test_get_account_id_error(self, mock_session, mock_sts_client, clean_env):
        """Test getting account ID with error."""
        # First call succeeds (for initialization), second fails
        mock_sts_client.get_caller_identity.side_effect = [
            {'Account': '123456789012', 'Arn': 'arn:aws:iam::123456789012:user/test-user'},
            ClientError(
                error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
                operation_name='GetCallerIdentity',
            ),
        ]
        mock_session.client.return_value = mock_sts_client

        manager = AWSClientManager()

        assert manager.get_account_id() is None

    def test_get_user_arn(self, mock_session, mock_sts_client, clean_env):
        """Test getting current user ARN."""
        mock_sts_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test-user',
        }
        mock_session.client.return_value = mock_sts_client

        manager = AWSClientManager()

        assert manager.get_user_arn() == 'arn:aws:iam::123456789012:user/test-user'

    def test_get_user_arn_error(self, mock_session, mock_sts_client, clean_env):
        """Test getting user ARN with error."""
        # First call succeeds (for initialization), second fails
        mock_sts_client.get_caller_identity.side_effect = [
            {'Account': '123456789012', 'Arn': 'arn:aws:iam::123456789012:user/test-user'},
            ClientError(
                error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
                operation_name='GetCallerIdentity',
            ),
        ]
        mock_session.client.return_value = mock_sts_client

        manager = AWSClientManager()

        assert manager.get_user_arn() is None

    def test_close(self, mock_session, mock_sts_client, clean_env):
        """Test closing the client manager."""
        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = {'Languages': []}

        mock_session.client.side_effect = [mock_sts_client, mock_translate_client]

        manager = AWSClientManager()

        # Create a client to populate cache
        manager.get_translate_client()
        assert len(manager._clients) == 1

        # Close should clear everything
        manager.close()
        assert len(manager._clients) == 0
        assert manager._session is None

    def test_context_manager(self, mock_session, mock_sts_client, clean_env):
        """Test using client manager as context manager."""
        mock_session.client.return_value = mock_sts_client

        with AWSClientManager() as manager:
            assert manager._session is not None

        # Should be closed after context exit
        assert manager._session is None
        assert len(manager._clients) == 0

    def test_thread_safety(self, mock_session, mock_sts_client, clean_env):
        """Test thread safety of client creation."""
        import threading
        import time

        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = {'Languages': []}

        mock_session.client.side_effect = [mock_sts_client, mock_translate_client]

        manager = AWSClientManager()
        clients = []

        def get_client():
            time.sleep(0.01)  # Small delay to increase chance of race condition
            clients.append(manager.get_translate_client())

        # Create multiple threads trying to get the same client
        threads = [threading.Thread(target=get_client) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should get the same cached client
        assert len(clients) == 5
        assert all(client == clients[0] for client in clients)

        # Only one client should have been created
        assert len(manager._clients) == 1


class TestAWSClientManagerEdgeCases:
    """Tests for AWS client manager edge cases."""

    @patch('boto3.Session')
    def test_validate_credentials_no_session(self, mock_session):
        """Test credential validation when session is not properly initialized."""
        from awslabs.amazon_translate_mcp_server.aws_client import AWSClientManager

        # Create manager but simulate session failure
        mock_session.side_effect = Exception('Session initialization failed')

        with pytest.raises(Exception):
            AWSClientManager()

    @patch('boto3.Session')
    def test_client_creation_with_invalid_service(self, mock_session):
        """Test client creation with invalid service name."""
        from awslabs.amazon_translate_mcp_server.aws_client import AWSClientManager

        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test-user',
        }

        def mock_client_factory(service, **kwargs):
            if service == 'sts':
                return mock_sts_client
            elif service == 'invalid-service':
                raise Exception('Invalid service')
            else:
                raise Exception('Unknown service')

        mock_session.return_value.client.side_effect = mock_client_factory

        manager = AWSClientManager()

        with pytest.raises(Exception):
            manager.get_translate_client()

    @patch('boto3.Session')
    def test_session_region_handling(self, mock_session):
        """Test session region handling."""
        from awslabs.amazon_translate_mcp_server.aws_client import AWSClientManager

        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test-user',
        }

        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_sts_client
        mock_session_instance.region_name = None  # No region set
        mock_session.return_value = mock_session_instance

        manager = AWSClientManager()

        # Should handle missing region gracefully
        region = manager.get_region()
        assert region is None

    @patch('boto3.Session')
    def test_client_manager_cleanup(self, mock_session):
        """Test client manager cleanup functionality."""
        from awslabs.amazon_translate_mcp_server.aws_client import AWSClientManager

        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test-user',
        }

        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = {'Languages': []}

        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = [mock_sts_client, mock_translate_client]
        mock_session.return_value = mock_session_instance

        manager = AWSClientManager()

        # Create a client to populate cache
        manager.get_translate_client()
        assert len(manager._clients) > 0

        # Test cleanup
        manager.close()
        assert len(manager._clients) == 0

    @patch('boto3.Session')
    def test_credential_refresh_scenarios(self, mock_session):
        """Test credential refresh scenarios."""
        from awslabs.amazon_translate_mcp_server.aws_client import AWSClientManager

        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test-user',
        }

        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_sts_client
        mock_session.return_value = mock_session_instance

        manager = AWSClientManager()

        # Test refresh credentials
        manager.refresh_credentials()

        # Should clear client cache
        assert len(manager._clients) == 0
