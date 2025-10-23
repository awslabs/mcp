import pytest
import requests
from awslabs.aws_api_mcp_server.core.common.errors import AwsApiMcpError
from awslabs.aws_api_mcp_server.core.common.models import (
    AwsApiMcpServerErrorResponse,
    AwsCliAliasResponse,
    Consent,
    Credentials,
    InterpretationResponse,
    ProgramInterpretationResponse,
)
from awslabs.aws_api_mcp_server.server import call_aws, call_aws_helper, main, suggest_aws_commands
from botocore.exceptions import NoCredentialsError
from fastmcp.server.elicitation import AcceptedElicitation
from tests.fixtures import TEST_CREDENTIALS, DummyCtx
from unittest.mock import AsyncMock, MagicMock, patch


@patch('awslabs.aws_api_mcp_server.server.get_read_only_operations')
@patch('awslabs.aws_api_mcp_server.server.server')
def test_main_read_operations_index_load_failure(mock_server, mock_get_read_ops):
    """Test main function when read operations index loading fails."""
    mock_get_read_ops.side_effect = Exception('Failed to load operations')

    with patch('awslabs.aws_api_mcp_server.server.WORKING_DIRECTORY', '/tmp/test'):
        with patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', 'us-east-1'):
            with patch('awslabs.aws_api_mcp_server.server.validate_aws_region'):
                # Should not raise exception, just log warning
                main()
                mock_server.run.assert_called_once()


@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_api_mcp_server.server.interpret_command')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.core.aws.service.is_operation_read_only')
async def test_call_aws_success(
    mock_is_operation_read_only,
    mock_translate_cli_to_ir,
    mock_validate,
    mock_interpret,
):
    """Test call_aws returns success for a valid read-only command."""
    # Create a proper ProgramInterpretationResponse mock
    mock_response = InterpretationResponse(error=None, json='{"Buckets": []}', status_code=200)

    mock_result = ProgramInterpretationResponse(
        response=mock_response,
        metadata=None,
        validation_failures=None,
        missing_context_failures=None,
        failed_constraints=None,
    )
    mock_interpret.return_value = mock_result

    mock_is_operation_read_only.return_value = True

    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
    mock_ir.command = MagicMock()
    mock_ir.command.is_awscli_customization = False  # Ensure interpret_command is called
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_response = MagicMock()
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    # Execute
    result = await call_aws.fn('aws s3api list-buckets', DummyCtx())

    # Verify - the result should be the ProgramInterpretationResponse object
    assert result == mock_result
    mock_translate_cli_to_ir.assert_called_once_with('aws s3api list-buckets')
    mock_validate.assert_called_once_with(mock_ir)
    mock_interpret.assert_called_once()


@patch('awslabs.aws_api_mcp_server.server.get_requests_session')
async def test_suggest_aws_commands_success(mock_get_session):
    """Test suggest_aws_commands returns suggestions for a valid query."""
    mock_suggestions = {
        'suggestions': [
            {
                'command': 'aws s3 ls',
                'confidence': 0.95,
                'description': 'List S3 buckets',
                'required_parameters': [],
            },
            {
                'command': 'aws s3api list-buckets',
                'confidence': 0.90,
                'description': 'List all S3 buckets using S3 API',
                'required_parameters': [],
            },
        ]
    }

    mock_response = MagicMock()
    mock_response.json.return_value = mock_suggestions

    mock_session = MagicMock()
    mock_session.post.return_value = mock_response
    mock_session.__enter__.return_value = mock_session
    mock_session.__exit__.return_value = None

    mock_get_session.return_value = mock_session

    result = await suggest_aws_commands.fn('List all S3 buckets', DummyCtx())

    assert result == mock_suggestions
    mock_session.post.assert_called_once()

    # Verify the HTTP call parameters
    call_args = mock_session.post.call_args
    assert call_args[1]['json'] == {'query': 'List all S3 buckets'}
    assert call_args[1]['timeout'] == 30


