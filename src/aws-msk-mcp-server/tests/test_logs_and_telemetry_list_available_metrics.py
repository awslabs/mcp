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

"""Unit tests for the list_available_metrics function in cluster_metrics_tools.py."""

import unittest
from awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools import (
    list_available_metrics,
)
from unittest.mock import patch


class TestListAvailableMetrics(unittest.TestCase):
    """Tests for the list_available_metrics function in cluster_metrics_tools.py."""

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.METRICS',
        {
            'BytesInPerSec': {'monitoring_level': 'DEFAULT', 'default_statistic': 'Sum'},
            'BytesOutPerSec': {'monitoring_level': 'DEFAULT', 'default_statistic': 'Sum'},
            'CpuUser': {'monitoring_level': 'PER_BROKER', 'default_statistic': 'Average'},
            'CpuSystem': {'monitoring_level': 'PER_BROKER', 'default_statistic': 'Average'},
        },
    )
    def test_list_available_metrics_provisioned(self):
        """Test the list_available_metrics function with a provisioned cluster."""
        # Test with DEFAULT monitoring level
        result = list_available_metrics(monitoring_level='DEFAULT')
        self.assertEqual(len(result), 2)
        self.assertIn('BytesInPerSec', result)
        self.assertIn('BytesOutPerSec', result)
        self.assertNotIn('CpuUser', result)
        self.assertNotIn('CpuSystem', result)

        # Test with PER_BROKER monitoring level
        result = list_available_metrics(monitoring_level='PER_BROKER')
        self.assertEqual(len(result), 2)
        self.assertIn('CpuUser', result)
        self.assertIn('CpuSystem', result)
        self.assertNotIn('BytesInPerSec', result)
        self.assertNotIn('BytesOutPerSec', result)

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.SERVERLESS_METRICS',
        {
            'BytesInPerSec': {'monitoring_level': 'DEFAULT', 'default_statistic': 'Sum'},
            'BytesOutPerSec': {'monitoring_level': 'DEFAULT', 'default_statistic': 'Sum'},
        },
    )
    def test_list_available_metrics_serverless(self):
        """Test the list_available_metrics function with a serverless cluster."""
        # Test with DEFAULT monitoring level
        result = list_available_metrics(monitoring_level='DEFAULT', serverless=True)
        self.assertEqual(len(result), 2)
        self.assertIn('BytesInPerSec', result)
        self.assertIn('BytesOutPerSec', result)

    def test_list_available_metrics_missing_monitoring_level(self):
        """Test the list_available_metrics function with missing monitoring level."""
        # Call the function and expect an error
        with self.assertRaises(ValueError) as context:
            list_available_metrics(monitoring_level=None)

        self.assertEqual(str(context.exception), 'Monitoring level must be provided')


if __name__ == '__main__':
    unittest.main()
