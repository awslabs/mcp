from awslabs.aws_mcp_server.core.common.errors import AwsMcpError
from awslabs.aws_mcp_server.core.common.models import RequireConsentResponse
from awslabs.aws_mcp_server.server import call_aws
from botocore.exceptions import NoCredentialsError
from tests.fixtures import TEST_CREDENTIALS
from unittest.mock import MagicMock, patch


@patch('awslabs.aws_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_mcp_server.server.get_local_credentials')
@patch('awslabs.aws_mcp_server.server.interpret_command')
@patch('awslabs.aws_mcp_server.server.validate')
@patch('awslabs.aws_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_mcp_server.server.check_for_consent')
@patch('awslabs.aws_mcp_server.server.is_operation_read_only')
def test_call_aws_success(
    mock_is_operation_read_only,
    mock_check_for_consent,
    mock_translate_cli_to_ir,
    mock_validate,
    mock_interpret,
    mock_get_creds,
):
    """Test call_aws returns success for a valid read-only command."""
    mock_get_creds.return_value = TEST_CREDENTIALS
    mock_result = MagicMock()
    mock_result.model_dump.return_value = {
        'success': True,
        'data': {'Buckets': []},
        'ResponseMetadata': {'HTTPStatusCode': 200},
    }
    mock_interpret.return_value = mock_result

    mock_is_operation_read_only.return_value = True

    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
    mock_translate_cli_to_ir.return_value = mock_ir

    # Mock response with classification that doesn't require consent
    mock_response = MagicMock()
    mock_response.classification = MagicMock()
    mock_response.classification.action_types = ['read-only']
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    # Mock check_for_consent returns false
    mock_check_for_consent.return_value = None

    # Execute
    result = call_aws('aws s3api list-buckets')

    # Verify
    assert result == {
        'success': True,
        'data': {'Buckets': []},
        'ResponseMetadata': {'HTTPStatusCode': 200},
    }
    mock_translate_cli_to_ir.assert_called_once_with('aws s3api list-buckets')
    mock_validate.assert_called_once_with(mock_ir)
    mock_check_for_consent.assert_called_once_with(
        cli_command='aws s3api list-buckets',
        ir=mock_ir,
        consent_token=None,
    )
    mock_get_creds.assert_called_once()
    mock_interpret.assert_called_once()


@patch('awslabs.aws_mcp_server.server.validate')
@patch('awslabs.aws_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_mcp_server.server.check_for_consent')
@patch('awslabs.aws_mcp_server.server.is_operation_read_only')
def test_call_aws_with_consent_response(
    mock_is_operation_read_only, mock_check_for_consent, mock_translate_cli_to_ir, mock_validate
):
    """Test call_aws returns consent required response when consent is needed."""
    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
    mock_translate_cli_to_ir.return_value = mock_ir

    # Mock response with classification that doesn't require consent
    mock_response = MagicMock()
    mock_response.classification = MagicMock()
    mock_response.classification.action_types = ['read-only']
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    # Mock check_for_consent returns false
    mock_check_for_consent.return_value = RequireConsentResponse(
        status='consent_required', message='some test message'
    )

    # Execute
    result = call_aws('aws s3api list-buckets')

    # Verify
    assert result == {'status': 'consent_required', 'message': 'some test message'}
    mock_translate_cli_to_ir.assert_called_once_with('aws s3api list-buckets')
    mock_validate.assert_called_once_with(mock_ir)
    mock_check_for_consent.assert_called_once_with(
        cli_command='aws s3api list-buckets',
        ir=mock_ir,
        consent_token=None,
    )


@patch('awslabs.aws_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_mcp_server.server.get_local_credentials')
@patch('awslabs.aws_mcp_server.server.interpret_command')
@patch('awslabs.aws_mcp_server.server.validate')
@patch('awslabs.aws_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_mcp_server.server.check_for_consent')
@patch('awslabs.aws_mcp_server.server.is_operation_read_only')
@patch('awslabs.aws_mcp_server.server.BYPASS_TOOL_CONSENT', True)
def test_call_aws_with_bypass_consent(
    mock_is_operation_read_only,
    mock_check_for_consent,
    mock_translate_cli_to_ir,
    mock_validate,
    mock_interpret,
    mock_get_creds,
):
    """Test call_aws bypasses consent when BYPASS_TOOL_CONSENT is True."""
    mock_get_creds.return_value = TEST_CREDENTIALS
    mock_result = MagicMock()
    mock_result.model_dump.return_value = {
        'success': True,
        'data': {'Buckets': []},
        'ResponseMetadata': {'HTTPStatusCode': 200},
    }
    mock_interpret.return_value = mock_result

    mock_is_operation_read_only.return_value = True

    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
    mock_translate_cli_to_ir.return_value = mock_ir

    # Mock response with classification that passes validation
    mock_response = MagicMock()
    mock_response.classification = MagicMock()
    mock_response.classification.action_types = ['read-only']
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    # Execute
    result = call_aws('aws s3api list-buckets')

    # Verify that consent check was bypassed and command executed successfully
    assert result == {
        'success': True,
        'data': {'Buckets': []},
        'ResponseMetadata': {'HTTPStatusCode': 200},
    }
    mock_translate_cli_to_ir.assert_called_once_with('aws s3api list-buckets')
    mock_validate.assert_called_once_with(mock_ir)
    mock_check_for_consent.assert_not_called()
    mock_get_creds.assert_called_once()
    mock_interpret.assert_called_once()


