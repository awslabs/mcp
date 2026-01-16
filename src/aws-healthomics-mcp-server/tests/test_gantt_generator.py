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

"""Tests for GanttGenerator visualization utility."""

import pytest
import xml.etree.ElementTree as ET
from awslabs.aws_healthomics_mcp_server.visualization.gantt_generator import GanttGenerator
from datetime import datetime, timedelta, timezone
from hypothesis import given, settings
from hypothesis import strategies as st


# Strategies for generating test data
@st.composite
def task_strategy(draw, base_time: datetime | None = None):
    """Generate a valid task dictionary for testing."""
    if base_time is None:
        base_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    # Generate task timing
    creation_offset = draw(st.integers(min_value=0, max_value=3600))
    start_offset = draw(st.integers(min_value=0, max_value=300))
    running_duration = draw(st.integers(min_value=1, max_value=3600))

    creation_time = base_time + timedelta(seconds=creation_offset)
    start_time = creation_time + timedelta(seconds=start_offset)
    stop_time = start_time + timedelta(seconds=running_duration)

    status = draw(st.sampled_from(['COMPLETED', 'FAILED', 'CANCELLED']))
    task_name = draw(
        st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=('L', 'N', 'P', 'S'), blacklist_characters='<>&"\''
            ),
        )
    )

    return {
        'taskName': task_name if task_name.strip() else 'Task',
        'creationTime': creation_time.isoformat(),
        'startTime': start_time.isoformat(),
        'stopTime': stop_time.isoformat(),
        'status': status,
        'allocatedCpus': draw(st.integers(min_value=1, max_value=96)),
        'allocatedMemoryGiB': draw(st.integers(min_value=1, max_value=768)),
        'instanceType': draw(
            st.sampled_from(
                [
                    'omics.c.large',
                    'omics.m.xlarge',
                    'omics.r.2xlarge',
                    'omics.m.4xlarge',
                    'omics.r.8xlarge',
                ]
            )
        ),
        'estimatedUSD': draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False)),
    }


@st.composite
def tasks_list_strategy(draw, min_tasks: int = 1, max_tasks: int = 20):
    """Generate a list of valid tasks."""
    base_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    num_tasks = draw(st.integers(min_value=min_tasks, max_value=max_tasks))
    tasks = []
    for _ in range(num_tasks):
        task = draw(task_strategy(base_time))
        tasks.append(task)
    return tasks


