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

"""Usage data validation for DynamoDB code generation.

This module provides validation for usage_data.json files used in code generation,
ensuring they conform to expected structure and contain data for all schema entities.
"""

from awslabs.dynamodb_mcp_server.repo_generation_tool.core.file_utils import (
    FileUtils,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.validation_utils import (
    ValidationResult,
)
from typing import Any, Dict, Set


class UsageDataValidator:
    """Validates usage_data.json structure and content against schema entities."""

    # Constants for better maintainability - use frozenset for immutability and performance
    REQUIRED_SECTIONS = frozenset(['sample_data', 'access_pattern_data', 'update_data'])
    KNOWN_TOP_LEVEL_KEYS = frozenset(['entities'])

    def __init__(self):
        """Initialize validator."""
        self.result = ValidationResult(is_valid=True, errors=[], warnings=[])

    def validate_usage_data_file(
        self, usage_data_path: str, schema_entities: set[str], entity_fields: dict[str, set[str]]
    ) -> ValidationResult:
        """Load and validate usage_data file against schema entities.

        Args:
            usage_data_path: Path to usage_data.json file
            schema_entities: Pre-extracted entity names from schema validation
            entity_fields: Pre-extracted entity fields from schema validation

        Returns:
            ValidationResult with errors and warnings
        """
        # Reset validation state
        self.result = ValidationResult(is_valid=True, errors=[], warnings=[])

        # Load usage_data file using FileUtils directly
        try:
            usage_data = FileUtils.load_json_file(usage_data_path, 'Usage data')
        except FileNotFoundError as e:
            self.result.add_error('file', str(e), 'Check the file path and ensure the file exists')
            self.result.is_valid = False
            return self.result
        except ValueError as e:
            if 'Invalid JSON' in str(e):
                self.result.add_error('json', str(e), 'Fix JSON syntax errors')
            else:
                self.result.add_error('file', str(e), 'Check file permissions and format')
            self.result.is_valid = False
            return self.result

        # Validate usage_data structure and content
        self._validate_usage_data_structure(usage_data, schema_entities, entity_fields)

        return self.result

    def _validate_usage_data_structure(
        self,
        usage_data: Dict[str, Any],
        schema_entities: Set[str],
        entity_fields: Dict[str, Set[str]],
    ) -> None:
        """Validate top-level usage_data structure."""
        if not isinstance(usage_data, dict):
            self.result.add_error(
                'root',
                'Usage data must be a JSON object',
                'Ensure the root element is a JSON object {}',
            )
            return

        # Validate required top-level 'entities' section
        if 'entities' not in usage_data:
            self.result.add_error(
                'root',
                "Missing required 'entities' key",
                "Add 'entities' key to the root object",
            )
            return

        # Check for unknown top-level keys (error, not warning)
        unknown_keys = set(usage_data.keys()) - self.KNOWN_TOP_LEVEL_KEYS
        if unknown_keys:
            unknown_list = sorted(unknown_keys)
            self.result.add_error(
                'root',
                f'Unknown top-level keys: {unknown_list}',
                f'Remove unknown keys. Valid keys are: {", ".join(sorted(self.KNOWN_TOP_LEVEL_KEYS))}',
            )

        # Validate entities section
        self._validate_entities_section(usage_data['entities'], schema_entities, entity_fields)

    def _validate_entities_section(
        self, entities: Any, schema_entities: Set[str], entity_fields: Dict[str, Set[str]]
    ) -> None:
        """Validate entities section against schema entities."""
        path = 'entities'

        if not isinstance(entities, dict):
            self.result.add_error(
                path, 'entities must be an object', 'Change entities to a JSON object'
            )
            return

        if not entities:
            self.result.add_error(
                path, 'entities cannot be empty', 'Add at least one entity definition'
            )
            return

        usage_data_entities = set(entities.keys())

        # Check for missing entities (entities in schema but not in usage_data)
        missing_entities = schema_entities - usage_data_entities
        if missing_entities:
            missing_list = sorted(missing_entities)
            self.result.add_error(
                path,
                f'Missing required entities: {missing_list}',
                f'Add usage data for entities: {", ".join(missing_list)}',
            )

        # Check for unknown entities (entities in usage_data but not in schema)
        unknown_entities = usage_data_entities - schema_entities
        if unknown_entities:
            unknown_list = sorted(unknown_entities)
            self.result.add_error(
                path,
                f'Unknown entities (not in schema): {unknown_list}',
                f'Remove unknown entities or add them to schema: {", ".join(unknown_list)}',
            )

        # Validate each entity structure
        for entity_name, entity_data in entities.items():
            valid_fields = entity_fields.get(entity_name, set())
            self._validate_entity_data(
                entity_name, entity_data, f'{path}.{entity_name}', valid_fields
            )

    def _validate_entity_data(
        self, entity_name: str, entity_data: Any, path: str, valid_fields: Set[str]
    ) -> None:
        """Validate single entity usage data structure."""
        if not isinstance(entity_data, dict):
            self.result.add_error(
                path,
                f"Entity '{entity_name}' must be an object",
                f'Change {entity_name} to a JSON object',
            )
            return

        # Check for required sections - all are required
        present_sections = set(entity_data.keys())

        # Check for missing required sections
        missing_sections = self.REQUIRED_SECTIONS - present_sections
        if missing_sections:
            for section in sorted(missing_sections):
                self.result.add_error(
                    f'{path}.{section}',
                    f"Missing required '{section}' section for entity '{entity_name}'",
                    f"Add '{section}' section with appropriate field values",
                )

        # Validate each section structure
        for section_name, section_data in entity_data.items():
            if section_name in self.REQUIRED_SECTIONS:
                self._validate_entity_section(
                    entity_name, section_name, section_data, f'{path}.{section_name}', valid_fields
                )
            else:
                # Unknown section name
                self.result.add_error(
                    f'{path}.{section_name}',
                    f"Unknown section '{section_name}' in entity '{entity_name}'",
                    f'Valid sections are: {", ".join(sorted(self.REQUIRED_SECTIONS))}',
                )

    def _validate_entity_section(
        self,
        entity_name: str,
        section_name: str,
        section_data: Any,
        path: str,
        valid_fields: Set[str],
    ) -> None:
        """Validate individual entity section (sample_data, access_pattern_data, update_data)."""
        if not isinstance(section_data, dict):
            self.result.add_error(
                path,
                f"Section '{section_name}' in entity '{entity_name}' must be an object",
                f'Change {section_name} to a JSON object with field values',
            )
            return

        # For sample_data, error if empty (other sections can be empty as they fall back to sample_data)
        if section_name == 'sample_data' and not section_data:
            self.result.add_error(
                path,
                f"Empty 'sample_data' section for entity '{entity_name}'",
                'Add sample field values for realistic code generation',
            )

        # Validate that all field names exist in the schema
        self._validate_field_names(entity_name, section_name, section_data, path, valid_fields)

    def _validate_field_names(
        self,
        entity_name: str,
        section_name: str,
        section_data: Dict[str, Any],
        path: str,
        valid_fields: Set[str],
    ) -> None:
        """Validate that all field names in usage_data exist in the schema."""
        if not valid_fields:
            # If we couldn't extract fields from schema, skip this validation
            return

        usage_fields = set(section_data.keys())

        # Check for unknown fields (fields in usage_data but not in schema)
        unknown_fields = usage_fields - valid_fields
        if unknown_fields:
            # Sort for consistent error ordering
            for field_name in sorted(unknown_fields):
                field_path = f'{path}.{field_name}'

                self.result.add_error(
                    field_path,
                    f"Unknown field '{field_name}' in {entity_name}.{section_name}",
                    f'Valid fields for {entity_name}: {", ".join(sorted(valid_fields))}',
                )

    def format_validation_result(self) -> str:
        """Format validation result as human-readable string."""
        return self.result.format('Usage data validation passed!', 'Usage data validation failed')
