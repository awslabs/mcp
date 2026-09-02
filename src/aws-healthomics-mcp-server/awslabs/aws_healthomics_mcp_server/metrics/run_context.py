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

"""Run and task resolution for vended-metrics queries.

Every metrics query is scoped by the run's actual execution window and task
map. This module resolves a run (GetRun + ListRunTasks) into the context the
metrics tools need: storage configuration (which drives metric presence),
GPU usage, the task name -> id map, and a buffered query window.
"""

from awslabs.aws_healthomics_mcp_server.metrics import schema
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_omics_client
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional


# Buffer applied around run/task start-stop when querying metrics. The leading
# buffer catches datapoints stamped just before the recorded start; the
# trailing buffer covers ingestion lag (~2 min nominal) for recently finished
# or still-running work.
WINDOW_START_BUFFER = timedelta(minutes=5)
WINDOW_END_BUFFER = timedelta(minutes=5)

RUN_ACTIVE_STATUSES = {'PENDING', 'STARTING', 'RUNNING', 'STOPPING'}


@dataclass(frozen=True)
class TaskContext:
    """A run task's identity, requested resources, and execution window."""

    task_id: str
    name: str
    status: str
    cpus: Optional[int] = None
    memory_gib: Optional[int] = None
    gpus: Optional[int] = None
    instance_type: Optional[str] = None
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None

    @property
    def requests_gpu(self) -> bool:
        """Whether the task requested accelerators."""
        return bool(self.gpus)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Wall-clock duration, if the task has both start and stop times."""
        if self.start_time and self.stop_time:
            return (self.stop_time - self.start_time).total_seconds()
        return None


@dataclass(frozen=True)
class RunContext:
    """Everything the metrics tools need to know about a run."""

    run_id: str
    workflow_id: Optional[str]
    status: str
    storage_type: Optional[str]
    scratch_mode: Optional[str]
    start_time: Optional[datetime]
    stop_time: Optional[datetime]
    tasks: List[TaskContext]

    @property
    def is_active(self) -> bool:
        """Whether the run is still executing (metrics may still be arriving)."""
        return self.status in RUN_ACTIVE_STATUSES

    @property
    def has_gpu_tasks(self) -> bool:
        """Whether any task in the run requested accelerators."""
        return any(t.requests_gpu for t in self.tasks)

    @property
    def task_by_id(self) -> Dict[str, TaskContext]:
        """Task id -> task."""
        return {t.task_id: t for t in self.tasks}

    @property
    def task_ids_by_name(self) -> Dict[str, List[str]]:
        """Task name -> task ids (scattered tasks share a name)."""
        result: Dict[str, List[str]] = {}
        for task in self.tasks:
            result.setdefault(task.name, []).append(task.task_id)
        return result

    def query_window(self, now: Optional[datetime] = None) -> tuple[datetime, datetime]:
        """The buffered [start, end] window for metrics queries on this run.

        Starts at the run start (minus buffer; falls back to the earliest task
        start). Ends at the run stop (plus buffer), or now for active runs.
        """
        now = now or datetime.now(timezone.utc)

        start = self.start_time
        if start is None:
            task_starts = [t.start_time for t in self.tasks if t.start_time]
            start = min(task_starts) if task_starts else now - timedelta(hours=1)

        end = self.stop_time if (self.stop_time and not self.is_active) else now

        return (start - WINDOW_START_BUFFER, min(end + WINDOW_END_BUFFER, now))

    @property
    def presence(self) -> schema.MetricPresence:
        """Expected metric presence for this run's configuration."""
        return schema.presence_for(
            storage_type=self.storage_type,
            scratch_mode=self.scratch_mode,
            has_gpu_tasks=self.has_gpu_tasks,
        )


def _to_task_context(task: Dict) -> TaskContext:
    """Map a ListRunTasks/GetRunTask item to a TaskContext."""
    return TaskContext(
        task_id=task.get('taskId', ''),
        name=task.get('name', ''),
        status=task.get('status', ''),
        cpus=task.get('cpus'),
        memory_gib=task.get('memory'),
        gpus=task.get('gpus'),
        instance_type=task.get('instanceType'),
        start_time=task.get('startTime'),
        stop_time=task.get('stopTime'),
    )


def resolve_run(run_id: str, region: Optional[str] = None) -> RunContext:
    """Resolve a run into the context needed for metrics queries.

    Calls GetRun and paginates ListRunTasks with the caller's credentials.

    Args:
        run_id: HealthOmics run id.
        region: Optional region override.

    Returns:
        The resolved RunContext.
    """
    client = get_omics_client(region_name=region)

    run = client.get_run(id=run_id)

    tasks: List[TaskContext] = []
    next_token: Optional[str] = None
    while True:
        kwargs = {'id': run_id, 'maxResults': 100}
        if next_token:
            kwargs['startingToken'] = next_token
        response = client.list_run_tasks(**kwargs)
        tasks.extend(_to_task_context(item) for item in response.get('items', []))
        next_token = response.get('nextToken')
        if not next_token:
            break

    return RunContext(
        run_id=run_id,
        workflow_id=run.get('workflowId'),
        status=run.get('status', ''),
        storage_type=run.get('storageType'),
        scratch_mode=run.get('scratchStorageMode'),
        start_time=run.get('startTime'),
        stop_time=run.get('stopTime'),
        tasks=tasks,
    )
