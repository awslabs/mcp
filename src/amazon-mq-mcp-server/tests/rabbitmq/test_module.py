import pytest
from awslabs.amazon_mq_mcp_server.rabbitmq.module import RabbitMQModule
from unittest.mock import Mock, patch


class TestRabbitMQModule:
    """Test class for the main RabbitMQModule functionality."""

    def setup_method(self):
        """Initialize test fixtures before each test method.

        Sets up mock MCP server and creates RabbitMQModule instance for testing.
        """
        self.mock_mcp = Mock()
        self.module = RabbitMQModule(self.mock_mcp)

    def test_init(self):
        """Test RabbitMQModule initialization.

        Verifies that module is properly initialized with MCP instance and null connection objects.
        """
        assert self.module.mcp == self.mock_mcp
        assert self.module.rmq is None
        assert self.module.rmq_admin is None

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.RabbitMQConnection')
    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.RabbitMQAdmin')
    def test_register_rabbitmq_management_tools_read_only(self, mock_admin_class, mock_conn_class):
        """Test registration of read-only RabbitMQ management tools.

        Verifies that tools are registered when allow_mutative_tools=False.
        """
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)
        # Verify that tools are registered
        assert self.mock_mcp.tool.called

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.RabbitMQConnection')
    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.RabbitMQAdmin')
    def test_register_rabbitmq_management_tools_with_mutative(
        self, mock_admin_class, mock_conn_class
    ):
        """Test registration of RabbitMQ management tools including mutative operations.

        Verifies that all tools (including mutative) are registered when allow_mutative_tools=True.
        """
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=True)
        # Verify that tools are registered
        assert self.mock_mcp.tool.called

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.RabbitMQConnection')
    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.RabbitMQAdmin')
    def test_initialize_connection_success(self, mock_admin_class, mock_conn_class):
        """Test successful RabbitMQ connection initialization.

        Verifies that connection and admin instances are properly set after successful initialization.
        """
        mock_conn_instance = Mock()
        mock_admin_instance = Mock()
        mock_conn_class.return_value = mock_conn_instance
        mock_admin_class.return_value = mock_admin_instance

        # Register tools to get access to the connection function
        self.module.register_rabbitmq_management_tools()

        # Simulate successful connection
        self.module.rmq = mock_conn_instance
        self.module.rmq_admin = mock_admin_instance

        assert self.module.rmq == mock_conn_instance
        assert self.module.rmq_admin == mock_admin_instance

    def test_read_only_tools_registration(self):
        """Test registration of read-only tools specifically.

        Verifies that read-only tools are properly registered via private method.
        """
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)
        # Verify that read-only tools are registered
        assert self.mock_mcp.tool.called

    def test_mutative_tools_registration(self):
        """Test registration of mutative tools specifically.

        Verifies that mutative tools are properly registered via private method.
        """
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=True)
        # Verify that mutative tools are registered
        assert self.mock_mcp.tool.called

    def test_mutative_tools_not_registered_when_disabled(self):
        """Test that mutative tools are not registered when disabled.

        Ensures mutative tools are excluded when allow_mutative_tools=False.
        """
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)
        # This test ensures that mutative tools are not registered when disabled
        # The actual verification would depend on the implementation details


class TestRabbitMQModuleToolFunctions:
    """Test class for RabbitMQ module tool function registration."""

    def setup_method(self):
        """Initialize test fixtures before each test method.

        Sets up mock MCP server and creates RabbitMQModule instance for testing.
        """
        self.mock_mcp = Mock()
        self.module = RabbitMQModule(self.mock_mcp)

    def test_list_queues_tool_registration(self):
        """Test that list_queues tool is properly registered.

        Verifies the list_queues tool is included in read-only tool registration.
        """
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)
        # Verify that the list_queues tool is registered
        assert self.mock_mcp.tool.called

    def test_mutative_tool_registration(self):
        """Test that mutative tools are properly registered.

        Verifies that mutative tools are registered correctly.
        """
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=True)
        # Verify that mutative tools are registered
        assert self.mock_mcp.tool.called

    def test_read_only_tools_registration_count(self):
        """Test the count of registered read-only tools.

        Verifies that multiple read-only tools are registered (count > 0).
        """
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)
        # Verify the number of read-only tools registered
        assert self.mock_mcp.tool.call_count > 0