async def test_suggest_aws_commands_empty_query():
    """Test suggest_aws_commands returns error for empty query."""
    result = await suggest_aws_commands.fn('', DummyCtx())

    assert result == AwsApiMcpServerErrorResponse(detail='Empty query provided')


@patch('awslabs.aws_api_mcp_server.server.get_requests_session')
async def test_suggest_aws_commands_exception(mock_get_session):
    """Test suggest_aws_commands returns error when HTTPError is raised."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError('404 Not Found')

    mock_session = MagicMock()
    mock_session.post.return_value = mock_response
    mock_session.__enter__.return_value = mock_session
    mock_session.__exit__.return_value = None

    mock_get_session.return_value = mock_session

    result = await suggest_aws_commands.fn('List S3 buckets', DummyCtx())

    assert result == AwsApiMcpServerErrorResponse(
        detail='Failed to execute tool due to internal error. Use your best judgement and existing knowledge to pick a command or point to relevant AWS Documentation.'
    )
    mock_response.raise_for_status.assert_called_once()
    mock_session.post.assert_called_once()


@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_api_mcp_server.server.REQUIRE_MUTATION_CONSENT', True)
@patch('awslabs.aws_api_mcp_server.server.interpret_command')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.core.aws.service.is_operation_read_only')
async def test_call_aws_with_consent_and_accept(
    mock_is_operation_read_only,
    mock_translate_cli_to_ir,
    mock_validate,
    mock_interpret,
):
    """Test call_aws with mutating action and consent enabled."""
    # Create a proper ProgramInterpretationResponse mock
    mock_response = InterpretationResponse(error=None, json='{"Buckets": []}', status_code=200)

    mock_result = ProgramInterpretationResponse(
        response=mock_response,
        metadata=None,
        validation_failures=None,
        missing_context_failures=None,
        failed_constraints=None,
    )
    mock_interpret.return_value = mock_result

    mock_is_operation_read_only.return_value = False

    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'create-bucket'
    mock_ir.command = MagicMock()
    mock_ir.command.is_awscli_customization = False  # Ensure interpret_command is called
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_response = MagicMock()
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    mock_ctx = AsyncMock()
    mock_ctx.elicit.return_value = AcceptedElicitation(data=Consent(answer=True))

    # Execute
    result = await call_aws.fn('aws s3api create-bucket --bucket somebucket', mock_ctx)

    # Verify that consent was requested
    assert result == mock_result
    mock_translate_cli_to_ir.assert_called_once_with('aws s3api create-bucket --bucket somebucket')
    mock_validate.assert_called_once_with(mock_ir)
    mock_interpret.assert_called_once()
    mock_ctx.elicit.assert_called_once()


@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_api_mcp_server.server.REQUIRE_MUTATION_CONSENT', True)
@patch('awslabs.aws_api_mcp_server.server.interpret_command')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.core.aws.service.is_operation_read_only')
async def test_call_aws_with_consent_and_reject(
    mock_is_operation_read_only,
    mock_translate_cli_to_ir,
    mock_validate,
    mock_interpret,
):
    """Test call_aws with mutating action and consent enabled."""
    mock_response = InterpretationResponse(error=None, json='{"Buckets": []}', status_code=200)
    mock_is_operation_read_only.return_value = False

    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'create-bucket'
    mock_ir.command = MagicMock()
    mock_ir.command.is_awscli_customization = False
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_response = MagicMock()
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    mock_ctx = AsyncMock()
    mock_ctx.elicit.return_value = AcceptedElicitation(data=Consent(answer=False))

    # Execute
    result = await call_aws.fn('aws s3api create-bucket --bucket somebucket', mock_ctx)

    # Verify that consent was requested
    assert result == AwsApiMcpServerErrorResponse(
        detail='Error while executing the command: User rejected the execution of the command.'
    )
    mock_translate_cli_to_ir.assert_called_once_with('aws s3api create-bucket --bucket somebucket')
    mock_validate.assert_called_once_with(mock_ir)


@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_api_mcp_server.server.REQUIRE_MUTATION_CONSENT', False)
@patch('awslabs.aws_api_mcp_server.server.interpret_command')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.core.aws.service.is_operation_read_only')
async def test_call_aws_without_consent(
    mock_is_operation_read_only,
    mock_translate_cli_to_ir,
    mock_validate,
    mock_interpret,
):
    """Test call_aws with mutating action and with consent disabled."""
    # Create a proper ProgramInterpretationResponse mock
    mock_response = InterpretationResponse(error=None, json='{"Buckets": []}', status_code=200)

    mock_result = ProgramInterpretationResponse(
        response=mock_response,
        metadata=None,
        validation_failures=None,
        missing_context_failures=None,
        failed_constraints=None,
    )
    mock_interpret.return_value = mock_result

    mock_is_operation_read_only.return_value = False

    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'create-bucket'
    mock_ir.command = MagicMock()
    mock_ir.command.is_awscli_customization = False  # Ensure interpret_command is called
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_response = MagicMock()
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    # Execute
    result = await call_aws.fn('aws s3api create-bucket --bucket somebucket', DummyCtx())

    # Verify that consent was requested
    assert result == mock_result
    mock_translate_cli_to_ir.assert_called_once_with('aws s3api create-bucket --bucket somebucket')
    mock_validate.assert_called_once_with(mock_ir)
    mock_interpret.assert_called_once()


@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
async def test_call_aws_validation_error_awsmcp_error(mock_translate_cli_to_ir):
    """Test call_aws returns error details for AwsApiMcpError during validation."""
    mock_error = AwsApiMcpError('Invalid command syntax')
    mock_failure = MagicMock()
    mock_failure.reason = 'Invalid command syntax'
    mock_error.as_failure = MagicMock(return_value=mock_failure)
    mock_translate_cli_to_ir.side_effect = mock_error

    # Execute
    result = await call_aws.fn('aws invalid-service invalid-operation', DummyCtx())

    # Verify
    assert result == AwsApiMcpServerErrorResponse(
        detail='Error while validating the command: Invalid command syntax'
    )
    mock_translate_cli_to_ir.assert_called_once_with('aws invalid-service invalid-operation')


@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
async def test_call_aws_validation_error_generic_exception(mock_translate_cli_to_ir):
    """Test call_aws returns error details for generic exception during validation."""
    mock_translate_cli_to_ir.side_effect = ValueError('Generic validation error')

    # Execute
    result = await call_aws.fn('aws s3api list-buckets', DummyCtx())

    # Verify
    assert result == AwsApiMcpServerErrorResponse(
        detail='Error while validating the command: Generic validation error'
    )


@patch('awslabs.aws_api_mcp_server.server.interpret_command', side_effect=NoCredentialsError())
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.core.aws.service.is_operation_read_only')
async def test_call_aws_no_credentials_error(
    mock_is_operation_read_only, mock_translate_cli_to_ir, mock_validate, mock_interpret
):
    """Test call_aws returns error when no AWS credentials are found."""
    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
    mock_ir.command = MagicMock()
    mock_ir.command.is_awscli_customization = False  # Ensure interpret_command is called
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_is_operation_read_only.return_value = True

    # Mock validation response
    mock_response = MagicMock()
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    # Execute
    result = await call_aws.fn('aws s3api list-buckets', DummyCtx())

    # Verify
    assert result == AwsApiMcpServerErrorResponse(
        detail='Error while executing the command: No AWS credentials found. '
        "Please configure your AWS credentials using 'aws configure' "
        'or set appropriate environment variables.'
    )


@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_api_mcp_server.server.interpret_command')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.core.aws.service.is_operation_read_only')
async def test_call_aws_execution_error_awsmcp_error(
    mock_is_operation_read_only,
    mock_translate_cli_to_ir,
    mock_validate,
    mock_interpret,
):
    """Test call_aws returns error details for AwsApiMcpError during execution."""
    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
    mock_ir.command = MagicMock()
    mock_ir.command.is_awscli_customization = False  # Ensure interpret_command is called
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_is_operation_read_only.return_value = True

    # Mock validation response
    mock_response = MagicMock()
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    mock_error = AwsApiMcpError('Execution failed')
    mock_failure = MagicMock()
    mock_failure.reason = 'Execution failed'
    mock_error.as_failure = MagicMock(return_value=mock_failure)
    mock_interpret.side_effect = mock_error

    # Execute
    result = await call_aws.fn('aws s3api list-buckets', DummyCtx())

    # Verify
    assert result == AwsApiMcpServerErrorResponse(
        detail='Error while executing the command: Execution failed'
    )


@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_api_mcp_server.server.interpret_command')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.core.aws.service.is_operation_read_only')
async def test_call_aws_execution_error_generic_exception(
    mock_is_operation_read_only,
    mock_translate_cli_to_ir,
    mock_validate,
    mock_interpret,
):
    """Test call_aws returns error details for generic exception during execution."""
    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
    mock_ir.command = MagicMock()
    mock_ir.command.is_awscli_customization = False  # Ensure interpret_command is called
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_is_operation_read_only.return_value = True

    # Mock validation response
    mock_response = MagicMock()
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    mock_interpret.side_effect = RuntimeError('Generic execution error')

    # Execute
    result = await call_aws.fn('aws s3api list-buckets', DummyCtx())

    # Verify
    assert result == AwsApiMcpServerErrorResponse(
        detail='Error while executing the command: Generic execution error'
    )


async def test_call_aws_non_aws_command():
    """Test call_aws with command that doesn't start with 'aws'."""
    with patch(
        'awslabs.aws_api_mcp_server.server.translate_cli_to_ir'
    ) as mock_translate_cli_to_ir:
        mock_translate_cli_to_ir.side_effect = ValueError("Command must start with 'aws'")

        result = await call_aws.fn('s3api list-buckets', DummyCtx())

        assert result == AwsApiMcpServerErrorResponse(
            detail="Error while validating the command: Command must start with 'aws'"
        )


