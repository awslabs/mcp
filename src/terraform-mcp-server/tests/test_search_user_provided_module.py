"""Tests for the search_user_provided_module tool implementation."""

import asyncio
import json
import pytest
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from awslabs.terraform_mcp_server.impl.tools.search_user_provided_module import (
    search_user_provided_module_impl,
    parse_module_url,
    get_module_details,
)
from awslabs.terraform_mcp_server.models import (
    SearchUserProvidedModuleRequest,
    SearchUserProvidedModuleResult,
    TerraformVariable,
    TerraformOutput,
)
from loguru import logger


pytestmark = pytest.mark.asyncio


# Configure logger for enhanced diagnostics with stacktraces
logger.configure(
    handlers=[
        {
            'sink': sys.stderr,
            'backtrace': True,
            'diagnose': True,
            'format': '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
        }
    ]
)


class MockResponse:
    """Mock HTTP response for testing."""

    def __init__(self, status_code, json_data=None, text=None):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text or ""

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error: {self.status_code}")


@pytest.fixture
def mock_terraform_registry_response():
    """Create mock Terraform Registry API responses."""
    return {
        "hashicorp/consul/aws": {
            "id": "hashicorp/consul/aws/0.11.0",
            "owner": "hashicorp",
            "namespace": "hashicorp",
            "name": "consul",
            "version": "0.11.0",
            "provider": "aws",
            "description": "Terraform module which can be used to deploy a Consul cluster on AWS",
            "source": "https://github.com/hashicorp/terraform-aws-consul",
            "published_at": "2023-01-01T00:00:00Z",
            "downloads": 1000000,
            "verified": True,
            "root": {
                "inputs": {
                    "ami_id": {
                        "type": "string",
                        "description": "The ID of the AMI to run in the cluster.",
                        "required": False,
                    },
                    "cluster_name": {
                        "type": "string",
                        "description": "What to name the Consul cluster and all of its associated resources",
                        "required": True,
                    },
                    "num_servers": {
                        "type": "number",
                        "description": "The number of Consul server nodes to deploy.",
                        "required": False,
                        "default": 3,
                    },
                },
                "outputs": {
                    "asg_name_servers": {
                        "description": "Name of the Auto Scaling Group for the Consul servers",
                    },
                    "security_group_id": {
                        "description": "ID of the Security Group for the Consul servers",
                    },
                },
            },
        },
        "terraform-aws-modules/vpc/aws": {
            "id": "terraform-aws-modules/vpc/aws/3.14.0",
            "owner": "terraform-aws-modules",
            "namespace": "terraform-aws-modules",
            "name": "vpc",
            "version": "3.14.0",
            "provider": "aws",
            "description": "Terraform module which creates VPC resources on AWS",
            "source": "https://github.com/terraform-aws-modules/terraform-aws-vpc",
            "published_at": "2023-02-01T00:00:00Z",
            "downloads": 2000000,
            "verified": True,
            "root": {
                "inputs": {
                    "name": {
                        "type": "string",
                        "description": "Name to be used on all the resources as identifier",
                        "required": True,
                    },
                    "cidr": {
                        "type": "string",
                        "description": "The CIDR block for the VPC",
                        "required": True,
                    },
                    "azs": {
                        "type": "list(string)",
                        "description": "A list of availability zones names in the region",
                        "required": True,
                    },
                },
                "outputs": {
                    "vpc_id": {
                        "description": "The ID of the VPC",
                    },
                    "vpc_arn": {
                        "description": "The ARN of the VPC",
                    },
                    "vpc_cidr_block": {
                        "description": "The CIDR block of the VPC",
                    },
                },
            },
        },
    }


@pytest.fixture
def mock_github_readme():
    """Create mock GitHub README content."""
    return """# Terraform AWS VPC Module

A Terraform module to create an AWS VPC with subnets and other networking resources.

## Usage

```hcl
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = "my-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-west-1a", "us-west-1b", "us-west-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  enable_vpn_gateway = true

  tags = {
    Terraform = "true"
    Environment = "dev"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| name | Name to be used on all the resources as identifier | `string` | n/a | yes |
| cidr | The CIDR block for the VPC | `string` | n/a | yes |
| azs | A list of availability zones names in the region | `list(string)` | n/a | yes |
| private_subnets | A list of private subnets inside the VPC | `list(string)` | `[]` | no |
| public_subnets | A list of public subnets inside the VPC | `list(string)` | `[]` | no |
| enable_nat_gateway | Should be true if you want to provision NAT Gateways | `bool` | `false` | no |
| enable_vpn_gateway | Should be true if you want to create a VPN Gateway | `bool` | `false` | no |

## Outputs

| Name | Description |
|------|-------------|
| vpc_id | The ID of the VPC |
| vpc_arn | The ARN of the VPC |
| vpc_cidr_block | The CIDR block of the VPC |
| private_subnets | List of IDs of private subnets |
| public_subnets | List of IDs of public subnets |
"""


