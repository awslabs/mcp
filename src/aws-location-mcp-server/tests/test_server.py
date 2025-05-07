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

import pytest

# Import the functions directly to avoid Field validation issues
from awslabs.aws_location_server.server import (
    GeoPlacesClient,
    GeoRoutesClient,
    calculate_route,
    get_place,
    main,
    optimize_waypoints,
    reverse_geocode,
    search_places,
    search_places_open_now,
)
from unittest.mock import MagicMock, patch


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


def test_geo_routes_client_initialization(monkeypatch):
    """Test the GeoRoutesClient initialization."""
    monkeypatch.setenv('AWS_REGION', 'us-west-2')

    with patch('boto3.client') as mock_boto3_client:
        _ = GeoRoutesClient()
        mock_boto3_client.assert_called_once()
        args, kwargs = mock_boto3_client.call_args
        assert args[0] == 'geo-routes'
        assert kwargs['region_name'] == 'us-west-2'


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
        assert kwargs['aws_access_key_id'] == 'AKIAIOSFODNN7EXAMPLE'
        assert kwargs['aws_secret_access_key'] == 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'


def test_geo_routes_client_initialization_exception():
    """Test the GeoRoutesClient initialization when an exception occurs."""
    with patch('boto3.client', side_effect=Exception('Test exception')):
        geo_client = GeoRoutesClient()
        assert geo_client.geo_routes_client is None


def test_main_stdio():
    """Test the main function with stdio transport."""
    with patch('awslabs.aws_location_server.server.mcp.run') as mock_run:
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_parse_args.return_value = MagicMock(sse=False, port=8888)
            main()
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert kwargs.get('transport') is None


def test_main_sse():
    """Test the main function with SSE transport."""
    with patch('awslabs.aws_location_server.server.mcp.run') as mock_run:
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_parse_args.return_value = MagicMock(sse=True, port=9999)
            main()
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert kwargs.get('transport') == 'sse'


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
