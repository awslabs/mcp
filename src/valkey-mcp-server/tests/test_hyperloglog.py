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

"""Tests for the HyperLogLog functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.hyperloglog import (
    hll_add,
    hll_count,
)
from unittest.mock import Mock, patch
from valkey.exceptions import ValkeyError


class TestHyperLogLog:
    """Tests for HyperLogLog operations."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Valkey connection."""
        with patch(
            'awslabs.valkey_mcp_server.tools.hyperloglog.ValkeyConnectionManager'
        ) as mock_manager:
            mock_conn = Mock()
            mock_manager.get_connection.return_value = mock_conn
            yield mock_conn

    @pytest.mark.asyncio
    async def test_hll_add(self, mock_connection):
        """Test adding elements to HyperLogLog."""
        key = 'test_hll'
        element = 'element1'

        # Test successful add with new elements
        mock_connection.pfadd.return_value = True
        result = await hll_add(key, element)
        assert f"Added 1 element to '{key}'" in result
        mock_connection.pfadd.assert_called_with(key, element)

        # Test add with existing elements
        mock_connection.pfadd.return_value = False
        result = await hll_add(key, element)
        assert f"No new element added to '{key}' (already existed)" in result

        # Test no element provided
        result = await hll_add(key, None)
        assert 'Error: an element is required' in result

        # Test error handling
        mock_connection.pfadd.side_effect = ValkeyError('Test error')
        result = await hll_add(key, element)
        assert f"Error adding element to '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_hll_count(self, mock_connection):
        """Test getting HyperLogLog cardinality."""
        key = 'test_hll'

        # Test successful count
        mock_connection.pfcount.return_value = 100
        result = await hll_count(key)
        assert f"Estimated unique elements in '{key}': 100" in result
        mock_connection.pfcount.assert_called_with(key)

        # Test error handling
        mock_connection.pfcount.side_effect = ValkeyError('Test error')
        result = await hll_count(key)
        assert f"Error getting count from '{key}'" in result
        assert 'Test error' in result
