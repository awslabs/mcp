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
from awslabs.aws_api_mcp_server.core.common.config import WORKING_DIRECTORY
from awslabs.aws_api_mcp_server.core.common.file_system_controls import validate_file_path
from unittest.mock import patch


def test_safe_path_allowed():
    """Test that files within working directory are allowed."""
    safe_path = os.path.join(WORKING_DIRECTORY, 'safe_file.txt')
    result = validate_file_path(safe_path)
    assert result == safe_path


def test_unsafe_path_blocked():
    """Test that files outside working directory are blocked."""
    unsafe_path = '/tmp/unsafe_file.txt'
    with pytest.raises(ValueError):
        validate_file_path(unsafe_path)


@patch(
    'awslabs.aws_api_mcp_server.core.common.file_system_controls.ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS',
    True,
)
def test_unrestricted_access_allows_unsafe_path():
    """Test that unrestricted access allows files outside working directory."""
    unsafe_path = '/tmp/unsafe_file.txt'
    result = validate_file_path(unsafe_path)
    assert result == unsafe_path
