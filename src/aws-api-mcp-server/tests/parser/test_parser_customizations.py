import pytest
from awslabs.aws_api_mcp_server.core.common.command import IRCommand
from awslabs.aws_api_mcp_server.core.common.errors import (
    CommandValidationError,
    FileParameterError,
    InvalidServiceOperationError,
    MissingRequiredParametersError,
    OperationNotAllowedError,
)
from awslabs.aws_api_mcp_server.core.parser.parser import (
    ALLOWED_CUSTOM_OPERATIONS,
    is_custom_operation,
    is_denied_custom_operation,
    parse,
)
from tests.fixtures import create_file_open_mock
from unittest.mock import patch


def test_wait_is_custom_operation():
    """Test if wait is classified as custom operation."""
    assert is_custom_operation('s3api', 'wait')


def test_custom_operation_is_detected():
    """Test a custom operation is detected as such."""
    for service, operations in ALLOWED_CUSTOM_OPERATIONS.items():
        if service == '*':
            continue
        for operation in operations:
            assert is_custom_operation(service, operation), (
                f'is_custom_operation incorrectly false for {service} {operation}'
            )


def test_s3api_list_buckets_not_custom():
    """Test non-custom operation returns false."""
    assert not is_custom_operation('s3api', 'list-buckets')


def test_non_custom_operation_not_denied():
    """Test non-custom operation is never denied."""
    assert not is_denied_custom_operation('s3api', 'list-buckets')


@pytest.mark.parametrize(
    'service,operation',
    [
        ('emr', 'ssh'),
        ('emr', 'sock'),
        ('emr', 'get'),
        ('emr', 'put'),
        ('deploy', 'install'),
        ('deploy', 'uninstall'),
    ],
)
def test_custom_command_not_in_allow_list_denied(service, operation):
    """Test non-custom operation is never denied."""
    assert is_denied_custom_operation(service, operation)


# S3 Customization Tests
def test_s3_ls_no_args():
    """Test aws s3 ls with no arguments."""
    result = parse('aws s3 ls')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 's3'
    assert result.command_metadata.operation_sdk_name == 'ls'
    assert result.is_awscli_customization is True
    assert result.parameters == {
        '--paths': 's3://',
        '--dir-op': False,
        '--human-readable': False,
        '--summarize': False,
    }


def test_s3_ls_with_bucket():
    """Test aws s3 ls with a specific bucket."""
    result = parse('aws s3 ls s3://my-bucket')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 's3'
    assert result.command_metadata.operation_sdk_name == 'ls'
    assert result.is_awscli_customization is True
    assert result.parameters['--paths'] == 's3://my-bucket'


def test_s3_ls_with_bucket_and_prefix():
    """Test aws s3 ls with bucket and prefix."""
    result = parse('aws s3 ls s3://my-bucket/prefix/')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 's3'
    assert result.command_metadata.operation_sdk_name == 'ls'
    assert result.is_awscli_customization is True
    assert result.parameters['--paths'] == 's3://my-bucket/prefix/'


def test_s3_ls_with_flags():
    """Test aws s3 ls with human-readable flag."""
    result = parse('aws s3 ls --human-readable')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 's3'
    assert result.command_metadata.operation_sdk_name == 'ls'
    assert result.is_awscli_customization is True
    assert result.parameters['--human-readable'] is True


def test_s3_ls_with_bucket_and_flags():
    """Test aws s3 ls with bucket and flags."""
    result = parse('aws s3 ls s3://my-bucket --human-readable --summarize')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 's3'
    assert result.command_metadata.operation_sdk_name == 'ls'
    assert result.is_awscli_customization is True
    assert result.parameters['--paths'] == 's3://my-bucket'
    assert result.parameters['--human-readable'] is True
    assert result.parameters['--summarize'] is True


def test_s3_cp_no_args():
    """Test aws s3 cp with no arguments (should fail with missing required params)."""
    with pytest.raises(MissingRequiredParametersError) as exc_info:
        parse('aws s3 cp')

    assert 'paths' in str(exc_info.value)


