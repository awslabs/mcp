"""Implementation of Terraform command execution tool."""

import json
import os
import re
import subprocess
from terraform_mcp_server.models import TerraformExecutionRequest, TerraformExecutionResult
from loguru import logger


async def execute_terraform_command_impl(
    request: TerraformExecutionRequest,
) -> TerraformExecutionResult:
    """Execute Terraform workflow commands against an AWS account.

    This tool runs Terraform commands (init, plan, validate, apply, destroy) in the
    specified working directory, with optional variables and region settings.

    Parameters:
        request: Details about the Terraform command to execute

    Returns:
        A TerraformExecutionResult object containing command output and status
    """
    logger.info(f"Executing 'terraform {request.command}' in {request.working_directory}")

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

    # Build the command
    cmd = ['terraform', request.command]

    # Add auto-approve flag for apply and destroy commands to make them non-interactive
    if request.command in ['apply', 'destroy']:
        logger.info(f'Adding -auto-approve flag to {request.command} command')
        cmd.append('-auto-approve')

    # Add variables only for commands that accept them (plan, apply, destroy)
    if request.command in ['plan', 'apply', 'destroy'] and request.variables:
        logger.info(f'Adding {len(request.variables)} variables to {request.command} command')
        for key, value in request.variables.items():
            cmd.append(f'-var={key}={value}')

    # Execute command
    try:
        process = subprocess.run(
            cmd, cwd=request.working_directory, capture_output=True, text=True, env=env
        )

        # Prepare the result
        stdout = process.stdout
        stderr = process.stderr if process.stderr else ''

        # Clean output text if requested
        if request.strip_ansi:
            logger.debug('Cleaning command output text (ANSI codes and control characters)')
            stdout = clean_output_text(stdout)
            stderr = clean_output_text(stderr)

        result = {
            'command': f'terraform {request.command}',
            'status': 'success' if process.returncode == 0 else 'error',
            'return_code': process.returncode,
            'stdout': stdout,
            'stderr': stderr,
            'working_directory': request.working_directory,
            'outputs': None,
        }

        # Get outputs if this was a successful apply command
        if request.command == 'apply' and process.returncode == 0:
            try:
                logger.info('Getting Terraform outputs')
                output_process = subprocess.run(
                    ['terraform', 'output', '-json'],
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
                    logger.info(f'Extracted {len(processed_outputs)} Terraform outputs')
            except Exception as e:
                logger.warning(f'Failed to get Terraform outputs: {e}')

        # Return the output
        return TerraformExecutionResult(**result)
    except Exception as e:
        return TerraformExecutionResult(
            command=f'terraform {request.command}',
            status='error',
            error_message=str(e),
            working_directory=request.working_directory,
            outputs=None,
        )
