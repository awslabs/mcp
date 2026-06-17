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

"""Tests for endpoint_metrics per-operation RED metrics from Application Signals."""

from awslabs.cloudwatch_applicationsignals_mcp_server import endpoint_metrics
from awslabs.cloudwatch_applicationsignals_mcp_server.endpoint_metrics import (
    _find_service_key_attributes,
    _latency_stats,
    _period_for_hours,
    _sum_datapoints,
    get_endpoint_red_metrics,
)
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


_NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)
_LATER = datetime(2024, 1, 2, tzinfo=timezone.utc)


class TestPeriodForHours:
    """Tests for _period_for_hours bucket selection."""

    def test_short_range_60s(self):
        """<= 3 hours picks a 60s period."""
        assert _period_for_hours(1) == 60
        assert _period_for_hours(3) == 60

    def test_medium_range_300s(self):
        """<= 24 hours (but > 3) picks a 300s period."""
        assert _period_for_hours(4) == 300
        assert _period_for_hours(24) == 300

    def test_long_range_3600s(self):
        """> 24 hours picks a 3600s period."""
        assert _period_for_hours(25) == 3600
        assert _period_for_hours(168) == 3600


class TestFindServiceKeyAttributes:
    """Tests for _find_service_key_attributes paginated lookup."""

    def test_found_first_page(self):
        """The matching service's KeyAttributes are returned from the first page."""
        mock_client = MagicMock()
        mock_client.list_services.return_value = {
            'ServiceSummaries': [
                {'KeyAttributes': {'Name': 'other-service'}},
                {'KeyAttributes': {'Name': 'my-service', 'Type': 'Service'}},
            ],
            'NextToken': None,
        }
        with patch.object(
            endpoint_metrics, 'get_applicationsignals_client', return_value=mock_client
        ):
            result = _find_service_key_attributes('my-service', _NOW, _LATER)
        assert result == {'Name': 'my-service', 'Type': 'Service'}
        mock_client.list_services.assert_called_once()

    def test_found_on_second_page(self):
        """Pagination follows NextToken until the service is found."""
        mock_client = MagicMock()
        mock_client.list_services.side_effect = [
            {'ServiceSummaries': [{'KeyAttributes': {'Name': 'a'}}], 'NextToken': 'tok'},
            {'ServiceSummaries': [{'KeyAttributes': {'Name': 'target'}}], 'NextToken': None},
        ]
        with patch.object(
            endpoint_metrics, 'get_applicationsignals_client', return_value=mock_client
        ):
            result = _find_service_key_attributes('target', _NOW, _LATER)
        assert result == {'Name': 'target'}
        assert mock_client.list_services.call_count == 2
        # Second call passes the NextToken.
        _, kwargs = mock_client.list_services.call_args
        assert kwargs['NextToken'] == 'tok'

    def test_not_found_returns_none(self):
        """When no service matches and pagination ends, None is returned."""
        mock_client = MagicMock()
        mock_client.list_services.return_value = {
            'ServiceSummaries': [{'KeyAttributes': {'Name': 'nope'}}],
            'NextToken': None,
        }
        with patch.object(
            endpoint_metrics, 'get_applicationsignals_client', return_value=mock_client
        ):
            result = _find_service_key_attributes('missing', _NOW, _LATER)
        assert result is None

    def test_empty_summaries_returns_none(self):
        """An empty ServiceSummaries list with no NextToken returns None."""
        mock_client = MagicMock()
        mock_client.list_services.return_value = {}
        with patch.object(
            endpoint_metrics, 'get_applicationsignals_client', return_value=mock_client
        ):
            result = _find_service_key_attributes('missing', _NOW, _LATER)
        assert result is None

    def test_summary_without_name_is_skipped(self):
        """A service summary whose KeyAttributes lack a Name is skipped, not matched."""
        mock_client = MagicMock()
        mock_client.list_services.return_value = {
            'ServiceSummaries': [
                {'KeyAttributes': {'Type': 'Service'}},  # no Name -> skipped
                {'KeyAttributes': {'Name': 'target', 'Type': 'Service'}},
            ],
            'NextToken': None,
        }
        with patch.object(
            endpoint_metrics, 'get_applicationsignals_client', return_value=mock_client
        ):
            result = _find_service_key_attributes('target', _NOW, _LATER)
        assert result == {'Name': 'target', 'Type': 'Service'}

    def test_first_case_insensitive_match_wins(self):
        """With multiple case-insensitive (non-exact) matches, the first is kept."""
        mock_client = MagicMock()
        mock_client.list_services.return_value = {
            'ServiceSummaries': [
                {'KeyAttributes': {'Name': 'SVC', 'Environment': 'eks:a'}},
                {'KeyAttributes': {'Name': 'Svc', 'Environment': 'eks:b'}},
            ],
            'NextToken': None,
        }
        with patch.object(
            endpoint_metrics, 'get_applicationsignals_client', return_value=mock_client
        ):
            result = _find_service_key_attributes('svc', _NOW, _LATER)
        # First case-insensitive match is retained; the second does not overwrite it.
        assert result == {'Name': 'SVC', 'Environment': 'eks:a'}


