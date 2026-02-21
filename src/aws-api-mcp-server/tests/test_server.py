import pytest
import requests
from awslabs.aws_api_mcp_server.core.common.config import get_server_auth
from awslabs.aws_api_mcp_server.core.common.errors import AwsApiMcpError, CommandValidationError
from awslabs.aws_api_mcp_server.core.common.help_command import generate_help_document
from awslabs.aws_api_mcp_server.core.common.helpers import as_json
from awslabs.aws_api_mcp_server.core.common.models import (
    AwsCliAliasResponse,
    Consent,
    Credentials,
    InterpretationResponse,
    ProgramInterpretationResponse,
)
from awslabs.aws_api_mcp_server.server import (
    call_aws,
    call_aws_helper,
    main,
    suggest_aws_commands,
)
from botocore.exceptions import NoCredentialsError
from fastmcp.server.auth import JWTVerifier
from fastmcp.server.elicitation import AcceptedElicitation
from tests.fixtures import TEST_CREDENTIALS, DummyCtx
from unittest.mock import AsyncMock, MagicMock, patch


@patch('awslabs.aws_api_mcp_server.server.os.chdir')
@patch('awslabs.aws_api_mcp_server.server.get_read_only_operations')
@patch('awslabs.aws_api_mcp_server.server.server')
def test_main_read_operations_index_load_failure(mock_server, mock_get_read_ops, mock_chdir):
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
    mock_ir.command.is_help_operation = False
    mock_ir.command.is_help_operation = False
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

    result = await suggest_aws_commands('List all S3 buckets', DummyCtx())

    assert result == mock_suggestions
    mock_session.post.assert_called_once()

    # Verify the HTTP call parameters
    call_args = mock_session.post.call_args
    assert call_args[1]['json'] == {'query': 'List all S3 buckets'}
    assert call_args[1]['timeout'] == 30


async def test_suggest_aws_commands_empty_query():
    """Test suggest_aws_commands raises error for empty query."""
    with pytest.raises(AwsApiMcpError) as exc_info:
        await suggest_aws_commands('', DummyCtx())

    assert 'Empty query provided' in str(exc_info.value)


