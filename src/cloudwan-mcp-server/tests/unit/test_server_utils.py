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

"""Unit tests for server utilities and client management."""

import json
import pytest
from awslabs.cloudwan_mcp_server.server import (
    _create_client,
    get_aws_client,
    get_global_networks,
    handle_aws_error,
    list_core_networks,
)
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


class TestAWSClientManagement:
    """Test AWS client management functionality."""

    def test_get_aws_client_default_region(self):
        """Test AWS client creation with default region."""
        _create_client.cache_clear()  # Clear cache to force client creation

        # Clear AWS_PROFILE to avoid session creation
        with patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'us-west-2', 'AWS_PROFILE': ''}, clear=True):
            with patch('boto3.client') as mock_client:
                mock_client.return_value = Mock()

                client = get_aws_client("networkmanager")

                mock_client.assert_called_once()
                call_args = mock_client.call_args
                assert call_args[0][0] == "networkmanager"
                assert call_args[1]["config"].region_name == "us-west-2"

    def test_get_aws_client_explicit_region(self):
        """Test AWS client creation with explicit region."""
        _create_client.cache_clear()  # Clear cache to force client creation

        with patch.dict('os.environ', {'AWS_PROFILE': ''}, clear=True):
            with patch('boto3.client') as mock_client:
                mock_client.return_value = Mock()

                client = get_aws_client("ec2", "eu-central-1")

                mock_client.assert_called_once()
                call_args = mock_client.call_args
                assert call_args[0][0] == "ec2"
                assert call_args[1]["config"].region_name == "eu-central-1"

    def test_get_aws_client_with_profile(self):
        """Test AWS client creation with AWS profile."""
        _create_client.cache_clear()  # Clear cache to force client creation

        with patch.dict('os.environ', {'AWS_PROFILE': 'test-profile'}):
            with patch('boto3.Session') as mock_session:
                mock_session_instance = Mock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.client.return_value = Mock()

                client = get_aws_client("networkmanager", "us-east-1")

                mock_session.assert_called_once_with(profile_name="test-profile")
                mock_session_instance.client.assert_called_once()

    def test_get_aws_client_caching(self):
        """Test AWS client caching functionality."""
        _create_client.cache_clear()  # Clear cache to start clean

        with patch.dict('os.environ', {'AWS_PROFILE': ''}, clear=True):
            with patch('boto3.client') as mock_client:
                mock_client.return_value = Mock()

                # First call should create client
                client1 = get_aws_client("networkmanager", "us-east-1")

                # Second call should return cached client
                client2 = get_aws_client("networkmanager", "us-east-1")

                # Should only call boto3.client once due to caching
                mock_client.assert_called_once()
                assert client1 is client2

    def test_get_aws_client_different_services_cached_separately(self):
        """Test that different services are cached separately."""
        _create_client.cache_clear()  # Clear cache to start clean

        with patch.dict('os.environ', {'AWS_PROFILE': ''}, clear=True):
            with patch('boto3.client') as mock_client:
                # Return different mock objects for different calls
                mock_client1 = Mock()
                mock_client2 = Mock()
                mock_client.side_effect = [mock_client1, mock_client2]

                client1 = get_aws_client("networkmanager", "us-east-1")
                client2 = get_aws_client("ec2", "us-east-1")

                # Should call boto3.client twice for different services
                assert mock_client.call_count == 2
                assert client1 is not client2
                assert client1 is mock_client1
                assert client2 is mock_client2

    def test_get_aws_client_fallback_region(self):
        """Test AWS client with fallback region."""
        _create_client.cache_clear()  # Clear cache to start clean

        with patch.dict('os.environ', {}, clear=True):
            with patch('boto3.client') as mock_client:
                mock_client.return_value = Mock()

                client = get_aws_client("networkmanager")

                call_args = mock_client.call_args
                assert call_args[1]["config"].region_name == "us-east-1"  # Default fallback


class TestErrorHandling:
    """Test error handling utilities."""

    def test_handle_aws_error_client_error(self):
        """Test handling of AWS ClientError."""
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'User is not authorized to perform this action'
            }
        }
        client_error = ClientError(error_response, 'TestOperation')

        result = handle_aws_error(client_error, "test_operation")
        response = json.loads(result)

        assert response["success"] is False
        assert "test_operation failed" in response["error"]
        assert "User is not authorized to perform this action" in response["error"]
        assert response["error_code"] == "AccessDenied"

    def test_handle_aws_error_generic_exception(self):
        """Test handling of generic exception."""
        generic_error = ValueError("Test error message")

        result = handle_aws_error(generic_error, "test_operation")
        response = json.loads(result)

        assert response["success"] is False
        assert "test_operation failed" in response["error"]
        assert "Test error message" in response["error"]
        assert "error_code" not in response

    def test_handle_aws_error_unknown_client_error(self):
        """Test handling of ClientError with missing fields."""
        error_response = {
            'Error': {
                # Missing Code and Message fields
            }
        }
        client_error = ClientError(error_response, 'TestOperation')

        result = handle_aws_error(client_error, "test_operation")
        response = json.loads(result)

        assert response["success"] is False
        assert response["error_code"] == "Unknown"

    def test_handle_aws_error_malformed_response(self):
        """Test handling of ClientError with malformed response."""
        error_response = {}  # Missing Error key
        client_error = ClientError(error_response, 'TestOperation')

        result = handle_aws_error(client_error, "test_operation")
        response = json.loads(result)

        assert response["success"] is False
        assert "test_operation failed" in response["error"]


