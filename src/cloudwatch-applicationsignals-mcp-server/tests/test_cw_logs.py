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

"""Tests for the CloudWatch Logs Insights data layer (service_events records)."""

import json
import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.service_events import cw_logs
from pathlib import Path
from unittest.mock import patch


FIXTURES_DIR = Path(__file__).parent / 'fixtures'


def _load(name):
    return json.loads((FIXTURES_DIR / name).read_text())


class _FakeLogsClient:
    """Minimal stand-in for a boto3 CloudWatch Logs client.

    ``records`` is the list of OTLP dicts to return (one per result row, as the
    ``@message`` field). ``log_groups`` is what describe_log_groups returns.
    """

    def __init__(self, records=None, log_groups=None):
        self._records = records or []
        self._log_groups = log_groups or []
        self.start_query_calls = []

    def start_query(self, **kwargs):
        self.start_query_calls.append(kwargs)
        return {'queryId': 'q-1'}

    def get_query_results(self, queryId):  # noqa: N803 (boto3 param name)
        results = []
        for rec in self._records:
            results.append(
                [
                    {'field': '@message', 'value': json.dumps(rec)},
                    {'field': '@timestamp', 'value': '2026-06-08 00:00:00.000'},
                ]
            )
        return {'status': 'Complete', 'results': results}

    def get_paginator(self, name):
        groups = self._log_groups
        return _FakePaginator(groups)


class _FakePaginator:
    def __init__(self, groups):
        self._groups = groups

    def paginate(self, **kwargs):
        return [{'logGroups': [{'logGroupName': g} for g in self._groups]}]


@pytest.fixture(autouse=True)
def _reset_cw_client(monkeypatch):
    """Ensure each test installs its own fake client and resets the module cache."""
    cw_logs._reset_client()
    monkeypatch.delenv('SERVICE_EVENTS_LOG_GROUP_PREFIX', raising=False)
    yield
    cw_logs._reset_client()


# ============================================================================
# Log group resolution
# ============================================================================


class TestLogGroupResolution:
    """Tests for log group name resolution and prefix handling."""

    def test_direct_group_for_named_service(self):
        """Build the direct log group name for a named service."""
        assert cw_logs._log_group_for('my-svc') == '/aws/service-events/my-svc'

    def test_prefix_overridable(self, monkeypatch):
        """Override the log group prefix via the environment variable."""
        monkeypatch.setenv('SERVICE_EVENTS_LOG_GROUP_PREFIX', '/custom/se')
        assert cw_logs._log_group_for('svc') == '/custom/se/svc'

    def test_resolve_named_service_skips_enumeration(self):
        """Resolve a named service without enumerating log groups."""
        fake = _FakeLogsClient(log_groups=['/aws/service-events/a', '/aws/service-events/b'])
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            groups = cw_logs._resolve_log_groups('my-svc')
        assert groups == ['/aws/service-events/my-svc']

    def test_resolve_wildcard_enumerates_prefix(self):
        """Enumerate all prefixed log groups when no service is given."""
        fake = _FakeLogsClient(log_groups=['/aws/service-events/a', '/aws/service-events/b'])
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            groups = cw_logs._resolve_log_groups(None)
        assert groups == ['/aws/service-events/a', '/aws/service-events/b']

    def test_resolve_wildcard_no_groups(self):
        """Return an empty list when no matching log groups exist."""
        fake = _FakeLogsClient(log_groups=[])
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            groups = cw_logs._resolve_log_groups(None)
        assert groups == []


# ============================================================================
# Query string construction
# ============================================================================