def test_s3_cp_with_source_and_dest():
    """Test aws s3 cp with source and destination."""
    import os
    from awslabs.aws_api_mcp_server.core.common.config import WORKING_DIRECTORY

    # Use working directory path instead of /tmp/
    local_file_path = os.path.join(WORKING_DIRECTORY, 'local-file.txt')
    result = parse(f'aws s3 cp {local_file_path} s3://my-bucket/')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 's3'
    assert result.command_metadata.operation_sdk_name == 'cp'
    assert result.is_awscli_customization is True
    assert result.parameters['--paths'] == [local_file_path, 's3://my-bucket/']


def test_s3_mv_with_source_and_dest():
    """Test aws s3 mv with source and destination."""
    result = parse('aws s3 mv s3://source-bucket/file.txt s3://dest-bucket/')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 's3'
    assert result.command_metadata.operation_sdk_name == 'mv'
    assert result.is_awscli_customization is True
    assert result.parameters['--paths'] == ['s3://source-bucket/file.txt', 's3://dest-bucket/']


def test_s3_rm_with_bucket():
    """Test aws s3 rm with a bucket path."""
    result = parse('aws s3 rm s3://my-bucket/file.txt')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 's3'
    assert result.command_metadata.operation_sdk_name == 'rm'
    assert result.is_awscli_customization is True
    assert result.parameters['--paths'] == [
        's3://my-bucket/file.txt'
    ]  # Returns a list, not a string


def test_s3_cp_stdin_as_source_blocked():
    """Test that 'aws s3 cp - s3://bucket/key' (stdin) is blocked."""
    expected_message = (
        "Invalid file parameter '-' for service 's3' and operation 'cp': "
        "streaming file ('-') is not allowed. Please provide a valid file path."
    )
    with pytest.raises(FileParameterError) as exc_info:
        parse('aws s3 cp - s3://my-bucket/file.txt')

    error = exc_info.value
    assert str(error) == expected_message
    assert error._service == 's3'
    assert error._operation == 'cp'
    assert error._file_path == '-'


def test_s3_cp_stdout_as_destination_blocked():
    """Test that 'aws s3 cp s3://bucket/key -' (stdout) is blocked."""
    expected_message = (
        "Invalid file parameter '-' for service 's3' and operation 'cp': "
        "streaming file ('-') is not allowed. Please provide a valid file path."
    )
    with pytest.raises(FileParameterError) as exc_info:
        parse('aws s3 cp s3://my-bucket/file.txt -')

    error = exc_info.value
    assert str(error) == expected_message
    assert error._service == 's3'
    assert error._operation == 'cp'
    assert error._file_path == '-'


# ConfigService Customization Tests
def test_configservice_get_status_no_args():
    """Test aws configservice get-status with no arguments."""
    result = parse('aws configservice get-status')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 'configservice'
    assert result.command_metadata.operation_sdk_name == 'get-status'
    assert result.is_awscli_customization is True
    assert result.parameters == {}  # No required parameters


def test_configservice_get_status_with_region():
    """Test aws configservice get-status with region."""
    result = parse('aws configservice get-status --region us-east-1')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 'configservice'
    assert result.command_metadata.operation_sdk_name == 'get-status'
    assert result.is_awscli_customization is True
    assert result.region == 'us-east-1'


def test_custom_operation_not_in_allow_list_denied():
    """Test operation not in allowlist fails with not allowed."""
    with pytest.raises(OperationNotAllowedError) as exc_info:
        parse('aws emr ssh')

    assert 'not allowed' in str(exc_info.value)


# EMR Customization Tests
def test_emr_describe_cluster_no_args():
    """Test aws emr add-steps with no arguments (should fail with missing required params)."""
    with pytest.raises(MissingRequiredParametersError) as exc_info:
        parse('aws emr describe-cluster')

    assert 'cluster-id' in str(exc_info.value)


def test_emr_add_steps_with_cluster_id():
    """Test aws emr add-steps with cluster ID (should fail with missing required params)."""
    with pytest.raises(MissingRequiredParametersError) as exc_info:
        parse('aws emr add-steps --cluster-id j-1234567890')

    assert 'steps' in str(exc_info.value)


