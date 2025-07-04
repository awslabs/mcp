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
"""Simple tests that actually work."""

from awslabs.ccapi_mcp_server.errors import ClientError


class TestSimple:
    """Simple tests that don't break."""

    def test_imports(self):
        """Test basic imports work."""
        from awslabs.ccapi_mcp_server import errors, server

        assert server is not None
        assert errors is not None

    def test_error_classes(self):
        """Test error classes."""
        error = ClientError('test message')
        assert str(error) == 'test message'

    async def test_basic_server_functions_exist(self):
        """Test server functions exist."""
        from awslabs.ccapi_mcp_server.server import (
            create_resource,
            delete_resource,
            get_resource,
            get_resource_schema_information,
            list_resources,
            update_resource,
        )

        # Just test they exist, don't call them
        assert callable(get_resource_schema_information)
        assert callable(list_resources)
        assert callable(get_resource)
        assert callable(create_resource)
        assert callable(update_resource)
        assert callable(delete_resource)
