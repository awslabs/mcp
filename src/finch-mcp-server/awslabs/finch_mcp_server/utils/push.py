"""Utility functions for pushing container images to repositories.

This module provides functions to push container images to repositories,
including Amazon ECR, and handle image tagging with hash values.

Note: These tools are intended for development and prototyping purposes only
and are not meant for production use cases.
"""

import logging
import re
from ..consts import ECR_REPOSITORY_PATTERN, STATUS_ERROR, STATUS_SUCCESS
from .common import execute_command, format_result
from typing import Any, Dict


logger = logging.getLogger(__name__)


def is_ecr_repository(repository: str) -> bool:
    """Validate if the provided repository URL is an ECR repository.

    ECR repository URLs typically follow the pattern:
    <aws_account_id>.dkr.ecr.<region>.amazonaws.com/<repository_name>:<tag>

    Args:
        repository: The repository URL to validate

    Returns:
        bool: True if the repository is an ECR repository, False otherwise

    """
    # Check if the repository matches the ECR pattern and has a valid region format
    match = re.match(ECR_REPOSITORY_PATTERN, repository)
    if not match:
        return False

    # Validate that the region is a valid AWS region format (e.g., us-west-2, eu-central-1)
    region = match.group(2)
    region_pattern = r'^[a-z]{2}-[a-z]+-\d+$'
    return bool(re.match(region_pattern, region))


def get_image_hash(image: str) -> Dict[str, Any]:
    """Get the hash (digest) of a container image.

    Args:
        image: The image name to get the hash for

    Returns:
        Dict containing status, message, and the image hash if successful

    """
    inspect_result = execute_command(['finch', 'image', 'inspect', image])

    if inspect_result.returncode != 0:
        return format_result(
            STATUS_ERROR,
            f'Failed to get hash for image {image}: {inspect_result.stderr}',
            stderr=inspect_result.stderr,
        )

    hash_match = re.search(r'"Id":\s*"(sha256:[a-f0-9]+)"', inspect_result.stdout)

    if not hash_match:
        return format_result(
            STATUS_ERROR, f'Could not find hash in image inspect output for {image}'
        )

    image_hash = hash_match.group(1)
    return format_result(
        STATUS_SUCCESS, f'Successfully retrieved hash for image {image}', hash=image_hash
    )


def push_image(image: str) -> Dict[str, Any]:
    """Push an image to a repository, replacing the tag with the image hash.

    Args:
        image: The image to push

    Returns:
        Result of the push task

    """
    hash_result = get_image_hash(image)

    if hash_result['status'] != STATUS_SUCCESS:
        return hash_result

    image_hash = hash_result['hash']

    tag_separator_index = image.rfind(':')
    if tag_separator_index > 0 and '/' not in image[tag_separator_index:]:
        repository = image[:tag_separator_index]
    else:
        repository = image

    short_hash = image_hash[7:19] if image_hash.startswith('sha256:') else image_hash[:12]
    hash_tagged_image = f'{repository}:{short_hash}'

    tag_result = execute_command(['finch', 'image', 'tag', image, hash_tagged_image])

    if tag_result.returncode != 0:
        return format_result(
            STATUS_ERROR,
            f'Failed to tag image with hash: {tag_result.stderr}',
            stderr=tag_result.stderr,
        )

    push_result = execute_command(['finch', 'image', 'push', hash_tagged_image])

    if push_result.returncode == 0:
        return format_result(
            STATUS_SUCCESS,
            f'Successfully pushed image {hash_tagged_image} (original: {image}).',
            stdout=push_result.stdout,
        )
    else:
        return format_result(
            STATUS_ERROR,
            f'Failed to push image {hash_tagged_image}: {push_result.stderr}',
            stderr=push_result.stderr,
        )
