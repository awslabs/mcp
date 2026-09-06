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

"""Tests for dynamic_instrumentation/snapshot_queries.py."""

import boto3
from awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.snapshot_queries import (
    _execute_cloudwatch_query,
)
from botocore.exceptions import ClientError
from botocore.stub import Stubber
from unittest.mock import MagicMock, patch


TIME = 'awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.snapshot_queries.time'
LOGS_CLIENT = 'awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.snapshot_queries.aws_clients.logs_client'


def _stub_logs():
    """Patch the shared parent logs_client with a stubbed client for the test."""
    client = boto3.client('logs', region_name='us-east-1')
    stubber = Stubber(client)
    stubber.activate()
    patcher = patch(LOGS_CLIENT, client)
    patcher.start()
    return stubber, patcher


class TestExecuteCloudwatchQuery:
    """Cover the start/poll lifecycle of _execute_cloudwatch_query."""

    @patch(TIME)
    def test_success_complete(self, mock_time):
        """Successful query returns parsed results."""
        mock_time.time.side_effect = [0, 1]
        mock_time.sleep = MagicMock()
        stubber, patcher = _stub_logs()
        try:
            stubber.add_response('start_query', {'queryId': 'q-1'})
            stubber.add_response(
                'get_query_results',
                {
                    'status': 'Complete',
                    'results': [[{'field': '@timestamp', 'value': '2024-01-01'}]],
                    'statistics': {
                        'recordsMatched': 1.0,
                        'recordsScanned': 1.0,
                        'bytesScanned': 100.0,
                    },
                },
            )
            result = _execute_cloudwatch_query(
                'fields @timestamp', 1000, 2000, log_group_name='/test/log-group'
            )
            stubber.assert_no_pending_responses()
        finally:
            patcher.stop()
        assert result['status'] == 'Complete'
        assert result['queryId'] == 'q-1'
        assert len(result['results']) == 1
        assert result['results'][0]['@timestamp'] == '2024-01-01'

    def test_start_failure(self):
        """A start_query client error is reported as an error result."""
        stubber, patcher = _stub_logs()
        try:
            stubber.add_client_error(
                'start_query',
                service_error_code='AccessDenied',
                service_message='access denied',
            )
            result = _execute_cloudwatch_query(
                'fields @timestamp', 1000, 2000, log_group_name='/test/log-group'
            )
        finally:
            patcher.stop()
        assert result['status'] == 'Error'
        assert 'Failed to start query' in result['error']

    @patch(TIME)
    def test_poll_failure(self, mock_time):
        """A get_query_results client error is reported as an error result."""
        mock_time.time.side_effect = [0, 1]
        mock_time.sleep = MagicMock()
        stubber, patcher = _stub_logs()
        try:
            stubber.add_response('start_query', {'queryId': 'q-1'})
            stubber.add_client_error(
                'get_query_results',
                service_error_code='ThrottlingException',
                service_message='slow down',
            )
            result = _execute_cloudwatch_query(
                'fields @timestamp', 1000, 2000, log_group_name='/test/log-group'
            )
        finally:
            patcher.stop()
        assert result['status'] == 'Error'
        assert 'Failed to get results' in result['error']
        assert result['queryId'] == 'q-1'

    @patch(TIME)
    def test_failed_status(self, mock_time):
        """A Failed query status is surfaced verbatim."""
        mock_time.time.side_effect = [0, 1]
        mock_time.sleep = MagicMock()
        stubber, patcher = _stub_logs()
        try:
            stubber.add_response('start_query', {'queryId': 'q-1'})
            stubber.add_response(
                'get_query_results',
                {
                    'status': 'Failed',
                    'results': [],
                    'statistics': {
                        'recordsMatched': 0.0,
                        'recordsScanned': 0.0,
                        'bytesScanned': 0.0,
                    },
                },
            )
            result = _execute_cloudwatch_query(
                'fields @timestamp', 1000, 2000, log_group_name='/test/log-group'
            )
        finally:
            patcher.stop()
        assert result['status'] == 'Failed'

    @patch(TIME)
    def test_poll_timeout(self, mock_time):
        """Polling past max_timeout returns a timeout result."""
        # First time.time() is poll_start, next call is past max_timeout — loop exits.
        mock_time.time.side_effect = [0, 100]
        mock_time.sleep = MagicMock()
        stubber, patcher = _stub_logs()
        try:
            stubber.add_response('start_query', {'queryId': 'q-1'})
            result = _execute_cloudwatch_query(
                'fields @timestamp', 1000, 2000, log_group_name='/test/log-group', max_timeout=30
            )
        finally:
            patcher.stop()
        assert result['status'] == 'Polling Timeout'

    def test_start_query_unexpected_exception(self):
        """An unexpected (non-ClientError) start exception is captured."""
        with patch(LOGS_CLIENT, _RaisingClient(start_exc=RuntimeError('unexpected'))):
            result = _execute_cloudwatch_query(
                'fields @timestamp', 1000, 2000, log_group_name='/test/log-group'
            )
        assert result['status'] == 'Error'
        assert 'unexpected' in result['error']

    def test_start_query_missing_query_id(self):
        """A start response without a queryId is reported as an error."""
        with patch(LOGS_CLIENT, _FakeClient(start_response={})):
            result = _execute_cloudwatch_query(
                'fields @timestamp', 1000, 2000, log_group_name='/test/log-group'
            )
        assert result['status'] == 'Error'
        assert 'did not return a queryId' in result['error']


class _FakeClient:
    """Minimal duck-typed CloudWatch Logs client for tests that bypass Stubber."""

    def __init__(self, start_response=None):
        """Store the canned start_query response."""
        self._start_response = start_response or {}

    def start_query(self, **_kwargs):
        """Return the canned start_query response."""
        return self._start_response


class _RaisingClient:
    """A client whose start_query raises a configured exception."""

    def __init__(self, start_exc=None):
        """Store the exception start_query should raise."""
        self._start_exc = start_exc

    def start_query(self, **_kwargs):
        """Raise the configured start exception."""
        if self._start_exc is not None:
            raise self._start_exc

    def get_query_results(self, **_kwargs):
        """Raise a ClientError for completeness."""
        raise ClientError({'Error': {'Code': 'x', 'Message': 'x'}}, 'GetQueryResults')
