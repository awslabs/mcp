import json
import pytest
from .history_handler import history
from awslabs.aws_mcp_server.core.aws.driver import translate_cli_to_ir
from awslabs.aws_mcp_server.core.aws.service import (
    check_for_consent,
    interpret_command,
    is_operation_read_only,
    validate,
)
from awslabs.aws_mcp_server.core.common.helpers import as_json
from awslabs.aws_mcp_server.core.common.models import (
    CommandMetadata,
    Context,
    Credentials,
    InterpretationMetadata,
    InterpretationResponse,
    IRTranslation,
    ProgramInterpretationResponse,
    ValidationFailure,
)
from awslabs.aws_mcp_server.core.metadata.read_only_operations_list import ReadOnlyOperations
from botocore.config import Config
from tests.fixtures import (
    CLOUD9_DESCRIBE_ENVIRONMENTS,
    CLOUD9_LIST_ENVIRONMENTS,
    CLOUD9_PARAMS_CLI_MISSING_CONTEXT,
    CLOUD9_PARAMS_CLI_NON_EXISTING_OPERATION,
    CLOUD9_PARAMS_CLI_VALIDATION_FAILURES,
    CLOUD9_PARAMS_MISSING_CONTEXT_FAILURES,
    CLOUDFORMATION_LIST_STACKS_FIRST_PAGE,
    EC2_DESCRIBE_INSTANCES,
    EC2_WAIT_COMMAND_CLI,
    EC2_WAIT_COMMAND_VALIDATION_FAILURES,
    GET_CALLER_IDENTITY_PAYLOAD,
    REDSHIFT_FIRST_PAGE,
    SSM_LIST_NODES_PAYLOAD,
    T2_EC2_DESCRIBE_INSTANCES,
    TEST_CREDENTIALS,
    patch_boto3,
    patch_boto3_paginated_cloudformation,
    patch_boto3_paginated_cloudformation_for_max_limit,
    patch_boto3_paginated_redshift,
)
from typing import Any
from unittest.mock import MagicMock, patch


@pytest.mark.parametrize(
    'cli_command,reason,service,operation',
    [
        (
            CLOUD9_PARAMS_CLI_NON_EXISTING_OPERATION,
            "The operation 'list-environments-1' for service 'cloud9' does not exist.",
            'cloud9',
            'list-environments-1',
        ),
        (
            EC2_WAIT_COMMAND_CLI,
            "The operation 'wait' for service 'ec2' is currently unsupported.",
            'ec2',
            'wait',
        ),
    ],
)
def test_interpret_returns_validation_failures(cli_command, reason, service, operation):
    """Test that interpret_command returns validation failures for invalid operations."""
    credentials = Credentials(**TEST_CREDENTIALS)
    response = interpret_command(
        cli_command=cli_command,
        credentials=credentials,
        default_region='us-east-1',
    )
    assert response.response is None
    assert response.validation_failures == [
        ValidationFailure(
            reason=reason,
            context=Context(
                service=service,
                operation=operation,
                parameters=None,
                args=None,
                region=None,
                operators=None,
            ),
        )
    ]


def test_interpret_returns_missing_context_failures():
    """Test that interpret_command returns missing context failures when required parameters are missing."""
    credentials = Credentials(**TEST_CREDENTIALS)
    response = interpret_command(
        cli_command=CLOUD9_PARAMS_CLI_MISSING_CONTEXT,
        credentials=credentials,
        default_region='us-east-1',
    )
    assert response.response is None
    assert response.missing_context_failures == [
        ValidationFailure(
            reason="The following parameters are missing for service 'cloud9' and operation 'create-environment-ec2': '--image-id'",
            context=Context(
                service='cloud9',
                operation='create-environment-ec2',
                parameters=['--image-id'],
                args=None,
                region=None,
                operators=None,
            ),
        )
    ]


