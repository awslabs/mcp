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

"""Unit tests for the metric_config module in logs_and_telemetry."""

import unittest
from awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools import (
    get_monitoring_level_rank,
)
from awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.metric_config import (
    METRICS,
    SERVERLESS_METRICS,
    get_metric_config,
)


class TestMetricConfig(unittest.TestCase):
    """Tests for the metric_config module in logs_and_telemetry."""

    def test_metrics_structure(self):
        """Test that the METRICS dictionary has the expected structure."""
        # Check that METRICS is not empty
        self.assertGreater(len(METRICS), 0)

        # Check a few key metrics to ensure they have the expected structure
        key_metrics = [
            'BytesInPerSec',
            'BytesOutPerSec',
            'GlobalTopicCount',
            'ActiveControllerCount',
        ]
        for metric_name in key_metrics:
            self.assertIn(metric_name, METRICS)
            metric_config = METRICS[metric_name]

            # Check that each metric has the required fields
            self.assertIn('monitoring_level', metric_config)
            self.assertIn('dimensions', metric_config)
            self.assertIn('default_statistic', metric_config)
            self.assertIn('description', metric_config)

            # Check that dimensions is a list
            self.assertIsInstance(metric_config['dimensions'], list)

            # Check that monitoring_level is one of the expected values
            self.assertIn(
                metric_config['monitoring_level'],
                ['DEFAULT', 'PER_BROKER', 'PER_TOPIC_PER_BROKER', 'PER_TOPIC_PER_PARTITION'],
            )

    def test_serverless_metrics_structure(self):
        """Test that the SERVERLESS_METRICS dictionary has the expected structure."""
        # Check that SERVERLESS_METRICS is not empty
        self.assertGreater(len(SERVERLESS_METRICS), 0)

        # Check a few key metrics to ensure they have the expected structure
        key_metrics = ['BytesInPerSec', 'BytesOutPerSec', 'MessagesInPerSec']
        for metric_name in key_metrics:
            self.assertIn(metric_name, SERVERLESS_METRICS)
            metric_config = SERVERLESS_METRICS[metric_name]

            # Check that each metric has the required fields
            self.assertIn('monitoring_level', metric_config)
            self.assertIn('dimensions', metric_config)
            self.assertIn('default_statistic', metric_config)
            self.assertIn('description', metric_config)

            # Check that dimensions is a list
            self.assertIsInstance(metric_config['dimensions'], list)

            # Check that monitoring_level is DEFAULT for serverless metrics
            self.assertEqual(metric_config['monitoring_level'], 'DEFAULT')

    def test_get_metric_config_provisioned(self):
        """Test the get_metric_config function for provisioned clusters."""
        # Test getting a metric config for a provisioned cluster
        metric_name = 'BytesInPerSec'
        config = get_metric_config(metric_name, serverless=False)

        # Check that the config has the expected structure
        self.assertEqual(config['monitoring_level'], 'DEFAULT')
        self.assertIn('Cluster Name', config['dimensions'])
        self.assertEqual(config['default_statistic'], 'Sum')
        self.assertIsInstance(config['description'], str)

    def test_get_metric_config_serverless(self):
        """Test the get_metric_config function for serverless clusters."""
        # Test getting a metric config for a serverless cluster
        metric_name = 'BytesInPerSec'
        config = get_metric_config(metric_name, serverless=True)

        # Check that the config has the expected structure
        self.assertEqual(config['monitoring_level'], 'DEFAULT')
        self.assertIn('Cluster Name', config['dimensions'])
        self.assertIn('Topic', config['dimensions'])
        self.assertEqual(config['default_statistic'], 'Sum')
        self.assertIsInstance(config['description'], str)

    def test_get_metric_config_invalid_metric(self):
        """Test the get_metric_config function with an invalid metric name."""
        # Test getting a metric config for an invalid metric name
        invalid_metric_name = 'InvalidMetricName'

        # Check that KeyError is raised for an invalid metric name
        with self.assertRaises(KeyError):
            get_metric_config(invalid_metric_name, serverless=False)

        with self.assertRaises(KeyError):
            get_metric_config(invalid_metric_name, serverless=True)

    def test_get_monitoring_level_rank(self):
        """Test the get_monitoring_level_rank function."""
        # Test the rank of each monitoring level
        self.assertEqual(get_monitoring_level_rank('DEFAULT'), 0)
        self.assertEqual(get_monitoring_level_rank('PER_BROKER'), 1)
        self.assertEqual(get_monitoring_level_rank('PER_TOPIC_PER_BROKER'), 2)
        self.assertEqual(get_monitoring_level_rank('PER_TOPIC_PER_PARTITION'), 3)

        # Test with an invalid monitoring level
        self.assertEqual(get_monitoring_level_rank('INVALID_LEVEL'), -1)

    def test_metric_dimensions_consistency(self):
        """Test that metric dimensions are consistent with their monitoring levels."""
        for metric_name, config in METRICS.items():
            monitoring_level = config['monitoring_level']
            dimensions = config['dimensions']

            # Check that dimensions are consistent with monitoring level
            if monitoring_level == 'DEFAULT':
                # All metrics should have 'Cluster Name' dimension
                self.assertIn('Cluster Name', dimensions)

            elif monitoring_level == 'PER_BROKER':
                # PER_BROKER metrics should have 'Broker ID' dimension
                self.assertIn('Cluster Name', dimensions)
                self.assertIn('Broker ID', dimensions)

            elif monitoring_level == 'PER_TOPIC_PER_BROKER':
                # PER_TOPIC_PER_BROKER metrics should have 'Topic' and 'Broker ID' dimensions
                self.assertIn('Cluster Name', dimensions)
                self.assertIn('Broker ID', dimensions)
                self.assertIn('Topic', dimensions)

    def test_serverless_metrics_subset(self):
        """Test that serverless metrics are a subset of the provisioned metrics."""
        # Check that all serverless metrics have corresponding provisioned metrics
        for metric_name in SERVERLESS_METRICS:
            # The metric name should exist in both dictionaries
            self.assertIn(metric_name, METRICS)

            # The serverless metric should have 'Topic' dimension
            self.assertIn('Topic', SERVERLESS_METRICS[metric_name]['dimensions'])


if __name__ == '__main__':
    unittest.main()
