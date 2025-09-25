"""Tests for the Terraform MCP server resources."""

import pytest
from awslabs.terraform_mcp_server.impl.resources.terraform_aws_provider_resources_listing import (
    terraform_aws_provider_assets_listing_impl,
)
from awslabs.terraform_mcp_server.impl.resources.terraform_awscc_provider_resources_listing import (
    terraform_awscc_provider_resources_listing_impl,
)
from pathlib import Path
from unittest.mock import mock_open, patch


pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_terraform_aws_provider_assets_listing_success():
    """Test the AWS provider resources listing with a mock file."""
    mock_content = """# AWS Provider Resources Listing

## Compute
- aws_instance
- aws_launch_template

## Storage
- aws_s3_bucket
- aws_ebs_volume
"""

    # Mock the Path.exists method to return True
    with patch.object(Path, 'exists', return_value=True):
        # Mock the open function
        with patch('builtins.open', mock_open(read_data=mock_content)):
            # Call the function
            result = await terraform_aws_provider_assets_listing_impl()

            # Check the result
            assert result == mock_content
            assert 'AWS Provider Resources Listing' in result
            assert 'Compute' in result
            assert 'aws_instance' in result


@pytest.mark.asyncio
async def test_terraform_aws_provider_assets_listing_file_not_found():
    """Test the AWS provider resources listing when the file is not found."""
    # Mock the Path.exists method to return False
    with patch.object(Path, 'exists', return_value=False):
        # Call the function
        result = await terraform_aws_provider_assets_listing_impl()

        # Check the result
        assert 'Error generating listing' in result
        assert 'Static assets list file not found' in result


@pytest.mark.asyncio
async def test_terraform_aws_provider_assets_listing_exception():
    """Test the AWS provider resources listing when an exception occurs."""
    # Mock the Path.exists method to return True
    with patch.object(Path, 'exists', return_value=True):
        # Mock the open function to raise an exception
        with patch('builtins.open', side_effect=Exception('Test exception')):
            # Call the function
            result = await terraform_aws_provider_assets_listing_impl()

            # Check the result
            assert 'Error generating listing' in result
            assert 'Test exception' in result


@pytest.mark.asyncio
async def test_terraform_awscc_provider_resources_listing_success():
    """Test the AWSCC provider resources listing with a mock file."""
    mock_content = """# AWSCC Provider Resources Listing

## Compute
- awscc_ec2_instance
- awscc_ec2_launch_template

## Storage
- awscc_s3_bucket
- awscc_ebs_volume
"""

    # Mock the Path.exists method to return True
    with patch.object(Path, 'exists', return_value=True):
        # Mock the open function
        with patch('builtins.open', mock_open(read_data=mock_content)):
            # Call the function
            result = await terraform_awscc_provider_resources_listing_impl()

            # Check the result
            assert result == mock_content
            assert 'AWSCC Provider Resources Listing' in result
            assert 'Compute' in result
            assert 'awscc_ec2_instance' in result


@pytest.mark.asyncio
async def test_terraform_awscc_provider_resources_listing_file_not_found():
    """Test the AWSCC provider resources listing when the file is not found."""
    # Mock the Path.exists method to return False
    with patch.object(Path, 'exists', return_value=False):
        # Call the function
        result = await terraform_awscc_provider_resources_listing_impl()

        # Check the result
        assert 'Error generating listing' in result
        assert 'Static assets list file not found' in result


@pytest.mark.asyncio
async def test_terraform_awscc_provider_resources_listing_exception():
    """Test the AWSCC provider resources listing when an exception occurs."""
    # Mock the Path.exists method to return True
    with patch.object(Path, 'exists', return_value=True):
        # Mock the open function to raise an exception
        with patch('builtins.open', side_effect=Exception('Test exception')):
            # Call the function
            result = await terraform_awscc_provider_resources_listing_impl()

            # Check the result
            assert 'Error generating listing' in result
            assert 'Test exception' in result