@pytest.mark.parametrize(
    'cli,output,event,service,service_full_name,operation',
    [
        (
            'aws cloud9 list-environments',
            CLOUD9_LIST_ENVIRONMENTS,
            ('ListEnvironments', {}, 'us-east-1', 10, 'https://cloud9.us-east-1.amazonaws.com'),
            'cloud9',
            'AWS Cloud9',
            'ListEnvironments',
        ),
        (
            'aws ec2 describe-instances --filters "Name=instance-state-name,Values=running"',
            EC2_DESCRIBE_INSTANCES,
            (
                'DescribeInstances',
                {
                    'Filters': [{'Name': 'instance-state-name', 'Values': ['running']}],
                },
                'us-east-1',
                10,
                'https://ec2.us-east-1.amazonaws.com',
            ),
            'ec2',
            'Amazon Elastic Compute Cloud',
            'DescribeInstances',
        ),
        (
            """aws ec2 describe-instances --query "Reservations[].Instances[?InstanceType=='t2.micro']" """,
            T2_EC2_DESCRIBE_INSTANCES,
            (
                'DescribeInstances',
                {},
                'us-east-1',
                10,
                'https://ec2.us-east-1.amazonaws.com',
            ),
            'ec2',
            'Amazon Elastic Compute Cloud',
            'DescribeInstances',
        ),
        (
            'aws cloud9 describe-environments --environment-ids 7d61007bd98b4d589f1504af84c168de b181ffd35fe2457c8c5ae9d75edc068a',
            CLOUD9_DESCRIBE_ENVIRONMENTS,
            (
                'DescribeEnvironments',
                {
                    'environmentIds': [
                        '7d61007bd98b4d589f1504af84c168de',  # pragma: allowlist secret
                        'b181ffd35fe2457c8c5ae9d75edc068a',  # pragma: allowlist secret
                    ]
                },
                'us-east-1',
                10,
                'https://cloud9.us-east-1.amazonaws.com',
            ),
            'cloud9',
            'AWS Cloud9',
            'DescribeEnvironments',
        ),
        (
            'aws sts get-caller-identity',
            GET_CALLER_IDENTITY_PAYLOAD,
            ('GetCallerIdentity', {}, 'us-east-1', 10, 'https://sts.amazonaws.com'),
            'sts',
            'AWS Security Token Service',
            'GetCallerIdentity',
        ),
        (
            'aws ssm list-nodes --sync-name Luna-Sync --filters Key=IpAddress,Values=1.0.0.1,Type=Equal',
            SSM_LIST_NODES_PAYLOAD,
            (
                'ListNodes',
                {
                    'SyncName': 'Luna-Sync',
                    'Filters': [
                        {
                            'Key': 'IpAddress',
                            'Values': ['1.0.0.1'],
                            'Type': 'Equal',
                        }
                    ],
                },
                'us-east-1',
                10,
                'https://ssm.us-east-1.amazonaws.com',
            ),
            'ssm',
            'Amazon Simple Systems Manager (SSM)',
            'ListNodes',
        ),
    ],
)
def test_interpret_returns_valid_response(
    cli, output: dict[str, Any], event, service, service_full_name, operation
):
    """Test that interpret_command returns a valid response for correct CLI commands."""
    with patch_boto3():
        history.events.clear()
        credentials = Credentials(**TEST_CREDENTIALS)
        response = interpret_command(
            cli_command=cli, default_region='us-east-1', credentials=credentials
        )
        assert response == ProgramInterpretationResponse(
            response=InterpretationResponse(json=as_json(output), error=None, status_code=200),
            failed_constraints=[],
            metadata=InterpretationMetadata(
                service=service,
                operation=operation,
                region_name='us-east-1',
                service_full_name=service_full_name,
            ),
        )
        assert event in history.events


def test_interpret_injects_region():
    """Test that interpret_command injects the correct region into the request."""
    region = 'eu-south-1'
    default_config = Config(region_name=region)
    with patch_boto3():
        with patch('awslabs.aws_mcp_server.core.parser.interpretation.Config') as patch_config:
            history.events.clear()
            patch_config.return_value = default_config
            credentials = Credentials(**TEST_CREDENTIALS)
            response = interpret_command(
                cli_command='aws cloud9 describe-environments --environment-ids 7d61007bd98b4d589f1504af84c168de b181ffd35fe2457c8c5ae9d75edc068a',
                credentials=credentials,
                default_region=region,
            )
            assert response.metadata == InterpretationMetadata(
                service='cloud9',
                operation='DescribeEnvironments',
                region_name=region,
                service_full_name='AWS Cloud9',
            )
            event = (
                'DescribeEnvironments',
                {
                    'environmentIds': [
                        '7d61007bd98b4d589f1504af84c168de',  # pragma: allowlist secret
                        'b181ffd35fe2457c8c5ae9d75edc068a',  # pragma: allowlist secret
                    ]
                },
                'eu-south-1',
                60,
                'https://cloud9.eu-south-1.amazonaws.com',
            )
            assert event in history.events


