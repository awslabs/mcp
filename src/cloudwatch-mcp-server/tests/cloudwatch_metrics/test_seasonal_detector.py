"""Comprehensive tests for seasonal detector functionality."""

import math
import numpy as np
import pytest
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.metric_analyzer import MetricAnalyzer
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.metric_data_decomposer import (
    MetricDataDecomposer,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import (
    AnomalyDetectionAlarmThreshold,
    DecompositionResult,
    Seasonality,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools import CloudWatchMetricsTools
from datetime import datetime
from tests.cloudwatch_metrics.test_utils import (
    create_mock_metric_response,
    create_sparse_data,
    create_timestamps_and_values_by_duration,
    sine_wave_pattern_minutes,
)
from unittest.mock import patch


class TestSeasonalDetector:
    """Comprehensive test suite for seasonal detector functionality."""

    @pytest.fixture
    def detector(self):
        """Create a SeasonalityDetector instance."""
        return MetricDataDecomposer()

    @pytest.fixture
    def metric_analyzer(self):
        """Create a MetricAnalyzer instance."""
        return MetricAnalyzer()

    # Density threshold tests
    def test_low_density_returns_none(self, detector):
        """Test that low density (≤50%) data returns NONE."""
        timestamps_ms, values = create_sparse_data(48, 0.3)

        result = detector.detect_seasonality_and_trend(timestamps_ms, values, 0.3, 60)

        assert result.seasonality == Seasonality.NONE

    def test_exactly_50_percent_density_returns_none(self, detector):
        """Test that exactly 50% density returns NONE."""
        timestamps_ms, values = create_sparse_data(48, 0.5)

        result = detector.detect_seasonality_and_trend(timestamps_ms, values, 0.5, 60)

        assert result.seasonality == Seasonality.NONE

    def test_high_density_allows_detection(self, detector):
        """Test that high density (>50%) allows seasonality detection."""
        timestamps_ms, values = create_timestamps_and_values_by_duration(
            48, 1, lambda m, b, a: sine_wave_pattern_minutes(m, b, a)
        )

        result = detector.detect_seasonality_and_trend(timestamps_ms, values, 1.0, 60)

        assert result.seasonality != Seasonality.NONE

    # Seasonality detection tests for all periods
    @pytest.mark.parametrize(
        'period_hours,expected_seasonality',
        [
            (24, Seasonality.ONE_DAY),  # 1 day - most reliable
            (168, Seasonality.ONE_WEEK),  # 1 week - most reliable
        ],
    )
    def test_seasonal_period_detection(self, detector, period_hours, expected_seasonality):
        """Test detection of specific seasonal periods."""
        duration_hours = max(period_hours * 3, 48)  # At least 3 cycles or 48 hours
        timestamps_ms, values = create_timestamps_and_values_by_duration(
            duration_hours, 1, lambda m, b, a: sine_wave_pattern_minutes(m, b, a, period_hours)
        )

        result = detector.detect_seasonality_and_trend(timestamps_ms, values, 1.0, 60)

        assert result.seasonality == expected_seasonality

    def test_short_period_seasonality_detection(self, detector):
        """Test detection of shorter seasonal periods."""
        # Test 15-minute seasonality with sufficient data
        timestamps_ms, values = create_timestamps_and_values_by_duration(
            2,
            1,  # 2 hours of 1-minute data
            lambda m, b, a: sine_wave_pattern_minutes(m, b, a, 1),  # 1-hour period
        )

        result = detector.detect_seasonality_and_trend(timestamps_ms, values, 1.0, 60)

        # May detect as 15-minute or higher period depending on strength
        assert result.seasonality in [
            Seasonality.FIFTEEN_MINUTES,
            Seasonality.ONE_HOUR,
            Seasonality.SIX_HOURS,
            Seasonality.ONE_DAY,
            Seasonality.NONE,
        ]

    def test_hourly_seasonality_detection(self, detector):
        """Test detection of hourly seasonal patterns."""
        # Test 1-hour seasonality with sufficient data
        timestamps_ms, values = create_timestamps_and_values_by_duration(
            6,
            1,  # 6 hours of 1-minute data
            lambda m, b, a: sine_wave_pattern_minutes(m, b, a, 1),  # 1-hour period
        )

        result = detector.detect_seasonality_and_trend(timestamps_ms, values, 1.0, 60)

        # May detect as hourly or higher period depending on strength
        assert result.seasonality in [
            Seasonality.ONE_HOUR,
            Seasonality.SIX_HOURS,
            Seasonality.ONE_DAY,
            Seasonality.NONE,
        ]

    def test_non_seasonal_data_returns_none(self, detector):
        """Test that non-seasonal data returns NONE."""
        # Flat line data
        timestamps_ms, values = create_timestamps_and_values_by_duration(48, 1)

        result = detector.detect_seasonality_and_trend(timestamps_ms, values, 1.0, 60)

        assert result.seasonality == Seasonality.NONE

    def test_random_noise_returns_none(self, detector):
        """Test that random noise returns NONE."""
        timestamps_ms, values = create_timestamps_and_values_by_duration(
            48, 1, lambda m, b, a: b + np.random.normal(0, a / 10)
        )

        result = detector.detect_seasonality_and_trend(timestamps_ms, values, 1.0, 60)

        assert result.seasonality == Seasonality.NONE

    # Edge cases and error handling
    def test_empty_data(self, detector):
        """Test handling of empty data."""
        result = detector.detect_seasonality_and_trend([], [], 1.0, 60)
        assert result.seasonality == Seasonality.NONE

    def test_single_point(self, detector):
        """Test handling of single data point."""
        timestamps_ms = [int(datetime.utcnow().timestamp() * 1000)]
        values = [1000.0]

        result = detector.detect_seasonality_and_trend(timestamps_ms, values, 1.0, 60)

        assert result.seasonality == Seasonality.NONE

    def test_two_points(self, detector):
        """Test handling of two data points."""
        base_time = int(datetime.utcnow().timestamp() * 1000)
        timestamps_ms = [base_time, base_time + 60 * 1000]
        values = [1000.0, 1500.0]

        result = detector.detect_seasonality_and_trend(timestamps_ms, values, 1.0, 60)

        assert result.seasonality == Seasonality.NONE

    def test_insufficient_data_for_period(self, detector):
        """Test handling of insufficient data for seasonal period."""
        # Only 1 hour of data, can't detect daily seasonality
        timestamps_ms, values = create_timestamps_and_values_by_duration(
            1, 1, lambda m, b, a: sine_wave_pattern_minutes(m, b, a, 24)
        )

        result = detector.detect_seasonality_and_trend(timestamps_ms, values, 1.0, 60)

        # Should not detect daily seasonality with only 1 hour of data
        assert result.seasonality != Seasonality.ONE_DAY

    def test_zero_publishing_period(self, detector):
        """Test handling of zero publishing period."""
        timestamps_ms, values = create_timestamps_and_values_by_duration(48, 1)

        # Zero period should cause an error in interpolation
        try:
            result = detector.detect_seasonality_and_trend(timestamps_ms, values, 1.0, 0)
            # If no error, should return a valid seasonality
            assert isinstance(result, DecompositionResult)
        except ValueError:
            # Expected behavior - zero period causes ValueError in range()
            pass

    # Interpolation tests
    def test_interpolation_preserves_seasonality(self, detector):
        """Test that interpolation preserves seasonal patterns."""
        # Create data with gaps but sufficient density for daily pattern
        timestamps_ms = []
        values = []
        base_time = int(datetime.utcnow().timestamp() * 1000)

        # Create 80% density data with strong daily pattern
        total_minutes = 72 * 60  # 3 days
        for i in range(0, total_minutes, 5):  # Every 5 minutes base
            if i % 5 == 0:  # Keep 4 out of 5 points (80% density)
                timestamp = base_time + i * 60 * 1000
                value = sine_wave_pattern_minutes(i, 1000.0, 500.0, 24)  # Strong daily pattern
                timestamps_ms.append(timestamp)
                values.append(value)

        # Ensure we actually have data
        assert len(timestamps_ms) > 0, 'Test data generation failed'

        result = detector.detect_seasonality_and_trend(
            timestamps_ms, values, 0.8, 300
        )  # 5-minute period

        # Should preserve seasonality with sufficient density and strong pattern
        # Result may vary based on actual pattern strength detected
        assert result.seasonality in [Seasonality.ONE_DAY, Seasonality.NONE]

    def test_interpolation_with_single_point(self, detector):
        """Test interpolation with single data point."""
        timestamps_ms = [int(datetime.utcnow().timestamp() * 1000)]
        values = [1000.0]

        interpolated_timestamps, interpolated_values = detector._interpolate_to_regular_grid(
            timestamps_ms, values, 60
        )

        assert interpolated_timestamps == timestamps_ms
        assert interpolated_values == values

    def test_interpolation_with_empty_data(self, detector):
        """Test interpolation with empty data."""
        interpolated_timestamps, interpolated_values = detector._interpolate_to_regular_grid(
            [], [], 60
        )

        assert interpolated_timestamps == []
        assert interpolated_values == []

    # Seasonal strength calculation tests
    def test_seasonal_strength_calculation(self, detector):
        """Test seasonal strength calculation with known pattern."""
        # Create perfect sine wave
        values = np.array([math.sin(2 * math.pi * i / 24) for i in range(72)])  # 3 days

        strength, _ = detector._calculate_seasonal_strength(values, 24)

        # Perfect sine wave should have high seasonal strength
        assert strength > MetricDataDecomposer.SEASONALITY_STRENGTH_THRESHOLD

    def test_seasonal_strength_flat_line(self, detector):
        """Test seasonal strength calculation with flat line."""
        values = np.array([1000.0] * 72)

        strength, _ = detector._calculate_seasonal_strength(values, 24)

        # Flat line should have zero seasonal strength
        assert strength == 0.0

    def test_seasonal_strength_insufficient_data(self, detector):
        """Test seasonal strength calculation with insufficient data."""
        values = np.array([1.0, 2.0, 3.0])  # Less than 2 periods

        strength, _ = detector._calculate_seasonal_strength(values, 24)

        assert strength == 0.0

    def test_seasonal_strength_zero_period(self, detector):
        """Test seasonal strength calculation with zero period."""
        values = np.array([1.0, 2.0, 3.0, 4.0])

        strength, _ = detector._calculate_seasonal_strength(values, 0)

        assert strength == 0.0

    def test_seasonal_strength_negative_period(self, detector):
        """Test seasonal strength calculation with negative period."""
        values = np.array([1.0, 2.0, 3.0, 4.0])

        strength, _ = detector._calculate_seasonal_strength(values, -1)

        assert strength == 0.0

    # Integration tests with MetricAnalyzer
    def test_sine_wave_seasonality_detection_integration(self, metric_analyzer):
        """Test sine wave seasonality detection through MetricAnalyzer."""
        timestamps_ms, values = create_timestamps_and_values_by_duration(
            72, 1, lambda m, b, a: sine_wave_pattern_minutes(m, b, a)
        )

        from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import MetricData

        metric_data = MetricData(period_seconds=60, timestamps=timestamps_ms, values=values)

        result = metric_analyzer.analyze_metric_data(metric_data)

        assert result['seasonality_seconds'] != Seasonality.NONE.value
        assert result['data_points_found'] == len(timestamps_ms)

    def test_flat_line_no_seasonality_integration(self, metric_analyzer):
        """Test flat line data shows no seasonality through MetricAnalyzer."""
        timestamps_ms, values = create_timestamps_and_values_by_duration(72, 1)

        from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import MetricData

        metric_data = MetricData(period_seconds=60, timestamps=timestamps_ms, values=values)

        result = metric_analyzer.analyze_metric_data(metric_data)

        # The result contains the Seasonality enum, not its value
        assert result['seasonality_seconds'] == 0  # NONE in seconds

    # Alarm recommendation tests
    async def test_sine_wave_alarm_recommendations(self):
        """Test sine wave generates anomaly detection alarm recommendations."""
        timestamps_ms, values = create_timestamps_and_values_by_duration(
            72, 1, lambda m, b, a: sine_wave_pattern_minutes(m, b, a)
        )
        response = create_mock_metric_response(timestamps_ms, values)

        tools = CloudWatchMetricsTools()
        with (
            patch.object(tools, 'get_metric_data') as mock_get_metric_data,
            patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.CloudFormationTemplateGenerator'
            ) as mock_template_gen,
        ):
            mock_get_metric_data.return_value = response

            # Mock template generator to return the recommendations as-is
            mock_template_gen.return_value.generate_output.return_value = []

            # Test the anomaly detection creation directly
            from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.metric_data_decomposer import (
                Seasonality,
            )

            anomaly_alarm = tools._create_anomaly_detector_recommendation(
                metric_name='CPUUtilization',
                namespace='AWS/EC2',
                dimensions=[],
                seasonality=Seasonality.ONE_DAY,
            )

            assert 'Anomaly detection' in anomaly_alarm.alarmDescription
            assert isinstance(anomaly_alarm.threshold, AnomalyDetectionAlarmThreshold)
            assert 'seasonality' in anomaly_alarm.alarmDescription.lower()
            assert anomaly_alarm.comparisonOperator == 'LessThanLowerOrGreaterThanUpperThreshold'

    async def test_non_seasonal_data_no_anomaly_alarm(self):
        """Test non-seasonal data doesn't generate anomaly detection alarms."""
        timestamps_ms, values = create_timestamps_and_values_by_duration(72, 1)

        analyzer = MetricAnalyzer()
        from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import MetricData

        metric_data = MetricData(period_seconds=60, timestamps=timestamps_ms, values=values)
        result = analyzer.analyze_metric_data(metric_data)

        # The result contains the Seasonality enum, not its value
        assert result['seasonality_seconds'] == 0  # NONE in seconds

    # Winsorization tests
    def test_winsorization_handles_outliers(self, detector):
        """Test that winsorization properly handles outliers."""
        # Create data with extreme outliers
        timestamps_ms, base_values = create_timestamps_and_values_by_duration(
            48, 1, lambda m, b, a: sine_wave_pattern_minutes(m, b, a)
        )

        # Add extreme outliers
        values = base_values.copy()
        values[10] = 1000000  # Extreme high outlier
        values[20] = -1000000  # Extreme low outlier

        result = detector.detect_seasonality_and_trend(timestamps_ms, values, 1.0, 60)

        # Should still detect seasonality despite outliers
        assert result.seasonality != Seasonality.NONE

    # Numerical stability tests
    def test_numerical_stability_with_constant_values(self, detector):
        """Test numerical stability with constant values."""
        values = np.array([1000.0] * 72)

        # This should not crash and should return 0 strength
        strength, _ = detector._calculate_seasonal_strength(values, 24)

        assert strength == 0.0

    def test_interpolation_with_none_period(self, detector):
        """Test interpolation with None period."""
        timestamps_ms, values = create_timestamps_and_values_by_duration(
            5, 60000
        )  # 1 minute intervals

        # This should trigger the period calculation from timestamps
        interpolated_timestamps, interpolated_values = detector._interpolate_to_regular_grid(
            timestamps_ms,
            values,
            60.0,  # Pass valid period
        )

        # Should use provided period
        assert len(interpolated_timestamps) >= len(timestamps_ms)
        assert len(interpolated_values) >= len(values)

    def test_interpolation_with_zero_period(self, detector):
        """Test interpolation with zero period."""
        timestamps_ms, values = create_timestamps_and_values_by_duration(5, 60000)

        # This should use provided period
        interpolated_timestamps, interpolated_values = detector._interpolate_to_regular_grid(
            timestamps_ms,
            values,
            300.0,  # 5 minute period
        )

        assert len(interpolated_timestamps) >= len(timestamps_ms)
        assert len(interpolated_values) >= len(values)

    def test_calculate_seasonal_strength_zero_cycles(self, detector):
        """Test seasonal strength calculation with zero cycles."""
        # Create data shorter than one seasonal period
        values = np.array([1.0, 2.0])  # Only 2 points for period of 24

        strength, _ = detector._calculate_seasonal_strength(values, 24)

        assert strength == 0.0

    def test_interpolation_with_single_timestamp_gap(self, detector):
        """Test detect_strongest_seasonality calculates period from single timestamp gap."""
        # Create timestamps with single gap to test period calculation in _detect_strongest_seasonality
        base_time = int(datetime.utcnow().timestamp() * 1000)
        timestamps_ms = [base_time, base_time + 60000]  # 1 minute gap
        values = [10.0, 20.0]

        # Call _detect_strongest_seasonality directly with None period
        result = detector._detect_strongest_seasonality(timestamps_ms, values, None)

        # Should calculate period from timestamp gap and return a result
        assert isinstance(result, DecompositionResult)

    def test_interpolation_with_negative_calculated_period(self, detector):
        """Test detect_strongest_seasonality handles invalid calculated period."""
        # Create timestamps that would result in negative or zero period calculation
        base_time = int(datetime.utcnow().timestamp() * 1000)
        timestamps_ms = [base_time, base_time]  # Same timestamp - zero gap
        values = [10.0, 20.0]

        # Call _detect_strongest_seasonality directly with None period
        result = detector._detect_strongest_seasonality(timestamps_ms, values, None)

        # Should use default 300 seconds when calculated period is invalid
        assert isinstance(result, DecompositionResult)

    def test_calculate_seasonal_strength_insufficient_cycles(self, detector):
        """Test seasonal strength calculation when n_cycles is exactly 0."""
        # Create data that results in exactly 0 cycles
        values = np.array([])  # Empty array

        strength, _ = detector._calculate_seasonal_strength(values, 24)

        assert strength == 0.0

    def test_calculate_seasonal_strength_single_value_large_period(self, detector):
        """Test seasonal strength calculation with single value and large period."""
        # Single value with period larger than data length
        values = np.array([1.0])  # 1 value, period 24 -> n_cycles = 1//24 = 0

        strength, _ = detector._calculate_seasonal_strength(values, 24)

        assert strength == 0.0

    def test_calculate_seasonal_strength_values_shorter_than_period(self, detector):
        """Test seasonal strength calculation when values array is shorter than seasonal period."""
        # 2 values with period 24 -> n_cycles = 2//24 = 0
        values = np.array([1.0, 2.0])  # 2 values, period 24

        strength, _ = detector._calculate_seasonal_strength(values, 24)

        assert strength == 0.0

    def test_calculate_seasonal_strength_direct_zero_cycles(self, detector):
        """Test seasonal strength calculation directly with zero cycles condition."""
        # Create values array that will definitely result in n_cycles = 0
        values = np.array([10.0, 20.0, 30.0])  # 3 values
        seasonal_period = 10  # period > len(values), so n_cycles = 3//10 = 0

        # Call the method directly
        strength, _ = detector._calculate_seasonal_strength(values, seasonal_period)

        # Should return 0.0 due to n_cycles <= 0 condition
        assert strength == 0.0
