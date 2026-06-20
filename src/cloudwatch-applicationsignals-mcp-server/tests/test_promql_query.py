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

"""Tests for the quoted-label PromQL query builders (promql_query module)."""

from awslabs.cloudwatch_applicationsignals_mcp_server.service_events import promql_query


class TestEscapeAndSelector:
    """Escaping and selector construction."""

    def test_escape_backslash_and_quote(self):
        """Escape both backslashes and double quotes in a literal."""
        assert promql_query._escape('a\\b"c') == 'a\\\\b\\"c'

    def test_build_selector_no_matchers(self):
        """A selector with no matchers is just the quoted metric name."""
        assert promql_query.build_selector('m') == '{"m"}'

    def test_build_selector_multiple_matchers(self):
        """Each matcher key and value is quoted in order."""
        sel = promql_query.build_selector('m', {'a': '1', 'b': '2'})
        assert sel == '{"m","a"="1","b"="2"}'


class TestFunctionMatchers:
    """All optional matcher branches in _function_matchers."""

    def test_all_matchers_present(self):
        """Every optional filter maps to its labelled matcher."""
        matchers = promql_query._function_matchers(
            service_name='svc',
            environment='prod',
            deployment_id='d-1',
            function_name='fn',
            status='error',
            operation='POST /checkout',
        )
        assert matchers == {
            promql_query.LABEL_SERVICE_NAME: 'svc',
            promql_query.LABEL_ENVIRONMENT: 'prod',
            promql_query.LABEL_DEPLOYMENT_ID: 'd-1',
            promql_query.LABEL_FUNCTION_NAME: 'fn',
            promql_query.LABEL_STATUS: 'error',
            promql_query.LABEL_OPERATION: 'POST /checkout',
        }

    def test_no_matchers_when_all_none(self):
        """No matchers are emitted when all filters are None."""
        assert promql_query._function_matchers(None) == {}

    def test_selector_includes_all_filters(self):
        """function_duration_selector threads every filter into the selector."""
        sel = promql_query.function_duration_selector(
            service_name='svc',
            environment='prod',
            deployment_id='d-1',
            function_name='fn',
            status='error',
            operation='op',
        )
        assert '"@resource.deployment.environment.name"="prod"' in sel
        assert '"@resource.aws.service_events.deployment.id"="d-1"' in sel
        assert '"function.name"="fn"' in sel
        assert '"status"="error"' in sel
        assert '"operation"="op"' in sel


class TestAggregationBuilders:
    """avg/count/errors expression builders, including topk and grouping."""

    def test_avg_by_function_topk(self):
        """avg_by_function wraps in topk when top is given."""
        expr = promql_query.avg_by_function(service_name='svc', top=3)
        assert expr.startswith('topk(3, histogram_avg(')

    def test_count_by_function_topk(self):
        """count_by_function wraps in topk when top is given."""
        expr = promql_query.count_by_function(service_name='svc', top=7)
        assert expr.startswith('topk(7, ')
        assert 'histogram_count(increase(' in expr

    def test_count_by_function_group_by_line_false(self):
        """Grouping drops the line label when group_by_line is False."""
        expr = promql_query.count_by_function(service_name='svc', group_by_line=False)
        assert '"aws.service_events.function_at_line"' not in expr
        assert 'sum by ("function.name")' in expr

    def test_count_by_function_group_by_line_true(self):
        """Grouping includes the line label by default."""
        expr = promql_query.count_by_function(service_name='svc')
        assert '"aws.service_events.function_at_line"' in expr

    def test_errors_by_function_default_status(self):
        """errors_by_function defaults the status filter to error."""
        expr = promql_query.errors_by_function(service_name='svc')
        assert '"status"="error"' in expr

    def test_errors_by_function_status_override(self):
        """errors_by_function keeps an explicit status filter."""
        expr = promql_query.errors_by_function(service_name='svc', status='fault')
        assert '"status"="fault"' in expr
        assert '"status"="error"' not in expr


class TestWindow:
    """hours_to_window mapping."""

    def test_positive_hours(self):
        """A positive hours value maps to an Nh window."""
        assert promql_query.hours_to_window(6) == '6h'

    def test_zero_and_negative_use_default(self):
        """Zero or negative hours fall back to the default window."""
        assert promql_query.hours_to_window(0) == promql_query.DEFAULT_RATE_WINDOW
        assert promql_query.hours_to_window(-5) == promql_query.DEFAULT_RATE_WINDOW


class TestValueOf:
    """_value_of parsing edge cases."""

    def test_missing_value(self):
        """An entry with no value field yields None."""
        assert promql_query._value_of({}) is None

    def test_short_value_list(self):
        """A value list shorter than two elements yields None."""
        assert promql_query._value_of({'value': [123]}) is None

    def test_non_numeric_value(self):
        """A non-numeric value string yields None."""
        assert promql_query._value_of({'value': [123, 'nope']}) is None

    def test_numeric_value(self):
        """A numeric value string is parsed to float."""
        assert promql_query._value_of({'value': [123, '4.5']}) == 4.5

    def test_nan_value(self):
        """A "NaN" value (e.g. histogram_avg over an empty window) yields None."""
        assert promql_query._value_of({'value': [123, 'NaN']}) is None

    def test_positive_inf_value(self):
        """A "+Inf" value yields None rather than a non-finite float."""
        assert promql_query._value_of({'value': [123, '+Inf']}) is None

    def test_inf_value(self):
        """An "Inf" value yields None."""
        assert promql_query._value_of({'value': [123, 'Inf']}) is None

    def test_negative_inf_value(self):
        """A "-Inf" value yields None."""
        assert promql_query._value_of({'value': [123, '-Inf']}) is None


