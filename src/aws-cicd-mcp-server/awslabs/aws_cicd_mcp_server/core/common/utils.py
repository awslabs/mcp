# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Utility functions for AWS CI/CD MCP Server."""

import boto3
from typing import Dict, List, Optional
from botocore.exceptions import ClientError
from .config import AWS_REGION


def paginate_results(client, operation: str, result_key: str, **kwargs) -> List:
    """Generic pagination helper using boto3 paginators."""
    try:
        paginator = client.get_paginator(operation)
        max_items = kwargs.pop('max_items', 100)
        
        results = []
        page_config = {'MaxItems': max_items} if max_items else {}
        
        for page in paginator.paginate(PaginationConfig=page_config, **kwargs):
            results.extend(page.get(result_key, []))
        
        return results
    except Exception:
        # Fallback to single call if pagination not supported
        response = getattr(client, operation)(**kwargs)
        return response.get(result_key, [])


async def validate_iam_role(role_arn: str, region: str = AWS_REGION) -> bool:
    """Validate IAM role exists."""
    try:
        iam = boto3.client('iam', region_name=region)
        role_name = role_arn.split('/')[-1]
        iam.get_role(RoleName=role_name)
        return True
    except ClientError:
        return False


async def validate_s3_bucket(bucket_name: str, region: str = AWS_REGION) -> bool:
    """Validate S3 bucket exists."""
    try:
        s3 = boto3.client('s3', region_name=region)
        s3.head_bucket(Bucket=bucket_name)
        return True
    except ClientError:
        return False