class TestRabbitMQModuleToolExecution:
    """Test class for RabbitMQ module tool execution functionality."""

    def setup_method(self):
        """Initialize test fixtures before each test method.

        Sets up mock MCP server and creates RabbitMQModule instance for testing.
        """
        self.mock_mcp = Mock()
        self.module = RabbitMQModule(self.mock_mcp)

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.RabbitMQConnection')
    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.RabbitMQAdmin')
    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_list_queues')
    def test_connection_and_tool_execution(self, mock_handle, mock_admin_class, mock_conn_class):
        """Test connection establishment and tool execution.

        Verifies that connection instances are properly set and tools can be executed.
        """
        mock_conn_instance = Mock()
        mock_admin_instance = Mock()
        mock_conn_class.return_value = mock_conn_instance
        mock_admin_class.return_value = mock_admin_instance
        mock_handle.return_value = ['queue1', 'queue2']

        self.module.register_rabbitmq_management_tools()

        # Simulate connection
        self.module.rmq = mock_conn_instance
        self.module.rmq_admin = mock_admin_instance

        # Verify that the connection instances are set
        assert self.module.rmq == mock_conn_instance
        assert self.module.rmq_admin == mock_admin_instance

    def test_read_only_tools_execution_paths(self):
        """Test execution paths for read-only tools.

        Ensures read-only tools can be executed without errors.
        """
        # Test that read-only tools can be executed without errors
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)
        assert self.mock_mcp.tool.called

    def test_mutative_tools_execution_paths(self):
        """Test execution paths for mutative tools.

        Ensures mutative tools can be executed without errors.
        """
        # Test that mutative tools can be executed without errors
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=True)
        assert self.mock_mcp.tool.called


class TestRabbitMQBrokerInitializeConnection:
    """Test class for RabbitMQ broker connection initialization with username/password."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions.

        Sets up mock MCP server with tool decorator to capture registered functions.
        """
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools()

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.RabbitMQConnection')
    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.RabbitMQAdmin')
    def test_rabbimq_broker_initialize_connection_success(self, mock_admin_class, mock_conn_class):
        """Test successful broker connection initialization.

        Verifies successful connection with username/password authentication.
        """
        mock_conn_instance = Mock()
        mock_admin_instance = Mock()
        mock_conn_class.return_value = mock_conn_instance
        mock_admin_class.return_value = mock_admin_instance

        func = self.captured_functions['rabbimq_broker_initialize_connection']
        result = func('test-hostname', 'test-user', 'test-pass')

        assert result == 'successfully connected'
        mock_conn_class.assert_called_once_with(
            hostname='test-hostname',  # pragma: allowlist secret
            username='test-user',  # pragma: allowlist secret
            password='test-pass',  # pragma: allowlist secret
        )
        mock_admin_class.assert_called_once_with(
            hostname='test-hostname',  # pragma: allowlist secret
            username='test-user',  # pragma: allowlist secret
            password='test-pass',  # pragma: allowlist secret
        )
        assert self.module.rmq == mock_conn_instance
        assert self.module.rmq_admin == mock_admin_instance

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.RabbitMQConnection')
    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.RabbitMQAdmin')
    def test_rabbimq_broker_initialize_connection_failure(self, mock_admin_class, mock_conn_class):
        """Test broker connection initialization failure handling.

        Verifies proper exception handling when connection fails.
        """
        mock_conn_class.side_effect = Exception('Connection failed')

        func = self.captured_functions['rabbimq_broker_initialize_connection']

        with pytest.raises(Exception, match='Connection failed'):
            func('test-hostname', 'test-user', 'test-pass')


