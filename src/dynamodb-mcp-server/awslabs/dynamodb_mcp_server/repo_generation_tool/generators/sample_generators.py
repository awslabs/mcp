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

"""Language-agnostic sample data generation for usage examples."""

from awslabs.dynamodb_mcp_server.repo_generation_tool.core.key_template_parser import (
    KeyTemplateParser,
)
from typing import Any


class SampleValueGenerator:
    """Language-agnostic sample value generator that delegates to language-specific implementations."""

    def __init__(self, language: str = 'python'):
        """Initialize the sample value generator for a specific language."""
        self.language = language
        self.language_generator = self._load_language_generator(language)
        self.template_parser = KeyTemplateParser()

    def _load_language_generator(self, language: str):
        """Load language-specific sample generator."""
        if language == 'python':
            from awslabs.dynamodb_mcp_server.repo_generation_tool.languages.python.sample_generators import (
                PythonSampleGenerator,
            )

            return PythonSampleGenerator()
        elif language == 'typescript':
            # Future implementation
            # from awslabs.dynamodb_mcp_server.repo_generation_tool.languages.typescript.sample_generators import (
            #     TypeScriptSampleGenerator,
            # )
            # return TypeScriptSampleGenerator()
            raise ValueError('TypeScript sample generator not yet implemented')
        else:
            supported_languages = ['python']  # Add as implemented
            raise ValueError(f'Unsupported language: {language}. Supported: {supported_languages}')

    def generate_sample_value(self, field: dict[str, Any]) -> str:
        """Generate sample value for field using language-specific generator."""
        field_type = field['type']
        field_name = field['name']

        # Handle array fields with item_type
        if field_type == 'array':
            item_type = field.get('item_type', 'string')
            return self.language_generator.get_sample_value(
                'array', field_name, item_type=item_type
            )

        return self.language_generator.get_sample_value(field_type, field_name)

    def generate_update_value(self, field: dict[str, Any]) -> str:
        """Generate update value for field using language-specific generator."""
        field_type = field['type']
        field_name = field['name']

        # Handle array fields with item_type
        if field_type == 'array':
            item_type = field.get('item_type', 'string')
            return self.language_generator.get_update_value(
                'array', field_name, item_type=item_type
            )

        return self.language_generator.get_update_value(field_type, field_name)

    def get_updatable_field(self, entity_config: dict[str, Any]) -> dict[str, Any] | None:
        """Get the first non-key field that can be updated."""
        # Extract parameters dynamically from templates (unified approach)
        pk_params = self.template_parser.extract_parameters(entity_config.get('pk_template', ''))
        sk_params = self.template_parser.extract_parameters(entity_config.get('sk_template', ''))
        key_fields = set(pk_params + sk_params)

        for field in entity_config['fields']:
            field_name = field['name']
            # Skip key fields and timestamp fields (usually auto-managed)
            if field_name not in key_fields and 'timestamp' not in field_name.lower():
                return field

        # Fallback to first non-key field if no suitable field found
        for field in entity_config['fields']:
            field_name = field['name']
            if field_name not in key_fields:
                return field

        return None

    def get_all_key_params(self, entity_config: dict[str, Any]) -> list[str]:
        """Get all key parameters (PK + SK) for an entity using the unified template approach.

        Args:
            entity_config: Entity configuration with pk_template and sk_template

        Returns:
            List of all key parameter names
        """
        pk_params = self.template_parser.extract_parameters(entity_config.get('pk_template', ''))
        sk_params = self.template_parser.extract_parameters(entity_config.get('sk_template', ''))
        return pk_params + sk_params

    def get_parameter_value(
        self, param: dict[str, Any], entity_name: str, all_entities: dict
    ) -> str:
        """Generate parameter value for access pattern testing using language-specific generator.

        This method delegates to the language-specific implementation to ensure
        proper syntax for the target programming language.

        Args:
            param: Parameter definition with 'name' and 'type'
            entity_name: Name of the entity this access pattern belongs to
            all_entities: Dictionary of all entity configurations from schema

        Returns:
            Language-specific string representation of the parameter value
        """
        return self.language_generator.get_parameter_value(param, entity_name, all_entities)