@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.core.aws.service.is_operation_read_only')
@patch('awslabs.aws_api_mcp_server.server.READ_OPERATIONS_ONLY_MODE')
async def test_when_operation_is_not_allowed(
    mock_read_operations_only_mode,
    mock_is_operation_read_only,
    mock_translate_cli_to_ir,
    mock_validate,
):
    """Test call_aws returns error when operation is not allowed in read-only mode."""
    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
    mock_ir.command = MagicMock()
    mock_ir.command.is_awscli_customization = False  # Ensure interpret_command is called
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_read_operations_only_mode.return_value = True

    # Mock validation response
    mock_response = MagicMock()
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    mock_is_operation_read_only.return_value = False

    # Execute
    result = await call_aws.fn('aws s3api list-buckets', DummyCtx())

    # verify
    assert result == AwsApiMcpServerErrorResponse(
        detail='Execution of this operation is not allowed because read only mode is enabled. It can be disabled by setting the READ_OPERATIONS_ONLY environment variable to False.'
    )


@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
async def test_call_aws_validation_failures(mock_translate_cli_to_ir, mock_validate):
    """Test call_aws returns error for validation failures."""
    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
    mock_ir.command = MagicMock()
    mock_ir.command.is_awscli_customization = False  # Ensure interpret_command is called
    mock_translate_cli_to_ir.return_value = mock_ir

    # Mock validation response with validation failures
    mock_response = MagicMock()
    mock_response.validation_failures = ['Invalid parameter value']
    mock_response.failed_constraints = None
    mock_response.model_dump_json.return_value = (
        '{"validation_failures": ["Invalid parameter value"]}'
    )
    mock_validate.return_value = mock_response

    # Execute
    result = await call_aws.fn('aws s3api list-buckets', DummyCtx())

    # Verify
    assert result == AwsApiMcpServerErrorResponse(
        detail='Error while validating the command: {"validation_failures": ["Invalid parameter value"]}'
    )
    mock_translate_cli_to_ir.assert_called_once_with('aws s3api list-buckets')
    mock_validate.assert_called_once_with(mock_ir)