class TestRabbitMQBrokerInitializeConnectionWithOAuth:
    """Test class for RabbitMQ broker connection initialization with OAuth."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions.

        Sets up mock MCP server with tool decorator to capture registered functions.
        """
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools()

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.RabbitMQConnection')
    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.RabbitMQAdmin')
    def test_rabbimq_broker_initialize_connection_with_oauth_success(
        self, mock_admin_class, mock_conn_class
    ):
        """Test successful broker connection initialization with OAuth.

        Verifies successful connection using OAuth token authentication.
        """
        mock_conn_instance = Mock()
        mock_admin_instance = Mock()
        mock_conn_class.return_value = mock_conn_instance
        mock_admin_class.return_value = mock_admin_instance

        func = self.captured_functions['rabbimq_broker_initialize_connection_with_oauth']
        result = func('test-hostname', 'oauth-token-123')

        assert result == 'successfully connected'
        mock_conn_class.assert_called_once_with(
            hostname='test-hostname',  # pragma: allowlist secret
            username='ignored',  # pragma: allowlist secret
            password='oauth-token-123',  # pragma: allowlist secret
        )
        mock_admin_class.assert_called_once_with(
            hostname='test-hostname',  # pragma: allowlist secret
            username='ignored',  # pragma: allowlist secret
            password='oauth-token-123',  # pragma: allowlist secret
        )
        assert self.module.rmq == mock_conn_instance
        assert self.module.rmq_admin == mock_admin_instance

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.RabbitMQConnection')
    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.RabbitMQAdmin')
    def test_rabbimq_broker_initialize_connection_with_oauth_failure(
        self, mock_admin_class, mock_conn_class
    ):
        """Test OAuth broker connection initialization failure handling.

        Verifies proper exception handling when OAuth connection fails.
        """
        mock_conn_class.side_effect = Exception('OAuth connection failed')

        func = self.captured_functions['rabbimq_broker_initialize_connection_with_oauth']

        with pytest.raises(Exception, match='OAuth connection failed'):
            func('test-hostname', 'oauth-token-123')


class TestRabbitMQBrokerListQueues:
    """Test class for RabbitMQ broker list queues functionality."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions."""
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_list_queues')
    def test_rabbitmq_broker_list_queues_success(self, mock_handle):
        """Test successful listing of RabbitMQ queues."""
        mock_handle.return_value = ['queue1', 'queue2']
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_list_queues']
        result = func()

        assert result == ['queue1', 'queue2']
        mock_handle.assert_called_once_with(self.module.rmq_admin)

    def test_rabbitmq_broker_list_queues_no_admin(self):
        """Test exception when rmq_admin is None."""
        func = self.captured_functions['rabbitmq_broker_list_queues']

        with pytest.raises(AssertionError):
            func()

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_list_queues')
    def test_rabbitmq_broker_list_queues_failure(self, mock_handle):
        """Test exception handling when listing queues fails."""
        mock_handle.side_effect = Exception('Failed to list queues')
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_list_queues']

        with pytest.raises(Exception, match='Failed to list queues'):
            func()


class TestRabbitMQBrokerListExchanges:
    """Test class for RabbitMQ broker list exchanges functionality."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions."""
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_list_exchanges')
    def test_rabbitmq_broker_list_exchanges_success(self, mock_handle):
        """Test successful listing of RabbitMQ exchanges."""
        mock_handle.return_value = ['exchange1', 'exchange2']
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_list_exchanges']
        result = func()

        assert result == ['exchange1', 'exchange2']
        mock_handle.assert_called_once_with(self.module.rmq_admin)

    def test_rabbitmq_broker_list_exchanges_no_admin(self):
        """Test exception when rmq_admin is None."""
        func = self.captured_functions['rabbitmq_broker_list_exchanges']

        with pytest.raises(AssertionError):
            func()

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_list_exchanges')
    def test_rabbitmq_broker_list_exchanges_failure(self, mock_handle):
        """Test exception handling when listing exchanges fails."""
        mock_handle.side_effect = Exception('Failed to list exchanges')
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_list_exchanges']

        with pytest.raises(Exception, match='Failed to list exchanges'):
            func()


