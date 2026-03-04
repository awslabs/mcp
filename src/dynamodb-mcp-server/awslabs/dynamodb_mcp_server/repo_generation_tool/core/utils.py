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

"""Utility functions for code generation."""

import re
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.language_config import (
    LanguageConfig,
)


def to_snake_case(camel_case_str: str) -> str:
    """Convert CamelCase to snake_case.

    Also handles hyphens by replacing them with underscores.

    Examples:
        - 'CamelCase' -> 'camel_case'
        - 'Events-ByDate' -> 'events_by_date'
        - 'Orders-ByEmail' -> 'orders_by_email'
    """
    # First, replace hyphens with underscores
    s0 = camel_case_str.replace('-', '_')
    # Insert underscore before uppercase letters (except first)
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s0)
    # Insert underscore before uppercase letters preceded by lowercase
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    # Clean up any double underscores that might result from hyphen replacement
    return re.sub('_+', '_', s2)


def to_pascal_case(snake_case_str: str) -> str:
    """Convert snake_case to PascalCase."""
    return ''.join(word.capitalize() for word in snake_case_str.split('_'))


def get_crud_method_names(entity_name: str, language_config: LanguageConfig) -> set[str]:
    """Get set of CRUD method names for an entity based on language configuration."""
    if not language_config.naming_conventions:
        # Fallback to Python-style naming if no naming conventions defined
        entity_name_snake = to_snake_case(entity_name)
        return {
            f'create_{entity_name_snake}',
            f'get_{entity_name_snake}',
            f'update_{entity_name_snake}',
            f'delete_{entity_name_snake}',
        }

    crud_patterns = language_config.naming_conventions.crud_patterns
    method_naming = language_config.naming_conventions.method_naming

    # Format entity name based on method naming convention
    if method_naming == 'snake_case':
        formatted_entity_name = to_snake_case(entity_name)
    elif method_naming == 'camelCase':
        formatted_entity_name = to_pascal_case(to_snake_case(entity_name))
    else:
        # Default to snake_case if unknown convention
        formatted_entity_name = to_snake_case(entity_name)

    # Generate CRUD method names using patterns
    crud_methods = set()
    for operation, pattern in crud_patterns.items():
        if '{entity_name}' in pattern:
            method_name = pattern.replace('{entity_name}', formatted_entity_name)
        elif '{EntityName}' in pattern:
            # For PascalCase entity names in patterns
            pascal_entity_name = to_pascal_case(to_snake_case(entity_name))
            method_name = pattern.replace('{EntityName}', pascal_entity_name)
        else:
            # Pattern doesn't contain placeholder, use as-is
            method_name = pattern

        crud_methods.add(method_name)

    return crud_methods


def get_crud_signature(entity_name: str, method_name: str, entity_config: dict) -> tuple[str, ...]:
    """Get the expected signature for a CRUD method.

    Returns a tuple of parameter types that the CRUD method expects.
    """
    entity_name_snake = to_snake_case(entity_name)

    # Extract pk and sk params from entity config
    pk_params = entity_config.get('pk_params', [])
    sk_params = entity_config.get('sk_params', [])
    key_params = pk_params + sk_params

    if method_name == f'create_{entity_name_snake}':
        # create takes a single entity parameter
        return ('entity',)
    elif method_name == f'get_{entity_name_snake}':
        # get takes pk/sk string parameters
        return tuple('string' for _ in key_params) if key_params else ('string',)
    elif method_name == f'update_{entity_name_snake}':
        # update takes a single entity parameter
        return ('entity',)
    elif method_name == f'delete_{entity_name_snake}':
        # delete takes pk/sk string parameters
        return tuple('string' for _ in key_params) if key_params else ('string',)

    return ()


def get_pattern_signature(pattern: dict) -> tuple[str, ...]:
    """Get the signature of an access pattern.

    Returns a tuple of parameter types.
    """
    params = pattern.get('parameters', [])
    return tuple(p.get('type', 'unknown') for p in params)


def has_signature_conflict(
    pattern: dict, entity_name: str, crud_methods: set[str], entity_config: dict
) -> bool:
    """Check if a pattern has a true signature conflict with CRUD methods.

    Returns True if the pattern name matches a CRUD method AND has the same signature.
    Returns False if names match but signatures differ (should be renamed, not filtered).
    """
    pattern_name = pattern['name']
    if pattern_name not in crud_methods:
        return False

    # Get signatures
    crud_sig = get_crud_signature(entity_name, pattern_name, entity_config)
    pattern_sig = get_pattern_signature(pattern)

    return crud_sig == pattern_sig


