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

"""Integration tests for Route 53 Profiles tools.

These tests require real AWS credentials and Route 53 Profiles resources.
They are skipped by default and should be run manually with:
    pytest tests/test_integ_route53_profiles.py -v --no-header
"""

import pytest


pytestmark = pytest.mark.skip(reason='Integration tests require real AWS resources')


class TestRoute53ProfilesIntegration:
    """Integration tests for Route 53 Profiles tools."""

    async def test_list_route53_profiles(self):
        """Test listing Route 53 Profiles against real AWS APIs."""
        from awslabs.aws_network_mcp_server.tools.route53_profiles import list_route53_profiles

        result = await list_route53_profiles(region='us-east-1')
        assert 'profiles' in result
        assert 'count' in result
        assert 'region' in result
        assert result['region'] == 'us-east-1'

    async def test_list_route53_profiles_with_profile_id(self):
        """Test listing Route 53 Profiles with a specific profile ID."""
        from awslabs.aws_network_mcp_server.tools.route53_profiles import list_route53_profiles

        # First list all profiles to get a profile ID
        result = await list_route53_profiles(region='us-east-1')
        if result['count'] > 0:
            pid = result['profiles'][0]['id']
            detail_result = await list_route53_profiles(region='us-east-1', profile_id=pid)
            assert 'profile_resources' in detail_result
