# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for file access validation in AWS CLI command parsing.

File paths appear in AWS CLI commands in the following ways:

1. Required positional outfile arguments for operations with streaming output:
   - Example: `aws s3api get-object --bucket test-bucket --key test-key /path/to/file.txt`
   - Example: `aws lambda invoke --function-name my-function /path/to/response.json`
   - Validated in: `parser.py` via `_validate_outfile()` function

2. Blob-type arguments that accept file paths with `file://` or `fileb://` prefixes:
   - Example: `aws apigatewayv2 import-api --body file:///path/to/api.yaml`
   - Example: `aws lambda invoke --function-name test --payload file:///path/to/data.json -`
   - Example: `aws rekognition detect-text --image-bytes fileb:///path/to/image.jpg`
   - Validated in: `services.py` via `RESTRICTED_URI_HANDLER` registered with 'load-cli-arg' event

3. Streaming blob-type arguments that only accept file paths without URI prefixes:
   - Example: `aws s3api put-object --bucket bucket --key file.txt --body /path/to/file.txt`
   - Example: `aws s3api upload-part --bucket bucket --key file.txt --body /path/to/part.bin --part-number 1 --upload-id x`
   - Validated in: `services.py` via `_validate_streaming_blob_path()` registered with 'process-cli-arg.*.*' event

4. Path arguments in AWS CLI customizations:
   - Example: `aws s3 cp /path/to/file.txt s3://bucket/key`
   - Example: `aws s3 sync s3://bucket/prefix /path/to/folder`
   - Example: `aws cloudformation package --template-file /home/user/cfn/template.json --s3-bucket my-bucket`
   - Example: `aws emr create-cluster --release-label emr-5.30.0 --configurations file:///tmp/config.json --instance-type m5.xlarge --instance-count 3`
   - Configured in: `file_system_controls.py` via `CUSTOM_FILE_PATH_ARGUMENTS` and `CUSTOM_BLOB_ARGUMENTS`
   - Validated in: `parser.py` via `_validate_customization_file_paths()` function

File Access Control Modes:

The FILE_ACCESS_MODE configuration controls file system access through three modes:

- FileAccessMode.WORKDIR (default): Only file paths within WORKING_DIRECTORY are allowed.
  This provides a sandboxed environment for file operations.

- FileAccessMode.UNRESTRICTED: Allows file paths anywhere on the local file system,
  bypassing the working directory restriction.

