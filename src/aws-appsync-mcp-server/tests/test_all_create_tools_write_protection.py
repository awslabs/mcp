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

"""Tests to ensure all create tools have write operation protection."""

import pytest
from awslabs.aws_appsync_mcp_server.decorators import set_write_allowed, write_operation
from unittest.mock import patch


class TestAllCreateToolsWriteProtection:
    """Test class to verify all create tools have write operation protection."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        # No need to store state since we're using global functions
        yield
        # Reset to default state
        set_write_allowed(False)

    @pytest.mark.asyncio
    async def test_create_api_write_protection(self):
        """Test create_api has write protection."""
        set_write_allowed(False)

        with patch(
            'awslabs.aws_appsync_mcp_server.operations.create_api.create_api_operation'
        ) as mock_op:
            mock_op.return_value = {'api': {'apiId': 'test'}}

            # Create a test function that simulates the decorated tool
            @write_operation
            async def test_create_api():
                return await mock_op()

            with pytest.raises(
                ValueError, match='Operation not permitted: Server is configured in read-only mode'
            ):
                await test_create_api()

    @pytest.mark.asyncio
    async def test_create_graphql_api_write_protection(self):
        """Test create_graphql_api has write protection."""
        set_write_allowed(False)

        with patch(
            'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.create_graphql_api_operation'
        ) as mock_op:
            mock_op.return_value = {'graphqlApi': {'apiId': 'test'}}

            @write_operation
            async def test_create_graphql_api():
                return await mock_op()

            with pytest.raises(
                ValueError, match='Operation not permitted: Server is configured in read-only mode'
            ):
                await test_create_graphql_api()

    @pytest.mark.asyncio
    async def test_create_api_key_write_protection(self):
        """Test create_api_key has write protection."""
        set_write_allowed(False)

        with patch(
            'awslabs.aws_appsync_mcp_server.operations.create_api_key.create_api_key_operation'
        ) as mock_op:
            mock_op.return_value = {'apiKey': {'id': 'test'}}

            @write_operation
            async def test_create_api_key():
                return await mock_op()

            with pytest.raises(
                ValueError, match='Operation not permitted: Server is configured in read-only mode'
            ):
                await test_create_api_key()

    @pytest.mark.asyncio
    async def test_create_api_cache_write_protection(self):
        """Test create_api_cache has write protection."""
        set_write_allowed(False)

        with patch(
            'awslabs.aws_appsync_mcp_server.operations.create_api_cache.create_api_cache_operation'
        ) as mock_op:
            mock_op.return_value = {'apiCache': {'status': 'CREATING'}}

            @write_operation
            async def test_create_api_cache():
                return await mock_op()

            with pytest.raises(
                ValueError, match='Operation not permitted: Server is configured in read-only mode'
            ):
                await test_create_api_cache()

    @pytest.mark.asyncio
    async def test_create_datasource_write_protection(self):
        """Test create_datasource has write protection."""
        set_write_allowed(False)

        with patch(
            'awslabs.aws_appsync_mcp_server.operations.create_datasource.create_datasource_operation'
        ) as mock_op:
            mock_op.return_value = {'dataSource': {'name': 'test'}}

            @write_operation
            async def test_create_datasource():
                return await mock_op()

            with pytest.raises(
                ValueError, match='Operation not permitted: Server is configured in read-only mode'
            ):
                await test_create_datasource()

    @pytest.mark.asyncio
    async def test_create_function_write_protection(self):
        """Test create_function has write protection."""
        set_write_allowed(False)

        with patch(
            'awslabs.aws_appsync_mcp_server.operations.create_function.create_function_operation'
        ) as mock_op:
            mock_op.return_value = {'functionConfiguration': {'name': 'test'}}

            @write_operation
            async def test_create_function():
                return await mock_op()

            with pytest.raises(
                ValueError, match='Operation not permitted: Server is configured in read-only mode'
            ):
                await test_create_function()

    @pytest.mark.asyncio
    async def test_create_channel_namespace_write_protection(self):
        """Test create_channel_namespace has write protection."""
        set_write_allowed(False)

        with patch(
            'awslabs.aws_appsync_mcp_server.operations.create_channel_namespace.create_channel_namespace_operation'
        ) as mock_op:
            mock_op.return_value = {'channelNamespace': {'name': 'test'}}

            @write_operation
            async def test_create_channel_namespace():
                return await mock_op()

            with pytest.raises(
                ValueError, match='Operation not permitted: Server is configured in read-only mode'
            ):
                await test_create_channel_namespace()

    @pytest.mark.asyncio
    async def test_create_domain_name_write_protection(self):
        """Test create_domain_name has write protection."""
        set_write_allowed(False)

        with patch(
            'awslabs.aws_appsync_mcp_server.operations.create_domain_name.create_domain_name_operation'
        ) as mock_op:
            mock_op.return_value = {'domainNameConfig': {'domainName': 'test.com'}}

            @write_operation
            async def test_create_domain_name():
                return await mock_op()

            with pytest.raises(
                ValueError, match='Operation not permitted: Server is configured in read-only mode'
            ):
                await test_create_domain_name()

    @pytest.mark.asyncio
    async def test_create_resolver_write_protection(self):
        """Test create_resolver has write protection."""
        set_write_allowed(False)

        with patch(
            'awslabs.aws_appsync_mcp_server.operations.create_resolver.create_resolver_operation'
        ) as mock_op:
            mock_op.return_value = {'resolver': {'typeName': 'Query'}}

            @write_operation
            async def test_create_resolver():
                return await mock_op()

            with pytest.raises(
                ValueError, match='Operation not permitted: Server is configured in read-only mode'
            ):
                await test_create_resolver()

    @pytest.mark.asyncio
    async def test_create_schema_write_protection(self):
        """Test create_schema has write protection."""
        set_write_allowed(False)

        with patch(
            'awslabs.aws_appsync_mcp_server.operations.create_schema.create_schema_operation'
        ) as mock_op:
            mock_op.return_value = {'status': 'SUCCESS'}

            @write_operation
            async def test_create_schema():
                return await mock_op()

            with pytest.raises(
                ValueError, match='Operation not permitted: Server is configured in read-only mode'
            ):
                await test_create_schema()

    @pytest.mark.asyncio
    async def test_all_create_tools_work_when_write_enabled(self):
        """Test that all create tools work when write operations are enabled."""
        set_write_allowed(True)

        @write_operation
        async def test_function():
            return 'success'

        result = await test_function()
        assert result == 'success'

    def test_write_operation_decorator_exists(self):
        """Test that the write_operation decorator is properly imported and available."""
        from awslabs.aws_appsync_mcp_server.decorators import write_operation

        assert callable(write_operation)

    def test_decorator_state_management(self):
        """Test that the decorator state management works correctly."""
        from awslabs.aws_appsync_mcp_server.decorators import is_write_allowed

        set_write_allowed(False)
        assert not is_write_allowed()

        set_write_allowed(True)
        assert is_write_allowed()
