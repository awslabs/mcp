"""Integration tests for the server module."""

import asyncio
import json
import os
import pytest
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport


# Load environment variables from .env file
load_dotenv()


def create_mcp_client():
    """Create an MCP client with proper environment variable passing.

    This helper function ensures that AWS credentials and other environment
    variables are properly passed to the MCP server subprocess, which is
    especially important on Windows where subprocess environment inheritance
    can be problematic.

    Returns:
        Client: Configured FastMCP client with proper environment variables
    """
    # Get AWS and Storage Lens environment variables
    aws_env = {k: v for k, v in os.environ.items() if k.startswith(('AWS_', 'STORAGE_LENS_'))}

    transport = PythonStdioTransport(
        script_path='awslabs/aws_finops_mcp_server/server.py', env=aws_env
    )

    return Client(transport)


async def _test_cost_explorer_get_cost_and_usage():
    """Test the cost_explorer_get_cost_and_usage tool using the MCP client."""
    # Calculate date range for the last 3 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # 3 months ago

    # Format dates as YYYY-MM-DD
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    # Use the client with proper environment variable passing
    async with create_mcp_client() as client:
        # Call the cost_explorer_get_cost_and_usage tool
        response = await client.call_tool(
            'ce_get_cost_usage',
            {
                'params': {
                    'TimePeriod': {'Start': start_date_str, 'End': end_date_str},
                    'Granularity': 'MONTHLY',
                    'Metrics': ['BlendedCost'],
                }
            },
        )

        # Print the raw response for debugging
        print('\n=== Cost Explorer Response ===')
        print(f'Response type: {type(response)}')
        print(f'Response content: {response}')

        # Safety checks before accessing response
        assert response is not None, 'Response should not be None'

        # Extract the text content from the response
        assert hasattr(response, 'content'), "Response should have 'content' attribute"
        assert len(response.content) > 0, 'Response content should not be empty'
        assert hasattr(response.content[0], 'text'), (
            "Response content item should have 'text' attribute"
        )

        text_content = response.content[0].text
        result = json.loads(text_content)

        # Print the parsed result
        print('\n=== Parsed Cost Explorer Result ===')
        print(json.dumps(result, indent=2))

        # Verify the result structure
        assert 'ResultsByTime' in result
        return True


async def _test_storage_lens_run_query():
    """Test the storage_lens_run_query tool using the MCP client."""
    # Get manifest location from environment variable
    manifest_location = os.environ.get('STORAGE_LENS_MANIFEST_LOCATION')
    if not manifest_location:
        return 'SKIP: STORAGE_LENS_MANIFEST_LOCATION environment variable not set'

    # Define test query
    query = "SELECT storage_class, SUM(CAST(metric_value AS DOUBLE)) as total_bytes FROM {table} WHERE metric_name = 'StorageBytes' GROUP BY storage_class"

    # Use the client with proper environment variable passing
    async with create_mcp_client() as client:
        # Call the storage_lens_run_query tool with only the query parameter
        response = await client.call_tool(
            'storage_lens_run_query',
            {'query': query},
        )

        # Print the raw response for debugging
        print('\n=== Storage Lens Response ===')
        print(f'Response type: {type(response)}')
        print(f'Response content: {response}')

        # Safety checks before accessing response
        assert response is not None, 'Response should not be None'

        # Extract the text content from the response
        assert hasattr(response, 'content'), "Response should have 'content' attribute"
        assert len(response.content) > 0, 'Response content should not be empty'
        assert hasattr(response.content[0], 'text'), (
            "Response content item should have 'text' attribute"
        )

        text_content = response.content[0].text
        result = json.loads(text_content)

        # Print the parsed result
        print('\n=== Parsed Storage Lens Result ===')
        print(json.dumps(result, indent=2))

        # Verify the result structure
        assert 'rows' in result
        assert 'statistics' in result
        assert 'query' in result
        assert 'manifest_location' in result
        assert 'data_location' in result
        return True


async def _test_prompt_registration():
    """Test that prompts are correctly registered and accessible."""
    # Use the client with proper environment variable passing
    async with create_mcp_client() as client:
        # Get the available prompts
        prompts = await client.list_prompts()

        # Print the prompts for debugging
        print('\n=== Available Prompts ===')
        for prompt in prompts:
            print(f'- {prompt.name}: {prompt.description}')

        # Check that our prompts are in the list
        prompt_names = [p.name for p in prompts]
        assert 'analyze_graviton_opportunities' in prompt_names
        assert 'analyze_savings_plans_opportunities' in prompt_names
        return True


