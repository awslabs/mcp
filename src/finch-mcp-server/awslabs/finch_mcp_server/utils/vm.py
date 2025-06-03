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
"""Utility functions for managing the Finch VM.

This module provides functions to check, initialize, start, stop, and configure
the Finch virtual machine that runs containers.

Note: These tools are intended for development and prototyping purposes only
and are not meant for production use cases.
"""

import os
import subprocess
import sys
import yaml
from ..consts import (
    FINCH_YAML_PATH,
    STATUS_ERROR,
    STATUS_SUCCESS,
    VM_STATE_NONEXISTENT,
    VM_STATE_RUNNING,
    VM_STATE_STOPPED,
    VM_STATE_UNKNOWN,
)
from .common import execute_command, format_result
from loguru import logger
from shutil import which
from typing import Dict, Literal


def get_vm_status() -> subprocess.CompletedProcess:
    """Get the current status of the Finch VM.

    This function executes 'finch vm status' and returns the raw result.
    It's a wrapper around execute_command that simplifies checking
    the VM status, which is a common operation used by multiple tools.

    Returns:
        CompletedProcess with the status command result, containing:
        - returncode: The exit code of the command
        - stdout: Standard output containing status information
        - stderr: Standard error output, may also contain status information

    """
    return execute_command(['finch', 'vm', 'status'])


def is_vm_nonexistent(status_result: subprocess.CompletedProcess) -> bool:
    """Check if the Finch VM is nonexistent based on status result.

    This function analyzes the output of 'finch vm status' to determine
    if the VM has not been created yet.

    Args:
        status_result: CompletedProcess object from running 'finch vm status'

    Returns:
        bool: True if the VM is nonexistent, False otherwise

    """
    return (
        'nonexistent' in status_result.stderr.lower()
        or 'nonexistent' in status_result.stdout.lower()
    )


def is_vm_stopped(status_result: subprocess.CompletedProcess) -> bool:
    """Check if the Finch VM is stopped based on status result.

    This function analyzes the output of 'finch vm status' to determine
    if the VM exists but is not currently running.

    Args:
        status_result: CompletedProcess object from running 'finch vm status'

    Returns:
        bool: True if the VM is stopped, False otherwise

    """
    return 'stopped' in status_result.stderr.lower() or 'stopped' in status_result.stdout.lower()


def is_vm_running(status_result: subprocess.CompletedProcess) -> bool:
    """Check if the Finch VM is running based on status result.

    This function analyzes the output of 'finch vm status' to determine
    if the VM is currently active and operational.

    Args:
        status_result: CompletedProcess object from running 'finch vm status'

    Returns:
        bool: True if the VM is running, False otherwise

    """
    return 'running' in status_result.stdout.lower() or 'running' in status_result.stderr.lower()


def initialize_vm() -> Dict[str, str]:
    """Initialize a new Finch VM.

    This function runs 'finch vm init' to create a new Finch VM instance.
    It's used when the VM doesn't exist yet and needs to be created.

    Returns:
        Dict[str, Any]: Result dictionary with:
            - status: "success" if initialization succeeded, "error" otherwise
            - message: Details about the initialization result

    """
    if sys.platform == 'linux':
        logger.debug('Linux OS detected. Finch does not use a VM on Linux...')
        return format_result(STATUS_SUCCESS, 'Finch does not use a VM on Linux..')

    logger.warning('Finch VM non existent, Initializing a new vm instance...')
    init_result = execute_command(['finch', 'vm', 'init'])

    if init_result.returncode == 0:
        return format_result(STATUS_SUCCESS, 'Finch VM was initialized successfully.')
    else:
        return format_result(STATUS_ERROR, f'Failed to initialize Finch VM: {init_result.stderr}')


def start_stopped_vm() -> Dict[str, str]:
    """Start a stopped Finch VM.

    This function runs 'finch vm start' to start a VM that exists but is
    currently stopped. It's used to make the VM operational when it's not running.

    Returns:
        Dict[str, Any]: Result dictionary with:
            - status: "success" if the VM was started successfully, "error" otherwise
            - message: Details about the start operation result

    """
    if sys.platform == 'linux':
        logger.debug('Linux OS detected. Finch does not use a VM on Linux...')
        return format_result(STATUS_SUCCESS, 'Finch does not use a VM on Linux..')

    logger.info('Finch VM is stopped. Starting it...')
    start_result = execute_command(['finch', 'vm', 'start'])

    if start_result.returncode == 0:
        return format_result(
            STATUS_SUCCESS, 'Finch VM was stopped and has been started successfully.'
        )
    else:
        return format_result(STATUS_ERROR, f'Failed to start Finch VM: {start_result.stderr}')


