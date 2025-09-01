import pytest
from awslabs.aws_api_mcp_server.core.aws.service import (
    check_elicitation_support,
    check_security_policy,
)
from awslabs.aws_api_mcp_server.core.common.models import (
    AwsApiMcpServerErrorResponse,
    InterpretationResponse,
    IRTranslation,
    ProgramInterpretationResponse,
)
from awslabs.aws_api_mcp_server.core.metadata.read_only_operations_list import ReadOnlyOperations
from awslabs.aws_api_mcp_server.core.security.policy import PolicyDecision, SecurityPolicy
from awslabs.aws_api_mcp_server.server import call_aws
from pathlib import Path
from tests.fixtures import DummyCtx
from unittest.mock import MagicMock, Mock, mock_open, patch


# Core SecurityPolicy Tests
def test_security_policy_file_loading_success():
    """Test successful policy loading from files."""
    mock_policy_data = (
        '{"denylist": ["aws iam delete-user"], "elicitList": ["aws s3api put-object"]}'
    )

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=mock_policy_data)):
            policy = SecurityPolicy()

            assert 'aws iam delete-user' in policy.denylist
            assert 'aws s3api put-object' in policy.elicit_list


def test_security_policy_customization_file_loading():
    """Test successful customization loading from separate file."""
    mock_policy_data = '{"denylist": [], "elicitList": []}'
    mock_customization_data = (
        '{"customizations": {"s3 ls": {"api_calls": ["aws s3api list-buckets"]}}}'
    )

    def mock_open_side_effect(file_path, *args, **kwargs):
        if 'mcp-security-policy.json' in str(file_path):
            return mock_open(read_data=mock_policy_data)()
        elif 'aws_api_customization.json' in str(file_path):
            return mock_open(read_data=mock_customization_data)()
        return mock_open()()

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', side_effect=mock_open_side_effect):
            policy = SecurityPolicy()

            assert 's3 ls' in policy.customizations
            assert policy.customizations['s3 ls'] == ['aws s3api list-buckets']


def test_security_policy_file_not_found():
    """Test behavior when policy file doesn't exist."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()

        assert len(policy.denylist) == 0
        assert len(policy.elicit_list) == 0
        assert len(policy.customizations) == 0


def test_security_policy_file_error_handling():
    """Test error handling for policy and customization files."""
    # Test JSON parse error
    invalid_json = '{"denylist": ["aws iam delete-user"'  # Missing closing bracket
    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=invalid_json)):
            policy = SecurityPolicy()
            assert len(policy.denylist) == 0
            assert len(policy.elicit_list) == 0

    # Test IO error
    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', side_effect=IOError('File read error')):
            policy = SecurityPolicy()
            assert len(policy.denylist) == 0
            assert len(policy.elicit_list) == 0

    # Test customization JSON parse error
    mock_policy_data = '{"denylist": [], "elicitList": []}'
    invalid_customization_json = '{"customizations": {'  # Invalid JSON

    def mock_open_side_effect(file_path, *args, **kwargs):
        if 'mcp-security-policy.json' in str(file_path):
            return mock_open(read_data=mock_policy_data)()
        elif 'aws_api_customization.json' in str(file_path):
            return mock_open(read_data=invalid_customization_json)()
        return mock_open()()

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', side_effect=mock_open_side_effect):
            policy = SecurityPolicy()
            assert len(policy.customizations) == 0

    # Test customization IO error
    def mock_open_io_error(file_path, *args, **kwargs):
        if 'mcp-security-policy.json' in str(file_path):
            return mock_open(read_data=mock_policy_data)()
        elif 'aws_api_customization.json' in str(file_path):
            raise IOError('Customization file read error')
        return mock_open()()

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', side_effect=mock_open_io_error):
            policy = SecurityPolicy()
            assert len(policy.customizations) == 0


def test_security_policy_customization_file_not_found():
    """Test behavior when customization file doesn't exist."""
    mock_policy_data = '{"denylist": [], "elicitList": []}'

    # Mock exists to return True for policy file, False for customization file
    with patch.object(Path, 'exists', return_value=False):
        with patch('builtins.open', mock_open(read_data=mock_policy_data)):
            policy = SecurityPolicy()

            assert len(policy.customizations) == 0


