"""Test utilities for CloudWatch metrics tests."""

import math
from datetime import datetime
from typing import List, Tuple
from unittest.mock import MagicMock


def create_timestamps_and_values(
    count: int,
    interval_ms: int = 300000,  # 5 minutes
    pattern_func=None,
    base_value: float = 50.0,
    amplitude: float = 20.0,
) -> Tuple[List[int], List[float]]:
    """Create test data with specified pattern."""
    base_time = int(datetime.utcnow().timestamp() * 1000)
    timestamps = [base_time + i * interval_ms for i in range(count)]

    if pattern_func:
        values = [pattern_func(i, base_value, amplitude) for i in range(count)]
    else:
        values = [base_value] * count

    return timestamps, values


def create_timestamps_and_values_by_duration(
    duration_hours: int,
    interval_minutes: int = 1,
    pattern_func=None,
    base_value: float = 1000.0,
    amplitude: float = 500.0,
) -> Tuple[List[int], List[float]]:
    """Create test data by duration with specified pattern."""
    timestamps_ms = []
    values = []
    base_time = int(datetime.utcnow().timestamp() * 1000)

    total_minutes = duration_hours * 60
    for i in range(0, total_minutes, interval_minutes):
        timestamp = base_time + i * 60 * 1000
        if pattern_func:
            value = pattern_func(i, base_value, amplitude)
        else:
            value = base_value
        timestamps_ms.append(timestamp)
        values.append(value)

    return timestamps_ms, values


def sine_wave_pattern(index: int, base_value: float, amplitude: float, period: int = 24) -> float:
    """Generate sine wave pattern."""
    return base_value + amplitude * math.sin(2 * math.pi * index / period)


def sine_wave_pattern_minutes(
    minute: int, base_value: float, amplitude: float, period_hours: int = 24
) -> float:
    """Generate sine wave pattern based on minutes."""
    return base_value + amplitude * math.sin(2 * math.pi * minute / (period_hours * 60))


def linear_trend_pattern(index: int, base_value: float, slope: float) -> float:
    """Generate linear trend pattern."""
    return base_value + slope * index


def create_sparse_data(
    total_duration_hours: int, density_ratio: float
) -> Tuple[List[int], List[float]]:
    """Create sparse data with specified density ratio."""
    timestamps_ms = []
    values = []
    base_time = int(datetime.utcnow().timestamp() * 1000)

    total_minutes = total_duration_hours * 60
    expected_points = int(total_minutes * density_ratio)

    for i in range(expected_points):
        minute_offset = int(i * total_minutes / expected_points)
        timestamp = base_time + minute_offset * 60 * 1000
        value = sine_wave_pattern_minutes(minute_offset, 1000.0, 500.0)
        timestamps_ms.append(timestamp)
        values.append(value)

    return timestamps_ms, values


def create_mock_metric_response(timestamps: List[int], values: List[float]) -> MagicMock:
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
