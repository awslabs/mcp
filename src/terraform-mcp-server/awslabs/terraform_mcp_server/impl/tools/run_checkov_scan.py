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
"""Implementation of Checkov scan tools."""

import json
import os
import re
import subprocess
from awslabs.terraform_mcp_server.impl.tools.utils import get_dangerous_patterns
from awslabs.terraform_mcp_server.models import (
    CheckovScanRequest,
    CheckovScanResult,
    CheckovVulnerability,
)
from loguru import logger
from typing import Any, Dict, List, Tuple


def _clean_output_text(text: str) -> str:
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


def _ensure_checkov_installed() -> bool:
    """Ensure Checkov is installed, and install it if not.

    Returns:
        True if Checkov is installed or was successfully installed, False otherwise
    """
    try:
        # Check if Checkov is already installed
        subprocess.run(
            ['checkov', '--version'],
            capture_output=True,
            text=True,
            check=False,
        )
        logger.info('Checkov is already installed')
        return True
    except FileNotFoundError:
        logger.warning('Checkov not found, attempting to install')
        try:
            # Install Checkov using pip
            subprocess.run(
                ['pip', 'install', 'checkov'],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info('Successfully installed Checkov')
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f'Failed to install Checkov: {e}')
            return False


def _parse_checkov_json_output(output: str) -> Tuple[List[CheckovVulnerability], Dict[str, Any]]:
    """Parse Checkov JSON output into structured vulnerability data.

    Args:
        output: JSON output from Checkov scan

    Returns:
        Tuple of (list of vulnerabilities, summary dictionary)
    """
    try:
        data = json.loads(output)
        vulnerabilities = []
        summary = {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'parsing_errors': 0,
            'resource_count': 0,
        }

        # Extract summary information
        if 'summary' in data:
            summary = data['summary']

        # Process check results
        if 'results' in data and 'failed_checks' in data['results']:
            for check in data['results']['failed_checks']:
                vuln = CheckovVulnerability(
                    id=check.get('check_id', 'UNKNOWN'),
                    type=check.get('check_type', 'terraform'),
                    resource=check.get('resource', 'UNKNOWN'),
                    file_path=check.get('file_path', 'UNKNOWN'),
                    line=check.get('file_line_range', [0, 0])[0],
                    description=check.get('check_name', 'UNKNOWN'),
                    guideline=check.get('guideline', None),
                    severity=(check.get('severity', 'MEDIUM') or 'MEDIUM').upper(),
                    fixed=False,
                    fix_details=None,
                )
                vulnerabilities.append(vuln)

        return vulnerabilities, summary
    except json.JSONDecodeError as e:
        logger.error(f'Failed to parse Checkov JSON output: {e}')
        return [], {'error': 'Failed to parse JSON output'}