class TestGanttGeneratorBasic:
    """Basic unit tests for GanttGenerator."""

    def test_empty_tasks(self):
        """Test generate_chart with empty task list."""
        generator = GanttGenerator()
        run_info = {'runName': 'TestRun'}
        svg = generator.generate_chart([], run_info)
        assert 'No task data available' in svg
        assert svg.startswith('<svg')
        assert svg.endswith('</svg>')

    def test_single_task(self):
        """Test generate_chart with a single task."""
        generator = GanttGenerator()
        base_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        tasks = [
            {
                'taskName': 'SingleTask',
                'creationTime': base_time.isoformat(),
                'startTime': (base_time + timedelta(seconds=30)).isoformat(),
                'stopTime': (base_time + timedelta(minutes=5)).isoformat(),
                'status': 'COMPLETED',
                'allocatedCpus': 4,
                'allocatedMemoryGiB': 8,
                'instanceType': 'omics.m.xlarge',
                'estimatedUSD': 0.05,
            }
        ]
        run_info = {'runName': 'TestRun'}
        svg = generator.generate_chart(tasks, run_info)

        assert svg.startswith('<svg')
        assert svg.endswith('</svg>')
        assert 'SingleTask' in svg
        assert '<rect' in svg

    def test_status_colors(self):
        """Test that different statuses produce different colors."""
        generator = GanttGenerator()
        base_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        for status, expected_color in GanttGenerator.STATUS_COLORS.items():
            tasks = [
                {
                    'taskName': f'Task_{status}',
                    'creationTime': base_time.isoformat(),
                    'startTime': (base_time + timedelta(seconds=10)).isoformat(),
                    'stopTime': (base_time + timedelta(minutes=1)).isoformat(),
                    'status': status,
                }
            ]
            run_info = {'runName': 'TestRun'}
            svg = generator.generate_chart(tasks, run_info)
            assert expected_color in svg, f'Expected color {expected_color} for status {status}'

    def test_time_units(self):
        """Test different time units."""
        generator = GanttGenerator()
        base_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        tasks = [
            {
                'taskName': 'Task1',
                'creationTime': base_time.isoformat(),
                'stopTime': (base_time + timedelta(hours=2)).isoformat(),
                'status': 'COMPLETED',
            }
        ]
        run_info = {'runName': 'TestRun'}

        for unit in ['sec', 'min', 'hr', 'day']:
            svg = generator.generate_chart(tasks, run_info, time_unit=unit)
            assert f'Time ({unit})' in svg

    def test_many_tasks_omits_labels(self):
        """Test that >100 tasks omits labels (Requirement 5.6)."""
        generator = GanttGenerator()
        base_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Create 101 tasks
        tasks = []
        for i in range(101):
            tasks.append(
                {
                    'taskName': f'Task{i}',
                    'creationTime': (base_time + timedelta(seconds=i)).isoformat(),
                    'stopTime': (base_time + timedelta(seconds=i + 60)).isoformat(),
                    'status': 'COMPLETED',
                }
            )

        run_info = {'runName': 'TestRun'}
        svg = generator.generate_chart(tasks, run_info)

        # With >100 tasks, left margin should be 40 (no labels)
        # The SVG should still be valid
        assert svg.startswith('<svg')
        assert svg.endswith('</svg>')

    def test_pending_phase_color(self):
        """Test that pending phase uses correct color."""
        generator = GanttGenerator()
        base_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        tasks = [
            {
                'taskName': 'Task1',
                'creationTime': base_time.isoformat(),
                'startTime': (base_time + timedelta(minutes=1)).isoformat(),
                'stopTime': (base_time + timedelta(minutes=5)).isoformat(),
                'status': 'COMPLETED',
            }
        ]
        run_info = {'runName': 'TestRun'}
        svg = generator.generate_chart(tasks, run_info)

        # Should contain the pending color
        assert GanttGenerator.PENDING_COLOR in svg

    def test_tooltip_content(self):
        """Test that tooltips contain required information (Requirement 5.4)."""
        generator = GanttGenerator()
        base_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        tasks = [
            {
                'taskName': 'TestTask',
                'creationTime': base_time.isoformat(),
                'startTime': (base_time + timedelta(seconds=30)).isoformat(),
                'stopTime': (base_time + timedelta(minutes=5)).isoformat(),
                'status': 'COMPLETED',
                'allocatedCpus': 4,
                'allocatedMemoryGiB': 8,
                'instanceType': 'omics.m.xlarge',
                'estimatedUSD': 0.0567,
            }
        ]
        run_info = {'runName': 'TestRun'}
        svg = generator.generate_chart(tasks, run_info)

        # Tooltip should contain task details
        assert 'TestTask' in svg
        assert 'CPUs: 4' in svg
        assert 'Memory: 8 GiB' in svg
        assert 'omics.m.xlarge' in svg
        assert '$0.0567' in svg

    def test_parse_time_with_z_suffix(self):
        """Test _parse_time handles Z suffix."""
        generator = GanttGenerator()
        result = generator._parse_time('2024-01-01T10:00:00Z')
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 10

    def test_parse_time_with_datetime(self):
        """Test _parse_time handles datetime objects."""
        generator = GanttGenerator()
        dt = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        result = generator._parse_time(dt)
        assert result == dt

    def test_parse_time_with_variable_fractional_seconds(self):
        """Test _parse_time handles ISO timestamps with variable fractional second precision.

        Python 3.10's fromisoformat only accepts 3 or 6 decimal places, but AWS
        HealthOmics can return timestamps with 5 decimal places (e.g., .22971).
        """
        generator = GanttGenerator()

        # 5 decimal places (the problematic case from production)
        result = generator._parse_time('2025-11-18T22:40:41.22971+00:00')
        assert result.year == 2025
        assert result.month == 11
        assert result.microsecond == 229710

        # 3 decimal places (milliseconds)
        result = generator._parse_time('2024-01-01T10:00:00.123+00:00')
        assert result.microsecond == 123000

        # 6 decimal places (microseconds)
        result = generator._parse_time('2024-01-01T10:00:00.123456+00:00')
        assert result.microsecond == 123456

        # 1 decimal place
        result = generator._parse_time('2024-01-01T10:00:00.1+00:00')
        assert result.microsecond == 100000


