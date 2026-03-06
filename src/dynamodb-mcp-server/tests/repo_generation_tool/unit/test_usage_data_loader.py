"""Unit tests for UsageDataLoader."""

import json
import pytest
import tempfile
from awslabs.dynamodb_mcp_server.repo_generation_tool.core import file_utils
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.usage_data_loader import (
    UsageDataLoader,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.languages.python.usage_data_formatter import (
    PythonUsageDataFormatter,
)
from pathlib import Path
from unittest.mock import mock_open, patch


@pytest.mark.unit
class TestUsageDataLoader:
    """Test UsageDataLoader functionality."""

    @pytest.fixture
    def sample_usage_data(self):
        """Sample usage data for testing."""
        return {
            'entities': {
                'User': {
                    'sample_data': {
                        'user_id': 'user-12345',
                        'username': 'john_doe',
                        'email': 'john.doe@example.com',
                    },
                    'access_pattern_data': {
                        'user_id': 'user-67890',
                        'username': 'jane_doe',
                        'email': 'jane.doe@example.com',
                    },
                    'update_data': {
                        'username': 'john_doe_updated',
                        'email': 'john.updated@example.com',
                    },
                },
                'Product': {
                    'sample_data': {
                        'product_id': 'prod-67890',
                        'name': 'Wireless Headphones',
                        'price': 99.99,
                    },
                    'access_pattern_data': {
                        'product_id': 'prod-11111',
                        'name': 'Bluetooth Speaker',
                        'price': 49.99,
                    },
                    'update_data': {'name': 'Premium Wireless Headphones', 'price': 89.99},
                },
            }
        }

    @pytest.fixture
    def temp_usage_file(self, sample_usage_data):
        """Create a temporary usage data file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_usage_data, f)
            temp_path = f.name
        yield temp_path
        Path(temp_path).unlink()

    def test_init_without_path(self):
        """Test initialization without usage data path."""
        loader = UsageDataLoader()
        assert loader.usage_data_path is None
        assert loader.usage_data == {}
        assert not loader.has_data()
        assert loader.formatter is None

    def test_init_with_nonexistent_path(self):
        """Test initialization with non-existent file path."""
        loader = UsageDataLoader('/nonexistent/path.json')
        assert loader.usage_data_path == '/nonexistent/path.json'
        assert loader.usage_data == {}
        assert not loader.has_data()

    def test_init_with_valid_path(self, temp_usage_file, sample_usage_data):
        """Test initialization with valid usage data file."""
        formatter = PythonUsageDataFormatter()
        loader = UsageDataLoader(temp_usage_file, formatter)
        assert loader.usage_data_path == temp_usage_file
        assert loader.usage_data == sample_usage_data
        assert loader.has_data()
        assert loader.formatter is formatter

    def test_load_usage_data_file_not_found(self):
        """Test loading non-existent usage data file."""
        loader = UsageDataLoader()
        loader.usage_data_path = '/nonexistent/file.json'

        with patch('builtins.open', side_effect=FileNotFoundError):
            loader._load_usage_data()

        assert loader.usage_data == {}

    def test_load_usage_data_invalid_json(self):
        """Test loading invalid JSON file."""
        loader = UsageDataLoader()
        loader.usage_data_path = 'invalid.json'

        with patch('builtins.open', mock_open(read_data='invalid json')):
            loader._load_usage_data()

        assert loader.usage_data == {}

    def test_load_usage_data_permission_error(self):
        """Test loading file with permission error."""
        loader = UsageDataLoader()
        loader.usage_data_path = 'restricted.json'

        with patch('builtins.open', side_effect=PermissionError):
            loader._load_usage_data()

        assert loader.usage_data == {}

    def test_get_sample_value_for_field_entity_specific(self, temp_usage_file):
        """Test getting sample value from entity-specific data."""
        formatter = PythonUsageDataFormatter()
        loader = UsageDataLoader(temp_usage_file, formatter)

        result = loader.get_sample_value_for_field('username', 'string', 'User')
        assert result == '"john_doe"'

        result = loader.get_sample_value_for_field('email', 'string', 'User')
        assert result == '"john.doe@example.com"'

    def test_get_sample_value_for_field_access_pattern_data(self, temp_usage_file):
        """Test getting sample value from access_pattern_data."""
        formatter = PythonUsageDataFormatter()
        loader = UsageDataLoader(temp_usage_file, formatter)

        result = loader.get_sample_value_for_field('product_id', 'string', 'Product')
        assert result == '"prod-67890"'

    def test_get_sample_value_for_field_fallback(self, temp_usage_file):
        """Test getting sample value with fallback to default."""
        formatter = PythonUsageDataFormatter()
        loader = UsageDataLoader(temp_usage_file, formatter)

        # Should return None for non-existent field
        result = loader.get_sample_value_for_field('category', 'string')
        assert result is None

    def test_get_sample_value_for_field_with_entity(self, temp_usage_file):
        """Test getting sample value with entity name."""
        formatter = PythonUsageDataFormatter()
        loader = UsageDataLoader(temp_usage_file, formatter)

        result = loader.get_sample_value_for_field('user_id', 'string', 'User')
        assert result == '"user-12345"'

        result = loader.get_sample_value_for_field('name', 'string', 'Product')
        assert result == '"Wireless Headphones"'

    def test_get_sample_value_for_field_multiple_entities(self, temp_usage_file):
        """Test getting sample values from different entities."""
        formatter = PythonUsageDataFormatter()
        loader = UsageDataLoader(temp_usage_file, formatter)

        # User entity
        result = loader.get_sample_value_for_field('user_id', 'string', 'User')
        assert result == '"user-12345"'

        # Product entity
        result = loader.get_sample_value_for_field('product_id', 'string', 'Product')
        assert result == '"prod-67890"'

    def test_get_sample_value_for_field_not_found(self, temp_usage_file):
        """Test getting sample value for non-existent field."""
        formatter = PythonUsageDataFormatter()
        loader = UsageDataLoader(temp_usage_file, formatter)

        result = loader.get_sample_value_for_field('nonexistent', 'string')
        assert result is None

    def test_get_update_value_for_field_entity_specific(self, temp_usage_file):
        """Test getting update value from entity-specific data."""
        formatter = PythonUsageDataFormatter()
        loader = UsageDataLoader(temp_usage_file, formatter)

        result = loader.get_update_value_for_field('username', 'string', 'User')
        assert result == '"john_doe_updated"'

    def test_get_update_value_for_field_fallback(self, temp_usage_file):
        """Test getting update value with fallback."""
        formatter = PythonUsageDataFormatter()
        loader = UsageDataLoader(temp_usage_file, formatter)

        # Should return None for non-existent field
        result = loader.get_update_value_for_field('status', 'string')
        assert result is None

    def test_get_update_value_for_field_not_found(self, temp_usage_file):
        """Test getting update value for non-existent field."""
        formatter = PythonUsageDataFormatter()
        loader = UsageDataLoader(temp_usage_file, formatter)

        result = loader.get_update_value_for_field('nonexistent', 'string')
        assert result is None

    def test_get_sample_value_without_formatter(self, temp_usage_file):
        """Test that loader returns None when no formatter is provided."""
        loader = UsageDataLoader(temp_usage_file)

        result = loader.get_sample_value_for_field('username', 'string', 'User')
        assert result is None

    def test_get_update_value_without_formatter(self, temp_usage_file):
        """Test that loader returns None when no formatter is provided."""
        loader = UsageDataLoader(temp_usage_file)

        result = loader.get_update_value_for_field('username', 'string', 'User')
        assert result is None

    def test_format_string_value(self):
        """Test string value formatting."""
        formatter = PythonUsageDataFormatter()

        assert formatter._format_string_value('simple') == '"simple"'
        assert formatter._format_string_value('with "quotes"') == '"with \\"quotes\\""'
        assert formatter._format_string_value('with\\backslash') == '"with\\\\backslash"'

    def test_format_integer_value(self):
        """Test integer value formatting."""
        formatter = PythonUsageDataFormatter()

        assert formatter._format_integer_value(42) == '42'
        assert formatter._format_integer_value(3.14) == '3'
        assert formatter._format_integer_value('123') == '123'
        assert formatter._format_integer_value('invalid') == '42'

    def test_format_decimal_value(self):
        """Test decimal value formatting."""
        formatter = PythonUsageDataFormatter()

        assert formatter._format_decimal_value(3.14) == 'Decimal("3.14")'
        assert formatter._format_decimal_value(42) == 'Decimal("42")'
        assert formatter._format_decimal_value('99.99') == 'Decimal("99.99")'
        assert formatter._format_decimal_value('invalid') == 'Decimal("3.14")'

    def test_format_boolean_value(self):
        """Test boolean value formatting."""
        formatter = PythonUsageDataFormatter()

        assert formatter._format_boolean_value(True) == 'True'
        assert formatter._format_boolean_value(False) == 'False'
        assert formatter._format_boolean_value('true') == 'True'
        assert formatter._format_boolean_value('false') == 'False'
        assert formatter._format_boolean_value('yes') == 'True'
        assert formatter._format_boolean_value('no') == 'False'
        assert formatter._format_boolean_value(1) == 'True'
        assert formatter._format_boolean_value(0) == 'False'

    def test_format_array_value(self):
        """Test array value formatting."""
        formatter = PythonUsageDataFormatter()

        assert formatter._format_array_value(['a', 'b']) == '["a", "b"]'
        assert formatter._format_array_value([1, 2, 3]) == '[1, 2, 3]'
        assert formatter._format_array_value([True, False]) == '[True, False]'
        assert formatter._format_array_value('single') == '["single"]'

    def test_format_object_value(self):
        """Test object value formatting."""
        formatter = PythonUsageDataFormatter()

        assert formatter._format_object_value({'key': 'value'}) == '{"key": "value"}'
        assert formatter._format_object_value('{"valid": "json"}') == '{"valid": "json"}'
        assert formatter._format_object_value('invalid json') == '{"value": "invalid json"}'
        assert formatter._format_object_value(123) == '{"value": "123"}'

    def test_format_value_for_type_all_types(self):
        """Test format_value for all supported types."""
        formatter = PythonUsageDataFormatter()

        assert formatter.format_value('test', 'string') == '"test"'
        assert formatter.format_value(42, 'integer') == '42'
        assert formatter.format_value(3.14, 'decimal') == 'Decimal("3.14")'
        assert formatter.format_value(True, 'boolean') == 'True'
        assert formatter.format_value(['a'], 'array') == '["a"]'
        assert formatter.format_value({'k': 'v'}, 'object') == '{"k": "v"}'
        assert formatter.format_value('test', 'uuid') == '"test"'
        assert formatter.format_value('test', 'unknown') == '"test"'

    def test_getter_methods(self, temp_usage_file, sample_usage_data):
        """Test all getter methods."""
        loader = UsageDataLoader(temp_usage_file)

        assert loader.get_all_usage_data() == sample_usage_data
        assert (
            loader.get_entity_sample_data('User')
            == sample_usage_data['entities']['User']['sample_data']
        )
        assert (
            loader.get_entity_update_data('User')
            == sample_usage_data['entities']['User']['update_data']
        )

    def test_getter_methods_missing_data(self, temp_usage_file):
        """Test getter methods with missing data."""
        loader = UsageDataLoader(temp_usage_file)

        assert loader.get_entity_sample_data('NonExistent') == {}
        assert loader.get_entity_update_data('NonExistent') == {}

    def test_empty_loader_getter_methods(self):
        """Test getter methods on empty loader."""
        loader = UsageDataLoader()

        assert loader.get_all_usage_data() == {}
        assert loader.get_entity_sample_data('User') == {}
        assert loader.get_entity_update_data('User') == {}

    def test_get_filter_value_entity_not_in_data(self, temp_usage_file):
        """Test get_filter_value_for_param when entity_name not in usage data."""
        loader = UsageDataLoader(temp_usage_file)
        result = loader.get_filter_value_for_param('some_param', 'string', 'NonExistentEntity')
        assert result is None

    def test_get_filter_value_param_not_in_filter_values(self, temp_usage_file):
        """Test get_filter_value_for_param when param not in filter_values."""
        loader = UsageDataLoader(temp_usage_file)
        # 'User' entity exists but has no filter_values section
        result = loader.get_filter_value_for_param('nonexistent_param', 'string', 'User')
        assert result is None

    def test_get_filter_value_no_entity_name(self, temp_usage_file):
        """Test get_filter_value_for_param without entity_name returns None."""
        loader = UsageDataLoader(temp_usage_file)
        result = loader.get_filter_value_for_param('some_param', 'string', entity_name=None)
        assert result is None

    def test_get_filter_value_with_filter_values_section(self, tmp_path):
        """Test get_filter_value_for_param returns formatted value from filter_values."""
        usage_data = {
            'entities': {
                'Order': {
                    'sample_data': {'order_id': 'ord-001'},
                    'access_pattern_data': {'order_id': 'ord-002'},
                    'update_data': {'status': 'SHIPPED'},
                    'filter_values': {
                        'excluded_status': 'CANCELLED',
                        'min_total': 25.0,
                    },
                }
            }
        }
        usage_file = tmp_path / 'usage.json'
        usage_file.write_text(json.dumps(usage_data))
        formatter = PythonUsageDataFormatter()
        loader = UsageDataLoader(str(usage_file), formatter=formatter)

        result = loader.get_filter_value_for_param('excluded_status', 'string', 'Order')
        assert result == '"CANCELLED"'

        result = loader.get_filter_value_for_param('min_total', 'decimal', 'Order')
        assert result is not None  # formatted decimal value

    def test_get_filter_value_without_formatter(self):
        """Test get_filter_value_for_param returns None when no formatter."""
        loader = UsageDataLoader()  # No path, no formatter
        result = loader.get_filter_value_for_param('param', 'string', 'Entity')
        assert result is None

    def test_load_usage_data_unexpected_error(self, tmp_path):
        """Test _load_usage_data handles unexpected exceptions (except Exception branch)."""
        usage_file = tmp_path / 'usage.json'
        usage_file.write_text('{}')

        with patch.object(
            file_utils.FileUtils, 'load_json_file', side_effect=RuntimeError('unexpected')
        ):
            loader = UsageDataLoader(str(usage_file))

        assert loader.usage_data == {}
        assert not loader.has_data()