@pytest.mark.parametrize(
    'cli, event, api_limit',
    [
        # MaxItems is the CLI version, maxResults is the boto3 API version
        # Priority has the lower value
        (
            'aws cloud9 list-environments --max-items 4',
            (
                'ListEnvironments',
                {'maxResults': 4},
                'us-east-1',
                10,
                'https://cloud9.us-east-1.amazonaws.com',
            ),
            5,
        ),
        # Priority has the value from the API, not the one from CLI
        (
            'aws cloud9 list-environments --max-items 40',
            (
                'ListEnvironments',
                {'maxResults': 25},
                'us-east-1',
                10,
                'https://cloud9.us-east-1.amazonaws.com',
            ),
            5,
        ),
        # Not passing at CLI but limited at API time
        (
            'aws cloud9 list-environments',
            (
                'ListEnvironments',
                {'maxResults': 5},
                'us-east-1',
                10,
                'https://cloud9.us-east-1.amazonaws.com',
            ),
            5,
        ),
        # This operation does not support limiting the number of results
        (
            'aws cloud9 describe-environments --environment-ids 7d61007bd98b4d589f1504af84c168de',  # pragma: allowlist secret
            (
                'DescribeEnvironments',
                {
                    'environmentIds': [
                        '7d61007bd98b4d589f1504af84c168de'  # pragma: allowlist secret
                    ]  # pragma: allowlist secret
                },  # pragma: allowlist secret
                'us-east-1',
                10,
                'https://cloud9.us-east-1.amazonaws.com',
            ),
            5,
        ),
        # This operation supports limiting the number of results, but different key when
        # passing to the service
        (
            'aws ec2 describe-instances --max-items 2',
            (
                'DescribeInstances',
                {'MaxResults': 2},
                'us-east-1',
                10,
                'https://ec2.us-east-1.amazonaws.com',
            ),
            5,
        ),
        # This call does not receive a limit at the API level
        # The one at the CLI level should be used
        (
            'aws ec2 describe-instances --max-items 2',
            (
                'DescribeInstances',
                {'MaxResults': 2},
                'us-east-1',
                10,
                'https://ec2.us-east-1.amazonaws.com',
            ),
            None,
        ),
        # This call does not receive a limit at the API level nor at the CLI level, but capped at 100
        (
            'aws ec2 describe-instances',
            (
                'DescribeInstances',
                {},
                'us-east-1',
                10,
                'https://ec2.us-east-1.amazonaws.com',
            ),
            None,
        ),
        # We pass the limit at the API level but since this is EC2 Describe* operation the limit won't be used
        (
            'aws ec2 describe-instances',
            (
                'DescribeInstances',
                {'MaxResults': 10},
                'us-east-1',
                10,
                'https://ec2.us-east-1.amazonaws.com',
            ),
            10,
        ),
        # This call does receive a limit at the API level
        (
            'aws ec2 describe-instances',
            (
                'DescribeInstances',
                {'MaxResults': 200},
                'us-east-1',
                10,
                'https://ec2.us-east-1.amazonaws.com',
            ),
            200,
        ),
        # This call does receive a limit at the CLI level
        (
            'aws ec2 describe-instances --max-items 200',
            (
                'DescribeInstances',
                {'MaxResults': 200},
                'us-east-1',
                10,
                'https://ec2.us-east-1.amazonaws.com',
            ),
            None,
        ),
        # This call does receive a limited, but limits are incompatible with InstanceIds parameter
        (
            'aws ec2 describe-instances --instance-ids i-0999cb9f50587d55f',
            (
                'DescribeInstances',
                {'InstanceIds': ['i-0999cb9f50587d55f']},
                'us-east-1',
                10,
                'https://ec2.us-east-1.amazonaws.com',
            ),
            10,
        ),
        # Prevent starting token to crash the API
        (
            'aws ec2 describe-capacity-reservation-fleets --capacity-reservation-fleet-ids 123 --starting-token tokenValue',
            (
                'DescribeCapacityReservationFleets',
                {'CapacityReservationFleetIds': ['123'], 'MaxResults': 10},
                'us-east-1',
                10,
                'https://ec2.us-east-1.amazonaws.com',
            ),
            10,
        ),
    ],
)
def test_interpret_api_injects_max_results_key(cli, event, api_limit):
    """Test that interpret_command injects max results key for paginated APIs."""
    with patch_boto3():
        history.events.clear()
        credentials = Credentials(**TEST_CREDENTIALS)
        interpret_command(
            cli_command=cli,
            credentials=credentials,
            default_region='us-east-1',
            max_results=api_limit,
        )
        assert event in history.events


