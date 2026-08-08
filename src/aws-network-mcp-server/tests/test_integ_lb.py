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

"""Integration tests for Phase 1 Load Balancer tools.

These tests require real AWS credentials and LB resources.
Run with: uv run --frozen pytest tests/test_integ_lb.py -v
Skip in CI with: pytest -m "not integration"
"""

import pytest


@pytest.mark.integration
class TestListLoadBalancersIntegration:
    """Integration tests for list_load_balancers."""

    async def test_list_load_balancers_real(self):
        """Test listing load balancers against real AWS API."""
        pytest.skip('Integration test — requires real AWS credentials and LB resources')


@pytest.mark.integration
class TestGetLbDetailsIntegration:
    """Integration tests for get_lb_details."""

    async def test_get_lb_details_real(self):
        """Test getting LB details against real AWS API."""
        pytest.skip('Integration test — requires real AWS credentials and LB resources')


@pytest.mark.integration
class TestGetLbTargetHealthIntegration:
    """Integration tests for get_lb_target_health."""

    async def test_get_lb_target_health_real(self):
        """Test getting target health against real AWS API."""
        pytest.skip('Integration test — requires real AWS credentials and LB resources')
