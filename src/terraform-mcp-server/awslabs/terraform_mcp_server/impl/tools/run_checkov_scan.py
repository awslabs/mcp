"""Implementation of Checkov scan and fix tools."""

import json
import os
import re
import subprocess
import tempfile
from typing import Dict, List, Optional, Any, Union, Tuple

from loguru import logger

from ...models import (
    CheckovScanRequest,
    CheckovScanResult,
    CheckovFixRequest,
    CheckovFixResult,
    CheckovVulnerability,
)


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
                    severity=check.get('severity', 'MEDIUM').upper(),
                    fixed=False,
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
    logger.info(f"Running Checkov scan in {request.working_directory}")

    # Ensure Checkov is installed
    if not _ensure_checkov_installed():
        return CheckovScanResult(
            status='error',
            working_directory=request.working_directory,
            error_message='Failed to install Checkov. Please install it manually with: pip install checkov',
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
    
    logger.info(f"Using absolute working directory: {working_dir}")
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
        logger.info(f"Executing command: {' '.join(cmd)}")
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        # Clean output text
        stdout = _clean_output_text(process.stdout)
        stderr = _clean_output_text(process.stderr)
        
        # Debug logging
        logger.info(f"Checkov return code: {process.returncode}")
        logger.info(f"Checkov stdout: {stdout}")
        logger.info(f"Checkov stderr: {stderr}")

        # Parse results if JSON output was requested
        vulnerabilities = []
        summary = {}
        if request.output_format == 'json' and stdout:
            vulnerabilities, summary = _parse_checkov_json_output(stdout)
        
        # For non-JSON output, try to parse vulnerabilities from the text output
        elif stdout and process.returncode == 1:  # Return code 1 means vulnerabilities were found
            # Simple regex to extract failed checks from CLI output
            failed_checks = re.findall(r'Check: (CKV\w*_\d+).*?FAILED for resource: ([\w\.]+).*?File: ([\w\/\.-]+):(\d+)', stdout, re.DOTALL)
            for check_id, resource, file_path, line in failed_checks:
                vuln = CheckovVulnerability(
                    id=check_id,
                    type='terraform',
                    resource=resource,
                    file_path=file_path,
                    line=int(line),
                    description=f"Failed check: {check_id}",
                    severity='MEDIUM',
                    fixed=False,
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

        # If auto-fix is requested and vulnerabilities were found, attempt to fix them
        if request.auto_fix and vulnerabilities:
            logger.info(f"Auto-fix requested, attempting to fix {len(vulnerabilities)} vulnerabilities")
            fix_request = CheckovFixRequest(
                working_directory=request.working_directory,
                vulnerability_ids=[v.id for v in vulnerabilities],
                backup_files=True,
            )
            fix_result = await run_checkov_fix_impl(fix_request)
            
            # Update vulnerabilities with fix status
            for vuln in result.vulnerabilities:
                for fixed_vuln in fix_result.fixed_vulnerabilities:
                    if vuln.id == fixed_vuln.id and vuln.resource == fixed_vuln.resource:
                        vuln.fixed = True
                        vuln.fix_details = fixed_vuln.fix_details

        return result
    except Exception as e:
        logger.error(f"Error running Checkov scan: {e}")
        return CheckovScanResult(
            status='error',
            working_directory=request.working_directory,
            error_message=str(e),
        )


async def run_checkov_fix_impl(request: CheckovFixRequest) -> CheckovFixResult:
    """Fix vulnerabilities found by Checkov in Terraform code.

    Args:
        request: Details about the vulnerabilities to fix

    Returns:
        A CheckovFixResult object containing fix results
    """
    logger.info(f"Attempting to fix {len(request.vulnerability_ids)} vulnerabilities in {request.working_directory}")

    # Ensure Checkov is installed
    if not _ensure_checkov_installed():
        return CheckovFixResult(
            status='error',
            working_directory=request.working_directory,
            error_message='Failed to install Checkov. Please install it manually with: pip install checkov',
        )

    # Create backup files if requested
    if request.backup_files:
        try:
            backup_dir = os.path.join(request.working_directory, '.checkov_backups')
            os.makedirs(backup_dir, exist_ok=True)
            logger.info(f"Created backup directory: {backup_dir}")
        except Exception as e:
            logger.error(f"Failed to create backup directory: {e}")
            return CheckovFixResult(
                status='error',
                working_directory=request.working_directory,
                error_message=f'Failed to create backup directory: {str(e)}',
            )

    # Build the command for fixing
    cmd = ['checkov', '--quiet', '-d', request.working_directory, '--framework', 'terraform']
    
    # Add specific check IDs to fix
    if request.vulnerability_ids:
        cmd.extend(['--check', ','.join(request.vulnerability_ids)])
    
    # Add fix flag
    cmd.extend(['--fix'])
    
    # Execute command
    try:
        logger.info(f"Executing command: {' '.join(cmd)}")
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        # Clean output text
        stdout = _clean_output_text(process.stdout)
        stderr = _clean_output_text(process.stderr)

        # Run a scan after fixing to see what was fixed and what remains
        scan_request = CheckovScanRequest(
            working_directory=request.working_directory,
            framework='terraform',
            check_ids=request.vulnerability_ids,
            output_format='json',
        )
        scan_result = await run_checkov_scan_impl(scan_request)

        # Determine which vulnerabilities were fixed
        fixed_vulnerabilities = []
        unfixed_vulnerabilities = []

        # If we have the original scan results, we can compare to determine what was fixed
        if scan_result.vulnerabilities:
            # These are the remaining unfixed vulnerabilities
            unfixed_vulnerabilities = scan_result.vulnerabilities
            
            # For fixed vulnerabilities, we need to parse the fix output
            # This is a simplified approach - in a real implementation, you'd want to
            # compare before/after scan results to determine exactly what was fixed
            fix_pattern = re.compile(r'Fixed\s+(\w+)\s+in\s+(.+?)\s+resource\s+(.+?)(?:\s|$)')
            for match in fix_pattern.finditer(stdout):
                check_id, file_path, resource = match.groups()
                fixed_vuln = CheckovVulnerability(
                    id=check_id,
                    type='terraform',
                    resource=resource,
                    file_path=file_path,
                    line=0,  # We don't know the exact line
                    description=f"Fixed {check_id}",
                    fixed=True,
                    fix_details=f"Automatically fixed by Checkov",
                )
                fixed_vulnerabilities.append(fixed_vuln)

        # Prepare the result
        return CheckovFixResult(
            status='success' if process.returncode == 0 else 'error',
            return_code=process.returncode,
            working_directory=request.working_directory,
            fixed_vulnerabilities=fixed_vulnerabilities,
            unfixed_vulnerabilities=unfixed_vulnerabilities,
            summary={
                'fixed_count': len(fixed_vulnerabilities),
                'unfixed_count': len(unfixed_vulnerabilities),
                'stdout': stdout,
                'stderr': stderr,
            },
        )
    except Exception as e:
        logger.error(f"Error fixing vulnerabilities: {e}")
        return CheckovFixResult(
            status='error',
            working_directory=request.working_directory,
            error_message=str(e),
        )
