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
"""Tests for validation error in CloudWatch Metrics tools."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools import CloudWatchMetricsTools


@pytest_asyncio.fixture
async def ctx():
    """Fixture to provide mock context."""
    return AsyncMock()


@pytest_asyncio.fixture
async def cloudwatch_metrics_tools():
    """Create CloudWatchMetricsTools instance with mocked client."""
    with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session') as mock_session:
        mock_session.return_value.client.return_value = MagicMock()
        tools = CloudWatchMetricsTools()
        return tools


@pytest.mark.asyncio
class TestValidationError:
    """Tests for validation error in CloudWatch Metrics tools."""

    async def test_group_by_dimension_not_in_schema_dimension_keys(self, ctx, cloudwatch_metrics_tools):
        """Test that an error is raised when group_by_dimension is not in schema_dimension_keys."""
        # Call the tool with group_by_dimension not in schema_dimension_keys
        with pytest.raises(ValueError) as excinfo:
            await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                start_time='2023-01-01T00:00:00Z',
                end_time='2023-01-01T01:00:00Z',
                statistic='AVG',
                group_by_dimension='InstanceId',
                schema_dimension_keys=['InstanceType']  # InstanceId is not in this list
            )
        
        # Verify the error message
        assert "group_by_dimension 'InstanceId' must be included in schema_dimension_keys" in str(excinfo.value)