- FileAccessMode.NO_ACCESS: Completely denies the use of local file paths in commands.
  S3 URIs (s3://...) and stdout redirect (-) remain allowed.
"""

import pytest
from awslabs.aws_api_mcp_server.core.common.config import WORKING_DIRECTORY, FileAccessMode
from awslabs.aws_api_mcp_server.core.common.errors import (
    FileParameterError,
    FilePathValidationError,
    LocalFileAccessDisabledError,
    OperationNotAllowedError,
)
from awslabs.aws_api_mcp_server.core.parser.parser import parse
from pathlib import Path
from unittest.mock import patch


@patch(
    'awslabs.aws_api_mcp_server.core.parser.parser.FILE_ACCESS_MODE',
    FileAccessMode.WORKDIR,
)
@patch(
    'awslabs.aws_api_mcp_server.core.common.file_system_controls.FILE_ACCESS_MODE',
    FileAccessMode.WORKDIR,
)
class TestDefaultFileAccessBehavior:
    """Tests for default file access validation behavior."""

    @patch(
        'awslabs.aws_api_mcp_server.core.common.file_system_controls.WORKING_DIRECTORY',
        Path.home(),
    )
    def test_valid_expand_user_home_directory(self):
        """Test that tilde or user home directory is invalid path."""
        result = parse(cli_command='aws s3 cp s3://my-bucket/my_file ~/temp/test.txt')
        assert result.command_metadata.service_sdk_name == 's3'
        assert result.command_metadata.operation_sdk_name == 'cp'
        assert len(result.parameters['--paths']) == 2
        assert result.parameters['--paths'][1] == str(Path.home() / 'temp' / 'test.txt')

    @patch(
        'awslabs.aws_api_mcp_server.core.common.file_system_controls.WORKING_DIRECTORY',
        Path.home(),
    )
    def test_valid_expand_user_home_directory_in_outfile_arg(self):
        """Test that tilde or user home directory is invalid path."""
        result = parse(
            cli_command='aws s3api get-object --bucket bucket --key file.txt ~/file.txt'
        )
        assert result.command_metadata.service_sdk_name == 's3'
        assert result.command_metadata.operation_sdk_name == 'GetObject'
        assert result.output_file is not None
        assert result.output_file.path == str(Path.home() / 'file.txt')

    @patch(
        'awslabs.aws_api_mcp_server.core.common.file_system_controls.WORKING_DIRECTORY',
        Path.home(),
    )
    def test_unexpanded_tilde_path_raises_error(self):
        """Test that unexpanded tilde paths are rejected."""
        with pytest.raises(FileParameterError, match='contains unexpanded tilde'):
            parse(cli_command='aws s3 cp s3://my_file ~user_that_does_not_exist/temp/test.txt')

    @pytest.mark.parametrize(
        'command',
        [
            ('aws s3api get-object --bucket test-bucket --key test-key ../outside/file.txt'),
            ('aws lambda invoke --function-name my-function ../response.json'),
        ],
    )
    def test_validate_output_file_raises_error_for_relative_paths_outside_workdir(self, command):
        """Test that _validate_output_file raises FileParameterError for relative paths resolved outside working directory."""
        with pytest.raises(FileParameterError, match='is outside the allowed working directory'):
            parse(command)

    @pytest.mark.parametrize(
        'command',
        [
            'aws lambda invoke --function-name MyFunction --payload file://../outside/payload.json -',
            'aws rekognition detect-text --image-bytes fileb://../outside/test.jpg',
            'aws s3api put-object --bucket bucket --key file.txt --body ../outside.toml',
        ],
    )
    def test_parse_raises_error_for_relative_paths_in_blob_args_outside_workdir(self, command):
        """Test that blob args with relative paths outside working directory are rejected."""
        with pytest.raises(
            FilePathValidationError,
            match='is outside the allowed working directory',
        ):
            parse(command)

    @pytest.mark.parametrize(
        'command',
        [
            # S3 custom file path arguments outside WORKING_DIRECTORY
            'aws s3 cp /tmp/file.txt s3://bucket/key',
            'aws s3 cp s3://bucket/key /tmp/file.txt',
            'aws s3 sync /tmp/folder s3://bucket/prefix',
            'aws s3 mv /tmp/file.txt s3://bucket/key',
            # CloudFormation custom file path arguments outside WORKING_DIRECTORY
            'aws cloudformation package --template-file /tmp/template.yaml --s3-bucket my-bucket',
            f'aws cloudformation package --template-file {WORKING_DIRECTORY}/template.yaml --s3-bucket my-bucket --output-template-file /tmp/packaged.yaml',
            'aws cloudformation deploy --template-file /tmp/template.json --stack-name my-stack',
            # CloudFront custom file path arguments outside WORKING_DIRECTORY
            'aws cloudfront sign --url https://example.com --private-key /tmp/private-key.pem --key-pair-id APKAEXAMPLE --date-less-than 2025-12-31',
            # ECS custom file path arguments outside WORKING_DIRECTORY
            'aws ecs deploy --cluster my-cluster --service my-service --task-definition /tmp/task-def.json --codedeploy-appspec /tmp/appspec.yaml',
            # EKS custom file path arguments outside WORKING_DIRECTORY
            'aws eks update-kubeconfig --name my-cluster --kubeconfig /tmp/kubeconfig',
            # GameLift custom file path arguments outside WORKING_DIRECTORY
            'aws gamelift upload-build --name my-build --build-version 1.0 --build-root /tmp/build --operating-system AMAZON_LINUX_2',
            'aws gamelift get-game-session-log --game-session-id gsess-123 --save-as /tmp/log.txt',
            # Deploy custom file path arguments outside WORKING_DIRECTORY
            'aws deploy push --application-name my-app --s3-location s3://my-bucket/app.zip --source /tmp/app',
            # EMR custom blob arguments outside WORKING_DIRECTORY
            'aws emr create-cluster --name my-cluster --release-label emr-5.30.0 --configurations file:///tmp/config.json --instance-type m5.xlarge --instance-count 3',
            'aws emr create-cluster --name my-cluster --release-label emr-5.30.0 --configurations InstanceCount=3,InstanceGroupType=MASTER --instance-fleets file:///tmp/fleets.json',
            'aws emr add-steps --cluster-id j-123456 --steps file:///tmp/steps.json',
        ],
    )
    def test_custom_file_path_arguments_outside_working_directory_rejected(self, command):
        """Test that custom file path arguments outside WORKING_DIRECTORY are rejected."""
        with pytest.raises(
            FileParameterError,
            match='is outside the allowed working directory',
        ):
            parse(command)


@patch(
    'awslabs.aws_api_mcp_server.core.parser.parser.FILE_ACCESS_MODE',
    FileAccessMode.NO_ACCESS,
)
@patch(
    'awslabs.aws_api_mcp_server.core.common.file_system_controls.FILE_ACCESS_MODE',
    FileAccessMode.NO_ACCESS,
)
class TestDisabledLocalFileAccess:
    """Tests for when local file access is disabled via FILE_ACCESS_MODE.NO_ACCESS."""

    @pytest.mark.parametrize(
        'command',
        [
            f'aws s3 cp {WORKING_DIRECTORY}/file.txt s3://bucket/key',
            f'aws s3 cp s3://bucket/key {WORKING_DIRECTORY}/file.txt',
            f'aws s3 sync {WORKING_DIRECTORY}/folder s3://bucket/prefix',
            f'aws s3 mv {WORKING_DIRECTORY}/file.txt s3://bucket/key',
            f'aws s3api get-object --bucket bucket --key file.txt {WORKING_DIRECTORY}/file.txt',
            f'aws lambda invoke --function-name MyFunction {WORKING_DIRECTORY}/result.json',
            f'aws emr add-steps --cluster-id j-ABCD1234EFGH --steps file://{WORKING_DIRECTORY}/steps.json',
        ],
    )
    def test_rejects_commands_with_local_paths(self, command):
        """Test that commands with local paths are rejected when FILE_ACCESS_MODE is NO_ACCESS."""
        with pytest.raises(
            FileParameterError,
            match='local file access is disabled',
        ):
            parse(command)

    @pytest.mark.parametrize(
        'command',
        [
            f'aws lambda invoke --function-name MyFunction --payload file://{WORKING_DIRECTORY}/payload.json -',
            f'aws lambda update-function-code --function-name MyFunction --zip-file fileb://{WORKING_DIRECTORY}/test.jpg',
            f'aws apigatewayv2 import-api --body file://{WORKING_DIRECTORY}/api.yaml',
            f'aws rekognition detect-text --image-bytes fileb://{WORKING_DIRECTORY}/test.jpg',
        ],
    )
    def test_rejects_file_blob_arguments(self, command):
        """Test that commands with file:// and fileb:// arguments are rejected when FILE_ACCESS_MODE is NO_ACCESS."""
        with pytest.raises(LocalFileAccessDisabledError):
            parse(command)

    @pytest.mark.parametrize(
        'command',
        [
            f'aws s3api put-object --bucket bucket --key file.txt --body {WORKING_DIRECTORY}/test-file.txt',
            f'aws s3api upload-part --bucket bucket --key file.txt --body {WORKING_DIRECTORY}/part.bin --part-number 1 --upload-id x',
            f'aws lambda invoke-async --function-name MyFunction --invoke-args {WORKING_DIRECTORY}/args.json',
        ],
    )
    def test_rejects_streaming_blob_arguments(self, command):
        """Test that commands with streaming blob arguments are rejected when FILE_ACCESS_MODE is NO_ACCESS.

        Streaming blob arguments accept only file paths.
        """
        with pytest.raises(LocalFileAccessDisabledError):
            parse(command)

    @pytest.mark.parametrize(
        'command,expected_service,expected_operation',
        [
            ('aws s3 cp s3://source-bucket/key s3://dest-bucket/key', 's3', 'cp'),
            ('aws s3 sync s3://source-bucket/prefix s3://dest-bucket/prefix', 's3', 'sync'),
            ('aws s3 mv s3://source-bucket/key s3://dest-bucket/key', 's3', 'mv'),
            ('aws s3api get-object --bucket bucket --key file.txt -', 's3', 'get-object'),
            (
                'aws lambda invoke --function-name MyFunction --payload \'{"key": "value"}\' -',
                'lambda',
                'invoke',
            ),
        ],
    )
    def test_allows_s3_uris_and_stdout_redirect(
        self, command, expected_service, expected_operation
    ):
        """Test that S3 URIs, stdout redirect, and inline values are allowed when FILE_ACCESS_MODE is NO_ACCESS."""
        result = parse(command)
        assert result.command_metadata.service_sdk_name == expected_service
        assert result.operation_cli_name == expected_operation

    @pytest.mark.parametrize(
        'command,expected_service,expected_operation',
        [
            # S3 operations that don't require local files
            ('aws s3 ls', 's3', 'ls'),
            ('aws s3 ls s3://bucket', 's3', 'ls'),
            ('aws s3 website s3://bucket --index-document index.html', 's3', 'website'),
            ('aws s3 rm s3://bucket/key', 's3', 'rm'),
            ('aws s3 mb s3://new-bucket', 's3', 'mb'),
            ('aws s3 rb s3://bucket', 's3', 'rb'),
            ('aws s3 presign s3://bucket/key', 's3', 'presign'),
            ('aws s3 cp s3://source/key s3://dest/key', 's3', 'cp'),
            ('aws s3 mv s3://source/key s3://dest/key', 's3', 'mv'),
            ('aws s3 sync s3://source s3://dest', 's3', 'sync'),
            # CloudTrail operations
            (
                'aws cloudtrail validate-logs --trail-arn arn:aws:cloudtrail:us-east-1:123456789012:trail/my-trail --start-time 2023-01-01T00:00:00Z',
                'cloudtrail',
                'validate-logs',
            ),
            # DataPipeline operations
            ('aws datapipeline list-runs --pipeline-id df-123456789', 'datapipeline', 'list-runs'),
            ('aws datapipeline create-default-roles', 'datapipeline', 'create-default-roles'),
            # DLM operations
            ('aws dlm create-default-role', 'dlm', 'create-default-role'),
            # ECR operations
            ('aws ecr get-login --region us-east-1 --no-include-email', 'ecr', 'get-login'),
            ('aws ecr get-login-password', 'ecr', 'get-login-password'),
            # ECR Public operations
            ('aws ecr-public get-login-password', 'ecr-public', 'get-login-password'),
            # EKS operations
            ('aws eks get-token --cluster-name my-cluster', 'eks', 'get-token'),
            # EMR operations
            (
                'aws emr add-instance-groups --cluster-id j-123456 --instance-groups InstanceGroupType=TASK,InstanceType=m5.xlarge,InstanceCount=2',
                'emr',
                'add-instance-groups',
            ),
            (
                'aws emr create-cluster --name my-cluster --release-label emr-5.30.0 --applications Name=Spark --ec2-attributes KeyName=my-key --instance-type m5.xlarge --instance-count 3 --use-default-roles',
                'emr',
                'create-cluster',
            ),
            ('aws emr describe-cluster --cluster-id j-123456', 'emr', 'describe-cluster'),
            (
                'aws emr modify-cluster-attributes --cluster-id j-123456 --visible-to-all-users',
                'emr',
                'modify-cluster-attributes',
            ),
            ('aws emr create-default-roles', 'emr', 'create-default-roles'),
            (
                'aws emr add-steps --cluster-id j-XXXXXXXX --steps Type=CUSTOM_JAR,Name=CustomJAR,ActionOnFailure=CONTINUE,Jar=s3://amzn-s3-demo-bucket/mytest.jar,Args=arg1,arg2,arg3',
                'emr',
                'add-steps',
            ),
            # EMR Containers operations
            (
                'aws emr-containers update-role-trust-policy --cluster-name my-cluster --namespace default --role-name my-role',
                'emr-containers',
                'update-role-trust-policy',
            ),
            # RDS operations
            (
                'aws rds generate-db-auth-token --hostname mydb.example.com --port 3306 --username admin',
                'rds',
                'generate-db-auth-token',
            ),
            # Deploy operations
            ('aws deploy deregister --instance-name my-instance', 'deploy', 'deregister'),
            # ConfigService operations
            ('aws configservice get-status', 'configservice', 'get-status'),
        ],
    )
    def test_allowed_custom_operations_work_with_disabled_file_access(
        self, command, expected_service, expected_operation
    ):
        """Test that allowed custom operations work when FILE_ACCESS_MODE is NO_ACCESS."""
        result = parse(command)
        assert result.command_metadata.service_sdk_name == expected_service
        assert result.operation_cli_name == expected_operation
        assert result.is_awscli_customization is True

    @pytest.mark.parametrize(
        'command,expected_service,expected_operation',
        [
            # CloudFormation operations that require local files
            (
                f'aws cloudformation package --template-file {WORKING_DIRECTORY}/template.yaml --s3-bucket my-bucket',
                'cloudformation',
                'package',
            ),
            (
                f'aws cloudformation deploy --template-file {WORKING_DIRECTORY}/template.yaml --stack-name my-stack',
                'cloudformation',
                'deploy',
            ),
            # CloudFront operations that require local files
            (
                f'aws cloudfront sign --url https://example.com --private-key {WORKING_DIRECTORY}/private-key.pem --key-pair-id APKAEXAMPLE',
                'cloudfront',
                'sign',
            ),
            # CodeArtifact operations that require local files
            (
                'aws codeartifact login --tool pip --domain my-domain --repository my-repo',
                'codeartifact',
                'login',
            ),
            # ECS operations that require local files
            (
                f'aws ecs deploy --cluster my-cluster --service my-service --task-definition {WORKING_DIRECTORY}/task-def.json',
                'ecs',
                'deploy',
            ),
            # EKS operations that require local files
            (
                'aws eks update-kubeconfig --name my-cluster',
                'eks',
                'update-kubeconfig',
            ),
            # GameLift operations that require local files
            (
                f'aws gamelift upload-build --name my-build --build-version 1.0 --build-root {WORKING_DIRECTORY}/build --operating-system AMAZON_LINUX_2',
                'gamelift',
                'upload-build',
            ),
            (
                f'aws gamelift get-game-session-log --game-session-id gsess-123 --save-as {WORKING_DIRECTORY}/log.txt',
                'gamelift',
                'get-game-session-log',
            ),
            # ServiceCatalog operations that require local files
            (
                f'aws servicecatalog generate --product-id prod-123 --provisioning-artifact-id pa-123 --output-file {WORKING_DIRECTORY}/output.json',
                'servicecatalog',
                'generate',
            ),
            # Deploy operations that require local files
            (
                f'aws deploy push --application-name my-app --s3-location s3://my-bucket/app.zip --source {WORKING_DIRECTORY}/app',
                'deploy',
                'push',
            ),
            (
                'aws deploy register --application-name my-app --s3-location s3://my-bucket/app.zip --description "My app"',
                'deploy',
                'register',
            ),
        ],
    )
    def test_file_based_custom_operations_rejected_with_disabled_file_access(
        self, command, expected_service, expected_operation
    ):
        """Test that file-based custom operations are rejected when FILE_ACCESS_MODE is NO_ACCESS."""
        with pytest.raises(OperationNotAllowedError) as exc_info:
            parse(command)

        error_message = str(exc_info.value)
        assert expected_service in error_message.lower()
        assert expected_operation in error_message.lower()


@patch(
    'awslabs.aws_api_mcp_server.core.common.file_system_controls.FILE_ACCESS_MODE',
    FileAccessMode.UNRESTRICTED,
)
class TestUnrestrictedLocalFileAccess:
    """Tests for when unrestricted local file access is enabled."""

    def test_allows_local_files_in_unrestricted_mode(self):
        """Test that FILE_ACCESS_MODE.UNRESTRICTED allows local files anywhere on the filesystem."""
        # With UNRESTRICTED mode, local files should be allowed
        command = 'aws s3 cp /tmp/file.txt s3://bucket/key'
        # Should not raise any exception about file access
        result = parse(command)
        assert result.command_metadata.service_sdk_name == 's3'