class TestQueryConstruction:
    """Tests for Insights query string construction."""

    def test_filters_on_event_name_and_limits(self):
        """Filter on event name and honor limit and time window."""
        fake = _FakeLogsClient(records=[])
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            cw_logs.run_insights_query(
                cw_logs.EVENT_INCIDENT_SNAPSHOT, hours=24, service_name='svc', limit=7
            )

        assert len(fake.start_query_calls) == 1
        call = fake.start_query_calls[0]
        assert call['logGroupNames'] == ['/aws/service-events/svc']
        qs = call['queryString']
        assert 'filter eventName = "aws.service_events.incident_snapshot"' in qs
        assert 'limit 7' in qs
        assert 'sort @timestamp desc' in qs
        # Time window honors hours.
        assert call['endTime'] - call['startTime'] == 24 * 3600

    def test_returns_empty_when_no_log_groups(self):
        """Return empty without starting a query when no groups resolve."""
        fake = _FakeLogsClient(log_groups=[])
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            # No service_name -> wildcard -> no groups -> empty without starting a query.
            out = cw_logs.run_insights_query(
                cw_logs.EVENT_ENDPOINT_SUMMARY, hours=24, service_name=None
            )
        assert out == []
        assert fake.start_query_calls == []


# ============================================================================
# OTLP parsing — typed query helpers against real fixtures
# ============================================================================


class TestEndpointSummaries:
    """Tests for parsing endpoint summary records."""

    def test_parses_fixture(self):
        """Parse an endpoint summary fixture into structured fields."""
        fake = _FakeLogsClient(records=[_load('serviceevents_endpoint_summary.json')])
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            out = cw_logs.query_endpoint_summaries(service_name='svc', hours=24, percentile=99)

        assert len(out) == 1
        ep = out[0]
        assert ep['operation'] == 'POST /investigation/trigger_error'
        assert ep['total_requests'] == 10
        assert ep['total_faults'] == 10
        assert ep['total_errors'] == 0
        assert ep['avg_duration_ms'] is not None
        assert ep['p99_duration_ms'] is not None
        assert 'error_breakdown' in ep

    def test_operation_filter(self):
        """Return empty when the operation filter matches nothing."""
        fake = _FakeLogsClient(records=[_load('serviceevents_endpoint_summary.json')])
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            out = cw_logs.query_endpoint_summaries(
                service_name='svc', hours=24, operation='nonexistent'
            )
        assert out == []


class TestIncidents:
    """Tests for parsing and filtering incident records."""

    def test_parses_python_exception(self):
        """Parse a Python exception incident fixture."""
        fake = _FakeLogsClient(records=[_load('serviceevents_incident_python_exception.json')])
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            out = cw_logs.query_incidents(service_name='svc', hours=24)
        assert len(out) == 1
        attrs = out[0]['attributes']
        assert attrs['aws.service_events.trigger_type'] == 'exception'
        assert attrs['aws.service_events.snapshot_id'].startswith('snap_')

    def test_trigger_type_filter(self):
        """Return empty when the trigger_type filter excludes the record."""
        fake = _FakeLogsClient(records=[_load('serviceevents_incident_python_exception.json')])
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            out = cw_logs.query_incidents(service_name='svc', hours=24, trigger_type='latency')
        assert out == []

    def test_query_incident_by_id_match(self):
        """Find an incident by snapshot id and miss on unknown ids."""
        rec = _load('serviceevents_incident_java_exception.json')
        sid = rec['attributes']['aws.service_events.snapshot_id']
        fake = _FakeLogsClient(records=[rec])
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            found = cw_logs.query_incident_by_id(sid, hours=72, service_name='svc')
            missing = cw_logs.query_incident_by_id(
                'snap_does_not_exist', hours=72, service_name='svc'
            )
        assert found is not None
        assert found['attributes']['aws.service_events.snapshot_id'] == sid
        assert missing is None


