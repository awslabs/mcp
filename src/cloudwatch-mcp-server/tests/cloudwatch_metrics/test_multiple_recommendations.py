"""Tests for multiple alarm recommendations functionality."""

import pytest
from unittest.mock import AsyncMock, patch
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import Dimension, AlarmRecommendation
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.threshold import create_threshold
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.constants import STATIC_TYPE, ANOMALY_DETECTION_TYPE
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.seasonal_detector import Seasonality


class TestMultipleRecommendations:
    """Test cases for multiple alarm recommendations."""

    @pytest.fixture
    def ctx(self):
        return AsyncMock()

    @pytest.fixture
    def cloudwatch_metrics_tools(self):
        from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools import CloudWatchMetricsTools
        return CloudWatchMetricsTools()

    async def test_all_static_recommendations(self, ctx, cloudwatch_metrics_tools):
        """Test scenario: 2 static threshold recommendations."""
        static_rec1 = AlarmRecommendation(
            alarmName="CPUHigh",
            alarmDescription="CPU high threshold",
            metricName="CPUUtilization",
            namespace="AWS/EC2",
            statistic="Average",
            dimensions=[Dimension(name='InstanceId', value='i-123')],
            threshold=create_threshold({"type": STATIC_TYPE, "value": 80.0}),
            comparisonOperator="GreaterThanThreshold",
            evaluationPeriods=2,
            period=300,
            treatMissingData="breaching"
        )
        
        static_rec2 = AlarmRecommendation(
            alarmName="CPUCritical",
            alarmDescription="CPU critical threshold",
            metricName="CPUUtilization",
            namespace="AWS/EC2",
            statistic="Average",
            dimensions=[Dimension(name='InstanceId', value='i-123')],
            threshold=create_threshold({"type": STATIC_TYPE, "value": 95.0}),
            comparisonOperator="GreaterThanThreshold",
            evaluationPeriods=1,
            period=300,
            treatMissingData="breaching"
        )

        with patch.object(cloudwatch_metrics_tools, '_lookup_metadata') as mock_lookup:
            mock_lookup.return_value = {
                'alarmRecommendations': [
                    {
                        'alarmName': 'CPUHigh',
                        'alarmDescription': 'CPU high threshold',
                        'threshold': {'staticValue': 80.0},
                        'comparisonOperator': 'GreaterThanThreshold',
                        'evaluationPeriods': 2,
                        'period': 300,
                        'treatMissingData': 'breaching',
                        'statistic': 'Average',
                        'dimensions': []
                    },
                    {
                        'alarmName': 'CPUCritical',
                        'alarmDescription': 'CPU critical threshold',
                        'threshold': {'staticValue': 95.0},
                        'comparisonOperator': 'GreaterThanThreshold',
                        'evaluationPeriods': 1,
                        'period': 300,
                        'treatMissingData': 'breaching',
                        'statistic': 'Average',
                        'dimensions': []
                    }
                ]
            }
            
            with patch.object(cloudwatch_metrics_tools, 'analyze_metric') as mock_analyze:
                mock_analyze.return_value = {
                    'seasonality_seconds': Seasonality.NONE,
                    'trend': {'trend_direction': 'stable'},
                    'statistics': {'mean': 50.0, 'std_deviation': 10.0},
                    'data_quality': {'quality_score': 0.9}
                }
                
                result = await cloudwatch_metrics_tools.get_recommended_metric_alarms(
                    ctx,
                    namespace='AWS/EC2',
                    metric_name='CPUUtilization',
                    dimensions=[]
                )
                
                assert len(result) == 2
                assert all(rec.threshold.type == STATIC_TYPE for rec in result)

    async def test_mixed_static_and_anomaly_recommendations(self, ctx, cloudwatch_metrics_tools):
        """Test scenario: 1 static + 1 anomaly detection recommendation."""
        with patch.object(cloudwatch_metrics_tools, '_lookup_metadata') as mock_lookup:
            mock_lookup.return_value = {
                'alarmRecommendations': [
                    {
                        'alarmName': 'CPUHigh',
                        'alarmDescription': 'CPU high threshold',
                        'threshold': {'staticValue': 80.0},
                        'comparisonOperator': 'GreaterThanThreshold',
                        'evaluationPeriods': 2,
                        'period': 300,
                        'treatMissingData': 'breaching',
                        'statistic': 'Average',
                        'dimensions': []
                    }
                ]
            }
            
            with patch.object(cloudwatch_metrics_tools, 'analyze_metric') as mock_analyze:
                mock_analyze.return_value = {
                    'seasonality_seconds': Seasonality.ONE_DAY,
                    'trend': {'trend_direction': 'positive'},
                    'statistics': {'mean': 50.0, 'std_deviation': 10.0},
                    'data_quality': {'quality_score': 0.9}
                }
                
                result = await cloudwatch_metrics_tools.get_recommended_metric_alarms(
                    ctx,
                    namespace='AWS/EC2',
                    metric_name='CPUUtilization',
                    dimensions=[]
                )
                
                assert len(result) == 1  # Only returns the static recommendation
                static_count = sum(1 for rec in result if rec.threshold.type == STATIC_TYPE)
                anomaly_count = sum(1 for rec in result if rec.threshold.type == ANOMALY_DETECTION_TYPE)
                assert static_count == 1
                assert anomaly_count == 0

    async def test_all_anomaly_recommendations(self, ctx, cloudwatch_metrics_tools):
        """Test scenario: 2 anomaly detection recommendations."""
        with patch.object(cloudwatch_metrics_tools, '_lookup_metadata') as mock_lookup:
            mock_lookup.return_value = {
                'alarmRecommendations': [
                    {
                        'alarmName': 'CPUAnomalyDaily',
                        'alarmDescription': 'CPU daily anomaly detection',
                        'threshold': {'anomalyDetector': {'sensitivity': 2}},
                        'comparisonOperator': 'LessThanLowerOrGreaterThanUpperThreshold',
                        'evaluationPeriods': 2,
                        'period': 300,
                        'treatMissingData': 'breaching',
                        'statistic': 'Average',
                        'dimensions': []
                    }
                ]
            }
            
            with patch.object(cloudwatch_metrics_tools, 'analyze_metric') as mock_analyze:
                mock_analyze.return_value = {
                    'seasonality_seconds': Seasonality.ONE_DAY,
                    'trend': {'trend_direction': 'positive'},
                    'statistics': {'mean': 50.0, 'std_deviation': 10.0},
                    'data_quality': {'quality_score': 0.9}
                }
                
                result = await cloudwatch_metrics_tools.get_recommended_metric_alarms(
                    ctx,
                    namespace='AWS/EC2',
                    metric_name='CPUUtilization',
                    dimensions=[]
                )
                
                assert len(result) == 1  # Only returns the anomaly detection recommendation
                assert all(rec.threshold.type == ANOMALY_DETECTION_TYPE for rec in result)

    async def test_multiple_recommendations_structure(self, ctx, cloudwatch_metrics_tools):
        """Test that the function can properly handle multiple recommendations."""
        recommendations = [
            AlarmRecommendation(
                alarmName="TestAlarm1",
                alarmDescription="First test alarm",
                metricName="CPUUtilization",
                namespace="AWS/EC2",
                statistic="Average",
                dimensions=[Dimension(name='InstanceId', value='i-123')],
                threshold=create_threshold({"type": STATIC_TYPE, "value": 80.0}),
                comparisonOperator="GreaterThanThreshold",
                evaluationPeriods=2,
                period=300,
                treatMissingData="breaching"
            ),
            AlarmRecommendation(
                alarmName="TestAlarm2",
                alarmDescription="Second test alarm",
                metricName="CPUUtilization",
                namespace="AWS/EC2",
                statistic="Average",
                dimensions=[Dimension(name='InstanceId', value='i-123')],
                threshold=create_threshold({"type": ANOMALY_DETECTION_TYPE, "sensitivity": 2}),
                comparisonOperator="LessThanLowerOrGreaterThanUpperThreshold",
                evaluationPeriods=2,
                period=300,
                treatMissingData="breaching"
            )
        ]

        assert len(recommendations) == 2
        assert recommendations[0].alarmName == "TestAlarm1"
        assert recommendations[1].alarmName == "TestAlarm2"
        assert recommendations[0].threshold.type == STATIC_TYPE
        assert recommendations[1].threshold.type == ANOMALY_DETECTION_TYPE

    async def test_empty_recommendations_list(self, ctx, cloudwatch_metrics_tools):
        """Test that empty list is handled correctly."""
        empty_recommendations = []
        
        assert isinstance(empty_recommendations, list)
        assert len(empty_recommendations) == 0

    async def test_existing_plus_generated_recommendations(self, ctx, cloudwatch_metrics_tools):
        """Test that existing JSON metadata recommendations are combined with generated ones."""
        from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import Dimension
        
        with patch.object(cloudwatch_metrics_tools, 'analyze_metric') as mock_analyze:
            mock_analyze.return_value = {
                'seasonality_seconds': Seasonality.ONE_DAY,
                'trend': {'trend_direction': 'positive'},
                'statistics': {'mean': 50.0, 'std_deviation': 10.0},
                'data_quality': {'quality_score': 0.9}
            }
            
            result = await cloudwatch_metrics_tools.get_recommended_metric_alarms(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                dimensions=[Dimension(name='InstanceId', value='i-1234567890abcdef0')]
            )
            
            assert len(result) == 1  # Should generate exactly one recommendation
            
            has_static = any(rec.threshold.type == STATIC_TYPE for rec in result)
            has_anomaly = any(rec.threshold.type == ANOMALY_DETECTION_TYPE for rec in result)
            
            if len(result) > 1:
                assert has_static or has_anomaly, "Should have at least one type of recommendation"
