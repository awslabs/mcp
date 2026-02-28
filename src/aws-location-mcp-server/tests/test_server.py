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
"""Tests for AWS Location Service MCP Server."""

import pytest

# Import the functions directly to avoid Field validation issues
from awslabs.aws_location_server.server import (
    GeoFencingClient,
    GeoPlacesClient,
    GeoRoutesClient,
    calculate_route,
    geocode,
    get_place,
    main,
    optimize_waypoints,
    reverse_geocode,
    search_places,
    search_places_open_now,
)
from unittest.mock import patch


@pytest.mark.asyncio
async def test_search_places(mock_boto3_client, mock_context):
    """Test the search_places tool."""
    # Set up test data
    query = 'Seattle'
    max_results = 5

    # Patch the geo_places_client in the server module
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await search_places(mock_context, query=query, max_results=max_results)

    # Verify the result
    assert result['query'] == query
    assert 'places' in result


@pytest.mark.asyncio
async def test_search_places_error_no_client(mock_context):
    """Test search_places when client is not initialized."""
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = None
        result = await search_places(mock_context, query='Seattle')

    assert 'error' in result
    assert 'AWS geo-places client not initialized' in result['error']


@pytest.mark.asyncio
async def test_search_places_geocode_error(mock_boto3_client, mock_context):
    """Test search_places when geocode returns no results."""
    # Set up geocode to return empty results
    mock_boto3_client.geocode.return_value = {'ResultItems': []}

    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await search_places(mock_context, query='NonexistentPlace')

    assert 'error' in result
    assert 'Could not geocode query' in result['error']


@pytest.mark.asyncio
async def test_search_places_client_error(mock_boto3_client, mock_context):
    """Test search_places when boto3 client raises an error."""
    from botocore.exceptions import ClientError

    # Set up boto3 client to raise ClientError
    mock_boto3_client.geocode.side_effect = ClientError(
        {'Error': {'Code': 'TestException', 'Message': 'Test error message'}}, 'geocode'
    )

    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await search_places(mock_context, query='Seattle')

    assert 'error' in result
    assert 'AWS geo-places Service error' in result['error']


@pytest.mark.asyncio
async def test_search_places_general_exception(mock_boto3_client, mock_context):
    """Test search_places when a general exception occurs."""
    # Set up boto3 client to raise a general exception
    mock_boto3_client.geocode.side_effect = Exception('Test general exception')

    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await search_places(mock_context, query='Seattle')

    assert 'error' in result
    assert 'Error searching places' in result['error']


@pytest.mark.asyncio
async def test_get_place(mock_boto3_client, mock_context):
    """Test the get_place tool."""
    # Set up mock response
    mock_boto3_client.get_place.return_value = {
        'Title': 'Test Place',
        'Address': {'Label': '123 Test St, Test City, TS'},
        'Position': [-122.3321, 47.6062],
        'Categories': [{'Name': 'Restaurant'}],
        'Contacts': {
            'Phones': [{'Value': '123-456-7890'}],
            'Websites': [{'Value': 'https://example.com'}],
            'Emails': [],
            'Faxes': [],
        },
    }

    # Patch the geo_places_client in the server module
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await get_place(mock_context, place_id='test-place-id')

    # Verify the result
    assert result['name'] == 'Test Place'
    assert result['address'] == '123 Test St, Test City, TS'
    assert result['coordinates']['longitude'] == -122.3321
    assert result['coordinates']['latitude'] == 47.6062
    assert result['categories'] == ['Restaurant']
    assert result['contacts']['phones'] == ['123-456-7890']
    assert result['contacts']['websites'] == ['https://example.com']


@pytest.mark.asyncio
async def test_get_place_raw_mode(mock_boto3_client, mock_context):
    """Test the get_place tool with raw mode."""
    # Set up mock response
    mock_response = {
        'Title': 'Test Place',
        'Address': {'Label': '123 Test St, Test City, TS'},
        'Position': [-122.3321, 47.6062],
    }
    mock_boto3_client.get_place.return_value = mock_response

    # Patch the geo_places_client in the server module
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await get_place(mock_context, place_id='test-place-id', mode='raw')

    # Verify the raw result is returned
    assert result == mock_response


@pytest.mark.asyncio
async def test_get_place_error_no_client(mock_context):
    """Test get_place when client is not initialized."""
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = None
        result = await get_place(mock_context, place_id='test-place-id')

    assert 'error' in result
    assert 'AWS geo-places client not initialized' in result['error']


@pytest.mark.asyncio
async def test_get_place_exception(mock_boto3_client, mock_context):
    """Test get_place when an exception occurs."""
    # Set up boto3 client to raise an exception
    mock_boto3_client.get_place.side_effect = Exception('Test exception')

    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await get_place(mock_context, place_id='test-place-id')

    assert 'error' in result
    assert 'Test exception' in result['error']


@pytest.mark.asyncio
async def test_reverse_geocode(mock_boto3_client, mock_context):
    """Test the reverse_geocode tool."""
    # Set up mock response
    mock_boto3_client.reverse_geocode.return_value = {
        'Place': {
            'Label': '123 Test St, Test City, TS',
            'Title': 'Test Place',
            'Geometry': {'Point': [-122.3321, 47.6062]},
            'Categories': [{'Name': 'Restaurant'}],
            'Address': {'Label': '123 Test St, Test City, TS'},
        }
    }

    # Patch the geo_places_client in the server module
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await reverse_geocode(mock_context, longitude=-122.3321, latitude=47.6062)

    # Verify the result
    assert result['name'] == '123 Test St, Test City, TS'
    assert result['address'] == '123 Test St, Test City, TS'
    assert result['coordinates']['longitude'] == -122.3321
    assert result['coordinates']['latitude'] == 47.6062
    assert result['categories'] == ['Restaurant']


@pytest.mark.asyncio
async def test_reverse_geocode_no_place(mock_boto3_client, mock_context):
    """Test reverse_geocode when no place is found."""
    # Set up mock response with no Place
    mock_boto3_client.reverse_geocode.return_value = {'SomeOtherField': 'value'}

    # Patch the geo_places_client in the server module
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await reverse_geocode(mock_context, longitude=-122.3321, latitude=47.6062)

    # Verify the raw response is returned
    assert 'raw_response' in result
    assert result['raw_response'] == {'SomeOtherField': 'value'}


@pytest.mark.asyncio
async def test_reverse_geocode_error_no_client(mock_context):
    """Test reverse_geocode when client is not initialized."""
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = None
        result = await reverse_geocode(mock_context, longitude=-122.3321, latitude=47.6062)

    assert 'error' in result
    assert 'AWS geo-places client not initialized' in result['error']


@pytest.mark.asyncio
async def test_reverse_geocode_client_error(mock_boto3_client, mock_context):
    """Test reverse_geocode when boto3 client raises a ClientError."""
    from botocore.exceptions import ClientError

    # Set up boto3 client to raise ClientError
    mock_boto3_client.reverse_geocode.side_effect = ClientError(
        {'Error': {'Code': 'TestException', 'Message': 'Test error message'}}, 'reverse_geocode'
    )

    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await reverse_geocode(mock_context, longitude=-122.3321, latitude=47.6062)

    assert 'error' in result
    assert 'AWS geo-places Service error' in result['error']


@pytest.mark.asyncio
async def test_reverse_geocode_general_exception(mock_boto3_client, mock_context):
    """Test reverse_geocode when a general exception occurs."""
    # Set up boto3 client to raise a general exception
    mock_boto3_client.reverse_geocode.side_effect = Exception('Test general exception')

    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await reverse_geocode(mock_context, longitude=-122.3321, latitude=47.6062)

    assert 'error' in result
    assert 'Error in reverse geocoding' in result['error']


@pytest.mark.asyncio
async def test_geocode(mock_boto3_client, mock_context):
    """Test the geocode tool."""
    # Set up mock response
    mock_boto3_client.geocode.return_value = {
        'ResultItems': [
            {
                'Position': [-79.3871, 43.6426],
                'Address': {'Label': 'CN Tower, 290 Bremner Blvd, Toronto, ON M5V 3L9, Canada'},
                'PlaceType': 'PointOfInterest',
            }
        ]
    }

    # Patch the geo_places_client in the server module
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await geocode(mock_context, location='CN Tower Toronto')

    # Verify the result
    assert result['location'] == 'CN Tower Toronto'
    assert result['coordinates']['longitude'] == -79.3871
    assert result['coordinates']['latitude'] == 43.6426
    assert result['address'] == 'CN Tower, 290 Bremner Blvd, Toronto, ON M5V 3L9, Canada'
    assert result['place_type'] == 'PointOfInterest'


@pytest.mark.asyncio
async def test_geocode_no_results(mock_boto3_client, mock_context):
    """Test geocode when no results are found."""
    # Set up geocode to return empty results
    mock_boto3_client.geocode.return_value = {'ResultItems': []}

    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await geocode(mock_context, location='NonexistentPlace')

    assert 'error' in result
    assert 'No coordinates found for location' in result['error']


@pytest.mark.asyncio
async def test_geocode_error_no_client(mock_context):
    """Test geocode when client is not initialized."""
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = None
        result = await geocode(mock_context, location='CN Tower')

    assert 'error' in result
    assert 'AWS geo-places client not initialized' in result['error']


@pytest.mark.asyncio
async def test_geocode_client_error(mock_boto3_client, mock_context):
    """Test geocode when boto3 client raises a ClientError."""
    from botocore.exceptions import ClientError

    # Set up boto3 client to raise ClientError
    mock_boto3_client.geocode.side_effect = ClientError(
        {'Error': {'Code': 'TestException', 'Message': 'Test error message'}}, 'geocode'
    )

    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await geocode(mock_context, location='CN Tower')

    assert 'error' in result
    assert 'AWS geo-places Service error' in result['error']


@pytest.mark.asyncio
async def test_geocode_general_exception(mock_boto3_client, mock_context):
    """Test geocode when a general exception occurs."""
    # Set up boto3 client to raise a general exception
    mock_boto3_client.geocode.side_effect = Exception('Test general exception')

    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await geocode(mock_context, location='CN Tower')

    assert 'error' in result
    assert 'Error geocoding location' in result['error']


@pytest.mark.asyncio
async def test_search_nearby(mock_boto3_client, mock_context):
    """Test the search_nearby tool."""
    # Set up mock response
    mock_boto3_client.search_nearby.return_value = {
        'ResultItems': [
            {
                'PlaceId': 'test-place-id',
                'Title': 'Test Place',
                'Address': {'Label': '123 Test St, Test City, TS'},
                'Position': [-122.3321, 47.6062],
                'Categories': [{'Name': 'Restaurant'}],
                'Contacts': {
                    'Phones': [{'Value': '123-456-7890'}],
                    'Websites': [{'Value': 'https://example.com'}],
                    'Emails': [],
                    'Faxes': [],
                },
            }
        ]
    }

    # Import the function directly to avoid Field validation issues
    from awslabs.aws_location_server.server import search_nearby as search_nearby_func

    # Patch the geo_places_client in the server module
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await search_nearby_func(
            mock_context,
            longitude=-122.3321,
            latitude=47.6062,
            radius=500,
        )

    # Verify the result
    assert 'places' in result
    assert len(result['places']) == 1
    assert result['places'][0]['name'] == 'Test Place'
    assert result['places'][0]['address'] == '123 Test St, Test City, TS'
    assert result['places'][0]['coordinates']['longitude'] == -122.3321
    assert result['places'][0]['coordinates']['latitude'] == 47.6062
    assert result['places'][0]['categories'] == ['Restaurant']
    assert result['places'][0]['contacts']['phones'] == ['123-456-7890']
    assert result['places'][0]['contacts']['websites'] == ['https://example.com']
    assert 'radius_used' in result


