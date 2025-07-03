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

"""Tests for common utilities and server initialization."""

import json
from awslabs.cloudwatch_mcp_server.cloudwatch_logs.models import (
    LogAnomaly,
    SavedLogsInsightsQuery,
)
from awslabs.cloudwatch_mcp_server.common import (
    clean_up_pattern,
    epoch_ms_to_utc_iso,
    filter_by_prefixes,
    remove_null_values,
)
from unittest.mock import Mock, patch


class TestCommonUtilities:
    """Test common utility functions."""

    def test_remove_null_values(self):
        """Test removing null values from dictionary."""
        input_dict = {
            'key1': 'value1',
            'key2': None,
            'key3': '',
            'key4': 'value4',
            'key5': 0,
            'key6': False,
            'key7': [],
        }

        result = remove_null_values(input_dict)

        # Should keep truthy values and remove falsy ones
        assert result == {'key1': 'value1', 'key4': 'value4'}

    def test_filter_by_prefixes(self):
        """Test filtering strings by prefixes."""
        strings = {
            '/aws/lambda/function1',
            '/aws/ec2/instance1',
            '/custom/app1',
            '/other/service1',
        }
        prefixes = {'/aws/lambda', '/custom'}

        result = filter_by_prefixes(strings, prefixes)

        assert result == {'/aws/lambda/function1', '/custom/app1'}

    def test_epoch_ms_to_utc_iso(self):
        """Test converting epoch milliseconds to ISO format."""
        # Test with a known timestamp
        epoch_ms = 1609459200000  # 2021-01-01 00:00:00 UTC
        result = epoch_ms_to_utc_iso(epoch_ms)

        assert result.startswith('2021-01-01T00:00:00')
        assert result.endswith('+00:00')

    def test_clean_up_pattern_with_logsamples(self):
        """Test clean_up_pattern function with @logSamples - covers line 37 in common.py."""
        pattern_result = [
            {
                '@message': 'Error occurred',
                '@tokens': ['error', 'occurred'],
                '@visualization': 'chart_data',
                '@logSamples': json.dumps(
                    [
                        {'timestamp': '2023-01-01T00:00:00Z', 'message': 'Sample 1'},
                        {'timestamp': '2023-01-01T00:01:00Z', 'message': 'Sample 2'},
                        {'timestamp': '2023-01-01T00:02:00Z', 'message': 'Sample 3'},
                    ]
                ),
            }
        ]

        clean_up_pattern(pattern_result)

        # Should remove @tokens and @visualization
        assert '@tokens' not in pattern_result[0]
        assert '@visualization' not in pattern_result[0]

        # Should limit @logSamples to 1 item
        assert len(pattern_result[0]['@logSamples']) == 1
        assert pattern_result[0]['@logSamples'][0]['message'] == 'Sample 1'

    def test_clean_up_pattern_missing_logsamples(self):
        """Test clean_up_pattern function when @logSamples is missing."""
        pattern_result = [
            {
                '@message': 'Error occurred',
                '@tokens': ['error', 'occurred'],
                '@visualization': 'chart_data',
                # Missing @logSamples
            }
        ]

        clean_up_pattern(pattern_result)

        # Should handle missing @logSamples gracefully
        assert pattern_result[0]['@logSamples'] == []

    def test_clean_up_pattern_empty_logsamples(self):
        """Test clean_up_pattern function with empty @logSamples."""
        pattern_result = [
            {
                '@message': 'Error occurred',
                '@tokens': ['error', 'occurred'],
                '@visualization': 'chart_data',
                '@logSamples': '[]',
            }
        ]

        clean_up_pattern(pattern_result)

        # Should handle empty @logSamples gracefully
        assert pattern_result[0]['@logSamples'] == []


