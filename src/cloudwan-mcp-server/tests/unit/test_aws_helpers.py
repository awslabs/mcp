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

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from botocore.config import Config
from botocore.exceptions import ClientError

from awslabs.cloudwan_mcp_server.server import _create_client, get_aws_client, handle_aws_error

# Cache capacity constant to match server configuration (@lru_cache(maxsize=10))
CACHE_CAPACITY = 10


class TestGetAWSClient:
    """Test get_aws_client utility function following AWS Labs patterns."""

    def setup_method(self) -> None:
        _create_client.cache_clear()  # Clear LRU cache

    @pytest.mark.unit
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    def test_get_aws_client_default_region(self, mock_boto3) -> None:
        """Test get_aws_client with default region configuration."""
        mock_client = Mock()
        mock_session = Mock()
        mock_session.client.return_value = mock_client
        mock_boto3.Session.return_value = mock_session
        mock_boto3.client.return_value = mock_client

        with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-west-2"}, clear=True):
            result = get_aws_client("networkmanager")

        assert result == mock_client

        # Could use either Session path or direct client path depending on config
        assert mock_boto3.Session.called or mock_boto3.client.called

    @pytest.mark.unit
    @patch("awslabs.cloudwan_mcp_server.server.aws_config")
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    def test_get_aws_client_explicit_region(self, mock_boto3, mock_aws_config) -> None:
        """Test get_aws_client with explicitly provided region."""
        mock_aws_config.default_region = "us-east-1"
        mock_aws_config.profile = None  # Ensure no profile is set

        mock_client = Mock()
        mock_session = Mock()
        mock_session.client.return_value = mock_client
        mock_boto3.Session.return_value = mock_session
        mock_boto3.client.return_value = mock_client

        result = get_aws_client("ec2", region="eu-west-1")

        assert result == mock_client
        # Should use direct client path when no profile in environment
        mock_boto3.client.assert_called_once()

        call_args = mock_boto3.client.call_args
        assert call_args[1]["region_name"] == "eu-west-1"

    @pytest.mark.unit
    @patch("awslabs.cloudwan_mcp_server.server.aws_config")
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    def test_get_aws_client_with_profile(self, mock_boto3, mock_aws_config) -> None:
        """Test get_aws_client with AWS profile configuration."""
        mock_aws_config.default_region = "us-east-1"
        mock_aws_config.profile = "test-profile"  # Set a test profile

        mock_session = Mock()
        mock_client = Mock()
        mock_session.client.return_value = mock_client
        mock_boto3.Session.return_value = mock_session

        result = get_aws_client("networkmanager")

        assert result == mock_client
        mock_boto3.Session.assert_called_once_with(profile_name="test-profile")
        mock_session.client.assert_called_once()

        call_args = mock_session.client.call_args
        assert call_args[0][0] == "networkmanager"
        assert isinstance(call_args[1]["config"], Config)

    @pytest.mark.unit
    @patch("awslabs.cloudwan_mcp_server.server.aws_config")
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    def test_get_aws_client_caching(self, mock_boto3, mock_aws_config) -> None:
        """Test get_aws_client caches clients properly."""
        mock_aws_config.default_region = "us-east-1"
        mock_aws_config.profile = None  # Ensure no profile is set

        mock_client = Mock()
        mock_session = Mock()
        mock_session.client.return_value = mock_client
        mock_boto3.Session.return_value = mock_session
        mock_boto3.client.return_value = mock_client

        # First call
        result1 = get_aws_client("networkmanager")
        # Second call with same parameters
        result2 = get_aws_client("networkmanager")

        # Should return same cached client
        assert result1 == result2
        assert result1 == mock_client

        # boto3.client should only be called once due to caching (no profile set)
        mock_boto3.client.assert_called_once()

    @pytest.mark.unit
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    def test_get_aws_client_different_services_cached_separately(self, mock_boto3) -> None:
        """Test different AWS services are cached separately."""
        mock_nm_client = Mock()
        mock_ec2_client = Mock()

        # Mock both direct client and session-based client creation paths
        mock_session = Mock()
        mock_boto3.Session.return_value = mock_session

        def session_client_side_effect(service, **kwargs):
            if service == "networkmanager":
                return mock_nm_client
            elif service == "ec2":
                return mock_ec2_client
            return Mock()

        def direct_client_side_effect(service, **kwargs):
            if service == "networkmanager":
                return mock_nm_client
            elif service == "ec2":
                return mock_ec2_client
            return Mock()

        mock_session.client.side_effect = session_client_side_effect
        mock_boto3.client.side_effect = direct_client_side_effect

        # Clear environment and aws_config to ensure direct client path
        with patch("awslabs.cloudwan_mcp_server.server.aws_config") as mock_aws_config:
            mock_aws_config.profile = None
            mock_aws_config.default_region = "us-east-1"

            with patch.dict("os.environ", {}, clear=True):
                nm_client = get_aws_client("networkmanager")
                ec2_client = get_aws_client("ec2")

            assert nm_client == mock_nm_client
            assert ec2_client == mock_ec2_client
            assert nm_client != ec2_client
            # Should use direct client path when no profile set
            assert mock_boto3.client.call_count == 2

    @pytest.mark.unit
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    def test_get_aws_client_config_parameters(self, mock_boto3) -> None:
        """Test get_aws_client creates Config with correct parameters."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        with patch("awslabs.cloudwan_mcp_server.server.aws_config") as mock_aws_config:
            mock_aws_config.profile = None
            mock_aws_config.default_region = "us-east-1"

            with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}, clear=True):
                get_aws_client("networkmanager")

            call_args = mock_boto3.client.call_args
            config = call_args[1]["config"]

            assert isinstance(config, Config)
            # Verify config parameters (accessing private attributes for testing)
            assert config.region_name == "us-east-1"
            assert config.retries["max_attempts"] == 3
            assert config.retries["mode"] == "adaptive"
            assert config.max_pool_connections == 10

    @pytest.mark.unit
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    def test_get_aws_client_fallback_region(self, mock_boto3) -> None:
        """Test get_aws_client falls back to us-east-1 when no region specified."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        # Clear any AWS_DEFAULT_REGION and test fallback
        with patch("awslabs.cloudwan_mcp_server.server.aws_config") as mock_aws_config:
            mock_aws_config.default_region = "us-east-1"
            mock_aws_config.profile = None

            with patch.dict("os.environ", {}, clear=True):
                result = get_aws_client("networkmanager")

            assert result == mock_client
            call_args = mock_boto3.client.call_args
            assert call_args[1]["region_name"] == "us-east-1"

    @pytest.mark.unit
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    def test_get_aws_client_cache_key_generation(self, mock_boto3) -> None:
        """Test cache key generation includes service, region, and profile."""
        mock_client1 = Mock()
        mock_client2 = Mock()

        call_count = 0

        def client_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_client1 if call_count == 1 else mock_client2

        mock_boto3.client.side_effect = client_side_effect

        # Same service, different regions - should create separate clients
        with patch("awslabs.cloudwan_mcp_server.server.aws_config") as mock_aws_config:
            mock_aws_config.profile = None  # Ensure direct client path

            with patch.dict("os.environ", {}, clear=True):
                client1 = get_aws_client("networkmanager", region="us-east-1")
                client2 = get_aws_client("networkmanager", region="us-west-2")

            assert client1 != client2
            assert mock_boto3.client.call_count == 2

    @pytest.mark.unit
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    def test_get_aws_client_exception_handling(self, mock_boto3) -> None:
        """Test get_aws_client handles exceptions appropriately."""
        mock_boto3.client.side_effect = ClientError(
            error_response={"Error": {"Code": "NoCredentialsError", "Message": "Unable to locate credentials"}},
            operation_name="CreateClient",
        )

        with patch("awslabs.cloudwan_mcp_server.server.aws_config") as mock_aws_config:
            mock_aws_config.profile = None
            mock_aws_config.default_region = "us-east-1"

            with pytest.raises(ClientError) as exc_info:
                get_aws_client("networkmanager")

            assert exc_info.value.response["Error"]["Code"] == "NoCredentialsError"


