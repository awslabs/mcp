"""Unit tests for AWS configuration manager tool."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from awslabs.cloudwan_mcp_server.server import aws_config_manager, _create_client, get_aws_client


class TestAWSConfigManager:
    """Test cases for AWS configuration manager."""

    @pytest.fixture
    def mock_boto3_session(self):
        """Mock boto3 session."""
        with patch('boto3.Session') as mock_session:
            mock_instance = Mock()
            mock_session.return_value = mock_instance
            
            # Mock STS client
            mock_sts = Mock()
            mock_sts.get_caller_identity.return_value = {
                'Account': '123456789012',
                'UserId': 'test-user-id',
                'Arn': 'arn:aws:iam::123456789012:user/test-user'
            }
            
            # Mock EC2 client
            mock_ec2 = Mock()
            mock_ec2.describe_regions.return_value = {
                'Regions': [
                    {'RegionName': 'us-east-1'},
                    {'RegionName': 'us-west-2'},
                    {'RegionName': 'eu-west-1'},
                ]
            }
            
            mock_instance.client.side_effect = lambda service, **kwargs: {
                'sts': mock_sts,
                'ec2': mock_ec2
            }.get(service, Mock())
            
            yield mock_session

    @pytest.fixture
    def mock_get_aws_client(self):
        """Mock the get_aws_client function."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_client:
            mock_sts = Mock()
            mock_sts.get_caller_identity.return_value = {
                'Account': '123456789012',
                'UserId': 'test-user-id',
                'Arn': 'arn:aws:iam::123456789012:user/test-user'
            }
            
            mock_ec2 = Mock()
            mock_ec2.describe_regions.return_value = {
                'Regions': [{'RegionName': 'us-east-1'}, {'RegionName': 'us-west-2'}]
            }
            
            mock_nm = Mock()
            mock_nm.describe_global_networks.return_value = {
                'GlobalNetworks': [{'GlobalNetworkId': 'gn-123'}]
            }
            
            def client_side_effect(service, region=None):
                return {
                    'sts': mock_sts,
                    'ec2': mock_ec2,
                    'networkmanager': mock_nm
                }.get(service, Mock())
            
            mock_client.side_effect = client_side_effect
            yield mock_client

    @pytest.mark.asyncio
    async def test_get_current_configuration_success(self, mock_get_aws_client):
        """Test getting current AWS configuration successfully."""
        # Clear cache for clean test
        _create_client.cache_clear()
        
        with patch.dict(os.environ, {'AWS_PROFILE': 'test-profile', 'AWS_DEFAULT_REGION': 'us-west-2'}):
            result = await aws_config_manager("get_current")
            
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["operation"] == "get_current"
        assert result_data["current_configuration"]["aws_profile"] == "test-profile"
        assert result_data["current_configuration"]["aws_region"] == "us-west-2"
        assert result_data["current_configuration"]["configuration_valid"] is True
        assert "identity" in result_data["current_configuration"]

    @pytest.mark.asyncio
    async def test_get_current_configuration_invalid(self):
        """Test getting current configuration with invalid credentials."""
        _create_client.cache_clear()
        
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_client:
            mock_client.side_effect = Exception("Invalid credentials")
            
            with patch.dict(os.environ, {'AWS_PROFILE': 'invalid-profile'}):
                result = await aws_config_manager("get_current")
        
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["current_configuration"]["configuration_valid"] is False
        assert "error" in result_data["current_configuration"]["identity"]

    @pytest.mark.asyncio
    async def test_set_profile_success(self, mock_boto3_session):
        """Test setting AWS profile successfully."""
        _create_client.cache_clear()
        
        result = await aws_config_manager("set_profile", profile="new-profile")
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["operation"] == "set_profile"
        assert result_data["new_profile"] == "new-profile"
        assert result_data["profile_valid"] is True
        assert result_data["cache_cleared"] is True
        assert os.environ.get("AWS_PROFILE") == "new-profile"

    @pytest.mark.asyncio
    async def test_set_profile_missing_parameter(self):
        """Test setting profile without providing profile name."""
        result = await aws_config_manager("set_profile")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "Profile name is required" in result_data["error"]

    @pytest.mark.asyncio
    async def test_set_profile_invalid(self):
        """Test setting invalid AWS profile."""
        with patch('boto3.Session') as mock_session:
            mock_session.side_effect = Exception("Profile not found")
            
            result = await aws_config_manager("set_profile", profile="invalid-profile")
            result_data = json.loads(result)
            
            assert result_data["success"] is False
            assert "Failed to validate profile" in result_data["error"]
            assert "suggestion" in result_data

    @pytest.mark.asyncio
    async def test_set_region_success(self, mock_boto3_session):
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
    async def test_set_region_invalid_format(self):
        """Test setting region with invalid format."""
        result = await aws_config_manager("set_region", region="INVALID_REGION!")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "Invalid region format" in result_data["error"]
        assert "suggestion" in result_data

    @pytest.mark.asyncio
    async def test_set_region_missing_parameter(self):
        """Test setting region without providing region name."""
        result = await aws_config_manager("set_region")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "Region name is required" in result_data["error"]

    @pytest.mark.asyncio
    async def test_set_both_success(self, mock_boto3_session):
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
    async def test_set_both_missing_parameters(self):
        """Test setting both with missing parameters."""
        result = await aws_config_manager("set_both", profile="test-profile")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "Both profile and region are required" in result_data["error"]

    @pytest.mark.asyncio
    async def test_validate_config_success(self, mock_get_aws_client):
        """Test validating configuration successfully."""
        with patch.dict(os.environ, {'AWS_PROFILE': 'test-profile', 'AWS_DEFAULT_REGION': 'us-east-1'}):
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
        """Test validation with some services failing."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_client:
            def failing_client(service, region=None):
                if service == "sts":
                    mock_sts = Mock()
                    mock_sts.get_caller_identity.return_value = {
                        'Account': '123456789012', 'UserId': 'test', 'Arn': 'test-arn'
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
    async def test_clear_cache_success(self):
        """Test clearing AWS client cache."""
        # Add some mock entries to cache
        # Add items to cache by using the client functions
        get_aws_client("networkmanager", "us-east-1")
        get_aws_client("ec2", "us-west-2")
        
        result = await aws_config_manager("clear_cache")
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["operation"] == "clear_cache"
        assert result_data["cache_entries_cleared"] == 2
        cache_info = _create_client.cache_info()
        assert cache_info.currsize == 0
        assert "message" in result_data

    @pytest.mark.asyncio
    async def test_unknown_operation(self):
        """Test handling unknown operation."""
        result = await aws_config_manager("unknown_operation")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "Unknown operation" in result_data["error"]
        assert "supported_operations" in result_data
        assert len(result_data["supported_operations"]) == 9

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test general exception handling."""
        with patch('os.getenv') as mock_getenv:
            mock_getenv.side_effect = Exception("Unexpected error")
            
            result = await aws_config_manager("get_current")
            result_data = json.loads(result)
            
            assert "success" in result_data
            assert "error" in result_data