def test_emr_describe_cluster_with_cluster_id():
    """Test aws emr describe-cluster with cluster ID."""
    result = parse('aws emr describe-cluster --cluster-id j-1234567890')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 'emr'
    assert result.command_metadata.operation_sdk_name == 'describe-cluster'
    assert result.is_awscli_customization is True
    assert result.parameters['--cluster-id'] == 'j-1234567890'


# RDS Customization Tests
def test_rds_generate_db_auth_token_no_args():
    """Test aws rds generate-db-auth-token with no arguments (should fail with missing required params)."""
    with pytest.raises(MissingRequiredParametersError) as exc_info:
        parse('aws rds generate-db-auth-token')

    error_msg = str(exc_info.value)
    assert 'hostname' in error_msg
    assert 'port' in error_msg
    assert 'username' in error_msg


def test_rds_generate_db_auth_token_with_all_required_args():
    """Test aws rds generate-db-auth-token with all required arguments."""
    result = parse('aws rds generate-db-auth-token --hostname myhost --port 3306 --username admin')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 'rds'
    assert result.command_metadata.operation_sdk_name == 'generate-db-auth-token'
    assert result.is_awscli_customization is True
    assert result.parameters['--hostname'] == 'myhost'
    assert result.parameters['--port'] == '3306'  # Port is a string, not an integer
    assert result.parameters['--username'] == 'admin'


def test_rds_generate_db_auth_token_with_region():
    """Test aws rds generate-db-auth-token with region."""
    result = parse(
        'aws rds generate-db-auth-token --hostname myhost --port 3306 --username admin --region us-east-1'
    )

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 'rds'
    assert result.command_metadata.operation_sdk_name == 'generate-db-auth-token'
    assert result.is_awscli_customization is True
    assert result.parameters['--hostname'] == 'myhost'
    assert result.parameters['--port'] == '3306'  # Port is a string, not an integer
    assert result.parameters['--username'] == 'admin'
    assert result.region == 'us-east-1'


# DataPipeline Customization Tests
def test_datapipeline_list_runs_no_args():
    """Test aws datapipeline list-runs with no arguments (should fail with missing required params)."""
    with pytest.raises(MissingRequiredParametersError) as exc_info:
        parse('aws datapipeline list-runs')

    assert 'pipeline-id' in str(exc_info.value)


def test_datapipeline_list_runs_with_pipeline_id():
    """Test aws datapipeline list-runs with pipeline ID."""
    result = parse('aws datapipeline list-runs --pipeline-id my-pipeline-id')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 'datapipeline'
    assert result.command_metadata.operation_sdk_name == 'list-runs'
    assert result.is_awscli_customization is True
    assert result.parameters['--pipeline-id'] == 'my-pipeline-id'


def test_datapipeline_list_runs_with_pipeline_id_and_region():
    """Test aws datapipeline list-runs with pipeline ID and region."""
    result = parse('aws datapipeline list-runs --pipeline-id my-pipeline-id --region us-east-1')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 'datapipeline'
    assert result.command_metadata.operation_sdk_name == 'list-runs'
    assert result.is_awscli_customization is True
    assert result.parameters['--pipeline-id'] == 'my-pipeline-id'
    assert result.region == 'us-east-1'


# Error Cases Tests
def test_invalid_s3_operation():
    """Test invalid S3 operation."""
    with pytest.raises(InvalidServiceOperationError) as exc_info:
        parse('aws s3 invalid-operation')

    assert 'invalid-operation' in str(exc_info.value)


def test_invalid_configservice_operation():
    """Test invalid ConfigService operation."""
    with pytest.raises(InvalidServiceOperationError) as exc_info:
        parse('aws configservice invalid-operation')

    assert 'invalid-operation' in str(exc_info.value)


def test_invalid_emr_operation():
    """Test invalid EMR operation."""
    with pytest.raises(InvalidServiceOperationError) as exc_info:
        parse('aws emr invalid-operation')

    assert 'invalid-operation' in str(exc_info.value)


