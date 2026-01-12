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

"""Task aggregation for scattered tasks and multi-run analysis."""

import polars as pl
import re


class TaskAggregator:
    """Aggregates metrics for scattered tasks across runs.

    This class normalizes task names by removing scatter/iteration suffixes
    and aggregates metrics using Polars for efficient DataFrame operations.

    Supports three workflow patterns:
    - WDL: taskName-<shard>-<attempt> (e.g., "alignReads-0-1", "alignReads-1-1")
    - Nextflow: taskName (index) (e.g., "alignReads (1)", "alignReads (sample1)")
    - CWL: taskName_<index> (e.g., "alignReads_0", "alignReads_1")
    """

    # Patterns for normalizing task names
    # WDL pattern: taskName-<shard>-<attempt> where shard and attempt are digits
    WDL_PATTERN = re.compile(r'^(.+)-(\d+)-(\d+)$')
    # Nextflow pattern: taskName (index) where index can be anything in parentheses
    NEXTFLOW_PATTERN = re.compile(r'^(.+)\s+\(.+\)$')
    # CWL pattern: taskName_<index> where index is digits at the end
    CWL_PATTERN = re.compile(r'^(.+)_(\d+)$')

    @classmethod
    def normalize_task_name(cls, task_name: str) -> str:
        """Remove scatter/iteration suffixes from task name.

        Normalizes task names by removing workflow-specific scatter/iteration
        suffixes to group related tasks together.

        Args:
            task_name: Original task name with potential scatter suffix

        Returns:
            Normalized base task name with scatter suffixes removed
        """
        if not task_name:
            return task_name

        # Try WDL pattern first: taskName-<shard>-<attempt>
        match = cls.WDL_PATTERN.match(task_name)
        if match:
            return match.group(1)

        # Try Nextflow pattern: taskName (index)
        match = cls.NEXTFLOW_PATTERN.match(task_name)
        if match:
            return match.group(1)

        # Try CWL pattern: taskName_<index>
        match = cls.CWL_PATTERN.match(task_name)
        if match:
            return match.group(1)

        # No pattern matched, return original name
        return task_name

    def aggregate_tasks(self, tasks: list[dict]) -> pl.DataFrame:
        """Aggregate metrics by normalized task name using Polars.

        Groups tasks by their normalized base name and calculates aggregate
        metrics including count, runtime statistics, utilization ratios, and costs.

        Args:
            tasks: List of task dictionaries with metrics. Expected keys:
                - taskName: Task name (required)
                - runningSeconds: Task running time in seconds
                - cpuEfficiencyRatio: CPU utilization ratio (0.0 to 1.0+)
                - memoryEfficiencyRatio: Memory utilization ratio (0.0 to 1.0+)
                - maxCpuUtilization: Maximum observed CPU usage
                - maxMemoryUtilizationGiB: Maximum observed memory usage in GiB
                - estimatedUSD: Estimated cost in USD

        Returns:
            Polars DataFrame with aggregated metrics per base task name.
            Columns include:
                - baseTaskName: Normalized task name
                - count: Number of task instances
                - meanRunningSeconds: Average runtime
                - maximumRunningSeconds: Maximum runtime
                - stdDevRunningSeconds: Standard deviation of runtime
                - maximumCpuUtilizationRatio: Maximum CPU utilization ratio
                - meanCpuUtilizationRatio: Average CPU utilization ratio
                - maximumMemoryUtilizationRatio: Maximum memory utilization ratio
                - meanMemoryUtilizationRatio: Average memory utilization ratio
                - maxObservedCpus: Maximum observed CPU usage across all instances
                - maxObservedMemoryGiB: Maximum observed memory usage across all instances
                - maximumEstimatedUSD: Maximum cost among instances
                - meanEstimatedUSD: Average cost per instance
                - totalEstimatedUSD: Total cost for all instances
        """
        if not tasks:
            return pl.DataFrame()

        # Ensure all required columns have default values
        normalized_tasks = []
        for task in tasks:
            normalized_task = {
                'taskName': task.get('taskName', ''),
                'runningSeconds': task.get('runningSeconds', 0.0),
                'cpuEfficiencyRatio': task.get('cpuEfficiencyRatio', 0.0),
                'memoryEfficiencyRatio': task.get('memoryEfficiencyRatio', 0.0),
                'maxCpuUtilization': task.get('maxCpuUtilization', 0.0),
                'maxMemoryUtilizationGiB': task.get('maxMemoryUtilizationGiB', 0.0),
                'estimatedUSD': task.get('estimatedUSD', 0.0),
            }
            normalized_tasks.append(normalized_task)

        # Convert to Polars DataFrame
        df = pl.DataFrame(normalized_tasks)

        # Add normalized task name column
        df = df.with_columns(
            pl.col('taskName')
            .map_elements(self.normalize_task_name, return_dtype=pl.Utf8)
            .alias('baseTaskName')
        )

        # Aggregate by base task name
        aggregated = df.group_by('baseTaskName').agg(
            [
                pl.len().alias('count'),
                pl.col('runningSeconds').mean().alias('meanRunningSeconds'),
                pl.col('runningSeconds').max().alias('maximumRunningSeconds'),
                pl.col('runningSeconds').std().alias('stdDevRunningSeconds'),
                pl.col('cpuEfficiencyRatio').max().alias('maximumCpuUtilizationRatio'),
                pl.col('cpuEfficiencyRatio').mean().alias('meanCpuUtilizationRatio'),
                pl.col('memoryEfficiencyRatio').max().alias('maximumMemoryUtilizationRatio'),
                pl.col('memoryEfficiencyRatio').mean().alias('meanMemoryUtilizationRatio'),
                pl.col('maxCpuUtilization').max().alias('maxObservedCpus'),
                pl.col('maxMemoryUtilizationGiB').max().alias('maxObservedMemoryGiB'),
                pl.col('estimatedUSD').max().alias('maximumEstimatedUSD'),
                pl.col('estimatedUSD').mean().alias('meanEstimatedUSD'),
                pl.col('estimatedUSD').sum().alias('totalEstimatedUSD'),
            ]
        )

        return aggregated