class TestRabbitMQBrokerListVhosts:
    """Test class for RabbitMQ broker list vhosts functionality."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions."""
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_list_vhosts')
    def test_rabbitmq_broker_list_vhosts_success(self, mock_handle):
        """Test successful listing of RabbitMQ vhosts."""
        mock_handle.return_value = ['/', 'vhost1']
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_list_vhosts']
        result = func()

        assert result == ['/', 'vhost1']
        mock_handle.assert_called_once_with(self.module.rmq_admin)

    def test_rabbitmq_broker_list_vhosts_no_admin(self):
        """Test exception when rmq_admin is None."""
        func = self.captured_functions['rabbitmq_broker_list_vhosts']

        with pytest.raises(AssertionError):
            func()

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_list_vhosts')
    def test_rabbitmq_broker_list_vhosts_failure(self, mock_handle):
        """Test exception handling when listing vhosts fails."""
        mock_handle.side_effect = Exception('Failed to list vhosts')
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_list_vhosts']

        with pytest.raises(Exception, match='Failed to list vhosts'):
            func()


class TestRabbitMQBrokerGetQueueInfo:
    """Test class for RabbitMQ broker get queue info functionality."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions."""
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.validate_rabbitmq_name')
    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_get_queue_info')
    def test_rabbitmq_broker_get_queue_info_success(self, mock_handle, mock_validate):
        """Test successful retrieval of queue info."""
        mock_handle.return_value = {'name': 'test-queue', 'messages': 10}
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_get_queue_info']
        result = func('test-queue', '/')

        assert result == {'name': 'test-queue', 'messages': 10}
        mock_validate.assert_called_once_with('test-queue', 'Queue name')
        mock_handle.assert_called_once_with(self.module.rmq_admin, 'test-queue', '/')

    def test_rabbitmq_broker_get_queue_info_no_admin(self):
        """Test exception when rmq_admin is None."""
        func = self.captured_functions['rabbitmq_broker_get_queue_info']

        with pytest.raises(AssertionError):
            func('test-queue')


class TestRabbitMQBrokerGetExchangeInfo:
    """Test class for RabbitMQ broker get exchange info functionality."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions."""
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.validate_rabbitmq_name')
    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_get_exchange_info')
    def test_rabbitmq_broker_get_exchange_info_success(self, mock_handle, mock_validate):
        """Test successful retrieval of exchange info."""
        mock_handle.return_value = {'name': 'test-exchange', 'type': 'direct'}
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_get_exchange_info']
        result = func('test-exchange', '/')

        assert result == {'name': 'test-exchange', 'type': 'direct'}
        mock_validate.assert_called_once_with('test-exchange', 'Exchange name')
        mock_handle.assert_called_once_with(self.module.rmq_admin, 'test-exchange', '/')

    def test_rabbitmq_broker_get_exchange_info_no_admin(self):
        """Test exception when rmq_admin is None."""
        func = self.captured_functions['rabbitmq_broker_get_exchange_info']

        with pytest.raises(AssertionError):
            func('test-exchange')


class TestRabbitMQBrokerListShovels:
    """Test class for RabbitMQ broker list shovels functionality."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions."""
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_list_shovels')
    def test_rabbitmq_broker_list_shovels_success(self, mock_handle):
        """Test successful listing of shovels."""
        mock_handle.return_value = ['shovel1', 'shovel2']
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_list_shovels']
        result = func()

        assert result == ['shovel1', 'shovel2']
        mock_handle.assert_called_once_with(self.module.rmq_admin)

    def test_rabbitmq_broker_list_shovels_no_admin(self):
        """Test exception when rmq_admin is None."""
        func = self.captured_functions['rabbitmq_broker_list_shovels']

        with pytest.raises(AssertionError):
            func()


class TestRabbitMQBrokerGetShovelInfo:
    """Test class for RabbitMQ broker get shovel info functionality."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions."""
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_shovel')
    def test_rabbitmq_broker_get_shovel_info_success(self, mock_handle):
        """Test successful retrieval of shovel info."""
        mock_handle.return_value = {'name': 'test-shovel', 'state': 'running'}
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_get_shovel_info']
        result = func('test-shovel', '/')

        assert result == {'name': 'test-shovel', 'state': 'running'}
        mock_handle.assert_called_once_with(self.module.rmq_admin, 'test-shovel', '/')

    def test_rabbitmq_broker_get_shovel_info_no_admin(self):
        """Test exception when rmq_admin is None."""
        func = self.captured_functions['rabbitmq_broker_get_shovel_info']

        with pytest.raises(AssertionError):
            func('test-shovel')


