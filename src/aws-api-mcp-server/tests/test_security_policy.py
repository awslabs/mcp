import json
import pytest
from awslabs.aws_api_mcp_server.core.aws.service import (
    check_security_policy,
)
from awslabs.aws_api_mcp_server.core.common.models import (
    AwsApiMcpServerErrorResponse,
    InterpretationResponse,
    IRTranslation,
    ProgramInterpretationResponse,
)
from awslabs.aws_api_mcp_server.core.metadata.read_only_operations_list import ReadOnlyOperations
from awslabs.aws_api_mcp_server.core.security.policy import (
    PolicyDecision,
    SecurityPolicy,
    check_elicitation_support,
)
from awslabs.aws_api_mcp_server.server import call_aws
from pathlib import Path
from tests.fixtures import DummyCtx
from unittest.mock import MagicMock, Mock, mock_open, patch


def create_mock_ir(service: str, operation: str):
    """Helper function to create mock IR objects for testing."""
    mock_ir = Mock(spec=IRTranslation)
    mock_ir.command_metadata = Mock()
    mock_ir.command_metadata.service_sdk_name = service
    mock_ir.command_metadata.operation_sdk_name = operation
    return mock_ir


def create_mock_ctx(supports_elicitation=True):
    """Helper function to create mock context for testing."""
    mock_ctx = Mock()
    if supports_elicitation:
        mock_ctx.elicit = Mock()
    else:
        # Remove elicit attribute to simulate no elicitation support
        if hasattr(mock_ctx, 'elicit'):
            delattr(mock_ctx, 'elicit')
    return mock_ctx


# Core SecurityPolicy Tests
def test_security_policy_file_loading_success():
    """Test successful policy loading from files."""
    mock_policy_data = '{"version":"1.0","policy":{"denyList":["aws iam delete-user"],"elicitList":["aws s3api put-object"]}}'

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=mock_policy_data)):
            mock_ctx = create_mock_ctx(supports_elicitation=True)
            policy = SecurityPolicy(mock_ctx)

            assert 'aws iam delete-user' in policy.denylist
            assert 'aws s3api put-object' in policy.elicit_list
            assert policy.supports_elicitation is True


def test_security_policy_file_loading_empty():
    """Test successful policy loading empty file."""
    mock_policy_data = '{}'

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=mock_policy_data)):
            mock_ctx = create_mock_ctx(supports_elicitation=True)
            policy = SecurityPolicy(mock_ctx)

            assert not policy.denylist
            assert not policy.elicit_list


def test_security_policy_customization_file_loading():
    """Test successful customization loading from separate file."""
    mock_policy_data = '{"version":"1.0","policy":{"denyList":[],"elicitList":[]}}'
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
            policy = SecurityPolicy(create_mock_ctx())

            assert 's3 ls' in policy.customizations
            assert policy.customizations['s3 ls'] == ['aws s3api list-buckets']


def test_security_policy_file_not_found():
    """Test behavior when policy file doesn't exist."""
    with patch.object(Path, 'exists', return_value=False):
        mock_ctx = create_mock_ctx(supports_elicitation=True)
        policy = SecurityPolicy(mock_ctx)

        assert len(policy.denylist) == 0
        assert len(policy.elicit_list) == 0
        assert len(policy.customizations) == 0


