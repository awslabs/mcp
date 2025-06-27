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

"""Tests for the pricing client module."""

import pytest
from awslabs.aws_pricing_mcp_server.pricing_client import (
    create_pricing_client,
    get_pricing_region,
)
from unittest.mock import Mock, patch


class TestGetPricingRegion:
    """Tests for the get_pricing_region function."""

    @pytest.mark.parametrize(
        'region,expected',
        [
            # Direct pricing regions
            ('us-east-1', 'us-east-1'),
            ('eu-central-1', 'eu-central-1'),
            ('ap-southeast-1', 'ap-southeast-1'),
            ('cn-northwest-1', 'cn-northwest-1'),
            # US/Americas regions
            ('us-west-2', 'us-east-1'),
            ('ca-central-1', 'us-east-1'),
            ('sa-east-1', 'us-east-1'),
            # Europe/Middle East/Africa regions
            ('eu-west-1', 'eu-central-1'),
            ('me-south-1', 'eu-central-1'),
            ('af-south-1', 'eu-central-1'),
            # Asia Pacific regions
            ('ap-east-1', 'ap-southeast-1'),
            # China regions
            ('cn-north-1', 'cn-northwest-1'),
            # Unknown regions default to us-east-1
            ('unknown-region', 'us-east-1'),
        ],
    )
    def test_region_mapping(self, region, expected):
        """Test region mapping to pricing endpoints."""
        assert get_pricing_region(region) == expected

    @pytest.mark.parametrize(
        'env_region,expected',
        [
            ('eu-west-1', 'eu-central-1'),
            ('us-east-1', 'us-east-1'),
            ('ap-northeast-1', 'ap-southeast-1'),
        ],
    )
    def test_uses_aws_region_env_var(self, env_region, expected, monkeypatch):
        """Test AWS_REGION env var is used when no region specified."""
        monkeypatch.setattr('awslabs.aws_pricing_mcp_server.consts.AWS_REGION', env_region)
        assert get_pricing_region() == expected


class TestCreatePricingClient:
    """Tests for the create_pricing_client function."""

    @pytest.mark.parametrize(
        'profile,region,expected_profile,expected_region',
        [
            (None, None, None, 'us-east-1'),
            ('test-profile', None, 'test-profile', 'us-east-1'),
            (None, 'eu-west-1', None, 'eu-central-1'),
            ('my-profile', 'ap-northeast-1', 'my-profile', 'ap-southeast-1'),
            (None, 'us-east-1', None, 'us-east-1'),  # Direct pricing region
        ],
    )
    @patch('awslabs.aws_pricing_mcp_server.pricing_client.boto3.Session')
    def test_create_client_parameters(
        self, mock_session, profile, region, expected_profile, expected_region
    ):
        """Test creating pricing client with various parameter combinations."""
        # Setup mocks
        mock_session_instance = Mock()
        mock_client = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = mock_client

        # Call function
        result = create_pricing_client(profile=profile, region=region)

        # Verify session creation
        mock_session.assert_called_once_with(profile_name=expected_profile)

        # Verify client creation
        mock_session_instance.client.assert_called_once()
        call_args = mock_session_instance.client.call_args
        assert call_args[0][0] == 'pricing'

        # Verify config
        config = call_args[1]['config']
        assert config.region_name == expected_region
        assert 'awslabs/mcp/' in config.user_agent_extra

        assert result == mock_client

    @patch('awslabs.aws_pricing_mcp_server.pricing_client.boto3.Session')
    def test_uses_env_profile_when_none_specified(self, mock_session, monkeypatch):
        """Test that AWS_PROFILE environment variable is used when no profile specified."""
        monkeypatch.setattr('awslabs.aws_pricing_mcp_server.consts.AWS_PROFILE', 'env-profile')

        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = Mock()

        create_pricing_client()

        mock_session.assert_called_once_with(profile_name='env-profile')
