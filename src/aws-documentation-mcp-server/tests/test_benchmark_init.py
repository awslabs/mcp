# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Regression test: server init must complete under a time threshold."""

import pytest
import statistics
import subprocess
import sys
from tests.conftest import INIT_TIME_THRESHOLD_MS, check_threshold


def _measure_init_time(module: str = 'server_aws') -> float:
    """Measure server init time in a subprocess, returns milliseconds."""
    code = (
        'import time; s=time.perf_counter(); '
        f'from awslabs.aws_documentation_mcp_server import {module}; '
        'print((time.perf_counter()-s)*1000)'
    )
    result = subprocess.run(
        [sys.executable, '-c', code],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f'Subprocess failed: {result.stderr}'
    return float(result.stdout.strip())


@pytest.mark.slow
@pytest.mark.parametrize('module', ['server_aws', 'server_aws_cn'])
def test_server_init_time(module):
    """Server init must be under threshold for both server modules.

    Threshold can be overridden via INIT_TIME_THRESHOLD_MS env var.
    Skip in fast test runs with: pytest -m "not slow"
    """
    times = [_measure_init_time(module) for _ in range(3)]
    median_ms = statistics.median(times)
    assert check_threshold(median_ms), (
        f'{module} init time {median_ms:.0f}ms exceeds {INIT_TIME_THRESHOLD_MS}ms threshold'
    )
