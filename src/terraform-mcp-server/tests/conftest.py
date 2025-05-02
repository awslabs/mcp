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

"""Test fixtures for the terraform-mcp-server tests."""

import json
import os
import pytest
import tempfile
from unittest.mock import MagicMock, patch


@pytest.fixture
def temp_terraform_dir():
    """Create a secure temporary directory for Terraform tests."""
    # Create a secure temporary directory
    temp_dir = tempfile.mkdtemp(prefix='terraform_test_')
    yield temp_dir
    # Clean up the directory after tests
    if os.path.exists(temp_dir):
        import shutil

        shutil.rmtree(temp_dir)


@pytest.fixture
def mock_terraform_command_output():
    """Create mock output for Terraform commands."""
    return {
        'init': {
            'success': {
                'returncode': 0,
                'stdout': 'Terraform has been successfully initialized!',
                'stderr': '',
            },
            'error': {'returncode': 1, 'stdout': '', 'stderr': 'Error: Could not load plugin'},
        },
        'plan': {
            'success': {
                'returncode': 0,
                'stdout': 'Plan: 3 to add, 1 to change, 2 to destroy.',
                'stderr': '',
            },
            'error': {
                'returncode': 1,
                'stdout': '',
                'stderr': 'Error: No configuration files found!',
            },
        },
        'apply': {
            'success': {
                'returncode': 0,
                'stdout': 'Apply complete! Resources: 3 added, 1 changed, 2 destroyed.',
                'stderr': '',
            },
            'error': {'returncode': 1, 'stdout': '', 'stderr': 'Error: Could not load backend'},
        },
        'destroy': {
            'success': {
                'returncode': 0,
                'stdout': 'Destroy complete! Resources: 6 destroyed.',
                'stderr': '',
            },
            'error': {'returncode': 1, 'stdout': '', 'stderr': 'Error: Could not read state file'},
        },
        'validate': {
            'success': {
                'returncode': 0,
                'stdout': 'Success! The configuration is valid.',
                'stderr': '',
            },
            'error': {'returncode': 1, 'stdout': '', 'stderr': 'Error: Invalid resource name'},
        },
        'output': {
            'success': {
                'returncode': 0,
                'stdout': json.dumps(
                    {
                        'instance_id': {'value': 'i-1234567890abcdef0', 'type': 'string'},
                        'vpc_id': {'value': 'vpc-1234567890abcdef0', 'type': 'string'},
                    }
                ),
                'stderr': '',
            },
            'error': {'returncode': 1, 'stdout': '', 'stderr': 'Error: No outputs found'},
        },
    }


@pytest.fixture
def mock_checkov_output(temp_terraform_dir):
    """Create mock output for Checkov scans."""
    main_tf_path = os.path.join(temp_terraform_dir, 'main.tf')
    json_output = {
        'results': {
            'failed_checks': [
                {
                    'check_id': 'CKV_AWS_1',
                    'check_name': 'Ensure S3 bucket has encryption enabled',
                    'check_result': {
                        'result': 'FAILED',
                        'evaluated_keys': ['server_side_encryption_configuration'],
                    },
                    'file_path': main_tf_path,
                    'file_line_range': [1, 10],
                    'resource': 'aws_s3_bucket.my_bucket',
                    'check_class': 'checkov.terraform.checks.resource.aws.S3Encryption',
                    'guideline': 'https://docs.bridgecrew.io/docs/s3-encryption',
                },
                {
                    'check_id': 'CKV_AWS_18',
                    'check_name': 'Ensure the S3 bucket has access logging enabled',
                    'check_result': {'result': 'FAILED', 'evaluated_keys': ['logging']},
                    'file_path': main_tf_path,
                    'file_line_range': [1, 10],
                    'resource': 'aws_s3_bucket.my_bucket',
                    'check_class': 'checkov.terraform.checks.resource.aws.S3AccessLogs',
                    'guideline': 'https://docs.bridgecrew.io/docs/s3-16-enable-logging',
                },
            ],
            'passed_checks': [
                {
                    'check_id': 'CKV_AWS_21',
                    'check_name': 'Ensure S3 bucket has versioning enabled',
                    'check_result': {'result': 'PASSED', 'evaluated_keys': ['versioning']},
                    'file_path': main_tf_path,
                    'file_line_range': [1, 10],
                    'resource': 'aws_s3_bucket.my_bucket',
                    'check_class': 'checkov.terraform.checks.resource.aws.S3Versioning',
                    'guideline': 'https://docs.bridgecrew.io/docs/s3-14-enable-versioning',
                }
            ],
            'skipped_checks': [],
        },
        'summary': {
            'passed': 1,
            'failed': 2,
            'skipped': 0,
            'parsing_errors': 0,
            'resource_count': 1,
        },
    }

    cli_output = f"""
    Check: CKV_AWS_1: "Ensure S3 bucket has encryption enabled"
    FAILED for resource: aws_s3_bucket.my_bucket
    File: {main_tf_path}:1-10

    Check: CKV_AWS_18: "Ensure the S3 bucket has access logging enabled"
    FAILED for resource: aws_s3_bucket.my_bucket
    File: {main_tf_path}:1-10

    Check: CKV_AWS_21: "Ensure S3 bucket has versioning enabled"
    PASSED for resource: aws_s3_bucket.my_bucket
    File: {main_tf_path}:1-10

    Passed checks: 1, Failed checks: 2, Skipped checks: 0
    """

    return {
        'json': {
            'success': {
                'returncode': 1,  # Checkov returns 1 when vulnerabilities are found
                'stdout': json.dumps(json_output),
                'stderr': '',
            },
            'error': {
                'returncode': 2,  # Checkov returns 2 for errors
                'stdout': '',
                'stderr': 'Error: Failed to run Checkov',
            },
        },
        'cli': {
            'success': {
                'returncode': 1,  # Checkov returns 1 when vulnerabilities are found
                'stdout': cli_output,
                'stderr': '',
            },
            'error': {
                'returncode': 2,  # Checkov returns 2 for errors
                'stdout': '',
                'stderr': 'Error: Failed to run Checkov',
            },
        },
    }


