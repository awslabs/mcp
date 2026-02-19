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

"""Unit tests for DeleteItemAccessPattern model."""

import pytest
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import (
    DeleteItemAccessPattern,
)


class TestDeleteItemAccessPattern:
    """Tests for DeleteItemAccessPattern model."""

    @pytest.fixture
    def deleteitem_pattern(self):
        """Base DeleteItem access pattern with sensible defaults for all tests."""
        return {
            'operation': 'DeleteItem',
            'pattern': 'test-pattern',
            'description': 'Test description',
            'table': 'test-table',
            'rps': 100,
            'item_size_bytes': 1000,
        }

    class TestValid:
        """Tests for valid DeleteItem creation."""

        def test_valid_deleteitem_minimal(self, deleteitem_pattern):
            """Test DeleteItem with valid minimal data."""
            ap = DeleteItemAccessPattern(**deleteitem_pattern)
            assert ap.operation == 'DeleteItem'
            assert ap.gsi_list == []

        def test_valid_deleteitem_with_gsi_list(self, deleteitem_pattern):
            """Test DeleteItem with GSI list."""
            deleteitem_pattern['gsi_list'] = ['gsi-1', 'gsi-2', 'gsi-3']
            ap = DeleteItemAccessPattern(**deleteitem_pattern)
            assert ap.gsi_list == ['gsi-1', 'gsi-2', 'gsi-3']
