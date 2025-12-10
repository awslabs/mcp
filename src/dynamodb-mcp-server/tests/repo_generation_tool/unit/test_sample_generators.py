"""Unit tests for language-specific sample generators."""

import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.language_sample_generator import (
    LanguageSampleGeneratorInterface,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.generators.sample_generators import (
    SampleValueGenerator,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.languages.python.sample_generators import (
    PythonSampleGenerator,
)


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

    def get_parameter_value(self, param: dict, entity_name: str, all_entities: dict) -> str:
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

        # Edge cases
        assert (
            generator.get_parameter_value(
                {'name': 'unknown', 'type': 'string'}, 'User', all_entities
            )
            == '""'
        )
        assert (
            generator.get_parameter_value(
                {'name': 'field', 'type': 'string'}, 'NonExistent', {'User': {'fields': []}}
            )
            == '""'
        )
        assert (
            generator.get_parameter_value(
                {'name': 'field', 'type': 'string'}, 'User', {'User': {}}
            )
            == '""'
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


@pytest.mark.unit
class TestSampleValueGeneratorIntegration:
    """Test integration of language-agnostic generator with Python implementation."""

    @pytest.fixture
    def generator(self):
        """Create a sample value generator for testing."""
        return SampleValueGenerator(language='python')

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
