# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the iac MCP Server."""

import pytest
from awslabs.iac_mcp_server.errors import handle_aws_api_error


@pytest.mark.asyncio
class TestErrors:
    """Tests on the errors module."""

    async def test_handle_access_denied(self):
        """Testing access denied."""
        error = Exception('AccessDenied')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('Access denied')

    async def test_handle_validation(self):
        """Testing validation."""
        error = Exception('ValidationException')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('Validation error')

    async def test_handle_rnf(self):
        """Testing rnf."""
        error = Exception('ResourceNotFoundException')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('Resource was not found')

    async def test_handle_ua(self):
        """Testing uae."""
        error = Exception('UnsupportedActionException')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('This action is not supported')

    async def test_handle_ip(self):
        """Testing ip."""
        error = Exception('InvalidPatchException')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('The patch document')

    async def test_handle_throttle(self):
        """Testing throttle."""
        error = Exception('ThrottlingException')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('Request was throttled')

    async def test_handle_other(self):
        """Testing big catch."""
        error = Exception('none of the above')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('An error occurred')
