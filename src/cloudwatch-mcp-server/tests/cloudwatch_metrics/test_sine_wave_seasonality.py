"""Test sine wave seasonality detection and alarm recommendations."""

import pytest
import math
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.metric_analyzer import MetricAnalyzer
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools import CloudWatchMetricsTools
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import Dimension
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.seasonal_detector import Seasonality


class TestSineWaveSeasonality:
    """Test sine wave seasonality detection and alarm recommendations."""

    @pytest.fixture
    def metric_analyzer(self):
        return MetricAnalyzer()

    def create_sine_wave_response(self, hours=24, period_hours=24, amplitude=500, offset=1000):
        """Create mock metric data response with sine wave data."""
        datapoints = []
        base_time = datetime.utcnow() - timedelta(hours=hours)
        
        for i in range(hours):
            timestamp = base_time + timedelta(hours=i)
            value = offset + amplitude * math.sin(2 * math.pi * i / period_hours)
            
            datapoint = MagicMock()
            datapoint.timestamp = timestamp
            datapoint.value = value
            datapoints.append(datapoint)
        
        metric_result = MagicMock()
        metric_result.datapoints = datapoints
        
        response = MagicMock()
        response.metricDataResults = [metric_result]
        
        return response

    def test_sine_wave_seasonality_detection(self, metric_analyzer):
        """Test that sine wave is detected as seasonal."""
        response = self.create_sine_wave_response(hours=72, period_hours=24)
        
        result = metric_analyzer.analyze_metric_from_get_metric_data(
            metric_data_response=response,
            namespace="Test",
            metric_name="SineWave",
            dimensions=[],
            analysis_period_minutes=4320  # 72 hours
        )
        
        assert result['seasonality_seconds'] != 0, f"Expected seasonality detection, got: {result['seasonality_seconds']}"
        assert result['data_points_found'] == 72

    async def test_sine_wave_alarm_recommendations(self):
        """Test that sine wave generates anomaly detection alarm recommendations."""
        # Create 72 hours of hourly sine wave data (3 complete 24-hour cycles)
        response = self.create_sine_wave_response(hours=72, period_hours=24)
        
        # Mock the get_metric_data method to return our sine wave
        tools = CloudWatchMetricsTools()
        with patch.object(tools, 'get_metric_data') as mock_get_metric_data:
            mock_get_metric_data.return_value = response
            
            ctx = AsyncMock()
            # Use a metric that has existing recommendations (AWS/EC2/CPUUtilization)
            result = await tools.get_recommended_metric_alarms(
                ctx,
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                dimensions=[]  # No specific dimensions
            )
            
            # Should generate anomaly detection alarm for seasonal sine wave
            assert len(result) == 1, f"Should generate exactly one alarm recommendation: {len(result)}"
            
            # Find the anomaly detection alarm
            anomaly_alarms = [r for r in result if 'AnomalyDetector' in r.alarmName]
            assert len(anomaly_alarms) == 1, "Should generate exactly one anomaly detection alarm for seasonal data"
            
            anomaly_alarm = anomaly_alarms[0]
            assert anomaly_alarm.threshold.type == "anomaly_detection"
            assert "seasonality" in anomaly_alarm.alarmDescription.lower()
            assert anomaly_alarm.comparisonOperator == "LessThanLowerOrGreaterThanUpperThreshold"

    async def test_non_seasonal_data_no_anomaly_alarm(self):
        """Test that non-seasonal data doesn't generate anomaly detection alarms."""
        # Create flat line data (no seasonality)
        datapoints = []
        base_time = datetime.utcnow() - timedelta(hours=72)
        
        for i in range(72):
            timestamp = base_time + timedelta(hours=i)
            value = 1000  # Constant value
            
            datapoint = MagicMock()
            datapoint.timestamp = timestamp
            datapoint.value = value
            datapoints.append(datapoint)
        
        metric_result = MagicMock()
        metric_result.datapoints = datapoints
        
        response = MagicMock()
        response.metricDataResults = [metric_result]
        
        # Test the metric analyzer directly to verify no seasonality
        analyzer = MetricAnalyzer()
        result = analyzer.analyze_metric_from_get_metric_data(
            metric_data_response=response,
            namespace="Test",
            metric_name="FlatLine",
            dimensions=[],
            analysis_period_minutes=4320
        )
        
        # Flat line should not be detected as seasonal
        assert result['seasonality_seconds'] == Seasonality.NONE, f"Flat line should not be seasonal: {result['seasonality_seconds']}"
