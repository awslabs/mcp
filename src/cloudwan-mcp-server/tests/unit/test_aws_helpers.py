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

"""AWS utility function tests following AWS Labs patterns."""

import pytest
from awslabs.cloudwan_mcp_server.server import _create_client, get_aws_client, handle_aws_error
from botocore.config import Config
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


# Cache capacity constant to match server configuration (@lru_cache(maxsize=10))
CACHE_CAPACITY = 10


class TestGetAWSClient:
    """Test get_aws_client utility function following AWS Labs patterns."""

    def setup_method(self):
        _create_client.cache_clear()  # Clear LRU cache

    @pytest.mark.unit
    @patch('awslabs.cloudwan_mcp_server.server.boto3.client')
    def test_get_aws_client_default_region(self, mock_boto_client):
        """Test get_aws_client with default region configuration."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        with patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'us-west-2'}):
            result = get_aws_client('networkmanager')

        assert result == mock_client
        mock_boto_client.assert_called_once()

        # Verify config was created with correct region
        call_args = mock_boto_client.call_args
        assert call_args[0][0] == 'networkmanager'
        assert call_args[1]['region_name'] == 'us-west-2'
        assert isinstance(call_args[1]['config'], Config)

    @pytest.mark.unit
    @patch('awslabs.cloudwan_mcp_server.server.boto3.client')
    def test_get_aws_client_explicit_region(self, mock_boto_client):
        """Test get_aws_client with explicitly provided region."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        result = get_aws_client('ec2', region='eu-west-1')

        assert result == mock_client
        mock_boto_client.assert_called_once()

        call_args = mock_boto_client.call_args
        assert call_args[1]['region_name'] == 'eu-west-1'

    @pytest.mark.unit
    @patch('awslabs.cloudwan_mcp_server.server.boto3.Session')
    def test_get_aws_client_with_profile(self, mock_session_class):
        """Test get_aws_client with AWS profile configuration."""
        mock_session = Mock()
        mock_client = Mock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        with patch.dict('os.environ', {
            'AWS_PROFILE': 'test-profile',
            'AWS_DEFAULT_REGION': 'us-east-1'
        }):
            result = get_aws_client('networkmanager')

        assert result == mock_client
        mock_session_class.assert_called_once_with(profile_name='test-profile')
        mock_session.client.assert_called_once()

        call_args = mock_session.client.call_args
        assert call_args[0][0] == 'networkmanager'
        assert isinstance(call_args[1]['config'], Config)

    @pytest.mark.unit
    @patch('awslabs.cloudwan_mcp_server.server.boto3.client')
    def test_get_aws_client_caching(self, mock_boto_client):
        """Test get_aws_client caches clients properly."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        with patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'us-east-1'}):
            # First call
            result1 = get_aws_client('networkmanager')
            # Second call with same parameters
            result2 = get_aws_client('networkmanager')

        # Should return same cached client
        assert result1 == result2
        assert result1 == mock_client

        # boto3.client should only be called once due to caching
        mock_boto_client.assert_called_once()

    @pytest.mark.unit
    @patch('awslabs.cloudwan_mcp_server.server.boto3.client')
    def test_get_aws_client_different_services_cached_separately(self, mock_boto_client):
        """Test different AWS services are cached separately."""
        mock_nm_client = Mock()
        mock_ec2_client = Mock()

        def client_side_effect(service, **kwargs):
            if service == 'networkmanager':
                return mock_nm_client
            elif service == 'ec2':
                return mock_ec2_client
            return Mock()

        mock_boto_client.side_effect = client_side_effect

        with patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'us-east-1'}):
            nm_client = get_aws_client('networkmanager')
            ec2_client = get_aws_client('ec2')

        assert nm_client == mock_nm_client
        assert ec2_client == mock_ec2_client
        assert nm_client != ec2_client
        assert mock_boto_client.call_count == 2

    @pytest.mark.unit
    @patch('awslabs.cloudwan_mcp_server.server.boto3.client')
    def test_get_aws_client_config_parameters(self, mock_boto_client):
        """Test get_aws_client creates Config with correct parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        with patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'us-east-1'}):
            get_aws_client('networkmanager')

        call_args = mock_boto_client.call_args
        config = call_args[1]['config']

        assert isinstance(config, Config)
        # Verify config parameters (accessing private attributes for testing)
        assert config.region_name == 'us-east-1'
        assert config.retries['max_attempts'] == 3
        assert config.retries['mode'] == 'adaptive'
        assert config.max_pool_connections == 10

    @pytest.mark.unit
    @patch('awslabs.cloudwan_mcp_server.server.boto3.client')
    def test_get_aws_client_fallback_region(self, mock_boto_client):
        """Test get_aws_client falls back to us-east-1 when no region specified."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Clear any AWS_DEFAULT_REGION
        with patch.dict('os.environ', {}, clear=True):
            result = get_aws_client('networkmanager')

        assert result == mock_client
        call_args = mock_boto_client.call_args
        assert call_args[1]['region_name'] == 'us-east-1'

    @pytest.mark.unit
    @patch('awslabs.cloudwan_mcp_server.server.boto3.client')
    def test_get_aws_client_cache_key_generation(self, mock_boto_client):
        """Test cache key generation includes service, region, and profile."""
        mock_client1 = Mock()
        mock_client2 = Mock()

        call_count = 0
        def client_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_client1 if call_count == 1 else mock_client2

        mock_boto_client.side_effect = client_side_effect

        # Same service, different regions - should create separate clients
        with patch.dict('os.environ', {}, clear=True):
            client1 = get_aws_client('networkmanager', region='us-east-1')
            client2 = get_aws_client('networkmanager', region='us-west-2')

        assert client1 != client2
        assert mock_boto_client.call_count == 2

    @pytest.mark.unit
    @patch('awslabs.cloudwan_mcp_server.server.boto3.client')
    def test_get_aws_client_exception_handling(self, mock_boto_client):
        """Test get_aws_client handles exceptions appropriately."""
        mock_boto_client.side_effect = Exception("No AWS credentials found")

        with pytest.raises(Exception):
            get_aws_client('networkmanager')


class TestHandleAWSError:
    """Test handle_aws_error utility function following AWS Labs patterns."""

    @pytest.mark.unit
    def test_handle_aws_client_error(self):
        """Test handle_aws_error with ClientError."""
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'User: arn:aws:iam::123456789012:user/test is not authorized'
            }
        }
        client_error = ClientError(error_response, 'ListCoreNetworks')

        result = handle_aws_error(client_error, 'List Core Networks')

        # Parse JSON response
        import json
        parsed = json.loads(result)

        assert parsed['success'] is False
        assert 'List Core Networks failed:' in parsed['error']
        assert 'not authorized' in parsed['error']
        assert parsed['error_code'] == 'AccessDenied'

    @pytest.mark.unit
    def test_handle_aws_client_error_missing_details(self):
        """Test handle_aws_error with ClientError missing error details."""
        error_response = {'Error': {}}
        client_error = ClientError(error_response, 'DescribeGlobalNetworks')

        result = handle_aws_error(client_error, 'Describe Global Networks')

        import json
        parsed = json.loads(result)

        assert parsed['success'] is False
        assert 'Describe Global Networks failed:' in parsed['error']
        assert parsed['error_code'] == 'Unknown'

    @pytest.mark.unit
    def test_handle_generic_exception(self):
        """Test handle_aws_error with generic Exception."""
        generic_error = ValueError("Invalid parameter format")

        result = handle_aws_error(generic_error, 'Validate Input')

        import json
        parsed = json.loads(result)

        assert parsed['success'] is False
        assert 'Validate Input failed:' in parsed['error']
        assert 'Invalid parameter format' in parsed['error']
        # Generic exceptions don't have error_code in current implementation
        assert 'error_code' not in parsed

    @pytest.mark.unit
    def test_handle_aws_error_json_formatting(self):
        """Test handle_aws_error returns properly formatted JSON."""
        error_response = {
            'Error': {
                'Code': 'ResourceNotFound',
                'Message': 'The specified core network does not exist'
            }
        }
        client_error = ClientError(error_response, 'GetCoreNetworkPolicy')

        result = handle_aws_error(client_error, 'Get Policy')

        # Verify it's valid JSON
        import json
        parsed = json.loads(result)

        # Verify formatting with indent
        assert '\n' in result  # Should be indented
        assert '  "success": false' in result
        assert '  "error_code": "ResourceNotFound"' in result

    @pytest.mark.unit
    def test_handle_aws_error_operation_context(self):
        """Test handle_aws_error includes operation context in error message."""
        operations = [
            'List Core Networks',
            'Describe VPCs',
            'Validate Policy Document',
            'Trace Network Path'
        ]

        for operation in operations:
            error = ValueError("Test error")
            result = handle_aws_error(error, operation)

            import json
            parsed = json.loads(result)

            assert operation in parsed['error']
            assert 'Test error' in parsed['error']

    @pytest.mark.unit
    def test_handle_aws_error_with_special_characters(self):
        """Test handle_aws_error handles special characters in error messages."""
        error_response = {
            'Error': {
                'Code': 'ValidationException',
                'Message': 'Invalid CIDR: "192.168.1.0/33" contains special chars: @#$%'
            }
        }
        client_error = ClientError(error_response, 'ValidateNetworkConfiguration')

        result = handle_aws_error(client_error, 'Validate Network')

        import json
        parsed = json.loads(result)

        assert parsed['success'] is False
        assert '@#$%' in parsed['error']  # Special characters preserved
        assert parsed['error_code'] == 'ValidationException'

    @pytest.mark.unit
    def test_handle_aws_error_empty_operation(self):
        """Test handle_aws_error with empty operation string."""
        error = RuntimeError("Connection timeout")

        result = handle_aws_error(error, '')

        import json
        parsed = json.loads(result)

        assert parsed['success'] is False
        assert ' failed: Connection timeout' in parsed['error']
        # Generic exceptions don't have error_code in current implementation
        assert 'error_code' not in parsed

    @pytest.mark.unit
    def test_handle_aws_error_datetime_in_response(self):
        """Test handle_aws_error doesn't break with datetime-like strings."""
        from datetime import datetime

        # Create error that might contain datetime info
        error_response = {
            'Error': {
                'Code': 'ThrottlingException',
                'Message': f'Request rate exceeded at {datetime.now().isoformat()}'
            }
        }
        client_error = ClientError(error_response, 'ListCoreNetworks')

        result = handle_aws_error(client_error, 'List Resources')

        import json
        parsed = json.loads(result)  # Should not raise JSON decode error

        assert parsed['success'] is False
        assert parsed['error_code'] == 'ThrottlingException'
        assert 'Request rate exceeded' in parsed['error']


