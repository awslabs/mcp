"""Tests for the amazon-sns-sqs-mcp-server."""
import pytest
import argparse
import sys
from unittest.mock import MagicMock, patch
from awslabs.amazon_sns_sqs_mcp_server.sns import (
    create_topic_override,
    is_mutative_action_allowed as sns_is_mutative_action_allowed,
)
from awslabs.amazon_sns_sqs_mcp_server.sqs import (
    create_queue_override,
    is_mutative_action_allowed as sqs_is_mutative_action_allowed,
)
from awslabs.amazon_sns_sqs_mcp_server.server import main, mcp


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
        create_topic_override(mock_mcp, mock_sns_client_getter, "")
        
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
            mock_mcp, mock_sns_client, {'TopicArn': 'arn:aws:sns:us-east-1:123456789012:test-topic'}
        )
        assert result is True
        
        # Test with missing TopicArn
        result, message = sns_is_mutative_action_allowed(
            mock_mcp, mock_sns_client, {}
        )
        assert result is False
        assert message == 'TopicArn is not passed to the tool'
        
        # Test with untagged resource
        mock_sns_client.list_tags_for_resource.return_value = {'Tags': []}
        result, message = sns_is_mutative_action_allowed(
            mock_mcp, mock_sns_client, {'TopicArn': 'arn:aws:sns:us-east-1:123456789012:test-topic'}
        )
        assert result is False
        assert message == 'mutating a resource without the mcp_server_version tag is not allowed'


class TestServerModule:
    """Test server module."""

    def test_mcp_initialization(self):
        """Test that the MCP server is initialized correctly."""
        assert mcp.name == 'awslabs.amazon-sns-sqs-mcp-server'
        assert "Manage Amazon SNS topics" in mcp.instructions
        assert "Amazon SQS queues" in mcp.instructions
        assert 'pydantic' in mcp.dependencies
        assert 'boto3' in mcp.dependencies

    @patch('awslabs.amazon_sns_sqs_mcp_server.server.mcp')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_without_sse(self, mock_parse_args, mock_mcp):
        """Test main function without SSE."""
        # Setup mock
        mock_args = MagicMock()
        mock_args.sse = False
        mock_parse_args.return_value = mock_args
        
        # Call main
        main()
        
        # Assert run was called without transport
        mock_mcp.run.assert_called_once_with()
        
    @patch('awslabs.amazon_sns_sqs_mcp_server.server.mcp')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_with_sse(self, mock_parse_args, mock_mcp):
        """Test main function with SSE."""
        # Setup mock
        mock_args = MagicMock()
        mock_args.sse = True
        mock_args.port = 9999
        mock_parse_args.return_value = mock_args
        
        # Call main
        main()
        
        # Assert port was set and run was called with transport=sse
        assert mock_mcp.settings.port == 9999
        mock_mcp.run.assert_called_once_with(transport='sse')


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
        create_queue_override(mock_mcp, mock_sqs_client_getter, "")
        
        # Assert tool was registered
        assert mock_mcp.tool.called
    
    def test_allow_mutative_action_only_on_tagged_sqs_resource(self):
        """Test allow_mutative_action_only_on_tagged_sqs_resource function."""
        # Mock FastMCP
        mock_mcp = MagicMock()
        
        # Mock SQS client with tagged resource
        mock_sqs_client = MagicMock()
        mock_sqs_client.list_queue_tags.return_value = {
            'Tags': {'mcp_server_version': '1.0.0'}
        }
        
        # Test with valid QueueUrl
        result, _ = sqs_is_mutative_action_allowed(
            mock_mcp, mock_sqs_client, {'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'}
        )
        assert result is True
        
        # Test with missing QueueUrl
        result, message = sqs_is_mutative_action_allowed(
            mock_mcp, mock_sqs_client, {}
        )
        assert result is False
        assert message == 'QueueUrl is not passed to the tool'
        
        # Test with untagged resource
        mock_sqs_client.list_queue_tags.return_value = {'Tags': {}}
        result, message = sqs_is_mutative_action_allowed(
            mock_mcp, mock_sqs_client, {'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'}
        )
        assert result is False
        assert message == 'mutating a resource without the mcp_server_version tag is not allowed'
