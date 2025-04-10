#!/usr/bin/env python3
"""Test script for Terraform MCP server implementation functions."""

import sys
import asyncio
import json
from loguru import logger
from typing import List, Optional, Dict, Any

# Configure logger for enhanced diagnostics with stacktraces
logger.configure(
    handlers=[
        {"sink": sys.stderr, "backtrace": True, "diagnose": True, 
         "format": "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"}
    ]
)

# Import implementation functions using absolute imports
from awslabs.terraform_mcp_server.impl.tools.search_aws_provider_docs import search_aws_provider_docs_impl
from awslabs.terraform_mcp_server.impl.tools.search_awscc_provider_docs import search_awscc_provider_docs_impl
from awslabs.terraform_mcp_server.impl.tools.search_specific_aws_ia_modules import search_specific_aws_ia_modules_impl
from awslabs.terraform_mcp_server.impl.tools.execute_terraform_command import execute_terraform_command_impl
from awslabs.terraform_mcp_server.impl.tools.run_checkov_scan import run_checkov_scan_impl
from awslabs.terraform_mcp_server.models import (
    TerraformExecutionRequest,
    CheckovScanRequest,
)


async def test_search_aws_provider_docs():
    """Test the AWS provider docs search function."""
    logger.info("=== Testing search_aws_provider_docs_impl ===")
    
    # Test case 1: Common resource with just 1 example snippet
    logger.info("**********---Test case 1: Searching for aws_s3_bucket---**********")
    results = await search_aws_provider_docs_impl("aws_s3_bucket")
    
    logger.info(f"Found {len(results)} results")
    for i, result in enumerate(results):
        logger.info(f"\nResult {i+1}:")
        logger.info(f"  Resource Name: {result.resource_name}")
        logger.info(f"  URL: {result.url}")
        if result.description:
            description_preview = result.description[:100] + "..." if len(result.description) > 100 else result.description
            logger.info(f"  Description: {description_preview}")
        else:
            logger.info("  No description")
        
        if result.example_snippets:
            logger.info(f"  Example Snippets: {len(result.example_snippets)} found")
            for j, snippet in enumerate(result.example_snippets):
                title = snippet.get("title", "Example")
                code = snippet.get("code", "")
                code_preview = code[:100] + "..." if len(code) > 100 else code
                logger.info(f"    Snippet {j+1} - {title}: {code_preview}")

    # Test case 12: Common resource with multiple example snippets
    logger.info("**********---Test case 2: Searching for aws_api_gateway_rest_api---**********")
    results = await search_aws_provider_docs_impl("aws_api_gateway_rest_api")
    
    logger.info(f"Found {len(results)} results")
    for i, result in enumerate(results):
        logger.info(f"\nResult {i+1}:")
        logger.info(f"  Resource Name: {result.resource_name}")
        logger.info(f"  URL: {result.url}")
        if result.description:
            description_preview = result.description[:100] + "..." if len(result.description) > 100 else result.description
            logger.info(f"  Description: {description_preview}")
        else:
            logger.info("  No description")
        
        if result.example_snippets:
            logger.info(f"  Example Snippets: {len(result.example_snippets)} found")
            for j, snippet in enumerate(result.example_snippets):
                title = snippet.get("title", "Example")
                code = snippet.get("code", "")
                code_preview = code[:100] + "..." if len(code) > 100 else code
                logger.info(f"    Snippet {j+1} - {title}: {code_preview}")

    # Test case 3: Resource with attribute
    logger.info("**********---Test case 3: Searching for aws_s3_bucket with versioning attribute---**********")
    results = await search_aws_provider_docs_impl("aws_s3_bucket", "versioning")
    for i, result in enumerate(results):
        logger.info(f"\nResult {i+1}:")
        logger.info(f"  Resource Name: {result.resource_name}")
        if result.description:
            description_preview = result.description[:100] + "..." if len(result.description) > 100 else result.description
            logger.info(f"  Description: {description_preview}")
        else:
            logger.info("  No description")

    # Test case 4: Specifying resource kind
    logger.info("**********---Test case 4: Searching for AWS resource with specific kind---**********")
    results = await search_aws_provider_docs_impl("aws_dynamodb_table", None, "resource")
    
    logger.info(f"Found {len(results)} results")
    for i, result in enumerate(results):
        logger.info(f"\nResult {i+1}:")
        logger.info(f"  Resource Name: {result.resource_name}")
        logger.info(f"  Kind: {result.kind}")
        if result.description:
            description_preview = result.description[:100] + "..." if len(result.description) > 100 else result.description
            logger.info(f"  Description: {description_preview}")
    
    # Test case 5: Specifying data source kind
    logger.info("**********---Test case 5: Searching for AWS data source with specific kind---**********")
    results = await search_aws_provider_docs_impl("aws_dynamodb_table", None, "data_source")
    
    logger.info(f"Found {len(results)} results")
    for i, result in enumerate(results):
        logger.info(f"\nResult {i+1}:")
        logger.info(f"  Resource Name: {result.resource_name}")
        logger.info(f"  Kind: {result.kind}")
        if result.description:
            description_preview = result.description[:100] + "..." if len(result.description) > 100 else result.description
            logger.info(f"  Description: {description_preview}")
    
    # Test case 6: Searching for both kinds
    logger.info("**********---Test case 6: Searching for AWS resource with both kinds---**********")
    results = await search_aws_provider_docs_impl("aws_dynamodb_table", None, "both")
    
    logger.info(f"Found {len(results)} results")
    for i, result in enumerate(results):
        logger.info(f"\nResult {i+1}:")
        logger.info(f"  Resource Name: {result.resource_name}")
        logger.info(f"  Kind: {result.kind}")
        if result.description:
            description_preview = result.description[:100] + "..." if len(result.description) > 100 else result.description
            logger.info(f"  Description: {description_preview}")

    # Test case 7: Non-existent resource
    logger.info("**********---Test case 7: Searching for non-existent resource---**********")
    results = await search_aws_provider_docs_impl("aws_nonexistent_resource")
    for i, result in enumerate(results):
        logger.info(f"\nResult {i+1}:")
        logger.info(f"  Resource Name: {result.resource_name}")
        if result.description:
            logger.info(f"  Description: {result.description}")