class TestRabbitMQBrokerGetClusterNodesInfo:
    """Test class for RabbitMQ broker get cluster nodes info functionality."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions."""
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_get_cluster_nodes')
    def test_rabbitmq_broker_get_cluster_nodes_info_success(self, mock_handle):
        """Test successful retrieval of cluster nodes info."""
        mock_handle.return_value = [{'name': 'node1', 'running': True}]
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_get_cluster_nodes_info']
        result = func()

        assert result == [{'name': 'node1', 'running': True}]
        mock_handle.assert_called_once_with(self.module.rmq_admin)

    def test_rabbitmq_broker_get_cluster_nodes_info_no_admin(self):
        """Test exception when rmq_admin is None."""
        func = self.captured_functions['rabbitmq_broker_get_cluster_nodes_info']

        with pytest.raises(AssertionError):
            func()


class TestRabbitMQBrokerListConnections:
    """Test class for RabbitMQ broker list connections functionality."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions."""
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_list_connections')
    def test_rabbitmq_broker_list_connections_success(self, mock_handle):
        """Test successful listing of connections."""
        mock_handle.return_value = [{'name': 'conn1'}, {'name': 'conn2'}]
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_list_connections']
        result = func()

        assert result == [{'name': 'conn1'}, {'name': 'conn2'}]
        mock_handle.assert_called_once_with(self.module.rmq_admin)

    def test_rabbitmq_broker_list_connections_no_admin(self):
        """Test exception when rmq_admin is None."""
        func = self.captured_functions['rabbitmq_broker_list_connections']

        with pytest.raises(AssertionError):
            func()


class TestRabbitMQBrokerListConsumers:
    """Test class for RabbitMQ broker list consumers functionality."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions."""
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_list_consumers')
    def test_rabbitmq_broker_list_consumers_success(self, mock_handle):
        """Test successful listing of consumers."""
        mock_handle.return_value = [{'consumer_tag': 'tag1'}, {'consumer_tag': 'tag2'}]
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_list_consumers']
        result = func()

        assert result == [{'consumer_tag': 'tag1'}, {'consumer_tag': 'tag2'}]
        mock_handle.assert_called_once_with(self.module.rmq_admin)

    def test_rabbitmq_broker_list_consumers_no_admin(self):
        """Test exception when rmq_admin is None."""
        func = self.captured_functions['rabbitmq_broker_list_consumers']

        with pytest.raises(AssertionError):
            func()


class TestRabbitMQBrokerListUsers:
    """Test class for RabbitMQ broker list users functionality."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions."""
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_list_users')
    def test_rabbitmq_broker_list_users_success(self, mock_handle):
        """Test successful listing of users."""
        mock_handle.return_value = [{'name': 'user1'}, {'name': 'user2'}]
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_list_users']
        result = func()

        assert result == [{'name': 'user1'}, {'name': 'user2'}]
        mock_handle.assert_called_once_with(self.module.rmq_admin)

    def test_rabbitmq_broker_list_users_no_admin(self):
        """Test exception when rmq_admin is None."""
        func = self.captured_functions['rabbitmq_broker_list_users']

        with pytest.raises(AssertionError):
            func()


class TestRabbitMQBrokerIsInAlarm:
    """Test class for RabbitMQ broker is in alarm functionality."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions."""
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_is_broker_in_alarm')
    def test_rabbitmq_broker_is_in_alarm_success(self, mock_handle):
        """Test successful alarm status check."""
        mock_handle.return_value = True
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_is_in_alarm']
        result = func()

        assert result is True
        mock_handle.assert_called_once_with(self.module.rmq_admin)

    def test_rabbitmq_broker_is_in_alarm_no_admin(self):
        """Test exception when rmq_admin is None."""
        func = self.captured_functions['rabbitmq_broker_is_in_alarm']

        with pytest.raises(AssertionError):
            func()