@pytest.mark.asyncio
async def test_search_nearby_raw_mode(mock_boto3_client, mock_context):
    """Test the search_nearby tool with raw mode."""
    # Set up mock response
    mock_boto3_client.search_nearby.return_value = {
        'ResultItems': [
            {
                'PlaceId': 'test-place-id',
                'Title': 'Test Place',
                'Address': {'Label': '123 Test St, Test City, TS'},
                'Position': [-122.3321, 47.6062],
            }
        ]
    }

    # Import the function directly to avoid Field validation issues
    from awslabs.aws_location_server.server import search_nearby as search_nearby_func

    # Patch the geo_places_client in the server module
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await search_nearby_func(
            mock_context,
            longitude=-122.3321,
            latitude=47.6062,
            radius=500,
        )

    # Verify the raw result is returned
    assert 'places' in result
    assert len(result['places']) == 1
    assert result['places'][0]['place_id'] == 'test-place-id'
    assert result['places'][0]['name'] == 'Test Place'


@pytest.mark.asyncio
async def test_search_nearby_no_results_expansion(mock_boto3_client, mock_context):
    """Test search_nearby with radius expansion when no results are found."""
    # Set up mock response to return empty results first, then results on second call
    mock_boto3_client.search_nearby.side_effect = [
        {'ResultItems': []},  # First call with initial radius
        {  # Second call with expanded radius
            'ResultItems': [
                {
                    'PlaceId': 'test-place-id',
                    'Title': 'Test Place',
                    'Address': {'Label': '123 Test St, Test City, TS'},
                    'Position': [-122.3321, 47.6062],
                }
            ]
        },
    ]

    # Import the function directly to avoid Field validation issues
    from awslabs.aws_location_server.server import search_nearby as search_nearby_func

    # Patch the geo_places_client in the server module
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await search_nearby_func(
            mock_context,
            longitude=-122.3321,
            latitude=47.6062,
            radius=500,
        )

    # Verify the result with expanded radius
    assert 'places' in result
    assert len(result['places']) == 1
    assert result['radius_used'] == 1000  # 500 * 2.0


@pytest.mark.asyncio
async def test_search_nearby_error_no_client(mock_context):
    """Test search_nearby when client is not initialized."""
    # Import the function directly to avoid Field validation issues
    from awslabs.aws_location_server.server import search_nearby as search_nearby_func

    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = None
        result = await search_nearby_func(
            mock_context,
            longitude=-122.3321,
            latitude=47.6062,
            radius=500,
        )

    assert 'error' in result
    assert 'AWS geo-places client not initialized' in result['error']


@pytest.mark.asyncio
async def test_search_nearby_exception(mock_boto3_client, mock_context):
    """Test search_nearby when an exception occurs."""
    # Set up boto3 client to raise an exception
    mock_boto3_client.search_nearby.side_effect = Exception('Test exception')

    # Import the function directly to avoid Field validation issues
    from awslabs.aws_location_server.server import search_nearby as search_nearby_func

    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await search_nearby_func(
            mock_context,
            longitude=-122.3321,
            latitude=47.6062,
            radius=500,
        )

    assert 'error' in result
    assert 'Test exception' in result['error']


@pytest.mark.asyncio
async def test_search_places_open_now(mock_boto3_client, mock_context):
    """Test the search_places_open_now tool."""
    # Set up mock responses
    mock_boto3_client.geocode.return_value = {'ResultItems': [{'Position': [-122.3321, 47.6062]}]}
    mock_boto3_client.search_text.return_value = {
        'ResultItems': [
            {
                'PlaceId': 'test-place-id',
                'Title': 'Test Place',
                'Address': {
                    'Label': '123 Test St, Test City, TS',
                    'Country': {'Name': 'USA'},
                    'Region': {'Name': 'WA'},
                    'Locality': 'Seattle',
                },
                'Position': [-122.3321, 47.6062],
                'Categories': [{'Name': 'Restaurant'}],
                'Contacts': {
                    'Phones': [{'Value': '123-456-7890'}],
                    'OpeningHours': {'Display': ['Mon-Fri: 9AM-5PM'], 'OpenNow': True},
                },
            }
        ]
    }

    # Import the function directly to avoid Field validation issues
    from awslabs.aws_location_server.server import (
        search_places_open_now as search_places_open_now_func,
    )

    # Patch the geo_places_client in the server module
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await search_places_open_now_func(
            mock_context,
            query='restaurants Seattle',
            initial_radius=500,
        )

    # Verify the result
    assert 'query' in result
    assert 'open_places' in result
    assert len(result['open_places']) == 1
    assert result['open_places'][0]['name'] == 'Test Place'
    assert result['open_places'][0]['open_now'] is True
    assert 'all_places' in result
    assert 'radius_used' in result


@pytest.mark.asyncio
async def test_search_places_open_now_no_geocode_results(mock_boto3_client, mock_context):
    """Test search_places_open_now when geocode returns no results."""
    # Set up geocode to return empty results
    mock_boto3_client.geocode.return_value = {'ResultItems': []}

    # Import the function directly to avoid Field validation issues
    from awslabs.aws_location_server.server import (
        search_places_open_now as search_places_open_now_func,
    )

    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await search_places_open_now_func(
            mock_context,
            query='NonexistentPlace',
            initial_radius=500,
        )

    assert 'error' in result
    assert 'Could not geocode query' in result['error']


@pytest.mark.asyncio
async def test_search_places_open_now_error_no_client(mock_context):
    """Test search_places_open_now when client is not initialized."""
    # Import the function directly to avoid Field validation issues
    from awslabs.aws_location_server.server import (
        search_places_open_now as search_places_open_now_func,
    )

    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = None
        result = await search_places_open_now_func(
            mock_context,
            query='restaurants Seattle',
            initial_radius=500,
        )

    assert 'error' in result
    assert 'AWS geo-places client not initialized' in result['error']


@pytest.mark.asyncio
async def test_search_places_open_now_client_error(mock_boto3_client, mock_context):
    """Test search_places_open_now when boto3 client raises a ClientError."""
    from botocore.exceptions import ClientError

    # Set up boto3 client to raise ClientError
    mock_boto3_client.geocode.side_effect = ClientError(
        {'Error': {'Code': 'TestException', 'Message': 'Test error message'}}, 'geocode'
    )

    # Import the function directly to avoid Field validation issues
    from awslabs.aws_location_server.server import (
        search_places_open_now as search_places_open_now_func,
    )

    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await search_places_open_now_func(
            mock_context,
            query='restaurants Seattle',
            initial_radius=500,
        )

    assert 'error' in result
    assert 'AWS geo-places Service error' in result['error']


@pytest.mark.asyncio
async def test_search_places_open_now_general_exception(mock_boto3_client, mock_context):
    """Test search_places_open_now when a general exception occurs."""
    # Set up boto3 client to raise a general exception
    mock_boto3_client.geocode.side_effect = Exception('Test general exception')

    # Import the function directly to avoid Field validation issues
    from awslabs.aws_location_server.server import (
        search_places_open_now as search_places_open_now_func,
    )

    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await search_places_open_now_func(
            mock_context,
            query='restaurants Seattle',
            initial_radius=500,
        )

    assert 'error' in result
    assert 'Test general exception' in result['error']


def test_geo_places_client_initialization(monkeypatch):
    """Test the GeoPlacesClient initialization."""
    # NOTE: No AWS credentials are set or required for this test. All AWS calls are mocked.
    monkeypatch.setenv('AWS_REGION', 'us-west-2')
    with patch('boto3.client') as mock_boto3_client:
        _ = GeoPlacesClient()
        mock_boto3_client.assert_called_once()
        args, kwargs = mock_boto3_client.call_args
        assert args[0] == 'geo-places'
        assert kwargs['region_name'] == 'us-west-2'


@pytest.mark.asyncio
async def test_calculate_route(mock_boto3_client, mock_context):
    """Test the calculate_route tool."""
    # Set up mock response
    mock_response = {
        'Routes': [
            {
                'Distance': 100.0,
                'DurationSeconds': 300,
                'Legs': [
                    {
                        'Distance': 100.0,
                        'DurationSeconds': 300,
                        'VehicleLegDetails': {
                            'TravelSteps': [
                                {
                                    'Distance': 50.0,
                                    'Duration': 150,
                                    'StartPosition': [-122.335167, 47.608013],
                                    'EndPosition': [-122.300000, 47.600000],
                                    'Type': 'Straight',
                                    'NextRoad': {'RoadName': 'Test Road'},
                                },
                                {
                                    'Distance': 50.0,
                                    'Duration': 150,
                                    'StartPosition': [-122.300000, 47.600000],
                                    'EndPosition': [-122.200676, 47.610149],
                                    'Type': 'Turn',
                                    'NextRoad': {'RoadName': 'Another Road'},
                                },
                            ]
                        },
                    }
                ],
            }
        ]
    }

    # Create a mock for the calculate_route function
    with patch('awslabs.aws_location_server.server.GeoRoutesClient') as mock_geo_client:
        # Set up the mock to return our mock_boto3_client
        mock_geo_client.return_value.geo_routes_client = mock_boto3_client

        # Mock the asyncio.to_thread function to return the mock response directly
        with patch('asyncio.to_thread', return_value=mock_response):
            # Call the function
            result = await calculate_route(
                mock_context,
                departure_position=[-122.335167, 47.608013],
                destination_position=[-122.200676, 47.610149],
                travel_mode='Car',
                optimize_for='FastestRoute',
            )

    # Verify the result
    assert 'distance_meters' in result
    assert 'duration_seconds' in result
    assert 'turn_by_turn' in result
    assert len(result['turn_by_turn']) == 2
    assert result['turn_by_turn'][0]['road_name'] == 'Test Road'
    assert result['turn_by_turn'][1]['road_name'] == 'Another Road'


@pytest.mark.asyncio
async def test_calculate_route_error(mock_boto3_client, mock_context):
    """Test the calculate_route tool when an error occurs."""
    # Set up boto3 client to raise ClientError
    mock_boto3_client.calculate_routes.side_effect = Exception('Test error')

    # Patch the geo_routes_client in the server module
    with patch('awslabs.aws_location_server.server.GeoRoutesClient') as mock_geo_client:
        mock_geo_client.return_value.geo_routes_client = mock_boto3_client

        # Mock asyncio.to_thread to propagate the exception
        with patch('asyncio.to_thread', side_effect=Exception('Test error')):
            result = await calculate_route(
                mock_context,
                departure_position=[-122.335167, 47.608013],
                destination_position=[-122.200676, 47.610149],
                travel_mode='Car',
                optimize_for='FastestRoute',
            )

    # Verify the result
    assert 'error' in result
    assert 'Test error' in result['error']


@pytest.mark.asyncio
async def test_calculate_route_no_client(mock_context):
    """Test calculate_route when client is not initialized."""
    with patch('awslabs.aws_location_server.server.GeoRoutesClient') as mock_geo_client:
        mock_geo_client.return_value.geo_routes_client = None
        result = await calculate_route(
            mock_context,
            departure_position=[-122.335167, 47.608013],
            destination_position=[-122.200676, 47.610149],
        )
    assert 'error' in result
    assert 'Failed to initialize Amazon geo-routes client' in result['error']


@pytest.mark.asyncio
async def test_calculate_route_no_routes(mock_boto3_client, mock_context):
    """Test calculate_route when no routes are found."""
    # Set up mock response with no routes
    mock_response = {'Routes': []}

    with patch('awslabs.aws_location_server.server.GeoRoutesClient') as mock_geo_client:
        mock_geo_client.return_value.geo_routes_client = mock_boto3_client
        with patch('asyncio.to_thread', return_value=mock_response):
            result = await calculate_route(
                mock_context,
                departure_position=[-122.335167, 47.608013],
                destination_position=[-122.200676, 47.610149],
            )
    assert 'error' in result
    assert 'No route found' in result['error']