async def test_search_awscc_provider_docs():
    """Test the AWSCC provider docs search function."""
    logger.info("\n=== Testing search_awscc_provider_docs_impl ===")
    
    # Test case 1: Common resource
    logger.info("**********---Test case 1: Searching for awscc_apigateway_api_key---**********")
    results = await search_awscc_provider_docs_impl("awscc_apigateway_api_key")
    
    logger.info(f"Found {len(results)} results")
    for i, result in enumerate(results):
        logger.info(f"\nResult {i+1}:")
        logger.info(f"  Resource Name: {result.resource_name}")
        logger.info(f"  URL: {result.url}")
        logger.info(f"  Kind: {result.kind}")
        if result.description:
            description_preview = result.description[:100] + "..." if len(result.description) > 100 else result.description
            logger.info(f"  Description: {description_preview}")
        else:
            logger.info("  No description")
        
        if result.example_snippets:
            logger.info(f"  Example Snippets: {len(result.example_snippets)} found")
            for j, snippet in enumerate(result.example_snippets):
                title = snippet.get("title", "Example")
                code = snippet.get("code", "")
                code_preview = code[:100] + "..." if len(code) > 100 else code
                logger.info(f"    Snippet {j+1} - {title}: {code_preview}")
        
        if result.arguments:
            logger.info(f"  Arguments/Schema: {len(result.arguments)} found")
            for j, arg in enumerate(result.arguments[:5]):  # Show only first 5 arguments
                name = arg.get("name", "")
                desc = arg.get("description", "")
                desc_preview = desc[:50] + "..." if len(desc) > 50 else desc
                logger.info(f"    Argument {j+1}: {name} - {desc_preview}")
    
    # Test case 2: Resource with attribute
    logger.info("**********---Test case 2: Searching for awscc_apigateway_api_key with name attribute---**********")
    results = await search_awscc_provider_docs_impl("awscc_apigateway_api_key", "name")
    
    logger.info(f"Found {len(results)} results")
    for i, result in enumerate(results):
        logger.info(f"\nResult {i+1}:")
        logger.info(f"  Resource Name: {result.resource_name}")
        logger.info(f"  Kind: {result.kind}")
        if result.description:
            description_preview = result.description[:100] + "..." if len(result.description) > 100 else result.description
            logger.info(f"  Description: {description_preview}")
    
    # Test case 3: Specifying resource kind
    logger.info("**********---Test case 3: Searching for AWSCC resource with specific kind---**********")
    results = await search_awscc_provider_docs_impl("awscc_apigateway_api_key", None, "resource")
    
    logger.info(f"Found {len(results)} results")
    for i, result in enumerate(results):
        logger.info(f"\nResult {i+1}:")
        logger.info(f"  Resource Name: {result.resource_name}")
        logger.info(f"  Kind: {result.kind}")
        if result.description:
            description_preview = result.description[:100] + "..." if len(result.description) > 100 else result.description
            logger.info(f"  Description: {description_preview}")
    
    # Test case 4: Specifying data source kind
    logger.info("**********---Test case 4: Searching for AWSCC data source with specific kind---**********")
    results = await search_awscc_provider_docs_impl("awscc_apigateway_api_key", None, "data_source")
    
    logger.info(f"Found {len(results)} results")
    for i, result in enumerate(results):
        logger.info(f"\nResult {i+1}:")
        logger.info(f"  Resource Name: {result.resource_name}")
        logger.info(f"  Kind: {result.kind}")
        if result.description:
            description_preview = result.description[:100] + "..." if len(result.description) > 100 else result.description
            logger.info(f"  Description: {description_preview}")
    
    # Test case 5: Searching for both kinds
    logger.info("**********---Test case 5: Searching for AWSCC resource with both kinds---**********")
    results = await search_awscc_provider_docs_impl("awscc_apigateway_api_key", None, "both")
    
    logger.info(f"Found {len(results)} results")
    for i, result in enumerate(results):
        logger.info(f"\nResult {i+1}:")
        logger.info(f"  Resource Name: {result.resource_name}")
        logger.info(f"  Kind: {result.kind}")
        if result.description:
            description_preview = result.description[:100] + "..." if len(result.description) > 100 else result.description
            logger.info(f"  Description: {description_preview}")
    
    # Test case 6: Non-existent resource
    logger.info("**********---Test case 6: Searching for non-existent resource---**********")
    results = await search_awscc_provider_docs_impl("awscc_nonexistent_resource")
    for i, result in enumerate(results):
        logger.info(f"\nResult {i+1}:")
        logger.info(f"  Resource Name: {result.resource_name}")
        if result.description:
            logger.info(f"  Description: {result.description}")

    # Test case 7: lambda_function resource
    logger.info("**********---Test case 7: Searching for lambda_function resource---**********")
    results = await search_awscc_provider_docs_impl("lambda_function", kind="resource")
    for i, result in enumerate(results):
        logger.info(f"\nResult {i+1}:")
        logger.info(f"  Resource Name: {result.resource_name}")
        if result.description:
            logger.info(f"  Description: {result.description}")


