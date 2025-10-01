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

import base64
import requests
from .connection import validate_rabbitmq_name
from typing import Any, Optional
from urllib.parse import quote


# https://rawcdn.githack.com/rabbitmq/rabbitmq-server/v4.0.7/deps/rabbitmq_management/priv/www/api/index.html
class RabbitMQAdmin:
    """RabbitMQAdmin class provides API to call RabbitMQ APIs."""

    def __init__(self, hostname: str, username: str, password: str):
        """Initialize RabbitMQ admin client."""
        host = hostname
        self.protocol = 'https'
        self.base_url = f'{self.protocol}://{host}/api'
        self.auth = base64.b64encode(f'{username}:{password}'.encode()).decode()
        self.headers = {'Authorization': f'Basic {self.auth}', 'Content-Type': 'application/json'}

    def _make_request(
        self, method: str, endpoint: str, data: Optional[dict] = None
    ) -> requests.Response:
        """Make HTTP request to RabbitMQ API."""
        url = f'{self.base_url}/{endpoint}'
        response = requests.request(method, url, headers=self.headers, json=data, verify=True)
        response.raise_for_status()
        return response

    def test_connection(self):
        """Test if the RabbitMQ admin HTTP endpoints are accessible."""
        self._make_request('GET', 'queues')

    def list_queues(self) -> list[dict]:
        """List all queues in the RabbitMQ server."""
        response = self._make_request('GET', 'queues')
        return response.json()

    def list_queues_by_vhost(self, vhost: str = '/') -> list[dict]:
        """List all queues in the RabbitMQ server for a specific vhost."""
        vhost_encoded = quote(vhost, safe='')
        response = self._make_request('GET', f'queues/{vhost_encoded}')
        return response.json()

    def list_exchanges(self) -> list[dict]:
        """List all exchanges in the RabbitMQ server."""
        response = self._make_request('GET', 'exchanges')
        return response.json()

    def list_exchanges_by_vhost(self, vhost: str = '/') -> list[dict]:
        """List all exchanges in the RabbitMQ server for a specific vhost."""
        vhost_encoded = quote(vhost, safe='')
        response = self._make_request('GET', f'exchanges/{vhost_encoded}')
        return response.json()

    def get_queue_info(self, queue: str, vhost: str = '/') -> dict:
        """Get detailed information about a specific queue."""
        vhost_encoded = quote(vhost, safe='')
        response = self._make_request('GET', f'queues/{vhost_encoded}/{queue}')
        return response.json()

    def delete_queue(self, queue: str, vhost: str = '/') -> None:
        """Delete a queue."""
        validate_rabbitmq_name(queue, 'Queue name')
        vhost_encoded = quote(vhost, safe='')
        self._make_request('DELETE', f'queues/{vhost_encoded}/{queue}')

    def purge_queue(self, queue: str, vhost: str = '/') -> None:
        """Remove all messages from a queue."""
        validate_rabbitmq_name(queue, 'Queue name')
        vhost_encoded = quote(vhost, safe='')
        self._make_request('DELETE', f'queues/{vhost_encoded}/{queue}/contents')

    def get_exchange_info(self, exchange: str, vhost: str = '/') -> dict:
        """Get detailed information about a specific exchange."""
        vhost_encoded = quote(vhost, safe='')
        response = self._make_request('GET', f'exchanges/{vhost_encoded}/{exchange}')
        return response.json()

    def delete_exchange(self, exchange: str, vhost: str = '/') -> None:
        """Delete an exchange."""
        validate_rabbitmq_name(exchange, 'Exchange name')
        vhost_encoded = quote(vhost, safe='')
        self._make_request('DELETE', f'exchanges/{vhost_encoded}/{exchange}')

    def get_bindings(
        self, queue: Optional[str] = None, exchange: Optional[str] = None, vhost: str = '/'
    ) -> list[dict]:
        """Get bindings, optionally filtered by queue or exchange."""
        vhost_encoded = quote(vhost, safe='')
        if queue:
            validate_rabbitmq_name(queue, 'Queue name')
            response = self._make_request('GET', f'queues/{vhost_encoded}/{queue}/bindings')
        elif exchange:
            validate_rabbitmq_name(exchange, 'Exchange name')
            response = self._make_request(
                'GET', f'exchanges/{vhost_encoded}/{exchange}/bindings/source'
            )
        else:
            response = self._make_request('GET', f'bindings/{vhost_encoded}')
        return response.json()

    def get_overview(self) -> dict:
        """Get overview of RabbitMQ server including version, stats, and listeners."""
        response = self._make_request('GET', 'overview')
        return response.json()

    def list_vhosts(self) -> dict:
        """List all vhost in the RabbitMQ server."""
        response = self._make_request('GET', 'vhosts')
        return response.json()

    def list_shovels(self) -> list[dict]:
        """List all shovels in the RabbitMQ server."""
        response = self._make_request('GET', 'shovels')
        return response.json()

    def get_shovel_info(self, shovel_name: str, vhost: str = '/') -> dict:
        """Get detailed information about a specific shovel in a vhost."""
        vhost_encoded = quote(vhost, safe='')
        response = self._make_request('GET', f'parameters/shovel/{vhost_encoded}/{shovel_name}')
        return response.json()

    def get_cluster_nodes(self) -> dict:
        """Get a list of nodes in the RabbitMQ cluster."""
        response = self._make_request('GET', 'nodes')
        return response.json()

    def get_node_information(self, node_name: str) -> dict:
        """Get a node information."""
        response = self._make_request('GET', f'nodes/{node_name}')
        return response.json()

    def get_node_memory(self, node_name: str) -> dict:
        """Get a node memory usage breakdown information."""
        response = self._make_request('GET', f'nodes/{node_name}/memory')
        return response.json()

    def list_connections(self) -> dict:
        """List all connections on the RabbitMQ broker."""
        response = self._make_request('GET', 'connections')
        return response.json()

    def list_consumers(self) -> Any:
        """List all consumers on the RabbitMQ broker."""
        response = self._make_request('GET', 'consumers')
        return response.json()

    def list_users(self) -> Any:
        """List all users on the RabbitMQ broker."""
        response = self._make_request('GET', 'users')
        return response.json()

    def get_alarm_status(self) -> int:
        """Get the alarm status of the RabbitMQ broker."""
        response = self._make_request('GET', 'health/checks/alarms')
        return response.status_code

    def get_is_node_quorum_critical(self) -> int:
        """Check if there are quorum queues with minimum online quorum."""
        response = self._make_request('GET', 'checks/node-is-quorum-critical')
        return response.status_code

    def get_broker_definition(self) -> dict:
        """Get the broker definition."""
        response = self._make_request('GET', 'definitions')
        return response.json()
