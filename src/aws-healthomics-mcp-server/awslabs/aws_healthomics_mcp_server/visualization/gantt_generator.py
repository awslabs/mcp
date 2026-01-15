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

from awslabs.aws_healthomics_mcp_server.visualization.svg_builder import SVGBuilder
from datetime import datetime
from typing import Union


class GanttGenerator:
    """Generates Gantt-style timeline visualizations.

    This class creates SVG Gantt charts showing task execution phases
    (pending and running) with status-based coloring.

    Attributes:
        STATUS_COLORS: Color mapping for task statuses (COMPLETED, FAILED, CANCELLED)
        PENDING_COLOR: Color for pending/starting phase
        TIME_SCALES: Conversion factors from seconds to time units
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
            tasks: List of task dictionaries with timing data. Each task should have:
                - creationTime: ISO timestamp when task was created
                - startTime: ISO timestamp when task started running (optional)
                - stopTime: ISO timestamp when task stopped
                - taskName: Name of the task
                - status: Task status (COMPLETED, FAILED, CANCELLED)
                - allocatedCpus: Number of CPUs allocated (optional)
                - allocatedMemoryGiB: Memory allocated in GiB (optional)
                - instanceType: Instance type used (optional)
                - estimatedUSD: Estimated cost in USD (optional)
            run_info: Run information dictionary with:
                - runName: Name of the run
                - arn: ARN of the run (optional)
            time_unit: Time unit for axis (sec, min, hr, day). Defaults to 'hr'.
            width: Chart width in pixels. Defaults to 960.
            height: Chart height in pixels. Defaults to 800.

        Returns:
            SVG string representing the Gantt chart
        """
        if not tasks:
            return self._empty_chart_svg(width, height)

        # Filter tasks with valid timing data (need at least creationTime and stopTime)
        valid_tasks = [t for t in tasks if t.get('creationTime') and t.get('stopTime')]
        if not valid_tasks:
            return self._empty_chart_svg(width, height)

        # Calculate time reference (earliest creation time)
        tare = min(self._parse_time(t['creationTime']) for t in valid_tasks)
        time_scale = self.TIME_SCALES.get(time_unit, 1 / 3600)

        # Calculate chart data
        chart_data = []
        max_time = 0.0

        for i, task in enumerate(valid_tasks):
            creation = self._parse_time(task['creationTime'])
            # Use creationTime as startTime if startTime is not available
            start = self._parse_time(task.get('startTime') or task['creationTime'])
            stop = self._parse_time(task['stopTime'])

            pending_start = (creation - tare).total_seconds() * time_scale
            pending_end = (start - tare).total_seconds() * time_scale
            running_end = (stop - tare).total_seconds() * time_scale

            # Calculate durations in seconds
            pending_seconds = (start - creation).total_seconds()
            running_seconds = (stop - start).total_seconds()

            max_time = max(max_time, running_end)

            chart_data.append(
                {
                    'index': i,
                    'name': task.get('taskName', f'Task {i}'),
                    'pending_start': pending_start,
                    'pending_end': pending_end,
                    'running_end': running_end,
                    'status': task.get('status', 'COMPLETED'),
                    'cpus': task.get('allocatedCpus', task.get('reservedCpus', 0)),
                    'memory': task.get('allocatedMemoryGiB', task.get('reservedMemoryGiB', 0)),
                    'instance_type': task.get('instanceType', 'N/A'),
                    'cost': task.get('estimatedUSD', 0),
                    # Timing details for tooltips
                    'creation_time': creation,
                    'start_time': start,
                    'stop_time': stop,
                    'pending_seconds': pending_seconds,
                    'running_seconds': running_seconds,
                }
            )

        # Handle edge case where max_time is 0 (all tasks completed instantly)
        if max_time <= 0:
            max_time = 1.0

        # Build SVG - omit labels if more than 100 tasks (Requirement 5.6)
        show_labels = len(valid_tasks) <= 100
        return self._build_svg(
            chart_data, run_info, max_time, time_unit, width, height, show_labels
        )

    def _parse_time(self, time_str: Union[str, datetime]) -> datetime:
        """Parse ISO timestamp string.

        Args:
            time_str: ISO format timestamp string or datetime object

        Returns:
            Parsed datetime object
        """
        if isinstance(time_str, datetime):
            return time_str
        # Handle ISO format with 'Z' suffix
        iso_string = time_str.replace('Z', '+00:00')
        # Normalize fractional seconds to 6 digits for Python 3.10 compatibility
        # Python 3.10's fromisoformat only accepts 3 or 6 decimal places
        import re

        match = re.match(r'(.+\.\d{1,6})(\d*)([+-]\d{2}:\d{2})?$', iso_string)
        if match:
            base, extra_digits, tz = match.groups()
            # Pad to 6 digits if needed
            decimal_part = base.split('.')[-1]
            if len(decimal_part) < 6:
                base = base[: -len(decimal_part)] + decimal_part.ljust(6, '0')
            iso_string = base + (tz or '')
        return datetime.fromisoformat(iso_string)

    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human-readable string.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string (e.g., "1h 23m 45s" or "5m 30s")
        """
        if seconds < 0:
            return '0s'

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if hours > 0:
            parts.append(f'{hours}h')
        if minutes > 0 or hours > 0:
            parts.append(f'{minutes}m')
        parts.append(f'{secs}s')

        return ' '.join(parts)

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
            chart_data: Processed chart data with timing and metadata
            run_info: Run information dictionary
            max_time: Maximum time value for scaling
            time_unit: Time unit label for axis
            width: Chart width in pixels
            height: Chart height in pixels
            show_labels: Whether to show task name labels

        Returns:
            SVG string
        """
        builder = SVGBuilder(width, height)

        # Add title
        run_id = run_info.get('runId', 'Unknown')
        run_name = run_info.get('runName', 'Unknown')
        task_count = len(chart_data)
        title = f'Run: {run_id}, Name: {run_name}, Tasks: {task_count}, Duration: {max_time:.2f} {time_unit}'
        builder.add_title(title)

        # Calculate dimensions with margins
        margin = {
            'top': 60,
            'right': 40,
            'bottom': 40,
            'left': 150 if show_labels else 40,
        }
        chart_width = width - margin['left'] - margin['right']
        chart_height = height - margin['top'] - margin['bottom']

        # Calculate bar dimensions
        num_tasks = len(chart_data)
        bar_height = min(20, chart_height / num_tasks - 2) if num_tasks > 0 else 20
        x_scale = chart_width / (max_time * 1.05) if max_time > 0 else 1  # 5% padding

        # Add bars for each task
        for task in chart_data:
            y = margin['top'] + task['index'] * (bar_height + 2)

            # Pending bar (grey) - Requirement 5.2
            pending_width = (task['pending_end'] - task['pending_start']) * x_scale
            if pending_width > 0:
                # Build pending tooltip with creation time and wait duration
                pending_duration = self._format_duration(task['pending_seconds'])
                creation_str = task['creation_time'].strftime('%Y-%m-%d %H:%M:%S')
                pending_tooltip = (
                    f'{task["name"]}: Pending\n'
                    f'Created: {creation_str}\n'
                    f'Wait time: {pending_duration}'
                )
                builder.add_rect(
                    x=margin['left'] + task['pending_start'] * x_scale,
                    y=y,
                    width=pending_width,
                    height=bar_height,
                    fill=self.PENDING_COLOR,
                    tooltip=pending_tooltip,
                )

            # Running bar (colored by status) - Requirement 5.3
            running_width = (task['running_end'] - task['pending_end']) * x_scale
            color = self.STATUS_COLORS.get(task['status'], '#6495ED')

            # Build tooltip with task details including timing - Requirement 5.4
            start_str = task['start_time'].strftime('%Y-%m-%d %H:%M:%S')
            stop_str = task['stop_time'].strftime('%Y-%m-%d %H:%M:%S')
            running_duration = self._format_duration(task['running_seconds'])
            tooltip = (
                f'{task["name"]}\n'
                f'Start: {start_str}\n'
                f'Stop: {stop_str}\n'
                f'Duration: {running_duration}\n'
                f'CPUs: {task["cpus"]}, Memory: {task["memory"]} GiB\n'
                f'Instance: {task["instance_type"]}\n'
                f'Cost: ${task["cost"]:.4f}'
            )
            builder.add_rect(
                x=margin['left'] + task['pending_end'] * x_scale,
                y=y,
                width=running_width,
                height=bar_height,
                fill=color,
                tooltip=tooltip,
            )

            # Task label (only if showing labels)
            if show_labels:
                # Truncate long task names to fit
                display_name = task['name'][:20] if len(task['name']) > 20 else task['name']
                builder.add_text(
                    x=margin['left'] - 5,
                    y=y + bar_height / 2,
                    text=display_name,
                    anchor='end',
                )

        # Add X axis with time scale - Requirement 5.5
        builder.add_x_axis(margin, chart_width, max_time, time_unit)

        return builder.build()

    def _empty_chart_svg(self, width: int, height: int) -> str:
        """Return SVG for empty chart.

        Args:
            width: Chart width in pixels
            height: Chart height in pixels

        Returns:
            SVG string with "no data" message
        """
        return (
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">\n'
            f'<text x="{width / 2}" y="{height / 2}" text-anchor="middle">'
            f'No task data available</text>\n'
            f'</svg>'
        )
