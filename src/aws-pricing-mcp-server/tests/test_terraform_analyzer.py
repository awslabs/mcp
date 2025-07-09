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

"""Tests for the Terraform project analyzer."""

import pytest
from awslabs.aws_pricing_mcp_server.terraform_analyzer import (
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

# Module blocks for testing module recognition
module "s3_bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "3.14.0"

  bucket = "my-s3-bucket"
  acl    = "private"

  versioning = {
    enabled = true
  }
}

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = "my-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-west-2a", "us-west-2b", "us-west-2c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true
}

module "custom_lambda" {
  source = "aws-ia/lambda-function/aws"

  function_name = "custom-lambda"
  handler       = "index.handler"
  runtime       = "nodejs18.x"
  memory_size   = 512
}

module "container_definition" {
  source = "cloudposse/ecs-container-definition/aws"

  container_name  = "app"
  container_image = "nginx:latest"
  essential       = true

  port_mappings = [
    {
      containerPort = 80
      hostPort      = 80
      protocol      = "tcp"
    }
  ]
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

    # Create a modules directory with a lambda module
    lambda_module_dir = project_dir / 'modules' / 'lambda'
    lambda_module_dir.mkdir(parents=True)

    # Create main.tf in the lambda module
    lambda_main_tf = lambda_module_dir / 'main.tf'
    lambda_main_tf.write_text(
        """
resource "aws_lambda_function" "this" {
  function_name = var.function_name
  handler       = var.handler
  runtime       = var.runtime
  memory_size   = var.memory_size

  filename = "dummy.zip"
  role     = aws_iam_role.lambda_role.arn
}

resource "aws_iam_role" "lambda_role" {
  name = "${var.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}
"""
    )

    # Create variables.tf in the lambda module
    lambda_variables_tf = lambda_module_dir / 'variables.tf'
    lambda_variables_tf.write_text(
        """
variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "handler" {
  description = "Lambda function handler"
  type        = string
}

variable "runtime" {
  description = "Lambda function runtime"
  type        = string
}

variable "memory_size" {
  description = "Lambda function memory size"
  type        = number
  default     = 128
}
"""
    )

    return project_dir


@pytest.mark.asyncio
async def test_analyze_terraform_project(sample_terraform_project):
    """Test analyzing a Terraform project."""
    result = await analyze_terraform_project(str(sample_terraform_project))

    assert result['status'] == 'success'
    # We should have the original 5 services plus at least 3 from modules (s3, vpc, lambda)
    assert len(result['services']) >= 8

    # Group services by source and provider
    aws_resources = []
    awscc_resources = []
    module_services = []

    for service in result['services']:
        if service['source'] == 'terraform':
            if service['provider'] == 'aws':
                aws_resources.append(service['name'])
            elif service['provider'] == 'awscc':
                awscc_resources.append(service['name'])
        elif service['source'] == 'terraform-module':
            module_services.append(service['name'])

    # Verify AWS provider services from direct resources
    assert 'lambda' in aws_resources
    assert 'dynamodb' in aws_resources
    assert 's3' in aws_resources

    # Verify AWSCC provider services from direct resources
    assert 'cloudformation' in awscc_resources
    assert 'organizations' in awscc_resources

    # Verify services found from modules
    assert 's3' in module_services
    assert 'vpc' in module_services
    assert 'lambda' in module_services
    assert 'ecs' in module_services  # From cloudposse/ecs-container-definition/aws


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

    # We should have the original 5 services plus at least 3 from modules (s3, vpc, lambda)
    assert len(services) >= 8

    # Group services by source and provider
    aws_resources = []
    awscc_resources = []
    module_services = []

    for service in services:
        if service['source'] == 'terraform':
            if service['provider'] == 'aws':
                aws_resources.append(service['name'])
            elif service['provider'] == 'awscc':
                awscc_resources.append(service['name'])
        elif service['source'] == 'terraform-module':
            module_services.append(service['name'])

    # Verify AWS provider services from direct resources
    assert 'lambda' in aws_resources
    assert 'dynamodb' in aws_resources
    assert 's3' in aws_resources

    # Verify AWSCC provider services from direct resources
    assert 'cloudformation' in awscc_resources
    assert 'organizations' in awscc_resources

    # Verify services found from modules
    assert 's3' in module_services
    assert 'vpc' in module_services
    assert 'lambda' in module_services
    assert 'ecs' in module_services  # From cloudposse/ecs-container-definition/aws


@pytest.mark.asyncio
async def test_module_finding():
    """Test the module finding functionality."""
    analyzer = TerraformAnalyzer('/tmp')  # Path doesn't matter for this test