@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
async def test_call_aws_failed_constraints(mock_translate_cli_to_ir, mock_validate):
    """Test call_aws returns error for failed constraints."""
    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
    mock_ir.command = MagicMock()
    mock_ir.command.is_awscli_customization = False  # Ensure interpret_command is called
    mock_translate_cli_to_ir.return_value = mock_ir

    # Mock validation response with failed constraints
    mock_response = MagicMock()
    mock_response.validation_failures = None
    mock_response.failed_constraints = ['Resource limit exceeded']
    mock_response.model_dump_json.return_value = (
        '{"failed_constraints": ["Resource limit exceeded"]}'
    )
    mock_validate.return_value = mock_response

    # Execute
    result = await call_aws.fn('aws s3api list-buckets', DummyCtx())

    # Verify
    assert result == AwsApiMcpServerErrorResponse(
        detail='Error while validating the command: {"failed_constraints": ["Resource limit exceeded"]}'
    )
    mock_translate_cli_to_ir.assert_called_once_with('aws s3api list-buckets')
    mock_validate.assert_called_once_with(mock_ir)


@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
async def test_call_aws_both_validation_failures_and_constraints(
    mock_translate_cli_to_ir, mock_validate
):
    """Test call_aws returns error for both validation failures and failed constraints."""
    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
    mock_ir.command = MagicMock()
    mock_ir.command.is_awscli_customization = False  # Ensure interpret_command is called
    mock_translate_cli_to_ir.return_value = mock_ir

    # Mock validation response with both validation failures and failed constraints
    mock_response = MagicMock()
    mock_response.validation_failures = ['Invalid parameter value']
    mock_response.failed_constraints = ['Resource limit exceeded']
    mock_response.model_dump_json.return_value = '{"validation_failures": ["Invalid parameter value"], "failed_constraints": ["Resource limit exceeded"]}'
    mock_validate.return_value = mock_response

    # Execute
    result = await call_aws.fn('aws s3api list-buckets', DummyCtx())

    # Verify
    assert result == AwsApiMcpServerErrorResponse(
        detail='Error while validating the command: {"validation_failures": ["Invalid parameter value"], "failed_constraints": ["Resource limit exceeded"]}'
    )
    mock_translate_cli_to_ir.assert_called_once_with('aws s3api list-buckets')
    mock_validate.assert_called_once_with(mock_ir)


