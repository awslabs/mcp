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

"""Schema validation for DynamoDB table definitions.

This module provides validation for schema.json files used in code generation,
ensuring they conform to expected structure and contain valid enum values.
"""

from awslabs.dynamodb_mcp_server.repo_generation_tool.core.cross_table_validator import (
    CrossTableValidator,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.file_utils import (
    FileUtils,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.gsi_validator import GSIValidator
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.range_query_validator import (
    RangeQueryValidator,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    REQUIRED_ACCESS_PATTERN_FIELDS,
    REQUIRED_ENTITY_FIELDS,
    REQUIRED_FIELD_PROPERTIES,
    REQUIRED_SCHEMA_FIELDS,
    REQUIRED_TABLE_CONFIG_FIELDS,
    REQUIRED_TABLE_FIELDS,
    AccessPattern,
    DynamoDBOperation,
    FieldType,
    ReturnType,
    validate_data_type,
    validate_enum_field,
    validate_parameter_core,
    validate_required_fields,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.validation_utils import (
    ValidationResult,
)
from typing import Any


class SchemaValidator:
    """Validates schema.json structure and values."""

    def __init__(self, strict_mode: bool = True):
        """Initialize validator.

        Args:
            strict_mode: If True, treats warnings as errors
        """
        self.strict_mode = strict_mode
        self.result = ValidationResult(is_valid=True, errors=[], warnings=[])
        self.global_entity_names: set[str] = set()  # Global entity name tracking across all tables
        self.pattern_ids: set[int] = set()  # Global pattern_id tracking across all tables
        self.table_map: dict[
            str, dict[str, Any]
        ] = {}  # Table name to table dict mapping for O(1) lookups
        self.gsi_validator = GSIValidator()  # GSI validation component
        self.range_query_validator = RangeQueryValidator()  # Range query validation component
        self.cross_table_validator = CrossTableValidator()  # Cross-table validation component

    def validate_schema_file(self, schema_path: str) -> ValidationResult:
        """Load and validate schema file.

        Args:
            schema_path: Path to schema.json file

        Returns:
            ValidationResult with errors and warnings
        """
        self.result = ValidationResult(is_valid=True, errors=[], warnings=[])
        self.global_entity_names = set()
        self.global_entity_fields = {}  # Track entity fields for reuse
        self.pattern_ids = set()
        self.table_map = {}  # Reset table map for each validation

        # Load JSON file using FileUtils directly
        try:
            schema = FileUtils.load_json_file(schema_path, 'Schema')
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

        # Validate schema structure and content
        self._validate_schema_structure(schema)

        # Perform GSI validation regardless of other validation errors
        # This ensures we collect all validation issues at once
        self._validate_gsi_configuration(schema)

        # Store extracted schema information in the result for reuse
        self.result.store_entity_info(self.global_entity_names, self.global_entity_fields)

        return self.result

    def _validate_schema_structure(self, schema: dict[str, Any]) -> None:
        """Validate top-level schema structure."""
        if not isinstance(schema, dict):
            self.result.add_error(
                'root',
                'Schema must be a JSON object',
                'Ensure the root element is a JSON object {}',
            )
            return

        # Validate required top-level sections for tables array format
        errors = validate_required_fields(schema, REQUIRED_SCHEMA_FIELDS, 'root')
        self.result.add_errors(errors)

        # Validate tables array
        if 'tables' in schema:
            self._validate_tables(schema['tables'])

        # Validate cross_table_access_patterns if present
        if 'cross_table_access_patterns' in schema:
            cross_table_errors = self.cross_table_validator.validate_cross_table_patterns(
                schema['cross_table_access_patterns'],
                schema,
                'cross_table_access_patterns',
                self.pattern_ids,
                self.table_map,  # Pass cached table map for O(1) lookups
                self.global_entity_names,  # Pass cached entity names for O(1) lookups
            )
            for error in cross_table_errors:
                self.result.errors.append(error)
                self.result.is_valid = False

    def _validate_tables(self, tables: Any) -> None:
        """Validate tables array."""
        path = 'tables'

        if not isinstance(tables, list):
            self.result.add_error(path, 'tables must be an array', 'Change tables to a JSON array')
            return

        if not tables:
            self.result.add_error(
                path, 'tables cannot be empty', 'Add at least one table definition'
            )
            return

        # Build table map for efficient lookups (O(1) instead of O(n))
        # Also validate table name uniqueness
        for i, table in enumerate(tables):
            if isinstance(table, dict):
                table_config = table.get('table_config', {})
                if isinstance(table_config, dict):
                    table_name = table_config.get('table_name')
                    if table_name:
                        # Check for duplicate table names
                        if table_name in self.table_map:
                            self.result.add_error(
                                f'{path}[{i}].table_config.table_name',
                                f"Duplicate table name '{table_name}'",
                                'Table names must be unique across all tables',
                            )
                        else:
                            self.table_map[table_name] = table

        # Validate each table
        for i, table in enumerate(tables):
            table_path = f'{path}[{i}]'
            self._validate_table(table, table_path, i)

    def _validate_table(self, table: Any, path: str, table_index: int) -> None:
        """Validate single table configuration."""
        if not isinstance(table, dict):
            self.result.add_error(path, 'Table must be an object', 'Change table to a JSON object')
            return

        # Check required fields for each table
        errors = validate_required_fields(table, REQUIRED_TABLE_FIELDS, path)
        self.result.add_errors(errors)

        # Validate table_config section
        if 'table_config' in table:
            self._validate_table_config(table['table_config'], f'{path}.table_config')

        # Validate entities section with table context
        if 'entities' in table:
            self._validate_entities(table['entities'], f'{path}.entities', table_index)

    def _validate_table_config(self, table_config: Any, path: str = 'table_config') -> None:
        """Validate table_config section."""
        if not isinstance(table_config, dict):
            self.result.add_error(
                path, 'table_config must be an object', 'Change table_config to a JSON object'
            )
            return

        # Check required fields
        errors = validate_required_fields(table_config, REQUIRED_TABLE_CONFIG_FIELDS, path)
        self.result.add_errors(errors)

        # Validate field types
        for field in REQUIRED_TABLE_CONFIG_FIELDS:
            if field in table_config:
                field_errors = validate_data_type(table_config[field], str, path, field)
                for error in field_errors:
                    self.result.errors.append(error)
                    self.result.is_valid = False

    def _validate_entities(
        self, entities: Any, path: str = 'entities', table_index: int = 0
    ) -> None:
        """Validate entities section."""
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

        # Collect entity names for reference validation within this table
        table_entity_names = set(entities.keys())

        # Check for global entity name uniqueness
        for entity_name in entities.keys():
            if entity_name in self.global_entity_names:
                self.result.add_error(
                    f'{path}.{entity_name}',
                    f"Duplicate entity name '{entity_name}' across tables",
                    'Entity names must be unique across all tables',
                )
            else:
                self.global_entity_names.add(entity_name)

        # Validate each entity
        for entity_name, entity_config in entities.items():
            self._validate_entity(
                entity_name, entity_config, f'{path}.{entity_name}', table_entity_names
            )

    def _validate_entity(
        self, entity_name: str, entity_config: Any, path: str, table_entity_names: set[str]
    ) -> None:
        """Validate single entity configuration."""
        if not isinstance(entity_config, dict):
            self.result.add_error(
                path,
                f"Entity '{entity_name}' must be an object",
                f'Change {entity_name} to a JSON object',
            )
            return

        # Check required fields
        errors = validate_required_fields(entity_config, REQUIRED_ENTITY_FIELDS, path)
        self.result.add_errors(errors)

        # Validate string fields with template-specific guidance
        string_fields = {'entity_type', 'pk_template'}
        for field in string_fields:
            if field in entity_config:
                field_errors = validate_data_type(entity_config[field], str, path, field)
                for error in field_errors:
                    self.result.errors.append(error)
                    self.result.is_valid = False
            elif field == 'pk_template':
                # Provide template-specific guidance for missing pk_template
                self.result.add_error(
                    f'{path}.{field}',
                    f"Missing required field '{field}'",
                    f"Add '{field}' field using template syntax like 'USER#{{user_id}}' or 'PROFILE#{{id}}#{{timestamp}}'. Parameters are automatically extracted from {{field_name}} placeholders",
                )

        # Validate sk_template if present (it's optional)
        if 'sk_template' in entity_config:
            if entity_config['sk_template'] is not None:
                field_errors = validate_data_type(
                    entity_config['sk_template'], str, path, 'sk_template'
                )
                for error in field_errors:
                    self.result.errors.append(error)
                    self.result.is_valid = False

        # Validate fields array and extract field names
        entity_field_names = set()
        if 'fields' in entity_config:
            self._validate_entity_fields(entity_config['fields'], f'{path}.fields')
            # Extract field names for reuse
            if isinstance(entity_config['fields'], list):
                for field in entity_config['fields']:
                    if isinstance(field, dict) and 'name' in field:
                        entity_field_names.add(field['name'])

        # Store extracted field information for reuse
        self.global_entity_fields[entity_name] = entity_field_names

        # Validate access patterns
        if 'access_patterns' in entity_config:
            self._validate_access_patterns(
                entity_config['access_patterns'], f'{path}.access_patterns', entity_name
            )

    def _validate_entity_fields(self, fields: Any, path: str) -> None:
        """Validate entity fields array."""
        if not isinstance(fields, list):
            self.result.add_error(path, 'fields must be an array', 'Change fields to a JSON array')
            return

        if not fields:
            self.result.add_error(
                path, 'fields cannot be empty', 'Add at least one field definition'
            )
            return

        field_names = set()
        for i, field in enumerate(fields):
            field_path = f'{path}[{i}]'
            self._validate_field_definition(field, field_path, field_names)

    def _validate_field_definition(self, field: Any, path: str, field_names: set[str]) -> None:
        """Validate single field definition."""
        if not isinstance(field, dict):
            self.result.add_error(path, 'Field must be an object', 'Change field to a JSON object')
            return

        # Check required properties
        errors = validate_required_fields(field, REQUIRED_FIELD_PROPERTIES, path)
        self.result.add_errors(errors)

        # Validate field name uniqueness
        if 'name' in field:
            field_name = field['name']
            if field_name in field_names:
                self.result.add_error(
                    f'{path}.name',
                    f"Duplicate field name '{field_name}'",
                    'Field names must be unique within an entity',
                )
            else:
                field_names.add(field_name)

        # Validate field type
        if 'type' in field:
            type_errors = validate_enum_field(field['type'], FieldType, path, 'type')
            for error in type_errors:
                self.result.errors.append(error)
                self.result.is_valid = False

            # Special validation for array type
            if field['type'] == FieldType.ARRAY.value and 'item_type' not in field:
                self.result.add_error(
                    f'{path}.item_type',
                    'Array fields must specify item_type',
                    "Add 'item_type' property for array fields",
                )

        # Validate required field
        if 'required' in field:
            req_errors = validate_data_type(field['required'], bool, path, 'required')
            for error in req_errors:
                self.result.errors.append(error)
                self.result.is_valid = False

    def _validate_access_patterns(self, patterns: Any, path: str, entity_name: str) -> None:
        """Validate access patterns array."""
        if not isinstance(patterns, list):
            self.result.add_error(
                path, 'access_patterns must be an array', 'Change access_patterns to a JSON array'
            )
            return

        pattern_names = set()
        for i, pattern in enumerate(patterns):
            pattern_path = f'{path}[{i}]'
            self._validate_access_pattern(pattern, pattern_path, entity_name, pattern_names)

    def _validate_access_pattern(
        self, pattern: Any, path: str, entity_name: str, pattern_names: set[str]
    ) -> None:
        """Validate single access pattern."""
        if not isinstance(pattern, dict):
            self.result.add_error(
                path, 'Access pattern must be an object', 'Change access pattern to a JSON object'
            )
            return

        # Check required fields
        errors = validate_required_fields(pattern, REQUIRED_ACCESS_PATTERN_FIELDS, path)
        self.result.add_errors(errors)

        # Validate pattern_id uniqueness and type (global across all tables)
        if 'pattern_id' in pattern:
            pattern_id = pattern['pattern_id']

            # Check type
            if not isinstance(pattern_id, int):
                self.result.add_error(
                    f'{path}.pattern_id',
                    f'pattern_id must be an integer, got {type(pattern_id).__name__}',
                    'Change pattern_id to an integer',
                )
            else:
                # Check uniqueness across all tables and entities
                if pattern_id in self.pattern_ids:
                    self.result.add_error(
                        f'{path}.pattern_id',
                        f'Duplicate pattern_id {pattern_id}',
                        'Pattern IDs must be unique across all tables and entities',
                    )
                else:
                    self.pattern_ids.add(pattern_id)

        # Validate pattern name uniqueness within entity
        if 'name' in pattern:
            pattern_name = pattern['name']
            if pattern_name in pattern_names:
                self.result.add_error(
                    f'{path}.name',
                    f"Duplicate pattern name '{pattern_name}' in entity '{entity_name}'",
                    'Pattern names must be unique within an entity',
                )
            else:
                pattern_names.add(pattern_name)

        # Validate operation
        if 'operation' in pattern:
            op_errors = validate_enum_field(
                pattern['operation'], DynamoDBOperation, path, 'operation'
            )
            for error in op_errors:
                self.result.errors.append(error)
                self.result.is_valid = False

        # Validate return_type
        if 'return_type' in pattern:
            rt_errors = validate_enum_field(
                pattern['return_type'], ReturnType, path, 'return_type'
            )
            for error in rt_errors:
                self.result.errors.append(error)
                self.result.is_valid = False

        # Validate parameters
        if 'parameters' in pattern:
            self._validate_parameters(pattern['parameters'], f'{path}.parameters')

        # Validate consistent_read field
        if 'consistent_read' in pattern:
            self._validate_consistent_read(pattern, path)

        # Validate range queries for main table (when index_name is not present)
        if 'range_condition' in pattern and not pattern.get('index_name'):
            self._validate_main_table_range_query(pattern, path)

    def _validate_parameters(self, parameters: Any, path: str) -> None:
        """Validate parameters array."""
        if not isinstance(parameters, list):
            self.result.add_error(
                path, 'parameters must be an array', 'Change parameters to a JSON array'
            )
            return

        param_names = set()
        for i, param in enumerate(parameters):
            param_path = f'{path}[{i}]'
            self._validate_parameter(param, param_path, param_names)

    def _validate_parameter(self, param: Any, path: str, param_names: set[str]) -> None:
        """Validate single parameter."""
        # Use shared core validation logic
        errors = validate_parameter_core(param, path, param_names, self.global_entity_names)

        # Add errors to result
        for error in errors:
            self.result.errors.append(error)
            self.result.is_valid = False

    def _validate_consistent_read(self, pattern: dict[str, Any], path: str) -> None:
        """Validate consistent_read field in an access pattern.

        Args:
            pattern: Access pattern dictionary containing consistent_read field
            path: Path context for error reporting
        """
        consistent_read = pattern['consistent_read']
        pattern_id = pattern.get('pattern_id', 'unknown')
        pattern_name = pattern.get('name', 'unknown')

        # Rule 1: Type validation - must be boolean
        if not isinstance(consistent_read, bool):
            self.result.add_error(
                f'{path}.consistent_read',
                f'Pattern {pattern_id} ({pattern_name}): consistent_read must be a boolean (true or false), got {type(consistent_read).__name__}',
                'Change consistent_read to true or false',
            )
            return

        # Rule 2: GSI restriction - cannot be true for GSI queries
        if consistent_read is True and 'index_name' in pattern:
            self.result.add_error(
                f'{path}.consistent_read',
                f'Pattern {pattern_id} ({pattern_name}): consistent_read cannot be true for GSI queries. Global Secondary Indexes only support eventually consistent reads.',
                'Either remove consistent_read or set it to false',
            )

    def _validate_main_table_range_query(self, pattern: dict[str, Any], path: str) -> None:
        """Validate range query configuration for main table sort key queries.

        This validates access patterns that use range conditions on the main table's
        sort key (not GSI). Ensures range conditions are valid and parameter counts
        are correct.

        Args:
            pattern: Access pattern dictionary to validate
            path: Path context for error reporting
        """
        try:
            # Convert pattern dict to AccessPattern object for validation
            parameters = []
            if 'parameters' in pattern and isinstance(pattern['parameters'], list):
                parameters = pattern['parameters']

            access_pattern = AccessPattern(
                pattern_id=pattern.get('pattern_id', 0),
                name=pattern.get('name', ''),
                description=pattern.get('description', ''),
                operation=pattern.get('operation', ''),
                parameters=parameters,
                return_type=pattern.get('return_type', ''),
                index_name=pattern.get('index_name'),
                range_condition=pattern.get('range_condition'),
            )

            # Perform comprehensive range query validation
            range_errors = self.range_query_validator.validate_complete_range_query(
                access_pattern, path
            )

            for error in range_errors:
                self.result.errors.append(error)
                self.result.is_valid = False

        except Exception as e:
            self.result.add_error(
                f'{path}.range_condition',
                f'Failed to validate main table range query: {e}',
                'Check range_condition, operation, and parameters configuration',
            )

    def format_validation_result(self) -> str:
        """Format validation result as human-readable string."""
        return self.result.format('Schema validation passed!', 'Schema validation failed')

    def _validate_gsi_configuration(self, schema: dict[str, Any]) -> None:
        """Validate GSI configuration across all tables in the schema.

        This method integrates GSI validation into the main schema processing pipeline,
        ensuring GSI definitions, mappings, and access patterns are validated before
        code generation attempts.

        """
        if 'tables' not in schema or not isinstance(schema['tables'], list):
            return

        for i, table in enumerate(schema['tables']):
            if not isinstance(table, dict):
                continue

            table_path = f'tables[{i}]'

            try:
                # Perform comprehensive GSI validation for this table
                gsi_errors = self.gsi_validator.validate_complete_gsi_configuration(
                    table, table_path
                )

                # Add all GSI validation errors to the main result
                for error in gsi_errors:
                    if error.severity == 'warning':
                        self.result.warnings.append(error)
                    else:
                        self.result.errors.append(error)
                        self.result.is_valid = False

            except Exception as e:
                # Handle any unexpected errors during GSI validation
                self.result.add_error(
                    f'{table_path}.gsi_validation',
                    f'GSI validation failed: {e}',
                    'Check GSI definitions, entity mappings, and access patterns for correct structure',
                )


def validate_schema_file(schema_path: str, strict_mode: bool = True) -> ValidationResult:
    """Convenience function to validate a schema file.

    Args:
        schema_path: Path to schema.json file
        strict_mode: If True, treats warnings as errors

    Returns:
        ValidationResult with errors and warnings
    """
    validator = SchemaValidator(strict_mode=strict_mode)
    return validator.validate_schema_file(schema_path)