@pytest.mark.parametrize(
    'cli, region',
    [
        (
            'aws cloudwatch list-managed-insight-rules --resource-arn arn:aws:cloudwatch:eu-west-2:123456789012:alarm:AlarmName',
            'eu-west-2',
        ),
        (
            'aws cloudwatch list-managed-insight-rules --resource-arn arn:aws:cloudwatch:eu-west-2:123456789012:alarm:AlarmName --region eu-central-1',
            'eu-central-1',
        ),
        (
            'aws cloudwatch list-managed-insight-rules --resource-arn arn:aws:cloudwatch::123456789012:alarm:AlarmName',
            'us-east-1',
        ),
    ],
)
def test_region_picked_up_from_arn(cli, region):
    """Test that region is correctly picked up from ARN in the CLI command."""
    with patch_boto3():
        credentials = Credentials(**TEST_CREDENTIALS)
        response = interpret_command(
            cli_command=cli,
            default_region='us-east-1',
            credentials=credentials,
        )
        assert response.metadata is not None
        assert response.metadata.region_name == region


def test_interpret_handles_counting_via_pagination():
    """Test that interpret_command handles resource counting via pagination."""
    with (
        patch(
            'awslabs.aws_mcp_server.core.parser.interpretation.build_result',
            return_value=CLOUDFORMATION_LIST_STACKS_FIRST_PAGE,
        ),
        patch_boto3_paginated_cloudformation(),
    ):
        credentials = Credentials(**TEST_CREDENTIALS)
        response = interpret_command(
            cli_command='aws cloudformation list-stacks',
            credentials=credentials,
            default_region='us-east-1',
            max_results=10,
            is_counting=True,
        )
        assert response.response is not None
        payload = json.loads(response.response.as_json or '{}')
        assert payload['resource_count_info'] is not None
        assert payload['resource_count_info']['resource_count'] == 2
        assert payload['resource_count_info']['status'] == 'exact'


def test_interpret_handles_counting_via_pagination_parsingpath():
    """Test that interpret_command handles resource counting via pagination with parsing path."""
    with (
        patch(
            'awslabs.aws_mcp_server.core.parser.interpretation.build_result',
            return_value=REDSHIFT_FIRST_PAGE,
        ),
        patch_boto3_paginated_redshift(),
    ):
        credentials = Credentials(**TEST_CREDENTIALS)
        response = interpret_command(
            cli_command='aws redshift describe-default-cluster-parameters --parameter-group-family redshift-1.0',
            credentials=credentials,
            default_region='us-east-1',
            max_results=10,
            is_counting=True,
        )
        assert response.response is not None
        payload = json.loads(response.response.as_json or '{}')
        assert payload['resource_count_info'] is not None
        assert payload['resource_count_info']['resource_count'] == 4
        assert payload['resource_count_info']['status'] == 'exact'


def test_interpret_handles_counting_when_timeout():
    """Test that interpret_command handles resource counting when a timeout occurs."""
    with (
        patch(
            'awslabs.aws_mcp_server.core.parser.interpretation.build_result',
            return_value=REDSHIFT_FIRST_PAGE,
        ),
        patch(
            'awslabs.aws_mcp_server.core.aws.resource_counting.get_current_time',
            side_effect=[0, 4.1],
        ),
        patch_boto3_paginated_redshift(),
    ):
        credentials = Credentials(**TEST_CREDENTIALS)
        response = interpret_command(
            cli_command='aws redshift describe-default-cluster-parameters --parameter-group-family redshift-1.0',
            credentials=credentials,
            default_region='us-east-1',
            max_results=10,
            is_counting=True,
        )
        assert response.response is not None
        payload = json.loads(response.response.as_json or '{}')
        assert payload['resource_count_info'] is not None
        assert payload['resource_count_info']['resource_count'] == 4
        assert payload['resource_count_info']['status'] == 'exact'


