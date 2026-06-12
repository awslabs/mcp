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

"""Tests for ServiceEvents tool handlers and call-tree formatting (CloudWatch Logs version)."""

import asyncio
from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.cw_logs import (
    CwLogsQueryError,
)
from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.formatting import (
    _call_path_to_ascii,
    render_incident_call_tree,
)
from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.promql_client import (
    PromQLQueryError,
)
from unittest.mock import patch


# ============================================================================
# Sample OTLP service_events records (matching mcp/new_example shapes)
# ============================================================================


def _incident_record(
    snapshot_id='snap-1',
    operation='GET /api/users',
    trigger_type='exception',
    duration_ms=150.5,
    status_code=500,
    exception_info=None,
    trace_id='abc123',
    span_id='def456',
):
    return {
        'resource': {
            'attributes': {
                'service.name': 'svc',
                'deployment.environment.name': 'prod',
                'cloud.region': 'us-west-2',
                'cloud.provider': 'aws',
            }
        },
        'attributes': {
            'event.name': 'aws.service_events.incident_snapshot',
            'aws.service_events.snapshot_id': snapshot_id,
            'aws.service_events.operation': operation,
            'aws.service_events.trigger_type': trigger_type,
            'aws.service_events.duration_ms': duration_ms,
            'http.response.status_code': status_code,
            'aws.service_events.deployment.id': 'dep-1',
        },
        'body': {
            'exception_info': exception_info or [],
            'request_context': {'status_code': status_code, 'type': 'http'},
        },
        'eventName': 'aws.service_events.incident_snapshot',
        'timeUnixNano': 1780098109463317248,
        'traceId': trace_id,
        'spanId': span_id,
    }


# ============================================================================
# TestCallPathToAscii — incident call_path rendering
# ============================================================================


class TestCallPathToAscii:
    """Test the flat call_path -> ASCII call tree renderer."""

    def test_empty(self):
        """Render an empty string for empty or None call paths."""
        assert _call_path_to_ascii([]) == ''
        assert _call_path_to_ascii(None) == ''

    def test_single_root(self):
        """Render a single root frame with its duration."""
        cp = [
            {
                'function_name': 'app.handle',
                'caller_function_name': None,
                'duration_ns': 1_000_000,
                'error': False,
            }
        ]
        result = _call_path_to_ascii(cp)
        assert 'app.handle' in result
        assert '1.0ms' in result

    def test_parent_child_edges(self):
        """Render parent-child edges and mark error frames."""
        cp = [
            {
                'function_name': 'child',
                'caller_function_name': 'root',
                'duration_ns': 500_000,
                'error': True,
            },
            {
                'function_name': 'root',
                'caller_function_name': None,
                'duration_ns': 1_000_000,
                'error': False,
            },
        ]
        result = _call_path_to_ascii(cp)
        assert 'root' in result
        assert 'child' in result
        assert '└── ' in result
        assert '★ ERROR' in result

    def test_external_caller_treated_as_root(self):
        """Treat a frame with an external caller as a root."""
        # caller not present in path -> the frame is a root.
        cp = [
            {
                'function_name': 'leaf',
                'caller_function_name': 'framework.dispatch',
                'duration_ns': 100,
                'error': False,
            }
        ]
        result = _call_path_to_ascii(cp)
        assert result.startswith('leaf')

    def test_render_with_header(self):
        """Render the call tree with its timing header."""
        cp = [
            {
                'function_name': 'app.handle',
                'caller_function_name': None,
                'duration_ns': 1_000_000,
                'error': False,
            }
        ]
        result = render_incident_call_tree(cp)
        assert '[Timing: function-call instrumentation]' in result
        assert 'app.handle' in result

    def test_render_empty_returns_empty(self):
        """Return an empty string when rendering an empty call tree."""
        assert render_incident_call_tree([]) == ''


# ============================================================================
# TestListFunctions (Functions metrics via PromQL / function_metrics)
# ============================================================================


def _fn_record(name, line=10, calls=100, avg_ms=5.0, errors=0):
    return {
        'name': name,
        'line': line,
        'calls': calls,
        'avg_duration_ms': avg_ms,
        'errors': errors,
    }