def is_semantically_equivalent_to_crud(
    pattern: dict, entity_name: str, entity_config: dict
) -> bool:
    """Check if an access pattern is functionally identical to a CRUD method.

    This detects patterns like 'get_user_by_id' that are semantically the same
    as the CRUD 'get_user' method (same operation, same key parameters).

    Returns True if the pattern should be filtered out as a CRUD duplicate.
    """
    operation = pattern.get('operation', '')
    params = pattern.get('parameters', [])
    pattern_name = pattern.get('name', '')
    entity_name_snake = to_snake_case(entity_name)

    # Get key params from entity config
    pk_params = entity_config.get('pk_params', [])
    sk_params = entity_config.get('sk_params', [])
    crud_key_params = set(pk_params + sk_params)

    # GetItem with same key params as CRUD get → equivalent to get_{entity}
    if operation == 'GetItem':
        crud_method = f'get_{entity_name_snake}'
        pattern_params = {p['name'] for p in params if p.get('type') != 'entity'}
        if pattern_params == crud_key_params and crud_method in pattern_name:
            return True

    # UpdateItem with single entity param → equivalent to update_{entity}
    # Only if pattern name contains the CRUD method name
    if operation == 'UpdateItem':
        crud_method = f'update_{entity_name_snake}'
        entity_params = [p for p in params if p.get('type') == 'entity']
        if len(entity_params) == 1 and len(params) == 1 and crud_method in pattern_name:
            return True

    # DeleteItem with same key params → equivalent to delete_{entity}
    # Only if pattern name contains the CRUD method name
    if operation == 'DeleteItem':
        crud_method = f'delete_{entity_name_snake}'
        pattern_params = {p['name'] for p in params if p.get('type') != 'entity'}
        if pattern_params == crud_key_params and crud_method in pattern_name:
            return True

    return False


def generate_renamed_method_name(pattern_name: str, pattern: dict) -> str:
    """Generate a deterministic renamed method name for a conflicting pattern.

    Uses the pattern's operation type and parameters to create a meaningful suffix.
    """
    params = pattern.get('parameters', [])
    operation = pattern.get('operation', '')

    # Check if pattern has multiple entity parameters (cross-table reference pattern)
    entity_params = [p for p in params if p.get('type') == 'entity']
    if len(entity_params) > 1:
        # Use "with_refs" suffix for patterns with multiple entity references
        return f'{pattern_name}_with_refs'

    # For Query/Scan operations that conflict with GetItem CRUD, use "_list" suffix
    if operation in ['Query', 'Scan']:
        # This is likely a Query pattern conflicting with a GetItem CRUD method
        # e.g., get_patient_medical_history (Query paginated list) vs get_patient_medical_history (GetItem one)
        return f'{pattern_name}_list'

    # Check for additional non-entity parameters
    non_entity_params = [p for p in params if p.get('type') != 'entity']
    if non_entity_params:
        # Use parameter names to create suffix
        param_names = [p['name'] for p in non_entity_params]
        suffix = '_and_'.join(param_names[:2])  # Limit to first 2 params
        return f'{pattern_name}_with_{suffix}'

    # Fallback: use pattern_id for uniqueness
    pattern_id = pattern.get('pattern_id', 'custom')
    return f'{pattern_name}_pattern_{pattern_id}'


