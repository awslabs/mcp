from typing import Any, Dict, Literal
import os
import subprocess
import logging
import sys
import json
import yaml

from ..consts import (
    VM_STATE_RUNNING, VM_STATE_STOPPED, VM_STATE_NONEXISTENT, VM_STATE_UNKNOWN,
    STATUS_SUCCESS, STATUS_ERROR,
    CONFIG_JSON_PATH, FINCH_YAML_PATH
)
from .common import execute_command, format_result

logger = logging.getLogger(__name__)

def get_vm_status() -> subprocess.CompletedProcess:
    """
    Get the current status of the Finch VM.
    
    This function executes 'finch vm status' and returns the raw result.
    It's a wrapper around execute_command that simplifies checking
    the VM status, which is a common operation used by multiple tools.
    
    Returns:
        CompletedProcess with the status command result, containing:
        - returncode: The exit code of the command
        - stdout: Standard output containing status information
        - stderr: Standard error output, may also contain status information
    """
    return execute_command(['finch','vm', 'status'])

def is_vm_nonexistent(status_result: subprocess.CompletedProcess) -> bool:
    """
    Check if the Finch VM is nonexistent based on status result.
    
    This function analyzes the output of 'finch vm status' to determine
    if the VM has not been created yet.
    
    Args:
        status_result: CompletedProcess object from running 'finch vm status'
        
    Returns:
        bool: True if the VM is nonexistent, False otherwise
    """
    return ("nonexistent" in status_result.stderr.lower() or 
            "nonexistent" in status_result.stdout.lower())

def is_vm_stopped(status_result: subprocess.CompletedProcess) -> bool:
    """
    Check if the Finch VM is stopped based on status result.
    
    This function analyzes the output of 'finch vm status' to determine
    if the VM exists but is not currently running.
    
    Args:
        status_result: CompletedProcess object from running 'finch vm status'
        
    Returns:
        bool: True if the VM is stopped, False otherwise
    """
    return ("stopped" in status_result.stderr.lower() or 
            "stopped" in status_result.stdout.lower())

def is_vm_running(status_result: subprocess.CompletedProcess) -> bool:
    """
    Check if the Finch VM is running based on status result.
    
    This function analyzes the output of 'finch vm status' to determine
    if the VM is currently active and operational.
    
    Args:
        status_result: CompletedProcess object from running 'finch vm status'
        
    Returns:
        bool: True if the VM is running, False otherwise
    """
    return ("running" in status_result.stdout.lower() or 
            "running" in status_result.stderr.lower())

def initialize_vm() -> Dict[str, Any]:
    """
    Initialize a new Finch VM.
    
    This function runs 'finch vm init' to create a new Finch VM instance.
    It's used when the VM doesn't exist yet and needs to be created.
    
    Returns:
        Dict[str, Any]: Result dictionary with:
            - status: "success" if initialization succeeded, "error" otherwise
            - message: Details about the initialization result
    """
    logger.warning("Finch VM non existent, Initializing a new vm instance...")
    init_result = execute_command(['finch', 'vm', 'init'])
    
    if init_result.returncode == 0:
        return format_result(STATUS_SUCCESS, "Finch VM was initialized successfully.")
    else:
        return format_result(STATUS_ERROR, f"Failed to initialize Finch VM: {init_result.stderr}")

def start_stopped_vm() -> Dict[str, Any]:
    """
    Start a stopped Finch VM.
    
    This function runs 'finch vm start' to start a VM that exists but is
    currently stopped. It's used to make the VM operational when it's not running.
    
    Returns:
        Dict[str, Any]: Result dictionary with:
            - status: "success" if the VM was started successfully, "error" otherwise
            - message: Details about the start operation result
    """
    logger.info("Finch VM is stopped. Starting it...")
    start_result = execute_command(['finch', 'vm', 'start'])
    
    if start_result.returncode == 0:
        return format_result(STATUS_SUCCESS, "Finch VM was stopped and has been started successfully.")
    else:
        return format_result(STATUS_ERROR, f"Failed to start Finch VM: {start_result.stderr}")

