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

"""Tests for the vended metrics PromQL client."""

import json
import pytest
from awslabs.aws_healthomics_mcp_server.metrics.client import (
    MAX_DATAPOINTS_PER_SERIES,
    TimeSeries,
    VendedMetricsClient,
    compute_step_seconds,
    summarize_series,
)
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch


START = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)


class TestSummarizeSeries:
    """Summary statistics per instrument type."""

    def test_empty_series(self):
        summary = summarize_series(TimeSeries(labels={}), is_counter=False)
        assert summary.datapoint_count == 0
        assert summary.minimum is None
        assert summary.average_rate is None

    def test_gauge_summary(self):
        series = TimeSeries(labels={}, timestamps=[0, 60, 120], values=[1.0, 3.0, 2.0])
        summary = summarize_series(series, is_counter=False)
        assert summary.datapoint_count == 3
        assert summary.minimum == 1.0
        assert summary.maximum == 3.0
        assert summary.average == 2.0
        assert summary.last == 2.0
        assert summary.total_delta is None

    def test_counter_delta_and_rate(self):
        """Counters report the window increase and per-second average rate."""
        series = TimeSeries(labels={}, timestamps=[0, 50, 100], values=[100.0, 500.0, 1100.0])
        summary = summarize_series(series, is_counter=True)
        assert summary.total_delta == 1000.0
        assert summary.average_rate == 10.0

    def test_counter_reset_falls_back_to_last_total(self):
        """A restart resets the counter; report the last total, never negative."""
        series = TimeSeries(labels={}, timestamps=[0, 60], values=[900.0, 200.0])
        summary = summarize_series(series, is_counter=True)
        assert summary.total_delta == 200.0

    def test_single_point_counter_has_no_delta(self):
        series = TimeSeries(labels={}, timestamps=[0], values=[42.0])
        summary = summarize_series(series, is_counter=True)
        assert summary.total_delta is None


class TestComputeStep:
    """Query step selection under the datapoint cap."""

    def test_default_step(self):
        assert compute_step_seconds(START, START + timedelta(hours=1), None) == 60

    def test_requested_step_respected(self):
        assert compute_step_seconds(START, START + timedelta(hours=1), 30) == 30

    def test_step_widened_for_long_windows(self):
        """A window that would exceed the datapoint cap widens the step."""
        window = timedelta(seconds=MAX_DATAPOINTS_PER_SERIES * 2)
        step = compute_step_seconds(START, START + window, 1)
        assert step > 1
        assert (window.total_seconds() / step) <= MAX_DATAPOINTS_PER_SERIES


def _mock_client(response_payload):
    """Build a VendedMetricsClient with mocked credentials and HTTP session."""
    with patch(
        'awslabs.aws_healthomics_mcp_server.metrics.client.get_aws_session'
    ) as mock_session:
        creds = MagicMock()
        creds.get_frozen_credentials.return_value = MagicMock(
            access_key='AK',
            secret_key='SK',  # pragma: allowlist secret
            token=None,
        )
        mock_session.return_value.region_name = 'us-east-1'
        mock_session.return_value.get_credentials.return_value = creds
        client = VendedMetricsClient()

    response = MagicMock()
    response.status_code = 200
    response.content = json.dumps(response_payload).encode()
    client._http = MagicMock()
    client._http.send.return_value = response
    return client


class TestVendedMetricsClient:
    """PromQL response parsing and error handling."""

    def test_query_range_parses_matrix(self):
        client = _mock_client(
            {
                'status': 'success',
                'data': {
                    'resultType': 'matrix',
                    'result': [
                        {
                            'metric': {'__name__': 'aws.omics.task.cpu.usage'},
                            'values': [[1000, '1.5'], [1060, '2.5']],
                        }
                    ],
                },
            }
        )
        series = client.query_range(
            '{"aws.omics.task.cpu.usage"}', START, START + timedelta(hours=1)
        )
        assert len(series) == 1
        assert series[0].values == [1.5, 2.5]
        assert series[0].timestamps == [1000.0, 1060.0]

    def test_instant_query_parses_vector(self):
        client = _mock_client(
            {
                'status': 'success',
                'data': {
                    'resultType': 'vector',
                    'result': [{'metric': {'x': 'y'}, 'value': [1000, '7']}],
                },
            }
        )
        series = client.instant_query('{"aws.omics.task.cpu.usage"}')
        assert series[0].values == [7.0]

    def test_series_returns_label_sets(self):
        client = _mock_client(
            {
                'status': 'success',
                'data': [{'__name__': 'aws.omics.task.cpu.usage'}],
            }
        )
        result = client.series(['{"aws.omics.task.cpu.usage"}'], START, START + timedelta(hours=1))
        assert result == [{'__name__': 'aws.omics.task.cpu.usage'}]

    def test_api_error_raises(self):
        client = _mock_client({'status': 'error', 'error': 'bad query'})
        with patch('awslabs.aws_healthomics_mcp_server.metrics.client.time_module.sleep'):
            with pytest.raises(RuntimeError, match='PromQL request failed'):
                client.instant_query('{"aws.omics.task.cpu.usage"}')

    def test_missing_credentials_raises(self):
        with patch(
            'awslabs.aws_healthomics_mcp_server.metrics.client.get_aws_session'
        ) as mock_session:
            mock_session.return_value.get_credentials.return_value = None
            with pytest.raises(ValueError, match='credentials'):
                VendedMetricsClient()


class TestQueryMetricSeries:
    """Series-cap avoidance and truncation detection."""

    def _client(self, batches):
        from unittest.mock import MagicMock

        client = MagicMock()
        client.query_range.side_effect = batches
        return client

    def test_direction_metric_queried_per_direction(self):
        from awslabs.aws_healthomics_mcp_server.metrics.client import query_metric_series

        client = self._client(
            [[TimeSeries(labels={'d': 'read'})], [TimeSeries(labels={'d': 'write'})]]
        )
        series, truncated = query_metric_series(
            client, 'aws.omics.task.filesystem.io', START, START + timedelta(hours=1), run_id='1'
        )
        assert len(series) == 2
        assert not truncated
        selectors = [c.args[0] for c in client.query_range.call_args_list]
        assert any('"filesystem.io.direction"="read"' in s for s in selectors)
        assert any('"filesystem.io.direction"="write"' in s for s in selectors)

    def test_explicit_direction_filter_disables_splitting(self):
        from awslabs.aws_healthomics_mcp_server.metrics.client import query_metric_series

        client = self._client([[]])
        query_metric_series(
            client,
            'aws.omics.task.filesystem.io',
            START,
            START + timedelta(hours=1),
            run_id='1',
            extra_labels={'filesystem.io.direction': 'read'},
        )
        assert client.query_range.call_count == 1

    def test_non_direction_metric_single_query(self):
        from awslabs.aws_healthomics_mcp_server.metrics.client import query_metric_series

        client = self._client([[]])
        query_metric_series(
            client, 'aws.omics.task.cpu.usage', START, START + timedelta(hours=1), run_id='1'
        )
        assert client.query_range.call_count == 1

    def test_cap_hit_flags_truncation(self):
        from awslabs.aws_healthomics_mcp_server.metrics.client import (
            MAX_SERIES_PER_QUERY,
            query_metric_series,
        )

        capped = [TimeSeries(labels={}) for _ in range(MAX_SERIES_PER_QUERY)]
        client = self._client([capped])
        series, truncated = query_metric_series(
            client, 'aws.omics.task.cpu.usage', START, START + timedelta(hours=1), run_id='1'
        )
        assert truncated
        assert len(series) == MAX_SERIES_PER_QUERY