def test_invalid_rds_operation():
    """Test invalid RDS operation."""
    with pytest.raises(InvalidServiceOperationError) as exc_info:
        parse('aws rds invalid-operation')

    assert 'invalid-operation' in str(exc_info.value)


# Edge Cases Tests
def test_s3_ls_with_empty_bucket():
    """Test aws s3 ls with empty bucket name."""
    result = parse('aws s3 ls s3://')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 's3'
    assert result.command_metadata.operation_sdk_name == 'ls'
    assert result.is_awscli_customization is True
    assert result.parameters['--paths'] == 's3://'


def test_s3_ls_with_special_characters_in_bucket():
    """Test aws s3 ls with special characters in bucket name."""
    result = parse('aws s3 ls s3://my-bucket-with-dashes_123')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 's3'
    assert result.command_metadata.operation_sdk_name == 'ls'
    assert result.is_awscli_customization is True
    assert result.parameters['--paths'] == 's3://my-bucket-with-dashes_123'


def test_rds_generate_db_auth_token_with_numeric_port():
    """Test aws rds generate-db-auth-token with numeric port."""
    result = parse('aws rds generate-db-auth-token --hostname myhost --port 5432 --username admin')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 'rds'
    assert result.command_metadata.operation_sdk_name == 'generate-db-auth-token'
    assert result.is_awscli_customization is True
    assert result.parameters['--port'] == '5432'  # Port is a string, not an integer


@patch(
    'awslabs.aws_api_mcp_server.core.common.file_system_controls.WORKING_DIRECTORY', '/test/path'
)
def test_local_file_uri():
    """Test aws command with URI input file parameter."""
    import io
    import zipfile

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(
            'lambda_function.py', 'def lambda_handler(event, context): return "Hello World"'
        )
    mock_zip_content = zip_buffer.getvalue()

    zip_file_path = '/test/path/lambda-deployment.zip'
    mock_open_side_effect, mock_files = create_file_open_mock(zip_file_path)

    with patch('builtins.open', side_effect=mock_open_side_effect):
        mock_file = mock_files[zip_file_path]
        mock_file.read.return_value = mock_zip_content

        result = parse(
            f'aws lambda create-function --function-name hello-world-lambda --runtime python3.9 '
            f'--role arn:aws:iam::123456789012:role/lambda-test-role --handler lambda_function.lambda_handler '
            f'--zip-file fileb://{zip_file_path} --description "A Hello World Lambda function"'
        )

        assert result.is_awscli_customization is False
        assert result.command_metadata.service_sdk_name == 'lambda'
        assert result.command_metadata.operation_sdk_name == 'CreateFunction'

        assert 'Code' in result.parameters
        assert 'ZipFile' in result.parameters['Code']
        assert isinstance(result.parameters['Code']['ZipFile'], bytes)
        assert result.parameters['Code']['ZipFile'] == mock_zip_content

        assert result.parameters['FunctionName'] == 'hello-world-lambda'
        assert result.parameters['Runtime'] == 'python3.9'
        assert result.parameters['Role'] == 'arn:aws:iam::123456789012:role/lambda-test-role'
        assert result.parameters['Handler'] == 'lambda_function.lambda_handler'
        assert result.parameters['Description'] == 'A Hello World Lambda function'


def test_http_uri_validation_error():
    """Test aws command with http:// URI throws validation error."""
    with pytest.raises(CommandValidationError) as exc_info:
        parse(
            'aws cloudformation create-stack --stack-name test-stack '
            '--template-body http://example.com/template.yaml'
        )

    error_message = str(exc_info.value)
    assert 'http:// prefix is not allowed' in error_message


def test_local_file_uri_validation_failure():
    """Test aws command with URI input file parameter outside the working directory."""
    with pytest.raises(
        CommandValidationError,
        match=r"File path '/etc/hosts' is outside the allowed working directory .*",
    ):
        result = parse('aws logs create-log-group --log-group-name file:///etc/hosts')

        assert result.is_awscli_customization is False
        assert result.command_metadata.service_sdk_name == 'lambda'
        assert result.command_metadata.operation_sdk_name == 'CreateFunction'
