"""Tests for the amazon-sns-sqs-mcp-server."""

from awslabs.amazon_sns_sqs_mcp_server.server import main, mcp
from awslabs.amazon_sns_sqs_mcp_server.sns import (
    create_topic_override,
)
from awslabs.amazon_sns_sqs_mcp_server.sns import (
    is_mutative_action_allowed as sns_is_mutative_action_allowed,
)
from awslabs.amazon_sns_sqs_mcp_server.sqs import (
    create_queue_override,
)
from awslabs.amazon_sns_sqs_mcp_server.sqs import (
    is_mutative_action_allowed as sqs_is_mutative_action_allowed,
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
            'Tags': [{'Key': 'mcp_server_version', 'Value': '1.0.0'}]
        }

        # Test with valid TopicArn
        result, _ = sns_is_mutative_action_allowed(
            mock_mcp,
            mock_sns_client,
            {'TopicArn': 'arn:aws:sns:us-east-1:123456789012:test-topic'},
        )
        assert result is True

        # Test with missing TopicArn
        result, message = sns_is_mutative_action_allowed(mock_mcp, mock_sns_client, {})
        assert result is False
        assert message == 'TopicArn is not passed to the tool'

        # Test with untagged resource
        mock_sns_client.list_tags_for_resource.return_value = {'Tags': []}
        result, message = sns_is_mutative_action_allowed(
            mock_mcp,
            mock_sns_client,
            {'TopicArn': 'arn:aws:sns:us-east-1:123456789012:test-topic'},
        )
        assert result is False
        assert message == 'mutating a resource without the mcp_server_version tag is not allowed'


class TestServerModule:
    """Test server module."""

    def test_mcp_initialization(self):
        """Test that the MCP server is initialized correctly."""
        assert mcp.name == 'awslabs.amazon-sns-sqs-mcp-server'

        # Check if instructions contains the expected strings
        instructions = mcp.instructions if mcp.instructions else ''
        assert 'Manage Amazon SNS topics' in instructions
        assert 'Amazon SQS queues' in instructions

        assert 'pydantic' in mcp.dependencies
        assert 'boto3' in mcp.dependencies

    @patch('boto3.Session')
    @patch('awslabs.amazon_sns_sqs_mcp_server.server.mcp')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_without_sse(self, mock_parse_args, mock_mcp, mock_session):
        """Test main function without SSE."""
        # Setup mock
        mock_args = MagicMock()
        mock_args.sse = False
        mock_parse_args.return_value = mock_args

        # Mock boto3 session to prevent credential lookup
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        # Call main
        main()

        # Assert run was called without transport
        mock_mcp.run.assert_called_once_with()

    @patch('boto3.Session')
    @patch('awslabs.amazon_sns_sqs_mcp_server.server.mcp')
    @patch('awslabs.amazon_sns_sqs_mcp_server.server.register_sns_tools')
    @patch('awslabs.amazon_sns_sqs_mcp_server.server.register_sqs_tools')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_with_allow_resource_creation(
        self, mock_parse_args, mock_register_sqs, mock_register_sns, mock_mcp, mock_session
    ):
        """Test main function with --allow-resource-creation flag."""
        # Setup mock with allow_resource_creation=True
        mock_args = MagicMock()
        mock_args.sse = False
        mock_args.allow_resource_creation = True
        mock_args.port = 8888
        mock_parse_args.return_value = mock_args

        # Mock boto3 session to prevent credential lookup
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        # Call main
        main()

        # Assert register_sns_tools and register_sqs_tools were called with disallow_resource_creation=False
        mock_register_sns.assert_called_once_with(mock_mcp, False)
        mock_register_sqs.assert_called_once_with(mock_mcp, False)

    @patch('boto3.Session')
    @patch('awslabs.amazon_sns_sqs_mcp_server.server.mcp')
    @patch('awslabs.amazon_sns_sqs_mcp_server.server.register_sns_tools')
    @patch('awslabs.amazon_sns_sqs_mcp_server.server.register_sqs_tools')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_without_allow_resource_creation(
        self, mock_parse_args, mock_register_sqs, mock_register_sns, mock_mcp, mock_session
    ):
        """Test main function without --allow-resource-creation flag."""
        # Setup mock with allow_resource_creation=False
        mock_args = MagicMock()
        mock_args.sse = False
        mock_args.allow_resource_creation = False
        mock_args.port = 8888
        mock_parse_args.return_value = mock_args

        # Mock boto3 session to prevent credential lookup
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        # Call main
        main()

        # Assert register_sns_tools and register_sqs_tools were called with disallow_resource_creation=True
        mock_register_sns.assert_called_once_with(mock_mcp, True)
        mock_register_sqs.assert_called_once_with(mock_mcp, True)


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
        mock_sqs_client.list_queue_tags.return_value = {'Tags': {'mcp_server_version': '1.0.0'}}

        # Test with valid QueueUrl
        result, _ = sqs_is_mutative_action_allowed(
            mock_mcp,
            mock_sqs_client,
            {'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'},
        )
        assert result is True

        # Test with missing QueueUrl
        result, message = sqs_is_mutative_action_allowed(mock_mcp, mock_sqs_client, {})
        assert result is False
        assert message == 'QueueUrl is not passed to the tool'

        # Test with untagged resource
        mock_sqs_client.list_queue_tags.return_value = {'Tags': {}}
        result, message = sqs_is_mutative_action_allowed(
            mock_mcp,
            mock_sqs_client,
            {'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'},
        )
        assert result is False
        assert message == 'mutating a resource without the mcp_server_version tag is not allowed'
