"""Tests for the run_checkov_scan implementation."""

import json
import os
import pytest
from awslabs.terraform_mcp_server.impl.tools.run_checkov_scan import (
    _clean_output_text,
    _parse_checkov_json_output,
    run_checkov_scan_impl,
)
from awslabs.terraform_mcp_server.models.models import CheckovScanRequest
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.asyncio


def test_clean_output_text_function():
    """Test the _clean_output_text function directly."""
    # Test with ANSI escape sequences
    ansi_text = '\x1b[31mError\x1b[0m: Something went wrong'
    cleaned_text = _clean_output_text(ansi_text)
    assert cleaned_text == 'Error: Something went wrong'

    # Test with control characters
    control_text = 'Line 1\x0bLine 2\x0cLine 3'
    cleaned_text = _clean_output_text(control_text)
    assert cleaned_text == 'Line 1Line 2Line 3'

    # Test with HTML entities
    html_text = 'This -&gt; that &lt;tag&gt; &amp; more'
    cleaned_text = _clean_output_text(html_text)
    assert cleaned_text == 'This -> that <tag> & more'

    # Test with Unicode box-drawing characters
    unicode_text = '┌───┐\n│ABC│\n└───┘'
    cleaned_text = _clean_output_text(unicode_text)
    assert 'ABC' in cleaned_text
    # Check that box-drawing characters are replaced with ASCII equivalents
    assert '+' in cleaned_text  # ┌ and ┘ should be replaced with +
    assert '|' in cleaned_text  # │ should be replaced with |
    assert '-' in cleaned_text  # ─ should be replaced with -

    # Test with None input - should handle it gracefully
    # Since the function expects a string, we'll test with empty string instead
    assert _clean_output_text('') == ''

    # Test with empty string
    assert _clean_output_text('') == ''


@pytest.mark.asyncio
async def test_parse_checkov_json_output_valid():
    """Test parsing valid Checkov JSON output."""
    # Create a valid JSON output
    json_output = {
        'results': {
            'failed_checks': [
                {
                    'check_id': 'CKV_AWS_1',
                    'check_name': 'Ensure S3 bucket has encryption enabled',
                    'check_type': 'terraform',
                    'file_path': '/path/to/main.tf',
                    'file_line_range': [1, 10],
                    'resource': 'aws_s3_bucket.my_bucket',
                    'guideline': 'https://docs.bridgecrew.io/docs/s3-encryption',
                    'severity': 'HIGH',
                },
                {
                    'check_id': 'CKV_AWS_2',
                    'check_name': 'Ensure S3 bucket has versioning enabled',
                    'check_type': 'terraform',
                    'file_path': '/path/to/main.tf',
                    'file_line_range': [1, 10],
                    'resource': 'aws_s3_bucket.my_bucket',
                    'guideline': None,
                    'severity': None,  # Test with None severity
                },
            ]
        },
        'summary': {
            'passed': 1,
            'failed': 2,
            'skipped': 0,
            'parsing_errors': 0,
            'resource_count': 3,
        },
    }

    # Parse the JSON output
    vulnerabilities, summary = _parse_checkov_json_output(json.dumps(json_output))

    # Check the results
    assert len(vulnerabilities) == 2
    assert vulnerabilities[0].id == 'CKV_AWS_1'
    assert vulnerabilities[0].description == 'Ensure S3 bucket has encryption enabled'
    assert vulnerabilities[0].severity == 'HIGH'
    assert vulnerabilities[0].guideline == 'https://docs.bridgecrew.io/docs/s3-encryption'

    assert vulnerabilities[1].id == 'CKV_AWS_2'
    assert vulnerabilities[1].description == 'Ensure S3 bucket has versioning enabled'
    assert vulnerabilities[1].severity == 'MEDIUM'  # Default value
    assert vulnerabilities[1].guideline is None

    assert summary['passed'] == 1
    assert summary['failed'] == 2
    assert summary['skipped'] == 0


