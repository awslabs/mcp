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

"""Tests for describe_rds_performance_metrics tool."""

import pytest
from awslabs.rds_control_plane_mcp_server.tools.general.describe_rds_performance_metrics import (
    METRICS,
    MetricSummary,
    MetricSummaryList,
    describe_rds_performance_metrics,
)
from datetime import datetime


class TestMetricSummary:
    """Test cases for MetricSummary model."""

    def test_metric_summary_from_complete_data(self):
        """Test MetricSummary creation from complete metric data."""
        metric_data = {
            'Id': 'metric_CPUUtilization_Average',
            'Label': 'CPUUtilization',
            'StatusCode': 'Complete',
            'Values': [10.5, 15.2, 20.1, 18.7, 12.3],
            'Timestamps': [
                datetime(2024, 1, 1, 12, 0, 0),
                datetime(2024, 1, 1, 12, 5, 0),
                datetime(2024, 1, 1, 12, 10, 0),
                datetime(2024, 1, 1, 12, 15, 0),
                datetime(2024, 1, 1, 12, 20, 0),
            ],
        }

        summary = MetricSummary.from_metric_data(metric_data)

        assert summary.id == 'metric_CPUUtilization_Average'
        assert summary.label == 'CPUUtilization'
        assert summary.data_status == 'Complete'
        assert summary.current_value == 12.3  # Last value
        assert summary.min_value == 10.5
        assert summary.max_value == 20.1
        assert summary.avg_value == 15.36  # Average of values
        assert summary.data_points_count == 5
        assert summary.change_percent == 17.14  # ((12.3 - 10.5) / 10.5) * 100

    def test_metric_summary_from_empty_data(self):
        """Test MetricSummary creation from empty metric data."""
        metric_data = {
            'Id': 'metric_test',
            'Label': 'TestMetric',
            'StatusCode': 'Complete',
            'Values': [],
            'Timestamps': [],
        }

        summary = MetricSummary.from_metric_data(metric_data)

        assert summary.id == 'metric_test'
        assert summary.label == 'TestMetric'
        assert summary.data_status == 'Complete'
        assert summary.current_value == 0
        assert summary.min_value == 0
        assert summary.max_value == 0
        assert summary.avg_value == 0
        assert summary.trend == 'no_data'
        assert summary.change_percent == 0
        assert summary.data_points_count == 0

    def test_metric_summary_trend_stable(self):
        """Test trend calculation for stable values."""
        metric_data = {
            'Id': 'test',
            'Label': 'Test',
            'StatusCode': 'Complete',
            'Values': [100.0, 100.5, 99.8, 100.2],  # Small changes < 1%
            'Timestamps': [
                datetime(2024, 1, 1, 12, 0, 0),
                datetime(2024, 1, 1, 12, 5, 0),
                datetime(2024, 1, 1, 12, 10, 0),
                datetime(2024, 1, 1, 12, 15, 0),
            ],
        }

        summary = MetricSummary.from_metric_data(metric_data)
        assert summary.trend == 'stable'

    def test_metric_summary_trend_increasing(self):
        """Test trend calculation for increasing values."""
        metric_data = {
            'Id': 'test',
            'Label': 'Test',
            'StatusCode': 'Complete',
            'Values': [100.0, 110.0],  # 10% increase
            'Timestamps': [
                datetime(2024, 1, 1, 12, 0, 0),
                datetime(2024, 1, 1, 12, 5, 0),
            ],
        }

        summary = MetricSummary.from_metric_data(metric_data)
        assert summary.trend == 'increasing'
        assert summary.change_percent == 10.0

    def test_metric_summary_trend_decreasing(self):
        """Test trend calculation for decreasing values."""
        metric_data = {
            'Id': 'test',
            'Label': 'Test',
            'StatusCode': 'Complete',
            'Values': [100.0, 90.0],  # 10% decrease
            'Timestamps': [
                datetime(2024, 1, 1, 12, 0, 0),
                datetime(2024, 1, 1, 12, 5, 0),
            ],
        }

        summary = MetricSummary.from_metric_data(metric_data)
        assert summary.trend == 'decreasing'
        assert summary.change_percent == -10.0

    def test_metric_summary_reversed_timestamps(self):
        """Test metric summary with timestamps in descending order."""
        metric_data = {
            'Id': 'test',
            'Label': 'Test',
            'StatusCode': 'Complete',
            'Values': [20.0, 10.0],  # Values corresponding to timestamps
            'Timestamps': [
                datetime(2024, 1, 1, 12, 5, 0),  # Later timestamp first
                datetime(2024, 1, 1, 12, 0, 0),  # Earlier timestamp second
            ],
        }

        summary = MetricSummary.from_metric_data(metric_data)
        assert summary.current_value == 20.0  # First value (most recent)