class TestLogModelsEdgeCases:
    """Test edge cases in log model validators."""

    def test_log_anomaly_log_samples_limit(self):
        """Test LogAnomaly model limits log samples to 1 - covers line 139 in models.py."""
        log_samples = [
            {'timestamp': 1609459200000, 'message': 'Sample 1'},
            {'timestamp': 1609459260000, 'message': 'Sample 2'},
            {'timestamp': 1609459320000, 'message': 'Sample 3'},
        ]

        anomaly = LogAnomaly(
            anomalyDetectorArn='arn:aws:logs:us-east-1:123456789012:anomaly-detector:test',
            logGroupArnList=['arn:aws:logs:us-east-1:123456789012:log-group:test-group'],
            firstSeen='1609459200000',
            lastSeen='1609459320000',
            description='Test anomaly',
            priority='HIGH',
            patternRegex='ERROR.*',
            patternString='ERROR message',
            logSamples=log_samples,  # 3 samples provided
            histogram={'1609459200000': 5, '1609459260000': 3},
        )

        # Should limit to only 1 log sample
        assert len(anomaly.logSamples) == 1
        assert anomaly.logSamples[0]['message'] == 'Sample 1'

        # Should convert timestamp to ISO format
        assert anomaly.logSamples[0]['timestamp'].endswith('+00:00')

    def test_saved_logs_insights_query_prefix_extraction(self):
        """Test SavedLogsInsightsQuery prefix extraction from query string."""
        query_with_prefix = """
        SOURCE logGroups(namePrefix: ["/aws/lambda", "/aws/ec2"])
        | filter @message like "ERROR"
        """

        query = SavedLogsInsightsQuery(name='Test Query', queryString=query_with_prefix)

        # Should extract prefixes from SOURCE command
        assert '/aws/lambda' in query.logGroupPrefixes
        assert '/aws/ec2' in query.logGroupPrefixes

    def test_saved_logs_insights_query_no_prefix(self):
        """Test SavedLogsInsightsQuery when no prefix is found."""
        query_without_prefix = 'fields @timestamp, @message | filter @message like "ERROR"'

        query = SavedLogsInsightsQuery(name='Test Query', queryString=query_without_prefix)

        # Should have empty prefixes set
        assert len(query.logGroupPrefixes) == 0

    def test_log_anomaly_histogram_conversion(self):
        """Test LogAnomaly histogram timestamp conversion."""
        anomaly = LogAnomaly(
            anomalyDetectorArn='arn:aws:logs:us-east-1:123456789012:anomaly-detector:test',
            logGroupArnList=['arn:aws:logs:us-east-1:123456789012:log-group:test-group'],
            firstSeen='1609459200000',
            lastSeen='1609459320000',
            description='Test anomaly',
            priority='HIGH',
            patternRegex='ERROR.*',
            patternString='ERROR message',
            logSamples=[],
            histogram={
                '1609459200000': 5,
                '1609459260000': 3,
            },  # String keys with epoch timestamps
        )

        # Should convert histogram keys to ISO format
        histogram_keys = list(anomaly.histogram.keys())
        assert all(key.endswith('+00:00') for key in histogram_keys)
        assert any('2021-01-01' in key for key in histogram_keys)


class TestServerInitialization:
    """Test server initialization error handling."""

    def test_server_main_function(self):
        """Test server main function."""
        with patch('awslabs.cloudwatch_mcp_server.server.mcp') as mock_mcp:
            with patch('awslabs.cloudwatch_mcp_server.server.logger') as mock_logger:
                from awslabs.cloudwatch_mcp_server.server import main

                main()

                # Should call mcp.run()
                mock_mcp.run.assert_called_once()
                mock_logger.info.assert_called_with('CloudWatch MCP server started')


class TestEdgeCasesCoverage:
    """Test additional edge cases to ensure complete coverage."""

    def test_epoch_ms_to_utc_iso_with_z_suffix(self):
        """Test epoch_ms_to_utc_iso when isoformat returns Z suffix."""
        # Mock the datetime module in the common module
        with patch('awslabs.cloudwatch_mcp_server.common.datetime') as mock_datetime:
            mock_dt = Mock()
            mock_dt.isoformat.return_value = '2021-01-01T00:00:00Z'
            mock_datetime.datetime.fromtimestamp.return_value = mock_dt

            result = epoch_ms_to_utc_iso(1609459200000)

            # Should convert Z to +00:00
            assert result == '2021-01-01T00:00:00+00:00'

    def test_filter_by_prefixes_empty_sets(self):
        """Test filter_by_prefixes with empty sets."""
        # Empty strings set
        result = filter_by_prefixes(set(), {'/aws'})
        assert result == set()

        # Empty prefixes set
        result = filter_by_prefixes({'/aws/lambda/func1'}, set())
        assert result == set()

        # Both empty
        result = filter_by_prefixes(set(), set())
        assert result == set()

    def test_clean_up_pattern_multiple_entries(self):
        """Test clean_up_pattern with multiple entries."""
        pattern_result = [
            {
                '@message': 'Error 1',
                '@tokens': ['error', '1'],
                '@logSamples': json.dumps([{'msg': 'sample1'}, {'msg': 'sample2'}]),
            },
            {
                '@message': 'Error 2',
                '@visualization': 'chart',
                '@logSamples': json.dumps([{'msg': 'sample3'}]),
            },
        ]

        clean_up_pattern(pattern_result)

        # Should process all entries
        assert len(pattern_result) == 2
        assert '@tokens' not in pattern_result[0]
        assert '@visualization' not in pattern_result[1]
        assert len(pattern_result[0]['@logSamples']) == 1
        assert len(pattern_result[1]['@logSamples']) == 1
