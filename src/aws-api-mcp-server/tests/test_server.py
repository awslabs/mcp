import pytest
from awslabs.aws_api_mcp_server.core.common.errors import AwsApiMcpError
from awslabs.aws_api_mcp_server.core.common.models import (
    AwsApiMcpServerErrorResponse,
    AwsCliAliasResponse,
    Consent,
    InterpretationResponse,
    ProgramInterpretationResponse,
)
from awslabs.aws_api_mcp_server.server import call_aws, main, suggest_aws_commands
from botocore.exceptions import NoCredentialsError
from mcp.server.elicitation import AcceptedElicitation
from tests.fixtures import DummyCtx
from unittest.mock import AsyncMock, MagicMock, patch


@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_api_mcp_server.server.interpret_command')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.server.is_operation_read_only')
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
    result = await call_aws('aws s3api list-buckets', DummyCtx())

    # Verify - the result should be the ProgramInterpretationResponse object
    assert result == mock_result
    mock_translate_cli_to_ir.assert_called_once_with('aws s3api list-buckets')
    mock_validate.assert_called_once_with(mock_ir)
    mock_interpret.assert_called_once()


@patch('awslabs.aws_api_mcp_server.server.knowledge_base')
async def test_suggest_aws_commands_success(mock_knowledge_base):
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
    mock_knowledge_base.get_suggestions.return_value = mock_suggestions

    result = await suggest_aws_commands('List all S3 buckets', DummyCtx())

    assert result == mock_suggestions
    mock_knowledge_base.get_suggestions.assert_called_once_with('List all S3 buckets')


async def test_suggest_aws_commands_empty_query():
    """Test suggest_aws_commands returns error for empty query."""
    result = await suggest_aws_commands('', DummyCtx())

    assert result == AwsApiMcpServerErrorResponse(detail='Empty query provided')


@patch('awslabs.aws_api_mcp_server.server.knowledge_base')
async def test_suggest_aws_commands_exception(mock_knowledge_base):
    """Test suggest_aws_commands returns error when knowledge base raises exception."""
    mock_knowledge_base.get_suggestions.side_effect = RuntimeError('Knowledge base error')

    result = await suggest_aws_commands('List S3 buckets', DummyCtx())

    assert result == AwsApiMcpServerErrorResponse(
        detail='Error while suggesting commands: Knowledge base error'
    )
    mock_knowledge_base.get_suggestions.assert_called_once_with('List S3 buckets')


@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_api_mcp_server.server.REQUIRE_MUTATION_CONSENT', True)
@patch('awslabs.aws_api_mcp_server.server.interpret_command')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.server.is_operation_read_only')
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
    result = await call_aws('aws s3api create-bucket --bucket somebucket', mock_ctx)

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
@patch('awslabs.aws_api_mcp_server.server.is_operation_read_only')
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
    result = await call_aws('aws s3api create-bucket --bucket somebucket', mock_ctx)

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
@patch('awslabs.aws_api_mcp_server.server.is_operation_read_only')
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
    result = await call_aws('aws s3api create-bucket --bucket somebucket', DummyCtx())

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
    result = await call_aws('aws invalid-service invalid-operation', DummyCtx())

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
    result = await call_aws('aws s3api list-buckets', DummyCtx())

    # Verify
    assert result == AwsApiMcpServerErrorResponse(
        detail='Error while validating the command: Generic validation error'
    )


@patch('awslabs.aws_api_mcp_server.server.interpret_command', side_effect=NoCredentialsError())
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.server.is_operation_read_only')
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
    result = await call_aws('aws s3api list-buckets', DummyCtx())

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
@patch('awslabs.aws_api_mcp_server.server.is_operation_read_only')
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
    result = await call_aws('aws s3api list-buckets', DummyCtx())

    # Verify
    assert result == AwsApiMcpServerErrorResponse(
        detail='Error while executing the command: Execution failed'
    )


