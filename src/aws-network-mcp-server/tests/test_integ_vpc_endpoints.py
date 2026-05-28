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

"""Integration tests for VPC Endpoint tools.

These tests require real AWS credentials and VPC endpoint resources.
Run with: uv run --frozen pytest tests/test_integ_vpc_endpoints.py -v

Prerequisites:
- AWS credentials configured (env vars, ~/.aws/credentials, or IAM role)
- At least one VPC endpoint in the target region
- IAM permissions: ec2:DescribeVpcEndpoints, ec2:DescribeSecurityGroups,
  ec2:DescribeNetworkInterfaces
"""

import pytest


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestListVpcEndpointsDetailedInteg:
    """Integration tests for list_vpc_endpoints_detailed."""

    @pytest.mark.skip(reason='Integration test — requires AWS credentials and VPC endpoints')
    async def test_list_all_endpoints(self):
        """List all VPC endpoints in the default region."""
        from awslabs.aws_network_mcp_server.tools.vpc_endpoints import (
            list_vpc_endpoints_detailed,
        )

        result = await list_vpc_endpoints_detailed(region='us-east-1')
        assert 'vpc_endpoints' in result
        assert 'count' in result
        assert isinstance(result['vpc_endpoints'], list)

    @pytest.mark.skip(reason='Integration test — requires AWS credentials and VPC endpoints')
    async def test_list_endpoints_with_vpc_filter(self):
        """List VPC endpoints filtered by VPC ID."""
        from awslabs.aws_network_mcp_server.tools.vpc_endpoints import (
            list_vpc_endpoints_detailed,
        )

        # Replace with a real VPC ID in your test account
        result = await list_vpc_endpoints_detailed(region='us-east-1', vpc_id='vpc-REPLACE_ME')
        assert 'vpc_endpoints' in result
        for ep in result['vpc_endpoints']:
            assert ep['vpc_id'] == 'vpc-REPLACE_ME'


class TestCheckEndpointConnectivityInteg:
    """Integration tests for check_endpoint_connectivity."""

    @pytest.mark.skip(reason='Integration test — requires AWS credentials and VPC endpoints')
    async def test_check_interface_endpoint(self):
        """Check connectivity for an interface VPC endpoint."""
        from awslabs.aws_network_mcp_server.tools.vpc_endpoints import (
            check_endpoint_connectivity,
        )

        # Replace with a real VPC endpoint ID in your test account
        result = await check_endpoint_connectivity(
            vpc_endpoint_id='vpce-REPLACE_ME', region='us-east-1'
        )
        assert 'endpoint' in result
        assert 'connectivity_checks' in result
        assert result['endpoint']['id'] == 'vpce-REPLACE_ME'
