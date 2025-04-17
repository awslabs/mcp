"""Tests for the execute_terraform_command implementation."""

import json
import pytest
from awslabs.terraform_mcp_server.impl.tools.execute_terraform_command import (
    execute_terraform_command_impl,
)
from awslabs.terraform_mcp_server.models.models import TerraformExecutionRequest
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_clean_output_text_helper():
    """Test the clean_output_text helper function indirectly."""
    # Create a mock request with all required parameters
    request = TerraformExecutionRequest(
        command='init',
        working_directory='/tmp',
        variables={},
        aws_region='us-west-2',
        strip_ansi=True,
    )

    # Create a mock subprocess result with ANSI and special characters
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = '\x1b[31mError\x1b[0m: Something went wrong\n┌───┐\n│ABC│\n└───┘'
    mock_result.stderr = 'This -&gt; that &lt;tag&gt; &amp; more'

    # Mock subprocess.run
    with patch('subprocess.run', return_value=mock_result):
        # Call the function
        result = await execute_terraform_command_impl(request)

        # The function should have cleaned the output
        # Check that the output is not None before asserting
        assert result.stdout is not None
        assert '\x1b[31m' not in result.stdout
        assert 'Error: Something went wrong' in result.stdout
        assert 'ABC' in result.stdout
        assert result.stderr is not None
        assert 'This -> that <tag> & more' in result.stderr


@pytest.mark.asyncio
async def test_execute_terraform_command_with_region(temp_terraform_dir):
    """Test the Terraform command execution with AWS region setting."""
    # Create a mock subprocess.run result
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = 'Terraform initialized in us-east-1 region'
    mock_result.stderr = ''

    # Create the request with a specific AWS region and all required parameters
    request = TerraformExecutionRequest(
        command='init',
        working_directory=temp_terraform_dir,
        variables={},
        aws_region='us-east-1',
        strip_ansi=True,
    )

    # Mock subprocess.run
    with patch('subprocess.run', return_value=mock_result) as mock_run:
        # Call the function
        result = await execute_terraform_command_impl(request)

        # Check that the environment was set correctly
        env_arg = mock_run.call_args[1]['env']
        assert 'AWS_REGION' in env_arg
        assert env_arg['AWS_REGION'] == 'us-east-1'

        # Check the result
        assert result.status == 'success'
        assert result.stdout == 'Terraform initialized in us-east-1 region'


@pytest.mark.asyncio
async def test_execute_terraform_command_exception_handling(temp_terraform_dir):
    """Test the Terraform command execution with exception handling."""
    # Create the request with all required parameters
    request = TerraformExecutionRequest(
        command='init',
        working_directory=temp_terraform_dir,
        variables={},
        aws_region=None,
        strip_ansi=True,
    )

    # Mock subprocess.run to raise an exception
    with patch('subprocess.run', side_effect=Exception('Command execution failed')):
        # Call the function
        result = await execute_terraform_command_impl(request)

        # Check the result
        assert result.status == 'error'
        assert result.error_message == 'Command execution failed'
        assert result.working_directory == temp_terraform_dir


@pytest.mark.asyncio
async def test_execute_terraform_command_output_error_handling(temp_terraform_dir):
    """Test the Terraform command execution with output error handling."""
    # Create mock subprocess.run results for apply and output commands
    mock_apply_result = MagicMock()
    mock_apply_result.returncode = 0
    mock_apply_result.stdout = 'Apply complete!'
    mock_apply_result.stderr = ''

    # Mock the output command to raise an exception
    def mock_subprocess_run(cmd, **kwargs):
        if 'output' in cmd:
            raise Exception('Output command failed')
        return mock_apply_result

    # Create the request with all required parameters
    request = TerraformExecutionRequest(
        command='apply',
        working_directory=temp_terraform_dir,
        variables={},
        aws_region=None,
        strip_ansi=True,
    )

    # Mock subprocess.run
    with patch('subprocess.run', side_effect=mock_subprocess_run):
        # Call the function
        result = await execute_terraform_command_impl(request)

        # Check the result - should still be success since apply worked
        assert result.status == 'success'
        assert result.outputs is None


@pytest.mark.asyncio
async def test_execute_terraform_command_output_json_error(temp_terraform_dir):
    """Test the Terraform command execution with JSON parsing error in outputs."""
    # Create mock subprocess.run results for apply and output commands
    mock_apply_result = MagicMock()
    mock_apply_result.returncode = 0
    mock_apply_result.stdout = 'Apply complete!'
    mock_apply_result.stderr = ''

    mock_output_result = MagicMock()
    mock_output_result.returncode = 0
    mock_output_result.stdout = 'Invalid JSON'  # Not valid JSON
    mock_output_result.stderr = ''

    # Mock subprocess.run to return different results for different commands
    def mock_subprocess_run(cmd, **kwargs):
        if 'output' in cmd:
            return mock_output_result
        return mock_apply_result

    # Create the request with all required parameters
    request = TerraformExecutionRequest(
        command='apply',
        working_directory=temp_terraform_dir,
        variables={},
        aws_region=None,
        strip_ansi=True,
    )

    # Mock subprocess.run
    with patch('subprocess.run', side_effect=mock_subprocess_run):
        # Call the function
        result = await execute_terraform_command_impl(request)

        # Check the result - should still be success since apply worked
        assert result.status == 'success'
        assert result.outputs is None


@pytest.mark.asyncio
async def test_execute_terraform_command_complex_outputs(temp_terraform_dir):
    """Test the Terraform command execution with complex output structures."""
    # Create mock subprocess.run results for apply and output commands
    mock_apply_result = MagicMock()
    mock_apply_result.returncode = 0
    mock_apply_result.stdout = 'Apply complete!'
    mock_apply_result.stderr = ''

    # Create complex output structure with nested values
    complex_outputs = {
        'instance_ids': {'value': ['i-1234', 'i-5678'], 'type': ['list', 'string']},
        'vpc_config': {
            'value': {'vpc_id': 'vpc-1234', 'subnet_ids': ['subnet-1', 'subnet-2']},
            'type': ['object', {'vpc_id': 'string', 'subnet_ids': ['list', 'string']}],
        },
        'simple_output': 'direct_value',  # Not in the standard format
    }

    mock_output_result = MagicMock()
    mock_output_result.returncode = 0
    mock_output_result.stdout = json.dumps(complex_outputs)
    mock_output_result.stderr = ''

    # Mock subprocess.run to return different results for different commands
    def mock_subprocess_run(cmd, **kwargs):
        if 'output' in cmd:
            return mock_output_result
        return mock_apply_result

    # Create the request with all required parameters
    request = TerraformExecutionRequest(
        command='apply',
        working_directory=temp_terraform_dir,
        variables={},
        aws_region=None,
        strip_ansi=True,
    )

    # Mock subprocess.run
    with patch('subprocess.run', side_effect=mock_subprocess_run):
        # Call the function
        result = await execute_terraform_command_impl(request)

        # Check the result
        assert result.status == 'success'
        assert result.outputs is not None
        assert result.outputs['instance_ids'] == ['i-1234', 'i-5678']
        assert result.outputs['vpc_config']['vpc_id'] == 'vpc-1234'
        assert result.outputs['vpc_config']['subnet_ids'] == ['subnet-1', 'subnet-2']
        assert result.outputs['simple_output'] == 'direct_value'
