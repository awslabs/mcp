import pytest
from awslabs.aws_api_mcp_server.core.common.command import IRCommand
from awslabs.aws_api_mcp_server.core.common.errors import (
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


def test_wait_allowed_for_all_custom_commands():
    """Test non-custom operation is never denied."""
    assert not is_denied_custom_operation('emr', 'wait')


@pytest.mark.parametrize(
    'service,operation',
    [
        ('emr', 'ssh'),
        ('emr', 'sock'),
        ('emr', 'get'),
        ('emr', 'put'),
        ('opsworks', 'register'),
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
    result = parse('aws s3 cp local-file.txt s3://my-bucket/')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 's3'
    assert result.command_metadata.operation_sdk_name == 'cp'
    assert result.is_awscli_customization is True
    assert result.parameters['--paths'] == ['local-file.txt', 's3://my-bucket/']


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


# Wait Commands Tests
def test_dynamodb_wait_table_exists():
    """Test aws dynamodb wait table-exists."""
    result = parse('aws dynamodb wait table-exists --table-name MyTable')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 'dynamodb'
    assert result.command_metadata.operation_sdk_name == 'wait table-exists'  # Includes subcommand
    assert result.is_awscli_customization is True
    assert result.parameters['--table-name'] == 'MyTable'


def test_ec2_wait_instance_running():
    """Test aws ec2 wait instance-running."""
    result = parse('aws ec2 wait instance-running --instance-ids i-1234567890abcdef0')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 'ec2'
    assert (
        result.command_metadata.operation_sdk_name == 'wait instance-running'
    )  # Includes subcommand
    assert result.is_awscli_customization is True
    assert result.parameters['--instance-ids'] == [
        'i-1234567890abcdef0'
    ]  # Returns a list, not a string


def test_ec2_wait_volume_available():
    """Test aws ec2 wait volume-available."""
    result = parse('aws ec2 wait volume-available --volume-ids vol-1234567890abcdef0')

    assert isinstance(result, IRCommand)
    assert result.command_metadata.service_sdk_name == 'ec2'
    assert (
        result.command_metadata.operation_sdk_name == 'wait volume-available'
    )  # Includes subcommand
    assert result.is_awscli_customization is True
    assert result.parameters['--volume-ids'] == [
        'vol-1234567890abcdef0'
    ]  # Returns a list, not a string


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


def test_invalid_wait_subcommand():
    """Test invalid wait subcommand."""
    with pytest.raises(InvalidServiceOperationError) as exc_info:
        parse('aws dynamodb wait invalid-subcommand')

    assert 'invalid-subcommand' in str(exc_info.value)


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
