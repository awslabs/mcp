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
# This file is part of the awslabs namespace.
# It is intentionally minimal to support PEP 420 namespace packages.

from awslabs.amazon_mq_mcp_server.rabbitmq.handlers import (
    handle_delete_exchange,
    handle_delete_queue,
    handle_enqueue,
    handle_fanout,
    handle_get_cluster_node_memory,
    handle_get_cluster_nodes,
    handle_get_exchange_info,
    handle_get_guidelines,
    handle_get_overview,
    handle_get_queue_info,
    handle_is_broker_in_alarm,
    handle_is_node_in_quorum_critical,
    handle_list_connections,
    handle_list_consumers,
    handle_list_exchanges,
    handle_list_exchanges_by_vhost,
    handle_list_queues,
    handle_list_queues_by_vhost,
    handle_list_shovels,
    handle_list_users,
    handle_list_vhosts,
    handle_purge_queue,
    handle_shovel,
)
from unittest.mock import MagicMock


class TestAMQPHandlers:
    """Tests for AMQP message handlers."""

    def test_handle_enqueue(self):
        """Test enqueue handler."""
        mock_rabbitmq = MagicMock()
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_rabbitmq.get_channel.return_value = (mock_connection, mock_channel)
        handle_enqueue(mock_rabbitmq, 'test-queue', 'test message')
        mock_channel.queue_declare.assert_called_once_with('test-queue')
        mock_channel.basic_publish.assert_called_once_with(
            exchange='', routing_key='test-queue', body='test message'
        )
        mock_connection.close.assert_called_once()

    def test_handle_fanout(self):
        """Test fanout handler."""
        mock_rabbitmq = MagicMock()
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_rabbitmq.get_channel.return_value = (mock_connection, mock_channel)
        handle_fanout(mock_rabbitmq, 'test-exchange', 'test message')
        mock_channel.exchange_declare.assert_called_once_with(
            exchange='test-exchange', exchange_type='fanout'
        )
        mock_channel.basic_publish.assert_called_once_with(
            exchange='test-exchange', routing_key='', body='test message'
        )
        mock_connection.close.assert_called_once()


class TestQueueHandlers:
    """Tests for queue management handlers."""

    def test_handle_list_queues(self):
        """Test list queues handler."""
        mock_admin = MagicMock()
        mock_admin.list_queues.return_value = [
            {'name': 'queue1', 'messages': 5},
            {'name': 'queue2', 'messages': 0},
        ]
        result = handle_list_queues(mock_admin)
        assert result == ['queue1', 'queue2']
        mock_admin.list_queues.assert_called_once()

    def test_handle_list_queues_by_vhost(self):
        """Test list queues by vhost handler."""
        mock_admin = MagicMock()
        mock_admin.list_queues_by_vhost.return_value = [{'name': 'queue1'}]
        result = handle_list_queues_by_vhost(mock_admin, '/test')
        assert result == ['queue1']
        mock_admin.list_queues_by_vhost.assert_called_once_with('/test')

    def test_handle_get_queue_info(self):
        """Test get queue info handler."""
        mock_admin = MagicMock()
        expected_info = {'name': 'test-queue', 'messages': 5}
        mock_admin.get_queue_info.return_value = expected_info
        result = handle_get_queue_info(mock_admin, 'test-queue', '/')
        assert result == expected_info
        mock_admin.get_queue_info.assert_called_once_with('test-queue', '/')

    def test_handle_delete_queue(self):
        """Test delete queue handler."""
        mock_admin = MagicMock()
        handle_delete_queue(mock_admin, 'test-queue', '/')
        mock_admin.delete_queue.assert_called_once_with('test-queue', '/')

    def test_handle_purge_queue(self):
        """Test purge queue handler."""
        mock_admin = MagicMock()
        handle_purge_queue(mock_admin, 'test-queue', '/')
        mock_admin.purge_queue.assert_called_once_with('test-queue', '/')


class TestExchangeHandlers:
    """Tests for exchange management handlers."""

    def test_handle_list_exchanges(self):
        """Test list exchanges handler."""
        mock_admin = MagicMock()
        mock_admin.list_exchanges.return_value = [
            {'name': 'exchange1', 'type': 'fanout'},
            {'name': 'exchange2', 'type': 'direct'},
        ]
        result = handle_list_exchanges(mock_admin)
        assert result == ['exchange1', 'exchange2']
        mock_admin.list_exchanges.assert_called_once()

    def test_handle_list_exchanges_by_vhost(self):
        """Test list exchanges by vhost handler."""
        mock_admin = MagicMock()
        mock_admin.list_exchanges_by_vhost.return_value = [{'name': 'exchange1'}]
        result = handle_list_exchanges_by_vhost(mock_admin, '/test')
        assert result == ['exchange1']
        mock_admin.list_exchanges_by_vhost.assert_called_once_with('/test')

    def test_handle_get_exchange_info(self):
        """Test get exchange info handler."""
        mock_admin = MagicMock()
        expected_info = {'name': 'test-exchange', 'type': 'fanout'}
        mock_admin.get_exchange_info.return_value = expected_info
        result = handle_get_exchange_info(mock_admin, 'test-exchange', '/')
        assert result == expected_info
        mock_admin.get_exchange_info.assert_called_once_with('test-exchange', '/')

    def test_handle_delete_exchange(self):
        """Test delete exchange handler."""
        mock_admin = MagicMock()
        handle_delete_exchange(mock_admin, 'test-exchange', '/')
        mock_admin.delete_exchange.assert_called_once_with('test-exchange', '/')


