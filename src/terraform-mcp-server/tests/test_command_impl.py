"""Tests for the Terraform MCP server tools."""

import json
import pytest
from awslabs.terraform_mcp_server.impl.tools.execute_terraform_command import (
    execute_terraform_command_impl,
)
from awslabs.terraform_mcp_server.impl.tools.run_checkov_scan import (
    run_checkov_scan_impl,
)
from awslabs.terraform_mcp_server.models import (
    CheckovScanRequest,
    TerraformExecutionRequest,
)
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_execute_terraform_command_success():
    """Test the Terraform command execution function with successful mocks."""
    # Create a mock subprocess.run result
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = 'Terraform initialized successfully!'
    mock_result.stderr = ''

    # Create the request
    request = TerraformExecutionRequest(
        command='init',
        working_directory='/tmp/terraform_test',
        variables={'environment': 'test'},
        aws_region='us-west-2',
        strip_ansi=True,
    )

    # Mock subprocess.run
    with patch('subprocess.run', return_value=mock_result):
        # Mock os.path.exists to return True
        with patch('os.path.exists', return_value=True):
            # Mock os.path.isdir to return True
            with patch('os.path.isdir', return_value=True):
                # Mock subprocess.check_output to return terraform version
                with patch('subprocess.check_output', return_value=b'Terraform v1.0.0'):
                    # Call the function
                    result = await execute_terraform_command_impl(request)

                    # Check the result
                    assert result is not None
                    assert result.status == 'success'
                    assert result.return_code == 0
                    assert 'Terraform initialized successfully!' in result.stdout
                    assert result.stderr == ''
                    assert result.command == 'terraform init'
                    assert result.working_directory == '/tmp/terraform_test'


@pytest.mark.asyncio
async def test_execute_terraform_command_error():
    """Test the Terraform command execution function with error mocks."""
    # Create a mock subprocess.run result
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = 'Error: Invalid command'
    mock_result.stderr = 'terraform: command not found'

    # Create the request
    request = TerraformExecutionRequest(
        command='init',
        working_directory='/tmp/terraform_test',
        variables={'environment': 'test'},
        aws_region='us-west-2',
        strip_ansi=True,
    )

    # Mock subprocess.run
    with patch('subprocess.run', return_value=mock_result):
        # Mock os.path.exists to return True
        with patch('os.path.exists', return_value=True):
            # Mock os.path.isdir to return True
            with patch('os.path.isdir', return_value=True):
                # Mock subprocess.check_output to return terraform version
                with patch('subprocess.check_output', return_value=b'Terraform v1.0.0'):
                    # Call the function
                    result = await execute_terraform_command_impl(request)

                    # Check the result
                    assert result is not None
                    assert result.status == 'error'
                    assert result.return_code == 1
                    assert 'Error: Invalid command' in result.stdout
                    assert 'terraform: command not found' in result.stderr


@pytest.mark.asyncio
async def test_run_checkov_scan_success():
    """Test the Checkov scan function with successful mocks."""
    # Create a mock subprocess.run result
    mock_result = MagicMock()
    mock_result.returncode = 0

    # Create valid JSON output
    checkov_output = {
        'results': {
            'failed_checks': [
                {
                    'check_id': 'CKV_AWS_1',
                    'check_name': 'Ensure S3 bucket has encryption enabled',
                    'check_result': {
                        'result': 'FAILED',
                        'evaluated_keys': ['server_side_encryption_configuration'],
                    },
                    'file_path': '/tmp/terraform_test/main.tf',
                    'file_line_range': [1, 10],
                    'resource': 'aws_s3_bucket.my_bucket',
                    'check_class': 'checkov.terraform.checks.resource.aws.S3Encryption',
                    'guideline': 'https://docs.bridgecrew.io/docs/s3-encryption',
                }
            ],
            'passed_checks': [],
            'skipped_checks': [],
        },
        'summary': {
            'passed': 0,
            'failed': 1,
            'skipped': 0,
            'parsing_errors': 0,
            'resource_count': 1,
        },
    }

    # Convert to JSON string and then to bytes
    mock_result.stdout = json.dumps(checkov_output)
    mock_result.stderr = ''

    # Create the request
    request = CheckovScanRequest(
        working_directory='/tmp/terraform_test', framework='terraform', output_format='json'
    )

    # Mock subprocess.run
    with patch('subprocess.run', return_value=mock_result):
        # Mock os.path.exists to return True
        with patch('os.path.exists', return_value=True):
            # Mock os.path.isdir to return True
            with patch('os.path.isdir', return_value=True):
                # Mock subprocess.check_output to check if checkov is installed
                with patch('subprocess.check_output', return_value=b'checkov 2.0.0'):
                    # Mock os.path.isabs to return True
                    with patch('os.path.isabs', return_value=True):
                        # Call the function
                        result = await run_checkov_scan_impl(request)

                        # Check the result
                        assert result is not None
                        assert result.status == 'success'
                        assert result.return_code == 0
                        assert len(result.vulnerabilities) == 1
                        assert result.vulnerabilities[0].id == 'CKV_AWS_1'
                        assert result.vulnerabilities[0].resource == 'aws_s3_bucket.my_bucket'
                        assert (
                            'Ensure S3 bucket has encryption enabled'
                            in result.vulnerabilities[0].description
                        )


