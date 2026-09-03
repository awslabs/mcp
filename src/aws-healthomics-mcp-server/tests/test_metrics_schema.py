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

"""Tests for the vended metrics schema."""

import pytest
from awslabs.aws_healthomics_mcp_server.metrics import schema


class TestSchemaContents:
    """The schema mirrors the registered vended-metrics contract."""

    def test_fourteen_metrics_total(self):
        """The contract defines exactly 14 metrics across 4 groups."""
        assert len(schema.ALL_METRICS) == 14
        assert len(schema.ALL_GROUPS) == 4

    def test_metric_names_are_unique(self):
        """No metric name appears in more than one group."""
        assert len(schema.ALL_METRIC_NAMES) == len(set(schema.ALL_METRIC_NAMES))

    def test_per_task_vs_per_run_split(self):
        """Only the run filesystem pair is per-run."""
        per_run = [m.name for m in schema.PER_RUN_STORAGE.metrics]
        assert per_run == [
            'aws.omics.run.filesystem.usage',
            'aws.omics.run.filesystem.limit',
        ]
        assert set(schema.PER_TASK_METRIC_NAMES) == set(schema.ALL_METRIC_NAMES) - set(per_run)

    def test_counters_are_the_io_sums(self):
        """network.io, filesystem.io and filesystem.operations are cumulative sums."""
        counters = {m.name for m in schema.ALL_METRICS if m.is_counter}
        assert counters == {
            'aws.omics.task.network.io',
            'aws.omics.task.filesystem.io',
            'aws.omics.task.filesystem.operations',
        }

    def test_gpu_metric_names(self):
        assert set(schema.GPU_METRIC_NAMES) == {
            'aws.omics.task.gpu.utilization',
            'aws.omics.task.gpu.memory.usage',
            'aws.omics.task.gpu.memory.limit',
        }

    def test_metric_of_unknown_name_lists_valid_names(self):
        with pytest.raises(ValueError, match='aws.omics.task.cpu.usage'):
            schema.metric_of('aws.omics.task.bogus')

    def test_is_per_task(self):
        assert schema.is_per_task('aws.omics.task.cpu.usage')
        assert not schema.is_per_task('aws.omics.run.filesystem.usage')


class TestPresenceFor:
    """Per-run-configuration presence rules."""

    def test_static_local_gpu_has_everything(self):
        presence = schema.presence_for('STATIC', 'LOCAL', has_gpu_tasks=True)
        assert set(presence.present) == set(schema.ALL_METRIC_NAMES)
        assert presence.missing == []

    def test_dynamic_omits_run_filesystem_limit(self):
        """DYNAMIC (EFS) has no fixed capacity, so no run filesystem limit."""
        presence = schema.presence_for('DYNAMIC', 'LOCAL', has_gpu_tasks=True)
        missing_names = {m.name for m in presence.missing}
        assert missing_names == {'aws.omics.run.filesystem.limit'}

    def test_shared_scratch_omits_scratch_limit(self):
        presence = schema.presence_for('STATIC', 'SHARED', has_gpu_tasks=True)
        missing_names = {m.name for m in presence.missing}
        assert missing_names == {'aws.omics.task.filesystem.scratch.storage.limit'}

    def test_no_gpu_omits_gpu_metrics(self):
        presence = schema.presence_for('STATIC', 'LOCAL', has_gpu_tasks=False)
        missing_names = {m.name for m in presence.missing}
        assert missing_names == set(schema.GPU_METRIC_NAMES)

    def test_non_filesystem_storage_omits_filesystem_metrics(self):
        """S3 (or unknown) storage: no run filesystem, no task filesystem I/O."""
        presence = schema.presence_for(None, 'LOCAL', has_gpu_tasks=False)
        missing_names = {m.name for m in presence.missing}
        assert 'aws.omics.task.filesystem.io' in missing_names
        assert 'aws.omics.task.filesystem.operations' in missing_names
        assert 'aws.omics.run.filesystem.usage' in missing_names
        assert 'aws.omics.run.filesystem.limit' in missing_names
        # compute metrics still present
        assert 'aws.omics.task.cpu.usage' in presence.present

    def test_every_missing_metric_has_a_reason(self):
        presence = schema.presence_for(None, 'SHARED', has_gpu_tasks=False)
        assert all(m.reason for m in presence.missing)

    def test_present_and_missing_partition_the_schema(self):
        presence = schema.presence_for('DYNAMIC', 'SHARED', has_gpu_tasks=False)
        names = set(presence.present) | {m.name for m in presence.missing}
        assert names == set(schema.ALL_METRIC_NAMES)
        assert not set(presence.present) & {m.name for m in presence.missing}


