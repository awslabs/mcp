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

"""Test cases for the list_route53_profiles tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


profiles_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.route53_profiles.list_route53_profiles'
)


class TestListRoute53Profiles:
    """Test cases for list_route53_profiles function."""

    @pytest.fixture
    def sample_profiles(self):
        """Sample Route 53 Profiles fixture."""
        return [
            {
                'Id': 'rp-111aaa',
                'Name': 'enterprise-dns-profile',
                'Status': 'COMPLETE',
                'ShareStatus': 'NOT_SHARED',
            },
            {
                'Id': 'rp-222bbb',
                'Name': 'shared-dns-profile',
                'Status': 'COMPLETE',
                'ShareStatus': 'SHARED_BY_ME',
            },
        ]

    @pytest.fixture
    def sample_associations(self):
        """Sample profile associations fixture."""
        return [
            {
                'ProfileId': 'rp-111aaa',
                'ResourceId': 'vpc-aaa',
            },
            {
                'ProfileId': 'rp-111aaa',
                'ResourceId': 'vpc-bbb',
            },
            {
                'ProfileId': 'rp-222bbb',
                'ResourceId': 'vpc-ccc',
            },
        ]

    @pytest.fixture
    def sample_resources(self):
        """Sample profile resource associations fixture."""
        return [
            {
                'ResourceType': 'PRIVATE_HOSTED_ZONE',
                'ResourceArn': 'arn:aws:route53:::hostedzone/Z111',
                'Name': 'corp.example.com',
                'Status': 'COMPLETE',
            },
            {
                'ResourceType': 'FIREWALL_RULE_GROUP',
                'ResourceArn': 'arn:aws:route53resolver:us-east-1:123456789012:firewall-rule-group/rslvr-frg-111',
                'Name': 'block-malware',
                'Status': 'COMPLETE',
            },
        ]

    @patch.object(profiles_module, 'get_aws_client')
    async def test_list_route53_profiles_success(
        self, mock_get_client, sample_profiles, sample_associations
    ):
        """Test successful Route 53 Profiles listing with VPC associations."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        profiles_paginator = MagicMock()
        assoc_paginator = MagicMock()

        def get_paginator_side_effect(api_name):
            if api_name == 'list_profiles':
                return profiles_paginator
            elif api_name == 'list_profile_associations':
                return assoc_paginator

        mock_client.get_paginator.side_effect = get_paginator_side_effect

        profiles_paginator.paginate.return_value = [{'ProfileSummaries': sample_profiles}]
        assoc_paginator.paginate.return_value = [{'ProfileAssociations': sample_associations}]

        result = await profiles_module.list_route53_profiles(region='us-east-1')

        assert result['region'] == 'us-east-1'
        assert result['count'] == 2
        assert len(result['profiles']) == 2
        assert result['profile_resources'] is None

        # Verify first profile has two VPC associations
        prof1 = result['profiles'][0]
        assert prof1['id'] == 'rp-111aaa'
        assert prof1['name'] == 'enterprise-dns-profile'
        assert prof1['status'] == 'COMPLETE'
        assert prof1['share_status'] == 'NOT_SHARED'
        assert prof1['vpc_associations'] == ['vpc-aaa', 'vpc-bbb']

        # Verify second profile has one VPC association
        prof2 = result['profiles'][1]
        assert prof2['id'] == 'rp-222bbb'
        assert prof2['vpc_associations'] == ['vpc-ccc']

        mock_get_client.assert_called_once_with('route53profiles', 'us-east-1', None)

    @patch.object(profiles_module, 'get_aws_client')
    async def test_list_route53_profiles_empty(self, mock_get_client):
        """Test listing when no Route 53 Profiles exist."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        profiles_paginator = MagicMock()
        assoc_paginator = MagicMock()

        def get_paginator_side_effect(api_name):
            if api_name == 'list_profiles':
                return profiles_paginator
            elif api_name == 'list_profile_associations':
                return assoc_paginator

        mock_client.get_paginator.side_effect = get_paginator_side_effect
        profiles_paginator.paginate.return_value = [{'ProfileSummaries': []}]
        assoc_paginator.paginate.return_value = [{'ProfileAssociations': []}]

        result = await profiles_module.list_route53_profiles(region='us-west-2')

        assert result == {
            'profiles': [],
            'profile_resources': None,
            'count': 0,
            'region': 'us-west-2',
        }

    @patch.object(profiles_module, 'get_aws_client')
    async def test_list_route53_profiles_with_profile(self, mock_get_client, sample_profiles):
        """Test Route 53 Profiles listing with specific AWS profile."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        profiles_paginator = MagicMock()
        assoc_paginator = MagicMock()

        def get_paginator_side_effect(api_name):
            if api_name == 'list_profiles':
                return profiles_paginator
            elif api_name == 'list_profile_associations':
                return assoc_paginator

        mock_client.get_paginator.side_effect = get_paginator_side_effect
        profiles_paginator.paginate.return_value = [{'ProfileSummaries': sample_profiles}]
        assoc_paginator.paginate.return_value = [{'ProfileAssociations': []}]

        await profiles_module.list_route53_profiles(
            region='eu-central-1', profile_name='test-profile'
        )

        mock_get_client.assert_called_once_with('route53profiles', 'eu-central-1', 'test-profile')

    @patch.object(profiles_module, 'get_aws_client')
    async def test_list_route53_profiles_with_profile_id(
        self, mock_get_client, sample_profiles, sample_associations, sample_resources
    ):
        """Test listing with profile_id returns attached resources."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        profiles_paginator = MagicMock()
        assoc_paginator = MagicMock()
        res_paginator = MagicMock()

        def get_paginator_side_effect(api_name):
            if api_name == 'list_profiles':
                return profiles_paginator
            elif api_name == 'list_profile_associations':
                return assoc_paginator
            elif api_name == 'list_profile_resource_associations':
                return res_paginator

        mock_client.get_paginator.side_effect = get_paginator_side_effect

        profiles_paginator.paginate.return_value = [{'ProfileSummaries': sample_profiles}]
        assoc_paginator.paginate.return_value = [{'ProfileAssociations': sample_associations}]
        res_paginator.paginate.return_value = [{'ProfileResourceAssociations': sample_resources}]

        result = await profiles_module.list_route53_profiles(
            region='us-east-1', profile_id='rp-111aaa'
        )

        assert result['profile_resources'] is not None
        assert len(result['profile_resources']) == 2
        assert result['profile_resources'][0]['resource_type'] == 'PRIVATE_HOSTED_ZONE'
        assert result['profile_resources'][0]['name'] == 'corp.example.com'
        assert result['profile_resources'][1]['resource_type'] == 'FIREWALL_RULE_GROUP'
        assert result['profile_resources'][1]['name'] == 'block-malware'

        res_paginator.paginate.assert_called_once_with(ProfileId='rp-111aaa')

    @patch.object(profiles_module, 'get_aws_client')
    async def test_list_route53_profiles_aws_error(self, mock_get_client):
        """Test AWS API error handling."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        profiles_paginator = MagicMock()
        mock_client.get_paginator.return_value = profiles_paginator
        profiles_paginator.paginate.side_effect = Exception('AccessDenied')

        with pytest.raises(ToolError, match='Error listing Route 53 Profiles.*AccessDenied'):
            await profiles_module.list_route53_profiles(region='us-east-1')
