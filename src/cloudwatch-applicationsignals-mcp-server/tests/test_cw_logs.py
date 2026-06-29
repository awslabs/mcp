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
from unittest.mock import MagicMock, patch


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
        assert dep['git_commit_sha'] == 'abababababababababababababababababababab'
        assert dep['deployment_id'] == '26605861522'
        assert dep['deployment_url'].endswith('/runs/26605861522')

    def test_commit_prefix_filter(self):
        """Match deployments by commit prefix and exclude non-matches."""
        fake = _FakeLogsClient(records=[_load('serviceevents_deployment.json')])
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            match = cw_logs.query_deployments(service_name='svc', hours=168, commit='ababab')
            nomatch = cw_logs.query_deployments(service_name='svc', hours=168, commit='c3b094')
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

    def test_percentile_zero_total(self):
        """Return None when all bucket counts are zero (total weight <= 0)."""
        duration = {'Values': [10000.0, 20000.0], 'Counts': [0, 0]}
        assert cw_logs._percentile_ms_from_duration(duration, 99) is None

    def test_percentile_falls_back_to_last_bucket(self):
        """Fall back to the largest bucket when the cumulative rank is never reached."""
        # Counts sum to 10; floating rank for p100 is 10.0. Rounding inside the loop
        # can leave the last bucket as the fallback return (line covering the final return).
        duration = {'Values': [10000.0, 20000.0, 30000.0], 'Counts': [1, 1, 8]}
        # p100 -> target_rank = 10; cumulative reaches 10 at the last bucket.
        assert cw_logs._percentile_ms_from_duration(duration, 100) == 30.0

    def test_percentile_mismatched_lengths(self):
        """Return None when Values and Counts arrays differ in length."""
        duration = {'Values': [10000.0], 'Counts': [1, 2]}
        assert cw_logs._percentile_ms_from_duration(duration, 99) is None


# ============================================================================
# Region resolution and lazy client build
# ============================================================================


class TestClientAndRegion:
    """Tests for region resolution and the lazily-built logs client."""

    def test_region_uses_aws_clients_constant(self):
        """Resolve the region from the aws_clients AWS_REGION constant."""
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.AWS_REGION',
            'eu-west-1',
        ):
            assert cw_logs._region() == 'eu-west-1'

    def test_get_logs_client_delegates_to_shared_client(self):
        """Use the shared aws_clients logs client rather than building its own."""
        sentinel = object()
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.get_logs_client',
            return_value=sentinel,
        ):
            assert cw_logs._get_logs_client() is sentinel


# ============================================================================
# Wildcard log group enumeration: cap + error handling
# ============================================================================


class _CappedPaginator:
    """Paginator yielding many groups across pages to exercise the cap."""

    def __init__(self, total):
        self._total = total

    def paginate(self, **kwargs):
        # Two pages, 40 groups each -> 80 total, exceeding the 50 cap.
        per_page = 40
        emitted = 0
        page = []
        while emitted < self._total:
            page.append({'logGroupName': f'/aws/service-events/svc-{emitted}'})
            emitted += 1
            if len(page) == per_page:
                yield {'logGroups': page}
                page = []
        if page:
            yield {'logGroups': page}


class TestWildcardEnumeration:
    """Tests for the cap and error paths in cross-service log group enumeration."""

    def test_caps_at_max_wildcard_groups(self):
        """Cap the wildcard scan at MAX_WILDCARD_LOG_GROUPS groups."""
        client = MagicMock()
        client.get_paginator.return_value = _CappedPaginator(total=80)
        with patch.object(cw_logs, '_get_logs_client', return_value=client):
            groups = cw_logs._resolve_log_groups(None)
        assert len(groups) == cw_logs.MAX_WILDCARD_LOG_GROUPS

    def test_enumeration_error_returns_empty(self):
        """Return an empty list when enumeration raises."""
        client = MagicMock()
        client.get_paginator.side_effect = RuntimeError('describe failed')
        with patch.object(cw_logs, '_get_logs_client', return_value=client):
            groups = cw_logs._resolve_log_groups(None)
        assert groups == []


# ============================================================================
# run_insights_query: extra filter, empty/unparsable messages
# ============================================================================


class TestRunInsightsQuery:
    """Tests for query assembly and record parsing in run_insights_query."""

    def test_extra_query_filter_appended(self):
        """Append an extra filter clause to the query string when provided."""
        fake = _FakeLogsClient(records=[])
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            cw_logs.run_insights_query(
                cw_logs.EVENT_DEPLOYMENT_EVENT,
                hours=24,
                service_name='svc',
                extra_query_filter='filter foo = "bar"',
            )
        qs = fake.start_query_calls[0]['queryString']
        assert 'filter foo = "bar"' in qs

    def test_skips_empty_and_unparsable_messages(self):
        """Skip rows with empty messages and rows whose @message is not valid JSON."""
        client = MagicMock()
        client.start_query.return_value = {'queryId': 'q-1'}
        client.get_query_results.return_value = {
            'status': 'Complete',
            'results': [
                [{'field': '@message', 'value': ''}],  # empty -> skipped
                [{'field': '@message', 'value': '{not json'}],  # unparsable -> skipped
                [{'field': '@message', 'value': json.dumps({'eventName': 'x'})}],
            ],
        }
        with patch.object(cw_logs, '_get_logs_client', return_value=client):
            out = cw_logs.run_insights_query(
                cw_logs.EVENT_INCIDENT_SNAPSHOT, hours=1, service_name='svc'
            )
        assert out == [{'eventName': 'x'}]


# ============================================================================
# _execute: failure and polling paths
# ============================================================================


