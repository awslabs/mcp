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
from awslabs.rds_control_plane_mcp_server.common import utils
from botocore.exceptions import ClientError


"""Tests for RDS Management MCP Server utilities."""


class TestApplyDocstring:
    """Tests for apply_docstring decorator."""

    def test_apply_docstring(self):
        """Test that docstring is applied correctly."""

        def test_func(x, y):
            """Original docstring."""
            return x + y

        new_docstring = 'This is a new docstring.'
        decorated_func = utils.apply_docstring(new_docstring)(test_func)

        assert decorated_func.__doc__ == new_docstring
        assert decorated_func(1, 2) == 3

    def test_apply_docstring_preserves_function_metadata(self):
        """Test that function metadata is preserved."""

        def test_func(x):
            """Original docstring."""
            return x * 2

        decorated_func = utils.apply_docstring('New docstring')(test_func)

        # Check that function metadata is preserved (thanks to @wraps)
        assert decorated_func.__name__ == test_func.__name__
        assert decorated_func.__module__ == test_func.__module__
        assert decorated_func.__qualname__ == test_func.__qualname__

    def test_apply_docstring_with_multiline_docstring(self):
        """Test applying a multiline docstring."""

        def test_func():
            pass

        multiline_doc = """
        This is a multiline docstring.

        It has multiple paragraphs and should be
        preserved exactly as is.

        Args:
            None

        Returns:
            None
        """

        decorated_func = utils.apply_docstring(multiline_doc)(test_func)
        assert decorated_func.__doc__ == multiline_doc


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