@patch('awslabs.aws_mcp_server.server.translate_cli_to_ir')
def test_call_aws_validation_error_awsmcp_error(mock_translate_cli_to_ir):
    """Test call_aws returns error details for AwsMcpError during validation."""
    mock_error = AwsMcpError('Invalid command syntax')
    mock_failure = MagicMock()
    mock_failure.reason = 'Invalid command syntax'
    mock_error.as_failure = MagicMock(return_value=mock_failure)
    mock_translate_cli_to_ir.side_effect = mock_error

    # Execute
    result = call_aws('aws invalid-service invalid-operation')

    # Verify
    assert result == {
        'error': True,
        'detail': 'Error while validating the command: Invalid command syntax',
    }
    mock_translate_cli_to_ir.assert_called_once_with('aws invalid-service invalid-operation')


@patch('awslabs.aws_mcp_server.server.translate_cli_to_ir')
def test_call_aws_validation_error_generic_exception(mock_translate_cli_to_ir):
    """Test call_aws returns error details for generic exception during validation."""
    mock_translate_cli_to_ir.side_effect = ValueError('Generic validation error')

    # Execute
    result = call_aws('aws s3api list-buckets')

    # Verify
    assert result == {
        'error': True,
        'detail': 'Error while validating the command: Generic validation error',
    }


@patch('awslabs.aws_mcp_server.server.get_local_credentials')
@patch('awslabs.aws_mcp_server.server.validate')
@patch('awslabs.aws_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_mcp_server.server.is_operation_read_only')
def test_call_aws_no_credentials_error(
    mock_is_operation_read_only, mock_translate_cli_to_ir, mock_validate, mock_get_creds
):
    """Test call_aws returns error when no AWS credentials are found."""
    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_is_operation_read_only.return_value = True

    # Mock validation response
    mock_response = MagicMock()
    mock_response.classification = MagicMock()
    mock_response.classification.action_types = ['read-only']
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    mock_get_creds.side_effect = NoCredentialsError()

    # Execute
    result = call_aws('aws s3api list-buckets')

    # Verify
    assert result == {
        'error': True,
        'detail': 'Error while executing the command: No AWS credentials found. '
        "Please configure your AWS credentials using 'aws configure' "
        'or set appropriate environment variables.',
    }


@patch('awslabs.aws_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_mcp_server.server.get_local_credentials')
@patch('awslabs.aws_mcp_server.server.interpret_command')
@patch('awslabs.aws_mcp_server.server.validate')
@patch('awslabs.aws_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_mcp_server.server.is_operation_read_only')
def test_call_aws_execution_error_awsmcp_error(
    mock_is_operation_read_only,
    mock_translate_cli_to_ir,
    mock_validate,
    mock_interpret,
    mock_get_creds,
):
    """Test call_aws returns error details for AwsMcpError during execution."""
    mock_get_creds.return_value = TEST_CREDENTIALS

    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_is_operation_read_only.return_value = True

    # Mock validation response
    mock_response = MagicMock()
    mock_response.classification = MagicMock()
    mock_response.classification.action_types = ['read-only']
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    mock_error = AwsMcpError('Execution failed')
    mock_failure = MagicMock()
    mock_failure.reason = 'Execution failed'
    mock_error.as_failure = MagicMock(return_value=mock_failure)
    mock_interpret.side_effect = mock_error

    # Execute
    result = call_aws('aws s3api list-buckets')

    # Verify
    assert result == {
        'error': True,
        'detail': 'Error while executing the command: Execution failed',
    }


