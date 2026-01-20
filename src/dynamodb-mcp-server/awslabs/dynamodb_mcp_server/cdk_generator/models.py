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

"""Data model classes for CDK generator."""

from dataclasses import dataclass, field
from typing import List, Optional


# AWS DynamoDB Limits
# Source: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Limits.html
MAX_GSI_PARTITION_KEYS = 4  # Maximum number of partition key attributes per GSI
MAX_GSI_SORT_KEYS = 4  # Maximum number of sort key attributes per GSI


@dataclass
class KeyAttribute:
    """Represents a key attribute (partition or sort key)."""

    name: str
    type: str  # 'S', 'N', or 'B'

    def to_cdk_type(self) -> str:
        """Map DynamoDB type to CDK AttributeType.

        Returns:
            CDK AttributeType string (STRING, NUMBER, or BINARY)

        Raises:
            ValueError: If type is not S, N, or B
        """
        mapping = {'S': 'STRING', 'N': 'NUMBER', 'B': 'BINARY'}
        if self.type not in mapping:
            raise ValueError(f"Invalid attribute type. type: '{self.type}', expected: S, N, or B")
        return mapping[self.type]


@dataclass
class GlobalSecondaryIndex:
    """Represents a GSI with support for multi-attribute composite keys."""

    index_name: str
    partition_keys: List[KeyAttribute]  # One or more partition key attributes
    sort_keys: List[KeyAttribute] = field(default_factory=list)  # Zero or more sort key attributes
    projection_type: str = 'ALL'  # 'ALL', 'KEYS_ONLY', 'INCLUDE'
    non_key_attributes: List[str] = field(default_factory=list)  # For INCLUDE projection

    def has_multi_partition_keys(self) -> bool:
        """Return True if GSI has multiple partition key attributes."""
        return len(self.partition_keys) > 1

    def has_multi_sort_keys(self) -> bool:
        """Return True if GSI has multiple sort key attributes."""
        return len(self.sort_keys) > 1


@dataclass
class TableDefinition:
    """Represents a DynamoDB table definition."""

    table_name: str  # Logical name from JSON (used for CfnOutput, not hardcoded in CDK)
    partition_key: KeyAttribute
    sort_key: Optional[KeyAttribute] = None
    global_secondary_indexes: Optional[List[GlobalSecondaryIndex]] = field(default_factory=list)
    ttl_attribute: Optional[str] = None