class TestDeployments:
    """Tests for parsing and deduplicating deployment records."""

    def test_parses_fixture(self):
        """Parse a deployment fixture into structured fields."""
        fake = _FakeLogsClient(records=[_load('serviceevents_deployment.json')])
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            out = cw_logs.query_deployments(service_name='svc', hours=168)
        assert len(out) == 1
        dep = out[0]
        assert dep['git_commit_sha'] == 'c3b0940dab7653ac8f4c2383c9dce96bb6dcc2ae'
        assert dep['deployment_id'] == '26605861522'
        assert dep['deployment_url'].endswith('/runs/26605861522')

    def test_commit_prefix_filter(self):
        """Match deployments by commit prefix and exclude non-matches."""
        fake = _FakeLogsClient(records=[_load('serviceevents_deployment.json')])
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            match = cw_logs.query_deployments(service_name='svc', hours=168, commit='c3b094')
            nomatch = cw_logs.query_deployments(service_name='svc', hours=168, commit='deadbeef')
        assert len(match) == 1
        assert nomatch == []

    @staticmethod
    def _dep(sha, dep_id, trigger):
        """Build a synthetic deployment OTLP record for tests."""
        return {
            'resource': {
                'attributes': {'service.name': 'svc', 'deployment.environment.name': 'prod'}
            },
            'attributes': {
                'event.name': 'aws.service_events.deployment_event',
                'vcs.ref.head.revision': sha,
                'aws.service_events.deployment.id': dep_id,
                'aws.service_events.deployment.trigger': trigger,
                'aws.service_events.deployment.url': f'https://x/runs/{dep_id}',
                'aws.service_events.deployment.timestamp': '2026-03-05T01:41:45Z',
            },
            'eventName': 'aws.service_events.deployment_event',
            'timeUnixNano': 1780007388903635645,
        }

    def test_startup_collapses_periodic_same_commit(self):
        """Collapse periodic re-emits into the startup for the same commit."""
        # Same commit, same deployment_id: one startup + one periodic -> only the startup.
        fake = _FakeLogsClient(
            records=[
                self._dep('abc123', 'run-1', 'startup'),
                self._dep('abc123', 'run-1', 'periodic'),
            ]
        )
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            out = cw_logs.query_deployments(service_name='svc', hours=168)
        assert len(out) == 1
        assert out[0]['trigger'] == 'startup'

    def test_periodic_only_shows_one(self):
        """Show one representative entry when only periodic re-emits exist."""
        # No startup for the commit; multiple periodic re-emits -> one representative entry.
        fake = _FakeLogsClient(
            records=[
                self._dep('def456', 'run-2', 'periodic'),
                self._dep('def456', 'run-2', 'periodic'),
            ]
        )
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            out = cw_logs.query_deployments(service_name='svc', hours=168)
        assert len(out) == 1
        assert out[0]['git_commit_sha'] == 'def456'
        assert out[0]['trigger'] == 'periodic'

    def test_multiple_restarts_same_commit_kept(self):
        """Keep distinct startup restarts for the same commit."""
        # Same commit, two distinct startup deployment_ids (real restarts) -> both kept;
        # periodic for that commit dropped.
        fake = _FakeLogsClient(
            records=[
                self._dep('c0ffee', 'run-10', 'startup'),
                self._dep('c0ffee', 'run-10', 'periodic'),
                self._dep('c0ffee', 'run-11', 'startup'),
            ]
        )
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            out = cw_logs.query_deployments(service_name='svc', hours=168)
        assert len(out) == 2
        assert {d['deployment_id'] for d in out} == {'run-10', 'run-11'}
        assert all(d['trigger'] == 'startup' for d in out)


# ============================================================================
# Percentile / average helpers
# ============================================================================


class TestDurationHelpers:
    """Tests for average and percentile duration helpers."""

    def test_avg_ms(self):
        """Compute average duration in milliseconds from microseconds."""
        # Sum is microseconds; avg = (Sum/Count)/1000 ms.
        duration = {'Count': 10, 'Sum': 150000.0}
        assert cw_logs._avg_ms_from_duration(duration) == 15.0

    def test_avg_ms_empty(self):
        """Return None for empty or zero-count duration data."""
        assert cw_logs._avg_ms_from_duration({}) is None
        assert cw_logs._avg_ms_from_duration({'Count': 0, 'Sum': 0}) is None

    def test_percentile(self):
        """Compute a percentile in milliseconds from bucketed data."""
        # All weight in a single 20000us bucket -> p99 = 20.0 ms.
        duration = {'Values': [10000.0, 20000.0], 'Counts': [0, 10]}
        assert cw_logs._percentile_ms_from_duration(duration, 99) == 20.0

    def test_percentile_empty(self):
        """Return None for empty percentile duration data."""
        assert cw_logs._percentile_ms_from_duration({}, 99) is None
        assert cw_logs._percentile_ms_from_duration({'Values': [], 'Counts': []}, 99) is None
