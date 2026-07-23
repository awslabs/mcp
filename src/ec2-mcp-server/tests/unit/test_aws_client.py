#!/usr/bin/env python3
"""
Unit tests for AWS client management.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from awslabs.ec2_mcp_server.aws_client import AwsClientManager, get_ec2_client


class TestAwsClientManager:
    """Test suite for AWS client management functionality."""
    
    def setup_method(self):
        """Clear cache before each test."""
        AwsClientManager.clear_cache()
    
    @patch('boto3.client')
    def test_get_ec2_client_default_region(self, mock_boto3_client):
        """Test client creation with default region."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        with patch.dict(os.environ, {'AWS_REGION': 'us-west-2'}):
            client = AwsClientManager.get_ec2_client()
        
        assert client is mock_client
        mock_boto3_client.assert_called_once()
        call_args = mock_boto3_client.call_args
        assert call_args[1]['region_name'] == 'us-west-2'
        assert 'awslabs-ec2-mcp-server' in call_args[1]['config'].user_agent_extra
    
    @patch('boto3.client')
    def test_get_ec2_client_specific_region(self, mock_boto3_client):
        """Test client creation with specific region."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        client = AwsClientManager.get_ec2_client('eu-west-1')
        
        assert client is mock_client
        call_args = mock_boto3_client.call_args
        assert call_args[1]['region_name'] == 'eu-west-1'
    
    @patch('boto3.client')
    def test_client_caching(self, mock_boto3_client):
        """Test that clients are cached properly."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        # First call
        client1 = AwsClientManager.get_ec2_client('us-east-1')
        
        # Second call with same region
        client2 = AwsClientManager.get_ec2_client('us-east-1')
        
        # Should be the same instance due to caching
        assert client1 is client2
        
        # boto3.client should only be called once due to caching
        assert mock_boto3_client.call_count == 1
    
    @patch('boto3.client')
    def test_different_regions_different_clients(self, mock_boto3_client):
        """Test that different regions get different clients."""
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()
        mock_boto3_client.side_effect = [mock_client1, mock_client2]
        
        client1 = AwsClientManager.get_ec2_client('us-east-1')
        client2 = AwsClientManager.get_ec2_client('us-west-2')
        
        assert client1 is not client2
        assert mock_boto3_client.call_count == 2
    
    def test_get_region_aws_region(self):
        """Test region detection from AWS_REGION environment variable."""
        with patch.dict(os.environ, {'AWS_REGION': 'ap-southeast-1'}):
            region = AwsClientManager._get_region()
            assert region == 'ap-southeast-1'
    
    def test_get_region_aws_default_region(self):
        """Test region detection from AWS_DEFAULT_REGION environment variable."""
        # Clear AWS_REGION if it exists
        with patch.dict(os.environ, {}, clear=True):
            with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'eu-central-1'}):
                region = AwsClientManager._get_region()
                assert region == 'eu-central-1'
    
    def test_get_region_fallback(self):
        """Test fallback to us-east-1 when no region is configured."""
        with patch.dict(os.environ, {}, clear=True):
            region = AwsClientManager._get_region()
            assert region == 'us-east-1'
    
    def test_clear_cache(self):
        """Test cache clearing functionality."""
        with patch('boto3.client') as mock_boto3_client:
            mock_boto3_client.return_value = MagicMock()
            
            # Create a client to populate cache
            AwsClientManager.get_ec2_client('us-east-1')
            
            # Verify cache has entry
            assert len(AwsClientManager._client_cache) == 1
            
            # Clear cache
            AwsClientManager.clear_cache()
            
            # Verify cache is empty
            assert len(AwsClientManager._client_cache) == 0
    
    @patch('boto3.client')
    def test_config_retry_settings(self, mock_boto3_client):
        """Test that retry configuration is set properly."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        AwsClientManager.get_ec2_client()
        
        call_args = mock_boto3_client.call_args
        config = call_args[1]['config']
        
        # Check retry configuration
        assert hasattr(config, 'retries')
        # Note: Checking exact retry values depends on botocore version
    
    @patch('awslabs.ec2_mcp_server.aws_client.AwsClientManager.get_ec2_client')
    def test_convenience_function(self, mock_get_client):
        """Test the convenience function get_ec2_client."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        client = get_ec2_client('us-west-1')
        
        assert client is mock_client
        mock_get_client.assert_called_once_with('us-west-1')


class TestEnvironmentVariablePrecedence:
    """Test environment variable precedence for region detection."""
    
    def test_aws_region_takes_precedence(self):
        """Test that AWS_REGION takes precedence over AWS_DEFAULT_REGION."""
        env_vars = {
            'AWS_REGION': 'us-east-1',
            'AWS_DEFAULT_REGION': 'us-west-2'
        }
        
        with patch.dict(os.environ, env_vars):
            region = AwsClientManager._get_region()
            assert region == 'us-east-1'
    
    def test_region_parameter_override(self):
        """Test that explicit region parameter overrides environment variables."""
        with patch.dict(os.environ, {'AWS_REGION': 'us-east-1'}):
            with patch('boto3.client') as mock_boto3_client:
                mock_boto3_client.return_value = MagicMock()
                
                AwsClientManager.get_ec2_client('eu-west-1')
                
                call_args = mock_boto3_client.call_args
                assert call_args[1]['region_name'] == 'eu-west-1'