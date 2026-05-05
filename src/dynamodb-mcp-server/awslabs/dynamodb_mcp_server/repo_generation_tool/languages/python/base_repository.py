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

import boto3
from botocore.exceptions import ClientError
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pydantic import BaseModel
from typing import Any, Generic, TypeVar


T = TypeVar('T', bound='ConfigurableEntity')

# Type alias for DynamoDB key values (supports String and Number key types)
KeyType = str | int | Decimal


class OptimisticLockException(Exception):
    """Raised when optimistic locking fails due to concurrent modification"""

    def __init__(self, entity_name: str, message: str = 'Item was modified by another process'):
        self.entity_name = entity_name
        super().__init__(f'{entity_name}: {message}')


@dataclass
class EntityConfig:
    """Configuration for DynamoDB entity key generation"""

    entity_type: str
    pk_builder: Callable[[Any], KeyType]
    pk_lookup_builder: Callable[..., KeyType]
    sk_builder: Callable[[Any], KeyType] | None = None
    sk_lookup_builder: Callable[..., KeyType] | None = None
    prefix_builder: Callable[..., str] | None = None  # Prefix is always string


class ConfigurableEntity(BaseModel):
    """Base class for entities with configuration-based key generation"""

    version: int = 1  # Optimistic locking version field

    @classmethod
    def get_config(cls) -> EntityConfig:
        """Return the entity configuration - must be implemented by subclasses"""
        raise NotImplementedError('Subclasses must implement get_config()')

    def pk(self) -> KeyType:
        """Get partition key value"""
        return self.get_config().pk_builder(self)

    def sk(self) -> KeyType | None:
        """Get sort key value"""
        config = self.get_config()
        if config.sk_builder is None:
            return None
        return config.sk_builder(self)

    @classmethod
    def build_pk_for_lookup(cls, *args, **kwargs) -> KeyType:
        """Build partition key for lookups"""
        if args:
            return cls.get_config().pk_lookup_builder(*args)
        else:
            return cls.get_config().pk_lookup_builder(**kwargs)

    @classmethod
    def build_sk_for_lookup(cls, *args, **kwargs) -> KeyType | None:
        """Build sort key for lookups"""
        config = cls.get_config()
        if config.sk_lookup_builder is None:
            return None
        if args:
            return config.sk_lookup_builder(*args)
        else:
            return config.sk_lookup_builder(**kwargs)

    @classmethod
    def get_sk_prefix(cls, **kwargs) -> str:
        """Get prefix for querying multiple items"""
        config = cls.get_config()
        if config.prefix_builder:
            return config.prefix_builder(**kwargs)
        return f'{config.entity_type}#'


