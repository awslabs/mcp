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

"""Python-specific sample value generation."""

from awslabs.dynamodb_mcp_server.repo_generation_tool.core.language_sample_generator import (
    LanguageSampleGeneratorInterface,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.usage_data_loader import (
    UsageDataLoader,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.languages.python.usage_data_formatter import (
    PythonUsageDataFormatter,
)
from typing import Optional


class PythonSampleGenerator(LanguageSampleGeneratorInterface):
    """Python-specific sample value generation"""

    def __init__(self, usage_data_path: Optional[str] = None):
        """Initialize with optional usage data JSON file for realistic sample data."""
        if usage_data_path:
            formatter = PythonUsageDataFormatter()
            self.usage_data_loader = UsageDataLoader(usage_data_path, formatter)
        else:
            self.usage_data_loader = None

    def get_default_values(self) -> dict[str, str]:
        """Python-specific default sample values"""
        return {
            'string': '"sample_{field_name}"',
            'integer': '42',
            'decimal': 'Decimal("3.14")',  # Python-specific
            'boolean': 'True',
            'array': '["sample1", "sample2"]',
            'object': '{{"key": "value"}}',  # Escaped braces for .format()
            'uuid': '"550e8400-e29b-41d4-a716-446655440000"',
        }

    def get_default_update_values(self) -> dict[str, str]:
        """Python-specific default update values"""
        return {
            'string': '"updated_{field_name}"',
            'integer': '99',
            'decimal': 'Decimal("9.99")',  # Python-specific
            'boolean': 'False',
            'array': '["updated1", "updated2"]',
            'object': '{{"updated_key": "updated_value"}}',  # Escaped braces for .format()
        }

    def get_sample_value(self, field_type: str, field_name: str, **kwargs) -> str:
        """Generate Python-specific sample value"""
        # Try to get realistic value from usage data first
        if self.usage_data_loader and self.usage_data_loader.has_data():
            entity_name = kwargs.get('entity_name')
            use_access_pattern_data = kwargs.get('use_access_pattern_data', False)
            realistic_value = self.usage_data_loader.get_sample_value_for_field(
                field_name,
                field_type,
                entity_name,
                use_access_pattern_data=use_access_pattern_data,
            )
            if realistic_value is not None:
                return realistic_value

        # Fall back to existing logic
        defaults = self.get_default_values()

        # Handle special cases based on field name patterns
        field_name_lower = field_name.lower()

        if field_type == 'string':
            # GSI-aware sample values for common field names
            if 'category' in field_name_lower:
                return '"electronics"'
            elif 'status' in field_name_lower:
                return '"active"'
            elif 'country' in field_name_lower:
                return '"US"'
            elif 'city' in field_name_lower:
                return '"Seattle"'
            elif 'price_range' in field_name_lower:
                return '"mid"'
            elif 'id' in field_name_lower:
                return f'"{field_name}123"'
        elif field_type == 'integer':
            if 'timestamp' in field_name_lower or 'time' in field_name_lower:
                return 'int(time.time())'
        elif field_type == 'decimal':
            if 'price' in field_name_lower:
                return 'Decimal("29.99")'
        elif field_type == 'array':
            item_type = kwargs.get('item_type', 'string')
            if item_type == 'string':
                return '["sample1", "sample2"]'
            elif item_type == 'integer':
                return '[1, 2, 3]'
            # Fall back to string array for unknown item types
            return '["sample1", "sample2"]'

        # Return default value for the field type, or fallback
        template = defaults.get(field_type, f'"sample_{field_name}"')
        return template.format(field_name=field_name)

    def get_update_value(self, field_type: str, field_name: str, **kwargs) -> str:
        """Generate Python-specific update value"""
        # Try to get realistic update value from usage data first
        if self.usage_data_loader and self.usage_data_loader.has_data():
            entity_name = kwargs.get('entity_name')
            realistic_value = self.usage_data_loader.get_update_value_for_field(
                field_name, field_type, entity_name
            )
            if realistic_value is not None:
                return realistic_value

        # Fall back to existing logic
        defaults = self.get_default_update_values()

        # Handle special cases
        field_name_lower = field_name.lower()

        if field_type == 'string':
            if 'username' in field_name_lower:
                return f'"{field_name}_updated"'
            elif 'content' in field_name_lower:
                return '"This is updated content"'
        elif field_type == 'integer':
            if 'timestamp' in field_name_lower:
                return 'int(time.time())'
        elif field_type == 'array':
            item_type = kwargs.get('item_type', 'string')
            if item_type == 'string':
                return '["updated1", "updated2", "updated3"]'
            elif item_type == 'integer':
                return '[10, 20, 30]'
            return '["updated1", "updated2"]'

        template = defaults.get(field_type, f'"updated_{field_name}"')
        return template.format(field_name=field_name)

    def get_gsi_sample_value(self, field_type: str, field_name: str, **kwargs) -> str:
        """Generate Python-specific sample value for GSI fields with consistent formatting.

        Args:
            field_type: The type of field
            field_name: The name of the field
            **kwargs: Additional parameters

        Returns:
            Python-formatted sample value for GSI usage
        """
        field_name_lower = field_name.lower()

        # Generate context-appropriate sample values for GSI fields
        if field_type == 'string':
            if 'category' in field_name_lower:
                return '"electronics"'
            elif 'status' in field_name_lower:
                return '"active"'
            elif 'country' in field_name_lower:
                return '"US"'
            elif 'city' in field_name_lower:
                return '"Seattle"'
            elif 'price_range' in field_name_lower:
                return '"mid"'
            elif 'id' in field_name_lower:
                return f'"{field_name}123"'
            else:
                return f'"sample_{field_name}"'
        elif field_type == 'integer':
            if 'timestamp' in field_name_lower or 'time' in field_name_lower:
                return '1640995200'  # Fixed timestamp for consistency
            else:
                return '42'
        elif field_type == 'decimal':
            if 'price' in field_name_lower:
                return 'Decimal("29.99")'
            else:
                return 'Decimal("3.14")'
        elif field_type == 'boolean':
            return 'True'
        elif field_type == 'array':
            item_type = kwargs.get('item_type', 'string')
            if item_type == 'string':
                return '["sample1", "sample2"]'
            elif item_type == 'integer':
                return '[1, 2, 3]'
            return '["sample1", "sample2"]'
        else:
            return f'"sample_{field_name}"'

    def get_parameter_value(
        self, param: dict, entity_name: str, all_entities: dict, generate_fallback: bool = False
    ) -> str | None:
        """Generate Python-specific parameter value for access pattern testing.

        Args:
            param: Parameter definition with 'name' and 'type'
            entity_name: Name of the entity this access pattern belongs to
            all_entities: Dictionary of all entity configurations from schema
            generate_fallback: If True, generate smart defaults for unknown parameters (for range queries)

        Returns:
            Python-specific string representation of the parameter value, or None if parameter
            doesn't exist in entity fields and has no usage_data (and generate_fallback=False)

        Examples:
            - Scalar field: 'created_entities["User"].user_id'
            - Entity reference: 'created_entities["User"]'
            - Complex type: '{}'
            - Non-existent field (generate_fallback=False): None
            - Non-existent field (generate_fallback=True): Smart default based on name
        """
        param_name = param['name']
        param_type = param.get('type', 'string')

        # For entity type parameters, reference the created entity
        if param_type == 'entity':
            entity_type = param.get('entity_type', entity_name)
            return f'created_entities["{entity_type}"]'

        # For complex types, use Python-specific placeholders
        if param_type == 'object' or param_type == 'dict':
            return '{}'
        elif param_type == 'array' or param_type == 'list':
            return '[]'

        # For scalar types, try to match with entity fields
        # Check if this parameter name exists as a field in the current entity
        if entity_name in all_entities:
            entity_config = all_entities[entity_name]
            entity_fields = [f['name'] for f in entity_config.get('fields', [])]

            if param_name in entity_fields:
                # Parameter exists in entity fields - always use entity reference
                return f'created_entities["{entity_name}"].{param_name}'

        # Parameter not in entity fields - try to get from usage_data
        # First try update_data (for UpdateItem parameters), then sample_data
        if self.usage_data_loader and self.usage_data_loader.has_data():
            # Try update_data first (for update parameters like quantity_change, status, etc.)
            update_value = self.usage_data_loader.get_update_value_for_field(
                param_name, param_type, entity_name
            )
            if update_value is not None:
                return update_value

            # Fall back to sample_data
            realistic_value = self.usage_data_loader.get_sample_value_for_field(
                param_name, param_type, entity_name
            )
            if realistic_value is not None:
                return realistic_value

        # Parameter doesn't exist in entity fields and has no usage_data
        if not generate_fallback:
            # Return None to signal parameter should be skipped (for phantom parameters)
            return None

        # Generate sensible default based on parameter name semantics (for range queries)
        param_name_lower = param_name.lower()

        # For range query parameters, use values that sort correctly for between operators
        if (
            'start' in param_name_lower
            or 'min' in param_name_lower
            or 'since' in param_name_lower
            or 'from' in param_name_lower
            or 'lower' in param_name_lower
        ):
            # Lower bound - sorts first
            if param_type == 'integer':
                return '0'
            elif param_type == 'decimal':
                return 'Decimal("0.00")'
            else:  # string (dates, timestamps, etc.)
                return '"2024-01-01"'
        elif (
            'end' in param_name_lower
            or 'max' in param_name_lower
            or 'until' in param_name_lower
            or 'to' in param_name_lower
            or 'upper' in param_name_lower
        ):
            # Upper bound - sorts last
            if param_type == 'integer':
                return '9999'
            elif param_type == 'decimal':
                return 'Decimal("9999.99")'
            else:  # string (dates, timestamps, etc.)
                return '"2024-12-31"'
        else:
            # Generic fallback for other parameter names
            if param_type == 'integer':
                return '100'
            elif param_type == 'decimal':
                return 'Decimal("100.00")'
            else:
                return f'"{param_name}_value"'
