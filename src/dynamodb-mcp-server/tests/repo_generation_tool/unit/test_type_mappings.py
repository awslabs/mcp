"""Unit tests for TypeMapper and language-specific type mappings."""

import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    FieldType,
    ParameterType,
    ReturnType,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.type_mappings import (
    TypeMapper,
    map_python_type,
)


@pytest.mark.unit
class TestTypeMapper:
    """Unit tests for TypeMapper class - fast, isolated tests."""

    @pytest.fixture
    def python_mapper(self):
        """Create a TypeMapper for Python."""
        return TypeMapper('python')

    def test_python_mapper_initialization(self, python_mapper):
        """Test that Python TypeMapper initializes correctly."""
        assert python_mapper.language == 'python'
        assert python_mapper.mapping is not None
        assert len(python_mapper.mapping) > 0

    def test_type_mappings_comprehensive(self, python_mapper):
        """Test all type mapping functionality comprehensively."""
        # Basic field types
        basic_types = [
            ('string', 'str'),
            ('integer', 'int'),
            ('decimal', 'Decimal'),
            ('boolean', 'bool'),
            ('uuid', 'str'),
        ]
        for input_type, expected in basic_types:
            result = python_mapper.map_type(input_type)
            assert result == expected, f'Expected {input_type} -> {expected}, got {result}'

        # Array types
        assert python_mapper.map_type('array', item_type='str') == 'list[str]'
        assert python_mapper.map_type('array', item_type='int') == 'list[int]'

        # Return types
        return_cases = [
            ('single_entity', 'User', 'User | None'),
            ('entity_list', 'Post', 'list[Post]'),
            ('success_flag', None, 'bool'),
            ('void', None, 'None'),
        ]
        for return_type, entity_name, expected in return_cases:
            result = python_mapper.map_return_type(return_type, entity_name)
            assert result == expected

    def test_field_and_parameter_mappings(self, python_mapper):
        """Test mapping field and parameter definitions to types."""
        # Field mappings
        field = {'type': 'string', 'required': True}
        assert python_mapper.map_field_type(field) == 'str'

        array_field = {'type': 'array', 'item_type': 'string', 'required': True}
        assert python_mapper.map_field_type(array_field) == 'list[str]'

        # Parameter mappings
        param = {'type': 'string'}
        assert python_mapper.map_parameter_type(param) == 'str'

        entity_param = {'type': 'entity', 'entity_type': 'User'}
        assert python_mapper.map_parameter_type(entity_param) == 'User'

    def test_unsupported_language_raises_error(self):
        """Test that unsupported language raises appropriate error."""
        with pytest.raises(ValueError, match='Unsupported language'):
            TypeMapper('invalid_language')

    def test_language_support_and_fallbacks(self):
        """Test language support, validation, and fallback behavior."""
        # Python validation and fallbacks
        mapper = TypeMapper('python')
        assert mapper is not None
        assert mapper.map_type('unknown_type') == 'Any'

        # Test TypeScript error handling (unsupported language)
        with pytest.raises(ValueError, match='Unsupported language'):
            TypeMapper('typescript')

    def test_edge_cases_and_missing_data(self):
        """Test edge cases with missing template variables and data."""
        mapper = TypeMapper('python')

        # Missing template variables should still return valid results
        assert mapper.map_type('array') is not None
        assert mapper.map_field_type({'type': 'array'}) is not None
        assert mapper.map_return_type('single_entity') is not None
        assert mapper.map_parameter_type({'type': 'entity'}) is not None

    def test_validation_and_utility_methods(self):
        """Test validation methods, supported types, and convenience functions."""
        mapper = TypeMapper('python')

        # Validation methods
        assert mapper.validate_field_type('string') is True
        assert mapper.validate_return_type('single_entity') is True
        assert mapper.validate_parameter_type('string') is True
        assert mapper.validate_field_type('invalid_type') is False
        assert mapper.validate_return_type('invalid_return') is False
        assert mapper.validate_parameter_type('invalid_param') is False

        # Supported types methods
        field_types = mapper.get_supported_field_types()
        assert isinstance(field_types, list) and len(field_types) > 0 and 'string' in field_types

        return_types = mapper.get_supported_return_types()
        assert (
            isinstance(return_types, list)
            and len(return_types) > 0
            and 'single_entity' in return_types
        )

        param_types = mapper.get_supported_parameter_types()
        assert isinstance(param_types, list) and len(param_types) > 0 and 'string' in param_types

        # Convenience function
        assert map_python_type('string') == 'str'
        assert map_python_type('array', item_type='int') == 'list[int]'
        assert map_python_type('unknown_type') == 'Any'


@pytest.mark.unit
class TestLanguageTypeMappingInterface:
    """Unit tests for the abstract base class and validation."""

    def test_all_mappings_property(self):
        """Test that all_mappings combines all mapping types."""
        from awslabs.dynamodb_mcp_server.repo_generation_tool.languages.python.type_mappings import (
            PythonTypeMappings,
        )

        python_mappings = PythonTypeMappings()
        all_mappings = python_mappings.all_mappings

        # Should contain mappings from all three categories
        assert FieldType.STRING.value in all_mappings
        assert ReturnType.SINGLE_ENTITY.value in all_mappings
        assert ParameterType.STRING.value in all_mappings

    def test_get_language_name(self):
        """Test language name extraction from class name."""
        from awslabs.dynamodb_mcp_server.repo_generation_tool.languages.python.type_mappings import (
            PythonTypeMappings,
        )

        python_mappings = PythonTypeMappings()
        assert python_mappings.get_language_name() == 'python'


@pytest.mark.unit
class TestPythonTypeMappings:
    """Unit tests for Python-specific type mappings."""

    @pytest.fixture
    def python_mappings(self):
        """Create PythonTypeMappings instance."""
        from awslabs.dynamodb_mcp_server.repo_generation_tool.languages.python.type_mappings import (
            PythonTypeMappings,
        )

        return PythonTypeMappings()

    def test_python_specific_methods(self, python_mappings):
        """Test Python-specific helper methods."""
        # Test array type formatting
        array_type = python_mappings.get_array_type('str')
        assert array_type == 'list[str]'

        # Test optional type formatting
        optional_type = python_mappings.get_optional_type('User')
        assert optional_type == 'User | None'

        # Test union syntax support
        assert python_mappings.supports_union_syntax() is True