class BaseRepository(Generic[T]):
    """Generic base repository for DynamoDB operations"""

    def __init__(
        self, model_class: type[T], table_name: str, pkey_name: str, skey_name: str | None = None
    ):
        self.model_class = model_class
        self.pkey_name = pkey_name
        self.skey_name = skey_name
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)

    def create(self, entity: T) -> T:
        """Create a new entity with optimistic locking (prevents overwrites)

        Note: Uses exclude_none=True to support sparse GSIs. Fields with None
        values are not written to DynamoDB, so items without GSI key values
        won't be indexed in those GSIs.
        """
        try:
            item = entity.model_dump(exclude_none=True)
            item[self.pkey_name] = entity.pk()
            if self.skey_name is not None:
                sk_value = entity.sk()
                if sk_value is not None:
                    item[self.skey_name] = sk_value

            # Ensure version starts at 1
            item['version'] = 1

            # Use condition to prevent overwriting existing items
            condition = f'attribute_not_exists({self.pkey_name})'

            self.table.put_item(Item=item, ConditionExpression=condition)

            # Update entity version and return
            entity.version = 1
            return entity
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConditionalCheckFailedException':
                raise OptimisticLockException(
                    self.model_class.__name__,
                    'Item already exists. Use update() to modify existing items.',
                ) from e
            error_msg = e.response['Error']['Message']
            raise RuntimeError(
                f'Failed to create {self.model_class.__name__}: {error_code} - {error_msg}'
            ) from e

    def get(
        self, pk: KeyType, sk: KeyType | None = None, consistent_read: bool = False
    ) -> T | None:
        """Generic get operation with optional consistent read"""
        try:
            key = {self.pkey_name: pk}
            if self.skey_name is not None and sk is not None:
                key[self.skey_name] = sk
            response = self.table.get_item(Key=key, ConsistentRead=consistent_read)
            if 'Item' in response:
                return self.model_class(**response['Item'])
            return None
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            raise RuntimeError(
                f'Failed to get {self.model_class.__name__}: {error_code} - {error_msg}'
            ) from e

    def update(self, entity: T) -> T:
        """Update an existing entity with optimistic locking (prevents lost updates)

        Note: Uses PutItem with exclude_none=True to support sparse GSIs. This
        replaces the entire item - fields with None values are not written, so
        they are removed from DynamoDB. Items will be removed from sparse GSIs
        when their key fields become None.
        """
        try:
            expected_version = entity.version
            new_version = expected_version + 1

            item = entity.model_dump(exclude_none=True)
            item[self.pkey_name] = entity.pk()
            if self.skey_name is not None:
                sk_value = entity.sk()
                if sk_value is not None:
                    item[self.skey_name] = sk_value

            # Set new version
            item['version'] = new_version

            # Use condition to check version matches (optimistic locking)
            self.table.put_item(
                Item=item,
                ConditionExpression='version = :expected_version',
                ExpressionAttributeValues={':expected_version': expected_version},
            )

            # Update entity version and return
            entity.version = new_version
            return entity
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConditionalCheckFailedException':
                raise OptimisticLockException(
                    self.model_class.__name__,
                    f'Item was modified by another process (expected version {expected_version})',
                ) from e
            error_msg = e.response['Error']['Message']
            raise RuntimeError(
                f'Failed to update {self.model_class.__name__}: {error_code} - {error_msg}'
            ) from e

    def delete(self, pk: KeyType, sk: KeyType | None = None) -> bool:
        """Generic delete operation"""
        try:
            key = {self.pkey_name: pk}
            if self.skey_name is not None and sk is not None:
                key[self.skey_name] = sk
            response = self.table.delete_item(Key=key)
            return response['ResponseMetadata']['HTTPStatusCode'] == 200
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            raise RuntimeError(
                f'Failed to delete {self.model_class.__name__}: {error_code} - {error_msg}'
            ) from e

    def delete_entity(self, entity: T) -> bool:
        """Delete using entity's pk/sk methods"""
        return self.delete(entity.pk(), entity.sk())

    def _parse_query_response(
        self, response: dict, skip_invalid_items: bool = True
    ) -> tuple[list[T], dict | None]:
        """Parse DynamoDB query/scan response into items and continuation token

        By default, skips items that fail validation. Set skip_invalid_items=False
        to raise an exception on validation errors instead.

        Args:
            response: DynamoDB query/scan response
            skip_invalid_items: If True, skip items that fail deserialization and continue. If False, raise exception on validation errors.

        Returns:
            tuple: (items, last_evaluated_key)
        """
        items = []
        for item in response.get('Items', []):
            try:
                items.append(self.model_class(**item))
            except Exception as e:
                if not skip_invalid_items:
                    raise RuntimeError(
                        f'Failed to deserialize {self.model_class.__name__}: {e}'
                    ) from e
                else:
                    print(f'Warning: Skipping invalid {self.model_class.__name__}: {e}')
                    continue

        return items, response.get('LastEvaluatedKey')

    def _parse_query_response_raw(
        self, response: dict
    ) -> tuple[list[dict[str, Any]], dict | None]:
        """Parse DynamoDB query/scan response into raw dict items and continuation token

        Used for item collection queries that return multiple entity types.
        Returns raw DynamoDB items without deserialization.

        Args:
            response: DynamoDB query/scan response

        Returns:
            tuple: (raw_items, last_evaluated_key)
        """
        items = response.get('Items', [])
        return items, response.get('LastEvaluatedKey')
