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

"""Comprehensive unit tests for AWS configuration manager with enhanced coverage."""

import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

from awslabs.cloudwan_mcp_server.server import aws_config_manager, _create_client


class TestAWSConfigManagerComprehensive:
    """Comprehensive test suite for AWS configuration manager covering all edge cases."""

    @pytest.fixture
    def mock_config_persistence_available(self):
        """Mock config persistence as available."""
        with patch('awslabs.cloudwan_mcp_server.server.config_persistence') as mock_cp:
            # Mock as real ConfigPersistence, not MockConfigPersistence
            mock_cp.__class__.__name__ = "ConfigPersistence"
            mock_cp.save_current_config.return_value = True
            mock_cp.load_current_config.return_value = {
                'aws_profile': 'test-profile',
                'aws_region': 'us-east-1'
            }
            mock_cp.get_config_history.return_value = [
                {'timestamp': '2024-01-01', 'profile': 'test-profile', 'region': 'us-east-1'}
            ]
            mock_cp.validate_config_file.return_value = {'valid': True}
            mock_cp.restore_config.return_value = True
            yield mock_cp

    @pytest.fixture
    def mock_config_persistence_unavailable(self):
        """Mock config persistence as unavailable (MockConfigPersistence)."""
        with patch('awslabs.cloudwan_mcp_server.server.config_persistence') as mock_cp:
            # Mock as MockConfigPersistence
            mock_cp.__class__.__name__ = "MockConfigPersistence"
            mock_cp.save_current_config.return_value = False
            mock_cp.load_current_config.return_value = None
            mock_cp.get_config_history.return_value = []
            mock_cp.validate_config_file.return_value = {
                'valid': False,
                'error': 'Config persistence module not available'
            }
            mock_cp.restore_config.return_value = False
            yield mock_cp

    @pytest.fixture  
    def mock_aws_clients(self):
        """Mock AWS clients with comprehensive responses."""
        mock_clients = {}
        
        # STS client mock
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'UserId': 'AIDACKCEVSQ6C2EXAMPLE',
            'Arn': 'arn:aws:iam::123456789012:user/test-user'
        }
        mock_clients['sts'] = mock_sts
        
        # EC2 client mock  
        mock_ec2 = Mock()
        mock_ec2.describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'},
                {'RegionName': 'us-west-2'},
                {'RegionName': 'eu-west-1'},
                {'RegionName': 'ap-southeast-1'}
            ]
        }
        mock_clients['ec2'] = mock_ec2
        
        # NetworkManager client mock
        mock_nm = Mock()
        mock_nm.describe_global_networks.return_value = {
            'GlobalNetworks': [
                {
                    'GlobalNetworkId': 'gn-12345',
                    'State': 'AVAILABLE'
                }
            ]
        }
        mock_clients['networkmanager'] = mock_nm
        
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            mock_get_client.side_effect = lambda service, region=None: mock_clients[service]
            yield mock_clients

    @pytest.fixture
    def mock_boto3_session(self):
        """Mock boto3 Session creation."""
        with patch('boto3.Session') as mock_session:
            mock_instance = Mock()
            mock_session.return_value = mock_instance
            
            # Configure mock clients
            mock_sts = Mock()
            mock_sts.get_caller_identity.return_value = {
                'Account': '123456789012', 
                'UserId': 'test-user',
                'Arn': 'arn:aws:iam::123456789012:user/test'
            }
            
            mock_ec2 = Mock()
            mock_ec2.describe_regions.return_value = {
                'Regions': [
                    {'RegionName': 'us-east-1'},
                    {'RegionName': 'us-west-2'}
                ]
            }
            
            mock_instance.client.side_effect = lambda service, **kwargs: {
                'sts': mock_sts,
                'ec2': mock_ec2
            }.get(service, Mock())
            
            yield mock_session

    def setup_method(self):
        """Clear cache before each test."""
        _create_client.cache_clear()

    @pytest.mark.asyncio
    async def test_get_current_with_config_persistence_available(self, mock_aws_clients, mock_config_persistence_available):
        """Test get_current operation when config persistence is available."""
        with patch.dict(os.environ, {'AWS_PROFILE': 'test-profile', 'AWS_DEFAULT_REGION': 'us-east-1'}):
            result = await aws_config_manager("get_current")
            
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["operation"] == "get_current"
        assert result_data["current_configuration"]["aws_profile"] == "test-profile"
        assert result_data["current_configuration"]["aws_region"] == "us-east-1"
        assert result_data["current_configuration"]["configuration_valid"] is True
        assert result_data["current_configuration"]["config_persistence_available"] is True
        assert "identity" in result_data["current_configuration"]

    @pytest.mark.asyncio
    async def test_get_current_with_config_persistence_unavailable(self, mock_aws_clients, mock_config_persistence_unavailable):
        """Test get_current operation when config persistence is unavailable."""
        with patch.dict(os.environ, {'AWS_PROFILE': 'test-profile', 'AWS_DEFAULT_REGION': 'us-east-1'}):
            result = await aws_config_manager("get_current")
            
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["current_configuration"]["config_persistence_available"] is False

    @pytest.mark.asyncio
    async def test_get_current_with_invalid_credentials(self, mock_config_persistence_available):
        """Test get_current with invalid AWS credentials."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_client:
            mock_client.side_effect = Exception("Invalid credentials")
            
            result = await aws_config_manager("get_current")
            result_data = json.loads(result)
            
            assert result_data["success"] is True
            assert result_data["current_configuration"]["configuration_valid"] is False
            assert "error" in result_data["current_configuration"]["identity"]

    @pytest.mark.asyncio
    async def test_set_profile_success_with_persistence(self, mock_boto3_session, mock_config_persistence_available):
        """Test successful profile setting with config persistence."""
        with patch('awslabs.cloudwan_mcp_server.server.secure_environment_update', return_value=True):
            result = await aws_config_manager("set_profile", profile="new-test-profile")
            
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["operation"] == "set_profile"
        assert result_data["new_profile"] == "new-test-profile"
        assert result_data["profile_valid"] is True
        assert result_data["config_persisted"] is True
        assert result_data["persistence_available"] is True
        assert result_data["cache_cleared"] is True

    @pytest.mark.asyncio
    async def test_set_profile_success_without_persistence(self, mock_boto3_session, mock_config_persistence_unavailable):
        """Test successful profile setting without config persistence."""
        with patch('awslabs.cloudwan_mcp_server.server.secure_environment_update', return_value=True):
            result = await aws_config_manager("set_profile", profile="new-test-profile")
            
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["config_persisted"] is False
        assert result_data["persistence_available"] is False

    @pytest.mark.asyncio
    async def test_set_profile_missing_parameter(self):
        """Test set_profile without providing profile name."""
        result = await aws_config_manager("set_profile")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "Profile name is required" in result_data["error"]

    @pytest.mark.asyncio
    async def test_set_profile_invalid_profile(self):
        """Test set_profile with invalid profile name."""
        with patch('boto3.Session') as mock_session:
            mock_session.side_effect = Exception("Profile not found")
            
            result = await aws_config_manager("set_profile", profile="invalid-profile")
            result_data = json.loads(result)
            
            assert result_data["success"] is False
            assert "Failed to validate profile" in result_data["error"]
            assert "suggestion" in result_data

    @pytest.mark.asyncio
    async def test_set_profile_environment_update_failure(self, mock_boto3_session):
        """Test set_profile when environment variable update fails."""
        with patch('awslabs.cloudwan_mcp_server.server.secure_environment_update', return_value=False):
            result = await aws_config_manager("set_profile", profile="test-profile")
            
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "Failed to update AWS_PROFILE environment variable" in result_data["error"]

    @pytest.mark.asyncio
    async def test_set_region_success(self, mock_boto3_session, mock_config_persistence_available):
        """Test successful region setting."""
        with patch('awslabs.cloudwan_mcp_server.server.secure_environment_update', return_value=True):
            result = await aws_config_manager("set_region", region="us-west-2")
            
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["operation"] == "set_region"
        assert result_data["new_region"] == "us-west-2"
        assert result_data["region_valid"] is True
        assert result_data["cache_cleared"] is True

    @pytest.mark.asyncio
    async def test_set_region_missing_parameter(self):
        """Test set_region without providing region name."""
        result = await aws_config_manager("set_region")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "Region name is required" in result_data["error"]

    @pytest.mark.asyncio
    async def test_set_region_invalid_format(self):
        """Test set_region with invalid region format."""
        result = await aws_config_manager("set_region", region="INVALID_REGION!")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "Invalid region format" in result_data["error"]
        assert "suggestion" in result_data

    @pytest.mark.asyncio
    async def test_set_region_unavailable_region(self, mock_boto3_session):
        """Test set_region with region not in available regions list."""
        # Mock EC2 to return limited regions
        mock_instance = mock_boto3_session.return_value
        mock_ec2 = mock_instance.client.return_value
        mock_ec2.describe_regions.return_value = {
            'Regions': [{'RegionName': 'us-east-1'}]  # Only us-east-1 available
        }
        
        result = await aws_config_manager("set_region", region="ap-south-1")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "is not available or accessible" in result_data["error"]
        assert "available_regions" in result_data

    @pytest.mark.asyncio
    async def test_set_both_success(self, mock_boto3_session, mock_config_persistence_available):
        """Test successful setting of both profile and region."""
        with patch('awslabs.cloudwan_mcp_server.server.secure_environment_update', return_value=True):
            result = await aws_config_manager("set_both", profile="test-profile", region="us-east-1")
            
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["operation"] == "set_both"
        assert result_data["new_profile"] == "test-profile"
        assert result_data["new_region"] == "us-east-1"
        assert result_data["cache_cleared"] is True
        assert result_data["config_persisted"] is True

    @pytest.mark.asyncio
    async def test_set_both_missing_parameters(self):
        """Test set_both with missing parameters."""
        result = await aws_config_manager("set_both", profile="test-profile")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "Both profile and region are required" in result_data["error"]

    @pytest.mark.asyncio
    async def test_validate_config_success(self, mock_aws_clients):
        """Test successful configuration validation."""
        result = await aws_config_manager("validate_config")
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["operation"] == "validate_config"
        assert result_data["overall_status"] == "valid"
        assert result_data["service_validations"]["sts"]["status"] == "success"
        assert result_data["service_validations"]["ec2"]["status"] == "success"
        assert result_data["service_validations"]["networkmanager"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_validate_config_partial_failure(self):
        """Test configuration validation with some services failing."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_client:
            def failing_client(service, region=None):
                if service == "sts":
                    mock_sts = Mock()
                    mock_sts.get_caller_identity.return_value = {
                        'Account': '123456789012',
                        'UserId': 'test',
                        'Arn': 'test-arn'
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
    async def test_clear_cache_success(self, mock_aws_clients):
        """Test clearing AWS client cache."""
        # Add items to cache by calling get_aws_client
        from awslabs.cloudwan_mcp_server.server import get_aws_client
        get_aws_client("networkmanager", "us-east-1")
        get_aws_client("ec2", "us-west-2")
        
        result = await aws_config_manager("clear_cache")
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["operation"] == "clear_cache"
        assert result_data["cache_entries_cleared"] >= 0  # May vary based on test execution
        
        # Verify cache is cleared
        cache_info = _create_client.cache_info()
        assert cache_info.currsize == 0

    @pytest.mark.asyncio
    async def test_get_config_history_with_persistence(self, mock_config_persistence_available):
        """Test getting config history when persistence is available."""
        result = await aws_config_manager("get_config_history")
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["operation"] == "get_config_history"
        assert "history_count" in result_data
        assert "history" in result_data

    @pytest.mark.asyncio
    async def test_get_config_history_without_persistence(self, mock_config_persistence_unavailable):
        """Test getting config history when persistence is unavailable."""
        result = await aws_config_manager("get_config_history")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "Configuration persistence is not available" in result_data["error"]
        assert "reason" in result_data

    @pytest.mark.asyncio
    async def test_validate_persistence_with_available_persistence(self, mock_config_persistence_available):
        """Test persistence validation when persistence is available."""
        result = await aws_config_manager("validate_persistence")
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["operation"] == "validate_persistence"
        assert "validation" in result_data
        assert result_data["persistence_type"] == "ConfigPersistence"

    @pytest.mark.asyncio
    async def test_validate_persistence_with_unavailable_persistence(self, mock_config_persistence_unavailable):
        """Test persistence validation when persistence is unavailable."""
        result = await aws_config_manager("validate_persistence")
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["persistence_type"] == "MockConfigPersistence"
        assert result_data["validation"]["valid"] is False

    @pytest.mark.asyncio
    async def test_restore_last_config_with_persistence(self, mock_config_persistence_available):
        """Test restoring last config when persistence is available."""
        result = await aws_config_manager("restore_last_config")
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["operation"] == "restore_last_config"
        assert "restored_config" in result_data
        assert result_data["cache_cleared"] is True

    @pytest.mark.asyncio
    async def test_restore_last_config_without_persistence(self, mock_config_persistence_unavailable):
        """Test restoring last config when persistence is unavailable."""
        result = await aws_config_manager("restore_last_config")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "Configuration persistence is not available" in result_data["error"]

    @pytest.mark.asyncio
    async def test_unknown_operation(self):
        """Test handling unknown operation."""
        result = await aws_config_manager("unknown_operation")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "Unknown operation" in result_data["error"]
        assert "supported_operations" in result_data

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test general exception handling."""
        with patch('os.getenv') as mock_getenv:
            mock_getenv.side_effect = Exception("Unexpected system error")
            
            result = await aws_config_manager("get_current")
            result_data = json.loads(result)
            
            # Should handle the exception gracefully
            assert "success" in result_data
            assert "error" in result_data

    @pytest.mark.asyncio
    async def test_lru_cache_behavior(self, mock_aws_clients):
        """Test that LRU cache behavior works correctly."""
        from awslabs.cloudwan_mcp_server.server import get_aws_client
        
        # Clear cache first
        _create_client.cache_clear()
        
        # Create multiple clients to test caching
        client1 = get_aws_client("sts", "us-east-1")
        client2 = get_aws_client("sts", "us-east-1")  # Should use cache
        client3 = get_aws_client("ec2", "us-west-2")  # Different service/region
        
        cache_info = _create_client.cache_info()
        assert cache_info.hits >= 1  # At least one cache hit from client2
        assert cache_info.currsize >= 1  # At least one item in cache

    @pytest.mark.asyncio
    async def test_thread_safety_patterns(self, mock_aws_clients):
        """Test thread safety patterns in configuration management."""
        import asyncio
        
        async def concurrent_operation(operation, **kwargs):
            return await aws_config_manager(operation, **kwargs)
        
        # Run multiple operations concurrently
        tasks = [
            concurrent_operation("get_current"),
            concurrent_operation("validate_config"),
            concurrent_operation("clear_cache")
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify no exceptions were raised due to race conditions
        for result in results:
            assert not isinstance(result, Exception)
            if isinstance(result, str):
                result_data = json.loads(result)
                assert "success" in result_data