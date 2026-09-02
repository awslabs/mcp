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

"""Tests for the vended-metrics analysis pass (classification, right-sizing, stuck runs)."""

from awslabs.aws_healthomics_mcp_server.metrics import analysis
from awslabs.aws_healthomics_mcp_server.metrics.analysis import (
    GIB,
    TaskSignature,
    analyze_run_metrics,
    build_task_signature,
    classify_signature,
    detect_stuck_tasks,
    format_metrics_report_section,
    metrics_section_for_report,
    right_size,
)
from awslabs.aws_healthomics_mcp_server.metrics.client import SeriesSummary
from awslabs.aws_healthomics_mcp_server.metrics.run_context import RunContext, TaskContext
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch


START = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)


def _task(task_id='t1', name='align', cpus=4, memory=16, gpus=None, status='COMPLETED'):
    return TaskContext(
        task_id=task_id,
        name=name,
        status=status,
        cpus=cpus,
        memory_gib=memory,
        gpus=gpus,
        start_time=START,
        stop_time=START + timedelta(hours=1) if status == 'COMPLETED' else None,
    )


def _run(tasks, status='COMPLETED', storage_type='STATIC', scratch_mode='LOCAL'):
    return RunContext(
        run_id='123',
        workflow_id='wf1',
        status=status,
        storage_type=storage_type,
        scratch_mode=scratch_mode,
        start_time=START,
        stop_time=START + timedelta(hours=2) if status == 'COMPLETED' else None,
        tasks=tasks,
    )


def _summary(maximum=None, average=None, total_delta=None, average_rate=None, count=10):
    return SeriesSummary(
        labels={},
        datapoint_count=count,
        minimum=0.0 if maximum is not None else None,
        maximum=maximum,
        average=average if average is not None else maximum,
        last=maximum,
        total_delta=total_delta,
        average_rate=average_rate,
    )


class TestClassifySignature:
    """Threshold-based bottleneck categories."""

    def _sig(self, **kwargs):
        return TaskSignature(task_id='t1', task_name='align', **kwargs)

    def test_cpu_bound(self):
        sig = self._sig(cpu_average=3.8, cpu_limit=4.0)
        assert classify_signature(sig) == ['CPU_BOUND']

    def test_memory_pressure(self):
        sig = self._sig(memory_peak_bytes=15.5 * GIB, memory_limit_bytes=16 * GIB)
        assert 'MEMORY_PRESSURE' in classify_signature(sig)

    def test_io_bound_low_cpu_high_io(self):
        sig = self._sig(
            cpu_average=0.5, cpu_limit=4.0, filesystem_rate_bytes_per_second=50_000_000
        )
        assert classify_signature(sig) == ['IO_BOUND']

    def test_gpu_idle(self):
        sig = self._sig(cpu_average=2.0, cpu_limit=4.0, gpu_peak_percent=3.0)
        assert 'GPU_IDLE' in classify_signature(sig)

    def test_scratch_near_limit(self):
        sig = self._sig(scratch_peak_bytes=90 * GIB, scratch_limit_bytes=100 * GIB)
        assert 'SCRATCH_NEAR_LIMIT' in classify_signature(sig)

    def test_over_provisioned(self):
        sig = self._sig(
            cpu_average=0.2,
            cpu_limit=4.0,
            memory_peak_bytes=1 * GIB,
            memory_limit_bytes=16 * GIB,
        )
        assert classify_signature(sig) == ['OVER_PROVISIONED']

    def test_balanced_default(self):
        sig = self._sig(cpu_average=2.0, cpu_limit=4.0)
        assert classify_signature(sig) == ['BALANCED']

    def test_no_data_is_balanced(self):
        assert classify_signature(self._sig()) == ['BALANCED']


class TestBuildTaskSignature:
    """Signature assembly from metric summaries."""

    def test_populates_all_dimensions(self):
        summaries = {
            'aws.omics.task.cpu.usage': {'t1': _summary(maximum=3.5, average=3.0)},
            'aws.omics.task.cpu.limit': {'t1': _summary(maximum=4.0)},
            'aws.omics.task.memory.usage': {'t1': _summary(maximum=8 * GIB)},
            'aws.omics.task.memory.limit': {'t1': _summary(maximum=16 * GIB)},
            'aws.omics.task.gpu.utilization': {'t1': _summary(maximum=85.0)},
            'aws.omics.task.filesystem.io': {'t1': _summary(average_rate=1_000_000.0)},
            'aws.omics.task.network.io': {'t1': _summary(average_rate=2_000_000.0)},
            'aws.omics.task.filesystem.scratch.storage.usage': {'t1': _summary(maximum=GIB)},
            'aws.omics.task.filesystem.scratch.storage.limit': {'t1': _summary(maximum=10 * GIB)},
        }
        sig = build_task_signature(_task(), summaries)
        assert sig.cpu_peak == 3.5
        assert sig.cpu_utilization == 0.75
        assert sig.memory_utilization == 0.5
        assert sig.gpu_peak_percent == 85.0
        assert sig.filesystem_rate_bytes_per_second == 1_000_000.0
        assert sig.network_rate_bytes_per_second == 2_000_000.0
        assert sig.scratch_utilization == 0.1
        assert sig.categories  # classified

    def test_missing_metrics_leave_none(self):
        sig = build_task_signature(_task(), {})
        assert sig.cpu_peak is None
        assert sig.cpu_utilization is None
        assert sig.categories == ['BALANCED']


