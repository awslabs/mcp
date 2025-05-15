"""Tests for the SNS module of amazon-sns-sqs-mcp-server."""

from awslabs.amazon_sns_sqs_mcp_server.common import MCP_SERVER_VERSION_TAG
from awslabs.amazon_sns_sqs_mcp_server.consts import MCP_SERVER_VERSION
from awslabs.amazon_sns_sqs_mcp_server.sns import (
    create_topic_override,
    is_mutative_action_allowed,
    is_unsubscribe_allowed,
    register_sns_tools,
)
from unittest.mock import MagicMock, patch


class TestSNSTools:
    """Test SNS tools."""

    def test_create_topic_override(self):
        """Test create_topic_override function."""
        # Mock FastMCP
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda x: x)

        # Mock SNS client getter
        mock_sns_client = MagicMock()
        mock_sns_client_getter = MagicMock(return_value=mock_sns_client)

        # Call the function
        create_topic_override(mock_mcp, mock_sns_client_getter, '')

        # Assert tool was registered
        assert mock_mcp.tool.called

    def test_allow_mutative_action_only_on_tagged_sns_resource(self):
        """Test allow_mutative_action_only_on_tagged_sns_resource function."""
        # Mock FastMCP
        mock_mcp = MagicMock()

        # Mock SNS client with tagged resource
        mock_sns_client = MagicMock()
        mock_sns_client.list_tags_for_resource.return_value = {
            'Tags': [{'Key': MCP_SERVER_VERSION_TAG, 'Value': '1.0.0'}]
        }

        # Test with valid TopicArn
        result, _ = is_mutative_action_allowed(
            mock_mcp,
            mock_sns_client,
            {'TopicArn': 'arn:aws:sns:us-east-1:123456789012:test-topic'},
        )
        assert result is True

        # Test with missing TopicArn
        result, message = is_mutative_action_allowed(mock_mcp, mock_sns_client, {})
        assert result is False
        assert message == 'TopicArn is not passed to the tool'

        # Test with untagged resource
        mock_sns_client.list_tags_for_resource.return_value = {'Tags': []}
        result, message = is_mutative_action_allowed(
            mock_mcp,
            mock_sns_client,
            {'TopicArn': 'arn:aws:sns:us-east-1:123456789012:test-topic'},
        )
        assert result is False
        assert message == 'mutating a resource without the mcp_server_version tag is not allowed'

    def test_create_topic_override_implementation(self):
        """Test create_topic_override function implementation."""
        # Mock FastMCP
        mock_mcp = MagicMock()

        # Capture the decorated function
        decorated_func = None

        def capture_func(func):
            nonlocal decorated_func
            decorated_func = func
            return func

        mock_mcp.tool.return_value = capture_func

        # Mock SNS client
        mock_sns_client = MagicMock()
        mock_sns_client.create_topic.return_value = {'TopicArn': 'test-topic-arn'}
        mock_sns_client_getter = MagicMock(return_value=mock_sns_client)

        # Call the function
        create_topic_override(mock_mcp, mock_sns_client_getter, '')

        # Verify the decorated function was captured
        assert decorated_func is not None

        # Test with standard topic
        result = decorated_func(
            name='test-topic',
            attributes={'DisplayName': 'Test Topic'},
            tags=[{'Key': 'Environment', 'Value': 'Test'}],
            region='us-west-2',
        )

        # Verify client was created with correct region
        mock_sns_client_getter.assert_called_with('us-west-2')

        # Verify create_topic was called with correct parameters
        mock_sns_client.create_topic.assert_called_with(
            Name='test-topic',
            Attributes={'DisplayName': 'Test Topic'},
            Tags=[
                {'Key': 'Environment', 'Value': 'Test'},
                {'Key': MCP_SERVER_VERSION_TAG, 'Value': MCP_SERVER_VERSION},
            ],
        )

        # Verify result
        assert result == {'TopicArn': 'test-topic-arn'}

        # Test with FIFO topic
        mock_sns_client.create_topic.reset_mock()
        result = decorated_func(name='test-topic.fifo', attributes={}, tags=[], region='us-east-1')

        # Verify FIFO attributes were added
        mock_sns_client.create_topic.assert_called_with(
            Name='test-topic.fifo',
            Attributes={'FifoTopic': 'true', 'FifoThroughputScope': 'MessageGroup'},
            Tags=[{'Key': MCP_SERVER_VERSION_TAG, 'Value': MCP_SERVER_VERSION}],
        )

    def test_is_mutative_action_allowed_exception(self):
        """Test is_mutative_action_allowed function with exception."""
        # Mock FastMCP
        mock_mcp = MagicMock()

        # Mock SNS client that raises exception
        mock_sns_client = MagicMock()
        mock_sns_client.list_tags_for_resource.side_effect = Exception('Test exception')

        # Test with exception
        result, message = is_mutative_action_allowed(
            mock_mcp,
            mock_sns_client,
            {'TopicArn': 'arn:aws:sns:us-east-1:123456789012:test-topic'},
        )
        assert result is False
        assert message == 'Test exception'

    def test_is_unsubscribe_allowed_exception(self):
        """Test is_unsubscribe_allowed function with exception."""
        # Mock FastMCP
        mock_mcp = MagicMock()

        # Mock SNS client that raises exception
        mock_sns_client = MagicMock()
        mock_sns_client.get_subscription_attributes.side_effect = Exception('Test exception')

        # Test with exception
        result, message = is_unsubscribe_allowed(
            mock_mcp,
            mock_sns_client,
            {'SubscriptionArn': 'arn:aws:sns:us-east-1:123456789012:test-topic:subscription-id'},
        )
        assert result is False
        assert message == 'Test exception'

    @patch('boto3.client')
    @patch('awslabs.amazon_sns_sqs_mcp_server.sns.AWSToolGenerator')
    def test_register_sns_tools(self, mock_aws_tool_generator, mock_boto3_client):
        """Test register_sns_tools function."""
        # Mock FastMCP
        mock_mcp = MagicMock()

        # Create a mock tool generator instance
        mock_generator_instance = MagicMock()
        mock_aws_tool_generator.return_value = mock_generator_instance

        # Call the function
        register_sns_tools(mock_mcp)

        # Verify AWSToolGenerator was instantiated
        mock_aws_tool_generator.assert_called_once()

        # Verify parameters safely without assuming position
        args, kwargs = mock_aws_tool_generator.call_args
        assert 'mcp' in kwargs or len(args) >= 3, 'MCP not passed to AWSToolGenerator'

        # Verify that generate() was called on the instance
        mock_generator_instance.generate.assert_called_once()

    @patch('boto3.client')
    @patch('awslabs.amazon_sns_sqs_mcp_server.sns.AWSToolGenerator')
    def test_register_sns_tools_with_disallow_resource_creation(
        self, mock_aws_tool_generator, mock_boto3_client
    ):
        """Test register_sns_tools function with disallow_resource_creation=True."""
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
        register_sns_tools(mock_mcp, disallow_resource_creation=True)

        # Verify that create_topic is set to be ignored in the tool_configuration
        assert 'create_topic' in tool_config_capture
        assert tool_config_capture['create_topic'] == {'ignore': True}

    def test_validator_with_different_operations(self):
        """Test validator with different SNS operations."""
        # Mock FastMCP
        mock_mcp = MagicMock()

        # Mock SNS client with tagged resource
        mock_sns_client = MagicMock()
        mock_sns_client.list_tags_for_resource.return_value = {
            'Tags': [{'Key': MCP_SERVER_VERSION_TAG, 'Value': '1.0.0'}]
        }

        # Test with confirm_subscription (uses TopicArn)
        result, _ = is_mutative_action_allowed(
            mock_mcp,
            mock_sns_client,
            {'TopicArn': 'arn:aws:sns:us-east-1:123456789012:test-topic', 'Token': 'abc123'},
        )
        assert result is True

        # Test with publish (uses TopicArn)
        result, _ = is_mutative_action_allowed(
            mock_mcp,
            mock_sns_client,
            {
                'TopicArn': 'arn:aws:sns:us-east-1:123456789012:test-topic',
                'Message': 'Hello world',
            },
        )
        assert result is True

        # Test with publish_batch (uses TopicArn)
        result, _ = is_mutative_action_allowed(
            mock_mcp,
            mock_sns_client,
            {
                'TopicArn': 'arn:aws:sns:us-east-1:123456789012:test-topic',
                'PublishBatchRequestEntries': [],
            },
        )
        assert result is True

    def test_unsubscribe_validator(self):
        """Test the unsubscribe validator."""
        # Mock FastMCP
        mock_mcp = MagicMock()

        # Mock SNS client
        mock_sns_client = MagicMock()

        # Mock get_subscription_attributes response
        mock_sns_client.get_subscription_attributes.return_value = {
            'Attributes': {'TopicArn': 'arn:aws:sns:us-east-1:123456789012:test-topic'}
        }

        # Mock list_tags_for_resource response for a tagged topic
        mock_sns_client.list_tags_for_resource.return_value = {
            'Tags': [{'Key': MCP_SERVER_VERSION_TAG, 'Value': '1.0.0'}]
        }

        # Test with valid SubscriptionArn
        result, _ = is_unsubscribe_allowed(
            mock_mcp,
            mock_sns_client,
            {'SubscriptionArn': 'arn:aws:sns:us-east-1:123456789012:test-topic:subscription-id'},
        )
        assert result is True

        # Test with missing SubscriptionArn
        result, message = is_unsubscribe_allowed(mock_mcp, mock_sns_client, {})
        assert result is False
        assert message == 'SubscriptionArn is not passed to the tool'

        # Test with missing TopicArn in subscription attributes
        mock_sns_client.get_subscription_attributes.return_value = {'Attributes': {}}
        result, message = is_unsubscribe_allowed(
            mock_mcp,
            mock_sns_client,
            {'SubscriptionArn': 'arn:aws:sns:us-east-1:123456789012:test-topic:subscription-id'},
        )
        assert result is False
        assert message == 'TopicArn is not passed to the tool'

        # Test with untagged topic
        mock_sns_client.get_subscription_attributes.return_value = {
            'Attributes': {'TopicArn': 'arn:aws:sns:us-east-1:123456789012:test-topic'}
        }
        mock_sns_client.list_tags_for_resource.return_value = {'Tags': []}
        result, message = is_unsubscribe_allowed(
            mock_mcp,
            mock_sns_client,
            {'SubscriptionArn': 'arn:aws:sns:us-east-1:123456789012:test-topic:subscription-id'},
        )
        assert result is False
        assert message == 'mutating a resource without the mcp_server_version tag is not allowed'
