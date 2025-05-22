"""Tests for the execute_terragrunt_command implementation."""

import json
import pytest
from awslabs.terraform_mcp_server.impl.tools.execute_terragrunt_command import (
    execute_terragrunt_command_impl,
)
from awslabs.terraform_mcp_server.models import (
    TerragruntExecutionRequest,
)
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_execute_terragrunt_command_success(temp_terraform_dir):
    """Test the Terragrunt command execution function with successful mocks."""
    # Create a mock subprocess.run result
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = 'Terragrunt initialized successfully!'
    mock_result.stderr = ''

    # Create the request
    request = TerragruntExecutionRequest(
        command='init',
        working_directory=temp_terraform_dir,
        variables={'environment': 'test'},
        aws_region='us-west-2',
        strip_ansi=True,
        include_dirs=None,
        exclude_dirs=None,
        run_all=False,
        terragrunt_config=None,
    )

    # Mock subprocess.run
    with patch('subprocess.run', return_value=mock_result):
        # Call the function
        result = await execute_terragrunt_command_impl(request)

    # Check the result
    assert result is not None
    assert result.status == 'success'
    assert result.return_code == 0
    assert result.stdout is not None and 'Terragrunt initialized successfully!' in result.stdout
    assert result.stderr == ''
    assert result.command == 'terragrunt init'
    assert result.working_directory == temp_terraform_dir


@pytest.mark.asyncio
async def test_execute_terragrunt_command_error(temp_terraform_dir):
    """Test the Terragrunt command execution function with error mocks."""
    # Create a mock subprocess.run result
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = 'Error running terragrunt'
    mock_result.stderr = 'Failed to initialize terragrunt'

    # Create the request
    request = TerragruntExecutionRequest(
        command='init',
        working_directory=temp_terraform_dir,
        variables={'environment': 'test'},
        aws_region='us-west-2',
        strip_ansi=True,
        include_dirs=None,
        exclude_dirs=None,
        run_all=False,
        terragrunt_config=None,
    )

    # Mock subprocess.run
    with patch('subprocess.run', return_value=mock_result):
        # Call the function
        result = await execute_terragrunt_command_impl(request)

    # Check the result
    assert result is not None
    assert result.status == 'error'
    assert result.return_code == 1
    assert result.stdout is not None and 'Error running terragrunt' in result.stdout
    assert 'Failed to initialize terragrunt' in result.stderr


@pytest.mark.asyncio
async def test_clean_output_text_helper(temp_terraform_dir):
    """Test the clean_output_text helper function indirectly."""
    # Create a mock request with all required parameters
    request = TerragruntExecutionRequest(
        command='init',
        working_directory=temp_terraform_dir,
        variables={},
        aws_region='us-west-2',
        strip_ansi=True,
        include_dirs=None,
        exclude_dirs=None,
        run_all=False,
        terragrunt_config=None,
    )

    # Create a mock subprocess result with ANSI and special characters
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = '\x1b[31mError\x1b[0m: Something went wrong\n┌───┐\n│ABC│\n└───┘'
    mock_result.stderr = 'This -&gt; that &lt;tag&gt; &amp; more'

    # Mock subprocess.run
    with patch('subprocess.run', return_value=mock_result):
        # Call the function
        result = await execute_terragrunt_command_impl(request)

    # The function should have cleaned the output
    # Check that the output is not None before asserting
    assert result.stdout is not None
    assert '\x1b[31m' not in result.stdout
    assert 'Error: Something went wrong' in result.stdout
    assert 'ABC' in result.stdout
    assert result.stderr is not None
    assert 'This -> that <tag> & more' in result.stderr


@pytest.mark.asyncio
async def test_execute_terragrunt_command_with_region(temp_terraform_dir):
    """Test the Terragrunt command execution with AWS region setting."""
    # Create a mock subprocess.run result
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = 'Terragrunt initialized in us-east-1 region'
    mock_result.stderr = ''

    # Create the request with a specific AWS region
    request = TerragruntExecutionRequest(
        command='init',
        working_directory=temp_terraform_dir,
        variables={},
        aws_region='us-east-1',
        strip_ansi=True,
        include_dirs=None,
        exclude_dirs=None,
        run_all=False,
        terragrunt_config=None,
    )

    # Mock subprocess.run
    with patch('subprocess.run', return_value=mock_result) as mock_run:
        # Call the function
        result = await execute_terragrunt_command_impl(request)

        # Check that the environment was set correctly
        env_arg = mock_run.call_args[1]['env']
        assert 'AWS_REGION' in env_arg
        assert env_arg['AWS_REGION'] == 'us-east-1'

        # Check the result
        assert result.status == 'success'
        assert result.stdout == 'Terragrunt initialized in us-east-1 region'