def test_security_policy_file_error_handling():
    """Test error handling for policy and customization files."""
    # Test JSON parse error in policy file (should be handled gracefully)
    invalid_policy_json = (
        '{"version":"1.0","policy":{"denyList": ["aws iam delete-user"'  # Missing closing bracket
    )
    valid_customization_json = '{"customizations": {}}'

    def mock_open_side_effect(file_path, *args, **kwargs):
        if 'mcp-security-policy.json' in str(file_path):
            return mock_open(read_data=invalid_policy_json)()
        elif 'aws_api_customization.json' in str(file_path):
            return mock_open(read_data=valid_customization_json)()
        return mock_open()()

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', side_effect=mock_open_side_effect):
            policy = SecurityPolicy(create_mock_ctx())
            assert len(policy.denylist) == 0
            assert len(policy.elicit_list) == 0

    # Test IO error in policy file (should be handled gracefully)
    def mock_open_io_error(file_path, *args, **kwargs):
        if 'mcp-security-policy.json' in str(file_path):
            raise IOError('File read error')
        elif 'aws_api_customization.json' in str(file_path):
            return mock_open(read_data=valid_customization_json)()
        return mock_open()()

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', side_effect=mock_open_io_error):
            policy = SecurityPolicy(create_mock_ctx())
            assert len(policy.denylist) == 0
            assert len(policy.elicit_list) == 0

    # Test customization JSON parse error (should raise since we control this file)
    mock_policy_data = '{"version":"1.0","policy":{"denyList":[],"elicitList":[]}}'
    invalid_customization_json = '{"customizations": {'  # Invalid JSON

    def mock_open_customization_error(file_path, *args, **kwargs):
        if 'mcp-security-policy.json' in str(file_path):
            return mock_open(read_data=mock_policy_data)()
        elif 'aws_api_customization.json' in str(file_path):
            return mock_open(read_data=invalid_customization_json)()
        return mock_open()()

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', side_effect=mock_open_customization_error):
            with pytest.raises(json.JSONDecodeError):
                SecurityPolicy()

    # Test customization IO error (should raise since we control this file)
    def mock_open_customization_io_error(file_path, *args, **kwargs):
        if 'mcp-security-policy.json' in str(file_path):
            return mock_open(read_data=mock_policy_data)()
        elif 'aws_api_customization.json' in str(file_path):
            raise IOError('Customization file read error')
        return mock_open()()

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', side_effect=mock_open_customization_io_error):
            with pytest.raises(IOError):
                SecurityPolicy()


def test_security_policy_customization_file_not_found():
    """Test behavior when customization file doesn't exist - should raise error."""
    mock_policy_data = '{"version":"1.0","policy":{"denyList":[],"elicitList":[]}}'

    def mock_open_side_effect(file_path, *args, **kwargs):
        if 'mcp-security-policy.json' in str(file_path):
            return mock_open(read_data=mock_policy_data)()
        elif 'aws_api_customization.json' in str(file_path):
            raise FileNotFoundError('Customization file not found')
        return mock_open()()

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', side_effect=mock_open_side_effect):
            with pytest.raises(FileNotFoundError):
                SecurityPolicy()


def test_security_policy_customization_missing_api_calls():
    """Test customization loading when api_calls key is missing - should load empty list."""
    mock_policy_data = '{"version":"1.0","policy":{"denyList":[],"elicitList":[]}}'
    mock_customization_data = '{"customizations": {"s3 ls": {"other_key": "value"}}}'

    def mock_open_side_effect(file_path, *args, **kwargs):
        if 'mcp-security-policy.json' in str(file_path):
            return mock_open(read_data=mock_policy_data)()
        elif 'aws_api_customization.json' in str(file_path):
            return mock_open(read_data=mock_customization_data)()
        return mock_open()()

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', side_effect=mock_open_side_effect):
            policy = SecurityPolicy(create_mock_ctx())

            # Should load with empty api_calls list since we control the file
            assert 's3 ls' in policy.customizations
            assert policy.customizations['s3 ls'] == []


def test_security_policy_deny_takes_priority():
    """Test that denylist takes priority over elicitList."""
    with patch.object(Path, 'exists', return_value=False):
        mock_ctx = create_mock_ctx(supports_elicitation=True)
        policy = SecurityPolicy(mock_ctx)
        policy.denylist = {'aws s3api list-buckets'}
        policy.elicit_list = {'aws s3api list-buckets'}

        decision = policy.determine_policy_effect('s3api', 'list_buckets', True)
        assert decision == PolicyDecision.DENY