async def run_checkov_scan_impl(request: CheckovScanRequest) -> CheckovScanResult:
    """Run Checkov scan on Terraform code.

    Args:
        request: Details about the Checkov scan to execute

    Returns:
        A CheckovScanResult object containing scan results and vulnerabilities
    """
    logger.info(f'Running Checkov scan in {request.working_directory}')

    # Ensure Checkov is installed
    if not _ensure_checkov_installed():
        return CheckovScanResult(
            status='error',
            working_directory=request.working_directory,
            error_message='Failed to install Checkov. Please install it manually with: pip install checkov',
            vulnerabilities=[],
            summary={},
            raw_output=None,
        )

    # Security checks for parameters

    # Check framework parameter for allowed values
    allowed_frameworks = ['terraform', 'cloudformation', 'kubernetes', 'dockerfile', 'arm', 'all']
    if request.framework not in allowed_frameworks:
        logger.error(f'Security violation: Invalid framework: {request.framework}')
        return CheckovScanResult(
            status='error',
            working_directory=request.working_directory,
            error_message=f"Security violation: Invalid framework '{request.framework}'. Allowed frameworks are: {', '.join(allowed_frameworks)}",
            vulnerabilities=[],
            summary={},
            raw_output=None,
        )

    # Check output_format parameter for allowed values
    allowed_output_formats = [
        'cli',
        'csv',
        'cyclonedx',
        'cyclonedx_json',
        'spdx',
        'json',
        'junitxml',
        'github_failed_only',
        'gitlab_sast',
        'sarif',
    ]
    if request.output_format not in allowed_output_formats:
        logger.error(f'Security violation: Invalid output format: {request.output_format}')
        return CheckovScanResult(
            status='error',
            working_directory=request.working_directory,
            error_message=f"Security violation: Invalid output format '{request.output_format}'. Allowed formats are: {', '.join(allowed_output_formats)}",
            vulnerabilities=[],
            summary={},
            raw_output=None,
        )

    # Check for command injection patterns in check_ids and skip_check_ids
    dangerous_patterns = get_dangerous_patterns()
    logger.debug(f'Checking for {len(dangerous_patterns)} dangerous patterns')

    if request.check_ids:
        for check_id in request.check_ids:
            for pattern in dangerous_patterns:
                if pattern in check_id:
                    logger.error(
                        f"Security violation: Potentially dangerous pattern '{pattern}' in check_id: {check_id}"
                    )
                    return CheckovScanResult(
                        status='error',
                        working_directory=request.working_directory,
                        error_message=f"Security violation: Potentially dangerous pattern '{pattern}' detected in check_id",
                        vulnerabilities=[],
                        summary={},
                        raw_output=None,
                    )

    if request.skip_check_ids:
        for skip_id in request.skip_check_ids:
            for pattern in dangerous_patterns:
                if pattern in skip_id:
                    logger.error(
                        f"Security violation: Potentially dangerous pattern '{pattern}' in skip_check_id: {skip_id}"
                    )
                    return CheckovScanResult(
                        status='error',
                        working_directory=request.working_directory,
                        error_message=f"Security violation: Potentially dangerous pattern '{pattern}' detected in skip_check_id",
                        vulnerabilities=[],
                        summary={},
                        raw_output=None,
                    )

    # Build the command
    # Convert working_directory to absolute path if it's not already
    working_dir = request.working_directory
    if not os.path.isabs(working_dir):
        # Get the current working directory of the MCP server
        current_dir = os.getcwd()
        # Go up to the project root directory (assuming we're in src/terraform-mcp-server/awslabs/terraform_mcp_server)
        project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
        # Join with the requested working directory
        working_dir = os.path.abspath(os.path.join(project_root, working_dir))

    logger.info(f'Using absolute working directory: {working_dir}')
    cmd = ['checkov', '--quiet', '-d', working_dir]

    # Add framework if specified
    if request.framework:
        cmd.extend(['--framework', request.framework])

    # Add specific check IDs if provided
    if request.check_ids:
        cmd.extend(['--check', ','.join(request.check_ids)])

    # Add skip check IDs if provided
    if request.skip_check_ids:
        cmd.extend(['--skip-check', ','.join(request.skip_check_ids)])

    # Set output format
    cmd.extend(['--output', request.output_format])

    # Execute command
    try:
        logger.info(f'Executing command: {" ".join(cmd)}')
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        # Clean output text
        stdout = _clean_output_text(process.stdout)
        stderr = _clean_output_text(process.stderr)

        # Debug logging
        logger.info(f'Checkov return code: {process.returncode}')
        logger.info(f'Checkov stdout: {stdout}')
        logger.info(f'Checkov stderr: {stderr}')

        # Parse results if JSON output was requested
        vulnerabilities = []
        summary = {}
        if request.output_format == 'json' and stdout:
            vulnerabilities, summary = _parse_checkov_json_output(stdout)

        # For non-JSON output, try to parse vulnerabilities from the text output
        elif stdout and process.returncode == 1:  # Return code 1 means vulnerabilities were found
            # Simple regex to extract failed checks from CLI output
            failed_checks = re.findall(
                r'Check: (CKV\w*_\d+).*?FAILED for resource: ([\w\.]+).*?File: ([\w\/\.-]+):(\d+)',
                stdout,
                re.DOTALL,
            )
            for check_id, resource, file_path, line in failed_checks:
                vuln = CheckovVulnerability(
                    id=check_id,
                    type='terraform',
                    resource=resource,
                    file_path=file_path,
                    line=int(line),
                    description=f'Failed check: {check_id}',
                    guideline=None,
                    severity='MEDIUM',
                    fixed=False,
                    fix_details=None,
                )
                vulnerabilities.append(vuln)

            # Extract summary counts
            passed_match = re.search(r'Passed checks: (\d+)', stdout)
            failed_match = re.search(r'Failed checks: (\d+)', stdout)
            skipped_match = re.search(r'Skipped checks: (\d+)', stdout)

            summary = {
                'passed': int(passed_match.group(1)) if passed_match else 0,
                'failed': int(failed_match.group(1)) if failed_match else 0,
                'skipped': int(skipped_match.group(1)) if skipped_match else 0,
            }

        # Prepare the result - consider it a success even if vulnerabilities were found
        # A return code of 1 from Checkov means vulnerabilities were found, not an error
        is_error = process.returncode not in [0, 1]
        result = CheckovScanResult(
            status='error' if is_error else 'success',
            return_code=process.returncode,
            working_directory=request.working_directory,
            vulnerabilities=vulnerabilities,
            summary=summary,
            raw_output=stdout,
        )

        return result
    except Exception as e:
        logger.error(f'Error running Checkov scan: {e}')
        return CheckovScanResult(
            status='error',
            working_directory=request.working_directory,
            error_message=str(e),
            vulnerabilities=[],
            summary={},
            raw_output=None,
        )
