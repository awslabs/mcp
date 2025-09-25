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

from awslabs.aws_api_mcp_server.core.common.command_metadata import CommandMetadata
from awslabs.aws_api_mcp_server.core.common.file_operations import (
    _could_be_file_path,
    extract_file_paths_from_parameters,
)


def test_extract_file_paths_with_non_string_list_items():
    """Test file path extraction handles non-string items in lists."""
    metadata = CommandMetadata('s3', 's3', 'cp')

    # Test with --paths parameter containing non-string items
    parameters = {'--paths': ['/path/to/file', 123, None, '/another/path']}
    file_paths = extract_file_paths_from_parameters(metadata, parameters)

    # Only string items that are not remote paths should be included
    assert '/path/to/file' in file_paths
    assert '/another/path' in file_paths
    assert len([p for p in file_paths if isinstance(p, str)]) == len(file_paths)


def test_could_be_file_path_return_false():
    """Test _could_be_file_path returns False for values without path indicators."""
    # Test the final return False case (line 155)
    assert not _could_be_file_path('test')
    assert not _could_be_file_path('value')


def test_extract_file_paths_binary_operation_param_names():
    """Test binary operations check parameter names as potential file paths."""
    metadata = CommandMetadata('lambda', 'lambda', 'invoke')

    # Test case where parameter names could be file paths
    parameters = {'output.json': 'some-value', '--function-name': 'my-func'}
    file_paths = extract_file_paths_from_parameters(metadata, parameters)

    # Should include parameter name that looks like a file path
    assert 'output.json' in file_paths


def test_extract_file_paths_string_parameter_in_file_params():
    """Test parameter name in file_params with string value."""
    metadata = CommandMetadata('s3', 's3', 'cp')

    # --paths is in file_params for s3 cp, test with string value
    parameters = {'--paths': '/local/file.txt'}
    file_paths = extract_file_paths_from_parameters(metadata, parameters)

    assert '/local/file.txt' in file_paths


def test_extract_file_paths_list_parameter_in_file_params():
    """Test parameter name in file_params with list value."""
    metadata = CommandMetadata('s3', 's3', 'cp')

    # --paths is in file_params for s3 cp, test with list value
    parameters = {'--paths': ['/local/file1.txt', '/local/file2.txt']}
    file_paths = extract_file_paths_from_parameters(metadata, parameters)

    assert '/local/file1.txt' in file_paths
    assert '/local/file2.txt' in file_paths