class TestDescribeRDSPerformanceMetrics:
    """Test cases for describe_rds_performance_metrics function."""

    @pytest.mark.asyncio
    async def test_describe_metrics_instance_success(self, mock_cloudwatch_client):
        """Test successful metrics retrieval for instance."""
        # Mock the CloudWatch client response
        mock_cloudwatch_client.get_paginator.return_value.paginate.return_value = [
            {
                'MetricDataResults': [
                    {
                        'Id': 'metric_CPUUtilization_Average',
                        'Label': 'CPUUtilization',
                        'StatusCode': 'Complete',
                        'Values': [15.5, 12.0, 18.0],
                        'Timestamps': [
                            datetime(2024, 1, 1, 12, 0, 0),
                            datetime(2024, 1, 1, 12, 5, 0),
                            datetime(2024, 1, 1, 12, 10, 0),
                        ],
                    }
                ]
            }
        ]

        result = await describe_rds_performance_metrics(
            resource_identifier='test-instance',
            resource_type='INSTANCE',
            start_date='2024-01-01T00:00:00Z',
            end_date='2024-01-01T23:59:59Z',
            period=300,
            stat='Average',
            scan_by='TimestampDescending',
        )

        assert isinstance(result, MetricSummaryList)
        assert result.resource_identifier == 'test-instance'
        assert result.resource_type == 'INSTANCE'
        assert len(result.metrics) == 1
        assert result.metrics[0].label == 'CPUUtilization'

    @pytest.mark.asyncio
    async def test_describe_metrics_cluster_success(self, mock_cloudwatch_client):
        """Test successful metrics retrieval for cluster."""
        mock_cloudwatch_client.get_paginator.return_value.paginate.return_value = [
            {
                'MetricDataResults': [
                    {
                        'Id': 'metric_VolumeBytesUsed_Average',
                        'Label': 'VolumeBytesUsed',
                        'StatusCode': 'Complete',
                        'Values': [1000000],
                        'Timestamps': [datetime(2024, 1, 1, 12, 0, 0)],
                    }
                ]
            }
        ]

        result = await describe_rds_performance_metrics(
            resource_identifier='test-cluster',
            resource_type='CLUSTER',
            start_date='2024-01-01T00:00:00Z',
            end_date='2024-01-01T23:59:59Z',
            period=300,
            stat='Average',
            scan_by='TimestampDescending',
        )

        assert result.resource_type == 'CLUSTER'

    @pytest.mark.asyncio
    async def test_describe_metrics_global_cluster(self, mock_cloudwatch_client):
        """Test metrics retrieval for global cluster."""
        mock_cloudwatch_client.get_paginator.return_value.paginate.return_value = [
            {'MetricDataResults': []}
        ]

        result = await describe_rds_performance_metrics(
            resource_identifier='test-global-cluster',
            resource_type='GLOBAL_CLUSTER',
            start_date='2024-01-01T00:00:00Z',
            end_date='2024-01-01T23:59:59Z',
            period=3600,
            stat='Maximum',
            scan_by='TimestampAscending',
        )

        assert result.resource_type == 'GLOBAL_CLUSTER'

    @pytest.mark.asyncio
    async def test_describe_metrics_with_z_suffix_dates(self, mock_cloudwatch_client):
        """Test metrics retrieval with Z suffix in dates."""
        mock_cloudwatch_client.get_paginator.return_value.paginate.return_value = [
            {'MetricDataResults': []}
        ]

        result = await describe_rds_performance_metrics(
            resource_identifier='test-instance',
            resource_type='INSTANCE',
            start_date='2024-01-01T00:00:00Z',
            end_date='2024-01-01T23:59:59Z',
            period=60,
            stat='Sum',
            scan_by='TimestampDescending',
        )

        assert result.resource_identifier == 'test-instance'

    @pytest.mark.asyncio
    async def test_describe_metrics_without_z_suffix_dates(self, mock_cloudwatch_client):
        """Test metrics retrieval without Z suffix in dates."""
        mock_cloudwatch_client.get_paginator.return_value.paginate.return_value = [
            {'MetricDataResults': []}
        ]

        result = await describe_rds_performance_metrics(
            resource_identifier='test-instance',
            resource_type='INSTANCE',
            start_date='2024-01-01T00:00:00+00:00',
            end_date='2024-01-01T23:59:59+00:00',
            period=60,
            stat='Minimum',
            scan_by='TimestampAscending',
        )

        assert result.resource_identifier == 'test-instance'

    @pytest.mark.asyncio
    async def test_describe_metrics_dimension_name_mapping(self, mock_cloudwatch_client):
        """Test that correct dimension names are used for different resource types."""
        mock_cloudwatch_client.get_paginator.return_value.paginate.return_value = [
            {'MetricDataResults': []}
        ]

        # Test instance dimension
        result = await describe_rds_performance_metrics(
            resource_identifier='test-instance',
            resource_type='INSTANCE',
            start_date='2024-01-01T00:00:00Z',
            end_date='2024-01-01T23:59:59Z',
            period=300,
            stat='Average',
            scan_by='TimestampDescending',
        )

        assert result.resource_identifier == 'test-instance'

        # Test cluster dimension
        result2 = await describe_rds_performance_metrics(
            resource_identifier='test-cluster',
            resource_type='CLUSTER',
            start_date='2024-01-01T00:00:00Z',
            end_date='2024-01-01T23:59:59Z',
            period=300,
            stat='Average',
            scan_by='TimestampDescending',
        )

        assert result2.resource_identifier == 'test-cluster'


