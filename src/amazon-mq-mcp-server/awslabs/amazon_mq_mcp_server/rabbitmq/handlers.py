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

from .admin import RabbitMQAdmin
from .connection import RabbitMQConnection
from datetime import datetime
from pathlib import Path
from typing import Any, List


################################################
######      RabbitMQ doc handlers         ######
################################################


def handle_get_guidelines(guideline_name: str):
    """Get RabbitMQ operational guidelines."""
    script_dir = Path(__file__).parent
    content = ''
    if guideline_name == 'rabbimq_broker_sizing_guide':
        content = (script_dir / 'doc' / 'rabbitmq_broker_sizing_guide.md').read_text()

    elif guideline_name == 'rabbitmq_broker_setup_best_practices_guide':
        content = (script_dir / 'doc' / 'rabbitmq_setup_best_practice.md').read_text()

    elif guideline_name == 'rabbitmq_quorum_queue_migration_guide':
        content = (script_dir / 'doc' / 'rabbitmq_quorum_queue_migration_guide.md').read_text()

    elif guideline_name == 'rabbitmq_client_performance_optimization_guide':
        content = (
            script_dir / 'doc' / 'rabbitmq_performance_optimization_best_practice.md'
        ).read_text()

    elif guideline_name == 'rabbitmq_check_broker_follow_best_practice_instructions':
        content = (
            script_dir / 'doc' / 'rabbitmq_check_broker_follow_best_practice_instructions.md'
        ).read_text()

    else:
        raise ValueError(f"{guideline_name} doesn't exist")

    return content


################################################
######      RabbitMQ AMQP handlers        ######
################################################


def handle_enqueue(rabbitmq: RabbitMQConnection, queue: str, message: str):
    """Send a message to a RabbitMQ queue."""
    connection, channel = rabbitmq.get_channel()
    channel.queue_declare(queue)
    channel.basic_publish(exchange='', routing_key=queue, body=message)
    connection.close()


def handle_fanout(rabbitmq: RabbitMQConnection, exchange: str, message: str):
    """Publish a message to a fanout exchange."""
    connection, channel = rabbitmq.get_channel()
    channel.exchange_declare(exchange=exchange, exchange_type='fanout')
    channel.basic_publish(exchange=exchange, routing_key='', body=message)
    connection.close()


################################################
######      RabbitMQ admin handlers       ######
################################################

## Health check


def handle_get_overview(rabbitmq_admin: RabbitMQAdmin) -> dict:
    """Get the overview of the broker deployment."""
    return rabbitmq_admin.get_overview()


def handle_is_broker_in_alarm(rabbitmq_admin: RabbitMQAdmin) -> bool:
    """Check the alarm status of the RabbitMQ broker."""
    status = rabbitmq_admin.get_alarm_status()
    return False if status == 200 else True


def handle_is_node_in_quorum_critical(rabbitmq_admin: RabbitMQAdmin) -> bool:
    """Check if there are quorum queues with minimum online quorum."""
    status = rabbitmq_admin.get_is_node_quorum_critical()
    return False if status == 200 else True


def handle_get_definition(rabbitmq_admin: RabbitMQAdmin) -> dict:
    """Get the server definition."""
    return rabbitmq_admin.get_broker_definition()


## Connections


def handle_list_connections(rabbitmq_admin: RabbitMQAdmin) -> list[Any]:
    """List all connections on the RabbitMQ broker."""
    filtered_conn = []
    for c in rabbitmq_admin.list_connections():
        filtered_conn.append(
            {
                'auth_mechanism': c['auth_mechanism'],
                'num_channels': c['channels'],
                'client_properties': c['client_properties'],
                'connected_at': datetime.fromtimestamp(c['connected_at'] / 1000).strftime(
                    '%Y-%m-%d %H:%M:%S'
                ),
                'state': c['state'],
            }
        )

    return filtered_conn


def handle_list_consumers(rabbitmq_admin: RabbitMQAdmin) -> list[dict]:
    """List all consumers on the RabbitMQ broker."""
    return rabbitmq_admin.list_consumers()


## Cluster