async def test_search_specific_aws_ia_modules():
    """Test the AWS IA modules search function."""
    logger.info("\n=== Testing search_specific_aws_ia_modules_impl ===")
    
    # Test case 1: Search all modules
    logger.info("Test case 1: Searching all AWS IA modules")
    results = await search_specific_aws_ia_modules_impl("")
    
    logger.info(f"Found {len(results)} modules")
    for i, result in enumerate(results):
        logger.info(f"\nModule {i+1}:")
        logger.info(f"  Name: {result.name}")
        logger.info(f"  Namespace: {result.namespace}")
        logger.info(f"  Description: {result.description[:100]}..." if result.description else "  No description")
        logger.info(f"  URL: {result.url}")
    
    # Test case 2: Search with query
    logger.info("\nTest case 2: Searching for 'bedrock' modules")
    results = await search_specific_aws_ia_modules_impl("bedrock")
    
    logger.info(f"Found {len(results)} modules")
    for i, result in enumerate(results):
        logger.info(f"\nModule {i+1}:")
        logger.info(f"  Name: {result.name}")
        logger.info(f"  Namespace: {result.namespace}")
        logger.info(f"  Description: {result.description[:100]}..." if result.description else "  No description")


async def test_execute_terraform_command():
    """Test the Terraform command execution function.
    
    Note: This test requires a valid Terraform configuration in a temporary directory.
    Skip this test if you don't have a valid Terraform configuration to test with.
    """
    logger.info("\n=== Testing execute_terraform_command_impl ===")
    logger.info("Skipping actual execution as it requires a valid Terraform configuration.")
    logger.info("To test this function, you would need to:")
    logger.info("1. Create a temporary directory with valid Terraform files")
    logger.info("2. Run terraform init, plan, etc. on those files")
    
    # Example of how you would call it (commented out)
    """
    request = TerraformExecutionRequest(
        command="validate",
        working_directory="/path/to/terraform/config",
        variables={"environment": "test"},
        aws_region="us-west-2",
        strip_ansi=True
    )
    
    result = await execute_terraform_command_impl(request)
    logger.info(f"Command: {result.command}")
    logger.info(f"Status: {result.status}")
    logger.info(f"Return Code: {result.return_code}")
    if result.stdout:
        logger.info(f"Stdout: {result.stdout[:100]}...")
    if result.stderr:
        logger.info(f"Stderr: {result.stderr[:100]}...")
    """