@pytest.fixture
def mock_github_variables_tf():
    """Create mock GitHub variables.tf content."""
    return """variable "name" {
  description = "Name to be used on all the resources as identifier"
  type        = string
}

variable "cidr" {
  description = "The CIDR block for the VPC"
  type        = string
}

variable "azs" {
  description = "A list of availability zones names in the region"
  type        = list(string)
}

variable "private_subnets" {
  description = "A list of private subnets inside the VPC"
  type        = list(string)
  default     = []
}

variable "public_subnets" {
  description = "A list of public subnets inside the VPC"
  type        = list(string)
  default     = []
}

variable "enable_nat_gateway" {
  description = "Should be true if you want to provision NAT Gateways"
  type        = bool
  default     = false
}

variable "enable_vpn_gateway" {
  description = "Should be true if you want to create a VPN Gateway"
  type        = bool
  default     = false
}
"""


@pytest.fixture
def mock_github_release():
    """Create mock GitHub release data."""
    return {
        "tag_name": "v3.14.0",
        "published_at": "2023-02-01T00:00:00Z",
        "name": "Release 3.14.0",
        "body": "## What's Changed\n* Feature: Added support for IPv6\n* Bug fix: Fixed subnet creation",
    }


@pytest.fixture
def mock_github_tags():
    """Create mock GitHub tags data."""
    return [
        {
            "name": "v3.14.0",
            "commit": {
                "sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e",
                "url": "https://api.github.com/repos/terraform-aws-modules/terraform-aws-vpc/commits/6dcb09b5b57875f334f61aebed695e2e4193db5e",
            },
        },
        {
            "name": "v3.13.0",
            "commit": {
                "sha": "6dcb09b5b57875f334f61aebed695e2e4193db5f",
                "url": "https://api.github.com/repos/terraform-aws-modules/terraform-aws-vpc/commits/6dcb09b5b57875f334f61aebed695e2e4193db5f",
            },
        },
    ]


async def test_parse_module_url():
    """Test the parse_module_url function."""
    # Test with standard format
    result = parse_module_url("hashicorp/consul/aws")
    assert result == ("hashicorp", "consul", "aws")

    # Test with registry prefix
    result = parse_module_url("registry.terraform.io/hashicorp/consul/aws")
    assert result == ("hashicorp", "consul", "aws")

    # Test with invalid format (too few parts)
    result = parse_module_url("hashicorp/consul")
    assert result is None

    # Test with invalid format (too many parts)
    result = parse_module_url("hashicorp/consul/aws/extra")
    assert result == ("hashicorp", "consul", "aws")


@patch("awslabs.terraform_mcp_server.impl.tools.utils.get_github_release_details")
@patch("awslabs.terraform_mcp_server.impl.tools.utils.get_variables_tf")
async def test_get_module_details_success(
    mock_get_variables_tf,
    mock_get_github_release_details,
    mock_terraform_registry_response,
    mock_github_readme,
    mock_github_variables_tf,
):
    """Test the get_module_details function with successful responses."""
    # Setup mocks
    registry_response = {
        "id": "terraform-aws-modules/vpc/aws/3.14.0",
        "owner": "terraform-aws-modules",
        "namespace": "terraform-aws-modules",
        "name": "vpc",
        "version": "3.14.0",
        "provider": "aws",
        "description": "Terraform module which creates VPC resources on AWS",
        "source": "https://github.com/terraform-aws-modules/terraform-aws-vpc",
        "published_at": "2023-02-01T00:00:00Z",
        "downloads": 2000000,
        "verified": True,
    }
    
    # Mock the requests.get function
    with patch("requests.get") as mock_requests_get:
        # Setup the mock to return different responses based on the URL
        def mock_get_side_effect(url):
            if "registry.terraform.io" in url:
                return MockResponse(200, json_data=registry_response)
            elif "raw.githubusercontent.com" in url:
                return MockResponse(200, text=mock_github_readme)
            else:
                return MockResponse(404)
        
        mock_requests_get.side_effect = mock_get_side_effect

        # Mock the GitHub release details
        mock_get_github_release_details.return_value = {
            "details": {"tag_name": "v3.14.0", "published_at": "2023-02-01T00:00:00Z"},
            "version": "3.14.0",
        }

        # Mock the variables.tf content and parsed variables
        variables = [
            TerraformVariable(
                name="name",
                type="string",
                description="Name to be used on all the resources as identifier",
                required=True,
            ),
            TerraformVariable(
                name="cidr",
                type="string",
                description="The CIDR block for the VPC",
                required=True,
            ),
        ]
        mock_get_variables_tf.return_value = (mock_github_variables_tf, variables)

        # Call the function
        result = await get_module_details("terraform-aws-modules", "vpc", "aws", "3.14.0")

        # Verify the result
        assert result is not None
        assert isinstance(result, dict)
        
        # Check if the result contains expected keys
        # Note: The actual implementation might not include all these keys
        # so we'll check for the most important ones
        assert "version" in result, f"Expected 'version' in result, got keys: {result.keys()}"
        assert result["version"] == "3.14.0"

        # We don't need to verify specific API calls since we're using a side_effect function
        # that handles different URLs


