"""Integration tests for RabbitMQ module with broker_id parameter."""

import pytest
from awslabs.amazon_mq_mcp_server.rabbitmq.module import RabbitMQModule
from unittest.mock import MagicMock, Mock, patch


class TestRabbitMQModuleBrokerId:
    """Integration tests for RabbitMQ module using broker_id."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions."""
        self.mock_mcp = Mock()
        self.captured_functions = {}
        self.mock_mq_client = MagicMock()

        def mock_mq_client_getter(region: str):
            return self.mock_mq_client

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp, mock_mq_client_getter)
        self.module.register_rabbitmq_management_tools()

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.admin.RabbitMQAdmin.test_connection')
    def test_initialize_connection_with_broker_id(self, mock_test_conn):
        """Test that initialize_connection accepts broker_id and retrieves hostname."""
        # Mock AWS API response
        self.mock_mq_client.describe_broker.return_value = {
            'BrokerInstances': [{'Endpoints': ['amqps://b-test-broker.mq.us-east-1.on.aws:5671']}]
        }
        mock_test_conn.return_value = None

        # Get the captured function
        func = self.captured_functions['rabbimq_broker_initialize_connection']

        # Execute - note the new parameters: broker_id and region
        result = func(
            broker_id='b-test-broker',
            region='us-east-1',
            username='admin',
            password='password123',  # pragma: allowlist secret
        )

        # Verify
        assert result == 'successfully connected'
        self.mock_mq_client.describe_broker.assert_called_once_with(BrokerId='b-test-broker')
        mock_test_conn.assert_called_once()

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.admin.RabbitMQAdmin.test_connection')
    def test_initialize_connection_with_oauth_and_broker_id(self, mock_test_conn):
        """Test that initialize_connection_with_oauth accepts broker_id."""
        # Mock AWS API response
        self.mock_mq_client.describe_broker.return_value = {
            'BrokerInstances': [{'Endpoints': ['amqps://b-oauth-broker.mq.us-west-2.on.aws:5671']}]
        }
        mock_test_conn.return_value = None

        # Get the captured function
        func = self.captured_functions['rabbimq_broker_initialize_connection_with_oauth']

        # Execute - note the new parameters: broker_id and region
        result = func(
            broker_id='b-oauth-broker',
            region='us-west-2',
            oauth_token='mock-oauth-token',
        )

        # Verify
        assert result == 'successfully connected'
        self.mock_mq_client.describe_broker.assert_called_once_with(BrokerId='b-oauth-broker')

    def test_initialize_connection_invalid_broker_id(self):
        """Test that invalid broker_id raises appropriate error."""
        # Mock AWS API to return no instances
        self.mock_mq_client.describe_broker.return_value = {'BrokerInstances': []}

        # Get the captured function
        func = self.captured_functions['rabbimq_broker_initialize_connection']

        # Execute and verify error
        with pytest.raises(ValueError) as exc_info:
            func(
                broker_id='b-nonexistent',
                region='us-east-1',
                username='admin',
                password='password123',  # pragma: allowlist secret
            )
        assert 'No broker instances found' in str(exc_info.value)

    def test_initialize_connection_empty_broker_id(self):
        """Test that empty broker_id raises ValueError."""
        # Get the captured function
        func = self.captured_functions['rabbimq_broker_initialize_connection']

        # Execute and verify error
        with pytest.raises(ValueError) as exc_info:
            func(
                broker_id='',
                region='us-east-1',
                username='admin',
                password='password123',  # pragma: allowlist secret
            )
        assert 'broker_id cannot be empty' in str(exc_info.value)

    def test_initialize_connection_empty_region(self):
        """Test that empty region parameter is accepted (region validation removed)."""
        # Mock AWS API response
        self.mock_mq_client.describe_broker.return_value = {
            'BrokerInstances': [{'Endpoints': ['amqps://b-test-broker.mq.us-east-1.on.aws:5671']}]
        }

        # Get the captured function
        func = self.captured_functions['rabbimq_broker_initialize_connection']

        # Execute - empty region should work since client getter handles it
        # This test now verifies that the function doesn't validate region
        # The client getter is responsible for region handling
        with patch('awslabs.amazon_mq_mcp_server.rabbitmq.admin.RabbitMQAdmin.test_connection'):
            result = func(
                broker_id='b-test-broker',
                region='',
                username='admin',
                password='password123',  # pragma: allowlist secret
            )
            assert result == 'successfully connected'

    def test_initialize_connection_aws_api_error(self):
        """Test handling of AWS API errors during broker lookup."""
        # Mock AWS API to raise an error
        self.mock_mq_client.describe_broker.side_effect = Exception('AccessDenied')

        # Get the captured function
        func = self.captured_functions['rabbimq_broker_initialize_connection']

        # Execute and verify error
        with pytest.raises(Exception) as exc_info:
            func(
                broker_id='b-test-broker',
                region='us-east-1',
                username='admin',
                password='password123',  # pragma: allowlist secret
            )
        assert 'Failed to retrieve broker hostname' in str(exc_info.value)
        assert 'AccessDenied' in str(exc_info.value)

    def test_tool_signature_has_broker_id_parameter(self):
        """Test that the tool signature includes broker_id and region parameters."""
        # Check rabbimq_broker_initialize_connection
        init_func = self.captured_functions['rabbimq_broker_initialize_connection']
        # Get the actual function parameters (not all local variables)
        import inspect

        sig = inspect.signature(init_func)
        param_names = list(sig.parameters.keys())

        assert 'broker_id' in param_names
        assert 'region' in param_names
        assert 'broker_hostname' not in param_names  # Should not be a parameter
        assert 'username' in param_names
        assert 'password' in param_names

        # Check rabbimq_broker_initialize_connection_with_oauth
        oauth_func = self.captured_functions['rabbimq_broker_initialize_connection_with_oauth']
        sig = inspect.signature(oauth_func)
        param_names = list(sig.parameters.keys())

        assert 'broker_id' in param_names
        assert 'region' in param_names
        assert 'broker_hostname' not in param_names  # Should not be a parameter
        assert 'oauth_token' in param_names
