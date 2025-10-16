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
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import (
    AlarmRecommendation,
    AlarmRecommendationDimension,
    Dimension,
    GetMetricDataResponse,
    MetricDataPoint,
    MetricDataResult,
    MetricMetadata,
    MetricMetadataIndexKey,
    StaticAlarmThreshold,
)
from datetime import datetime
from pydantic import ValidationError


class TestDimension:
    """Tests for the Dimension model."""

    def test_dimension_creation(self):
        """Test creating a Dimension instance."""
        dimension = Dimension(name='InstanceId', value='i-1234567890abcdef0')
        assert dimension.name == 'InstanceId'
        assert dimension.value == 'i-1234567890abcdef0'

    def test_dimension_validation(self):
        """Test validation for Dimension model."""
        # Missing required fields should raise ValidationError
        with pytest.raises(ValidationError):
            Dimension(name='InstanceId')  # type: ignore[call-arg] # Missing value

        with pytest.raises(ValidationError):
            Dimension(value='i-1234567890abcdef0')  # type: ignore[call-arg] # Missing name


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
            MetricDataPoint(timestamp=timestamp)  # type: ignore[call-arg] # Missing value

        with pytest.raises(ValidationError):
            MetricDataPoint(value=10.5)  # type: ignore[call-arg] # Missing timestamp


class TestMetricDataResult:
    """Tests for the MetricDataResult model."""

    def test_metric_data_result_creation(self):
        """Test creating a MetricDataResult instance."""
        timestamp = datetime(2023, 1, 1, 0, 0, 0)
        data_point = MetricDataPoint(timestamp=timestamp, value=10.5)

        result = MetricDataResult(
            id='m1',
            label='CPUUtilization',
            statusCode='Complete',
            datapoints=[data_point],
            messages=[],
        )

        assert result.id == 'm1'
        assert result.label == 'CPUUtilization'
        assert result.statusCode == 'Complete'
        assert len(result.datapoints) == 1
        assert result.datapoints[0].timestamp == timestamp
        assert result.datapoints[0].value == 10.5
        assert result.messages == []

    def test_metric_data_result_default_values(self):
        """Test default values for MetricDataResult model."""
        result = MetricDataResult(id='m1', label='CPUUtilization', statusCode='Complete')

        assert result.datapoints == []
        assert result.messages == []


class TestGetMetricDataResponse:
    """Tests for the GetMetricDataResponse model."""

    def test_get_metric_data_response_creation(self):
        """Test creating a GetMetricDataResponse instance."""
        timestamp = datetime(2023, 1, 1, 0, 0, 0)
        data_point = MetricDataPoint(timestamp=timestamp, value=10.5)

        metric_result = MetricDataResult(
            id='m1', label='CPUUtilization', statusCode='Complete', datapoints=[data_point]
        )

        response = GetMetricDataResponse(metricDataResults=[metric_result], messages=[])

        assert len(response.metricDataResults) == 1
        assert response.metricDataResults[0].id == 'm1'
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
            id='m1', label='CPUUtilization', statusCode='Complete', datapoints=[data_point1]
        )

        metric_result2 = MetricDataResult(
            id='m2', label='MemoryUtilization', statusCode='Complete', datapoints=[data_point2]
        )

        response = GetMetricDataResponse(metricDataResults=[metric_result1, metric_result2])

        assert len(response.metricDataResults) == 2
        assert response.metricDataResults[0].label == 'CPUUtilization'
        assert response.metricDataResults[1].label == 'MemoryUtilization'


