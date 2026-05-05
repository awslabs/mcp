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

"""Python-specific type mappings."""

from awslabs.dynamodb_mcp_server.repo_generation_tool.core.language_type_mapper import (
    LanguageTypeMappingInterface,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    FieldType,
    ParameterType,
    ReturnType,
)


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
            ParameterType.DECIMAL.value: 'Decimal',
            ParameterType.BOOLEAN.value: 'bool',
            ParameterType.ARRAY.value: 'list[{item_type}]',
            ParameterType.OBJECT.value: 'dict[str, Any]',
            ParameterType.UUID.value: 'str',
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