def stop_vm(force: bool = False) -> Dict[str, Any]:
    """
    Stop a running Finch VM.
    
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
    command = ['finch', 'vm', 'stop']
    if force:
        command.append('--force')
        
    stop_result = execute_command(command)
    
    if stop_result.returncode == 0:
        return format_result(STATUS_SUCCESS, "Finch VM has been stopped successfully.")
    else:
        return format_result(STATUS_ERROR, f"Failed to stop Finch VM: {stop_result.stderr}")

def remove_vm(force: bool = False) -> Dict[str, Any]:
    """
    Remove the Finch VM.
    
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
    command = ['finch', 'vm', 'rm']
    if force:
        command.append('--force')
        
    remove_result = execute_command(command)
    
    if remove_result.returncode == 0:
        return format_result(STATUS_SUCCESS, "Finch VM has been removed successfully.")
    else:
        return format_result(STATUS_ERROR, f"Failed to remove Finch VM: {remove_result.stderr}")

def restart_running_vm() -> Dict[str, Any]:
    """
    Restart a running Finch VM (stop then start).
    
    This function performs a full restart of the VM by first stopping it
    (with force=True to ensure it stops) and then starting it again.
    It's useful when you need to refresh the VM state completely.
    
    Returns:
        Dict[str, Any]: Result dictionary with:
            - status: "success" if the VM was restarted successfully, "error" otherwise
            - message: Details about the restart operation result
    """
    logger.info("Finch VM is running. Restarting it...")
    
    stop_result = stop_vm(force=True)
    if stop_result["status"] == STATUS_ERROR:
        return stop_result
    
    start_result = start_stopped_vm()
    
    return start_result

def check_finch_installation() -> Dict[str, Any]:
    """
    Check if the Finch CLI tool is installed on the system.
    
    This function uses 'which finch' on macOS/Linux to determine if the
    Finch command-line tool is available in the system PATH. It's a
    prerequisite check before attempting to use any Finch functionality.
    
    Returns:
        Dict[str, Any]: Result dictionary with:
            - status: "success" if Finch is installed, "error" otherwise
            - message: Details about the installation status
    """
    try:
        if sys.platform == "darwin" or sys.platform == "linux":
            result = execute_command(['which', 'finch'])
            if result.returncode == 0:
                return format_result(STATUS_SUCCESS, "Finch is installed.")
            else:
                return format_result(STATUS_ERROR, "Finch is not installed.")
        else:
            return format_result(STATUS_ERROR, f"Unsupported operating system. {sys.platform}")
    except Exception as e:
        return format_result(STATUS_ERROR, f"Error checking Finch installation: {str(e)}")