class TestMetricsConstants:
    """Test cases for METRICS constants."""

    def test_instance_metrics(self):
        """Test that instance metrics are defined correctly."""
        instance_metrics = METRICS['INSTANCE']

        expected_metrics = [
            'CPUUtilization',
            'FreeableMemory',
            'DatabaseConnections',
            'ReadIOPS',
            'WriteIOPS',
        ]

        for metric in expected_metrics:
            assert metric in instance_metrics

    def test_cluster_metrics(self):
        """Test that cluster metrics are defined correctly."""
        cluster_metrics = METRICS['CLUSTER']

        expected_metrics = [
            'AuroraVolumeBytesLeftTotal',
            'VolumeBytesUsed',
            'VolumeReadIOPs',
            'VolumeWriteIOPs',
        ]

        for metric in expected_metrics:
            assert metric in cluster_metrics

    def test_global_cluster_metrics(self):
        """Test that global cluster metrics are defined correctly."""
        global_cluster_metrics = METRICS['GLOBAL_CLUSTER']

        expected_metrics = ['AuroraGlobalDBReplicationLag', 'AuroraGlobalDBReplicatedWriteIO']

        for metric in expected_metrics:
            assert metric in global_cluster_metrics

    def test_all_resource_types_present(self):
        """Test that all expected resource types are present."""
        expected_types = ['INSTANCE', 'CLUSTER', 'GLOBAL_CLUSTER']

        for resource_type in expected_types:
            assert resource_type in METRICS
            assert isinstance(METRICS[resource_type], list)
            assert len(METRICS[resource_type]) > 0