class TestMetricMetadataIndexKey:
    """Tests for MetricMetadataIndexKey model."""

    def test_key_creation(self):
        """Test creating a metric metadata index key."""
        key = MetricMetadataIndexKey('AWS/EC2', 'CPUUtilization')

        assert key.namespace == 'AWS/EC2'
        assert key.metric_name == 'CPUUtilization'

    def test_key_hashing(self):
        """Test that keys can be hashed for dictionary use."""
        key1 = MetricMetadataIndexKey('AWS/EC2', 'CPUUtilization')
        key2 = MetricMetadataIndexKey('AWS/EC2', 'CPUUtilization')
        key3 = MetricMetadataIndexKey('AWS/Lambda', 'Duration')

        # Same keys should have same hash
        assert hash(key1) == hash(key2)

        # Different keys should have different hash (usually)
        assert hash(key1) != hash(key3)

    def test_key_equality(self):
        """Test key equality comparison."""
        key1 = MetricMetadataIndexKey('AWS/EC2', 'CPUUtilization')
        key2 = MetricMetadataIndexKey('AWS/EC2', 'CPUUtilization')
        key3 = MetricMetadataIndexKey('AWS/Lambda', 'Duration')

        # Same keys should be equal
        assert key1 == key2

        # Different keys should not be equal
        assert key1 != key3

        # Key should not equal non-key objects
        assert key1 != 'not a key'

    def test_key_as_dict_key(self):
        """Test using key as dictionary key."""
        key1 = MetricMetadataIndexKey('AWS/EC2', 'CPUUtilization')
        key2 = MetricMetadataIndexKey('AWS/EC2', 'CPUUtilization')
        key3 = MetricMetadataIndexKey('AWS/Lambda', 'Duration')

        test_dict = {}
        test_dict[key1] = 'value1'
        test_dict[key3] = 'value2'

        # Should be able to retrieve using equivalent key
        assert test_dict[key2] == 'value1'
        assert test_dict[key3] == 'value2'

        # Should have 2 entries
        assert len(test_dict) == 2

    def test_key_repr(self):
        """Test string representation of key."""
        key = MetricMetadataIndexKey('AWS/EC2', 'CPUUtilization')
        repr_str = repr(key)

        assert 'MetricMetadataIndexKey' in repr_str
        assert 'AWS/EC2' in repr_str
        assert 'CPUUtilization' in repr_str


class TestMetricMetadata:
    """Tests for MetricMetadata model."""

    def test_metric_metadata_creation(self):
        """Test creating a metric metadata with all fields."""
        description = MetricMetadata(
            description='Test metric description',
            recommendedStatistics='Average, Maximum, Minimum',
            unit='Percent',
        )

        assert description.description == 'Test metric description'
        assert description.recommendedStatistics == 'Average, Maximum, Minimum'
        assert description.unit == 'Percent'

    def test_metric_metadata_validation(self):
        """Test metric metadata field validation."""
        # Test that all fields are required
        with pytest.raises(ValidationError):
            MetricMetadata()  # type: ignore[call-arg] # Missing all required fields

        with pytest.raises(ValidationError):
            MetricMetadata(description='Test')  # type: ignore[call-arg] # Missing recommendedStatistics and unit


class TestDimensionValidation:
    """Tests for Dimension model validation."""

    def test_dimension_creation(self):
        """Test creating a dimension."""
        dimension = Dimension(name='InstanceId', value='i-1234567890abcdef0')

        assert dimension.name == 'InstanceId'
        assert dimension.value == 'i-1234567890abcdef0'

    def test_dimension_validation(self):
        """Test dimension field validation."""
        # Test that all fields are required
        with pytest.raises(ValidationError):
            Dimension()  # type: ignore[call-arg] # Missing name and value


class TestAlarmRecommendationDimension:
    """Tests for TestAlarmRecommendationDimension model."""

    def test_alarm_recommendation_dimension_creation_with_value(self):
        """Test creating an alarm recommendation dimension with value."""
        dimension = AlarmRecommendationDimension(name='Role', value='WRITER')

        assert dimension.name == 'Role'
        assert dimension.value == 'WRITER'

    def test_alarm_recommendation_dimension_creation_without_value(self):
        """Test creating an alarm recommendation dimension without value."""
        dimension = AlarmRecommendationDimension(name='InstanceId')

        assert dimension.name == 'InstanceId'
        assert dimension.value is None


