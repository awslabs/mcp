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
"""Tests for AWS Location Service MCP Server."""

import os
import pytest
from unittest.mock import MagicMock, patch

import boto3
import botocore.exceptions

from awslabs.aws_location_server.server import search_places, get_coordinates, LocationClient


@pytest.mark.asyncio
async def test_search_places(mock_boto3_client, mock_context):
    """Test the search_places tool."""
    # Set up test data
    query = "Seattle"
    max_results = 5
    
    # Call the function
    with patch('awslabs.aws_location_server.server.location_client.location_client', mock_boto3_client):
        result = await search_places(mock_context, query=query, max_results=max_results)
    
    # Verify the result
    assert result['query'] == query
    assert len(result['places']) == 1
    assert result['places'][0]['name'] == 'Seattle, WA, USA'
    assert result['places'][0]['coordinates']['longitude'] == -122.3321
    assert result['places'][0]['coordinates']['latitude'] == 47.6062
    
    # Verify the boto3 client was called correctly
    mock_boto3_client.search_place_index_for_text.assert_called_once_with(
        IndexName='ExamplePlaceIndex',
        Text=query,
        MaxResults=max_results
    )


@pytest.mark.asyncio
async def test_get_coordinates(mock_boto3_client, mock_context):
    """Test the get_coordinates tool."""
    # Set up test data
    location = "Seattle"
    
    # Call the function
    with patch('awslabs.aws_location_server.server.location_client.location_client', mock_boto3_client):
        result = await get_coordinates(mock_context, location=location)
    
    # Verify the result
    assert result['location'] == location
    assert result['formatted_address'] == 'Seattle, WA, USA'
    assert result['coordinates']['longitude'] == -122.3321
    assert result['coordinates']['latitude'] == 47.6062
    assert result['country'] == 'USA'
    assert result['region'] == 'Washington'
    assert result['municipality'] == 'Seattle'
    
    # Verify the boto3 client was called correctly
    mock_boto3_client.search_place_index_for_text.assert_called_once_with(
        IndexName='ExamplePlaceIndex',
        Text=location,
        MaxResults=1
    )


@pytest.mark.asyncio
async def test_search_places_error(mock_context):
    """Test the search_places tool with an error."""
    # Set up test data
    query = "Seattle"
    
    # Mock boto3 client to raise an exception
    mock_client = MagicMock()
    error_response = {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Place index not found'}}
    mock_client.search_place_index_for_text.side_effect = botocore.exceptions.ClientError(
        error_response, 'SearchPlaceIndexForText'
    )
    
    # Call the function
    with patch('awslabs.aws_location_server.server.location_client.location_client', mock_client):
        result = await search_places(mock_context, query=query)
    
    # Verify the result contains an error
    assert 'error' in result
    assert 'place index not found' in result['error'].lower()
    
    # Verify the context.error was called
    mock_context.error.assert_called_once()


@pytest.mark.asyncio
async def test_get_coordinates_no_results(mock_context):
    """Test the get_coordinates tool with no results."""
    # Set up test data
    location = "NonexistentPlace"
    
    # Mock boto3 client to return no results
    mock_client = MagicMock()
    mock_client.search_place_index_for_text.return_value = {'Results': []}
    
    # Call the function
    with patch('awslabs.aws_location_server.server.location_client.location_client', mock_client):
        result = await get_coordinates(mock_context, location=location)
    
    # Verify the result contains an error
    assert 'error' in result
    assert 'no results found' in result['error'].lower()
    
    # Verify the context.error was called
    mock_context.error.assert_called_once()


def test_location_client_initialization():
    """Test the LocationClient initialization."""
    # Test with environment variables
    with patch.dict(os.environ, {
        'AWS_REGION': 'us-west-2',
        'AWS_ACCESS_KEY_ID': 'test-key',
        'AWS_SECRET_ACCESS_KEY': 'test-secret',
        'AWS_LOCATION_PLACE_INDEX': 'TestPlaceIndex'
    }):
        with patch('boto3.client') as mock_boto3_client:
            client = LocationClient()
            
            # Verify the client was initialized with the correct parameters
            mock_boto3_client.assert_called_once()
            args, kwargs = mock_boto3_client.call_args
            assert args[0] == 'location'
            assert kwargs['region_name'] == 'us-west-2'
            assert kwargs['aws_access_key_id'] == 'test-key'
            assert kwargs['aws_secret_access_key'] == 'test-secret'
            assert client.default_place_index == 'TestPlaceIndex'