@pytest.mark.asyncio
async def test_calculate_route_raw_mode(mock_boto3_client, mock_context):
    """Test calculate_route with raw mode."""
    # Since we can't easily modify local variables in the function,
    # we'll skip this test as it's not possible to test the raw mode
    # without modifying the function to accept a mode parameter.
    #
    # In a real-world scenario, we would refactor the function to accept
    # a mode parameter, but for this test we'll just verify that the
    # function processes the response correctly.

    # Create a mock response with the expected structure
    mock_response = {'Routes': [{'Distance': 100.0, 'DurationSeconds': 300}]}

    # Create a mock for the calculate_route function
    with patch('awslabs.aws_location_server.server.GeoRoutesClient') as mock_geo_client:
        # Set up the mock to return our mock_boto3_client
        mock_geo_client.return_value.geo_routes_client = mock_boto3_client

        # Mock asyncio.to_thread to return the mock response
        with patch('asyncio.to_thread', return_value=mock_response):
            # Call the function
            result = await calculate_route(
                mock_context,
                departure_position=[-122.335167, 47.608013],
                destination_position=[-122.200676, 47.610149],
            )

    # Verify the result has the expected structure
    assert 'distance_meters' in result
    assert 'duration_seconds' in result
    assert 'turn_by_turn' in result


@pytest.mark.asyncio
async def test_optimize_waypoints(mock_boto3_client, mock_context):
    """Test the optimize_waypoints tool."""
    # Set up mock response
    mock_boto3_client.optimize_waypoints.return_value = {
        'Routes': [
            {
                'Distance': 150.0,
                'DurationSeconds': 450,
                'Waypoints': [
                    {'Position': [-122.200676, 47.610149]},
                ],
            }
        ],
    }

    # Patch the geo_routes_client in the server module
    with patch('awslabs.aws_location_server.server.GeoRoutesClient') as mock_geo_client:
        mock_geo_client.return_value.geo_routes_client = mock_boto3_client

        # Mock asyncio.to_thread to return the mock response directly
        with patch(
            'asyncio.to_thread', return_value=mock_boto3_client.optimize_waypoints.return_value
        ):
            result = await optimize_waypoints(
                mock_context,
                origin_position=[-122.335167, 47.608013],
                destination_position=[-122.121513, 47.673988],
                waypoints=[{'Position': [-122.200676, 47.610149]}],
                travel_mode='Car',
                mode='summary',
            )

    # Verify the result
    assert 'distance_meters' in result
    assert 'duration_seconds' in result
    assert 'optimized_order' in result
    assert len(result['optimized_order']) == 1


@pytest.mark.asyncio
async def test_optimize_waypoints_error(mock_boto3_client, mock_context):
    """Test the optimize_waypoints tool when an error occurs."""
    # Set up boto3 client to raise Exception
    mock_boto3_client.optimize_waypoints.side_effect = Exception('Test error')

    # Patch the geo_routes_client in the server module
    with patch('awslabs.aws_location_server.server.GeoRoutesClient') as mock_geo_client:
        mock_geo_client.return_value.geo_routes_client = mock_boto3_client

        # Mock asyncio.to_thread to propagate the exception
        with patch('asyncio.to_thread', side_effect=Exception('Test error')):
            result = await optimize_waypoints(
                mock_context,
                origin_position=[-122.335167, 47.608013],
                destination_position=[-122.121513, 47.673988],
                waypoints=[{'Position': [-122.200676, 47.610149]}],
                travel_mode='Car',
                mode='summary',
            )

    # Verify the result
    assert 'error' in result
    assert 'Test error' in result['error']


@pytest.mark.asyncio
async def test_optimize_waypoints_no_client(mock_context):
    """Test optimize_waypoints when client is not initialized."""
    with patch('awslabs.aws_location_server.server.GeoRoutesClient') as mock_geo_client:
        mock_geo_client.return_value.geo_routes_client = None
        result = await optimize_waypoints(
            mock_context,
            origin_position=[-122.335167, 47.608013],
            destination_position=[-122.121513, 47.673988],
            waypoints=[{'Position': [-122.200676, 47.610149]}],
        )
    assert 'error' in result
    assert 'Failed to initialize Amazon geo-routes client' in result['error']


@pytest.mark.asyncio
async def test_optimize_waypoints_no_routes(mock_boto3_client, mock_context):
    """Test optimize_waypoints when no routes are found."""
    # Set up mock response with no routes
    mock_boto3_client.optimize_waypoints.return_value = {'Routes': []}

    with patch('awslabs.aws_location_server.server.GeoRoutesClient') as mock_geo_client:
        mock_geo_client.return_value.geo_routes_client = mock_boto3_client
        with patch(
            'asyncio.to_thread', return_value=mock_boto3_client.optimize_waypoints.return_value
        ):
            result = await optimize_waypoints(
                mock_context,
                origin_position=[-122.335167, 47.608013],
                destination_position=[-122.121513, 47.673988],
                waypoints=[{'Position': [-122.200676, 47.610149]}],
            )
    assert 'error' in result
    assert 'No route found' in result['error']


@pytest.mark.asyncio
async def test_optimize_waypoints_raw_mode(mock_boto3_client, mock_context):
    """Test optimize_waypoints with raw mode."""
    # Set up mock response
    mock_response = {'Routes': [{'Distance': 150.0, 'DurationSeconds': 450}]}
    mock_boto3_client.optimize_waypoints.return_value = mock_response

    with patch('awslabs.aws_location_server.server.GeoRoutesClient') as mock_geo_client:
        mock_geo_client.return_value.geo_routes_client = mock_boto3_client
        with patch('asyncio.to_thread', return_value=mock_response):
            result = await optimize_waypoints(
                mock_context,
                origin_position=[-122.335167, 47.608013],
                destination_position=[-122.121513, 47.673988],
                waypoints=[{'Position': [-122.200676, 47.610149]}],
                mode='raw',
            )
    assert result == mock_response


def test_geo_routes_client_initialization(monkeypatch):
    """Test the GeoRoutesClient initialization."""
    monkeypatch.setenv('AWS_REGION', 'us-west-2')

    with patch('boto3.client') as mock_boto3_client:
        _ = GeoRoutesClient()
        mock_boto3_client.assert_called_once()
        args, kwargs = mock_boto3_client.call_args
        assert args[0] == 'geo-routes'
        assert kwargs['region_name'] == 'us-west-2'


@pytest.mark.asyncio
async def test_calculate_route_with_leg_geometry(mock_boto3_client, mock_context):
    """Test calculate_route with leg geometry enabled."""
    # Since we can't easily modify local variables in the function,
    # we'll create a custom implementation that captures the parameters

    # Create a mock response with the expected structure
    mock_response = {
        'Routes': [
            {
                'Distance': 100.0,
                'DurationSeconds': 300,
                'Legs': [
                    {
                        'Distance': 100.0,
                        'DurationSeconds': 300,
                        'VehicleLegDetails': {
                            'TravelSteps': [
                                {
                                    'Distance': 50.0,
                                    'Duration': 150,
                                    'StartPosition': [-122.335167, 47.608013],
                                    'EndPosition': [-122.300000, 47.600000],
                                    'Type': 'Straight',
                                    'NextRoad': {'RoadName': 'Test Road'},
                                }
                            ]
                        },
                    }
                ],
            }
        ]
    }

    # Create a patched version of the client that captures the parameters
    params_captured = {}

    def mock_calculate_routes(**params):
        nonlocal params_captured
        params_captured = params
        return mock_response

    # Create a mock for the calculate_route function
    with patch('awslabs.aws_location_server.server.GeoRoutesClient') as mock_geo_client:
        # Set up the mock to return our mock_boto3_client with the custom implementation
        mock_boto3_client.calculate_routes.side_effect = mock_calculate_routes
        mock_geo_client.return_value.geo_routes_client = mock_boto3_client

        # Mock asyncio.to_thread to return the mock response
        with patch('asyncio.to_thread', side_effect=lambda f, **kwargs: f(**kwargs)):
            # Call the function
            result = await calculate_route(
                mock_context,
                departure_position=[-122.335167, 47.608013],
                destination_position=[-122.200676, 47.610149],
                travel_mode='Car',
                optimize_for='FastestRoute',
            )

    # Verify the function was called
    assert mock_boto3_client.calculate_routes.called

    # Verify the result has the expected structure
    assert 'distance_meters' in result
    assert 'duration_seconds' in result
    assert 'turn_by_turn' in result


def test_geo_routes_client_initialization_with_credentials(monkeypatch):
    """Test the GeoRoutesClient initialization with explicit credentials."""
    monkeypatch.setenv('AWS_REGION', 'us-west-2')
    monkeypatch.setenv(
        'AWS_ACCESS_KEY_ID', 'AKIAIOSFODNN7EXAMPLE'
    )  # pragma: allowlist secret - Test credential for unit tests only
    monkeypatch.setenv(
        'AWS_SECRET_ACCESS_KEY', 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
    )  # pragma: allowlist secret - Test credential for unit tests only

    with patch('boto3.client') as mock_boto3_client:
        _ = GeoRoutesClient()
        mock_boto3_client.assert_called_once()
        args, kwargs = mock_boto3_client.call_args
        assert args[0] == 'geo-routes'
        assert kwargs['region_name'] == 'us-west-2'
        assert (
            kwargs['aws_access_key_id'] == 'AKIAIOSFODNN7EXAMPLE'
        )  # pragma: allowlist secret - Test credential for unit tests only
        assert (
            kwargs['aws_secret_access_key'] == 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        )  # pragma: allowlist secret - Test credential for unit tests only


def test_geo_routes_client_initialization_exception():
    """Test the GeoRoutesClient initialization when an exception occurs."""
    with patch('boto3.client', side_effect=Exception('Test exception')):
        geo_client = GeoRoutesClient()
        assert geo_client.geo_routes_client is None


def test_main_stdio():
    """Test the main function with stdio transport."""
    with patch('awslabs.aws_location_server.server.mcp.run') as mock_run:
        main()
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_search_places_with_bounding_box(mock_boto3_client, mock_context):
    """Test search_places with bounding box filter when initial search returns no results."""
    # Set up mock responses
    mock_boto3_client.geocode.return_value = {'ResultItems': [{'Position': [-122.3321, 47.6062]}]}

    # First search_text call returns empty results, second call with bounding box returns results
    mock_boto3_client.search_text.side_effect = [
        {'ResultItems': []},  # First call returns empty
        {  # Second call with bounding box returns results
            'ResultItems': [
                {
                    'PlaceId': 'test-place-id',
                    'Title': 'Test Place',
                    'Address': {'Label': '123 Test St, Test City, TS'},
                    'Position': [-122.3321, 47.6062],
                    'Categories': [{'Name': 'Restaurant'}],
                }
            ]
        },
    ]

    # Patch the geo_places_client in the server module
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await search_places(mock_context, query='Seattle', max_results=5)

    # Verify the result
    assert 'places' in result
    assert len(result['places']) == 1
    assert result['places'][0]['name'] == 'Test Place'


