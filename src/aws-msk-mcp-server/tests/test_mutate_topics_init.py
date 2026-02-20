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

"""Tests for the mutate_topics __init__ module tool wrappers."""

from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp import FastMCP


class TestMutateTopicsInit:
    """Tests for mutate_topics module registration and tool wrappers."""

    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.create_topic')
    @patch('boto3.client')
    def test_create_topic_tool_with_configs(self, mock_boto_client, mock_create_topic):
        """Test create_topic tool wrapper with configs parameter."""
        # Arrange
        from awslabs.aws_msk_mcp_server.tools.mutate_topics import register_module

        mcp = FastMCP('test')
        register_module(mcp)
        
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_create_topic.return_value = {'TopicArn': 'arn:test', 'Status': 'CREATING'}

        # Get the registered tool
        tool_func = None
        for tool in mcp._tools.values():
            if tool.name == 'create_topic':
                tool_func = tool.fn
                break

        # Act
        tool_func(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
            topic_name='test-topic',
            partition_count=3,
            replication_factor=2,
            configs='eyJjbGVhbnVwLnBvbGljeSI6ICJjb21wYWN0In0=',
        )

        # Assert
        mock_create_topic.assert_called_once()
        # Verify configs was passed
        assert mock_create_topic.call_args[0][5] == 'eyJjbGVhbnVwLnBvbGljeSI6ICJjb21wYWN0In0='

    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.create_topic')
    @patch('boto3.client')
    def test_create_topic_tool_without_configs(self, mock_boto_client, mock_create_topic):
        """Test create_topic tool wrapper without configs parameter."""
        # Arrange
        from awslabs.aws_msk_mcp_server.tools.mutate_topics import register_module

        mcp = FastMCP('test')
        register_module(mcp)
        
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_create_topic.return_value = {'TopicArn': 'arn:test', 'Status': 'CREATING'}

        # Get the registered tool
        tool_func = None
        for tool in mcp._tools.values():
            if tool.name == 'create_topic':
                tool_func = tool.fn
                break

        # Act
        tool_func(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
            topic_name='test-topic',
            partition_count=3,
            replication_factor=2,
            configs=None,
        )

        # Assert
        mock_create_topic.assert_called_once()
        # Verify only 5 positional args (no configs)
        assert len(mock_create_topic.call_args[0]) == 5

    @patch('awslabs.aws_msk_mcp_server.tools.mutate_topics.update_topic')
    @patch('boto3.client')
    def test_update_topic_tool_with_both_params(self, mock_boto_client, mock_update_topic):
        """Test update_topic tool wrapper with both optional parameters."""
        # Arrange
        from awslabs.aws_msk_mcp_server.tools.mutate_topics import register_module

        mcp = FastMCP('test')
        register_module(mcp)
        
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_update_topic.return_value = {'TopicArn': 'arn:test', 'Status': 'UPDATING'}

        # Get the registered tool
        tool_func = None
        for tool in mcp._tools.values():
            if tool.name == 'update_topic':
                tool_func = tool.fn
                break

        # Act
        tool_func(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
            topic_name='test-topic',
            configs='eyJjbGVhbnVwLnBvbGljeSI6ICJjb21wYWN0In0=',
            partition_count=10,
        )

        # Assert
        mock_update_topic.assert_called_once()
        call_kwargs = mock_update_topic.call_args[1]
        assert 'configs' in call_kwargs
        assert 'partition_count' in call_kwargs