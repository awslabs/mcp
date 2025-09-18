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

import os
import pytest
from awslabs.aws_api_mcp_server.core.common.command_metadata import CommandMetadata
from awslabs.aws_api_mcp_server.core.common.config import WORKING_DIRECTORY
from awslabs.aws_api_mcp_server.core.common.file_operations import (
    extract_file_paths_from_parameters,
    is_binary_output_operation,
    is_s3_download_operation,
)
from awslabs.aws_api_mcp_server.core.parser.parser import parse
from unittest.mock import patch


def test_binary_output_operations_detection():
    """Test detection of operations that produce binary output."""
    # S3 get-object should be detected
    metadata = CommandMetadata('s3api', 's3api', 'get-object')
    assert is_binary_output_operation(metadata)

    # Lambda invoke should be detected
    metadata = CommandMetadata('lambda', 'lambda', 'invoke')
    assert is_binary_output_operation(metadata)

    # Regular operations should not be detected
    metadata = CommandMetadata('ec2', 'ec2', 'describe-instances')
    assert not is_binary_output_operation(metadata)


def test_s3_download_operations_detection():
    """Test detection of S3 download operations."""
    # S3 cp should be detected
    metadata = CommandMetadata('s3', 's3', 'cp')
    assert is_s3_download_operation(metadata)

    # S3 sync should be detected
    metadata = CommandMetadata('s3', 's3', 'sync')
    assert is_s3_download_operation(metadata)

    # S3API operations should not be detected as S3 downloads
    metadata = CommandMetadata('s3api', 's3api', 'get-object')
    assert not is_s3_download_operation(metadata)


def test_file_path_extraction_s3_operations():
    """Test file path extraction for S3 operations."""
    metadata = CommandMetadata('s3', 's3', 'cp')

    # S3 download to local file
    parameters = {'--paths': ['s3://bucket/key', '/tmp/localfile.txt']}
    file_paths = extract_file_paths_from_parameters(metadata, parameters)
    assert '/tmp/localfile.txt' in file_paths
    assert 's3://bucket/key' not in file_paths  # Remote path should be excluded

    # Local upload to S3
    parameters = {'--paths': ['/tmp/localfile.txt', 's3://bucket/key']}
    file_paths = extract_file_paths_from_parameters(metadata, parameters)
    assert '/tmp/localfile.txt' in file_paths


def test_file_path_extraction_binary_operations():
    """Test file path extraction for binary output operations."""
    metadata = CommandMetadata('lambda', 'lambda', 'invoke')

    # Lambda invoke with output file
    parameters = {'--function-name': 'my-function', 'outfile': 'response.json'}
    file_paths = extract_file_paths_from_parameters(metadata, parameters)
    assert 'response.json' in file_paths
    assert 'my-function' not in file_paths  # Function name should be excluded


def test_comprehensive_validation_blocks_unsafe_paths():
    """Test that comprehensive validation blocks unsafe file paths."""
    # Test S3 download to unsafe location
    with pytest.raises(ValueError) as exc_info:
        parse('aws s3 cp s3://bucket/key /tmp/unsafe.txt')

    assert 'is outside the allowed working directory' in str(exc_info.value)

    # Test Lambda invoke to unsafe location
    with pytest.raises(ValueError) as exc_info:
        parse('aws lambda invoke --function-name test /home/user/unsafe.json')

    assert 'is outside the allowed working directory' in str(exc_info.value)


def test_comprehensive_validation_allows_safe_paths():
    """Test that comprehensive validation allows safe file paths."""
    safe_file = os.path.join(WORKING_DIRECTORY, 'safe.txt')

    # Test S3 download to safe location
    result = parse(f'aws s3 cp s3://bucket/key {safe_file}')
    assert result is not None

    # Test Lambda invoke to safe location
    safe_json = os.path.join(WORKING_DIRECTORY, 'response.json')
    result = parse(f'aws lambda invoke --function-name test {safe_json}')
    assert result is not None


@patch(
    'awslabs.aws_api_mcp_server.core.common.file_system_controls.ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS',
    True,
)
def test_unrestricted_access_bypass():
    """Test that unrestricted access allows any file path."""
    # Should work with unrestricted access enabled
    result = parse('aws s3 cp s3://bucket/key /tmp/anywhere.txt')
    assert result is not None
