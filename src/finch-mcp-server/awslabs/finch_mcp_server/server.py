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

"""Finch MCP Server main module.

This module provides the MCP server implementation for Finch container operations.

Note: The tools provided by this MCP server are intended for development and prototyping
purposes only and are not meant for production use cases.
"""

import json
import os
import re
import sys
from awslabs.finch_mcp_server.consts import LOG_FILE, SERVER_NAME, STATUS_ERROR

# Import Pydantic models for input validation
from awslabs.finch_mcp_server.models import ContainerInspectResult, ContainerLSResult, Result
from awslabs.finch_mcp_server.utils.build import build_image, contains_ecr_reference
from awslabs.finch_mcp_server.utils.common import format_result
from awslabs.finch_mcp_server.utils.container_inspect import inspect_container
from awslabs.finch_mcp_server.utils.container_ls import list_containers
from awslabs.finch_mcp_server.utils.ecr import create_ecr_repository
from awslabs.finch_mcp_server.utils.image_ls import list_images

# Import utility functions from local modules
from awslabs.finch_mcp_server.utils.push import is_ecr_repository, push_image
from awslabs.finch_mcp_server.utils.version import get_version
from awslabs.finch_mcp_server.utils.vm import (
    check_finch_installation,
    configure_ecr,
    get_vm_status,
    initialize_vm,
    is_vm_nonexistent,
    is_vm_running,
    is_vm_stopped,
    start_stopped_vm,
    stop_vm,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Any, Dict, List, Optional


# Configure loguru logger
def sensitive_data_filter(record):
    """Filter that redacts sensitive information from log messages.

    This function processes log records to redact sensitive information such as
    API keys, passwords, and credentials from the message.

    Args:
        record: The log record to process

    Returns:
        bool: True to allow the log record to be processed, False to filter it out

    """
    # Define patterns for sensitive data detection
    patterns = [
        # AWS Access Key (20 character alphanumeric)
        (re.compile(r'((?<![A-Z0-9])[A-Z0-9]{20}(?![A-Z0-9]))'), 'AWS_ACCESS_KEY_REDACTED'),
        # AWS Secret Key (40 character base64)
        (
            re.compile(r'((?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=]))'),
            'AWS_SECRET_KEY_REDACTED',
        ),
        # API Keys
        (
            re.compile(r'(api[_-]?key[=:]\s*[\'"]?)[^\'"\s]+([\'"]?)', re.IGNORECASE),
            r'api_key=REDACTED',
        ),
        # Passwords
        (
            re.compile(r'(password[=:]\s*[\'"]?)[^\'"\s]+([\'"]?)', re.IGNORECASE),
            r'password=REDACTED',
        ),
        # Secrets
        (
            re.compile(r'(secret[=:]\s*[\'"]?)[^\'"\s]+([\'"]?)', re.IGNORECASE),
            r'secret=REDACTED',
        ),
        # Tokens
        (re.compile(r'(token[=:]\s*[\'"]?)[^\'"\s]+([\'"]?)', re.IGNORECASE), r'\1REDACTED\2'),
        # URLs with credentials
        (re.compile(r'(https?://)([^:@\s]+):([^:@\s]+)@'), r'\1REDACTED:REDACTED@'),
        # JWT tokens (common format)
        (
            re.compile(r'eyJ[a-zA-Z0-9_-]{5,}\.eyJ[a-zA-Z0-9_-]{5,}\.[a-zA-Z0-9_-]{5,}'),
            'JWT_TOKEN_REDACTED',
        ),
        # OAuth tokens
        (
            re.compile(r'(oauth[_-]?token[=:]\s*[\'"]?)[^\'"\s]+([\'"]?)', re.IGNORECASE),
            r'\1REDACTED\2',
        ),
        # Generic credentials
        (
            re.compile(r'(credential[s]?[=:]\s*[\'"]?)[^\'"\s]+([\'"]?)', re.IGNORECASE),
            r'\1REDACTED\2',
        ),
    ]

    try:
        if 'message' in record:
            message = record['message']

            for pattern, replacement in patterns:
                message = pattern.sub(replacement, message)

            record['message'] = message

    except Exception as e:
        if 'message' in record:
            record['message'] = (
                f'{record["message"]} [SENSITIVE_DATA_FILTER_ERROR: Exception occurred during sensitive data filtering]'
            )
        else:
            record['message'] = (
                '[SENSITIVE_DATA_FILTER_ERROR: Exception occurred during sensitive data filtering]'
            )
        logger.debug(f'Error in sensitive_data_filter: {str(e)}')

    # Return True to allow the log record to be processed
    return True


# Remove all default handlers then add our own
logger.remove()

log_level = os.environ.get('FASTMCP_LOG_LEVEL', 'INFO').upper()
logger.add(
    LOG_FILE,
    rotation='10 MB',
    retention=7,
    level=log_level,
    format='{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}',
    filter=sensitive_data_filter,
)

# Add a handler for stderr
logger.add(
    sys.stderr,
    level=log_level,
    format='{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}',
    filter=sensitive_data_filter,
)

logger = logger.bind(name=SERVER_NAME)

# Initialize the MCP server
mcp = FastMCP(SERVER_NAME)
enable_aws_resource_write = False


def ensure_vm_running() -> Dict[str, Any]:
    """Ensure that the Finch VM is running before performing operations.

    This function checks the current status of the Finch VM and takes appropriate action:
    - If the VM is nonexistent: Creates a new VM instance using 'finch vm init'
    - If the VM is stopped: Starts the VM using 'finch vm start'
    - If the VM is already running: Does nothing

    Returns:
        Dict[str, Any]: A dictionary containing:
            - status (str): "success" if the VM is running or was started successfully,
                            "error" otherwise
            - message (str): A descriptive message about the result of the operation

    """
    try:
        if sys.platform == 'linux':
            logger.info('Linux OS detected. Finch does not use a VM on Linux...')
            return format_result('success', 'Finch does not use a VM on Linux..')

        status_result = get_vm_status()

        if is_vm_nonexistent(status_result):
            logger.info('Finch VM does not exist. Initializing...')
            result = initialize_vm()
            if result['status'] == 'error':
                return result
            return format_result('success', 'Finch VM was initialized successfully.')
        elif is_vm_stopped(status_result):
            logger.info('Finch VM is stopped. Starting it...')
            result = start_stopped_vm()
            if result['status'] == 'error':
                return result
            return format_result('success', 'Finch VM was started successfully.')
        elif is_vm_running(status_result):
            return format_result('success', 'Finch VM is already running.')
        else:
            return format_result(
                'error',
                f'Unknown VM status: status code {status_result.returncode}',
            )
    except Exception as e:
        return format_result('error', f'Error ensuring Finch VM is running: {str(e)}')


@mcp.tool()
async def finch_build_container_image(
    dockerfile_path: str = Field(..., description='Absolute path to the Dockerfile'),
    context_path: str = Field(..., description='Absolute path to the build context directory'),
    tags: Optional[List[str]] = Field(
        default=None,
        description="List of tags to apply to the image (e.g., ['myimage:latest', 'myimage:v1'])",
    ),
    platforms: Optional[List[str]] = Field(
        default=None, description="List of target platforms (e.g., ['linux/amd64', 'linux/arm64'])"
    ),
    target: Optional[str] = Field(default=None, description='Target build stage to build'),
    no_cache: Optional[bool] = Field(default=False, description='Whether to disable cache'),
    pull: Optional[bool] = Field(default=False, description='Whether to always pull base images'),
    build_contexts: Optional[List[str]] = Field(
        default=None, description='List of additional build contexts'
    ),
    outputs: Optional[str] = Field(default=None, description='Output destination'),
    cache_from: Optional[List[str]] = Field(
        default=None, description='List of external cache sources'
    ),
    quiet: Optional[bool] = Field(default=False, description='Whether to suppress build output'),
    progress: Optional[str] = Field(default='auto', description='Type of progress output'),
) -> Result:
    """Build a container image using Finch.

    This tool builds a Docker image using the specified Dockerfile and context directory.
    It supports a range of build options including tags, platforms, and more.
    If the Dockerfile contains references to ECR repositories, it verifies that
    ecr login cred helper is properly configured before proceeding with the build.

    Note: for ecr-login to work server needs access to AWS credentials/profile which are configured
    in the server mcp configuration file.

    Returns:
        Result: An object containing:
            - status (str): "success" if the operation succeeded, "error" otherwise
            - message (str): A descriptive message about the result of the operation

    Example response:
        Result(status="success", message="Successfully built image from /path/to/Dockerfile")

    """
    logger.info('tool-name: finch_build_container_image')
    logger.info(f'tool-args: dockerfile_path={dockerfile_path}, context_path={context_path}')

    try:
        finch_install_status = check_finch_installation()
        if finch_install_status['status'] == 'error':
            return Result(**finch_install_status)

        if contains_ecr_reference(dockerfile_path):
            logger.info('ECR reference detected in Dockerfile, configuring ECR login')
            config_result, config_changed = configure_ecr()
            if config_result['status'] == 'error':
                return Result(**config_result)
            if config_changed:
                logger.info('ECR configuration changed, restarting VM')
                stop_vm(force=True)

        vm_status = ensure_vm_running()
        if vm_status['status'] == 'error':
            return Result(**vm_status)

        result = build_image(
            dockerfile_path=dockerfile_path,
            context_path=context_path,
            tags=tags,
            platforms=platforms,
            target=target,
            no_cache=no_cache,
            pull=pull,
            build_contexts=build_contexts,
            outputs=outputs,
            cache_from=cache_from,
            quiet=quiet,
            progress=progress,
        )
        return Result(**result)
    except Exception as e:
        error_result = format_result('error', f'Error building Docker image: {str(e)}')
        return Result(**error_result)


@mcp.tool()
async def finch_push_image(
    image: str = Field(
        ..., description='The full image name to push, including the repository URL and tag'
    ),
) -> Result:
    """Push a container image to a repository using finch, replacing the tag with the image hash.

    If the image URL is an ECR repository, it verifies that ECR login cred helper is configured.
    This tool  gets the image hash, creates a new tag using the hash, and pushes the image with
    the hash tag to the repository. If the image URL is an ECR repository, it verifies that
    ECR login is properly configured before proceeding with the push.

    The tool expects the image to be already built and available locally. It uses
    'finch image inspect' to get the hash, 'finch image tag' to create a new tag,
    and 'finch image push' to perform the actual push operation.

    When the server is in read-only mode (which is the default unless --enable-aws-resource-write
    is specified), this tool will return an error when pushing to ECR repositories.

    Returns:
        Result: An object containing:
            - status (str): "success" if the operation succeeded, "error" otherwise
            - message (str): A descriptive message about the result of the operation

    Example response:
        Result(status="success", message="Successfully pushed image 123456789012.dkr.ecr.us-west-2.amazonaws.com/my-repo:abcdef123456 to ECR.")

    """
    logger.info('tool-name: finch_push_image')
    logger.info(f'tool-args: image={image}')

    try:
        finch_install_status = check_finch_installation()
        if finch_install_status['status'] == 'error':
            return Result(**finch_install_status)

        is_ecr = is_ecr_repository(image)
        if is_ecr:
            # Check if AWS resource write is enabled for ECR pushes
            if not enable_aws_resource_write:
                logger.warning(
                    f'Attempt to push image to ECR "{image}" without AWS resource write enabled'
                )
                error_result = format_result(
                    'error', 'Server running in read-only mode, unable to push to ECR repository'
                )
                return Result(**error_result)

            logger.info('ECR repository detected, configuring ECR login')
            config_result, config_changed = configure_ecr()
            if config_result['status'] == 'error':
                return Result(**config_result)
            if config_changed:
                logger.info('ECR configuration changed, restarting VM')
                stop_vm(force=True)

        vm_status = ensure_vm_running()
        if vm_status['status'] == 'error':
            return Result(**vm_status)

        result = push_image(image)
        return Result(**result)
    except Exception as e:
        error_result = format_result('error', f'Error pushing image: {str(e)}')
        return Result(**error_result)


def set_enable_aws_resource_write(enabled: bool):
    """Set whether AWS resource creation/modification is enabled.

    When AWS resource write is disabled, certain operations like creating ECR repositories
    will return an error.

    Args:
        enabled (bool): True to enable AWS resource creation/modification, False to disable it

    """
    global enable_aws_resource_write
    enable_aws_resource_write = enabled
    logger.info(f'AWS resource write enabled: {enable_aws_resource_write}')


@mcp.tool()
async def finch_create_ecr_repo(
    repository_name: str = Field(
        ..., description='The name of the repository to check or create in ECR'
    ),
    region: Optional[str] = Field(
        default=None,
        description='AWS region for the ECR repository. If not provided, uses the default region from AWS configuration',
    ),
) -> Result:
    """Check if an ECR repository exists and create it if it doesn't.

    This tool checks if the specified ECR repository exists using boto3.
    If the repository doesn't exist, it creates a new one with the given name.
    The tool requires appropriate AWS credentials configured.

    When the server is in read-only mode (which is the default unless --enable-aws-resource-write
    is specified), this tool will return an error and will not create any repositories.

    Returns:
        Result: An object containing:
            - status (str): "success" if the operation succeeded, "error" otherwise
            - message (str): A descriptive message about the result of the operation

    Example response:
        Result(status="success", message="Successfully created ECR repository 'my-app'.",
               repository_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app",
               exists=False)

    """
    logger.info('tool-name: finch_create_ecr_repo')
    logger.info(f'tool-args: repository_name={repository_name}')

    # Check if AWS resource write is enabled
    if not enable_aws_resource_write:
        logger.warning(
            f'Attempt to create ECR repo "{repository_name}" without AWS resource write enabled'
        )
        error_result = format_result(
            'error', 'Server running in read-only mode, unable to perform the action'
        )
        return Result(**error_result)

    try:
        result = create_ecr_repository(
            repository_name=repository_name,
            region=region,
        )
        return Result(**result)
    except Exception as e:
        error_result = format_result('error', f'Error checking/creating ECR repository: {str(e)}')
        return Result(**error_result)


@mcp.resource(uri='finch://containers', name='finch_container_ls', mime_type='application/json')
async def finch_container_ls() -> ContainerLSResult:
    """List containers using Finch.

    This resource provides a list of containers with various filtering options.
    By default, it shows all containers (including stopped ones) with all_containers=True.
    The output is formatted as JSON for easy parsing by LLMs and other tools.
    Note: This resource does not accept any parameters directly. The implementation
    uses default parameters (all_containers=True) to show all containers.

    Returns:
        ContainerLSResult: An object containing:
            - status (str): "success" if the operation succeeded, "error" otherwise
            - message (str): A descriptive message about the result of the operation
            - raw_output (str): Raw JSON output from the command if successful
    Example response:
        ContainerLSResult(
            status="success",
            message="Successfully listed containers",
            raw_output='[{"ID":"test-container-1","Image":"nginx:latest","Command":"/docker-entrypoint.sh nginx -g daemon off;","Created":"2025-07-17 10:30:45 -0700 PDT","Status":"Up 2 hours","Ports":"0.0.0.0:8080->80/tcp","Names":"test-nginx"},{"ID":"test-container-2","Image":"python:3.9-alpine","Command":"python app.py","Created":"2025-07-17 09:15:30 -0700 PDT","Status":"Exited (0) 30 minutes ago","Ports":"","Names":"test-python"}]'
        )

    """
    logger.info('resource-name: finch_container_ls')
    logger.info('resource-args: none')

    try:
        finch_install_status = check_finch_installation()
        if finch_install_status['status'] == 'error':
            return ContainerLSResult(
                status=finch_install_status['status'],
                message=finch_install_status['message'],
                raw_output=None,
            )

        vm_status = ensure_vm_running()
        if vm_status['status'] == 'error':
            return ContainerLSResult(
                status=vm_status['status'], message=vm_status['message'], raw_output=None
            )

        # Use default parameters for list_containers
        result = list_containers(
            all_containers=True,  # Show all containers by default
            filter_expr=None,
            format_str=None,
            last=None,
            latest=False,
            no_trunc=False,
            quiet=False,
            size=False,
        )
        return ContainerLSResult(
            status=result['status'], message=result['message'], raw_output=result.get('raw_output')
        )
    except Exception as e:
        return ContainerLSResult(
            status='error', message=f'Error listing containers: {str(e)}', raw_output=None
        )


@mcp.resource(
    uri='finch://containers/{container_id}',
    name='finch_container_inspect',
    mime_type='application/json',
)
async def finch_container_inspect(container_id: str) -> ContainerInspectResult:
    """Inspect a container to get detailed information.

    This resource retrieves detailed information about a specific container,
    including its configuration, state, network settings, and more.
    The output is formatted as JSON for easy parsing by LLMs and other tools.

    Args:
        container_id (str): The ID or name of the container to inspect
    Returns:
        ContainerInspectResult: An object containing:
            - status (str): "success" if the operation succeeded, "error" otherwise
            - message (str): A descriptive message about the result of the operation
            - raw_output (str, optional): Raw JSON output from the inspect command if successful
    Example response:
        ContainerInspectResult(
            status="success",
            message="Successfully inspected container test-container-1",
            raw_output='[{"Id":"test-container-1","Created":"2025-07-17T10:30:45.000000000Z","State":{"Status":"running","Running":true},"Config":{"Image":"nginx:latest","ExposedPorts":{"80/tcp":{}}},"NetworkSettings":{"Ports":{"80/tcp":[{"HostIp":"0.0.0.0","HostPort":"8080"}]}}}]'
        )

    """
    logger.info('resource-name: finch_container_inspect')
    logger.info(f'resource-args: container_id={container_id}')

    try:
        finch_install_status = check_finch_installation()
        if finch_install_status['status'] == 'error':
            return ContainerInspectResult(
                status=finch_install_status['status'],
                message=finch_install_status['message'],
                container_info=None,
                raw_output=None,
            )

        vm_status = ensure_vm_running()
        if vm_status['status'] == 'error':
            return ContainerInspectResult(
                status=vm_status['status'],
                message=vm_status['message'],
                container_info=None,
                raw_output=None,
            )

        result = inspect_container(container_id)
        return ContainerInspectResult(
            status=result['status'],
            message=result['message'],
            container_info=result.get('container_info'),
            raw_output=result.get('raw_output'),
        )
    except Exception as e:
        return ContainerInspectResult(
            status='error',
            message=f'Error inspecting container: {str(e)}',
            container_info=None,
            raw_output=None,
        )


@mcp.resource(uri='finch://images', name='finch_image_list', mime_type='application/json')
async def finch_image_list() -> str:
    """List container images using Finch.

    This resource provides a list of container images.
    It returns structured information about each image including repository,
    tag, image ID, created time, and size.

    Returns:
        str: JSON string containing image list information

    """
    logger.info('resource: finch_image_list')

    try:
        # Always use all_images=True to show all images by default
        result = list_images(all_images=True)
        return json.dumps(result, indent=2)
    except Exception as e:
        error_result = format_result(STATUS_ERROR, f'Error listing images: {str(e)}')
        return json.dumps(error_result, indent=2)


@mcp.resource(uri='finch://version', name='finch_version', mime_type='application/json')
async def finch_version() -> str:
    """Get Finch version information.

    This resource provides version information for the Finch installation,
    including version numbers and build information.

    Returns:
        str: JSON string containing version information

    """
    logger.info('resource: finch_version')

    try:
        result = get_version()
        return json.dumps(result, indent=2)
    except Exception as e:
        error_result = format_result(STATUS_ERROR, f'Error getting version: {str(e)}')
        return json.dumps(error_result, indent=2)


def main(enable_aws_resource_write: bool = False):
    """Run the Finch MCP server.

    Args:
        enable_aws_resource_write (bool, optional): Whether to enable AWS resource creation/modification. Defaults to False.

    """
    # Set AWS resource write mode
    set_enable_aws_resource_write(enable_aws_resource_write)

    logger.info('Starting Finch MCP server')
    logger.info(f'Logs will be written to: {LOG_FILE}')
    mcp.run(transport='stdio')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run the Finch MCP server')
    parser.add_argument(
        '--enable-aws-resource-write',
        action='store_true',
        help='Enable AWS resource creation and modification (disabled by default)',
    )
    args = parser.parse_args()

    main(enable_aws_resource_write=args.enable_aws_resource_write)
