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

import numpy as np
import pandas as pd
import statsmodels.api as sm
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.constants import (
    NUMERICAL_STABILITY_THRESHOLD,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import (
    DecompositionResult,
    Seasonality,
    Trend,
)
from loguru import logger
from statsmodels.regression.linear_model import OLS
from typing import List, Optional, Tuple


class MetricDataDecomposer:
    """Decomposes metric time series data into seasonal and trend components."""

    SEASONALITY_STRENGTH_THRESHOLD = 0.6  # See https://robjhyndman.com/hyndsight/tsoutliers/
    STATISTICAL_SIGNIFICANCE_THRESHOLD = 0.05

    def detect_seasonality_and_trend(
        self,
        timestamps_ms: List[int],
        values: List[float],
        density_ratio: float,
        publishing_period_seconds: int,
    ) -> DecompositionResult:
        """Analyze seasonality and extract trend component.

        Returns:
            DecompositionResult with seasonality and trend
        """
        # Return NONE for empty data or insufficient density
        if not timestamps_ms or not values or density_ratio <= 0.5:
            return DecompositionResult(seasonality=Seasonality.NONE, trend=Trend.NONE)

        # Interpolate if we have sufficient density
        timestamps_ms, values = self._interpolate_to_regular_grid(
            timestamps_ms, values, publishing_period_seconds
        )

        return self._detect_strongest_seasonality(timestamps_ms, values, publishing_period_seconds)

    def _interpolate_to_regular_grid(
        self, timestamps_ms: List[int], values: List[float], period_seconds: float
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
        self, timestamps_ms: List[int], values: List[float], period_seconds: Optional[float]
    ) -> DecompositionResult:
        """Detect seasonal patterns and compute trend in the data."""
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
        best_deseasonalized = None

        for seasonal_period_seconds in seasonal_periods_seconds:
            datapoints_per_period = seasonal_period_seconds / period_seconds
            min_required_points = datapoints_per_period * 2

            if len(values) < min_required_points or datapoints_per_period <= 0:
                continue

            strength, deseasonalized = self._calculate_seasonal_strength(
                winsorized_values, int(datapoints_per_period)
            )
            if strength > best_strength:
                best_strength = strength
                best_seasonality = Seasonality.from_seconds(seasonal_period_seconds)
                best_deseasonalized = deseasonalized

        # Compute trend from deseasonalized data if seasonality detected
        if best_strength > self.SEASONALITY_STRENGTH_THRESHOLD and best_deseasonalized is not None:
            trend = self._compute_trend(best_deseasonalized)
            return DecompositionResult(seasonality=best_seasonality, trend=trend)
        else:
            # No seasonality, compute trend on raw values
            trend = self._compute_trend(winsorized_values)
            return DecompositionResult(seasonality=Seasonality.NONE, trend=trend)

    def _calculate_seasonal_strength(
        self, values: np.ndarray, seasonal_period: int
    ) -> Tuple[float, Optional[np.ndarray]]:
        """Calculate seasonal strength and extract deseasonalized data for trend.

        Returns:
            Tuple of (strength, deseasonalized_values) where deseasonalized = original - seasonal_pattern
        """
        if len(values) < seasonal_period * 2 or seasonal_period <= 0:
            return (0.0, None)

        # Reshape data into seasonal cycles
        n_cycles = len(values) // seasonal_period
        if n_cycles <= 0:
            return (0.0, None)

        truncated_values = values[: n_cycles * seasonal_period]
        reshaped = truncated_values.reshape(n_cycles, seasonal_period)

        # Calculate seasonal pattern (mean across cycles)
        seasonal_pattern = np.mean(reshaped, axis=0)
        tiled_pattern = np.tile(seasonal_pattern, n_cycles)

        # Calculate trend (moving average) for seasonal strength calculation
        trend_series = (
            pd.Series(truncated_values)
            .rolling(window=seasonal_period, center=True, min_periods=1)
            .mean()
        )
        trend = np.asarray(trend_series)

        # Calculate components
        detrended = truncated_values - trend
        remainder = detrended - tiled_pattern

        # Seasonal strength = 1 - Var(remainder) / Var(detrended)
        var_remainder = np.var(remainder)
        var_detrended = np.var(detrended)

        if var_detrended <= NUMERICAL_STABILITY_THRESHOLD:
            return (0.0, None)

        strength = max(0.0, float(1 - var_remainder / var_detrended))

        # Return deseasonalized data (original - seasonal pattern) for trend calculation
        deseasonalized = truncated_values - tiled_pattern
        return (strength, deseasonalized)

    def _compute_trend(self, values: np.ndarray) -> Trend:
        """Compute trend using OLS on trend component values."""
        if len(values) <= 2:
            return Trend.NONE

        try:
            valid_data = [
                (i, v) for i, v in enumerate(values) if not np.isnan(v) and not np.isinf(v)
            ]
            if len(valid_data) <= 2:
                return Trend.NONE

            x_vals = np.array([x for x, _ in valid_data])
            y_vals = np.array([y for _, y in valid_data])

            # Check if all values are the same (flat line)
            if np.std(y_vals) < NUMERICAL_STABILITY_THRESHOLD:
                return Trend.NONE

            x_vals = (x_vals - x_vals.min()) / (
                x_vals.max() - x_vals.min() + NUMERICAL_STABILITY_THRESHOLD
            )

            X = sm.add_constant(x_vals)
            model = OLS(y_vals, X).fit()

            slope = model.params[1]
            p_value = model.pvalues[1]

            if p_value >= self.STATISTICAL_SIGNIFICANCE_THRESHOLD:
                return Trend.NONE

            return Trend.POSITIVE if slope > 0 else Trend.NEGATIVE
        except Exception as e:
            logger.warning(f'Error computing trend: {e}')
            return Trend.NONE