def filter_conflicting_patterns(
    access_patterns: list[dict],
    crud_methods: set[str],
    entity_name: str = None,
    entity_config: dict = None,
) -> tuple[list[dict], dict[str, bool]]:
    """Filter and rename access patterns that conflict with CRUD method names.

    Filtering rules:
    - Patterns with same name AND same signature as CRUD: filtered out (true duplicates)
    - Patterns semantically equivalent to CRUD (e.g., get_user_by_id ≡ get_user): filtered out
    - Patterns with same name but different signature: renamed and kept
    - Patterns with different names and different semantics: kept as-is

    Args:
        access_patterns: List of access pattern definitions
        crud_methods: Set of CRUD method names for the entity
        entity_name: Name of the entity (for signature comparison)
        entity_config: Entity configuration with pk_params/sk_params

    Returns:
        Tuple of (filtered patterns, crud_consistent_read_map)
        - filtered patterns: List of access patterns with conflicts resolved
        - crud_consistent_read_map: Dict mapping CRUD method names to consistent_read values
    """
    result = []
    crud_consistent_read = {}
    entity_name_snake = to_snake_case(entity_name) if entity_name else ''

    for pattern in access_patterns:
        pattern_name = pattern['name']
        operation = pattern.get('operation', '')

        # PutItem patterns are always kept (renamed if conflict: create_X -> put_X)
        if operation == 'PutItem':
            if pattern_name in crud_methods:
                renamed_pattern = pattern.copy()
                renamed_pattern['original_name'] = pattern_name
                if pattern_name.startswith('create_'):
                    renamed_pattern['name'] = 'put_' + pattern_name[7:]
                    # Update description to reflect put/upsert semantics
                    desc = renamed_pattern.get('description', '')
                    if desc.lower().startswith('create '):
                        renamed_pattern['description'] = 'Put (upsert) ' + desc[7:]
                else:
                    renamed_pattern['name'] = f'put_{pattern_name}'
                result.append(renamed_pattern)
            else:
                result.append(pattern)
            continue

        # Check for semantic equivalence first (e.g., get_user_by_id ≡ get_user)
        if entity_name and entity_config:
            if is_semantically_equivalent_to_crud(pattern, entity_name, entity_config):
                # Capture consistent_read value for GetItem patterns that map to CRUD get
                if operation == 'GetItem':
                    crud_get_method = f'get_{entity_name_snake}'
                    if crud_get_method in crud_methods:
                        # Use OR logic: if any pattern has consistent_read=True, keep it True
                        current_value = crud_consistent_read.get(crud_get_method, False)
                        crud_consistent_read[crud_get_method] = current_value or pattern.get(
                            'consistent_read', False
                        )
                # Semantically identical to CRUD - filter out regardless of name
                continue

        if pattern_name not in crud_methods:
            # No name conflict, keep as-is
            result.append(pattern)
        elif entity_name and entity_config:
            # Check if it's a true signature conflict
            if has_signature_conflict(pattern, entity_name, crud_methods, entity_config):
                # True duplicate - filter out
                # Capture consistent_read value for GetItem patterns
                if operation == 'GetItem':
                    crud_get_method = f'get_{entity_name_snake}'
                    if crud_get_method in crud_methods:
                        # Use OR logic: if any pattern has consistent_read=True, keep it True
                        current_value = crud_consistent_read.get(crud_get_method, False)
                        crud_consistent_read[crud_get_method] = current_value or pattern.get(
                            'consistent_read', False
                        )
                continue
            else:
                # Same name but different signature - rename and keep
                renamed_pattern = pattern.copy()
                renamed_pattern['original_name'] = pattern_name
                renamed_pattern['name'] = generate_renamed_method_name(pattern_name, pattern)
                result.append(renamed_pattern)
        else:
            # Legacy behavior: filter by name only (backward compatibility)
            # Capture consistent_read for GetItem before filtering
            if operation == 'GetItem' and pattern_name.startswith('get_'):
                # Use OR logic: if any pattern has consistent_read=True, keep it True
                current_value = crud_consistent_read.get(pattern_name, False)
                crud_consistent_read[pattern_name] = current_value or pattern.get(
                    'consistent_read', False
                )
            continue

    return result, crud_consistent_read


def generate_test_instruction(
    entity_name: str, method_name: str, is_filtered: bool, parameters: list[dict]
) -> str:
    """Generate test instruction for the access pattern."""
    repo_name = f'{entity_name.lower()}_repo'
    param_placeholders = ['...' for _ in parameters]

    if is_filtered:
        return f'Use CRUD method: {repo_name}.{method_name}({", ".join(param_placeholders)})'
    else:
        return f'Use generated method: {repo_name}.{method_name}({", ".join(param_placeholders)})'


def format_entity_imports(entity_names: list[str]) -> str:
    """Format entity imports for repositories file."""
    return f'from entities import {", ".join(sorted(entity_names))}'


def detect_item_collection(entity_name: str, entity_config: dict, table_data: dict) -> bool:
    """Check if this entity is part of an item collection (shares PK with other entities).

    An item collection exists when multiple entities in the same table use the same
    partition key pattern. This requires SK prefix filtering in queries to get only
    the desired entity type.

    Args:
        entity_name: Name of the current entity
        entity_config: Configuration for the current entity
        table_data: Full table data with all entities

    Returns:
        True if multiple entities share the same PK template

    Example:
        TenantUser:     pk_template="TENANT#{tenant_id}#USER#{user_id}"
        TenantProgress: pk_template="TENANT#{tenant_id}#USER#{user_id}"
        → Returns True (item collection detected)
    """
    current_pk_template = entity_config.get('pk_template')
    if not current_pk_template:
        return False

    # Check if any other entity in the same table has the same PK template
    for other_name, other_config in table_data.get('entities', {}).items():
        if other_name == entity_name:
            continue
        if other_config.get('pk_template') == current_pk_template:
            return True
    return False


def get_sk_prefix(sk_template: str) -> str:
    """Extract the static prefix from an SK template for begins_with filtering.

    Args:
        sk_template: Sort key template with optional {field} placeholders

    Returns:
        Static prefix before first template variable, or entire template if no variables

    Examples:
        "PROGRESS#{course_id}#{lesson_id}" → "PROGRESS#"
        "USER#PROFILE" → "USER#PROFILE"
        "ENROLLMENT#{date}" → "ENROLLMENT#"
        "{timestamp}" → "" (no static prefix)
    """
    if not sk_template:
        return ''

    # Find the first template variable
    if '{' in sk_template:
        return sk_template.split('{')[0]
    else:
        # No variables, entire template is the static prefix
        return sk_template