@patch('awslabs.aws_api_mcp_server.server.execute_awscli_customization')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.core.aws.service.is_operation_read_only')
async def test_call_aws_awscli_customization_success(
    mock_is_operation_read_only,
    mock_translate_cli_to_ir,
    mock_validate,
    mock_execute_awscli_customization,
):
    """Test call_aws returns success response for AWS CLI customization command."""
    mock_ir = MagicMock()
    mock_ir.command = MagicMock()
    mock_ir.command.is_awscli_customization = True
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_is_operation_read_only.return_value = True

    mock_response = MagicMock()
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    expected_response = AwsCliAliasResponse(response='Command executed successfully', error=None)
    mock_execute_awscli_customization.return_value = expected_response

    result = await call_aws.fn('aws configure list', DummyCtx())

    assert result == expected_response
    mock_translate_cli_to_ir.assert_called_once_with('aws configure list')
    mock_validate.assert_called_once_with(mock_ir)
    mock_execute_awscli_customization.assert_called_once_with(
        'aws configure list',
        mock_ir.command,
        credentials=None,
    )


@patch('awslabs.aws_api_mcp_server.server.execute_awscli_customization')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.core.aws.service.is_operation_read_only')
async def test_call_aws_awscli_customization_error(
    mock_is_operation_read_only,
    mock_translate_cli_to_ir,
    mock_validate,
    mock_execute_awscli_customization,
):
    """Test call_aws handles error response from AWS CLI customization command."""
    mock_ir = MagicMock()
    mock_ir.command = MagicMock()
    mock_ir.command.is_awscli_customization = True
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_is_operation_read_only.return_value = True

    mock_response = MagicMock()
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    error_response = AwsApiMcpServerErrorResponse(
        detail="Error while executing 'aws configure list': Configuration file not found"
    )
    mock_execute_awscli_customization.return_value = error_response

    mock_ctx = MagicMock()
    mock_ctx.error = AsyncMock()

    result = await call_aws.fn('aws configure list', mock_ctx)

    assert result == error_response
    mock_translate_cli_to_ir.assert_called_once_with('aws configure list')
    mock_validate.assert_called_once_with(mock_ir)
    mock_execute_awscli_customization.assert_called_once_with(
        'aws configure list',
        mock_ir.command,
        credentials=None,
    )
    mock_ctx.error.assert_called_once_with(error_response.detail)