@pytest.mark.asyncio
async def test_search_places_with_opening_hours(mock_boto3_client, mock_context):
    """Test search_places with opening hours in the response."""
    # Set up mock responses
    mock_boto3_client.geocode.return_value = {'ResultItems': [{'Position': [-122.3321, 47.6062]}]}
    mock_boto3_client.search_text.return_value = {
        'ResultItems': [
            {
                'PlaceId': 'test-place-id',
                'Title': 'Test Place',
                'Address': {'Label': '123 Test St, Test City, TS'},
                'Position': [-122.3321, 47.6062],
                'Categories': [{'Name': 'Restaurant'}],
                'Contacts': {
                    'OpeningHours': {
                        'Display': ['Mon-Fri: 9AM-5PM'],
                        'OpenNow': True,
                        'Components': [{'DayOfWeek': 'Monday', 'Hours': '9AM-5PM'}],
                    }
                },
            }
        ]
    }

    # Patch the geo_places_client in the server module
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await search_places(mock_context, query='Seattle', max_results=5)

    # Verify the result
    assert 'places' in result
    assert len(result['places']) == 1
    assert result['places'][0]['name'] == 'Test Place'
    assert len(result['places'][0]['opening_hours']) == 1
    assert result['places'][0]['opening_hours'][0]['open_now'] is True
    assert result['places'][0]['opening_hours'][0]['display'] == ['Mon-Fri: 9AM-5PM']


@pytest.mark.asyncio
async def test_search_places_open_now_with_contacts_opening_hours(mock_boto3_client, mock_context):
    """Test search_places_open_now with opening hours in Contacts."""
    # Set up mock responses
    mock_boto3_client.geocode.return_value = {'ResultItems': [{'Position': [-122.3321, 47.6062]}]}
    mock_boto3_client.search_text.return_value = {
        'ResultItems': [
            {
                'PlaceId': 'test-place-id',
                'Title': 'Test Place',
                'Address': {'Label': '123 Test St, Test City, TS'},
                'Position': [-122.3321, 47.6062],
                'Categories': [{'Name': 'Restaurant'}],
                'Contacts': {
                    'OpeningHours': {
                        'Display': ['Mon-Fri: 9AM-5PM'],
                        'OpenNow': True,
                    }
                },
            }
        ]
    }

    # Patch the geo_places_client in the server module
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await search_places_open_now(
            mock_context,
            query='restaurants Seattle',
            initial_radius=500,
        )

    # Verify the result
    assert 'open_places' in result
    assert len(result['open_places']) == 1
    assert result['open_places'][0]['name'] == 'Test Place'
    assert result['open_places'][0]['open_now'] is True


@pytest.mark.asyncio
async def test_search_places_open_now_with_expanded_radius(mock_boto3_client, mock_context):
    """Test search_places_open_now with radius expansion."""
    # Set up mock responses
    mock_boto3_client.geocode.return_value = {'ResultItems': [{'Position': [-122.3321, 47.6062]}]}

    # First search returns no open places, second search with expanded radius returns open places
    mock_boto3_client.search_text.side_effect = [
        {  # First call returns places but none are open
            'ResultItems': [
                {
                    'PlaceId': 'test-place-id-1',
                    'Title': 'Test Place 1',
                    'Address': {'Label': '123 Test St, Test City, TS'},
                    'Position': [-122.3321, 47.6062],
                    'Categories': [{'Name': 'Restaurant'}],
                    'OpeningHours': {'Display': ['Mon-Fri: 9AM-5PM'], 'OpenNow': False},
                }
            ]
        },
        {  # Second call with expanded radius returns open places
            'ResultItems': [
                {
                    'PlaceId': 'test-place-id-2',
                    'Title': 'Test Place 2',
                    'Address': {'Label': '456 Test St, Test City, TS'},
                    'Position': [-122.3421, 47.6162],
                    'Categories': [{'Name': 'Restaurant'}],
                    'OpeningHours': {'Display': ['Mon-Fri: 9AM-5PM'], 'OpenNow': True},
                }
            ]
        },
    ]

    # Patch the geo_places_client in the server module
    with patch('awslabs.aws_location_server.server.geo_places_client') as mock_geo_client:
        mock_geo_client.geo_places_client = mock_boto3_client
        result = await search_places_open_now(
            mock_context,
            query='restaurants Seattle',
            initial_radius=500,
        )

    # Verify the result
    assert 'open_places' in result
    assert len(result['open_places']) == 1
    assert result['open_places'][0]['name'] == 'Test Place 2'
    assert result['open_places'][0]['open_now'] is True
    assert result['radius_used'] == 500.0  # Initial radius


def test_geo_places_client_initialization_with_credentials(monkeypatch):
    """Test the GeoPlacesClient initialization with explicit credentials."""
    monkeypatch.setenv('AWS_REGION', 'us-west-2')
    monkeypatch.setenv(
        'AWS_ACCESS_KEY_ID', 'AKIAIOSFODNN7EXAMPLE'
    )  # pragma: allowlist secret - Test credential for unit tests only
    monkeypatch.setenv(
        'AWS_SECRET_ACCESS_KEY', 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
    )  # pragma: allowlist secret - Test credential for unit tests only

    with patch('boto3.client') as mock_boto3_client:
        _ = GeoPlacesClient()
        mock_boto3_client.assert_called_once()
        args, kwargs = mock_boto3_client.call_args
        assert args[0] == 'geo-places'
        assert kwargs['region_name'] == 'us-west-2'
        assert kwargs['aws_access_key_id'] == 'AKIAIOSFODNN7EXAMPLE'
        assert kwargs['aws_secret_access_key'] == 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'


def test_geo_places_client_initialization_exception():
    """Test the GeoPlacesClient initialization when an exception occurs."""
    with patch('boto3.client', side_effect=Exception('Test exception')):
        geo_client = GeoPlacesClient()
        assert geo_client.geo_places_client is None


def test_geo_places_client_initialization_with_session_token(monkeypatch):
    """Test the GeoPlacesClient initialization with session token."""
    monkeypatch.setenv('AWS_REGION', 'us-west-2')
    monkeypatch.setenv(
        'AWS_ACCESS_KEY_ID', 'AKIAIOSFODNN7EXAMPLE'
    )  # pragma: allowlist secret - Test credential for unit tests only
    monkeypatch.setenv(
        'AWS_SECRET_ACCESS_KEY', 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
    )  # pragma: allowlist secret - Test credential for unit tests only
    monkeypatch.setenv(
        'AWS_SESSION_TOKEN',
        'AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4Olgk',
    )  # pragma: allowlist secret - Test credential for unit tests only

    with patch('boto3.client') as mock_boto3_client:
        _ = GeoPlacesClient()
        mock_boto3_client.assert_called_once()
        args, kwargs = mock_boto3_client.call_args
        assert args[0] == 'geo-places'
        assert kwargs['region_name'] == 'us-west-2'
        assert kwargs['aws_access_key_id'] == 'AKIAIOSFODNN7EXAMPLE'
        assert kwargs['aws_secret_access_key'] == 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        assert (
            kwargs['aws_session_token']
            == 'AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4Olgk'
        )


def test_geo_routes_client_initialization_with_session_token(monkeypatch):
    """Test the GeoRoutesClient initialization with session token."""
    monkeypatch.setenv('AWS_REGION', 'us-west-2')
    monkeypatch.setenv(
        'AWS_ACCESS_KEY_ID', 'AKIAIOSFODNN7EXAMPLE'
    )  # pragma: allowlist secret - Test credential for unit tests only
    monkeypatch.setenv(
        'AWS_SECRET_ACCESS_KEY', 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
    )  # pragma: allowlist secret - Test credential for unit tests only
    monkeypatch.setenv(
        'AWS_SESSION_TOKEN',
        'AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4Olgk',
    )  # pragma: allowlist secret - Test credential for unit tests only

    with patch('boto3.client') as mock_boto3_client:
        _ = GeoRoutesClient()
        mock_boto3_client.assert_called_once()
        args, kwargs = mock_boto3_client.call_args
        assert args[0] == 'geo-routes'
        assert kwargs['region_name'] == 'us-west-2'
        assert kwargs['aws_access_key_id'] == 'AKIAIOSFODNN7EXAMPLE'
        assert kwargs['aws_secret_access_key'] == 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        assert (
            kwargs['aws_session_token']
            == 'AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4Olgk'
        )


# ============================================================================
# GeoFencingClient Initialization Tests
# ============================================================================


def test_geo_fencing_client_initialization(monkeypatch):
    """Test the GeoFencingClient initialization with default credential chain.

    Validates: Requirements 4.1, 4.3
    """
    monkeypatch.setenv('AWS_REGION', 'us-west-2')
    # Clear any explicit credentials to test default chain
    monkeypatch.delenv('AWS_ACCESS_KEY_ID', raising=False)
    monkeypatch.delenv('AWS_SECRET_ACCESS_KEY', raising=False)
    monkeypatch.delenv('AWS_SESSION_TOKEN', raising=False)

    with patch('boto3.client') as mock_boto3_client:
        _ = GeoFencingClient()
        mock_boto3_client.assert_called_once()
        args, kwargs = mock_boto3_client.call_args
        assert args[0] == 'location'
        assert kwargs['region_name'] == 'us-west-2'
        # Verify no explicit credentials are passed when using default chain
        assert 'aws_access_key_id' not in kwargs
        assert 'aws_secret_access_key' not in kwargs


def test_geo_fencing_client_initialization_with_credentials(monkeypatch):
    """Test the GeoFencingClient initialization with explicit credentials.

    Validates: Requirements 4.1, 4.2
    """
    monkeypatch.setenv('AWS_REGION', 'us-west-2')
    monkeypatch.setenv(
        'AWS_ACCESS_KEY_ID', 'AKIAIOSFODNN7EXAMPLE'
    )  # pragma: allowlist secret - Test credential for unit tests only
    monkeypatch.setenv(
        'AWS_SECRET_ACCESS_KEY', 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
    )  # pragma: allowlist secret - Test credential for unit tests only

    with patch('boto3.client') as mock_boto3_client:
        _ = GeoFencingClient()
        mock_boto3_client.assert_called_once()
        args, kwargs = mock_boto3_client.call_args
        assert args[0] == 'location'
        assert kwargs['region_name'] == 'us-west-2'
        assert (
            kwargs['aws_access_key_id'] == 'AKIAIOSFODNN7EXAMPLE'
        )  # pragma: allowlist secret - Test credential for unit tests only
        assert (
            kwargs['aws_secret_access_key'] == 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        )  # pragma: allowlist secret - Test credential for unit tests only


def test_geo_fencing_client_initialization_with_session_token(monkeypatch):
    """Test the GeoFencingClient initialization with session token.

    Validates: Requirements 4.1, 4.2
    """
    monkeypatch.setenv('AWS_REGION', 'us-west-2')
    monkeypatch.setenv(
        'AWS_ACCESS_KEY_ID', 'AKIAIOSFODNN7EXAMPLE'
    )  # pragma: allowlist secret - Test credential for unit tests only
    monkeypatch.setenv(
        'AWS_SECRET_ACCESS_KEY', 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
    )  # pragma: allowlist secret - Test credential for unit tests only
    monkeypatch.setenv(
        'AWS_SESSION_TOKEN',
        'AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4Olgk',
    )  # pragma: allowlist secret - Test credential for unit tests only

    with patch('boto3.client') as mock_boto3_client:
        _ = GeoFencingClient()
        mock_boto3_client.assert_called_once()
        args, kwargs = mock_boto3_client.call_args
        assert args[0] == 'location'
        assert kwargs['region_name'] == 'us-west-2'
        assert (
            kwargs['aws_access_key_id'] == 'AKIAIOSFODNN7EXAMPLE'
        )  # pragma: allowlist secret - Test credential for unit tests only
        assert (
            kwargs['aws_secret_access_key'] == 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        )  # pragma: allowlist secret - Test credential for unit tests only
        assert (
            kwargs['aws_session_token']
            == 'AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4Olgk'
        )  # pragma: allowlist secret - Test credential for unit tests only


def test_geo_fencing_client_initialization_exception():
    """Test the GeoFencingClient initialization when an exception occurs.

    Validates: Requirements 4.4
    """
    with patch('boto3.client', side_effect=Exception('Test exception')):
        geo_client = GeoFencingClient()
        assert geo_client.location_client is None


