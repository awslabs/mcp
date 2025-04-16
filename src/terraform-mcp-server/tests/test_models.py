# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Tests for the models module of the terraform-mcp-server."""

from awslabs.terraform_mcp_server.models import (
    CheckovScanRequest,
    CheckovScanResult,
    CheckovVulnerability,
    ModuleSearchResult,
    SubmoduleInfo,
    TerraformAWSCCProviderDocsResult,
    TerraformAWSProviderDocsResult,
    TerraformExecutionRequest,
    TerraformExecutionResult,
    TerraformOutput,
    TerraformVariable,
)


class TestTerraformExecutionRequest:
    """Tests for the TerraformExecutionRequest model."""

    def test_terraform_execution_request_creation(self):
        """Test creating a TerraformExecutionRequest."""
        request = TerraformExecutionRequest(
            command='init',
            working_directory='/tmp/terraform_test',
            variables={'environment': 'test'},
            aws_region='us-west-2',
            strip_ansi=True,
        )

        assert request.command == 'init'
        assert request.working_directory == '/tmp/terraform_test'
        assert request.variables == {'environment': 'test'}
        assert request.aws_region == 'us-west-2'
        assert request.strip_ansi is True

    def test_terraform_execution_request_defaults(self):
        """Test TerraformExecutionRequest with default values."""
        request = TerraformExecutionRequest(
            command='init', working_directory='/tmp/terraform_test'
        )

        assert request.command == 'init'
        assert request.working_directory == '/tmp/terraform_test'
        assert request.variables is None
        assert request.aws_region is None
        assert request.strip_ansi is True


class TestTerraformExecutionResult:
    """Tests for the TerraformExecutionResult model."""

    def test_terraform_execution_result_success(self):
        """Test creating a successful TerraformExecutionResult."""
        result = TerraformExecutionResult(
            status='success',
            return_code=0,
            stdout='Terraform initialized successfully!',
            stderr='',
            command='terraform init',
            working_directory='/tmp/terraform_test',
            outputs={'instance_id': 'i-1234567890abcdef0'},
        )

        assert result.status == 'success'
        assert result.return_code == 0
        assert result.stdout == 'Terraform initialized successfully!'
        assert result.stderr == ''
        assert result.command == 'terraform init'
        assert result.working_directory == '/tmp/terraform_test'
        assert result.outputs == {'instance_id': 'i-1234567890abcdef0'}
        assert result.error_message is None

    def test_terraform_execution_result_error(self):
        """Test creating an error TerraformExecutionResult."""
        result = TerraformExecutionResult(
            status='error',
            return_code=1,
            stdout='',
            stderr='Error: Could not load plugin',
            command='terraform init',
            working_directory='/tmp/terraform_test',
            error_message='Failed to initialize Terraform',
        )

        assert result.status == 'error'
        assert result.return_code == 1
        assert result.stdout == ''
        assert result.stderr == 'Error: Could not load plugin'
        assert result.command == 'terraform init'
        assert result.working_directory == '/tmp/terraform_test'
        assert result.outputs is None
        assert result.error_message == 'Failed to initialize Terraform'


class TestCheckovScanRequest:
    """Tests for the CheckovScanRequest model."""

    def test_checkov_scan_request_creation(self):
        """Test creating a CheckovScanRequest."""
        request = CheckovScanRequest(
            working_directory='/tmp/terraform_test',
            framework='terraform',
            check_ids=['CKV_AWS_1', 'CKV_AWS_2'],
            skip_check_ids=['CKV_AWS_3'],
            output_format='json',
        )

        assert request.working_directory == '/tmp/terraform_test'
        assert request.framework == 'terraform'
        assert request.check_ids == ['CKV_AWS_1', 'CKV_AWS_2']
        assert request.skip_check_ids == ['CKV_AWS_3']
        assert request.output_format == 'json'

    def test_checkov_scan_request_defaults(self):
        """Test CheckovScanRequest with default values."""
        request = CheckovScanRequest(working_directory='/tmp/terraform_test')

        assert request.working_directory == '/tmp/terraform_test'
        assert request.framework == 'terraform'
        assert request.check_ids is None
        assert request.skip_check_ids is None
        assert request.output_format == 'json'