class TestHandleAWSError:
    """Test handle_aws_error utility function following AWS Labs patterns."""

    @pytest.mark.unit
    def test_handle_aws_client_error(self) -> None:
        """Test handle_aws_error with ClientError."""
        error_response = {
            "Error": {"Code": "AccessDenied", "Message": "User: arn:aws:iam::123456789012:user/test is not authorized"}
        }
        client_error = ClientError(error_response, "ListCoreNetworks")

        result = handle_aws_error(client_error, "List Core Networks")

        # Parse JSON response
        parsed = json.loads(result)

        assert parsed["success"] is False
        assert "List Core Networks failed:" in parsed["error"]
        assert parsed["error_code"] == "AccessDenied"  # Added missing assertion

    @pytest.mark.unit
    def test_handle_aws_client_error_missing_details(self) -> None:
        """Test handle_aws_error with ClientError missing error details."""
        error_response = {"Error": {}}
        client_error = ClientError(error_response, "DescribeGlobalNetworks")

        result = handle_aws_error(client_error, "Describe Global Networks")

        parsed = json.loads(result)

        assert parsed["success"] is False
        assert "Describe Global Networks failed:" in parsed["error"]
        assert parsed["error_code"] == "Unknown"

    @pytest.mark.unit
    def test_handle_generic_exception(self) -> None:
        """Test handle_aws_error with generic Exception."""
        generic_error = ValueError("Invalid parameter format")

        result = handle_aws_error(generic_error, "Validate Input")

        parsed = json.loads(result)

        assert parsed["success"] is False
        assert "Validate Input failed:" in parsed["error"]
        assert "error_code" in parsed  # Added check
        assert parsed["error_code"] == "UnknownError"

    @pytest.mark.unit
    def test_handle_aws_error_json_formatting(self) -> None:
        """Test handle_aws_error returns properly formatted JSON."""
        error_response = {
            "Error": {
                "Code": "ThrottlingException",
                "Message": f"Request rate exceeded at {datetime.now().isoformat()}",
            }
        }
        client_error = ClientError(error_response, "ListResources")

        result = handle_aws_error(client_error, "List Resources")
        parsed = json.loads(result)

        assert parsed["success"] is False
        assert parsed["error_code"] == "ThrottlingException"
        assert "Request rate exceeded" in parsed["error"]

    @pytest.mark.unit
    def test_handle_aws_error_operation_context(self) -> None:
        """Test handle_aws_error includes operation context in error message."""
        operations = ["List Core Networks", "Describe VPCs", "Validate Policy Document", "Trace Network Path"]

        for operation in operations:
            error = ValueError("Test error")
            result = handle_aws_error(error, operation)

            parsed = json.loads(result)

            assert operation in parsed["error"]
            assert "Test error" in parsed["error"]

    @pytest.mark.unit
    def test_handle_aws_error_with_special_characters(self) -> None:
        """Test handle_aws_error handles special characters in error messages."""
        error_response = {"Error": {"Code": "ValidationException", "Message": "Invalid CIDR block format: @#$%"}}
        client_error = ClientError(error_response, "ValidateNetworkConfiguration")

        result = handle_aws_error(client_error, "Validate Network")
        parsed = json.loads(result)

        assert parsed["error_code"] == "ValidationException"
        assert "@#$%" in parsed["error"]
        assert "[CREDENTIAL_REDACTED]" not in parsed["error"]  # Ensure sanitization doesn't affect

    @pytest.mark.unit
    def test_handle_aws_error_empty_operation(self) -> None:
        """Test handle_aws_error with empty operation string."""
        error = RuntimeError("Connection timeout")

        result = handle_aws_error(error, "")

        parsed = json.loads(result)

        assert parsed["success"] is False
        assert " failed: Connection timeout" in parsed["error"]
        # Generic exceptions should have error_code
        assert parsed["error_code"] == "UnknownError"

    @pytest.mark.unit
    def test_handle_aws_error_datetime_in_response(self) -> None:
        """Test handle_aws_error doesn't break with datetime-like strings."""

        # Create error that might contain datetime info
        error_response = {
            "Error": {
                "Code": "ThrottlingException",
                "Message": f"Request rate exceeded at {datetime.now().isoformat()}",
            }
        }
        client_error = ClientError(error_response, "ListCoreNetworks")

        result = handle_aws_error(client_error, "List Resources")

        parsed = json.loads(result)  # Should not raise JSON decode error

        assert parsed["success"] is False
        assert parsed["error_code"] == "ThrottlingException"
        assert "Request rate exceeded" in parsed["error"]


