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
import pytest
from awslabs.rds_control_plane_mcp_server import utils
from botocore.exceptions import ClientError


"""Tests for RDS Management MCP Server utilities."""


@pytest.mark.asyncio
class TestHandleAwsError:
    """Tests for handle_aws_error function."""

    async def test_handle_aws_error_client_error(self):
        """Test handling AWS client error."""
        operation = 'test_operation'
        error = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='DescribeDBClusters',
        )

        result = await utils.handle_aws_error(operation, error)

        assert 'error' in result
        assert 'Access denied' in str(result)
        assert 'error_code' in result
        assert result['error_code'] == 'AccessDenied'

    async def test_handle_aws_error_general_exception(self):
        """Test handling general exception."""
        operation = 'test_operation'
        error = ValueError('Invalid value')

        result = await utils.handle_aws_error(operation, error)

        assert 'error' in result
        assert 'Invalid value' in str(result)
        assert 'error_type' in result
