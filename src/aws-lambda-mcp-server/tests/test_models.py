# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the models module."""

import pytest
from pydantic import ValidationError
from awslabs.aws_lambda_mcp_server.models import (
    SamBuildRequest, SamInitRequest, SamDeployRequest, 
    GetIaCGuidanceRequest, GetLambdaEventSchemasRequest, GetLambdaGuidanceRequest,
    CreateFunctionRequest, UpdateFunctionRequest, Runtime
)


class TestSamBuildRequest:
    """Tests for the SamBuildRequest model."""

    def test_sam_build_request_required_fields(self):
        """Test SamBuildRequest with required fields."""
        request = SamBuildRequest(project_directory="/tmp/test-project")
        assert request.project_directory == "/tmp/test-project"
        assert request.resource_id is None
        assert request.template_file is None
        assert request.cached is False
        assert request.use_container is False

    def test_sam_build_request_all_fields(self):
        """Test SamBuildRequest with all fields."""
        request = SamBuildRequest(
            project_directory="/tmp/test-project",
            resource_id="MyFunction",
            template_file="template.yaml",
            base_dir="/tmp",
            build_dir="/tmp/build",
            cache_dir="/tmp/cache",
            cached=True,
            use_container=True,
            no_use_container=False,
            container_env_vars={"NODE_ENV": "production"},
            container_env_var_file="env.json",
            skip_pull_image=True,
            build_method="esbuild",
            build_in_source=True,
            no_build_in_source=False,
            beta_features=True,
            no_beta_features=False,
            build_image="amazon/aws-sam-cli-build-image-nodejs18.x",
            debug=True
        )
        assert request.project_directory == "/tmp/test-project"
        assert request.resource_id == "MyFunction"
        assert request.template_file == "template.yaml"
        assert request.base_dir == "/tmp"
        assert request.build_dir == "/tmp/build"
        assert request.cache_dir == "/tmp/cache"
        assert request.cached is True
        assert request.use_container is True
        assert request.no_use_container is False
        assert request.container_env_vars == {"NODE_ENV": "production"}
        assert request.container_env_var_file == "env.json"
        assert request.skip_pull_image is True
        assert request.build_method == "esbuild"
        assert request.build_in_source is True
        assert request.no_build_in_source is False
        assert request.beta_features is True
        assert request.no_beta_features is False
        assert request.build_image == "amazon/aws-sam-cli-build-image-nodejs18.x"
        assert request.debug is True

    def test_sam_build_request_missing_required_fields(self):
        """Test SamBuildRequest with missing required fields."""
        with pytest.raises(ValidationError):
            SamBuildRequest()


class TestSamInitRequest:
    """Tests for the SamInitRequest model."""

    def test_sam_init_request_required_fields(self):
        """Test SamInitRequest with required fields."""
        request = SamInitRequest(
            project_name="test-project",
            runtime="nodejs18.x",
            project_directory="/tmp/test-project",
            dependency_manager="npm"
        )
        assert request.project_name == "test-project"
        assert request.runtime == "nodejs18.x"
        assert request.project_directory == "/tmp/test-project"
        assert request.dependency_manager == "npm"
        assert request.architecture == "x86_64"
        assert request.package_type == "Zip"
        assert request.application_template == "hello-world"

    def test_sam_init_request_all_fields(self):
        """Test SamInitRequest with all fields."""
        request = SamInitRequest(
            project_name="test-project",
            runtime="nodejs18.x",
            project_directory="/tmp/test-project",
            dependency_manager="npm",
            architecture="arm64",
            package_type="Image",
            application_template="quick-start",
            application_insights=True,
            no_application_insights=False,
            base_image="amazon/nodejs18.x-base",
            config_env="dev",
            config_file="samconfig.toml",
            debug=True,
            extra_content='{"key": "value"}',
            location="https://github.com/aws/aws-sam-cli-app-templates",
            save_params=True,
            tracing=True,
            no_tracing=False
        )
        assert request.project_name == "test-project"
        assert request.runtime == "nodejs18.x"
        assert request.project_directory == "/tmp/test-project"
        assert request.dependency_manager == "npm"
        assert request.architecture == "arm64"
        assert request.package_type == "Image"
        assert request.application_template == "quick-start"
        assert request.application_insights is True
        assert request.no_application_insights is False
        assert request.base_image == "amazon/nodejs18.x-base"
        assert request.config_env == "dev"
        assert request.config_file == "samconfig.toml"
        assert request.debug is True
        assert request.extra_content == '{"key": "value"}'
        assert request.location == "https://github.com/aws/aws-sam-cli-app-templates"
        assert request.save_params is True
        assert request.tracing is True
        assert request.no_tracing is False

    def test_sam_init_request_missing_required_fields(self):
        """Test SamInitRequest with missing required fields."""
        with pytest.raises(ValidationError):
            SamInitRequest(
                project_name="test-project",
                runtime="nodejs18.x"
            )


