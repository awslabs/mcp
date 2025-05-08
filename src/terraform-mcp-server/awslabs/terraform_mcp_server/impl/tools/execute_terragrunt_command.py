"""Implementation of Terragrunt command execution tool."""

import json
import os
import re
import subprocess
from awslabs.terraform_mcp_server.impl.tools.utils import get_dangerous_patterns
from awslabs.terraform_mcp_server.models import (
    TerragruntExecutionRequest,
    TerragruntExecutionResult,
)
from loguru import logger


async def execute_terragrunt_command_impl(
    request: TerragruntExecutionRequest,
) -> TerragruntExecutionResult:
    """Execute Terragrunt workflow commands against an AWS account.

    This tool runs Terragrunt commands (init, plan, validate, apply, destroy, run-all) in the
    specified working directory, with optional variables and region settings.

    Parameters:
        request: Details about the Terragrunt command to execute

    Returns:
        A TerragruntExecutionResult object containing command output and status
    """
    logger.info(f"Executing 'terragrunt {request.command}' in {request.working_directory}")

    # Helper function to clean output text
    def clean_output_text(text: str) -> str:
        """Clean output text by removing or replacing problematic Unicode characters.

        Args:
            text: The text to clean

        Returns:
            Cleaned text with ASCII-friendly replacements
        """
        if not text:
            return text

        # First remove ANSI escape sequences (color codes, cursor movement)
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        text = ansi_escape.sub('', text)

        # Remove C0 and C1 control characters (except common whitespace)
        control_chars = re.compile(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]')
        text = control_chars.sub('', text)

        # Replace HTML entities
        html_entities = {
            '-&gt;': '->',  # Replace HTML arrow
            '&lt;': '<',  # Less than
            '&gt;': '>',  # Greater than
            '&amp;': '&',  # Ampersand
        }
        for entity, replacement in html_entities.items():
            text = text.replace(entity, replacement)

        # Replace box-drawing and other special Unicode characters with ASCII equivalents
        unicode_chars = {
            '\u2500': '-',  # Horizontal line
            '\u2502': '|',  # Vertical line
            '\u2514': '+',  # Up and right
            '\u2518': '+',  # Up and left
            '\u2551': '|',  # Double vertical
            '\u2550': '-',  # Double horizontal
            '\u2554': '+',  # Double down and right
            '\u2557': '+',  # Double down and left
            '\u255a': '+',  # Double up and right
            '\u255d': '+',  # Double up and left
            '\u256c': '+',  # Double cross
            '\u2588': '#',  # Full block
            '\u25cf': '*',  # Black circle
            '\u2574': '-',  # Left box drawing
            '\u2576': '-',  # Right box drawing
            '\u2577': '|',  # Down box drawing
            '\u2575': '|',  # Up box drawing
        }
        for char, replacement in unicode_chars.items():
            text = text.replace(char, replacement)

        return text

    # Set environment variables for AWS region if provided
    env = os.environ.copy()
    if request.aws_region:
        env['AWS_REGION'] = request.aws_region

    # Security check for command injection
    allowed_commands = ['init', 'plan', 'validate', 'apply', 'destroy', 'output', 'run-all']
    if request.command not in allowed_commands:
        logger.error(f'Invalid Terragrunt command: {request.command}')
        return TerragruntExecutionResult(
            command=f'terragrunt {request.command}',
            status='error',
            error_message=f'Invalid Terragrunt command: {request.command}. Allowed commands are: {", ".join(allowed_commands)}',
            working_directory=request.working_directory,
            outputs=None,
        )

    # Validate that terragrunt_config is not used with run-all
    if request.terragrunt_config and request.command == 'run-all':
        logger.error('terragrunt_config cannot be used with run-all command')
        return TerragruntExecutionResult(
            command=f'terragrunt {request.command}',
            status='error',
            error_message='Invalid configuration: --terragrunt-config cannot be used with run-all command',
            working_directory=request.working_directory,
            outputs=None,
        )

    # Check for potentially dangerous characters or command injection attempts
    dangerous_patterns = get_dangerous_patterns()
    logger.debug(f'Checking for {len(dangerous_patterns)} dangerous patterns')

    for pattern in dangerous_patterns:
        if request.variables:
            # Check if the pattern is in any of the variable values
            for var_name, var_value in request.variables.items():
                if pattern in str(var_value) or pattern in str(var_name):
                    logger.error(
                        f'Potentially dangerous pattern detected in variable {var_name}: {pattern}'
                    )
                    return TerragruntExecutionResult(
                        command=f'terragrunt {request.command}',
                        status='error',
                        error_message=f"Security violation: Potentially dangerous pattern '{pattern}' detected in variable '{var_name}'",
                        working_directory=request.working_directory,
                        outputs=None,
                    )

        # Check terragrunt_config for dangerous patterns
        if request.terragrunt_config and pattern in str(request.terragrunt_config):
            logger.error(f'Potentially dangerous pattern detected in terragrunt_config: {pattern}')
            return TerragruntExecutionResult(
                command=f'terragrunt {request.command}',
                status='error',
                error_message=f"Security violation: Potentially dangerous pattern '{pattern}' detected in terragrunt_config",
                working_directory=request.working_directory,
                outputs=None,
            )

        # Also check include_dirs and exclude_dirs for dangerous patterns
        if request.include_dirs:
            for dir_path in request.include_dirs:
                if pattern in str(dir_path):
                    logger.error(
                        f'Potentially dangerous pattern detected in include_dirs: {pattern}'
                    )
                    return TerragruntExecutionResult(
                        command=f'terragrunt {request.command}',
                        status='error',
                        error_message=f"Security violation: Potentially dangerous pattern '{pattern}' detected in include_dirs",
                        working_directory=request.working_directory,
                        outputs=None,
                    )

        if request.exclude_dirs:
            for dir_path in request.exclude_dirs:
                if pattern in str(dir_path):
                    logger.error(
                        f'Potentially dangerous pattern detected in exclude_dirs: {pattern}'
                    )
                    return TerragruntExecutionResult(
                        command=f'terragrunt {request.command}',
                        status='error',
                        error_message=f"Security violation: Potentially dangerous pattern '{pattern}' detected in exclude_dirs",
                        working_directory=request.working_directory,
                        outputs=None,
                    )

    # Build the command
    base_cmd = ['terragrunt']

    # Handle run-all command differently
    if request.command == 'run-all':
        base_cmd.append('run-all')
        # The actual terraform command becomes the first argument
        # Default to 'apply' if not specified in the command
        base_cmd.append('apply')
    else:
        base_cmd.append(request.command)

    # Add auto-approve flag for apply and destroy commands to make them non-interactive
    if request.command in ['apply', 'destroy'] or (request.command == 'run-all'):
        logger.info(f'Adding -auto-approve flag to {request.command} command')
        base_cmd.append('-auto-approve')

    # Add terragrunt_config if specified and not using run-all
    if request.terragrunt_config:
        logger.info(f'Using custom terragrunt config file: {request.terragrunt_config}')
        base_cmd.append(f'--terragrunt-config={request.terragrunt_config}')

    # Add variables only for commands that accept them (plan, apply, destroy, output)
    if request.command in ['plan', 'apply', 'destroy', 'output', 'run-all'] and request.variables:
        logger.info(f'Adding {len(request.variables)} variables to {request.command} command')
        for key, value in request.variables.items():
            base_cmd.append(f'-var={key}={value}')

    # Add include-dirs if specified
    if request.include_dirs and request.command == 'run-all':
        for dir_path in request.include_dirs:
            base_cmd.append(f'--queue-include-dir={dir_path}')

    # Add exclude-dirs if specified
    if request.exclude_dirs and request.command == 'run-all':
        for dir_path in request.exclude_dirs:
            base_cmd.append(f'--queue-exclude-dir={dir_path}')

    # Execute command
    try:
        process = subprocess.run(
            base_cmd, cwd=request.working_directory, capture_output=True, text=True, env=env
        )

        # Prepare the result
        stdout = process.stdout
        stderr = process.stderr if process.stderr else ''

        # Clean output text if requested
        if request.strip_ansi:
            logger.debug('Cleaning command output text (ANSI codes and control characters)')
            stdout = clean_output_text(stdout)
            stderr = clean_output_text(stderr)

        # Extract affected directories for run-all command
        affected_dirs = None
        if request.command == 'run-all':
            affected_dirs = []
            # Look for directory paths in the output
            dir_pattern = re.compile(r'Module at\s+"([^"]+)"')
            for match in dir_pattern.finditer(stdout):
                affected_dirs.append(match.group(1))

        result = {
            'command': f'terragrunt {request.command}',
            'status': 'success' if process.returncode == 0 else 'error',
            'return_code': process.returncode,
            'stdout': stdout,
            'stderr': stderr,
            'working_directory': request.working_directory,
            'outputs': None,
            'affected_dirs': affected_dirs,
        }

        # Get outputs if this was a successful apply or output command
        if (
            request.command in ['apply', 'output'] or (request.command == 'run-all')
        ) and process.returncode == 0:
            try:
                logger.info('Getting Terragrunt outputs')
                output_process = subprocess.run(
                    ['terragrunt', 'output', '-json'],
                    cwd=request.working_directory,
                    capture_output=True,
                    text=True,
                    env=env,
                )

                if output_process.returncode == 0 and output_process.stdout:
                    # Get output and clean it if needed
                    output_stdout = output_process.stdout
                    if request.strip_ansi:
                        output_stdout = clean_output_text(output_stdout)

                    # Parse the JSON output
                    raw_outputs = json.loads(output_stdout)

                    # Process outputs to extract values from complex structure
                    processed_outputs = {}
                    for key, value in raw_outputs.items():
                        # Terraform outputs in JSON format have a nested structure
                        # with 'value', 'type', and sometimes 'sensitive'
                        if isinstance(value, dict) and 'value' in value:
                            processed_outputs[key] = value['value']
                        else:
                            processed_outputs[key] = value

                    result['outputs'] = processed_outputs
                    logger.info(f'Extracted {len(processed_outputs)} Terragrunt outputs')
            except Exception as e:
                logger.warning(f'Failed to get Terragrunt outputs: {e}')

        # Return the output
        return TerragruntExecutionResult(**result)
    except Exception as e:
        return TerragruntExecutionResult(
            command=f'terragrunt {request.command}',
            status='error',
            error_message=str(e),
            working_directory=request.working_directory,
            outputs=None,
        )
