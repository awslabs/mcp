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

"""Unit tests for UpdateItemAccessPattern model."""

import pytest
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import (
    UpdateItemAccessPattern,
)


class TestUpdateItemAccessPattern:
    """Tests for UpdateItemAccessPattern model."""

    @pytest.fixture
    def updateitem_pattern(self):
        """Base UpdateItem access pattern with sensible defaults for all tests."""
        return {
            'operation': 'UpdateItem',
            'pattern': 'test-pattern',
            'description': 'Test description',
            'table': 'test-table',
            'rps': 100,
            'item_size_bytes': 1000,
        }

    class TestValid:
        """Tests for valid UpdateItem creation."""

        def test_valid_updateitem_minimal(self, updateitem_pattern):
            """Test UpdateItem with valid minimal data."""
            ap = UpdateItemAccessPattern(**updateitem_pattern)
            assert ap.operation == 'UpdateItem'
            assert ap.gsi_list == []

        def test_valid_updateitem_with_gsi_list(self, updateitem_pattern):
            """Test UpdateItem with GSI list."""
            updateitem_pattern['gsi_list'] = ['gsi-1']
            ap = UpdateItemAccessPattern(**updateitem_pattern)
            assert ap.gsi_list == ['gsi-1']