def configure_ecr() -> Dict[str, Any]:
    """
    Configure Finch to use ECR (Amazon Elastic Container Registry).
    
    This function updates two Finch configuration files using a merge policy:
    1. ~/.finch/config.json - Sets 'credsStore' to 'ecr-login' while preserving other settings
    2. ~/.finch/finch.yaml - Adds 'ecr-login' to the creds_helpers list while preserving other settings
    
    This enables Finch to authenticate with Amazon ECR.
    
    Returns:
        Dict[str, Any]: Result dictionary with:
            - status: "success" if the configuration was updated successfully, "error" otherwise
            - message: Details about the configuration result
            - changed: Boolean indicating whether the configuration was changed
    """
    try:
        changed_json = False
        changed_yaml = False
        config_dir = os.path.expanduser("~/.finch")
        
        # Create the directory if it doesn't exist
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            logger.info(f"Created directory: {config_dir}")
        
        config_json_path = os.path.expanduser(CONFIG_JSON_PATH)
        
        existing_config_json = {}
        if os.path.exists(config_json_path):
            try:
                with open(config_json_path, 'r') as f:
                    existing_config_json = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in {config_json_path}, will create a new valid JSON file")
            except Exception as e:
                logger.warning(f"Error reading {config_json_path}: {str(e)}")
        
        if existing_config_json.get("credsStore") != "ecr-login":
            existing_config_json["credsStore"] = "ecr-login"
            changed_json = True
            
            with open(config_json_path, 'w') as f:
                json.dump(existing_config_json, f, indent=4)
        elif not os.path.exists(config_json_path):
            with open(config_json_path, 'w') as f:
                json.dump({"credsStore": "ecr-login"}, f, indent=4)
            changed_json = True
        
        finch_yaml_path = os.path.expanduser(FINCH_YAML_PATH)
        
        if os.path.exists(finch_yaml_path):
            try:
                with open(finch_yaml_path, 'r') as f:
                    yaml_content = yaml.safe_load(f) or {}
                
                if 'creds_helpers' in yaml_content:
                    if not isinstance(yaml_content['creds_helpers'], list):
                        yaml_content['creds_helpers'] = [yaml_content['creds_helpers']] if yaml_content['creds_helpers'] else []
                    
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
                logger.warning(f"Error updating {finch_yaml_path} with PyYAML: {str(e)}")
                return format_result(STATUS_ERROR, f"Failed to update YAML file: {str(e)}")
        else:
            return format_result(STATUS_ERROR,"finch yaml file not found in ~/.finch/finch.yaml")

        changed = changed_json or changed_yaml
        
        if changed:
            return format_result(STATUS_SUCCESS, "ECR configuration updated successfully using PyYAML.", changed=True)
        else:
            return format_result(STATUS_SUCCESS, "ECR was already configured correctly.", changed=False)
    
    except Exception as e:
        return format_result(STATUS_ERROR, f"Failed to configure ECR: {str(e)}")

def is_ecr_credhelper_configured() -> Dict[str, Any]:
    """
    Check if Finch is configured to use ECR credhelper (Amazon Elastic Container Registry).
    
    This function examines two Finch configuration files:
    1. ~/.finch/config.json - Checks if 'credsStore' is set to 'ecr-login'
    2. ~/.finch/finch.yaml - Checks if 'ecr-login' is in the creds_helpers list
    
    Returns:
        Dict[str, Any]: Result dictionary with:
            - status: "success" if the check completed successfully, "error" otherwise
            - message: Details about the ECR credhelper configuration status
            - configured: Boolean indicating whether ECR is properly configured
            - config_json_status: Boolean indicating if config.json is properly configured
            - finch_yaml_status: Boolean indicating if finch.yaml is properly configured
    """
    try:
        config_json_configured = False
        finch_yaml_configured = False
        
        # Check config.json
        config_json_path = os.path.expanduser(CONFIG_JSON_PATH)
        if os.path.exists(config_json_path):
            # TODO: Add support where configuration can have credhelpers with individual repositories configured to use ecr-login
            try:
                with open(config_json_path, 'r') as f:
                    config_json = json.load(f)
                    config_json_configured = config_json.get("credsStore") == "ecr-login"
            except Exception as e:
                logger.warning(f"Error reading {config_json_path}: {str(e)}")
        
        finch_yaml_path = os.path.expanduser(FINCH_YAML_PATH)
        if os.path.exists(finch_yaml_path):
            try:
                with open(finch_yaml_path, 'r') as f:
                    yaml_content = yaml.safe_load(f) or {}
                    
                    if 'creds_helpers' in yaml_content:
                        if isinstance(yaml_content['creds_helpers'], list):
                            finch_yaml_configured = 'ecr-login' in yaml_content['creds_helpers']
                        else:
                            finch_yaml_configured = yaml_content['creds_helpers'] == 'ecr-login'
            except Exception as e:
                logger.warning(f"Error reading {finch_yaml_path}: {str(e)}")
        
        is_configured = config_json_configured and finch_yaml_configured
        
        if is_configured:
            message = "ECR is properly configured in Finch."
        elif config_json_configured and not finch_yaml_configured:
            message = "ECR is partially configured: config.json is correct but finch.yaml is not configured."
        elif not config_json_configured and finch_yaml_configured:
            message = "ECR is partially configured: finch.yaml is correct but config.json is not configured."
        else:
            message = "ECR is not configured in Finch."
        
        return format_result(
            STATUS_SUCCESS, 
            message, 
            configured=is_configured,
            config_json_status=config_json_configured,
            finch_yaml_status=finch_yaml_configured
        )
    
    except Exception as e:
        return format_result(STATUS_ERROR, f"Error checking ECR configuration: {str(e)}")

