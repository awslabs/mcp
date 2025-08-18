import pytest
from awslabs.aws_api_mcp_server.core.aws.driver import (
    IRTranslation,
    get_local_credentials,
    translate_cli_to_ir,
)
from awslabs.aws_api_mcp_server.core.common.command import IRCommand
from awslabs.aws_api_mcp_server.core.common.command_metadata import CommandMetadata
from awslabs.aws_api_mcp_server.core.common.errors import (
    DeniedGlobalArgumentsError,
    ExpectedArgumentError,
    InvalidParametersReceivedError,
    InvalidServiceError,
    InvalidServiceOperationError,
    MalformedFilterError,
    MissingRequiredParametersError,
    ParameterSchemaValidationError,
    ParameterValidationErrorRecord,
    UnknownArgumentsError,
    UnknownFiltersError,
    UnsupportedFilterError,
)
from awslabs.aws_api_mcp_server.core.common.models import Credentials
from botocore.exceptions import NoCredentialsError
from tests.fixtures import S3_CLI_NO_REGION
from unittest.mock import MagicMock, patch


@patch('awslabs.aws_api_mcp_server.core.aws.driver.boto3.Session')
def test_get_local_credentials_success_with_aws_mcp_profile(mock_session_class):
    """Test get_local_credentials returns credentials when available."""
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session

    mock_credentials = MagicMock()
    mock_credentials.access_key = 'test-access-key'
    mock_credentials.secret_key = 'test-secret-key'  # pragma: allowlist secret
    mock_credentials.token = 'test-session-token'

    mock_session.get_credentials.return_value = mock_credentials

    result = get_local_credentials(profile='test')

    assert isinstance(result, Credentials)
    assert result.access_key_id == 'test-access-key'
    assert result.secret_access_key == 'test-secret-key'  # pragma: allowlist secret
    assert result.session_token == 'test-session-token'
    mock_session_class.assert_called_once_with(profile_name='test')
    mock_session.get_credentials.assert_called_once()


@patch('awslabs.aws_api_mcp_server.core.aws.driver.boto3.Session')
def test_get_local_credentials_success_with_default_creds(mock_session_class):
    """Test get_local_credentials returns credentials when available."""
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session

    mock_credentials = MagicMock()
    mock_credentials.access_key = 'test-access-key'
    mock_credentials.secret_key = 'test-secret-key'  # pragma: allowlist secret
    mock_credentials.token = 'test-session-token'

    mock_session.get_credentials.return_value = mock_credentials

    result = get_local_credentials()

    assert isinstance(result, Credentials)
    assert result.access_key_id == 'test-access-key'
    assert result.secret_access_key == 'test-secret-key'  # pragma: allowlist secret
    assert result.session_token == 'test-session-token'
    mock_session_class.assert_called_once()
    mock_session.get_credentials.assert_called_once()


@patch('awslabs.aws_api_mcp_server.core.aws.driver.boto3.Session')
def test_get_local_credentials_raises_no_credentials_error(mock_session_class):
    """Test get_local_credentials raises NoCredentialsError when credentials are None."""
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session
    mock_session.get_credentials.return_value = None

    with pytest.raises(NoCredentialsError):
        get_local_credentials()

    mock_session_class.assert_called_once()
    mock_session.get_credentials.assert_called_once()


