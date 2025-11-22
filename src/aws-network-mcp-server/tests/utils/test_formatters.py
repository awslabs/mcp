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

"""Test cases for the formatters utils module."""

from awslabs.aws_network_mcp_server.utils.formatters import (
    format_routes,
    format_stateful_rule,
    format_stateless_rule,
    parse_suricata_rule,
)


class TestFormatters:
    """Test cases for formatter utility functions."""

    def test_format_stateless_rule_basic(self):
        """Test basic stateless rule formatting."""
        rule = {
            'MatchAttributes': {
                'Sources': ['10.0.0.0/8'],
                'Destinations': '0.0.0.0/0',
                'Protocols': [6],
            },
            'RuleDefinition': {'Actions': ['aws:pass']},
        }

        result = format_stateless_rule(rule, '100')

        assert result['priority'] == 100
        assert result['action'] == 'aws:pass'
        assert result['protocol'] == [6]
        assert result['source'] == ['10.0.0.0/8']
        assert result['destination'] == '0.0.0.0/0 (anywhere)'

    def test_format_stateless_rule_anywhere_source(self):
        """Test stateless rule formatting with anywhere source."""
        rule = {
            'MatchAttributes': {
                'Sources': '0.0.0.0/0',
                'Destinations': ['192.168.1.0/24'],
                'Protocols': [17],
            },
            'RuleDefinition': {'Actions': ['aws:drop']},
        }

        result = format_stateless_rule(rule, '200')

        assert result['source'] == '0.0.0.0/0 (anywhere)'
        assert result['destination'] == ['192.168.1.0/24']

    def test_format_stateless_rule_missing_attributes(self):
        """Test stateless rule formatting with missing attributes."""
        rule = {
            'MatchAttributes': {},
            'RuleDefinition': {'Actions': ['aws:forward_to_sfe']},
        }

        result = format_stateless_rule(rule, '300')

        assert result['priority'] == 300
        assert result['action'] == 'aws:forward_to_sfe'
        assert result['protocol'] is None
        assert result['source'] is None
        assert result['destination'] is None

    def test_format_stateful_rule_basic(self):
        """Test basic stateful rule formatting."""
        rule = {
            'Action': 'PASS',
            'Header': {
                'Protocol': 'TCP',
                'Source': '10.0.0.0/8',
                'SourcePort': '80',
                'Destination': '192.168.1.0/24',
                'DestinationPort': '443',
                'Direction': 'FORWARD',
            },
            'RuleOptions': [{'Keyword': 'sid', 'Value': '12345'}],
        }

        result = format_stateful_rule(rule, 'rule-001')

        assert result['rule_id'] == 'rule-001'
        assert result['type'] == 'standard'
        assert result['action'] == 'PASS'
        assert result['protocol'] == 'TCP'
        assert result['source']['network'] == '10.0.0.0/8'
        assert result['source']['port'] == '80'
        assert result['destination']['network'] == '192.168.1.0/24'
        assert result['destination']['port'] == '443'
        assert result['direction'] == 'FORWARD'

    def test_format_stateful_rule_missing_header(self):
        """Test stateful rule formatting with missing header."""
        rule = {'Action': 'DROP', 'RuleOptions': []}

        result = format_stateful_rule(rule, 'rule-002')

        assert result['rule_id'] == 'rule-002'
        assert result['action'] == 'DROP'
        assert result['protocol'] is None
        assert result['source']['network'] is None
        assert result['destination']['network'] is None

    def test_format_routes_single_segment(self):
        """Test route formatting for single segment."""
        routes_data = {
            'production/us-east-1': [
                {
                    'DestinationCidrBlock': '10.0.0.0/16',
                    'Destinations': [{'TransitGatewayAttachmentId': 'tgw-attach-123'}],
                    'Type': 'PROPAGATED',
                    'State': 'ACTIVE',
                }
            ]
        }

        result = format_routes(routes_data, 'core-network-123')

        assert result['core_network_id'] == 'core-network-123'
        assert 'production' in result['segments']
        assert 'us-east-1' in result['segments']['production']['regions']

        route = result['segments']['production']['regions']['us-east-1']['routes'][0]
        assert route['destination'] == '10.0.0.0/16'
        assert route['target'] == 'tgw-attach-123'
        assert route['target_type'] == 'PROPAGATED'
        assert route['state'] == 'ACTIVE'

    def test_format_routes_multiple_segments_regions(self):
        """Test route formatting for multiple segments and regions."""
        routes_data = {
            'production/us-east-1': [
                {
                    'DestinationCidrBlock': '10.1.0.0/16',
                    'Destinations': [{'CoreNetworkAttachmentId': 'cn-attach-prod'}],
                    'State': 'ACTIVE',
                }
            ],
            'staging/us-west-2': [
                {
                    'DestinationCidrBlock': '10.2.0.0/16',
                    'Destinations': [{'CoreNetworkAttachmentId': 'cn-attach-stage'}],
                    'State': 'ACTIVE',
                }
            ],
        }

        result = format_routes(routes_data, 'core-network-456')

        assert len(result['segments']) == 2
        assert 'production' in result['segments']
        assert 'staging' in result['segments']

        prod_route = result['segments']['production']['regions']['us-east-1']['routes'][0]
        assert prod_route['target'] == 'cn-attach-prod'

        stage_route = result['segments']['staging']['regions']['us-west-2']['routes'][0]
        assert stage_route['target'] == 'cn-attach-stage'

    def test_format_routes_empty_data(self):
        """Test route formatting with empty data."""
        result = format_routes({}, 'core-network-empty')

        assert result['core_network_id'] == 'core-network-empty'
        assert result['segments'] == {}

    def test_format_routes_no_destinations(self):
        """Test route formatting when destinations are empty."""
        routes_data = {
            'test/us-east-1': [
                {
                    'DestinationCidrBlock': '10.0.0.0/16',
                    'Destinations': [{}],
                    'State': 'ACTIVE',
                }
            ]
        }

        result = format_routes(routes_data, 'core-network-test')

        route = result['segments']['test']['regions']['us-east-1']['routes'][0]
        assert route['target'] is None

    def test_parse_suricata_rule_valid_rule(self):
        """Test parsing a valid Suricata rule."""
        rule_string = (
            'drop tcp any any -> 10.0.0.0/8 80 (msg:"Block HTTP to internal"; sid:1001; rev:1;)'
        )

        result = parse_suricata_rule(rule_string)

        assert result is not None
        assert result['rule_id'] == '1001'
        assert result['type'] == 'suricata'
        assert result['action'] == 'drop'
        assert result['protocol'] == 'tcp'
        assert result['source']['network'] == 'any'
        assert result['source']['port'] == 'any'
        assert result['destination']['network'] == '10.0.0.0/8'
        assert result['destination']['port'] == '80'
        assert result['conditions']['msg'] == '"Block HTTP to internal"'
        assert result['conditions']['sid'] == '1001'
        assert result['conditions']['rev'] == '1'

    def test_parse_suricata_rule_minimal_options(self):
        """Test parsing Suricata rule with minimal options."""
        rule_string = 'alert tcp any any -> any 443 (sid:2001;)'

        result = parse_suricata_rule(rule_string)

        assert result is not None
        assert result['rule_id'] == '2001'
        assert result['action'] == 'alert'
        assert result['conditions']['sid'] == '2001'
        assert len(result['conditions']) == 1

    def test_parse_suricata_rule_invalid_format(self):
        """Test parsing an invalid Suricata rule format."""
        invalid_rule = 'this is not a valid suricata rule format'

        result = parse_suricata_rule(invalid_rule)

        assert result is None

    def test_parse_suricata_rule_empty_string(self):
        """Test parsing empty string."""
        result = parse_suricata_rule('')

        assert result is None

    def test_parse_suricata_rule_whitespace_only(self):
        """Test parsing whitespace-only string."""
        result = parse_suricata_rule('   \n\t   ')

        assert result is None
