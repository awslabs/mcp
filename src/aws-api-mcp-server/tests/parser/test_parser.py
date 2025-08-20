import pytest
import re
from awslabs.aws_api_mcp_server.core.common.command_metadata import CommandMetadata
from awslabs.aws_api_mcp_server.core.common.errors import (
    ClientSideFilterError,
    CommandValidationError,
    ExpectedArgumentError,
    InvalidChoiceForParameterError,
    InvalidParametersReceivedError,
    InvalidServiceError,
    InvalidServiceOperationError,
    InvalidTypeForParameterError,
    MalformedFilterError,
    MissingOperationError,
    MissingRequiredParametersError,
    ParameterSchemaValidationError,
    ParameterValidationErrorRecord,
    ServiceNotAllowedError,
    ShortHandParserError,
    UnknownFiltersError,
)
from awslabs.aws_api_mcp_server.core.parser.parser import parse
from unittest.mock import patch


@pytest.mark.parametrize(
    'command,service',
    [
        ('aws s4 ls', 's4'),
        ('aws cloud8 list-environments', 'cloud8'),
    ],
)
def test_invalid_service(command, service):
    """Test that an invalid service raises InvalidServiceError."""
    with pytest.raises(InvalidServiceError, match=service):
        parse(command)


@pytest.mark.parametrize(
    'command,service',
    [
        ('aws configure', 'configure'),
        ('aws history list', 'history'),
    ],
)
def test_service_not_allowed(command, service):
    """Test that not allowed services raises the right exception."""
    with pytest.raises(ServiceNotAllowedError, match=service):
        parse(command)


@pytest.mark.parametrize(
    'command,operation',
    [
        ('aws ec2 lss', 'lss'),
        ('aws cloud9 list-environments-1', 'list-environments-1'),
        # This also asserts that we do not exit the library due to `--version` being passed as a parameter
        (
            'aws ec2 describe-instance-profile-associations --instance-profile-name MyProfile --version 6',
            'describe-instance-profile-associations',
        ),
    ],
)
def test_invalid_operation(command, operation):
    """Test that an invalid operation raises InvalidServiceOperationError."""
    with pytest.raises(InvalidServiceOperationError, match=operation):
        parse(command)


@pytest.mark.parametrize(
    'command',
    [
        'aws ec2',
        'aws s3api --region us-east-1',
    ],
)
def test_missing_operation(command):
    """Test that missing operation raises MissingOperationError."""
    with pytest.raises(MissingOperationError):
        parse(command)


@pytest.mark.parametrize(
    'command,message',
    [
        (
            'aws cloud9 describe-environment-status',
            str(
                MissingRequiredParametersError(
                    'cloud9',
                    'describe-environment-status',
                    ['--environment-id'],
                    CommandMetadata('cloud9', None, 'DescribeEnvironmentStatus'),
                )
            ),
        ),
    ],
)
def test_missing_required_parameters(command, message):
    """Test that missing required parameters raise MissingRequiredParametersError."""
    with pytest.raises(MissingRequiredParametersError, match=message):
        parse(command)


@pytest.mark.parametrize(
    'command,message',
    [
        (
            'aws datazone get-project --domain-id dzd_48zojaeqnhm45s --project-id c93nhfs5467guo',
            str(
                InvalidParametersReceivedError(
                    'datazone',
                    'get-project',
                    ['--project-id'],
                    [
                        '--domain-identifier',
                        '--identifier',
                    ],
                )
            ),
        ),
        (
            'aws datazone get-project --domain-identifier dzd_48zojaeqnhm45s --project-id c93nhfs5467guo',
            str(
                InvalidParametersReceivedError(
                    'datazone',
                    'get-project',
                    ['--project-id'],
                    [
                        '--domain-identifier',
                        '--identifier',
                    ],
                )
            ),
        ),
        (
            'aws ec2 describe-transit-gateway-peering-attachments --transit-gateway-peering-attachment-ids tgw-attach-4455667788aabbccd',
            str(
                InvalidParametersReceivedError(
                    'ec2',
                    'describe-transit-gateway-peering-attachments',
                    ['--transit-gateway-peering-attachment-ids'],
                    [
                        '--filters, --max-items, --max-results, --next-token, --page-size, --starting-token, --transit-gateway-attachment-ids'
                    ],
                )
            ),
        ),
        (
            'aws cloud9 describe-environment-status --evnironment-id 1234',
            str(
                InvalidParametersReceivedError(
                    'cloud9',
                    'describe-environment-status',
                    ['--evnironment-id'],
                    ['--environment-id'],
                )
            ),
        ),
    ],
)
def test_hallucinated_parameters_are_detected(command, message):
    """Test that hallucinated parameters are detected and raise InvalidParametersReceivedError."""
    with pytest.raises(InvalidParametersReceivedError, match=re.escape(message)):
        parse(command)