class TestVhostHandlers:
    """Tests for vhost management handlers."""

    def test_handle_list_vhosts(self):
        """Test list vhosts handler."""
        mock_admin = MagicMock()
        mock_admin.list_vhosts.return_value = [
            {'name': '/', 'tracing': False},
            {'name': '/test', 'tracing': True},
        ]
        result = handle_list_vhosts(mock_admin)
        assert result == ['/', '/test']
        mock_admin.list_vhosts.assert_called_once()


class TestShovelHandlers:
    """Tests for shovel management handlers."""

    def test_handle_list_shovels(self):
        """Test list shovels handler."""
        mock_admin = MagicMock()
        expected_shovels = [{'name': 'shovel1'}, {'name': 'shovel2'}]
        mock_admin.list_shovels.return_value = expected_shovels
        result = handle_list_shovels(mock_admin)
        assert result == expected_shovels
        mock_admin.list_shovels.assert_called_once()

    def test_handle_shovel(self):
        """Test get shovel info handler."""
        mock_admin = MagicMock()
        expected_info = {'name': 'test-shovel', 'state': 'running'}
        mock_admin.get_shovel_info.return_value = expected_info
        result = handle_shovel(mock_admin, 'test-shovel', '/')
        assert result == expected_info
        mock_admin.get_shovel_info.assert_called_once_with('test-shovel', '/')


class TestDocHandlers:
    """Tests for documentation handlers."""

    def test_handle_get_guidelines(self):
        """Test get general best practices handler."""
        result = handle_get_guidelines('rabbitmq_broker_setup_best_practices_guide')
        assert isinstance(result, str)
        result = handle_get_guidelines('rabbimq_broker_sizing_guide')
        assert isinstance(result, str)
        result = handle_get_guidelines('rabbitmq_quorum_queue_migration_guide')
        assert isinstance(result, str)
        result = handle_get_guidelines('rabbitmq_client_performance_optimization_guide')
        assert isinstance(result, str)
        assert len(result) > 0


class TestHealthHandlers:
    """Tests for health check handlers."""

    def test_handle_get_overview(self):
        """Test get overview handler."""
        mock_admin = MagicMock()
        expected_overview = {'rabbitmq_version': '3.8.0'}
        mock_admin.get_overview.return_value = expected_overview
        result = handle_get_overview(mock_admin)
        assert result == expected_overview
        mock_admin.get_overview.assert_called_once()

    def test_handle_is_broker_in_alarm(self):
        """Test broker alarm status handler."""
        mock_admin = MagicMock()
        mock_admin.get_alarm_status.return_value = 200
        result = handle_is_broker_in_alarm(mock_admin)
        assert result is False
        mock_admin.get_alarm_status.assert_called_once()

    def test_handle_is_node_in_quorum_critical(self):
        """Test node quorum critical status handler."""
        mock_admin = MagicMock()
        mock_admin.get_is_node_quorum_critical.return_value = 200
        result = handle_is_node_in_quorum_critical(mock_admin)
        assert result is False
        mock_admin.get_is_node_quorum_critical.assert_called_once()


class TestConnectionHandlers:
    """Tests for connection handlers."""

    def test_handle_list_connections(self):
        """Test list connections handler."""
        mock_admin = MagicMock()
        mock_admin.list_connections.return_value = [
            {
                'auth_mechanism': 'PLAIN',
                'channels': 1,
                'client_properties': {},
                'connected_at': 1609459200000,
                'state': 'running',
            }
        ]
        result = handle_list_connections(mock_admin)
        assert len(result) == 1
        assert result[0]['auth_mechanism'] == 'PLAIN'
        mock_admin.list_connections.assert_called_once()

    def test_handle_list_consumers(self):
        """Test list consumers handler."""
        mock_admin = MagicMock()
        expected_consumers = [{'queue': 'test-queue'}]
        mock_admin.list_consumers.return_value = expected_consumers
        result = handle_list_consumers(mock_admin)
        assert result == expected_consumers
        mock_admin.list_consumers.assert_called_once()


class TestClusterHandlers:
    """Tests for cluster handlers."""

    def test_handle_get_cluster_nodes(self):
        """Test get cluster nodes handler."""
        mock_admin = MagicMock()
        mock_admin.get_cluster_nodes.return_value = [
            {
                'name': 'node1',
                'mem_alarm': False,
                'disk_free_alarm': False,
                'disk_free': 1000000,
                'mem_limit': 2000000,
                'mem_used': 1000000,
                'rates_mode': 'basic',
                'uptime': 3600000,
                'running': True,
                'queue_created': 5,
                'queue_deleted': 1,
                'connection_created': 10,
            }
        ]
        result = handle_get_cluster_nodes(mock_admin)
        assert len(result) == 1
        assert result[0]['name'] == 'node1'
        assert result[0]['mem_used_in_percentage'] == 50.0
        mock_admin.get_cluster_nodes.assert_called_once()

    def test_handle_get_cluster_node_memory(self):
        """Test get cluster node memory handler."""
        mock_admin = MagicMock()
        expected_memory = {'memory': {'total': 1000000}}
        mock_admin.get_node_memory.return_value = expected_memory
        result = handle_get_cluster_node_memory(mock_admin, 'node1')
        assert result == expected_memory
        mock_admin.get_node_memory.assert_called_once_with(node_name='node1')


class TestUserHandlers:
    """Tests for user handlers."""

    def test_handle_list_users(self):
        """Test list users handler."""
        mock_admin = MagicMock()
        expected_users = [{'name': 'admin'}]
        mock_admin.list_users.return_value = expected_users
        result = handle_list_users(mock_admin)
        assert result == expected_users
        mock_admin.list_users.assert_called_once()