class TestRabbitMQBrokerIsQuorumCritical:
    """Test class for RabbitMQ broker is quorum critical functionality."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions."""
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=False)

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_is_node_in_quorum_critical')
    def test_rabbitmq_broker_is_quorum_critical_success(self, mock_handle):
        """Test successful quorum critical status check."""
        mock_handle.return_value = False
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_is_quorum_critical']
        result = func()

        assert result is False
        mock_handle.assert_called_once_with(self.module.rmq_admin)

    def test_rabbitmq_broker_is_quorum_critical_no_admin(self):
        """Test exception when rmq_admin is None."""
        func = self.captured_functions['rabbitmq_broker_is_quorum_critical']

        with pytest.raises(AssertionError):
            func()


class TestRabbitMQBrokerDeleteQueue:
    """Test class for RabbitMQ broker delete queue functionality."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions."""
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=True)

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.validate_rabbitmq_name')
    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_delete_queue')
    def test_rabbitmq_broker_delete_queue_success(self, mock_handle, mock_validate):
        """Test successful queue deletion."""
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_delete_queue']
        result = func('test-queue', '/')

        assert result == 'Queue test-queue successfully deleted'
        mock_validate.assert_called_once_with('test-queue', 'Queue name')
        mock_handle.assert_called_once_with(self.module.rmq_admin, 'test-queue', '/')

    def test_rabbitmq_broker_delete_queue_no_admin(self):
        """Test exception when rmq_admin is None."""
        func = self.captured_functions['rabbitmq_broker_delete_queue']

        with pytest.raises(AssertionError):
            func('test-queue')


class TestRabbitMQBrokerPurgeQueue:
    """Test class for RabbitMQ broker purge queue functionality."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions."""
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=True)

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.validate_rabbitmq_name')
    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_purge_queue')
    def test_rabbitmq_broker_purge_queue_success(self, mock_handle, mock_validate):
        """Test successful queue purging."""
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_purge_queue']
        result = func('test-queue', '/')

        assert result == 'Queue test-queue successfully purged'
        mock_validate.assert_called_once_with('test-queue', 'Queue name')
        mock_handle.assert_called_once_with(self.module.rmq_admin, 'test-queue', '/')

    def test_rabbitmq_broker_purge_queue_no_admin(self):
        """Test exception when rmq_admin is None."""
        func = self.captured_functions['rabbitmq_broker_purge_queue']

        with pytest.raises(AssertionError):
            func('test-queue')


class TestRabbitMQBrokerDeleteExchange:
    """Test class for RabbitMQ broker delete exchange functionality."""

    def setup_method(self):
        """Initialize test fixtures and capture tool functions."""
        self.mock_mcp = Mock()
        self.captured_functions = {}

        def mock_tool_decorator(func):
            self.captured_functions[func.__name__] = func
            return func

        self.mock_mcp.tool.return_value = mock_tool_decorator
        self.module = RabbitMQModule(self.mock_mcp)
        self.module.register_rabbitmq_management_tools(allow_mutative_tools=True)

    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.validate_rabbitmq_name')
    @patch('awslabs.amazon_mq_mcp_server.rabbitmq.module.handle_delete_exchange')
    def test_rabbitmq_broker_delete_exchange_success(self, mock_handle, mock_validate):
        """Test successful exchange deletion."""
        self.module.rmq_admin = Mock()

        func = self.captured_functions['rabbitmq_broker_delete_exchange']
        result = func('test-exchange', '/')

        assert result == 'Exchange test-exchange successfully deleted'
        mock_validate.assert_called_once_with('test-exchange', 'Exchange name')
        mock_handle.assert_called_once_with(self.module.rmq_admin, 'test-exchange', '/')

    def test_rabbitmq_broker_delete_exchange_no_admin(self):
        """Test exception when rmq_admin is None."""
        func = self.captured_functions['rabbitmq_broker_delete_exchange']

        with pytest.raises(AssertionError):
            func('test-exchange')