@pytest.mark.asyncio
async def test_execute_terragrunt_command_dangerous_patterns(temp_terraform_dir):
    """Test the Terragrunt command execution function with dangerous patterns in variables."""
    # Create the request with a dangerous pattern in variables
    request = TerragruntExecutionRequest(
        command='apply',
        working_directory=temp_terraform_dir,
        variables={'environment': 'test; rm -rf /'},  # Dangerous pattern
        aws_region='us-west-2',
        strip_ansi=True,
        include_dirs=None,
        exclude_dirs=None,
        run_all=False,
        terragrunt_config=None,
    )

    # Call the function directly (no need for mocking as it should fail early)
    result = await execute_terragrunt_command_impl(request)

    # Check the result
    assert result is not None
    assert result.status == 'error'
    assert result.error_message is not None and 'Security violation' in result.error_message
    assert 'Potentially dangerous pattern' in result.error_message


@pytest.mark.asyncio
async def test_execute_terragrunt_command_with_outputs(temp_terraform_dir):
    """Test the Terragrunt command execution function with outputs."""
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
    request = TerragruntExecutionRequest(
        command='apply',
        working_directory=temp_terraform_dir,
        variables={'environment': 'test'},
        aws_region='us-west-2',
        strip_ansi=True,
        include_dirs=None,
        exclude_dirs=None,
        run_all=False,
        terragrunt_config=None,
    )

    # Mock subprocess.run to return different results for different commands
    def mock_subprocess_run(cmd, **kwargs):
        if 'output' in cmd:
            return mock_output_result
        return mock_apply_result

    # Mock subprocess.run
    with patch('subprocess.run', side_effect=mock_subprocess_run):
        # Call the function
        result = await execute_terragrunt_command_impl(request)

        # Check the result
        assert result is not None
        assert result.status == 'success'
        assert result.return_code == 0
        assert result.outputs is not None
        assert result.outputs['instance_id'] == 'i-1234567890abcdef0'
        assert result.outputs['vpc_id'] == 'vpc-1234567890abcdef0'


@pytest.mark.asyncio
async def test_execute_terragrunt_command_complex_outputs(temp_terraform_dir):
    """Test the Terragrunt command execution with complex output structures."""
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

    # Create the request
    request = TerragruntExecutionRequest(
        command='apply',
        working_directory=temp_terraform_dir,
        variables={},
        aws_region=None,
        strip_ansi=True,
        include_dirs=None,
        exclude_dirs=None,
        run_all=False,
        terragrunt_config=None,
    )

    # Mock subprocess.run
    with patch('subprocess.run', side_effect=mock_subprocess_run):
        # Call the function
        result = await execute_terragrunt_command_impl(request)

        # Check the result
        assert result.status == 'success'
        assert result.outputs is not None
        assert result.outputs['instance_ids'] == ['i-1234', 'i-5678']
        assert result.outputs['vpc_config']['vpc_id'] == 'vpc-1234'
        assert result.outputs['vpc_config']['subnet_ids'] == ['subnet-1', 'subnet-2']
        assert result.outputs['simple_output'] == 'direct_value'


@pytest.mark.asyncio
async def test_execute_terragrunt_command_output_error_handling(temp_terraform_dir):
    """Test the Terragrunt command execution with output error handling."""
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

    # Create the request
    request = TerragruntExecutionRequest(
        command='apply',
        working_directory=temp_terraform_dir,
        variables={},
        aws_region=None,
        strip_ansi=True,
        include_dirs=None,
        exclude_dirs=None,
        run_all=False,
        terragrunt_config=None,
    )

    # Mock subprocess.run
    with patch('subprocess.run', side_effect=mock_subprocess_run):
        # Call the function
        result = await execute_terragrunt_command_impl(request)

        # Check the result - should still be success since apply worked
        assert result.status == 'success'
        assert result.outputs is None


