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

"""Coverage report generation for OSS-Fuzz integration.

This module provides the CoverageReporter class for generating HTML and JSON
coverage reports from fuzzing runs. It supports merging coverage data from
multiple runs and identifying uncovered code paths.

The coverage reporter integrates with Python's coverage.py library and is
compatible with the project's existing coverage reporting tools.

Example usage:
    ```python
    from fuzzing.coverage_reporter import CoverageReporter
    from pathlib import Path

    reporter = CoverageReporter(output_dir=Path('coverage_reports'))

    # Generate reports from coverage data
    html_path = reporter.generate_html_report(Path('.coverage'))
    json_path = reporter.generate_json_report(Path('.coverage'))

    # Merge multiple coverage files
    merged = reporter.merge_coverage(
        Path('.coverage.fuzz1'),
        Path('.coverage.fuzz2'),
    )
    ```
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class CoverageStats:
    """Statistics from a coverage report.

    Attributes:
        total_statements: Total number of executable statements
        covered_statements: Number of statements executed
        missing_statements: Number of statements not executed
        total_branches: Total number of branches (if branch coverage enabled)
        covered_branches: Number of branches taken
        missing_branches: Number of branches not taken
        line_coverage_percent: Percentage of lines covered
        branch_coverage_percent: Percentage of branches covered (if applicable)
    """

    total_statements: int = 0
    covered_statements: int = 0
    missing_statements: int = 0
    total_branches: int = 0
    covered_branches: int = 0
    missing_branches: int = 0
    line_coverage_percent: float = 0.0
    branch_coverage_percent: float = 0.0


@dataclass
class FileCoverage:
    """Coverage information for a single file.

    Attributes:
        filename: Path to the source file
        covered_lines: Set of line numbers that were executed
        missing_lines: Set of line numbers that were not executed
        covered_branches: Set of branch identifiers that were taken
        missing_branches: Set of branch identifiers that were not taken
    """

    filename: str
    covered_lines: set[int] = field(default_factory=set)
    missing_lines: set[int] = field(default_factory=set)
    covered_branches: set[str] = field(default_factory=set)
    missing_branches: set[str] = field(default_factory=set)


@dataclass
class CoverageReport:
    """Complete coverage report from a fuzzing run.

    Attributes:
        timestamp: When the report was generated
        stats: Overall coverage statistics
        files: Per-file coverage information
        source_dir: Root directory of source files
    """

    timestamp: datetime
    stats: CoverageStats
    files: dict[str, FileCoverage]
    source_dir: Optional[Path] = None


class CoverageReporter:
    """Generates and manages coverage reports from fuzzing.

    This class provides functionality to:
    - Generate HTML coverage reports for visual inspection
    - Generate JSON coverage reports for programmatic analysis
    - Merge coverage data from multiple fuzzing runs
    - Identify uncovered code paths that may need additional fuzz targets

    The reporter uses Python's coverage.py library under the hood and is
    compatible with the project's existing coverage infrastructure.
    """

    def __init__(self, output_dir: Path):
        """Initialize the coverage reporter.

        Args:
            output_dir: Directory where coverage reports will be written
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_html_report(
        self,
        coverage_data: Path,
        title: Optional[str] = None,
    ) -> Path:
        """Generate HTML coverage report.

        Creates an HTML report showing line and branch coverage with
        source code highlighting.

        Args:
            coverage_data: Path to .coverage data file
            title: Optional title for the report

        Returns:
            Path to the generated HTML report directory

        Raises:
            FileNotFoundError: If coverage_data doesn't exist
            RuntimeError: If coverage report generation fails
        """
        if not coverage_data.exists():
            raise FileNotFoundError(f'Coverage data file not found: {coverage_data}')

        html_dir = self.output_dir / 'html'
        html_dir.mkdir(parents=True, exist_ok=True)

        # Build coverage command
        cmd = [
            'python',
            '-m',
            'coverage',
            'html',
            f'--data-file={coverage_data}',
            f'--directory={html_dir}',
        ]

        if title:
            cmd.append(f'--title={title}')

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'Failed to generate HTML coverage report: {e.stderr}') from e

        return html_dir

    def generate_json_report(
        self,
        coverage_data: Path,
        pretty_print: bool = True,
    ) -> Path:
        """Generate JSON coverage report.

        Creates a JSON report containing detailed coverage information
        suitable for programmatic analysis.

        Args:
            coverage_data: Path to .coverage data file
            pretty_print: Whether to format JSON with indentation

        Returns:
            Path to the generated JSON report file

        Raises:
            FileNotFoundError: If coverage_data doesn't exist
            RuntimeError: If coverage report generation fails
        """
        if not coverage_data.exists():
            raise FileNotFoundError(f'Coverage data file not found: {coverage_data}')

        json_file = self.output_dir / 'coverage.json'

        # Build coverage command
        cmd = [
            'python',
            '-m',
            'coverage',
            'json',
            f'--data-file={coverage_data}',
            f'-o={json_file}',
        ]

        if pretty_print:
            cmd.append('--pretty-print')

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'Failed to generate JSON coverage report: {e.stderr}') from e

        return json_file

    def merge_coverage(self, *coverage_files: Path) -> Path:
        """Merge multiple coverage data files.

        Combines coverage data from multiple fuzzing runs into a single
        coverage file. The merged coverage represents the union of all
        line and branch coverage from the input files.

        Args:
            *coverage_files: Paths to .coverage data files to merge

        Returns:
            Path to the merged coverage data file

        Raises:
            ValueError: If no coverage files are provided
            FileNotFoundError: If any coverage file doesn't exist
            RuntimeError: If coverage merge fails
        """
        if not coverage_files:
            raise ValueError('At least one coverage file must be provided')

        # Verify all files exist
        for cov_file in coverage_files:
            if not cov_file.exists():
                raise FileNotFoundError(f'Coverage file not found: {cov_file}')

        merged_file = self.output_dir / '.coverage.merged'

        # Build coverage combine command
        cmd = [
            'python',
            '-m',
            'coverage',
            'combine',
            f'--data-file={merged_file}',
            '--keep',  # Keep original files
        ]
        cmd.extend(str(f) for f in coverage_files)

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'Failed to merge coverage files: {e.stderr}') from e

        return merged_file

    def get_coverage_stats(self, coverage_data: Path) -> CoverageStats:
        """Get coverage statistics from a coverage data file.

        Args:
            coverage_data: Path to .coverage data file

        Returns:
            CoverageStats with line and branch coverage information

        Raises:
            FileNotFoundError: If coverage_data doesn't exist
            RuntimeError: If reading coverage data fails
        """
        if not coverage_data.exists():
            raise FileNotFoundError(f'Coverage data file not found: {coverage_data}')

        # Generate JSON report to parse stats
        json_file = self.output_dir / '.coverage_stats.json'

        cmd = [
            'python',
            '-m',
            'coverage',
            'json',
            f'--data-file={coverage_data}',
            f'-o={json_file}',
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)

            with open(json_file, 'r') as f:
                data = json.load(f)

            totals = data.get('totals', {})

            stats = CoverageStats(
                total_statements=totals.get('num_statements', 0),
                covered_statements=totals.get('covered_lines', 0),
                missing_statements=totals.get('missing_lines', 0),
                total_branches=totals.get('num_branches', 0),
                covered_branches=totals.get('covered_branches', 0),
                missing_branches=totals.get('missing_branches', 0),
                line_coverage_percent=totals.get('percent_covered', 0.0),
                branch_coverage_percent=totals.get('percent_covered_branches', 0.0),
            )

            # Clean up temp file
            json_file.unlink(missing_ok=True)

            return stats

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'Failed to get coverage stats: {e.stderr}') from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f'Failed to parse coverage JSON: {e}') from e

    def get_uncovered_files(self, coverage_data: Path) -> list[str]:
        """Get list of files with uncovered code.

        Identifies source files that have lines not covered by fuzzing,
        which may need additional fuzz targets or seed corpus entries.

        Args:
            coverage_data: Path to .coverage data file

        Returns:
            List of file paths with uncovered lines

        Raises:
            FileNotFoundError: If coverage_data doesn't exist
            RuntimeError: If reading coverage data fails
        """
        if not coverage_data.exists():
            raise FileNotFoundError(f'Coverage data file not found: {coverage_data}')

        # Generate JSON report to parse file coverage
        json_file = self.output_dir / '.coverage_files.json'

        cmd = [
            'python',
            '-m',
            'coverage',
            'json',
            f'--data-file={coverage_data}',
            f'-o={json_file}',
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)

            with open(json_file, 'r') as f:
                data = json.load(f)

            uncovered = []
            for filename, file_data in data.get('files', {}).items():
                missing = file_data.get('missing_lines', [])
                if missing:
                    uncovered.append(filename)

            # Clean up temp file
            json_file.unlink(missing_ok=True)

            return sorted(uncovered)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'Failed to get uncovered files: {e.stderr}') from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f'Failed to parse coverage JSON: {e}') from e

    def generate_summary_report(
        self,
        coverage_data: Path,
        output_file: Optional[Path] = None,
    ) -> str:
        """Generate a text summary of coverage.

        Creates a human-readable summary showing overall coverage
        statistics and files with lowest coverage.

        Args:
            coverage_data: Path to .coverage data file
            output_file: Optional path to write summary to

        Returns:
            The summary text

        Raises:
            FileNotFoundError: If coverage_data doesn't exist
            RuntimeError: If generating summary fails
        """
        stats = self.get_coverage_stats(coverage_data)
        uncovered = self.get_uncovered_files(coverage_data)

        timestamp = datetime.now(timezone.utc).isoformat()

        lines = [
            '=' * 60,
            'FUZZING COVERAGE SUMMARY',
            '=' * 60,
            f'Generated: {timestamp}',
            '',
            'OVERALL STATISTICS',
            '-' * 60,
            f'Line Coverage:   {stats.line_coverage_percent:.1f}%',
            f'  Covered:       {stats.covered_statements}',
            f'  Missing:       {stats.missing_statements}',
            f'  Total:         {stats.total_statements}',
            '',
        ]

        if stats.total_branches > 0:
            lines.extend(
                [
                    f'Branch Coverage: {stats.branch_coverage_percent:.1f}%',
                    f'  Covered:       {stats.covered_branches}',
                    f'  Missing:       {stats.missing_branches}',
                    f'  Total:         {stats.total_branches}',
                    '',
                ]
            )

        if uncovered:
            lines.extend(
                [
                    'FILES WITH UNCOVERED CODE',
                    '-' * 60,
                ]
            )
            for filename in uncovered[:20]:  # Limit to top 20
                lines.append(f'  {filename}')
            if len(uncovered) > 20:
                lines.append(f'  ... and {len(uncovered) - 20} more files')
            lines.append('')

        lines.append('=' * 60)

        summary = '\n'.join(lines)

        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                f.write(summary)

        return summary
