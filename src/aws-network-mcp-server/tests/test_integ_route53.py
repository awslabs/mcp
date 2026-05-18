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

"""Integration tests for Phase 2 Route 53 / DNS tools.

These tests require real AWS credentials and Route 53 resources.
Run with: uv run --frozen pytest tests/test_integ_route53.py -v
"""

import pytest


# Skip integration tests unless explicitly requested with: pytest -m integration
pytestmark = pytest.mark.skip(
    reason='Integration tests require real AWS credentials and resources'
)


@pytest.mark.integration
class TestListHostedZonesIntegration:
    """Integration tests for list_hosted_zones."""

    async def test_list_hosted_zones_returns_results(self):
        """Test that list_hosted_zones returns valid results against real AWS."""
        from awslabs.aws_network_mcp_server.tools.route53.list_hosted_zones import (
            list_hosted_zones,
        )

        result = await list_hosted_zones()
        assert 'hosted_zones' in result
        assert 'count' in result
        assert isinstance(result['hosted_zones'], list)
        assert isinstance(result['count'], int)

    async def test_list_hosted_zones_filter_public(self):
        """Test public zone filtering against real AWS."""
        from awslabs.aws_network_mcp_server.tools.route53.list_hosted_zones import (
            list_hosted_zones,
        )

        result = await list_hosted_zones(zone_type='public')
        for zone in result['hosted_zones']:
            assert zone['is_private'] is False


@pytest.mark.integration
class TestQueryDnsRecordsIntegration:
    """Integration tests for query_dns_records."""

    async def test_query_dns_records_returns_results(self):
        """Test that query_dns_records returns valid results against real AWS.

        Note: Requires at least one hosted zone to exist.
        """
        from awslabs.aws_network_mcp_server.tools.route53.list_hosted_zones import (
            list_hosted_zones,
        )
        from awslabs.aws_network_mcp_server.tools.route53.query_dns_records import (
            query_dns_records,
        )

        zones = await list_hosted_zones()
        if zones['count'] == 0:
            pytest.skip('No hosted zones available for integration test')

        zone_id = zones['hosted_zones'][0]['id']
        result = await query_dns_records(hosted_zone_id=zone_id)
        assert 'records' in result
        assert 'count' in result
        assert 'hosted_zone_id' in result


@pytest.mark.integration
class TestCheckHealthChecksIntegration:
    """Integration tests for check_health_checks."""

    async def test_check_health_checks_returns_results(self):
        """Test that check_health_checks returns valid results against real AWS."""
        from awslabs.aws_network_mcp_server.tools.route53.check_health_checks import (
            check_health_checks,
        )

        result = await check_health_checks()
        assert 'health_checks' in result
        assert 'count' in result
        assert isinstance(result['health_checks'], list)


@pytest.mark.integration
class TestListResolverRulesIntegration:
    """Integration tests for list_resolver_rules."""

    async def test_list_resolver_rules_returns_results(self):
        """Test that list_resolver_rules returns valid results against real AWS."""
        from awslabs.aws_network_mcp_server.tools.route53.list_resolver_rules import (
            list_resolver_rules,
        )

        result = await list_resolver_rules(region='us-east-1')
        assert 'resolver_rules' in result
        assert 'resolver_endpoints' in result
        assert 'region' in result
        assert result['region'] == 'us-east-1'