def test_interpret_handles_counting_when_hit_max_limit_exact():
    """Test that interpret_command handles resource counting when hitting the max limit exactly."""
    with (
        patch(
            'awslabs.aws_mcp_server.core.parser.interpretation.build_result',
            return_value=REDSHIFT_FIRST_PAGE,
        ),
        patch('awslabs.aws_mcp_server.core.aws.resource_counting.MAX_RESOURCE_COUNT', 2),
        patch_boto3_paginated_redshift(),
    ):
        credentials = Credentials(**TEST_CREDENTIALS)
        response = interpret_command(
            cli_command='aws redshift describe-default-cluster-parameters --parameter-group-family redshift-1.0',
            credentials=credentials,
            default_region='us-east-1',
            max_results=10,
            is_counting=True,
        )
        assert response.response is not None
        payload = json.loads(response.response.as_json or '{}')
        assert payload['resource_count_info'] is not None
        assert payload['resource_count_info']['resource_count'] == 2
        assert payload['resource_count_info']['status'] == 'at_least'


def test_interpret_handles_counting_when_first_page_time_took_long():
    """Test that interpret_command handles resource counting when the first page takes too long."""
    with (
        patch(
            'awslabs.aws_mcp_server.core.parser.interpretation.build_result',
            return_value=REDSHIFT_FIRST_PAGE,
        ),
        patch('awslabs.aws_mcp_server.core.aws.resource_counting.TIMEOUT', -1),
        patch_boto3_paginated_redshift(),
    ):
        credentials = Credentials(**TEST_CREDENTIALS)
        response = interpret_command(
            cli_command='aws redshift describe-default-cluster-parameters --parameter-group-family redshift-1.0',
            credentials=credentials,
            default_region='us-east-1',
            max_results=10,
            is_counting=True,
        )
        assert response.response is not None
        payload = json.loads(response.response.as_json or '{}')
        assert payload['resource_count_info'] is not None
        assert payload['resource_count_info']['resource_count'] == 2
        assert payload['resource_count_info']['status'] == 'at_least'


def test_interpret_handles_counting_when_hit_max_limit_at_least():
    """Test interpret handles counting when hitting max limit at least."""
    with (
        patch(
            'awslabs.aws_mcp_server.core.parser.interpretation.build_result',
            return_value=CLOUDFORMATION_LIST_STACKS_FIRST_PAGE,
        ),
        patch('awslabs.aws_mcp_server.core.aws.resource_counting.MAX_RESOURCE_COUNT', 1),
        patch_boto3_paginated_cloudformation_for_max_limit(),
    ):
        credentials = Credentials(**TEST_CREDENTIALS)
        response = interpret_command(
            cli_command='aws cloudformation list-stacks',
            credentials=credentials,
            default_region='us-east-1',
            max_results=10,
            is_counting=True,
        )
        assert response.response is not None
        payload = json.loads(response.response.as_json or '{}')

        # Verify that the response includes correct pagination handling
        assert payload['resource_count_info'] is not None
        assert payload['resource_count_info']['resource_count'] == 1
        assert payload['resource_count_info']['status'] == 'at_least'


def test_validate_success():
    """Test that validate returns success for a valid IR translation."""
    ir = translate_cli_to_ir('aws s3api list-buckets')
    response = validate(ir)
    response_json = json.loads(response.model_dump_json())
    assert response_json['validation_failures'] is None
    assert response_json['missing_context_failures'] is None
    assert response_json['failed_constraints'] == []


