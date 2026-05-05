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

"""Unit tests for Table model."""

import pytest
from .test_data_model import strip_pydantic_error_url
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import (
    MAX_GSIS_PER_TABLE,
    Table,
    format_validation_errors,
)
from pydantic import ValidationError


class TestTable:
    """Tests for Table model."""

    @pytest.fixture
    def valid_table_data(self):
        """Valid table data."""
        return {'name': 'test-table', 'item_count': 1000, 'item_size_bytes': 2000}

    class TestValid:
        """Tests for valid Table creation."""

        def test_valid_table_minimal(self, valid_table_data):
            """Test table with valid minimal data."""
            table = Table(**valid_table_data)
            assert table.name == 'test-table'
            assert table.item_count == 1000
            assert table.item_size_bytes == 2000
            assert table.gsi_list == []

        def test_valid_table_with_gsis(self, valid_table_data):
            """Test table with GSIs."""
            valid_table_data['gsi_list'] = [
                {'name': 'test-gsi', 'item_size_bytes': 1000, 'item_count': 100}
            ]
            table = Table(**valid_table_data)
            assert len(table.gsi_list) == 1
            assert table.gsi_list[0].name == 'test-gsi'

        def test_valid_table_max_gsis(self, valid_table_data):
            """Test table with maximum number of GSIs."""
            gsi_list = [
                {'name': f'gsi-{i}', 'item_size_bytes': 1000, 'item_count': 100}
                for i in range(MAX_GSIS_PER_TABLE)
            ]
            valid_table_data['gsi_list'] = gsi_list
            table = Table(**valid_table_data)
            assert len(table.gsi_list) == MAX_GSIS_PER_TABLE

    class TestInvalid:
        """Tests for invalid Table creation."""

        def test_invalid_table_empty_name(self, valid_table_data):
            """Test table with empty name."""
            valid_table_data['name'] = ''
            with pytest.raises(ValidationError) as exc_info:
                Table(**valid_table_data)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == "1 validation error for Table\nname\n  String should have at least 1 character [type=string_too_short, input_value='', input_type=str]"
            )
            assert format_validation_errors(exc_info.value) == 'name: cannot be empty. name: '

        def test_invalid_table_item_count_zero(self, valid_table_data):
            """Test table with zero item count."""
            valid_table_data['item_count'] = 0
            with pytest.raises(ValidationError) as exc_info:
                Table(**valid_table_data)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == '1 validation error for Table\nitem_count\n  Input should be greater than 0 [type=greater_than, input_value=0, input_type=int]'
            )
            assert (
                format_validation_errors(exc_info.value)
                == 'item_count: must be greater than 0. item_count: 0'
            )

        def test_invalid_table_item_size_exceeds_max(self, valid_table_data):
            """Test table with item size exceeding maximum."""
            valid_table_data['item_size_bytes'] = 409601
            with pytest.raises(ValidationError) as exc_info:
                Table(**valid_table_data)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == '1 validation error for Table\nitem_size_bytes\n  Input should be less than or equal to 409600 [type=less_than_equal, input_value=409601, input_type=int]'
            )
            assert (
                format_validation_errors(exc_info.value)
                == 'item_size_bytes: must be at most 409600. item_size_bytes: 409601'
            )

        def test_invalid_table_too_many_gsis(self, valid_table_data):
            """Test table with too many GSIs."""
            gsi_list = [
                {'name': f'gsi-{i}', 'item_size_bytes': 1000, 'item_count': 100} for i in range(21)
            ]
            valid_table_data['gsi_list'] = gsi_list
            with pytest.raises(ValidationError) as exc_info:
                Table(**valid_table_data)
            err = strip_pydantic_error_url(exc_info.value)
            assert err.startswith(
                '1 validation error for Table\ngsi_list\n  List should have at most 20 items after validation, not 21 [type=too_long, input_value='
            )
            assert (
                format_validation_errors(exc_info.value)
                == 'gsi_list: must have at most 20 items. gsi_list: 21'
            )

        def test_invalid_table_duplicate_gsi_names(self, valid_table_data):
            """Test table with duplicate GSI names."""
            gsi_list = [
                {'name': 'duplicate-gsi', 'item_size_bytes': 1000, 'item_count': 100},
                {'name': 'duplicate-gsi', 'item_size_bytes': 1500, 'item_count': 200},
            ]
            valid_table_data['gsi_list'] = gsi_list
            with pytest.raises(ValidationError) as exc_info:
                Table(**valid_table_data)
            err = strip_pydantic_error_url(exc_info.value)
            assert err.startswith(
                '1 validation error for Table\ngsi_list\n  Value error, duplicate GSI name. name: "duplicate-gsi" [type=value_error, input_value='
            )
            assert (
                format_validation_errors(exc_info.value)
                == 'gsi_list: duplicate GSI name. name: "duplicate-gsi"'
            )

        def test_invalid_table_gsi_size_exceeds_table_size(self, valid_table_data):
            """Test table with GSI size exceeding table size."""
            valid_table_data['item_size_bytes'] = 1000
            gsi_list = [{'name': 'large-gsi', 'item_size_bytes': 2000, 'item_count': 100}]
            valid_table_data['gsi_list'] = gsi_list
            with pytest.raises(ValidationError) as exc_info:
                Table(**valid_table_data)
            err = strip_pydantic_error_url(exc_info.value)
            assert err.startswith(
                '1 validation error for Table\n  Value error, GSI item_size_bytes cannot exceed table item_size_bytes. gsi_item_size_bytes: 2000, table_item_size_bytes: 1000 [type=value_error, input_value='
            )
            assert (
                format_validation_errors(exc_info.value)
                == 'GSI item_size_bytes cannot exceed table item_size_bytes. gsi_item_size_bytes: 2000, table_item_size_bytes: 1000'
            )