class TestAlarmRecommendation:
    """Tests for AlarmRecommendation model."""

    def test_alarm_recommendation_creation(self):
        """Test creating an alarm recommendation."""
        threshold = StaticAlarmThreshold(staticValue=80.0, justification='Test justification')

        dimensions = [
            AlarmRecommendationDimension(name='InstanceId', value='i-1234567890abcdef0'),
            AlarmRecommendationDimension(name='Role', value='WRITER'),
        ]

        alarm = AlarmRecommendation(
            alarmDescription='Test alarm description',
            threshold=threshold,
            period=300,
            comparisonOperator='GreaterThanThreshold',
            statistic='Average',
            evaluationPeriods=2,
            datapointsToAlarm=2,
            treatMissingData='missing',
            dimensions=dimensions,
            intent='Test alarm intent',
            cloudformation_template={'test': 'template'},
        )

        assert alarm.alarmDescription == 'Test alarm description'
        assert isinstance(alarm.threshold, StaticAlarmThreshold)
        assert alarm.threshold.staticValue == 80.0
        assert alarm.period == 300
        assert alarm.comparisonOperator == 'GreaterThanThreshold'
        assert alarm.statistic == 'Average'
        assert alarm.evaluationPeriods == 2
        assert alarm.datapointsToAlarm == 2
        assert alarm.treatMissingData == 'missing'
        assert len(alarm.dimensions) == 2
        assert alarm.intent == 'Test alarm intent'
        assert alarm.cloudformation_template == {'test': 'template'}

    def test_alarm_recommendation_with_minimal_fields(self):
        """Test creating an alarm recommendation with minimal fields."""
        threshold = StaticAlarmThreshold(staticValue=1.0, justification='Test')

        alarm = AlarmRecommendation(
            alarmDescription='Minimal alarm',
            threshold=threshold,
            period=60,
            comparisonOperator='GreaterThanThreshold',
            statistic='Maximum',
            evaluationPeriods=1,
            datapointsToAlarm=1,
            treatMissingData='missing',
            intent='Minimal test',
        )

        assert alarm.alarmDescription == 'Minimal alarm'
        assert len(alarm.dimensions) == 0  # Default empty list
        assert alarm.cloudformation_template is None  # Default None for non-anomaly alarms

    def test_alarm_recommendation_serialization(self):
        """Test alarm recommendation serialization."""
        threshold = StaticAlarmThreshold(staticValue=80.0, justification='Test')
        alarm = AlarmRecommendation(
            alarmDescription='Test',
            threshold=threshold,
            period=300,
            comparisonOperator='GreaterThanThreshold',
            statistic='Average',
            evaluationPeriods=1,
            datapointsToAlarm=1,
            treatMissingData='missing',
            intent='Test',
            cloudformation_template={'test': 'value'},
        )

        serialized = alarm.model_dump()
        assert 'alarmDescription' in serialized
        assert 'cloudformation_template' in serialized
        assert serialized['cloudformation_template'] == {'test': 'value'}

    def test_alarm_recommendation_serialization_without_template(self):
        """Test alarm recommendation serialization without cloudformation_template."""
        threshold = StaticAlarmThreshold(staticValue=80.0, justification='Test')
        alarm = AlarmRecommendation(
            alarmDescription='Test',
            threshold=threshold,
            period=300,
            comparisonOperator='GreaterThanThreshold',
            statistic='Average',
            evaluationPeriods=1,
            datapointsToAlarm=1,
            treatMissingData='missing',
            intent='Test',
        )

        serialized = alarm.model_dump()
        assert 'alarmDescription' in serialized
        assert 'cloudformation_template' not in serialized


class TestAnomalyDetectionAlarmThreshold:
    """Tests for AnomalyDetectionAlarmThreshold model."""

    def test_sensitivity_validation_invalid_zero(self):
        """Test sensitivity validation rejects zero."""
        from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import (
            AnomalyDetectionAlarmThreshold,
        )

        with pytest.raises(
            ValueError, match='Sensitivity must be above 0 and less than or equal to 100'
        ):
            AnomalyDetectionAlarmThreshold(sensitivity=0, justification='Test')

    def test_sensitivity_validation_invalid_negative(self):
        """Test sensitivity validation rejects negative values."""
        from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import (
            AnomalyDetectionAlarmThreshold,
        )

        with pytest.raises(
            ValueError, match='Sensitivity must be above 0 and less than or equal to 100'
        ):
            AnomalyDetectionAlarmThreshold(sensitivity=-1, justification='Test')

    def test_sensitivity_validation_invalid_over_100(self):
        """Test sensitivity validation rejects values over 100."""
        from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import (
            AnomalyDetectionAlarmThreshold,
        )

        with pytest.raises(
            ValueError, match='Sensitivity must be above 0 and less than or equal to 100'
        ):
            AnomalyDetectionAlarmThreshold(sensitivity=101, justification='Test')


class TestMetricData:
    """Tests for the MetricData model."""

    def test_metric_data_valid(self):
        """Test MetricData with valid data."""
        from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import MetricData

        data = MetricData(
            period_seconds=60, timestamps=[1000, 2000, 3000], values=[10.0, 20.0, 30.0]
        )

        assert data.period_seconds == 60
        assert len(data.timestamps) == 3
        assert len(data.values) == 3

    def test_metric_data_mismatched_lengths(self):
        """Test MetricData with mismatched timestamp/value lengths."""
        from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import MetricData

        with pytest.raises(ValueError, match='Timestamps and values must have the same length'):
            MetricData(period_seconds=60, timestamps=[1000, 2000], values=[10.0, 20.0, 30.0])

    def test_metric_data_invalid_period(self):
        """Test MetricData with invalid period."""
        from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import MetricData

        with pytest.raises(ValueError, match='Timeseries must have a period >= 0'):
            MetricData(period_seconds=0, timestamps=[1000], values=[10.0])