class TestExecuteErrors:
    """Tests for start/poll error handling in _execute."""

    def test_start_query_failure_raises(self):
        """Wrap a start_query exception in CwLogsQueryError."""
        client = MagicMock()
        client.start_query.side_effect = RuntimeError('start boom')
        with patch.object(cw_logs, '_get_logs_client', return_value=client):
            with pytest.raises(cw_logs.CwLogsQueryError, match='Failed to start query'):
                cw_logs._execute('q', 1, ['/aws/service-events/svc'])

    def test_missing_query_id_raises(self):
        """Raise when start_query returns no queryId."""
        client = MagicMock()
        client.start_query.return_value = {}
        with patch.object(cw_logs, '_get_logs_client', return_value=client):
            with pytest.raises(cw_logs.CwLogsQueryError, match='did not return a queryId'):
                cw_logs._execute('q', 1, ['/aws/service-events/svc'])

    def test_get_query_results_failure_raises(self):
        """Wrap a get_query_results exception in CwLogsQueryError."""
        client = MagicMock()
        client.start_query.return_value = {'queryId': 'q-1'}
        client.get_query_results.side_effect = RuntimeError('poll boom')
        with patch.object(cw_logs, '_get_logs_client', return_value=client):
            with pytest.raises(cw_logs.CwLogsQueryError, match='Failed to get query results'):
                cw_logs._execute('q', 1, ['/aws/service-events/svc'])

    def test_failed_status_raises(self):
        """Raise when the query terminates with a non-Complete status."""
        client = MagicMock()
        client.start_query.return_value = {'queryId': 'q-1'}
        client.get_query_results.return_value = {'status': 'Failed'}
        with patch.object(cw_logs, '_get_logs_client', return_value=client):
            with pytest.raises(cw_logs.CwLogsQueryError, match='Query Failed'):
                cw_logs._execute('q', 1, ['/aws/service-events/svc'])

    def test_timeout_raises(self):
        """Raise CwLogsQueryError when the query never completes within the timeout."""
        client = MagicMock()
        client.start_query.return_value = {'queryId': 'q-1'}
        client.get_query_results.return_value = {'status': 'Running'}
        # Drive time so the poll loop runs once then exceeds QUERY_TIMEOUT_SECONDS.
        times = iter([0.0, 0.0, 0.0, cw_logs.QUERY_TIMEOUT_SECONDS + 1])

        def fake_time():
            try:
                return next(times)
            except StopIteration:
                return cw_logs.QUERY_TIMEOUT_SECONDS + 1

        with (
            patch.object(cw_logs, '_get_logs_client', return_value=client),
            patch.object(cw_logs.time, 'time', side_effect=fake_time),
            patch.object(cw_logs.time, 'sleep'),
        ):
            with pytest.raises(cw_logs.CwLogsQueryError, match='did not complete within'):
                cw_logs._execute('q', 1, ['/aws/service-events/svc'])


# ============================================================================
# Limit/filter break branches in typed query helpers
# ============================================================================


class TestQueryLimitsAndFilters:
    """Tests for limit truncation and Python-side filters in typed helpers."""

    @staticmethod
    def _summary_record(operation):
        """Build a minimal endpoint_summary OTLP record."""
        return {
            'resource': {'attributes': {'service.name': 'svc'}},
            'attributes': {'aws.service_events.operation': operation},
            'body': {'duration': {'Count': 1, 'Sum': 1000.0}},
            'eventName': cw_logs.EVENT_ENDPOINT_SUMMARY,
        }

    def test_endpoint_summary_honors_limit(self):
        """Stop collecting endpoint summaries once the limit is reached."""
        fake = _FakeLogsClient(records=[self._summary_record(f'op-{i}') for i in range(5)])
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            out = cw_logs.query_endpoint_summaries(service_name='svc', hours=24, limit=2)
        assert len(out) == 2

    def test_incidents_endpoint_filter(self):
        """Filter incidents by an operation/endpoint substring."""
        match = {
            'resource': {'attributes': {'service.name': 'svc'}},
            'attributes': {
                'aws.service_events.operation': 'POST /checkout',
                'aws.service_events.trigger_type': 'exception',
            },
            'eventName': cw_logs.EVENT_INCIDENT_SNAPSHOT,
        }
        other = {
            'resource': {'attributes': {'service.name': 'svc'}},
            'attributes': {
                'aws.service_events.operation': 'GET /health',
                'aws.service_events.trigger_type': 'exception',
            },
            'eventName': cw_logs.EVENT_INCIDENT_SNAPSHOT,
        }
        fake = _FakeLogsClient(records=[match, other])
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            out = cw_logs.query_incidents(service_name='svc', hours=24, endpoint='checkout')
        assert len(out) == 1
        assert out[0]['attributes']['aws.service_events.operation'] == 'POST /checkout'

    def test_deployments_honor_limit(self):
        """Stop collecting deployments once the limit is reached."""
        fake = _FakeLogsClient(
            records=[TestDeployments._dep(f'sha-{i}', f'run-{i}', 'startup') for i in range(5)]
        )
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            out = cw_logs.query_deployments(service_name='svc', hours=168, limit=2)
        assert len(out) == 2

    def test_deployments_dedupes_startup_by_deployment_id(self):
        """Drop a duplicate startup that repeats the same deployment_id for one commit."""
        # Same commit, two startup events with the SAME deployment_id -> only one kept.
        fake = _FakeLogsClient(
            records=[
                TestDeployments._dep('shaX', 'run-dup', 'startup'),
                TestDeployments._dep('shaX', 'run-dup', 'startup'),
            ]
        )
        with patch.object(cw_logs, '_get_logs_client', return_value=fake):
            out = cw_logs.query_deployments(service_name='svc', hours=168)
        assert len(out) == 1
        assert out[0]['deployment_id'] == 'run-dup'
