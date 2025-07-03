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

"""Tests for the CloudWatch Logs models."""

from awslabs.cloudwatch_mcp_server.cloudwatch_logs.models import (
    LogAnomaly,
    LogGroupMetadata,
)


class TestLogGroupMetadata:
    """Tests for LogGroupMetadata model."""

    def test_convert_to_iso8601_returns_string_unchanged(self):
        """Test that string timestamps are returned unchanged (covers 'return v' line)."""
        # Test data with string timestamp (already in ISO format)
        log_group_data = {
            'logGroupName': '/aws/test/group',
            'creationTime': '2023-01-01T00:00:00+00:00',  # String timestamp
            'metricFilterCount': 0,
            'storedBytes': 1024,
            'logGroupClass': 'STANDARD',
            'logGroupArn': 'arn:aws:logs:us-east-1:123456789012:log-group:/aws/test/group',
        }

        log_group = LogGroupMetadata(**log_group_data)

        # Verify the string timestamp was returned unchanged
        assert log_group.creationTime == '2023-01-01T00:00:00+00:00'


class TestLogAnomaly:
    """Tests for LogAnomaly model."""

    def test_timestamp_fields_return_string_unchanged(self):
        """Test that string timestamps in LogAnomaly are returned unchanged (covers 'return v' line)."""
        # Test data with string timestamps (already in ISO format)
        anomaly_data = {
            'anomalyDetectorArn': 'arn:aws:logs:us-east-1:123456789012:detector:test',
            'logGroupArnList': ['arn:aws:logs:us-east-1:123456789012:log-group:/aws/test'],
            'firstSeen': '2023-01-01T00:00:00+00:00',  # String timestamp
            'lastSeen': '2023-01-01T01:00:00+00:00',  # String timestamp
            'description': 'Test anomaly',
            'priority': 'HIGH',
            'patternRegex': '.*error.*',
            'patternString': 'error pattern',
            'logSamples': [{'timestamp': 1672531200000, 'message': 'test message'}],
            'histogram': {'1672531200000': 10},
        }

        anomaly = LogAnomaly(**anomaly_data)

        # Verify the string timestamps were returned unchanged
        assert anomaly.firstSeen == '2023-01-01T00:00:00+00:00'
        assert anomaly.lastSeen == '2023-01-01T01:00:00+00:00'
