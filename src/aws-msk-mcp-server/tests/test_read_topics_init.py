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

"""Tests for the read_topics __init__ module tool wrappers."""

from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp import FastMCP


class TestReadTopicsInit:
    """Tests for read_topics module registration and tool wrappers."""

    @patch('awslabs.aws_msk_mcp_server.tools.read_topics.list_topics')
    @patch('boto3.client')
    def test_list_topics_tool_with_all_params(self, mock_boto_client, mock_list_topics):
        """Test list_topics tool wrapper with all optional parameters."""
        # Arrange
        from awslabs.aws_msk_mcp_server.tools.read_topics import register_module

        mcp = FastMCP('test')
        register_module(mcp)
        
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_list_topics.return_value = {'topics': []}

        # Get the registered tool
        tool_func = None
        for tool in mcp._tools.values():
            if tool.name == 'list_topics':
                tool_func = tool.fn
                break

        # Act
        tool_func(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
            topic_name_filter='test',
            max_results=10,
            next_token='token',
        )

        # Assert
        mock_list_topics.assert_called_once()
        call_kwargs = mock_list_topics.call_args[1]
        assert 'topic_name_filter' in call_kwargs
        assert 'max_results' in call_kwargs
        assert 'next_token' in call_kwargs

    @patch('awslabs.aws_msk_mcp_server.tools.read_topics.describe_topic_partitions')
    @patch('boto3.client')
    def test_describe_topic_partitions_tool_with_params(
        self, mock_boto_client, mock_describe_partitions
    ):
        """Test describe_topic_partitions tool wrapper with optional parameters."""
        # Arrange
        from awslabs.aws_msk_mcp_server.tools.read_topics import register_module

        mcp = FastMCP('test')
        register_module(mcp)
        
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_describe_partitions.return_value = {'Partitions': []}

        # Get the registered tool
        tool_func = None
        for tool in mcp._tools.values():
            if tool.name == 'describe_topic_partitions':
                tool_func = tool.fn
                break

        # Act
        tool_func(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
            topic_name='test-topic',
            max_results=10,
            next_token='token',
        )

        # Assert
        mock_describe_partitions.assert_called_once()
        call_kwargs = mock_describe_partitions.call_args[1]
        assert 'max_results' in call_kwargs
        assert 'next_token' in call_kwargs