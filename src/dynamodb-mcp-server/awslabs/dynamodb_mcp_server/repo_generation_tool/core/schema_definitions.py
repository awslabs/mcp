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

"""Schema definitions and enums for DynamoDB table schema validation.

This module defines all the valid values and structures expected in schema.json files
used for code generation. It serves as the single source of truth for schema validation.
"""

from awslabs.dynamodb_mcp_server.repo_generation_tool.core.validation_utils import (
    ValidationError,
)
from dataclasses import dataclass
from enum import Enum
from typing import Any


class FieldType(Enum):
    """Valid field types in entity definitions."""

    STRING = 'string'
    INTEGER = 'integer'
    DECIMAL = 'decimal'
    BOOLEAN = 'boolean'
    ARRAY = 'array'
    OBJECT = 'object'
    UUID = 'uuid'


class ReturnType(Enum):
    """Valid return types for access patterns."""

    SINGLE_ENTITY = 'single_entity'
    ENTITY_LIST = 'entity_list'
    SUCCESS_FLAG = 'success_flag'
    MIXED_DATA = 'mixed_data'
    VOID = 'void'


class DynamoDBOperation(Enum):
    """Valid DynamoDB operations for access patterns."""

    GET_ITEM = 'GetItem'
    PUT_ITEM = 'PutItem'
    DELETE_ITEM = 'DeleteItem'
    QUERY = 'Query'
    SCAN = 'Scan'
    UPDATE_ITEM = 'UpdateItem'
    BATCH_GET_ITEM = 'BatchGetItem'
    BATCH_WRITE_ITEM = 'BatchWriteItem'


class ParameterType(Enum):
    """Valid parameter types in access patterns."""

    STRING = 'string'
    INTEGER = 'integer'
    DECIMAL = 'decimal'
    BOOLEAN = 'boolean'
    ARRAY = 'array'
    OBJECT = 'object'
    UUID = 'uuid'
    ENTITY = 'entity'


class DynamoDBType(Enum):
    """DynamoDB native attribute types."""

    STRING = 'S'
    NUMBER = 'N'
    BINARY = 'B'
    STRING_SET = 'SS'
    NUMBER_SET = 'NS'
    BINARY_SET = 'BS'
    MAP = 'M'
    LIST = 'L'
    NULL = 'NULL'
    BOOLEAN = 'BOOL'


class RangeCondition(Enum):
    """Valid range conditions for sort key queries."""

    BEGINS_WITH = 'begins_with'
    BETWEEN = 'between'
    GREATER_THAN = '>'
    LESS_THAN = '<'
    GREATER_THAN_OR_EQUAL = '>='
    LESS_THAN_OR_EQUAL = '<='


class GSIProjectionType(Enum):
    """Valid GSI projection types."""

    ALL = 'ALL'
    KEYS_ONLY = 'KEYS_ONLY'
    INCLUDE = 'INCLUDE'


@dataclass
class GSIDefinition:
    """Definition of a Global Secondary Index."""

    name: str
    partition_key: str
    sort_key: str | None = None  # Optional: GSI can have only partition key
    projection: str = 'ALL'  # ALL, KEYS_ONLY, INCLUDE (defaults to ALL)
    included_attributes: list[str] | None = None  # Required when projection is INCLUDE


@dataclass
class GSIMapping:
    """Mapping of entity fields to GSI keys."""

    name: str
    pk_template: str
    sk_template: str | None = None  # Optional: GSI mapping can have only partition key


@dataclass
class Field:
    """Entity field definition."""

    name: str
    type: str
    required: bool
    item_type: str | None = None  # Required when type is "array"


@dataclass
class Parameter:
    """Access pattern parameter definition."""

    name: str
    type: str
    entity_type: str | None = None  # Required when type is "entity"


@dataclass
class AccessPattern:
    """Access pattern definition with GSI support."""

    pattern_id: int
    name: str
    description: str
    operation: str
    parameters: list[Parameter]
    return_type: str
    index_name: str | None = None  # GSI name for GSI queries
    range_condition: str | None = None  # Range condition for GSI range queries


@dataclass
class Entity:
    """Entity definition with GSI mapping support."""

    entity_type: str
    pk_template: str
    fields: list[Field]
    access_patterns: list[AccessPattern]
    sk_template: str | None = None  # Optional: Entity can have only partition key
    gsi_mappings: list[GSIMapping] | None = None  # GSI mappings for this entity


@dataclass
class TableConfig:
    """Table configuration."""

    table_name: str
    partition_key: str
    sort_key: str | None = None  # Optional: Table can have only partition key


@dataclass
class Table:
    """Table definition with GSI support."""

    table_config: TableConfig
    entities: dict[str, Entity]
    gsi_list: list[GSIDefinition] | None = None  # GSI definitions for this table


# Validation utilities
def get_enum_values(enum_class) -> list[str]:
    """Get list of valid string values from enum."""
    return [item.value for item in enum_class]


def is_valid_enum_value(value: str, enum_class) -> bool:
    """Check if value is valid for given enum."""
    return value in get_enum_values(enum_class)


