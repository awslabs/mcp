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
