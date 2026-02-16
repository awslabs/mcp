# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Regression test: server init must complete under a time threshold."""

import statistics
import subprocess
import sys

import pytest

from tests.conftest import INIT_TIME_THRESHOLD_MS, check_threshold


def _measure_init_time() -> float:
    """Measure server init time in a subprocess, returns milliseconds."""
    code = (
        "import time; s=time.perf_counter(); "
        "from awslabs.aws_documentation_mcp_server import server_aws; "
        "print((time.perf_counter()-s)*1000)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Subprocess failed: {result.stderr}"
    return float(result.stdout.strip())


def test_server_init_time():
    """Regression test: server init must be under threshold.

    Validates: Requirements 5.1, 5.2, 5.3
    """
    times = [_measure_init_time() for _ in range(3)]
    median_ms = statistics.median(times)
    assert check_threshold(median_ms), (
        f"Server init time {median_ms:.0f}ms exceeds {INIT_TIME_THRESHOLD_MS}ms threshold"
    )
