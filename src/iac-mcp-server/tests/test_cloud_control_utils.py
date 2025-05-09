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
from awslabs.iac_mcp_server.cloud_control_utils import progress_event, validate_patch
from awslabs.iac_mcp_server.errors import ClientError


@pytest.mark.asyncio
class TestUtils:
    """Tests on the cloud_control_utils module."""

    async def test_empty_patch(self):
        """Testing no information in patch."""
        validate_patch([])

    async def test_patch_with_invalid_shape_1(self):
        """Testing bad shape."""
        with pytest.raises(ClientError):
            validate_patch(['not_a_dict'])

    async def test_patch_with_invalid_shape_2(self):
        """Testing no operation."""
        with pytest.raises(ClientError):
            validate_patch([{'not-op': 'is bad'}])

    async def test_patch_with_invalid_shape_3(self):
        """Testing invalid operation."""
        with pytest.raises(ClientError):
            validate_patch([{'op': 'invalid'}])

    async def test_patch_with_invalid_shape_4(self):
        """Testing no path."""
        with pytest.raises(ClientError):
            validate_patch([{'op': 'add', 'not-path': 'is bad'}])

    async def test_happy_remove(self):
        """Testing simple remove."""
        validate_patch([{'op': 'remove', 'path': '/property'}])

    async def test_patch_with_invalid_shape_5(self):
        """Testing no value."""
        with pytest.raises(ClientError):
            validate_patch([{'op': 'add', 'path': '/property', 'not-value': 'is bad'}])

    async def test_happy_add(self):
        """Testing simple add."""
        validate_patch([{'op': 'add', 'path': '/property', 'value': '25'}])

    async def test_patch_with_invalid_shape_6(self):
        """Testing no from."""
        with pytest.raises(ClientError):
            validate_patch([{'op': 'move', 'path': '/property', 'not-from': 'is bad'}])

    async def test_progress_event(self):
        """Testing mapping progress event."""
        request = {
            'OperationStatus': 'SUCCESS',
            'TypeName': 'AWS::CodeStarConnections::Connection',
            'RequestToken': '25',
        }

        response = {
            'status': 'SUCCESS',
            'resource_type': 'AWS::CodeStarConnections::Connection',
            'is_complete': True,
            'request_token': '25',
        }

        assert progress_event(request) == response