def test_security_policy_default_behavior():
    """Test default behavior for all operation types."""
    with patch.object(Path, 'exists', return_value=False):
        mock_ctx = create_mock_ctx(supports_elicitation=True)
        policy = SecurityPolicy(mock_ctx)

        # Test read-only operations are allowed
        decision = policy.determine_policy_effect('s3api', 'list_buckets', True)
        assert decision == PolicyDecision.ALLOW

        # Test mutations are allowed by default (with elicitation support)
        decision = policy.determine_policy_effect('s3api', 'put_object', False)
        assert decision == PolicyDecision.ALLOW
        assert decision == PolicyDecision.ALLOW


def test_security_policy_operation_name_conversion():
    """Test operation name conversion from various formats to kebab-case."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy(create_mock_ctx())
        policy.denylist = {'aws s3api list-buckets', 'aws s3api list-objects-v2'}

        # Test camelCase operation name gets converted
        decision = policy.determine_policy_effect('s3api', 'ListBuckets', True)
        assert decision == PolicyDecision.DENY

        # Test operation name with multiple capitals
        decision = policy.determine_policy_effect('s3api', 'ListObjectsV2', True)
        assert decision == PolicyDecision.DENY

        # Test operation name already in kebab-case
        decision = policy.determine_policy_effect('s3api', 'list-buckets', True)
        assert decision == PolicyDecision.DENY


# Customization Tests
def test_security_policy_customization_parent_deny():
    """Test customization when parent command is in denylist."""
    with patch.object(Path, 'exists', return_value=False):
        mock_ctx = create_mock_ctx(supports_elicitation=True)
        policy = SecurityPolicy(mock_ctx)
        policy.denylist = {'aws s3 ls'}
        policy.customizations = {'s3 ls': ['aws s3api list-buckets']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation == 'list_buckets'

        mock_ir = create_mock_ir('s3', 'ls')
        decision = policy.check_customization(mock_ir, mock_is_read_only)
        assert decision == PolicyDecision.DENY


def test_security_policy_customization_parent_elicit():
    """Test customization when parent command is in elicit list."""
    with patch.object(Path, 'exists', return_value=False):
        mock_ctx = create_mock_ctx(supports_elicitation=True)
        policy = SecurityPolicy(mock_ctx)
        policy.elicit_list = {'aws s3 ls'}
        policy.customizations = {'s3 ls': ['aws s3api list-buckets']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation == 'list_buckets'

        mock_ir = create_mock_ir('s3', 'ls')
        decision = policy.check_customization(mock_ir, mock_is_read_only)
        assert decision == PolicyDecision.ELICIT


def test_security_policy_customization_parent_elicit_no_support():
    """Test customization when parent is in elicit list but elicitation not supported."""
    with patch.object(Path, 'exists', return_value=False):
        mock_ctx = create_mock_ctx(supports_elicitation=False)
        policy = SecurityPolicy(mock_ctx)
        policy.elicit_list = {'aws s3 ls'}
        policy.customizations = {'s3 ls': ['aws s3api list-buckets']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation == 'list_buckets'

        mock_ir = create_mock_ir('s3', 'ls')
        decision = policy.check_customization(mock_ir, mock_is_read_only)
        assert decision == PolicyDecision.DENY


def test_security_policy_customization_child_deny():
    """Test customization when child API call is in denylist."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy(create_mock_ctx())
        policy.denylist = {'aws s3api list-buckets'}
        policy.customizations = {'s3 ls': ['aws s3api list-buckets', 'aws s3api list-objects-v2']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation in ['list_buckets', 'list_objects_v2']

        mock_ir = create_mock_ir('s3', 'ls')
        decision = policy.check_customization(mock_ir, mock_is_read_only)
        assert decision == PolicyDecision.DENY


def test_security_policy_customization_child_elicit():
    """Test customization when child API call is in elicit list."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy(create_mock_ctx())
        policy.elicit_list = {'aws s3api list-objects-v2'}
        policy.customizations = {'s3 ls': ['aws s3api list-buckets', 'aws s3api list-objects-v2']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation in ['list_buckets', 'list_objects_v2']

        mock_ir = create_mock_ir('s3', 'ls')
        decision = policy.check_customization(mock_ir, mock_is_read_only)
        assert decision == PolicyDecision.ELICIT


def test_security_policy_customization_child_elicit_no_support():
    """Test customization when child is in elicit list but elicitation not supported."""
    with patch.object(Path, 'exists', return_value=False):
        mock_ctx = create_mock_ctx(supports_elicitation=False)
        policy = SecurityPolicy(mock_ctx)
        policy.elicit_list = {'aws s3api list-objects-v2'}
        policy.customizations = {'s3 ls': ['aws s3api list-buckets', 'aws s3api list-objects-v2']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation in ['list_buckets', 'list_objects_v2']

        mock_ir = create_mock_ir('s3', 'ls')
        decision = policy.check_customization(mock_ir, mock_is_read_only)
        assert decision == PolicyDecision.DENY


def test_security_policy_customization_mixed_decisions_deny_wins():
    """Test customization with mixed decisions - deny should win."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy(create_mock_ctx())
        policy.denylist = {'aws s3api list-buckets'}
        policy.elicit_list = {'aws s3api list-objects-v2'}
        policy.customizations = {'s3 ls': ['aws s3api list-buckets', 'aws s3api list-objects-v2']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation in ['list_buckets', 'list_objects_v2']

        mock_ir = create_mock_ir('s3', 'ls')
        decision = policy.check_customization(mock_ir, mock_is_read_only)
        assert decision == PolicyDecision.DENY


def test_security_policy_customization_all_allowed():
    """Test customization when all child API calls are allowed."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy(create_mock_ctx())
        policy.customizations = {'s3 ls': ['aws s3api list-buckets', 'aws s3api list-objects-v2']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation in ['list_buckets', 'list_objects_v2']

        mock_ir = create_mock_ir('s3', 'ls')
        decision = policy.check_customization(mock_ir, mock_is_read_only)
        assert decision == PolicyDecision.ALLOW


def test_security_policy_customization_no_match():
    """Test customization when command doesn't match any customization."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy(create_mock_ctx())
        policy.customizations = {'s3 ls': ['aws s3api list-buckets']}

        def mock_is_read_only(service, operation):
            return True

        mock_ir = create_mock_ir('ec2', 'describe_instances')
        decision = policy.check_customization(mock_ir, mock_is_read_only)
        assert decision is None


def test_security_policy_customization_invalid_command():
    """Test customization with invalid IR metadata."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy(create_mock_ctx())
        policy.customizations = {'s3 ls': ['aws s3api list-buckets']}

        def mock_is_read_only(service, operation):
            return True

        # Test with IR that has no command_metadata
        mock_ir = Mock(spec=IRTranslation)
        mock_ir.command_metadata = None
        decision = policy.check_customization(mock_ir, mock_is_read_only)
        assert decision is None

        # Test with IR that has incomplete metadata
        mock_ir = Mock(spec=IRTranslation)
        mock_ir.command_metadata = Mock()
        mock_ir.command_metadata.service_sdk_name = None
        mock_ir.command_metadata.operation_sdk_name = 'ls'
        decision = policy.check_customization(mock_ir, mock_is_read_only)
        assert decision is None


def test_security_policy_customization_invalid_api_call():
    """Test customization with invalid API call format in customizations."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy(create_mock_ctx())
        policy.customizations = {'s3 ls': ['invalid-api-call', 'aws s3api list-buckets']}

        def mock_is_read_only(service, operation):
            return service == 's3api' and operation == 'list_buckets'

        mock_ir = create_mock_ir('s3', 'ls')
        decision = policy.check_customization(mock_ir, mock_is_read_only)
        assert decision == PolicyDecision.ALLOW


# Integration Tests
def test_check_security_policy_customization_deny():
    """Test security policy integration when customization returns deny."""
    mock_policy_instance = Mock()
    mock_policy_instance.check_customization.return_value = PolicyDecision.DENY
    mock_policy_instance.supports_elicitation = True

    with patch(
        'awslabs.aws_api_mcp_server.core.aws.service.SecurityPolicy',
        return_value=mock_policy_instance,
    ):
        mock_ctx = Mock()
        mock_ctx.elicit = Mock()

        mock_read_only_ops = Mock(spec=ReadOnlyOperations)
        mock_ir = Mock(spec=IRTranslation)
        mock_ir.command_metadata = Mock()
        mock_ir.command_metadata.service_sdk_name = 's3api'
        mock_ir.command_metadata.operation_sdk_name = 'list_buckets'

        decision = check_security_policy(mock_ir, mock_read_only_ops, mock_ctx)

        assert decision == PolicyDecision.DENY
        mock_policy_instance.check_customization.assert_called_once()


def test_check_security_policy_no_customization():
    """Test security policy integration when no customization matches."""
    mock_policy_instance = Mock()
    mock_policy_instance.check_customization.return_value = None
    mock_policy_instance.determine_policy_effect.return_value = PolicyDecision.ALLOW
    mock_policy_instance.supports_elicitation = True

    with patch(
        'awslabs.aws_api_mcp_server.core.aws.service.SecurityPolicy',
        return_value=mock_policy_instance,
    ):
        mock_ctx = Mock()
        mock_ctx.elicit = Mock()

        mock_read_only_ops = Mock(spec=ReadOnlyOperations)
        mock_ir = Mock(spec=IRTranslation)
        mock_ir.command_metadata = Mock()
        mock_ir.command_metadata.service_sdk_name = 's3api'
        mock_ir.command_metadata.operation_sdk_name = 'list_buckets'

        decision = check_security_policy(mock_ir, mock_read_only_ops, mock_ctx)

        assert decision == PolicyDecision.ALLOW
        mock_policy_instance.determine_policy_effect.assert_called_once()


def test_security_policy_customization_missing_customizations_key():
    """Test customization loading when customizations key is missing."""
    mock_policy_data = '{"version":"1.0","policy":{"denyList":[],"elicitList":[]}}'
    mock_customization_data = '{"other_key": "value"}'  # Missing customizations key

    def mock_open_side_effect(file_path, *args, **kwargs):
        if 'mcp-security-policy.json' in str(file_path):
            return mock_open(read_data=mock_policy_data)()
        elif 'aws_api_customization.json' in str(file_path):
            return mock_open(read_data=mock_customization_data)()
        return mock_open()()

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', side_effect=mock_open_side_effect):
            policy = SecurityPolicy(create_mock_ctx())

            assert len(policy.customizations) == 0


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

    result = await call_aws.fn('aws s3 rm s3://bucket/file', ctx)

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

    result = await call_aws.fn('aws s3api put-object --bucket test --key test', ctx)

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


def test_check_security_policy_missing_metadata_with_elicitation():
    """Test check_security_policy when IR has missing metadata and elicitation is supported."""
    mock_policy_instance = Mock()
    mock_policy_instance.check_customization.return_value = None
    mock_policy_instance.supports_elicitation = True

    with patch(
        'awslabs.aws_api_mcp_server.core.aws.service.SecurityPolicy',
        return_value=mock_policy_instance,
    ):
        mock_ctx = MagicMock()
        mock_ctx.elicit = MagicMock()

        mock_read_only_ops = MagicMock(spec=ReadOnlyOperations)
        mock_ir = MagicMock(spec=IRTranslation)
        mock_ir.command_metadata = None

        decision = check_security_policy(mock_ir, mock_read_only_ops, mock_ctx)

        assert decision == PolicyDecision.ELICIT


def test_check_security_policy_missing_metadata_without_elicitation():
    """Test check_security_policy when IR has missing metadata and elicitation is not supported."""
    mock_policy_instance = Mock()
    mock_policy_instance.check_customization.return_value = None
    mock_policy_instance.supports_elicitation = False

    with patch(
        'awslabs.aws_api_mcp_server.core.aws.service.SecurityPolicy',
        return_value=mock_policy_instance,
    ):
        mock_ctx = MagicMock()

        mock_read_only_ops = MagicMock(spec=ReadOnlyOperations)
        mock_ir = MagicMock(spec=IRTranslation)
        mock_ir.command_metadata = None

        decision = check_security_policy(mock_ir, mock_read_only_ops, mock_ctx)

        assert decision == PolicyDecision.DENY


def test_check_security_policy_is_read_only_func_called():
    """Test that is_read_only_func is properly called in check_security_policy."""
    mock_policy_instance = Mock()
    mock_policy_instance.check_customization.return_value = None
    mock_policy_instance.determine_policy_effect.return_value = PolicyDecision.ALLOW
    mock_policy_instance.supports_elicitation = True

    with patch(
        'awslabs.aws_api_mcp_server.core.aws.service.SecurityPolicy',
        return_value=mock_policy_instance,
    ):
        mock_ctx = MagicMock()
        mock_ctx.elicit = MagicMock()

        mock_read_only_ops = MagicMock(spec=ReadOnlyOperations)
        mock_read_only_ops.has.return_value = True

        mock_ir = MagicMock(spec=IRTranslation)
        mock_ir.command_metadata = MagicMock()
        mock_ir.command_metadata.service_sdk_name = 'test-service'
        mock_ir.command_metadata.operation_sdk_name = 'test-operation'

        result = check_security_policy(mock_ir, mock_read_only_ops, mock_ctx)

        mock_read_only_ops.has.assert_called_with(
            service='test-service', operation='test-operation'
        )
        assert result == PolicyDecision.ALLOW


def test_determine_policy_effect_s3_elicit_no_support():
    """Test s3 service elicit without elicitation support."""
    with patch.object(Path, 'exists', return_value=False):
        mock_ctx = create_mock_ctx(supports_elicitation=False)
        policy = SecurityPolicy(mock_ctx)
        policy.elicit_list = {'aws s3 put-object'}

        # Should return DENY when elicitation not supported
        decision = policy.determine_policy_effect('s3', 'put_object', False)
        assert decision == PolicyDecision.DENY


def test_determine_policy_effect_non_s3_elicit_no_support():
    """Test non-s3 service elicit without elicitation support."""
    with patch.object(Path, 'exists', return_value=False):
        mock_ctx = create_mock_ctx(supports_elicitation=False)
        policy = SecurityPolicy(mock_ctx)
        policy.elicit_list = {'aws ec2 terminate-instances'}

        # Should return DENY when elicitation not supported
        decision = policy.determine_policy_effect('ec2', 'terminate_instances', False)
        assert decision == PolicyDecision.DENY


def test_check_customization_elicit_decision():
    """Test customization returning ELICIT decision."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy(create_mock_ctx())
        policy.elicit_list = {'aws s3api put-object'}
        policy.customizations = {'s3 sync': ['aws s3api get-object', 'aws s3api put-object']}

        def mock_is_read_only(service, operation):
            return operation == 'get_object'  # Only get-object is read-only

        mock_ir = create_mock_ir('s3', 'sync')
        decision = policy.check_customization(mock_ir, mock_is_read_only)
        assert decision == PolicyDecision.ELICIT


@patch('awslabs.aws_api_mcp_server.core.security.policy.READ_OPERATIONS_ONLY_MODE', True)
def test_determine_policy_effect_read_operations_only_mode():
    """Test determine_policy_effect with READ_OPERATIONS_ONLY_MODE enabled."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy(create_mock_ctx())

        # Read-only operation should be allowed
        decision = policy.determine_policy_effect('s3api', 'list_buckets', True)
        assert decision == PolicyDecision.ALLOW

        # Non-read-only operation should be denied
        decision = policy.determine_policy_effect('s3api', 'put_object', False)
        assert decision == PolicyDecision.DENY


@patch('awslabs.aws_api_mcp_server.core.security.policy.REQUIRE_MUTATION_CONSENT', True)
def test_determine_policy_effect_require_mutation_consent():
    """Test determine_policy_effect with REQUIRE_MUTATION_CONSENT enabled."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy(create_mock_ctx(supports_elicitation=True))

        # Read-only operation should be allowed
        decision = policy.determine_policy_effect('ec2', 'describe_instances', True)
        assert decision == PolicyDecision.ALLOW

        # Non-read-only operation should require elicitation
        decision = policy.determine_policy_effect('ec2', 'terminate_instances', False)
        assert decision == PolicyDecision.ELICIT
