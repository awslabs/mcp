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
"""Utility functions for working with Amazon ECR repositories.

This module provides functions to check if an ECR repository exists and create it if needed.

Note: These tools are intended for development and prototyping purposes only and are not meant
for production use cases.
"""

import boto3
from ..consts import STATUS_ERROR, STATUS_SUCCESS
from .common import format_result
from botocore.exceptions import ClientError
from loguru import logger
from typing import Dict, Optional


def create_ecr_repository(
    repository_name: str,
    region: Optional[str] = None,
) -> Dict[str, str]:
    """Check if an ECR repository exists and create it if it doesn't.

    This function first checks if the specified ECR repository exists using boto3.
    If the repository doesn't exist, it creates a new one with the given name.

    Args:
        repository_name: The name of the repository to check or create in ECR
        region: AWS region for the ECR repository. If not provided, uses the default region
                from AWS configuration

    Returns:
        Dict[str, Any]: A dictionary containing:
            - status: "success" if the operation succeeded, "error" otherwise
            - message: Details about the result of the operation

    """
    try:
        ecr_client = boto3.client('ecr', region_name=region) if region else boto3.client('ecr')

        try:
            response = ecr_client.describe_repositories(repositoryNames=[repository_name])

            if 'repositories' in response and len(response['repositories']) > 0:
                repository = response['repositories'][0]
                repository_uri = repository.get('repositoryUri', '')

                logger.debug(
                    f"ECR repository '{repository_name}' already exists with URI: {repository_uri}"
                )
                return format_result(
                    STATUS_SUCCESS,
                    f"ECR repository '{repository_name}' already exists.",
                )
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')

            if error_code != 'RepositoryNotFoundException':
                return format_result(
                    STATUS_ERROR,
                    f'Error checking ECR repository: {str(e)}',
                )

        response = ecr_client.create_repository(
            repositoryName=repository_name,
            imageScanningConfiguration={'scanOnPush': True},
            imageTagMutability='IMMUTABLE',
        )

        repository = response.get('repository', {})
        repository_uri = repository.get('repositoryUri', '')

        logger.debug(f"Created ECR repository '{repository_name}' with URI: {repository_uri}")
        return format_result(
            STATUS_SUCCESS,
            f"Successfully created ECR repository '{repository_name}' with URI: {repository_uri}.",
        )

    except ClientError as e:
        return format_result(
            STATUS_ERROR,
            f"Failed to create ECR repository '{repository_name}': {str(e)}",
        )
    except Exception as e:
        return format_result(
            STATUS_ERROR,
            f"Unexpected error creating ECR repository '{repository_name}': {str(e)}",
        )
