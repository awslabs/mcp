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

"""Tests for the function_metrics PromQL (CloudWatch Metrics V2) layer."""

from awslabs.cloudwatch_applicationsignals_mcp_server.service_events import function_metrics
from unittest.mock import patch


# ============================================================================
# function_metrics: fetch + merge + sort
# ============================================================================


class TestFunctionMetrics:
    """Tests for fetching, merging, sorting, and searching function metrics."""

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.function_metrics.promql_client.instant_query'
    )
    def test_fetch_merges_avg_count_errors(self, mock_query):
        """Merge avg, count, and error series into one record per function."""
        # avg (µs), count, errors — returned in call order.
        mock_query.side_effect = [
            {
                'result': [
                    {
                        'metric': {
                            'function.name': 'f1',
                            'aws.service_events.function_at_line': '10',
                        },
                        'value': [0, '5000.0'],
                    }
                ]
            },  # avg_us = 5000 -> 5.0 ms
            {'result': [{'metric': {'function.name': 'f1'}, 'value': [0, '100']}]},  # calls
            {'result': [{'metric': {'function.name': 'f1'}, 'value': [0, '3']}]},  # errors
        ]
        recs = function_metrics.fetch_function_records(service_name='svc', hours=1)
        assert len(recs) == 1
        r = recs[0]
        assert r['name'] == 'f1'
        assert r['line'] == 10
        assert r['calls'] == 100
        assert r['avg_duration_ms'] == 5.0
        assert r['errors'] == 3

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.function_metrics.promql_client.instant_query'
    )
    def test_fetch_union_of_functions(self, mock_query):
        """Return the union of functions across all metric series."""
        mock_query.side_effect = [
            {'result': [{'metric': {'function.name': 'a'}, 'value': [0, '1000.0']}]},
            {'result': [{'metric': {'function.name': 'b'}, 'value': [0, '50']}]},
            {'result': []},
        ]
        recs = function_metrics.fetch_function_records(service_name='svc')
        assert {r['name'] for r in recs} == {'a', 'b'}

    def test_sort_and_limit_by_calls(self):
        """Sort by call count and limit the result set."""
        records = [
            {'name': 'a', 'calls': 10, 'avg_duration_ms': 5, 'errors': 0},
            {'name': 'b', 'calls': 99, 'avg_duration_ms': 1, 'errors': 0},
        ]
        out = function_metrics.sort_and_limit(records, 'calls', 1)
        assert [r['name'] for r in out] == ['b']

    def test_sort_by_duration_uses_avg(self):
        """Sort by duration using the average duration field."""
        records = [
            {'name': 'slow', 'calls': 1, 'avg_duration_ms': 500, 'errors': 0},
            {'name': 'fast', 'calls': 1, 'avg_duration_ms': 2, 'errors': 0},
        ]
        out = function_metrics.sort_and_limit(records, 'duration', 2)
        assert [r['name'] for r in out] == ['slow', 'fast']

    @patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.function_metrics.promql_client.label_values_query'
    )
    def test_search_filters_substring_case_insensitive(self, mock_lv):
        """Filter function names by case-insensitive substring match."""
        mock_lv.return_value = ['mod.process_a', 'mod.handle', 'mod.PROCESS_b']
        out = function_metrics.search_function_names('process', service_name='svc')
        assert out == ['mod.process_a', 'mod.PROCESS_b']