class TestCheckovVulnerability:
    """Tests for the CheckovVulnerability model."""

    def test_checkov_vulnerability_creation(self):
        """Test creating a CheckovVulnerability."""
        vulnerability = CheckovVulnerability(
            id='CKV_AWS_1',
            type='terraform_aws',
            description='Ensure S3 bucket has encryption enabled',
            resource='aws_s3_bucket.my_bucket',
            file_path='/tmp/terraform_test/main.tf',
            line=5,
            guideline='https://docs.bridgecrew.io/docs/s3-encryption',
            severity='HIGH',
        )

        assert vulnerability.id == 'CKV_AWS_1'
        assert vulnerability.type == 'terraform_aws'
        assert vulnerability.description == 'Ensure S3 bucket has encryption enabled'
        assert vulnerability.resource == 'aws_s3_bucket.my_bucket'
        assert vulnerability.file_path == '/tmp/terraform_test/main.tf'
        assert vulnerability.line == 5
        assert vulnerability.guideline == 'https://docs.bridgecrew.io/docs/s3-encryption'
        assert vulnerability.severity == 'HIGH'
        assert vulnerability.fixed is False


class TestCheckovScanResult:
    """Tests for the CheckovScanResult model."""

    def test_checkov_scan_result_success(self):
        """Test creating a successful CheckovScanResult."""
        vulnerability = CheckovVulnerability(
            id='CKV_AWS_1',
            type='terraform_aws',
            description='Ensure S3 bucket has encryption enabled',
            resource='aws_s3_bucket.my_bucket',
            file_path='/tmp/terraform_test/main.tf',
            line=5,
            guideline='https://docs.bridgecrew.io/docs/s3-encryption',
        )

        result = CheckovScanResult(
            status='success',
            return_code=1,  # Checkov returns 1 when vulnerabilities are found
            working_directory='/tmp/terraform_test',
            vulnerabilities=[vulnerability],
            summary={
                'passed': 0,
                'failed': 1,
                'skipped': 0,
                'parsing_errors': 0,
                'resource_count': 1,
            },
            raw_output='Check: CKV_AWS_1: "Ensure S3 bucket has encryption enabled"\nFAILED for resource: aws_s3_bucket.my_bucket',
        )

        assert result.status == 'success'
        assert result.return_code == 1
        assert len(result.vulnerabilities) == 1
        assert result.vulnerabilities[0].id == 'CKV_AWS_1'
        assert result.summary['passed'] == 0
        assert result.summary['failed'] == 1
        assert 'Ensure S3 bucket has encryption enabled' in result.raw_output
        assert result.error_message is None

    def test_checkov_scan_result_error(self):
        """Test creating an error CheckovScanResult."""
        result = CheckovScanResult(
            status='error',
            return_code=2,
            working_directory='/tmp/terraform_test',
            error_message='Failed to run Checkov',
            raw_output='Error: Failed to run Checkov',
        )

        assert result.status == 'error'
        assert result.return_code == 2
        assert result.vulnerabilities == []
        assert result.summary == {}
        assert result.raw_output == 'Error: Failed to run Checkov'
        assert result.error_message == 'Failed to run Checkov'


class TestTerraformAWSProviderDocsResult:
    """Tests for the TerraformAWSProviderDocsResult model."""

    def test_terraform_aws_provider_docs_result_creation(self):
        """Test creating a TerraformAWSProviderDocsResult."""
        asset = TerraformAWSProviderDocsResult(
            asset_name='aws_s3_bucket',
            asset_type='resource',
            description='Provides an S3 bucket resource.',
            url='https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket',
            example_usage=[
                {
                    'title': 'Basic Usage',
                    'code': 'resource "aws_s3_bucket" "example" {\n  bucket = "my-bucket"\n}',
                }
            ],
            arguments=[
                {'name': 'bucket', 'description': 'The name of the bucket.', 'required': 'false'}
            ],
            attributes=[{'name': 'id', 'description': 'The name of the bucket.'}],
        )

        assert asset.asset_name == 'aws_s3_bucket'
        assert asset.asset_type == 'resource'
        assert asset.description == 'Provides an S3 bucket resource.'
        assert (
            asset.url
            == 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket'
        )
        assert len(asset.example_usage) == 1
        assert 'bucket = "my-bucket"' in asset.example_usage[0]['code']
        assert len(asset.arguments) == 1
        assert asset.arguments[0]['name'] == 'bucket'
        assert asset.arguments[0]['description'] == 'The name of the bucket.'
        assert asset.arguments[0]['required'] == 'false'
        assert len(asset.attributes) == 1
        assert asset.attributes[0]['name'] == 'id'
        assert asset.attributes[0]['description'] == 'The name of the bucket.'


