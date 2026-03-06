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

"""Pydantic-based data models for DynamoDB Cost & Performance Calculator."""

import math
from pydantic import (
    BaseModel,
    Field,
    PositiveFloat,
    PositiveInt,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic.types import StringConstraints
from typing import Annotated, List, Literal, Optional, Union
from typing_extensions import Self


# https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_BatchGetItem.html
MAX_BATCH_GET_ITEMS = 100

# https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html
MAX_BATCH_WRITE_ITEMS = 25

# https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ServiceQuotas.html
MAX_GSIS_PER_TABLE = 20

# https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Constraints.html
MAX_ITEM_SIZE_BYTES = 409600

# https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html
MAX_TRANSACT_ITEMS = 100

# https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/on-demand-capacity-mode.html
RCU_SIZE = 4096

# https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/on-demand-capacity-mode.html
WCU_SIZE = 1024

# https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/CapacityUnitCalculations.html
STORAGE_OVERHEAD_BYTES = 100


NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]
ItemSizeBytes = Annotated[int, Field(ge=1, le=MAX_ITEM_SIZE_BYTES)]


class StorageEntity(BaseModel):
    """Base class for DynamoDB storage entities (tables and GSIs)."""

    name: NonEmptyStr
    item_size_bytes: ItemSizeBytes
    item_count: PositiveInt

    def storage_gb(self) -> float:
        """Calculate storage in GB."""
        return (self.item_count * (self.item_size_bytes + STORAGE_OVERHEAD_BYTES)) / (1024**3)


class GSI(StorageEntity):
    """Global Secondary Index definition."""

    def write_wcus(self) -> float:
        """Calculate WCUs for a single write."""
        return math.ceil(self.item_size_bytes / WCU_SIZE)


class Table(StorageEntity):
    """DynamoDB table definition."""

    gsi_list: Annotated[List[GSI], Field(default_factory=list, max_length=MAX_GSIS_PER_TABLE)]

    @field_validator('gsi_list')
    @classmethod
    def _validate_gsi_list_unique_names(cls, v: List[GSI]) -> List[GSI]:
        """Validate GSI names are unique."""
        seen_names: set[str] = set()
        for gsi in v:
            if gsi.name in seen_names:
                raise ValueError(f'duplicate GSI name. name: "{gsi.name}"')
            seen_names.add(gsi.name)
        return v

    @model_validator(mode='after')
    def _validate_gsi_sizes(self) -> 'Table':
        """Validate GSI sizes against table size."""
        for gsi in self.gsi_list:
            if gsi.item_size_bytes > self.item_size_bytes:
                raise ValueError(
                    f'GSI item_size_bytes cannot exceed table item_size_bytes. '
                    f'gsi_item_size_bytes: {gsi.item_size_bytes}, table_item_size_bytes: {self.item_size_bytes}'
                )

        return self


class AccessPatternCommon(BaseModel):
    """Common fields for all access patterns."""

    pattern: NonEmptyStr
    description: NonEmptyStr
    table: NonEmptyStr
    rps: PositiveFloat
    item_size_bytes: ItemSizeBytes


class GsiMixin(BaseModel):
    """Mixin for operations that support GSI targeting."""

    gsi: Annotated[Optional[str], StringConstraints(min_length=1)] = None


class StronglyConsistentMixin(BaseModel):
    """Mixin for read operations that support consistency mode."""

    strongly_consistent: bool = False

    def consistency_multiplier(self) -> float:
        """Get consistency multiplier for RCU calculations."""
        return 1.0 if self.strongly_consistent else 0.5


class ItemCountMixin(BaseModel):
    """Mixin for multi-item operations."""

    item_count: PositiveInt


class GsiListMixin(BaseModel):
    """Mixin for write operations that affect GSIs."""

    gsi_list: List[str] = Field(default_factory=list)

    @field_validator('gsi_list')
    @classmethod
    def _validate_gsi_list(cls, v: List[str]) -> List[str]:
        """Validate GSI list has no empty strings or duplicates."""
        for gsi_name in v:
            if not gsi_name:
                raise ValueError('GSI name cannot be empty')
        seen_names: set[str] = set()
        for gsi_name in v:
            if gsi_name in seen_names:
                raise ValueError(f'duplicate GSI name in gsi_list. name: "{gsi_name}"')
            seen_names.add(gsi_name)
        return v

    def calculate_gsi_wcus(self, table) -> List[tuple[str, float]]:
        """Calculate WCUs for each affected GSI.

        Args:
            table: Table instance containing GSI definitions

        Returns:
            List of (gsi_name, wcus) tuples
        """
        gsi_map = {gsi.name: gsi for gsi in table.gsi_list}
        results = []

        for gsi_name in self.gsi_list:
            gsi = gsi_map.get(gsi_name)
            if not gsi:
                continue

            wcus = gsi.write_wcus()
            if isinstance(self, ItemCountMixin):
                wcus *= self.item_count

            results.append((gsi_name, wcus))

        return results