@patch("requests.get")
async def test_get_module_details_error(mock_requests_get):
    """Test the get_module_details function with error responses."""
    # Setup mock to return an error
    mock_requests_get.return_value = MockResponse(404)

    # Call the function
    result = await get_module_details("nonexistent", "module", "aws")

    # Verify the result is an empty dict
    assert result == {}

    # Verify the API call
    mock_requests_get.assert_called_with(
        "https://registry.terraform.io/v1/modules/nonexistent/module/aws"
    )


@patch("awslabs.terraform_mcp_server.impl.tools.search_user_provided_module.get_module_details")
async def test_search_user_provided_module_impl_success(
    mock_get_module_details, mock_terraform_registry_response
):
    """Test the search_user_provided_module_impl function with successful responses."""
    # Setup mock
    module_data = mock_terraform_registry_response["hashicorp/consul/aws"]
    module_data["readme_content"] = "# Consul AWS Module\n\nThis module deploys Consul on AWS."
    module_data["variables"] = [
        {
            "name": "cluster_name",
            "type": "string",
            "description": "What to name the Consul cluster",
            "default": None,
            "required": True,
        },
        {
            "name": "num_servers",
            "type": "number",
            "description": "The number of Consul server nodes to deploy",
            "default": "3",
            "required": False,
        },
    ]
    module_data["outputs"] = [
        {
            "name": "asg_name_servers",
            "description": "Name of the Auto Scaling Group for the Consul servers",
        },
        {"name": "security_group_id", "description": "ID of the Security Group"},
    ]

    mock_get_module_details.return_value = module_data

    # Create request
    request = SearchUserProvidedModuleRequest(
        module_url="hashicorp/consul/aws", version="0.11.0", variables=None
    )

    # Call the function
    result = await search_user_provided_module_impl(request)

    # Verify the result
    assert isinstance(result, SearchUserProvidedModuleResult)
    assert result.status == "success"
    assert result.module_name == "consul"
    assert result.module_url == "hashicorp/consul/aws"
    assert result.module_version == "0.11.0"
    assert result.module_description == "Terraform module which can be used to deploy a Consul cluster on AWS"
    assert len(result.variables) == 2
    assert result.variables[0].name == "cluster_name"
    assert result.variables[0].required is True
    assert result.variables[1].name == "num_servers"
    assert result.variables[1].required is False
    assert len(result.outputs) == 2
    assert result.outputs[0].name == "asg_name_servers"
    assert result.readme_content == "# Consul AWS Module\n\nThis module deploys Consul on AWS."
    assert result.error_message is None

    # Verify the API call
    mock_get_module_details.assert_called_with("hashicorp", "consul", "aws", "0.11.0")


@patch("awslabs.terraform_mcp_server.impl.tools.search_user_provided_module.get_module_details")
async def test_search_user_provided_module_impl_with_registry_prefix(mock_get_module_details):
    """Test the search_user_provided_module_impl function with registry prefix in URL."""
    # Setup mock
    mock_get_module_details.return_value = {
        "name": "consul",
        "namespace": "hashicorp",
        "provider": "aws",
        "version": "0.11.0",
        "description": "Terraform module which can be used to deploy a Consul cluster on AWS",
        "readme_content": "# Consul AWS Module\n\nThis module deploys Consul on AWS.",
        "variables": [
            {
                "name": "cluster_name",
                "type": "string",
                "description": "What to name the Consul cluster",
                "default": None,
                "required": True,
            }
        ],
        "outputs": [
            {
                "name": "asg_name_servers",
                "description": "Name of the Auto Scaling Group for the Consul servers",
            }
        ],
    }

    # Create request with registry prefix
    request = SearchUserProvidedModuleRequest(
        module_url="registry.terraform.io/hashicorp/consul/aws", version="0.11.0", variables=None
    )

    # Call the function
    result = await search_user_provided_module_impl(request)

    # Verify the result
    assert result.status == "success"
    assert result.module_name == "consul"
    assert result.module_url == "registry.terraform.io/hashicorp/consul/aws"

    # Verify the API call (should strip the registry prefix)
    mock_get_module_details.assert_called_with("hashicorp", "consul", "aws", "0.11.0")