@pytest.mark.parametrize(
    'command',
    [
        # Cloud9 available region
        'aws cloud9 list-environments --region us-east-1',
        # Cloud9 is available in il-central-1
        'aws cloud9 list-environments --region il-central-1',
        # Health is available in us-east-2
        'aws health describe-events --region us-east-2',
        # Health is available in us-east-1
        'aws health describe-events --region us-east-1',
        # Health is NOT available in af-south-1 but aws-cli has a special handling for it, default to us-east-1
        'aws health describe-events --region af-south-1',
        # Devicefarm is ONLY available in region us-west-2, code defaults to correct region
        'aws devicefarm list-devices --region us-west-1',
    ],
)
def test_for_valid_regions(command):
    """Test that valid regions are accepted for commands."""
    parse(command)


@pytest.mark.parametrize(
    'command, message',
    [
        (
            'aws ec2 get-subnet-cidr-reservations --subnet-id 12 --color START',
            str(InvalidChoiceForParameterError('color', 'START')),
        )
    ],
)
def test_invalid_choice_for_option(command, message):
    """Test that an invalid choice for an option raises InvalidChoiceForParameterError."""
    with pytest.raises(InvalidChoiceForParameterError, match=message):
        parse(command)


@pytest.mark.parametrize(
    'command, message',
    [
        (
            'aws databrew list-jobs --max-items MAXITEMS',
            str(InvalidTypeForParameterError('--max-items', int)),
        )
    ],
)
def test_invalid_type_for_parameter(command, message):
    """Test that an invalid type for a parameter raises InvalidTypeForParameterError."""
    with pytest.raises(InvalidTypeForParameterError, match=message):
        parse(command)


@pytest.mark.parametrize(
    'command, message',
    [
        (
            'aws lambda  update-function-code --function-name MyFunction --zip-file  fileb://newfunction.zip',
            str(
                CommandValidationError(
                    '-zip-file must be a zip file with the fileb:// prefix.\nExample usage:  --zip-file fileb://path/to/file.zip'
                )
            ),
        )
    ],
)
def test_command_validation_error_for_parameter(command, message):
    """Test that a command validation error is raised for invalid parameters."""
    with pytest.raises(CommandValidationError, match=message):
        parse(command)


@pytest.mark.parametrize(
    'command, messages',
    [
        (
            'aws iot describe-certificate --certificate-id 4f0ba',
            [
                "The parameter '--certificate-id' received an invalid input: "
                + 'Invalid length for parameter input, value: 5, valid min length: 64'
            ],
        ),
        (
            'aws --region=us-east-1 inspector2 list-findings --filter-criteria \'{"myKey": 1}\' '
            + "--sort-criteria 'field=AWS_ACCOUNT_ID,_sortOrder=desc'",
            [
                "The parameter '--filter-criteria' received an invalid input: "
                + 'Unknown parameter in input: "myKey", must be one of: findingArn, awsAccountId,',
                "\nThe parameter '--sort-criteria' received an invalid input: "
                + 'Missing required parameter in input: "sortOrder"',
            ],
        ),
    ],
)
def test_schema_validation(command, messages):
    """Test that schema validation errors are raised for invalid input."""
    with pytest.raises(ParameterSchemaValidationError, match='.+'.join(messages)):
        parse(command)


@pytest.mark.parametrize(
    'command, message',
    [
        (
            'aws kinesis get-records --shard-iterator',
            str(
                ExpectedArgumentError(
                    '--shard-iterator',
                    'expected one argument',
                    CommandMetadata('kinesis', None, 'GetRecords'),
                )
            ),
        )
    ],
)
def test_expected_required_argument(command, message):
    """Test that missing required argument raises ExpectedArgumentError."""
    with pytest.raises(ExpectedArgumentError, match=message):
        parse(command)


