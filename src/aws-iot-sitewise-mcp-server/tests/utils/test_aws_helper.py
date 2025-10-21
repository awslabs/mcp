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

"""Tests for AWS helper utilities."""

import os
import pytest
from unittest.mock import Mock, patch
from awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper import AwsHelper


class TestAwsHelper:
    """Test cases for AwsHelper class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Clear cached partition before each test
        AwsHelper._aws_partition = None

    def test_get_aws_region_from_env(self):
        """Test getting AWS region from environment variable."""
        with patch.dict(os.environ, {'AWS_REGION': 'us-west-2'}):
            assert AwsHelper.get_aws_region() == 'us-west-2'

    def test_get_aws_region_default(self):
        """Test getting default AWS region when not set in environment."""
        with patch.dict(os.environ, {}, clear=True):
            assert AwsHelper.get_aws_region() == 'us-east-1'

    def test_get_aws_region_empty_env(self):
        """Test getting default AWS region when environment variable is empty."""
        with patch.dict(os.environ, {'AWS_REGION': ''}):
            assert AwsHelper.get_aws_region() == 'us-east-1'

    @patch('boto3.client')
    def test_get_aws_partition_success(self, mock_boto_client):
        """Test successfully getting AWS partition from STS."""
        # Mock STS client response
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws:sts::123456789012:assumed-role/MyRole/MySession'
        }
        mock_boto_client.return_value = mock_sts

        result = AwsHelper.get_aws_partition()
        
        assert result == 'aws'
        mock_boto_client.assert_called_once_with('sts')
        mock_sts.get_caller_identity.assert_called_once()

    @patch('boto3.client')
    def test_get_aws_partition_china(self, mock_boto_client):
        """Test getting AWS China partition from STS."""
        # Mock STS client response for China partition
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws-cn:sts::123456789012:assumed-role/MyRole/MySession'
        }
        mock_boto_client.return_value = mock_sts

        result = AwsHelper.get_aws_partition()
        
        assert result == 'aws-cn'

    @patch('boto3.client')
    def test_get_aws_partition_govcloud(self, mock_boto_client):
        """Test getting AWS GovCloud partition from STS."""
        # Mock STS client response for GovCloud partition
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws-us-gov:sts::123456789012:assumed-role/MyRole/MySession'
        }
        mock_boto_client.return_value = mock_sts

        result = AwsHelper.get_aws_partition()
        
        assert result == 'aws-us-gov'

    @patch('boto3.client')
    def test_get_aws_partition_exception(self, mock_boto_client):
        """Test getting default partition when STS call fails."""
        # Mock STS client to raise exception
        mock_boto_client.side_effect = Exception("STS call failed")

        result = AwsHelper.get_aws_partition()
        
        assert result == 'aws'

    @patch('boto3.client')
    def test_get_aws_partition_cached(self, mock_boto_client):
        """Test that partition is cached after first call."""
        # Mock STS client response
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws:sts::123456789012:assumed-role/MyRole/MySession'
        }
        mock_boto_client.return_value = mock_sts

        # First call
        result1 = AwsHelper.get_aws_partition()
        assert result1 == 'aws'
        
        # Second call should use cached value
        result2 = AwsHelper.get_aws_partition()
        assert result2 == 'aws'
        
        # STS should only be called once
        mock_boto_client.assert_called_once_with('sts')
        mock_sts.get_caller_identity.assert_called_once()

    @patch('boto3.client')
    def test_get_aws_partition_invalid_arn(self, mock_boto_client):
        """Test handling of invalid ARN format."""
        # Mock STS client response with invalid ARN
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'invalid-arn-format'
        }
        mock_boto_client.return_value = mock_sts

        result = AwsHelper.get_aws_partition()
        
        # Should fall back to default partition on error
        assert result == 'aws'
