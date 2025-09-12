"""Tests for MetricAnalyzer class."""

import numpy as np
import pytest
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.metric_analyzer import MetricAnalyzer
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.seasonal_detector import Seasonality
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import Trend


class TestMetricAnalyzer:
    """Tests for MetricAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = MetricAnalyzer()

    def test_analyze_empty_data(self):
        """Test comprehensive analysis with empty data."""
        result = self.analyzer.analyze([], [])
        
        assert result['trend'] == Trend.NONE
        assert result['seasonality_seconds'] == Seasonality.NONE
        assert result['data_quality']['total_points'] is None

    def test_analyze_mismatched_data(self):
        """Test comprehensive analysis with mismatched timestamp and value lengths."""
        result = self.analyzer.analyze([1000, 2000], [10.0])
        
        assert result['trend'] == Trend.NONE
        assert result['seasonality_seconds'] == Seasonality.NONE
        assert result['data_quality']['total_points'] is None

    def test_analyze_insufficient_clean_data(self):
        """Test comprehensive analysis with insufficient clean data after filtering."""
        timestamps = [1000]
        values = [10.0]
        
        result = self.analyzer.analyze(timestamps, values)
        
        assert result['trend'] == Trend.NONE
        assert result['seasonality_seconds'] == Seasonality.NONE
        assert result['data_quality']['total_points'] is None

    def test_analyze_with_nan_values(self):
        """Test comprehensive analysis filters out NaN values."""
        timestamps = [1000, 2000, 3000, 4000]
        values = [10.0, float('nan'), 12.0, float('inf')]
        
        result = self.analyzer.analyze(timestamps, values)
        
        # Should have filtered out NaN and inf values, leaving 2 clean points
        assert result['data_quality']['total_points'] == 4
        assert result['seasonality_seconds'] == Seasonality.NONE  # Not enough clean data

    def test_compute_trend_insufficient_data(self):
        """Test trend computation with insufficient data."""
        result = self.analyzer._compute_trend([10.0])
        
        assert result == Trend.NONE

    def test_compute_trend_valid_data(self):
        """Test trend computation with valid data."""
        values = [10.0, 12.0, 14.0, 16.0, 18.0]  # Clear upward trend
        
        result = self.analyzer._compute_trend(values)
        
        assert result == Trend.POSITIVE

    def test_compute_trend_negative_data(self):
        """Test trend computation with negative trend data."""
        values = [18.0, 16.0, 14.0, 12.0, 10.0]  # Clear downward trend
        
        result = self.analyzer._compute_trend(values)
        
        assert result == Trend.NEGATIVE

    def test_compute_publishing_period_insufficient_data(self):
        """Test publishing period computation with insufficient data."""
        period = self.analyzer._compute_publishing_period([1000])
        density_ratio = self.analyzer._compute_density_ratio([1000], period)
        
        assert period is None
        assert density_ratio is None

    def test_compute_publishing_period_regular_intervals(self):
        """Test publishing period computation with regular intervals."""
        timestamps = [1000, 2000, 3000, 4000, 5000]  # 1-second intervals
        
        period = self.analyzer._compute_publishing_period(timestamps)
        density_ratio = self.analyzer._compute_density_ratio(timestamps, period)
        
        assert period == 1.0
        assert density_ratio == 1.0  # Perfect density

    def test_compute_publishing_period_irregular_intervals(self):
        """Test publishing period computation with irregular intervals."""
        timestamps = [1000, 2000, 4000, 5000, 6000]  # Mixed intervals
        
        period = self.analyzer._compute_publishing_period(timestamps)
        density_ratio = self.analyzer._compute_density_ratio(timestamps, period)
        
        # Most common gap is 1000ms (appears 3 times out of 4) - 75% >= 50%
        assert period == 1.0
        assert density_ratio is not None

    def test_compute_publishing_period_truly_irregular_intervals(self):
        """Test publishing period computation with truly irregular intervals."""
        timestamps = [1000, 3000, 7000, 12000]  # All different gaps
        
        period = self.analyzer._compute_publishing_period(timestamps)
        density_ratio = self.analyzer._compute_density_ratio(timestamps, period)
        
        # Returns the most common gap even if irregular - gaps are 2000, 4000, 5000
        # Most common is 2000ms (appears first), so period should be 2.0 seconds
        assert period == 2.0
        assert density_ratio is not None

    def test_compute_statistics_empty_data(self):
        """Test statistics computation with empty data."""
        result = self.analyzer._compute_statistics([])
        
        # Test all essential statistics are None for empty data
        assert result['min'] is None
        assert result['max'] is None
        assert result['std_deviation'] is None
        assert result['coefficient_of_variation'] is None
        assert result['median'] is None

    def test_compute_statistics_valid_data(self):
        """Test statistics computation with valid data."""
        values = [10.0, 12.0, 14.0, 16.0, 18.0]
        
        result = self.analyzer._compute_statistics(values)
        
        # Test the 5 essential statistics
        assert result['min'] == 10.0
        assert result['max'] == 18.0
        assert result['std_deviation'] > 0
        assert result['coefficient_of_variation'] > 0
        assert result['median'] == 14.0

    def test_compute_statistics_zero_mean(self):
        """Test statistics computation with zero mean (edge case for CV)."""
        values = [-5.0, 0.0, 5.0]  # Mean is 0
        
        result = self.analyzer._compute_statistics(values)
        
        assert result['coefficient_of_variation'] is None  # CV undefined for zero mean
        assert result['std_deviation'] > 0
        assert result['min'] == -5.0
        assert result['max'] == 5.0

    def test_analyze_with_seasonality(self):
        """Test comprehensive analysis includes seasonality with realistic data."""
        # Set random seed for deterministic tests
        np.random.seed(42)
        
        # Data with potential seasonal pattern (more points for better detection)
        timestamps = list(range(1000, 25000, 1000))  # 24 points
        # Create data with some variation but not perfect seasonality
        values = [10 + 2 * np.sin(i * 0.5) + np.random.normal(0, 0.1) for i in range(24)]
        
        result = self.analyzer.analyze(timestamps, values)
        
        # Verify all sections are present
        assert 'seasonality_seconds' in result
        assert 'trend' in result
        assert 'data_quality' in result
        assert 'statistics' in result
        
        # Verify data quality includes density info
        assert 'density_ratio' in result['data_quality']
        assert 'publishing_period_seconds' in result['data_quality']
        assert 'data_quality' in result
        
        # Verify seasonality is enum value - with fixed seed, should be deterministic
        seasonality = result['seasonality_seconds']
        assert seasonality == Seasonality.NONE  # Expected result with this data pattern
        
    def test_analyze_insufficient_seasonal_data(self):
        """Test seasonality detection with insufficient data."""
        timestamps = [1000, 2000, 3000, 4000, 5000]
        values = [10.0, 12.0, 14.0, 16.0, 18.0]
        
        result = self.analyzer.analyze(timestamps, values)
        
        # Should still have seasonality section but with insufficient data indication
        assert 'seasonality_seconds' in result
        assert result['seasonality_seconds'] == Seasonality.NONE
