"""Comprehensive tests for MetricAnalyzer class."""

import math
import numpy as np
import pytest
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.metric_analyzer import MetricAnalyzer
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import MetricData, Seasonality, Trend
from datetime import datetime
from tests.cloudwatch_metrics.test_utils import (
    create_timestamps_and_values,
    linear_trend_pattern,
    sine_wave_pattern,
)
from typing import List, Tuple
from unittest.mock import MagicMock


class TestMetricAnalyzer:
    """Comprehensive test suite for MetricAnalyzer functionality."""

    # Test constants
    BASE_VALUE = 1000.0
    AMPLITUDE = 500.0
    DEFAULT_INTERVAL_MS = 1000  # 1 second
    RANDOM_SEED = 42

    @pytest.fixture
    def analyzer(self):
        """Create a MetricAnalyzer instance."""
        return MetricAnalyzer()

    # Test utilities
    def create_timestamps_and_values(
        self,
        count: int,
        interval_ms: int = DEFAULT_INTERVAL_MS,
        pattern_func=None,
        base_value: float = BASE_VALUE,
        amplitude: float = AMPLITUDE,
    ) -> Tuple[List[int], List[float]]:
        """Create test data with specified pattern."""
        base_time = int(datetime.utcnow().timestamp() * 1000)
        timestamps = [base_time + i * interval_ms for i in range(count)]

        if pattern_func:
            values = [pattern_func(i, base_value, amplitude) for i in range(count)]
        else:
            values = [base_value] * count

        return timestamps, values

    def _analyze_with_metric_data(self, analyzer, timestamps, values, period_seconds=60):
        """Helper method to analyze data using MetricData object."""
        metric_data = MetricData(
            period_seconds=period_seconds, timestamps=timestamps, values=values
        )
        return analyzer.analyze_metric_data(metric_data)

    def sine_wave_pattern(
        self, index: int, base_value: float, amplitude: float, period: int = 24
    ) -> float:
        """Generate sine wave pattern."""
        return base_value + amplitude * math.sin(2 * math.pi * index / period)

    def linear_trend_pattern(self, index: int, base_value: float, slope: float) -> float:
        """Generate linear trend pattern."""
        return base_value + slope * index

    def create_mock_metric_response(self, timestamps: List[int], values: List[float]) -> MagicMock:
        """Create mock CloudWatch metric response."""
        datapoints = []
        for timestamp_ms, value in zip(timestamps, values):
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
            datapoint = MagicMock()
            datapoint.timestamp = timestamp
            datapoint.value = value
            datapoints.append(datapoint)

        metric_result = MagicMock()
        metric_result.datapoints = datapoints

        response = MagicMock()
        response.metricDataResults = [metric_result]

        return response

    # Edge cases and error handling
    def test_analyze_empty_data(self, analyzer):
        """Test comprehensive analysis with empty data."""
        result = self._analyze_with_metric_data(analyzer, [], [])

        assert result == {'message': 'No metric data available for analysis'}

    def test_analyze_mismatched_data(self, analyzer):
        """Test comprehensive analysis with mismatched timestamp and value lengths."""
        # MetricData validation will catch this, so we expect an exception
        with pytest.raises(ValueError):
            self._analyze_with_metric_data(analyzer, [1000, 2000], [10.0])

    def test_analyze_single_point(self, analyzer):
        """Test comprehensive analysis with single data point."""
        timestamps, values = create_timestamps_and_values(1)

        result = self._analyze_with_metric_data(analyzer, timestamps, values)

        assert result == {'message': 'Insufficient valid data points for analysis'}

    def test_analyze_with_nan_values(self, analyzer):
        """Test comprehensive analysis filters out NaN values."""
        timestamps, _ = create_timestamps_and_values(4)
        values = [10.0, float('nan'), 12.0, float('inf')]

        result = self._analyze_with_metric_data(analyzer, timestamps, values)

        # With 2 valid values (10.0 and 12.0), analysis should succeed
        assert result['message'] == 'Metric analysis completed successfully'
        assert result['data_points_found'] == 4

    def test_analyze_with_all_invalid_values(self, analyzer):
        """Test comprehensive analysis with all NaN/inf values."""
        timestamps, _ = create_timestamps_and_values(4)
        values = [float('nan'), float('inf'), float('nan'), float('inf')]

        result = self._analyze_with_metric_data(analyzer, timestamps, values)

        assert result == {'message': 'Insufficient valid data points for analysis'}

    # Trend computation tests

    def test_compute_publishing_period_insufficient_data(self, analyzer):
        """Test publishing period computation with insufficient data."""
        timestamps, _ = create_timestamps_and_values(1)

        period = analyzer._compute_publishing_period(timestamps)
        density_ratio = analyzer._compute_density_ratio(timestamps, period)

        assert period is None
        assert density_ratio is None

    def test_compute_publishing_period_regular_intervals(self, analyzer):
        """Test publishing period computation with regular intervals."""
        timestamps, _ = create_timestamps_and_values(5, self.DEFAULT_INTERVAL_MS)

        period = analyzer._compute_publishing_period(timestamps)
        density_ratio = analyzer._compute_density_ratio(timestamps, period)

        assert period == 1.0
        assert density_ratio == 1.0

    def test_compute_publishing_period_irregular_intervals(self, analyzer):
        """Test publishing period computation with irregular intervals."""
        base_time = int(datetime.utcnow().timestamp() * 1000)
        timestamps = [
            base_time,
            base_time + 1000,
            base_time + 3000,
            base_time + 4000,
            base_time + 5000,
        ]

        period = analyzer._compute_publishing_period(timestamps)
        density_ratio = analyzer._compute_density_ratio(timestamps, period)

        assert period == 1.0  # Most common gap
        assert density_ratio is not None

    def test_compute_publishing_period_truly_irregular(self, analyzer):
        """Test publishing period computation with truly irregular intervals."""
        base_time = int(datetime.utcnow().timestamp() * 1000)
        timestamps = [base_time, base_time + 2000, base_time + 6000, base_time + 11000]

        period = analyzer._compute_publishing_period(timestamps)
        density_ratio = analyzer._compute_density_ratio(timestamps, period)

        assert period == 2.0  # First gap becomes most common
        assert density_ratio is not None

    # Statistics computation tests
    def test_compute_statistics_empty_data(self, analyzer):
        """Test statistics computation with empty data."""
        result = analyzer._compute_statistics([])

        assert result['min'] is None
        assert result['max'] is None
        assert result['std_deviation'] is None
        assert result['coefficient_of_variation'] is None
        assert result['median'] is None

    def test_compute_statistics_valid_data(self, analyzer):
        """Test statistics computation with valid data."""
        values = [10.0, 12.0, 14.0, 16.0, 18.0]

        result = analyzer._compute_statistics(values)

        assert result['min'] == 10.0
        assert result['max'] == 18.0
        assert result['std_deviation'] > 0
        assert result['coefficient_of_variation'] > 0
        assert result['median'] == 14.0

    def test_compute_statistics_zero_mean(self, analyzer):
        """Test statistics computation with zero mean (CV edge case)."""
        values = [-5.0, 0.0, 5.0]

        result = analyzer._compute_statistics(values)

        assert result['coefficient_of_variation'] is None
        assert result['std_deviation'] > 0
        assert result['min'] == -5.0
        assert result['max'] == 5.0

    def test_compute_statistics_constant_values(self, analyzer):
        """Test statistics computation with constant values."""
        values = [self.BASE_VALUE] * 5

        result = analyzer._compute_statistics(values)

        assert result['min'] == self.BASE_VALUE
        assert result['max'] == self.BASE_VALUE
        assert result['std_deviation'] == 0.0
        assert result['coefficient_of_variation'] == 0.0
        assert result['median'] == self.BASE_VALUE

    # Integration tests
    def test_analyze_with_seasonal_pattern(self, analyzer):
        """Test comprehensive analysis with seasonal pattern."""
        np.random.seed(self.RANDOM_SEED)

        timestamps, _ = create_timestamps_and_values(24, self.DEFAULT_INTERVAL_MS)
        values = [
            sine_wave_pattern(i, self.BASE_VALUE, 100.0) + np.random.normal(0, 10.0)
            for i in range(24)
        ]

        result = self._analyze_with_metric_data(analyzer, timestamps, values)

        assert 'seasonality_seconds' in result
        assert 'trend' in result
        assert 'data_quality' in result
        assert 'statistics' in result
        assert 'density_ratio' in result['data_quality']
        assert 'publishing_period_seconds' in result['data_quality']
        assert isinstance(result['seasonality_seconds'], (int, float))

    def test_analyze_with_trend_pattern(self, analyzer):
        """Test comprehensive analysis with trend pattern."""
        timestamps, _ = create_timestamps_and_values(10, self.DEFAULT_INTERVAL_MS)
        values = [linear_trend_pattern(i, self.BASE_VALUE, 50.0) for i in range(10)]

        result = self._analyze_with_metric_data(analyzer, timestamps, values)

        assert result['trend'] == Trend.POSITIVE
        assert result['statistics']['min'] < result['statistics']['max']
        assert result['data_quality']['density_ratio'] == 1.0

    def test_analyze_flat_data(self, analyzer):
        """Test comprehensive analysis with flat data."""
        timestamps, values = create_timestamps_and_values(10, self.DEFAULT_INTERVAL_MS)

        result = self._analyze_with_metric_data(analyzer, timestamps, values)

        assert result['trend'] == Trend.NONE
        assert result['seasonality_seconds'] == 0  # NONE in seconds
        assert result['statistics']['std_deviation'] == 0.0
        assert result['statistics']['coefficient_of_variation'] == 0.0

    def test_analyze_insufficient_seasonal_data(self, analyzer):
        """Test seasonality detection with insufficient data."""
        timestamps, values = create_timestamps_and_values(5, self.DEFAULT_INTERVAL_MS)

        result = self._analyze_with_metric_data(analyzer, timestamps, values)

        assert result['seasonality_seconds'] == 0  # NONE in seconds
        assert result['data_quality']['total_points'] == 5

    # Integration with CloudWatch response
    def test_analyze_direct(self, analyzer):
        """Test analyze method directly with raw data."""
        timestamps = [1000, 2000, 3000, 4000]
        values = [10.0, 20.0, 30.0, 40.0]

        result = self._analyze_with_metric_data(analyzer, timestamps, values)

        assert result['data_points_found'] == 4
        assert 'seasonality_seconds' in result
        assert 'trend' in result

    def test_compute_seasonality_exception_handling(self, analyzer):
        """Test seasonality computation handles exceptions gracefully."""
        timestamps, values = create_timestamps_and_values(5)

        # Force an exception by passing invalid parameters
        result = analyzer._compute_seasonality_and_trend(timestamps, values, None, None)

        assert result.seasonality == Seasonality.NONE
        assert result.trend == Trend.NONE

    def test_compute_publishing_period_exception_handling(self, analyzer):
        """Test publishing period computation handles exceptions gracefully."""
        # Empty list will cause exception in gap calculation
        result = analyzer._compute_publishing_period([])

        assert result is None

    def test_compute_density_ratio_exception_handling(self, analyzer):
        """Test density ratio computation handles exceptions gracefully."""
        timestamps, _ = create_timestamps_and_values(5)

        # Pass None period to trigger exception
        result = analyzer._compute_density_ratio(timestamps, None)

        assert result is None

    def test_compute_statistics_exception_handling(self, analyzer):
        """Test statistics computation handles exceptions gracefully."""
        # Pass invalid data that will cause numpy to fail
        values = []

        result = analyzer._compute_statistics(values)

        # Should return dict with None values for all stats
        assert all(v is None for v in result.values())

    def test_compute_density_ratio_exception_handling_sum_error(self, analyzer):
        """Test density ratio computation with sum exception."""
        import pytest
        from unittest.mock import patch

        timestamps_ms = [1000, 2000, 3000]

        # Patch the sum function to raise an exception
        with patch('builtins.sum', side_effect=Exception('Sum error')):
            with pytest.raises(Exception, match='Sum error'):
                analyzer._compute_density_ratio(timestamps_ms, 1.0)

    def test_compute_publishing_period_exception_handling_counter_error(self, analyzer):
        """Test publishing period computation with Counter exception."""
        from unittest.mock import patch

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.metric_analyzer.Counter'
        ) as mock_counter:
            mock_counter.side_effect = Exception('Counter error')

            result = analyzer._compute_publishing_period([1000, 2000, 3000])
            assert result is None

    def test_compute_seasonality_exception_handling_detector_error(self, analyzer):
        """Test seasonality computation with detector exception."""
        import pytest
        from unittest.mock import patch

        # Mock the seasonal decomposer to raise an exception
        with patch.object(
            analyzer.decomposer,
            'detect_seasonality_and_trend',
            side_effect=Exception('Seasonality error'),
        ):
            with pytest.raises(Exception, match='Seasonality error'):
                analyzer._compute_seasonality_and_trend(
                    [1000, 2000, 3000], [1.0, 2.0, 3.0], 0.8, 60.0
                )

    def test_compute_statistics_exception_handling_numpy_error(self, analyzer):
        """Test statistics computation with numpy exception."""
        import pytest
        from unittest.mock import patch

        # Mock numpy to raise an exception
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.metric_analyzer.np.array'
        ) as mock_array:
            mock_array.side_effect = Exception('Numpy error')

            with pytest.raises(Exception, match='Numpy error'):
                analyzer._compute_statistics([1.0, 2.0, 3.0])

    def test_analyze_metric_data_exception_returns_empty_with_message(self, analyzer):
        """Test that exceptions during analysis return empty dict with message."""
        from unittest.mock import patch

        timestamps, values = create_timestamps_and_values(5)

        # Mock _compute_publishing_period to raise an exception
        with patch.object(
            analyzer, '_compute_publishing_period', side_effect=Exception('Test error')
        ):
            result = self._analyze_with_metric_data(analyzer, timestamps, values)

            assert result == {'message': 'Unable to analyze metric data'}