@dataclass
class DataModel:
    """Root data model containing all table definitions."""

    tables: List[TableDefinition] = field(default_factory=list)

    @staticmethod
    def _validate_is_object(data, context: str) -> None:
        """Validate that data is a dictionary object.

        Args:
            data: Data to validate
            context: Context string for error messages

        Raises:
            ValueError: If data is not a dictionary
        """
        if not isinstance(data, dict):
            raise ValueError(f'{context} must be an object')

    @staticmethod
    def _validate_string_field(data: dict, field_name: str, context: str) -> str:
        """Validate that a field exists and is a string.

        Args:
            data: Dictionary containing the field
            field_name: Name of the field to validate
            context: Context string for error messages

        Returns:
            The string value

        Raises:
            ValueError: If field is missing or not a string
        """
        if field_name not in data:
            raise ValueError(f'{context}.{field_name} must be a string')
        if not isinstance(data[field_name], str):
            raise ValueError(f'{context}.{field_name} must be a string')
        return data[field_name]

    @staticmethod
    def _validate_array_field(data: dict, field_name: str, context: str) -> list:
        """Validate that a field exists and is an array.

        Args:
            data: Dictionary containing the field
            field_name: Name of the field to validate
            context: Context string for error messages

        Returns:
            The list value

        Raises:
            ValueError: If field is missing or not a list
        """
        if field_name not in data:
            raise ValueError(f'{context}.{field_name} must be an array')
        if not isinstance(data[field_name], list):
            raise ValueError(f'{context}.{field_name} must be an array')
        return data[field_name]

    @classmethod
    def from_json(cls, data: dict) -> 'DataModel':
        """Parse JSON dict into DataModel with validation.

        Args:
            data: Dictionary containing table definitions

        Returns:
            DataModel instance

        Raises:
            ValueError: If required fields are missing or invalid, with hierarchical context
        """
        if not isinstance(data, dict):
            raise ValueError('Input must be a dictionary')

        if 'tables' not in data:
            raise ValueError('Configuration must contain a "tables" property')

        if not isinstance(data['tables'], list):
            raise ValueError('Configuration "tables" property must be an array')

        tables = []
        for i, table_data in enumerate(data['tables']):
            table = cls._parse_table(table_data, table_index=i)
            tables.append(table)

        model = cls(tables=tables)
        model.validate()
        return model

    @classmethod
    def _parse_attribute_definitions(cls, attr_definitions: list, context: str) -> dict:
        """Parse AttributeDefinitions and return a map of attribute names to types.

        Args:
            attr_definitions: List of attribute definition dictionaries
            context: Context string for error messages (e.g., 'tables[0]')

        Returns:
            Dictionary mapping attribute names to types

        Raises:
            ValueError: If attribute definitions are invalid
        """
        attr_types = {}
        for attr_index, attr_def in enumerate(attr_definitions):
            attr_context = f'{context}.AttributeDefinitions[{attr_index}]'

            cls._validate_is_object(attr_def, attr_context)
            attr_name = cls._validate_string_field(attr_def, 'AttributeName', attr_context)

            if 'AttributeType' not in attr_def:
                raise ValueError(f"{attr_context}.AttributeType must be 'S', 'N', or 'B'")

            attr_type = attr_def['AttributeType']

            if attr_type not in ['S', 'N', 'B']:
                raise ValueError(f"{attr_context}.AttributeType must be 'S', 'N', or 'B'")

            attr_types[attr_name] = attr_type

        return attr_types

    @classmethod
    def _parse_key_schema(cls, key_schema: list, attr_types: dict, context: str) -> tuple:
        """Parse KeySchema and return partition and sort keys.

        Args:
            key_schema: List of key schema element dictionaries
            attr_types: Map of attribute names to types
            context: Context string for error messages (e.g., 'tables[0]')

        Returns:
            Tuple of (partition_key, sort_key) where sort_key may be None

        Raises:
            ValueError: If key schema is invalid
        """
        partition_key = None
        sort_key = None

        for key_index, key_element in enumerate(key_schema):
            key_context = f'{context}.KeySchema[{key_index}]'

            cls._validate_is_object(key_element, key_context)
            attr_name = cls._validate_string_field(key_element, 'AttributeName', key_context)

            if 'KeyType' not in key_element:
                raise ValueError(f"{key_context}.KeyType must be 'HASH' or 'RANGE'")

            key_type = key_element['KeyType']

            if key_type not in ['HASH', 'RANGE']:
                raise ValueError(f"{key_context}.KeyType must be 'HASH' or 'RANGE'")

            if attr_name not in attr_types:
                raise ValueError(
                    f"{key_context}: AttributeName '{attr_name}' not found in AttributeDefinitions"
                )

            if key_type == 'HASH':
                if partition_key is not None:
                    raise ValueError(
                        f'{context}.KeySchema must contain exactly one HASH key, found 2'
                    )
                partition_key = KeyAttribute(name=attr_name, type=attr_types[attr_name])
            elif key_type == 'RANGE':
                if sort_key is not None:
                    raise ValueError(
                        f'{context}.KeySchema must contain at most one RANGE key, found 2'
                    )
                sort_key = KeyAttribute(name=attr_name, type=attr_types[attr_name])

        if partition_key is None:
            raise ValueError(f'{context}.KeySchema must contain exactly one HASH key')

        return partition_key, sort_key

    @classmethod
    def _parse_ttl_specification(cls, ttl_data: dict, context: str) -> Optional[str]:
        """Parse TimeToLiveSpecification and return TTL attribute name if enabled.

        Args:
            ttl_data: TimeToLiveSpecification dictionary
            context: Context string for error messages (e.g., 'tables[0]')

        Returns:
            TTL attribute name if enabled, None otherwise

        Raises:
            ValueError: If TTL specification is invalid
        """
        ttl_context = f'{context}.TimeToLiveSpecification'

        cls._validate_is_object(ttl_data, ttl_context)

        if 'Enabled' not in ttl_data:
            raise ValueError(f'{ttl_context}.Enabled must be a boolean')

        if not isinstance(ttl_data['Enabled'], bool):
            raise ValueError(f'{ttl_context}.Enabled must be a boolean')

        if ttl_data['Enabled']:
            return cls._validate_string_field(ttl_data, 'AttributeName', ttl_context)

        return None

    @classmethod
    def _parse_table(cls, table_data: dict, table_index: int) -> TableDefinition:
        """Parse a single table definition from JSON.

        Args:
            table_data: Dictionary containing table definition
            table_index: Index of the table in the tables array

        Returns:
            TableDefinition instance

        Raises:
            ValueError: If required fields are missing or invalid, with hierarchical context
        """
        context = f'tables[{table_index}]'

        cls._validate_is_object(table_data, context)

        table_name = cls._validate_string_field(table_data, 'TableName', context)
        cls._validate_array_field(table_data, 'KeySchema', context)
        attr_definitions = cls._validate_array_field(table_data, 'AttributeDefinitions', context)

        attr_types = cls._parse_attribute_definitions(attr_definitions, context)

        partition_key, sort_key = cls._parse_key_schema(
            table_data['KeySchema'], attr_types, context
        )

        gsis = []
        if 'GlobalSecondaryIndexes' in table_data:
            gsi_list = cls._validate_array_field(table_data, 'GlobalSecondaryIndexes', context)

            for gsi_index, gsi_data in enumerate(gsi_list):
                gsi = cls._parse_gsi(gsi_data, attr_types, table_index, gsi_index)
                gsis.append(gsi)

        ttl_attribute = None
        if 'TimeToLiveSpecification' in table_data:
            ttl_attribute = cls._parse_ttl_specification(
                table_data['TimeToLiveSpecification'], context
            )

        return TableDefinition(
            table_name=table_name,
            partition_key=partition_key,
            sort_key=sort_key,
            global_secondary_indexes=gsis,
            ttl_attribute=ttl_attribute,
        )

    @classmethod
    def _parse_gsi_key_schema(cls, key_schema: list, attr_types: dict, context: str) -> tuple:
        """Parse GSI KeySchema and return partition and sort keys.

        GSI KeySchema supports multiple HASH and RANGE entries (up to 4 each).

        Args:
            key_schema: List of key schema element dictionaries
            attr_types: Map of attribute names to types
            context: Context string for error messages (e.g., 'tables[0].GlobalSecondaryIndexes[0]')

        Returns:
            Tuple of (partition_keys, sort_keys) as lists

        Raises:
            ValueError: If key schema is invalid
        """
        partition_keys = []
        sort_keys = []

        for key_index, key_element in enumerate(key_schema):
            key_context = f'{context}.KeySchema[{key_index}]'

            cls._validate_is_object(key_element, key_context)
            attr_name = cls._validate_string_field(key_element, 'AttributeName', key_context)

            if 'KeyType' not in key_element:
                raise ValueError(f"{key_context}.KeyType must be 'HASH' or 'RANGE'")

            key_type = key_element['KeyType']

            if key_type not in ['HASH', 'RANGE']:
                raise ValueError(f"{key_context}.KeyType must be 'HASH' or 'RANGE'")

            if attr_name not in attr_types:
                raise ValueError(
                    f"{key_context}: AttributeName '{attr_name}' not found in AttributeDefinitions"
                )

            if key_type == 'HASH':
                partition_keys.append(KeyAttribute(name=attr_name, type=attr_types[attr_name]))
            elif key_type == 'RANGE':
                sort_keys.append(KeyAttribute(name=attr_name, type=attr_types[attr_name]))

        if not partition_keys:
            raise ValueError(f'{context}.KeySchema must contain at least one HASH key')

        # Validate against AWS limits
        if len(partition_keys) > MAX_GSI_PARTITION_KEYS:
            raise ValueError(
                f'{context}.KeySchema must contain at most {MAX_GSI_PARTITION_KEYS} HASH keys, found {len(partition_keys)}'
            )

        if len(sort_keys) > MAX_GSI_SORT_KEYS:
            raise ValueError(
                f'{context}.KeySchema must contain at most {MAX_GSI_SORT_KEYS} RANGE keys, found {len(sort_keys)}'
            )

        return partition_keys, sort_keys

    @classmethod
    def _parse_gsi_projection(cls, projection: dict, context: str) -> tuple:
        """Parse GSI Projection configuration.

        Args:
            projection: Projection dictionary (may be empty)
            context: Context string for error messages

        Returns:
            Tuple of (projection_type, non_key_attributes)

        Raises:
            ValueError: If projection configuration is invalid
        """
        projection_type = 'ALL'
        non_key_attributes = []

        if not projection:
            return projection_type, non_key_attributes

        if 'ProjectionType' in projection:
            projection_type = projection['ProjectionType']
            if projection_type not in ['ALL', 'KEYS_ONLY', 'INCLUDE']:
                raise ValueError(
                    f"{context}.Projection.ProjectionType must be 'ALL', 'KEYS_ONLY', or 'INCLUDE'"
                )

        if 'NonKeyAttributes' in projection:
            non_key_attributes = projection['NonKeyAttributes']
            if not isinstance(non_key_attributes, list):
                raise ValueError(f'{context}.Projection.NonKeyAttributes must be an array')

        # Validate NonKeyAttributes based on ProjectionType
        if projection_type == 'INCLUDE':
            if not non_key_attributes:
                raise ValueError(
                    f'{context}.Projection.NonKeyAttributes is required when ProjectionType is INCLUDE'
                )
            for i, attr in enumerate(non_key_attributes):
                if not isinstance(attr, str):
                    raise ValueError(
                        f'{context}.Projection.NonKeyAttributes[{i}] must be a string'
                    )
                if not attr:
                    raise ValueError(
                        f'{context}.Projection.NonKeyAttributes[{i}] must not be empty'
                    )
        elif projection_type in ['ALL', 'KEYS_ONLY']:
            if non_key_attributes:
                raise ValueError(
                    f'{context}.Projection.NonKeyAttributes is not allowed when ProjectionType is {projection_type}'
                )

        return projection_type, non_key_attributes

    @classmethod
    def _parse_gsi(
        cls, gsi_data: dict, attr_types: dict, table_index: int, gsi_index: int
    ) -> GlobalSecondaryIndex:
        """Parse a GlobalSecondaryIndex definition.

        Args:
            gsi_data: Dictionary containing GSI definition
            attr_types: Map of attribute names to types
            table_index: Index of the parent table in the tables array
            gsi_index: Index of the GSI in the GlobalSecondaryIndexes array

        Returns:
            GlobalSecondaryIndex instance

        Raises:
            ValueError: If required fields are missing or invalid, with hierarchical context
        """
        context = f'tables[{table_index}].GlobalSecondaryIndexes[{gsi_index}]'

        cls._validate_is_object(gsi_data, context)
        index_name = cls._validate_string_field(gsi_data, 'IndexName', context)
        cls._validate_array_field(gsi_data, 'KeySchema', context)

        partition_keys, sort_keys = cls._parse_gsi_key_schema(
            gsi_data['KeySchema'], attr_types, context
        )

        projection_type, non_key_attributes = cls._parse_gsi_projection(
            gsi_data.get('Projection', {}), context
        )

        return GlobalSecondaryIndex(
            index_name=index_name,
            partition_keys=partition_keys,
            sort_keys=sort_keys,
            projection_type=projection_type,
            non_key_attributes=non_key_attributes,
        )

    def validate(self) -> None:
        """Validate the data model structure.

        Raises:
            ValueError: With descriptive message identifying the specific failure
        """
        if not self.tables:
            raise ValueError('Data model must contain at least one table')

        # Check for duplicate table names
        table_names = [table.table_name for table in self.tables]
        duplicates = [name for name in table_names if table_names.count(name) > 1]
        if duplicates:
            unique_duplicates = list(set(duplicates))
            raise ValueError(
                f'Data model contains duplicate table names. table_names: {", ".join(unique_duplicates)}'
            )

        for table in self.tables:
            # Check for duplicate GSI names within a table
            if table.global_secondary_indexes:
                gsi_names = [gsi.index_name for gsi in table.global_secondary_indexes]
                duplicates = [name for name in gsi_names if gsi_names.count(name) > 1]
                if duplicates:
                    unique_duplicates = list(set(duplicates))
                    raise ValueError(
                        f"Table contains duplicate GSI names. table_name: '{table.table_name}', gsi_names: {', '.join(unique_duplicates)}"
                    )