class TestBuildSelector:
    """PromQL selector construction."""

    def test_basic_run_selector(self):
        selector = schema.build_selector('aws.omics.task.cpu.usage', run_id='1234567')
        assert selector == (
            '{"aws.omics.task.cpu.usage", '
            '"@instrumentation.@name"="cloudwatch.aws/omics", '
            '"@resource.aws.omics.run.id"="1234567"}'
        )

    def test_task_scoped_selector(self):
        selector = schema.build_selector(
            'aws.omics.task.memory.usage', run_id='1234567', task_id='7654321'
        )
        assert '"@resource.aws.omics.task.id"="7654321"' in selector

    def test_direction_datapoint_attribute(self):
        selector = schema.build_selector(
            'aws.omics.task.filesystem.io',
            run_id='1234567',
            extra_labels={'filesystem.io.direction': 'read'},
        )
        assert '"filesystem.io.direction"="read"' in selector

    def test_workflow_selector(self):
        selector = schema.build_selector('aws.omics.task.cpu.usage', workflow_id='999')
        assert '"@resource.aws.omics.workflow.id"="999"' in selector

    def test_task_id_rejected_on_per_run_metric(self):
        with pytest.raises(ValueError, match='per-run metric'):
            schema.build_selector(
                'aws.omics.run.filesystem.usage', run_id='1234567', task_id='7654321'
            )

    def test_unknown_metric_rejected(self):
        with pytest.raises(ValueError, match='Unknown vended metric'):
            schema.build_selector('not.a.metric', run_id='1234567')

    def test_undeclared_datapoint_attribute_rejected(self):
        with pytest.raises(ValueError, match='not a datapoint attribute'):
            schema.build_selector(
                'aws.omics.task.cpu.usage',
                run_id='1234567',
                extra_labels={'filesystem.io.direction': 'read'},
            )

    def test_disallowed_datapoint_value_rejected(self):
        with pytest.raises(ValueError, match='not an allowed value'):
            schema.build_selector(
                'aws.omics.task.filesystem.io',
                run_id='1234567',
                extra_labels={'filesystem.io.direction': 'sideways'},
            )

    def test_gpu_id_accepts_any_value(self):
        """gpu.id has an unbounded value set (empty allowed list = any value)."""
        selector = schema.build_selector(
            'aws.omics.task.gpu.utilization',
            run_id='1234567',
            extra_labels={'gpu.id': '0'},
        )
        assert '"gpu.id"="0"' in selector

    def test_quotes_are_escaped(self):
        selector = schema.build_selector('aws.omics.task.cpu.usage', run_id='ru"n')
        assert '"ru\\"n"' in selector


class TestRegionSupport:
    """Vended metrics regional availability."""

    def test_il_central_1_not_supported(self):
        assert not schema.is_region_supported('il-central-1')

    def test_other_regions_supported(self):
        assert schema.is_region_supported('us-east-1')
        assert schema.is_region_supported('us-west-2')
        assert schema.is_region_supported(None)

    def test_unsupported_reason_names_region_and_fallback(self):
        reason = schema.region_unsupported_reason('il-central-1')
        assert 'il-central-1' in reason
        assert 'AnalyzeAHORunPerformance' in reason


class TestLaunchDateAndSampling:
    """Production launch gating and per-metric sampling cadences."""

    def test_run_before_launch_predates(self):
        from datetime import datetime, timezone

        before = datetime(2026, 9, 6, 23, 59, tzinfo=timezone.utc)
        assert schema.predates_launch(before)

    def test_run_on_or_after_launch_does_not_predate(self):
        from datetime import datetime, timezone

        on_launch = datetime(2026, 9, 7, 0, 0, tzinfo=timezone.utc)
        assert not schema.predates_launch(on_launch)
        assert not schema.predates_launch(None)

    def test_launch_reason_names_date_and_fallback(self):
        reason = schema.launch_date_reason()
        assert '2026-09-07' in reason
        assert 'AnalyzeAHORunPerformance' in reason

    def test_short_task_reason_includes_duration(self):
        reason = schema.short_task_reason(12.0)
        assert '12s' in reason
        assert str(schema.MIN_TASK_DURATION_SECONDS) in reason

    def test_scratch_usage_has_slow_sampling_interval(self):
        """Scratch usage walks the filesystem, so it is sampled every ~20 min."""
        metric = schema.metric_of('aws.omics.task.filesystem.scratch.storage.usage')
        assert metric.sampling_interval_seconds == 20 * 60

    def test_other_metrics_use_default_sampling_interval(self):
        for name in ('aws.omics.task.cpu.usage', 'aws.omics.task.filesystem.io'):
            metric = schema.metric_of(name)
            assert metric.sampling_interval_seconds == schema.DEFAULT_SAMPLING_INTERVAL_SECONDS