@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', None)
@patch('awslabs.aws_api_mcp_server.server.WORKING_DIRECTORY', '/tmp')
def test_main_missing_aws_region():
    """Test main function raises ValueError when AWS_REGION environment variable is not set."""
    with pytest.raises(ValueError, match=r'AWS_REGION environment variable is not defined.'):
        main()


@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_api_mcp_server.server.WORKING_DIRECTORY', 'relative/path')
def test_main_relative_working_directory():
    """Test main function raises ValueError when AWS_API_MCP_WORKING_DIR is a relative path."""
    with pytest.raises(
        ValueError,
        match=r'AWS_API_MCP_WORKING_DIR must be an absolute path.',
    ):
        main()


@patch('awslabs.aws_api_mcp_server.server.os.chdir')
@patch('awslabs.aws_api_mcp_server.server.server')
@patch('awslabs.aws_api_mcp_server.server.get_read_only_operations')
@patch('awslabs.aws_api_mcp_server.server.READ_OPERATIONS_ONLY_MODE', True)
@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_api_mcp_server.server.WORKING_DIRECTORY', '/tmp')
def test_main_success_with_read_only_mode(
    mock_get_read_only_operations,
    mock_server,
    mock_chdir,
):
    """Test main function executes successfully with read-only mode enabled."""
    mock_read_operations = MagicMock()
    mock_get_read_only_operations.return_value = mock_read_operations
    mock_server.run = MagicMock()

    main()

    mock_chdir.assert_called_once_with('/tmp')
    mock_get_read_only_operations.assert_called_once()
    mock_server.run.assert_called_once_with(transport='stdio')


@patch('awslabs.aws_api_mcp_server.core.common.config.ENABLE_AGENT_SCRIPTS', True)
async def test_get_execution_plan_is_available_when_env_var_is_set():
    """Test get_execution_plan returns script content when script exists."""
    # Re-import the server module to ensure the tool is registered
    import awslabs.aws_api_mcp_server.server
    import importlib

    importlib.reload(awslabs.aws_api_mcp_server.server)

    from awslabs.aws_api_mcp_server.server import server

    tools = await server._list_tools()
    tool_names = [tool.name for tool in tools]
    assert 'get_execution_plan' in tool_names


@patch('awslabs.aws_api_mcp_server.core.common.config.ENABLE_AGENT_SCRIPTS', False)
async def test_get_execution_plan_is_available_when_env_var_is_not_set():
    """Test get_execution_plan returns script content when script exists."""
    # Re-import the server module to ensure the tool is not registered
    import awslabs.aws_api_mcp_server.server
    import importlib

    importlib.reload(awslabs.aws_api_mcp_server.server)

    from awslabs.aws_api_mcp_server.server import server

    tools = await server._list_tools()
    tool_names = [tool.name for tool in tools]
    assert 'get_execution_plan' not in tool_names


@patch('awslabs.aws_api_mcp_server.core.common.config.ENABLE_AGENT_SCRIPTS', True)
async def test_get_execution_plan_script_not_found():
    """Test get_execution_plan returns error when script does not exist."""
    # Re-import the server module to ensure the function is defined
    import awslabs.aws_api_mcp_server.server
    import importlib

    importlib.reload(awslabs.aws_api_mcp_server.server)

    from awslabs.aws_api_mcp_server.server import get_execution_plan

    # Mock the AGENT_SCRIPTS_MANAGER after reloading
    with patch(
        'awslabs.aws_api_mcp_server.server.AGENT_SCRIPTS_MANAGER'
    ) as mock_agent_scripts_manager:
        mock_agent_scripts_manager.get_script.return_value = None

        result = await get_execution_plan.fn('non-existent-script', DummyCtx())

        assert isinstance(result, AwsApiMcpServerErrorResponse)
        assert (
            result.detail
            == 'Error while retrieving execution plan: Script non-existent-script not found'
        )
        mock_agent_scripts_manager.get_script.assert_called_once_with('non-existent-script')


