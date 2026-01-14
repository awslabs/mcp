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

"""Tests for analyze-database-incident and compare-database-periods models."""

import pytest
from datetime import datetime, timezone
from awslabs.cloudwatch_mcp_server.database_insights.models import (
    IncidentAnalysisResult,
    PeriodComparison,
    TopSqlStatement,
    WaitEventDetail,
)


@pytest.fixture
def sample_top_sql():
    """Sample top SQL statements."""
    return [
        TopSqlStatement(
            sql_id='SQL1',
            sql_text='SELECT * FROM large_table WHERE status = ?',
            total_load=20.0,
            avg_load=10.0,
        ),
        TopSqlStatement(
            sql_id='SQL2',
            sql_text='INSERT INTO orders VALUES (?)',
            total_load=5.0,
            avg_load=2.5,
        ),
    ]


@pytest.fixture
def sample_wait_events():
    """Sample wait events."""
    return [
        WaitEventDetail(
            wait_event='IO:DataFileRead',
            wait_category='IO',
            total_load=15.0,
            avg_load=7.5,
            interpretation='Storage I/O bottleneck. Check IOPS limits.',
        ),
        WaitEventDetail(
            wait_event='CPU',
            wait_category='CPU',
            total_load=5.0,
            avg_load=2.5,
            interpretation='Query is compute-bound.',
        ),
    ]


class TestIncidentAnalysisResult:
    """Test IncidentAnalysisResult model."""

    def test_create_incident_analysis_result(self, sample_top_sql, sample_wait_events):
        """Test creating an IncidentAnalysisResult."""
        result = IncidentAnalysisResult(
            db_resource_id='db-ABC123',
            start_time=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 0, 10, 0, tzinfo=timezone.utc),
            summary='During the 10 minute incident window, the database experienced high load.',
            total_db_load=25.0,
            peak_db_load=12.0,
            top_sql=sample_top_sql,
            top_wait_events=sample_wait_events,
            recommendations=[
                'Review top SQL query: SELECT * FROM large_table...',
                'Check storage IOPS and throughput limits',
            ],
        )

        assert result.db_resource_id == 'db-ABC123'
        assert result.total_db_load == 25.0
        assert result.peak_db_load == 12.0
        assert len(result.top_sql) == 2
        assert len(result.top_wait_events) == 2
        assert len(result.recommendations) == 2
        assert 'incident' in result.summary.lower()

    def test_incident_analysis_json_serialization(self, sample_top_sql, sample_wait_events):
        """Test that IncidentAnalysisResult can be serialized to JSON."""
        result = IncidentAnalysisResult(
            db_resource_id='db-ABC123',
            start_time=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 0, 10, 0, tzinfo=timezone.utc),
            summary='Test summary',
            total_db_load=25.0,
            peak_db_load=12.0,
            top_sql=sample_top_sql,
            top_wait_events=sample_wait_events,
            recommendations=['Test recommendation'],
        )

        json_str = result.model_dump_json()
        assert 'db-ABC123' in json_str
        assert 'SQL1' in json_str


class TestPeriodComparison:
    """Test PeriodComparison model."""

    def test_create_period_comparison(self, sample_top_sql, sample_wait_events):
        """Test creating a PeriodComparison."""
        result = PeriodComparison(
            db_resource_id='db-ABC123',
            baseline_start=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            baseline_end=datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
            incident_start=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            incident_end=datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
            baseline_load=5.0,
            incident_load=25.0,
            load_change_percent=400.0,
            new_sql_queries=sample_top_sql[:1],
            increased_sql_queries=sample_top_sql[1:],
            new_wait_events=sample_wait_events[:1],
            summary='Load changed from 5.0 to 25.0 AAS (+400.0%).',
        )

        assert result.db_resource_id == 'db-ABC123'
        assert result.baseline_load == 5.0
        assert result.incident_load == 25.0
        assert result.load_change_percent == 400.0
        assert len(result.new_sql_queries) == 1
        assert len(result.increased_sql_queries) == 1
        assert len(result.new_wait_events) == 1

    def test_period_comparison_json_serialization(self, sample_top_sql, sample_wait_events):
        """Test that PeriodComparison can be serialized to JSON."""
        result = PeriodComparison(
            db_resource_id='db-ABC123',
            baseline_start=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            baseline_end=datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
            incident_start=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            incident_end=datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
            baseline_load=5.0,
            incident_load=25.0,
            load_change_percent=400.0,
            new_sql_queries=[],
            increased_sql_queries=[],
            new_wait_events=[],
            summary='Test summary',
        )

        json_str = result.model_dump_json()
        assert 'db-ABC123' in json_str
        assert '400.0' in json_str