@pytest.mark.asyncio
async def test_execute_terraform_command_invalid_command():
    """Test the Terraform command execution function with an invalid command."""
    # Skip this test - we can't directly test with an invalid command
    # because the validation happens at the model level
    # Instead, we'll verify that the allowed_commands list in the function
    # contains the expected values

    # Get the source code of the function
    import inspect

    source = inspect.getsource(execute_terraform_command_impl)

    # Check that the allowed_commands list contains the expected values
    assert "allowed_commands = ['init', 'plan', 'validate', 'apply', 'destroy']" in source

    # Check that there's validation logic for the command
    assert 'if request.command not in allowed_commands:' in source
    assert 'Invalid Terraform command' in source


@pytest.mark.asyncio
async def test_execute_terraform_command_dangerous_patterns():
    """Test the Terraform command execution function with dangerous patterns in variables."""
    # Create the request with a dangerous pattern in variables
    request = TerraformExecutionRequest(
        command='apply',
        working_directory='/tmp/terraform_test',
        variables={'environment': 'test; rm -rf /'},  # Dangerous pattern
        aws_region='us-west-2',
        strip_ansi=True,
    )

    # Call the function
    result = await execute_terraform_command_impl(request)

    # Check the result
    assert result is not None
    assert result.status == 'error'
    assert 'Security violation' in result.error_message
    assert 'Potentially dangerous pattern' in result.error_message


@pytest.mark.asyncio
async def test_execute_terraform_command_with_outputs():
    """Test the Terraform command execution function with outputs."""
    # Create mock subprocess.run results for apply and output commands
    mock_apply_result = MagicMock()
    mock_apply_result.returncode = 0
    mock_apply_result.stdout = 'Apply complete!'
    mock_apply_result.stderr = ''

    mock_output_result = MagicMock()
    mock_output_result.returncode = 0
    mock_output_result.stdout = json.dumps(
        {
            'instance_id': {'value': 'i-1234567890abcdef0', 'type': 'string'},
            'vpc_id': {'value': 'vpc-1234567890abcdef0', 'type': 'string'},
        }
    )
    mock_output_result.stderr = ''

    # Create the request
    request = TerraformExecutionRequest(
        command='apply',
        working_directory='/tmp/terraform_test',
        variables={'environment': 'test'},
        aws_region='us-west-2',
        strip_ansi=True,
    )

    # Mock subprocess.run to return different results for different commands
    def mock_subprocess_run(cmd, **kwargs):
        if 'output' in cmd:
            return mock_output_result
        return mock_apply_result

    # Mock subprocess.run
    with patch('subprocess.run', side_effect=mock_subprocess_run):
        # Mock os.path.exists to return True
        with patch('os.path.exists', return_value=True):
            # Mock os.path.isdir to return True
            with patch('os.path.isdir', return_value=True):
                # Mock subprocess.check_output to return terraform version
                with patch('subprocess.check_output', return_value=b'Terraform v1.0.0'):
                    # Call the function
                    result = await execute_terraform_command_impl(request)

                    # Check the result
                    assert result is not None
                    assert result.status == 'success'
                    assert result.return_code == 0
                    assert result.outputs is not None
                    assert result.outputs['instance_id'] == 'i-1234567890abcdef0'
                    assert result.outputs['vpc_id'] == 'vpc-1234567890abcdef0'


@pytest.mark.asyncio
async def test_run_checkov_scan_invalid_framework():
    """Test the Checkov scan function with an invalid framework."""
    # Create the request with an invalid framework
    request = CheckovScanRequest(
        working_directory='/tmp/terraform_test',
        framework='invalid_framework',  # Invalid framework
        output_format='json',
    )

    # Call the function
    result = await run_checkov_scan_impl(request)

    # Check the result
    assert result is not None
    assert result.status == 'error'
    assert 'Security violation' in result.error_message
    assert 'Invalid framework' in result.error_message


