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
from pydantic import BaseModel
from typing import Any, Generic, TypeVar


T = TypeVar('T', bound='ConfigurableEntity')


@dataclass
class EntityConfig:
    """Configuration for DynamoDB entity key generation"""

    entity_type: str
    pk_builder: Callable[[Any], str]
    pk_lookup_builder: Callable[..., str]
    sk_builder: Callable[[Any], str] | None = None
    sk_lookup_builder: Callable[..., str] | None = None
    prefix_builder: Callable[..., str] | None = None


class ConfigurableEntity(BaseModel):
    """Base class for entities with configuration-based key generation"""

    @classmethod
    def get_config(cls) -> EntityConfig:
        """Return the entity configuration - must be implemented by subclasses"""
        raise NotImplementedError('Subclasses must implement get_config()')

    def pk(self) -> str:
        """Get partition key value"""
        return self.get_config().pk_builder(self)

    def sk(self) -> str | None:
        """Get sort key value"""
        config = self.get_config()
        if config.sk_builder is None:
            return None
        return config.sk_builder(self)

    @classmethod
    def build_pk_for_lookup(cls, *args, **kwargs) -> str:
        """Build partition key for lookups"""
        if args:
            return cls.get_config().pk_lookup_builder(*args)
        else:
            return cls.get_config().pk_lookup_builder(**kwargs)

    @classmethod
    def build_sk_for_lookup(cls, *args, **kwargs) -> str | None:
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
        """Generic create operation"""
        try:
            item = entity.model_dump()
            item[self.pkey_name] = entity.pk()
            if self.skey_name is not None:
                sk_value = entity.sk()
                if sk_value is not None:
                    item[self.skey_name] = sk_value
            self.table.put_item(Item=item)
            return entity
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            raise RuntimeError(
                f'Failed to create {self.model_class.__name__}: {error_code} - {error_msg}'
            ) from e

    def get(self, pk: str, sk: str | None = None) -> T | None:
        """Generic get operation"""
        try:
            key = {self.pkey_name: pk}
            if self.skey_name is not None and sk is not None:
                key[self.skey_name] = sk
            response = self.table.get_item(Key=key)
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
        """Generic update operation"""
        try:
            item = entity.model_dump()
            item[self.pkey_name] = entity.pk()
            if self.skey_name is not None:
                sk_value = entity.sk()
                if sk_value is not None:
                    item[self.skey_name] = sk_value
            self.table.put_item(Item=item)
            return entity
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            raise RuntimeError(
                f'Failed to update {self.model_class.__name__}: {error_code} - {error_msg}'
            ) from e

    def delete(self, pk: str, sk: str | None = None) -> bool:
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
