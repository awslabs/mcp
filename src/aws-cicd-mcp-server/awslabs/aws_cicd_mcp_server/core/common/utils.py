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

"""Utility functions for AWS CI/CD MCP Server."""

import boto3
from typing import Dict, List, Optional
from botocore.exceptions import ClientError
from .config import AWS_REGION, DEFAULT_MAX_ITEMS, DEFAULT_PAGE_SIZE


def paginate_results(client, operation: str, result_key: str, **kwargs) -> List:
    """Generic pagination helper following AWS MCP server patterns."""
    try:
        paginator = client.get_paginator(operation)
        page_config = {
            'MaxItems': kwargs.pop('max_items', DEFAULT_MAX_ITEMS),
            'PageSize': kwargs.pop('page_size', DEFAULT_PAGE_SIZE)
        }
        
        results = []
        for page in paginator.paginate(PaginationConfig=page_config, **kwargs):
            results.extend(page.get(result_key, []))
        
        return results
    except ClientError:
        # Re-raise ClientError so it can be handled by the decorator
        raise
    except Exception:
        # Fallback to single call if pagination not supported
        try:
            response = getattr(client, operation)(**kwargs)
            return response.get(result_key, [])
        except ClientError:
            # Re-raise ClientError from fallback call
            raise


async def validate_iam_role(role_arn: str, region: str = AWS_REGION) -> bool:
    """Validate IAM role exists and is assumable."""
    try:
        iam = boto3.client('iam', region_name=region)
        role_name = role_arn.split('/')[-1]
        iam.get_role(RoleName=role_name)
        return True
    except ClientError:
        return False


async def validate_s3_bucket(bucket_name: str, region: str = AWS_REGION) -> bool:
    """Validate S3 bucket exists and is accessible."""
    try:
        s3 = boto3.client('s3', region_name=region)
        s3.head_bucket(Bucket=bucket_name)
        return True
    except ClientError:
        return False


def remove_null_values(data: Dict) -> Dict:
    """Remove None values from dictionary."""
    return {k: v for k, v in data.items() if v is not None}