class ReadMixin(AccessPatternCommon, StronglyConsistentMixin):
    """Base for read operations."""


class SearchMixin(ReadMixin, ItemCountMixin, GsiMixin):
    """Base for multi-item read operations that support GSI targeting (Query, Scan)."""

    @model_validator(mode='after')
    def _validate_gsi_consistency(self) -> Self:
        """Validate that GSI operations cannot use strong consistency."""
        if self.gsi is not None and self.strongly_consistent:
            raise ValueError(
                'GSI does not support strongly consistent reads. '
                f'gsi: "{self.gsi}", strongly_consistent: {self.strongly_consistent}'
            )
        return self

    def calculate_rcus(self) -> float:
        """Calculate Read Capacity Units."""
        total_size_bytes = self.item_size_bytes * self.item_count
        return math.ceil(total_size_bytes / RCU_SIZE) * self.consistency_multiplier()


class WriteMixin(AccessPatternCommon, GsiListMixin):
    """Base for write operations."""

    def calculate_wcus(self) -> float:
        """Calculate Write Capacity Units."""
        return math.ceil(self.item_size_bytes / WCU_SIZE)


class GetItemAccessPattern(ReadMixin):
    """GetItem operation."""

    operation: Literal['GetItem'] = 'GetItem'

    def calculate_rcus(self) -> float:
        """Calculate Read Capacity Units."""
        return math.ceil(self.item_size_bytes / RCU_SIZE) * self.consistency_multiplier()


class QueryAccessPattern(SearchMixin):
    """Query operation."""

    operation: Literal['Query'] = 'Query'


class ScanAccessPattern(SearchMixin):
    """Scan operation."""

    operation: Literal['Scan'] = 'Scan'


class PutItemAccessPattern(WriteMixin):
    """PutItem operation."""

    operation: Literal['PutItem'] = 'PutItem'


class UpdateItemAccessPattern(WriteMixin):
    """UpdateItem operation."""

    operation: Literal['UpdateItem'] = 'UpdateItem'


class DeleteItemAccessPattern(WriteMixin):
    """DeleteItem operation."""

    operation: Literal['DeleteItem'] = 'DeleteItem'


class BatchGetItemAccessPattern(ReadMixin, ItemCountMixin):
    """BatchGetItem operation."""

    operation: Literal['BatchGetItem'] = 'BatchGetItem'

    @field_validator('item_count')
    @classmethod
    def _validate_item_count_max(cls, v: int) -> int:
        """Validate item_count is within BatchGetItem limits."""
        if v > MAX_BATCH_GET_ITEMS:
            raise ValueError(f'must be at most {MAX_BATCH_GET_ITEMS}. item_count: {v}')
        return v

    def calculate_rcus(self) -> float:
        """Calculate Read Capacity Units."""
        rcus_per_item = math.ceil(self.item_size_bytes / RCU_SIZE)
        return rcus_per_item * self.item_count * self.consistency_multiplier()


class BatchWriteItemAccessPattern(WriteMixin, ItemCountMixin):
    """BatchWriteItem operation."""

    operation: Literal['BatchWriteItem'] = 'BatchWriteItem'

    @field_validator('item_count')
    @classmethod
    def _validate_item_count_max(cls, v: int) -> int:
        """Validate item_count is within BatchWriteItem limits."""
        if v > MAX_BATCH_WRITE_ITEMS:
            raise ValueError(f'must be at most {MAX_BATCH_WRITE_ITEMS}. item_count: {v}')
        return v

    def calculate_wcus(self) -> float:
        """Calculate Write Capacity Units."""
        wcus_per_item = math.ceil(self.item_size_bytes / WCU_SIZE)
        return wcus_per_item * self.item_count


class TransactGetItemsAccessPattern(AccessPatternCommon, ItemCountMixin):
    """TransactGetItems operation."""

    operation: Literal['TransactGetItems'] = 'TransactGetItems'

    @field_validator('item_count')
    @classmethod
    def _validate_item_count_max(cls, v: int) -> int:
        """Validate item_count is within TransactGetItems limits."""
        if v > MAX_TRANSACT_ITEMS:
            raise ValueError(f'must be at most {MAX_TRANSACT_ITEMS}. item_count: {v}')
        return v

    def calculate_rcus(self) -> float:
        """Calculate Read Capacity Units."""
        rcus_per_item = math.ceil(self.item_size_bytes / RCU_SIZE)
        return 2 * rcus_per_item * self.item_count