class TestRightSize:
    """Observed-peak right-sizing suggestions."""

    def test_suggests_reduction_when_peak_below_request(self):
        run = _run([_task('t1', 'align', cpus=8, memory=32)])
        sig = TaskSignature(
            task_id='t1',
            task_name='align',
            cpu_peak=1.4,
            memory_peak_bytes=2 * GIB,
        )
        suggestions = right_size(run, [sig], headroom=0.2)
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s.recommended_cpus == 2  # ceil(1.4 * 1.2)
        assert s.current_cpus == 8
        assert s.recommended_memory_gib == 2.4
        assert s.current_memory_gib == 32

    def test_no_suggestion_when_already_tight(self):
        run = _run([_task('t1', 'align', cpus=2, memory=4)])
        sig = TaskSignature(
            task_id='t1', task_name='align', cpu_peak=1.9, memory_peak_bytes=3.9 * GIB
        )
        assert right_size(run, [sig], headroom=0.2) == []

    def test_scratch_suggestion_always_reported(self):
        run = _run([_task('t1', 'align')])
        sig = TaskSignature(task_id='t1', task_name='align', scratch_peak_bytes=50 * GIB)
        suggestions = right_size(run, [sig], headroom=0.2)
        assert suggestions[0].recommended_scratch_gib == 60.0

    def test_scattered_tasks_use_group_peak(self):
        run = _run([_task('t1', 'align', cpus=8), _task('t2', 'align', cpus=8)])
        sigs = [
            TaskSignature(task_id='t1', task_name='align', cpu_peak=1.0),
            TaskSignature(task_id='t2', task_name='align', cpu_peak=5.0),
        ]
        suggestions = right_size(run, sigs, headroom=0.0)
        assert suggestions[0].recommended_cpus == 5
        assert suggestions[0].task_count == 2


class TestDetectStuckTasks:
    """Stuck-run classification for active runs."""

    def _client_with(self, cpu=None, io=None, mem=None, mem_limit=None):
        from awslabs.aws_healthomics_mcp_server.metrics.client import TimeSeries

        def fake_query(selector, start, end, step=None):
            def series(values, task='t1'):
                return [
                    TimeSeries(
                        labels={'@resource.aws.omics.task.id': task},
                        timestamps=[float(i * 60) for i in range(len(values))],
                        values=values,
                    )
                ]

            if 'cpu.usage' in selector and cpu is not None:
                return series(cpu)
            if 'filesystem.io' in selector and io is not None:
                return series(io)
            if 'memory.usage' in selector and mem is not None:
                return series(mem)
            if 'memory.limit' in selector and mem_limit is not None:
                return series(mem_limit)
            return []

        client = MagicMock()
        client.query_range.side_effect = fake_query
        return client

    def test_progressing(self):
        run = _run([_task('t1', 'align', status='RUNNING')], status='RUNNING')
        client = self._client_with(cpu=[2.0, 2.1], io=[0.0, 5_000_000.0])
        verdicts = detect_stuck_tasks(client, run)
        assert verdicts[0]['verdict'] == 'PROGRESSING'

    def test_possibly_hung(self):
        run = _run([_task('t1', 'align', status='RUNNING')], status='RUNNING')
        client = self._client_with(cpu=[0.001, 0.002], io=[100.0, 100.0])
        verdicts = detect_stuck_tasks(client, run)
        assert verdicts[0]['verdict'] == 'POSSIBLY_HUNG'

    def test_memory_thrash_suspect(self):
        run = _run([_task('t1', 'align', cpus=4, memory=16, status='RUNNING')], status='RUNNING')
        client = self._client_with(
            cpu=[0.5, 0.6],
            io=[0.0, 50_000_000.0],
            mem=[15.5 * GIB, 15.8 * GIB],
            mem_limit=[16 * GIB, 16 * GIB],
        )
        verdicts = detect_stuck_tasks(client, run)
        assert verdicts[0]['verdict'] == 'MEMORY_THRASH_SUSPECT'

    def test_no_recent_data(self):
        run = _run([_task('t1', 'align', status='RUNNING')], status='RUNNING')
        client = self._client_with()
        verdicts = detect_stuck_tasks(client, run)
        assert verdicts[0]['verdict'] == 'NO_RECENT_DATA'

    def test_completed_run_returns_nothing(self):
        run = _run([_task('t1', 'align')])
        assert detect_stuck_tasks(MagicMock(), run) == []