def handle_get_cluster_nodes(rabbitmq_admin: RabbitMQAdmin) -> list[dict]:
    """Get the names of nodes in the cluster."""
    filtered_result = []
    for r in rabbitmq_admin.get_cluster_nodes():
        filtered_result.append(
            {
                'name': r['name'],
                'mem_alarm': r['mem_alarm'],
                'disk_free_alarm': r['disk_free_alarm'],
                'disk_free_in_bytes': r['disk_free'],
                'mem_limit_in_bytes': r['mem_limit'],
                'mem_used_in_bytes': r['mem_used'],
                'mem_used_in_percentage': (r['mem_used'] / r['mem_limit']) * 100,
                'rates_mode': r['rates_mode'],
                'uptime_in_milli_seconds': r['uptime'],
                'running': r['running'],
                'num_queue_created': r['queue_created'],
                'num_queue_deleted': r['queue_deleted'],
                'connection_created': r['connection_created'],
            }
        )

    return filtered_result


def handle_get_cluster_node_memory(rabbitmq_admin: RabbitMQAdmin, node_name: str) -> dict:
    """Get the information about a node in the cluster."""
    return rabbitmq_admin.get_node_memory(node_name=node_name)


## Queues


def handle_list_queues(rabbitmq_admin: RabbitMQAdmin) -> List[str]:
    """List all queue names in the RabbitMQ server."""
    result = rabbitmq_admin.list_queues()
    return [queue['name'] for queue in result]


def handle_list_queues_by_vhost(rabbitmq_admin: RabbitMQAdmin, vhost: str = '/') -> List[str]:
    """List all queue names in a specific vhost."""
    result = rabbitmq_admin.list_queues_by_vhost(vhost)
    return [queue['name'] for queue in result]


def handle_get_queue_info(rabbitmq_admin: RabbitMQAdmin, queue: str, vhost: str = '/') -> dict:
    """Get detailed information about a specific queue."""
    return rabbitmq_admin.get_queue_info(queue, vhost)


def handle_delete_queue(rabbitmq_admin: RabbitMQAdmin, queue: str, vhost: str = '/') -> None:
    """Delete a queue from the RabbitMQ server."""
    rabbitmq_admin.delete_queue(queue, vhost)


def handle_purge_queue(rabbitmq_admin: RabbitMQAdmin, queue: str, vhost: str = '/') -> None:
    """Remove all messages from a queue."""
    rabbitmq_admin.purge_queue(queue, vhost)


## Exchanges


def handle_list_exchanges(rabbitmq_admin: RabbitMQAdmin) -> List[str]:
    """List all exchange names in the RabbitMQ server."""
    result = rabbitmq_admin.list_exchanges()
    return [exchange['name'] for exchange in result]


def handle_list_exchanges_by_vhost(rabbitmq_admin: RabbitMQAdmin, vhost: str = '/') -> List[str]:
    """List all exchange names in a specific vhost."""
    result = rabbitmq_admin.list_exchanges_by_vhost(vhost)
    return [queue['name'] for queue in result]


def handle_delete_exchange(rabbitmq_admin: RabbitMQAdmin, exchange: str, vhost: str = '/') -> None:
    """Delete an exchange from the RabbitMQ server."""
    rabbitmq_admin.delete_exchange(exchange, vhost)


def handle_get_exchange_info(
    rabbitmq_admin: RabbitMQAdmin, exchange: str, vhost: str = '/'
) -> dict:
    """Get detailed information about a specific exchange."""
    return rabbitmq_admin.get_exchange_info(exchange, vhost)


## Vhosts


def handle_list_vhosts(rabbitmq_admin: RabbitMQAdmin) -> List[str]:
    """List all vhost names in the RabbitMQ server."""
    result = rabbitmq_admin.list_vhosts()
    return [vhost['name'] for vhost in result]


## Shovels


def handle_list_shovels(rabbitmq_admin: RabbitMQAdmin) -> List[dict]:
    """List all shovels in the RabbitMQ server."""
    return rabbitmq_admin.list_shovels()


def handle_shovel(rabbitmq_admin: RabbitMQAdmin, shovel_name: str, vhost: str = '/') -> dict:
    """Get detailed information about a specific shovel."""
    return rabbitmq_admin.get_shovel_info(shovel_name, vhost)


## Users


def handle_list_users(rabbitmq_admin: RabbitMQAdmin) -> list[dict]:
    """List all users on the RabbitMQ broker."""
    return rabbitmq_admin.list_users()
