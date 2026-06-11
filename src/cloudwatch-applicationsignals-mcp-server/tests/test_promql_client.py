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

"""Tests for the PromQL client and quoted-label query builders."""

import json
import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.service_events import (
    promql_client,
    promql_query,
)
from awslabs.cloudwatch_applicationsignals_mcp_server.service_events.promql_client import (
    PromQLQueryError,
)
from unittest.mock import MagicMock, patch


class _FakeResponse:
    def __init__(self, status_code, payload=None, text=None):
        self.status_code = status_code
        self.text = text if text is not None else json.dumps(payload or {})


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    promql_client._reset_session()
    # Real (dummy) credentials so SigV4 signing succeeds without AWS access.
    from botocore.credentials import Credentials

    monkeypatch.setattr(
        promql_client,
        '_get_credentials',
        lambda: Credentials('AKIDTEST', 'secrettest', 'tokentest'),
    )
    monkeypatch.setattr(promql_client, '_region', lambda: 'us-west-2')
    yield
    promql_client._reset_session()


def _patch_http(response):
    """Patch the client's HTTP session to return a fixed response and capture the request."""
    fake = MagicMock()
    fake.send.return_value = response
    return patch.object(promql_client, '_get_http_session', return_value=fake), fake


# ============================================================================
# Query builders (quoted-label syntax)
# ============================================================================


class TestQueryBuilders:
    """Tests for quoted-label PromQL query builders."""

    def test_selector_quotes_metric_and_labels(self):
        """Quote the metric name and label values in a selector."""
        sel = promql_query.function_duration_selector(service_name='svc')
        assert sel == '{"service.function.duration","@resource.service.name"="svc"}'

    def test_selector_escapes_quotes(self):
        """Escape embedded quotes in label values."""
        sel = promql_query.build_selector('m', {'k': 'a"b'})
        assert sel == '{"m","k"="a\\"b"}'

    def test_avg_by_function_shape(self):
        """Build an average-by-function expression with the expected shape."""
        expr = promql_query.avg_by_function(service_name='svc', window='5m')
        assert expr.startswith('histogram_avg(sum by (')
        assert '"function.name"' in expr
        assert 'increase(' in expr
        assert '[5m]' in expr

    def test_count_uses_increase_not_rate(self):
        """Build a count expression using increase rather than rate."""
        expr = promql_query.count_by_function(service_name='svc')
        assert 'histogram_count(increase(' in expr
        assert 'rate(' not in expr

    def test_topk_wrapping(self):
        """Wrap an expression in topk when a top limit is given."""
        expr = promql_query.avg_by_function(service_name='svc', top=5)
        assert expr.startswith('topk(5, ')

    def test_errors_adds_status_filter(self):
        """Add a status=error filter to the errors expression."""
        expr = promql_query.errors_by_function(service_name='svc')
        assert '"status"="error"' in expr

    def test_hours_to_window(self):
        """Convert an hours value into a PromQL window string."""
        assert promql_query.hours_to_window(1) == '1h'
        assert promql_query.hours_to_window(24) == '24h'
        assert promql_query.hours_to_window(0) == promql_query.DEFAULT_RATE_WINDOW

    def test_vector_to_function_records_merges_line(self):
        """Merge the function line number into vector records."""
        result = [
            {
                'metric': {'function.name': 'f1', 'aws.service_events.function_at_line': '10'},
                'value': [123, '5.0'],
            },
            {'metric': {'function.name': 'f2'}, 'value': [123, '9.0']},
        ]
        recs = promql_query.vector_to_function_records(result, 'avg_us')
        assert recs['f1']['avg_us'] == 5.0
        assert recs['f1']['line'] == 10
        assert recs['f2']['avg_us'] == 9.0
        assert 'line' not in recs['f2']

    def test_vector_to_function_records_skips_bad_values(self):
        """Skip vector records whose value is not numeric."""
        result = [{'metric': {'function.name': 'f1'}, 'value': [123, 'notanumber']}]
        assert promql_query.vector_to_function_records(result, 'v') == {}