def stop_vm(force: bool = False) -> Dict[str, str]:
    """Stop a running Finch VM.

    This function runs 'finch vm stop' to shut down a running VM.
    If force is True, it adds the '--force' flag to forcefully terminate
    the VM even if it's in use.

    Args:
        force: Whether to force stop the VM. Use this when the VM might be
               in an inconsistent state or when normal shutdown fails.

    Returns:
        Dict[str, Any]: Result dictionary with:
            - status: "success" if the VM was stopped successfully, "error" otherwise
            - message: Details about the stop operation result

    """
    if sys.platform == 'linux':
        logger.debug('Linux OS detected. Finch does not use a VM on Linux...')
        return format_result(STATUS_SUCCESS, 'Finch does not use a VM on Linux..')

    command = ['finch', 'vm', 'stop']
    if force:
        command.append('--force')

    stop_result = execute_command(command)

    if stop_result.returncode == 0:
        return format_result(STATUS_SUCCESS, 'Finch VM has been stopped successfully.')
    else:
        return format_result(STATUS_ERROR, f'Failed to stop Finch VM: {stop_result.stderr}')


def remove_vm(force: bool = False) -> Dict[str, str]:
    """Remove the Finch VM.

    This function runs 'finch vm rm' to remove the VM.
    If force is True, it adds the '--force' flag to forcefully remove
    the VM even if it's in use.

    Args:
        force: Whether to force remove the VM. Use this when the VM might be
               in an inconsistent state or when normal removal fails.

    Returns:
        Dict[str, Any]: Result dictionary with:
            - status: "success" if the VM was removed successfully, "error" otherwise
            - message: Details about the remove operation result

    """
    if sys.platform == 'linux':
        logger.debug('Linux OS detected. Finch does not use a VM on Linux...')
        return format_result(STATUS_SUCCESS, 'Finch does not use a VM on Linux..')

    command = ['finch', 'vm', 'rm']
    if force:
        command.append('--force')

    remove_result = execute_command(command)

    if remove_result.returncode == 0:
        return format_result(STATUS_SUCCESS, 'Finch VM has been removed successfully.')
    else:
        return format_result(STATUS_ERROR, f'Failed to remove Finch VM: {remove_result.stderr}')


def restart_running_vm() -> Dict[str, str]:
    """Restart a running Finch VM (stop then start).

    This function performs a full restart of the VM by first stopping it
    (with force=True to ensure it stops) and then starting it again.
    It's useful when you need to refresh the VM state completely.

    Returns:
        Dict[str, Any]: Result dictionary with:
            - status: "success" if the VM was restarted successfully, "error" otherwise
            - message: Details about the restart operation result

    """
    if sys.platform == 'linux':
        logger.debug('Linux OS detected. Finch does not use a VM on Linux...')
        return format_result(STATUS_SUCCESS, 'Finch does not use a VM on Linux..')

    logger.info('Finch VM is running. Restarting it...')

    stop_result = stop_vm(force=True)
    if stop_result['status'] == STATUS_ERROR:
        return stop_result

    start_result = start_stopped_vm()

    return start_result


def check_finch_installation() -> Dict[str, str]:
    """Check if the Finch CLI tool is installed on the system.

    This function uses 'which finch' on macOS/Linux to determine if the
    Finch command-line tool is available in the system PATH. It's a
    prerequisite check before attempting to use any Finch functionality.

    Returns:
        Dict[str, Any]: Result dictionary with:
            - status: "success" if Finch is installed, "error" otherwise
            - message: Details about the installation status

    """
    try:
        if which('finch') is not None:
            return format_result(STATUS_SUCCESS, 'Finch is installed.')
        else:
            return format_result(STATUS_ERROR, 'Finch is not installed.')
    except Exception as e:
        return format_result(STATUS_ERROR, f'Error checking Finch installation: {str(e)}')