class TestSumDatapoints:
    """Tests for _sum_datapoints aggregation."""

    def test_sums_sum_and_samplecount(self):
        """Sum and SampleCount are accumulated across datapoints."""
        mock_cw = MagicMock()
        mock_cw.get_metric_statistics.return_value = {
            'Datapoints': [
                {'Sum': 10, 'SampleCount': 3},
                {'Sum': 5, 'SampleCount': 2},
            ]
        }
        ref = {'Namespace': 'NS', 'MetricName': 'M', 'Dimensions': [{'Name': 'd', 'Value': 'v'}]}
        with patch.object(endpoint_metrics, 'get_cloudwatch_client', return_value=mock_cw):
            total_sum, total_count = _sum_datapoints(ref, _NOW, _LATER, 300)
        assert total_sum == 15
        assert total_count == 5
        _, kwargs = mock_cw.get_metric_statistics.call_args
        assert kwargs['Namespace'] == 'NS'
        assert kwargs['MetricName'] == 'M'
        assert kwargs['Period'] == 300

    def test_empty_datapoints(self):
        """No datapoints yields (0, 0)."""
        mock_cw = MagicMock()
        mock_cw.get_metric_statistics.return_value = {'Datapoints': []}
        ref = {'Namespace': 'NS', 'MetricName': 'M'}
        with patch.object(endpoint_metrics, 'get_cloudwatch_client', return_value=mock_cw):
            assert _sum_datapoints(ref, _NOW, _LATER, 60) == (0, 0)

    def test_none_values_treated_as_zero(self):
        """None Sum/SampleCount values are coerced to zero."""
        mock_cw = MagicMock()
        mock_cw.get_metric_statistics.return_value = {
            'Datapoints': [{'Sum': None, 'SampleCount': None}, {'Sum': 4, 'SampleCount': 1}]
        }
        ref = {'Namespace': 'NS', 'MetricName': 'M'}
        with patch.object(endpoint_metrics, 'get_cloudwatch_client', return_value=mock_cw):
            assert _sum_datapoints(ref, _NOW, _LATER, 60) == (4, 1)


class TestLatencyStats:
    """Tests for _latency_stats edge cases."""

    def test_empty_datapoints_returns_none(self):
        """No datapoints returns (None, None, 0)."""
        mock_cw = MagicMock()
        mock_cw.get_metric_statistics.return_value = {'Datapoints': []}
        ref = {'Namespace': 'NS', 'MetricName': 'Latency'}
        with patch.object(endpoint_metrics, 'get_cloudwatch_client', return_value=mock_cw):
            assert _latency_stats(ref, _NOW, _LATER, 60, 99) == (None, None, 0)

    def test_single_datapoint(self):
        """A single datapoint yields its average and percentile."""
        mock_cw = MagicMock()
        mock_cw.get_metric_statistics.return_value = {
            'Datapoints': [
                {'Average': 100.0, 'SampleCount': 4, 'ExtendedStatistics': {'p99': 250.5}}
            ]
        }
        ref = {'Namespace': 'NS', 'MetricName': 'Latency'}
        with patch.object(endpoint_metrics, 'get_cloudwatch_client', return_value=mock_cw):
            avg, pval, count = _latency_stats(ref, _NOW, _LATER, 60, 99)
        assert avg == 100.0
        assert pval == 250.5
        assert count == 4
        _, kwargs = mock_cw.get_metric_statistics.call_args
        assert kwargs['ExtendedStatistics'] == ['p99']

    def test_weighted_average_and_max_percentile(self):
        """Average is sample-count weighted; percentile is the max across datapoints."""
        mock_cw = MagicMock()
        mock_cw.get_metric_statistics.return_value = {
            'Datapoints': [
                {'Average': 100.0, 'SampleCount': 1, 'ExtendedStatistics': {'p90': 150.0}},
                {'Average': 200.0, 'SampleCount': 3, 'ExtendedStatistics': {'p90': 400.0}},
            ]
        }
        ref = {'Namespace': 'NS', 'MetricName': 'Latency'}
        with patch.object(endpoint_metrics, 'get_cloudwatch_client', return_value=mock_cw):
            avg, pval, count = _latency_stats(ref, _NOW, _LATER, 60, 90)
        # (100*1 + 200*3) / 4 = 175.0
        assert avg == 175.0
        assert pval == 400.0
        assert count == 4

    def test_zero_total_count_avg_none(self):
        """Datapoints with zero total sample count yield a None average."""
        mock_cw = MagicMock()
        mock_cw.get_metric_statistics.return_value = {
            'Datapoints': [{'Average': 100.0, 'SampleCount': 0, 'ExtendedStatistics': {}}]
        }
        ref = {'Namespace': 'NS', 'MetricName': 'Latency'}
        with patch.object(endpoint_metrics, 'get_cloudwatch_client', return_value=mock_cw):
            avg, pval, count = _latency_stats(ref, _NOW, _LATER, 60, 99)
        assert avg is None
        # No percentile value present -> None.
        assert pval is None
        assert count == 0


