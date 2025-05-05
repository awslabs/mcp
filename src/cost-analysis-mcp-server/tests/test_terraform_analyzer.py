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

"""Tests for the Terraform project analyzer."""

import pytest
from awslabs.cost_analysis_mcp_server.terraform_analyzer import (
    TerraformAnalyzer,
    analyze_terraform_project,
)


@pytest.fixture
def sample_terraform_project(tmp_path):
    """Create a sample Terraform project for testing."""
    project_dir = tmp_path / 'terraform_project'
    project_dir.mkdir()

    # Create a main.tf file with AWS and AWSCC resources
    main_tf = project_dir / 'main.tf'
    main_tf.write_text(
        """
provider "aws" {
  region = "us-west-2"
}

provider "awscc" {
  region = "us-west-2"
}

resource "aws_lambda_function" "example" {
  filename      = "lambda_function_payload.zip"
  function_name = "lambda_function_name"
  role          = aws_iam_role.lambda_role.arn
  handler       = "index.handler"
  runtime       = "nodejs18.x"
}

resource "aws_dynamodb_table" "example" {
  name           = "example-table"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"
  attribute {
    name = "id"
    type = "S"
  }
}

data "aws_s3_bucket" "existing" {
  bucket = "my-bucket"
}

resource "awscc_cloudformation_stack" "example" {
  name = "example-stack"
  template_body = jsonencode({
    Resources = {
      MyBucket = {
        Type = "AWS::S3::Bucket"
      }
    }
  })
}

data "awscc_organizations_organization" "current" {
}
"""
    )

    # Create a variables.tf file
    variables_tf = project_dir / 'variables.tf'
    variables_tf.write_text(
        """
variable "environment" {
  type    = string
  default = "dev"
}
"""
    )

    return project_dir


@pytest.mark.asyncio
async def test_analyze_terraform_project(sample_terraform_project):
    """Test analyzing a Terraform project."""
    result = await analyze_terraform_project(str(sample_terraform_project))

    assert result['status'] == 'success'
    assert len(result['services']) == 5

    # Group services by provider
    aws_services = []
    awscc_services = []

    for service in result['services']:
        assert service['source'] == 'terraform'
        if service['provider'] == 'aws':
            aws_services.append(service['name'])
        elif service['provider'] == 'awscc':
            awscc_services.append(service['name'])

    # Verify AWS provider services
    assert 'lambda' in aws_services
    assert 'dynamodb' in aws_services
    assert 's3' in aws_services

    # Verify AWSCC provider services
    assert 'cloudformation' in awscc_services
    assert 'organizations' in awscc_services


@pytest.mark.asyncio
async def test_analyze_nonexistent_project():
    """Test analyzing a non-existent project directory."""
    result = await analyze_terraform_project('/nonexistent/path')

    assert result['status'] == 'error'
    assert not result['services']
    assert 'Path not found' in result['details']['error']


@pytest.mark.asyncio
async def test_analyze_empty_project(tmp_path):
    """Test analyzing an empty project directory."""
    empty_dir = tmp_path / 'empty_project'
    empty_dir.mkdir()

    result = await analyze_terraform_project(str(empty_dir))

    assert result['status'] == 'success'
    assert not result['services']


@pytest.mark.asyncio
async def test_terraform_analyzer_file_analysis(sample_terraform_project):
    """Test the file analysis method of TerraformAnalyzer."""
    analyzer = TerraformAnalyzer(str(sample_terraform_project))
    main_tf = sample_terraform_project / 'main.tf'

    services = analyzer._analyze_file(main_tf)

    assert len(services) == 5

    # Group services by provider
    aws_services = []
    awscc_services = []

    for service in services:
        assert service['source'] == 'terraform'
        if service['provider'] == 'aws':
            aws_services.append(service['name'])
        elif service['provider'] == 'awscc':
            awscc_services.append(service['name'])

    # Verify AWS provider services
    assert 'lambda' in aws_services
    assert 'dynamodb' in aws_services
    assert 's3' in aws_services

    # Verify AWSCC provider services
    assert 'cloudformation' in awscc_services
    assert 'organizations' in awscc_services
