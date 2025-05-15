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
"""Tests for the cfn MCP Server."""

import pytest
from awslabs.cfn_mcp_server.errors import handle_aws_api_error


@pytest.mark.asyncio
class TestErrors:
    """Tests on the errors module."""

    async def test_handle_access_denied(self):
        """Testing access denied."""
        error = Exception('AccessDenied')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('Access denied')  # pyright: ignore[reportAttributeAccessIssue]

    async def test_handle_incomplete_signature(self):
        """Testing incomplete signature."""
        error = Exception('IncompleteSignature')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('Incomplete signature')  # pyright: ignore[reportAttributeAccessIssue]

    async def test_handle_invalid_action(self):
        """Testing invalid action."""
        error = Exception('InvalidAction')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('Invalid action')  # pyright: ignore[reportAttributeAccessIssue]

    async def test_handle_invalid_client_token(self):
        """Testing invalid client token."""
        error = Exception('InvalidClientTokenId')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('Invalid client token id')  # pyright: ignore[reportAttributeAccessIssue]

    async def test_handle_not_authorized(self):
        """Testing invalid not authorized."""
        error = Exception('NotAuthorized')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('Not authorized')  # pyright: ignore[reportAttributeAccessIssue]

    async def test_handle_validation(self):
        """Testing validation."""
        error = Exception('ValidationException')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('Validation error')  # pyright: ignore[reportAttributeAccessIssue]

    async def test_handle_rnf(self):
        """Testing rnf."""
        error = Exception('ResourceNotFoundException')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('Resource was not found')  # pyright: ignore[reportAttributeAccessIssue]

    async def test_handle_ua(self):
        """Testing uae."""
        error = Exception('UnsupportedActionException')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('This action is not supported')  # pyright: ignore[reportAttributeAccessIssue]

    async def test_handle_ip(self):
        """Testing ip."""
        error = Exception('InvalidPatchException')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('The patch document')  # pyright: ignore[reportAttributeAccessIssue]

    async def test_handle_throttle(self):
        """Testing throttle."""
        error = Exception('ThrottlingException')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('Request was throttled')  # pyright: ignore[reportAttributeAccessIssue]

    async def test_handle_internal_failure(self):
        """Testing internal failure."""
        error = Exception('InternalFailure')
        mapped = handle_aws_api_error(error)
        assert not hasattr(mapped, 'message')

    async def test_handle_service_unavailable(self):
        """Testing internal failure."""
        error = Exception('ServiceUnavailable')
        mapped = handle_aws_api_error(error)
        assert not hasattr(mapped, 'message')

    async def test_handle_other(self):
        """Testing big catch."""
        error = Exception('none of the above')
        mapped = handle_aws_api_error(error)
        assert mapped.message.startswith('An error occurred')  # pyright: ignore[reportAttributeAccessIssue]