def test_security_policy_customization_missing_api_calls():
    """Test customization loading when api_calls key is missing."""
    mock_policy_data = '{"denylist": [], "elicitList": []}'
    mock_customization_data = '{"customizations": {"s3 ls": {"other_key": "value"}}}'

    def mock_open_side_effect(file_path, *args, **kwargs):
        if 'mcp-security-policy.json' in str(file_path):
            return mock_open(read_data=mock_policy_data)()
        elif 'aws_api_customization.json' in str(file_path):
            return mock_open(read_data=mock_customization_data)()
        return mock_open()()

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', side_effect=mock_open_side_effect):
            policy = SecurityPolicy()

            assert 's3 ls' not in policy.customizations


def test_security_policy_deny_takes_priority():
    """Test that denylist takes priority over elicitList."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.denylist = {'aws s3api list-buckets'}
        policy.elicit_list = {'aws s3api list-buckets'}

        decision = policy.get_decision('s3api', 'list_buckets', True, True)
        assert decision == PolicyDecision.DENY


def test_security_policy_s3_service_mapping():
    """Test S3 service mapping to s3api in CLI operations."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()

        # Test denylist mapping
        policy.denylist = {'aws s3api list-buckets'}
        decision = policy.get_decision('s3', 'list_buckets', True, True)
        assert decision == PolicyDecision.DENY

        # Test elicit list mapping
        policy.denylist = set()
        policy.elicit_list = {'aws s3api put-object'}
        decision = policy.get_decision('s3', 'put_object', False, True)
        assert decision == PolicyDecision.ELICIT

        # Test both variants in denylist
        policy.denylist = {'aws s3 ls', 'aws s3api list-buckets'}
        policy.elicit_list = set()
        decision = policy.get_decision('s3', 'list_buckets', True, True)
        assert decision == PolicyDecision.DENY

        # Test both variants in elicit list
        policy.denylist = set()
        policy.elicit_list = {'aws s3 cp', 'aws s3api put-object'}
        decision = policy.get_decision('s3', 'put_object', False, True)
        assert decision == PolicyDecision.ELICIT


def test_security_policy_elicit_fallback_to_deny():
    """Test elicitation fallback to deny when client doesn't support it."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.elicit_list = {'aws s3api put-object'}

        decision = policy.get_decision('s3api', 'put_object', False, False)
        assert decision == PolicyDecision.DENY


def test_security_policy_default_behavior():
    """Test default behavior for all operation types."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()

        # Test read-only operations are allowed
        decision = policy.get_decision('s3api', 'list_buckets', True, True)
        assert decision == PolicyDecision.ALLOW

        # Test mutations are allowed by default (with elicitation support)
        decision = policy.get_decision('s3api', 'put_object', False, True)
        assert decision == PolicyDecision.ALLOW

        # Test mutations are allowed by default (without elicitation support)
        decision = policy.get_decision('s3api', 'put_object', False, False)
        assert decision == PolicyDecision.ALLOW