@pytest.mark.parametrize(
    'command',
    [
        "aws apigateway get-export --parameters extensions='postman' --rest-api-id a1b2c3d4e5 --stage-name dev --export-type swagger -",
    ],
)
def test_does_not_crash_on_parameter_without_value(command):
    """Test that parser does not crash when a parameter is missing a value."""
    parse(command)


@pytest.mark.parametrize(
    'command, error, params',
    [
        (
            'aws dynamodb scan --table-name a --scan-filter <',
            ShortHandParserError,
            ('--scan-filter', "Expected: '=', received: '<' for input:\n"),
        ),
    ],
)
def test_does_not_crash_on_invalid_command(command, error, params):
    """Test that parser does not crash on invalid command and raises the correct error."""
    with pytest.raises(error, match=re.escape(str(error(*params)))):
        parse(command)


@pytest.mark.parametrize(
    'command',
    [
        # EC2 filter by tag
        'aws ec2 --region eu-west-2 describe-instances --filters Name=tag:Name,Values=instance',
        'aws --region eu-west-2 ssm list-documents --filters Key=tag:region,Values=east,west',
    ],
)
def test_tag_key_filter(command):
    """Test that tag key filters are parsed without error."""
    parse(command)


@pytest.mark.parametrize(
    'command,error_class,message',
    [
        (
            'aws ssm list-documents --filters Key=Unknown,Values=Automation',
            UnknownFiltersError,
            str(
                UnknownFiltersError(
                    'ssm',
                    ['Unknown'],
                )
            ),
        ),
        (
            'aws ssm list-commands --filters key=InvokedAfter,value=2020-02-01T00:00:00Z,type=Equal',
            MalformedFilterError,
            str(
                MalformedFilterError(
                    'ssm', 'list-commands', {'key', 'value', 'type'}, {'key', 'value'}
                )
            ),
        ),
    ],
)
def test_filter_validation_errors(command, error_class, message):
    """Test that filter validation errors raise the correct exception."""
    with pytest.raises(error_class, match=re.escape(message)):
        parse(command)


@pytest.mark.parametrize(
    'command',
    [
        # https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_ListCommands.html
        'aws ssm list-commands --filters "key=InvokedAfter,value=2020-02-01T00:00:00Z"',
        # the command below passes client side validation in AWS CLI but fails server side validation
        'aws ssm list-commands --filters "key=UnknownKey,value=2020-02-01T00:00:00Z"',
    ],
)
def test_filter_validation_is_bypassed_when_docs_are_missing(command):
    """Test that filter key validation is bypassed when documentation is missing.

    Filter key names (like InvokedAfter in '--filters key=InvokedAfter,value=...') are extracted
    from documentation in get_operation_filters. This approach doesn't work in all cases, and
    this test checks that filter key validation is bypassed when get_operation_filters fails to
    extract key names. If not bypassed, validation can fail for valid commands.
    """
    parse(command)


@pytest.mark.parametrize(
    'command',
    [
        'aws ssm list-documents --filters Key=DocumentType,Values=Automation',
        'aws ssm list-documents --filters Key=Owner,Values=Self',
        'aws ssm list-documents --filters Key=PlatformTypes,Values=Linux',
        'aws ssm list-documents --filters Key=Name,Values=AWS-A',
        'aws ssm list-documents --filters Key=SearchKeyword,Values=trail,enable',
        'aws ssm list-documents --filters Key=DocumentType,Values=Automation Key=SearchKeyword,Values=Bucket,Logging',
        'aws ssm list-documents --filters '
        + '\'[{"Key": "DocumentType", "Values": ["Automation"]}, {"Key": "SearchKeyword", "Values": ["Bucket", "Logging"]}]\'',
    ],
)
def test_ssm_list_documents_filters(command):
    """Test that SSM list-documents filters are parsed without error."""
    parse(command)


@pytest.mark.parametrize(
    'command',
    [
        'aws ecs describe-clusters --cluster NikeBirdTestingStack-TestClusterE0095054-mrCdRAUoOji0',
        'aws ecs describe-clusters --clusters NikeBirdTestingStack-TestClusterE0095054-mrCdRAUoOji0',
    ],
)
def test_plural_singular_params(command):
    """Test that singular and plural parameter forms are supported."""
    parse(command)