@pytest.mark.asyncio
async def test_parse_checkov_json_output_invalid():
    """Test parsing invalid Checkov JSON output."""
    # Test with invalid JSON
    vulnerabilities, summary = _parse_checkov_json_output('Invalid JSON')
    assert len(vulnerabilities) == 0
    assert 'error' in summary

    # Test with valid JSON but missing required fields
    valid_but_incomplete = json.dumps({'results': {}})
    vulnerabilities, summary = _parse_checkov_json_output(valid_but_incomplete)
    assert len(vulnerabilities) == 0

    # Test with valid JSON but empty failed_checks
    valid_but_empty = json.dumps(
        {'results': {'failed_checks': []}, 'summary': {'passed': 0, 'failed': 0}}
    )
    vulnerabilities, summary = _parse_checkov_json_output(valid_but_empty)
    assert len(vulnerabilities) == 0
    assert summary['passed'] == 0
    assert summary['failed'] == 0


@pytest.mark.asyncio
async def test_run_checkov_scan_with_absolute_path(temp_terraform_dir):
    """Test running Checkov scan with an absolute path."""
    # Create the request with an absolute path and all required parameters
    absolute_path = os.path.abspath(temp_terraform_dir)
    request = CheckovScanRequest(
        working_directory=absolute_path,
        framework='terraform',
        output_format='json',
        check_ids=None,
        skip_check_ids=None,
    )

    # Create a mock subprocess.run result
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps(
        {'results': {'failed_checks': []}, 'summary': {'passed': 5, 'failed': 0, 'skipped': 0}}
    )
    mock_result.stderr = ''

    # Mock subprocess.run and _ensure_checkov_installed
    with patch('subprocess.run', return_value=mock_result):
        with patch(
            'awslabs.terraform_mcp_server.impl.tools.run_checkov_scan._ensure_checkov_installed',
            return_value=True,
        ):
            # Call the function
            result = await run_checkov_scan_impl(request)

            # Check the result
            assert result.status == 'success'
            assert result.working_directory == absolute_path
            assert result.summary['passed'] == 5
            assert result.summary['failed'] == 0


@pytest.mark.asyncio
async def test_run_checkov_scan_with_relative_path(temp_terraform_dir):
    """Test running Checkov scan with a relative path."""
    # Create a relative path (just the directory name)
    relative_path = os.path.basename(temp_terraform_dir)

    # Create the request with a relative path and all required parameters
    request = CheckovScanRequest(
        working_directory=relative_path,
        framework='terraform',
        output_format='json',
        check_ids=None,
        skip_check_ids=None,
    )

    # Create a mock subprocess.run result
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps(
        {'results': {'failed_checks': []}, 'summary': {'passed': 3, 'failed': 0, 'skipped': 0}}
    )
    mock_result.stderr = ''

    # Mock subprocess.run, _ensure_checkov_installed, and os.path.isabs
    with patch('subprocess.run', return_value=mock_result):
        with patch(
            'awslabs.terraform_mcp_server.impl.tools.run_checkov_scan._ensure_checkov_installed',
            return_value=True,
        ):
            with patch('os.path.isabs', return_value=False):
                with patch('os.getcwd', return_value='/fake/cwd'):
                    with patch('os.path.abspath', return_value='/fake/absolute/path'):
                        # Call the function
                        result = await run_checkov_scan_impl(request)

                        # Check the result
                        assert result.status == 'success'
                        assert result.working_directory == relative_path
                        assert result.summary['passed'] == 3


@pytest.mark.asyncio
async def test_run_checkov_scan_with_skip_check_ids_dangerous_pattern(temp_terraform_dir):
    """Test running Checkov scan with dangerous patterns in skip_check_ids."""
    # Create the request with dangerous patterns in skip_check_ids and all required parameters
    request = CheckovScanRequest(
        working_directory=temp_terraform_dir,
        framework='terraform',
        output_format='json',
        check_ids=None,
        skip_check_ids=['CKV_AWS_1; rm -rf /'],  # Dangerous pattern
    )

    # Call the function
    result = await run_checkov_scan_impl(request)

    # Check the result
    assert result.status == 'error'
    assert result.error_message is not None
    assert 'Security violation' in result.error_message
    assert 'Potentially dangerous pattern' in result.error_message