class TestVectorToFunctionValue:
    """vector_to_function_value extraction."""

    def test_extracts_pairs(self):
        """Extract (function.name, value) pairs from an instant vector."""
        result = [
            {'metric': {'function.name': 'f1'}, 'value': [1, '2.0']},
            {'metric': {'function.name': 'f2'}, 'value': [1, '3.5']},
        ]
        assert promql_query.vector_to_function_value(result) == [('f1', 2.0), ('f2', 3.5)]

    def test_skips_missing_function_or_value(self):
        """Skip entries missing a function name or a parseable value."""
        result = [
            {'metric': {}, 'value': [1, '2.0']},  # no function name
            {'metric': {'function.name': 'f2'}, 'value': [1, 'bad']},  # bad value
            {'metric': {'function.name': 'f3'}, 'value': [1, '9.0']},  # kept
        ]
        assert promql_query.vector_to_function_value(result) == [('f3', 9.0)]

    def test_empty_or_none_result(self):
        """An empty or None result yields no pairs."""
        assert promql_query.vector_to_function_value([]) == []
        assert promql_query.vector_to_function_value(None) == []


class TestVectorToFunctionRecords:
    """vector_to_function_records indexing and line coercion."""

    def test_line_int_coercion(self):
        """A numeric line label is coerced to int."""
        result = [
            {
                'metric': {'function.name': 'f1', 'aws.service_events.function_at_line': '42'},
                'value': [1, '5.0'],
            }
        ]
        recs = promql_query.vector_to_function_records(result, 'avg_us')
        assert recs['f1'] == {'avg_us': 5.0, 'line': 42}

    def test_line_non_int_falls_back_to_raw(self):
        """A non-integer line label falls back to the raw string value."""
        result = [
            {
                'metric': {
                    'function.name': 'f1',
                    'aws.service_events.function_at_line': 'L10',
                },
                'value': [1, '5.0'],
            }
        ]
        recs = promql_query.vector_to_function_records(result, 'avg_us')
        assert recs['f1']['line'] == 'L10'

    def test_skips_entries_without_value(self):
        """Entries without a parseable value are skipped entirely."""
        result = [{'metric': {'function.name': 'f1'}, 'value': [1, 'bad']}]
        assert promql_query.vector_to_function_records(result, 'v') == {}


class TestErrorsByOperationException:
    """Tests for the count-metric error-pattern builder."""

    def test_basic_query_shape(self):
        """Builds a sum-by-(operation, exception) sum_over_time query on the count metric."""
        expr = promql_query.errors_by_operation_exception('svc', window='3h')
        assert expr == (
            'sum by (operation, exception) '
            '(sum_over_time({"count","@resource.service.name"="svc"}[3h]))'
        )

    def test_operation_and_environment_filters(self):
        """Operation and environment add quoted-label matchers to the selector."""
        expr = promql_query.errors_by_operation_exception(
            'svc', window='1h', operation='POST /x', environment='eks:e'
        )
        assert '"operation"="POST /x"' in expr
        assert '"@resource.deployment.environment.name"="eks:e"' in expr
        assert '"@resource.service.name"="svc"' in expr

    def test_top_wraps_in_topk(self):
        """A top value wraps the aggregation in topk()."""
        expr = promql_query.errors_by_operation_exception('svc', window='3h', top=5)
        assert expr.startswith('topk(5, ')


class TestVectorToErrorPatterns:
    """Tests for parsing the count-metric error-pattern result."""

    def test_maps_and_sorts_rows(self):
        """Rows map to {operation, exception, exception_type, count}, sorted by count."""
        result = [
            {
                'metric': {'operation': 'GET /a', 'exception': 'foo.Bar NotFound'},
                'value': [0, '10'],
            },
            {'metric': {'operation': 'POST /b', 'exception': 'baz Qux'}, 'value': [0, '30']},
        ]
        rows = promql_query.vector_to_error_patterns(result)
        assert rows == [
            {
                'operation': 'POST /b',
                'exception': 'baz Qux',
                'exception_type': 'Qux',
                'count': 30,
            },
            {
                'operation': 'GET /a',
                'exception': 'foo.Bar NotFound',
                'exception_type': 'NotFound',
                'count': 10,
            },
        ]

    def test_drops_series_without_exception(self):
        """Series with no exception label are dropped."""
        result = [{'metric': {'operation': 'GET /c'}, 'value': [0, '99']}]
        assert promql_query.vector_to_error_patterns(result) == []

    def test_drops_non_finite_values(self):
        """NaN/Inf counts are dropped (reusing the _value_of finite guard)."""
        result = [{'metric': {'operation': 'GET /d', 'exception': 'x Y'}, 'value': [0, 'NaN']}]
        assert promql_query.vector_to_error_patterns(result) == []

    def test_exception_without_space_keeps_full_string(self):
        """An exception label with no space uses the full string as the short name."""
        result = [{'metric': {'operation': 'GET /e', 'exception': 'BareName'}, 'value': [0, '2']}]
        rows = promql_query.vector_to_error_patterns(result)
        assert rows[0]['exception_type'] == 'BareName'

    def test_top_caps_rows(self):
        """The top arg caps the number of returned rows (after sorting)."""
        result = [
            {'metric': {'operation': f'op{i}', 'exception': f'e E{i}'}, 'value': [0, str(i)]}
            for i in range(5)
        ]
        rows = promql_query.vector_to_error_patterns(result, top=2)
        assert [r['count'] for r in rows] == [4, 3]

    def test_none_result_yields_empty(self):
        """A None result yields an empty list."""
        assert promql_query.vector_to_error_patterns(None) == []
