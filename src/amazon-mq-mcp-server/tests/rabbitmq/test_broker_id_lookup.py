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
"""Tests for broker ID to hostname lookup functionality."""

import pytest
from awslabs.amazon_mq_mcp_server.rabbitmq.connection import get_broker_hostname_from_id
from unittest.mock import MagicMock


class TestGetBrokerHostnameFromId:
    """Tests for the get_broker_hostname_from_id function."""

    def test_successful_hostname_lookup_on_aws(self):
        """Test successful hostname lookup with on.aws domain."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.describe_broker.return_value = {
            'BrokerInstances': [
                {
                    'Endpoints': [
                        'amqps://b-a9565a64-da39-4afc-9239-c43a9376b5ba.mq.us-east-1.on.aws:5671'
                    ]
                }
            ]
        }

        # Execute
        hostname = get_broker_hostname_from_id(
            mock_client, 'b-a9565a64-da39-4afc-9239-c43a9376b5ba'
        )

        # Verify
        assert hostname == 'b-a9565a64-da39-4afc-9239-c43a9376b5ba.mq.us-east-1.on.aws'
        mock_client.describe_broker.assert_called_once_with(
            BrokerId='b-a9565a64-da39-4afc-9239-c43a9376b5ba'
        )

    def test_successful_hostname_lookup_amazonaws_com(self):
        """Test successful hostname lookup with amazonaws.com domain."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.describe_broker.return_value = {
            'BrokerInstances': [
                {
                    'Endpoints': [
                        'amqps://b-9560b8e1-3d33-4d91-9488-a3dc4a61dfe7.mq.us-west-2.amazonaws.com:5671'
                    ]
                }
            ]
        }

        # Execute
        hostname = get_broker_hostname_from_id(
            mock_client, 'b-9560b8e1-3d33-4d91-9488-a3dc4a61dfe7'
        )

        # Verify
        assert hostname == 'b-9560b8e1-3d33-4d91-9488-a3dc4a61dfe7.mq.us-west-2.amazonaws.com'

    def test_multiple_endpoints_selects_amqps(self):
        """Test that AMQPS endpoint is selected when multiple endpoints exist."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.describe_broker.return_value = {
            'BrokerInstances': [
                {
                    'Endpoints': [
                        'https://b-abc123.mq.us-east-1.on.aws:443',
                        'amqps://b-abc123.mq.us-east-1.on.aws:5671',
                    ]
                }
            ]
        }

        # Execute
        hostname = get_broker_hostname_from_id(mock_client, 'b-abc123')

        # Verify - should select the amqps endpoint
        assert hostname == 'b-abc123.mq.us-east-1.on.aws'

    def test_empty_broker_id(self):
        """Test that empty broker_id raises ValueError."""
        mock_client = MagicMock()
        with pytest.raises(ValueError) as exc_info:
            get_broker_hostname_from_id(mock_client, '')
        assert 'broker_id cannot be empty' in str(exc_info.value)

    def test_whitespace_broker_id(self):
        """Test that whitespace-only broker_id raises ValueError."""
        mock_client = MagicMock()
        with pytest.raises(ValueError) as exc_info:
            get_broker_hostname_from_id(mock_client, '   ')
        assert 'broker_id cannot be empty' in str(exc_info.value)

    def test_no_broker_instances(self):
        """Test error when broker has no instances."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.describe_broker.return_value = {'BrokerInstances': []}

        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            get_broker_hostname_from_id(mock_client, 'b-nonexistent')
        assert 'No broker instances found' in str(exc_info.value)
        assert 'b-nonexistent' in str(exc_info.value)

    def test_no_endpoints(self):
        """Test error when broker instance has no endpoints."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.describe_broker.return_value = {'BrokerInstances': [{'Endpoints': []}]}

        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            get_broker_hostname_from_id(mock_client, 'b-provisioning')
        assert 'No endpoints found' in str(exc_info.value)
        assert 'b-provisioning' in str(exc_info.value)

    def test_no_amqps_endpoint(self):
        """Test error when no AMQPS endpoint is available."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.describe_broker.return_value = {
            'BrokerInstances': [{'Endpoints': ['https://b-abc123.mq.us-east-1.on.aws:443']}]
        }

        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            get_broker_hostname_from_id(mock_client, 'b-abc123')
        assert 'No AMQPS endpoint found' in str(exc_info.value)
        assert 'b-abc123' in str(exc_info.value)

    def test_aws_api_error(self):
        """Test handling of AWS API errors."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.describe_broker.side_effect = Exception('AccessDenied')

        # Execute and verify
        with pytest.raises(Exception) as exc_info:
            get_broker_hostname_from_id(mock_client, 'b-abc123')
        assert 'Failed to retrieve broker hostname' in str(exc_info.value)
        assert 'b-abc123' in str(exc_info.value)
        assert 'AccessDenied' in str(exc_info.value)

    def test_broker_not_found(self):
        """Test handling when broker doesn't exist."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.describe_broker.side_effect = Exception('NotFoundException')

        # Execute and verify
        with pytest.raises(Exception) as exc_info:
            get_broker_hostname_from_id(mock_client, 'b-nonexistent')
        assert 'Failed to retrieve broker hostname' in str(exc_info.value)
        assert 'NotFoundException' in str(exc_info.value)

    def test_different_regions(self):
        """Test that the client is used correctly regardless of region."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.describe_broker.return_value = {
            'BrokerInstances': [{'Endpoints': ['amqps://b-abc123.mq.eu-west-1.on.aws:5671']}]
        }

        # Execute
        hostname = get_broker_hostname_from_id(mock_client, 'b-abc123')

        # Verify
        assert 'eu-west-1' in hostname