@patch('awslabs.aws_api_mcp_server.server.get_requests_session')
async def test_suggest_aws_commands_exception(mock_get_session):
    """Test suggest_aws_commands raises error when HTTPError is raised."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError('404 Not Found')

    mock_session = MagicMock()
    mock_session.post.return_value = mock_response
    mock_session.__enter__.return_value = mock_session
    mock_session.__exit__.return_value = None

    mock_get_session.return_value = mock_session

    with pytest.raises(AwsApiMcpError) as exc_info:
        await suggest_aws_commands('List S3 buckets', DummyCtx())

    assert 'Failed to execute tool due to internal error' in str(exc_info.value)
    mock_response.raise_for_status.assert_called_once()
    mock_session.post.assert_called_once()


@patch('awslabs.aws_api_mcp_server.server.execute_awscli_customization')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
async def test_call_aws_helper_passes_region_to_customization(
    mock_translate_cli_to_ir,
    mock_validate,
    mock_execute,
):
    """Ensure region is forwarded to execute_awscli_customization when using customizations."""
    # Arrange IR with customization flag
    mock_command = MagicMock()
    mock_command.is_awscli_customization = True
    mock_command.is_help_operation = False
    mock_command.service_name = 's3'
    mock_command.operation_cli_name = 'ls'
    mock_ir = MagicMock()
    mock_ir.command = mock_command
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_validate.return_value = MagicMock(validation_failed=False)
    mock_execute.return_value = AwsCliAliasResponse(response='', error='')

    # Avoid policy gating
    with (
        patch('awslabs.aws_api_mcp_server.server.READ_OPERATIONS_INDEX', None),
        patch('awslabs.aws_api_mcp_server.server.READ_OPERATIONS_ONLY_MODE', False),
        patch('awslabs.aws_api_mcp_server.server.REQUIRE_MUTATION_CONSENT', False),
    ):
        # Act
        result = await call_aws_helper(
            cli_command='aws s3 ls',
            ctx=DummyCtx(),  # type: ignore[arg-type]
            max_results=None,
            credentials=None,
            default_region='eu-west-1',
        )

    # Assert
    assert isinstance(result, AwsCliAliasResponse)
    _, kwargs = mock_execute.call_args
    assert kwargs.get('default_region_override') == 'eu-west-1'


@patch('awslabs.aws_api_mcp_server.server.interpret_command')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
async def test_call_aws_helper_passes_region_to_interpret(
    mock_translate_cli_to_ir,
    mock_validate,
    mock_interpret,
):
    """Ensure region is forwarded to interpret_command for normal operations."""
    # Arrange IR without customization
    mock_command = MagicMock()
    mock_command.is_awscli_customization = False
    mock_command.is_help_operation = False
    mock_command.service_name = 's3api'
    mock_command.operation_cli_name = 'list-buckets'
    mock_ir = MagicMock()
    mock_ir.command = mock_command
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_validate.return_value = MagicMock(validation_failed=False)
    mock_interpret.return_value = ProgramInterpretationResponse(
        response=InterpretationResponse(error=None, json='{}', status_code=200),
        metadata=None,
        validation_failures=None,
        missing_context_failures=None,
        failed_constraints=None,
    )

    # Avoid policy gating
    with (
        patch('awslabs.aws_api_mcp_server.server.READ_OPERATIONS_INDEX', None),
        patch('awslabs.aws_api_mcp_server.server.READ_OPERATIONS_ONLY_MODE', False),
        patch('awslabs.aws_api_mcp_server.server.REQUIRE_MUTATION_CONSENT', False),
    ):
        # Act
        result = await call_aws_helper(
            cli_command='aws s3api list-buckets',
            ctx=DummyCtx(),  # type: ignore[arg-type]
            max_results=None,
            credentials=None,
            default_region='eu-west-2',
        )

    # Assert
    assert isinstance(result, ProgramInterpretationResponse)
    _, kwargs = mock_interpret.call_args
    assert kwargs.get('default_region_override') == 'eu-west-2'


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
    mock_ir.command.is_help_operation = False
    mock_ir.command.is_help_operation = False
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
    mock_ir.command.is_help_operation = False
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_response = MagicMock()
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    mock_ctx = AsyncMock()
    mock_ctx.elicit.return_value = AcceptedElicitation(data=Consent(answer=False))

    # Execute and verify that consent was requested and error is raised
    with pytest.raises(AwsApiMcpError) as exc_info:
        await call_aws('aws s3api create-bucket --bucket somebucket', mock_ctx)

    assert 'User rejected the execution of the command' in str(exc_info.value)
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
    mock_ir.command.is_help_operation = False
    mock_ir.command.is_help_operation = False
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

    # Execute and verify
    with pytest.raises(AwsApiMcpError) as exc_info:
        await call_aws('aws invalid-service invalid-operation', DummyCtx())

    assert 'Invalid command syntax' in str(exc_info.value)
    mock_translate_cli_to_ir.assert_called_once_with('aws invalid-service invalid-operation')


@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
async def test_call_aws_validation_error_generic_exception(mock_translate_cli_to_ir):
    """Test call_aws returns error details for generic exception during validation."""
    mock_translate_cli_to_ir.side_effect = ValueError('Generic validation error')

    # Execute and verify
    with pytest.raises(AwsApiMcpError) as exc_info:
        await call_aws('aws s3api list-buckets', DummyCtx())

    assert 'Generic validation error' in str(exc_info.value)


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
    mock_ir.command.is_help_operation = False
    mock_ir.command.is_help_operation = False
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_is_operation_read_only.return_value = True

    # Mock validation response
    mock_response = MagicMock()
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    # Execute and verify
    with pytest.raises(AwsApiMcpError) as exc_info:
        await call_aws('aws s3api list-buckets', DummyCtx())

    assert 'No AWS credentials found' in str(exc_info.value)


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
    mock_ir.command.is_help_operation = False
    mock_ir.command.is_help_operation = False
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

    # Execute and verify
    with pytest.raises(AwsApiMcpError) as exc_info:
        await call_aws('aws s3api list-buckets', DummyCtx())

    assert 'Execution failed' in str(exc_info.value)


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
    mock_ir.command.is_help_operation = False
    mock_ir.command.is_help_operation = False
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_is_operation_read_only.return_value = True

    # Mock validation response
    mock_response = MagicMock()
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    mock_interpret.side_effect = RuntimeError('Generic execution error')

    # Execute and verify
    with pytest.raises(AwsApiMcpError) as exc_info:
        await call_aws('aws s3api list-buckets', DummyCtx())

    assert 'Generic execution error' in str(exc_info.value)


async def test_call_aws_non_aws_command():
    """Test call_aws with command that doesn't start with 'aws'."""
    with patch(
        'awslabs.aws_api_mcp_server.server.translate_cli_to_ir'
    ) as mock_translate_cli_to_ir:
        mock_translate_cli_to_ir.side_effect = ValueError("Command must start with 'aws'")

        with pytest.raises(AwsApiMcpError) as exc_info:
            await call_aws('s3api list-buckets', DummyCtx())

        assert "Command must start with 'aws'" in str(exc_info.value)


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
    mock_ir.command.is_help_operation = False
    mock_ir.command.is_help_operation = False
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_read_operations_only_mode.return_value = True

    # Mock validation response
    mock_response = MagicMock()
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    mock_is_operation_read_only.return_value = False

    # Execute and verify
    with pytest.raises(AwsApiMcpError) as exc_info:
        await call_aws('aws s3api list-buckets', DummyCtx())

    assert 'Execution of this operation is not allowed because read only mode is enabled' in str(
        exc_info.value
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
    mock_ir.command.is_help_operation = False
    mock_ir.command.is_help_operation = False
    mock_translate_cli_to_ir.return_value = mock_ir

    # Mock validation response with validation failures
    mock_response = MagicMock()
    mock_response.validation_failures = ['Invalid parameter value']
    mock_response.failed_constraints = None
    mock_response.model_dump_json.return_value = (
        '{"validation_failures": ["Invalid parameter value"]}'
    )
    mock_validate.return_value = mock_response

    # Execute and verify
    with pytest.raises(CommandValidationError) as exc_info:
        await call_aws('aws s3api list-buckets', DummyCtx())

    assert 'Invalid parameter value' in str(exc_info.value)
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
    mock_ir.command.is_help_operation = False
    mock_ir.command.is_help_operation = False
    mock_translate_cli_to_ir.return_value = mock_ir

    # Mock validation response with failed constraints
    mock_response = MagicMock()
    mock_response.validation_failures = None
    mock_response.failed_constraints = ['Resource limit exceeded']
    mock_response.model_dump_json.return_value = (
        '{"failed_constraints": ["Resource limit exceeded"]}'
    )
    mock_validate.return_value = mock_response

    # Execute and verify
    with pytest.raises(CommandValidationError) as exc_info:
        await call_aws('aws s3api list-buckets', DummyCtx())

    assert 'Resource limit exceeded' in str(exc_info.value)
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
    mock_ir.command.is_help_operation = False
    mock_ir.command.is_help_operation = False
    mock_translate_cli_to_ir.return_value = mock_ir

    # Mock validation response with both validation failures and failed constraints
    mock_response = MagicMock()
    mock_response.validation_failures = ['Invalid parameter value']
    mock_response.failed_constraints = ['Resource limit exceeded']
    mock_response.model_dump_json.return_value = '{"validation_failures": ["Invalid parameter value"], "failed_constraints": ["Resource limit exceeded"]}'
    mock_validate.return_value = mock_response

    # Execute and verify
    with pytest.raises(CommandValidationError) as exc_info:
        await call_aws('aws s3api list-buckets', DummyCtx())

    error_msg = str(exc_info.value)
    assert 'Invalid parameter value' in error_msg
    assert 'Resource limit exceeded' in error_msg
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
    mock_ir.command.is_help_operation = False
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
        'aws configure list',
        mock_ir.command,
        credentials=None,
        default_region_override=None,
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
    mock_ir.command.is_help_operation = False
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_is_operation_read_only.return_value = True

    mock_response = MagicMock()
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    mock_execute_awscli_customization.side_effect = AwsApiMcpError(
        "Error while executing 'aws configure list': Configuration file not found"
    )

    with pytest.raises(AwsApiMcpError) as exc_info:
        await call_aws('aws configure list', DummyCtx())

    assert 'Configuration file not found' in str(exc_info.value)
    mock_translate_cli_to_ir.assert_called_once_with('aws configure list')
    mock_validate.assert_called_once_with(mock_ir)
    mock_execute_awscli_customization.assert_called_once_with(
        'aws configure list',
        mock_ir.command,
        credentials=None,
        default_region_override=None,
    )


@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', None)
@patch('awslabs.aws_api_mcp_server.server.WORKING_DIRECTORY', '/tmp')
def test_main_missing_aws_region():
    """Test main function raises ValueError when AWS_REGION environment variable is not set."""
    with pytest.raises(ValueError, match=r'AWS_REGION environment variable is not defined.'):
        main()


@patch('awslabs.aws_api_mcp_server.server.os.chdir')
@patch('awslabs.aws_api_mcp_server.server.server')
@patch('awslabs.aws_api_mcp_server.server.get_read_only_operations')
@patch('awslabs.aws_api_mcp_server.server.READ_OPERATIONS_ONLY_MODE', True)
@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_api_mcp_server.server.WORKING_DIRECTORY', '/tmp')
@patch('awslabs.aws_api_mcp_server.server.TRANSPORT', 'stdio')
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


@patch('awslabs.aws_api_mcp_server.server.os.chdir')
@patch('awslabs.aws_api_mcp_server.server.server')
@patch('awslabs.aws_api_mcp_server.server.get_read_only_operations')
@patch('awslabs.aws_api_mcp_server.server.READ_OPERATIONS_ONLY_MODE', True)
@patch('awslabs.aws_api_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_api_mcp_server.server.WORKING_DIRECTORY', '/tmp')
@patch('awslabs.aws_api_mcp_server.server.TRANSPORT', 'streamable-http')
@patch('awslabs.aws_api_mcp_server.server.HOST', '0.0.0.0')
@patch('awslabs.aws_api_mcp_server.server.PORT', 8080)
@patch('awslabs.aws_api_mcp_server.server.STATELESS_HTTP', True)
def test_main_success_with_http_transport(
    mock_get_read_only_operations,
    mock_server,
    mock_chdir,
):
    """Test main function executes successfully with HTTP transport (else branch)."""
    mock_read_operations = MagicMock()
    mock_get_read_only_operations.return_value = mock_read_operations
    mock_server.run = MagicMock()

    main()

    mock_chdir.assert_called_once_with('/tmp')
    mock_get_read_only_operations.assert_called_once()
    mock_server.run.assert_called_once_with(
        transport='streamable-http',
        host='0.0.0.0',
        port=8080,
        stateless_http=True,
    )


@patch('awslabs.aws_api_mcp_server.core.common.config.ENABLE_AGENT_SCRIPTS', True)
async def test_get_execution_plan_is_available_when_env_var_is_set():
    """Test get_execution_plan returns script content when script exists."""
    # Re-import the server module to ensure the tool is registered
    import awslabs.aws_api_mcp_server.server
    import importlib

    importlib.reload(awslabs.aws_api_mcp_server.server)

    from awslabs.aws_api_mcp_server.server import server

    tools = await server.list_tools()
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

    tools = await server.list_tools()
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

        with pytest.raises(AwsApiMcpError) as exc_info:
            await get_execution_plan('non-existent-script', DummyCtx())

        assert 'Script non-existent-script not found' in str(exc_info.value)
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

        with pytest.raises(AwsApiMcpError) as exc_info:
            await get_execution_plan('test-script', DummyCtx())

        assert 'Test exception' in str(exc_info.value)


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
    mock_ir.command.is_help_operation = False
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

    mock_interpret.assert_called_once_with(
        cli_command='aws s3api list-buckets',
        max_results=None,
        credentials=test_credentials,
        default_region_override=None,
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
    mock_ir.command.is_help_operation = False
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
        cli_command='aws s3api list-buckets',
        max_results=None,
        credentials=None,
        default_region_override=None,
    )
    assert result == mock_response


@patch('awslabs.aws_api_mcp_server.server.call_aws_helper')
async def test_call_aws_delegates_to_helper(mock_call_aws_helper):
    """Test call_aws delegates to call_aws_helper with None credentials."""
    mock_response = MagicMock()
    mock_call_aws_helper.return_value = mock_response

    ctx = DummyCtx()

    result = await call_aws('aws s3api list-buckets', ctx)

    mock_call_aws_helper.assert_called_once_with(
        cli_command='aws s3api list-buckets', ctx=ctx, max_results=None, credentials=None
    )
    assert result == mock_response


@pytest.mark.parametrize(
    'service, operation',
    [
        ('s3', 'ls'),
        ('s3api', 'list-buckets'),
        ('ec2', 'describe-instances'),
        ('lambda', 'list-functions'),
        ('dynamodb', 'list-tables'),
        ('iam', 'get-user'),
        ('cloudwatch', 'get-metric-data'),
        ('apigateway', 'get-rest-apis'),
        ('rds', 'describe-db-instances'),
        ('sns', 'list-topics'),
        ('sqs', 'list-queues'),
        ('sts', 'get-caller-identity'),
        ('cloudformation', 'describe-stacks'),
        ('kms', 'list-keys'),
        ('elasticbeanstalk', 'describe-environments'),
        ('organizations', 'list-accounts'),
        ('ec2', 'describe-volumes'),
        ('ecs', 'list-clusters'),
        ('efs', 'describe-file-systems'),
        ('route53', 'list-hosted-zones'),
        ('lightsail', 'get-instances'),
    ],
)
async def test_call_aws_help_command_success(service, operation):
    """Test call_aws returns success response for help command."""
    help_document = generate_help_document(service, operation)
    assert help_document is not None
    expected_response = ProgramInterpretationResponse(
        response=InterpretationResponse(error=None, json=as_json(help_document), status_code=200),
        metadata=None,
        validation_failures=None,
        missing_context_failures=None,
        failed_constraints=None,
    )

    result = await call_aws(f'aws {service} {operation} help', DummyCtx())

    assert result == expected_response


@patch('awslabs.aws_api_mcp_server.server.get_help_document')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
async def test_call_aws_help_command_failure(
    mock_translate_cli_to_ir,
    mock_validate,
    mock_get_help_document,
):
    """Test call_aws raises error when help command fails."""
    mock_ir = MagicMock()
    mock_ir.command = MagicMock()
    mock_ir.command.is_awscli_customization = False
    mock_ir.command.is_help_operation = True
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_response = MagicMock()
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    mock_get_help_document.side_effect = AwsApiMcpError('Failed to generate help document')

    with pytest.raises(AwsApiMcpError) as exc_info:
        await call_aws('aws non-existing-service non-existing-operation help', DummyCtx())

    assert 'Failed to generate help document' in str(exc_info.value)
    mock_translate_cli_to_ir.assert_called_once_with(
        'aws non-existing-service non-existing-operation help'
    )
    mock_validate.assert_called_once_with(mock_ir)
    mock_get_help_document.assert_called_once()


# Tests for get_server_auth function
@patch('awslabs.aws_api_mcp_server.core.common.config.TRANSPORT', 'stdio')
def test_get_server_auth_non_streamable_http():
    """Test get_server_auth returns early when TRANSPORT is not 'streamable-http'."""
    auth_provider = get_server_auth()

    assert auth_provider is None


@patch('awslabs.aws_api_mcp_server.core.common.config.TRANSPORT', 'streamable-http')
@patch('awslabs.aws_api_mcp_server.core.common.config.AUTH_TYPE', 'no-auth')
def test_get_server_auth_streamable_http_no_auth():
    """Test get_server_auth with streamable-http transport but no-auth."""
    auth_provider = get_server_auth()

    assert auth_provider is None


@patch('awslabs.aws_api_mcp_server.core.common.config.TRANSPORT', 'streamable-http')
@patch('awslabs.aws_api_mcp_server.core.common.config.AUTH_TYPE', None)
def test_get_server_auth_auth_type_not_set():
    """Test get_server_auth raises ValueError when AUTH_TYPE is not set for streamable-http."""
    with pytest.raises(
        ValueError,
        match='TRANSPORT="streamable-http" requires the following environment variable to be set: AUTH_TYPE to `no-auth` or `oauth`',
    ):
        get_server_auth()


@patch('awslabs.aws_api_mcp_server.core.common.config.TRANSPORT', 'streamable-http')
@patch('awslabs.aws_api_mcp_server.core.common.config.AUTH_TYPE', 'invalid-auth-type')
def test_get_server_auth_invalid_auth_type():
    """Test get_server_auth raises ValueError when AUTH_TYPE has invalid value for streamable-http."""
    with pytest.raises(
        ValueError,
        match='TRANSPORT="streamable-http" requires the following environment variable to be set: AUTH_TYPE to `no-auth` or `oauth`',
    ):
        get_server_auth()


@patch('awslabs.aws_api_mcp_server.core.common.config.TRANSPORT', 'streamable-http')
@patch('awslabs.aws_api_mcp_server.core.common.config.AUTH_TYPE', 'oauth')
@patch('awslabs.aws_api_mcp_server.core.common.config.AUTH_ISSUER', None)
@patch('awslabs.aws_api_mcp_server.core.common.config.AUTH_JWKS_URI', 'https://example.com/jwks')
def test_get_server_auth_oauth_missing_issuer():
    """Test get_server_auth raises ValueError when AUTH_ISSUER is missing for oauth."""
    with pytest.raises(
        ValueError,
        match='AUTH_TYPE="oauth" requires the following environment variables to be set: AUTH_ISSUER and AUTH_JWKS_URI',
    ):
        get_server_auth()


@patch('awslabs.aws_api_mcp_server.core.common.config.TRANSPORT', 'streamable-http')
@patch('awslabs.aws_api_mcp_server.core.common.config.AUTH_TYPE', 'oauth')
@patch('awslabs.aws_api_mcp_server.core.common.config.AUTH_ISSUER', 'https://issuer.example.com')
@patch('awslabs.aws_api_mcp_server.core.common.config.AUTH_JWKS_URI', None)
def test_get_server_auth_oauth_missing_jwks_uri():
    """Test get_server_auth raises ValueError when AUTH_JWKS_URI is missing for oauth."""
    with pytest.raises(
        ValueError,
        match='AUTH_TYPE="oauth" requires the following environment variables to be set: AUTH_ISSUER and AUTH_JWKS_URI',
    ):
        get_server_auth()


@patch('awslabs.aws_api_mcp_server.core.common.config.TRANSPORT', 'streamable-http')
@patch('awslabs.aws_api_mcp_server.core.common.config.AUTH_TYPE', 'oauth')
@patch('awslabs.aws_api_mcp_server.core.common.config.AUTH_ISSUER', None)
@patch('awslabs.aws_api_mcp_server.core.common.config.AUTH_JWKS_URI', None)
def test_get_server_auth_oauth_missing_both():
    """Test get_server_auth raises ValueError when both AUTH_ISSUER and AUTH_JWKS_URI are missing for oauth."""
    with pytest.raises(
        ValueError,
        match='AUTH_TYPE="oauth" requires the following environment variables to be set: AUTH_ISSUER and AUTH_JWKS_URI',
    ):
        get_server_auth()


@patch('awslabs.aws_api_mcp_server.core.common.config.TRANSPORT', 'streamable-http')
@patch('awslabs.aws_api_mcp_server.core.common.config.AUTH_TYPE', 'oauth')
@patch('awslabs.aws_api_mcp_server.core.common.config.AUTH_ISSUER', 'https://issuer.example.com')
@patch('awslabs.aws_api_mcp_server.core.common.config.AUTH_JWKS_URI', 'https://example.com/jwks')
def test_get_server_auth_oauth_valid():
    """Test get_server_auth with valid oauth configuration."""
    auth_provider = get_server_auth()

    assert isinstance(auth_provider, JWTVerifier)

    # Verify the JWTVerifier is configured correctly
    assert auth_provider.issuer == 'https://issuer.example.com'
    assert auth_provider.jwks_uri == 'https://example.com/jwks'
