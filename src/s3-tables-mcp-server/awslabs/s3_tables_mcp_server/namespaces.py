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

"""Namespace Management tools for S3 Tables MCP Server."""

from .utils import get_s3tables_client, handle_exceptions
from typing import Any, Dict, Optional


@handle_exceptions
async def create_namespace(
    table_bucket_arn: str,
    namespace: str,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new namespace."""
    client = get_s3tables_client(region_name)
    response = client.create_namespace(tableBucketARN=table_bucket_arn, namespace=[namespace])

    return dict(response)


@handle_exceptions
async def delete_namespace(
    table_bucket_arn: str,
    namespace: str,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Delete a namespace.

    Permissions:
    You must have the s3tables:DeleteNamespace permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.delete_namespace(tableBucketARN=table_bucket_arn, namespace=namespace)
    return dict(response)


@handle_exceptions
async def get_namespace(
    table_bucket_arn: str, namespace: str, region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Get details about a namespace.

    Gets details about a namespace.

    Permissions:
    You must have the s3tables:GetNamespace permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.get_namespace(tableBucketARN=table_bucket_arn, namespace=namespace)
    return dict(response)
