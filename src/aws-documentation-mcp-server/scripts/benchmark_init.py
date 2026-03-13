#!/usr/bin/env python3
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

"""Benchmark script for measuring AWS Documentation MCP Server initialization time.

Measures total server module import time, individual dependency import times,
and phase-level times (FastMCP creation, UUID generation, version lookup)
using isolated subprocesses for accurate cold-start measurements.

Usage:
    python3 scripts/benchmark_init.py --iterations 5 --format both
"""

import argparse
import json
import statistics
import subprocess
import sys
import time


# Dependencies to benchmark individually
DEPENDENCIES = ['mcp', 'pydantic', 'httpx', 'markdownify', 'loguru', 'bs4']

# Subprocess timeout in seconds
SUBPROCESS_TIMEOUT = 30

# Threshold for flagging slow phases (milliseconds)
DEFAULT_THRESHOLD_MS = 200.0


# ---------------------------------------------------------------------------
# Importable helper functions (used by property tests in Task 8.2)
# ---------------------------------------------------------------------------


def sort_bottleneck_report(phases: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Sort phases by time descending (slowest first).

    Args:
        phases: List of (phase_name, time_ms) tuples.

    Returns:
        New list sorted by time_ms in descending order.
    """
    return sorted(phases, key=lambda x: x[1], reverse=True)


def compute_median(values: list[float]) -> float:
    """Compute the median of a list of values.

    Args:
        values: Non-empty list of numeric values.

    Returns:
        The median value, computed via statistics.median.

    Raises:
        statistics.StatisticsError: If values is empty.
    """
    return statistics.median(values)


def identify_threshold_violations(
    phases: list[tuple[str, float]], threshold_ms: float = DEFAULT_THRESHOLD_MS
) -> list[str]:
    """Identify phases that exceed the given threshold.

    Args:
        phases: List of (phase_name, time_ms) tuples.
        threshold_ms: Threshold in milliseconds (default 200.0).

    Returns:
        List of violation description strings for phases exceeding the threshold.
        Each string has the format: "<name>: <time>ms > <threshold>ms"
    """
    violations = []
    for name, time_ms in phases:
        if time_ms > threshold_ms:
            violations.append(f'{name}: {time_ms:.0f}ms > {threshold_ms:.0f}ms')
    return violations


# ---------------------------------------------------------------------------
# Subprocess measurement helpers
# ---------------------------------------------------------------------------


def _run_timed_subprocess(code: str) -> float:
    """Run a Python code snippet in a subprocess and return the printed time in ms.

    The code snippet must print a single float representing elapsed seconds.

    Returns:
        Elapsed time in milliseconds, or -1.0 on failure.
    """
    try:
        result = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
        )
        if result.returncode != 0:
            print(f'  [error] subprocess failed: {result.stderr.strip()}', file=sys.stderr)
            return -1.0
        return float(result.stdout.strip()) * 1000.0  # convert seconds to ms
    except subprocess.TimeoutExpired:
        print('  [error] subprocess timed out', file=sys.stderr)
        return -1.0
    except (ValueError, IndexError) as e:
        print(f'  [error] could not parse output: {e}', file=sys.stderr)
        return -1.0


def measure_server_init() -> float:
    """Measure full server module import time in an isolated subprocess.

    Returns:
        Import time in milliseconds.
    """
    code = (
        'import time; s=time.perf_counter(); '
        'from awslabs.aws_documentation_mcp_server import server_aws; '
        'print(time.perf_counter()-s)'
    )
    return _run_timed_subprocess(code)


def measure_single_import(module_name: str) -> float:
    """Measure import time for a single module in an isolated subprocess.

    Args:
        module_name: The module to import (e.g. 'mcp', 'pydantic').

    Returns:
        Import time in milliseconds.
    """
    code = (
        f'import time; s=time.perf_counter(); '
        f'import {module_name}; '
        f'print(time.perf_counter()-s)'
    )
    return _run_timed_subprocess(code)


def measure_phase(phase_name: str, code: str) -> float:
    """Measure a specific initialization phase in an isolated subprocess.

    Args:
        phase_name: Human-readable name for the phase.
        code: Python code snippet that prints elapsed seconds.

    Returns:
        Phase time in milliseconds.
    """
    return _run_timed_subprocess(code)


# ---------------------------------------------------------------------------
# Phase measurement code snippets
# ---------------------------------------------------------------------------

PHASE_SNIPPETS = {
    'FastMCP creation': (
        'import time; s=time.perf_counter(); '
        'from mcp.server.fastmcp import FastMCP; '
        'FastMCP("bench"); '
        'print(time.perf_counter()-s)'
    ),
    'UUID generation': (
        'import time; s=time.perf_counter(); '
        'import uuid; str(uuid.uuid4()); '
        'print(time.perf_counter()-s)'
    ),
    'version lookup': (
        "import time; s=time.perf_counter(); "
        "from importlib.metadata import version as _v; "
        "_v('awslabs.aws-documentation-mcp-server'); "
        "print(time.perf_counter()-s)"
    ),
}


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------


def run_benchmark(iterations: int) -> dict:
    """Run the full benchmark suite.

    Args:
        iterations: Number of times to measure server init (for median).

    Returns:
        Structured benchmark results dict.
    """
    # 1. Measure server init across iterations
    print(f'Measuring server init time ({iterations} iterations)...', file=sys.stderr)
    init_times: list[float] = []
    for i in range(iterations):
        t = measure_server_init()
        if t >= 0:
            init_times.append(t)
            print(f'  Iteration {i + 1}: {t:.1f}ms', file=sys.stderr)
        else:
            print(f'  Iteration {i + 1}: FAILED', file=sys.stderr)

    median_init = compute_median(init_times) if init_times else -1.0

    # 2. Measure individual dependency imports
    print('\nMeasuring dependency import times...', file=sys.stderr)
    dep_times: dict[str, float] = {}
    for dep in DEPENDENCIES:
        t = measure_single_import(dep)
        dep_times[dep] = t
        status = f'{t:.1f}ms' if t >= 0 else 'FAILED'
        print(f'  {dep}: {status}', file=sys.stderr)

    # 3. Measure phase-level times
    print('\nMeasuring phase-level times...', file=sys.stderr)
    phase_times: dict[str, float] = {}
    for phase_name, code in PHASE_SNIPPETS.items():
        t = measure_phase(phase_name, code)
        phase_times[phase_name] = t
        status = f'{t:.1f}ms' if t >= 0 else 'FAILED'
        print(f'  {phase_name}: {status}', file=sys.stderr)

    # 4. Build phases list (dependencies + phases combined)
    all_phases: list[tuple[str, float]] = []
    for name, t in dep_times.items():
        if t >= 0:
            all_phases.append((name, t))
    for name, t in phase_times.items():
        if t >= 0:
            all_phases.append((name, t))

    # 5. Sort bottleneck report (slowest first)
    sorted_phases = sort_bottleneck_report(all_phases)

    # 6. Identify threshold violations
    violations = identify_threshold_violations(sorted_phases)

    # Build result structure
    results = {
        'server_init_ms': {
            'median': round(median_init, 1),
            'times': [round(t, 1) for t in init_times],
        },
        'dependency_imports_ms': {
            name: round(t, 1) for name, t in dep_times.items() if t >= 0
        },
        'phases': [
            {'name': name, 'time_ms': round(t, 1)} for name, t in sorted_phases
        ],
        'threshold_violations': violations,
    }

    return results


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def format_text_report(results: dict) -> str:
    """Format benchmark results as human-readable text.

    Args:
        results: Benchmark results dict from run_benchmark().

    Returns:
        Formatted text report string.
    """
    lines = []
    lines.append('=' * 60)
    lines.append('AWS Documentation MCP Server — Init Benchmark')
    lines.append('=' * 60)

    # Server init summary
    init = results['server_init_ms']
    lines.append(f"\nServer Init (median): {init['median']:.1f}ms")
    lines.append(f"  Iterations: {', '.join(f'{t:.1f}ms' for t in init['times'])}")

    # Bottleneck report (sorted slowest-to-fastest)
    lines.append('\nBottleneck Report (slowest → fastest):')
    lines.append('-' * 40)
    for phase in results['phases']:
        bar = '█' * max(1, int(phase['time_ms'] / 20))
        lines.append(f"  {phase['name']:>20s}: {phase['time_ms']:>8.1f}ms  {bar}")

    # Threshold violations
    violations = results['threshold_violations']
    if violations:
        lines.append(f'\n⚠ Threshold violations (>{DEFAULT_THRESHOLD_MS:.0f}ms):')
        for v in violations:
            lines.append(f'  • {v}')
    else:
        lines.append(f'\n✓ No phases exceed {DEFAULT_THRESHOLD_MS:.0f}ms threshold')

    lines.append('')
    return '\n'.join(lines)


def format_json_report(results: dict) -> str:
    """Format benchmark results as JSON.

    Args:
        results: Benchmark results dict from run_benchmark().

    Returns:
        JSON string.
    """
    return json.dumps(results, indent=2)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    """CLI entry point for the benchmark script."""
    parser = argparse.ArgumentParser(
        description='Benchmark AWS Documentation MCP Server initialization time'
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=5,
        help='Number of iterations for server init measurement (default: 5)',
    )
    parser.add_argument(
        '--format',
        choices=['text', 'json', 'both'],
        default='both',
        help='Output format (default: both)',
    )
    args = parser.parse_args()

    if args.iterations < 1:
        parser.error('--iterations must be at least 1')

    results = run_benchmark(args.iterations)

    # Output in requested format
    if args.format in ('text', 'both'):
        print('\n' + format_text_report(results))

    if args.format in ('json', 'both'):
        if args.format == 'both':
            print('\n--- JSON Output ---')
        print(format_json_report(results))


if __name__ == '__main__':
    main()
