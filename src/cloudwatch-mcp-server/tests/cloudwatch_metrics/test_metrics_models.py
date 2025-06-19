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
"""Tests for CloudWatch Metrics models."""

import pytest
from datetime import datetime
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import (
    Dimension,
    MetricDataPoint,
    MetricDataResult,
    GetMetricDataResponse,
)
from pydantic import ValidationError


class TestDimension:
    """Tests for the Dimension model."""

    def test_dimension_creation(self):
        """Test creating a Dimension instance."""
        dimension = Dimension(name="InstanceId", value="i-1234567890abcdef0")
        assert dimension.name == "InstanceId"
        assert dimension.value == "i-1234567890abcdef0"

    def test_dimension_validation(self):
        """Test validation for Dimension model."""
        # Missing required fields should raise ValidationError
        with pytest.raises(ValidationError):
            Dimension(name="InstanceId")  # Missing value
        
        with pytest.raises(ValidationError):
            Dimension(value="i-1234567890abcdef0")  # Missing name


class TestMetricDataPoint:
    """Tests for the MetricDataPoint model."""

    def test_metric_data_point_creation(self):
        """Test creating a MetricDataPoint instance."""
        timestamp = datetime(2023, 1, 1, 0, 0, 0)
        data_point = MetricDataPoint(timestamp=timestamp, value=10.5)
        
        assert data_point.timestamp == timestamp
        assert data_point.value == 10.5

    def test_metric_data_point_validation(self):
        """Test validation for MetricDataPoint model."""
        timestamp = datetime(2023, 1, 1, 0, 0, 0)
        
        # Missing required fields should raise ValidationError
        with pytest.raises(ValidationError):
            MetricDataPoint(timestamp=timestamp)  # Missing value
        
        with pytest.raises(ValidationError):
            MetricDataPoint(value=10.5)  # Missing timestamp


class TestMetricDataResult:
    """Tests for the MetricDataResult model."""

    def test_metric_data_result_creation(self):
        """Test creating a MetricDataResult instance."""
        timestamp = datetime(2023, 1, 1, 0, 0, 0)
        data_point = MetricDataPoint(timestamp=timestamp, value=10.5)
        
        result = MetricDataResult(
            id="m1",
            label="CPUUtilization",
            statusCode="Complete",
            datapoints=[data_point],
            messages=[]
        )
        
        assert result.id == "m1"
        assert result.label == "CPUUtilization"
        assert result.statusCode == "Complete"
        assert len(result.datapoints) == 1
        assert result.datapoints[0].timestamp == timestamp
        assert result.datapoints[0].value == 10.5
        assert result.messages == []

    def test_metric_data_result_default_values(self):
        """Test default values for MetricDataResult model."""
        result = MetricDataResult(
            id="m1",
            label="CPUUtilization",
            statusCode="Complete"
        )
        
        assert result.datapoints == []
        assert result.messages == []


class TestGetMetricDataResponse:
    """Tests for the GetMetricDataResponse model."""

    def test_get_metric_data_response_creation(self):
        """Test creating a GetMetricDataResponse instance."""
        timestamp = datetime(2023, 1, 1, 0, 0, 0)
        data_point = MetricDataPoint(timestamp=timestamp, value=10.5)
        
        metric_result = MetricDataResult(
            id="m1",
            label="CPUUtilization",
            statusCode="Complete",
            datapoints=[data_point]
        )
        
        response = GetMetricDataResponse(
            metricDataResults=[metric_result],
            messages=[]
        )
        
        assert len(response.metricDataResults) == 1
        assert response.metricDataResults[0].id == "m1"
        assert response.messages == []

    def test_get_metric_data_response_default_values(self):
        """Test default values for GetMetricDataResponse model."""
        response = GetMetricDataResponse()
        
        assert response.metricDataResults == []
        assert response.messages == []

    def test_get_metric_data_response_with_multiple_results(self):
        """Test GetMetricDataResponse with multiple metric results."""
        timestamp1 = datetime(2023, 1, 1, 0, 0, 0)
        timestamp2 = datetime(2023, 1, 1, 0, 5, 0)
        
        data_point1 = MetricDataPoint(timestamp=timestamp1, value=10.5)
        data_point2 = MetricDataPoint(timestamp=timestamp2, value=15.2)
        
        metric_result1 = MetricDataResult(
            id="m1",
            label="CPUUtilization",
            statusCode="Complete",
            datapoints=[data_point1]
        )
        
        metric_result2 = MetricDataResult(
            id="m2",
            label="MemoryUtilization",
            statusCode="Complete",
            datapoints=[data_point2]
        )
        
        response = GetMetricDataResponse(
            metricDataResults=[metric_result1, metric_result2]
        )
        
        assert len(response.metricDataResults) == 2
        assert response.metricDataResults[0].label == "CPUUtilization"
        assert response.metricDataResults[1].label == "MemoryUtilization"