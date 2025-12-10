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
        self._complete_mappings = complete_mappings

    @property
    def field_type_mappings(self):
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
        if self._complete_mappings:
            return {
                'string': 'param_str',
                'integer': 'param_int',
                'boolean': 'param_bool',
                'entity': 'Entity',
            }
        return {'string': 'param_str'}


class IncompleteFieldTypeMappings(LanguageTypeMappingInterface):
    @property
    def field_type_mappings(self):
        return {'string': 'str'}

    @property
    def return_type_mappings(self):
        return {rt.value: f'TestReturn_{rt.value}' for rt in ReturnType}

    @property
    def parameter_type_mappings(self):
        return {pt.value: f'TestParam_{pt.value}' for pt in ParameterType}


class IncompleteReturnTypeMappings(LanguageTypeMappingInterface):
    @property
    def field_type_mappings(self):
        return {ft.value: f'TestField_{ft.value}' for ft in FieldType}

    @property
    def return_type_mappings(self):
        return {'single_entity': 'Entity'}

    @property
    def parameter_type_mappings(self):
        return {pt.value: f'TestParam_{pt.value}' for pt in ParameterType}


class IncompleteParameterTypeMappings(LanguageTypeMappingInterface):
    @property
    def field_type_mappings(self):
        return {ft.value: f'TestField_{ft.value}' for ft in FieldType}

    @property
    def return_type_mappings(self):
        return {rt.value: f'TestReturn_{rt.value}' for rt in ReturnType}

    @property
    def parameter_type_mappings(self):
        return {'string': 'str'}


@pytest.mark.unit
class TestLanguageTypeMappingInterface:
    """Unit tests for LanguageTypeMappingInterface concrete methods."""

    @pytest.fixture
    def complete_mapping(self):
        return MockTypeMappingImplementation(complete_mappings=True)

    def test_all_mappings_combines_all_types(self, complete_mapping):
        """Test that all_mappings combines field, return, and parameter mappings with correct precedence."""
        all_mappings = complete_mapping.all_mappings
        assert 'decimal' in all_mappings
        assert 'single_entity' in all_mappings
        assert 'entity' in all_mappings
        assert all_mappings['decimal'] == 'Decimal'
        assert all_mappings['single_entity'] == 'Optional[Entity]'
        assert all_mappings['entity'] == 'Entity'
        # Verify parameter mappings take precedence for overlapping keys
        assert all_mappings['string'] == 'param_str'
        assert all_mappings['integer'] == 'param_int'

    def test_validate_completeness_success(self, complete_mapping):
        complete_mapping.validate_completeness()

    def test_validate_completeness_missing_field_types(self):
        incomplete_mapping = IncompleteFieldTypeMappings()
        with pytest.raises(ValueError) as exc_info:
            incomplete_mapping.validate_completeness()
        error_message = str(exc_info.value)
        assert 'Missing field type mappings' in error_message
        assert 'IncompleteFieldTypeMappings' in error_message

    def test_validate_completeness_missing_return_types(self):
        incomplete_mapping = IncompleteReturnTypeMappings()
        with pytest.raises(ValueError) as exc_info:
            incomplete_mapping.validate_completeness()
        error_message = str(exc_info.value)
        assert 'Missing return type mappings' in error_message
        assert 'IncompleteReturnTypeMappings' in error_message

    def test_validate_completeness_missing_parameter_types(self):
        incomplete_mapping = IncompleteParameterTypeMappings()
        with pytest.raises(ValueError) as exc_info:
            incomplete_mapping.validate_completeness()
        error_message = str(exc_info.value)
        assert 'Missing parameter type mappings' in error_message
        assert 'IncompleteParameterTypeMappings' in error_message

    def test_get_language_name_scenarios(self):
        class PythonTypeMappings(MockTypeMappingImplementation):
            pass

        assert PythonTypeMappings().get_language_name() == 'python'

        class CustomMapper(MockTypeMappingImplementation):
            pass

        assert CustomMapper().get_language_name() == 'custommapper'

    def test_abstract_properties_coverage(self, complete_mapping):
        assert complete_mapping.field_type_mappings is not None
        assert complete_mapping.return_type_mappings is not None
        assert complete_mapping.parameter_type_mappings is not None
