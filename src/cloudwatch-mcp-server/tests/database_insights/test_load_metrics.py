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

"""Tests for get-database-load-metrics tool."""

import pytest
from datetime import datetime, timezone
from awslabs.cloudwatch_mcp_server.database_insights.models import (
    DatabaseLoadResult,
    DimensionKeyDetail,
    DatabaseInsightsMetric,
)


@pytest.fixture
def sample_resource_metrics_response():
    """Sample PI get_resource_metrics response."""
    return {
        'AlignedStartTime': datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        'AlignedEndTime': datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
        'Identifier': 'db-ABC123',
        'MetricList': [
            {
                'Key': {
                    'Metric': 'db.load.avg',
                    'Dimensions': {'db.sql.statement': 'SELECT * FROM users'},
                },
                'DataPoints': [
                    {'Timestamp': datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc), 'Value': 2.5},
                    {'Timestamp': datetime(2024, 1, 1, 0, 30, 0, tzinfo=timezone.utc), 'Value': 3.0},
                ],
            },
            {
                'Key': {
                    'Metric': 'db.load.avg',
                    'Dimensions': {'db.sql.statement': 'INSERT INTO orders'},
                },
                'DataPoints': [
                    {'Timestamp': datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc), 'Value': 1.5},
                    {'Timestamp': datetime(2024, 1, 1, 0, 30, 0, tzinfo=timezone.utc), 'Value': 2.0},
                ],
            },
        ],
    }


class TestDatabaseLoadResultModel:
    """Test DatabaseLoadResult model creation from API response data."""

    def test_create_database_load_result(self, sample_resource_metrics_response):
        """Test creating a DatabaseLoadResult from sample data."""
        # Simulate processing the API response
        top_dimensions = []
        for metric_list in sample_resource_metrics_response.get('MetricList', []):
            dimensions = metric_list.get('Key', {}).get('Dimensions', {})
            sql_text = dimensions.get('db.sql.statement', 'N/A')

            data_points = []
            total = 0.0
            for dp in metric_list.get('DataPoints', []):
                if 'Value' in dp:
                    total += dp['Value']
                    data_points.append(DatabaseInsightsMetric(
                        timestamp=dp['Timestamp'],
                        value=dp['Value'],
                    ))

            top_dimensions.append(DimensionKeyDetail(
                dimension='db.sql.statement',
                value=sql_text,
                total=round(total, 4),
                data_points=data_points,
            ))

        result = DatabaseLoadResult(
            db_resource_id='db-ABC123',
            start_time=sample_resource_metrics_response['AlignedStartTime'],
            end_time=sample_resource_metrics_response['AlignedEndTime'],
            period_seconds=60,
            db_load_avg=2.25,
            db_load_max=3.0,
            top_dimensions=top_dimensions,
        )

        assert result.db_resource_id == 'db-ABC123'
        assert result.period_seconds == 60
        assert len(result.top_dimensions) == 2
        assert result.top_dimensions[0].value == 'SELECT * FROM users'
        assert result.top_dimensions[0].total == 5.5
        assert result.top_dimensions[1].value == 'INSERT INTO orders'
        assert result.top_dimensions[1].total == 3.5

    def test_database_load_result_with_vcpu(self):
        """Test DatabaseLoadResult with vCPU count for contention analysis."""
        start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)

        result = DatabaseLoadResult(
            db_resource_id='db-ABC123',
            start_time=start,
            end_time=end,
            period_seconds=60,
            db_load_avg=6.5,  # Higher than vCPU count
            db_load_max=8.0,
            vcpu_count=4,  # 4 vCPUs
        )

        # When db_load_avg > vcpu_count, there's contention
        assert result.db_load_avg > result.vcpu_count
        assert result.vcpu_count == 4

    def test_database_load_result_json_serialization(self):
        """Test that DatabaseLoadResult can be serialized to JSON."""
        start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)

        result = DatabaseLoadResult(
            db_resource_id='db-ABC123',
            start_time=start,
            end_time=end,
            period_seconds=60,
            db_load_avg=2.5,
            db_load_max=5.0,
        )

        json_str = result.model_dump_json()
        assert 'db-ABC123' in json_str
        assert 'db_load_avg' in json_str