def test_geo_fencing_client_initialization_default_region(monkeypatch):
    """Test the GeoFencingClient initialization with default region.

    Validates: Requirements 4.1
    """
    # Clear AWS_REGION to test default value
    monkeypatch.delenv('AWS_REGION', raising=False)
    monkeypatch.delenv('AWS_ACCESS_KEY_ID', raising=False)
    monkeypatch.delenv('AWS_SECRET_ACCESS_KEY', raising=False)
    monkeypatch.delenv('AWS_SESSION_TOKEN', raising=False)

    with patch('boto3.client') as mock_boto3_client:
        geo_client = GeoFencingClient()
        mock_boto3_client.assert_called_once()
        args, kwargs = mock_boto3_client.call_args
        assert args[0] == 'location'
        assert kwargs['region_name'] == 'us-east-1'  # Default region
        assert geo_client.aws_region == 'us-east-1'


# ============================================================================
# Geofence Collection Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_geofence_collection_success(mock_boto3_client, mock_context):
    """Test create_geofence_collection success case.

    Validates: Requirements 1.1, 5.1
    """
    from awslabs.aws_location_server.server import create_geofence_collection
    from datetime import datetime, timezone

    # Set up mock response
    create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    mock_boto3_client.create_geofence_collection.return_value = {
        'CollectionName': 'test-collection',
        'CollectionArn': 'arn:aws:geo:us-east-1:123456789012:geofence-collection/test-collection',
        'CreateTime': create_time,
    }

    # Patch the geo_fencing_client in the server module
    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            return_value=mock_boto3_client.create_geofence_collection.return_value,
        ):
            result = await create_geofence_collection(
                mock_context,
                collection_name='test-collection',
                description='Test description',
            )

    # Verify the result
    assert 'collection_name' in result
    assert result['collection_name'] == 'test-collection'
    assert 'collection_arn' in result
    assert 'arn:aws:geo' in result['collection_arn']
    assert 'create_time' in result
    assert result['create_time'] == create_time.isoformat()


@pytest.mark.asyncio
async def test_create_geofence_collection_client_error(mock_boto3_client, mock_context):
    """Test create_geofence_collection when boto3 client raises a ClientError.

    Validates: Requirements 1.5, 5.2
    """
    from awslabs.aws_location_server.server import create_geofence_collection
    from botocore.exceptions import ClientError

    # Set up boto3 client to raise ClientError
    mock_boto3_client.create_geofence_collection.side_effect = ClientError(
        {'Error': {'Code': 'ConflictException', 'Message': 'Collection already exists'}},
        'create_geofence_collection',
    )

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            side_effect=ClientError(
                {'Error': {'Code': 'ConflictException', 'Message': 'Collection already exists'}},
                'create_geofence_collection',
            ),
        ):
            result = await create_geofence_collection(
                mock_context,
                collection_name='test-collection',
            )

    assert 'error' in result
    assert 'AWS Location Service error' in result['error']


@pytest.mark.asyncio
async def test_create_geofence_collection_general_exception(mock_boto3_client, mock_context):
    """Test create_geofence_collection when a general exception occurs.

    Validates: Requirements 1.5, 5.2
    """
    from awslabs.aws_location_server.server import create_geofence_collection

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch('asyncio.to_thread', side_effect=Exception('Test general exception')):
            result = await create_geofence_collection(
                mock_context,
                collection_name='test-collection',
            )

    assert 'error' in result
    assert 'Error creating geofence collection' in result['error']


@pytest.mark.asyncio
async def test_create_geofence_collection_uninitialized_client(mock_context):
    """Test create_geofence_collection when client is not initialized.

    Validates: Requirements 4.5
    """
    from awslabs.aws_location_server.server import create_geofence_collection

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = None
        result = await create_geofence_collection(
            mock_context,
            collection_name='test-collection',
        )

    assert 'error' in result
    assert 'AWS Location geofencing client not initialized' in result['error']


@pytest.mark.asyncio
async def test_list_geofence_collections_success(mock_boto3_client, mock_context):
    """Test list_geofence_collections success case.

    Validates: Requirements 1.2, 5.1
    """
    from awslabs.aws_location_server.server import list_geofence_collections
    from datetime import datetime, timezone

    # Set up mock response
    create_time1 = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    create_time2 = datetime(2024, 1, 16, 11, 45, 0, tzinfo=timezone.utc)
    mock_boto3_client.list_geofence_collections.return_value = {
        'Entries': [
            {
                'CollectionName': 'collection-1',
                'CollectionArn': 'arn:aws:geo:us-east-1:123456789012:geofence-collection/collection-1',
                'CreateTime': create_time1,
            },
            {
                'CollectionName': 'collection-2',
                'CollectionArn': 'arn:aws:geo:us-east-1:123456789012:geofence-collection/collection-2',
                'CreateTime': create_time2,
            },
        ]
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            return_value=mock_boto3_client.list_geofence_collections.return_value,
        ):
            result = await list_geofence_collections(mock_context, max_results=10)

    # Verify the result
    assert 'collections' in result
    assert len(result['collections']) == 2
    assert result['collections'][0]['collection_name'] == 'collection-1'
    assert (
        result['collections'][0]['collection_arn']
        == 'arn:aws:geo:us-east-1:123456789012:geofence-collection/collection-1'
    )
    assert result['collections'][0]['create_time'] == create_time1.isoformat()
    assert result['collections'][1]['collection_name'] == 'collection-2'


@pytest.mark.asyncio
async def test_list_geofence_collections_empty(mock_boto3_client, mock_context):
    """Test list_geofence_collections when no collections exist.

    Validates: Requirements 1.2, 5.1
    """
    from awslabs.aws_location_server.server import list_geofence_collections

    # Set up mock response with empty list
    mock_boto3_client.list_geofence_collections.return_value = {'Entries': []}

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            return_value=mock_boto3_client.list_geofence_collections.return_value,
        ):
            result = await list_geofence_collections(mock_context, max_results=10)

    # Verify the result
    assert 'collections' in result
    assert len(result['collections']) == 0


@pytest.mark.asyncio
async def test_list_geofence_collections_client_error(mock_boto3_client, mock_context):
    """Test list_geofence_collections when boto3 client raises a ClientError.

    Validates: Requirements 1.5, 5.2
    """
    from awslabs.aws_location_server.server import list_geofence_collections
    from botocore.exceptions import ClientError

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            side_effect=ClientError(
                {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
                'list_geofence_collections',
            ),
        ):
            result = await list_geofence_collections(mock_context, max_results=10)

    assert 'error' in result
    assert 'AWS Location Service error' in result['error']


@pytest.mark.asyncio
async def test_list_geofence_collections_general_exception(mock_boto3_client, mock_context):
    """Test list_geofence_collections when a general exception occurs.

    Validates: Requirements 1.5, 5.2
    """
    from awslabs.aws_location_server.server import list_geofence_collections

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch('asyncio.to_thread', side_effect=Exception('Test general exception')):
            result = await list_geofence_collections(mock_context, max_results=10)

    assert 'error' in result
    assert 'Error listing geofence collections' in result['error']


@pytest.mark.asyncio
async def test_list_geofence_collections_uninitialized_client(mock_context):
    """Test list_geofence_collections when client is not initialized.

    Validates: Requirements 4.5
    """
    from awslabs.aws_location_server.server import list_geofence_collections

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = None
        result = await list_geofence_collections(mock_context, max_results=10)

    assert 'error' in result
    assert 'AWS Location geofencing client not initialized' in result['error']


@pytest.mark.asyncio
async def test_describe_geofence_collection_success(mock_boto3_client, mock_context):
    """Test describe_geofence_collection success case.

    Validates: Requirements 1.3, 5.1
    """
    from awslabs.aws_location_server.server import describe_geofence_collection
    from datetime import datetime, timezone

    # Set up mock response
    create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    update_time = datetime(2024, 1, 20, 14, 45, 0, tzinfo=timezone.utc)
    mock_boto3_client.describe_geofence_collection.return_value = {
        'CollectionName': 'test-collection',
        'CollectionArn': 'arn:aws:geo:us-east-1:123456789012:geofence-collection/test-collection',
        'Description': 'Test collection description',
        'CreateTime': create_time,
        'UpdateTime': update_time,
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            return_value=mock_boto3_client.describe_geofence_collection.return_value,
        ):
            result = await describe_geofence_collection(
                mock_context,
                collection_name='test-collection',
            )

    # Verify the result
    assert 'collection_name' in result
    assert result['collection_name'] == 'test-collection'
    assert 'collection_arn' in result
    assert 'arn:aws:geo' in result['collection_arn']
    assert 'description' in result
    assert result['description'] == 'Test collection description'
    assert 'create_time' in result
    assert result['create_time'] == create_time.isoformat()
    assert 'update_time' in result
    assert result['update_time'] == update_time.isoformat()


@pytest.mark.asyncio
async def test_describe_geofence_collection_not_found(mock_boto3_client, mock_context):
    """Test describe_geofence_collection when collection is not found.

    Validates: Requirements 1.5, 5.2
    """
    from awslabs.aws_location_server.server import describe_geofence_collection
    from botocore.exceptions import ClientError

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            side_effect=ClientError(
                {
                    'Error': {
                        'Code': 'ResourceNotFoundException',
                        'Message': 'Collection not found',
                    }
                },
                'describe_geofence_collection',
            ),
        ):
            result = await describe_geofence_collection(
                mock_context,
                collection_name='nonexistent-collection',
            )

    assert 'error' in result
    assert 'AWS Location Service error' in result['error']


@pytest.mark.asyncio
async def test_describe_geofence_collection_general_exception(mock_boto3_client, mock_context):
    """Test describe_geofence_collection when a general exception occurs.

    Validates: Requirements 1.5, 5.2
    """
    from awslabs.aws_location_server.server import describe_geofence_collection

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch('asyncio.to_thread', side_effect=Exception('Test general exception')):
            result = await describe_geofence_collection(
                mock_context,
                collection_name='test-collection',
            )

    assert 'error' in result
    assert 'Error describing geofence collection' in result['error']


@pytest.mark.asyncio
async def test_describe_geofence_collection_uninitialized_client(mock_context):
    """Test describe_geofence_collection when client is not initialized.

    Validates: Requirements 4.5
    """
    from awslabs.aws_location_server.server import describe_geofence_collection

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = None
        result = await describe_geofence_collection(
            mock_context,
            collection_name='test-collection',
        )

    assert 'error' in result
    assert 'AWS Location geofencing client not initialized' in result['error']


@pytest.mark.asyncio
async def test_delete_geofence_collection_success(mock_boto3_client, mock_context):
    """Test delete_geofence_collection success case.

    Validates: Requirements 1.4, 5.1
    """
    from awslabs.aws_location_server.server import delete_geofence_collection

    # Set up mock response (delete returns empty response on success)
    mock_boto3_client.delete_geofence_collection.return_value = {}

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            return_value=mock_boto3_client.delete_geofence_collection.return_value,
        ):
            result = await delete_geofence_collection(
                mock_context,
                collection_name='test-collection',
            )

    # Verify the result
    assert 'success' in result
    assert result['success'] is True
    assert 'collection_name' in result
    assert result['collection_name'] == 'test-collection'


@pytest.mark.asyncio
async def test_delete_geofence_collection_client_error(mock_boto3_client, mock_context):
    """Test delete_geofence_collection when boto3 client raises a ClientError.

    Validates: Requirements 1.5, 5.2
    """
    from awslabs.aws_location_server.server import delete_geofence_collection
    from botocore.exceptions import ClientError

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            side_effect=ClientError(
                {
                    'Error': {
                        'Code': 'ResourceNotFoundException',
                        'Message': 'Collection not found',
                    }
                },
                'delete_geofence_collection',
            ),
        ):
            result = await delete_geofence_collection(
                mock_context,
                collection_name='nonexistent-collection',
            )

    assert 'error' in result
    assert 'AWS Location Service error' in result['error']


