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

"""Tests for the vended-metrics MCP tools."""

import pytest
from awslabs.aws_healthomics_mcp_server.metrics.client import SeriesSummary, TimeSeries
from awslabs.aws_healthomics_mcp_server.metrics.run_context import RunContext, TaskContext
from awslabs.aws_healthomics_mcp_server.tools import run_metrics
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch


START = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)


def _task(task_id, name, duration_hours=1.0, gpus=None):
    return TaskContext(
        task_id=task_id,
        name=name,
        status='COMPLETED',
        cpus=4,
        memory_gib=16,
        gpus=gpus,
        start_time=START,
        stop_time=START + timedelta(hours=duration_hours),
    )


def _run(run_id, tasks, storage_type='STATIC', scratch_mode='LOCAL', duration_hours=2.0):
    return RunContext(
        run_id=run_id,
        workflow_id='wf1',
        status='COMPLETED',
        storage_type=storage_type,
        scratch_mode=scratch_mode,
        start_time=START,
        stop_time=START + timedelta(hours=duration_hours),
        tasks=tasks,
    )


def _summary(maximum, is_counter=False):
    if is_counter:
        return SeriesSummary(
            labels={}, datapoint_count=10, total_delta=maximum, average_rate=maximum / 100
        )
    return SeriesSummary(
        labels={},
        datapoint_count=10,
        minimum=0.0,
        maximum=maximum,
        average=maximum / 2,
        last=maximum,
    )


class TestCompareTaskMetrics:
    """Cross-run task alignment and metric deltas."""

    def test_aligns_by_task_name_and_ranks_by_duration_delta(self):
        run_a = _run('1', [_task('a1', 'align', 1.0), _task('a2', 'sort', 0.5)])
        run_b = _run('2', [_task('b1', 'align', 3.0), _task('b2', 'sort', 0.5)])
        metrics_a = {'aws.omics.task.cpu.usage': {'a1': _summary(4.0), 'a2': _summary(1.0)}}
        metrics_b = {'aws.omics.task.cpu.usage': {'b1': _summary(1.0), 'b2': _summary(1.0)}}

        result = run_metrics.compare_task_metrics(run_a, run_b, metrics_a, metrics_b)

        assert result[0]['task_name'] == 'align'
        assert result[0]['duration_delta_seconds'] == 7200.0
        delta = result[0]['metric_deltas'][0]
        assert delta['metric'] == 'aws.omics.task.cpu.usage'
        assert delta['run_a'] == 4.0
        assert delta['run_b'] == 1.0
        assert delta['relative_delta'] == pytest.approx(-0.75)

    def test_task_only_in_one_run_is_flagged(self):
        run_a = _run('1', [_task('a1', 'align')])
        run_b = _run('2', [_task('b1', 'align'), _task('b2', 'extra')])
        result = run_metrics.compare_task_metrics(run_a, run_b, {}, {})
        extra = next(r for r in result if r['task_name'] == 'extra')
        assert extra['note'] == 'Task only present in run B'

    def test_scattered_tasks_use_peak_across_shards(self):
        run_a = _run('1', [_task('a1', 'align'), _task('a2', 'align')])
        run_b = _run('2', [_task('b1', 'align')])
        metrics_a = {'aws.omics.task.cpu.usage': {'a1': _summary(2.0), 'a2': _summary(8.0)}}
        metrics_b = {'aws.omics.task.cpu.usage': {'b1': _summary(8.0)}}
        result = run_metrics.compare_task_metrics(run_a, run_b, metrics_a, metrics_b)
        delta = result[0]['metric_deltas'][0]
        assert delta['run_a'] == 8.0
        assert delta['relative_delta'] == 0.0


class TestAggregateWorkflowMetrics:
    """Per-task-name distributions across runs."""

    def test_distributions_across_runs(self):
        runs = [
            _run('1', [_task('t1', 'align', 1.0)]),
            _run('2', [_task('t2', 'align', 2.0)]),
            _run('3', [_task('t3', 'align', 3.0)]),
        ]
        summaries = {
            '1': {'aws.omics.task.memory.usage': {'t1': _summary(10.0)}},
            '2': {'aws.omics.task.memory.usage': {'t2': _summary(20.0)}},
            '3': {'aws.omics.task.memory.usage': {'t3': _summary(30.0)}},
        }
        result = run_metrics.aggregate_workflow_metrics(runs, summaries)

        assert result['runs_aggregated'] == 3
        align = result['task_distributions'][0]
        assert align['task_name'] == 'align'
        assert align['duration_seconds']['max'] == 3 * 3600
        assert align['duration_seconds']['samples'] == 3
        mem = align['metrics']['aws.omics.task.memory.usage']
        assert mem['max'] == 30.0
        assert mem['p50'] == 20.0

    def test_variance_flag_present_with_multiple_samples(self):
        runs = [
            _run('1', [_task('t1', 'align', 1.0)]),
            _run('2', [_task('t2', 'align', 5.0)]),
        ]
        result = run_metrics.aggregate_workflow_metrics(runs, {'1': {}, '2': {}})
        cv = result['task_distributions'][0]['duration_seconds']['coefficient_of_variation']
        assert cv > 0.5