@patch('awslabs.aws_mcp_server.server.DEFAULT_REGION', 'us-east-1')
@patch('awslabs.aws_mcp_server.server.get_local_credentials')
@patch('awslabs.aws_mcp_server.server.interpret_command')
@patch('awslabs.aws_mcp_server.server.validate')
@patch('awslabs.aws_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_mcp_server.server.is_operation_read_only')
def test_call_aws_execution_error_generic_exception(
    mock_is_operation_read_only,
    mock_translate_cli_to_ir,
    mock_validate,
    mock_interpret,
    mock_get_creds,
):
    """Test call_aws returns error details for generic exception during execution."""
    mock_get_creds.return_value = TEST_CREDENTIALS

    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_is_operation_read_only.return_value = True

    # Mock validation response
    mock_response = MagicMock()
    mock_response.classification = MagicMock()
    mock_response.classification.action_types = ['read-only']
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    mock_interpret.side_effect = RuntimeError('Generic execution error')

    # Execute
    result = call_aws('aws s3api list-buckets')

    # Verify
    assert result == {
        'error': True,
        'detail': 'Error while executing the command: Generic execution error',
    }


def test_call_aws_non_aws_command():
    """Test call_aws with command that doesn't start with 'aws'."""
    with patch('awslabs.aws_mcp_server.server.translate_cli_to_ir') as mock_translate_cli_to_ir:
        mock_translate_cli_to_ir.side_effect = ValueError("Command must start with 'aws'")

        result = call_aws('s3api list-buckets')

        assert result == {
            'error': True,
            'detail': "Error while validating the command: Command must start with 'aws'",
        }


@patch('awslabs.aws_mcp_server.server.validate')
@patch('awslabs.aws_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_mcp_server.server.is_operation_read_only')
@patch('awslabs.aws_mcp_server.server.READ_OPERATIONS_ONLY_MODE')
def test_when_operation_is_not_allowed(
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
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_read_operations_only_mode.return_value = True

    # Mock validation response
    mock_response = MagicMock()
    mock_response.classification = MagicMock()
    mock_response.classification.action_types = ['read-only']
    mock_response.validation_failed = False
    mock_validate.return_value = mock_response

    mock_is_operation_read_only.return_value = False

    # Execute
    result = call_aws('aws s3api list-buckets')

    # verify
    assert result['error']
    assert (
        'Execution of this operation is not allowed because read only mode is enabled'
        in result['detail']
    )


@patch('awslabs.aws_mcp_server.server.validate')
@patch('awslabs.aws_mcp_server.server.translate_cli_to_ir')
def test_call_aws_validation_failures(mock_translate_cli_to_ir, mock_validate):
    """Test call_aws returns error for validation failures."""
    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
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
    result = call_aws('aws s3api list-buckets')

    # Verify
    assert result == {
        'error': True,
        'detail': 'Error while validating the command: {"validation_failures": ["Invalid parameter value"]}',
    }
    mock_translate_cli_to_ir.assert_called_once_with('aws s3api list-buckets')
    mock_validate.assert_called_once_with(mock_ir)


@patch('awslabs.aws_mcp_server.server.validate')
@patch('awslabs.aws_mcp_server.server.translate_cli_to_ir')
def test_call_aws_failed_constraints(mock_translate_cli_to_ir, mock_validate):
    """Test call_aws returns error for failed constraints."""
    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
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
    result = call_aws('aws s3api list-buckets')

    # Verify
    assert result == {
        'error': True,
        'detail': 'Error while validating the command: {"failed_constraints": ["Resource limit exceeded"]}',
    }
    mock_translate_cli_to_ir.assert_called_once_with('aws s3api list-buckets')
    mock_validate.assert_called_once_with(mock_ir)


@patch('awslabs.aws_mcp_server.server.validate')
@patch('awslabs.aws_mcp_server.server.translate_cli_to_ir')
def test_call_aws_both_validation_failures_and_constraints(
    mock_translate_cli_to_ir, mock_validate
):
    """Test call_aws returns error for both validation failures and failed constraints."""
    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list-buckets'
    mock_translate_cli_to_ir.return_value = mock_ir

    # Mock validation response with both validation failures and failed constraints
    mock_response = MagicMock()
    mock_response.validation_failures = ['Invalid parameter value']
    mock_response.failed_constraints = ['Resource limit exceeded']
    mock_response.model_dump_json.return_value = '{"validation_failures": ["Invalid parameter value"], "failed_constraints": ["Resource limit exceeded"]}'
    mock_validate.return_value = mock_response

    # Execute
    result = call_aws('aws s3api list-buckets')

    # Verify
    assert result == {
        'error': True,
        'detail': 'Error while validating the command: {"validation_failures": ["Invalid parameter value"], "failed_constraints": ["Resource limit exceeded"]}',
    }
    mock_translate_cli_to_ir.assert_called_once_with('aws s3api list-buckets')
    mock_validate.assert_called_once_with(mock_ir)