def suggest_enum_value(invalid_value: str, enum_class) -> str:
    """Suggest the closest valid enum value for an invalid input."""
    valid_values = get_enum_values(enum_class)

    # Simple suggestion logic - find closest match by length and common characters
    if not invalid_value:
        return f'Valid options: {", ".join(valid_values)}'

    # Look for exact substring matches first
    substring_matches = [v for v in valid_values if invalid_value.lower() in v.lower()]
    if substring_matches:
        return f"Did you mean '{substring_matches[0]}'? Valid options: {', '.join(valid_values)}"

    # Look for values that start with the same characters
    prefix_matches = [v for v in valid_values if v.lower().startswith(invalid_value.lower()[:3])]
    if prefix_matches:
        return f"Did you mean '{prefix_matches[0]}'? Valid options: {', '.join(valid_values)}"

    return f'Valid options: {", ".join(valid_values)}'


def get_all_enum_classes() -> dict[str, type]:
    """Get mapping of enum names to enum classes for validation."""
    return {
        'FieldType': FieldType,
        'ReturnType': ReturnType,
        'DynamoDBOperation': DynamoDBOperation,
        'ParameterType': ParameterType,
        'DynamoDBType': DynamoDBType,
        'RangeCondition': RangeCondition,
        'GSIProjectionType': GSIProjectionType,
    }


# Schema structure constants
REQUIRED_SCHEMA_FIELDS = {'tables'}  # Top-level schema structure
REQUIRED_TABLE_FIELDS = {'table_config', 'entities'}  # Each table object
REQUIRED_TABLE_CONFIG_FIELDS = {'table_name', 'partition_key'}  # sort_key is optional
REQUIRED_ENTITY_FIELDS = {'entity_type', 'pk_template', 'fields'}  # sk_template is optional
REQUIRED_FIELD_PROPERTIES = {'name', 'type', 'required'}
REQUIRED_ACCESS_PATTERN_FIELDS = {'pattern_id', 'name', 'description', 'operation', 'return_type'}
REQUIRED_PARAMETER_FIELDS = {'name', 'type'}

# GSI-related field requirements
REQUIRED_GSI_DEFINITION_FIELDS = {'name', 'partition_key'}  # sort_key is optional
REQUIRED_GSI_MAPPING_FIELDS = {'name', 'pk_template'}  # sk_template is optional

# Optional fields that have specific validation rules
OPTIONAL_FIELD_PROPERTIES = {'item_type'}  # Required when type is "array"
OPTIONAL_PARAMETER_FIELDS = {'entity_type'}  # Required when type is "entity"
OPTIONAL_TABLE_FIELDS = {'gsi_list'}  # Optional GSI definitions
OPTIONAL_ENTITY_FIELDS = {'gsi_mappings'}  # Optional GSI mappings
OPTIONAL_ACCESS_PATTERN_FIELDS = {'index_name', 'range_condition'}  # Optional GSI query fields

# Valid range condition values
VALID_RANGE_CONDITIONS = {
    RangeCondition.BEGINS_WITH.value,
    RangeCondition.BETWEEN.value,
    RangeCondition.GREATER_THAN.value,
    RangeCondition.LESS_THAN.value,
    RangeCondition.GREATER_THAN_OR_EQUAL.value,
    RangeCondition.LESS_THAN_OR_EQUAL.value,
}

# Valid GSI projection types
VALID_GSI_PROJECTION_TYPES = {
    GSIProjectionType.ALL.value,
    GSIProjectionType.KEYS_ONLY.value,
    GSIProjectionType.INCLUDE.value,
}

# Optional fields for GSI definitions
OPTIONAL_GSI_DEFINITION_FIELDS = {'sort_key', 'projection', 'included_attributes'}


def validate_required_fields(
    data: dict[str, Any], required_fields: set[str], path: str
) -> list[ValidationError]:
    """Validate that all required fields are present in data."""
    errors = []
    missing_fields = required_fields - set(data.keys())

    for field in missing_fields:
        errors.append(
            ValidationError(
                path=f'{path}.{field}',
                message=f"Missing required field '{field}'",
                suggestion=f"Add '{field}' field to {path}",
            )
        )

    return errors


def validate_enum_field(
    value: Any, enum_class: type, path: str, field_name: str
) -> list[ValidationError]:
    """Validate that a field value matches an enum."""
    errors = []

    if not isinstance(value, str):
        errors.append(
            ValidationError(
                path=f'{path}.{field_name}',
                message=f"Field '{field_name}' must be a string, got {type(value).__name__}",
                suggestion=f'Change {field_name} to a string value',
            )
        )
        return errors

    if not is_valid_enum_value(value, enum_class):
        suggestion = suggest_enum_value(value, enum_class)
        errors.append(
            ValidationError(
                path=f'{path}.{field_name}',
                message=f"Invalid {field_name} value '{value}'",
                suggestion=suggestion,
            )
        )

    return errors


def validate_data_type(
    value: Any, expected_type: type, path: str, field_name: str
) -> list[ValidationError]:
    """Validate that a field has the expected data type."""
    errors = []

    if not isinstance(value, expected_type):
        errors.append(
            ValidationError(
                path=f'{path}.{field_name}',
                message=f"Field '{field_name}' must be {expected_type.__name__}, got {type(value).__name__}",
                suggestion=f'Change {field_name} to {expected_type.__name__} type',
            )
        )

    return errors
