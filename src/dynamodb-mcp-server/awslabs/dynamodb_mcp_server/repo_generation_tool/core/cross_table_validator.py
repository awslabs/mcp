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

"""Validator for cross-table access patterns.

This module provides validation for cross_table_access_patterns in schema.json files,
supporting atomic transactions (TransactWrite, TransactGet) and future operation types.
"""

from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    ParameterType,
    validate_parameter_core,
    validate_required_fields,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.validation_utils import (
    ValidationError,
)
from typing import Any


class CrossTableValidator:
    """Validates cross-table access patterns including transactions and future operation types."""

    def validate_cross_table_patterns(
        self,
        patterns: Any,
        schema: dict[str, Any],
        path: str,
        pattern_ids: set[int],
        table_map: dict[str, dict[str, Any]],
        global_entity_names: set[str],
    ) -> list[ValidationError]:
        """Validate cross_table_access_patterns section.

        Args:
            patterns: The cross_table_access_patterns array from schema
            schema: The complete schema dict for table/entity lookups
            path: Path context for error reporting
            pattern_ids: Set of already-used pattern IDs (will be updated)
            table_map: Pre-built table name to table dict mapping for O(1) lookups
            global_entity_names: Pre-built set of all entity names for O(1) lookups

        Returns:
            List of validation errors
        """
        errors = []

        if not isinstance(patterns, list):
            errors.append(
                ValidationError(
                    path=path,
                    message='cross_table_access_patterns must be an array',
                    suggestion='Change cross_table_access_patterns to a JSON array',
                )
            )
            return errors

        if not patterns:
            # Empty array is valid - just means no cross-table patterns
            return errors

        # Validate each cross-table pattern
        for i, pattern in enumerate(patterns):
            pattern_path = f'{path}[{i}]'
            pattern_errors = self._validate_cross_table_pattern(
                pattern, pattern_path, schema, pattern_ids, table_map, global_entity_names
            )
            errors.extend(pattern_errors)

        return errors

    def _validate_cross_table_pattern(
        self,
        pattern: Any,
        path: str,
        schema: dict[str, Any],
        pattern_ids: set[int],
        table_map: dict[str, dict[str, Any]],
        global_entity_names: set[str],
    ) -> list[ValidationError]:
        """Validate a single cross-table access pattern.

        Args:
            pattern: The pattern dictionary to validate
            path: Path context for error reporting
            schema: The complete schema dict for table/entity lookups
            pattern_ids: Set of already-used pattern IDs (will be updated)
            table_map: Pre-built table name to table dict mapping for O(1) lookups
            global_entity_names: Pre-built set of all entity names for O(1) lookups

        Returns:
            List of validation errors
        """
        errors = []

        if not isinstance(pattern, dict):
            errors.append(
                ValidationError(
                    path=path,
                    message='Cross-table pattern must be an object',
                    suggestion='Change pattern to a JSON object',
                )
            )
            return errors

        # Validate required fields
        required_fields = {
            'pattern_id',
            'name',
            'description',
            'operation',
            'entities_involved',
            'parameters',
            'return_type',
        }
        errors.extend(validate_required_fields(pattern, required_fields, path))

        # Validate pattern_id uniqueness (global across all patterns)
        if 'pattern_id' in pattern:
            pattern_id = pattern['pattern_id']

            if not isinstance(pattern_id, int):
                errors.append(
                    ValidationError(
                        path=f'{path}.pattern_id',
                        message=f'pattern_id must be an integer, got {type(pattern_id).__name__}',
                        suggestion='Change pattern_id to an integer',
                    )
                )
            else:
                if pattern_id in pattern_ids:
                    errors.append(
                        ValidationError(
                            path=f'{path}.pattern_id',
                            message=f'Duplicate pattern_id {pattern_id}',
                            suggestion='Pattern IDs must be unique across all tables and cross-table patterns',
                        )
                    )
                else:
                    pattern_ids.add(pattern_id)

        # Validate operation type
        if 'operation' in pattern:
            operation = pattern['operation']
            valid_operations = ['TransactWrite', 'TransactGet']

            if operation not in valid_operations:
                errors.append(
                    ValidationError(
                        path=f'{path}.operation',
                        message=f"Invalid operation '{operation}'. Valid operations: {', '.join(valid_operations)}",
                        suggestion=f'Use one of: {", ".join(valid_operations)}',
                    )
                )

        # Validate entities_involved
        if 'entities_involved' in pattern:
            entities_errors = self._validate_entities_involved(
                pattern['entities_involved'],
                f'{path}.entities_involved',
                schema,
                pattern.get('operation'),
                table_map,
            )
            errors.extend(entities_errors)

        # Validate return_type
        if 'return_type' in pattern:
            return_type = pattern['return_type']
            valid_return_types = ['boolean', 'object', 'array']

            if return_type not in valid_return_types:
                errors.append(
                    ValidationError(
                        path=f'{path}.return_type',
                        message=f"Invalid return_type '{return_type}'. Valid types: {', '.join(valid_return_types)}",
                        suggestion=f'Use one of: {", ".join(valid_return_types)}',
                    )
                )

        # Validate parameters
        if 'parameters' in pattern:
            parameters_errors = self._validate_parameters(
                pattern['parameters'],
                f'{path}.parameters',
                schema,
                global_entity_names,
            )
            errors.extend(parameters_errors)

        return errors

    def _validate_entities_involved(
        self,
        entities_involved: Any,
        path: str,
        schema: dict[str, Any],
        operation: str | None,
        table_map: dict[str, dict[str, Any]],
    ) -> list[ValidationError]:
        """Validate entities_involved array in cross-table pattern.

        Args:
            entities_involved: The entities_involved array to validate
            path: Path context for error reporting
            schema: The complete schema dict for table/entity lookups
            operation: The operation type (TransactWrite/TransactGet) for action validation
            table_map: Pre-built table name to table dict mapping for O(1) lookups

        Returns:
            List of validation errors
        """
        errors = []

        if not isinstance(entities_involved, list):
            errors.append(
                ValidationError(
                    path=path,
                    message='entities_involved must be an array',
                    suggestion='Change entities_involved to a JSON array',
                )
            )
            return errors

        if not entities_involved:
            errors.append(
                ValidationError(
                    path=path,
                    message='entities_involved cannot be empty',
                    suggestion='Add at least one entity involvement definition',
                )
            )
            return errors

        # Validate each entity involvement
        for i, entity_inv in enumerate(entities_involved):
            entity_path = f'{path}[{i}]'
            entity_errors = self._validate_entity_involvement(
                entity_inv, entity_path, schema, operation, table_map
            )
            errors.extend(entity_errors)

        return errors

    def _validate_entity_involvement(
        self,
        entity_inv: Any,
        path: str,
        schema: dict[str, Any],
        operation: str | None,
        table_map: dict[str, dict[str, Any]],
    ) -> list[ValidationError]:
        """Validate a single entity involvement in cross-table pattern.

        Args:
            entity_inv: The entity involvement dictionary to validate
            path: Path context for error reporting
            schema: The complete schema dict for table/entity lookups
            operation: The operation type (TransactWrite/TransactGet) for action validation
            table_map: Pre-built table name to table dict mapping for O(1) lookups

        Returns:
            List of validation errors
        """
        errors = []

        if not isinstance(entity_inv, dict):
            errors.append(
                ValidationError(
                    path=path,
                    message='Entity involvement must be an object',
                    suggestion='Change entity involvement to a JSON object',
                )
            )
            return errors

        # Validate required fields
        required_fields = {'table', 'entity', 'action'}
        errors.extend(validate_required_fields(entity_inv, required_fields, path))

        # Validate table reference
        if 'table' in entity_inv:
            table_name = entity_inv['table']
            table = self._find_table(schema, table_name, table_map)

            if not table:
                errors.append(
                    ValidationError(
                        path=f'{path}.table',
                        message=f"Table '{table_name}' not found in schema",
                        suggestion='Ensure the table is defined in the tables array',
                    )
                )
            else:
                # Validate entity reference within the table
                if 'entity' in entity_inv:
                    entity_name = entity_inv['entity']
                    entities = table.get('entities', {})

                    if entity_name not in entities:
                        errors.append(
                            ValidationError(
                                path=f'{path}.entity',
                                message=f"Entity '{entity_name}' not found in table '{table_name}'",
                                suggestion=f'Ensure the entity is defined in table {table_name}',
                            )
                        )

        # Validate action compatibility with operation
        if 'action' in entity_inv and operation:
            action = entity_inv['action']
            valid_actions = self._get_valid_actions(operation)

            if action not in valid_actions:
                errors.append(
                    ValidationError(
                        path=f'{path}.action',
                        message=f"Invalid action '{action}' for operation '{operation}'. Valid actions: {', '.join(valid_actions)}",
                        suggestion=f'Use one of: {", ".join(valid_actions)}',
                    )
                )

        return errors

    def _find_table(
        self,
        schema: dict[str, Any],
        table_name: str,
        table_map: dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Find a table by name in the schema.

        Args:
            schema: The complete schema dict
            table_name: The name of the table to find
            table_map: Pre-built table name to table dict mapping for O(1) lookups

        Returns:
            The table dict if found, None otherwise
        """
        return table_map.get(table_name)

    def _get_valid_actions(self, operation: str) -> list[str]:
        """Get the list of valid actions for an operation type.

        Args:
            operation: The operation type (TransactWrite or TransactGet)

        Returns:
            List of valid action names for the operation
        """
        if operation == 'TransactWrite':
            return ['Put', 'Update', 'Delete', 'ConditionCheck']
        elif operation == 'TransactGet':
            return ['Get']
        else:
            return []

    def _validate_parameters(
        self,
        parameters: Any,
        path: str,
        schema: dict[str, Any],
        global_entity_names: set[str],
    ) -> list[ValidationError]:
        """Validate parameters array in cross-table pattern.

        Args:
            parameters: The parameters array to validate
            path: Path context for error reporting
            schema: The complete schema dict for entity lookups
            global_entity_names: Pre-built set of all entity names for O(1) lookups

        Returns:
            List of validation errors
        """
        errors = []

        if not isinstance(parameters, list):
            errors.append(
                ValidationError(
                    path=path,
                    message='parameters must be an array',
                    suggestion='Change parameters to a JSON array',
                )
            )
            return errors

        # Empty parameters array is valid
        if not parameters:
            return errors

        # Validate each parameter
        param_names = set()
        for i, param in enumerate(parameters):
            param_path = f'{path}[{i}]'
            param_errors = self._validate_parameter(
                param, param_path, schema, param_names, global_entity_names
            )
            errors.extend(param_errors)

        return errors

    def _validate_parameter(
        self,
        param: Any,
        path: str,
        schema: dict[str, Any],
        param_names: set[str],
        global_entity_names: set[str],
    ) -> list[ValidationError]:
        """Validate a single parameter in cross-table pattern.

        Args:
            param: The parameter dictionary to validate
            path: Path context for error reporting
            schema: The complete schema dict for entity lookups
            param_names: Set of already-used parameter names (will be updated)
            global_entity_names: Pre-built set of all entity names for O(1) lookups

        Returns:
            List of validation errors
        """
        # Use shared core validation logic
        errors = validate_parameter_core(param, path, param_names, global_entity_names)

        # Additional validation specific to cross-table patterns:
        # Validate parameter type consistency with entity fields (for non-entity parameters)
        if 'type' in param and 'name' in param and param['type'] != ParameterType.ENTITY.value:
            param_name = param['name']
            param_type = param['type']

            # Check if this parameter name matches any entity field
            field_type = self._find_field_type_in_schema(schema, param_name)

            if field_type and field_type != param_type:
                # Parameter type doesn't match field type
                errors.append(
                    ValidationError(
                        path=f'{path}.type',
                        message=f"Parameter '{param_name}' type '{param_type}' doesn't match field type '{field_type}'",
                        suggestion=f"Change parameter type to '{field_type}' to match the entity field definition",
                    )
                )

        return errors

    def _find_field_type_in_schema(self, schema: dict[str, Any], field_name: str) -> str | None:
        """Find the type of a field by searching all entities in the schema.

        Args:
            schema: The complete schema dict
            field_name: The name of the field to find

        Returns:
            The field type if found, None otherwise
        """
        tables = schema.get('tables', [])

        for table in tables:
            if isinstance(table, dict):
                entities = table.get('entities', {})
                if isinstance(entities, dict):
                    for entity_config in entities.values():
                        if isinstance(entity_config, dict):
                            fields = entity_config.get('fields', [])
                            for field in fields:
                                if isinstance(field, dict) and field.get('name') == field_name:
                                    return field.get('type')

        return None