class TransactWriteItemsAccessPattern(AccessPatternCommon, ItemCountMixin, GsiListMixin):
    """TransactWriteItems operation."""

    operation: Literal['TransactWriteItems'] = 'TransactWriteItems'

    @field_validator('item_count')
    @classmethod
    def _validate_item_count_max(cls, v: int) -> int:
        """Validate item_count is within TransactWriteItems limits."""
        if v > MAX_TRANSACT_ITEMS:
            raise ValueError(f'must be at most {MAX_TRANSACT_ITEMS}. item_count: {v}')
        return v

    def calculate_wcus(self) -> float:
        """Calculate Write Capacity Units."""
        wcus_per_item = math.ceil(self.item_size_bytes / WCU_SIZE)
        return 2 * wcus_per_item * self.item_count


AccessPattern = Annotated[
    Union[
        GetItemAccessPattern,
        QueryAccessPattern,
        ScanAccessPattern,
        PutItemAccessPattern,
        UpdateItemAccessPattern,
        DeleteItemAccessPattern,
        BatchGetItemAccessPattern,
        BatchWriteItemAccessPattern,
        TransactGetItemsAccessPattern,
        TransactWriteItemsAccessPattern,
    ],
    Field(discriminator='operation'),
]


class DataModel(BaseModel):
    """Root model for calculator input."""

    access_pattern_list: List[AccessPattern]
    table_list: List[Table]

    @field_validator('access_pattern_list')
    @classmethod
    def _validate_access_pattern_list_non_empty(
        cls, v: List[AccessPattern]
    ) -> List[AccessPattern]:
        """Validate access_pattern_list is not empty."""
        if not v:
            raise ValueError('access_pattern_list must contain at least one access pattern')
        return v

    @model_validator(mode='after')
    def _validate_cross_references(self) -> 'DataModel':
        """Validate cross-model references."""
        table_map = {table.name: table for table in self.table_list}
        self._validate_unique_table_names()
        self._validate_access_patterns(table_map)
        return self

    def _validate_unique_table_names(self) -> None:
        """Validate that table names are unique."""
        table_names = [table.name for table in self.table_list]
        seen_names = set()
        for name in table_names:
            if name in seen_names:
                raise ValueError(f'duplicate table name. name: "{name}"')
            seen_names.add(name)

    def _validate_access_patterns(self, table_map: dict) -> None:
        """Validate all access patterns against table definitions."""
        for ap in self.access_pattern_list:
            self._validate_access_pattern_table_exists(ap, table_map)
            table = table_map[ap.table]
            gsi_names = {gsi.name for gsi in table.gsi_list}
            self._validate_access_pattern_gsi_references(ap, gsi_names)
            self._validate_access_pattern_item_size(ap, table, gsi_names)

    def _validate_access_pattern_table_exists(self, ap, table_map: dict) -> None:
        """Validate that the access pattern references an existing table."""
        if ap.table not in table_map:
            raise ValueError(f'table does not exist. table: "{ap.table}"')

    def _validate_access_pattern_gsi_references(self, ap, gsi_names: set) -> None:
        """Validate that GSI references in access pattern exist."""
        if hasattr(ap, 'gsi') and ap.gsi is not None:
            if ap.gsi not in gsi_names:
                raise ValueError(f'GSI does not exist. gsi: "{ap.gsi}", table: "{ap.table}"')

        if hasattr(ap, 'gsi_list'):
            for gsi_name in ap.gsi_list:
                if gsi_name not in gsi_names:
                    raise ValueError(f'GSI does not exist. gsi: "{gsi_name}", table: "{ap.table}"')

    def _validate_access_pattern_item_size(self, ap, table, gsi_names: set) -> None:
        """Validate that access pattern item size doesn't exceed target size."""
        if hasattr(ap, 'gsi') and ap.gsi is not None:
            gsi = next((g for g in table.gsi_list if g.name == ap.gsi), None)
            if gsi and ap.item_size_bytes > gsi.item_size_bytes:
                raise ValueError(
                    f'item_size_bytes cannot exceed GSI item_size_bytes. '
                    f'access_pattern_size: {ap.item_size_bytes}, gsi_size: {gsi.item_size_bytes}, gsi: "{ap.gsi}"'
                )
        else:
            if ap.item_size_bytes > table.item_size_bytes:
                raise ValueError(
                    f'item_size_bytes cannot exceed table item_size_bytes. '
                    f'access_pattern_size: {ap.item_size_bytes}, table_size: {table.item_size_bytes}, table: "{ap.table}"'
                )