@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_api_mcp_server.server.interpret_command')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.server.is_operation_read_only')
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
    result = await call_aws('aws s3api list-buckets', DummyCtx())

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

        result = await call_aws('s3api list-buckets', DummyCtx())

        assert result == AwsApiMcpServerErrorResponse(
            detail="Error while validating the command: Command must start with 'aws'"
        )


@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.server.is_operation_read_only')
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
    result = await call_aws('aws s3api list-buckets', DummyCtx())

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
    result = await call_aws('aws s3api list-buckets', DummyCtx())

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
    result = await call_aws('aws s3api list-buckets', DummyCtx())

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
    result = await call_aws('aws s3api list-buckets', DummyCtx())

    # Verify
    assert result == AwsApiMcpServerErrorResponse(
        detail='Error while validating the command: {"validation_failures": ["Invalid parameter value"], "failed_constraints": ["Resource limit exceeded"]}'
    )
    mock_translate_cli_to_ir.assert_called_once_with('aws s3api list-buckets')
    mock_validate.assert_called_once_with(mock_ir)


@patch('awslabs.aws_api_mcp_server.server.execute_awscli_customization')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.server.is_operation_read_only')
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

    result = await call_aws('aws configure list', DummyCtx())

    assert result == expected_response
    mock_translate_cli_to_ir.assert_called_once_with('aws configure list')
    mock_validate.assert_called_once_with(mock_ir)
    mock_execute_awscli_customization.assert_called_once_with(
        'aws configure list', mock_ir.command
    )


@patch('awslabs.aws_api_mcp_server.server.execute_awscli_customization')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.server.is_operation_read_only')
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

    result = await call_aws('aws configure list', mock_ctx)

    assert result == error_response
    mock_translate_cli_to_ir.assert_called_once_with('aws configure list')
    mock_validate.assert_called_once_with(mock_ir)
    mock_execute_awscli_customization.assert_called_once_with(
        'aws configure list', mock_ir.command
    )
    mock_ctx.error.assert_called_once_with(error_response.detail)


@patch('awslabs.aws_api_mcp_server.core.kb.threading.Thread')
@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', None)
@patch('awslabs.aws_api_mcp_server.server.WORKING_DIRECTORY', '/tmp')
def test_main_missing_aws_region(mock_thread):
    """Test main function raises ValueError when AWS_REGION environment variable is not set."""
    with pytest.raises(ValueError, match=r'AWS_REGION environment variable is not defined.'):
        main()


@patch('awslabs.aws_api_mcp_server.core.kb.threading.Thread')
@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_api_mcp_server.server.WORKING_DIRECTORY', 'relative/path')
def test_main_relative_working_directory(mock_thread):
    """Test main function raises ValueError when AWS_API_MCP_WORKING_DIR is a relative path."""
    with pytest.raises(
        ValueError,
        match=r'AWS_API_MCP_WORKING_DIR must be an absolute path.',
    ):
        main()


@patch('awslabs.aws_api_mcp_server.core.kb.threading.Thread')
@patch('awslabs.aws_api_mcp_server.server.os.chdir')
@patch('awslabs.aws_api_mcp_server.server.server')
@patch('awslabs.aws_api_mcp_server.server.get_read_only_operations')
@patch('awslabs.aws_api_mcp_server.server.knowledge_base')
@patch('awslabs.aws_api_mcp_server.server.READ_OPERATIONS_ONLY_MODE', True)
@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_api_mcp_server.server.WORKING_DIRECTORY', '/tmp')
def test_main_success_with_read_only_mode(
    mock_knowledge_base,
    mock_get_read_only_operations,
    mock_server,
    mock_chdir,
    mock_thread,
):
    """Test main function executes successfully with read-only mode enabled."""
    mock_knowledge_base.setup = MagicMock()
    mock_read_operations = MagicMock()
    mock_get_read_only_operations.return_value = mock_read_operations
    mock_server.run = MagicMock()

    main()

    mock_chdir.assert_called_once_with('/tmp')
    mock_knowledge_base.setup.assert_called_once()
    mock_get_read_only_operations.assert_called_once()
    mock_server.run.assert_called_once_with(transport='stdio')
