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

from loguru import logger
import numpy as np
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.constants import NUMERICAL_STABILITY_THRESHOLD, STATISTICAL_SIGNIFICANCE_THRESHOLD
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.seasonal_detector import SeasonalDetector
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import Trend, Seasonality
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.constants import SEASONALITY_STRENGTH_THRESHOLD


class MetricAnalyzer:
    """Metric analysis including trend, density, seasonality, and statistical measures."""

    def __init__(self):
        self.seasonal_detector = SeasonalDetector()

    def analyze_metric_from_get_metric_data(self, metric_data_response, namespace, metric_name, dimensions, analysis_period_minutes):
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=analysis_period_minutes)
        
        analysis_result = {
            'recommendations_allowed': False,
            'metric_info': {
                'namespace': namespace,
                'metric_name': metric_name,
                'dimensions': [{'name': d.name, 'value': d.value} for d in dimensions],
                'analysis_period_minutes': analysis_period_minutes,
                'time_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                }
            },
            'data_points_found': 0,
            'seasonality_seconds': Seasonality.NONE,
            'trend': Trend.NONE,
            'data_quality': {},
            'statistics': {}
        }
        
        if metric_data_response.metricDataResults and metric_data_response.metricDataResults[0].datapoints:
            datapoints = metric_data_response.metricDataResults[0].datapoints
            timestamps_ms = [int(dp.timestamp.timestamp() * 1000) for dp in datapoints]
            values = [dp.value for dp in datapoints]
            
            sorted_data = sorted(zip(timestamps_ms, values))
            if sorted_data:
                timestamps_ms, values = zip(*sorted_data)
            else:
                timestamps_ms, values = [], []
            
            analysis_result['data_points_found'] = len(values)
            if timestamps_ms and values:
                analysis = self.analyze(list(timestamps_ms), list(values))
                
                analysis_result.update({
                    'seasonality_seconds': analysis['seasonality_seconds'],
                    'trend': analysis['trend'],
                    'statistics': analysis['statistics'],
                    'data_quality': analysis['data_quality']
                })
        
        return analysis_result

    def analyze(self, timestamps_ms: List[int], values: List[float]) -> Dict[str, Any]:
        if not timestamps_ms or not values or len(timestamps_ms) != len(values) or len(timestamps_ms) < 2:
            return self._empty_analysis_result()

        clean_data = [
            (ts, val)
            for ts, val in zip(timestamps_ms, values)
            if not (np.isnan(val) or np.isinf(val))
        ]

        clean_timestamps, clean_values = zip(*clean_data)
        clean_timestamps = list(clean_timestamps)
        clean_values = list(clean_values)

        # Compute detailed analysis
        publishing_period_seconds = self._compute_publishing_period(clean_timestamps)
        density_ratio = self._compute_density_ratio(clean_timestamps, publishing_period_seconds)
        seasonality = self._compute_seasonality(clean_timestamps, clean_values, density_ratio, publishing_period_seconds)
        trend = self._compute_trend(clean_values)
        statistics = self._compute_statistics(clean_values)
        
        return {
            'seasonality_seconds': seasonality,
            'trend': trend,
            'statistics': statistics,
            'data_quality': {
                'total_points': len(values),
                'density_ratio': density_ratio,
                'publishing_period_seconds': publishing_period_seconds,
            },
        }

    def _empty_analysis_result(self) -> Dict[str, Any]:
        """Return empty analysis result for invalid input."""
        return {
            'seasonality_seconds': Seasonality.NONE,
            'trend': Trend.NONE,
            'statistics': {'std_deviation': None, 'variance': None, 'coefficient_of_variation': None},
            'data_quality': {'total_points': None, 'density_ratio': None, 'publishing_period_seconds': None},
        }

    def _compute_trend(self, values: List[float]) -> Trend:
        if not values or len(values) <= 2:
            return Trend.NONE

        try:
            valid_data = [(i, v) for i, v in enumerate(values) if not np.isnan(v) and not np.isinf(v)]
            if len(valid_data) <= 2:
                return Trend.NONE

            x_vals = np.array([x for x, _ in valid_data])
            y_vals = np.array([y for _, y in valid_data])

            # Check if all values are the same (flat line)
            if np.std(y_vals) < NUMERICAL_STABILITY_THRESHOLD:
                return Trend.NONE

            x_vals = (x_vals - x_vals.min()) / (x_vals.max() - x_vals.min() + NUMERICAL_STABILITY_THRESHOLD)

            X = sm.add_constant(x_vals)
            model = OLS(y_vals, X).fit()

            slope = model.params[1]
            p_value = model.pvalues[1]

            if p_value >= STATISTICAL_SIGNIFICANCE_THRESHOLD:
                return Trend.NONE

            return Trend.POSITIVE if slope > 0 else Trend.NEGATIVE
        except Exception as e:
            logger.warning(f"Error computing trend: {e}")
            return Trend.NONE

    def _compute_seasonality(self, timestamps_ms: List[int], values: List[float], density_ratio: Optional[float], publishing_period_seconds: Optional[float]) -> Seasonality:
        """Compute seasonality analysis using the seasonal detector with density information."""
        if density_ratio is None or publishing_period_seconds is None:
            return Seasonality.NONE
            
        try:
            return self.seasonal_detector.detect_seasonality(timestamps_ms, values, density_ratio, int(publishing_period_seconds))
        except Exception as e:
            logger.error(f'Error computing seasonality: {e}')
            return Seasonality.NONE

    def _compute_publishing_period(self, timestamps_ms: List[int]) -> Optional[float]:
        """Compute the publishing period in seconds from timestamp gaps."""
        try:
            gaps = [timestamps_ms[i + 1] - timestamps_ms[i] for i in range(len(timestamps_ms) - 1)]
            gap_counts = Counter(gaps)

            if not gap_counts:
                return None

            most_common_gap_ms, _ = gap_counts.most_common(1)[0]
            return self._get_closest_cloudwatch_period(most_common_gap_ms / 1000)
        except Exception as e:
            logger.warning(f"Error computing publishing period: {e}")
            return None

    def _get_closest_cloudwatch_period(self, period_seconds: float) -> float:
        """Validate and normalize period to CloudWatch valid values."""
        valid_periods = [1, 5, 10, 30] + [i * 60 for i in range(1, 3601)]  # 1min to 1hour multiples
        
        # Find closest valid period
        closest_period = min(valid_periods, key=lambda x: abs(x - period_seconds))
        
        # Only return if within 10% tolerance
        if abs(closest_period - period_seconds) / closest_period <= 0.1:
            return closest_period
        
        return period_seconds  # Return original if no close match

    def _compute_density_ratio(self, timestamps_ms: List[int], publishing_period_seconds: float) -> Optional[float]:
        """Calculate density ratio based on perfect timeline."""
        if not publishing_period_seconds or publishing_period_seconds <= 0 or len(timestamps_ms) < 2:
            return None
            
        try:
            start_time = timestamps_ms[0]
            publishing_period_ms = publishing_period_seconds * 1000
            perfect_end_time = start_time + (publishing_period_ms * (len(timestamps_ms) - 1))
            actual_points_in_range = sum(1 for ts in timestamps_ms if ts <= perfect_end_time)
            return actual_points_in_range / len(timestamps_ms)
        except Exception as e:
            logger.error(f'Error calculating density ratio: {e}', exc_info=True)
            return None

    def _compute_statistics(self, values: List[float]) -> Dict[str, Any]:
        """Compute essential statistical measures for LLM consumption."""
        if not values:
            return {'min': None, 'max': None, 'std_deviation': None, 'coefficient_of_variation': None, 'median': None}

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
            logger.warning(f"Error computing statistics: {e}")
            return {'min': None, 'max': None, 'std_deviation': None, 'coefficient_of_variation': None, 'median': None}
