"""Tests for the SQS module of amazon-sns-sqs-mcp-server."""

from awslabs.amazon_sns_sqs_mcp_server.common import MCP_SERVER_VERSION_TAG
from awslabs.amazon_sns_sqs_mcp_server.consts import MCP_SERVER_VERSION
from awslabs.amazon_sns_sqs_mcp_server.sqs import (
    create_queue_override,
    is_mutative_action_allowed,
    register_sqs_tools,
)
from unittest.mock import MagicMock, patch


class TestSQSTools:
    """Test SQS tools."""

    def test_create_queue_override(self):
        """Test create_queue_override function."""
        # Mock FastMCP
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda x: x)

        # Mock SQS client getter
        mock_sqs_client = MagicMock()
        mock_sqs_client_getter = MagicMock(return_value=mock_sqs_client)

        # Call the function
        create_queue_override(mock_mcp, mock_sqs_client_getter, '')

        # Assert tool was registered
        assert mock_mcp.tool.called

    def test_allow_mutative_action_only_on_tagged_sqs_resource(self):
        """Test allow_mutative_action_only_on_tagged_sqs_resource function."""
        # Mock FastMCP
        mock_mcp = MagicMock()

        # Mock SQS client with tagged resource
        mock_sqs_client = MagicMock()
        mock_sqs_client.list_queue_tags.return_value = {'Tags': {MCP_SERVER_VERSION_TAG: '1.0.0'}}

        # Test with valid QueueUrl
        result, _ = is_mutative_action_allowed(
            mock_mcp,
            mock_sqs_client,
            {'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'},
        )
        assert result is True

        # Test with missing QueueUrl
        result, message = is_mutative_action_allowed(mock_mcp, mock_sqs_client, {})
        assert result is False
        assert message == 'QueueUrl is not passed to the tool'

        # Test with untagged resource
        mock_sqs_client.list_queue_tags.return_value = {'Tags': {}}
        result, message = is_mutative_action_allowed(
            mock_mcp,
            mock_sqs_client,
            {'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'},
        )
        assert result is False
        assert message == 'mutating a resource without the mcp_server_version tag is not allowed'

    @patch('boto3.client')
    @patch('awslabs.amazon_sns_sqs_mcp_server.sqs.AWSToolGenerator')
    def test_register_sqs_tools(self, mock_aws_tool_generator, mock_boto3_client):
        """Test register_sqs_tools function."""
        # Create a mock tool generator instance
        mock_generator_instance = MagicMock()
        mock_aws_tool_generator.return_value = mock_generator_instance

        # Mock FastMCP
        mock_mcp = MagicMock()

        # Call the function
        register_sqs_tools(mock_mcp)

        # Verify AWSToolGenerator was instantiated
        mock_aws_tool_generator.assert_called_once()

        # Verify that generate() was called on the instance
        mock_generator_instance.generate.assert_called_once()

    @patch('boto3.client')
    @patch('awslabs.amazon_sns_sqs_mcp_server.sqs.AWSToolGenerator')
    def test_register_sqs_tools_with_disallow_resource_creation(
        self, mock_aws_tool_generator, mock_boto3_client
    ):
        """Test register_sqs_tools function with disallow_resource_creation=True."""
        # Mock FastMCP
        mock_mcp = MagicMock()

        # Create a spy that captures the tool_configuration
        tool_config_capture = {}

        # Define a mock AWSToolGenerator that captures the tool_configuration
        def mock_generator(
            service_name,
            service_display_name,
            mcp,
            tool_configuration,
            skip_param_documentation,
            mcp_server_version=MCP_SERVER_VERSION,
        ):
            nonlocal tool_config_capture
            tool_config_capture = tool_configuration
            return MagicMock()

        # Set our mock function as the side effect
        mock_aws_tool_generator.side_effect = mock_generator

        # Call the function with disallow_resource_creation=True
        register_sqs_tools(mock_mcp, disallow_resource_creation=True)

        # Verify that create_queue is set to be ignored in the tool_configuration
        assert 'create_queue' in tool_config_capture
        assert tool_config_capture['create_queue'] == {'ignore': True}

    def test_validator_with_different_operations(self):
        """Test validator with different SQS operations."""
        # Mock FastMCP
        mock_mcp = MagicMock()

        # Mock SQS client with tagged resource
        mock_sqs_client = MagicMock()
        mock_sqs_client.list_queue_tags.return_value = {'Tags': {MCP_SERVER_VERSION_TAG: '1.0.0'}}

        # Test with send_message (uses QueueUrl)
        result, _ = is_mutative_action_allowed(
            mock_mcp,
            mock_sqs_client,
            {
                'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue',
                'MessageBody': 'Hello world',
            },
        )
        assert result is True

        # Test with receive_message (uses QueueUrl)
        result, _ = is_mutative_action_allowed(
            mock_mcp,
            mock_sqs_client,
            {
                'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue',
                'MaxNumberOfMessages': 10,
            },
        )
        assert result is True

        # Test with send_message_batch (uses QueueUrl)
        result, _ = is_mutative_action_allowed(
            mock_mcp,
            mock_sqs_client,
            {
                'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue',
                'Entries': [],
            },
        )
        assert result is True

        # Test with delete_message (uses QueueUrl)
        result, _ = is_mutative_action_allowed(
            mock_mcp,
            mock_sqs_client,
            {
                'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue',
                'ReceiptHandle': 'receipt-handle',
            },
        )
        assert result is True

    def test_create_queue_override_implementation(self):
        """Test create_queue_override function implementation."""
        # Mock FastMCP
        mock_mcp = MagicMock()

        # Capture the decorated function
        decorated_func = None

        def capture_func(func):
            nonlocal decorated_func
            decorated_func = func
            return func

        mock_mcp.tool.return_value = capture_func

        # Mock SQS client
        mock_sqs_client = MagicMock()
        mock_sqs_client.create_queue.return_value = {
            'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'
        }
        mock_sqs_client_getter = MagicMock(return_value=mock_sqs_client)

        # Call the function
        create_queue_override(mock_mcp, mock_sqs_client_getter, '')

        # Verify the decorated function was captured
        assert decorated_func is not None

        # Test with standard queue
        result = decorated_func(
            queue_name='test-queue',
            attributes={'DelaySeconds': '60'},
            tags={'Environment': 'Test'},
            region='us-west-2',
        )

        # Verify client was created with correct region
        mock_sqs_client_getter.assert_called_with('us-west-2')

        # Verify create_queue was called with correct parameters
        mock_sqs_client.create_queue.assert_called_with(
            QueueName='test-queue',
            Attributes={'DelaySeconds': '60'},
            tags={'Environment': 'Test', MCP_SERVER_VERSION_TAG: MCP_SERVER_VERSION},
        )

        # Verify result
        assert result == {
            'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'
        }

        # Test with FIFO queue
        mock_sqs_client.create_queue.reset_mock()
        result = decorated_func(
            queue_name='test-queue.fifo', attributes={}, tags={}, region='us-east-1'
        )

        # Verify FIFO attributes were added
        mock_sqs_client.create_queue.assert_called_with(
            QueueName='test-queue.fifo',
            Attributes={
                'FifoQueue': 'true',
                'DeduplicationScope': 'messageGroup',
                'FifoThroughputLimit': 'perMessageGroupId',
            },
            tags={MCP_SERVER_VERSION_TAG: MCP_SERVER_VERSION},
        )

    def test_create_queue_override_with_fifo_and_custom_attributes(self):
        """Test create_queue_override function with FIFO queue and custom attributes."""
        # Mock FastMCP
        mock_mcp = MagicMock()

        # Capture the decorated function
        decorated_func = None

        def capture_func(func):
            nonlocal decorated_func
            decorated_func = func
            return func

        mock_mcp.tool.return_value = capture_func

        # Mock SQS client
        mock_sqs_client = MagicMock()
        mock_sqs_client.create_queue.return_value = {
            'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue.fifo'
        }
        mock_sqs_client_getter = MagicMock(return_value=mock_sqs_client)

        # Call the function
        create_queue_override(mock_mcp, mock_sqs_client_getter, '')

        # Test with FIFO queue and custom attributes
        mock_sqs_client.create_queue.reset_mock()
        assert decorated_func is not None, 'decorated_func should not be None'
        result = decorated_func(
            queue_name='test-queue.fifo',
            attributes={'ContentBasedDeduplication': 'true', 'VisibilityTimeout': '60'},
            tags={'Project': 'TestProject'},
            region='us-east-1',
        )

        # Verify FIFO attributes were added while preserving custom attributes
        mock_sqs_client.create_queue.assert_called_with(
            QueueName='test-queue.fifo',
            Attributes={
                'ContentBasedDeduplication': 'true',
                'VisibilityTimeout': '60',
                'FifoQueue': 'true',
                'DeduplicationScope': 'messageGroup',
                'FifoThroughputLimit': 'perMessageGroupId',
            },
            tags={'Project': 'TestProject', MCP_SERVER_VERSION_TAG: MCP_SERVER_VERSION},
        )

        # Verify result
        assert result == {
            'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue.fifo'
        }

    def test_is_mutative_action_allowed_exception(self):
        """Test is_mutative_action_allowed function with exception."""
        # Mock FastMCP
        mock_mcp = MagicMock()

        # Mock SQS client that raises exception
        mock_sqs_client = MagicMock()
        mock_sqs_client.list_queue_tags.side_effect = Exception('Test exception')

        # Test with exception
        result, message = is_mutative_action_allowed(
            mock_mcp,
            mock_sqs_client,
            {'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'},
        )
        assert result is False
        assert message == 'Test exception'
