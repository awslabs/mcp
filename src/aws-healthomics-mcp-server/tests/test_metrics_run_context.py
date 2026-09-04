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

"""Tests for run/task resolution for vended-metrics queries."""

from awslabs.aws_healthomics_mcp_server.metrics.run_context import (
    WINDOW_END_BUFFER,
    WINDOW_START_BUFFER,
    RunContext,
    TaskContext,
    resolve_run,
)
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch


START = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
STOP = START + timedelta(hours=2)
NOW = STOP + timedelta(hours=1)


def _task(task_id='t1', name='align', gpus=None, start=START, stop=STOP):
    return TaskContext(
        task_id=task_id,
        name=name,
        status='COMPLETED',
        cpus=4,
        memory_gib=16,
        gpus=gpus,
        start_time=start,
        stop_time=stop,
    )


def _run(status='COMPLETED', tasks=None, start=START, stop=STOP, **kwargs):
    return RunContext(
        run_id='123',
        workflow_id='wf1',
        status=status,
        storage_type=kwargs.get('storage_type', 'STATIC'),
        scratch_mode=kwargs.get('scratch_mode', 'LOCAL'),
        start_time=start,
        stop_time=stop,
        tasks=tasks if tasks is not None else [_task()],
    )


class TestRunContext:
    """RunContext derived properties and query window."""

    def test_query_window_buffers_completed_run(self):
        start, end = _run().query_window(now=NOW)
        assert start == START - WINDOW_START_BUFFER
        assert end == STOP + WINDOW_END_BUFFER

    def test_query_window_active_run_ends_now(self):
        run = _run(status='RUNNING', stop=None)
        start, end = run.query_window(now=NOW)
        assert end == NOW

    def test_query_window_never_exceeds_now(self):
        """A run that just stopped doesn't produce a window in the future."""
        just_now = STOP + timedelta(seconds=10)
        _, end = _run().query_window(now=just_now)
        assert end == just_now

    def test_query_window_falls_back_to_task_starts(self):
        run = _run(start=None)
        start, _ = run.query_window(now=NOW)
        assert start == START - WINDOW_START_BUFFER

    def test_has_gpu_tasks(self):
        assert not _run().has_gpu_tasks
        assert _run(tasks=[_task(gpus=1)]).has_gpu_tasks

    def test_task_ids_by_name_groups_scattered_tasks(self):
        run = _run(tasks=[_task('t1', 'align'), _task('t2', 'align'), _task('t3', 'sort')])
        assert run.task_ids_by_name == {'align': ['t1', 't2'], 'sort': ['t3']}

    def test_presence_uses_run_configuration(self):
        run = _run(scratch_mode='SHARED')
        missing = {m.name for m in run.presence.missing}
        assert 'aws.omics.task.filesystem.scratch.storage.limit' in missing

    def test_task_duration(self):
        assert _task().duration_seconds == 7200.0
        assert _task(stop=None).duration_seconds is None


class TestResolveRun:
    """GetRun/ListRunTasks resolution and pagination."""

    @patch('awslabs.aws_healthomics_mcp_server.metrics.run_context.get_omics_client')
    def test_resolves_run_and_paginates_tasks(self, mock_client_factory):
        client = MagicMock()
        mock_client_factory.return_value = client
        client.get_run.return_value = {
            'workflowId': 'wf1',
            'status': 'COMPLETED',
            'storageType': 'DYNAMIC',
            'scratchStorageMode': 'SHARED',
            'startTime': START,
            'stopTime': STOP,
        }
        client.list_run_tasks.side_effect = [
            {
                'items': [
                    {
                        'taskId': 't1',
                        'name': 'align',
                        'status': 'COMPLETED',
                        'cpus': 4,
                        'memory': 16,
                        'gpus': 1,
                        'startTime': START,
                        'stopTime': STOP,
                    }
                ],
                'nextToken': 'page2',
            },
            {'items': [{'taskId': 't2', 'name': 'sort', 'status': 'COMPLETED'}]},
        ]

        run = resolve_run('123')

        assert run.storage_type == 'DYNAMIC'
        assert run.scratch_mode == 'SHARED'
        assert [t.task_id for t in run.tasks] == ['t1', 't2']
        assert run.has_gpu_tasks
        # pagination used the returned token
        assert client.list_run_tasks.call_args_list[1].kwargs['startingToken'] == 'page2'