@pytest.fixture
def mock_subprocess():
    """Create a mock subprocess module."""
    with (
        patch('subprocess.run') as mock_run,
        patch('subprocess.check_output') as mock_check_output,
    ):
        # Default return values
        mock_run.return_value = MagicMock(returncode=0, stdout='Success', stderr='')
        mock_check_output.return_value = b'Success'

        yield {'run': mock_run, 'check_output': mock_check_output}


@pytest.fixture
def mock_os_path():
    """Create a mock os.path module."""
    with (
        patch('os.path.exists') as mock_exists,
        patch('os.path.isdir') as mock_isdir,
        patch('os.path.isabs') as mock_isabs,
    ):
        # Default return values
        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_isabs.return_value = True

        yield {'exists': mock_exists, 'isdir': mock_isdir, 'isabs': mock_isabs}


@pytest.fixture
def mock_aws_provider_docs():
    """Create mock AWS provider documentation data."""
    return [
        {
            'asset_name': 'aws_s3_bucket',
            'asset_type': 'resource',
            'description': 'Provides an S3 bucket resource.',
            'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket',
            'example_usage': [
                'resource "aws_s3_bucket" "example" {\n  bucket = "my-bucket"\n  tags = {\n    Name = "My bucket"\n  }\n}'
            ],
            'arguments': [
                {'name': 'bucket', 'description': 'The name of the bucket.', 'required': False},
                {
                    'name': 'tags',
                    'description': 'A map of tags to assign to the bucket.',
                    'required': False,
                },
            ],
            'attributes': [
                {'name': 'id', 'description': 'The name of the bucket.'},
                {'name': 'arn', 'description': 'The ARN of the bucket.'},
            ],
        },
        {
            'asset_name': 'aws_s3_bucket',
            'asset_type': 'data_source',
            'description': 'Provides details about an S3 bucket.',
            'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/s3_bucket',
            'example_usage': ['data "aws_s3_bucket" "example" {\n  bucket = "my-bucket"\n}'],
            'arguments': [
                {'name': 'bucket', 'description': 'The name of the bucket.', 'required': True}
            ],
            'attributes': [
                {'name': 'id', 'description': 'The name of the bucket.'},
                {'name': 'arn', 'description': 'The ARN of the bucket.'},
            ],
        },
    ]


@pytest.fixture
def mock_awscc_provider_docs():
    """Create mock AWSCC provider documentation data."""
    return [
        {
            'asset_name': 'awscc_s3_bucket',
            'asset_type': 'resource',
            'description': 'Provides an S3 bucket resource using Cloud Control API.',
            'url': 'https://registry.terraform.io/providers/hashicorp/awscc/latest/docs/resources/s3_bucket',
            'example_usage': [
                'resource "awscc_s3_bucket" "example" {\n  bucket_name = "my-bucket"\n  tags = {\n    Name = "My bucket"\n  }\n}'
            ],
            'schema_arguments': [
                {
                    'name': 'bucket_name',
                    'description': 'The name of the bucket.',
                    'required': True,
                },
                {
                    'name': 'tags',
                    'description': 'A map of tags to assign to the bucket.',
                    'required': False,
                },
            ],
        },
        {
            'asset_name': 'awscc_s3_bucket',
            'asset_type': 'data_source',
            'description': 'Provides details about an S3 bucket using Cloud Control API.',
            'url': 'https://registry.terraform.io/providers/hashicorp/awscc/latest/docs/data-sources/s3_bucket',
            'example_usage': [
                'data "awscc_s3_bucket" "example" {\n  bucket_name = "my-bucket"\n}'
            ],
            'schema_arguments': [
                {'name': 'bucket_name', 'description': 'The name of the bucket.', 'required': True}
            ],
        },
    ]


