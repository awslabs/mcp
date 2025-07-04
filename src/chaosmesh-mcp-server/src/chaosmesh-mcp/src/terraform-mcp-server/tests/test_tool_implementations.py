"""Tests for the tool implementations of the terraform-mcp-server."""

import asyncio
import json
import pytest
import sys
from awslabs.terraform_mcp_server.impl.tools.search_aws_provider_docs import (
    search_aws_provider_docs_impl,
)
from awslabs.terraform_mcp_server.impl.tools.search_awscc_provider_docs import (
    search_awscc_provider_docs_impl,
)
from awslabs.terraform_mcp_server.impl.tools.search_specific_aws_ia_modules import (
    search_specific_aws_ia_modules_impl,
)
from loguru import logger
from typing import Any


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


def print_aws_provider_results(results):
    """Print formatted results data using the provided logger.

    Args:
        results: List of result objects containing asset information
        logger: Logger object to use for output
    """
    logger.info(f'Found {len(results)} results')

    for i, result in enumerate(results):
        logger.info(f'\nResult {i + 1}:')
        logger.info(f'  Asset Name: {result.asset_name}')
        logger.info(f'  Asset Type: {result.asset_type}')
        logger.info(f'  URL: {result.url}')

        # Handle description
        if result.description:
            description_preview = (
                result.description[:50] + '...'
                if len(result.description) > 50
                else result.description
            )
            logger.info(f'  Description: {description_preview}')
        else:
            logger.info('  No description')

        # Handle example usage
        if result.example_usage:
            logger.info(f'  Example Usage: {len(result.example_usage)} found')

        # Handle arguments
        if result.arguments:
            logger.info(f'  Arguments: {len(result.arguments)} found')

        # Handle attributes
        if result.attributes:
            logger.info(f'  Attributes: {len(result.attributes)} found')


def print_awscc_provider_results(results):
    """Print formatted results data using the provided logger.

    Args:
        results: List of result objects containing asset information
        logger: Logger object to use for output
    """
    logger.info(f'Found {len(results)} results')

    for i, result in enumerate(results):
        logger.info(f'\nResult {i + 1}:')
        logger.info(f'  Asset Name: {result.asset_name}')
        logger.info(f'  Asset Type: {result.asset_type}')
        logger.info(f'  URL: {result.url}')

        # Handle description
        if result.description:
            description_preview = (
                result.description[:50] + '...'
                if len(result.description) > 50
                else result.description
            )
            logger.info(f'  Description: {description_preview}')
        else:
            logger.info('  No description')

        # Handle example usage
        if result.example_usage:
            logger.info(f'  Example Usage: {len(result.example_usage)} found')

        # Handle schema arguments
        if result.schema_arguments:
            logger.info(f'  Schema arguments: {len(result.schema_arguments)} found')


async def test_search_aws_provider_docs():
    """Test the AWS provider docs search function."""
    logger.info('=== Testing search_aws_provider_docs_impl ===')

    # Test case 1: Common resource with just 1 example snippet
    logger.info('**********---Test case 1: Searching for aws_s3_bucket as a resource---**********')
    results = await search_aws_provider_docs_impl('aws_s3_bucket', 'resource')
    print_aws_provider_results(results)

    # Test case 2: Common resource with multiple example snippets
    logger.info(
        '**********---Test case 2: Searching for aws_api_gateway_rest_api as a resource---**********'
    )
    results = await search_aws_provider_docs_impl('api_gateway_rest_api', 'resource')
    print_aws_provider_results(results)

    # Test case 3: Common resource with multiple example snippets and multiple arguments in subsections
    logger.info(
        '**********---Test case 3: Searching for aws_lambda_function as a resource---**********'
    )
    results = await search_aws_provider_docs_impl('aws_lambda_function', 'resource')
    print_aws_provider_results(results)

    # Test case 4: Specifying data source as asset type
    logger.info(
        '**********---Test case 4: Searching for aws_lambda_function as a data source ---**********'
    )
    results = await search_aws_provider_docs_impl('aws_lambda_function', 'data_source')
    print_aws_provider_results(results)

    # Test case 5: Searching for both kinds
    logger.info('**********---Test case 5: Searching for aws_dynamodb_table as both ---**********')
    results = await search_aws_provider_docs_impl('aws_dynamodb_table', 'both')
    print_aws_provider_results(results)

    # Test case 6: Non-existent resource
    logger.info('**********---Test case 6: Searching for non-existent resource---**********')
    results = await search_aws_provider_docs_impl('aws_nonexistent_resource')
    print_aws_provider_results(results)


async def test_search_awscc_provider_docs():
    """Test the AWSCC provider docs search function."""
    logger.info('\n=== Testing search_awscc_provider_docs_impl ===')

    # Test case 1: Common resource
    logger.info(
        '**********---Test case 1: Searching for awscc_apigateway_api_key as a resource---**********'
    )
    results = await search_awscc_provider_docs_impl('awscc_apigateway_api_key', 'resource')
    print_awscc_provider_results(results)

    # Test case 2: Resource with attribute
    logger.info(
        '**********---Test case 2: Searching for awscc_apigateway_api_key as a data source---**********'
    )
    results = await search_awscc_provider_docs_impl('awscc_apigateway_api_key', 'data_source')
    print_awscc_provider_results(results)

    # Test case 3: lambda_function resource
    logger.info(
        '**********---Test case 7: Searching for lambda_function as a resource---**********'
    )
    results = await search_awscc_provider_docs_impl('lambda_function', 'resource')
    print_awscc_provider_results(results)

    # Test case 4: Searching for both kinds
    logger.info(
        '**********---Test case 4: Searching for lambda_function as both kinds---**********'
    )
    results = await search_awscc_provider_docs_impl('awscc_lambda_function', 'both')
    print_awscc_provider_results(results)

    # Test case 5: Non-existent resource
    logger.info('**********---Test case 5: Searching for non-existent resource---**********')
    results = await search_awscc_provider_docs_impl('awscc_nonexistent_resource')
    print_awscc_provider_results(results)


async def test_search_specific_aws_ia_modules():
    """Test the AWS IA modules search function."""
    logger.info('\n=== Testing search_specific_aws_ia_modules_impl ===')

    # Test case 1: Search all modules
    logger.info('Test case 1: Searching all AWS IA modules')
    results = await search_specific_aws_ia_modules_impl('')

    logger.info(f'Found {len(results)} modules')
    for i, result in enumerate(results):
        logger.info(f'\nModule {i + 1}:')
        logger.info(f'  Name: {result.name}')
        logger.info(f'  Namespace: {result.namespace}')
        logger.info(
            f'  Description: {result.description[:100]}...'
            if result.description
            else '  No description'
        )
        logger.info(f'  URL: {result.url}')

    # Test case 2: Search with query
    logger.info("\nTest case 2: Searching for 'bedrock' modules")
    results = await search_specific_aws_ia_modules_impl('bedrock')

    logger.info(f'Found {len(results)} modules')
    for i, result in enumerate(results):
        logger.info(f'\nModule {i + 1}:')
        logger.info(f'  Name: {result.name}')
        logger.info(f'  Namespace: {result.namespace}')
        logger.info(
            f'  Description: {result.description[:100]}...'
            if result.description
            else '  No description'
        )


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


async def main():
    """Run all tests."""
    try:
        await test_search_aws_provider_docs()
        await test_search_awscc_provider_docs()
    except Exception as e:
        logger.exception(f'Error running tests: {e}')


if __name__ == '__main__':
    asyncio.run(main())