@pytest.mark.asyncio
async def test_run_checkov_scan_cli_output_parsing(temp_terraform_dir):
    """Test running Checkov scan with CLI output format and parsing the results."""
    # Create the request with all required parameters
    request = CheckovScanRequest(
        working_directory=temp_terraform_dir,
        framework='terraform',
        output_format='cli',
        check_ids=None,
        skip_check_ids=None,
    )

    # Create a mock subprocess.run result with CLI output
    mock_result = MagicMock()
    mock_result.returncode = 1  # Vulnerabilities found

    # Create CLI output with multiple checks
    cli_output = f"""
    Check: CKV_AWS_1: "Ensure S3 bucket has encryption enabled"
    FAILED for resource: aws_s3_bucket.my_bucket
    File: {temp_terraform_dir}/main.tf:5

    Check: CKV_AWS_2: "Ensure S3 bucket has versioning enabled"
    FAILED for resource: aws_s3_bucket.my_bucket
    File: {temp_terraform_dir}/main.tf:10

    Check: CKV_AWS_3: "Ensure S3 bucket has logging enabled"
    FAILED for resource: aws_s3_bucket.my_bucket
    File: {temp_terraform_dir}/main.tf:15

    Passed checks: 2, Failed checks: 3, Skipped checks: 1
    """

    mock_result.stdout = cli_output
    mock_result.stderr = ''

    # Mock subprocess.run and _ensure_checkov_installed
    with patch('subprocess.run', return_value=mock_result):
        with patch(
            'awslabs.terraform_mcp_server.impl.tools.run_checkov_scan._ensure_checkov_installed',
            return_value=True,
        ):
            # Call the function
            result = await run_checkov_scan_impl(request)

            # Check the result
            assert result.status == 'success'
            assert result.return_code == 1
            assert len(result.vulnerabilities) == 3
            assert result.summary['passed'] == 2
            assert result.summary['failed'] == 3
            assert result.summary['skipped'] == 1


@pytest.mark.asyncio
async def test_run_checkov_scan_with_return_code_2(temp_terraform_dir):
    """Test running Checkov scan with return code 2 (error)."""
    # Create the request with all required parameters
    request = CheckovScanRequest(
        working_directory=temp_terraform_dir,
        framework='terraform',
        output_format='json',
        check_ids=None,
        skip_check_ids=None,
    )

    # Create a mock subprocess.run result with error
    mock_result = MagicMock()
    mock_result.returncode = 2  # Error code
    mock_result.stdout = 'Error running checkov'
    mock_result.stderr = 'Failed to parse Terraform files'

    # Mock subprocess.run and _ensure_checkov_installed
    with patch('subprocess.run', return_value=mock_result):
        with patch(
            'awslabs.terraform_mcp_server.impl.tools.run_checkov_scan._ensure_checkov_installed',
            return_value=True,
        ):
            # Call the function
            result = await run_checkov_scan_impl(request)

            # Check the result
            assert result.status == 'error'
            assert result.return_code == 2
            assert len(result.vulnerabilities) == 0


@pytest.mark.asyncio
async def test_run_checkov_scan_exception_handling(temp_terraform_dir):
    """Test running Checkov scan with exception handling."""
    # Create the request with all required parameters
    request = CheckovScanRequest(
        working_directory=temp_terraform_dir,
        framework='terraform',
        output_format='json',
        check_ids=None,
        skip_check_ids=None,
    )

    # Mock subprocess.run to raise an exception
    with patch('subprocess.run', side_effect=Exception('Command execution failed')):
        with patch(
            'awslabs.terraform_mcp_server.impl.tools.run_checkov_scan._ensure_checkov_installed',
            return_value=True,
        ):
            # Call the function
            result = await run_checkov_scan_impl(request)

            # Check the result
            assert result.status == 'error'
            assert result.error_message == 'Command execution failed'
            assert result.working_directory == temp_terraform_dir
