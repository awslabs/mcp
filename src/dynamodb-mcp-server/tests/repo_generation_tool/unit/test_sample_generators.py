"""Unit tests for language-specific sample generators."""

import json
import pytest
import tempfile
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.language_sample_generator import (
    LanguageSampleGeneratorInterface,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.generators.sample_generators import (
    SampleValueGenerator,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.languages.python.sample_generators import (
    PythonSampleGenerator,
)
from pathlib import Path


class MockSampleGenerator(LanguageSampleGeneratorInterface):
    """Mock implementation for testing abstract methods."""

    def get_sample_value(self, field_type: str, field_name: str, **kwargs) -> str:
        """Generate a sample value for testing."""
        return f'sample_{field_name}'

    def get_update_value(self, field_type: str, field_name: str, **kwargs) -> str:
        """Generate an update value for testing."""
        return f'updated_{field_name}'

    def get_default_values(self) -> dict[str, str]:
        """Return default values for testing."""
        return {'string': 'test'}

    def get_default_update_values(self) -> dict[str, str]:
        """Return default update values for testing."""
        return {'string': 'updated_test'}

    def get_parameter_value(self, param: dict, entity_name: str, all_entities: dict) -> str | None:
        """Generate a parameter value for testing."""
        return f'param_{param["name"]}'


@pytest.mark.unit
class TestLanguageSampleGeneratorInterface:
    """Test abstract interface methods."""

    def test_abstract_interface_cannot_be_instantiated(self):
        """Test that abstract interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LanguageSampleGeneratorInterface()  # type: ignore[abstract]

    def test_mock_implementation_works(self):
        """Test that concrete implementation works."""
        generator = MockSampleGenerator()

        # Test all abstract methods are implemented
        assert generator.get_sample_value('string', 'test') == 'sample_test'
        assert generator.get_update_value('string', 'test') == 'updated_test'
        assert generator.get_default_values() == {'string': 'test'}
        assert generator.get_default_update_values() == {'string': 'updated_test'}
        assert generator.get_parameter_value({'name': 'test'}, 'Entity', {}) == 'param_test'


@pytest.mark.unit
class TestPythonSampleGenerator:
    """Test Python-specific sample generation."""

    @pytest.fixture
    def generator(self):
        """Create a Python sample generator for testing."""
        return PythonSampleGenerator()

    @pytest.fixture
    def sample_usage_data(self):
        """Sample usage data for testing."""
        return {
            'entities': {
                'User': {
                    'sample_data': {
                        'username': 'realistic_user',
                        'email': 'user@realistic.com',
                        'category': 'electronics',
                    },
                    'access_pattern_data': {
                        'username': 'another_user',
                        'email': 'another@realistic.com',
                        'category': 'books',
                    },
                    'update_data': {'username': 'updated_realistic_user'},
                }
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

    @pytest.fixture
    def generator_with_usage_data(self, temp_usage_file):
        """Create a Python sample generator with usage data."""
        return PythonSampleGenerator(temp_usage_file)

    def test_init_without_usage_data(self):
        """Test initialization without usage data."""
        generator = PythonSampleGenerator()
        assert generator.usage_data_loader is None

    def test_init_with_usage_data(self, temp_usage_file):
        """Test initialization with usage data."""
        generator = PythonSampleGenerator(temp_usage_file)
        assert generator.usage_data_loader is not None
        assert generator.usage_data_loader.has_data()

    def test_init_with_invalid_usage_data(self):
        """Test initialization with invalid usage data path."""
        generator = PythonSampleGenerator('/nonexistent/path.json')
        assert generator.usage_data_loader is not None
        assert not generator.usage_data_loader.has_data()

    def test_get_sample_value_with_usage_data_priority(self, generator_with_usage_data):
        """Test that usage data takes priority over default values."""
        # Should use realistic value from usage data
        result = generator_with_usage_data.get_sample_value(
            'string', 'username', entity_name='User'
        )
        assert result == '"realistic_user"'

        # Should use realistic value from entity sample_data
        result = generator_with_usage_data.get_sample_value(
            'string', 'category', entity_name='User'
        )
        assert result == '"electronics"'

    def test_get_sample_value_fallback_to_defaults(self, generator_with_usage_data):
        """Test fallback to default values when usage data not available."""
        # Should fall back to default pattern matching
        result = generator_with_usage_data.get_sample_value('string', 'user_id')
        assert result == '"user_id123"'

    def test_get_update_value_with_usage_data_priority(self, generator_with_usage_data):
        """Test that usage data takes priority for update values."""
        # Should use realistic update value from usage data
        result = generator_with_usage_data.get_update_value(
            'string', 'username', entity_name='User'
        )
        assert result == '"updated_realistic_user"'

    def test_get_update_value_fallback_to_defaults(self, generator_with_usage_data):
        """Test fallback to default update values when usage data not available."""
        # Should fall back to default update pattern
        result = generator_with_usage_data.get_update_value('string', 'description')
        assert result == '"updated_description"'

    def test_get_parameter_value_with_usage_data(self, generator_with_usage_data):
        """Test parameter value generation with usage data."""
        all_entities = {'User': {'fields': []}}

        # Should use update_data value first (priority over sample_data)
        result = generator_with_usage_data.get_parameter_value(
            {'name': 'username', 'type': 'string'}, 'User', all_entities
        )
        assert result == '"updated_realistic_user"'

    def test_sample_and_update_value_generation(self, generator):
        """Test sample and update value generation for all field types."""
        # Decimal
        assert 'Decimal(' in generator.get_sample_value(
            'decimal', 'price'
        ) and '29.99' in generator.get_sample_value('decimal', 'price')
        assert 'Decimal(' in generator.get_update_value(
            'decimal', 'amount'
        ) and '9.99' in generator.get_update_value('decimal', 'amount')

        # String patterns - sample
        for field, expected in [
            ('user_id', '"user_id123"'),
            ('product_category', '"electronics"'),
            ('status', '"active"'),
            ('country', '"US"'),
            ('city', '"Seattle"'),
            ('price_range', '"mid"'),
        ]:
            assert generator.get_sample_value('string', field) == expected

        # String patterns - update
        assert generator.get_update_value('string', 'username') == '"username_updated"'
        assert generator.get_update_value('string', 'content') == '"This is updated content"'

        # Integer patterns
        assert generator.get_sample_value('integer', 'created_timestamp') == 'int(time.time())'
        assert generator.get_update_value('integer', 'updated_timestamp') == 'int(time.time())'

        # Array with item types
        assert (
            generator.get_sample_value('array', 'tags', item_type='string')
            == '["sample1", "sample2"]'
        )
        assert generator.get_sample_value('array', 'numbers', item_type='integer') == '[1, 2, 3]'
        assert (
            generator.get_update_value('array', 'tags', item_type='string')
            == '["updated1", "updated2", "updated3"]'
        )

        # Fallbacks
        assert generator.get_sample_value('unknown_type', 'test_field') == '"sample_test_field"'
        assert generator.get_update_value('unknown_type', 'test_field') == '"updated_test_field"'
        assert (
            generator.get_sample_value('array', 'items', item_type='unknown')
            == '["sample1", "sample2"]'
        )
        assert (
            generator.get_update_value('array', 'items', item_type='unknown')
            == '["updated1", "updated2"]'
        )

    def test_default_values_structure(self, generator):
        """Test default values and update values dictionary structure."""
        # Test default values
        defaults = generator.get_default_values()
        expected_types = ['string', 'integer', 'decimal', 'boolean', 'array', 'object', 'uuid']
        for field_type in expected_types:
            assert field_type in defaults
        assert 'Decimal(' in defaults['decimal']

        # Test default update values
        update_defaults = generator.get_default_update_values()
        update_expected = ['string', 'integer', 'decimal', 'boolean', 'array', 'object']
        for field_type in update_expected:
            assert field_type in update_defaults
        assert 'Decimal(' in update_defaults['decimal']

    def test_parameter_value_generation(self, generator):
        """Test parameter value generation for all scenarios."""
        all_entities = {'User': {'fields': [{'name': 'user_id', 'type': 'string'}]}}

        # Scalar field match
        assert (
            generator.get_parameter_value(
                {'name': 'user_id', 'type': 'string'}, 'User', all_entities
            )
            == 'created_entities["User"].user_id'
        )

        # Entity types
        assert (
            generator.get_parameter_value(
                {'name': 'user', 'type': 'entity', 'entity_type': 'User'},
                'Order',
                {'User': {}, 'Order': {}},
            )
            == 'created_entities["User"]'
        )
        assert (
            generator.get_parameter_value({'name': 'user', 'type': 'entity'}, 'User', {})
            == 'created_entities["User"]'
        )

        # Complex types
        assert (
            generator.get_parameter_value(
                {'name': 'data', 'type': 'dict'}, 'User', {'User': {'fields': []}}
            )
            == '{}'
        )
        assert (
            generator.get_parameter_value(
                {'name': 'data', 'type': 'object'}, 'User', {'User': {'fields': []}}
            )
            == '{}'
        )
        assert (
            generator.get_parameter_value(
                {'name': 'items', 'type': 'array'}, 'Product', {'Product': {'fields': []}}
            )
            == '[]'
        )
        assert (
            generator.get_parameter_value(
                {'name': 'items', 'type': 'list'}, 'Product', {'Product': {'fields': []}}
            )
            == '[]'
        )

        # Edge cases - unknown parameters return None when generate_fallback=False
        assert (
            generator.get_parameter_value(
                {'name': 'unknown', 'type': 'string'},
                'User',
                all_entities,
                generate_fallback=False,
            )
            is None
        )

        # Unknown parameters generate defaults when generate_fallback=True
        assert (
            generator.get_parameter_value(
                {'name': 'unknown', 'type': 'string'}, 'User', all_entities, generate_fallback=True
            )
            == '"unknown_value"'
        )
        assert (
            generator.get_parameter_value(
                {'name': 'field', 'type': 'string'}, 'NonExistent', {'User': {'fields': []}}
            )
            is None
        )
        assert (
            generator.get_parameter_value(
                {'name': 'field', 'type': 'string'}, 'User', {'User': {}}
            )
            is None
        )

    def test_gsi_sample_value_patterns(self, generator):
        """Test GSI sample value generation for all field patterns."""
        # String patterns
        for field, expected in [
            ('category', '"electronics"'),
            ('status', '"active"'),
            ('country', '"US"'),
            ('city', '"Seattle"'),
            ('price_range', '"mid"'),
            ('user_id', '"user_id123"'),
        ]:
            assert generator.get_gsi_sample_value('string', field) == expected
        assert generator.get_gsi_sample_value('string', 'other_field') == '"sample_other_field"'

        # Other types
        assert generator.get_gsi_sample_value('integer', 'created_timestamp') == '1640995200'
        assert generator.get_gsi_sample_value('integer', 'count') == '42'
        assert generator.get_gsi_sample_value('decimal', 'product_price') == 'Decimal("29.99")'
        assert generator.get_gsi_sample_value('decimal', 'amount') == 'Decimal("3.14")'
        assert generator.get_gsi_sample_value('boolean', 'active') == 'True'
        assert (
            generator.get_gsi_sample_value('array', 'tags', item_type='string')
            == '["sample1", "sample2"]'
        )
        assert (
            generator.get_gsi_sample_value('array', 'numbers', item_type='integer') == '[1, 2, 3]'
        )
        assert (
            generator.get_gsi_sample_value('unknown_type', 'test_field') == '"sample_test_field"'
        )
        assert (
            generator.get_gsi_sample_value('array', 'items', item_type='unknown')
            == '["sample1", "sample2"]'
        )

    def test_get_parameter_value_fallback_to_sample_data(self, temp_usage_file):
        """Test parameter value falls back to sample_data when update_data doesn't exist (lines 261-265)."""
        # Create usage data with only sample_data (no update_data)
        usage_data = {
            'entities': {
                'User': {
                    'sample_data': {'search_term': 'example_search'}
                    # No update_data
                }
            }
        }
        Path(temp_usage_file).write_text(json.dumps(usage_data))

        generator = PythonSampleGenerator(usage_data_path=temp_usage_file)
        # search_term is NOT in entity fields - should use usage_data
        all_entities = {'User': {'fields': [{'name': 'email', 'type': 'string'}]}}

        result = generator.get_parameter_value(
            {'name': 'search_term', 'type': 'string'}, 'User', all_entities
        )

        # Should fall back to sample_data (not update_data since it doesn't exist)
        assert result == '"example_search"'

    def test_get_parameter_value_range_query_lower_bound(self, generator):
        """Test range query parameter generation for lower bounds (lines 284-289)."""
        all_entities = {'Order': {'fields': []}}

        # Test various lower bound parameter names
        lower_bound_params = [
            ('start_date', 'string', '"2024-01-01"'),
            ('min_price', 'integer', '0'),
            ('since_timestamp', 'string', '"2024-01-01"'),
            ('from_date', 'string', '"2024-01-01"'),
            ('lower_bound', 'decimal', 'Decimal("0.00")'),
        ]

        for param_name, param_type, expected in lower_bound_params:
            result = generator.get_parameter_value(
                {'name': param_name, 'type': param_type},
                'Order',
                all_entities,
                generate_fallback=True,
            )
            assert result == expected, (
                f'Failed for {param_name}: expected {expected}, got {result}'
            )

    def test_get_parameter_value_range_query_upper_bound(self, generator):
        """Test range query parameter generation for upper bounds (lines 298-303)."""
        all_entities = {'Order': {'fields': []}}

        # Test various upper bound parameter names
        upper_bound_params = [
            ('end_date', 'string', '"2024-12-31"'),
            ('max_price', 'integer', '9999'),
            ('until_timestamp', 'string', '"2024-12-31"'),
            ('to_date', 'string', '"2024-12-31"'),
            ('upper_bound', 'decimal', 'Decimal("9999.99")'),
        ]

        for param_name, param_type, expected in upper_bound_params:
            result = generator.get_parameter_value(
                {'name': param_name, 'type': param_type},
                'Order',
                all_entities,
                generate_fallback=True,
            )
            assert result == expected, (
                f'Failed for {param_name}: expected {expected}, got {result}'
            )

    def test_get_parameter_value_generic_fallback(self, generator):
        """Test generic fallback for other parameter types (lines 307, 309)."""
        all_entities = {'Product': {'fields': []}}

        # Test generic parameter names that don't match range query patterns
        generic_params = [
            ('category', 'string', '"category_value"'),
            ('quantity', 'integer', '100'),
            ('rating', 'decimal', 'Decimal("100.00")'),
        ]

        for param_name, param_type, expected in generic_params:
            result = generator.get_parameter_value(
                {'name': param_name, 'type': param_type},
                'Product',
                all_entities,
                generate_fallback=True,
            )
            assert result == expected, (
                f'Failed for {param_name}: expected {expected}, got {result}'
            )


@pytest.mark.unit
class TestSampleValueGeneratorIntegration:
    """Test integration of language-agnostic generator with Python implementation."""

    @pytest.fixture
    def generator(self):
        """Create a sample value generator for testing."""
        return SampleValueGenerator(language='python')

    @pytest.fixture
    def sample_usage_data(self):
        """Sample usage data for testing."""
        return {
            'entities': {
                'Product': {
                    'sample_data': {'name': 'Realistic Product Name'},
                    'access_pattern_data': {'name': 'Another Product Name'},
                    'update_data': {'name': 'Updated Product Name'},
                }
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

    @pytest.fixture
    def generator_with_usage_data(self, temp_usage_file):
        """Create a sample value generator with usage data."""
        return SampleValueGenerator(language='python', usage_data_path=temp_usage_file)

    def test_init_with_usage_data_path(self, temp_usage_file):
        """Test initialization with usage data path."""
        generator = SampleValueGenerator(language='python', usage_data_path=temp_usage_file)
        assert generator.usage_data_path == temp_usage_file
        assert generator.language_generator.usage_data_loader is not None

    def test_generate_sample_value_with_kwargs(self, generator_with_usage_data):
        """Test sample value generation with kwargs passed through."""
        result = generator_with_usage_data.generate_sample_value(
            {'type': 'string', 'name': 'name'}, entity_name='Product'
        )
        assert result == '"Realistic Product Name"'

    def test_generate_update_value_with_kwargs(self, generator_with_usage_data):
        """Test update value generation with kwargs passed through."""
        # Should fall back to default since no update data in sample
        result = generator_with_usage_data.generate_update_value(
            {'type': 'string', 'name': 'description'}, entity_name='Product'
        )
        assert result == '"updated_description"'

    def test_get_updatable_field_excludes_gsi_keys(self, generator):
        """Test that get_updatable_field excludes GSI key fields."""
        config = {
            'pk_template': 'USER#{user_id}',
            'sk_template': 'PROFILE#{profile_id}',
            'fields': [
                {'name': 'user_id', 'type': 'string'},
                {'name': 'profile_id', 'type': 'string'},
                {'name': 'gsi_pk_field', 'type': 'string'},
                {'name': 'gsi_sk_field', 'type': 'string'},
                {'name': 'email', 'type': 'string'},
                {'name': 'created_timestamp', 'type': 'integer'},
            ],
            'gsi_mappings': [
                {
                    'name': 'GSI1',
                    'pk_template': 'GSI1PK#{gsi_pk_field}',
                    'sk_template': 'GSI1SK#{gsi_sk_field}',
                }
            ],
        }

        updatable_field = generator.get_updatable_field(config)
        assert updatable_field['name'] == 'email'  # Should skip GSI key fields

    def test_get_updatable_field_excludes_timestamp_fields(self, generator):
        """Test that get_updatable_field excludes timestamp fields."""
        config = {
            'pk_template': 'USER#{user_id}',
            'fields': [
                {'name': 'user_id', 'type': 'string'},
                {'name': 'created_timestamp', 'type': 'integer'},
                {'name': 'updated_timestamp', 'type': 'integer'},
                {'name': 'last_modified_timestamp', 'type': 'integer'},
                {'name': 'email', 'type': 'string'},
            ],
        }

        updatable_field = generator.get_updatable_field(config)
        assert updatable_field['name'] == 'email'  # Should skip timestamp fields

    def test_unsupported_language_error(self):
        """Test error handling for unsupported language."""
        with pytest.raises(ValueError, match='Unsupported language: java'):
            SampleValueGenerator(language='java')

    def test_typescript_not_implemented(self):
        """Test TypeScript generator not yet implemented."""
        with pytest.raises(ValueError, match='TypeScript sample generator not yet implemented'):
            SampleValueGenerator(language='typescript')

    def test_value_generation_delegation(self, generator):
        """Test sample and update value generation delegation."""
        assert 'Decimal(' in generator.generate_sample_value(
            {'type': 'decimal', 'name': 'price'}
        ) and '29.99' in generator.generate_sample_value({'type': 'decimal', 'name': 'price'})
        assert (
            generator.generate_sample_value(
                {'type': 'array', 'name': 'tags', 'item_type': 'string'}
            )
            == '["sample1", "sample2"]'
        )
        assert 'Decimal(' in generator.generate_update_value(
            {'type': 'decimal', 'name': 'amount'}
        ) and '9.99' in generator.generate_update_value({'type': 'decimal', 'name': 'amount'})
        assert (
            generator.generate_update_value(
                {'type': 'array', 'name': 'items', 'item_type': 'integer'}
            )
            == '[10, 20, 30]'
        )

    def test_helper_methods(self, generator):
        """Test helper methods for entity and parameter handling."""
        # get_updatable_field
        config = {
            'pk_template': 'USER#{user_id}',
            'sk_template': 'PROFILE#{profile_id}',
            'fields': [
                {'name': 'user_id', 'type': 'string'},
                {'name': 'profile_id', 'type': 'string'},
                {'name': 'email', 'type': 'string'},
                {'name': 'created_timestamp', 'type': 'integer'},
            ],
        }
        assert generator.get_updatable_field(config)['name'] == 'email'
        assert (
            generator.get_updatable_field(
                {
                    'pk_template': 'USER#{user_id}',
                    'fields': [
                        {'name': 'user_id', 'type': 'string'},
                        {'name': 'created_timestamp', 'type': 'integer'},
                    ],
                }
            )['name']
            == 'created_timestamp'
        )
        assert (
            generator.get_updatable_field({'pk_template': 'USER#{user_id}', 'fields': []}) is None
        )

        # get_all_key_params
        assert generator.get_all_key_params(
            {'pk_template': 'USER#{user_id}', 'sk_template': 'POST#{post_id}#{timestamp}'}
        ) == ['user_id', 'post_id', 'timestamp']

        # get_parameter_value
        assert (
            generator.get_parameter_value(
                {'name': 'user_id', 'type': 'string'},
                'User',
                {'User': {'fields': [{'name': 'user_id', 'type': 'string'}]}},
            )
            == 'created_entities["User"].user_id'
        )

    def test_get_all_key_params_deduplicates_shared_fields(self, generator):
        """Test that get_all_key_params deduplicates when same field is in both PK and SK templates."""
        # Same field in both PK and SK (e.g., pk_template: "REST#{id}", sk_template: "REST#{id}")
        result = generator.get_all_key_params(
            {'pk_template': 'REST#{restaurant_id}', 'sk_template': 'REST#{restaurant_id}'}
        )
        assert result == ['restaurant_id']  # Should appear only once

    def test_get_all_key_params_preserves_unique_fields(self, generator):
        """Test that get_all_key_params preserves unique fields from both templates."""
        result = generator.get_all_key_params(
            {'pk_template': 'USER#{user_id}', 'sk_template': 'ORDER#{order_id}'}
        )
        assert result == ['user_id', 'order_id']

    def test_get_all_key_params_partial_overlap(self, generator):
        """Test dedup with partial overlap between PK and SK params."""
        result = generator.get_all_key_params(
            {
                'pk_template': 'TENANT#{tenant_id}#USER#{user_id}',
                'sk_template': 'DATA#{user_id}#{record_id}',
            }
        )
        # user_id appears in both, should only appear once (from pk_params)
        assert result == ['tenant_id', 'user_id', 'record_id']

    def test_get_parameter_value_uses_filter_values(self, tmp_path):
        """Test that get_parameter_value falls through to filter_values when param not in entity fields."""
        usage_data = {
            'entities': {
                'Order': {
                    'sample_data': {'order_id': 'ord-001', 'customer_id': 'cust-001'},
                    'access_pattern_data': {'order_id': 'ord-002'},
                    'update_data': {'status': 'SHIPPED'},
                    'filter_values': {
                        'excluded_status': 'CANCELLED',
                    },
                }
            }
        }
        usage_file = tmp_path / 'usage.json'
        usage_file.write_text(json.dumps(usage_data))

        generator = PythonSampleGenerator(usage_data_path=str(usage_file))

        entity_config = {
            'entity_type': 'ORDER',
            'pk_template': 'CUST#{customer_id}',
            'sk_template': 'ORDER#{order_id}',
            'fields': [
                {'name': 'customer_id', 'type': 'string', 'required': True},
                {'name': 'order_id', 'type': 'string', 'required': True},
            ],
        }

        # excluded_status is NOT in entity fields — should come from filter_values
        param = {'name': 'excluded_status', 'type': 'string'}
        result = generator.get_parameter_value(
            param, 'Order', {'Order': entity_config}, generate_fallback=False
        )
        assert result == '"CANCELLED"'

    def test_get_parameter_value_filter_value_is_none_falls_through(self, tmp_path):
        """Test that when filter_value is None, falls through to generate_fallback (branch 271->275)."""
        usage_data = {
            'entities': {
                'Order': {
                    'sample_data': {'order_id': 'ord-001'},
                    'access_pattern_data': {'order_id': 'ord-002'},
                    'update_data': {'status': 'SHIPPED'},
                    'filter_values': {},  # Empty — param not in filter_values
                }
            }
        }
        usage_file = tmp_path / 'usage.json'
        usage_file.write_text(json.dumps(usage_data))

        generator = PythonSampleGenerator(usage_data_path=str(usage_file))
        entity_config = {
            'entity_type': 'ORDER',
            'pk_template': 'CUST#{customer_id}',
            'sk_template': 'ORDER#{order_id}',
            'fields': [
                {'name': 'customer_id', 'type': 'string', 'required': True},
                {'name': 'order_id', 'type': 'string', 'required': True},
            ],
        }

        # param not in entity fields and not in filter_values — with generate_fallback=True
        # should return a generated default, not None
        param = {'name': 'some_threshold', 'type': 'decimal'}
        result = generator.get_parameter_value(
            param, 'Order', {'Order': entity_config}, generate_fallback=True
        )
        assert result is not None  # fallback generated

    def test_get_gsi_sample_value_integer_no_timestamp(self):
        """Test get_gsi_sample_value for integer field without timestamp (branch 99->114)."""
        generator = PythonSampleGenerator()
        result = generator.get_gsi_sample_value('integer', 'score')
        assert result == '42'

    def test_get_gsi_sample_value_decimal_no_price(self):
        """Test get_gsi_sample_value for decimal field without price (branch 102->114)."""
        generator = PythonSampleGenerator()
        result = generator.get_gsi_sample_value('decimal', 'rating')
        assert result == 'Decimal("3.14")'

    def test_get_update_value_array_unknown_item_type(self):
        """Test get_update_value for array with unknown item_type falls back (branch 140->150)."""
        generator = PythonSampleGenerator()
        result = generator.get_update_value('array', 'items', item_type='object')
        assert result == '["updated1", "updated2"]'