class TestHelpers:
    """Small pure helpers in the tools module."""

    def test_parse_time_accepts_z_suffix(self):
        parsed = run_metrics._parse_time('2026-08-01T12:00:00Z', 'start_time')
        assert parsed == START

    def test_parse_time_rejects_garbage(self):
        with pytest.raises(ValueError, match='start_time'):
            run_metrics._parse_time('yesterday', 'start_time')

    def test_downsample_caps_points(self):
        series = TimeSeries(
            labels={},
            timestamps=[float(i) for i in range(1000)],
            values=[float(i) for i in range(1000)],
        )
        points = run_metrics._downsample(series, max_points=100)
        assert len(points) == 100
        assert points[0] == [0.0, 0.0]

    def test_percentile_nearest_rank(self):
        assert run_metrics._percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 3.0
        assert run_metrics._percentile([5.0], 0.9) == 5.0


def _mock_ctx():
    ctx = MagicMock()
    ctx.error = AsyncMock()
    return ctx


@pytest.mark.asyncio
class TestListRunMetricsTool:
    """ListAHORunMetrics availability reporting."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.resolve_run')
    async def test_reports_available_and_missing(self, mock_resolve, mock_client_cls):
        mock_resolve.return_value = _run('123', [_task('t1', 'align')])
        client = mock_client_cls.return_value
        client.series.return_value = [
            {'__name__': 'aws.omics.task.cpu.usage', '@resource.aws.omics.task.id': 't1'},
        ]

        result = await run_metrics.list_run_metrics(_mock_ctx(), run_id='123')

        assert result['vended_metrics_found'] is True
        available = {m['metric'] for m in result['available_metrics']}
        assert available == {'aws.omics.task.cpu.usage'}
        missing = {m['metric'] for m in result['missing_metrics']}
        # GPU metrics absent-with-reason (no GPU tasks); others unexpectedly absent
        assert 'aws.omics.task.gpu.utilization' in missing
        assert 'aws.omics.task.memory.usage' in missing

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.resolve_run')
    async def test_no_series_flags_feature_absent(self, mock_resolve, mock_client_cls):
        mock_resolve.return_value = _run('123', [_task('t1', 'align')])
        mock_client_cls.return_value.series.return_value = []

        result = await run_metrics.list_run_metrics(_mock_ctx(), run_id='123')

        assert result['vended_metrics_found'] is False
        assert 'note' in result

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.resolve_run')
    async def test_error_is_returned_not_raised(self, mock_resolve):
        mock_resolve.side_effect = RuntimeError('boom')
        ctx = _mock_ctx()
        result = await run_metrics.list_run_metrics(ctx, run_id='123')
        assert 'boom' in result['error']
        ctx.error.assert_awaited()


@pytest.mark.asyncio
class TestGetRunMetricsTool:
    """GetAHORunMetrics retrieval and validation."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.resolve_run')
    async def test_returns_series_with_task_names(self, mock_resolve, mock_client_cls):
        mock_resolve.return_value = _run('123', [_task('t1', 'align')])
        client = mock_client_cls.return_value

        def fake_query(selector, start, end, step=None):
            if 'cpu.usage' in selector:
                return [
                    TimeSeries(
                        labels={'@resource.aws.omics.task.id': 't1'},
                        timestamps=[1000.0, 1060.0],
                        values=[1.0, 3.0],
                    )
                ]
            return []

        client.query_range.side_effect = fake_query

        result = await run_metrics.get_run_metrics(
            _mock_ctx(),
            run_id='123',
            metric_names=['aws.omics.task.cpu.usage', 'aws.omics.task.memory.usage'],
        )

        assert len(result['metrics']) == 1
        metric = result['metrics'][0]
        assert metric['metric'] == 'aws.omics.task.cpu.usage'
        series = metric['series'][0]
        assert series['task_name'] == 'align'
        assert series['summary']['maximum'] == 3.0
        assert series['values'] == [[1000.0, 1.0], [1060.0, 3.0]]
        assert result['missing_metrics'][0]['metric'] == 'aws.omics.task.memory.usage'

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.resolve_run')
    async def test_invalid_metric_name_errors_with_valid_names(
        self, mock_resolve, mock_client_cls
    ):
        mock_resolve.return_value = _run('123', [_task('t1', 'align')])
        result = await run_metrics.get_run_metrics(
            _mock_ctx(), run_id='123', metric_names=['bogus.metric']
        )
        assert 'Unknown vended metric' in result['error']
        assert 'aws.omics.task.cpu.usage' in result['error']

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.resolve_run')
    async def test_direction_filter_applied_to_io_metrics(self, mock_resolve, mock_client_cls):
        mock_resolve.return_value = _run('123', [_task('t1', 'align')])
        client = mock_client_cls.return_value
        client.query_range.return_value = []

        await run_metrics.get_run_metrics(
            _mock_ctx(),
            run_id='123',
            metric_names=['aws.omics.task.filesystem.io'],
            direction='read',
        )

        selector = client.query_range.call_args.args[0]
        assert '"filesystem.io.direction"="read"' in selector