@pytest.fixture
def mock_aws_ia_modules():
    """Create mock AWS-IA modules data."""
    return [
        {
            'name': 'bedrock',
            'namespace': 'aws-ia',
            'provider': 'aws',
            'version': '1.0.0',
            'description': 'Amazon Bedrock module for generative AI applications',
            'url': 'https://registry.terraform.io/modules/aws-ia/bedrock/aws/latest',
            'readme': '# AWS Bedrock Terraform Module\n\nThis module helps you deploy Amazon Bedrock resources.',
            'variables': [
                {
                    'name': 'name',
                    'description': 'Name to use for resources',
                    'default': 'bedrock-module',
                },
                {
                    'name': 'model_id',
                    'description': 'ID of the Bedrock model to use',
                    'default': None,
                },
            ],
            'outputs': [
                {'name': 'bedrock_endpoint_url', 'description': 'URL of the Bedrock endpoint'},
                {'name': 'model_arn', 'description': 'ARN of the Bedrock model'},
            ],
            'submodules': ['agent', 'knowledge_base'],
        },
        {
            'name': 'opensearch-serverless',
            'namespace': 'aws-ia',
            'provider': 'aws',
            'version': '1.0.0',
            'description': 'OpenSearch Serverless collection for vector search',
            'url': 'https://registry.terraform.io/modules/aws-ia/opensearch-serverless/aws/latest',
            'readme': '# AWS OpenSearch Serverless Terraform Module\n\nThis module helps you deploy OpenSearch Serverless collections.',
            'variables': [
                {
                    'name': 'collection_name',
                    'description': 'Name of the OpenSearch Serverless collection',
                    'default': 'vector-search',
                },
                {
                    'name': 'vector_search_enabled',
                    'description': 'Whether to enable vector search',
                    'default': True,
                },
            ],
            'outputs': [
                {
                    'name': 'collection_endpoint',
                    'description': 'Endpoint of the OpenSearch Serverless collection',
                },
                {
                    'name': 'collection_arn',
                    'description': 'ARN of the OpenSearch Serverless collection',
                },
            ],
            'submodules': [],
        },
    ]


@pytest.fixture
def mock_terragrunt_command_output():
    """Create mock output for Terragrunt commands."""
    return {
        'init': {
            'success': {
                'returncode': 0,
                'stdout': 'Terragrunt has been successfully initialized!',
                'stderr': '',
            },
            'error': {'returncode': 1, 'stdout': '', 'stderr': 'Error: Could not load plugin'},
        },
        'plan': {
            'success': {
                'returncode': 0,
                'stdout': 'Plan: 3 to add, 1 to change, 2 to destroy.',
                'stderr': '',
            },
            'error': {
                'returncode': 1,
                'stdout': '',
                'stderr': 'Error: No configuration files found!',
            },
        },
        'apply': {
            'success': {
                'returncode': 0,
                'stdout': 'Apply complete! Resources: 3 added, 1 changed, 2 destroyed.',
                'stderr': '',
            },
            'error': {'returncode': 1, 'stdout': '', 'stderr': 'Error: Could not load backend'},
        },
        'destroy': {
            'success': {
                'returncode': 0,
                'stdout': 'Destroy complete! Resources: 6 destroyed.',
                'stderr': '',
            },
            'error': {'returncode': 1, 'stdout': '', 'stderr': 'Error: Could not read state file'},
        },
        'validate': {
            'success': {
                'returncode': 0,
                'stdout': 'Success! The configuration is valid.',
                'stderr': '',
            },
            'error': {'returncode': 1, 'stdout': '', 'stderr': 'Error: Invalid resource name'},
        },
        'output': {
            'success': {
                'returncode': 0,
                'stdout': json.dumps(
                    {
                        'instance_id': {'value': 'i-1234567890abcdef0', 'type': 'string'},
                        'vpc_id': {'value': 'vpc-1234567890abcdef0', 'type': 'string'},
                    }
                ),
                'stderr': '',
            },
            'error': {'returncode': 1, 'stdout': '', 'stderr': 'Error: No outputs found'},
        },
        'run-all': {
            'success': {
                'returncode': 0,
                'stdout': 'Terragrunt will run the following modules:\n'
                'Module at "/path/to/module1"\n'
                'Module at "/path/to/module2"\n\n'
                'Are you sure you want to run \'terragrunt apply\' in each module? (y/n)\n'
                'Running \'terragrunt apply\' in Module at "/path/to/module1"...\n'
                'Running \'terragrunt apply\' in Module at "/path/to/module2"...\n',
                'stderr': '',
            },
            'error': {
                'returncode': 1,
                'stdout': '',
                'stderr': 'Error: No terragrunt.hcl files found',
            },
        },
    }