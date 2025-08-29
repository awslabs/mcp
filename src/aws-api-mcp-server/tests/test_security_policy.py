from awslabs.aws_api_mcp_server.core.aws.service import check_security_policy
from awslabs.aws_api_mcp_server.core.common.models import IRTranslation
from awslabs.aws_api_mcp_server.core.metadata.read_only_operations_list import ReadOnlyOperations
from awslabs.aws_api_mcp_server.core.security.policy import PolicyDecision, SecurityPolicy
from pathlib import Path
from unittest.mock import Mock, mock_open, patch


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


def test_security_policy_deny_takes_priority():
    """Test that denylist takes priority over elicitList."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.denylist = {'aws s3api list-buckets'}
        policy.elicit_list = {'aws s3api list-buckets'}

        decision = policy.get_decision('s3api', 'list_buckets', True, True)
        assert decision == PolicyDecision.DENY


def test_security_policy_elicit_fallback_to_deny():
    """Test elicitation fallback to deny when client doesn't support it."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()
        policy.elicit_list = {'aws s3api put-object'}

        decision = policy.get_decision('s3api', 'put_object', False, False)
        assert decision == PolicyDecision.DENY


def test_security_policy_default_read_only_allowed():
    """Test default behavior for read-only operations."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()

        decision = policy.get_decision('s3api', 'list_buckets', True, True)
        assert decision == PolicyDecision.ALLOW


def test_security_policy_default_mutation_elicited():
    """Test default behavior for mutation operations."""
    with patch.object(Path, 'exists', return_value=False):
        policy = SecurityPolicy()

        decision = policy.get_decision('s3api', 'put_object', False, True)
        assert decision == PolicyDecision.ELICIT


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
