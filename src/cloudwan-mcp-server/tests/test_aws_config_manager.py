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

"""Comprehensive tests for AWS Config Manager."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from awslabs.cloudwan_mcp_server.utils.aws_config_manager import (
    get_aws_config,
    get_aws_client
)


class TestAWSConfigManager:
    """Test cases for AWSConfigManager."""

    def setup_method(self):
        """Set up test environment."""
        # Clear any existing singleton
        global _aws_config_instance
        _aws_config_instance = None
        
    def test_singleton_pattern(self):
        """Test that AWSConfigManager follows singleton pattern."""
        config1 = get_aws_config()
        config2 = get_aws_config()
        
        assert config1 is config2, "AWSConfigManager should be a singleton"
        
    def test_default_initialization(self):
        """Test default configuration values."""
        config = AWSConfigManager()
        
        assert config.default_region == "us-west-2"
        assert config.profile is None
        assert config.debug is False
        
    @patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'eu-west-1', 'AWS_PROFILE': 'test-profile'})
    def test_environment_variable_initialization(self):
        """Test initialization from environment variables."""
        config = AWSConfigManager()
        
        assert config.default_region == "eu-west-1"
        assert config.profile == "test-profile"
        
    def test_set_profile_validation(self):
        """Test profile validation."""
        config = AWSConfigManager()
        
        # Valid profile names
        assert config.set_profile("dev") is True
        assert config.set_profile("production-profile") is True
        assert config.set_profile("test_123") is True
        
        # Invalid profile names
        assert config.set_profile("") is False
        assert config.set_profile("profile with spaces") is False
        assert config.set_profile("profile@invalid") is False
        
    def test_set_region_validation(self):
        """Test region validation."""
        config = AWSConfigManager()
        
        # Valid regions
        assert config.set_region("us-east-1") is True
        assert config.set_region("eu-central-1") is True
        assert config.set_region("ap-southeast-2") is True
        
        # Invalid regions
        assert config.set_region("") is False
        assert config.set_region("invalid-region") is False
        assert config.set_region("us-east") is False
        
    def test_set_profile_updates_profile(self):
        """Test that set_profile actually updates the profile."""
        config = AWSConfigManager()
        
        config.set_profile("new-profile")
        assert config.profile == "new-profile"
        
    def test_set_region_updates_region(self):
        """Test that set_region actually updates the region."""
        config = AWSConfigManager()
        
        config.set_region("us-east-1")
        assert config.default_region == "us-east-1"
        
    def test_to_dict(self):
        """Test configuration serialization."""
        config = AWSConfigManager()
        config.set_profile("test-profile")
        config.set_region("us-east-1")
        
        config_dict = config.to_dict()
        
        expected = {
            "profile": "test-profile",
            "default_region": "us-east-1",
            "debug": False
        }
        
        assert config_dict == expected


class TestAWSConfigManagerTool:
    """Test cases for the aws_config_manager MCP tool."""
    
    def setup_method(self):
        """Set up test environment."""
        # Reset singleton
        global _aws_config_instance
        _aws_config_instance = None
        
    @pytest.mark.asyncio
    async def test_get_current_operation(self):
        """Test get_current operation."""
        result_str = await aws_config_manager("get_current")
        result = json.loads(result_str)
        
        assert result["status"] == "success"
        assert "current_profile" in result["data"]
        assert "current_region" in result["data"]
        assert "debug" in result["data"]
        
    @pytest.mark.asyncio
    async def test_set_profile_operation(self):
        """Test set_profile operation."""
        result_str = await aws_config_manager("set_profile", profile="test-profile")
        result = json.loads(result_str)
        
        assert result["status"] == "success"
        assert result["data"]["profile_updated"] is True
        
        # Verify the profile was actually set
        config = get_aws_config()
        assert config.profile == "test-profile"
        
    @pytest.mark.asyncio
    async def test_set_profile_invalid(self):
        """Test set_profile operation with invalid profile."""
        result_str = await aws_config_manager("set_profile", profile="invalid profile")
        result = json.loads(result_str)
        
        assert result["status"] == "error"
        assert "invalid profile name" in result["error"].lower()
        
    @pytest.mark.asyncio
    async def test_set_region_operation(self):
        """Test set_region operation."""
        result_str = await aws_config_manager("set_region", region="eu-west-1")
        result = json.loads(result_str)
        
        assert result["status"] == "success"
        assert result["data"]["region_updated"] is True
        
        # Verify the region was actually set
        config = get_aws_config()
        assert config.default_region == "eu-west-1"
        
    @pytest.mark.asyncio
    async def test_set_region_invalid(self):
        """Test set_region operation with invalid region."""
        result_str = await aws_config_manager("set_region", region="invalid-region")
        result = json.loads(result_str)
        
        assert result["status"] == "error"
        assert "invalid region format" in result["error"].lower()
        
    @pytest.mark.asyncio
    async def test_set_both_operation(self):
        """Test set_both operation."""
        result_str = await aws_config_manager(
            "set_both", 
            profile="production", 
            region="us-east-1"
        )
        result = json.loads(result_str)
        
        assert result["status"] == "success"
        assert result["data"]["profile_updated"] is True
        assert result["data"]["region_updated"] is True
        
        # Verify both were actually set
        config = get_aws_config()
        assert config.profile == "production"
        assert config.default_region == "us-east-1"
        
    @pytest.mark.asyncio
    async def test_validate_config_operation(self):
        """Test validate_config operation."""
        result_str = await aws_config_manager("validate_config")
        result = json.loads(result_str)
        
        assert result["status"] == "success"
        assert "validation" in result["data"]
        assert "profile_valid" in result["data"]["validation"]
        assert "region_valid" in result["data"]["validation"]
        
    @pytest.mark.asyncio
    async def test_clear_cache_operation(self):
        """Test clear_cache operation."""
        result_str = await aws_config_manager("clear_cache")
        result = json.loads(result_str)
        
        assert result["status"] == "success"
        assert "cache_cleared" in result["data"]
        
    @pytest.mark.asyncio
    async def test_invalid_operation(self):
        """Test invalid operation."""
        result_str = await aws_config_manager("invalid_operation")
        result = json.loads(result_str)
        
        assert result["status"] == "error"
        assert "unsupported operation" in result["error"].lower()
        
    @pytest.mark.asyncio
    async def test_missing_required_parameters(self):
        """Test operations with missing required parameters."""
        # set_profile without profile parameter
        result_str = await aws_config_manager("set_profile")
        result = json.loads(result_str)
        assert result["status"] == "error"
        
        # set_region without region parameter
        result_str = await aws_config_manager("set_region")
        result = json.loads(result_str)
        assert result["status"] == "error"
        
    @pytest.mark.asyncio
    async def test_set_both_partial_failure(self):
        """Test set_both with one valid and one invalid parameter."""
        result_str = await aws_config_manager(
            "set_both", 
            profile="valid-profile", 
            region="invalid-region"
        )
        result = json.loads(result_str)
        
        assert result["status"] == "success"  # Partial success
        assert result["data"]["profile_updated"] is True
        assert result["data"]["region_updated"] is False
        
    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test concurrent access to configuration manager."""
        import asyncio
        
        async def set_profile_task(profile_name):
            return await aws_config_manager("set_profile", profile=profile_name)
            
        # Run multiple profile updates concurrently
        tasks = [
            set_profile_task(f"profile-{i}")
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All operations should succeed
        for result_str in results:
            result = json.loads(result_str)
            assert result["status"] == "success"
            
        # Final profile should be one of the set profiles
        config = get_aws_config()
        assert config.profile.startswith("profile-")
        
    @pytest.mark.asyncio
    @patch('awslabs.cloudwan_mcp_server.utils.aws_config_manager.get_aws_client')
    async def test_cache_integration(self, mock_get_client):
        """Test integration with AWS client cache."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # Set initial configuration
        await aws_config_manager("set_profile", profile="test-profile")
        await aws_config_manager("set_region", region="us-east-1")
        
        # Clear cache should work without errors
        result_str = await aws_config_manager("clear_cache")
        result = json.loads(result_str)
        
        assert result["status"] == "success"
        
    @pytest.mark.asyncio
    async def test_config_history_tracking(self):
        """Test that configuration changes are tracked."""
        # Make several configuration changes
        await aws_config_manager("set_profile", profile="profile-1")
        await aws_config_manager("set_region", region="us-east-1")
        await aws_config_manager("set_profile", profile="profile-2")
        
        # Get configuration history
        result_str = await aws_config_manager("get_config_history")
        result = json.loads(result_str)
        
        assert result["status"] == "success"
        assert "history" in result["data"]
        
    @pytest.mark.asyncio
    async def test_error_handling_exception(self):
        """Test proper error handling when exceptions occur."""
        # Mock an internal error
        with patch('awslabs.cloudwan_mcp_server.utils.aws_config_manager.get_aws_config') as mock_get_config:
            mock_get_config.side_effect = Exception("Internal error")
            
            result_str = await aws_config_manager("get_current")
            result = json.loads(result_str)
            
            assert result["status"] == "error"
            assert "failed to execute" in result["error"].lower()
            
    def test_profile_name_security(self):
        """Test that profile names are properly validated for security."""
        config = AWSConfigManager()
        
        # Test injection attempts
        malicious_profiles = [
            "profile; rm -rf /",
            "profile && echo vulnerable",
            "profile | cat /etc/passwd",
            "profile`whoami`",
            "profile$(id)",
            "../../../etc/passwd",
            "NUL",
            "CON"
        ]
        
        for malicious_profile in malicious_profiles:
            assert config.set_profile(malicious_profile) is False, f"Should reject malicious profile: {malicious_profile}"
            
    def test_region_name_security(self):
        """Test that region names are properly validated for security."""
        config = AWSConfigManager()
        
        # Test injection attempts
        malicious_regions = [
            "us-east-1; rm -rf /",
            "us-east-1 && echo vulnerable", 
            "us-east-1 | cat /etc/passwd",
            "../../../etc/passwd",
            "us-east-1`whoami`"
        ]
        
        for malicious_region in malicious_regions:
            assert config.set_region(malicious_region) is False, f"Should reject malicious region: {malicious_region}"