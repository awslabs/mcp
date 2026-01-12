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

"""Concurrent resource tracking for workflow runs."""

from datetime import datetime
from typing import NamedTuple, Optional


class TimelineEvent(NamedTuple):
    """Event in the resource timeline."""

    time: datetime
    event_type: str  # 'start' or 'stop'
    cpus: float
    memory_gib: float


class ConcurrentResourceTracker:
    """Tracks concurrent resource usage across tasks.

    This class calculates peak and average concurrent resource usage
    by processing task start/stop events over time.
    """

    def calculate_concurrent_metrics(self, tasks: list[dict]) -> dict:
        """Calculate peak and average concurrent resource usage.

        Args:
            tasks: List of task dictionaries with timing and resource data.
                   Each task should have:
                   - startTime: ISO timestamp or datetime when task started running
                   - stopTime: ISO timestamp or datetime when task stopped
                   - reservedCpus: Number of CPUs reserved for the task
                   - reservedMemoryGiB: Memory in GiB reserved for the task

        Returns:
            Dictionary with:
            - peakConcurrentCpus: Maximum simultaneous CPU usage
            - peakConcurrentMemoryGiB: Maximum simultaneous memory usage
            - averageConcurrentCpus: Time-weighted average CPU usage
            - averageConcurrentMemoryGiB: Time-weighted average memory usage
        """
        events = self._build_timeline_events(tasks)

        if not events:
            return {
                'peakConcurrentCpus': 0.0,
                'peakConcurrentMemoryGiB': 0.0,
                'averageConcurrentCpus': 0.0,
                'averageConcurrentMemoryGiB': 0.0,
            }

        # Sort events by time
        events.sort(key=lambda e: e.time)

        # Track current and peak resources
        current_cpus = 0.0
        current_memory = 0.0
        peak_cpus = 0.0
        peak_memory = 0.0

        # Track time-weighted sums for average calculation
        weighted_cpu_sum = 0.0
        weighted_memory_sum = 0.0
        previous_time = events[0].time

        for event in events:
            # Calculate time delta from previous event
            delta_seconds = (event.time - previous_time).total_seconds()

            # Accumulate weighted sums (area under the curve)
            weighted_cpu_sum += current_cpus * delta_seconds
            weighted_memory_sum += current_memory * delta_seconds

            # Update current resources based on event type
            if event.event_type == 'start':
                current_cpus += event.cpus
                current_memory += event.memory_gib
            else:  # 'stop'
                current_cpus -= event.cpus
                current_memory -= event.memory_gib

            # Track peaks (after updating for start events)
            peak_cpus = max(peak_cpus, current_cpus)
            peak_memory = max(peak_memory, current_memory)

            previous_time = event.time

        # Calculate total duration
        total_seconds = (events[-1].time - events[0].time).total_seconds()

        # Calculate time-weighted averages
        avg_cpus = weighted_cpu_sum / total_seconds if total_seconds > 0 else 0.0
        avg_memory = weighted_memory_sum / total_seconds if total_seconds > 0 else 0.0

        return {
            'peakConcurrentCpus': peak_cpus,
            'peakConcurrentMemoryGiB': peak_memory,
            'averageConcurrentCpus': avg_cpus,
            'averageConcurrentMemoryGiB': avg_memory,
        }

    def _build_timeline_events(self, tasks: list[dict]) -> list[TimelineEvent]:
        """Build timeline events from task list.

        Args:
            tasks: List of task dictionaries

        Returns:
            List of TimelineEvent objects
        """
        events = []

        for task in tasks:
            start_time = task.get('startTime')
            stop_time = task.get('stopTime')
            cpus = task.get('reservedCpus', 0)
            memory = task.get('reservedMemoryGiB', 0)

            # Skip tasks without required timing data
            if not start_time or not stop_time:
                continue

            # Parse timestamps if strings
            start_time = self._parse_timestamp(start_time)
            stop_time = self._parse_timestamp(stop_time)

            if start_time is None or stop_time is None:
                continue

            # Create start and stop events
            events.append(TimelineEvent(start_time, 'start', float(cpus), float(memory)))
            events.append(TimelineEvent(stop_time, 'stop', float(cpus), float(memory)))

        return events

    def _parse_timestamp(self, timestamp) -> Optional[datetime]:
        """Parse a timestamp into a datetime object.

        Args:
            timestamp: ISO timestamp string or datetime object

        Returns:
            datetime object or None if parsing fails
        """
        if isinstance(timestamp, datetime):
            return timestamp

        if isinstance(timestamp, str):
            try:
                # Handle ISO format with Z suffix
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                return None

        return None