def test_security_policy_operation_name_conversion():
    """Test operation name conversion from various formats to kebab-case."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.denylist = {'aws s3api list-buckets', 'aws s3api list-objects-v2'}

        # Test camelCase operation name gets converted
        decision = policy.get_decision('s3api', 'ListBuckets', True, True)
        assert decision == PolicyDecision.DENY

        # Test operation name with multiple capitals
        decision = policy.get_decision('s3api', 'ListObjectsV2', True, True)
        assert decision == PolicyDecision.DENY

        # Test operation name already in kebab-case
        decision = policy.get_decision('s3api', 'list-buckets', True, True)
        assert decision == PolicyDecision.DENY


# Customization Tests
def test_security_policy_customization_parent_deny():
    """Test customization when parent command is in denylist."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.denylist = {'aws s3 ls'}
        policy.customizations = {'s3 ls': ['aws s3api list-buckets']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation == 'list_buckets'

        decision = policy.check_customization('aws s3 ls my-bucket', mock_is_read_only, True)
        assert decision == PolicyDecision.DENY


def test_security_policy_customization_parent_elicit():
    """Test customization when parent command is in elicit list."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.elicit_list = {'aws s3 ls'}
        policy.customizations = {'s3 ls': ['aws s3api list-buckets']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation == 'list_buckets'

        decision = policy.check_customization('aws s3 ls my-bucket', mock_is_read_only, True)
        assert decision == PolicyDecision.ELICIT


def test_security_policy_customization_parent_elicit_no_support():
    """Test customization when parent is in elicit list but elicitation not supported."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.elicit_list = {'aws s3 ls'}
        policy.customizations = {'s3 ls': ['aws s3api list-buckets']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation == 'list_buckets'

        decision = policy.check_customization('aws s3 ls my-bucket', mock_is_read_only, False)
        assert decision == PolicyDecision.DENY


def test_security_policy_customization_child_deny():
    """Test customization when child API call is in denylist."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.denylist = {'aws s3api list-buckets'}
        policy.customizations = {'s3 ls': ['aws s3api list-buckets', 'aws s3api list-objects-v2']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation in ['list_buckets', 'list_objects_v2']

        decision = policy.check_customization('aws s3 ls my-bucket', mock_is_read_only, True)
        assert decision == PolicyDecision.DENY


def test_security_policy_customization_child_elicit():
    """Test customization when child API call is in elicit list."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.elicit_list = {'aws s3api list-objects-v2'}
        policy.customizations = {'s3 ls': ['aws s3api list-buckets', 'aws s3api list-objects-v2']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation in ['list_buckets', 'list_objects_v2']

        decision = policy.check_customization('aws s3 ls my-bucket', mock_is_read_only, True)
        assert decision == PolicyDecision.ELICIT


def test_security_policy_customization_child_elicit_no_support():
    """Test customization when child is in elicit list but elicitation not supported."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.elicit_list = {'aws s3api list-objects-v2'}
        policy.customizations = {'s3 ls': ['aws s3api list-buckets', 'aws s3api list-objects-v2']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation in ['list_buckets', 'list_objects_v2']

        decision = policy.check_customization('aws s3 ls my-bucket', mock_is_read_only, False)
        assert decision == PolicyDecision.DENY


def test_security_policy_customization_mixed_decisions_deny_wins():
    """Test customization with mixed decisions - deny should win."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.denylist = {'aws s3api list-buckets'}
        policy.elicit_list = {'aws s3api list-objects-v2'}
        policy.customizations = {'s3 ls': ['aws s3api list-buckets', 'aws s3api list-objects-v2']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation in ['list_buckets', 'list_objects_v2']

        decision = policy.check_customization('aws s3 ls my-bucket', mock_is_read_only, True)
        assert decision == PolicyDecision.DENY


def test_security_policy_customization_all_allowed():
    """Test customization when all child API calls are allowed."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.customizations = {'s3 ls': ['aws s3api list-buckets', 'aws s3api list-objects-v2']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation in ['list_buckets', 'list_objects_v2']

        decision = policy.check_customization('aws s3 ls my-bucket', mock_is_read_only, True)
        assert decision == PolicyDecision.ALLOW


def test_security_policy_customization_no_match():
    """Test customization when command doesn't match any customization."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.customizations = {'s3 ls': ['aws s3api list-buckets']}

        def mock_is_read_only(service, operation):
            return True

        decision = policy.check_customization(
            'aws ec2 describe-instances', mock_is_read_only, True
        )
        assert decision is None


def test_security_policy_customization_invalid_command():
    """Test customization with invalid command format."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.customizations = {'s3 ls': ['aws s3api list-buckets']}

        def mock_is_read_only(service, operation):
            return True

        # Test with command that doesn't start with 'aws'
        decision = policy.check_customization('s3 ls my-bucket', mock_is_read_only, True)
        assert decision is None

        # Test with command that has less than 3 parts
        decision = policy.check_customization('aws s3', mock_is_read_only, True)
        assert decision is None


def test_security_policy_customization_invalid_api_call():
    """Test customization with invalid API call format in customizations."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.customizations = {'s3 ls': ['invalid-api-call', 'aws s3api list-buckets']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation == 'list_buckets'

        decision = policy.check_customization('aws s3 ls my-bucket', mock_is_read_only, True)
        assert decision == PolicyDecision.ALLOW


# Integration Tests
@patch('awslabs.aws_api_mcp_server.core.aws.service.security_policy')
def test_check_security_policy_customization_deny(mock_security_policy):
    """Test security policy integration when customization returns deny."""
    mock_security_policy.check_customization.return_value = PolicyDecision.DENY

    mock_ctx = Mock()
    mock_ctx.elicit = Mock()

    mock_read_only_ops = Mock(spec=ReadOnlyOperations)
    mock_ir = Mock(spec=IRTranslation)
    mock_ir.command_metadata = Mock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list_buckets'

    decision = check_security_policy('aws s3 ls', mock_ir, mock_read_only_ops, mock_ctx)

    assert decision == PolicyDecision.DENY
    mock_security_policy.check_customization.assert_called_once()


@patch('awslabs.aws_api_mcp_server.core.aws.service.security_policy')
def test_check_security_policy_no_customization(mock_security_policy):
    """Test security policy integration when no customization matches."""
    mock_security_policy.check_customization.return_value = None
    mock_security_policy.get_decision.return_value = PolicyDecision.ALLOW

    mock_ctx = Mock()
    mock_ctx.elicit = Mock()

    mock_read_only_ops = Mock(spec=ReadOnlyOperations)
    mock_ir = Mock(spec=IRTranslation)
    mock_ir.command_metadata = Mock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list_buckets'

    decision = check_security_policy(
        'aws s3api list-buckets', mock_ir, mock_read_only_ops, mock_ctx
    )

    assert decision == PolicyDecision.ALLOW
    mock_security_policy.get_decision.assert_called_once()


def test_security_policy_customization_missing_customizations_key():
    """Test customization loading when customizations key is missing."""
    mock_policy_data = '{"denylist": [], "elicitList": []}'
    mock_customization_data = '{"other_key": "value"}'  # Missing customizations key

    def mock_open_side_effect(file_path, *args, **kwargs):
        if 'mcp-security-policy.json' in str(file_path):
            return mock_open(read_data=mock_policy_data)()
        elif 'aws_api_customization.json' in str(file_path):
            return mock_open(read_data=mock_customization_data)()
        return mock_open()()

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', side_effect=mock_open_side_effect):
            policy = SecurityPolicy()

            assert len(policy.customizations) == 0


def test_check_customization_empty_decisions():
    """Test check_customization when all decisions are ALLOW."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.customizations = {'s3 ls': ['aws s3api list-buckets']}

        def mock_is_read_only(service, operation):
            return True  # All operations are read-only

        decision = policy.check_customization('aws s3 ls my-bucket', mock_is_read_only, True)
        assert decision == PolicyDecision.ALLOW


def test_check_customization_elicit_priority():
    """Test check_customization when some decisions are ELICIT."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.elicit_list = {'aws s3api put-object'}  # Explicitly add to elicit list
        policy.customizations = {'s3 sync': ['aws s3api list-buckets', 'aws s3api put-object']}

        def mock_is_read_only(service, operation):
            return operation == 'list_buckets'  # Only list-buckets is read-only

        decision = policy.check_customization('aws s3 sync source dest', mock_is_read_only, True)
        assert decision == PolicyDecision.ELICIT


# Server Integration Tests
@patch('awslabs.aws_api_mcp_server.server.interpret_command')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.server.check_security_policy')
@patch('awslabs.aws_api_mcp_server.server.READ_OPERATIONS_INDEX', MagicMock())
async def test_call_aws_security_policy_deny(
    mock_check_security_policy,
    mock_translate_cli_to_ir,
    mock_validate,
    mock_interpret,
):
    """Test call_aws when security policy denies the operation."""
    # Mock IR and validation
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command.is_awscli_customization = False
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_validation = MagicMock()
    mock_validation.validation_failed = False
    mock_validate.return_value = mock_validation

    # Mock security policy to return DENY
    mock_check_security_policy.return_value = PolicyDecision.DENY

    ctx = DummyCtx()

    result = await call_aws('aws s3 rm s3://bucket/file', ctx)

    assert isinstance(result, AwsApiMcpServerErrorResponse)
    assert result.detail == 'Execution of this operation is denied by security policy.'
    mock_check_security_policy.assert_called_once()


@patch('awslabs.aws_api_mcp_server.server.interpret_command')
@patch('awslabs.aws_api_mcp_server.server.validate')
@patch('awslabs.aws_api_mcp_server.server.translate_cli_to_ir')
@patch('awslabs.aws_api_mcp_server.server.check_security_policy')
@patch('awslabs.aws_api_mcp_server.server.request_consent')
@patch('awslabs.aws_api_mcp_server.server.READ_OPERATIONS_INDEX', MagicMock())
async def test_call_aws_security_policy_elicit(
    mock_request_consent,
    mock_check_security_policy,
    mock_translate_cli_to_ir,
    mock_validate,
    mock_interpret,
):
    """Test call_aws when security policy requires elicitation."""
    # Mock IR and validation
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command.is_awscli_customization = False
    mock_translate_cli_to_ir.return_value = mock_ir

    mock_validation = MagicMock()
    mock_validation.validation_failed = False
    mock_validate.return_value = mock_validation

    # Mock security policy to return ELICIT
    mock_check_security_policy.return_value = PolicyDecision.ELICIT

    # Mock interpret_command to return success
    mock_response = InterpretationResponse(
        error=None, json='{"result": "success"}', status_code=200
    )
    mock_result = ProgramInterpretationResponse(
        response=mock_response,
        metadata=None,
        validation_failures=None,
        missing_context_failures=None,
        failed_constraints=None,
    )
    mock_interpret.return_value = mock_result

    ctx = DummyCtx()

    result = await call_aws('aws s3api put-object --bucket test --key test', ctx)

    mock_check_security_policy.assert_called_once()
    mock_request_consent.assert_called_once_with(
        'aws s3api put-object --bucket test --key test', ctx
    )
    assert isinstance(result, ProgramInterpretationResponse)


@pytest.mark.asyncio
async def test_check_elicitation_support():
    """Test elicitation support checking."""
    # Test when context has elicit method
    ctx = MagicMock()
    ctx.elicit = MagicMock()
    result = check_elicitation_support(ctx)
    assert result is True

    # Test when context doesn't have elicit method
    ctx = MagicMock()
    del ctx.elicit
    result = check_elicitation_support(ctx)
    assert result is False

    # Test when hasattr raises exception
    ctx = MagicMock()
    with patch('builtins.hasattr', side_effect=Exception('Test exception')):
        result = check_elicitation_support(ctx)

        assert result is False


@patch('awslabs.aws_api_mcp_server.core.aws.service.security_policy')
def test_is_read_only_func_in_check_security_policy(mock_security_policy):
    """Test the is_read_only_func lambda inside check_security_policy."""
    mock_security_policy.check_customization.return_value = None
    mock_security_policy.get_decision.return_value = PolicyDecision.ALLOW

    mock_ctx = MagicMock()
    mock_read_only_ops = MagicMock(spec=ReadOnlyOperations)
    mock_read_only_ops.has.return_value = True

    mock_ir = MagicMock(spec=IRTranslation)
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 's3api'
    mock_ir.command_metadata.operation_sdk_name = 'list_buckets'

    # Call check_security_policy which will use the is_read_only_func
    result = check_security_policy('aws s3api list-buckets', mock_ir, mock_read_only_ops, mock_ctx)

    # Verify that read_only_operations.has was called (via is_read_only_func)
    mock_read_only_ops.has.assert_called_with(service='s3api', operation='list_buckets')
    assert result == PolicyDecision.ALLOW