class TestGetEndpointRedMetrics:
    """Tests for the get_endpoint_red_metrics entry point."""

    def test_service_not_found_returns_not_found(self):
        """When the service KeyAttributes are not found, a not-found diagnostic is returned."""
        mock_as = MagicMock()
        mock_as.list_services.return_value = {'ServiceSummaries': [], 'NextToken': None}
        with patch.object(endpoint_metrics, 'get_applicationsignals_client', return_value=mock_as):
            summaries, not_found = get_endpoint_red_metrics('missing', hours=24)
        assert summaries == []
        assert not_found is not None
        assert not_found['status'] == 'service_not_found'
        assert 'missing' in not_found['message']

    def test_not_found_message_includes_environment(self):
        """When an environment is given, the not-found message names it."""
        mock_as = MagicMock()
        mock_as.list_services.return_value = {'ServiceSummaries': [], 'NextToken': None}
        with patch.object(endpoint_metrics, 'get_applicationsignals_client', return_value=mock_as):
            _, not_found = get_endpoint_red_metrics('missing', environment='eks:prod')
        assert not_found is not None
        assert 'eks:prod' in not_found['message']

    def test_happy_path_all_metric_types(self):
        """A full operation with LATENCY/FAULT/ERROR metrics produces a complete summary."""
        key_attrs = {'Name': 'svc', 'Type': 'Service'}
        mock_as = MagicMock()
        mock_as.list_services.return_value = {
            'ServiceSummaries': [{'KeyAttributes': key_attrs}],
            'NextToken': None,
        }
        # The API returns operations under "ServiceOperations" with UPPERCASE MetricType.
        mock_as.list_service_operations.return_value = {
            'ServiceOperations': [
                {
                    'Name': 'GET /orders',
                    'MetricReferences': [
                        {'MetricType': 'LATENCY', 'Namespace': 'NS', 'MetricName': 'Latency'},
                        {'MetricType': 'FAULT', 'Namespace': 'NS', 'MetricName': 'Fault'},
                        {'MetricType': 'ERROR', 'Namespace': 'NS', 'MetricName': 'Error'},
                    ],
                }
            ],
            'NextToken': None,
        }

        mock_cw = MagicMock()

        def _stats(**kwargs):
            if kwargs.get('MetricName') == 'Latency':
                return {
                    'Datapoints': [
                        {'Average': 50.0, 'SampleCount': 10, 'ExtendedStatistics': {'p99': 120.0}}
                    ]
                }
            if kwargs.get('MetricName') == 'Fault':
                return {'Datapoints': [{'Sum': 2, 'SampleCount': 10}]}
            if kwargs.get('MetricName') == 'Error':
                return {'Datapoints': [{'Sum': 3, 'SampleCount': 10}]}
            return {'Datapoints': []}

        mock_cw.get_metric_statistics.side_effect = _stats

        with (
            patch.object(endpoint_metrics, 'get_applicationsignals_client', return_value=mock_as),
            patch.object(endpoint_metrics, 'get_cloudwatch_client', return_value=mock_cw),
        ):
            summaries, not_found = get_endpoint_red_metrics('svc', hours=24, percentile=99)

        assert not_found is None
        assert len(summaries) == 1
        summary = summaries[0]
        assert summary['operation'] == 'GET /orders'
        assert summary['service_name'] == 'svc'
        assert summary['total_requests'] == 10
        assert summary['total_faults'] == 2
        assert summary['total_errors'] == 3
        assert summary['avg_duration_ms'] == 50.0
        assert summary['p99_duration_ms'] == 120.0
        # list_service_operations was called with the resolved KeyAttributes.
        _, kwargs = mock_as.list_service_operations.call_args
        assert kwargs['KeyAttributes'] == key_attrs

    def test_operation_filter_excludes_non_matching(self):
        """The operation filter (case-insensitive substring) excludes non-matching ops."""
        mock_as = MagicMock()
        mock_as.list_services.return_value = {
            'ServiceSummaries': [{'KeyAttributes': {'Name': 'svc'}}],
            'NextToken': None,
        }
        mock_as.list_service_operations.return_value = {
            'ServiceOperations': [
                {'Name': 'GET /orders', 'MetricReferences': []},
                {'Name': 'POST /payments', 'MetricReferences': []},
            ],
            'NextToken': None,
        }
        mock_cw = MagicMock()
        with (
            patch.object(endpoint_metrics, 'get_applicationsignals_client', return_value=mock_as),
            patch.object(endpoint_metrics, 'get_cloudwatch_client', return_value=mock_cw),
        ):
            summaries, not_found = get_endpoint_red_metrics('svc', operation='PAYMENTS')
        assert not_found is None
        assert len(summaries) == 1
        assert summaries[0]['operation'] == 'POST /payments'
        # No metric refs -> defaults, and CloudWatch was never queried.
        assert summaries[0]['total_requests'] == 0
        assert summaries[0]['avg_duration_ms'] is None
        mock_cw.get_metric_statistics.assert_not_called()

    def test_operations_paginated(self):
        """list_service_operations pagination is followed via NextToken."""
        mock_as = MagicMock()
        mock_as.list_services.return_value = {
            'ServiceSummaries': [{'KeyAttributes': {'Name': 'svc'}}],
            'NextToken': None,
        }
        mock_as.list_service_operations.side_effect = [
            {'ServiceOperations': [{'Name': 'op-a', 'MetricReferences': []}], 'NextToken': 'next'},
            {'ServiceOperations': [{'Name': 'op-b', 'MetricReferences': []}], 'NextToken': None},
        ]
        with patch.object(endpoint_metrics, 'get_applicationsignals_client', return_value=mock_as):
            summaries, not_found = get_endpoint_red_metrics('svc')
        assert not_found is None
        assert {r['operation'] for r in summaries} == {'op-a', 'op-b'}
        assert mock_as.list_service_operations.call_count == 2
        _, kwargs = mock_as.list_service_operations.call_args
        assert kwargs['NextToken'] == 'next'

    def test_limit_caps_results(self):
        """The limit parameter caps the number of summaries returned."""
        mock_as = MagicMock()
        mock_as.list_services.return_value = {
            'ServiceSummaries': [{'KeyAttributes': {'Name': 'svc'}}],
            'NextToken': None,
        }
        mock_as.list_service_operations.return_value = {
            'ServiceOperations': [{'Name': f'op-{i}', 'MetricReferences': []} for i in range(5)],
            'NextToken': None,
        }
        with patch.object(endpoint_metrics, 'get_applicationsignals_client', return_value=mock_as):
            summaries, not_found = get_endpoint_red_metrics('svc', limit=2)
        assert not_found is None
        assert len(summaries) == 2

    def test_failure_path_raises(self):
        """An AWS failure during operation listing propagates to the caller."""
        mock_as = MagicMock()
        mock_as.list_services.return_value = {
            'ServiceSummaries': [{'KeyAttributes': {'Name': 'svc'}}],
            'NextToken': None,
        }
        mock_as.list_service_operations.side_effect = RuntimeError('boom')
        with patch.object(endpoint_metrics, 'get_applicationsignals_client', return_value=mock_as):
            try:
                get_endpoint_red_metrics('svc')
                raised = False
            except RuntimeError as e:
                raised = str(e) == 'boom'
        assert raised

    def test_case_insensitive_name_match(self):
        """A case-insensitive Name match resolves the service (exact match preferred)."""
        mock_as = MagicMock()
        mock_as.list_services.return_value = {
            'ServiceSummaries': [
                {'KeyAttributes': {'Name': 'Billing-Service', 'Type': 'Service'}}
            ],
            'NextToken': None,
        }
        mock_as.list_service_operations.return_value = {
            'ServiceOperations': [{'Name': 'GET /x', 'MetricReferences': []}],
            'NextToken': None,
        }
        with patch.object(endpoint_metrics, 'get_applicationsignals_client', return_value=mock_as):
            summaries, not_found = get_endpoint_red_metrics('billing-service')
        assert not_found is None
        assert len(summaries) == 1

    def test_environment_disambiguates_same_name(self):
        """When environment is given, only the service in that environment resolves."""
        mock_as = MagicMock()
        mock_as.list_services.return_value = {
            'ServiceSummaries': [
                {'KeyAttributes': {'Name': 'svc', 'Environment': 'eks:dev'}},
                {'KeyAttributes': {'Name': 'svc', 'Environment': 'eks:prod'}},
            ],
            'NextToken': None,
        }
        mock_as.list_service_operations.return_value = {
            'ServiceOperations': [],
            'NextToken': None,
        }
        with patch.object(endpoint_metrics, 'get_applicationsignals_client', return_value=mock_as):
            _, not_found = get_endpoint_red_metrics('svc', environment='eks:prod')
        assert not_found is None
        # The prod KeyAttributes (not dev) were used for the operations query.
        _, kwargs = mock_as.list_service_operations.call_args
        assert kwargs['KeyAttributes']['Environment'] == 'eks:prod'