def restart_vm_if_running() -> Dict[str, Any]:
    """
    Restart the Finch VM if it's currently running.
    
    This function checks if the Finch VM is running, and if so, stops and starts it
    to pick up any configuration changes. If the VM is not running, it does nothing.
    
    Returns:
        Dict[str, Any]: Result dictionary with:
            - status: "success" if the operation succeeded, "error" otherwise
            - message: Details about the restart operation result
            - restarted: Boolean indicating whether the VM was restarted
    """
    try:
        status_result = get_vm_status()
        
        if is_vm_running(status_result):
            stop_result = stop_vm()
            if stop_result["status"] == STATUS_ERROR:
                return {**stop_result, "restarted": False}
            
            start_result = start_stopped_vm()
            if start_result["status"] == STATUS_ERROR:
                return {**start_result, "restarted": False}
            
            return format_result(STATUS_SUCCESS, "Finch VM has been restarted to apply new configuration.", restarted=True)
        else:
            return format_result(STATUS_SUCCESS, "Finch VM is not running, no restart needed.", restarted=False)
    
    except Exception as e:
        return format_result(STATUS_ERROR, f"Error checking or restarting Finch VM: {str(e)}")

def validate_vm_state(expected_state: Literal["running", "stopped", "nonexistent"]) -> Dict[str, Any]:
    """
    Validate that the Finch VM is in the expected state.
    
    This function checks the current state of the VM and compares it to the expected state.
    It's used to verify that operations like start, stop, and remove have the desired effect.
    
    Args:
        expected_state: The state the VM should be in ("running", "stopped", or "nonexistent")
        
    Returns:
        Dict[str, Any]: Result dictionary with:
            - status: "success" if the VM is in the expected state, "error" otherwise
            - message: Details about the validation result
            - validated: Boolean indicating whether validation passed
    """
    try:
        status_result = get_vm_status()
        
        if expected_state == VM_STATE_RUNNING and is_vm_running(status_result):
            return format_result(STATUS_SUCCESS, "Validation passed: Finch VM is running as expected.", validated=True)
        elif expected_state == VM_STATE_STOPPED and is_vm_stopped(status_result):
            return format_result(STATUS_SUCCESS, "Validation passed: Finch VM is stopped as expected.", validated=True)
        elif expected_state == VM_STATE_NONEXISTENT and is_vm_nonexistent(status_result):
            return format_result(STATUS_SUCCESS, "Validation passed: Finch VM is nonexistent as expected.", validated=True)
        else:
            actual_state = VM_STATE_UNKNOWN
            if is_vm_running(status_result):
                actual_state = VM_STATE_RUNNING
            elif is_vm_stopped(status_result):
                actual_state = VM_STATE_STOPPED
            elif is_vm_nonexistent(status_result):
                actual_state = VM_STATE_NONEXISTENT
                
            return format_result(
                STATUS_ERROR, 
                f"Validation failed: Expected Finch VM to be {expected_state}, but it is {actual_state}.",
                validated=False
            )
    except Exception as e:
        return format_result(STATUS_ERROR, f"Error validating VM state: {str(e)}", validated=False)
