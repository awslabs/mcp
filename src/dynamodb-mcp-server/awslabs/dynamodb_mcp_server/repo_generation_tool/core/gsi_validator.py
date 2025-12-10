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

"""GSI validation system for DynamoDB schema definitions.

This module provides comprehensive validation for Global Secondary Index (GSI) definitions,
entity mappings, and access patterns. It ensures GSI configurations are valid and consistent
with the schema requirements.
"""

from awslabs.dynamodb_mcp_server.repo_generation_tool.core.key_template_parser import (
    KeyTemplateParser,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.range_query_validator import (
    RangeQueryValidator,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    AccessPattern,
    Field,
    GSIDefinition,
    GSIMapping,
    ValidationError,
)
from typing import Any


class GSIValidator:
    """Validator for GSI definitions, mappings, and access patterns.

    Provides comprehensive validation including:
    - GSI name uniqueness
    - Entity mapping validation
    - Template parameter validation
    - Range condition validation
    - Parameter count validation for range queries
    """

    def __init__(self):
        """Initialize GSI validator with template parser and range query validator."""
        self.template_parser = KeyTemplateParser()
        self.range_query_validator = RangeQueryValidator()

    def validate_gsi_names_unique(
        self, gsi_list: list[GSIDefinition], table_path: str = 'gsi_list'
    ) -> list[ValidationError]:
        """Ensure GSI names are unique within a table.

        Args:
            gsi_list: List of GSI definitions to validate
            table_path: Path context for error reporting

        Returns:
            List of ValidationError objects for duplicate GSI names
        """
        errors = []

        if not gsi_list:
            return errors

        seen_names: set[str] = set()

        for i, gsi in enumerate(gsi_list):
            gsi_path = f'{table_path}[{i}]'

            if not isinstance(gsi, GSIDefinition):
                errors.append(
                    ValidationError(
                        path=f'{gsi_path}',
                        message='GSI definition must be a GSIDefinition object',
                        suggestion='Ensure GSI is properly structured with name, partition_key, and sort_key',
                    )
                )
                continue

            gsi_name = gsi.name

            if gsi_name in seen_names:
                errors.append(
                    ValidationError(
                        path=f'{gsi_path}.name',
                        message=f"Duplicate GSI name '{gsi_name}' found in table",
                        suggestion=f"GSI names must be unique within a table. Choose a different name for GSI '{gsi_name}'",
                    )
                )
            else:
                seen_names.add(gsi_name)

        return errors

    def validate_gsi_mappings(
        self,
        mappings: list[GSIMapping],
        gsi_list: list[GSIDefinition],
        entity_path: str = 'gsi_mappings',
    ) -> list[ValidationError]:
        """Ensure entity mappings reference valid GSIs that exist in the table GSI list.

        Args:
            mappings: List of GSI mappings from entity definition
            gsi_list: List of GSI definitions from table configuration
            entity_path: Path context for error reporting

        Returns:
            List of ValidationError objects for invalid GSI references
        """
        errors = []

        if not mappings:
            return errors

        # Create set of valid GSI names for efficient lookup
        valid_gsi_names: set[str] = set()
        if gsi_list:
            valid_gsi_names = {gsi.name for gsi in gsi_list}

        for i, mapping in enumerate(mappings):
            mapping_path = f'{entity_path}[{i}]'

            if not isinstance(mapping, GSIMapping):
                errors.append(
                    ValidationError(
                        path=f'{mapping_path}',
                        message='GSI mapping must be a GSIMapping object',
                        suggestion='Ensure GSI mapping has name, pk_template, and sk_template fields',
                    )
                )
                continue

            mapping_name = mapping.name

            if mapping_name not in valid_gsi_names:
                if valid_gsi_names:
                    available_gsis = ', '.join(sorted(valid_gsi_names))
                    suggestion = f'Use one of the available GSI names: {available_gsis}'
                else:
                    suggestion = (
                        'Define GSI in table gsi_list before referencing it in entity mappings'
                    )

                errors.append(
                    ValidationError(
                        path=f'{mapping_path}.name',
                        message=f"GSI '{mapping_name}' referenced in entity mapping but not found in table gsi_list",
                        suggestion=suggestion,
                    )
                )

        return errors

    def validate_template_parameters(
        self,
        template: str,
        entity_fields: list[Field],
        template_path: str,
        template_type: str = 'template',
    ) -> list[ValidationError]:
        """Validate that all template parameters exist as entity fields using KeyTemplateParser.

        Args:
            template: Template string to validate (e.g., "USER#{user_id}#STATUS#{status}")
            entity_fields: List of Field objects from entity definition
            template_path: Path context for error reporting
            template_type: Type of template for error messages (e.g., "pk_template", "sk_template")

        Returns:
            List of ValidationError objects for missing template parameters
        """
        errors = []

        # First validate template syntax
        syntax_errors = self.template_parser.validate_template_syntax(template)
        for error in syntax_errors:
            # Update path to include template context
            error.path = f'{template_path}.{template_type}'
            errors.append(error)

        # If syntax is invalid, don't proceed with parameter validation
        if syntax_errors:
            return errors

        # Extract parameters from template
        try:
            parameters = self.template_parser.extract_parameters(template)
        except Exception as e:
            errors.append(
                ValidationError(
                    path=f'{template_path}.{template_type}',
                    message=f'Failed to extract parameters from template: {e}',
                    suggestion='Check template syntax and parameter format',
                )
            )
            return errors

        # Validate parameters exist in entity fields
        param_errors = self.template_parser.validate_parameters(parameters, entity_fields)
        for error in param_errors:
            # Update path to include template context
            error.path = f'{template_path}.{template_type}.{error.path.split(".")[-1]}'
            errors.append(error)

        return errors

    def validate_range_conditions(
        self, range_condition: str, pattern_path: str = 'range_condition'
    ) -> list[ValidationError]:
        """Validate range_condition against allowed DynamoDB operators.

        Delegates to RangeQueryValidator for common validation logic.

        Args:
            range_condition: Range condition value to validate
            pattern_path: Path context for error reporting

        Returns:
            List of ValidationError objects for invalid range conditions
        """
        return self.range_query_validator.validate_range_condition(range_condition, pattern_path)

    def validate_parameter_count(
        self, pattern: AccessPattern, pattern_path: str = 'access_pattern'
    ) -> list[ValidationError]:
        """Validate parameter count matches range condition requirements.

        Delegates to RangeQueryValidator for common validation logic.

        Args:
            pattern: AccessPattern object to validate
            pattern_path: Path context for error reporting

        Returns:
            List of ValidationError objects for incorrect parameter counts
        """
        return self.range_query_validator.validate_parameter_count(pattern, pattern_path)

    def validate_gsi_access_patterns(
        self,
        patterns: list[AccessPattern],
        gsi_list: list[GSIDefinition],
        entity_path: str = 'access_patterns',
    ) -> list[ValidationError]:
        """Validate GSI-related access patterns including index references and range conditions.

        Args:
            patterns: List of access patterns to validate
            gsi_list: List of GSI definitions from table configuration
            entity_path: Path context for error reporting

        Returns:
            List of ValidationError objects for GSI access pattern issues
        """
        errors = []

        if not patterns:
            return errors

        # Create set of valid GSI names
        valid_gsi_names: set[str] = set()
        if gsi_list:
            valid_gsi_names = {gsi.name for gsi in gsi_list}

        for i, pattern in enumerate(patterns):
            pattern_path = f'{entity_path}[{i}]'

            # Validate index_name if specified
            if pattern.index_name:
                if pattern.index_name not in valid_gsi_names:
                    if valid_gsi_names:
                        available_indexes = ', '.join(sorted(valid_gsi_names))
                        suggestion = f'Use one of the available GSI names: {available_indexes}'
                    else:
                        suggestion = (
                            'Define GSI in table gsi_list before referencing it in access patterns'
                        )

                    errors.append(
                        ValidationError(
                            path=f'{pattern_path}.index_name',
                            message=f"Access pattern references unknown GSI '{pattern.index_name}'",
                            suggestion=suggestion,
                        )
                    )

            # Validate range_condition if specified
            if pattern.range_condition:
                range_errors = self.validate_range_conditions(
                    pattern.range_condition, f'{pattern_path}.range_condition'
                )
                errors.extend(range_errors)

                # Validate parameter count for range conditions
                param_count_errors = self.validate_parameter_count(pattern, pattern_path)
                errors.extend(param_count_errors)

        return errors

    def validate_complete_gsi_configuration(
        self, table_data: dict[str, Any], table_path: str = 'table'
    ) -> list[ValidationError]:
        """Perform comprehensive GSI validation for a complete table configuration.

        This is the main orchestrator method that coordinates all GSI validation steps:
        1. Parse and validate GSI list
        2. Validate GSI name uniqueness
        3. Validate all entities' GSI configurations

        Args:
            table_data: Complete table configuration dictionary
            table_path: Path context for error reporting

        Returns:
            List of ValidationError objects for all GSI-related issues
        """
        errors = []

        # Parse GSI list from table
        gsi_list, parse_errors = self._parse_gsi_list(table_data, table_path)
        errors.extend(parse_errors)
        if parse_errors:
            return errors

        # Validate GSI name uniqueness
        gsi_name_errors = self.validate_gsi_names_unique(gsi_list, f'{table_path}.gsi_list')
        errors.extend(gsi_name_errors)

        # Validate entities if present
        if 'entities' in table_data:
            entity_errors = self._validate_entities_gsi_configuration(
                table_data['entities'], gsi_list, table_path
            )
            errors.extend(entity_errors)

        return errors

    # Private helper methods for validate_complete_gsi_configuration

    def _parse_gsi_list(
        self, table_data: dict[str, Any], table_path: str
    ) -> tuple[list[GSIDefinition], list[ValidationError]]:
        """Parse and validate GSI list from table data.

        Args:
            table_data: Complete table configuration dictionary
            table_path: Path context for error reporting

        Returns:
            Tuple of (gsi_list, errors) where gsi_list is the parsed GSI definitions
            and errors is a list of ValidationError objects
        """
        errors = []
        gsi_list = []

        if 'gsi_list' not in table_data or not table_data['gsi_list']:
            return gsi_list, errors

        if not isinstance(table_data['gsi_list'], list):
            errors.append(
                ValidationError(
                    path=f'{table_path}.gsi_list',
                    message='gsi_list must be an array',
                    suggestion='Change gsi_list to a JSON array',
                )
            )
            return gsi_list, errors

        try:
            for i, gsi in enumerate(table_data['gsi_list']):
                if not isinstance(gsi, dict):
                    errors.append(
                        ValidationError(
                            path=f'{table_path}.gsi_list[{i}]',
                            message='GSI definition must be an object',
                            suggestion='Ensure GSI has name, partition_key, and sort_key fields',
                        )
                    )
                    continue

                # Check for required fields (sort_key is optional)
                missing_fields = []
                for field in ['name', 'partition_key']:
                    if field not in gsi:
                        missing_fields.append(field)

                if missing_fields:
                    errors.append(
                        ValidationError(
                            path=f'{table_path}.gsi_list[{i}]',
                            message=f'GSI definition missing required fields: {", ".join(missing_fields)}',
                            suggestion=f'Add missing fields: {", ".join(missing_fields)}',
                        )
                    )
                    continue

                gsi_list.append(
                    GSIDefinition(
                        name=gsi['name'],
                        partition_key=gsi['partition_key'],
                        sort_key=gsi.get('sort_key'),
                    )
                )

        except Exception as e:
            errors.append(
                ValidationError(
                    path=f'{table_path}.gsi_list',
                    message=f'Failed to parse GSI definitions: {e}',
                    suggestion='Check GSI definition structure (name, partition_key, sort_key required)',
                )
            )

        return gsi_list, errors

    def _parse_entity_fields(
        self, entity_data: dict[str, Any], entity_path: str
    ) -> tuple[list[Field], list[ValidationError]]:
        """Parse entity fields from entity data.

        Args:
            entity_data: Entity configuration dictionary
            entity_path: Path context for error reporting

        Returns:
            Tuple of (entity_fields, errors) where entity_fields is the parsed Field objects
            and errors is a list of ValidationError objects
        """
        errors = []
        entity_fields = []

        if 'fields' not in entity_data:
            return entity_fields, errors

        if not isinstance(entity_data['fields'], list):
            errors.append(
                ValidationError(
                    path=f'{entity_path}.fields',
                    message='Entity fields must be an array',
                    suggestion='Change fields to a JSON array',
                )
            )
            return entity_fields, errors

        entity_fields = [
            Field(
                name=field.get('name', ''),
                type=field.get('type', ''),
                required=field.get('required', False),
                item_type=field.get('item_type'),
            )
            for field in entity_data['fields']
            if isinstance(field, dict) and 'name' in field
        ]

        return entity_fields, errors

    def _validate_entity_gsi_mappings(
        self,
        entity_data: dict[str, Any],
        entity_fields: list[Field],
        gsi_list: list[GSIDefinition],
        entity_path: str,
    ) -> list[ValidationError]:
        """Validate GSI mappings for a single entity.

        Args:
            entity_data: Entity configuration dictionary
            entity_fields: Parsed entity fields
            gsi_list: List of GSI definitions from table
            entity_path: Path context for error reporting

        Returns:
            List of ValidationError objects for GSI mapping issues
        """
        errors = []

        if 'gsi_mappings' not in entity_data or not entity_data['gsi_mappings']:
            return errors

        if not isinstance(entity_data['gsi_mappings'], list):
            errors.append(
                ValidationError(
                    path=f'{entity_path}.gsi_mappings',
                    message='GSI mappings must be an array',
                    suggestion='Change gsi_mappings to a JSON array',
                )
            )
            return errors

        try:
            gsi_mappings = []
            for i, mapping in enumerate(entity_data['gsi_mappings']):
                if not isinstance(mapping, dict):
                    errors.append(
                        ValidationError(
                            path=f'{entity_path}.gsi_mappings[{i}]',
                            message='GSI mapping must be an object',
                            suggestion='Ensure GSI mapping has name, pk_template, and sk_template fields',
                        )
                    )
                    continue

                # Check for required fields (sk_template is optional)
                missing_fields = []
                for field in ['name', 'pk_template']:
                    if field not in mapping:
                        missing_fields.append(field)

                if missing_fields:
                    errors.append(
                        ValidationError(
                            path=f'{entity_path}.gsi_mappings[{i}]',
                            message=f'GSI mapping missing required fields: {", ".join(missing_fields)}',
                            suggestion=f'Add missing fields: {", ".join(missing_fields)}',
                        )
                    )
                    continue

                gsi_mappings.append(
                    GSIMapping(
                        name=mapping['name'],
                        pk_template=mapping['pk_template'],
                        sk_template=mapping.get('sk_template'),
                    )
                )

            # Validate GSI mapping references
            mapping_errors = self.validate_gsi_mappings(
                gsi_mappings, gsi_list, f'{entity_path}.gsi_mappings'
            )
            errors.extend(mapping_errors)

            # Validate GSI mapping templates
            for i, mapping in enumerate(gsi_mappings):
                mapping_path = f'{entity_path}.gsi_mappings[{i}]'

                # Validate pk_template
                pk_errors = self.validate_template_parameters(
                    mapping.pk_template, entity_fields, mapping_path, 'pk_template'
                )
                errors.extend(pk_errors)

                # Validate sk_template if present (it's optional)
                if mapping.sk_template is not None:
                    sk_errors = self.validate_template_parameters(
                        mapping.sk_template, entity_fields, mapping_path, 'sk_template'
                    )
                    errors.extend(sk_errors)

        except Exception as e:
            errors.append(
                ValidationError(
                    path=f'{entity_path}.gsi_mappings',
                    message=f'Failed to parse GSI mappings: {e}',
                    suggestion='Check GSI mapping structure (name, pk_template, sk_template required)',
                )
            )

        return errors

    def _validate_entity_access_patterns(
        self, entity_data: dict[str, Any], gsi_list: list[GSIDefinition], entity_path: str
    ) -> list[ValidationError]:
        """Validate access patterns for a single entity.

        Args:
            entity_data: Entity configuration dictionary
            gsi_list: List of GSI definitions from table
            entity_path: Path context for error reporting

        Returns:
            List of ValidationError objects for access pattern issues
        """
        errors = []

        if 'access_patterns' not in entity_data or not isinstance(
            entity_data['access_patterns'], list
        ):
            return errors

        try:
            access_patterns = []
            for pattern_data in entity_data['access_patterns']:
                if isinstance(pattern_data, dict):
                    # Extract parameters
                    parameters = []
                    if 'parameters' in pattern_data and isinstance(
                        pattern_data['parameters'], list
                    ):
                        parameters = pattern_data['parameters']

                    access_patterns.append(
                        AccessPattern(
                            pattern_id=pattern_data.get('pattern_id', 0),
                            name=pattern_data.get('name', ''),
                            description=pattern_data.get('description', ''),
                            operation=pattern_data.get('operation', ''),
                            parameters=parameters,
                            return_type=pattern_data.get('return_type', ''),
                            index_name=pattern_data.get('index_name'),
                            range_condition=pattern_data.get('range_condition'),
                        )
                    )

            # Validate GSI access patterns
            pattern_errors = self.validate_gsi_access_patterns(
                access_patterns, gsi_list, f'{entity_path}.access_patterns'
            )
            errors.extend(pattern_errors)

        except Exception as e:
            errors.append(
                ValidationError(
                    path=f'{entity_path}.access_patterns',
                    message=f'Failed to parse access patterns: {e}',
                    suggestion='Check access pattern structure',
                )
            )

        return errors

    def _validate_entities_gsi_configuration(
        self, entities: dict[str, Any], gsi_list: list[GSIDefinition], table_path: str
    ) -> list[ValidationError]:
        """Validate GSI configuration for all entities in a table.

        Args:
            entities: Dictionary of entity configurations
            gsi_list: List of GSI definitions from table
            table_path: Path context for error reporting

        Returns:
            List of ValidationError objects for all entity GSI issues
        """
        errors = []

        if not isinstance(entities, dict):
            return errors

        for entity_name, entity_data in entities.items():
            entity_path = f'{table_path}.entities.{entity_name}'

            if not isinstance(entity_data, dict):
                continue

            # Parse entity fields
            entity_fields, field_errors = self._parse_entity_fields(entity_data, entity_path)
            errors.extend(field_errors)
            if field_errors:
                continue

            # Validate GSI mappings
            mapping_errors = self._validate_entity_gsi_mappings(
                entity_data, entity_fields, gsi_list, entity_path
            )
            errors.extend(mapping_errors)

            # Validate access patterns
            pattern_errors = self._validate_entity_access_patterns(
                entity_data, gsi_list, entity_path
            )
            errors.extend(pattern_errors)

        return errors