async def test_run_checkov_scan():
    """Test the Checkov scan function.
    
    Note: This test requires a valid Terraform configuration in a temporary directory.
    Skip this test if you don't have a valid Terraform configuration to test with.
    """
    logger.info("\n=== Testing run_checkov_scan_impl ===")
    logger.info("Skipping actual execution as it requires a valid Terraform configuration.")
    logger.info("To test this function, you would need to:")
    logger.info("1. Create a temporary directory with valid Terraform files")
    logger.info("2. Run Checkov on those files")
    
    # Example of how you would call it (commented out)
    """
    request = CheckovScanRequest(
        working_directory="/path/to/terraform/config",
        framework="terraform",
        output_format="json",
        auto_fix=False
    )
    
    result = await run_checkov_scan_impl(request)
    logger.info(f"Status: {result.status}")
    logger.info(f"Return Code: {result.return_code}")
    logger.info(f"Found {len(result.vulnerabilities)} vulnerabilities")
    for i, vuln in enumerate(result.vulnerabilities[:3]):  # Show first 3 only
        logger.info(f"\nVulnerability {i+1}:")
        logger.info(f"  ID: {vuln.id}")
        logger.info(f"  Resource: {vuln.resource}")
        logger.info(f"  Description: {vuln.description[:100]}..." if vuln.description else "  No description")
    """


def format_json(obj: Any) -> str:
    """Format an object as pretty JSON."""
    if hasattr(obj, "model_dump"):
        # For Pydantic v2
        data = obj.model_dump()
    elif hasattr(obj, "dict"):
        # For Pydantic v1
        data = obj.dict()
    else:
        data = obj
    return json.dumps(data, indent=2, default=str)


async def main():
    """Run all tests."""
    try:
        # await test_search_aws_provider_docs()
        await test_search_awscc_provider_docs()
        # await test_search_specific_aws_ia_modules()
        # Commented out as they require terraform configurations
        # await test_execute_terraform_command()
        # await test_run_checkov_scan()
    except Exception as e:
        logger.exception(f"Error running tests: {e}")


if __name__ == "__main__":
    asyncio.run(main())