@pytest.mark.parametrize(
    'command',
    [
        'aws s3api get-bucket-location --bucket=deploymentloggingbucke-9c88ebe0707be65d2518510c64917283d761bf03',
        "aws ec2 describe-availability-zones --query='AvailabilityZones[?ZoneName==`us-east-1a`]'",
        'aws s3api get-bucket-lifecycle --bucket my-s3-bucket',
        'aws --region=us-east-1 ec2 get-subnet-cidr-reservations --subnet-id subnet-012 --color=on',
        'aws s3api get-object --bucket aws-sam-cli-managed-default-samclisourcebucket --key lambda-sqs-sam-test-1/1f1a15295b5529effed491b54a5b5b83.template -',
        "aws apigateway get-export --parameters extensions='postman' --rest-api-id a1b2c3d4e5 --stage-name dev --export-type swagger -",
    ],
)
def test_should_pass_for_valid_equal_sign_params(command):
    """Test that valid equal sign parameters are accepted."""
    parse(command)


@pytest.mark.parametrize(
    'command',
    # All these are valid
    [
        'aws datazone get-project --domain-identifier dzd_48zojaeqnhm45s --identifier c93nhfs5467gu',
        'aws datazone get-project --domain-id dzd_48zojaeqnhm45s --identifier c93nhfs5467gu',
        'aws datazone get-project --domain-id dzd_48zojaeqnhm45s --id c93nhfs5467gu',
        'aws datazone list-data-sources --domain-identifier dzd_3k1qn3y0j4a9e4 --project-identifier d06ions0xledxs',
        'aws datazone list-data-sources --domain-identifier dzd_3k1qn3y0j4a9e4 --project d06ions0xledxs',
    ],
)
def test_prefix_parameter(command):
    """Test that the AWS CLI supports prefixes for its parameters."""
    parse(command)


@pytest.mark.parametrize(
    'command',
    # All these are valid
    [
        'aws ssm list-nodes --filters Type=Equal,Key=Region,Values=us-west-2 --sync-name AWS-QuickSetup-ManagedNode',
        'aws ssm list-nodes --filters Key=PlatformType,Values=Linux,Type=Equal',
        'aws ssm list-nodes --filters Key=PlatformType,Values=Windows,Type=Equal',
        'aws ssm list-nodes --filters Type=Equal,Key=AccountId,Values=877423370825 --sync-name AWS-QuickSetup-ManagedNode',
        "aws ssm list-nodes --filters Type=Equal,Key=PlatformName,Values='Amazon Linux' Type=Equal,Key=PlatformVersion,Values=1 --sync-name AWS-QuickSetup-ManagedNode",
        "aws ssm list-nodes --filters Type=Equal,Key=PlatformName,Values='Microsoft Windows Server 2019 Datacenter' --sync-name AWS-QuickSetup-ManagedNode",
        'aws ssm list-nodes --filters Type=Equal,Key=PlatformName,Values=Ubuntu Type=Equal,Key=PlatformVersion,Values=20.04 Type=Equal,Key=Region,Values=us-west-2 --sync-name AWS-QuickSetup-ManagedNode',
        "aws ssm list-nodes --filters Type=Equal,Key=PlatformName,Values='Red Hat Enterprise Linux' Type=Equal,Key=PlatformVersion,Values=8.9 Type=Equal,Key=OrganizationalUnitId,Values=ou-1234-abcd1234efgh5678 --sync-name AWS-QuickSetup-ManagedNode",
        'aws ssm list-nodes --filters Type=Equal,Key=AgentType,Values=amazon-ssm-agent Type=Equal,Key=AgentVersion,Values=3.3.1142.0',
        "aws ssm list-nodes --filters Type=Equal,Key=PlatformName,Values='Amazon Linux' Type=Equal,Key=PlatformVersion,Values=2 Type=Equal,Key=AccountId,Values=877423370825 Type=Equal,Key=AgentType,Values=amazon-ssm-agent Type=Equal,Key=AgentVersion,Values=3.3.1230.0 --sync-name AWS-QuickSetup-ManagedNode",
        "aws ssm list-nodes --filters Type=Equal,Key=PlatformName,Values='Microsoft Windows Server 2008 R2 Enterprise' Type=Equal,Key=Region,Values=eu-central-1 --sync-name AWS-QuickSetup-ManagedNode",
        "aws ssm list-nodes --filters Type=Equal,Key=PlatformName,Values='CentOS Linux' Type=Equal,Key=PlatformVersion,Values=7 Type=Equal,Key=OrganizationalUnitId,Values=ou-1234-abcd1234efgh5678 --sync-name AWS-QuickSetup-ManagedNode",
        'aws ssm list-nodes --filters Type=Equal,Key=PlatformName,Values=Ubuntu Type=Equal,Key=AccountId,Values=917775104684 --sync-name AWS-QuickSetup-ManagedNode',
        'aws ssm list-nodes --filters Type=Equal,Key=PlatformType,Values=Linux Type=Equal,Key=PlatformName,Values=Bottlerocket Type=Equal,Key=PlatformVersion,Values=1.19.5 Type=Equal,Key=Region,Values=us-east-1,us-east-2 --sync-name AWS-QuickSetup-ManagedNode',
    ],
)
def test_valid_ssm_cli_commands_only_filters(command: str):
    """Test that valid SSM CLI commands with only filters are accepted."""
    parse(command)


