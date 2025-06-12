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

import pytest
from awslabs.cdk_mcp_server.data.solutions_constructs_parser import (
    extract_code_example,
    extract_default_settings,
    extract_description,
    extract_properties,
    extract_props,
    extract_props_markdown,
    extract_services_from_pattern_name,
    extract_use_cases,
    fetch_pattern_list,
    get_all_patterns_info,
    get_pattern_info,
    get_pattern_raw,
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

```typescript
import { Construct } from 'constructs';
import { Stack, StackProps } from 'aws-cdk-lib';
import { LambdaToDynamoDB } from '@aws-solutions-constructs/aws-lambda-dynamodb';

export class MyStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    new LambdaToDynamoDB(this, 'LambdaToDynamoDBPattern', {
      lambdaFunctionProps: {
        runtime: lambda.Runtime.NODEJS_18_X,
        handler: 'index.handler',
        code: lambda.Code.fromAsset(`${__dirname}/lambda`)
      },
      dynamoTableProps: {
        partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING }
      }
    });
  }
}
```
"""

# Sample AsciiDoc content for testing
SAMPLE_ADOC = """
//!!NODE_ROOT <section>
//== aws-alb-lambda module

[.topic]
= aws-alb-lambda
:info_doctype: section
:info_title: aws-alb-lambda

= Overview

This AWS Solutions Construct implements an an Application Load Balancer
to an AWS Lambda function

Here is a minimal deployable pattern definition:

====
[role="tablist"]
Typescript::
+
[source,typescript]
----
import { Construct } from 'constructs';
import { Stack, StackProps } from 'aws-cdk-lib';
import { AlbToLambda, AlbToLambdaProps } from '@aws-solutions-constructs/aws-alb-lambda';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as lambda from 'aws-cdk-lib/aws-lambda';
----
====
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


@pytest.mark.asyncio
async def test_get_pattern_info_with_adoc():
    """Test getting pattern info with AsciiDoc content."""
    # Mock the httpx.AsyncClient.get method directly
    with patch('httpx.AsyncClient.get') as mock_get:
        # First response for README.adoc
        adoc_response = AsyncMock()
        adoc_response.status_code = 200
        adoc_response.text = SAMPLE_ADOC

        # Set up the mock to return the adoc response
        mock_get.return_value = adoc_response

        info = await get_pattern_info('aws-alb-lambda')
        assert info['pattern_name'] == 'aws-alb-lambda'
        assert 'Application Load Balancer' in info['services']
        assert 'Lambda' in info['services']
        assert 'description' in info
        assert (
            'This AWS Solutions Construct implements an an Application Load Balancer to an AWS Lambda function'
            in info['description']
        )


@pytest.mark.asyncio
async def test_get_pattern_info_not_found():
    """Test getting pattern info when pattern is not found."""
    # Mock the httpx.AsyncClient.get method directly
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        info = await get_pattern_info('non-existent-pattern')
        assert 'error' in info
        assert 'status_code' in info
        assert info['status_code'] == 404


@pytest.mark.asyncio
async def test_get_pattern_raw():
    """Test getting raw pattern content."""
    # Mock the httpx.AsyncClient.get method directly
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_README
        mock_get.return_value = mock_response

        result = await get_pattern_raw('aws-lambda-dynamodb')
        assert result['status'] == 'success'
        assert result['pattern_name'] == 'aws-lambda-dynamodb'
        assert 'Lambda' in result['services']
        assert 'DynamoDB' in result['services']
        assert result['content'] == SAMPLE_README
        assert 'message' in result


@pytest.mark.asyncio
async def test_get_pattern_raw_not_found():
    """Test getting raw pattern content when pattern is not found."""
    # Mock the httpx.AsyncClient.get method directly
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = await get_pattern_raw('non-existent-pattern')
        assert 'error' in result
        assert 'status_code' in result
        assert result['status_code'] == 404


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


def test_extract_description_from_adoc():
    """Test extracting description from AsciiDoc content."""
    description = extract_description(SAMPLE_ADOC)
    assert (
        'This AWS Solutions Construct implements an an Application Load Balancer to an AWS Lambda function'
        in description
    )


def test_extract_props_markdown():
    """Test extracting props markdown from README content."""
    props_markdown = extract_props_markdown(SAMPLE_README)
    assert '| Name | Description |' in props_markdown
    assert (
        '| `lambdaFunctionProps` | Properties for the Lambda function. Defaults to `lambda.FunctionProps()`. |'
        in props_markdown
    )
    assert (
        '| `dynamoTableProps` | Properties for the DynamoDB table. Required. |' in props_markdown
    )


def test_extract_props_markdown_not_found():
    """Test extracting props markdown when not found."""
    props_markdown = extract_props_markdown('# Test\n\nNo props section here.')
    assert props_markdown == 'No props section found'


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


def test_extract_code_example():
    """Test extracting code example from README content."""
    code_example = extract_code_example(SAMPLE_README)
    assert 'import { Construct } from' in code_example
    assert 'new LambdaToDynamoDB(' in code_example
    assert 'lambdaFunctionProps:' in code_example


def test_extract_code_example_not_found():
    """Test extracting code example when not found."""
    code_example = extract_code_example('# Test\n\nNo code example here.')
    assert code_example == 'No code example available'


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


@pytest.mark.asyncio
async def test_search_patterns_error():
    """Test searching patterns with an error."""
    # Mock the search_utils.search_items_with_terms function to raise an exception
    with patch(
        'awslabs.cdk_mcp_server.data.solutions_constructs_parser.search_utils.search_items_with_terms'
    ) as mock_search:
        mock_search.side_effect = Exception('Test error')

        results = await search_patterns(['lambda', 'dynamodb'])
        assert len(results) == 0


@pytest.mark.asyncio
async def test_get_all_patterns_info():
    """Test getting info for all patterns."""
    # Mock fetch_pattern_list to return a list of patterns
    with patch(
        'awslabs.cdk_mcp_server.data.solutions_constructs_parser.fetch_pattern_list'
    ) as mock_fetch:
        mock_fetch.return_value = ['aws-lambda-dynamodb', 'aws-apigateway-lambda']

        # Mock get_pattern_info to return consistent data
        with patch(
            'awslabs.cdk_mcp_server.data.solutions_constructs_parser.get_pattern_info'
        ) as mock_get_info:
            mock_get_info.side_effect = [
                {
                    'pattern_name': 'aws-lambda-dynamodb',
                    'services': ['Lambda', 'DynamoDB'],
                    'description': 'Test description 1',
                },
                {
                    'pattern_name': 'aws-apigateway-lambda',
                    'services': ['API Gateway', 'Lambda'],
                    'description': 'Test description 2',
                },
            ]

            results = await get_all_patterns_info()
            assert len(results) == 2
            assert results[0]['pattern_name'] == 'aws-lambda-dynamodb'
            assert results[1]['pattern_name'] == 'aws-apigateway-lambda'


@pytest.mark.asyncio
async def test_get_all_patterns_info_with_error():
    """Test getting info for all patterns with an error for one pattern."""
    # Mock fetch_pattern_list to return a list of patterns
    with patch(
        'awslabs.cdk_mcp_server.data.solutions_constructs_parser.fetch_pattern_list'
    ) as mock_fetch:
        mock_fetch.return_value = ['aws-lambda-dynamodb', 'aws-apigateway-lambda']

        # Mock get_pattern_info to return data for first pattern and raise exception for second
        with patch(
            'awslabs.cdk_mcp_server.data.solutions_constructs_parser.get_pattern_info'
        ) as mock_get_info:
            mock_get_info.side_effect = [
                {
                    'pattern_name': 'aws-lambda-dynamodb',
                    'services': ['Lambda', 'DynamoDB'],
                    'description': 'Test description 1',
                },
                Exception('Test error'),
            ]

            results = await get_all_patterns_info()
            assert len(results) == 2
            assert results[0]['pattern_name'] == 'aws-lambda-dynamodb'
            assert 'error' in results[1]
            assert results[1]['pattern_name'] == 'aws-apigateway-lambda'


@pytest.mark.asyncio
async def test_get_all_patterns_info_with_fetch_error():
    """Test getting info for all patterns with an error in fetch_pattern_list."""
    # Mock fetch_pattern_list to raise an exception
    with patch(
        'awslabs.cdk_mcp_server.data.solutions_constructs_parser.fetch_pattern_list'
    ) as mock_fetch:
        mock_fetch.side_effect = Exception('Test error')

        results = await get_all_patterns_info()
        assert len(results) == 0