class TestListFunctions:
    """Test list_functions tool handler (CloudWatch Metrics V2 / PromQL source)."""

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools.function_metrics.fetch_function_records'
    )
    def test_default_mode(self, mock_fetch):
        """Should fetch records and return avg+count, no percentiles."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            list_functions,
        )

        mock_fetch.return_value = [_fn_record('my_func', line=10, calls=100, avg_ms=5.0)]

        result = list_functions(hours=24)

        assert result['total_functions'] == 1
        assert result['returned'] == 1
        assert result['filter'] is None
        assert result['sort_by'] == 'calls'
        assert result['data_source'] == 'cloudwatch_metrics_v2'
        assert len(result['functions']) == 1
        fn = result['functions'][0]
        assert fn['name'] == 'my_func'
        assert fn['avg_duration_ms'] == 5.0
        assert fn['calls'] == 100
        # No percentiles in the PromQL-backed output.
        assert not any(k.startswith('p99') or k.startswith('p50') for k in fn)
        assert 'file_path' not in fn

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools.function_metrics.fetch_function_records'
    )
    def test_filter_errors(self, mock_fetch):
        """filter='errors' keeps only functions with errors > 0."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            list_functions,
        )

        mock_fetch.return_value = [
            _fn_record('error_func', calls=50, avg_ms=10.0, errors=7),
            _fn_record('clean_func', calls=80, avg_ms=2.0, errors=0),
        ]

        result = list_functions(hours=24, filter='errors')

        assert result['filter'] == 'errors'
        assert result['total_functions'] == 1
        assert result['functions'][0]['name'] == 'error_func'
        assert result['functions'][0]['errors'] == 7

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools.function_metrics.fetch_function_records'
    )
    def test_filter_slow_uses_avg(self, mock_fetch):
        """filter='slow' thresholds on average duration."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            list_functions,
        )

        mock_fetch.return_value = [
            _fn_record('slow_func', avg_ms=250.0),
            _fn_record('fast_func', avg_ms=5.0),
        ]

        result = list_functions(hours=24, filter='slow', threshold_ms=100.0)

        assert {f['name'] for f in result['functions']} == {'slow_func'}

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools.function_metrics.fetch_function_records'
    )
    def test_endpoint_filters_by_operation(self, mock_fetch):
        """Endpoint is passed through as the operation filter and echoed in the result."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            list_functions,
        )

        mock_fetch.return_value = [_fn_record('f')]
        result = list_functions(hours=24, endpoint='POST /checkout')
        assert result['endpoint_filter'] == 'POST /checkout'
        assert mock_fetch.call_args[1]['operation'] == 'POST /checkout'

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools.function_metrics.fetch_function_records'
    )
    def test_query_error_returns_empty(self, mock_fetch):
        """Should return empty result with error on PromQL failure."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            list_functions,
        )

        mock_fetch.side_effect = PromQLQueryError('query timeout')

        result = list_functions(hours=24)

        assert result['total_functions'] == 0
        assert 'error' in result


# ============================================================================
# TestSearchFunctions
# ============================================================================


class TestSearchFunctions:
    """Test search_functions tool handler (PromQL label-values source)."""

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools.function_metrics.search_function_names'
    )
    def test_returns_matching_names(self, mock_search):
        """Should return function-name matches from the metrics label values."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            search_functions,
        )

        mock_search.return_value = ['my_func', 'my_other_func']

        result = search_functions(query='my_func')

        assert result['query'] == 'my_func'
        assert result['total_matches'] == 2
        assert result['returned'] == 2
        assert {f['name'] for f in result['functions']} == {'my_func', 'my_other_func'}
        assert mock_search.call_args[1]['query'] == 'my_func'

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools.function_metrics.search_function_names'
    )
    def test_query_error_returns_empty(self, mock_search):
        """Return an empty result with an error on PromQL failure."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            search_functions,
        )

        mock_search.side_effect = PromQLQueryError('boom')
        result = search_functions(query='x')
        assert result['total_matches'] == 0
        assert 'error' in result


# ============================================================================
# TestGetEndpoints (ServiceEvents CloudWatch Logs source; AppSignals disabled)
# ============================================================================


class TestGetEndpoints:
    """Test get_endpoints tool handler."""

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.cw_logs.query_endpoint_summaries'
    )
    def test_list_mode(self, mock_query):
        """Return all endpoints in list mode."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            get_endpoints,
        )

        mock_query.return_value = [
            {
                'operation': 'POST /checkout',
                'total_requests': 10,
                'total_faults': 2,
                'total_errors': 1,
                'avg_duration_ms': 15.0,
                'p99_duration_ms': 25.0,
            }
        ]

        result = asyncio.get_event_loop().run_until_complete(get_endpoints(hours=24))

        assert result['data_source'] == 'service_events'
        assert result['total_endpoints'] == 1
        assert result['endpoints'][0]['operation'] == 'POST /checkout'
        assert result['endpoints'][0]['total_faults'] == 2

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.cw_logs.query_endpoint_summaries'
    )
    def test_detail_mode_single_match(self, mock_query):
        """Return the endpoint directly when a single operation matches."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            get_endpoints,
        )

        mock_query.return_value = [
            {'operation': 'POST /checkout', 'total_requests': 10, 'total_faults': 2}
        ]

        result = asyncio.get_event_loop().run_until_complete(
            get_endpoints(operation='POST /checkout')
        )

        # Single match returns the endpoint directly with data_source.
        assert result['operation'] == 'POST /checkout'
        assert result['data_source'] == 'service_events'

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.cw_logs.query_endpoint_summaries'
    )
    def test_query_error_returns_empty(self, mock_query):
        """Return an empty result with an error on CloudWatch Logs failure."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            get_endpoints,
        )

        mock_query.side_effect = CwLogsQueryError('boom')

        result = asyncio.get_event_loop().run_until_complete(get_endpoints(hours=24))

        assert result['total_endpoints'] == 0
        assert 'error' in result
        assert result['data_source'] == 'service_events'

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.endpoint_metrics.get_endpoint_red_metrics'
    )
    def test_appsignals_red_metrics_when_enabled(self, mock_red):
        """Use Application Signals RED metrics when enabled."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events import state
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            get_endpoints,
        )

        state.set_appsignals_enabled(True)
        mock_red.return_value = [
            {
                'operation': 'GET /api/orders',
                'service_name': 'orders',
                'total_requests': 100,
                'total_faults': 3,
                'total_errors': 1,
                'avg_duration_ms': 12.0,
                'p99_duration_ms': 40.0,
            }
        ]

        result = asyncio.get_event_loop().run_until_complete(
            get_endpoints(hours=24, service_name='orders')
        )

        # AppSignals is the source; CW-logs endpoint query is not consulted.
        assert result['data_source'] == 'application_signals'
        assert result['total_endpoints'] == 1
        assert result['endpoints'][0]['operation'] == 'GET /api/orders'
        mock_red.assert_called_once()


# ============================================================================
# TestGetIncidents (ServiceEvents CloudWatch Logs)
# ============================================================================


class TestGetIncidents:
    """Test get_incidents tool handler."""

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.cw_logs.query_incidents'
    )
    def test_endpoint_filter_passed(self, mock_query):
        """Pass the endpoint filter through to the incident query."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            get_incidents,
        )

        mock_query.return_value = []

        asyncio.get_event_loop().run_until_complete(
            get_incidents(endpoint='/api/users', service_name='svc')
        )

        call_kwargs = mock_query.call_args[1]
        assert call_kwargs['endpoint'] == '/api/users'

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.cw_logs.query_incidents'
    )
    def test_dedup_by_operation(self, mock_query):
        """Keep incidents with distinct operations during dedup."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            get_incidents,
        )

        mock_query.return_value = [
            _incident_record(snapshot_id='snap-1', operation='GET /api/a'),
            _incident_record(snapshot_id='snap-2', operation='GET /api/b'),
        ]

        result = asyncio.get_event_loop().run_until_complete(get_incidents(service_name='svc'))

        # Both incidents kept (different operation).
        assert result['total_unique_incidents'] == 2
        assert result['data_source'] == 'service_events'
        ids = {i['snapshot_id'] for i in result['incidents']}
        assert ids == {'snap-1', 'snap-2'}

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.cw_logs.query_incidents'
    )
    def test_summary_fields(self, mock_query):
        """Populate incident summary, correlation, and cloud context fields."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            get_incidents,
        )

        mock_query.return_value = [
            _incident_record(
                snapshot_id='snap-x', operation='GET /x', trigger_type='latency', duration_ms=99.0
            )
        ]

        result = asyncio.get_event_loop().run_until_complete(get_incidents())

        inc = result['incidents'][0]
        assert inc['snapshot_id'] == 'snap-x'
        assert inc['operation'] == 'GET /x'
        assert inc['trigger_type'] == 'latency'
        assert inc['duration_ms'] == 99.0
        assert inc['telemetry_correlation']['trace_id'] == 'abc123'
        assert inc['cloud_context']['cloud.region'] == 'us-west-2'

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.cw_logs.query_incidents'
    )
    def test_query_error_returns_empty(self, mock_query):
        """Return an empty result with an error when the incident query fails."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            get_incidents,
        )

        mock_query.side_effect = CwLogsQueryError('nope')

        result = asyncio.get_event_loop().run_until_complete(get_incidents())

        assert result['total_unique_incidents'] == 0
        assert 'error' in result


# ============================================================================
# TestGetIncidentDetails (ServiceEvents CloudWatch Logs)
# ============================================================================


class TestGetIncidentDetails:
    """Test get_incident_details tool handler."""

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.cw_logs.query_incident_by_id'
    )
    def test_exception_with_call_path(self, mock_query):
        """Render an exception incident with its call tree."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            get_incident_details,
        )

        exc = [
            {
                'exception_type': 'RuntimeError',
                'exception_message': 'boom',
                'stack_trace': 'Traceback ...',
                'call_path': [
                    {
                        'function_name': 'root',
                        'caller_function_name': None,
                        'duration_ns': 1_000_000,
                        'error': False,
                    },
                    {
                        'function_name': 'fail',
                        'caller_function_name': 'root',
                        'duration_ns': 800_000,
                        'error': True,
                    },
                ],
            }
        ]
        mock_query.return_value = _incident_record(
            snapshot_id='snap-1', trigger_type='exception', exception_info=exc
        )

        result = asyncio.get_event_loop().run_until_complete(
            get_incident_details(snapshot_id='snap-1')
        )

        assert result['snapshot_id'] == 'snap-1'
        assert result['trigger_type'] == 'exception'
        assert result['exception_type'] == 'RuntimeError'
        assert result['exception_message'] == 'boom'
        assert 'stack_trace' in result
        assert 'call_tree' in result
        assert 'root' in result['call_tree']
        assert 'fail' in result['call_tree']
        assert '★ ERROR' in result['call_tree']
        assert '[Timing: function-call instrumentation]' in result['call_tree']
        assert 'call_tree_note' not in result
        assert result['telemetry_correlation']['trace_id'] == 'abc123'

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.cw_logs.query_incident_by_id'
    )
    def test_no_call_path_sets_call_tree_note(self, mock_query):
        """Set a call_tree_note when the exception has no call path."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            get_incident_details,
        )

        exc = [
            {
                'exception_type': 'FastFail',
                'exception_message': 'oops',
                'stack_trace': 'tb',
                'call_path': [],
            }
        ]
        mock_query.return_value = _incident_record(
            snapshot_id='snap-2', trigger_type='exception', exception_info=exc
        )

        result = asyncio.get_event_loop().run_until_complete(
            get_incident_details(snapshot_id='snap-2')
        )

        assert 'call_tree' not in result
        assert 'call_tree_note' in result
        assert result['exception_type'] == 'FastFail'

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.cw_logs.query_incident_by_id'
    )
    def test_latency_incident(self, mock_query):
        """Mark a latency incident and add a latency note."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            get_incident_details,
        )

        mock_query.return_value = _incident_record(
            snapshot_id='snap-lat', trigger_type='latency', status_code=200, exception_info=[]
        )

        result = asyncio.get_event_loop().run_until_complete(
            get_incident_details(snapshot_id='snap-lat')
        )

        assert result['is_latency_incident'] is True
        assert 'latency_note' in result
        assert 'call tree is not available' in result['latency_note'].lower()

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.cw_logs.query_incident_by_id'
    )
    def test_not_found(self, mock_query):
        """Return a not-found error when the incident does not exist."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            get_incident_details,
        )

        mock_query.return_value = None

        result = asyncio.get_event_loop().run_until_complete(
            get_incident_details(snapshot_id='snap-gone')
        )

        assert result['error'] == 'No data found'


# ============================================================================
# TestFindDeployment (ServiceEvents CloudWatch Logs)
# ============================================================================


class TestFindDeployment:
    """Test find_deployment tool handler."""

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.cw_logs.query_deployments'
    )
    def test_find_by_commit(self, mock_query):
        """Find a deployment by commit prefix."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            find_deployment,
        )

        mock_query.return_value = [
            {
                'git_commit_sha': 'abc123full',
                'git_repo_url': 'https://github.com/org/repo',
                'deployment_url': 'https://github.com/org/repo/actions/runs/1',
                'deployed_at': '2026-03-05T01:41:45Z',
                'deployment_id': 'run-1',
                'trigger': 'startup',
                'service_name': 'svc',
                'environment': 'prod',
            }
        ]

        result = find_deployment(git_commit_sha='abc123')

        assert result['found'] is True
        assert result['total_deployments'] == 1
        assert result['deployments'][0]['git_commit_sha'] == 'abc123full'
        call_kwargs = mock_query.call_args[1]
        assert call_kwargs['commit'] == 'abc123'

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.cw_logs.query_deployments'
    )
    def test_no_match(self, mock_query):
        """Return not-found with a suggestion when no deployment matches."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.tools import (
            find_deployment,
        )

        mock_query.return_value = []

        result = find_deployment(git_commit_sha='nonexistent')

        assert result['found'] is False
        assert 'suggestion' in result