class TestAnalyzeRunMetrics:
    """Orchestration and unavailable paths."""

    @patch('awslabs.aws_healthomics_mcp_server.metrics.analysis.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.metrics.analysis.resolve_run')
    def test_unsupported_region(self, mock_resolve, mock_client_cls):
        mock_resolve.return_value = _run([_task()])
        type(mock_client_cls.return_value).region = 'il-central-1'
        result = analyze_run_metrics('123')
        assert result['available'] is False
        assert 'il-central-1' in result['reason']

    @patch('awslabs.aws_healthomics_mcp_server.metrics.analysis.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.metrics.analysis.resolve_run')
    def test_no_metrics_found(self, mock_resolve, mock_client_cls):
        mock_resolve.return_value = _run([_task()])
        client = mock_client_cls.return_value
        type(client).region = 'us-west-2'
        client.query_range.return_value = []
        result = analyze_run_metrics('123')
        assert result['available'] is False
        assert 'manifest' in result['reason']

    @patch('awslabs.aws_healthomics_mcp_server.metrics.analysis.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.metrics.analysis.resolve_run')
    def test_full_analysis(self, mock_resolve, mock_client_cls):
        from awslabs.aws_healthomics_mcp_server.metrics.client import TimeSeries

        mock_resolve.return_value = _run([_task('t1', 'align', cpus=8, memory=32)])
        client = mock_client_cls.return_value
        type(client).region = 'us-west-2'

        def fake_query(selector, start, end, step=None):
            values = {
                'cpu.usage"': [0.5, 0.6],
                'cpu.limit"': [8.0, 8.0],
                'memory.usage"': [1 * GIB, 2 * GIB],
                'memory.limit"': [32 * GIB, 32 * GIB],
            }
            for key, vals in values.items():
                if key in selector:
                    return [
                        TimeSeries(
                            labels={'@resource.aws.omics.task.id': 't1'},
                            timestamps=[0.0, 60.0],
                            values=vals,
                        )
                    ]
            return []

        client.query_range.side_effect = fake_query
        result = analyze_run_metrics('123', headroom=0.2)

        assert result['available'] is True
        assert result['tasks_observed'] == 1
        assert result['category_counts'] == {'OVER_PROVISIONED': 1}
        assert result['right_sizing'][0].recommended_cpus == 1
        assert result['stuck_tasks'] == []


class TestReportFormatting:
    """Markdown section rendering and never-raise wrapper."""

    def test_unavailable_renders_reason(self):
        lines = format_metrics_report_section(
            {'run_id': '123', 'available': False, 'reason': 'because'}
        )
        assert any('because' in line for line in lines)

    def test_full_result_renders_sections(self):
        sig = TaskSignature(
            task_id='t1', task_name='align', cpu_average=0.2, cpu_peak=0.2, cpu_limit=8.0
        )
        sig.categories = ['OVER_PROVISIONED']
        result = {
            'run_id': '123',
            'available': True,
            'storage_type': 'STATIC',
            'scratch_mode': 'LOCAL',
            'tasks_observed': 1,
            'task_count': 1,
            'category_counts': {'OVER_PROVISIONED': 1},
            'signatures': [sig],
            'stuck_tasks': [],
            'right_sizing': [
                analysis.RightSizing(
                    task_name='align', task_count=1, recommended_cpus=1, current_cpus=8
                )
            ],
            'missing_metrics': [{'metric': 'aws.omics.task.gpu.utilization', 'reason': 'no GPU'}],
        }
        text = '\n'.join(format_metrics_report_section(result))
        assert 'Notable Task Signatures' in text
        assert 'Right-Sizing Suggestions' in text
        assert 'cpus 8 -> 1' in text
        assert 'gpu.utilization' in text

    @patch('awslabs.aws_healthomics_mcp_server.metrics.analysis.resolve_run')
    def test_section_never_raises(self, mock_resolve):
        mock_resolve.side_effect = RuntimeError('boom')
        lines = metrics_section_for_report('123')
        assert any('could not be analyzed' in line for line in lines)