@pytest.mark.parametrize(
    'command',
    # All these are valid
    [
        'aws ssm list-nodes-summary --aggregators AggregatorType=Count,TypeName=Instance,AttributeName=ResourceType',
        'aws ssm list-nodes-summary --aggregators AggregatorType=Count,TypeName=Instance,AttributeName=ResourceType --sync-name AWS-QuickSetup-ManagedNode',
        "aws ssm list-nodes-summary --aggregators AggregatorType=Count,TypeName=Instance,AttributeName=AgentVersion --filters Type=Equal,Key=OrganizationalUnitId,Values=ou-1234-abcd1234efgh5678 Type=Equal,Key=PlatformName,Values='Red Hat Enterprise Linux Server' --sync-name AWS-QuickSetup-ManagedNode",
        "aws ssm list-nodes-summary --aggregators AggregatorType=Count,TypeName=Instance,AttributeName=PlatformType --filters Type=Equal,Key=PlatformName,Values='Microsoft Windows Server 2022 Standard' --sync-name AWS-QuickSetup-ManagedNode",
        'aws ssm list-nodes-summary --aggregators AggregatorType=Count,TypeName=Instance,AttributeName=ResourceType --filters Type=Equal,Key=PlatformVersion,Values=22.04 Type=Equal,Key=PlatformName,Values=Ubuntu Type=Equal,Key=Region,Values=us-west-2 --sync-name AWS-QuickSetup-ManagedNode',
        'aws ssm list-nodes-summary --aggregators AggregatorType=Count,TypeName=Instance,AttributeName=ResourceType --filters Type=Equal,Key=AgentVersion,Values=3.3.1132.0 Type=Equal,Key=AgentType,Values=amazon-ssm-agent',
        "aws ssm list-nodes-summary --aggregators AggregatorType=Count,TypeName=Instance,AttributeName=AgentVersion --filters Type=Equal,Key=AgentType,Values=amazon-ssm-agent Type=Equal,Key=PlatformVersion,Values=2 Type=Equal,Key=PlatformName,Values='Amazon Linux' --sync-name AWS-QuickSetup-ManagedNode",
        "aws ssm list-nodes-summary --aggregators AggregatorType=Count,TypeName=Instance,AttributeName=ResourceType --filters Type=Equal,Key=Region,Values=eu-central-1 Type=Equal,Key=PlatformName,Values='Amazon Linux' --sync-name AWS-QuickSetup-ManagedNode",
        "aws ssm list-nodes-summary --aggregators AggregatorType=Count,TypeName=Instance,AttributeName=ResourceType --filters Type=Equal,Key=OrganizationalUnitId,Values=ou-1234-abcd1234efgh5678 Type=Equal,Key=PlatformName,Values='CentOS Linux' --sync-name AWS-QuickSetup-ManagedNode",
        'aws ssm list-nodes-summary --aggregators AggregatorType=Count,TypeName=Instance,AttributeName=ResourceType --filters Type=Equal,Key=PlatformType,Values=Linux --sync-name AWS-QuickSetup-ManagedNode',
        'aws ssm list-nodes-summary --aggregators AggregatorType=Count,TypeName=Instance,AttributeName=AgentVersion --filters Type=Equal,Key=AccountId,Values=877423370825 Type=Equal,Key=AgentType,Values=amazon-ssm-agent --sync-name AWS-QuickSetup-ManagedNode',
        'aws ssm list-nodes-summary --aggregators AggregatorType=Count,TypeName=Instance,AttributeName=Region --filters Type=Equal,Key=PlatformName,Values=SLES --sync-name AWS-QuickSetup-ManagedNode',
        'aws ssm list-nodes-summary --aggregators AggregatorType=Count,TypeName=Instance,AttributeName=ResourceType --filters Type=Equal,Key=Region,Values=us-west-2 --sync-name AWS-QuickSetup-ManagedNode',
    ],
)
def test_valid_ssm_cli_commands_filters_and_attributes(command: str):
    """Test that valid SSM CLI commands with filters and attributes are accepted."""
    parse(command)