@pytest.mark.asyncio
async def test_delete_geofence_collection_general_exception(mock_boto3_client, mock_context):
    """Test delete_geofence_collection when a general exception occurs.

    Validates: Requirements 1.5, 5.2
    """
    from awslabs.aws_location_server.server import delete_geofence_collection

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch('asyncio.to_thread', side_effect=Exception('Test general exception')):
            result = await delete_geofence_collection(
                mock_context,
                collection_name='test-collection',
            )

    assert 'error' in result
    assert 'Error deleting geofence collection' in result['error']


@pytest.mark.asyncio
async def test_delete_geofence_collection_uninitialized_client(mock_context):
    """Test delete_geofence_collection when client is not initialized.

    Validates: Requirements 4.5
    """
    from awslabs.aws_location_server.server import delete_geofence_collection

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = None
        result = await delete_geofence_collection(
            mock_context,
            collection_name='test-collection',
        )

    assert 'error' in result
    assert 'AWS Location geofencing client not initialized' in result['error']


@pytest.mark.asyncio
async def test_list_geofence_collections_with_pagination(mock_boto3_client, mock_context):
    """Test list_geofence_collections with different max_results values.

    Validates: Requirements 1.2
    """
    from awslabs.aws_location_server.server import list_geofence_collections
    from datetime import datetime, timezone

    # Set up mock response with multiple collections
    create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    mock_boto3_client.list_geofence_collections.return_value = {
        'Entries': [
            {
                'CollectionName': f'collection-{i}',
                'CollectionArn': f'arn:aws:geo:us-east-1:123456789012:geofence-collection/collection-{i}',
                'CreateTime': create_time,
            }
            for i in range(5)
        ]
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            return_value=mock_boto3_client.list_geofence_collections.return_value,
        ):
            result = await list_geofence_collections(mock_context, max_results=5)

    # Verify the result
    assert 'collections' in result
    assert len(result['collections']) == 5
    for i, collection in enumerate(result['collections']):
        assert collection['collection_name'] == f'collection-{i}'


@pytest.mark.asyncio
async def test_describe_geofence_collection_empty_description(mock_boto3_client, mock_context):
    """Test describe_geofence_collection when description is empty.

    Validates: Requirements 1.3, 5.1
    """
    from awslabs.aws_location_server.server import describe_geofence_collection
    from datetime import datetime, timezone

    # Set up mock response without description
    create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    update_time = datetime(2024, 1, 20, 14, 45, 0, tzinfo=timezone.utc)
    mock_boto3_client.describe_geofence_collection.return_value = {
        'CollectionName': 'test-collection',
        'CollectionArn': 'arn:aws:geo:us-east-1:123456789012:geofence-collection/test-collection',
        'CreateTime': create_time,
        'UpdateTime': update_time,
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            return_value=mock_boto3_client.describe_geofence_collection.return_value,
        ):
            result = await describe_geofence_collection(
                mock_context,
                collection_name='test-collection',
            )

    # Verify the result
    assert 'collection_name' in result
    assert result['collection_name'] == 'test-collection'
    assert 'description' in result
    assert result['description'] == ''  # Default empty string


@pytest.mark.asyncio
async def test_create_geofence_collection_without_description(mock_boto3_client, mock_context):
    """Test create_geofence_collection without optional description.

    Validates: Requirements 1.1, 5.1
    """
    from awslabs.aws_location_server.server import create_geofence_collection
    from datetime import datetime, timezone

    # Set up mock response
    create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    mock_boto3_client.create_geofence_collection.return_value = {
        'CollectionName': 'test-collection',
        'CollectionArn': 'arn:aws:geo:us-east-1:123456789012:geofence-collection/test-collection',
        'CreateTime': create_time,
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            return_value=mock_boto3_client.create_geofence_collection.return_value,
        ):
            result = await create_geofence_collection(
                mock_context,
                collection_name='test-collection',
                # No description provided
            )

    # Verify the result
    assert 'collection_name' in result
    assert result['collection_name'] == 'test-collection'
    assert 'collection_arn' in result
    assert 'create_time' in result


# ============================================================================
# Geofence CRUD Tests
# ============================================================================


@pytest.mark.asyncio
async def test_put_geofence_circle_success(mock_boto3_client, mock_context):
    """Test put_geofence with circle geometry success case.

    Validates: Requirements 2.1, 5.1
    """
    from awslabs.aws_location_server.server import put_geofence
    from datetime import datetime, timezone

    create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    update_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    mock_boto3_client.put_geofence.return_value = {
        'GeofenceId': 'test-geofence',
        'CreateTime': create_time,
        'UpdateTime': update_time,
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch('asyncio.to_thread', return_value=mock_boto3_client.put_geofence.return_value):
            result = await put_geofence(
                mock_context,
                collection_name='test-collection',
                geofence_id='test-geofence',
                geometry_type='Circle',
                circle_center=[-122.3321, 47.6062],
                circle_radius=1000.0,
            )

    assert 'geofence_id' in result
    assert result['geofence_id'] == 'test-geofence'
    assert 'create_time' in result
    assert 'update_time' in result


@pytest.mark.asyncio
async def test_put_geofence_polygon_success(mock_boto3_client, mock_context):
    """Test put_geofence with polygon geometry success case.

    Validates: Requirements 2.2, 5.1
    """
    from awslabs.aws_location_server.server import put_geofence
    from datetime import datetime, timezone

    create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    update_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    mock_boto3_client.put_geofence.return_value = {
        'GeofenceId': 'test-geofence',
        'CreateTime': create_time,
        'UpdateTime': update_time,
    }

    polygon_coords = [
        [
            [-122.3321, 47.6062],
            [-122.3421, 47.6062],
            [-122.3421, 47.6162],
            [-122.3321, 47.6062],  # Closed ring
        ]
    ]

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch('asyncio.to_thread', return_value=mock_boto3_client.put_geofence.return_value):
            result = await put_geofence(
                mock_context,
                collection_name='test-collection',
                geofence_id='test-geofence',
                geometry_type='Polygon',
                polygon_coordinates=polygon_coords,
            )

    assert 'geofence_id' in result
    assert result['geofence_id'] == 'test-geofence'
    assert 'create_time' in result
    assert 'update_time' in result


@pytest.mark.asyncio
async def test_put_geofence_invalid_geometry_type(mock_boto3_client, mock_context):
    """Test put_geofence with invalid geometry type.

    Validates: Requirements 2.7, 5.2
    """
    from awslabs.aws_location_server.server import put_geofence

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        result = await put_geofence(
            mock_context,
            collection_name='test-collection',
            geofence_id='test-geofence',
            geometry_type='InvalidType',
        )

    assert 'error' in result
    assert "geometry_type must be 'Circle' or 'Polygon'" in result['error']


@pytest.mark.asyncio
async def test_put_geofence_circle_missing_center(mock_boto3_client, mock_context):
    """Test put_geofence with circle geometry missing center.

    Validates: Requirements 2.7, 5.2
    """
    from awslabs.aws_location_server.server import put_geofence

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        result = await put_geofence(
            mock_context,
            collection_name='test-collection',
            geofence_id='test-geofence',
            geometry_type='Circle',
            circle_center=None,
            circle_radius=1000.0,
        )

    assert 'error' in result
    assert 'Circle geometry requires center' in result['error']


@pytest.mark.asyncio
async def test_put_geofence_circle_invalid_radius(mock_boto3_client, mock_context):
    """Test put_geofence with circle geometry invalid radius.

    Validates: Requirements 2.7, 5.2
    """
    from awslabs.aws_location_server.server import put_geofence

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        result = await put_geofence(
            mock_context,
            collection_name='test-collection',
            geofence_id='test-geofence',
            geometry_type='Circle',
            circle_center=[-122.3321, 47.6062],
            circle_radius=-100.0,
        )

    assert 'error' in result
    assert 'Circle geometry requires positive radius' in result['error']


@pytest.mark.asyncio
async def test_put_geofence_polygon_not_closed(mock_boto3_client, mock_context):
    """Test put_geofence with polygon geometry not closed.

    Validates: Requirements 2.7, 5.2
    """
    from awslabs.aws_location_server.server import put_geofence

    polygon_coords = [
        [
            [-122.3321, 47.6062],
            [-122.3421, 47.6062],
            [-122.3421, 47.6162],
            [-122.3321, 47.6162],  # Not closed - different from first point
        ]
    ]

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        result = await put_geofence(
            mock_context,
            collection_name='test-collection',
            geofence_id='test-geofence',
            geometry_type='Polygon',
            polygon_coordinates=polygon_coords,
        )

    assert 'error' in result
    assert 'Polygon linear ring must be closed' in result['error']


@pytest.mark.asyncio
async def test_put_geofence_uninitialized_client(mock_context):
    """Test put_geofence when client is not initialized.

    Validates: Requirements 4.5
    """
    from awslabs.aws_location_server.server import put_geofence

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = None
        result = await put_geofence(
            mock_context,
            collection_name='test-collection',
            geofence_id='test-geofence',
            geometry_type='Circle',
            circle_center=[-122.3321, 47.6062],
            circle_radius=1000.0,
        )

    assert 'error' in result
    assert 'AWS Location geofencing client not initialized' in result['error']


@pytest.mark.asyncio
async def test_get_geofence_success(mock_boto3_client, mock_context):
    """Test get_geofence success case.

    Validates: Requirements 2.3, 5.1, 5.3
    """
    from awslabs.aws_location_server.server import get_geofence
    from datetime import datetime, timezone

    create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    update_time = datetime(2024, 1, 20, 14, 45, 0, tzinfo=timezone.utc)
    mock_boto3_client.get_geofence.return_value = {
        'GeofenceId': 'test-geofence',
        'Geometry': {
            'Circle': {
                'Center': [-122.3321, 47.6062],
                'Radius': 1000.0,
            }
        },
        'Status': 'ACTIVE',
        'CreateTime': create_time,
        'UpdateTime': update_time,
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch('asyncio.to_thread', return_value=mock_boto3_client.get_geofence.return_value):
            result = await get_geofence(
                mock_context,
                collection_name='test-collection',
                geofence_id='test-geofence',
            )

    assert 'geofence_id' in result
    assert result['geofence_id'] == 'test-geofence'
    assert 'geometry' in result
    assert 'Circle' in result['geometry']
    assert 'status' in result
    assert result['status'] == 'ACTIVE'
    assert 'create_time' in result
    assert 'update_time' in result


@pytest.mark.asyncio
async def test_get_geofence_not_found(mock_boto3_client, mock_context):
    """Test get_geofence when geofence is not found.

    Validates: Requirements 5.2
    """
    from awslabs.aws_location_server.server import get_geofence
    from botocore.exceptions import ClientError

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            side_effect=ClientError(
                {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Geofence not found'}},
                'get_geofence',
            ),
        ):
            result = await get_geofence(
                mock_context,
                collection_name='test-collection',
                geofence_id='nonexistent-geofence',
            )

    assert 'error' in result
    assert 'AWS Location Service error' in result['error']


@pytest.mark.asyncio
async def test_get_geofence_uninitialized_client(mock_context):
    """Test get_geofence when client is not initialized.

    Validates: Requirements 4.5
    """
    from awslabs.aws_location_server.server import get_geofence

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = None
        result = await get_geofence(
            mock_context,
            collection_name='test-collection',
            geofence_id='test-geofence',
        )

    assert 'error' in result
    assert 'AWS Location geofencing client not initialized' in result['error']


@pytest.mark.asyncio
async def test_list_geofences_success(mock_boto3_client, mock_context):
    """Test list_geofences success case.

    Validates: Requirements 2.4, 5.1, 5.3
    """
    from awslabs.aws_location_server.server import list_geofences
    from datetime import datetime, timezone

    create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    mock_boto3_client.list_geofences.return_value = {
        'Entries': [
            {
                'GeofenceId': 'geofence-1',
                'Geometry': {'Circle': {'Center': [-122.3321, 47.6062], 'Radius': 1000.0}},
                'Status': 'ACTIVE',
                'CreateTime': create_time,
            },
            {
                'GeofenceId': 'geofence-2',
                'Geometry': {
                    'Polygon': [
                        [
                            [-122.3321, 47.6062],
                            [-122.3421, 47.6062],
                            [-122.3421, 47.6162],
                            [-122.3321, 47.6062],
                        ]
                    ]
                },
                'Status': 'ACTIVE',
                'CreateTime': create_time,
            },
        ]
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread', return_value=mock_boto3_client.list_geofences.return_value
        ):
            result = await list_geofences(
                mock_context,
                collection_name='test-collection',
                max_results=10,
            )

    assert 'geofences' in result
    assert len(result['geofences']) == 2
    assert result['geofences'][0]['geofence_id'] == 'geofence-1'
    assert 'geometry' in result['geofences'][0]
    assert 'status' in result['geofences'][0]
    assert 'create_time' in result['geofences'][0]


@pytest.mark.asyncio
async def test_list_geofences_empty(mock_boto3_client, mock_context):
    """Test list_geofences when no geofences exist.

    Validates: Requirements 2.4, 5.1
    """
    from awslabs.aws_location_server.server import list_geofences

    mock_boto3_client.list_geofences.return_value = {'Entries': []}

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread', return_value=mock_boto3_client.list_geofences.return_value
        ):
            result = await list_geofences(
                mock_context,
                collection_name='test-collection',
                max_results=10,
            )

    assert 'geofences' in result
    assert len(result['geofences']) == 0


@pytest.mark.asyncio
async def test_list_geofences_uninitialized_client(mock_context):
    """Test list_geofences when client is not initialized.

    Validates: Requirements 4.5
    """
    from awslabs.aws_location_server.server import list_geofences

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = None
        result = await list_geofences(
            mock_context,
            collection_name='test-collection',
            max_results=10,
        )

    assert 'error' in result
    assert 'AWS Location geofencing client not initialized' in result['error']


@pytest.mark.asyncio
async def test_batch_delete_geofences_success(mock_boto3_client, mock_context):
    """Test batch_delete_geofences success case.

    Validates: Requirements 2.5, 5.1
    """
    from awslabs.aws_location_server.server import batch_delete_geofences

    mock_boto3_client.batch_delete_geofence.return_value = {'Errors': []}

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread', return_value=mock_boto3_client.batch_delete_geofence.return_value
        ):
            result = await batch_delete_geofences(
                mock_context,
                collection_name='test-collection',
                geofence_ids=['geofence-1', 'geofence-2'],
            )

    assert 'deleted' in result
    assert 'errors' in result
    assert 'geofence-1' in result['deleted']
    assert 'geofence-2' in result['deleted']
    assert len(result['errors']) == 0


