"""Utility functions for working with Amazon ECR repositories.

This module provides functions to check if an ECR repository exists and create it if needed.
"""

import json
import logging
from ..consts import STATUS_ERROR, STATUS_SUCCESS
from .common import execute_command, format_result
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


def check_ecr_repository(
    app_name: str,
    region: Optional[str] = None,
    scan_on_push: bool = True,
    image_tag_mutability: str = 'IMMUTABLE',
) -> Dict[str, Any]:
    """Check if an ECR repository exists and create it if it doesn't.

    This function first checks if the specified ECR repository exists by using the AWS CLI.
    If the repository doesn't exist, it creates a new one with the given name.

    Args:
        app_name: The name of the application/repository to check or create in ECR
        region: AWS region for the ECR repository. If not provided, uses the default region
                from AWS configuration
        scan_on_push: Whether to enable scan on push for the repository. Defaults to True.
        image_tag_mutability: Image tag mutability setting. Can be "MUTABLE" or "IMMUTABLE".
                             Defaults to "IMMUTABLE".

    Returns:
        Dict[str, Any]: A dictionary containing:
            - status (str): "success" if the operation succeeded, "error" otherwise
            - message (str): A descriptive message about the result of the operation
            - repository_uri (str, optional): The URI of the repository if successful
            - stdout (str, optional): Standard output from the command if successful
            - stderr (str, optional): Standard error output if the command failed
            - exists (bool, optional): Whether the repository already existed

    """
    describe_cmd = ['aws', 'ecr', 'describe-repositories', '--repository-names', app_name]

    describe_result = execute_command(describe_cmd)

    if describe_result.returncode == 0:
        try:
            repo_data = json.loads(describe_result.stdout)
            if 'repositories' in repo_data and len(repo_data['repositories']) > 0:
                repository = repo_data['repositories'][0]
                repository_uri = repository.get('repositoryUri', '')

                return format_result(
                    STATUS_SUCCESS,
                    f"ECR repository '{app_name}' already exists.",
                    repository_uri=repository_uri,
                    stdout=describe_result.stdout,
                    exists=True,
                )
        except json.JSONDecodeError:
            return format_result(
                STATUS_ERROR,
                f'Failed to parse ECR repository information: {describe_result.stderr}',
                stderr=describe_result.stderr,
            )

    if 'RepositoryNotFoundException' not in describe_result.stderr:
        return format_result(
            STATUS_ERROR,
            f'Error checking ECR repository: {describe_result.stderr}',
            stderr=describe_result.stderr,
        )

    # Repository doesn't exist, create it
    create_cmd = [
        'aws',
        'ecr',
        'create-repository',
        '--repository-name',
        app_name,
        '--image-scanning-configuration',
        f'scanOnPush={str(scan_on_push).lower()}',
        '--image-tag-mutability',
        image_tag_mutability,
    ]

    create_result = execute_command(create_cmd)

    if create_result.returncode == 0:
        try:
            repo_data = json.loads(create_result.stdout)
            repository = repo_data.get('repository', {})
            repository_uri = repository.get('repositoryUri', '')

            return format_result(
                STATUS_SUCCESS,
                f"Successfully created ECR repository '{app_name}'.",
                repository_uri=repository_uri,
                stdout=create_result.stdout,
                exists=False,
            )
        except json.JSONDecodeError:
            return format_result(
                STATUS_ERROR,
                f'Failed to parse created ECR repository information: {create_result.stderr}',
                stderr=create_result.stderr,
            )
    else:
        return format_result(
            STATUS_ERROR,
            f"Failed to create ECR repository '{app_name}': {create_result.stderr}",
            stderr=create_result.stderr,
        )
