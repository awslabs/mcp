from typing import List, Optional, Tuple
import numpy as np
import pandas as pd
from collections import Counter

from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.constants import NUMERICAL_STABILITY_THRESHOLD, SEASONALITY_STRENGTH_THRESHOLD
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import Seasonality


class SeasonalDetector:
    """Detects seasonal patterns in CloudWatch metric data."""

    def detect_seasonality(
        self,
        timestamps_ms: List[int], 
        values: List[float], 
        density_ratio: float,
        publishing_period_seconds: int
    ) -> Seasonality:
        """Analyze seasonality using density ratio and publishing period."""
        # Return NONE if density is too low (≤50%)
        if density_ratio <= 0.5:
            return Seasonality.NONE
        
        # Interpolate if we have sufficient density
        timestamps_ms, values = self._interpolate_to_regular_grid(
            timestamps_ms, values, publishing_period_seconds
        )
        
        return self._detect_strongest_seasonality(timestamps_ms, values, publishing_period_seconds)

    def _interpolate_to_regular_grid(
        self,
        timestamps_ms: List[int], 
        values: List[float], 
        period_seconds: float
    ) -> Tuple[List[int], List[float]]:
        """Interpolate data to regular grid using numpy."""
        if len(timestamps_ms) < 2:
            return timestamps_ms, values
        
        period_ms = int(period_seconds * 1000)
        start_time = timestamps_ms[0]
        end_time = timestamps_ms[-1]
        
        # Create regular grid
        regular_timestamps = list(range(start_time, end_time + period_ms, period_ms))
        
        # Interpolate using numpy
        interpolated_values = np.interp(regular_timestamps, timestamps_ms, values).tolist()
        
        return regular_timestamps, interpolated_values

    def _detect_strongest_seasonality(
        self,
        timestamps_ms: List[int], 
        values: List[float], 
        period_seconds: Optional[float]
    ) -> Seasonality:
        """Detect seasonal patterns in the data."""
        timestamps_ms = sorted(timestamps_ms)
        
        # Calculate period for analysis
        if period_seconds is None and len(timestamps_ms) > 1:
            period_seconds = (timestamps_ms[1] - timestamps_ms[0]) / 1000
        
        if period_seconds is None or period_seconds <= 0:
            period_seconds = 300  # 5 minutes default
        
        # Winsorize values
        values_array = np.array(values)
        qtiles = np.quantile(values_array, [0.001, 0.999])
        lo, hi = qtiles
        winsorized_values = np.clip(values_array, lo, hi)
        
        # Test seasonal periods
        seasonal_periods_seconds = [
            Seasonality.FIFTEEN_MINUTES.value,
            Seasonality.ONE_HOUR.value,
            Seasonality.SIX_HOURS.value,
            Seasonality.ONE_DAY.value,
            Seasonality.ONE_WEEK.value,
        ]
        
        best_seasonality = Seasonality.NONE
        best_strength = 0.0
        
        for seasonal_period_seconds in seasonal_periods_seconds:
            datapoints_per_period = seasonal_period_seconds / period_seconds
            min_required_points = datapoints_per_period * 2
            
            if len(values) < min_required_points or datapoints_per_period <= 0:
                continue
            
            strength = self._calculate_seasonal_strength(winsorized_values, int(datapoints_per_period))
            if strength > best_strength:
                best_strength = strength
                best_seasonality = Seasonality.from_seconds(seasonal_period_seconds)
        
        # Return seasonality if strength is above threshold
        return best_seasonality if best_strength > SEASONALITY_STRENGTH_THRESHOLD else Seasonality.NONE

    def _calculate_seasonal_strength(self, values: np.ndarray, seasonal_period: int) -> float:
        """Calculate seasonal strength using improved algorithm."""
        if len(values) < seasonal_period * 2 or seasonal_period <= 0:
            return 0.0
        
        # Reshape data into seasonal cycles
        n_cycles = len(values) // seasonal_period
        if n_cycles <= 0:
            return 0.0
            
        truncated_values = values[:n_cycles * seasonal_period]
        reshaped = truncated_values.reshape(n_cycles, seasonal_period)
        
        # Calculate seasonal pattern (mean across cycles)
        seasonal_pattern = np.mean(reshaped, axis=0)
        tiled_pattern = np.tile(seasonal_pattern, n_cycles)
        
        # Calculate trend (moving average)
        trend = pd.Series(truncated_values).rolling(window=seasonal_period, center=True, min_periods=1).mean().values
        
        # Calculate components
        detrended = truncated_values - trend
        remainder = detrended - tiled_pattern
        
        # Seasonal strength = 1 - Var(remainder) / Var(detrended)
        var_remainder = np.var(remainder)
        var_detrended = np.var(detrended)
        
        if var_detrended <= NUMERICAL_STABILITY_THRESHOLD:
            return 0.0
        
        strength = max(0.0, 1 - var_remainder / var_detrended)
        return strength