@pytest.mark.asyncio
class TestGetWorkflowMetricsTool:
    """GetAHOWorkflowMetrics run selection and aggregation."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.resolve_run')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.get_omics_client')
    async def test_filters_runs_by_workflow(self, mock_omics, mock_resolve, mock_client_cls):
        mock_omics.return_value.list_runs.return_value = {
            'items': [
                {'id': '1', 'workflowId': 'wf1'},
                {'id': '2', 'workflowId': 'other'},
                {'id': '3', 'workflowId': 'wf1'},
            ]
        }
        mock_resolve.side_effect = lambda run_id, region=None: _run(
            run_id, [_task(f't{run_id}', 'align')]
        )
        mock_client_cls.return_value.query_range.return_value = []

        result = await run_metrics.get_workflow_metrics(_mock_ctx(), workflow_id='wf1', max_runs=5)

        assert result['run_ids'] == ['1', '3']
        assert result['runs_aggregated'] == 2
        assert result['runs_without_vended_metrics'] == ['1', '3']

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.get_omics_client')
    async def test_no_runs_found(self, mock_omics):
        mock_omics.return_value.list_runs.return_value = {'items': []}
        result = await run_metrics.get_workflow_metrics(_mock_ctx(), workflow_id='wf1')
        assert result['runs_aggregated'] == 0


@pytest.mark.asyncio
class TestUnsupportedRegionGating:
    """All metrics tools short-circuit with an explanation in il-central-1."""

    def _client_in(self, mock_client_cls, region):
        client = mock_client_cls.return_value
        type(client).region = region
        return client

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.resolve_run')
    async def test_list_run_metrics(self, mock_resolve, mock_client_cls):
        mock_resolve.return_value = _run('123', [_task('t1', 'align')])
        client = self._client_in(mock_client_cls, 'il-central-1')

        result = await run_metrics.list_run_metrics(_mock_ctx(), run_id='123')

        assert result['vended_metrics_supported'] is False
        assert result['vended_metrics_found'] is False
        assert 'il-central-1' in result['note']
        client.series.assert_not_called()

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.resolve_run')
    async def test_get_run_metrics(self, mock_resolve, mock_client_cls):
        mock_resolve.return_value = _run('123', [_task('t1', 'align')])
        client = self._client_in(mock_client_cls, 'il-central-1')

        result = await run_metrics.get_run_metrics(
            _mock_ctx(), run_id='123', metric_names=['aws.omics.task.cpu.usage']
        )

        assert result['vended_metrics_supported'] is False
        assert result['metrics'] == []
        assert result['missing_metrics'][0]['metric'] == 'aws.omics.task.cpu.usage'
        assert 'il-central-1' in result['missing_metrics'][0]['reason']
        client.query_range.assert_not_called()

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.resolve_run')
    async def test_compare_run_metrics(self, mock_resolve, mock_client_cls):
        mock_resolve.side_effect = lambda run_id, region=None: _run(
            run_id, [_task(f't{run_id}', 'align')]
        )
        client = self._client_in(mock_client_cls, 'il-central-1')

        result = await run_metrics.compare_run_metrics(_mock_ctx(), run_id_a='1', run_id_b='2')

        assert result['vended_metrics_supported'] is False
        assert result['task_comparisons'] == []
        client.query_range.assert_not_called()

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.resolve_run')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.get_omics_client')
    async def test_get_workflow_metrics(self, mock_omics, mock_resolve, mock_client_cls):
        mock_omics.return_value.list_runs.return_value = {
            'items': [{'id': '1', 'workflowId': 'wf1'}]
        }
        client = self._client_in(mock_client_cls, 'il-central-1')

        result = await run_metrics.get_workflow_metrics(_mock_ctx(), workflow_id='wf1')

        assert result['vended_metrics_supported'] is False
        assert result['runs_aggregated'] == 0
        assert 'il-central-1' in result['note']
        client.query_range.assert_not_called()

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.resolve_run')
    async def test_supported_region_proceeds(self, mock_resolve, mock_client_cls):
        mock_resolve.return_value = _run('123', [_task('t1', 'align')])
        client = self._client_in(mock_client_cls, 'us-west-2')
        client.series.return_value = []

        result = await run_metrics.list_run_metrics(_mock_ctx(), run_id='123')

        assert 'vended_metrics_supported' not in result
        client.series.assert_called_once()


@pytest.mark.asyncio
class TestLimitationSurfacing:
    """Launch-date, short-task, and scratch-cadence limitations in tool output."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.resolve_run')
    async def test_pre_launch_run_gets_launch_date_reason(self, mock_resolve, mock_client_cls):
        pre_launch = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
        run = _run('123', [_task('t1', 'align')])
        object.__setattr__(run, 'start_time', pre_launch)
        object.__setattr__(run, 'stop_time', pre_launch + timedelta(hours=2))
        mock_resolve.return_value = run
        client = mock_client_cls.return_value
        type(client).region = 'us-west-2'
        client.series.return_value = []

        result = await run_metrics.list_run_metrics(_mock_ctx(), run_id='123')

        assert '2026-09-07' in result['note']
        assert all(
            '2026-09-07' in m['reason']
            for m in result['missing_metrics']
            if 'Expected' in m['reason']
        )

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.resolve_run')
    async def test_short_task_caveat_listed(self, mock_resolve, mock_client_cls):
        short = _task('t1', 'quick', duration_hours=30 / 3600)  # 30 seconds
        mock_resolve.return_value = _run('123', [short, _task('t2', 'align')])
        client = mock_client_cls.return_value
        type(client).region = 'us-west-2'
        client.series.return_value = [
            {'__name__': 'aws.omics.task.cpu.usage', '@resource.aws.omics.task.id': 't2'},
        ]

        result = await run_metrics.list_run_metrics(_mock_ctx(), run_id='123')

        assert any('shorter than 60s' in c for c in result['caveats'])

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.resolve_run')
    async def test_scratch_cadence_caveat_and_interval(self, mock_resolve, mock_client_cls):
        mock_resolve.return_value = _run('123', [_task('t1', 'align')])
        client = mock_client_cls.return_value
        type(client).region = 'us-west-2'
        client.series.return_value = [
            {
                '__name__': 'aws.omics.task.filesystem.scratch.storage.usage',
                '@resource.aws.omics.task.id': 't1',
            },
        ]

        result = await run_metrics.list_run_metrics(_mock_ctx(), run_id='123')

        scratch = next(
            m
            for m in result['available_metrics']
            if m['metric'] == 'aws.omics.task.filesystem.scratch.storage.usage'
        )
        assert scratch['sampling_interval_seconds'] == 1200
        assert any('20 minutes' in c for c in result['caveats'])

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.resolve_run')
    async def test_short_task_reason_on_get_run_metrics(self, mock_resolve, mock_client_cls):
        short = _task('t1', 'quick', duration_hours=20 / 3600)  # 20 seconds
        run = _run('123', [short])
        # place the run after the production launch so the short-task reason applies
        post_launch = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
        object.__setattr__(run, 'start_time', post_launch)
        object.__setattr__(run, 'stop_time', post_launch + timedelta(hours=1))
        mock_resolve.return_value = run
        client = mock_client_cls.return_value
        type(client).region = 'us-west-2'
        client.query_range.return_value = []

        result = await run_metrics.get_run_metrics(
            _mock_ctx(),
            run_id='123',
            metric_names=['aws.omics.task.cpu.usage'],
            task_id='t1',
        )

        assert 'shorter than the 60s minimum' in result['missing_metrics'][0]['reason']

    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.VendedMetricsClient')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_metrics.resolve_run')
    async def test_get_run_metrics_reports_scratch_sampling_interval(
        self, mock_resolve, mock_client_cls
    ):
        mock_resolve.return_value = _run('123', [_task('t1', 'align')])
        client = mock_client_cls.return_value
        type(client).region = 'us-west-2'
        client.query_range.return_value = [
            TimeSeries(
                labels={'@resource.aws.omics.task.id': 't1'},
                timestamps=[0.0, 1200.0],
                values=[1.0, 2.0],
            )
        ]

        result = await run_metrics.get_run_metrics(
            _mock_ctx(),
            run_id='123',
            metric_names=['aws.omics.task.filesystem.scratch.storage.usage'],
        )

        assert result['metrics'][0]['sampling_interval_seconds'] == 1200