@pytest.mark.parametrize(
    'cli_command,validate_response',
    [
        (CLOUD9_PARAMS_CLI_NON_EXISTING_OPERATION, CLOUD9_PARAMS_CLI_VALIDATION_FAILURES),
        (EC2_WAIT_COMMAND_CLI, EC2_WAIT_COMMAND_VALIDATION_FAILURES),
    ],
)
def test_validate_returns_validation_failures(cli_command, validate_response):
    """Test that validate returns expected validation failures for invalid commands."""
    ir = translate_cli_to_ir(cli_command)
    response = validate(ir)
    response_json = json.loads(response.model_dump_json())
    assert response_json == validate_response


def test_validate_returns_missing_context_failures():
    """Test that validate returns missing context failures for incomplete commands."""
    ir = translate_cli_to_ir(CLOUD9_PARAMS_CLI_MISSING_CONTEXT)
    response = validate(ir)
    response_json = json.loads(response.model_dump_json())
    assert response_json == CLOUD9_PARAMS_MISSING_CONTEXT_FAILURES


@pytest.mark.parametrize(
    'cli_command,validation_failure_reason',
    [
        (
            'aws ec2 describe-instances --instance-ids abcdefgh',
            (
                "The parameter 'InstanceIds' received an invalid input: "
                'Invalid parameter value: The parameter InstanceIds does not match the ^i-[a-f0-9]{8,17}$ pattern'
            ),
        ),
        (
            'aws ec2 describe-security-groups --group-ids abcdefgh',
            (
                "The parameter 'GroupIds' received an invalid input: "
                'Invalid parameter value: The parameter GroupIds does not match the ^sg-[a-f0-9]{8,17}$ pattern'
            ),
        ),
        (
            'aws ec2 describe-instance-attribute --attribute instanceType --instance-id abcdefgh',
            (
                "The parameter 'InstanceId' received an invalid input: "
                'Invalid parameter value: The parameter InstanceId does not match the ^i-[a-f0-9]{8,17}$ pattern'
            ),
        ),
        (
            'aws ec2 describe-security-group-references --group-id abcdefgh',
            (
                "The parameter 'GroupId' received an invalid input: "
                'Invalid parameter value: The parameter GroupId does not match the ^sg-[a-f0-9]{8,17}$ pattern'
            ),
        ),
        (
            'aws ec2 revoke-security-group-ingress --group-id abcdefgh',
            (
                "The parameter 'GroupId' received an invalid input: "
                'Invalid parameter value: The parameter GroupId does not match the ^sg-[a-f0-9]{8,17}$ pattern'
            ),
        ),
    ],
)
def test_validate_returns_ec2_validation_failures(cli_command, validation_failure_reason):
    """Test that validate returns EC2 validation failures for invalid parameters."""
    ir = translate_cli_to_ir(cli_command)
    response = validate(ir)
    response_json = json.loads(response.model_dump_json())
    validation_failures = response_json['validation_failures']
    assert len(validation_failures) == 1
    assert validation_failures[0]['reason'] == validation_failure_reason


@patch('awslabs.aws_mcp_server.core.aws.service.token_manager')
@patch('awslabs.aws_mcp_server.core.aws.service.confirm_list')
def test_call_aws_mutating_action_no_token(mock_confirm_list, mock_token_manager):
    """Test call_aws with a mutating action that requires consent but no token is provided."""
    mock_confirm_list.has.return_value = True

    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 'ec2'
    mock_ir.command_metadata.operation_sdk_name = 'terminate-instances'

    # Mock token manager to indicate no valid token exists
    mock_token_manager.has_valid_token_for_command.return_value = False
    mock_token_manager.generate_token.return_value = 'new-consent-token-123'

    # Execute
    result = check_for_consent(
        cli_command='aws ec2 terminate-instances --instance-ids i-1234567890abcdef0',
        ir=mock_ir,
        consent_token=None,
    )

    # Verify
    assert result is not None
    assert result.status == 'consent_required'
    assert 'new-consent-token-123' in result.message
    mock_confirm_list.has.assert_called_once_with(service='ec2', operation='terminate-instances')
    mock_token_manager.has_valid_token_for_command.assert_called_once_with(
        'aws ec2 terminate-instances --instance-ids i-1234567890abcdef0'
    )
    mock_token_manager.generate_token.assert_called_once_with(
        'aws ec2 terminate-instances --instance-ids i-1234567890abcdef0'
    )


