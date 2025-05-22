"""Utility functions for building container images using Finch.

This module provides functions to build Docker images using Finch and check
if Dockerfiles contain references to ECR repositories.

Note: These tools are intended for development and prototyping purposes only
and are not meant for production use cases.
"""

import os
import re
from ..consts import ECR_REFERENCE_PATTERN, STATUS_ERROR, STATUS_SUCCESS
from .common import execute_command, format_result
from loguru import logger
from typing import Any, Dict, List, Optional


def contains_ecr_reference(dockerfile_path: str) -> bool:
    """Check if a Dockerfile contains references to ECR repositories.

    This function scans the Dockerfile for `FROM` or other directives
    that might reference an ECR repository.

    Args:
        dockerfile_path (str): Path to the Dockerfile to check.

    Returns:
        bool: True if the Dockerfile contains ECR references, False otherwise.

    """
    try:
        if not os.path.exists(dockerfile_path):
            logger.warning(f'Dockerfile not found at {dockerfile_path}')
            return False

        with open(dockerfile_path, 'r') as f:
            content = f.read()
            return bool(re.search(ECR_REFERENCE_PATTERN, content))
    except Exception as e:
        logger.error(f'Error checking Dockerfile for ECR references: {str(e)}')
        return False


def build_image(
    dockerfile_path: str,
    context_path: str,
    tags: Optional[List[str]] = None,
    platforms: Optional[List[str]] = None,
    target: Optional[str] = None,
    no_cache: bool = False,
    pull: bool = False,
    add_hosts: Optional[List[str]] = None,
    allow: Optional[List[str]] = None,
    build_contexts: Optional[List[str]] = None,
    outputs: Optional[str] = None,
    cache_from: Optional[List[str]] = None,
    cache_to: Optional[List[str]] = None,
    quiet: bool = False,
    progress: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a container image using Finch.

    Args:
        dockerfile_path: Path to the Dockerfile
        context_path: Path to the build context directory
        tags: List of tags to apply to the image
        platforms: List of target platforms
        target: Target build stage
        no_cache: Whether to disable cache
        pull: Whether to always pull base images
        add_hosts: List of custom host-to-IP mappings
        allow: List of extra privileged entitlements
        build_contexts: List of additional build contexts
        outputs: Output destination
        cache_from: List of external cache sources
        cache_to: List of cache export destinations
        quiet: Whether to suppress build output
        progress: Type of progress output
    Returns:
        Dict[str, Any]: Result of the build operation

    """
    try:
        # Check if Dockerfile exists
        if not os.path.exists(dockerfile_path):
            return format_result(STATUS_ERROR, f'Dockerfile not found at {dockerfile_path}')

        if not os.path.exists(context_path):
            return format_result(STATUS_ERROR, f'Context directory not found at {context_path}')

        command = ['finch', 'image', 'build']

        command.extend(['-f', dockerfile_path])

        if tags:
            for tag in tags:
                command.extend(['-t', tag])

        if platforms:
            for platform in platforms:
                command.extend(['--platform', platform])

        if target:
            command.extend(['--target', target])

        if no_cache:
            command.append('--no-cache')

        if pull:
            command.append('--pull')

        if add_hosts:
            for host in add_hosts:
                command.extend(['--add-host', host])

        if allow:
            for a in allow:
                command.extend(['--allow', a])

        if build_contexts:
            for ctx in build_contexts:
                command.extend(['--build-context', ctx])

        if outputs:
            command.extend(['--output', outputs])

        if cache_from:
            for cache in cache_from:
                command.extend(['--cache-from', cache])

        if cache_to:
            for cache in cache_to:
                command.extend(['--cache-to', cache])

        if quiet:
            command.append('--quiet')

        if progress:
            command.extend(['--progress', progress])

        command.append(context_path)

        logger.info(f'Building image with command: {" ".join(command)}')
        build_result = execute_command(command)

        if build_result.returncode == 0:
            return format_result(
                STATUS_SUCCESS,
                f'Successfully built image from {dockerfile_path}',
                stdout=build_result.stdout,
            )
        else:
            return format_result(
                STATUS_ERROR,
                f'Failed to build image: {build_result.stderr}',
                stderr=build_result.stderr,
            )

    except Exception as e:
        logger.error(f'Error building image: {str(e)}')
        return format_result(STATUS_ERROR, f'Error building image: {str(e)}')
