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

"""Gantt chart generation for workflow timeline visualization."""

from datetime import datetime


class GanttGenerator:
    """Generates Gantt-style timeline visualizations.

    This class creates SVG Gantt charts showing task execution phases
    (pending and running) with status-based coloring.
    """

    STATUS_COLORS = {
        'COMPLETED': '#6495ED',  # cornflowerblue
        'FAILED': '#DC143C',  # crimson
        'CANCELLED': '#FFA500',  # orange
    }
    PENDING_COLOR = '#D3D3D3'  # lightgrey

    TIME_SCALES = {
        'sec': 1,
        'min': 1 / 60,
        'hr': 1 / 3600,
        'day': 1 / 86400,
    }

    def generate_chart(
        self,
        tasks: list[dict],
        run_info: dict,
        time_unit: str = 'hr',
        width: int = 960,
        height: int = 800,
    ) -> str:
        """Generate SVG Gantt chart for tasks.

        Args:
            tasks: List of task dictionaries with timing data
            run_info: Run information dictionary
            time_unit: Time unit for axis (sec, min, hr, day)
            width: Chart width in pixels
            height: Chart height in pixels

        Returns:
            SVG string
        """
        # Stub implementation - will be completed in Task 9
        raise NotImplementedError('GanttGenerator.generate_chart will be implemented in Task 9')

    def _parse_time(self, time_str: str) -> datetime:
        """Parse ISO timestamp string.

        Args:
            time_str: ISO format timestamp

        Returns:
            Parsed datetime object
        """
        # Stub implementation - will be completed in Task 9
        raise NotImplementedError('GanttGenerator._parse_time will be implemented in Task 9')

    def _build_svg(
        self,
        chart_data: list[dict],
        run_info: dict,
        max_time: float,
        time_unit: str,
        width: int,
        height: int,
        show_labels: bool,
    ) -> str:
        """Build SVG string from chart data.

        Args:
            chart_data: Processed chart data
            run_info: Run information
            max_time: Maximum time value
            time_unit: Time unit label
            width: Chart width
            height: Chart height
            show_labels: Whether to show task labels

        Returns:
            SVG string
        """
        # Stub implementation - will be completed in Task 9
        raise NotImplementedError('GanttGenerator._build_svg will be implemented in Task 9')

    def _empty_chart_svg(self, width: int, height: int) -> str:
        """Return SVG for empty chart.

        Args:
            width: Chart width
            height: Chart height

        Returns:
            SVG string with "no data" message
        """
        # Stub implementation - will be completed in Task 9
        raise NotImplementedError('GanttGenerator._empty_chart_svg will be implemented in Task 9')