def test_ssm_cli_raises_parameter_schema_validation_error_when_windows_server_shorthand_used():
    """Test that a schema validation error is raised for Windows Server shorthand in SSM CLI."""
    command = "aws ssm list-nodes-summary --aggregators AggregatorType=Count,TypeName=Instance,AttributeName=ResourceType --filters Type=Equal,Key=PlatformName,Values='Windows Server 2022' --sync-name AWS-QuickSetup-ManagedNode"
    with pytest.raises(
        ParameterSchemaValidationError,
        match=re.escape(
            str(
                ParameterSchemaValidationError(
                    [
                        ParameterValidationErrorRecord(
                            parameter='Filters',
                            reason="Incorrect value Windows Server 2022 for key PlatformName. Use instead: Key=PlatformName,Values='Microsoft Windows Server 2022 Standard',Type=Equal ",
                        )
                    ]
                )
            )
        ),
    ):
        parse(command)


def test_ssm_cli_raises_parameter_schema_validation_error_when_platform_type_should_be_used_instead_of_platform_name():
    """Test that a schema validation error is raised when PlatformType should be used instead of PlatformName."""
    command = 'aws ssm list-nodes --filters Key=PlatformName,Values=Linux,Type=Equal --sync-name AWS-QuickSetup-ManagedNode'
    with pytest.raises(
        ParameterSchemaValidationError,
        match=str(
            ParameterSchemaValidationError(
                [
                    ParameterValidationErrorRecord(
                        parameter='Filters',
                        reason="Incorrect value Linux for key PlatformName. Use instead Key=PlatformType,Values='Linux',Type=Equal",
                    )
                ]
            )
        ),
    ):
        parse(command)


def test_ssm_cli_raises_parameter_schema_validation_error_when_platform_name_should_be_used_instead_of_platform_type():
    """Test that a schema validation error is raised when PlatformName should be used instead of PlatformType."""
    command = "aws ssm list-nodes --filters Key=PlatformType,Values='Amazon Linux',Type=Equal --sync-name AWS-QuickSetup-ManagedNode"
    with pytest.raises(
        ParameterSchemaValidationError,
        match=re.escape(
            str(
                ParameterSchemaValidationError(
                    [
                        ParameterValidationErrorRecord(
                            parameter='Filters',
                            reason="Incorrect value Amazon Linux for key PlatformType, accepted values are: ['linux', 'windows', 'macos']. Use instead: Key=PlatformName,Values='Amazon Linux',Type=Equal",
                        )
                    ]
                )
            )
        ),
    ):
        parse(command)


def test_ssm_cli_raises_parameter_schema_validation_error_when_sync_name_is_expected_but_missing():
    """Test that a schema validation error is raised when --sync-name is required but missing."""
    command = 'aws ssm list-nodes --filters Type=Equal,Key=AccountId,Values=91777510468'
    with pytest.raises(
        ParameterSchemaValidationError,
        match='the parameter and value --sync-name AWS-QuickSetup-ManagedNode is required for this command.',
    ):
        parse(command)