# ============================================================================
# Client request / response handling
# ============================================================================


class TestMakeRequest:
    """Tests for PromQL client request and response handling."""

    def test_success_returns_data(self):
        """Return the data payload on a successful response."""
        payload = {'status': 'success', 'data': {'resultType': 'vector', 'result': [1, 2]}}
        p, fake = _patch_http(_FakeResponse(200, payload))
        with p:
            data = promql_client.make_request('query', {'query': 'up'})
        assert data == {'resultType': 'vector', 'result': [1, 2]}
        # Signed request was sent once.
        assert fake.send.call_count == 1

    def test_prometheus_error_raises(self):
        """Raise on a Prometheus error status response."""
        payload = {'status': 'error', 'errorType': 'bad_data', 'error': 'boom'}
        p, _ = _patch_http(_FakeResponse(400, payload))
        with p, pytest.raises(PromQLQueryError, match='boom'):
            promql_client.make_request('query', {'query': 'bad'})

    def test_invalid_json_raises(self):
        """Raise when the response body is not valid JSON."""
        p, _ = _patch_http(_FakeResponse(200, text='<html>not json</html>'))
        with p, pytest.raises(PromQLQueryError, match='Invalid JSON'):
            promql_client.make_request('query', {'query': 'up'})

    def test_server_error_retries_then_fails(self):
        """Retry on server errors and fail after max attempts."""
        fake = MagicMock()
        fake.send.return_value = _FakeResponse(503, text='unavailable')
        with (
            patch.object(promql_client, '_get_http_session', return_value=fake),
            patch.object(promql_client, '_sleep_backoff', lambda *_: None),
        ):
            with pytest.raises(PromQLQueryError, match='after .* attempts'):
                promql_client.make_request('query', {'query': 'up'})
        assert fake.send.call_count == promql_client.MAX_RETRIES

    def test_instant_query_helper(self):
        """Return vector data from the instant query helper."""
        payload = {'status': 'success', 'data': {'resultType': 'vector', 'result': []}}
        p, _ = _patch_http(_FakeResponse(200, payload))
        with p:
            out = promql_client.instant_query('up', time_param='123')
        assert out['resultType'] == 'vector'

    def test_label_values_sorted(self):
        """Return label values sorted alphabetically."""
        payload = {'status': 'success', 'data': ['c', 'a', 'b']}
        p, _ = _patch_http(_FakeResponse(200, payload))
        with p:
            out = promql_client.label_values_query('function.name')
        assert out == ['a', 'b', 'c']

    def test_series_query_returns_list(self):
        """Return the series list from a series query."""
        payload = {'status': 'success', 'data': [{'__name__': 'm'}]}
        p, _ = _patch_http(_FakeResponse(200, payload))
        with p:
            out = promql_client.series_query(['{"m"}'], start='1', end='2')
        assert out == [{'__name__': 'm'}]


class TestMatchParamEncoding:
    """match[] must be signed as a single string, not a list (else SigV4 403)."""

    def test_single_selector_is_string(self):
        """Encode a single selector as a bare string."""
        assert promql_client._match_param(['{"m"}']) == '{"m"}'

    def test_none_when_empty(self):
        """Return None for empty or missing selectors."""
        assert promql_client._match_param(None) is None
        assert promql_client._match_param([]) is None

    def test_multiple_selectors_uses_first(self):
        """Use the first selector when multiple are supplied."""
        assert promql_client._match_param(['{"a"}', '{"b"}']) == '{"a"}'

    def test_label_values_passes_string_match(self):
        """Send the match parameter as a string, never a list."""
        payload = {'status': 'success', 'data': ['x']}
        captured = {}

        def _fake_make_request(endpoint, params=None, region=None):
            captured['params'] = params
            return payload['data']

        with patch.object(promql_client, 'make_request', _fake_make_request):
            promql_client.label_values_query('function.name', match=['{"m"}'])
        # The value sent must be a bare string, never a list.
        assert captured['params']['match[]'] == '{"m"}'
        assert not isinstance(captured['params']['match[]'], list)
