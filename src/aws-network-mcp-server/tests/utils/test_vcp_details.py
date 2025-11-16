#!/usr/bin/env python3
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

"""Test cases for the vcp_details utils module."""

import pytest
from unittest.mock import MagicMock, patch
from awslabs.aws_network_mcp_server.utils.vcp_details import (
    process_route_tables,
    process_subnets,
    process_igws,
)


class TestVcpDetails:
    """Test cases for vcp_details utility functions."""

    @pytest.fixture
    def mock_ec2_client(self):
        """Mock EC2 client fixture."""
        return MagicMock()

    @pytest.fixture
    def sample_vpc_data(self):
        """Sample VPC data fixture."""
        return {
            'VpcId': 'vpc-12345678',
            'State': 'available',
            'CidrBlock': '10.0.0.0/16',
            'DhcpOptionsId': 'dopt-12345678',
            'InstanceTenancy': 'default',
            'IsDefault': False
        }

    def test_process_route_tables_basic(self):
        """Test basic route tables processing."""
        route_tables_data = {
            'RouteTables': [
                {
                    'RouteTableId': 'rtb-12345678',
                    'VpcId': 'vpc-12345678',
                    'Routes': [
                        {
                            'DestinationCidrBlock': '10.0.0.0/16',
                            'GatewayId': 'local',
                            'State': 'active',
                            'Origin': 'CreateRouteTable'
                        }
                    ],
                    'Associations': []
                }
            ]
        }

        result = process_route_tables(route_tables_data)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].id == 'rtb-12345678'

    def test_process_subnets_basic(self):
        """Test basic subnets processing."""
        subnets_data = {
            'Subnets': [
                {
                    'SubnetId': 'subnet-12345678',
                    'VpcId': 'vpc-12345678',
                    'CidrBlock': '10.0.1.0/24',
                    'AvailabilityZone': 'us-east-1a',
                    'MapPublicIpOnLaunch': True
                }
            ]
        }

        route_tables_data = {'RouteTables': []}

        result = process_subnets(subnets_data, route_tables_data)

        assert isinstance(result, list)
        assert len(result) == 1

    def test_process_igws_basic(self):
        """Test basic IGW processing."""
        igws_data = {
            'InternetGateways': [
                {
                    'InternetGatewayId': 'igw-12345678',
                    'State': 'available',
                    'Attachments': [{'VpcId': 'vpc-12345678', 'State': 'available'}]
                }
            ]
        }

        result = process_igws(igws_data)

        assert result is not None