@pytest.mark.parametrize(
    'command',
    # All these are valid
    [
        'aws ssm list-nodes --filters Key=PlatformType,Values=Windows,Type=Equal',
        'aws ssm list-nodes --filters Key=PlatformType,Values=windows,Type=Equal',
        'aws ssm list-nodes --filters Key=PlatformType,Values=MacOs,Type=Equal',
        'aws ssm list-nodes --filters Key=PlatformType,Values=macos,Type=Equal',
        'aws ssm list-nodes --filters Key=PlatformType,Values=MACOS,Type=Equal',
        "aws ssm list-nodes-summary --aggregators AggregatorType=Count,TypeName=Instance,AttributeName=PlatformType --filters Type=Equal,Key=PlatformName,Values='Microsoft Windows Server 2022 Standard' --sync-name AWS-QuickSetup-ManagedNode",
        "aws ssm list-nodes-summary --aggregators AggregatorType=Count,TypeName=Instance,AttributeName=PlatformVersion --filters Type=Equal,Key=PlatformName,Values='microsoft windows server 2022 standard' --sync-name AWS-QuickSetup-ManagedNode",
        "aws ssm list-nodes-summary --aggregators AggregatorType=Count,TypeName=Instance,AttributeName=ResourceType --filters Type=Equal,Key=PlatformName,Values='MicroSOFT windows Server 2022 sTaNdard' --sync-name AWS-QuickSetup-ManagedNode",
    ],
)
def test_ssm_cli_validation_is_case_insensitive(command: str):
    """Test that SSM CLI validation is case insensitive."""
    parse(command)


def test_ssm_cli_raises_parameter_schema_validation_error_when_platform_version_missing():
    """Test that a schema validation error is raised when PlatformVersion is missing for Amazon Linux 2."""
    command = "aws ssm list-nodes --filters Key=PlatformName,Values='Amazon Linux 2',Type=Equal"
    with pytest.raises(
        ParameterSchemaValidationError,
        match=re.escape(
            str(
                ParameterSchemaValidationError(
                    [
                        ParameterValidationErrorRecord(
                            parameter='Filters',
                            reason="Incorrect value Amazon Linux 2 for key PlatformName. Also version suffix 2 should be part of PlatformVersion. Use instead:Key=PlatformName,Values='Amazon Linux',Type=Equal Key=PlatformVersion,Values='2',Type=Equal",
                        )
                    ]
                )
            )
        ),
    ):
        parse(command)


def test_client_side_filter_error():
    """Test that a malformed client-side filter raises an error."""
    command = 'aws ec2 describe-instances --query "Reservations[[]"'
    with pytest.raises(
        ClientSideFilterError, match="Error parsing client-side filter 'Reservations[[]'*"
    ):
        parse(command)


@pytest.mark.parametrize(
    'command',
    [
        'aws s3api get-object --bucket aws-sam-cli-managed-default-samclisourcebucket --key lambda-sqs-sam-test-1/1f1a15295b5529effed491b54a5b5b83.template myfile.template',
        'aws lambda invoke --function-name my-function response.json',
    ],
)
def test_outfile_parameter_not_supported(command):
    """Test that outfile parameters raise a validation error."""
    with pytest.raises(
        CommandValidationError,
        match='Output file parameters are not supported yet. Use - as the output file to get the requested data in the response.',
    ):
        parse(command)


def test_valid_expand_user_home_directory():
    """Test that tilde is replaced with user home directory."""
    result = parse(cli_command='aws s3 cp s3://my_file ~/temp/test.txt')
    assert not any(param.startswith('~') for param in result.parameters['--paths'])


def test_invalid_expand_user_home_directory():
    """Test that tilde is not replaced."""
    result = parse(cli_command='aws s3 cp s3://my_file ~user_that_does_not_exist/temp/test.txt')
    assert any(param.startswith('~') for param in result.parameters['--paths'])


@patch('boto3.Session')
def test_profile(mock_boto3_session):
    """Test that the profile is correctly extracted."""
    mock_session_instance = mock_boto3_session.return_value
    mock_session_instance.region_name = 'us-east-1'

    result = parse(cli_command='aws s3api list-buckets --profile test-profile')
    assert result.profile == 'test-profile'
    mock_boto3_session.assert_called_with(profile_name='test-profile')
