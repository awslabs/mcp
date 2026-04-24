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

"""Language-specific type mappings for code generation."""

from awslabs.dynamodb_mcp_server.repo_generation_tool.core.language_type_mapper import (
    LanguageTypeMappingInterface,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    FieldType,
    ParameterType,
    ReturnType,
    get_enum_values,
    is_valid_enum_value,
)
from typing import Any


class TypeMapper:
    """Maps generic types to language-specific types with validation."""

    def __init__(self, language: str = 'python'):
        """Initialize the type mapper for a specific language."""
        self.language = language
        self.language_mappings = self._load_language_mappings(language)

        # Validate completeness at initialization
        self.language_mappings.validate_completeness()

        # Get the combined mappings dictionary
        self.mapping = self.language_mappings.all_mappings

    def _load_language_mappings(self, language: str) -> LanguageTypeMappingInterface:
        """Dynamically load and validate language-specific mappings."""
        if language == 'python':
            from awslabs.dynamodb_mcp_server.repo_generation_tool.languages.python.type_mappings import (
                PythonTypeMappings,
            )

            return PythonTypeMappings()
        else:
            supported_languages = ['python']
            raise ValueError(f'Unsupported language: {language}. Supported: {supported_languages}')

    def map_type(self, generic_type: str, **kwargs) -> str:
        """Map a generic type to language-specific type."""
        if generic_type not in self.mapping:
            return 'Any' if self.language == 'python' else 'any'

        type_template = self.mapping[generic_type]

        # Handle templated types (e.g., List[str], Optional[User])
        try:
            return type_template.format(**kwargs)
        except KeyError:
            # If template variables are missing, return the base type
            return type_template

    def map_field_type(self, field: dict[str, Any]) -> str:
        """Map a field definition to language-specific type."""
        field_type = field['type']

        if field_type == 'array':
            item_type = self.map_type(field.get('item_type', 'string'))
            return self.map_type('array', item_type=item_type)

        return self.map_type(field_type)

    def map_return_type(self, return_type: str, entity_name: str = None) -> str:
        """Map a return type to language-specific type."""
        if entity_name:
            return self.map_type(return_type, entity=entity_name)
        return self.map_type(return_type)

    def map_parameter_type(self, param: dict[str, Any]) -> str:
        """Map a parameter definition to language-specific type."""
        param_type = param['type']

        if param_type == ParameterType.ENTITY.value:
            entity_type = param.get('entity_type', 'Any')
            return self.map_type(param_type, entity_type=entity_type)

        if param_type == ParameterType.ARRAY.value:
            item_type = self.map_type(param.get('item_type', 'string'))
            return self.map_type('array', item_type=item_type)

        return self.map_type(param_type)

    def validate_field_type(self, field_type: str) -> bool:
        """Validate that a field type is supported."""
        return is_valid_enum_value(field_type, FieldType)

    def validate_return_type(self, return_type: str) -> bool:
        """Validate that a return type is supported."""
        return is_valid_enum_value(return_type, ReturnType)

    def validate_parameter_type(self, param_type: str) -> bool:
        """Validate that a parameter type is supported."""
        return is_valid_enum_value(param_type, ParameterType)

    def get_supported_field_types(self) -> list[str]:
        """Get list of supported field types."""
        return get_enum_values(FieldType)

    def get_supported_return_types(self) -> list[str]:
        """Get list of supported return types."""
        return get_enum_values(ReturnType)

    def get_supported_parameter_types(self) -> list[str]:
        """Get list of supported parameter types."""
        return get_enum_values(ParameterType)


# Convenience function for Python (default)
def map_python_type(generic_type: str, **kwargs) -> str:
    """Quick function to map to Python types."""
    mapper = TypeMapper('python')
    return mapper.map_type(generic_type, **kwargs)
