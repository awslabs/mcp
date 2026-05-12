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

"""Access pattern mapping and conflict resolution."""

from awslabs.dynamodb_mcp_server.repo_generation_tool.core.language_config import (
    LanguageConfig,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.type_mappings import (
    TypeMapper,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.utils import (
    filter_conflicting_patterns,
    get_crud_method_names,
    to_snake_case,
)
from typing import Any


class AccessPatternMapper:
    """Handles access pattern mapping and conflict resolution."""

    def __init__(self, language_config: LanguageConfig, type_mapper: TypeMapper = None):
        """Initialize the access pattern mapper."""
        self.language_config = language_config
        self.type_mapper = type_mapper

    def _get_equivalent_crud_method(
        self, pattern: dict, entity_name_snake: str, crud_methods: set[str]
    ) -> str:
        """Get the equivalent CRUD method name for a filtered pattern.

        Maps operations to their CRUD equivalents:
        - GetItem -> get_{entity}
        - PutItem -> create_{entity} (closest CRUD equivalent for conflict detection)
        - UpdateItem -> update_{entity}
        - DeleteItem -> delete_{entity}
        """
        operation = pattern.get('operation', '')

        # Map operation to CRUD method prefix
        operation_to_crud = {
            'GetItem': f'get_{entity_name_snake}',
            'PutItem': f'create_{entity_name_snake}',
            'UpdateItem': f'update_{entity_name_snake}',
            'DeleteItem': f'delete_{entity_name_snake}',
        }

        crud_method = operation_to_crud.get(operation)
        if crud_method and crud_method in crud_methods:
            return crud_method

        # Fallback to original name if no mapping found
        return pattern['name']

    def generate_mapping(
        self,
        entity_name: str,
        entity_config: dict[str, Any],
        gsi_list: list[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Generate mapping for all access patterns in an entity.

        Args:
            entity_name: Name of the entity
            entity_config: Entity configuration dictionary
            gsi_list: Optional list of GSI definitions for projection info

        Returns:
            Dictionary mapping pattern IDs to pattern metadata including projection info
        """
        entity_name_snake = to_snake_case(entity_name)
        crud_methods = get_crud_method_names(entity_name, self.language_config)

        # Get the filtered/renamed patterns to determine actual method names
        filtered_patterns, _ = filter_conflicting_patterns(
            entity_config.get('access_patterns', []),
            crud_methods,
            entity_name=entity_name,
            entity_config=entity_config,
        )

        # Build a lookup from pattern_id to the resolved method name
        pattern_id_to_method = {}
        for pattern in filtered_patterns:
            pattern_id_to_method[pattern['pattern_id']] = pattern['name']

        # Generate mapping for all access patterns
        entity_mapping = {}
        for pattern in entity_config.get('access_patterns', []):
            pattern_id = str(pattern['pattern_id'])

            # Determine the actual method name (may be renamed or mapped to CRUD)
            if pattern['pattern_id'] in pattern_id_to_method:
                # Pattern was kept (possibly renamed)
                method_name = pattern_id_to_method[pattern['pattern_id']]
            else:
                # Pattern was filtered as duplicate - map to equivalent CRUD method
                method_name = self._get_equivalent_crud_method(
                    pattern, entity_name_snake, crud_methods
                )

            # Get the actual return type based on operation and return_type
            schema_return_type = pattern.get('return_type', 'Any')
            operation = pattern.get('operation', 'Unknown')

            # For Query/Scan operations returning entity_list, use paginated return type
            if (
                self.type_mapper
                and operation in ['Query', 'Scan']
                and schema_return_type == 'entity_list'
            ):
                actual_return_type = f'tuple[list[{entity_name}], dict | None]'
            # For Query/Scan operations returning mixed_data (item collections), use paginated dict return type
            elif (
                self.type_mapper
                and operation in ['Query', 'Scan']
                and schema_return_type == 'mixed_data'
            ):
                actual_return_type = 'tuple[list[dict[str, Any]], dict | None]'
            elif self.type_mapper:
                actual_return_type = self.type_mapper.map_return_type(
                    schema_return_type, entity_name
                )
            else:
                actual_return_type = schema_return_type

            mapping_entry = {
                'pattern_id': pattern['pattern_id'],
                'description': pattern['description'],
                'entity': entity_name,
                'repository': f'{entity_name}Repository',
                'method_name': method_name,
                'parameters': pattern.get('parameters', []),
                'return_type': actual_return_type,
                'operation': operation,
                'index_name': pattern.get('index_name'),
                'range_condition': pattern.get('range_condition'),
            }

            # Include consistent_read for read operations (GetItem, Query, Scan, BatchGetItem)
            # Defaults to false (eventually consistent). Omit for write operations.
            read_operations = {'GetItem', 'Query', 'Scan', 'BatchGetItem'}
            if operation in read_operations:
                mapping_entry['consistent_read'] = pattern.get('consistent_read', False)

            # Include filter_expression when present
            if pattern.get('filter_expression'):
                mapping_entry['filter_expression'] = pattern['filter_expression']

            entity_mapping[pattern_id] = mapping_entry

            # Add GSI projection info if this pattern uses a GSI
            if pattern.get('index_name') and gsi_list:
                # Find the GSI definition
                gsi = next((g for g in gsi_list if g.get('name') == pattern['index_name']), None)
                if gsi:
                    entity_mapping[pattern_id]['projection'] = gsi.get('projection', 'ALL')
                    if gsi.get('projection') == 'INCLUDE' and 'included_attributes' in gsi:
                        entity_mapping[pattern_id]['projected_attributes'] = gsi[
                            'included_attributes'
                        ]

        return entity_mapping
