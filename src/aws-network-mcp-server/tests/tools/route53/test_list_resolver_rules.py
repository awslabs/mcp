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

"""Test cases for the list_resolver_rules tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


resolver_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.route53.list_resolver_rules'
)


class TestListResolverRules:
    """Test cases for list_resolver_rules function."""

    @pytest.fixture
    def sample_rules(self):
        """Sample resolver rules fixture."""
        return [
            {
                'Id': 'rslvr-rr-111',
                'Name': 'forward-onprem',
                'DomainName': 'corp.example.com.',
                'RuleType': 'FORWARD',
                'Status': 'COMPLETE',
                'TargetIps': [
                    {'Ip': '10.0.0.53', 'Port': 53},
                    {'Ip': '10.0.1.53', 'Port': 53},
                ],
            },
            {
                'Id': 'rslvr-rr-222',
                'Name': 'system-rule',
                'DomainName': 'amazonaws.com.',
                'RuleType': 'SYSTEM',
                'Status': 'COMPLETE',
                'TargetIps': [],
            },
        ]

    @pytest.fixture
    def sample_endpoints(self):
        """Sample resolver endpoints fixture."""
        return [
            {
                'Id': 'rslvr-out-111',
                'Name': 'outbound-ep',
                'Direction': 'OUTBOUND',
                'HostVPCId': 'vpc-123',
                'Status': 'OPERATIONAL',
                'IpAddressCount': 2,
            },
        ]

    @patch.object(resolver_module, 'get_aws_client')
    async def test_list_resolver_rules_success(
        self, mock_get_client, sample_rules, sample_endpoints
    ):
        """Test successful resolver rules listing."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Set up paginators
        rules_paginator = MagicMock()
        assoc_paginator = MagicMock()
        endpoints_paginator = MagicMock()
        ip_paginator = MagicMock()

        def get_paginator_side_effect(api_name):
            if api_name == 'list_resolver_rules':
                return rules_paginator
            elif api_name == 'list_resolver_rule_associations':
                return assoc_paginator
            elif api_name == 'list_resolver_endpoints':
                return endpoints_paginator
            elif api_name == 'list_resolver_endpoint_ip_addresses':
                return ip_paginator

        mock_client.get_paginator.side_effect = get_paginator_side_effect

        rules_paginator.paginate.return_value = [{'ResolverRules': sample_rules}]
        assoc_paginator.paginate.return_value = [
            {
                'ResolverRuleAssociations': [
                    {'ResolverRuleId': 'rslvr-rr-111', 'VPCId': 'vpc-aaa'},
                    {'ResolverRuleId': 'rslvr-rr-111', 'VPCId': 'vpc-bbb'},
                    {'ResolverRuleId': 'rslvr-rr-222', 'VPCId': 'vpc-aaa'},
                ]
            }
        ]
        endpoints_paginator.paginate.return_value = [{'ResolverEndpoints': sample_endpoints}]
        ip_paginator.paginate.return_value = [
            {
                'IpAddresses': [
                    {'Ip': '10.0.0.10', 'SubnetId': 'subnet-111'},
                    {'Ip': '10.0.1.10', 'SubnetId': 'subnet-222'},
                ]
            }
        ]

        result = await resolver_module.list_resolver_rules(region='us-east-1')

        assert result['region'] == 'us-east-1'
        assert len(result['resolver_rules']) == 2
        assert result['resolver_rules'][0]['vpc_associations'] == ['vpc-aaa', 'vpc-bbb']
        assert result['resolver_rules'][0]['target_ips'] == [
            {'ip': '10.0.0.53', 'port': 53},
            {'ip': '10.0.1.53', 'port': 53},
        ]
        assert len(result['resolver_endpoints']) == 1
        assert result['resolver_endpoints'][0]['ip_addresses'] == [
            {'ip': '10.0.0.10', 'subnet_id': 'subnet-111'},
            {'ip': '10.0.1.10', 'subnet_id': 'subnet-222'},
        ]
        mock_get_client.assert_called_once_with('route53resolver', 'us-east-1', None)

    @patch.object(resolver_module, 'get_aws_client')
    async def test_list_resolver_rules_empty(self, mock_get_client):
        """Test listing when no resolver rules or endpoints exist."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        rules_paginator = MagicMock()
        endpoints_paginator = MagicMock()

        def get_paginator_side_effect(api_name):
            if api_name == 'list_resolver_rules':
                return rules_paginator
            elif api_name == 'list_resolver_endpoints':
                return endpoints_paginator
            return MagicMock()

        mock_client.get_paginator.side_effect = get_paginator_side_effect
        rules_paginator.paginate.return_value = [{'ResolverRules': []}]
        endpoints_paginator.paginate.return_value = [{'ResolverEndpoints': []}]

        result = await resolver_module.list_resolver_rules(region='us-west-2')

        assert result == {
            'resolver_rules': [],
            'resolver_endpoints': [],
            'region': 'us-west-2',
        }

    @patch.object(resolver_module, 'get_aws_client')
    async def test_list_resolver_rules_with_profile(
        self, mock_get_client, sample_rules, sample_endpoints
    ):
        """Test resolver rules listing with specific AWS profile."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        rules_paginator = MagicMock()
        assoc_paginator = MagicMock()
        endpoints_paginator = MagicMock()
        ip_paginator = MagicMock()

        def get_paginator_side_effect(api_name):
            if api_name == 'list_resolver_rules':
                return rules_paginator
            elif api_name == 'list_resolver_rule_associations':
                return assoc_paginator
            elif api_name == 'list_resolver_endpoints':
                return endpoints_paginator
            elif api_name == 'list_resolver_endpoint_ip_addresses':
                return ip_paginator

        mock_client.get_paginator.side_effect = get_paginator_side_effect
        rules_paginator.paginate.return_value = [{'ResolverRules': sample_rules}]
        assoc_paginator.paginate.return_value = [{'ResolverRuleAssociations': []}]
        endpoints_paginator.paginate.return_value = [{'ResolverEndpoints': sample_endpoints}]
        ip_paginator.paginate.return_value = [{'IpAddresses': []}]

        await resolver_module.list_resolver_rules(
            region='eu-central-1', profile_name='test-profile'
        )

        mock_get_client.assert_called_once_with('route53resolver', 'eu-central-1', 'test-profile')

    @patch.object(resolver_module, 'get_aws_client')
    async def test_list_resolver_rules_aws_error(self, mock_get_client):
        """Test AWS API error handling."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        rules_paginator = MagicMock()
        mock_client.get_paginator.return_value = rules_paginator
        rules_paginator.paginate.side_effect = Exception('AccessDenied')

        with pytest.raises(ToolError, match='Error listing resolver rules.*AccessDenied'):
            await resolver_module.list_resolver_rules(region='us-east-1')