@pytest.mark.asyncio
async def test_execute_terragrunt_command_run_all(temp_terraform_dir):
    """Test the Terragrunt run-all command execution."""
    # Create mock results for the run-all command and the output command
    mock_run_all_result = MagicMock()
    mock_run_all_result.returncode = 0
    mock_run_all_result.stdout = """
    Terragrunt will run the following modules:
    Module at "/path/to/module1"
    Module at "/path/to/module2"
    Module at "/path/to/module3"

    Are you sure you want to run 'terragrunt apply' in each module? (y/n)
    Running 'terragrunt apply' in Module at "/path/to/module1"...
    Running 'terragrunt apply' in Module at "/path/to/module2"...
    Running 'terragrunt apply' in Module at "/path/to/module3"...
    """
    mock_run_all_result.stderr = ''

    # Create a mock for the output command too
    mock_output_result = MagicMock()
    mock_output_result.returncode = 0
    mock_output_result.stdout = '{}'  # Empty JSON output
    mock_output_result.stderr = ''

    # Create the request
    request = TerragruntExecutionRequest(
        command='run-all',
        working_directory=temp_terraform_dir,
        variables={'environment': 'test'},
        aws_region='us-west-2',
        strip_ansi=True,
        include_dirs=['/path/to/module1', '/path/to/module2'],
        exclude_dirs=['/path/to/excluded'],
        run_all=True,
        terragrunt_config=None,
    )

    # Define a side_effect function that returns different mocks for different commands
    def mock_subprocess_run(cmd, **kwargs):
        if len(cmd) > 1 and cmd[1] == 'output':
            return mock_output_result
        return mock_run_all_result

    # Mock subprocess.run with our side_effect function
    with patch('subprocess.run', side_effect=mock_subprocess_run) as mock_run:
        # Call the function
        result = await execute_terragrunt_command_impl(request)

        # Get the first call args (the run-all command)
        first_call_args = mock_run.call_args_list[0][0][0]

        # Check that the command was constructed correctly
        assert 'terragrunt' in first_call_args
        assert 'run-all' in first_call_args
        assert 'apply' in first_call_args
        assert '-auto-approve' in first_call_args
        assert any('--queue-include-dir=/path/to/module1' in arg for arg in first_call_args)
        assert any('--queue-include-dir=/path/to/module2' in arg for arg in first_call_args)
        assert any('--queue-exclude-dir=/path/to/excluded' in arg for arg in first_call_args)

        # Check the result
        assert result.status == 'success'
        assert result.affected_dirs is not None


@pytest.mark.asyncio
async def test_execute_terragrunt_command_invalid_command(temp_terraform_dir):
    """Test the Terragrunt command execution with an invalid command."""
    # Create the request with a valid command first
    request = TerragruntExecutionRequest(
        command='init',  # Valid command to pass validation
        working_directory=temp_terraform_dir,
        variables={},
        aws_region=None,
        strip_ansi=True,
        include_dirs=None,
        exclude_dirs=None,
        run_all=False,
        terragrunt_config=None,
    )

    # Then modify the command directly to bypass validation
    request.command = 'invalid-command'  # type: ignore

    # Now call the function with our invalid command
    result = await execute_terragrunt_command_impl(request)

    # Check that the function handled the invalid command properly
    assert result.status == 'error'
    assert result.error_message is not None
    assert 'Invalid Terragrunt command' in result.error_message
    assert 'Allowed commands are:' in result.error_message


@pytest.mark.asyncio
async def test_execute_terragrunt_command_with_exception(temp_terraform_dir):
    """Test the Terragrunt command execution when an exception occurs."""
    # Create the request
    request = TerragruntExecutionRequest(
        command='init',
        working_directory=temp_terraform_dir,
        variables={},
        aws_region=None,
        strip_ansi=True,
        include_dirs=None,
        exclude_dirs=None,
        run_all=False,
        terragrunt_config=None,
    )

    # Mock subprocess.run to raise an exception
    with patch('subprocess.run', side_effect=Exception('Command execution failed')):
        # Call the function
        result = await execute_terragrunt_command_impl(request)

        # Check the result
        assert result.status == 'error'
        assert result.error_message == 'Command execution failed'


@pytest.mark.asyncio
async def test_execute_terragrunt_command_with_custom_config(temp_terraform_dir):
    """Test the Terragrunt command execution with a custom config file."""
    # Create a mock subprocess.run result
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = 'Terragrunt initialized with custom config!'
    mock_result.stderr = ''

    # Custom config path
    custom_config = 'custom-terragrunt.hcl'

    # Create the request with a custom config file
    request = TerragruntExecutionRequest(
        command='init',
        working_directory=temp_terraform_dir,
        variables={'environment': 'test'},
        aws_region='us-west-2',
        strip_ansi=True,
        include_dirs=None,
        exclude_dirs=None,
        run_all=False,
        terragrunt_config=custom_config,
    )

    # Mock subprocess.run
    with patch('subprocess.run', return_value=mock_result) as mock_run:
        # Call the function
        result = await execute_terragrunt_command_impl(request)

        # Check the result
        assert result.status == 'success'
        assert result.stdout == 'Terragrunt initialized with custom config!'

        # Verify the command included the custom config flag
        cmd_args = mock_run.call_args[0][0]
        assert f'--terragrunt-config={custom_config}' in cmd_args
