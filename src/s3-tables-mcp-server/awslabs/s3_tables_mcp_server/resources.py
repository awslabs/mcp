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

"""MCP resource definitions for S3 Tables MCP Server."""

import json
from .models import (
    NamespacesResource,
    NamespaceSummary,
    TableBucketsResource,
    TableBucketSummary,
    TablesResource,
    TableSummary,
)
from .utils import get_s3tables_client
from pydantic import BaseModel
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar


T = TypeVar('T')
ResourceT = TypeVar('ResourceT', bound=BaseModel)


def create_error_response(error: Exception, resource_name: str) -> str:
    """Create a standardized error response.

    Args:
        error: The exception that occurred
        resource_name: The name of the resource being accessed

    Returns:
        A JSON string containing the error response
    """
    return json.dumps({'error': str(error), resource_name: [], 'total_count': 0})


async def paginate_and_collect(
    paginator: Any,
    collection_key: str,
    item_constructor: Callable[[Dict[str, Any]], T],
    **pagination_args,
) -> List[T]:
    """Collect items from a paginated response.

    Args:
        paginator: The paginator to use
        collection_key: The key in the response that contains the items
        item_constructor: A function that constructs an item from a response
        **pagination_args: Additional arguments to pass to the paginator

    Returns:
        A list of constructed items
    """
    items = []
    for page in paginator.paginate(**pagination_args):
        for item in page.get(collection_key, []):
            items.append(item_constructor(item))
    return items


async def create_resource_response(
    items: List[T], resource_class: Type[ResourceT], resource_name: str
) -> str:
    """Create a resource response.

    Args:
        items: The items to include in the resource
        resource_class: The resource class to use
        resource_name: The name of the resource

    Returns:
        A JSON string containing the resource response
    """
    try:
        resource = resource_class(**{resource_name: items, 'total_count': len(items)})
        return resource.model_dump_json()
    except Exception as e:
        return create_error_response(e, resource_name)


async def list_table_buckets_resource(region_name: Optional[str] = None) -> str:
    """List all S3 Tables buckets.

    Lists table buckets for your account. Requires s3tables:ListTableBuckets permission.
    The API supports pagination with continuationToken and filtering with prefix.

    Returns:
        A JSON string containing the list of table buckets and total count.
    """
    try:
        client = get_s3tables_client(region_name)
        paginator = client.get_paginator('list_table_buckets')

        table_buckets = await paginate_and_collect(
            paginator=paginator,
            collection_key='tableBuckets',
            item_constructor=lambda bucket: TableBucketSummary(
                arn=bucket['arn'],
                name=bucket['name'],
                owner_account_id=bucket['ownerAccountId'],
                created_at=bucket['createdAt'],
                table_bucket_id=bucket.get('tableBucketId'),
                type=bucket.get('type'),
            ),
        )

        return await create_resource_response(
            items=table_buckets, resource_class=TableBucketsResource, resource_name='table_buckets'
        )

    except Exception as e:
        return create_error_response(e, 'table_buckets')


async def get_table_buckets(region_name: Optional[str] = None) -> List[TableBucketSummary]:
    """Get all table buckets as TableBucketSummary objects.

    Returns:
        A list of TableBucketSummary objects
    """
    response = await list_table_buckets_resource(region_name=region_name)
    data = json.loads(response)
    if 'error' in data:
        raise Exception(data['error'])
    return [TableBucketSummary(**bucket) for bucket in data['table_buckets']]


async def list_namespaces_resource(region_name: Optional[str] = None) -> str:
    """List all namespaces across all table buckets.

    Lists the namespaces within table buckets. Requires s3tables:ListNamespaces permission.
    The API supports pagination with continuationToken and filtering with prefix.

    Returns:
        A JSON string containing the list of namespaces and total count.
    """
    try:
        client = get_s3tables_client(region_name)

        # Get all table buckets
        table_buckets = await get_table_buckets(region_name=region_name)

        # Then get namespaces for each bucket
        all_namespaces = []
        for bucket in table_buckets:
            try:
                namespace_paginator = client.get_paginator('list_namespaces')
                namespaces = await paginate_and_collect(
                    paginator=namespace_paginator,
                    collection_key='namespaces',
                    item_constructor=lambda namespace: NamespaceSummary(
                        namespace=namespace['namespace'],
                        created_at=namespace['createdAt'],
                        created_by=namespace['createdBy'],
                        owner_account_id=namespace['ownerAccountId'],
                        namespace_id=namespace.get('namespaceId'),
                        table_bucket_id=namespace.get('tableBucketId'),
                    ),
                    tableBucketARN=bucket.arn,
                )
                all_namespaces.extend(namespaces)
            except Exception as e:
                return create_error_response(e, 'namespaces')

        return await create_resource_response(
            items=all_namespaces, resource_class=NamespacesResource, resource_name='namespaces'
        )

    except Exception as e:
        return create_error_response(e, 'namespaces')


async def list_tables_resource(region_name: Optional[str] = None) -> str:
    """List all Iceberg tables across all table buckets and namespaces.

    Lists tables in the given table bucket. Requires s3tables:ListTables permission.
    The API supports pagination with continuationToken, filtering with prefix and namespace,
    and limiting results with maxTables.

    Returns:
        A JSON string containing the list of tables and total count.
    """
    try:
        client = get_s3tables_client(region_name)

        # Get all table buckets
        table_buckets = await get_table_buckets(region_name=region_name)

        # Then get tables for each bucket
        all_tables = []
        for bucket in table_buckets:
            try:
                table_paginator = client.get_paginator('list_tables')

                tables = await paginate_and_collect(
                    paginator=table_paginator,
                    collection_key='tables',
                    item_constructor=lambda table: TableSummary(
                        namespace=table['namespace'],
                        name=table['name'],
                        type=table['type'],
                        table_arn=table['tableARN'],
                        created_at=table['createdAt'],
                        modified_at=table['modifiedAt'],
                        namespace_id=table.get('namespaceId'),
                        table_bucket_id=table.get('tableBucketId'),
                    ),
                    tableBucketARN=bucket.arn,
                )

                all_tables.extend(tables)
            except Exception as e:
                return create_error_response(e, 'tables')

        return await create_resource_response(
            items=all_tables, resource_class=TablesResource, resource_name='tables'
        )

    except Exception as e:
        return create_error_response(e, 'tables')
