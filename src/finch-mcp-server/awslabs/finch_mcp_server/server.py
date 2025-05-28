"""Finch MCP Server main module.

This module provides the MCP server implementation for Finch container operations.

Note: The tools provided by this MCP server are intended for development and prototyping
purposes only and are not meant for production use cases.
"""

import os
import re
import sys
from awslabs.finch_mcp_server.consts import LOG_FILE, SERVER_NAME

# Import Pydantic models for input validation
from awslabs.finch_mcp_server.models import (
    BuildImageRequest,
    CreateEcrRepoRequest,
    PushImageRequest,
    Result,
)
from awslabs.finch_mcp_server.utils.build import build_image, contains_ecr_reference
from awslabs.finch_mcp_server.utils.common import format_result
from awslabs.finch_mcp_server.utils.ecr import create_ecr_repository

# Import utility functions from local modules
from awslabs.finch_mcp_server.utils.push import is_ecr_repository, push_image
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
from typing import Any, Dict


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
            logger.debug('Linux OS detected. Finch does not use a VM on Linux..')
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
async def finch_build_container_image(request: BuildImageRequest) -> Result:
    """Build a container image using Finch.

    This tool builds a Docker image using the specified Dockerfile and context directory.
    It supports a range of build options including tags, platforms, and more.
    If the Dockerfile contains references to ECR repositories, it verifies that
    ecr login cred helper is properly configured before proceeding with the build.

    Note: for ecr-login to work server needs access to AWS credentials/profile which are configured
    in the server mcp configuration file.

    Arguments:
        request : The request object of type BuildImageRequest containing all build parameters.
            - dockerfile_path (str): Absolute path to the Dockerfile
            - context_path (str): Absolute path to the build context directory
            - tags (List[str], optional): List of tags to apply to the image (e.g., ["myimage:latest", "myimage:v1"])
            - platforms (List[str], optional): List of target platforms (e.g., ["linux/amd64", "linux/arm64"])
            - target (str, optional): Target build stage to build
            - no_cache (bool, optional): Whether to disable cache. Defaults to False.
            - pull (bool, optional): Whether to always pull base images. Defaults to False.
            - build_contexts (List[str], optional): List of additional build contexts
            - outputs (str, optional): Output destination
            - cache_from (List[str], optional): List of external cache sources
            - quiet (bool, optional): Whether to suppress build output. Defaults to False.
            - progress (str, optional): Type of progress output. Defaults to "auto".

    Returns:
        Result: An object containing:
            - status (str): "success" if the operation succeeded, "error" otherwise
            - message (str): A descriptive message about the result of the operation

    Example response:
        Result(status="success", message="Successfully built image from /path/to/Dockerfile")

    """
    logger.info('tool-name: finch_build_container_image')
    logger.info(
        f'tool-args: dockerfile_path={request.dockerfile_path}, context_path={request.context_path}'
    )

    try:
        finch_install_status = check_finch_installation()
        if finch_install_status['status'] == 'error':
            return Result(**finch_install_status)

        if contains_ecr_reference(request.dockerfile_path):
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
            dockerfile_path=request.dockerfile_path,
            context_path=request.context_path,
            tags=request.tags,
            platforms=request.platforms,
            target=request.target,
            no_cache=request.no_cache,
            pull=request.pull,
            build_contexts=request.build_contexts,
            outputs=request.outputs,
            cache_from=request.cache_from,
            quiet=request.quiet,
            progress=request.progress,
        )
        return Result(**result)
    except Exception as e:
        error_result = format_result('error', f'Error building Docker image: {str(e)}')
        return Result(**error_result)


@mcp.tool()
async def finch_push_image(request: PushImageRequest) -> Result:
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

    Arguments:
        request (str): The full image name to push, including the repository URL and tag.
                    For ECR repositories, it must follow the format:
                    <aws_account_id>.dkr.ecr.<region>.amazonaws.com/<repository_name>:<tag>

    Returns:
        Result: An object containing:
            - status (str): "success" if the operation succeeded, "error" otherwise
            - message (str): A descriptive message about the result of the operation

    Example response:
        Result(status="success", message="Successfully pushed image 123456789012.dkr.ecr.us-west-2.amazonaws.com/my-repo:latest to ECR.")

    """
    logger.info('tool-name: finch_push_image')
    logger.info(f'tool-args: image={request.image}')

    try:
        finch_install_status = check_finch_installation()
        if finch_install_status['status'] == 'error':
            return Result(**finch_install_status)

        is_ecr = is_ecr_repository(request.image)
        if is_ecr:
            # Check if AWS resource write is enabled for ECR pushes
            if not enable_aws_resource_write:
                logger.warning(
                    f'Attempt to push image to ECR "{request.image}" without AWS resource write enabled'
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

        result = push_image(request.image)
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
async def finch_create_ecr_repo(request: CreateEcrRepoRequest) -> Result:
    """Check if an ECR repository exists and create it if it doesn't.

    This tool checks if the specified ECR repository exists using boto3.
    If the repository doesn't exist, it creates a new one with the given name.
    The tool requires appropriate AWS credentials configured.

    When the server is in read-only mode (which is the default unless --enable-aws-resource-write
    is specified), this tool will return an error and will not create any repositories.

    Arguments:
        request: The request object of type CreateEcrRepoRequest containing:
            - repository_name (str): The name of the repository to check or create in ECR
            - region (str, optional): AWS region for the ECR repository. If not provided, uses the default region
                                     from AWS configuration

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
    logger.info(f'tool-args: repository_name={request.repository_name}')

    # Check if AWS resource write is enabled
    if not enable_aws_resource_write:
        logger.warning(
            f'Attempt to create ECR repo "{request.repository_name}" without AWS resource write enabled'
        )
        error_result = format_result(
            'error', 'Server running in read-only mode, unable to perform the action'
        )
        return Result(**error_result)

    try:
        result = create_ecr_repository(
            repository_name=request.repository_name,
            region=request.region,
        )
        return Result(**result)
    except Exception as e:
        error_result = format_result('error', f'Error checking/creating ECR repository: {str(e)}')
        return Result(**error_result)


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
