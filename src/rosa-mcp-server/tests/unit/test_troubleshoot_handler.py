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

"""Tests for the ROSA troubleshoot handler."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_troubleshoot_handler import (
    RosaTroubleshootHandler,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestSearchTroubleshootGuide:
    """Tests for rosa_search_troubleshoot_guide."""

    @pytest.mark.asyncio
    async def test_search_troubleshoot_guide_finds_pod_pending(
        self, mock_mcp, mock_context
    ):
        """Test searching for pod pending issues returns relevant results."""
        handler = RosaTroubleshootHandler(mock_mcp)
        result = await handler.rosa_search_troubleshoot_guide(
            mock_context, query='pod stuck pending'
        )

        assert isinstance(result, list)
        data = json.loads(result[0].text)
        assert data['results_count'] >= 1
        # Should find the "Pod stuck in Pending state" entry
        titles = [r['title'] for r in data['results']]
        assert any('Pending' in t for t in titles)

    @pytest.mark.asyncio
    async def test_search_troubleshoot_guide_finds_network_issues(
        self, mock_mcp, mock_context
    ):
        """Test searching for network issues returns relevant results."""
        handler = RosaTroubleshootHandler(mock_mcp)
        result = await handler.rosa_search_troubleshoot_guide(
            mock_context, query='connection timeout dns'
        )

        data = json.loads(result[0].text)
        assert data['results_count'] >= 1
        titles = [r['title'] for r in data['results']]
        assert any('Network' in t or 'connectivity' in t.lower() for t in titles)

    @pytest.mark.asyncio
    async def test_search_troubleshoot_guide_no_results(
        self, mock_mcp, mock_context
    ):
        """Test searching for unrelated query returns no results."""
        handler = RosaTroubleshootHandler(mock_mcp)
        result = await handler.rosa_search_troubleshoot_guide(
            mock_context, query='banana smoothie recipe'
        )

        data = json.loads(result[0].text)
        assert data['results_count'] == 0
        assert data['results'] == []

    @pytest.mark.asyncio
    async def test_search_troubleshoot_guide_multiple_matches(
        self, mock_mcp, mock_context
    ):
        """Test that a broad query matches multiple KB entries."""
        handler = RosaTroubleshootHandler(mock_mcp)
        # 'timeout' appears in multiple entries (ingress/route + network)
        result = await handler.rosa_search_troubleshoot_guide(
            mock_context, query='timeout'
        )

        data = json.loads(result[0].text)
        assert data['results_count'] >= 2

    @pytest.mark.asyncio
    async def test_search_troubleshoot_guide_results_sorted_by_relevance(
        self, mock_mcp, mock_context
    ):
        """Test that results are sorted by relevance score descending."""
        handler = RosaTroubleshootHandler(mock_mcp)
        result = await handler.rosa_search_troubleshoot_guide(
            mock_context, query='pod pending stuck not starting'
        )

        data = json.loads(result[0].text)
        if data['results_count'] > 1:
            scores = [r['relevance_score'] for r in data['results']]
            assert scores == sorted(scores, reverse=True)


class TestGetMetricsGuidance:
    """Tests for rosa_get_metrics_guidance."""

    @pytest.mark.asyncio
    async def test_get_metrics_guidance_returns_data(
        self, mock_mcp, mock_context
    ):
        """Test metrics guidance returns complete guidance data."""
        handler = RosaTroubleshootHandler(mock_mcp)
        result = await handler.rosa_get_metrics_guidance(mock_context)

        assert isinstance(result, list)
        data = json.loads(result[0].text)
        assert 'container_insights' in data
        assert 'openshift_monitoring' in data
        assert 'recommended_alarms' in data
        assert data['container_insights']['namespace'] == 'ContainerInsights'
        assert len(data['container_insights']['key_metrics']) > 0
        assert len(data['recommended_alarms']) > 0

    @pytest.mark.asyncio
    async def test_get_metrics_guidance_contains_expected_metrics(
        self, mock_mcp, mock_context
    ):
        """Test that guidance contains expected key metrics."""
        handler = RosaTroubleshootHandler(mock_mcp)
        result = await handler.rosa_get_metrics_guidance(mock_context)

        data = json.loads(result[0].text)
        metric_names = [m['name'] for m in data['container_insights']['key_metrics']]
        assert 'cpu_usage_total' in metric_names
        assert 'memory_usage' in metric_names
        assert 'node_cpu_utilization' in metric_names


class TestGetVpcConfig:
    """Tests for rosa_get_vpc_config."""

    @pytest.mark.asyncio
    async def test_get_vpc_config_calls_boto3(
        self, mock_mcp, mock_context, mock_ocm_client
    ):
        """Test that VPC config retrieves data from boto3 EC2."""
        # Set up OCM client to return cluster info with subnet IDs
        mock_ocm_client.get_cluster = AsyncMock(return_value={
            'id': 'test-cluster-id',
            'name': 'test-cluster',
            'aws': {'subnet_ids': ['subnet-111', 'subnet-222']},
            'region': {'id': 'us-east-1'},
            'hypershift': {'enabled': False},
        })

        handler = RosaTroubleshootHandler(
            mock_mcp, ocm_client=mock_ocm_client, allow_sensitive_data_access=True
        )

        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            'Subnets': [
                {
                    'SubnetId': 'subnet-111',
                    'VpcId': 'vpc-abc',
                    'AvailabilityZone': 'us-east-1a',
                    'CidrBlock': '10.0.1.0/24',
                    'MapPublicIpOnLaunch': False,
                    'AvailableIpAddressCount': 250,
                },
                {
                    'SubnetId': 'subnet-222',
                    'VpcId': 'vpc-abc',
                    'AvailabilityZone': 'us-east-1b',
                    'CidrBlock': '10.0.2.0/24',
                    'MapPublicIpOnLaunch': True,
                    'AvailableIpAddressCount': 240,
                },
            ]
        }
        mock_ec2.describe_vpcs.return_value = {
            'Vpcs': [{'VpcId': 'vpc-abc', 'CidrBlock': '10.0.0.0/16'}]
        }
        mock_ec2.describe_security_groups.return_value = {
            'SecurityGroups': [
                {
                    'GroupId': 'sg-111',
                    'GroupName': 'rosa-cluster-sg',
                    'Description': 'ROSA cluster security group',
                }
            ]
        }
        mock_ec2.describe_nat_gateways.return_value = {
            'NatGateways': [
                {
                    'NatGatewayId': 'nat-111',
                    'State': 'available',
                    'SubnetId': 'subnet-222',
                    'ConnectivityType': 'public',
                }
            ]
        }
        mock_ec2.describe_route_tables.return_value = {
            'RouteTables': [
                {
                    'RouteTableId': 'rtb-111',
                    'Associations': [{'SubnetId': 'subnet-222'}],
                    'Routes': [
                        {'DestinationCidrBlock': '0.0.0.0/0', 'GatewayId': 'igw-123'},
                    ],
                },
                {
                    'RouteTableId': 'rtb-222',
                    'Associations': [{'SubnetId': 'subnet-111'}],
                    'Routes': [
                        {'DestinationCidrBlock': '0.0.0.0/0', 'NatGatewayId': 'nat-111'},
                    ],
                },
            ]
        }

        with patch('boto3.client', return_value=mock_ec2):
            result = await handler.rosa_get_vpc_config(
                mock_context, cluster_id='test-cluster-id'
            )

        data = json.loads(result[0].text)
        assert data['vpc_id'] == 'vpc-abc'
        assert data['vpc_cidr'] == '10.0.0.0/16'
        assert len(data['subnets']) == 2
        assert len(data['security_groups']) == 1
        assert len(data['nat_gateways']) == 1
        # subnet-222 has IGW route so should be public
        public_subnets = [s for s in data['subnets'] if s['Public']]
        assert len(public_subnets) == 1
        assert public_subnets[0]['SubnetId'] == 'subnet-222'

    @pytest.mark.asyncio
    async def test_get_vpc_config_no_subnets_returns_error(
        self, mock_mcp, mock_context, mock_ocm_client
    ):
        """Test that missing subnet IDs returns an error message."""
        mock_ocm_client.get_cluster = AsyncMock(return_value={
            'id': 'test-cluster-id',
            'name': 'test-cluster',
            'aws': {},
            'region': {'id': 'us-east-1'},
            'hypershift': {'enabled': False},
        })
        mock_ocm_client.list_machine_pools = AsyncMock(return_value={'items': []})

        handler = RosaTroubleshootHandler(
            mock_mcp, ocm_client=mock_ocm_client, allow_sensitive_data_access=True
        )

        result = await handler.rosa_get_vpc_config(
            mock_context, cluster_id='test-cluster-id'
        )

        data = json.loads(result[0].text)
        assert 'error' in data
