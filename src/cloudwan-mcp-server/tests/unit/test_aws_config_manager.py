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


"""Unit tests for AWS configuration manager tool."""

import json
import os
from typing import Generator
from unittest.mock import Mock, patch

import pytest

from awslabs.cloudwan_mcp_server.server import _create_client, aws_config_manager, get_aws_client


def _setup_test_environment(profile: str | None = None, region: str | None = None) -> None:
    """Helper to manage test environment variables."""
    import os

    os.environ.clear()
    if profile:
        os.environ["AWS_PROFILE"] = profile
    if region:
        os.environ["AWS_DEFAULT_REGION"] = region
    os.environ.setdefault("AWS_PROFILE", "default")
    os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")


class TestAWSConfigManager:
    """Test cases for AWS configuration manager."""

    CACHE_CAPACITY = 10  # Required for LRU cache tests

    @pytest.fixture(autouse=True)
    def reset_environment(self) -> Generator:
        """Reset environment after each test."""
        _setup_test_environment()
        yield
        _create_client.cache_clear()

    @pytest.fixture
    def mock_boto3_session(self) -> Generator:
        """Mock boto3 session."""
        with patch("boto3.Session") as mock_session:
            mock_instance = Mock()
            mock_session.return_value = mock_instance

            # Mock STS client
            mock_sts = Mock()
            mock_sts.get_caller_identity.return_value = {
                "Account": "123456789012",
                "UserId": "test-user-id",
                "Arn": "arn:aws:iam::123456789012:user/test-user",
            }

            # Mock EC2 client
            mock_ec2 = Mock()
            mock_ec2.describe_regions.return_value = {
                "Regions": [
                    {"RegionName": "us-east-1"},
                    {"RegionName": "us-west-2"},
                    {"RegionName": "eu-west-1"},
                ]
            }

            mock_instance.client.side_effect = lambda service, **kwargs: {"sts": mock_sts, "ec2": mock_ec2}.get(
                service, Mock()
            )

            yield mock_session

    @pytest.fixture
    def mock_get_aws_client(self) -> Generator:
        """Mock the get_aws_client function."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:
            mock_sts = Mock()
            mock_sts.get_caller_identity.return_value = {
                "Account": "123456789012",
                "UserId": "test-user-id",
                "Arn": "arn:aws:iam::123456789012:user/test-user",
            }

            mock_ec2 = Mock()
            mock_ec2.describe_regions.return_value = {
                "Regions": [{"RegionName": "us-east-1"}, {"RegionName": "us-west-2"}]
            }

            mock_nm = Mock()
            mock_nm.describe_global_networks.return_value = {"GlobalNetworks": [{"GlobalNetworkId": "gn-123"}]}

            def client_side_effect(service, region=None):
                return {"sts": mock_sts, "ec2": mock_ec2, "networkmanager": mock_nm}.get(service, Mock())

            mock_client.side_effect = client_side_effect
            yield mock_client

    @pytest.mark.asyncio
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    async def test_get_current_configuration_success(self, mock_boto3: Mock, mock_get_aws_client: Generator) -> None:
        """Test getting current AWS configuration successfully."""
        # Clear cache for clean test
        _create_client.cache_clear()

        # Patch aws_config to return test values
        with patch("awslabs.cloudwan_mcp_server.server.aws_config") as mock_aws_config:
            mock_aws_config.profile = "test-profile"
            mock_aws_config.default_region = "us-west-2"

            with patch.dict(os.environ, {"AWS_PROFILE": "test-profile", "AWS_DEFAULT_REGION": "us-west-2"}, clear=True):
                result = await aws_config_manager("get_current")

        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["operation"] == "get_current"
        assert result_data["current_configuration"]["aws_profile"] == "test-profile"
        assert result_data["current_configuration"]["aws_region"] == "us-west-2"
        assert result_data["current_configuration"]["configuration_valid"] is True
        assert "identity" in result_data["current_configuration"]
        assert "account" in result_data["current_configuration"]["identity"]
        assert "user_id" in result_data["current_configuration"]["identity"]

    @pytest.mark.asyncio
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    async def test_get_current_configuration_invalid(self, mock_boto3: Mock) -> None:
        """Test getting current configuration with invalid credentials."""
        _create_client.cache_clear()

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:
            mock_client.side_effect = Exception("Invalid credentials")

            with patch.dict(os.environ, {"AWS_PROFILE": "invalid-profile"}):
                result = await aws_config_manager("get_current")

        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["current_configuration"]["configuration_valid"] is False
        assert "error" in result_data["current_configuration"]["identity"]

    @pytest.mark.asyncio
    async def test_set_profile_success(self, mock_boto3_session: Generator) -> None:
        """Test setting AWS profile successfully."""
        _create_client.cache_clear()

        result = await aws_config_manager("set_profile", profile="new-profile")
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["operation"] == "set_profile"
        assert result_data["new_profile"] == "new-profile"
        assert result_data["profile_valid"] is True
        assert result_data["cache_cleared"] is True
        assert "identity" in result_data
        assert result_data["identity"]["account"] == "123456789012"
        assert os.environ.get("AWS_PROFILE") == "new-profile"

    @pytest.mark.asyncio
    async def test_set_profile_missing_parameter(self) -> None:
        """Test setting profile without providing profile name."""
        result = await aws_config_manager("set_profile")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "Profile name is required" in result_data["error"]

    @pytest.mark.asyncio
    async def test_set_profile_invalid(self) -> None:
        """Test setting invalid AWS profile."""
        with patch("boto3.Session") as mock_session:
            mock_session.side_effect = Exception("Profile not found")

            result = await aws_config_manager("set_profile", profile="invalid-profile")
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "Failed to validate profile" in result_data["error"]
            assert "suggestion" in result_data

    @pytest.mark.asyncio
    async def test_set_region_success(self, mock_boto3_session: Generator) -> None:
        """Test setting AWS region successfully."""
        _create_client.cache_clear()

        result = await aws_config_manager("set_region", region="eu-west-1")
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["operation"] == "set_region"
        assert result_data["new_region"] == "eu-west-1"
        assert result_data["region_valid"] is True
        assert result_data["cache_cleared"] is True
        assert os.environ.get("AWS_DEFAULT_REGION") == "eu-west-1"

    @pytest.mark.asyncio
    async def test_set_region_invalid_format(self) -> None:
        """Test setting region with invalid format."""
        result = await aws_config_manager("set_region", region="INVALID_REGION!")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "Invalid region format" in result_data["error"]
        assert "suggestion" in result_data

    @pytest.mark.asyncio
    async def test_set_region_missing_parameter(self) -> None:
        """Test setting region without providing region name."""
        result = await aws_config_manager("set_region")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "Region name is required" in result_data["error"]

    @pytest.mark.asyncio
    async def test_set_both_success(self, mock_boto3_session: Generator) -> None:
        """Test setting both profile and region successfully."""
        _create_client.cache_clear()

        result = await aws_config_manager("set_both", profile="test-profile", region="us-east-1")
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["operation"] == "set_both"
        assert result_data["new_profile"] == "test-profile"
        assert result_data["new_region"] == "us-east-1"
        assert result_data["cache_cleared"] is True
        assert os.environ.get("AWS_PROFILE") == "test-profile"
        assert os.environ.get("AWS_DEFAULT_REGION") == "us-east-1"

    @pytest.mark.asyncio
    async def test_set_both_missing_parameters(self) -> None:
        """Test setting both with missing parameters."""
        result = await aws_config_manager("set_both", profile="test-profile")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "Both profile and region are required" in result_data["error"]

    @pytest.mark.asyncio
    async def test_validate_config_success(self, mock_get_aws_client: Generator) -> None:
        """Test validating configuration successfully."""
        with patch.dict(os.environ, {"AWS_PROFILE": "test-profile", "AWS_DEFAULT_REGION": "us-east-1"}):
            result = await aws_config_manager("validate_config")

        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["operation"] == "validate_config"
        assert result_data["overall_status"] == "valid"
        assert result_data["service_validations"]["sts"]["status"] == "success"
        assert result_data["service_validations"]["ec2"]["status"] == "success"
        assert result_data["service_validations"]["networkmanager"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_validate_config_partial_failure(self) -> None:
        """Test validation with some services failing."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:

            def failing_client(service, region=None):
                if service == "sts":
                    mock_sts = Mock()
                    mock_sts.get_caller_identity.return_value = {
                        "Account": "123456789012",
                        "UserId": "test",
                        "Arn": "test-arn",
                    }
                    return mock_sts
                else:
                    raise Exception("Service unavailable")

            mock_client.side_effect = failing_client

            result = await aws_config_manager("validate_config")
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert result_data["overall_status"] == "invalid"
            assert result_data["service_validations"]["sts"]["status"] == "success"
            assert result_data["service_validations"]["ec2"]["status"] == "failed"

    @pytest.mark.asyncio
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    async def test_clear_cache_success(self, mock_boto3: Mock, mock_get_aws_client: Generator) -> None:
        """Test clearing AWS client cache."""
        _create_client.cache_clear()

        # Add some mock entries to cache
        # Add items to cache by using the client functions
        get_aws_client("networkmanager", "us-east-1")
        get_aws_client("ec2", "us-west-2")

        result = await aws_config_manager("clear_cache")
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["operation"] == "clear_cache"
        assert result_data["cache_entries_cleared"] == "LRU cache cleared"
        cache_info = _create_client.cache_info()
        assert cache_info.currsize == 0
        assert "message" in result_data

    @pytest.mark.asyncio
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    async def test_lru_cache_eviction(self, mock_boto3: Mock) -> None:
        """Test LRU cache eviction policy through _create_client function."""
        _create_client.cache_clear()

        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
            for i in range(self.CACHE_CAPACITY - 1):
                service = f"service-{i}"
                get_aws_client(service)

        initial_cache_info = _create_client.cache_info()
        assert initial_cache_info.currsize == self.CACHE_CAPACITY - 1

        get_aws_client("new-service")

        final_cache_info = _create_client.cache_info()
        assert final_cache_info.currsize == self.CACHE_CAPACITY

    @pytest.mark.asyncio
    async def test_unknown_operation(self) -> None:
        """Test handling unknown operation."""
        result = await aws_config_manager("unknown_operation")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "Unknown operation" in result_data["error"]
        assert "supported_operations" in result_data and isinstance(result_data["supported_operations"], list)
        assert sorted(result_data["supported_operations"]) == [
            "clear_cache",
            "get_config_history",
            "get_current",
            "restore_last_config",
            "set_both",
            "set_profile",
            "set_region",
            "validate_config",
            "validate_persistence",
        ]  # Corrected list

    @pytest.mark.asyncio
    async def test_exception_handling(self) -> None:
        """Test general exception handling."""
        # Mock the aws_config to raise an exception during access
        with patch("awslabs.cloudwan_mcp_server.server.aws_config") as mock_aws_config:
            # Make the profile property raise an exception when accessed
            type(mock_aws_config).profile = property(lambda self: (_ for _ in ()).throw(Exception("Unexpected error")))

            result = await aws_config_manager("get_current")
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "Unexpected error" in result_data["error"]  # noqa: S101
            assert result_data["error_code"] == "UnknownError"