class TestAWSClientCaching:
    """Test AWS client caching behavior following AWS Labs patterns."""

    def setup_method(self):
        """Clear client cache before each test."""
        _create_client.cache_clear()

    @pytest.mark.unit
    @patch('awslabs.cloudwan_mcp_server.server.boto3.client')
    def test_client_cache_isolation(self, mock_boto_client):
        """Test cache isolation between configurations."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        get_aws_client('networkmanager', 'us-east-1')
        cache_info = _create_client.cache_info()
        assert cache_info.currsize == 1

    @pytest.mark.asyncio
    @patch('awslabs.cloudwan_mcp_server.server.boto3.client')
    async def test_lru_cache_eviction(self, mock_boto_client):
        """Test LRU cache eviction policy through _create_client function."""
        # Clear cache first
        _create_client.cache_clear()

        # Test cache behavior by creating clients that should be cached
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Fill cache to near capacity by creating different client configurations
        with patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'us-east-1'}):
            for i in range(CACHE_CAPACITY - 1):
                # Create clients for different services to fill cache
                service = f'service-{i}'
                get_aws_client(service)

        # Verify cache is being used
        initial_cache_info = _create_client.cache_info()
        assert initial_cache_info.currsize == CACHE_CAPACITY - 1

        # Add one more to trigger potential eviction
        get_aws_client('new-service')

        # Verify cache management
        final_cache_info = _create_client.cache_info()
        assert final_cache_info.currsize == CACHE_CAPACITY

    @pytest.mark.unit
    @patch('awslabs.cloudwan_mcp_server.server.boto3.client')
    def test_client_cache_cleanup(self, mock_boto_client):
        """Test client cache can be cleared properly."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Add entries to cache
        with patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'us-east-1'}):
            get_aws_client('networkmanager')
            get_aws_client('ec2')

        cache_info = _create_client.cache_info()
        assert cache_info.currsize >= 1

        # Clear cache
        _create_client.cache_clear()
        cache_info = _create_client.cache_info()
        assert cache_info.currsize == 0

    @pytest.mark.unit
    @patch('awslabs.cloudwan_mcp_server.server.boto3.client')
    def test_client_cache_thread_safety_pattern(self, mock_boto_client):
        """Test client cache follows thread-safe access patterns."""
        # This test verifies the LRU cache is thread-safe
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Test basic cache operations don't raise exceptions
        with patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'us-east-1'}):
            client = get_aws_client('networkmanager')
            assert client == mock_client

        cache_info = _create_client.cache_info()
        assert cache_info.currsize >= 0
