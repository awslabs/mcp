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

"""Test cases for the get_firewall_rules tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
firewall_rules_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.network_firewall.get_firewall_rules'
)


class TestGetFirewallRules:
    """Test cases for get_firewall_rules function."""

    @pytest.fixture
    def mock_nfw_client(self):
        """Mock Network Firewall client fixture."""
        return MagicMock()

    @pytest.fixture
    def firewall_response(self):
        """Mock firewall response."""
        return {
            'Firewall': {
                'FirewallName': 'test-firewall',
                'FirewallArn': 'arn:aws:network-firewall:us-east-1:123456789012:firewall/test-firewall',
                'FirewallPolicyArn': 'arn:aws:network-firewall:us-east-1:123456789012:firewall-policy/test-policy',
            }
        }

    @pytest.fixture
    def policy_response(self):
        """Mock policy response."""
        return {
            'FirewallPolicy': {
                'StatelessRuleGroupReferences': [
                    {
                        'ResourceArn': 'arn:aws:network-firewall:us-east-1:123456789012:stateless-rulegroup/test-stateless'
                    }
                ],
                'StatefulRuleGroupReferences': [
                    {
                        'ResourceArn': 'arn:aws:network-firewall:us-east-1:123456789012:stateful-rulegroup/test-stateful'
                    }
                ],
            }
        }

    @pytest.fixture
    def stateless_rule_group(self):
        """Mock stateless rule group."""
        return {
            'RuleGroup': {
                'RulesSource': {
                    'StatelessRulesAndCustomActions': {
                        'StatelessRules': [
                            {
                                'Priority': 1,
                                'RuleDefinition': {'Actions': ['aws:pass']},
                                'MatchAttributes': {
                                    'Sources': ['10.0.0.0/8'],
                                    'Destinations': ['0.0.0.0/0'],
                                    'Protocols': [6],
                                },
                            }
                        ]
                    }
                }
            }
        }

    @pytest.fixture
    def stateful_rule_group_standard(self):
        """Mock stateful rule group with standard rules."""
        return {
            'RuleGroup': {
                'RuleGroupName': 'test-stateful',
                'RulesSource': {
                    'StatefulRules': [
                        {
                            'Action': 'PASS',
                            'Header': {
                                'Protocol': 'TCP',
                                'Source': '10.0.0.0/8',
                                'SourcePort': 'ANY',
                                'Destination': '0.0.0.0/0',
                                'DestinationPort': '80',
                                'Direction': 'FORWARD',
                            },
                            'RuleOptions': [],
                        }
                    ]
                },
            }
        }

    @pytest.fixture
    def stateful_rule_group_suricata(self):
        """Mock stateful rule group with Suricata rules."""
        return {
            'RuleGroup': {
                'RuleGroupName': 'test-suricata',
                'RulesSource': {
                    'RulesString': 'alert tcp any any -> any 80 (msg:"HTTP traffic"; sid:1;)'
                },
            }
        }

    @patch.object(firewall_rules_module, 'get_aws_client')
    async def test_get_firewall_rules_success_with_both_rule_types(
        self,
        mock_get_client,
        mock_nfw_client,
        firewall_response,
        policy_response,
        stateless_rule_group,
        stateful_rule_group_standard,
    ):
        """Test successful retrieval with both stateless and stateful rules."""
        mock_get_client.return_value = mock_nfw_client
        mock_nfw_client.describe_firewall.return_value = firewall_response
        mock_nfw_client.describe_firewall_policy.return_value = policy_response

        def mock_describe_rule_group(RuleGroupArn):
            if 'stateless' in RuleGroupArn:
                return stateless_rule_group
            return stateful_rule_group_standard

        mock_nfw_client.describe_rule_group.side_effect = mock_describe_rule_group

        result = await firewall_rules_module.get_firewall_rules(
            firewall_name='test-firewall', region='us-east-1'
        )

        assert result['firewall_name'] == 'test-firewall'
        assert result['summary']['total_stateless_rules'] == 1
        assert result['summary']['total_stateful_rules'] == 1
        assert len(result['stateless_rules']) == 1
        assert len(result['stateful_rules']) == 1
        assert result['stateless_rules'][0]['priority'] == 1
        assert result['stateful_rules'][0]['rule_group_name'] == 'test-stateful'

    @patch.object(firewall_rules_module, 'get_aws_client')
    async def test_get_firewall_rules_with_suricata_rules(
        self, mock_get_client, mock_nfw_client, firewall_response, stateful_rule_group_suricata
    ):
        """Test retrieval with Suricata format rules."""
        mock_get_client.return_value = mock_nfw_client
        mock_nfw_client.describe_firewall.return_value = firewall_response
        mock_nfw_client.describe_firewall_policy.return_value = {
            'FirewallPolicy': {
                'StatelessRuleGroupReferences': [],
                'StatefulRuleGroupReferences': [
                    {
                        'ResourceArn': 'arn:aws:network-firewall:us-east-1:123456789012:stateful-rulegroup/test-suricata'
                    }
                ],
            }
        }
        mock_nfw_client.describe_rule_group.return_value = stateful_rule_group_suricata

        result = await firewall_rules_module.get_firewall_rules(firewall_name='test-firewall')

        assert result['summary']['total_stateless_rules'] == 0
        assert result['summary']['total_stateful_rules'] == 1
        assert result['stateful_rules'][0]['type'] == 'suricata'
        assert result['stateful_rules'][0]['action'] == 'alert'

    @patch.object(firewall_rules_module, 'get_aws_client')
    async def test_get_firewall_rules_empty_policy(
        self, mock_get_client, mock_nfw_client, firewall_response
    ):
        """Test with empty firewall policy."""
        mock_get_client.return_value = mock_nfw_client
        mock_nfw_client.describe_firewall.return_value = firewall_response
        mock_nfw_client.describe_firewall_policy.return_value = {
            'FirewallPolicy': {
                'StatelessRuleGroupReferences': [],
                'StatefulRuleGroupReferences': [],
            }
        }

        result = await firewall_rules_module.get_firewall_rules(
            firewall_name='test-firewall', region='us-west-2'
        )

        assert result['summary']['total_stateless_rules'] == 0
        assert result['summary']['total_stateful_rules'] == 0
        assert result['stateless_rules'] == []
        assert result['stateful_rules'] == []

    @patch.object(firewall_rules_module, 'get_aws_client')
    async def test_get_firewall_rules_with_profile(
        self, mock_get_client, mock_nfw_client, firewall_response
    ):
        """Test with custom AWS profile."""
        mock_get_client.return_value = mock_nfw_client
        mock_nfw_client.describe_firewall.return_value = firewall_response
        mock_nfw_client.describe_firewall_policy.return_value = {'FirewallPolicy': {}}

        await firewall_rules_module.get_firewall_rules(
            firewall_name='test-firewall', profile_name='custom-profile'
        )

        mock_get_client.assert_called_once_with('network-firewall', None, 'custom-profile')

    @patch.object(firewall_rules_module, 'get_aws_client')
    async def test_get_firewall_rules_firewall_not_found(self, mock_get_client, mock_nfw_client):
        """Test firewall not found error."""
        mock_get_client.return_value = mock_nfw_client
        mock_nfw_client.describe_firewall.side_effect = Exception('ResourceNotFoundException')

        with pytest.raises(
            ToolError, match='There was an error getting AWS Network Firewall rules'
        ):
            await firewall_rules_module.get_firewall_rules(firewall_name='nonexistent-firewall')

    @patch.object(firewall_rules_module, 'get_aws_client')
    async def test_get_firewall_rules_policy_error(
        self, mock_get_client, mock_nfw_client, firewall_response
    ):
        """Test policy retrieval error."""
        mock_get_client.return_value = mock_nfw_client
        mock_nfw_client.describe_firewall.return_value = firewall_response
        mock_nfw_client.describe_firewall_policy.side_effect = Exception('AccessDenied')

        with pytest.raises(ToolError):
            await firewall_rules_module.get_firewall_rules(firewall_name='test-firewall')

    @patch.object(firewall_rules_module, 'get_aws_client')
    async def test_get_firewall_rules_rule_group_error(
        self, mock_get_client, mock_nfw_client, firewall_response, policy_response
    ):
        """Test rule group retrieval error."""
        mock_get_client.return_value = mock_nfw_client
        mock_nfw_client.describe_firewall.return_value = firewall_response
        mock_nfw_client.describe_firewall_policy.return_value = policy_response
        mock_nfw_client.describe_rule_group.side_effect = Exception('RuleGroupNotFound')

        with pytest.raises(ToolError):
            await firewall_rules_module.get_firewall_rules(firewall_name='test-firewall')