def configure_ecr() -> tuple[Dict[str, str], bool]:
    r"""Configure Finch to use ECR (Amazon Elastic Container Registry).

    This function updates the Finch YAML configuration file:
    - macOS: ~/.finch/finch.yaml
    - Windows: %LocalAppData%\.finch\finch.yaml

    It adds 'ecr-login' to the creds_helpers list while preserving other settings.

    This enables Finch to authenticate with Amazon ECR. The config.json file is not modified
    as it is automatically handled when adding the ecr-login credential helper in finch.yaml.

    Returns:
        tuple[Dict[str, str], bool]: A tuple containing:
            - Result dictionary with:
                - status: "success" if the configuration was updated successfully, "error" otherwise
                - message: Details about the configuration result
            - Boolean indicating if the configuration was changed (True if changed, False otherwise)

    """
    try:
        if sys.platform == 'linux':
            (
                logger.info(
                    'Linux OS detected. config.json set in DOCKER_CONFIG is used for credentials'
                ),
                False,
            )
            return format_result(
                'success', 'config.json set in DOCKER_CONFIG is used for credentials'
            ), False

        changed_yaml = False
        # For Windows, FINCH_YAML_PATH is already an absolute path
        # For macOS, we need to expand the ~ in the path
        finch_yaml_path = FINCH_YAML_PATH
        if sys.platform != 'win32':
            finch_yaml_path = os.path.expanduser(FINCH_YAML_PATH)

        if os.path.exists(finch_yaml_path):
            try:
                with open(finch_yaml_path, 'r') as f:
                    yaml_content = yaml.safe_load(f) or {}

                if 'creds_helpers' in yaml_content:
                    if not isinstance(yaml_content['creds_helpers'], list):
                        yaml_content['creds_helpers'] = (
                            [yaml_content['creds_helpers']]
                            if yaml_content['creds_helpers']
                            else []
                        )

                    if 'ecr-login' not in yaml_content['creds_helpers']:
                        yaml_content['creds_helpers'].append('ecr-login')
                        changed_yaml = True
                else:
                    yaml_content['creds_helpers'] = ['ecr-login']
                    changed_yaml = True

                if changed_yaml:
                    with open(finch_yaml_path, 'w') as f:
                        yaml.dump(yaml_content, f, default_flow_style=False)

            except Exception as e:
                logger.warning(f'Error updating {finch_yaml_path} with PyYAML: {str(e)}')
                return format_result(
                    STATUS_ERROR, f'Failed to update finch YAML file: {str(e)}'
                ), False
        else:
            if sys.platform == 'win32':
                error_msg = f'finch yaml file not found at {finch_yaml_path}'
            else:
                error_msg = 'finch yaml file not found in finch.yaml'
            return format_result(STATUS_ERROR, error_msg), False

        if changed_yaml:
            # Log the change status
            logger.debug('ECR configuration was updated in finch.yaml')
            result = format_result(
                STATUS_SUCCESS,
                'ECR configuration updated successfully in finch.yaml.',
            )
        else:
            # Log that no changes were needed
            logger.debug('ECR was already configured correctly in finch.yaml')
            result = format_result(
                STATUS_SUCCESS,
                'ECR was already configured correctly in finch.yaml.',
            )

        return result, changed_yaml

    except Exception as e:
        return format_result(STATUS_ERROR, f'Failed to configure ECR: {str(e)}'), False


def validate_vm_state(
    expected_state: Literal['running', 'stopped', 'nonexistent'],
) -> Dict[str, str]:
    """Validate that the Finch VM is in the expected state.

    This function checks the current state of the VM and compares it to the expected state.
    It's used to verify that operations like start, stop, and remove have the desired effect.

    Args:
        expected_state: The state the VM should be in ("running", "stopped", or "nonexistent")

    Returns:
        Dict[str, str]: Result dictionary with:
            - status: "success" if the VM is in the expected state, "error" otherwise
            - message: Details about the validation result

    """
    try:
        status_result = get_vm_status()

        if expected_state == VM_STATE_RUNNING and is_vm_running(status_result):
            logger.debug('VM state validation passed: running')
            return format_result(
                STATUS_SUCCESS,
                'Validation passed: Finch VM is running as expected.',
            )
        elif expected_state == VM_STATE_STOPPED and is_vm_stopped(status_result):
            logger.debug('VM state validation passed: stopped')
            return format_result(
                STATUS_SUCCESS,
                'Validation passed: Finch VM is stopped as expected.',
            )
        elif expected_state == VM_STATE_NONEXISTENT and is_vm_nonexistent(status_result):
            logger.debug('VM state validation passed: nonexistent')
            return format_result(
                STATUS_SUCCESS,
                'Validation passed: Finch VM is nonexistent as expected.',
            )
        else:
            actual_state = VM_STATE_UNKNOWN
            if is_vm_running(status_result):
                actual_state = VM_STATE_RUNNING
            elif is_vm_stopped(status_result):
                actual_state = VM_STATE_STOPPED
            elif is_vm_nonexistent(status_result):
                actual_state = VM_STATE_NONEXISTENT

            logger.debug(
                f'VM state validation failed: expected={expected_state}, actual={actual_state}'
            )
            return format_result(
                STATUS_ERROR,
                f'Validation failed: Expected Finch VM to be {expected_state}, but it is {actual_state}.',
            )
    except Exception as e:
        logger.error(f'Error during VM state validation: {str(e)}')
        return format_result(STATUS_ERROR, f'Error validating VM state: {str(e)}')