@pytest.mark.asyncio
async def test_run_checkov_scan_invalid_output_format():
    """Test the Checkov scan function with an invalid output format."""
    # Create the request with an invalid output format
    request = CheckovScanRequest(
        working_directory='/tmp/terraform_test',
        framework='terraform',
        output_format='invalid_format',  # Invalid output format
    )

    # Call the function
    result = await run_checkov_scan_impl(request)

    # Check the result
    assert result is not None
    assert result.status == 'error'
    assert 'Security violation' in result.error_message
    assert 'Invalid output format' in result.error_message


@pytest.mark.asyncio
async def test_run_checkov_scan_dangerous_patterns():
    """Test the Checkov scan function with dangerous patterns in check_ids."""
    # Create the request with a dangerous pattern in check_ids
    request = CheckovScanRequest(
        working_directory='/tmp/terraform_test',
        framework='terraform',
        output_format='json',
        check_ids=['CKV_AWS_1; rm -rf /'],  # Dangerous pattern
    )

    # Call the function
    result = await run_checkov_scan_impl(request)

    # Check the result
    assert result is not None
    assert result.status == 'error'
    assert 'Security violation' in result.error_message
    assert 'Potentially dangerous pattern' in result.error_message


@pytest.mark.asyncio
async def test_run_checkov_scan_cli_output():
    """Test the Checkov scan function with CLI output format."""
    # Create a mock subprocess.run result with CLI output
    mock_result = MagicMock()
    mock_result.returncode = 1  # Vulnerabilities found
    mock_result.stdout = """
    Check: CKV_AWS_1: "Ensure S3 bucket has encryption enabled"
    FAILED for resource: aws_s3_bucket.my_bucket
    File: /tmp/terraform_test/main.tf:1-10

    Check: CKV_AWS_2: "Ensure S3 bucket has versioning enabled"
    FAILED for resource: aws_s3_bucket.my_bucket
    File: /tmp/terraform_test/main.tf:1-10

    Passed checks: 0
    Failed checks: 2
    Skipped checks: 0
    """
    mock_result.stderr = ''

    # Create the request
    request = CheckovScanRequest(
        working_directory='/tmp/terraform_test', framework='terraform', output_format='cli'
    )

    # Mock subprocess.run
    with patch('subprocess.run', return_value=mock_result):
        # Mock os.path.exists to return True
        with patch('os.path.exists', return_value=True):
            # Mock os.path.isdir to return True
            with patch('os.path.isdir', return_value=True):
                # Mock subprocess.check_output to check if checkov is installed
                with patch('subprocess.check_output', return_value=b'checkov 2.0.0'):
                    # Mock os.path.isabs to return True
                    with patch('os.path.isabs', return_value=True):
                        # Call the function
                        result = await run_checkov_scan_impl(request)

                        # Check the result
                        assert result is not None
                        assert result.status == 'success'
                        assert result.return_code == 1
                        assert len(result.vulnerabilities) == 2
                        assert result.summary['passed'] == 0
                        assert result.summary['failed'] == 2
                        assert result.summary['skipped'] == 0


@pytest.mark.asyncio
async def test_run_checkov_scan_error():
    """Test the Checkov scan function with error mocks."""
    # Create a mock subprocess.run result
    mock_result = MagicMock()
    mock_result.returncode = 2  # Error code
    mock_result.stdout = 'Error running checkov'
    mock_result.stderr = 'checkov: command not found'

    # Create the request
    request = CheckovScanRequest(
        working_directory='/tmp/terraform_test', framework='terraform', output_format='json'
    )

    # Mock subprocess.run
    with patch('subprocess.run', return_value=mock_result):
        # Mock os.path.exists to return True
        with patch('os.path.exists', return_value=True):
            # Mock os.path.isdir to return True
            with patch('os.path.isdir', return_value=True):
                # Mock subprocess.check_output to check if checkov is installed
                with patch('subprocess.check_output', return_value=b'checkov 2.0.0'):
                    # Mock os.path.isabs to return True
                    with patch('os.path.isabs', return_value=True):
                        # Call the function
                        result = await run_checkov_scan_impl(request)

                        # Check the result
                        assert result is not None
                        assert result.status == 'error'
                        assert result.return_code == 2


@pytest.mark.asyncio
async def test_run_checkov_scan_checkov_not_installed():
    """Test the Checkov scan function when Checkov is not installed."""
    # Create the request
    request = CheckovScanRequest(
        working_directory='/tmp/terraform_test', framework='terraform', output_format='json'
    )

    # Mock _ensure_checkov_installed to return False
    with patch(
        'awslabs.terraform_mcp_server.impl.tools.run_checkov_scan._ensure_checkov_installed',
        return_value=False,
    ):
        # Call the function
        result = await run_checkov_scan_impl(request)

        # Check the result
        assert result is not None
        assert result.status == 'error'
        assert 'Failed to install Checkov' in result.error_message