@patch('awslabs.aws_api_mcp_server.core.common.config.ENABLE_AGENT_SCRIPTS', True)
async def test_get_execution_plan_exception_handling():
    """Test get_execution_plan handles exceptions properly."""
    # Re-import the server module to ensure the function is defined
    import awslabs.aws_api_mcp_server.server
    import importlib

    importlib.reload(awslabs.aws_api_mcp_server.server)

    from awslabs.aws_api_mcp_server.server import get_execution_plan

    # Mock the AGENT_SCRIPTS_MANAGER after reloading
    with patch(
        'awslabs.aws_api_mcp_server.server.AGENT_SCRIPTS_MANAGER'
    ) as mock_agent_scripts_manager:
        mock_agent_scripts_manager.get_script.side_effect = Exception('Test exception')

        mock_ctx = MagicMock()
        mock_ctx.error = AsyncMock()

        result = await get_execution_plan.fn('test-script', mock_ctx)

        assert isinstance(result, AwsApiMcpServerErrorResponse)
        assert result.detail == 'Error while retrieving execution plan: Test exception'
        mock_ctx.error.assert_called_once_with(
            'Error while retrieving execution plan: Test exception'
        )


# Tests for call_aws_helper function
@patch('awslabs.aws_api_mcp_server.server.interpret_command')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
async def test_call_aws_helper_with_credentials(mock_translate, mock_validate, mock_interpret):
    """Test call_aws_helper passes credentials to interpret_command."""
    test_credentials = Credentials(**TEST_CREDENTIALS)

    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
    mock_ir.command.is_awscli_customization = False  # Ensure interpret_command is called
    mock_translate.return_value = mock_ir

    mock_validation = MagicMock()
    mock_validation.validation_failed = False
    mock_validate.return_value = mock_validation

    mock_response = MagicMock()
    mock_interpret.return_value = mock_response

    result = await call_aws_helper(
        'aws s3api list-buckets',
        AsyncMock(),
        credentials=test_credentials,
    )

    print(result)

    mock_interpret.assert_called_once_with(
        cli_command='aws s3api list-buckets',
        max_results=None,
        credentials=test_credentials,
    )
    assert result == mock_response


@patch('awslabs.aws_api_mcp_server.server.interpret_command')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
async def test_call_aws_helper_without_credentials(mock_translate, mock_validate, mock_interpret):
    """Test call_aws_helper works without credentials."""
    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
    mock_ir.command.is_awscli_customization = False  # Ensure interpret_command is called
    mock_translate.return_value = mock_ir

    mock_validation = MagicMock()
    mock_validation.validation_failed = False
    mock_validate.return_value = mock_validation

    mock_response = MagicMock()
    mock_interpret.return_value = mock_response

    result = await call_aws_helper(
        'aws s3api list-buckets',
        AsyncMock(),
        credentials=None,
    )

    mock_interpret.assert_called_once_with(
        cli_command='aws s3api list-buckets', max_results=None, credentials=None
    )
    assert result == mock_response


@patch('awslabs.aws_api_mcp_server.server.call_aws_helper')
async def test_call_aws_delegates_to_helper(mock_call_aws_helper):
    """Test call_aws delegates to call_aws_helper with None credentials."""
    mock_response = MagicMock()
    mock_call_aws_helper.return_value = mock_response

    ctx = DummyCtx()

    result = await call_aws.fn('aws s3api list-buckets', ctx)

    mock_call_aws_helper.assert_called_once_with(
        cli_command='aws s3api list-buckets', ctx=ctx, max_results=None, credentials=None
    )
    assert result == mock_response
