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

from awslabs.cdk_mcp_server.data.lambda_powertools_loader import (
    get_lambda_powertools_section,
    get_topic_map,
)
from unittest.mock import mock_open, patch


def test_get_topic_map():
    """Test getting the topic map."""
    topic_map = get_topic_map()

    # Check that all expected topics are present
    assert 'index' in topic_map
    assert 'logging' in topic_map
    assert 'tracing' in topic_map
    assert 'metrics' in topic_map
    assert 'cdk' in topic_map
    assert 'dependencies' in topic_map
    assert 'insights' in topic_map
    assert 'bedrock' in topic_map

    # Check that descriptions are present
    assert topic_map['index'] == 'Overview and table of contents'
    assert topic_map['logging'] == 'Structured logging implementation'
    assert topic_map['tracing'] == 'Tracing implementation'
    assert topic_map['metrics'] == 'Metrics implementation'
    assert topic_map['cdk'] == 'CDK integration patterns'
    assert topic_map['dependencies'] == 'Dependencies management'
    assert topic_map['insights'] == 'Lambda Insights integration'
    assert topic_map['bedrock'] == 'Bedrock Agent integration'


@patch('os.path.dirname')
@patch('os.path.join')
@patch('builtins.open', new_callable=mock_open, read_data='Test content')
def test_get_lambda_powertools_section_success(mock_file, mock_join, mock_dirname):
    """Test getting a Lambda Powertools section successfully."""
    # Mock the directory path
    mock_dirname.return_value = '/mock/path'

    # Test with specific topic
    mock_join.return_value = '/mock/path/static/lambda_powertools/logging.md'
    content = get_lambda_powertools_section('logging')
    assert content == 'Test content'
    mock_file.assert_called_with(
        '/mock/path/static/lambda_powertools/logging.md', 'r', encoding='utf-8'
    )

    # Test with empty topic (should default to index)
    mock_join.return_value = '/mock/path/static/lambda_powertools/index.md'
    content = get_lambda_powertools_section('')
    assert content == 'Test content'
    mock_file.assert_called_with(
        '/mock/path/static/lambda_powertools/index.md', 'r', encoding='utf-8'
    )

    # Test with 'index' topic
    mock_join.return_value = '/mock/path/static/lambda_powertools/index.md'
    content = get_lambda_powertools_section('index')
    assert content == 'Test content'
    mock_file.assert_called_with(
        '/mock/path/static/lambda_powertools/index.md', 'r', encoding='utf-8'
    )


@patch('os.path.dirname')
@patch('os.path.join')
@patch('builtins.open')
def test_get_lambda_powertools_section_file_not_found(mock_file, mock_join, mock_dirname):
    """Test getting a Lambda Powertools section when file is not found."""
    # Mock the directory path
    mock_dirname.return_value = '/mock/path'
    mock_join.return_value = '/mock/path/static/lambda_powertools/logging.md'

    # Mock file not found error
    mock_file.side_effect = FileNotFoundError()

    # Test with specific topic
    content = get_lambda_powertools_section('logging')
    assert 'Error: File for topic' in content
    assert 'not found' in content
    assert '/mock/path/static/lambda_powertools/logging.md' in content


def test_get_lambda_powertools_section_invalid_topic():
    """Test getting a Lambda Powertools section with invalid topic."""
    # Test with invalid topic
    content = get_lambda_powertools_section('invalid_topic')
    assert "Topic 'invalid_topic' not found" in content
    assert 'Available topics:' in content

    # Verify that all valid topics are listed in the error message
    topic_map = get_topic_map()
    for topic in topic_map:
        if topic != 'index':  # index is not shown in the list
            assert topic in content
            assert topic_map[topic] in content