@pytest.mark.parametrize(
    'command,program',
    [
        (
            S3_CLI_NO_REGION,
            IRTranslation(
                command_metadata=CommandMetadata(
                    's3', 'Amazon Simple Storage Service', 'ListBuckets'
                ),
            ),
        ),
        (
            'aws cloud8 list-environments',
            IRTranslation(validation_failures=[InvalidServiceError('cloud8').as_failure()]),
        ),
        # s3 is valid but it is not a real service API - it boils down to multiple API calls to s3api
        (
            'aws s3 ls s3://flock-datasets-us-west-2-516690746032',
            IRTranslation(
                command=IRCommand(
                    command_metadata=CommandMetadata('s3', None, 'ls'),
                    region='us-east-1',
                    parameters={},
                    is_awscli_customization=True,
                ),
                command_metadata=CommandMetadata('s3', None, 'ls'),
            ),
        ),
        (
            'aws s3 ls',
            IRTranslation(
                command=IRCommand(
                    command_metadata=CommandMetadata('s3', None, 'ls'),
                    region='us-east-1',
                    parameters={},
                    is_awscli_customization=True,
                ),
                command_metadata=CommandMetadata('s3', None, 'ls'),
            ),
        ),
        (
            'aws dynamodb wait table-exists --table-name MyTable',
            IRTranslation(
                command=IRCommand(
                    command_metadata=CommandMetadata('dynamodb', None, 'wait table-exists'),
                    region='us-east-1',
                    parameters={'--table-name': 'MyTable'},
                    is_awscli_customization=True,
                ),
                command_metadata=CommandMetadata('dynamodb', None, 'wait table-exists'),
            ),
        ),
        (
            'aws ec2 lss',
            IRTranslation(
                validation_failures=[InvalidServiceOperationError('ec2', 'lss').as_failure()]
            ),
        ),
        (
            'aws cloud9 describe-environment-status',
            IRTranslation(
                missing_context_failures=[
                    MissingRequiredParametersError(
                        'cloud9',
                        'describe-environment-status',
                        ['--environment-id'],
                        CommandMetadata('cloud9', 'AWS Cloud9', 'DescribeEnvironmentStatus'),
                    ).as_failure()
                ],
                command_metadata=CommandMetadata(
                    'cloud9', 'AWS Cloud9', 'DescribeEnvironmentStatus'
                ),
            ),
        ),
        (
            'aws kinesis get-records --shard-iterator',
            IRTranslation(
                missing_context_failures=[
                    ExpectedArgumentError(
                        '--shard-iterator',
                        'expected one argument',
                        CommandMetadata('kinesis', 'Amazon Kinesis', 'GetRecords'),
                    ).as_failure()
                ],
                command_metadata=CommandMetadata('kinesis', 'Amazon Kinesis', 'GetRecords'),
            ),
        ),
        (
            'aws cloud9 describe-environment-status --environment-id xyz --status',
            IRTranslation(
                validation_failures=[
                    InvalidParametersReceivedError(
                        'cloud9',
                        'describe-environment-status',
                        ['--status'],
                        ['--environment-id'],
                    ).as_failure()
                ]
            ),
        ),
        (
            'aws batch list-jobs --no-verify-ssl --debug --endpoint-url http://gooble.com --no-sign-request',
            IRTranslation(
                validation_failures=[
                    DeniedGlobalArgumentsError(
                        'batch',
                        [
                            '--debug',
                            '--endpoint-url',
                            '--no-sign-request',
                            '--no-verify-ssl',
                        ],
                    ).as_failure()
                ]
            ),
        ),
        (
            'aws ec2 describe-instances --region eu-west-1 --filters "Name=instance-state-name-1,Values=running"',
            IRTranslation(
                validation_failures=[
                    UnknownFiltersError(
                        'ec2',
                        [
                            'instance-state-name-1',
                        ],
                    ).as_failure()
                ]
            ),
        ),
        (
            'aws ec2 describe-route-tables --filters instance-state-name=running',
            IRTranslation(
                validation_failures=[
                    MalformedFilterError(
                        'ec2',
                        'describe-route-tables',
                        keys={'instance-state-name'},
                        expected_keys={'Name', 'Values'},
                    ).as_failure()
                ]
            ),
        ),
        (
            'aws ec2 describe-instances --filters {}',
            IRTranslation(
                validation_failures=[
                    MalformedFilterError(
                        'ec2',
                        'describe-instances',
                        keys=set(),
                        expected_keys={'Name', 'Values'},
                    ).as_failure()
                ]
            ),
        ),
        (
            'aws ec2 describe-instances --filters \'{"Name": "test", "Name": "test"}\'',
            IRTranslation(
                validation_failures=[
                    MalformedFilterError(
                        'ec2',
                        'describe-instances',
                        keys={'Name'},
                        expected_keys={'Name', 'Values'},
                    ).as_failure()
                ]
            ),
        ),
        (
            'aws elasticbeanstalk list-platform-versions --filters=some-fitler=some-value',
            IRTranslation(
                validation_failures=[
                    UnsupportedFilterError(
                        'elasticbeanstalk',
                        'list-platform-versions',
                        keys={'Type', 'Operator', 'Values'},
                    ).as_failure()
                ]
            ),
        ),
        (
            # list-notebook-metadata doesn't accept list of filters, this case we don't handle yet
            'aws athena list-notebook-metadata --filters Name=test --work-group grp',
            IRTranslation(
                validation_failures=[
                    UnsupportedFilterError(
                        'athena',
                        'list-notebook-metadata',
                        keys=set(),
                    ).as_failure()
                ]
            ),
        ),
        (
            'aws s3api get-bucket-intelligent-tiering-configuration --bucket my-bucket --output json',
            IRTranslation(
                missing_context_failures=[
                    MissingRequiredParametersError(
                        's3api',
                        'get-bucket-intelligent-tiering-configuration',
                        ['--id'],
                        CommandMetadata(
                            's3',
                            'Amazon Simple Storage Service',
                            'GetBucketIntelligentTieringConfiguration',
                        ),
                    ).as_failure()
                ],
                command_metadata=CommandMetadata(
                    's3',
                    'Amazon Simple Storage Service',
                    'GetBucketIntelligentTieringConfiguration',
                ),
            ),
        ),
        (
            'aws s3control list-access-grants --account-id test_account',
            IRTranslation(
                validation_failures=[
                    ParameterSchemaValidationError(
                        [
                            ParameterValidationErrorRecord(
                                '--account-id',
                                'Invalid pattern for parameter , value: test_account, valid pattern: ^\\d{12}$',
                            )
                        ]
                    ).as_failure()
                ]
            ),
        ),
        (
            'aws datazone search-listings --domain-identifier dzd_rmvr776t4h0pvi --search-text shipping logistics costs',
            IRTranslation(
                validation_failures=[
                    UnknownArgumentsError(
                        'datazone',
                        'search-listings',
                        ['logistics', 'costs'],
                    ).as_failure()
                ]
            ),
        ),
        (
            'aws kinesis describe-stream --stream-name 12345~**',
            IRTranslation(
                validation_failures=[
                    ParameterSchemaValidationError(
                        [
                            ParameterValidationErrorRecord(
                                '--stream-name',
                                'Invalid pattern for parameter , value: 12345~**, valid pattern: [a-zA-Z0-9_.-]+',
                            )
                        ]
                    ).as_failure()
                ]
            ),
        ),
        (
            (
                'aws kinesis describe-stream --stream-name 1234511111111111111111111111111111111111'
                '1111111111111111111111111111111111111111111111111111111111111111111111111111111111'
                '1111111111111111111111111111111111111111111111111111111111111111111111111111111111'
                '1111111111111111111111111111111111111111111111111111111111111111111111111111111111'
                '1111111111111111111111111111111111111111111111111111111111111111111111111111111111'
                '1111111111111111111111111111111111111111111111111111111111111111111111111111111111'
                '1111111111111111111111111111111111111111111111111111111111111111111111111111111111'
                '1111111111111111111111111111111111111111111111111111111111111111111111111111111111'
                '1111111111111111111111111111111111111111111111111111111111111111111111111'
            ),
            IRTranslation(
                validation_failures=[
                    ParameterSchemaValidationError(
                        [
                            ParameterValidationErrorRecord(
                                '--stream-name',
                                'Invalid length for parameter , value: 687, valid max length: 128',
                            )
                        ]
                    ).as_failure()
                ]
            ),
        ),
    ],
)
def test_driver(command, program):
    """Test that CLI command is correctly translated to IR program."""
    translated = translate_cli_to_ir(command)
    assert translated == program
    assert translated.command_metadata == program.command_metadata


@pytest.mark.parametrize(
    'command',
    [
        # Cloud9 is not available in ap-southeast-3
        'aws cloud9 list-environments --region ap-southeast-3',
        # And fake regions are not tracked as well
        'aws cloud9 list-environments --region bogus',
        # Datazone not available in certain regions
        'aws datazone get-environment --domain-identifier dzd_rm8rqsucr193md --identifier dzd --region eu-central-2',
        'aws datazone get-environment --domain-identifier dzd_rm8rqsucr193md --identifier dzd --region ap-south-1',
        'aws datazone get-environment --domain-identifier dzd_rm8rqsucr193md --identifier dzd --region ap-east-1',
        'aws datazone get-environment --domain-identifier dzd_rm8rqsucr193md --identifier dzd --region eu-central-2',
        # Service is not available in default region
        'aws datazone get-environment --domain-identifier dzd_rm8rqsucr193md --identifier dzd',
    ],
)
def test_invalid_region(command):
    """Test that invalid or unavailable regions are handled correctly."""
    translate_cli_to_ir(command)
