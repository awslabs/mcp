"""Unit tests for LanguageTypeMappingInterface."""

import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.language_type_mapper import (
    LanguageTypeMappingInterface,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    FieldType,
    ParameterType,
    ReturnType,
)


class MockTypeMappingImplementation(LanguageTypeMappingInterface):
    """Test implementation of LanguageTypeMappingInterface for testing."""

    def __init__(self, complete_mappings=True):
        """Initialize mock type mapping implementation."""
        self._complete_mappings = complete_mappings

    @property
    def field_type_mappings(self):
        """Return field type mappings for testing."""
        if self._complete_mappings:
            return {
                'string': 'str',
                'integer': 'int',
                'decimal': 'Decimal',
                'boolean': 'bool',
                'array': 'list',
                'object': 'dict',
                'uuid': 'str',
            }
        return {'string': 'str', 'integer': 'int'}

    @property
    def return_type_mappings(self):
        """Return return type mappings for testing."""
        if self._complete_mappings:
            return {
                'single_entity': 'Optional[Entity]',
                'entity_list': 'list[Entity]',
                'success_flag': 'bool',
                'mixed_data': 'dict',
                'void': 'None',
            }
        return {'single_entity': 'Optional[Entity]', 'entity_list': 'list[Entity]'}

    @property
    def parameter_type_mappings(self):
        """Return parameter type mappings for testing."""
        if self._complete_mappings:
            return {
                'string': 'param_str',
                'integer': 'param_int',
                'decimal': 'param_decimal',
                'boolean': 'param_bool',
                'array': 'param_list',
                'object': 'param_dict',
                'uuid': 'param_uuid',
                'entity': 'Entity',
            }
        return {'string': 'param_str'}


class IncompleteFieldTypeMappings(LanguageTypeMappingInterface):
    """Test class with incomplete field type mappings."""

    @property
    def field_type_mappings(self):
        """Return incomplete field type mappings."""
        return {'string': 'str'}

    @property
    def return_type_mappings(self):
        """Return complete return type mappings."""
        return {rt.value: f'TestReturn_{rt.value}' for rt in ReturnType}

    @property
    def parameter_type_mappings(self):
        """Return complete parameter type mappings."""
        return {pt.value: f'TestParam_{pt.value}' for pt in ParameterType}


class IncompleteReturnTypeMappings(LanguageTypeMappingInterface):
    """Test class with incomplete return type mappings."""

    @property
    def field_type_mappings(self):
        """Return complete field type mappings."""
        return {ft.value: f'TestField_{ft.value}' for ft in FieldType}

    @property
    def return_type_mappings(self):
        """Return incomplete return type mappings."""
        return {'single_entity': 'Entity'}

    @property
    def parameter_type_mappings(self):
        """Return complete parameter type mappings."""
        return {pt.value: f'TestParam_{pt.value}' for pt in ParameterType}


class IncompleteParameterTypeMappings(LanguageTypeMappingInterface):
    """Test class with incomplete parameter type mappings."""

    @property
    def field_type_mappings(self):
        """Return complete field type mappings."""
        return {ft.value: f'TestField_{ft.value}' for ft in FieldType}

    @property
    def return_type_mappings(self):
        """Return complete return type mappings."""
        return {rt.value: f'TestReturn_{rt.value}' for rt in ReturnType}

    @property
    def parameter_type_mappings(self):
        """Return incomplete parameter type mappings."""
        return {'string': 'str'}


@pytest.mark.unit
class TestLanguageTypeMappingInterface:
    """Unit tests for LanguageTypeMappingInterface concrete methods."""

    @pytest.fixture
    def complete_mapping(self):
        """Create a complete type mapping implementation for testing."""
        return MockTypeMappingImplementation(complete_mappings=True)

    def test_all_mappings_combines_all_types(self, complete_mapping):
        """Test that all_mappings combines field, return, and parameter mappings with correct precedence."""
        all_mappings = complete_mapping.all_mappings
        assert 'decimal' in all_mappings
        assert 'single_entity' in all_mappings
        assert 'entity' in all_mappings
        assert all_mappings['decimal'] == 'param_decimal'  # Parameter mappings take precedence
        assert all_mappings['single_entity'] == 'Optional[Entity]'
        assert all_mappings['entity'] == 'Entity'
        # Verify parameter mappings take precedence for overlapping keys
        assert all_mappings['string'] == 'param_str'
        assert all_mappings['integer'] == 'param_int'

    def test_validate_completeness_success(self, complete_mapping):
        """Test that validate_completeness passes for complete mappings."""
        complete_mapping.validate_completeness()

    def test_validate_completeness_missing_field_types(self):
        """Test that validate_completeness raises error for missing field types."""
        incomplete_mapping = IncompleteFieldTypeMappings()
        with pytest.raises(ValueError) as exc_info:
            incomplete_mapping.validate_completeness()
        error_message = str(exc_info.value)
        assert 'Missing field type mappings' in error_message
        assert 'IncompleteFieldTypeMappings' in error_message

    def test_validate_completeness_missing_return_types(self):
        """Test that validate_completeness raises error for missing return types."""
        incomplete_mapping = IncompleteReturnTypeMappings()
        with pytest.raises(ValueError) as exc_info:
            incomplete_mapping.validate_completeness()
        error_message = str(exc_info.value)
        assert 'Missing return type mappings' in error_message
        assert 'IncompleteReturnTypeMappings' in error_message

    def test_validate_completeness_missing_parameter_types(self):
        """Test that validate_completeness raises error for missing parameter types."""
        incomplete_mapping = IncompleteParameterTypeMappings()
        with pytest.raises(ValueError) as exc_info:
            incomplete_mapping.validate_completeness()
        error_message = str(exc_info.value)
        assert 'Missing parameter type mappings' in error_message
        assert 'IncompleteParameterTypeMappings' in error_message

    def test_get_language_name_scenarios(self):
        """Test that get_language_name derives name from class name correctly."""

        class PythonTypeMappings(MockTypeMappingImplementation):
            pass

        assert PythonTypeMappings().get_language_name() == 'python'

        class CustomMapper(MockTypeMappingImplementation):
            pass

        assert CustomMapper().get_language_name() == 'custommapper'

    def test_abstract_properties_coverage(self, complete_mapping):
        """Test that all abstract properties are implemented and accessible."""
        assert complete_mapping.field_type_mappings is not None
        assert complete_mapping.return_type_mappings is not None
        assert complete_mapping.parameter_type_mappings is not None
