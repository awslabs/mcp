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

import pika
import ssl
from typing import Any
from urllib.parse import urlparse


class RabbitMQConnection:
    """RabbitMQ connection manager for message operations."""

    def __init__(self, hostname: str, username: str, password: str):
        """Initialize RabbitMQ connection parameters."""
        port = 5671
        host = hostname
        self.protocol = 'amqps'
        self.url = f'{self.protocol}://{username}:{password}@{host}:{port}'
        self.parameters = pika.URLParameters(self.url)
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.parameters.ssl_options = pika.SSLOptions(context=ssl_context)

    def get_channel(self) -> tuple[Any, Any]:
        """Create and return a connection and channel for RabbitMQ operations."""
        connection = pika.BlockingConnection(self.parameters)
        channel = connection.channel()
        return connection, channel


def validate_rabbitmq_name(name: str, field_name: str) -> None:
    """Validate RabbitMQ queue/exchange names."""
    if not name or not name.strip():
        raise ValueError(f'{field_name} cannot be empty')
    if not all(c.isalnum() or c in '-_.:' for c in name):
        raise ValueError(
            f'{field_name} can only contain letters, digits, hyphen, underscore, period, or colon'
        )
    if len(name) > 255:
        raise ValueError(f'{field_name} must be less than 255 characters')


def get_broker_hostname_from_id(mq_client: Any, broker_id: str) -> str:
    """Retrieve the broker hostname from Amazon MQ DescribeBroker API using the broker ID."""
    if not broker_id or not broker_id.strip():
        raise ValueError('broker_id cannot be empty')

    try:
        # Call DescribeBroker API using the provided client
        response = mq_client.describe_broker(BrokerId=broker_id)

        # Extract broker instances
        broker_instances = response.get('BrokerInstances', [])
        if not broker_instances:
            raise ValueError(
                f'No broker instances found for broker_id: {broker_id}. '
                f'The broker may not exist or may not be in a running state.'
            )

        # Get the first broker instance
        broker_instance = broker_instances[0]

        # Extract endpoints
        endpoints = broker_instance.get('Endpoints', [])
        if not endpoints:
            raise ValueError(
                f'No endpoints found for broker_id: {broker_id}. '
                f'The broker may not be fully provisioned yet.'
            )

        # Find the AMQPS endpoint (format: amqps://hostname:5671)
        amqps_endpoint = None
        for endpoint in endpoints:
            if endpoint.startswith('amqps://'):
                amqps_endpoint = endpoint
                break

        if not amqps_endpoint:
            raise ValueError(
                f'No AMQPS endpoint found for broker_id: {broker_id}. '
                f'Available endpoints: {endpoints}'
            )

        hostname = urlparse(amqps_endpoint).hostname

        return hostname

    except ValueError:
        # Re-raise ValueError as-is
        raise
    except Exception as e:
        # Wrap other exceptions with context
        raise Exception(f'Failed to retrieve broker hostname for {broker_id}: {str(e)}') from e
