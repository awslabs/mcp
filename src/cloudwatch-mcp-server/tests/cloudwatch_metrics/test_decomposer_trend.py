"""Tests for trend detection in MetricDataDecomposer."""

import math
import pytest
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import Seasonality, Trend
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.metric_data_decomposer import MetricDataDecomposer
from datetime import datetime


class TestDecomposerTrend:
    """Test trend detection on seasonal and non-seasonal data."""

    @pytest.fixture
    def decomposer(self):
        """Create MetricDataDecomposer instance for testing."""
        return MetricDataDecomposer()

    def test_perfect_sine_wave_no_trend(self, decomposer):
        """Perfect sine wave centered at 1000 should have no trend."""
        timestamps_ms = []
        values = []
        base_time = int(datetime.utcnow().timestamp() * 1000)

        # Create perfect sine wave over 2 weeks
        for i in range(336):  # 2 weeks of hourly data
            timestamp = base_time + i * 60 * 60 * 1000
            # Perfect sine wave with 24-hour period, centered at 1000
            value = 1000.0 + 500.0 * math.sin(2 * math.pi * i / 24)
            timestamps_ms.append(timestamp)
            values.append(value)

        result = decomposer.detect_seasonality_and_trend(timestamps_ms, values, 1.0, 3600)

        # Should detect seasonality (daily or weekly for 2 weeks of data)
        assert result.seasonality in [Seasonality.ONE_DAY, Seasonality.ONE_WEEK]
        # Perfect sine wave should have NO trend
        assert result.trend == Trend.NONE, f'Expected NONE but got {result.trend}'

    def test_sine_wave_with_positive_trend(self, decomposer):
        """Sine wave with positive linear trend should be detected."""
        timestamps_ms = []
        values = []
        base_time = int(datetime.utcnow().timestamp() * 1000)

        # Create sine wave with strong positive trend
        for i in range(336):  # 2 weeks of hourly data
            timestamp = base_time + i * 60 * 60 * 1000
            # Sine wave + significant linear trend
            value = 1000.0 + 500.0 * math.sin(2 * math.pi * i / 24) + (i * 5.0)
            timestamps_ms.append(timestamp)
            values.append(value)

        result = decomposer.detect_seasonality_and_trend(timestamps_ms, values, 1.0, 3600)

        # Should detect daily seasonality
        assert result.seasonality == Seasonality.ONE_DAY
        # Should detect positive trend
        assert result.trend == Trend.POSITIVE

    def test_sine_wave_with_negative_trend(self, decomposer):
        """Sine wave with negative linear trend should be detected."""
        timestamps_ms = []
        values = []
        base_time = int(datetime.utcnow().timestamp() * 1000)

        # Create sine wave with strong negative trend
        for i in range(336):  # 2 weeks of hourly data
            timestamp = base_time + i * 60 * 60 * 1000
            # Sine wave + significant negative trend
            value = 2000.0 + 500.0 * math.sin(2 * math.pi * i / 24) - (i * 5.0)
            timestamps_ms.append(timestamp)
            values.append(value)

        result = decomposer.detect_seasonality_and_trend(timestamps_ms, values, 1.0, 3600)

        # Should detect daily seasonality
        assert result.seasonality == Seasonality.ONE_DAY
        # Should detect negative trend
        assert result.trend == Trend.NEGATIVE

    def test_non_seasonal_positive_trend(self, decomposer):
        """Non-seasonal data with positive trend."""
        timestamps_ms = []
        values = []
        base_time = int(datetime.utcnow().timestamp() * 1000)

        # Linear increase with noise
        for i in range(100):
            timestamp = base_time + i * 60 * 1000
            value = 100.0 + (i * 2.0)  # Clear positive trend
            timestamps_ms.append(timestamp)
            values.append(value)

        result = decomposer.detect_seasonality_and_trend(timestamps_ms, values, 1.0, 60)

        # Should not detect seasonality
        assert result.seasonality == Seasonality.NONE
        # Should detect positive trend
        assert result.trend == Trend.POSITIVE

    def test_non_seasonal_negative_trend(self, decomposer):
        """Non-seasonal data with negative trend."""
        timestamps_ms = []
        values = []
        base_time = int(datetime.utcnow().timestamp() * 1000)

        # Linear decrease
        for i in range(100):
            timestamp = base_time + i * 60 * 1000
            value = 500.0 - (i * 2.0)  # Clear negative trend
            timestamps_ms.append(timestamp)
            values.append(value)

        result = decomposer.detect_seasonality_and_trend(timestamps_ms, values, 1.0, 60)

        # Should not detect seasonality
        assert result.seasonality == Seasonality.NONE
        # Should detect negative trend
        assert result.trend == Trend.NEGATIVE

    def test_non_seasonal_flat_line(self, decomposer):
        """Non-seasonal flat line should have no trend."""
        timestamps_ms = []
        values = []
        base_time = int(datetime.utcnow().timestamp() * 1000)

        # Constant value
        for i in range(100):
            timestamp = base_time + i * 60 * 1000
            value = 1000.0  # Flat line
            timestamps_ms.append(timestamp)
            values.append(value)

        result = decomposer.detect_seasonality_and_trend(timestamps_ms, values, 1.0, 60)

        # Should not detect seasonality
        assert result.seasonality == Seasonality.NONE
        # Should have no trend
        assert result.trend == Trend.NONE