async def _test_graviton_prompt_execution():
    """Test that the Graviton migration prompt can be executed."""
    # Use the client with proper environment variable passing
    async with create_mcp_client() as client:
        # Call the prompt with string arguments
        response = await client.get_prompt(
            'analyze_graviton_opportunities',
            {
                'account_ids': '123456789012',  # Single account as string
                'lookback_days': '7',  # String
                'region': 'us-west-2',  # String
            },
        )

        # Print the raw response for debugging
        print('\n=== Graviton Prompt Response ===')
        print(f'Response type: {type(response)}')
        print(f'Response content: {response}')

        # Check that we got a response
        assert response is not None, 'Response should not be None'

        # Check that the response has messages
        assert hasattr(response, 'messages'), 'Response should have messages attribute'
        assert len(response.messages) > 0, 'Response should have at least one message'

        # Check that the first message contains the expected content
        first_message = response.messages[0]
        message_text = (
            first_message.content.text
            if hasattr(first_message.content, 'text')
            else str(first_message.content)
        )
        assert '123456789012' in message_text
        assert 'compute_optimizer_get_ec2_instance_recommendations' in message_text
        return True


async def _test_savings_plans_prompt_execution():
    """Test that the Savings Plans prompt can be executed."""
    # Use the client with proper environment variable passing
    async with create_mcp_client() as client:
        # Call the prompt with string arguments
        response = await client.get_prompt(
            'analyze_savings_plans_opportunities',
            {
                'account_ids': '123456789012',  # Single account as string
                'lookback_days': '60',  # String
                'term_in_years': '3',  # String
            },
        )

        # Print the raw response for debugging
        print('\n=== Savings Plans Prompt Response ===')
        print(f'Response type: {type(response)}')
        print(f'Response content: {response}')

        # Check that we got a response
        assert response is not None, 'Response should not be None'

        # Check that the response has messages
        assert hasattr(response, 'messages'), 'Response should have messages attribute'
        assert len(response.messages) > 0, 'Response should have at least one message'

        # Check that the first message contains the expected content
        first_message = response.messages[0]
        message_text = (
            first_message.content.text
            if hasattr(first_message.content, 'text')
            else str(first_message.content)
        )
        assert '123456789012' in message_text
        assert 'cost_explorer_get_savings_plans_purchase_recommendation' in message_text
        return True


@pytest.mark.integration
def test_cost_explorer_get_cost_and_usage():
    """Run the cost explorer test using asyncio.run()."""
    try:
        result = asyncio.run(_test_cost_explorer_get_cost_and_usage())
        assert result is True
    except ClientError as e:
        # If we get an access denied error, we'll skip the test
        if e.response['Error']['Code'] in ['AccessDenied', 'UnauthorizedOperation']:
            pytest.skip(f"AWS credentials don't have permission: {str(e)}")
        else:
            raise


@pytest.mark.integration
def test_storage_lens_run_query():
    """Run the storage lens test using asyncio.run()."""
    try:
        result = asyncio.run(_test_storage_lens_run_query())
        if result == 'SKIP: STORAGE_LENS_MANIFEST_LOCATION environment variable not set':
            pytest.skip(result)
        assert result is True
    except ClientError as e:
        # If we get an access denied error or the bucket doesn't exist, we'll skip the test
        if e.response['Error']['Code'] in [
            'AccessDenied',
            'UnauthorizedOperation',
            'NoSuchBucket',
        ]:
            pytest.skip(f"AWS credentials don't have permission or bucket doesn't exist: {str(e)}")
        else:
            raise


@pytest.mark.integration
def test_prompt_registration():
    """Test that prompts are correctly registered and accessible."""
    result = asyncio.run(_test_prompt_registration())
    assert result is True


@pytest.mark.integration
def test_graviton_prompt_execution():
    """Test that the Graviton migration prompt can be executed."""
    result = asyncio.run(_test_graviton_prompt_execution())
    assert result is True


@pytest.mark.integration
def test_savings_plans_prompt_execution():
    """Test that the Savings Plans prompt can be executed."""
    result = asyncio.run(_test_savings_plans_prompt_execution())
    assert result is True