    # Test S3 module finding
    s3_source = 'terraform-aws-modules/s3-bucket/aws'
    s3_vars = {'bucket': 'my-bucket', 'acl': 'private'}
    s3_services = analyzer._find_aws_services_from_module(s3_source, s3_vars)

    assert len(s3_services) > 0
    assert any(service['name'] == 's3' for service in s3_services)

    # Test VPC module finding
    vpc_source = 'terraform-aws-modules/vpc/aws'
    vpc_vars = {'name': 'my-vpc', 'cidr': '10.0.0.0/16'}
    vpc_services = analyzer._find_aws_services_from_module(vpc_source, vpc_vars)

    assert len(vpc_services) > 0
    assert any(service['name'] == 'vpc' for service in vpc_services)

    # Test AWS-IA module finding
    lambda_source = 'aws-ia/lambda-function/aws'
    lambda_vars = {
        'function_name': 'test-lambda',
        'handler': 'index.handler',
        'runtime': 'nodejs18.x',
    }
    lambda_services = analyzer._find_aws_services_from_module(lambda_source, lambda_vars)

    assert len(lambda_services) > 0
    assert any(service['name'] == 'lambda' for service in lambda_services)

    # Test other AWS provider module finding (e.g., cloudposse/ecs-container-definition/aws)
    ecs_source = 'cloudposse/ecs-container-definition/aws'
    ecs_vars = {'container_name': 'app', 'container_image': 'nginx:latest', 'essential': 'true'}
    ecs_services = analyzer._find_aws_services_from_module(ecs_source, ecs_vars)

    assert len(ecs_services) > 0
    assert any(service['name'] == 'ecs' for service in ecs_services)


@pytest.mark.asyncio
async def test_local_module_finding(tmp_path):
    """Test the local module finding functionality."""
    # Create a temporary directory structure for the test
    project_dir = tmp_path / 'test_project'
    project_dir.mkdir()

    # Create a local module directory with AWS resources
    module_dir = project_dir / 'modules' / 'lambda'
    module_dir.mkdir(parents=True)

    # Create a main.tf file in the module directory with AWS resources
    module_main_tf = module_dir / 'main.tf'
    module_main_tf.write_text(
        """
        resource "aws_lambda_function" "test" {
            function_name = var.function_name
            handler       = var.handler
            runtime       = var.runtime
            role          = aws_iam_role.lambda_role.arn
        }

        resource "aws_iam_role" "lambda_role" {
            name = "${var.function_name}-role"
            assume_role_policy = jsonencode({
                Version = "2012-10-17"
                Statement = [{
                    Action = "sts:AssumeRole"
                    Effect = "Allow"
                    Principal = {
                        Service = "lambda.amazonaws.com"
                    }
                }]
            })
        }
        """
    )

    # Create a variables.tf file in the module directory
    module_vars_tf = module_dir / 'variables.tf'
    module_vars_tf.write_text(
        """
        variable "function_name" {
            description = "Name of the Lambda function"
            type        = string
        }

        variable "handler" {
            description = "Lambda function handler"
            type        = string
        }

        variable "runtime" {
            description = "Lambda function runtime"
            type        = string
        }
        """
    )

    # Create a main.tf file in the project directory that uses the local module
    project_main_tf = project_dir / 'main.tf'
    project_main_tf.write_text(
        """
        module "lambda" {
            source = "./modules/lambda"

            function_name = "test-lambda"
            handler       = "index.handler"
            runtime       = "nodejs18.x"
        }
        """
    )

    # Initialize the analyzer with the project directory
    analyzer = TerraformAnalyzer(str(project_dir))

    # Test local module finding
    local_source = './modules/lambda'
    local_vars = {
        'function_name': 'test-lambda',
        'handler': 'index.handler',
        'runtime': 'nodejs18.x',
    }
    local_services = analyzer._find_aws_services_from_module(local_source, local_vars)

    # Verify that the lambda service was found from the local module
    assert len(local_services) > 0
    assert any(service['name'] == 'lambda' for service in local_services)

    # Test the full project analysis
    result = await analyze_terraform_project(str(project_dir))

    # Verify that the project analysis found the lambda service
    assert result['status'] == 'success'

    # Group services by source and provider
    module_services = [
        service['name']
        for service in result['services']
        if service['source'] == 'terraform-module'
    ]

    # Verify services found from modules
    assert 'lambda' in module_services
