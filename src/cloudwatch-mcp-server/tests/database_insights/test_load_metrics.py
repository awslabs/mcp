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

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from awslabs.cloudwatch_mcp_server.database_insights.models import (
    DatabaseLoadResult,
    DimensionKeyDetail,
    DatabaseInsightsMetric,
)
from awslabs.cloudwatch_mcp_server.database_insights.tools import DatabaseInsightsTools




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

    def test_database_load_result_json_serialization(self):
        """Test that DatabaseLoadResult can be serialized to JSON with correct structure."""
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

        # Verify it's valid JSON
        parsed = json.loads(json_str)

        # Verify structure and values
        assert parsed['db_resource_id'] == 'db-ABC123'
        assert parsed['period_seconds'] == 60
        assert parsed['db_load_avg'] == 2.5
        assert parsed['db_load_max'] == 5.0
        assert 'start_time' in parsed
        assert 'end_time' in parsed
        assert 'top_dimensions' in parsed
        assert isinstance(parsed['top_dimensions'], list)


class TestGetDatabaseLoadMetricsTool:
    """Test the get-database-load-metrics tool execution."""

    @pytest.mark.asyncio
    async def test_get_load_metrics_returns_results(self, mock_context, register_tools_and_capture):
        """Test that get_database_load_metrics returns structured results."""
        mock_pi_response = {
            'AlignedStartTime': datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            'AlignedEndTime': datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
            'Identifier': 'db-TEST123',
            'MetricList': [
                {
                    'Key': {'Metric': 'db.load.avg'},
                    'DataPoints': [
                        {'Timestamp': datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc), 'Value': 2.5},
                        {'Timestamp': datetime(2024, 1, 1, 0, 30, 0, tzinfo=timezone.utc), 'Value': 3.5},
                    ],
                },
                {
                    'Key': {
                        'Metric': 'db.load.avg',
                        'Dimensions': {'db.sql': 'SELECT * FROM users'},
                    },
                    'DataPoints': [
                        {'Timestamp': datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc), 'Value': 2.0},
                        {'Timestamp': datetime(2024, 1, 1, 0, 30, 0, tzinfo=timezone.utc), 'Value': 2.5},
                    ],
                },
            ],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.database_insights.tools.boto3.Session'
        ) as mock_session:
            mock_pi_client = MagicMock()
            mock_pi_client.get_resource_metrics.return_value = mock_pi_response
            mock_session.return_value.client.return_value = mock_pi_client

            tools = DatabaseInsightsTools()
            registered = register_tools_and_capture(tools)

            result_json = await registered['get-database-load-metrics'](
                mock_context,
                db_resource_id='db-TEST123',
                start_time='2024-01-01T00:00:00Z',
                end_time='2024-01-01T01:00:00Z',
                group_by='db.sql',
                limit=10,
                region='us-east-1',
            )
            result = json.loads(result_json)

            assert result['db_resource_id'] == 'db-TEST123'
            assert result['db_load_avg'] == 3.0  # (2.5 + 3.5) / 2
            assert result['db_load_max'] == 3.5
            assert len(result['top_dimensions']) >= 1
            assert 'period_seconds' in result

    @pytest.mark.asyncio
    async def test_get_load_metrics_error_handling(self, mock_context, register_tools_and_capture):
        """Test that PI errors are returned as JSON."""
        with patch(
            'awslabs.cloudwatch_mcp_server.database_insights.tools.boto3.Session'
        ) as mock_session:
            mock_pi_client = MagicMock()
            mock_pi_client.get_resource_metrics.side_effect = Exception('PI service unavailable')
            mock_session.return_value.client.return_value = mock_pi_client

            tools = DatabaseInsightsTools()
            registered = register_tools_and_capture(tools)

            result_json = await registered['get-database-load-metrics'](
                mock_context,
                db_resource_id='db-TEST123',
                start_time='2024-01-01T00:00:00Z',
                end_time='2024-01-01T01:00:00Z',
                group_by='db.sql',
                limit=10,
                region='us-east-1',
            )
            result = json.loads(result_json)

            assert 'error' in result
            assert 'PI service unavailable' in result['error']

    @pytest.mark.asyncio
    async def test_get_load_metrics_summed_fallback(self, mock_context, register_tools_and_capture):
        """If PI returns only per-dimension series, the tool should sum values per timestamp."""
        mock_pi_response = {
            'AlignedStartTime': datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            'AlignedEndTime': datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
            'Identifier': 'db-FALLBACK123',
            'MetricList': [
                {
                    'Key': {
                        'Metric': 'db.load.avg',
                        'Dimensions': {'db.sql': 'SELECT * FROM users'},
                    },
                    'DataPoints': [
                        {'Timestamp': datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc), 'Value': 2.5},
                        {'Timestamp': datetime(2024, 1, 1, 0, 30, 0, tzinfo=timezone.utc), 'Value': 3.0},
                    ],
                },
                {
                    'Key': {
                        'Metric': 'db.load.avg',
                        'Dimensions': {'db.sql': 'INSERT INTO orders'},
                    },
                    'DataPoints': [
                        {'Timestamp': datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc), 'Value': 1.5},
                        {'Timestamp': datetime(2024, 1, 1, 0, 30, 0, tzinfo=timezone.utc), 'Value': 2.0},
                    ],
                },
            ],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.database_insights.tools.boto3.Session'
        ) as mock_session:
            mock_pi_client = MagicMock()
            mock_pi_client.get_resource_metrics.return_value = mock_pi_response
            mock_session.return_value.client.return_value = mock_pi_client

            tools = DatabaseInsightsTools()
            registered = register_tools_and_capture(tools)

            result_json = await registered['get-database-load-metrics'](
                mock_context,
                db_resource_id='db-FALLBACK123',
                start_time='2024-01-01T00:00:00Z',
                end_time='2024-01-01T01:00:00Z',
                group_by='db.sql',
                limit=10,
                region='us-east-1',
            )
            result = json.loads(result_json)

            # Per-timestamp sums: 0:00 -> 2.5+1.5=4.0, 0:30 -> 3.0+2.0=5.0
            assert result['db_load_avg'] == 4.5  # (4.0 + 5.0) / 2
            assert result['db_load_max'] == 5.0
            assert len(result['overall_metrics']) == 2
            vals = [p['value'] for p in result['overall_metrics']]
            assert 4.0 in vals and 5.0 in vals