@patch('awslabs.aws_mcp_server.core.aws.service.token_manager')
@patch('awslabs.aws_mcp_server.core.aws.service.confirm_list')
def test_call_aws_mutating_action_with_valid_token(mock_confirm_list, mock_token_manager):
    """Test call_aws with a mutating action and a valid consent token."""
    mock_confirm_list.has.return_value = True

    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 'ec2'
    mock_ir.command_metadata.operation_sdk_name = 'terminate-instances'

    # Mock token manager to validate the token
    mock_token_manager.validate_token.return_value = True

    # Execute
    result = check_for_consent(
        cli_command='aws ec2 terminate-instances --instance-ids i-1234567890abcdef0',
        ir=mock_ir,
        consent_token='valid-token-123',
    )

    # Verify
    assert result is None
    mock_confirm_list.has.assert_called_once_with(service='ec2', operation='terminate-instances')
    mock_token_manager.validate_token.assert_called_once_with(
        'valid-token-123', 'aws ec2 terminate-instances --instance-ids i-1234567890abcdef0'
    )


@patch('awslabs.aws_mcp_server.core.aws.service.token_manager')
@patch('awslabs.aws_mcp_server.core.aws.service.confirm_list')
def test_call_aws_mutating_action_with_invalid_token(mock_confirm_list, mock_token_manager):
    """Test call_aws with a mutating action and an invalid consent token."""
    mock_confirm_list.has.return_value = True

    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 'ec2'
    mock_ir.command_metadata.operation_sdk_name = 'terminate-instances'

    # Mock token manager to invalidate the token
    mock_token_manager.validate_token.return_value = False
    mock_token_manager.has_valid_token_for_command.return_value = False
    mock_token_manager.generate_token.return_value = 'new-consent-token-456'

    # Execute with invalid consent token
    result = check_for_consent(
        cli_command='aws ec2 terminate-instances --instance-ids i-1234567890abcdef0',
        ir=mock_ir,
        consent_token='invalid-token-123',
    )

    # Verify
    assert result is not None
    assert result.status == 'consent_required'
    assert "Consent token expired, invalid, or doesn't match" in result.message
    assert 'new-consent-token-456' in result.message
    mock_confirm_list.has.assert_called_once_with(service='ec2', operation='terminate-instances')
    mock_token_manager.validate_token.assert_called_once_with(
        'invalid-token-123', 'aws ec2 terminate-instances --instance-ids i-1234567890abcdef0'
    )


@patch('awslabs.aws_mcp_server.core.aws.service.token_manager')
@patch('awslabs.aws_mcp_server.core.aws.service.confirm_list')
def test_call_aws_mutating_action_with_previous_valid_token(mock_confirm_list, mock_token_manager):
    """Test call_aws with a mutating action and a previously valid token for the command."""
    mock_confirm_list.has.return_value = True

    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 'ec2'
    mock_ir.command_metadata.operation_sdk_name = 'terminate-instances'

    # Mock token manager to indicate a valid token exists
    mock_token_manager.validate_token.return_value = False  # No token provided
    mock_token_manager.has_valid_token_for_command.return_value = True  # But previous token exists

    # Execute without consent token (but previous token exists)
    result = check_for_consent(
        cli_command='aws ec2 terminate-instances --instance-ids i-1234567890abcdef0',
        ir=mock_ir,
        consent_token=None,
    )

    # Verify
    assert result is None
    mock_confirm_list.has.assert_called_once_with(service='ec2', operation='terminate-instances')
    mock_token_manager.has_valid_token_for_command.assert_called_once_with(
        'aws ec2 terminate-instances --instance-ids i-1234567890abcdef0'
    )