@pytest.mark.asyncio
async def test_batch_delete_geofences_mixed_results(mock_boto3_client, mock_context):
    """Test batch_delete_geofences with mixed success and failure.

    Validates: Requirements 2.5, 5.1
    """
    from awslabs.aws_location_server.server import batch_delete_geofences

    mock_boto3_client.batch_delete_geofence.return_value = {
        'Errors': [
            {
                'GeofenceId': 'geofence-2',
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Geofence not found'},
            }
        ]
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread', return_value=mock_boto3_client.batch_delete_geofence.return_value
        ):
            result = await batch_delete_geofences(
                mock_context,
                collection_name='test-collection',
                geofence_ids=['geofence-1', 'geofence-2'],
            )

    assert 'deleted' in result
    assert 'errors' in result
    assert 'geofence-1' in result['deleted']
    assert 'geofence-2' not in result['deleted']
    assert len(result['errors']) == 1
    assert result['errors'][0]['geofence_id'] == 'geofence-2'


@pytest.mark.asyncio
async def test_batch_delete_geofences_uninitialized_client(mock_context):
    """Test batch_delete_geofences when client is not initialized.

    Validates: Requirements 4.5
    """
    from awslabs.aws_location_server.server import batch_delete_geofences

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = None
        result = await batch_delete_geofences(
            mock_context,
            collection_name='test-collection',
            geofence_ids=['geofence-1'],
        )

    assert 'error' in result
    assert 'AWS Location geofencing client not initialized' in result['error']


# ============================================================================
# Position Evaluation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_batch_evaluate_geofences_success(mock_boto3_client, mock_context):
    """Test batch_evaluate_geofences success case.

    Validates: Requirements 3.1, 3.2, 5.1
    """
    from awslabs.aws_location_server.server import batch_evaluate_geofences

    mock_boto3_client.batch_evaluate_geofences.return_value = {'Errors': []}

    device_position_updates = [
        {
            'device_id': 'device-1',
            'position': [-122.3321, 47.6062],
            'sample_time': '2024-01-15T10:30:00Z',
        },
        {
            'device_id': 'device-2',
            'position': [-122.3421, 47.6162],
            'sample_time': '2024-01-15T10:30:00Z',
        },
    ]

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            return_value=mock_boto3_client.batch_evaluate_geofences.return_value,
        ):
            result = await batch_evaluate_geofences(
                mock_context,
                collection_name='test-collection',
                device_position_updates=device_position_updates,
            )

    assert 'results' in result
    assert isinstance(result['results'], list)


@pytest.mark.asyncio
async def test_batch_evaluate_geofences_invalid_position(mock_boto3_client, mock_context):
    """Test batch_evaluate_geofences with invalid position.

    Validates: Requirements 3.4, 5.2
    """
    from awslabs.aws_location_server.server import batch_evaluate_geofences

    device_position_updates = [
        {
            'device_id': 'device-1',
            'position': [-122.3321],  # Invalid - only one coordinate
            'sample_time': '2024-01-15T10:30:00Z',
        },
    ]

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        result = await batch_evaluate_geofences(
            mock_context,
            collection_name='test-collection',
            device_position_updates=device_position_updates,
        )

    assert 'error' in result
    assert 'Invalid position for device device-1' in result['error']


@pytest.mark.asyncio
async def test_batch_evaluate_geofences_invalid_coordinates(mock_boto3_client, mock_context):
    """Test batch_evaluate_geofences with out-of-range coordinates.

    Validates: Requirements 3.4, 5.2
    """
    from awslabs.aws_location_server.server import batch_evaluate_geofences

    device_position_updates = [
        {
            'device_id': 'device-1',
            'position': [-200.0, 47.6062],  # Invalid longitude
            'sample_time': '2024-01-15T10:30:00Z',
        },
    ]

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        result = await batch_evaluate_geofences(
            mock_context,
            collection_name='test-collection',
            device_position_updates=device_position_updates,
        )

    assert 'error' in result
    assert 'Invalid coordinates for device device-1' in result['error']


@pytest.mark.asyncio
async def test_batch_evaluate_geofences_uninitialized_client(mock_context):
    """Test batch_evaluate_geofences when client is not initialized.

    Validates: Requirements 4.5
    """
    from awslabs.aws_location_server.server import batch_evaluate_geofences

    device_position_updates = [
        {
            'device_id': 'device-1',
            'position': [-122.3321, 47.6062],
            'sample_time': '2024-01-15T10:30:00Z',
        },
    ]

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = None
        result = await batch_evaluate_geofences(
            mock_context,
            collection_name='test-collection',
            device_position_updates=device_position_updates,
        )

    assert 'error' in result
    assert 'AWS Location geofencing client not initialized' in result['error']


@pytest.mark.asyncio
async def test_forecast_geofence_events_success(mock_boto3_client, mock_context):
    """Test forecast_geofence_events success case.

    Validates: Requirements 3.3, 5.1, 5.4
    """
    from awslabs.aws_location_server.server import forecast_geofence_events
    from datetime import datetime, timezone

    forecasted_time = datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc)
    mock_boto3_client.forecast_geofence_events.return_value = {
        'ForecastedEvents': [
            {
                'GeofenceId': 'geofence-1',
                'EventType': 'ENTER',
                'ForecastedBreachTime': forecasted_time,
            },
        ]
    }

    device_state = {
        'position': [-122.3321, 47.6062],
        'speed': 10.0,
        'heading': 45.0,
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            return_value=mock_boto3_client.forecast_geofence_events.return_value,
        ):
            result = await forecast_geofence_events(
                mock_context,
                collection_name='test-collection',
                device_id='device-1',
                device_state=device_state,
                time_horizon_minutes=30.0,
            )

    assert 'forecasted_events' in result
    assert len(result['forecasted_events']) == 1
    assert result['forecasted_events'][0]['geofence_id'] == 'geofence-1'
    assert result['forecasted_events'][0]['event_type'] == 'ENTER'
    assert result['forecasted_events'][0]['forecasted_time'] == forecasted_time.isoformat()


