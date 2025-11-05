"""Tests for trend detection in MetricDataDecomposer."""

import math
import numpy as np
import pytest
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.metric_data_decomposer import (
    MetricDataDecomposer,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import Seasonality, Trend
from datetime import datetime
from unittest.mock import patch


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

    def test_seasonal_strength_zero_cycles(self, decomposer):
        """Test seasonal strength calculation with zero cycles."""
        values = np.array([1.0, 2.0])  # Too few values for any seasonal period
        seasonal_period = 10

        strength, deseasonalized = decomposer._calculate_seasonal_strength(values, seasonal_period)

        assert strength == 0.0
        assert deseasonalized is None

    def test_compute_trend_with_nan_values(self, decomposer):
        """Test trend computation with NaN values."""
        values = np.array([1.0, 2.0, np.nan, 4.0, 5.0, np.nan, 7.0, 8.0, 9.0, 10.0])

        result = decomposer._compute_trend(values)

        # Should handle NaN values and still detect trend
        assert result == Trend.POSITIVE

    def test_compute_trend_with_inf_values(self, decomposer):
        """Test trend computation with infinite values."""
        values = np.array([1.0, 2.0, np.inf, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])

        result = decomposer._compute_trend(values)

        # Should handle inf values and still detect trend
        assert result == Trend.POSITIVE

    def test_compute_trend_insufficient_data(self, decomposer):
        """Test trend computation with insufficient valid data."""
        values = np.array([1.0, np.nan])

        result = decomposer._compute_trend(values)

        assert result == Trend.NONE

    def test_compute_trend_exception_handling(self, decomposer):
        """Test trend computation exception handling."""
        # Empty array should trigger exception handling
        values = np.array([])

        result = decomposer._compute_trend(values)

        assert result == Trend.NONE

    def test_compute_trend_only_two_valid_points(self, decomposer):
        """Test trend computation with exactly 2 valid data points."""
        values = np.array([np.nan, 1.0, np.nan, 2.0, np.nan])

        result = decomposer._compute_trend(values)

        # Should return NONE with only 2 valid points
        assert result == Trend.NONE

    def test_compute_trend_negative_slope(self, decomposer):
        """Test trend computation detects negative slope."""
        values = np.array([10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0])

        result = decomposer._compute_trend(values)

        assert result == Trend.NEGATIVE

    def test_compute_trend_with_statsmodels_exception(self, decomposer):
        """Test trend computation handles statsmodels exceptions."""
        # Create values that might cause numerical issues
        values = np.array([1e-100, 1e-100, 1e-100, 1e-100, 1e-100])

        result = decomposer._compute_trend(values)

        # Should handle exception and return NONE
        assert result == Trend.NONE

    def test_calculate_seasonal_strength_edge_case(self, decomposer):
        """Test seasonal strength with edge case that triggers n_cycles check."""
        # Create array where length is less than 2*seasonal_period but division gives 0
        values = np.array([1.0])
        seasonal_period = 10

        strength, deseasonalized = decomposer._calculate_seasonal_strength(values, seasonal_period)

        assert strength == 0.0
        assert deseasonalized is None

    def test_calculate_seasonal_strength_negative_period(self, decomposer):
        """Test seasonal strength with negative seasonal period."""
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        seasonal_period = -1

        strength, deseasonalized = decomposer._calculate_seasonal_strength(values, seasonal_period)

        assert strength == 0.0
        assert deseasonalized is None

    def test_calculate_seasonal_strength_exactly_one_cycle(self, decomposer):
        """Test seasonal strength with exactly one seasonal cycle."""
        # This should trigger the n_cycles <= 0 check since we need at least 2 cycles
        seasonal_period = 5
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])  # Exactly 1 cycle

        strength, deseasonalized = decomposer._calculate_seasonal_strength(values, seasonal_period)

        # Should return 0.0 because we need at least 2 cycles
        assert strength == 0.0
        assert deseasonalized is None

    def test_compute_trend_ols_exception(self, decomposer):
        """Test trend computation handles OLS exceptions."""
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        # Mock OLS to raise an exception
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.metric_data_decomposer.OLS'
        ) as mock_ols:
            mock_ols.side_effect = Exception('OLS error')

            result = decomposer._compute_trend(values)

            assert result == Trend.NONE