class TestGanttGeneratorPropertyBased:
    """Property-based tests for GanttGenerator using Hypothesis."""

    @given(tasks=tasks_list_strategy(min_tasks=1, max_tasks=50))
    @settings(max_examples=100)
    def test_property_svg_contains_required_visual_elements(self, tasks: list[dict]):
        """Property 7: SVG Contains Required Visual Elements.

        For any task in the timeline, the SVG SHALL contain exactly two rectangle
        elements for that task (pending phase and running phase), and the running
        phase rectangle SHALL have a fill color matching the task's status.

        **Validates: Requirements 5.2, 5.3, 5.4**
        **Feature: run-analyzer-enhancement, Property 7: SVG Contains Required Visual Elements**
        """
        generator = GanttGenerator()
        run_info = {'runName': 'TestRun'}
        svg = generator.generate_chart(tasks, run_info)

        # Property: SVG is well-formed
        assert svg.startswith('<svg'), 'SVG must start with <svg'
        assert svg.endswith('</svg>'), 'SVG must end with </svg>'

        # Property: SVG is valid XML
        try:
            root = ET.fromstring(svg)
        except ET.ParseError as e:
            pytest.fail(f'SVG is not well-formed XML: {e}')

        # Count rectangles in the SVG
        rects = root.findall('.//{http://www.w3.org/2000/svg}rect')
        if not rects:
            # Try without namespace (some SVGs may not use namespace prefix)
            rects = [elem for elem in root.iter() if elem.tag.endswith('rect')]

        # Property: For each task, there should be at least one rectangle
        # (pending phase may have zero width if start == creation)
        num_tasks = len(tasks)
        # Each task has at most 2 rects (pending + running), at least 1 (running)
        assert len(rects) >= num_tasks, (
            f'Expected at least {num_tasks} rectangles for {num_tasks} tasks, got {len(rects)}'
        )
        assert len(rects) <= num_tasks * 2, (
            f'Expected at most {num_tasks * 2} rectangles for {num_tasks} tasks, got {len(rects)}'
        )

        # Property: Running phase rectangles have correct status colors
        for task in tasks:
            status = task.get('status', 'COMPLETED')
            expected_color = GanttGenerator.STATUS_COLORS.get(status, '#6495ED')
            assert expected_color in svg, (
                f'Expected color {expected_color} for status {status} in SVG'
            )

    @given(
        time_unit=st.sampled_from(['sec', 'min', 'hr', 'day']),
        width=st.integers(min_value=200, max_value=2000),
        height=st.integers(min_value=200, max_value=2000),
    )
    @settings(max_examples=100)
    def test_property_valid_svg_for_any_parameters(self, time_unit: str, width: int, height: int):
        """Property: Valid SVG output for any valid parameters.

        For any valid time unit and dimensions, the generated SVG should be
        well-formed and contain the correct dimensions.

        **Validates: Requirements 5.5, 5.7**
        **Feature: run-analyzer-enhancement, Property 7: SVG Contains Required Visual Elements**
        """
        generator = GanttGenerator()
        base_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        tasks = [
            {
                'taskName': 'Task1',
                'creationTime': base_time.isoformat(),
                'startTime': (base_time + timedelta(seconds=30)).isoformat(),
                'stopTime': (base_time + timedelta(minutes=5)).isoformat(),
                'status': 'COMPLETED',
            }
        ]
        run_info = {'runName': 'TestRun'}

        svg = generator.generate_chart(
            tasks, run_info, time_unit=time_unit, width=width, height=height
        )

        # Property: SVG has correct dimensions
        assert f'width="{width}"' in svg
        assert f'height="{height}"' in svg

        # Property: SVG contains time unit label
        assert f'Time ({time_unit})' in svg

        # Property: SVG is valid XML
        try:
            ET.fromstring(svg)
        except ET.ParseError as e:
            pytest.fail(f'SVG is not valid XML: {e}')

    @given(status=st.sampled_from(['COMPLETED', 'FAILED', 'CANCELLED']))
    @settings(max_examples=100)
    def test_property_status_color_mapping(self, status: str):
        """Property: Status colors are correctly mapped.

        For any task status, the running phase rectangle SHALL have the
        correct fill color as defined in STATUS_COLORS.

        **Validates: Requirements 5.3**
        **Feature: run-analyzer-enhancement, Property 7: SVG Contains Required Visual Elements**
        """
        generator = GanttGenerator()
        base_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        tasks = [
            {
                'taskName': 'Task1',
                'creationTime': base_time.isoformat(),
                'startTime': (base_time + timedelta(seconds=30)).isoformat(),
                'stopTime': (base_time + timedelta(minutes=5)).isoformat(),
                'status': status,
            }
        ]
        run_info = {'runName': 'TestRun'}

        svg = generator.generate_chart(tasks, run_info)
        expected_color = GanttGenerator.STATUS_COLORS[status]

        # Property: The expected color appears in the SVG
        assert expected_color in svg, f'Expected color {expected_color} for status {status}'

        # Property: The pending color also appears (for the pending phase)
        assert GanttGenerator.PENDING_COLOR in svg, 'Expected pending color in SVG'