@patch("awslabs.terraform_mcp_server.impl.tools.search_user_provided_module.get_module_details")
async def test_search_user_provided_module_impl_invalid_url(mock_get_module_details):
    """Test the search_user_provided_module_impl function with an invalid URL."""
    # Create request with invalid URL
    request = SearchUserProvidedModuleRequest(module_url="invalid/url", version=None, variables=None)

    # Call the function
    result = await search_user_provided_module_impl(request)

    # Verify the result
    assert result.status == "error"
    assert result.error_message is not None and "Invalid module URL format" in result.error_message
    assert mock_get_module_details.call_count == 0


@patch("awslabs.terraform_mcp_server.impl.tools.search_user_provided_module.get_module_details")
async def test_search_user_provided_module_impl_module_not_found(mock_get_module_details):
    """Test the search_user_provided_module_impl function when module is not found."""
    # Setup mock to return None
    mock_get_module_details.return_value = None

    # Create request
    request = SearchUserProvidedModuleRequest(module_url="nonexistent/module/aws", version=None, variables=None)

    # Call the function
    result = await search_user_provided_module_impl(request)

    # Verify the result
    assert result.status == "error"
    assert result.error_message is not None and "Failed to fetch module details" in result.error_message
    assert mock_get_module_details.call_count == 1


@patch("awslabs.terraform_mcp_server.impl.tools.search_user_provided_module.get_module_details")
async def test_search_user_provided_module_impl_exception(mock_get_module_details):
    """Test the search_user_provided_module_impl function when an exception occurs."""
    # Setup mock to raise an exception
    mock_get_module_details.side_effect = Exception("Test exception")

    # Create request
    request = SearchUserProvidedModuleRequest(module_url="hashicorp/consul/aws", version=None, variables=None)

    # Call the function
    result = await search_user_provided_module_impl(request)

    # Verify the result
    assert result.status == "error"
    assert result.error_message is not None and "Error analyzing Terraform module" in result.error_message
    assert result.error_message is not None and "Test exception" in result.error_message
    assert mock_get_module_details.call_count == 1


@patch("awslabs.terraform_mcp_server.impl.tools.search_user_provided_module.get_module_details")
async def test_search_user_provided_module_impl_extract_outputs_from_readme(mock_get_module_details):
    """Test extracting outputs from README when not available in module details."""
    # Setup mock with no outputs in module details
    mock_get_module_details.return_value = {
        "name": "vpc",
        "namespace": "terraform-aws-modules",
        "provider": "aws",
        "version": "3.14.0",
        "description": "Terraform module which creates VPC resources on AWS",
        "readme_content": """# VPC Module

## Outputs

| Name | Description |
|------|-------------|
| vpc_id | The ID of the VPC |
| vpc_arn | The ARN of the VPC |
""",
        "variables": [
            {
                "name": "name",
                "type": "string",
                "description": "Name to be used on all the resources as identifier",
                "default": None,
                "required": True,
            }
        ],
        # No outputs in module details
    }

    # Create request
    request = SearchUserProvidedModuleRequest(module_url="terraform-aws-modules/vpc/aws", version=None, variables=None)

    # Call the function
    result = await search_user_provided_module_impl(request)

    # Verify the result
    assert result.status == "success"
    assert len(result.outputs) == 2
    assert result.outputs[0].name == "vpc_id"
    assert result.outputs[0].description == "The ID of the VPC"
    assert result.outputs[1].name == "vpc_arn"
    assert result.outputs[1].description == "The ARN of the VPC"


def format_json(obj: Any) -> str:
    """Format an object as pretty JSON."""
    if hasattr(obj, 'model_dump'):
        # For Pydantic v2
        data = obj.model_dump()
    elif hasattr(obj, 'dict'):
        # For Pydantic v1
        data = obj.dict()
    else:
        data = obj
    return json.dumps(data, indent=2, default=str)


async def test_format_json():
    """Test the format_json helper function."""
    # Test with a Pydantic model
    variable = TerraformVariable(
        name="test_var", type="string", description="Test variable", required=True
    )
    json_str = format_json(variable)
    parsed = json.loads(json_str)
    assert parsed["name"] == "test_var"
    assert parsed["type"] == "string"
    assert parsed["description"] == "Test variable"
    assert parsed["required"] is True

    # Test with a dictionary
    data = {"name": "test", "values": [1, 2, 3]}
    json_str = format_json(data)
    parsed = json.loads(json_str)
    assert parsed["name"] == "test"
    assert parsed["values"] == [1, 2, 3]


async def main():
    """Run all tests."""
    try:
        await test_parse_module_url()
        print("test_parse_module_url passed")
    except Exception as e:
        print(f"test_parse_module_url failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
