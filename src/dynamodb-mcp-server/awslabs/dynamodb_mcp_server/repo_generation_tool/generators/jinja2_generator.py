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

"""Jinja2-specific generator implementation."""

from awslabs.dynamodb_mcp_server.repo_generation_tool.core.key_template_parser import (
    KeyTemplateParser,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.utils import (
    filter_conflicting_patterns,
    get_crud_method_names,
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

    def __init__(self, schema_path: str, templates_dir: str = None, language: str = 'python'):
        """Initialize the Jinja2 generator with schema and templates."""
        super().__init__(schema_path, language)

        self.access_pattern_mapper = AccessPatternMapper(self.language_config, self.type_mapper)
        self.sample_generator = SampleValueGenerator()
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
        # nosec B701 - autoescape disabled for code generation, not HTML rendering
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=False,  # Explicitly disabled for code generation (not HTML)
        )

        # Add custom filter for parameter substitution
        def substitute_params(template, params):
            """Replace {param} with {entity.param} for all params in the list."""
            result = template
            for param in params:
                result = result.replace(f'{{{param}}}', f'{{entity.{param}}}')
            return result

        def substitute_self_params(template, params):
            """Replace {param} with {self.param} for all params in the list."""
            result = template
            for param in params:
                result = result.replace(f'{{{param}}}', f'{{self.{param}}}')
            return result

        self.env.filters['substitute_params'] = substitute_params
        self.env.filters['substitute_self_params'] = substitute_self_params

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
        import re

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

            processed_mapping['pk_params'] = self.template_parser.extract_parameters(
                gsi_pk_template
            )
            processed_mapping['sk_params'] = self.template_parser.extract_parameters(
                gsi_sk_template
            )

            # Check if GSI PK/SK are pure numeric field references
            processed_mapping['pk_is_numeric'] = self._check_template_is_pure_numeric(
                gsi_pk_template, processed_mapping['pk_params'], fields
            )
            processed_mapping['sk_is_numeric'] = self._check_template_is_pure_numeric(
                gsi_sk_template, processed_mapping['sk_params'], fields
            )

            processed_gsi_mappings.append(processed_mapping)

        processed_config['gsi_mappings'] = processed_gsi_mappings

        return processed_config

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
        filtered_patterns = filter_conflicting_patterns(
            processed_config.get('access_patterns', []),
            crud_methods,
            entity_name=entity_name,
            entity_config=processed_config,
        )

        def format_parameters(params):
            """Format parameter list for method signature."""
            formatted = []
            for param in params:
                if param.get('type') == 'entity':
                    param_type = param.get('entity_type', 'Any')
                else:
                    param_type = self.type_mapper.map_parameter_type(param)
                formatted.append(f'{param["name"]}: {param_type}')
            return ', '.join(formatted)

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
            table_config=table_config,
            table_data=table_data,
            map_return_type=lambda rt, en: self.type_mapper.map_return_type(rt, en),
            format_parameters=format_parameters,
            get_gsi_mapping_for_index=get_gsi_mapping_for_index,
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
        entity_mapping = self.access_pattern_mapper.generate_mapping(entity_name, processed_config)

        # Generate the repository code
        repo_code = self.generate_repository(entity_name, entity_config, table_config, table_data)

        return repo_code, entity_mapping

    def generate_usage_examples(
        self,
        access_pattern_mapping: dict[str, Any],
        all_entities: dict[str, Any],
        all_tables: list[dict[str, Any]],
    ) -> str:
        """Generate usage examples using Jinja2."""
        if not self.usage_examples_template:
            return '# Usage examples template not found'

        entity_names = list(all_entities.keys())
        repository_names = [f'{name}Repository' for name in entity_names]

        # For single table scenarios, use the first table's config
        table_config = all_tables[0]['table_config'] if all_tables else {}

        return self.usage_examples_template.render(
            entity_names=entity_names,
            repository_names=repository_names,
            entities=all_entities,
            table_config=table_config,
            tables=all_tables,
            access_patterns=access_pattern_mapping,
            generate_sample_value=self.sample_generator.generate_sample_value,
            get_updatable_field=self.sample_generator.get_updatable_field,
            generate_update_value=self.sample_generator.generate_update_value,
            get_all_key_params=self.sample_generator.get_all_key_params,
            get_parameter_value=self.sample_generator.get_parameter_value,
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
            usage_examples_code = self.generate_usage_examples(
                access_pattern_mapping, preprocessed_entities, all_tables
            )

        # Generate headers using templates
        entities_header = ''
        if self.entities_header_template:
            entities_header = self.entities_header_template.render()

        repositories_header = ''
        if self.repositories_header_template:
            repositories_header = self.repositories_header_template.render()

        # Create complete file content for entities
        entities_content = ''
        if entities_header:
            entities_content += entities_header + '\n\n'
        entities_content += '\n\n'.join(entities_code) + '\n'

        # Create complete file content for repositories
        repositories_content = ''
        if repositories_header:
            repositories_content += repositories_header + '\n'
        from awslabs.dynamodb_mcp_server.repo_generation_tool.core.utils import (
            format_entity_imports,
        )

        repositories_content += format_entity_imports(all_entity_names) + '\n\n'
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

        # Create generation result
        generation_result = GenerationResult(
            generated_files=generated_files,
            access_pattern_mapping=access_pattern_mapping,
            generator_type=self.__class__.__name__,
        )

        # Use output manager to write all files
        output_manager = OutputManager(output_dir, self.language)
        output_manager.write_generated_files(generation_result)
