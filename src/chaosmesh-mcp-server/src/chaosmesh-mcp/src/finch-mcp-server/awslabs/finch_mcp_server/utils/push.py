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

"""Utility functions for pushing container images to repositories.

This module provides functions to push container images to repositories,
including Amazon ECR, and handle image tagging with hash values.

Note: These tools are intended for development and prototyping purposes only
and are not meant for production use cases.
"""

import re
from ..consts import ECR_REFERENCE_PATTERN, REGION_PATTERN, STATUS_ERROR, STATUS_SUCCESS
from .common import execute_command, format_result
from loguru import logger
from typing import Dict


def is_ecr_repository(repository: str) -> bool:
    """Validate if the provided repository URL is an ECR repository.

    ECR repository URLs typically follow the pattern:
    <aws_account_id>.dkr.ecr.<region>.amazonaws.com/<repository_name>:<tag>

    Args:
        repository: The repository URL to validate

    Returns:
        bool: True if the repository is an ECR repository, False otherwise

    """
    match = re.search(ECR_REFERENCE_PATTERN, repository)
    if not match:
        return False

    # Validate that the region is a valid AWS region format (e.g., us-west-2, eu-central-1)
    region = match.group(3)
    return bool(re.match(REGION_PATTERN, region))


def get_image_short_hash(image: str) -> tuple[Dict[str, str], str]:
    """Get the short hash (digest) of a container image.

    Args:
        image: The image name to get the hash for

    Returns:
        A tuple containing:
        - Dict with status and message
        - The short hash as a string (empty string if operation failed)

    """
    inspect_result = execute_command(['finch', 'image', 'inspect', image])

    if inspect_result.returncode != 0:
        # Log stderr for debugging
        logger.debug(f'STDERR from image inspect: {inspect_result.stderr}')
        error_result = format_result(
            STATUS_ERROR,
            f'Failed to get hash for image {image}: {inspect_result.stderr}',
        )
        return error_result, ''

    hash_match = re.search(r'"Id":\s*"(sha256:[a-f0-9]+)"', inspect_result.stdout)

    if not hash_match:
        error_result = format_result(
            STATUS_ERROR, f'Could not find hash in image inspect output for {image}'
        )
        return error_result, ''

    image_hash = hash_match.group(1)
    short_hash = image_hash[7:19] if image_hash.startswith('sha256:') else image_hash[:12]
    logger.debug(f'Retrieved hash for image {image}: {image_hash}')
    return format_result(
        STATUS_SUCCESS,
        f'Successfully retrieved hash for image {image}',
    ), short_hash


def push_image(image: str) -> Dict[str, str]:
    """Push an image to a repository, replacing the tag with the image hash.

    Args:
        image: The image to push

    Returns:
        Result of the push task

    """
    hash_result, short_hash = get_image_short_hash(image)

    if hash_result['status'] != STATUS_SUCCESS:
        return hash_result

    tag_separator_index = image.rfind(':')
    if tag_separator_index > 0:
        repository = image[:tag_separator_index]
    else:
        repository = image

    hash_tagged_image = f'{repository}:{short_hash}'

    tag_result = execute_command(['finch', 'image', 'tag', image, hash_tagged_image])

    if tag_result.returncode != 0:
        # Log stderr for debugging
        logger.debug(f'STDERR from image tag: {tag_result.stderr}')
        return format_result(
            STATUS_ERROR,
            f'Failed to tag image with hash: {tag_result.stderr}',
        )

    push_result = execute_command(['finch', 'image', 'push', hash_tagged_image])

    if push_result.returncode == 0:
        logger.debug(f'STDOUT from image push: {push_result.stdout}')
        return format_result(
            STATUS_SUCCESS,
            f'Successfully pushed image {hash_tagged_image} (original: {image}).',
        )
    else:
        logger.debug(f'STDERR from image push: {push_result.stderr}')
        return format_result(
            STATUS_ERROR,
            f'Failed to push image {hash_tagged_image}: {push_result.stderr}',
        )