@patch('awslabs.aws_mcp_server.core.aws.service.token_manager')
@patch('awslabs.aws_mcp_server.core.aws.service.confirm_list')
def test_call_aws_unknown_action_type(mock_confirm_list, mock_token_manager):
    """Test call_aws with an unknown action type that requires consent."""
    mock_confirm_list.has.return_value = True

    # Mock IR with command metadata
    mock_ir = MagicMock()
    mock_ir.command_metadata = MagicMock()
    mock_ir.command_metadata.service_sdk_name = 'custom-service'
    mock_ir.command_metadata.operation_sdk_name = 'custom-operation'

    # Mock token manager
    mock_token_manager.has_valid_token_for_command.return_value = False
    mock_token_manager.generate_token.return_value = 'new-consent-token-789'

    # Execute
    result = check_for_consent(
        cli_command='aws custom-service custom-operation',
        ir=mock_ir,
        consent_token=None,
    )

    # Verify
    assert result is not None
    assert result.status == 'consent_required'
    assert 'new-consent-token-789' in result.message
    mock_confirm_list.has.assert_called_once_with(
        service='custom-service', operation='custom-operation'
    )
    mock_token_manager.has_valid_token_for_command.assert_called_once_with(
        'aws custom-service custom-operation'
    )


def test_is_operation_read_only_returns_true_for_read_only_operation():
    """Test is_operation_read_only returns True for a read-only operation."""
    ir = IRTranslation(
        command_metadata=CommandMetadata(
            service_sdk_name='s3',
            service_full_sdk_name='Amazon S3',
            operation_sdk_name='list-buckets',
        )
    )

    read_only_operations = ReadOnlyOperations()
    read_only_operations['s3'] = ['list-buckets', 'get-*']

    result = is_operation_read_only(ir, read_only_operations)

    assert result is True


def test_is_operation_read_only_returns_true_for_wildcard_match():
    """Test is_operation_read_only returns True for a wildcard match."""
    ir = IRTranslation(
        command_metadata=CommandMetadata(
            service_sdk_name='s3',
            service_full_sdk_name='Amazon S3',
            operation_sdk_name='get-object',
        )
    )

    read_only_operations = ReadOnlyOperations()
    read_only_operations['s3'] = ['list-buckets', 'get-*']

    result = is_operation_read_only(ir, read_only_operations)

    assert result is True


def test_is_operation_read_only_returns_false_for_non_read_only_operation():
    """Test is_operation_read_only returns False for non-read-only operation."""
    ir = IRTranslation(
        command_metadata=CommandMetadata(
            service_sdk_name='s3',
            service_full_sdk_name='Amazon S3',
            operation_sdk_name='delete-object',
        )
    )

    read_only_operations = ReadOnlyOperations()
    read_only_operations['s3'] = ['list-buckets', 'get-*']

    result = is_operation_read_only(ir, read_only_operations)

    assert result is False


def test_is_operation_read_only_returns_false_for_unknown_service():
    """Test is_operation_read_only returns False for unknown service."""
    ir = IRTranslation(
        command_metadata=CommandMetadata(
            service_sdk_name='unknown-service',
            service_full_sdk_name='Unknown Service',
            operation_sdk_name='list-buckets',
        )
    )

    read_only_operations = ReadOnlyOperations()
    read_only_operations['s3'] = ['list-buckets', 'get-*']

    result = is_operation_read_only(ir, read_only_operations)

    assert result is False


def test_is_operation_read_only_raises_error_for_missing_command_metadata():
    """Test is_operation_read_only raises error for missing command metadata."""
    ir = IRTranslation(command_metadata=None)
    read_only_operations = ReadOnlyOperations()

    with pytest.raises(RuntimeError, match='failed to check if operation is allowed'):
        is_operation_read_only(ir, read_only_operations)


def test_is_operation_read_only_raises_error_for_missing_service_name():
    """Test is_operation_read_only raises error for missing service name."""
    ir = IRTranslation(
        command_metadata=CommandMetadata(
            service_sdk_name='',
            service_full_sdk_name='Amazon S3',
            operation_sdk_name='list-buckets',
        )
    )
    read_only_operations = ReadOnlyOperations()

    with pytest.raises(RuntimeError, match='failed to check if operation is allowed'):
        is_operation_read_only(ir, read_only_operations)


def test_is_operation_read_only_raises_error_for_missing_operation_name():
    """Test is_operation_read_only raises error for missing operation name."""
    ir = IRTranslation(
        command_metadata=CommandMetadata(
            service_sdk_name='s3', service_full_sdk_name='Amazon S3', operation_sdk_name=''
        )
    )
    read_only_operations = ReadOnlyOperations()

    with pytest.raises(RuntimeError, match='failed to check if operation is allowed'):
        is_operation_read_only(ir, read_only_operations)
