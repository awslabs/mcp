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

"""Tests for Database Insights models."""

import pytest
from datetime import datetime, timezone
import json
from awslabs.cloudwatch_mcp_server.database_insights.models import (
    DatabaseInstance,
    DatabaseInsightsMetric,
    DatabaseLoadResult,
    DimensionKeyDetail,
    ListDatabasesResult,
)


class TestDatabaseInstance:
    """Test DatabaseInstance model."""

    def test_database_instance_creation(self):
        """Test creating a DatabaseInstance with all fields."""
        instance = DatabaseInstance(
            dbi_resource_id='db-ABC123',
            db_instance_identifier='my-database',
            engine='postgres',
            engine_version='14.6',
            insights_enabled=True,
            insights_retention_days=7,
            instance_class='db.r5.large',
            region='us-east-1',
        )
        assert instance.dbi_resource_id == 'db-ABC123'
        assert instance.db_instance_identifier == 'my-database'
        assert instance.engine == 'postgres'
        assert instance.insights_enabled is True
        assert instance.insights_retention_days == 7

    def test_database_instance_optional_fields(self):
        """Test DatabaseInstance with optional fields as None."""
        instance = DatabaseInstance(
            dbi_resource_id='db-XYZ789',
            db_instance_identifier='test-db',
            engine='mysql',
            engine_version='8.0',
            insights_enabled=False,
            region='us-west-2',
        )
        assert instance.insights_retention_days is None
        assert instance.instance_class is None


class TestDatabaseInsightsMetric:
    """Test DatabaseInsightsMetric model."""

    def test_metric_creation(self):
        """Test creating a metric data point."""
        ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        metric = DatabaseInsightsMetric(timestamp=ts, value=2.5)
        assert metric.timestamp == ts
        assert metric.value == 2.5


class TestDimensionKeyDetail:
    """Test DimensionKeyDetail model."""

    def test_dimension_key_detail_creation(self):
        """Test creating a dimension key detail."""
        ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        data_points = [
            DatabaseInsightsMetric(timestamp=ts, value=1.5),
            DatabaseInsightsMetric(timestamp=ts, value=2.0),
        ]
        detail = DimensionKeyDetail(
            dimension='db.sql',
            value='SELECT * FROM users',
            total=3.5,
            data_points=data_points,
        )
        assert detail.dimension == 'db.sql'
        assert detail.value == 'SELECT * FROM users'
        assert detail.total == 3.5
        assert len(detail.data_points) == 2

    def test_dimension_key_detail_empty_data_points(self):
        """Test DimensionKeyDetail with empty data points."""
        detail = DimensionKeyDetail(
            dimension='db.wait_event',
            value='IO:DataFileRead',
            total=0.0,
        )
        assert detail.data_points == []


class TestDatabaseLoadResult:
    """Test DatabaseLoadResult model."""

    def test_database_load_result_creation(self):
        """Test creating a database load result."""
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
        assert result.db_resource_id == 'db-ABC123'
        assert result.period_seconds == 60
        assert result.db_load_avg == 2.5
        assert result.db_load_max == 5.0
        assert result.top_dimensions == []
        assert result.overall_metrics == []


class TestListDatabasesResult:
    """Test ListDatabasesResult model."""

    def test_list_databases_result_empty(self):
        """Test creating an empty ListDatabasesResult."""
        result = ListDatabasesResult(
            databases=[],
            region='us-east-1',
            total_count=0,
            insights_enabled_count=0,
        )
        assert result.databases == []
        assert result.region == 'us-east-1'
        assert result.total_count == 0
        assert result.insights_enabled_count == 0

    def test_list_databases_result_with_instances(self):
        """Test creating a ListDatabasesResult with database instances."""
        db = DatabaseInstance(
            dbi_resource_id='db-TEST123',
            db_instance_identifier='test-db',
            engine='postgres',
            engine_version='15.4',
            insights_enabled=True,
            insights_retention_days=7,
            instance_class='db.t3.medium',
            region='us-east-1',
        )
        result = ListDatabasesResult(
            databases=[db],
            region='us-east-1',
            total_count=1,
            insights_enabled_count=1,
        )
        assert len(result.databases) == 1
        assert result.databases[0].db_instance_identifier == 'test-db'
        assert result.total_count == 1
        assert result.insights_enabled_count == 1

    def test_list_databases_result_json_serialization(self):
        """Test that ListDatabasesResult serializes to valid JSON."""
        result = ListDatabasesResult(
            databases=[],
            region='eu-west-1',
            total_count=0,
            insights_enabled_count=0,
        )
        json_str = result.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed['region'] == 'eu-west-1'
        assert parsed['total_count'] == 0
        assert parsed['insights_enabled_count'] == 0
        assert parsed['databases'] == []