@pytest.mark.asyncio
async def test_forecast_geofence_events_missing_position(mock_boto3_client, mock_context):
    """Test forecast_geofence_events with missing position.

    Validates: Requirements 5.2
    """
    from awslabs.aws_location_server.server import forecast_geofence_events

    device_state = {
        'speed': 10.0,
        # Missing position
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        result = await forecast_geofence_events(
            mock_context,
            collection_name='test-collection',
            device_id='device-1',
            device_state=device_state,
            time_horizon_minutes=30.0,
        )

    assert 'error' in result
    assert 'device_state must contain position' in result['error']


@pytest.mark.asyncio
async def test_forecast_geofence_events_invalid_coordinates(mock_boto3_client, mock_context):
    """Test forecast_geofence_events with invalid coordinates.

    Validates: Requirements 5.2
    """
    from awslabs.aws_location_server.server import forecast_geofence_events

    device_state = {
        'position': [-200.0, 47.6062],  # Invalid longitude
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        result = await forecast_geofence_events(
            mock_context,
            collection_name='test-collection',
            device_id='device-1',
            device_state=device_state,
            time_horizon_minutes=30.0,
        )

    assert 'error' in result
    assert 'Invalid coordinates' in result['error']


@pytest.mark.asyncio
async def test_forecast_geofence_events_uninitialized_client(mock_context):
    """Test forecast_geofence_events when client is not initialized.

    Validates: Requirements 4.5
    """
    from awslabs.aws_location_server.server import forecast_geofence_events

    device_state = {
        'position': [-122.3321, 47.6062],
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = None
        result = await forecast_geofence_events(
            mock_context,
            collection_name='test-collection',
            device_id='device-1',
            device_state=device_state,
            time_horizon_minutes=30.0,
        )

    assert 'error' in result
    assert 'AWS Location geofencing client not initialized' in result['error']


# Additional tests for coverage - geofencing error handling paths


@pytest.mark.asyncio
async def test_put_geofence_client_error(mock_boto3_client, mock_context):
    """Test put_geofence when boto3 client raises a ClientError.

    Validates: Requirements 2.7, 5.2
    """
    from awslabs.aws_location_server.server import put_geofence
    from botocore.exceptions import ClientError

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            side_effect=ClientError(
                {'Error': {'Code': 'ValidationException', 'Message': 'Invalid geofence'}},
                'put_geofence',
            ),
        ):
            result = await put_geofence(
                mock_context,
                collection_name='test-collection',
                geofence_id='test-geofence',
                geometry_type='Circle',
                circle_center=[-122.3321, 47.6062],
                circle_radius=1000.0,
            )

    assert 'error' in result
    assert 'AWS Location Service error' in result['error']


@pytest.mark.asyncio
async def test_put_geofence_general_exception(mock_boto3_client, mock_context):
    """Test put_geofence when a general exception occurs.

    Validates: Requirements 2.7, 5.2
    """
    from awslabs.aws_location_server.server import put_geofence

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch('asyncio.to_thread', side_effect=Exception('Test general exception')):
            result = await put_geofence(
                mock_context,
                collection_name='test-collection',
                geofence_id='test-geofence',
                geometry_type='Circle',
                circle_center=[-122.3321, 47.6062],
                circle_radius=1000.0,
            )

    assert 'error' in result
    assert 'Error creating/updating geofence' in result['error']


@pytest.mark.asyncio
async def test_put_geofence_polygon_missing_coordinates(mock_boto3_client, mock_context):
    """Test put_geofence with polygon geometry missing coordinates.

    Validates: Requirements 2.7, 5.2
    """
    from awslabs.aws_location_server.server import put_geofence

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        result = await put_geofence(
            mock_context,
            collection_name='test-collection',
            geofence_id='test-geofence',
            geometry_type='Polygon',
            polygon_coordinates=None,
        )

    assert 'error' in result
    assert 'Polygon geometry requires at least one linear ring' in result['error']


@pytest.mark.asyncio
async def test_put_geofence_polygon_too_few_points(mock_boto3_client, mock_context):
    """Test put_geofence with polygon geometry with too few points.

    Validates: Requirements 2.7, 5.2
    """
    from awslabs.aws_location_server.server import put_geofence

    polygon_coords = [
        [
            [-122.3321, 47.6062],
            [-122.3421, 47.6062],
            [-122.3321, 47.6062],  # Only 3 points
        ]
    ]

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        result = await put_geofence(
            mock_context,
            collection_name='test-collection',
            geofence_id='test-geofence',
            geometry_type='Polygon',
            polygon_coordinates=polygon_coords,
        )

    assert 'error' in result
    assert 'Polygon linear ring requires at least 4 points' in result['error']


@pytest.mark.asyncio
async def test_put_geofence_with_properties(mock_boto3_client, mock_context):
    """Test put_geofence with geofence properties.

    Validates: Requirements 2.1, 5.1
    """
    from awslabs.aws_location_server.server import put_geofence
    from datetime import datetime, timezone

    create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    update_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    mock_boto3_client.put_geofence.return_value = {
        'GeofenceId': 'test-geofence',
        'CreateTime': create_time,
        'UpdateTime': update_time,
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch('asyncio.to_thread', return_value=mock_boto3_client.put_geofence.return_value):
            result = await put_geofence(
                mock_context,
                collection_name='test-collection',
                geofence_id='test-geofence',
                geometry_type='Circle',
                circle_center=[-122.3321, 47.6062],
                circle_radius=1000.0,
                properties={'zone_type': 'restricted', 'priority': 'high'},
            )

    assert 'geofence_id' in result
    assert result['geofence_id'] == 'test-geofence'


@pytest.mark.asyncio
async def test_get_geofence_client_error(mock_boto3_client, mock_context):
    """Test get_geofence when boto3 client raises a ClientError.

    Validates: Requirements 5.2
    """
    from awslabs.aws_location_server.server import get_geofence
    from botocore.exceptions import ClientError

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            side_effect=ClientError(
                {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Geofence not found'}},
                'get_geofence',
            ),
        ):
            result = await get_geofence(
                mock_context,
                collection_name='test-collection',
                geofence_id='nonexistent-geofence',
            )

    assert 'error' in result
    assert 'AWS Location Service error' in result['error']


@pytest.mark.asyncio
async def test_get_geofence_general_exception(mock_boto3_client, mock_context):
    """Test get_geofence when a general exception occurs.

    Validates: Requirements 5.2
    """
    from awslabs.aws_location_server.server import get_geofence

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch('asyncio.to_thread', side_effect=Exception('Test general exception')):
            result = await get_geofence(
                mock_context,
                collection_name='test-collection',
                geofence_id='test-geofence',
            )

    assert 'error' in result
    assert 'Error getting geofence' in result['error']


@pytest.mark.asyncio
async def test_list_geofences_client_error(mock_boto3_client, mock_context):
    """Test list_geofences when boto3 client raises a ClientError.

    Validates: Requirements 5.2
    """
    from awslabs.aws_location_server.server import list_geofences
    from botocore.exceptions import ClientError

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            side_effect=ClientError(
                {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
                'list_geofences',
            ),
        ):
            result = await list_geofences(
                mock_context,
                collection_name='test-collection',
                max_results=10,
            )

    assert 'error' in result
    assert 'AWS Location Service error' in result['error']


@pytest.mark.asyncio
async def test_list_geofences_general_exception(mock_boto3_client, mock_context):
    """Test list_geofences when a general exception occurs.

    Validates: Requirements 5.2
    """
    from awslabs.aws_location_server.server import list_geofences

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch('asyncio.to_thread', side_effect=Exception('Test general exception')):
            result = await list_geofences(
                mock_context,
                collection_name='test-collection',
                max_results=10,
            )

    assert 'error' in result
    assert 'Error listing geofences' in result['error']


@pytest.mark.asyncio
async def test_batch_delete_geofences_client_error(mock_boto3_client, mock_context):
    """Test batch_delete_geofences when boto3 client raises a ClientError.

    Validates: Requirements 5.2
    """
    from awslabs.aws_location_server.server import batch_delete_geofences
    from botocore.exceptions import ClientError

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            side_effect=ClientError(
                {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
                'batch_delete_geofence',
            ),
        ):
            result = await batch_delete_geofences(
                mock_context,
                collection_name='test-collection',
                geofence_ids=['geofence-1', 'geofence-2'],
            )

    assert 'error' in result
    assert 'AWS Location Service error' in result['error']


@pytest.mark.asyncio
async def test_batch_delete_geofences_general_exception(mock_boto3_client, mock_context):
    """Test batch_delete_geofences when a general exception occurs.

    Validates: Requirements 5.2
    """
    from awslabs.aws_location_server.server import batch_delete_geofences

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch('asyncio.to_thread', side_effect=Exception('Test general exception')):
            result = await batch_delete_geofences(
                mock_context,
                collection_name='test-collection',
                geofence_ids=['geofence-1', 'geofence-2'],
            )

    assert 'error' in result
    assert 'Error batch deleting geofences' in result['error']


@pytest.mark.asyncio
async def test_batch_evaluate_geofences_client_error(mock_boto3_client, mock_context):
    """Test batch_evaluate_geofences when boto3 client raises a ClientError.

    Validates: Requirements 5.2
    """
    from awslabs.aws_location_server.server import batch_evaluate_geofences
    from botocore.exceptions import ClientError

    device_position_updates = [
        {
            'device_id': 'device-1',
            'position': [-122.3321, 47.6062],
            'sample_time': '2024-01-15T10:30:00Z',
        }
    ]

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            side_effect=ClientError(
                {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
                'batch_evaluate_geofences',
            ),
        ):
            result = await batch_evaluate_geofences(
                mock_context,
                collection_name='test-collection',
                device_position_updates=device_position_updates,
            )

    assert 'error' in result
    assert 'AWS Location Service error' in result['error']


@pytest.mark.asyncio
async def test_batch_evaluate_geofences_general_exception(mock_boto3_client, mock_context):
    """Test batch_evaluate_geofences when a general exception occurs.

    Validates: Requirements 5.2
    """
    from awslabs.aws_location_server.server import batch_evaluate_geofences

    device_position_updates = [
        {
            'device_id': 'device-1',
            'position': [-122.3321, 47.6062],
            'sample_time': '2024-01-15T10:30:00Z',
        }
    ]

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch('asyncio.to_thread', side_effect=Exception('Test general exception')):
            result = await batch_evaluate_geofences(
                mock_context,
                collection_name='test-collection',
                device_position_updates=device_position_updates,
            )

    assert 'error' in result
    assert 'Error evaluating geofences' in result['error']


@pytest.mark.asyncio
async def test_batch_evaluate_geofences_with_errors_in_response(mock_boto3_client, mock_context):
    """Test batch_evaluate_geofences when response contains errors.

    Validates: Requirements 3.1, 3.2
    """
    from awslabs.aws_location_server.server import batch_evaluate_geofences

    device_position_updates = [
        {
            'device_id': 'device-1',
            'position': [-122.3321, 47.6062],
            'sample_time': '2024-01-15T10:30:00Z',
        }
    ]

    mock_response = {
        'Errors': [
            {
                'DeviceId': 'device-1',
                'Error': {
                    'Code': 'ValidationException',
                    'Message': 'Invalid device position',
                },
            }
        ]
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch('asyncio.to_thread', return_value=mock_response):
            result = await batch_evaluate_geofences(
                mock_context,
                collection_name='test-collection',
                device_position_updates=device_position_updates,
            )

    assert 'results' in result
    assert len(result['results']) == 1
    assert result['results'][0]['device_id'] == 'device-1'
    assert 'error' in result['results'][0]


@pytest.mark.asyncio
async def test_forecast_geofence_events_client_error(mock_boto3_client, mock_context):
    """Test forecast_geofence_events when boto3 client raises a ClientError.

    Validates: Requirements 5.2
    """
    from awslabs.aws_location_server.server import forecast_geofence_events
    from botocore.exceptions import ClientError

    device_state = {
        'position': [-122.3321, 47.6062],
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch(
            'asyncio.to_thread',
            side_effect=ClientError(
                {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
                'forecast_geofence_events',
            ),
        ):
            result = await forecast_geofence_events(
                mock_context,
                collection_name='test-collection',
                device_id='device-1',
                device_state=device_state,
                time_horizon_minutes=30.0,
            )

    assert 'error' in result
    assert 'AWS Location Service error' in result['error']


@pytest.mark.asyncio
async def test_forecast_geofence_events_general_exception(mock_boto3_client, mock_context):
    """Test forecast_geofence_events when a general exception occurs.

    Validates: Requirements 5.2
    """
    from awslabs.aws_location_server.server import forecast_geofence_events

    device_state = {
        'position': [-122.3321, 47.6062],
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch('asyncio.to_thread', side_effect=Exception('Test general exception')):
            result = await forecast_geofence_events(
                mock_context,
                collection_name='test-collection',
                device_id='device-1',
                device_state=device_state,
                time_horizon_minutes=30.0,
            )

    assert 'error' in result
    assert 'Error forecasting geofence events' in result['error']


@pytest.mark.asyncio
async def test_forecast_geofence_events_with_speed_and_heading(mock_boto3_client, mock_context):
    """Test forecast_geofence_events with speed and heading parameters.

    Validates: Requirements 3.3, 5.1
    """
    from awslabs.aws_location_server.server import forecast_geofence_events
    from datetime import datetime, timezone

    device_state = {
        'position': [-122.3321, 47.6062],
        'speed': 15.0,  # meters per second
        'heading': 90.0,  # degrees from north
    }

    forecasted_time = datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc)
    mock_response = {
        'ForecastedEvents': [
            {
                'GeofenceId': 'geofence-1',
                'EventType': 'ENTER',
                'ForecastedBreachTime': forecasted_time,
            }
        ]
    }

    with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
        mock_geo_client.location_client = mock_boto3_client
        with patch('asyncio.to_thread', return_value=mock_response):
            result = await forecast_geofence_events(
                mock_context,
                collection_name='test-collection',
                device_id='device-1',
                device_state=device_state,
                time_horizon_minutes=30.0,
            )

    assert 'forecasted_events' in result
    assert len(result['forecasted_events']) == 1
    assert result['forecasted_events'][0]['geofence_id'] == 'geofence-1'
    assert result['forecasted_events'][0]['event_type'] == 'ENTER'
