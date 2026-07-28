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

"""Tests for trace_tools X-Ray trace lookup (get_xray_trace + helpers)."""

import json
import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.trace_tools import (
    _convert_otel_to_xray_trace_id,
    _extract_segment_summary,
    _parse_xray_trace,
    _scan_for_issues,
    get_xray_trace,
)
from unittest.mock import MagicMock, patch


class TestConvertOtelToXrayTraceId:
    """Tests for OTel -> X-Ray trace ID conversion."""

    def test_otel_format_with_0x_prefix(self):
        """OTel 0x-prefixed 32-hex ID converts to X-Ray format."""
        result = _convert_otel_to_xray_trace_id('0xdeadbeefdeadbeefdeadbeefdeadbeef')
        assert result == '1-deadbeef-deadbeefdeadbeefdeadbeef'

    def test_raw_32_hex(self):
        """Raw 32-hex ID (no prefix) converts to X-Ray format."""
        result = _convert_otel_to_xray_trace_id('deadbeefdeadbeefdeadbeefdeadbeef')
        assert result == '1-deadbeef-deadbeefdeadbeefdeadbeef'

    def test_xray_format_passthrough(self):
        """Already-X-Ray-format IDs pass through unchanged."""
        xray_id = '1-deadbeef-deadbeefdeadbeefdeadbeef'
        result = _convert_otel_to_xray_trace_id(xray_id)
        assert result == xray_id

    def test_uppercase_hex(self):
        """Uppercase hex is normalized to lowercase."""
        result = _convert_otel_to_xray_trace_id('0xDEADBEEFDEADBEEFDEADBEEFDEADBEEF')
        assert result == '1-deadbeef-deadbeefdeadbeefdeadbeef'

    def test_uppercase_0x_prefix(self):
        """An uppercase 0X prefix is accepted."""
        result = _convert_otel_to_xray_trace_id('0Xdeadbeefdeadbeefdeadbeefdeadbeef')
        assert result == '1-deadbeef-deadbeefdeadbeefdeadbeef'

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace is stripped before conversion."""
        result = _convert_otel_to_xray_trace_id('  0xdeadbeefdeadbeefdeadbeefdeadbeef  ')
        assert result == '1-deadbeef-deadbeefdeadbeefdeadbeef'

    def test_invalid_too_short(self):
        """A too-short ID raises ValueError."""
        with pytest.raises(ValueError):
            _convert_otel_to_xray_trace_id('0xabc123')

    def test_invalid_non_hex(self):
        """A non-hex ID raises ValueError."""
        with pytest.raises(ValueError):
            _convert_otel_to_xray_trace_id('0xzzzz34c6deadbeefdeadbeefdeadbeef')

    def test_invalid_empty(self):
        """An empty string raises ValueError."""
        with pytest.raises(ValueError):
            _convert_otel_to_xray_trace_id('')

    def test_example_from_user(self):
        """Verify a representative real-world example converts correctly."""
        result = _convert_otel_to_xray_trace_id('0x699f76fcb8d4bfe141ab8d7a5945d7bb')
        assert result == '1-699f76fc-b8d4bfe141ab8d7a5945d7bb'


class TestExtractSegmentSummary:
    """Tests for the X-Ray segment-document summarizer."""

    def test_basic_segment(self):
        """A minimal segment yields name and computed duration_ms."""
        doc = {'name': 'my-service', 'start_time': 1000.0, 'end_time': 1000.5}
        result = _extract_segment_summary(doc)
        assert result['name'] == 'my-service'
        assert round(result['duration_ms'], 1) == 500.0

    def test_segment_with_errors(self):
        """error/fault flags surface when true."""
        doc = {
            'name': 'failing-service',
            'start_time': 1000.0,
            'end_time': 1000.1,
            'error': True,
            'fault': True,
        }
        result = _extract_segment_summary(doc)
        assert result['error'] is True
        assert result['fault'] is True

    def test_no_error_flags_omitted(self):
        """Falsy error/fault flags are omitted from the summary."""
        doc = {
            'name': 'healthy-service',
            'start_time': 1000.0,
            'end_time': 1000.1,
            'error': False,
            'fault': False,
        }
        result = _extract_segment_summary(doc)
        assert 'error' not in result
        assert 'fault' not in result

    def test_http_details(self):
        """HTTP method/url/status are extracted."""
        doc = {
            'name': 'api-call',
            'start_time': 1000.0,
            'end_time': 1000.2,
            'http': {
                'request': {'method': 'GET', 'url': 'https://api.example.com/data'},
                'response': {'status': 200},
            },
        }
        result = _extract_segment_summary(doc)
        assert result['http']['method'] == 'GET'
        assert result['http']['url'] == 'https://api.example.com/data'
        assert result['http']['status'] == 200

    def test_aws_service_details(self):
        """AWS namespace and operation/table details are extracted."""
        doc = {
            'name': 'DynamoDB',
            'start_time': 1000.0,
            'end_time': 1000.05,
            'namespace': 'aws',
            'aws': {'operation': 'GetItem', 'table_name': 'users-table'},
        }
        result = _extract_segment_summary(doc)
        assert result['namespace'] == 'aws'
        assert result['aws']['operation'] == 'GetItem'
        assert result['aws']['table_name'] == 'users-table'

    def test_cause_exceptions(self):
        """Cause exceptions are summarized (type/message)."""
        doc = {
            'name': 'failing-call',
            'start_time': 1000.0,
            'end_time': 1000.1,
            'fault': True,
            'cause': {
                'exceptions': [{'type': 'TimeoutError', 'message': 'Connection timed out'}],
            },
        }
        result = _extract_segment_summary(doc)
        assert len(result['cause']) == 1
        assert result['cause'][0]['type'] == 'TimeoutError'

    def test_sql_details(self):
        """SQL sanitized query and database type are extracted."""
        doc = {
            'name': 'postgres',
            'start_time': 1000.0,
            'end_time': 1000.05,
            'sql': {
                'sanitized_query': 'SELECT * FROM users WHERE id = ?',
                'database_type': 'PostgreSQL',
            },
        }
        result = _extract_segment_summary(doc)
        assert result['sql']['query'] == 'SELECT * FROM users WHERE id = ?'
        assert result['sql']['database_type'] == 'PostgreSQL'

    def test_nested_subsegments(self):
        """Nested subsegments are summarized recursively."""
        doc = {
            'name': 'root',
            'start_time': 1000.0,
            'end_time': 1001.0,
            'subsegments': [
                {
                    'name': 'child-1',
                    'start_time': 1000.0,
                    'end_time': 1000.5,
                    'subsegments': [
                        {'name': 'grandchild', 'start_time': 1000.1, 'end_time': 1000.2}
                    ],
                }
            ],
        }
        result = _extract_segment_summary(doc)
        assert len(result['subsegments']) == 1
        child = result['subsegments'][0]
        assert child['name'] == 'child-1'
        assert len(child['subsegments']) == 1
        assert child['subsegments'][0]['name'] == 'grandchild'

    def test_depth_limit(self):
        """Subsegment recursion stops at depth 5."""
        deepest = {'name': 'level-7', 'start_time': 1000.0, 'end_time': 1000.1}
        current = deepest
        for i in range(6, 0, -1):
            current = {
                'name': f'level-{i}',
                'start_time': 1000.0,
                'end_time': 1000.1,
                'subsegments': [current],
            }
        root = {
            'name': 'level-0',
            'start_time': 1000.0,
            'end_time': 1001.0,
            'subsegments': [current],
        }

        result = _extract_segment_summary(root, depth=0)

        node = result
        depth = 0
        while 'subsegments' in node and node['subsegments']:
            node = node['subsegments'][0]
            depth += 1

        assert depth <= 5


class TestScanForIssues:
    """Tests for the recursive error/fault scanner."""

    def test_no_issues(self):
        """Clean segments report no errors or faults."""
        segments = [{'name': 'a', 'duration_ms': 100}, {'name': 'b', 'duration_ms': 200}]
        has_errors, has_faults = _scan_for_issues(segments)
        assert has_errors is False
        assert has_faults is False

    def test_top_level_error(self):
        """A top-level error is detected."""
        segments = [{'name': 'a', 'error': True}]
        has_errors, has_faults = _scan_for_issues(segments)
        assert has_errors is True
        assert has_faults is False

    def test_nested_fault(self):
        """A fault nested in a subsegment is detected."""
        segments = [{'name': 'a', 'subsegments': [{'name': 'b', 'fault': True}]}]
        has_errors, has_faults = _scan_for_issues(segments)
        assert has_errors is False
        assert has_faults is True

    def test_deeply_nested_error(self):
        """An error+fault several levels deep is detected."""
        segments = [
            {
                'name': 'a',
                'subsegments': [
                    {
                        'name': 'b',
                        'subsegments': [{'name': 'c', 'error': True, 'fault': True}],
                    }
                ],
            }
        ]
        has_errors, has_faults = _scan_for_issues(segments)
        assert has_errors is True
        assert has_faults is True


class TestParseXrayTrace:
    """Tests for parsing a raw X-Ray trace into a summary."""

    @staticmethod
    def _make_trace(segments_docs):
        """Build a mock X-Ray trace response from segment documents."""
        return {
            'Id': '1-deadbeef-deadbeefdeadbeefdeadbeef',
            'Duration': 1.5,
            'Segments': [
                {'Id': f'seg-{i}', 'Document': json.dumps(doc)}
                for i, doc in enumerate(segments_docs)
            ],
        }

    def test_basic_trace(self):
        """A single-segment trace parses with no errors/faults."""
        trace = self._make_trace(
            [{'name': 'my-service', 'start_time': 1000.0, 'end_time': 1001.5}]
        )
        result = _parse_xray_trace(trace)
        assert result['trace_id'] == '1-deadbeef-deadbeefdeadbeefdeadbeef'
        assert result['duration_s'] == 1.5
        assert len(result['segments']) == 1
        assert result['segments'][0]['name'] == 'my-service'
        assert result['has_errors'] is False
        assert result['has_faults'] is False

    def test_trace_with_faults(self):
        """A fault in a nested AWS subsegment is surfaced."""
        trace = self._make_trace(
            [
                {
                    'name': 'api-gateway',
                    'start_time': 1000.0,
                    'end_time': 1001.0,
                    'subsegments': [
                        {
                            'name': 'DynamoDB',
                            'start_time': 1000.1,
                            'end_time': 1000.9,
                            'namespace': 'aws',
                            'fault': True,
                            'aws': {'operation': 'PutItem', 'table_name': 'orders'},
                            'cause': {
                                'exceptions': [
                                    {
                                        'type': 'ProvisionedThroughputExceededException',
                                        'message': 'Rate exceeded',
                                    }
                                ],
                            },
                        }
                    ],
                }
            ]
        )
        result = _parse_xray_trace(trace)
        assert result['has_faults'] is True
        dynamo = result['segments'][0]['subsegments'][0]
        assert dynamo['name'] == 'DynamoDB'
        assert dynamo['fault'] is True
        assert dynamo['aws']['operation'] == 'PutItem'
        assert dynamo['cause'][0]['type'] == 'ProvisionedThroughputExceededException'

    def test_invalid_document_json_skipped(self):
        """A segment with unparseable JSON is skipped, valid ones kept."""
        trace = {
            'Id': '1-test-trace',
            'Duration': 1.0,
            'Segments': [
                {'Id': 'seg-0', 'Document': 'not-valid-json'},
                {
                    'Id': 'seg-1',
                    'Document': json.dumps({'name': 'valid', 'start_time': 1.0, 'end_time': 2.0}),
                },
            ],
        }
        result = _parse_xray_trace(trace)
        assert len(result['segments']) == 1
        assert result['segments'][0]['name'] == 'valid'

    def test_multiple_segments(self):
        """Multiple top-level segments are all parsed; errors aggregated."""
        trace = self._make_trace(
            [
                {'name': 'service-a', 'start_time': 1000.0, 'end_time': 1000.5},
                {'name': 'service-b', 'start_time': 1000.0, 'end_time': 1001.0, 'error': True},
            ]
        )
        result = _parse_xray_trace(trace)
        assert len(result['segments']) == 2
        assert result['has_errors'] is True
        assert result['has_faults'] is False


@pytest.mark.asyncio
class TestGetXrayTrace:
    """Tests for the get_xray_trace tool entry point."""

    async def test_no_trace_ids(self):
        """Empty input returns an error without calling X-Ray."""
        result = await get_xray_trace(trace_ids='')
        assert 'error' in result

    async def test_too_many_trace_ids(self):
        """More than 5 trace IDs is rejected."""
        ids = ','.join(['deadbeefdeadbeefdeadbeefdeadbeef'] * 6)
        result = await get_xray_trace(trace_ids=ids)
        assert 'error' in result
        assert 'Maximum 5' in result['error']

    async def test_invalid_trace_id(self):
        """An unparseable trace ID returns an error."""
        result = await get_xray_trace(trace_ids='not-a-valid-id')
        assert 'error' in result

    async def test_success_with_fault_and_conversion(self):
        """A 2-segment trace is summarized with faults and id conversion recorded."""
        mock_xray = MagicMock()
        mock_xray.batch_get_traces.return_value = {
            'Traces': [
                {
                    'Id': '1-deadbeef-deadbeefdeadbeefdeadbeef',
                    'Duration': 2.0,
                    'Segments': [
                        {
                            'Id': 'seg-0',
                            'Document': json.dumps(
                                {'name': 'frontend', 'start_time': 1000.0, 'end_time': 1002.0}
                            ),
                        },
                        {
                            'Id': 'seg-1',
                            'Document': json.dumps(
                                {
                                    'name': 'backend',
                                    'start_time': 1000.5,
                                    'end_time': 1001.8,
                                    'fault': True,
                                }
                            ),
                        },
                    ],
                }
            ],
            'UnprocessedTraceIds': [],
        }

        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.trace_tools.xray_client',
            mock_xray,
        ):
            result = await get_xray_trace(trace_ids='0xdeadbeefdeadbeefdeadbeefdeadbeef')

        # OTel input was converted to X-Ray format before the API call.
        mock_xray.batch_get_traces.assert_called_once_with(
            TraceIds=['1-deadbeef-deadbeefdeadbeefdeadbeef']
        )
        assert len(result['traces']) == 1
        trace = result['traces'][0]
        assert trace['has_faults'] is True
        assert {s['name'] for s in trace['segments']} == {'frontend', 'backend'}
        # Conversion mapping is included because input was not X-Ray format.
        assert result['trace_id_conversions'] == {
            '0xdeadbeefdeadbeefdeadbeefdeadbeef': '1-deadbeef-deadbeefdeadbeefdeadbeef'
        }

    async def test_unprocessed_trace_ids_note(self):
        """Unprocessed (unsampled) trace IDs add an explanatory note."""
        mock_xray = MagicMock()
        mock_xray.batch_get_traces.return_value = {
            'Traces': [],
            'UnprocessedTraceIds': ['1-deadbeef-deadbeefdeadbeefdeadbeef'],
        }
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.trace_tools.xray_client',
            mock_xray,
        ):
            result = await get_xray_trace(trace_ids='1-deadbeef-deadbeefdeadbeefdeadbeef')

        assert result['traces'] == []
        assert result['unprocessed_trace_ids'] == ['1-deadbeef-deadbeefdeadbeefdeadbeef']
        assert 'note' in result
