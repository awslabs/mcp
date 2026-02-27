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

"""Tests for the mutate_topics/__init__.py module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.mutate_topics import register_module
from mcp.server.fastmcp import FastMCP
from typing import cast
from unittest.mock import MagicMock, patch


class TestMutateTopicsInit:
    """Tests for the mutate_topics/__init__.py module."""

    def test_register_module(self):
        """Test the register_module function registers all tools."""
        # Arrange
        mock_mcp = MagicMock(spec=FastMCP)

        # Act
        register_module(mock_mcp)

        # Assert
        assert mock_mcp.tool.call_count == 3
        tool_names = [call[1]['name'] for call in mock_mcp.tool.call_args_list]
        assert 'create_topic' in tool_names
        assert 'update_topic' in tool_names
        assert 'delete_topic' in tool_names

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.check_mcp_generated_tag')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.create_topic')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.Config')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.__version__', '1.0.0')
    def test_create_topic_tool_with_configs(
        self, mock_config, mock_create_topic, mock_check_tag, mock_boto3_client
    ):
        """Test the create_topic tool wrapper with configs parameter."""
        # Arrange
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        register_module(cast(FastMCP, MockMCP()))

        create_topic_tool = decorated_functions['create_topic']
        assert create_topic_tool is not None

        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client

        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance

        mock_check_tag.return_value = True

        expected_response = {'TopicArn': 'arn:test', 'Status': 'CREATING'}
        mock_create_topic.return_value = expected_response

        # Act
        result = create_topic_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
            topic_name='new-topic',
            partition_count=3,
            replication_factor=2,
            configs='eyJjbGVhbnVwLnBvbGljeSI6ICJjb21wYWN0In0=',
        )

        # Assert
        mock_config.assert_called_once_with(
            user_agent_extra='awslabs/mcp/aws-msk-mcp-server/1.0.0'
        )
        mock_boto3_client.assert_called_once_with(
            'kafka', region_name='us-east-1', config=mock_config_instance
        )
        mock_create_topic.assert_called_once_with(
            'arn:aws:kafka:us-east-1:123:cluster/test/abc',
            'new-topic',
            3,
            2,
            mock_kafka_client,
            'eyJjbGVhbnVwLnBvbGljeSI6ICJjb21wYWN0In0=',
        )
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.check_mcp_generated_tag')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.create_topic')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.Config')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.__version__', '1.0.0')
    def test_create_topic_tool_without_configs(
        self, mock_config, mock_create_topic, mock_check_tag, mock_boto3_client
    ):
        """Test the create_topic tool wrapper without configs parameter."""
        # Arrange
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        register_module(cast(FastMCP, MockMCP()))

        create_topic_tool = decorated_functions['create_topic']

        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client

        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance

        mock_check_tag.return_value = True

        expected_response = {'TopicArn': 'arn:test', 'Status': 'CREATING'}
        mock_create_topic.return_value = expected_response

        # Act
        result = create_topic_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
            topic_name='new-topic',
            partition_count=3,
            replication_factor=2,
            configs=None,
        )

        # Assert
        mock_create_topic.assert_called_once_with(
            'arn:aws:kafka:us-east-1:123:cluster/test/abc',
            'new-topic',
            3,
            2,
            mock_kafka_client,
        )
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.check_mcp_generated_tag')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.Config')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.__version__', '1.0.0')
    def test_create_topic_tool_tag_check_fails(
        self, mock_config, mock_check_tag, mock_boto3_client
    ):
        """Test the create_topic tool wrapper raises ValueError when tag check fails."""
        # Arrange
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        register_module(cast(FastMCP, MockMCP()))

        create_topic_tool = decorated_functions['create_topic']

        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client

        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance

        mock_check_tag.return_value = False

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            create_topic_tool(
                region='us-east-1',
                cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
                topic_name='new-topic',
                partition_count=3,
                replication_factor=2,
                configs=None,
            )

        assert "does not have the 'MCP Generated' tag" in str(excinfo.value)

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.check_mcp_generated_tag')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.update_topic')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.Config')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.__version__', '1.0.0')
    def test_update_topic_tool_with_both_params(
        self, mock_config, mock_update_topic, mock_check_tag, mock_boto3_client
    ):
        """Test the update_topic tool wrapper with both optional parameters."""
        # Arrange
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        register_module(cast(FastMCP, MockMCP()))

        update_topic_tool = decorated_functions['update_topic']
        assert update_topic_tool is not None

        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client

        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance

        mock_check_tag.return_value = True

        expected_response = {'TopicArn': 'arn:test', 'Status': 'UPDATING'}
        mock_update_topic.return_value = expected_response

        # Act
        result = update_topic_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
            topic_name='test-topic',
            configs='eyJjbGVhbnVwLnBvbGljeSI6ICJjb21wYWN0In0=',
            partition_count=10,
        )

        # Assert
        mock_config.assert_called_once_with(
            user_agent_extra='awslabs/mcp/aws-msk-mcp-server/1.0.0'
        )
        mock_boto3_client.assert_called_once_with(
            'kafka', region_name='us-east-1', config=mock_config_instance
        )
        mock_update_topic.assert_called_once_with(
            'arn:aws:kafka:us-east-1:123:cluster/test/abc',
            'test-topic',
            mock_kafka_client,
            configs='eyJjbGVhbnVwLnBvbGljeSI6ICJjb21wYWN0In0=',
            partition_count=10,
        )
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.check_mcp_generated_tag')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.update_topic')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.Config')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.__version__', '1.0.0')
    def test_update_topic_tool_without_optional_params(
        self, mock_config, mock_update_topic, mock_check_tag, mock_boto3_client
    ):
        """Test the update_topic tool wrapper without optional parameters."""
        # Arrange
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        register_module(cast(FastMCP, MockMCP()))

        update_topic_tool = decorated_functions['update_topic']

        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client

        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance

        mock_check_tag.return_value = True

        expected_response = {'TopicArn': 'arn:test', 'Status': 'UPDATING'}
        mock_update_topic.return_value = expected_response

        # Act
        result = update_topic_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
            topic_name='test-topic',
            configs=None,
            partition_count=None,
        )

        # Assert
        mock_update_topic.assert_called_once_with(
            'arn:aws:kafka:us-east-1:123:cluster/test/abc',
            'test-topic',
            mock_kafka_client,
        )
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.check_mcp_generated_tag')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.Config')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.__version__', '1.0.0')
    def test_update_topic_tool_tag_check_fails(
        self, mock_config, mock_check_tag, mock_boto3_client
    ):
        """Test the update_topic tool wrapper raises ValueError when tag check fails."""
        # Arrange
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        register_module(cast(FastMCP, MockMCP()))

        update_topic_tool = decorated_functions['update_topic']

        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client

        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance

        mock_check_tag.return_value = False

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            update_topic_tool(
                region='us-east-1',
                cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
                topic_name='test-topic',
                configs=None,
                partition_count=None,
            )

        assert "does not have the 'MCP Generated' tag" in str(excinfo.value)

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.check_mcp_generated_tag')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.delete_topic')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.Config')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.__version__', '1.0.0')
    def test_delete_topic_tool(
        self, mock_config, mock_delete_topic, mock_check_tag, mock_boto3_client
    ):
        """Test the delete_topic tool wrapper."""
        # Arrange
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        register_module(cast(FastMCP, MockMCP()))

        delete_topic_tool = decorated_functions['delete_topic']
        assert delete_topic_tool is not None

        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client

        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance

        mock_check_tag.return_value = True

        expected_response = {'TopicArn': 'arn:test', 'Status': 'DELETING'}
        mock_delete_topic.return_value = expected_response

        # Act
        result = delete_topic_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
            topic_name='test-topic',
            confirm_delete='DELETE',
        )

        # Assert
        mock_config.assert_called_once_with(
            user_agent_extra='awslabs/mcp/aws-msk-mcp-server/1.0.0'
        )
        mock_boto3_client.assert_called_once_with(
            'kafka', region_name='us-east-1', config=mock_config_instance
        )
        mock_delete_topic.assert_called_once_with(
            'arn:aws:kafka:us-east-1:123:cluster/test/abc',
            'test-topic',
            mock_kafka_client,
            'DELETE',
        )
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.check_mcp_generated_tag')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.Config')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.__version__', '1.0.0')
    def test_delete_topic_tool_tag_check_fails(
        self, mock_config, mock_check_tag, mock_boto3_client
    ):
        """Test the delete_topic tool wrapper raises ValueError when tag check fails."""
        # Arrange
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        register_module(cast(FastMCP, MockMCP()))

        delete_topic_tool = decorated_functions['delete_topic']

        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client

        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance

        mock_check_tag.return_value = False

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            delete_topic_tool(
                region='us-east-1',
                cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
                topic_name='test-topic',
                confirm_delete='DELETE',
            )

        assert "does not have the 'MCP Generated' tag" in str(excinfo.value)
