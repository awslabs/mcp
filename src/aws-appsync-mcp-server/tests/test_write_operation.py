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

"""Tests for the write_operation decorator."""

import pytest
from awslabs.aws_appsync_mcp_server.decorators import (
    is_write_allowed,
    set_write_allowed,
    write_operation,
)


@pytest.mark.asyncio
async def test_write_operation_allowed():
    """Test write operation when write operations are allowed."""
    # Enable write operations
    set_write_allowed(True)

    @write_operation
    async def test_function():
        return 'success'

    result = await test_function()
    assert result == 'success'


@pytest.mark.asyncio
async def test_write_operation_not_allowed():
    """Test write operation when write operations are not allowed."""
    # Disable write operations
    set_write_allowed(False)

    @write_operation
    async def test_function():
        return 'success'

    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await test_function()


@pytest.mark.asyncio
async def test_write_operation_with_args_and_kwargs():
    """Test write operation decorator with function arguments."""
    # Enable write operations
    set_write_allowed(True)

    @write_operation
    async def test_function_with_args(arg1, arg2, kwarg1=None):
        return f'{arg1}-{arg2}-{kwarg1}'

    result = await test_function_with_args('test1', 'test2', kwarg1='test3')
    assert result == 'test1-test2-test3'


@pytest.mark.asyncio
async def test_write_operation_preserves_function_metadata():
    """Test that write_operation decorator preserves function metadata."""

    @write_operation
    async def test_function():
        """Test function docstring."""
        return 'success'

    assert test_function.__name__ == 'test_function'
    assert test_function.__doc__ == 'Test function docstring.'


def test_write_allowed_state_management():
    """Test that write allowed state can be properly managed."""
    # Test initial state
    set_write_allowed(False)
    assert not is_write_allowed()

    # Test enabling write operations
    set_write_allowed(True)
    assert is_write_allowed()

    # Test disabling write operations
    set_write_allowed(False)
    assert not is_write_allowed()
