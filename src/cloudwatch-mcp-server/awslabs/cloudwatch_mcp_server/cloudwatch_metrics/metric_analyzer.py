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
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.constants import (
    NUMERICAL_STABILITY_THRESHOLD,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.metric_data_decomposer import (
    MetricDataDecomposer,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import (
    DecompositionResult,
    MetricData,
    Seasonality,
    Trend,
)
from collections import Counter
from loguru import logger
from typing import Any, Dict, Optional


class MetricAnalyzer:
    """Metric analysis including trend, density, seasonality, and statistical measures."""

    def __init__(self):
        """Initialize the metric analyzer."""
        self.decomposer = MetricDataDecomposer()

    def analyze_metric_data(self, metric_data: MetricData) -> Dict[str, Any]:
        """Analyze metric data and return comprehensive analysis results.

        Args:
            metric_data: MetricData object containing timestamps and values

        Returns:
            Dict containing analysis results including seasonality, trend, statistics, and message
        """
        if not metric_data.timestamps or not metric_data.values:
            return {'message': 'No metric data available for analysis'}

        clean_data = [
            (ts, val)
            for ts, val in zip(metric_data.timestamps, metric_data.values)
            if val is not None and not (np.isnan(val) or np.isinf(val))
        ]

        if len(clean_data) < 2:
            return {'message': 'Insufficient valid data points for analysis'}

        clean_timestamps, clean_values = zip(*clean_data)
        clean_timestamps = list(clean_timestamps)
        clean_values = list(clean_values)

        try:
            # Compute detailed analysis
            publishing_period_seconds = self._compute_publishing_period(clean_timestamps)
            density_ratio = self._compute_density_ratio(
                clean_timestamps, publishing_period_seconds or 0.0
            )
            decomposition = self._compute_seasonality_and_trend(
                clean_timestamps, clean_values, density_ratio, publishing_period_seconds
            )
            statistics = self._compute_statistics(clean_values)

            return {
                'data_points_found': len(metric_data.values),
                'seasonality_seconds': decomposition.seasonality.value,
                'trend': decomposition.trend,
                'statistics': statistics,
                'data_quality': {
                    'total_points': len(metric_data.values),
                    'density_ratio': density_ratio,
                    'publishing_period_seconds': publishing_period_seconds,
                },
                'message': 'Metric analysis completed successfully',
            }
        except Exception as e:
            logger.error(f'Error during metric analysis: {str(e)}')
            return {'message': 'Unable to analyze metric data'}

    def _compute_seasonality_and_trend(
        self,
        timestamps_ms: list[int],
        values: list[float],
        density_ratio: Optional[float],
        publishing_period_seconds: Optional[float],
    ):
        """Compute seasonality and trend using decomposition.

        Returns:
            DecompositionResult with seasonality and trend
        """
        if density_ratio is None or publishing_period_seconds is None:
            return DecompositionResult(seasonality=Seasonality.NONE, trend=Trend.NONE)

        try:
            return self.decomposer.detect_seasonality_and_trend(
                timestamps_ms, values, density_ratio, int(publishing_period_seconds)
            )
        except Exception as e:
            logger.error(f'Error computing seasonality and trend: {e}')
            raise

    def _compute_publishing_period(self, timestamps_ms: list[int]) -> Optional[float]:
        """Compute the publishing period in seconds from timestamp gaps."""
        try:
            gaps = [timestamps_ms[i + 1] - timestamps_ms[i] for i in range(len(timestamps_ms) - 1)]
            gap_counts = Counter(gaps)

            if not gap_counts:
                return None

            most_common_gap_ms, _ = gap_counts.most_common(1)[0]
            return self._get_closest_cloudwatch_period(most_common_gap_ms / 1000)
        except Exception as e:
            logger.warning(f'Error computing publishing period: {e}')
            return None

    def _get_closest_cloudwatch_period(self, period_seconds: float) -> float:
        """Validate and normalize period to CloudWatch valid values."""
        valid_periods = [1, 5, 10, 30] + [
            i * 60 for i in range(1, 3601)
        ]  # 1min to 1hour multiples

        # Find closest valid period
        closest_period = min(valid_periods, key=lambda x: abs(x - period_seconds))

        # Only return if within 10% tolerance
        if abs(closest_period - period_seconds) / closest_period <= 0.1:
            return closest_period

        return period_seconds  # Return original if no close match

    def _compute_density_ratio(
        self, timestamps_ms: list[int], publishing_period_seconds: float
    ) -> Optional[float]:
        """Calculate density ratio based on perfect timeline."""
        if (
            not publishing_period_seconds
            or publishing_period_seconds <= 0
            or len(timestamps_ms) < 2
        ):
            return None

        try:
            start_time = timestamps_ms[0]
            publishing_period_ms = publishing_period_seconds * 1000
            perfect_end_time = start_time + (publishing_period_ms * (len(timestamps_ms) - 1))
            actual_points_in_range = sum(1 for ts in timestamps_ms if ts <= perfect_end_time)
            return actual_points_in_range / len(timestamps_ms)
        except Exception as e:
            logger.error(f'Error calculating density ratio: {e}', exc_info=True)
            raise

    def _compute_statistics(self, values: list[float]) -> Dict[str, Any]:
        """Compute essential statistical measures for LLM consumption."""
        if not values:
            return {
                'min': None,
                'max': None,
                'std_deviation': None,
                'coefficient_of_variation': None,
                'median': None,
            }

        try:
            values_array = np.array(values)
            mean_val = np.mean(values_array)
            std_dev = np.std(values_array, ddof=0)
            cv = std_dev / abs(mean_val) if abs(mean_val) > NUMERICAL_STABILITY_THRESHOLD else None

            return {
                'min': float(np.min(values_array)),
                'max': float(np.max(values_array)),
                'std_deviation': float(std_dev),
                'coefficient_of_variation': float(cv) if cv is not None else None,
                'median': float(np.median(values_array)),
            }
        except Exception as e:
            logger.warning(f'Error computing statistics: {e}')
            raise