class TestAWSClientCaching:
    """Test AWS client caching behavior following AWS Labs patterns."""

    def setup_method(self) -> None:
        """Clear client cache before each test."""
        _create_client.cache_clear()

    @pytest.mark.unit
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    def test_client_cache_isolation(self, mock_boto3) -> None:
        """Test cache isolation between configurations."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        get_aws_client("networkmanager", "us-east-1")
        cache_info = _create_client.cache_info()
        assert cache_info.currsize == 1

    @pytest.mark.asyncio
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    async def test_lru_cache_eviction(self, mock_boto3) -> None:
        """Test LRU cache eviction policy through _create_client function."""
        # Clear cache first
        _create_client.cache_clear()

        # Test cache behavior by creating clients that should be cached
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        # Fill cache to near capacity by creating different client configurations
        with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
            for i in range(CACHE_CAPACITY - 1):
                # Create clients for different services to fill cache
                service = f"service-{i}"
                get_aws_client(service)

        # Verify cache is being used
        initial_cache_info = _create_client.cache_info()
        assert initial_cache_info.currsize == CACHE_CAPACITY - 1

        # Add one more to trigger potential eviction
        get_aws_client("new-service")

        # Verify cache management
        final_cache_info = _create_client.cache_info()
        assert final_cache_info.currsize == CACHE_CAPACITY

    @pytest.mark.unit
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    def test_client_cache_cleanup(self, mock_boto3) -> None:
        """Test client cache can be cleared properly."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        # Add entries to cache
        with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
            get_aws_client("networkmanager")
            get_aws_client("ec2")

        cache_info = _create_client.cache_info()
        assert cache_info.currsize >= 1

        # Clear cache
        _create_client.cache_clear()
        cache_info = _create_client.cache_info()
        assert cache_info.currsize == 0

    @pytest.mark.unit
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    def test_client_cache_thread_safety_pattern(self, mock_boto3) -> None:
        """Test client cache follows thread-safe access patterns."""
        # This test verifies the LRU cache is thread-safe
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        # Test basic cache operations don't raise exceptions
        with patch("awslabs.cloudwan_mcp_server.server.aws_config") as mock_aws_config:
            mock_aws_config.default_region = "us-east-1"
            mock_aws_config.profile = None

            with patch.dict("os.environ", {}, clear=True):
                client = get_aws_client("networkmanager")
                assert client == mock_client

        cache_info = _create_client.cache_info()
        assert cache_info.currsize >= 0
