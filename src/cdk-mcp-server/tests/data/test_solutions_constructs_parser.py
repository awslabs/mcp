import pytest
from awslabs.cdk_mcp_server.data.solutions_constructs_parser import (
    extract_default_settings,
    extract_description,
    extract_properties,
    extract_props,
    extract_services_from_pattern_name,
    extract_use_cases,
    fetch_pattern_list,
    get_pattern_info,
    parse_readme_content,
    search_patterns,
)
from unittest.mock import AsyncMock, MagicMock, patch


# Test data
SAMPLE_README = """
# aws-lambda-dynamodb

This pattern creates a Lambda function that is triggered by API Gateway and writes to DynamoDB.

## Description
This pattern creates a Lambda function that is triggered by API Gateway and writes to DynamoDB. It includes all necessary permissions and configurations.

## Pattern Construct Props

| Name | Description |
|------|-------------|
| `lambdaFunctionProps` | Properties for the Lambda function. Defaults to `lambda.FunctionProps()`. |
| `dynamoTableProps` | Properties for the DynamoDB table. Required. |
| `apiGatewayProps` | Properties for the API Gateway. Optional. |

## Pattern Properties

| Name | Description |
|------|-------------|
| `lambdaFunction` | The Lambda function. Access via `pattern.lambdaFunction`. |
| `dynamoTable` | The DynamoDB table. Access via `pattern.dynamoTable`. |
| `apiGateway` | The API Gateway. Access via `pattern.apiGateway`. |

## Default Settings
* Lambda function with Node.js 18 runtime
* DynamoDB table with on-demand capacity
* API Gateway with default settings

## Use Cases
* Building serverless APIs with DynamoDB backend
* Creating data processing pipelines
* Implementing REST APIs with persistent storage
"""


@pytest.mark.asyncio
async def test_fetch_pattern_list():
    """Test fetching pattern list."""
    # Create a mock response with a regular method (not a coroutine)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {'name': 'aws-lambda-dynamodb', 'type': 'dir'},
        {'name': 'aws-apigateway-lambda', 'type': 'dir'},
        {'name': 'core', 'type': 'dir'},  # Should be filtered out
    ]

    # Create a mock client context manager
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_response

    # Mock the httpx.AsyncClient constructor
    with patch('httpx.AsyncClient', return_value=mock_client):
        # Reset the cache to ensure we're not using cached data
        from awslabs.cdk_mcp_server.data.solutions_constructs_parser import _pattern_list_cache

        _pattern_list_cache['timestamp'] = None
        _pattern_list_cache['data'] = []

        # Call the function
        patterns = await fetch_pattern_list()

        # Verify the results
        assert len(patterns) == 2
        assert 'aws-lambda-dynamodb' in patterns
        assert 'aws-apigateway-lambda' in patterns
        assert 'core' not in patterns


@pytest.mark.asyncio
async def test_get_pattern_info():
    """Test getting pattern info."""
    # Mock the httpx.AsyncClient.get method directly
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_README
        mock_get.return_value = mock_response

        info = await get_pattern_info('aws-lambda-dynamodb')
        assert info['pattern_name'] == 'aws-lambda-dynamodb'
        assert 'Lambda' in info['services']
        assert 'DynamoDB' in info['services']
        assert 'description' in info
        assert 'use_cases' in info


def test_extract_services_from_pattern_name():
    """Test extracting services from pattern name."""
    services = extract_services_from_pattern_name('aws-lambda-dynamodb')
    assert services == ['Lambda', 'DynamoDB']

    services = extract_services_from_pattern_name('aws-apigateway-lambda')
    assert services == ['API Gateway', 'Lambda']

    services = extract_services_from_pattern_name('aws-s3-lambda')
    assert services == ['S3', 'Lambda']


def test_extract_description():
    """Test extracting description from README content."""
    description = extract_description(SAMPLE_README)
    assert 'creates a Lambda function' in description
    assert 'triggered by API Gateway' in description


def test_extract_props():
    """Test extracting props from README content."""
    props = extract_props(SAMPLE_README)
    assert 'lambdaFunctionProps' in props
    assert 'dynamoTableProps' in props
    assert 'apiGatewayProps' in props
    assert props['dynamoTableProps']['required'] is True
    assert props['apiGatewayProps']['required'] is False


def test_extract_properties():
    """Test extracting properties from README content."""
    properties = extract_properties(SAMPLE_README)
    assert 'lambdaFunction' in properties
    assert 'dynamoTable' in properties
    assert 'apiGateway' in properties
    assert properties['lambdaFunction']['access_method'] == 'pattern.lambdaFunction'


def test_extract_default_settings():
    """Test extracting default settings from README content."""
    defaults = extract_default_settings(SAMPLE_README)
    assert len(defaults) == 3
    assert 'Lambda function with Node.js 18 runtime' in defaults
    assert 'DynamoDB table with on-demand capacity' in defaults


def test_extract_use_cases():
    """Test extracting use cases from README content."""
    use_cases = extract_use_cases(SAMPLE_README)
    assert len(use_cases) == 3
    assert 'Building serverless APIs with DynamoDB backend' in use_cases
    assert 'Creating data processing pipelines' in use_cases


def test_parse_readme_content():
    """Test parsing complete README content."""
    result = parse_readme_content('aws-lambda-dynamodb', SAMPLE_README)
    assert result['pattern_name'] == 'aws-lambda-dynamodb'
    assert 'Lambda' in result['services']
    assert 'DynamoDB' in result['services']
    assert 'description' in result
    assert 'props' in result
    assert 'properties' in result
    assert 'default_settings' in result
    assert 'use_cases' in result


@pytest.mark.asyncio
async def test_search_patterns():
    """Test searching patterns by services."""
    # Mock the search_utils.search_items_with_terms function to control the search results
    with patch(
        'awslabs.cdk_mcp_server.data.solutions_constructs_parser.search_utils.search_items_with_terms'
    ) as mock_search:
        # Set up the mock to return only one matching pattern
        mock_search.return_value = [
            {'item': 'aws-lambda-dynamodb', 'matched_terms': ['lambda', 'dynamodb']}
        ]

        # Mock get_pattern_info to return consistent data
        with patch(
            'awslabs.cdk_mcp_server.data.solutions_constructs_parser.get_pattern_info'
        ) as mock_get_info:
            mock_get_info.return_value = {
                'pattern_name': 'aws-lambda-dynamodb',
                'services': ['Lambda', 'DynamoDB'],
                'description': 'Test description',
            }

            results = await search_patterns(['lambda', 'dynamodb'])
            assert len(results) == 1
            assert results[0]['pattern_name'] == 'aws-lambda-dynamodb'
            assert 'Lambda' in results[0]['services']
            assert 'DynamoDB' in results[0]['services']