class TestTerraformAWSCCProviderDocsResult:
    """Tests for the TerraformAWSCCProviderDocsResult model."""

    def test_terraform_awscc_provider_docs_result_creation(self):
        """Test creating a TerraformAWSCCProviderDocsResult."""
        asset = TerraformAWSCCProviderDocsResult(
            asset_name='awscc_s3_bucket',
            asset_type='resource',
            description='Provides an S3 bucket resource using Cloud Control API.',
            url='https://registry.terraform.io/providers/hashicorp/awscc/latest/docs/resources/s3_bucket',
            example_usage=[
                {
                    'title': 'Basic Usage',
                    'code': 'resource "awscc_s3_bucket" "example" {\n  bucket_name = "my-bucket"\n}',
                }
            ],
            schema_arguments=[
                {'name': 'bucket_name', 'description': 'The name of the bucket.', 'required': True}
            ],
        )

        assert asset.asset_name == 'awscc_s3_bucket'
        assert asset.asset_type == 'resource'
        assert asset.description == 'Provides an S3 bucket resource using Cloud Control API.'
        assert (
            asset.url
            == 'https://registry.terraform.io/providers/hashicorp/awscc/latest/docs/resources/s3_bucket'
        )
        assert len(asset.example_usage) == 1
        assert 'bucket_name = "my-bucket"' in asset.example_usage[0]['code']
        assert len(asset.schema_arguments) == 1
        assert asset.schema_arguments[0]['name'] == 'bucket_name'
        assert asset.schema_arguments[0]['description'] == 'The name of the bucket.'
        assert asset.schema_arguments[0]['required'] is True


class TestModuleSearchResult:
    """Tests for the ModuleSearchResult model."""

    def test_module_search_result_creation(self):
        """Test creating a ModuleSearchResult."""
        submodule = SubmoduleInfo(
            name='agent', path='modules/agent', description='Bedrock agent submodule'
        )

        variable = TerraformVariable(
            name='name',
            type='string',
            description='Name to use for resources',
            default='bedrock-module',
        )

        output = TerraformOutput(
            name='bedrock_endpoint_url', description='URL of the Bedrock endpoint'
        )

        module = ModuleSearchResult(
            name='bedrock',
            namespace='aws-ia',
            provider='aws',
            version='1.0.0',
            description='Amazon Bedrock module for generative AI applications',
            url='https://registry.terraform.io/modules/aws-ia/bedrock/aws/latest',
            readme_content='# AWS Bedrock Terraform Module\n\nThis module helps you deploy Amazon Bedrock resources.',
            input_count=2,
            output_count=2,
            submodules=[submodule],
            variables=[variable],
            outputs=[output],
        )

        assert module.name == 'bedrock'
        assert module.namespace == 'aws-ia'
        assert module.provider == 'aws'
        assert module.version == '1.0.0'
        assert module.description == 'Amazon Bedrock module for generative AI applications'
        assert module.url == 'https://registry.terraform.io/modules/aws-ia/bedrock/aws/latest'
        assert 'AWS Bedrock Terraform Module' in module.readme_content
        assert module.input_count == 2
        assert module.output_count == 2
        assert module.has_submodules is True
        assert len(module.submodules) == 1
        assert module.submodules[0].name == 'agent'
        assert module.submodules[0].path == 'modules/agent'
        assert module.submodules[0].description == 'Bedrock agent submodule'
        assert len(module.variables) == 1
        assert module.variables[0].name == 'name'
        assert module.variables[0].type == 'string'
        assert module.variables[0].description == 'Name to use for resources'
        assert module.variables[0].default == 'bedrock-module'
        assert len(module.outputs) == 1
        assert module.outputs[0].name == 'bedrock_endpoint_url'
        assert module.outputs[0].description == 'URL of the Bedrock endpoint'


class TestSubmoduleInfo:
    """Tests for the SubmoduleInfo model."""

    def test_submodule_info_creation(self):
        """Test creating a SubmoduleInfo."""
        submodule = SubmoduleInfo(
            name='agent',
            path='modules/agent',
            description='Bedrock agent submodule',
            readme_content='# Agent Submodule\n\nThis submodule deploys a Bedrock agent.',
        )

        assert submodule.name == 'agent'
        assert submodule.path == 'modules/agent'
        assert submodule.description == 'Bedrock agent submodule'
        assert (
            submodule.readme_content
            == '# Agent Submodule\n\nThis submodule deploys a Bedrock agent.'
        )


class TestTerraformVariable:
    """Tests for the TerraformVariable model."""

    def test_terraform_variable_creation(self):
        """Test creating a TerraformVariable."""
        variable = TerraformVariable(
            name='name',
            type='string',
            description='Name to use for resources',
            default='bedrock-module',
            required=False,
        )

        assert variable.name == 'name'
        assert variable.type == 'string'
        assert variable.description == 'Name to use for resources'
        assert variable.default == 'bedrock-module'
        assert variable.required is False


class TestTerraformOutput:
    """Tests for the TerraformOutput model."""

    def test_terraform_output_creation(self):
        """Test creating a TerraformOutput."""
        output = TerraformOutput(
            name='bedrock_endpoint_url', description='URL of the Bedrock endpoint'
        )

        assert output.name == 'bedrock_endpoint_url'
        assert output.description == 'URL of the Bedrock endpoint'
