# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pika
import pytest
from awslabs.amazon_mq_mcp_server.rabbitmq.connection import (
    RabbitMQConnection,
    validate_rabbitmq_name,
)
from string import punctuation
from unittest.mock import MagicMock, patch


class TestRabbitMQConnection:
    """Tests for RabbitMQConnection class."""

    def test_init_with_tls(self):
        """Test initialization with TLS enabled."""
        conn = RabbitMQConnection('test-host', 'user', 'pass')
        assert conn.protocol == 'amqps'
        assert conn.url == 'amqps://user:pass@test-host:5671'  # pragma: allowlist secret
        assert conn.parameters.ssl_options is not None

    @pytest.mark.parametrize(
        ('username', 'password'),
        [
            ('user', f'synthetic{character}password')
            for character in punctuation
            if character not in ',:='
        ]
        + [
            ('user.name_1', 'synthetic-password'),
            ('user', 'synthetic%2Fpassword'),
            ('user', 'synthetic%41password'),
            ('user', 'synthetic@%/#?password'),
            ('user', 'aB3#' * 62 + 'xY'),
        ],
    )
    def test_init_preserves_credentials(self, username, password):
        """Preserve literal credentials when constructing AMQPS connection parameters."""
        conn = RabbitMQConnection('test-host', username, password)

        credentials = conn.parameters.credentials
        assert isinstance(credentials, pika.PlainCredentials)
        assert credentials.username == username
        assert credentials.password == password
        assert conn.parameters.host == 'test-host'
        assert conn.parameters.port == 5671
        assert conn.parameters.virtual_host == '/'
        assert conn.parameters.ssl_options is not None

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.connection.pika.BlockingConnection')
    def test_get_channel(self, mock_connection_class):
        """Test getting a channel."""
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel
        mock_connection_class.return_value = mock_connection
        conn = RabbitMQConnection('test-host', 'user', 'pass')
        connection, channel = conn.get_channel()
        assert connection == mock_connection
        assert channel == mock_channel
        mock_connection_class.assert_called_once_with(conn.parameters)


class TestValidateRabbitMQName:
    """Tests for validate_rabbitmq_name function."""

    def test_valid_names(self):
        """Test valid RabbitMQ names."""
        valid_names = ['test', 'test-queue', 'test_queue', 'test.queue', 'test:queue', '123']
        for name in valid_names:
            validate_rabbitmq_name(name, 'test')  # Should not raise

    def test_empty_name(self):
        """Test empty name validation."""
        with pytest.raises(ValueError, match='test cannot be empty'):
            validate_rabbitmq_name('', 'test')
        with pytest.raises(ValueError, match='test cannot be empty'):
            validate_rabbitmq_name('   ', 'test')

    def test_invalid_characters(self):
        """Test invalid characters in name."""
        with pytest.raises(ValueError, match='can only contain letters, digits'):
            validate_rabbitmq_name('test@queue', 'test')

    def test_name_too_long(self):
        """Test name length validation."""
        long_name = 'a' * 256
        with pytest.raises(ValueError, match='must be less than 255 characters'):
            validate_rabbitmq_name(long_name, 'test')
