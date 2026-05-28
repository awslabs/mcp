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

"""Test cases for the list_dns_firewall_rules tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


firewall_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.route53.list_dns_firewall_rules'
)


class TestListDnsFirewallRules:
    """Test cases for list_dns_firewall_rules function."""

    @pytest.fixture
    def sample_rule_groups(self):
        """Sample firewall rule groups fixture."""
        return [
            {
                'Id': 'rslvr-frg-111',
                'Name': 'block-malware-domains',
                'ShareStatus': 'NOT_SHARED',
                'OwnerId': '123456789012',
            },
            {
                'Id': 'rslvr-frg-222',
                'Name': 'allow-internal-domains',
                'ShareStatus': 'SHARED_WITH_ME',
                'OwnerId': '987654321098',
            },
        ]

    @pytest.fixture
    def sample_associations(self):
        """Sample firewall rule group associations fixture."""
        return [
            {
                'FirewallRuleGroupId': 'rslvr-frg-111',
                'VpcId': 'vpc-aaa',
                'Priority': 100,
            },
            {
                'FirewallRuleGroupId': 'rslvr-frg-111',
                'VpcId': 'vpc-bbb',
                'Priority': 200,
            },
            {
                'FirewallRuleGroupId': 'rslvr-frg-222',
                'VpcId': 'vpc-aaa',
                'Priority': 300,
            },
        ]

    @pytest.fixture
    def sample_firewall_rules(self):
        """Sample individual firewall rules fixture."""
        return [
            {
                'Name': 'block-bad-domains',
                'Priority': 1,
                'Action': 'BLOCK',
                'FirewallDomainListId': 'rslvr-fdl-111',
                'BlockResponse': 'NXDOMAIN',
            },
            {
                'Name': 'alert-suspicious',
                'Priority': 2,
                'Action': 'ALERT',
                'FirewallDomainListId': 'rslvr-fdl-222',
                'BlockResponse': None,
            },
        ]

    @patch.object(firewall_module, 'get_aws_client')
    async def test_list_dns_firewall_rules_success(
        self, mock_get_client, sample_rule_groups, sample_associations
    ):
        """Test successful DNS Firewall rule groups listing with VPC associations."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        groups_paginator = MagicMock()
        assoc_paginator = MagicMock()

        def get_paginator_side_effect(api_name):
            if api_name == 'list_firewall_rule_groups':
                return groups_paginator
            elif api_name == 'list_firewall_rule_group_associations':
                return assoc_paginator

        mock_client.get_paginator.side_effect = get_paginator_side_effect

        groups_paginator.paginate.return_value = [{'FirewallRuleGroups': sample_rule_groups}]
        assoc_paginator.paginate.return_value = [
            {'FirewallRuleGroupAssociations': sample_associations}
        ]

        result = await firewall_module.list_dns_firewall_rules(region='us-east-1')

        assert result['region'] == 'us-east-1'
        assert result['count'] == 2
        assert len(result['firewall_rule_groups']) == 2
        assert result['firewall_rules'] is None

        # Verify first group has two VPC associations
        group1 = result['firewall_rule_groups'][0]
        assert group1['id'] == 'rslvr-frg-111'
        assert group1['name'] == 'block-malware-domains'
        assert len(group1['vpc_associations']) == 2
        assert group1['vpc_associations'][0] == {'vpc_id': 'vpc-aaa', 'priority': 100}
        assert group1['vpc_associations'][1] == {'vpc_id': 'vpc-bbb', 'priority': 200}

        # Verify second group has one VPC association
        group2 = result['firewall_rule_groups'][1]
        assert group2['id'] == 'rslvr-frg-222'
        assert len(group2['vpc_associations']) == 1

        mock_get_client.assert_called_once_with('route53resolver', 'us-east-1', None)

    @patch.object(firewall_module, 'get_aws_client')
    async def test_list_dns_firewall_rules_empty(self, mock_get_client):
        """Test listing when no DNS Firewall rule groups exist."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        groups_paginator = MagicMock()
        assoc_paginator = MagicMock()

        def get_paginator_side_effect(api_name):
            if api_name == 'list_firewall_rule_groups':
                return groups_paginator
            elif api_name == 'list_firewall_rule_group_associations':
                return assoc_paginator

        mock_client.get_paginator.side_effect = get_paginator_side_effect
        groups_paginator.paginate.return_value = [{'FirewallRuleGroups': []}]
        assoc_paginator.paginate.return_value = [{'FirewallRuleGroupAssociations': []}]

        result = await firewall_module.list_dns_firewall_rules(region='us-west-2')

        assert result == {
            'firewall_rule_groups': [],
            'firewall_rules': None,
            'count': 0,
            'region': 'us-west-2',
        }

    @patch.object(firewall_module, 'get_aws_client')
    async def test_list_dns_firewall_rules_with_profile(self, mock_get_client, sample_rule_groups):
        """Test DNS Firewall rules listing with specific AWS profile."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        groups_paginator = MagicMock()
        assoc_paginator = MagicMock()

        def get_paginator_side_effect(api_name):
            if api_name == 'list_firewall_rule_groups':
                return groups_paginator
            elif api_name == 'list_firewall_rule_group_associations':
                return assoc_paginator

        mock_client.get_paginator.side_effect = get_paginator_side_effect
        groups_paginator.paginate.return_value = [{'FirewallRuleGroups': sample_rule_groups}]
        assoc_paginator.paginate.return_value = [{'FirewallRuleGroupAssociations': []}]

        await firewall_module.list_dns_firewall_rules(
            region='eu-central-1', profile_name='test-profile'
        )

        mock_get_client.assert_called_once_with('route53resolver', 'eu-central-1', 'test-profile')

    @patch.object(firewall_module, 'get_aws_client')
    async def test_list_dns_firewall_rules_with_rule_group_id(
        self, mock_get_client, sample_rule_groups, sample_associations, sample_firewall_rules
    ):
        """Test listing with rule_group_id returns individual firewall rules."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        groups_paginator = MagicMock()
        assoc_paginator = MagicMock()
        rules_paginator = MagicMock()

        def get_paginator_side_effect(api_name):
            if api_name == 'list_firewall_rule_groups':
                return groups_paginator
            elif api_name == 'list_firewall_rule_group_associations':
                return assoc_paginator
            elif api_name == 'list_firewall_rules':
                return rules_paginator

        mock_client.get_paginator.side_effect = get_paginator_side_effect

        groups_paginator.paginate.return_value = [{'FirewallRuleGroups': sample_rule_groups}]
        assoc_paginator.paginate.return_value = [
            {'FirewallRuleGroupAssociations': sample_associations}
        ]
        rules_paginator.paginate.return_value = [{'FirewallRules': sample_firewall_rules}]

        result = await firewall_module.list_dns_firewall_rules(
            region='us-east-1', rule_group_id='rslvr-frg-111'
        )

        assert result['firewall_rules'] is not None
        assert len(result['firewall_rules']) == 2
        assert result['firewall_rules'][0]['name'] == 'block-bad-domains'
        assert result['firewall_rules'][0]['action'] == 'BLOCK'
        assert result['firewall_rules'][0]['block_response'] == 'NXDOMAIN'
        assert result['firewall_rules'][1]['name'] == 'alert-suspicious'
        assert result['firewall_rules'][1]['action'] == 'ALERT'
        assert result['firewall_rules'][1]['block_response'] is None

        rules_paginator.paginate.assert_called_once_with(FirewallRuleGroupId='rslvr-frg-111')

    @patch.object(firewall_module, 'get_aws_client')
    async def test_list_dns_firewall_rules_aws_error(self, mock_get_client):
        """Test AWS API error handling."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        groups_paginator = MagicMock()
        mock_client.get_paginator.return_value = groups_paginator
        groups_paginator.paginate.side_effect = Exception('AccessDenied')

        with pytest.raises(ToolError, match='Error listing DNS Firewall rules.*AccessDenied'):
            await firewall_module.list_dns_firewall_rules(region='us-east-1')
