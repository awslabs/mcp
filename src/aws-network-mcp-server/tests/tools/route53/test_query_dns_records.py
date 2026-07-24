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

"""Test cases for the query_dns_records tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


dns_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.route53.query_dns_records'
)


class TestQueryDnsRecords:
    """Test cases for query_dns_records function."""

    @pytest.fixture
    def sample_records(self):
        """Sample DNS record sets fixture."""
        return {
            'ResourceRecordSets': [
                {
                    'Name': 'example.com.',
                    'Type': 'A',
                    'TTL': 300,
                    'ResourceRecords': [{'Value': '1.2.3.4'}],
                },
                {
                    'Name': 'www.example.com.',
                    'Type': 'CNAME',
                    'TTL': 600,
                    'ResourceRecords': [{'Value': 'example.com'}],
                },
                {
                    'Name': 'alias.example.com.',
                    'Type': 'A',
                    'AliasTarget': {
                        'DNSName': 'my-alb-123.us-east-1.elb.amazonaws.com.',
                        'HostedZoneId': 'Z35SXDOTRQ7X7K',
                        'EvaluateTargetHealth': True,
                    },
                },
            ],
            'IsTruncated': False,
        }

    @patch.object(dns_module, 'get_aws_client')
    async def test_query_dns_records_success(self, mock_get_client, sample_records):
        """Test successful DNS records query."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_resource_record_sets.return_value = sample_records

        result = await dns_module.query_dns_records(hosted_zone_id='Z1234')

        assert result['count'] == 3
        assert result['hosted_zone_id'] == 'Z1234'
        assert result['records'][0]['name'] == 'example.com.'
        assert result['records'][0]['type'] == 'A'
        assert result['records'][0]['is_alias'] is False
        assert result['records'][0]['routing_policy'] == 'simple'
        mock_get_client.assert_called_once_with('route53', None, None)

    @patch.object(dns_module, 'get_aws_client')
    async def test_query_dns_records_record_type_filter(self, mock_get_client, sample_records):
        """Test filtering by record type."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_resource_record_sets.return_value = sample_records

        result = await dns_module.query_dns_records(hosted_zone_id='Z1234', record_type='A')

        assert result['count'] == 2
        for r in result['records']:
            assert r['type'] == 'A'

    @patch.object(dns_module, 'get_aws_client')
    async def test_query_dns_records_name_prefix_filter(self, mock_get_client):
        """Test filtering by name prefix."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_resource_record_sets.return_value = {
            'ResourceRecordSets': [
                {
                    'Name': 'www.example.com.',
                    'Type': 'A',
                    'TTL': 300,
                    'ResourceRecords': [{'Value': '1.2.3.4'}],
                },
                {
                    'Name': 'www.example.com.',
                    'Type': 'AAAA',
                    'TTL': 300,
                    'ResourceRecords': [{'Value': '::1'}],
                },
                {
                    'Name': 'xyz.example.com.',
                    'Type': 'A',
                    'TTL': 300,
                    'ResourceRecords': [{'Value': '5.6.7.8'}],
                },
            ],
            'IsTruncated': False,
        }

        result = await dns_module.query_dns_records(hosted_zone_id='Z1234', name_prefix='www.')

        assert result['count'] == 2
        for r in result['records']:
            assert r['name'].startswith('www.')

    @patch.object(dns_module, 'get_aws_client')
    async def test_query_dns_records_alias_detection(self, mock_get_client, sample_records):
        """Test alias record detection."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_resource_record_sets.return_value = sample_records

        result = await dns_module.query_dns_records(hosted_zone_id='Z1234')

        alias_record = result['records'][2]
        assert alias_record['is_alias'] is True
        assert (
            alias_record['alias_target']['dns_name'] == 'my-alb-123.us-east-1.elb.amazonaws.com.'
        )
        assert alias_record['ttl'] is None
        assert alias_record['resource_records'] is None

    @patch.object(dns_module, 'get_aws_client')
    async def test_query_dns_records_routing_policy_detection(self, mock_get_client):
        """Test routing policy detection from record fields."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_resource_record_sets.return_value = {
            'ResourceRecordSets': [
                {
                    'Name': 'w.example.com.',
                    'Type': 'A',
                    'TTL': 300,
                    'SetIdentifier': 'w1',
                    'Weight': 70,
                    'ResourceRecords': [{'Value': '1.1.1.1'}],
                },
                {
                    'Name': 'l.example.com.',
                    'Type': 'A',
                    'TTL': 300,
                    'SetIdentifier': 'l1',
                    'Region': 'us-east-1',
                    'ResourceRecords': [{'Value': '2.2.2.2'}],
                },
                {
                    'Name': 'f.example.com.',
                    'Type': 'A',
                    'TTL': 300,
                    'SetIdentifier': 'f1',
                    'Failover': 'PRIMARY',
                    'ResourceRecords': [{'Value': '3.3.3.3'}],
                },
                {
                    'Name': 'g.example.com.',
                    'Type': 'A',
                    'TTL': 300,
                    'SetIdentifier': 'g1',
                    'GeoLocation': {'CountryCode': 'US'},
                    'ResourceRecords': [{'Value': '4.4.4.4'}],
                },
            ],
            'IsTruncated': False,
        }

        result = await dns_module.query_dns_records(hosted_zone_id='Z1234')

        assert result['records'][0]['routing_policy'] == 'weighted'
        assert result['records'][1]['routing_policy'] == 'latency'
        assert result['records'][2]['routing_policy'] == 'failover'
        assert result['records'][3]['routing_policy'] == 'geolocation'

    @patch.object(dns_module, 'get_aws_client')
    async def test_query_dns_records_manual_pagination(self, mock_get_client):
        """Test manual pagination with IsTruncated."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_resource_record_sets.side_effect = [
            {
                'ResourceRecordSets': [
                    {
                        'Name': 'a.example.com.',
                        'Type': 'A',
                        'TTL': 300,
                        'ResourceRecords': [{'Value': '1.1.1.1'}],
                    },
                ],
                'IsTruncated': True,
                'NextRecordName': 'b.example.com.',
                'NextRecordType': 'A',
            },
            {
                'ResourceRecordSets': [
                    {
                        'Name': 'b.example.com.',
                        'Type': 'A',
                        'TTL': 300,
                        'ResourceRecords': [{'Value': '2.2.2.2'}],
                    },
                ],
                'IsTruncated': False,
            },
        ]

        result = await dns_module.query_dns_records(hosted_zone_id='Z1234')

        assert result['count'] == 2
        assert mock_client.list_resource_record_sets.call_count == 2

    @patch.object(dns_module, 'get_aws_client')
    async def test_query_dns_records_early_stop_name_prefix(self, mock_get_client):
        """Test early-stop when name_prefix no longer matches."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_resource_record_sets.return_value = {
            'ResourceRecordSets': [
                {
                    'Name': 'api.example.com.',
                    'Type': 'A',
                    'TTL': 300,
                    'ResourceRecords': [{'Value': '1.1.1.1'}],
                },
                {
                    'Name': 'api.example.com.',
                    'Type': 'AAAA',
                    'TTL': 300,
                    'ResourceRecords': [{'Value': '::1'}],
                },
                {
                    'Name': 'www.example.com.',
                    'Type': 'A',
                    'TTL': 300,
                    'ResourceRecords': [{'Value': '2.2.2.2'}],
                },
            ],
            'IsTruncated': True,
            'NextRecordName': 'zzz.example.com.',
            'NextRecordType': 'A',
        }

        result = await dns_module.query_dns_records(hosted_zone_id='Z1234', name_prefix='api.')

        # Should stop early when 'www.example.com.' doesn't match 'api.' prefix
        assert result['count'] == 2
        # Should NOT make a second API call due to early-stop
        assert mock_client.list_resource_record_sets.call_count == 1

    async def test_query_dns_records_empty_zone_id(self):
        """Test empty hosted_zone_id validation."""
        with pytest.raises(ToolError, match='hosted_zone_id is required'):
            await dns_module.query_dns_records(hosted_zone_id='')

    async def test_query_dns_records_invalid_record_type(self):
        """Test invalid record_type validation."""
        with pytest.raises(ToolError, match='Invalid record_type "INVALID"'):
            await dns_module.query_dns_records(hosted_zone_id='Z1234', record_type='INVALID')

    @patch.object(dns_module, 'get_aws_client')
    async def test_query_dns_records_no_such_hosted_zone(self, mock_get_client):
        """Test NoSuchHostedZone error handling."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_resource_record_sets.side_effect = Exception(
            'An error occurred (NoSuchHostedZone)'
        )

        with pytest.raises(ToolError, match='not found'):
            await dns_module.query_dns_records(hosted_zone_id='Z_INVALID')

    @patch.object(dns_module, 'get_aws_client')
    async def test_query_dns_records_pagination_with_identifier(self, mock_get_client):
        """Test pagination handles NextRecordIdentifier for weighted/latency records."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_resource_record_sets.side_effect = [
            {
                'ResourceRecordSets': [
                    {
                        'Name': 'w.example.com.',
                        'Type': 'A',
                        'TTL': 300,
                        'SetIdentifier': 'w1',
                        'Weight': 70,
                        'ResourceRecords': [{'Value': '1.1.1.1'}],
                    },
                ],
                'IsTruncated': True,
                'NextRecordName': 'w.example.com.',
                'NextRecordType': 'A',
                'NextRecordIdentifier': 'w2',
            },
            {
                'ResourceRecordSets': [
                    {
                        'Name': 'w.example.com.',
                        'Type': 'A',
                        'TTL': 300,
                        'SetIdentifier': 'w2',
                        'Weight': 30,
                        'ResourceRecords': [{'Value': '2.2.2.2'}],
                    },
                ],
                'IsTruncated': False,
            },
        ]

        result = await dns_module.query_dns_records(hosted_zone_id='Z1234')

        assert result['count'] == 2
        # Verify the second call includes StartRecordIdentifier
        second_call = mock_client.list_resource_record_sets.call_args_list[1]
        assert second_call[1].get('StartRecordIdentifier') == 'w2'
