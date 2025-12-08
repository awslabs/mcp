"""Python-specific type mappings"""

from awslabs.dynamodb_mcp_server.repo_generation_tool.core.language_type_mapper import (
    LanguageTypeMappingInterface,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    FieldType,
    ParameterType,
    ReturnType,
)
from typing import Dict


class PythonTypeMappings(LanguageTypeMappingInterface):
    """Python-specific type mappings - implements all required abstract properties"""

    @property
    def field_type_mappings(self) -> dict[str, str]:
        """Python field type mappings using modern Python 3.10+ syntax"""
        return {
            FieldType.STRING.value: 'str',
            FieldType.INTEGER.value: 'int',
            FieldType.DECIMAL.value: 'Decimal',
            FieldType.BOOLEAN.value: 'bool',
            FieldType.ARRAY.value: 'list[{item_type}]',
            FieldType.OBJECT.value: 'dict[str, Any]',
            FieldType.UUID.value: 'str',  # For now, could be uuid.UUID in future
        }

    @property
    def return_type_mappings(self) -> dict[str, str]:
        """Python return type mappings using Python 3.10+ union syntax"""
        return {
            ReturnType.SINGLE_ENTITY.value: '{entity} | None',
            ReturnType.ENTITY_LIST.value: 'list[{entity}]',
            ReturnType.SUCCESS_FLAG.value: 'bool',
            ReturnType.MIXED_DATA.value: 'dict',
            ReturnType.VOID.value: 'None',
        }

    @property
    def parameter_type_mappings(self) -> dict[str, str]:
        """Python parameter type mappings"""
        return {
            ParameterType.STRING.value: 'str',
            ParameterType.INTEGER.value: 'int',
            ParameterType.BOOLEAN.value: 'bool',
            ParameterType.ENTITY.value: '{entity_type}',
        }

    # Optional: Language-specific custom methods
    def get_array_type(self, item_type: str) -> str:
        """Python-specific array type formatting"""
        return f'list[{item_type}]'

    def get_optional_type(self, base_type: str) -> str:
        """Python-specific optional type formatting"""
        return f'{base_type} | None'

    def supports_union_syntax(self) -> bool:
        """Python 3.10+ supports modern union syntax"""
        return True
