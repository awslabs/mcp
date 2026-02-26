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

import re
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.key_template_parser import (
    KeyTemplateParser,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.utils import (
    detect_item_collection,
    filter_conflicting_patterns,
    get_crud_method_names,
    get_sk_prefix,
    to_snake_case,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.generators.access_pattern_mapper import (
    AccessPatternMapper,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.generators.base_generator import (
    BaseGenerator,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.generators.sample_generators import (
    SampleValueGenerator,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.output.output_manager import (
    GeneratedFile,
    GenerationResult,
    OutputManager,
)
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from typing import Any


class Jinja2Generator(BaseGenerator):
    """Generator using Jinja2 templates."""

    def __init__(
        self,
        schema_path: str,
        templates_dir: str = None,
        language: str = 'python',
        usage_data_path: str = None,
    ):
        """Initialize the Jinja2 generator with schema and templates."""
        super().__init__(schema_path, language)

        self.access_pattern_mapper = AccessPatternMapper(self.language_config, self.type_mapper)
        self.sample_generator = SampleValueGenerator(language, usage_data_path)
        self.template_parser = KeyTemplateParser()

        # Setup template environment
        if templates_dir is None:
            # Use language-specific templates directory
            generator_dir = Path(__file__).parent.parent
            templates_dir = generator_dir / 'languages' / language / 'templates'

        # Note: autoescape is explicitly set to False for code generation
        # This is appropriate because:
        # 1. We're generating source code (Python, TypeScript, etc.), not HTML/XML
        # 2. HTML escaping would corrupt code syntax (e.g., <, >, & in code)
        # 3. All template inputs come from validated schema files, not user web input
        # 4. Generated code is written to files, not rendered in browsers
        # Security: Schema validation ensures all inputs are safe before template rendering
        self.env = Environment(  # nosec B701 - Content is NOT HTML and NOT served
            loader=FileSystemLoader(templates_dir),
            autoescape=False,  # Explicitly disabled for code generation (not HTML)
        )

        # Add custom filter for parameter substitution
        def substitute_params(template, params):
            """Replace {param} or {param:format} with {entity.param} or {entity.param:format}.

            Handles Python format specifiers like :05d, :.2f, :>10, etc.
            Uses regex to match parameter with optional format spec.
            """
            result = template
            for param in params:
                # Match {param} or {param:format_spec}
                pattern = r'\{' + re.escape(param) + r'(:[^}]*)?\}'
                replacement = r'{entity.' + param + r'\1}'
                result = re.sub(pattern, replacement, result)
            return result

        def substitute_self_params(template, params):
            """Replace {param} with {self.param} for all params in the list."""
            result = template
            for param in params:
                result = result.replace(f'{{{param}}}', f'{{self.{param}}}')
            return result

        self.env.filters['substitute_params'] = substitute_params
        self.env.filters['substitute_self_params'] = substitute_self_params
        self.env.filters['to_snake_case'] = to_snake_case

        # Add regex_findall filter for template parameter extraction
        def regex_findall(text, pattern):
            """Extract all matches of a regex pattern from text."""
            return re.findall(pattern, text)

        self.env.filters['regex_findall'] = regex_findall

        # Add filter to get resolvable access pattern parameters
        def filter_resolvable_access_pattern_params(
            parameters, entity_name, all_entities, get_param_value_func, pattern=None
        ):
            """Filter access pattern parameters to only those that can be resolved to values.

            Used as a Jinja2 filter in usage_examples_template.j2 to ensure generated
            method calls only include parameters that exist in the entity schema or
            usage_data. This keeps usage examples in sync with generated repository
            method signatures (which use the same filtering logic in format_parameters).

            Args:
                parameters: List of parameter dicts from access pattern definition,
                    each with 'name' and 'type' keys
                entity_name: Name of the entity (e.g., 'User', 'Order')
                all_entities: Dict of all entity configurations keyed by entity name
                get_param_value_func: Function to resolve parameter to a value,
                    returns None if parameter cannot be resolved
                pattern: Optional access pattern dict for context (e.g., range_condition)

            Returns:
                List of resolved parameter values (strings), excluding any parameters
                where get_param_value_func returned None

            Example:
                Template usage:
                    {%- set valid_params = pattern.parameters | filter_resolvable_access_pattern_params(
                        entity, entities, get_parameter_value, pattern) %}

                If parameters = [{"name": "user_id", ...}, {"name": "phantom", ...}]
                and "phantom" doesn't exist in entity fields, returns only the
                resolved value for user_id.

            Note:
                This filter must stay in sync with format_parameters() in
                generate_repository() - both use get_parameter_value() to determine
                parameter validity. See test_phantom_parameter_excluded_from_both_*
                for the coupling test.
            """
            valid_values = []
            for idx, param in enumerate(parameters):
                # For range query parameters, always include them (they're intentionally different from field names)
                # Range parameters are typically the 2nd+ parameters when range_condition is present
                is_range_param = (
                    pattern
                    and pattern.get('range_condition')
                    and idx > 0  # Not the first param (partition key)
                )

                if is_range_param:
                    # Range parameters are always valid, get their value
                    # The wrapper will automatically enable fallback generation
                    value = get_param_value_func(param, entity_name, all_entities)
                    if value is not None:
                        valid_values.append(value)
                    continue

                # For non-range parameters, check if they exist
                value = get_param_value_func(param, entity_name, all_entities)
                if value is not None:
                    valid_values.append(value)
            return valid_values

        self.env.filters['filter_resolvable_access_pattern_params'] = (
            filter_resolvable_access_pattern_params
        )

        try:
            self.entity_template = self.env.get_template('entity_template.j2')
        except Exception as e:
            raise FileNotFoundError(
                f"Required template 'entity_template.j2' not found in {templates_dir}. "
                f'This template is essential for entity generation. Error: {e}'
            )

        try:
            self.repository_template = self.env.get_template('repository_template.j2')
        except Exception as e:
            raise FileNotFoundError(
                f"Required template 'repository_template.j2' not found in {templates_dir}. "
                f'This template is essential for repository generation. Error: {e}'
            )

        # Load header templates
        try:
            self.entities_header_template = self.env.get_template('entities_header.j2')
        except Exception as e:
            print(f'Warning: Could not load entities header template: {e}')
            self.entities_header_template = None

        try:
            self.repositories_header_template = self.env.get_template('repositories_header.j2')
        except Exception as e:
            print(f'Warning: Could not load repositories header template: {e}')
            self.repositories_header_template = None

        # Load usage example template if it exists
        try:
            self.usage_examples_template = self.env.get_template('usage_examples_template.j2')
        except Exception as e:
            print(f'Warning: Could not load usage examples template: {e}')
            self.usage_examples_template = None

        # Load transaction service template if it exists
        try:
            self.transaction_service_template = self.env.get_template(
                'transaction_service_template.j2'
            )
        except Exception as e:
            print(f'Warning: Could not load transaction service template: {e}')
            self.transaction_service_template = None

    def _is_pure_field_reference(self, template: str) -> bool:
        """Check if template is a pure field reference like '{field_name}'.

        A pure field reference contains only a single {field} placeholder with no
        additional text. This is important for numeric fields where we want to
        pass the raw value instead of converting to string.

        Args:
            template: Template string to check

        Returns:
            True if template is exactly '{field_name}', False otherwise

        Examples:
            >>> _is_pure_field_reference('{score}')  # True
            >>> _is_pure_field_reference('SCORE#{score}')  # False
            >>> _is_pure_field_reference('{user_id}#{score}')  # False
        """
        if not template:
            return False
        # Check if template matches pattern: starts with {, ends with }, single field
        return bool(re.match(r'^\{(\w+)\}$', template))

    def _get_field_type(self, field_name: str, fields: list[dict[str, Any]]) -> str | None:
        """Get the type of a field by name.

        Args:
            field_name: Name of the field to look up
            fields: List of field definitions

        Returns:
            Field type string or None if not found
        """
        for field in fields:
            if field.get('name') == field_name:
                return field.get('type')
        return None

    def _is_numeric_type(self, field_type: str | None) -> bool:
        """Check if a field type is numeric (integer or decimal).

        Args:
            field_type: The field type string

        Returns:
            True if type is 'integer' or 'decimal'
        """
        return field_type in ('integer', 'decimal')

    def _check_template_is_pure_numeric(
        self, template: str, params: list[str], fields: list[dict[str, Any]]
    ) -> bool:
        """Check if a template is a pure reference to a numeric field.

        This returns True only when:
        1. The template is a pure field reference (e.g., '{score}')
        2. The referenced field is numeric (integer or decimal)

        Args:
            template: The template string
            params: Extracted parameters from the template
            fields: List of field definitions

        Returns:
            True if template is a pure numeric field reference
        """
        if not self._is_pure_field_reference(template):
            return False
        if len(params) != 1:
            return False
        field_type = self._get_field_type(params[0], fields)
        return self._is_numeric_type(field_type)

    def _extract_template_fields(self, template: str | list[str] | None) -> list[str]:
        """Extract field names from template(s), handling both string and list.

        Args:
            template: Single template string, list of templates, or None

        Returns:
            List of field names extracted from {field_name} placeholders
        """
        if isinstance(template, list):
            fields = []
            for tmpl in template:
                fields.extend(re.findall(r'\{([^}]+)\}', tmpl))
            return fields
        elif template:
            return re.findall(r'\{([^}]+)\}', template)
        return []

    def _process_key_template(
        self, template: str | list[str] | None, fields: list[dict[str, Any]], key_name: str = 'key'
    ) -> dict[str, Any]:
        """Process a key template (PK or SK) and return metadata.

        Args:
            template: Template string, list of templates, or None
            fields: List of field definitions for numeric type checking
            key_name: Name of the key for error messages (e.g., 'partition_key', 'sort_key')

        Returns:
            Dictionary with keys: params, is_multi_attribute, templates, is_numeric

        Raises:
            ValueError: If multi-attribute key has invalid number of attributes (not 1-4)
        """
        if isinstance(template, list):
            # Multi-attribute key
            if not (1 <= len(template) <= 4):
                raise ValueError(
                    f'Multi-attribute {key_name} must have 1-4 attributes, got {len(template)}'
                )

            all_params = []
            for tmpl in template:
                all_params.extend(self.template_parser.extract_parameters(tmpl))

            return {
                'params': all_params,
                'is_multi_attribute': True,
                'templates': template,
                'is_numeric': False,  # Multi-attribute keys return tuples, not single numeric values
            }
        elif template:
            # Single-attribute key
            params = self.template_parser.extract_parameters(template)
            return {
                'params': params,
                'is_multi_attribute': False,
                'templates': None,
                'is_numeric': self._check_template_is_pure_numeric(template, params, fields),
            }
        else:
            # No key
            return {
                'params': [],
                'is_multi_attribute': False,
                'templates': None,
                'is_numeric': False,
            }

    def _preprocess_entity_config(self, entity_config: dict[str, Any]) -> dict[str, Any]:
        """Preprocess entity config to extract template parameters and add GSI data."""
        # Create a copy to avoid modifying the original
        processed_config = entity_config.copy()
        fields = entity_config.get('fields', [])

        # Extract parameters from main table templates
        pk_template = entity_config.get('pk_template', '')
        sk_template = entity_config.get('sk_template', '')

        processed_config['pk_params'] = self.template_parser.extract_parameters(pk_template)
        processed_config['sk_params'] = self.template_parser.extract_parameters(sk_template)

        # Check if PK/SK are pure numeric field references
        processed_config['pk_is_numeric'] = self._check_template_is_pure_numeric(
            pk_template, processed_config['pk_params'], fields
        )
        processed_config['sk_is_numeric'] = self._check_template_is_pure_numeric(
            sk_template, processed_config['sk_params'], fields
        )

        # Process GSI mappings if they exist
        gsi_mappings = entity_config.get('gsi_mappings', [])
        processed_gsi_mappings = []

        for gsi_mapping in gsi_mappings:
            processed_mapping = gsi_mapping.copy()
            gsi_pk_template = gsi_mapping.get('pk_template', '')
            gsi_sk_template = gsi_mapping.get('sk_template', '')

            # Add safe_name for Python method names (snake_case, no hyphens)
            # Keep original 'name' for DynamoDB IndexName and documentation
            original_name = gsi_mapping.get('name', '')
            processed_mapping['safe_name'] = to_snake_case(original_name)

            # Process partition key template
            try:
                pk_metadata = self._process_key_template(
                    gsi_pk_template, fields, f"partition_key for GSI '{original_name}'"
                )
                processed_mapping['pk_params'] = pk_metadata['params']
                processed_mapping['pk_is_multi_attribute'] = pk_metadata['is_multi_attribute']
                processed_mapping['pk_templates'] = pk_metadata['templates']
                processed_mapping['pk_is_numeric'] = pk_metadata['is_numeric']
            except ValueError as e:
                raise ValueError(f"Invalid GSI '{original_name}': {e}") from e

            # Process sort key template
            try:
                sk_metadata = self._process_key_template(
                    gsi_sk_template, fields, f"sort_key for GSI '{original_name}'"
                )
                processed_mapping['sk_params'] = sk_metadata['params']
                processed_mapping['sk_is_multi_attribute'] = sk_metadata['is_multi_attribute']
                processed_mapping['sk_templates'] = sk_metadata['templates']
                processed_mapping['sk_is_numeric'] = sk_metadata['is_numeric']
            except ValueError as e:
                raise ValueError(f"Invalid GSI '{original_name}': {e}") from e

            processed_gsi_mappings.append(processed_mapping)

        processed_config['gsi_mappings'] = processed_gsi_mappings

        return processed_config

    def _check_needs_any_import(self, all_tables: list[dict[str, Any]]) -> bool:
        """Check if Any import is needed for dict return types.

        Returns True if any access pattern uses a GSI with KEYS_ONLY projection,
        unsafe INCLUDE projection, or has mixed_data return type.
        """
        for table in all_tables:
            gsi_list = table.get('gsi_list', [])
            entities = table.get('entities', {})

            for entity_name, entity_config in entities.items():
                for pattern in entity_config.get('access_patterns', []):
                    # Check for mixed_data return type (item collections)
                    if pattern.get('return_type') == 'mixed_data':
                        return True

                    # Check if pattern uses a GSI
                    if 'index_name' not in pattern:
                        continue

                    # Find the GSI definition
                    gsi = next((g for g in gsi_list if g['name'] == pattern['index_name']), None)
                    if not gsi:
                        continue

                    # KEYS_ONLY always returns dict
                    if gsi.get('projection') == 'KEYS_ONLY':
                        return True

                    # INCLUDE might return dict if has required non-projected fields
                    if gsi.get('projection') == 'INCLUDE':
                        # Check if this is unsafe INCLUDE (has required non-projected fields)
                        if self._is_unsafe_include_projection(
                            gsi, entity_config, table.get('table_config', {})
                        ):
                            return True

        return False

    def _is_unsafe_include_projection(
        self, gsi: dict[str, Any], entity_config: dict[str, Any], table_config: dict[str, Any]
    ) -> bool:
        """Check if INCLUDE projection has required fields not projected (unsafe).

        Returns True if the projection will return dict instead of Entity.
        """
        projected = set(gsi.get('included_attributes', []))

        # Key fields are always projected by DynamoDB
        key_fields = {table_config.get('partition_key')}
        if table_config.get('sort_key'):
            key_fields.add(table_config['sort_key'])

        # Extract GSI template fields (also always projected)
        gsi_mapping = next(
            (m for m in entity_config.get('gsi_mappings', []) if m['name'] == gsi['name']), None
        )
        if gsi_mapping:
            # Extract field names from templates (handles both string and list)
            pk_fields = self._extract_template_fields(gsi_mapping.get('pk_template'))
            sk_fields = self._extract_template_fields(gsi_mapping.get('sk_template'))
            key_fields.update(pk_fields + sk_fields)

        # Check if any non-projected, non-key fields are required
        for field in entity_config.get('fields', []):
            if field['name'] in projected or field['name'] in key_fields:
                continue  # Field is projected
            if field.get('required', False):
                return True  # Has required field not projected - unsafe!

        return False

    def generate_entity(self, entity_name: str, entity_config: dict[str, Any]) -> str:
        """Generate entity code using Jinja2."""
        # Preprocess entity config to extract parameters
        processed_config = self._preprocess_entity_config(entity_config)

        return self.entity_template.render(
            entity_name=entity_name,
            entity_config=processed_config,
            map_field_type=self.type_mapper.map_field_type,
        )

    def generate_repository(
        self,
        entity_name: str,
        entity_config: dict[str, Any],
        table_config: dict[str, Any] = None,
        table_data: dict[str, Any] = None,
    ) -> str:
        """Generate repository code using Jinja2."""
        # Preprocess entity config to extract parameters
        processed_config = self._preprocess_entity_config(entity_config)

        entity_name_snake = to_snake_case(entity_name)
        crud_methods = get_crud_method_names(entity_name, self.language_config)
        filtered_patterns, crud_consistent_read = filter_conflicting_patterns(
            processed_config.get('access_patterns', []),
            crud_methods,
            entity_name=entity_name,
            entity_config=processed_config,
        )

        def format_parameters(params, pattern=None):
            """Format parameter list for method signature, filtering out non-existent fields.

            Args:
                params: List of parameter dicts from access pattern
                pattern: Optional access pattern dict for context (e.g., range_condition)

            Returns:
                Comma-separated string of formatted parameters
            """
            formatted = []
            for idx, param in enumerate(params):
                # For range query parameters, always include them (they're intentionally different from field names)
                # Range parameters are typically the 2nd+ parameters when range_condition is present
                is_range_param = (
                    pattern
                    and pattern.get('range_condition')
                    and idx > 0  # Not the first param (partition key)
                )

                if is_range_param:
                    # Range parameters are always valid, don't skip
                    param_type = self.type_mapper.map_parameter_type(param)
                    formatted.append(f'{param["name"]}: {param_type}')
                    continue

                # For non-range parameters, check if they exist in entity fields or usage_data
                param_value = self.sample_generator.get_parameter_value(
                    param, entity_name, {entity_name: processed_config}
                )
                if param_value is None:
                    # Parameter doesn't exist in entity, skip it
                    continue

                param_type = self.type_mapper.map_parameter_type(param)
                formatted.append(f'{param["name"]}: {param_type}')
            # Return empty string if no valid parameters (avoid trailing comma)
            return ', '.join(formatted) if formatted else ''

        # table_config should always be provided
        if table_config is None:
            raise ValueError('table_config is required')

        def get_gsi_mapping_for_index(index_name):
            """Get GSI mapping for a specific index name."""
            if not processed_config.get('gsi_mappings'):
                return None
            for mapping in processed_config['gsi_mappings']:
                if mapping['name'] == index_name:
                    return mapping
            return None

        return self.repository_template.render(
            entity_name=entity_name,
            entity_name_snake=entity_name_snake,
            entity_config=processed_config,
            filtered_access_patterns=filtered_patterns,
            crud_consistent_read=crud_consistent_read,
            table_config=table_config,
            table_data=table_data,
            map_return_type=lambda rt, en: self.type_mapper.map_return_type(rt, en),
            format_parameters=format_parameters,
            get_gsi_mapping_for_index=get_gsi_mapping_for_index,
            detect_item_collection=detect_item_collection,
            get_sk_prefix=get_sk_prefix,
        )

    def generate_repository_with_mapping(
        self,
        entity_name: str,
        entity_config: dict[str, Any],
        table_config: dict[str, Any] = None,
        table_data: dict[str, Any] = None,
    ) -> tuple[str, dict[str, Any]]:
        """Generate repository code and return mapping data."""
        # Preprocess entity config to extract parameters
        processed_config = self._preprocess_entity_config(entity_config)

        # Generate mapping for all access patterns
        entity_mapping = self.access_pattern_mapper.generate_mapping(
            entity_name, processed_config, table_data.get('gsi_list') if table_data else None
        )

        # Generate the repository code
        repo_code = self.generate_repository(entity_name, entity_config, table_config, table_data)

        return repo_code, entity_mapping

    def _format_parameters(self, params: list[dict[str, Any]]) -> str:
        """Format parameter list for transaction method signature.

        Args:
            params: List of parameter dicts from cross-table pattern

        Returns:
            Comma-separated string of formatted parameters
        """
        formatted = []
        for param in params:
            param_type = self.type_mapper.map_parameter_type(param)
            formatted.append(f'{param["name"]}: {param_type}')
        return ', '.join(formatted) if formatted else ''

    def _get_param_description(self, param: dict[str, Any]) -> str:
        """Get description for a parameter in docstring.

        Args:
            param: Parameter dict from cross-table pattern

        Returns:
            Description string for the parameter
        """
        param_type = self.type_mapper.map_parameter_type(param)

        if param.get('type') == 'entity':
            return f'{param_type} entity to process'
        else:
            return f'{param_type} value'

    def _get_return_description(self, pattern: dict[str, Any]) -> str:
        """Get description for return value in docstring.

        Args:
            pattern: Cross-table pattern dict

        Returns:
            Description string for the return value
        """
        return_type = pattern.get('return_type', 'boolean')
        operation = pattern.get('operation', 'TransactWrite')

        if return_type == 'boolean':
            return 'True if transaction succeeded, False otherwise'
        elif return_type == 'object':
            if operation == 'TransactGet':
                return 'Dictionary containing retrieved entities'
            return 'Result object from transaction'
        elif return_type == 'array':
            return 'List of results from transaction'
        else:
            return 'Transaction result'

    def _get_table_list(self, pattern: dict[str, Any]) -> str:
        """Get comma-separated list of tables involved in pattern.

        Args:
            pattern: Cross-table pattern dict

        Returns:
            Comma-separated string of table names
        """
        entities_involved = pattern.get('entities_involved', [])
        tables = [entity_inv['table'] for entity_inv in entities_involved]
        return ', '.join(tables)

    def _get_entity_imports(self, cross_table_patterns: list[dict[str, Any]]) -> str:
        """Get comma-separated list of unique entity names for imports.

        Args:
            cross_table_patterns: List of cross-table pattern dicts

        Returns:
            Comma-separated string of entity names for import statement
        """
        entity_names = self._extract_entity_names(cross_table_patterns)
        return ', '.join(sorted(entity_names))

    def _extract_entity_names(self, cross_table_patterns: list[dict[str, Any]]) -> set[str]:
        """Extract unique entity names from cross-table patterns.

        Args:
            cross_table_patterns: List of cross-table pattern dicts

        Returns:
            Set of unique entity names
        """
        entity_names = set()
        for pattern in cross_table_patterns:
            for entity_inv in pattern.get('entities_involved', []):
                entity_names.add(entity_inv['entity'])
        return entity_names

    def _build_entities_involved_list(self, pattern: dict[str, Any]) -> list[dict[str, Any]]:
        """Build entities_involved array with table, entity, and action.

        Args:
            pattern: Cross-table pattern definition

        Returns:
            List of entity involvement dicts with table, entity, and action fields
        """
        entities_involved = []
        for entity_inv in pattern.get('entities_involved', []):
            entities_involved.append(
                {
                    'table': entity_inv['table'],
                    'entity': entity_inv['entity'],
                    'action': entity_inv['action'],
                }
            )
        return entities_involved

    def _create_transaction_pattern_mapping(self, pattern: dict[str, Any]) -> dict[str, Any]:
        """Create access pattern mapping entry for a cross-table transaction pattern.

        Args:
            pattern: Cross-table pattern definition from schema

        Returns:
            Dictionary with pattern metadata for access_pattern_mapping.json
        """
        # Get the actual return type
        schema_return_type = pattern.get('return_type', 'boolean')
        operation = pattern.get('operation', 'TransactWrite')

        # Map return type using type mapper
        if self.type_mapper:
            actual_return_type = self.type_mapper.map_return_type(schema_return_type, None)
        else:
            actual_return_type = schema_return_type

        # Build entities_involved array with table, entity, and action
        entities_involved = self._build_entities_involved_list(pattern)

        # Create mapping entry with service field instead of repository
        mapping_entry = {
            'pattern_id': pattern['pattern_id'],
            'description': pattern['description'],
            'service': 'TransactionService',
            'method_name': pattern['name'],
            'parameters': pattern.get('parameters', []),
            'return_type': actual_return_type,
            'operation': operation,
            'entities_involved': entities_involved,
            'transaction_type': 'cross_table',
        }

        return mapping_entry

    def generate_transaction_service(
        self,
        cross_table_patterns: list[dict[str, Any]],
        all_entities: dict[str, Any],
    ) -> str:
        """Generate transaction service code using Jinja2.

        Args:
            cross_table_patterns: List of cross-table pattern definitions from schema
            all_entities: Dictionary of all entity configurations keyed by entity name

        Returns:
            Generated transaction service code as a string, or empty string if no patterns
        """
        if not self.transaction_service_template:
            return ''

        # Return empty string if no patterns to generate
        if not cross_table_patterns:
            return ''

        # Extract unique entity names for imports
        entity_names = self._extract_entity_names(cross_table_patterns)

        # Build entity to table mapping for key lookups
        entity_to_table_config = {}
        for table in self.schema['tables']:
            table_config = table['table_config']
            for entity_name in table['entities'].keys():
                entity_to_table_config[entity_name] = table_config

        # Render template with all required context
        return self.transaction_service_template.render(
            cross_table_patterns=cross_table_patterns,
            entity_imports=', '.join(sorted(entity_names)),
            entity_to_table_config=entity_to_table_config,
            format_parameters=self._format_parameters,
            map_return_type=self.type_mapper.map_return_type,
            get_param_description=self._get_param_description,
            get_return_description=self._get_return_description,
            format_table_names=self._get_table_list,
        )

    def generate_usage_examples(
        self,
        access_pattern_mapping: dict[str, Any],
        all_entities: dict[str, Any],
        all_tables: list[dict[str, Any]],
        cross_table_patterns: list[dict[str, Any]] | None = None,
    ) -> str:
        """Generate usage examples using Jinja2.

        Args:
            access_pattern_mapping: Mapping of access pattern IDs to implementations
            all_entities: Dictionary of all entity configurations
            all_tables: List of all table configurations
            cross_table_patterns: List of all cross-table patterns (all operation types)
        """
        if not self.usage_examples_template:
            return '# Usage examples template not found'

        entity_names = list(all_entities.keys())
        repository_names = [f'{name}Repository' for name in entity_names]

        # For single table scenarios, use the first table's config
        table_config = all_tables[0]['table_config'] if all_tables else {}

        # Default to empty list if None
        if cross_table_patterns is None:
            cross_table_patterns = []

        def generate_sample_value_wrapper(field: dict[str, Any], **kwargs) -> str:
            """Wrapper to handle use_access_pattern_data flag."""
            use_access_pattern_data = kwargs.pop('use_access_pattern_data', False)
            use_transaction_data = kwargs.pop('use_transaction_data', False)
            if use_access_pattern_data:
                kwargs['use_access_pattern_data'] = True
            if use_transaction_data:
                kwargs['use_transaction_data'] = True
            return self.sample_generator.generate_sample_value(field, **kwargs)

        def get_parameter_value_wrapper(
            param: dict, entity_name: str, all_entities: dict
        ) -> str | None:
            """Wrapper that enables smart defaults for all unknown parameters.

            The filter_resolvable_access_pattern_params will handle whether to include
            the parameter based on range_condition logic.
            """
            # Always enable fallback - let the filter decide whether to use the value
            return self.sample_generator.get_parameter_value(
                param, entity_name, all_entities, generate_fallback=True
            )

        return self.usage_examples_template.render(
            entity_names=entity_names,
            repository_names=repository_names,
            entities=all_entities,
            table_config=table_config,
            tables=all_tables,
            access_patterns=access_pattern_mapping,
            cross_table_patterns=cross_table_patterns,
            generate_sample_value=generate_sample_value_wrapper,
            get_updatable_field=self.sample_generator.get_updatable_field,
            generate_update_value=self.sample_generator.generate_update_value,
            get_all_key_params=self.sample_generator.get_all_key_params,
            get_parameter_value=get_parameter_value_wrapper,
            get_entity_config=lambda entity_type: all_entities.get(entity_type, {}),
            to_snake_case=to_snake_case,
        )

    def generate_all(self, output_dir: str, generate_usage_examples: bool = False) -> None:
        """Generate all entities and repositories."""
        all_tables = self.schema['tables']

        entities_code = []
        repositories_code = []
        access_pattern_mapping = {}
        all_entity_names = []
        all_entities = {}

        # Iterate through all tables
        for table in all_tables:
            table_config = table['table_config']
            table_entities = table['entities']

            # Process each entity in the current table
            for entity_name, entity_config in table_entities.items():
                # Generate entity
                entity_code = self.generate_entity(entity_name, entity_config)
                entities_code.append(entity_code)

                # Track all entities for imports and usage examples
                all_entity_names.append(entity_name)
                all_entities[entity_name] = entity_config

                # Generate repository with table-specific configuration
                repo_code, entity_mapping = self.generate_repository_with_mapping(
                    entity_name, entity_config, table_config, table
                )
                repositories_code.append(repo_code)
                access_pattern_mapping.update(entity_mapping)

        # Preprocess all entities for usage examples
        preprocessed_entities = {}
        for entity_name, entity_config in all_entities.items():
            preprocessed_entities[entity_name] = self._preprocess_entity_config(entity_config)

        # Generate usage examples if requested
        usage_examples_code = ''
        if generate_usage_examples:
            # Pass all cross-table patterns to usage examples
            # The template will handle different operation types appropriately
            cross_table_patterns = self.schema.get('cross_table_access_patterns', [])

            usage_examples_code = self.generate_usage_examples(
                access_pattern_mapping,
                preprocessed_entities,
                all_tables,
                cross_table_patterns=cross_table_patterns,
            )

        # Check if Any import is needed (for dict return types from KEYS_ONLY or unsafe INCLUDE projections)
        needs_any_import = self._check_needs_any_import(all_tables)

        # Generate headers using templates
        entities_header = ''
        if self.entities_header_template:
            entities_header = self.entities_header_template.render()

        repositories_header = ''
        if self.repositories_header_template:
            repositories_header = self.repositories_header_template.render(
                needs_any_import=needs_any_import, entity_names=all_entity_names
            )

        # Create complete file content for entities
        entities_content = ''
        if entities_header:
            entities_content += entities_header + '\n\n'
        entities_content += '\n\n'.join(entities_code) + '\n'

        # Create complete file content for repositories
        repositories_content = ''
        if repositories_header:
            repositories_content += repositories_header + '\n\n'
        repositories_content += '\n\n'.join(repositories_code) + '\n'

        # Create file manifest for flexible output
        generated_files = []

        # Add entities file with complete content
        generated_files.append(
            GeneratedFile(
                path=self.language_config.file_patterns['entities'],
                description=f'{len(entities_code)} entities',
                category='entities',
                content=entities_content,
                count=len(entities_code),
            )
        )

        # Add repositories file with complete content
        generated_files.append(
            GeneratedFile(
                path=self.language_config.file_patterns['repositories'],
                description=f'{len(repositories_code)} repositories',
                category='repositories',
                content=repositories_content,
                count=len(repositories_code),
            )
        )

        # Add support files from language config (no content - will be copied)
        for support_file in self.language_config.support_files:
            generated_files.append(
                GeneratedFile(
                    path=support_file.dest,
                    description=support_file.description,
                    category=support_file.category,
                    content='',  # Empty content means copy from source
                )
            )

        # Add usage examples if generated
        if usage_examples_code:
            generated_files.append(
                GeneratedFile(
                    path=self.language_config.file_patterns['usage_examples'],
                    description='Interactive examples',
                    category='examples',
                    content=usage_examples_code,
                )
            )

        # Generate transaction service if cross-table patterns exist
        cross_table_patterns = self.schema.get('cross_table_access_patterns', [])
        if cross_table_patterns and self.transaction_service_template:
            transaction_service_code = self.generate_transaction_service(
                cross_table_patterns, all_entities
            )

            if transaction_service_code:
                generated_files.append(
                    GeneratedFile(
                        path='transaction_service.py',
                        description=f'{len(cross_table_patterns)} cross-table transaction patterns',
                        category='services',
                        content=transaction_service_code,
                        count=len(cross_table_patterns),
                    )
                )

                # Add cross-table patterns to access pattern mapping
                for pattern in cross_table_patterns:
                    pattern_mapping = self._create_transaction_pattern_mapping(pattern)
                    access_pattern_mapping[str(pattern['pattern_id'])] = pattern_mapping

        # Create generation result
        generation_result = GenerationResult(
            generated_files=generated_files,
            access_pattern_mapping=access_pattern_mapping,
            generator_type=self.__class__.__name__,
        )

        # Use output manager to write all files
        output_manager = OutputManager(output_dir, self.language)
        output_manager.write_generated_files(generation_result)