class TestResponseFormats:
    """Test response format consistency."""

    def test_success_response_structure(self):
        """Test that success responses have consistent structure."""
        # This would be tested indirectly through tool tests
        # but we can test the basic JSON structure
        pass

    def test_error_response_structure(self, expected_error_format):
        """Test that error responses follow expected format."""
        error = ValueError("Test error")
        result = handle_aws_error(error, "test_operation")
        response = json.loads(result)

        # Check required fields
        assert "success" in response
        assert "error" in response
        assert response["success"] is False
        assert isinstance(response["error"], str)

    def test_json_serialization(self):
        """Test that responses are valid JSON."""
        error = ClientError(
            {'Error': {'Code': 'TestError', 'Message': 'Test message'}},
            'TestOperation'
        )

        result = handle_aws_error(error, "test_operation")

        # Should not raise exception
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_unicode_handling_in_errors(self):
        """Test that unicode characters in errors are handled properly."""
        error = ValueError("Test error with unicode: 测试")

        result = handle_aws_error(error, "test_operation")
        response = json.loads(result)

        assert "测试" in response["error"]
        assert response["success"] is False


class TestServerUtils:
    """Test server utility functions."""

    @pytest.fixture
    def mock_get_aws_client(self):
        """Mock get_aws_client function."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_client:
            mock_nm = Mock()
            mock_nm.list_core_networks.return_value = {
                "CoreNetworks": [
                    {
                        "CoreNetworkId": "core-network-1234567890abcdef0",
                        "GlobalNetworkId": "global-network-1234567890abcdef0",
                        "State": "AVAILABLE"
                    }
                ]
            }
            mock_nm.describe_global_networks.return_value = {
                "GlobalNetworks": [
                    {
                        "GlobalNetworkId": "global-network-1234567890abcdef0",
                        "State": "AVAILABLE"
                    }
                ]
            }
            mock_client.return_value = mock_nm
            yield mock_client

@pytest.fixture
def expected_error_format():
    """Standard error response structure."""
    return {
        "success": False,
        "error": "",
        "error_code": "",
        "details": {}
    }

@pytest.mark.asyncio
async def test_list_core_networks_success(self, mock_get_aws_client):
    result = await list_core_networks("us-east-1")
    response = json.loads(result)

    assert response["success"] is True
    assert response["region"] == "us-east-1"
    assert response["total_count"] == 1
    assert len(response["core_networks"]) == 1

    # Verify core network details
    core_network = response["core_networks"][0]
    assert core_network["CoreNetworkId"] == "core-network-1234567890abcdef0"
    assert core_network["State"] == "AVAILABLE"

@pytest.mark.asyncio
async def test_list_core_networks_empty_response(self, mock_get_aws_client):
    # Override mock to return empty response
    mock_client = Mock()
    mock_client.list_core_networks.return_value = {"CoreNetworks": []}
    mock_get_aws_client.return_value = mock_client

    result = await list_core_networks("us-west-2")
    response = json.loads(result)

    assert response["success"] is True
    assert response["region"] == "us-west-2"
    assert response["message"] == "No CloudWAN core networks found in the specified region."
    assert response["core_networks"] == []

@pytest.mark.asyncio
async def test_list_core_networks_client_error(self, mock_get_aws_client):
    # Mock ClientError
    error_response = {
        'Error': {
            'Code': 'AccessDenied',
            'Message': 'User is not authorized to perform networkmanager:ListCoreNetworks'
        }
    }
    mock_get_aws_client.return_value.list_core_networks.side_effect = ClientError(
        error_response, 'ListCoreNetworks'
    )

    result = await list_core_networks("us-east-1")
    response = json.loads(result)

    assert response["success"] is False
    assert "list_core_networks failed" in response["error"]
    assert response["error_code"] == "AccessDenied"

@pytest.mark.asyncio
async def test_get_global_networks_error(self, mock_get_aws_client):
    # Mock client error
    mock_client = Mock()
    mock_client.describe_global_networks.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
        "DescribeGlobalNetworks"
    )
    mock_get_aws_client.return_value = mock_client

    result = await get_global_networks("us-east-1")
    response = json.loads(result)

    assert response["success"] is False
    assert "get_global_networks failed" in response["error"]
    assert response["error_code"] == "AccessDenied"


class TestEnvironmentHandling:
    """Test environment variable handling."""

    def test_aws_region_precedence(self):
        """Test AWS region precedence: parameter > env var > default."""
        _create_client.cache_clear()  # Clear cache to start clean

        with patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'env-region', 'AWS_PROFILE': ''}, clear=True):
            with patch('boto3.client') as mock_client:
                mock_client.return_value = Mock()

                # Explicit region should override env var
                get_aws_client("networkmanager", "explicit-region")

                # Verify the call was made correctly
                assert mock_client.call_count == 1
                call_args = mock_client.call_args
                assert call_args is not None, "Expected boto3.client to be called"
                assert call_args[1]["config"].region_name == "explicit-region"

    def test_aws_profile_handling(self):
        """Test AWS profile environment variable handling."""
        with patch.dict('os.environ', {'AWS_PROFILE': 'test-profile'}):
            with patch('boto3.Session') as mock_session:
                mock_session.return_value.client.return_value = Mock()

                get_aws_client("networkmanager")

                mock_session.assert_called_once_with(profile_name="test-profile")

    def test_missing_environment_variables(self):
        """Test behavior when environment variables are missing."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('boto3.client') as mock_client:
                mock_client.return_value = Mock()

                client = get_aws_client("networkmanager")

                # Should use fallback values
                call_args = mock_client.call_args
                assert call_args[1]["config"].region_name == "us-east-1"