class TestSamDeployRequest:
    """Tests for the SamDeployRequest model."""

    def test_sam_deploy_request_required_fields(self):
        """Test SamDeployRequest with required fields."""
        request = SamDeployRequest(
            application_name="test-app",
            project_directory="/tmp/test-project"
        )
        assert request.application_name == "test-app"
        assert request.project_directory == "/tmp/test-project"
        assert request.template_file is None
        assert request.s3_bucket is None
        assert request.capabilities == ["CAPABILITY_IAM"]
        assert request.no_confirm_changeset is True

    def test_sam_deploy_request_all_fields(self):
        """Test SamDeployRequest with all fields."""
        request = SamDeployRequest(
            application_name="test-app",
            project_directory="/tmp/test-project",
            template_file="template.yaml",
            s3_bucket="my-bucket",
            s3_prefix="my-prefix",
            region="us-west-2",
            profile="default",
            parameter_overrides="ParameterKey=Key,ParameterValue=Value",
            capabilities=["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
            no_confirm_changeset=False,
            config_file="samconfig.toml",
            config_env="dev",
            guided_deploy=True,
            no_execute_changeset=True,
            fail_on_empty_changeset=True,
            force_upload=True,
            use_json=True,
            metadata={"key": "value"},
            notification_arns=["arn:aws:sns:us-west-2:123456789012:my-topic"],
            tags={"key": "value"},
            resolve_s3=True,
            disable_rollback=True,
            debug=True
        )
        assert request.application_name == "test-app"
        assert request.project_directory == "/tmp/test-project"
        assert request.template_file == "template.yaml"
        assert request.s3_bucket == "my-bucket"
        assert request.s3_prefix == "my-prefix"
        assert request.region == "us-west-2"
        assert request.profile == "default"
        assert request.parameter_overrides == "ParameterKey=Key,ParameterValue=Value"
        assert request.capabilities == ["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"]
        assert request.no_confirm_changeset is False
        assert request.config_file == "samconfig.toml"
        assert request.config_env == "dev"
        assert request.guided_deploy is True
        assert request.no_execute_changeset is True
        assert request.fail_on_empty_changeset is True
        assert request.force_upload is True
        assert request.use_json is True
        assert request.metadata == {"key": "value"}
        assert request.notification_arns == ["arn:aws:sns:us-west-2:123456789012:my-topic"]
        assert request.tags == {"key": "value"}
        assert request.resolve_s3 is True
        assert request.disable_rollback is True
        assert request.debug is True


class TestGetIaCGuidanceRequest:
    """Tests for the GetIaCGuidanceRequest model."""

    def test_get_iac_guidance_request_required_fields(self):
        """Test GetIaCGuidanceRequest with required fields."""
        request = GetIaCGuidanceRequest(
            resource_type="Lambda",
            use_case="Serverless API"
        )
        assert request.resource_type == "Lambda"
        assert request.use_case == "Serverless API"
        assert request.iac_tool == "CloudFormation"
        assert request.include_examples is True
        assert request.advanced_options is False

    def test_get_iac_guidance_request_all_fields(self):
        """Test GetIaCGuidanceRequest with all fields."""
        request = GetIaCGuidanceRequest(
            resource_type="Lambda",
            use_case="Serverless API",
            iac_tool="SAM",
            include_examples=False,
            advanced_options=True
        )
        assert request.resource_type == "Lambda"
        assert request.use_case == "Serverless API"
        assert request.iac_tool == "SAM"
        assert request.include_examples is False
        assert request.advanced_options is True

    def test_get_iac_guidance_request_invalid_iac_tool(self):
        """Test GetIaCGuidanceRequest with invalid iac_tool."""
        with pytest.raises(ValidationError):
            GetIaCGuidanceRequest(
                resource_type="Lambda",
                use_case="Serverless API",
                iac_tool="Invalid"
            )


class TestGetLambdaEventSchemasRequest:
    """Tests for the GetLambdaEventSchemasRequest model."""

    def test_get_lambda_event_schemas_request_required_fields(self):
        """Test GetLambdaEventSchemasRequest with required fields."""
        request = GetLambdaEventSchemasRequest(
            event_source="S3",
            runtime="nodejs"
        )
        assert request.event_source == "S3"
        assert request.runtime == "nodejs"

    def test_get_lambda_event_schemas_request_missing_required_fields(self):
        """Test GetLambdaEventSchemasRequest with missing required fields."""
        with pytest.raises(ValidationError):
            GetLambdaEventSchemasRequest(event_source="S3")


class TestGetLambdaGuidanceRequest:
    """Tests for the GetLambdaGuidanceRequest model."""

    def test_get_lambda_guidance_request_required_fields(self):
        """Test GetLambdaGuidanceRequest with required fields."""
        request = GetLambdaGuidanceRequest(
            runtime="nodejs18.x",
            use_case="Serverless API"
        )
        assert request.runtime == "nodejs18.x"
        assert request.use_case == "Serverless API"
        assert request.event_source is None
        assert request.include_examples is True
        assert request.advanced_options is False

    def test_get_lambda_guidance_request_all_fields(self):
        """Test GetLambdaGuidanceRequest with all fields."""
        request = GetLambdaGuidanceRequest(
            runtime="nodejs18.x",
            use_case="Serverless API",
            event_source="API Gateway",
            include_examples=False,
            advanced_options=True
        )
        assert request.runtime == "nodejs18.x"
        assert request.use_case == "Serverless API"
        assert request.event_source == "API Gateway"
        assert request.include_examples is False
        assert request.advanced_options is True


class TestCreateFunctionRequest:
    """Tests for the CreateFunctionRequest model."""

    def test_create_function_request_required_fields(self):
        """Test CreateFunctionRequest with required fields."""
        request = CreateFunctionRequest(
            function_name="test-function",
            runtime=Runtime.NODEJS18_X,
            role="arn:aws:iam::123456789012:role/lambda-role",
            handler="index.handler",
            code_path="/tmp/function.zip"
        )
        assert request.function_name == "test-function"
        assert request.runtime == Runtime.NODEJS18_X
        assert request.role == "arn:aws:iam::123456789012:role/lambda-role"
        assert request.handler == "index.handler"
        assert request.code_path == "/tmp/function.zip"
        assert request.s3_bucket is None
        assert request.s3_key is None
        assert request.s3_object_version is None
        assert request.image_uri is None
        assert request.source_kms_key_arn is None
        assert request.timeout == 3
        assert request.memory_size == 128
        assert request.architectures == ["x86_64"]

    def test_create_function_request_all_fields(self):
        """Test CreateFunctionRequest with all fields."""
        request = CreateFunctionRequest(
            function_name="test-function",
            runtime=Runtime.NODEJS18_X,
            role="arn:aws:iam::123456789012:role/lambda-role",
            handler="index.handler",
            code_path="/tmp/function.zip",
            description="Test function",
            timeout=30,
            memory_size=512,
            environment_variables={"NODE_ENV": "production"},
            tags={"key": "value"},
            vpc_config={"SubnetIds": ["subnet-123"], "SecurityGroupIds": ["sg-123"]},
            dead_letter_config={"TargetArn": "arn:aws:sns:us-west-2:123456789012:my-topic"},
            tracing_config={"Mode": "Active"},
            layers=["arn:aws:lambda:us-west-2:123456789012:layer:my-layer:1"],
            architectures=["arm64"]
        )
        assert request.function_name == "test-function"
        assert request.runtime == Runtime.NODEJS18_X
        assert request.role == "arn:aws:iam::123456789012:role/lambda-role"
        assert request.handler == "index.handler"
        assert request.code_path == "/tmp/function.zip"
        assert request.s3_bucket is None
        assert request.s3_key is None
        assert request.s3_object_version is None
        assert request.image_uri is None
        assert request.source_kms_key_arn is None
        assert request.description == "Test function"
        assert request.timeout == 30
        assert request.memory_size == 512
        assert request.environment_variables == {"NODE_ENV": "production"}
        assert request.tags == {"key": "value"}
        assert request.vpc_config == {"SubnetIds": ["subnet-123"], "SecurityGroupIds": ["sg-123"]}
        assert request.dead_letter_config == {"TargetArn": "arn:aws:sns:us-west-2:123456789012:my-topic"}
        assert request.tracing_config == {"Mode": "Active"}
        assert request.layers == ["arn:aws:lambda:us-west-2:123456789012:layer:my-layer:1"]
        assert request.architectures == ["arm64"]

    def test_create_function_request_with_s3(self):
        """Test CreateFunctionRequest with S3 parameters."""
        request = CreateFunctionRequest(
            function_name="test-function",
            runtime=Runtime.NODEJS18_X,
            role="arn:aws:iam::123456789012:role/lambda-role",
            handler="index.handler",
            s3_bucket="my-bucket",
            s3_key="my-key",
            s3_object_version="1",
            source_kms_key_arn="arn:aws:kms:us-west-2:123456789012:key/my-key"
        )
        assert request.function_name == "test-function"
        assert request.runtime == Runtime.NODEJS18_X
        assert request.role == "arn:aws:iam::123456789012:role/lambda-role"
        assert request.handler == "index.handler"
        assert request.code_path is None
        assert request.s3_bucket == "my-bucket"
        assert request.s3_key == "my-key"
        assert request.s3_object_version == "1"
        assert request.image_uri is None
        assert request.source_kms_key_arn == "arn:aws:kms:us-west-2:123456789012:key/my-key"

    def test_create_function_request_with_image(self):
        """Test CreateFunctionRequest with image URI."""
        request = CreateFunctionRequest(
            function_name="test-function",
            runtime=Runtime.NODEJS18_X,
            role="arn:aws:iam::123456789012:role/lambda-role",
            handler="index.handler",
            image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/my-image:latest"
        )
        assert request.function_name == "test-function"
        assert request.runtime == Runtime.NODEJS18_X
        assert request.role == "arn:aws:iam::123456789012:role/lambda-role"
        assert request.handler == "index.handler"
        assert request.code_path is None
        assert request.s3_bucket is None
        assert request.s3_key is None
        assert request.s3_object_version is None
        assert request.image_uri == "123456789012.dkr.ecr.us-west-2.amazonaws.com/my-image:latest"
        assert request.source_kms_key_arn is None

    def test_create_function_request_missing_required_fields(self):
        """Test CreateFunctionRequest with missing required fields."""
        with pytest.raises(ValidationError):
            CreateFunctionRequest(
                function_name="test-function",
                runtime=Runtime.NODEJS18_X,
                role="arn:aws:iam::123456789012:role/lambda-role"
            )


class TestUpdateFunctionRequest:
    """Tests for the UpdateFunctionRequest model."""

    def test_update_function_request_required_fields(self):
        """Test UpdateFunctionRequest with required fields."""
        request = UpdateFunctionRequest(
            function_name="test-function"
        )
        assert request.function_name == "test-function"
        assert request.role is None
        assert request.handler is None
        assert request.code_path is None
        assert request.s3_bucket is None
        assert request.s3_key is None
        assert request.s3_object_version is None
        assert request.image_uri is None
        assert request.source_kms_key_arn is None

    def test_update_function_request_all_fields(self):
        """Test UpdateFunctionRequest with all fields."""
        request = UpdateFunctionRequest(
            function_name="test-function",
            role="arn:aws:iam::123456789012:role/lambda-role",
            handler="index.handler",
            code_path="/tmp/function.zip",
            description="Updated function",
            timeout=30,
            memory_size=512,
            environment_variables={"NODE_ENV": "production"},
            vpc_config={"SubnetIds": ["subnet-123"], "SecurityGroupIds": ["sg-123"]},
            dead_letter_config={"TargetArn": "arn:aws:sns:us-west-2:123456789012:my-topic"},
            tracing_config={"Mode": "Active"},
            layers=["arn:aws:lambda:us-west-2:123456789012:layer:my-layer:1"],
            architectures=["arm64"]
        )
        assert request.function_name == "test-function"
        assert request.role == "arn:aws:iam::123456789012:role/lambda-role"
        assert request.handler == "index.handler"
        assert request.code_path == "/tmp/function.zip"
        assert request.s3_bucket is None
        assert request.s3_key is None
        assert request.s3_object_version is None
        assert request.image_uri is None
        assert request.source_kms_key_arn is None
        assert request.description == "Updated function"
        assert request.timeout == 30
        assert request.memory_size == 512
        assert request.environment_variables == {"NODE_ENV": "production"}
        assert request.vpc_config == {"SubnetIds": ["subnet-123"], "SecurityGroupIds": ["sg-123"]}
        assert request.dead_letter_config == {"TargetArn": "arn:aws:sns:us-west-2:123456789012:my-topic"}
        assert request.tracing_config == {"Mode": "Active"}
        assert request.layers == ["arn:aws:lambda:us-west-2:123456789012:layer:my-layer:1"]
        assert request.architectures == ["arm64"]

    def test_update_function_request_with_s3(self):
        """Test UpdateFunctionRequest with S3 parameters."""
        request = UpdateFunctionRequest(
            function_name="test-function",
            s3_bucket="my-bucket",
            s3_key="my-key",
            s3_object_version="1",
            source_kms_key_arn="arn:aws:kms:us-west-2:123456789012:key/my-key"
        )
        assert request.function_name == "test-function"
        assert request.code_path is None
        assert request.s3_bucket == "my-bucket"
        assert request.s3_key == "my-key"
        assert request.s3_object_version == "1"
        assert request.image_uri is None
        assert request.source_kms_key_arn == "arn:aws:kms:us-west-2:123456789012:key/my-key"

    def test_update_function_request_with_image(self):
        """Test UpdateFunctionRequest with image URI."""
        request = UpdateFunctionRequest(
            function_name="test-function",
            image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/my-image:latest"
        )
        assert request.function_name == "test-function"
        assert request.code_path is None
        assert request.s3_bucket is None
        assert request.s3_key is None
        assert request.s3_object_version is None
        assert request.image_uri == "123456789012.dkr.ecr.us-west-2.amazonaws.com/my-image:latest"
        assert request.source_kms_key_arn is None


class TestRuntime:
    """Tests for the Runtime enum."""

    def test_runtime_values(self):
        """Test Runtime enum values."""
        assert Runtime.NODEJS18_X.value == "nodejs18.x"
        assert Runtime.NODEJS20_X.value == "nodejs20.x"
        assert Runtime.NODEJS22_X.value == "nodejs22.x"
        assert Runtime.PYTHON39.value == "python3.9"
        assert Runtime.PYTHON310.value == "python3.10"
        assert Runtime.PYTHON311.value == "python3.11"
        assert Runtime.PYTHON312.value == "python3.12"
        assert Runtime.PYTHON313.value == "python3.13"
        assert Runtime.JAVA17.value == "java17"
        assert Runtime.JAVA21.value == "java21"
        assert Runtime.DOTNET8.value == "dotnet8"
        assert Runtime.RUBY32.value == "ruby3.2"
        assert Runtime.GO1_X.value == "go1.x"
