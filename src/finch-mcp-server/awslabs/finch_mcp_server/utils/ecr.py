"""Utility functions for working with Amazon ECR repositories.

This module provides functions to check if an ECR repository exists and create it if needed.

Note: These tools are intended for development and prototyping purposes only and are not meant
for production use cases.
"""

import boto3
import logging
from ..consts import STATUS_ERROR, STATUS_SUCCESS
from .common import format_result
from botocore.exceptions import ClientError
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


def create_ecr_repository(
    app_name: str,
    region: Optional[str] = None,
) -> Dict[str, Any]:
    """Check if an ECR repository exists and create it if it doesn't.

    This function first checks if the specified ECR repository exists using boto3.
    If the repository doesn't exist, it creates a new one with the given name.

    Args:
        app_name: The name of the application/repository to check or create in ECR
        region: AWS region for the ECR repository. If not provided, uses the default region
                from AWS configuration

    Returns:
        Dict[str, Any]: A dictionary containing:
            - status (str): "success" if the operation succeeded, "error" otherwise
            - message (str): A descriptive message about the result of the operation
            - repository_uri (str, optional): The URI of the repository if successful
            - exists (bool, optional): Whether the repository already existed

    """
    try:
        # Create ECR client with optional region
        ecr_client = boto3.client('ecr', region_name=region) if region else boto3.client('ecr')

        # Try to describe the repository to check if it exists
        try:
            response = ecr_client.describe_repositories(repositoryNames=[app_name])

            if 'repositories' in response and len(response['repositories']) > 0:
                repository = response['repositories'][0]
                repository_uri = repository.get('repositoryUri', '')

                return format_result(
                    STATUS_SUCCESS,
                    f"ECR repository '{app_name}' already exists.",
                    repository_uri=repository_uri,
                    exists=True,
                )
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')

            # If repository doesn't exist, we'll create it
            if error_code != 'RepositoryNotFoundException':
                return format_result(
                    STATUS_ERROR,
                    f'Error checking ECR repository: {str(e)}',
                )

        # Repository doesn't exist, create it
        response = ecr_client.create_repository(
            repositoryName=app_name,
            imageScanningConfiguration={'scanOnPush': True},
            imageTagMutability='IMMUTABLE',
        )

        repository = response.get('repository', {})
        repository_uri = repository.get('repositoryUri', '')

        return format_result(
            STATUS_SUCCESS,
            f"Successfully created ECR repository '{app_name}'.",
            repository_uri=repository_uri,
            exists=False,
        )

    except ClientError as e:
        return format_result(
            STATUS_ERROR,
            f"Failed to create ECR repository '{app_name}': {str(e)}",
        )
    except Exception as e:
        return format_result(
            STATUS_ERROR,
            f"Unexpected error creating ECR repository '{app_name}': {str(e)}",
        )