_ERROR_MESSAGE_MAP = {
    'string_too_short': 'cannot be empty',
    'greater_than': 'must be greater than {gt}',
    'greater_than_equal': 'must be at least {ge}',
    'less_than_equal': 'must be at most {le}',
    'too_long': 'must have at most {max_length} items. {field_name}: {actual_length}',
}


def _format_location(loc: tuple) -> str:
    """Format Pydantic location tuple as readable path.

    Example: ('table_list', 3, 'item_count') -> 'table_list[3].item_count'
    """
    parts = []
    for item in loc:
        if isinstance(item, int):
            parts.append(f'[{item}]')
        else:
            if parts:
                parts.append('.')
            parts.append(str(item))
    return ''.join(parts)


def _customize_error_message(error: dict) -> str:
    """Convert Pydantic error to custom message format."""
    error_type = error.get('type', '')
    ctx = error.get('ctx', {})
    input_value = error.get('input')
    template = _ERROR_MESSAGE_MAP.get(error_type)
    if template:
        # For too_long, inject field_name and don't append input_value
        if error_type == 'too_long':
            field_name = error.get('loc', ('value',))[-1]
            ctx = {**ctx, 'field_name': field_name}
            return template.format(**ctx)
        msg = template.format(**ctx) if ctx else template
        field_name = error.get('loc', ('value',))[-1]
        return f'{msg}. {field_name}: {input_value}'
    msg = error.get('msg', '')
    # Strip "Value error, " prefix from custom validators
    if msg.startswith('Value error, '):
        msg = msg[len('Value error, ') :]
    return msg


def format_validation_errors(e: ValidationError) -> str:
    r"""Format Pydantic validation errors with location context and custom messages.

    Extracts location paths from Pydantic errors and prefixes
    each error message with the location for context. Also converts
    Pydantic's default constraint messages to custom format.

    Examples:
        Constraint error:
            "Input should be greater than or equal to 1"
            becomes
            "table_list[3].item_count: must be at least 1. item_count: -3"

        Model validator error (GSI size exceeds table size):
            "Value error, GSI item_size_bytes cannot exceed table item_size_bytes..."
            becomes
            "table_list[0]: GSI item_size_bytes cannot exceed table item_size_bytes. gsi_item_size_bytes: 800, table_item_size_bytes: 500"

        Model validator error (GSI with strongly consistent reads):
            "Value error, GSI does not support strongly consistent reads..."
            becomes
            "access_pattern_list[0].Query: GSI does not support strongly consistent reads. gsi: \"GSI1\", strongly_consistent: True"

        Field validator error (duplicate GSI names):
            "Value error, duplicate GSI name. name: \"GSI1\""
            becomes
            "table_list[0].gsi_list: duplicate GSI name. name: \"GSI1\""

        Discriminated union error (empty GSI name in QueryAccessPattern):
            "String should have at least 1 character"
            becomes
            "access_pattern_list[0].Query.gsi: cannot be empty. gsi: "

            Note: 'Query' appears in the path because AccessPattern uses
            Field(discriminator='operation'), so Pydantic includes the
            discriminator value in the error location.

        Type parsing error (invalid boolean from JSON):
            "Input should be a valid boolean, unable to interpret input"
            becomes
            "access_pattern_list[0].GetItem.strongly_consistent: Input should be a valid boolean, unable to interpret input"

            Note: Pydantic coerces "yes", "true", "1", "on" to True. Only
            unrecognizable values like "invalid_value" trigger this error.

        Invalid discriminator value (unknown operation type):
            "Input tag 'ASD' found using 'operation' does not match any of the expected tags..."
            becomes
            "access_pattern_list[0]: Input tag 'ASD' found using 'operation' does not match any of the expected tags: 'GetItem', 'Query', 'Scan', 'PutItem', 'UpdateItem', 'DeleteItem', 'BatchGetItem', 'BatchWriteItem', 'TransactGetItems', 'TransactWriteItems'"
    """
    formatted_errors = []
    for error in e.errors():
        loc = error.get('loc', ())
        msg = _customize_error_message(error)
        location = _format_location(loc)
        if location:
            formatted_errors.append(f'{location}: {msg}')
        else:
            formatted_errors.append(msg)
    return '\n'.join(formatted_errors)
