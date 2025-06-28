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

"""Tests for utils module integration."""

import os
from unittest.mock import patch, MagicMock

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from awslabs.amazon_sagemaker_mcp_server.utils.aws_client import (
    validate_aws_credentials,
    get_sagemaker_client,
)
from awslabs.amazon_sagemaker_mcp_server.utils.permissions import (
    require_write_access,
    require_sensitive_data_access,
    PermissionError,
)


class TestUtilsIntegration:
    """Test integration between utils modules."""

    def test_client_and_permissions_integration(self):
        """Test that client creation works with permission checks."""
        # Test read-only mode (default)
        with patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_session') as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value = mock_session_instance
            
            # Should be able to create client in read-only mode
            client = get_sagemaker_client()
            assert client is not None
            
            # Should not be able to perform write operations
            with pytest.raises(PermissionError):
                require_write_access()

    def test_credential_validation_with_permissions(self):
        """Test credential validation combined with permission checks."""
        # Test with valid credentials but no write access
        with patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_session') as mock_session:
            with patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_aws_config'):
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_sts_client = MagicMock()
                mock_session_instance.client.return_value = mock_sts_client
                mock_sts_client.get_caller_identity.return_value = {'Account': '123456789012'}
                
                # Credentials should be valid
                assert validate_aws_credentials() is True
                
                # But write access should still be denied
                with pytest.raises(PermissionError):
                    require_write_access()

    def test_environment_variable_consistency(self):
        """Test that environment variables are handled consistently across modules."""
        # Test AWS region consistency
        os.environ['AWS_REGION'] = 'eu-west-1'
        
        with patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_session') as mock_session:
            mock_session_instance = MagicMock()
            mock_session_instance.region_name = 'eu-west-1'
            mock_session.return_value = mock_session_instance
            
            from awslabs.amazon_sagemaker_mcp_server.utils.aws_client import get_current_region
            region = get_current_region()
            assert region == 'eu-west-1'

    def test_error_handling_consistency(self):
        """Test that error handling is consistent across utils modules."""
        # Test AWS client error handling
        with patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_session') as mock_session:
            with patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_aws_config'):
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_sts_client = MagicMock()
                mock_session_instance.client.return_value = mock_sts_client
                mock_sts_client.get_caller_identity.side_effect = ClientError(
                    {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
                    'GetCallerIdentity'
                )
                
                # Should handle AWS errors gracefully
                assert validate_aws_credentials() is False

        # Test permission error handling
        with pytest.raises(PermissionError) as exc_info:
            require_write_access()
        
        assert "Write access is required" in str(exc_info.value)

    def test_configuration_precedence(self):
        """Test configuration precedence across utils modules."""
        # Test that explicit credentials take precedence over profile
        os.environ['AWS_ACCESS_KEY_ID'] = 'explicit-key'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'explicit-secret'
        os.environ['AWS_PROFILE'] = 'test-profile'
        # Clear session token to avoid interference
        if 'AWS_SESSION_TOKEN' in os.environ:
            del os.environ['AWS_SESSION_TOKEN']
        
        with patch('boto3.Session') as mock_session:
            from awslabs.amazon_sagemaker_mcp_server.utils.aws_client import get_session
            get_session()
            
            # Should use explicit credentials, not profile
            # Check that it was called with explicit credentials
            call_args = mock_session.call_args
            assert call_args[1]['aws_access_key_id'] == 'explicit-key'
            assert call_args[1]['aws_secret_access_key'] == 'explicit-secret'
            assert call_args[1]['region_name'] == 'us-east-1'


class TestUtilsModuleStructure:
    """Test utils module structure and imports."""

    def test_utils_module_imports(self):
        """Test that utils modules can be imported correctly."""
        # Test aws_client imports
        from awslabs.amazon_sagemaker_mcp_server.utils.aws_client import (
            get_sagemaker_client,
            get_sagemaker_runtime_client,
            validate_aws_credentials,
        )
        
        # Test permissions imports
        from awslabs.amazon_sagemaker_mcp_server.utils.permissions import (
            require_write_access,
            require_sensitive_data_access,
            is_write_access_enabled,
            is_sensitive_data_access_enabled,
        )
        
        # All imports should succeed
        assert callable(get_sagemaker_client)
        assert callable(get_sagemaker_runtime_client)
        assert callable(validate_aws_credentials)
        assert callable(require_write_access)
        assert callable(require_sensitive_data_access)
        assert callable(is_write_access_enabled)
        assert callable(is_sensitive_data_access_enabled)

    def test_utils_init_module(self):
        """Test utils __init__ module."""
        from awslabs.amazon_sagemaker_mcp_server.utils import __init__
        # Should be able to import without errors
        assert __init__ is not None


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_typical_read_only_workflow(self):
        """Test a typical read-only workflow."""
        with patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_session') as mock_session:
            with patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_aws_config'):
                # Setup mocks
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_sts_client = MagicMock()
                mock_sagemaker_client = MagicMock()
                mock_session_instance.client.side_effect = lambda service, **kwargs: {
                    'sts': mock_sts_client,
                    'sagemaker': mock_sagemaker_client,
                }[service]
                
                mock_sts_client.get_caller_identity.return_value = {'Account': '123456789012'}
                mock_sagemaker_client.list_endpoints.return_value = {'Endpoints': []}
                
                # Validate credentials
                assert validate_aws_credentials() is True
                
                # Get client and perform read operation
                client = get_sagemaker_client()
                response = client.list_endpoints()
                assert 'Endpoints' in response
                
                # Write operations should be blocked
                with pytest.raises(PermissionError):
                    require_write_access()

    def test_typical_write_enabled_workflow(self):
        """Test a typical workflow with write access enabled."""
        os.environ['ALLOW_WRITE'] = 'true'
        
        with patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_session') as mock_session:
            with patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_aws_config'):
                # Setup mocks
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_sts_client = MagicMock()
                mock_sagemaker_client = MagicMock()
                mock_session_instance.client.side_effect = lambda service, **kwargs: {
                    'sts': mock_sts_client,
                    'sagemaker': mock_sagemaker_client,
                }[service]
                
                mock_sts_client.get_caller_identity.return_value = {'Account': '123456789012'}
                mock_sagemaker_client.create_endpoint.return_value = {'EndpointArn': 'arn:aws:sagemaker:us-east-1:123456789012:endpoint/test'}
                
                # Validate credentials
                assert validate_aws_credentials() is True
                
                # Write operations should be allowed
                require_write_access()  # Should not raise
                
                # Get client and perform write operation
                client = get_sagemaker_client()
                response = client.create_endpoint(EndpointName='test', EndpointConfigName='test-config')
                assert 'EndpointArn' in response

    def test_credential_failure_scenario(self):
        """Test scenario with credential failures."""
        with patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_session') as mock_session:
            with patch('awslabs.amazon_sagemaker_mcp_server.utils.aws_client.get_aws_config'):
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_sts_client = MagicMock()
                mock_session_instance.client.return_value = mock_sts_client
                mock_sts_client.get_caller_identity.side_effect = NoCredentialsError()
                
                # Credential validation should fail
                assert validate_aws_credentials() is False
                
                # Client creation should still work (boto3 handles this)
                client = get_sagemaker_client()
                assert client is not None
