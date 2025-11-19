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
from awslabs.aws_api_mcp_server.core.common.config import WORKING_DIRECTORY, FileAccessMode
from awslabs.aws_api_mcp_server.core.common.errors import FilePathValidationError
from awslabs.aws_api_mcp_server.core.common.file_system_controls import (
    CUSTOM_FILE_PATH_ARGUMENTS,
    extract_file_paths_from_parameters,
    validate_file_path,
)
from awslabs.aws_api_mcp_server.core.parser.parser import ALLOWED_CUSTOM_OPERATIONS
from unittest.mock import patch


def test_safe_path_allowed():
    """Test that files within working directory are allowed."""
    safe_path = os.path.join(WORKING_DIRECTORY, 'safe_file.txt')
    result = validate_file_path(safe_path)
    assert result == safe_path


def test_unsafe_path_blocked():
    """Test that files outside working directory are blocked."""
    unsafe_path = '/tmp/unsafe_file.txt'
    with pytest.raises(FilePathValidationError):
        validate_file_path(unsafe_path)


@patch(
    'awslabs.aws_api_mcp_server.core.common.file_system_controls.FILE_ACCESS_MODE',
    FileAccessMode.UNRESTRICTED,
)
def test_unrestricted_access_allows_unsafe_path():
    """Test that FILE_ACCESS_MODE.UNRESTRICTED allows files outside working directory."""
    unsafe_path = '/tmp/unsafe_file.txt'
    result = validate_file_path(unsafe_path)
    assert result == unsafe_path


def test_all_custom_operations_have_file_path_arguments_entry():
    """Test that all custom commands must have explicitly listed file path arguments.

    This ensures that every custom operation in ALLOWED_CUSTOM_OPERATIONS has a corresponding
    entry in CUSTOM_FILE_PATH_ARGUMENTS, even if it's an empty list. This is important for
    maintaining awareness of which custom operations accept file paths and which don't.
    """
    missing_entries = []

    for service, operations in ALLOWED_CUSTOM_OPERATIONS.items():
        # Skip the wildcard service
        if service == '*':
            continue

        # Check if service exists in CUSTOM_FILE_PATH_ARGUMENTS
        if service not in CUSTOM_FILE_PATH_ARGUMENTS:
            missing_entries.append(
                f"Service '{service}' is missing from CUSTOM_FILE_PATH_ARGUMENTS"
            )
            continue

        # Check if all operations for this service have entries
        for operation in operations:
            if operation not in CUSTOM_FILE_PATH_ARGUMENTS[service]:
                missing_entries.append(
                    f"Operation '{operation}' for service '{service}' is missing from CUSTOM_FILE_PATH_ARGUMENTS"
                )

    assert not missing_entries, (
        'The following custom operations are missing from CUSTOM_FILE_PATH_ARGUMENTS:\n'
        + '\n'.join(missing_entries)
        + '\n\nAll custom operations must have an explicit entry in CUSTOM_FILE_PATH_ARGUMENTS, '
        + "even if it's an empty list (for operations that don't accept file paths)."
    )


def test_extract_file_paths_service_non_custom_operation():
    """Test extract_file_paths_from_parameters with non-custom operation."""
    command_metadata = CommandMetadata(
        service_sdk_name='lambda', service_full_sdk_name='AWS Lambda', operation_sdk_name='Invoke'
    )

    parameters = {
        'FunctionName': 'MyFunction',
        'Payload': '{"key": "value"}',
    }

    result = extract_file_paths_from_parameters(command_metadata, parameters)

    assert result == []


def test_extract_file_paths_param_value_is_list():
    """Test extract_file_paths_from_parameters when param_value is a list for file path arguments."""
    command_metadata = CommandMetadata(
        service_sdk_name='s3', service_full_sdk_name='s3', operation_sdk_name='sync'
    )

    parameters = {
        '--paths': [
            '/local/file1.txt',
            's3://bucket/key1',
        ],
        '--other-param': 'value',
    }

    result = extract_file_paths_from_parameters(command_metadata, parameters)

    # Should extract only the local file paths (remote paths are filtered out)
    expected = ['/local/file1.txt']
    assert result == expected


def test_extract_file_paths_parameter_none_value():
    """Test extract_file_paths_from_parameters with emr create-cluster and --configurations parameter set to None."""
    command_metadata = CommandMetadata(
        service_sdk_name='emr', service_full_sdk_name='emr', operation_sdk_name='create-cluster'
    )

    parameters = {
        '--configurations': None,
        '--name': 'MyCluster',
    }

    result = extract_file_paths_from_parameters(command_metadata, parameters)

    assert result == []
