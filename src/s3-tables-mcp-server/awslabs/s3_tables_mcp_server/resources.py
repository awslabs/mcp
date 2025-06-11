#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""MCP resource definitions for S3 Tables MCP Server."""

import json

from loguru import logger

from .models import (
    NamespacesResource,
    NamespaceSummary,
    TableBucketsResource,
    TableBucketSummary,
    TablesResource,
    TableSummary,
)
from .utils import get_s3tables_client


async def list_table_buckets_resource() -> str:
    """List all S3 Tables buckets."""
    try:
        client = get_s3tables_client()
        table_buckets = []
        paginator = client.get_paginator('list_table_buckets')
        
        for page in paginator.paginate():
            for bucket in page.get('tableBuckets', []):
                table_buckets.append(TableBucketSummary(
                    arn=bucket['arn'],
                    name=bucket['name'],
                    owner_account_id=bucket['ownerAccountId'],
                    created_at=bucket['createdAt'],
                    table_bucket_id=bucket.get('tableBucketId'),
                    type=bucket.get('type')
                ))
        
        resource = TableBucketsResource(table_buckets=table_buckets, total_count=len(table_buckets))
        return resource.model_dump_json()
        
    except Exception as e:
        logger.error(f'Failed to list table buckets: {str(e)}')
        return json.dumps({'error': str(e), 'table_buckets': [], 'total_count': 0})


async def list_namespaces_resource() -> str:
    """List all namespaces across all table buckets."""
    try:
        client = get_s3tables_client()
        
        table_buckets = []
        bucket_paginator = client.get_paginator('list_table_buckets')
        for page in bucket_paginator.paginate():
            table_buckets.extend(page.get('tableBuckets', []))
        
        all_namespaces = []
        for bucket in table_buckets:
            try:
                namespace_paginator = client.get_paginator('list_namespaces')
                for page in namespace_paginator.paginate(tableBucketARN=bucket['arn']):
                    for namespace in page.get('namespaces', []):
                        all_namespaces.append(NamespaceSummary(
                            namespace=namespace['namespace'],
                            created_at=namespace['createdAt'],
                            created_by=namespace['createdBy'],
                            owner_account_id=namespace['ownerAccountId'],
                            namespace_id=namespace.get('namespaceId'),
                            table_bucket_id=namespace.get('tableBucketId')
                        ))
            except Exception as e:
                logger.warning(f'Failed to list namespaces for bucket {bucket["arn"]}: {str(e)}')
                continue
        
        resource = NamespacesResource(namespaces=all_namespaces, total_count=len(all_namespaces))
        return resource.model_dump_json()
        
    except Exception as e:
        logger.error(f'Failed to list namespaces: {str(e)}')
        return json.dumps({'error': str(e), 'namespaces': [], 'total_count': 0})


async def list_tables_resource() -> str:
    """List all Iceberg tables across all table buckets and namespaces."""
    try:
        client = get_s3tables_client()
        
        table_buckets = []
        bucket_paginator = client.get_paginator('list_table_buckets')
        for page in bucket_paginator.paginate():
            table_buckets.extend(page.get('tableBuckets', []))
        
        all_tables = []
        for bucket in table_buckets:
            try:
                table_paginator = client.get_paginator('list_tables')
                for page in table_paginator.paginate(tableBucketARN=bucket['arn']):
                    for table in page.get('tables', []):
                        all_tables.append(TableSummary(
                            namespace=table['namespace'],
                            name=table['name'],
                            type=table['type'],
                            table_arn=table['tableARN'],
                            created_at=table['createdAt'],
                            modified_at=table['modifiedAt'],
                            namespace_id=table.get('namespaceId'),
                            table_bucket_id=table.get('tableBucketId')
                        ))
            except Exception as e:
                logger.warning(f'Failed to list tables for bucket {bucket["arn"]}: {str(e)}')
                continue
        
        resource = TablesResource(tables=all_tables, total_count=len(all_tables))
        return resource.model_dump_json()
        
    except Exception as e:
        logger.error(f'Failed to list tables: {str(e)}')
        return json.dumps({'error': str(e), 'tables': [], 'total_count': 0})
