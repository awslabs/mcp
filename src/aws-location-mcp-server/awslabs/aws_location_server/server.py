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

"""Amazon Location Service MCP Server implementation using geo-places client only."""

import argparse
import boto3
import botocore.config
import botocore.exceptions
import os
import sys
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Dict, Optional
import asyncio


# Set up logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

# Initialize FastMCP server
mcp = FastMCP(
    'awslabs.aws-location-mcp-server',
    instructions="""
    # Amazon Location Service MCP Server (geo-places)

    This server provides tools to interact with Amazon Location Service geo-places capabilities, focusing on place search, details, and geocoding.

    ## Features
    - Search for places using text queries
    - Get place details by PlaceId
    - Reverse geocode coordinates
    - Search for places nearby a location
    - Search for places open now (extension)

    ## Prerequisites
    1. Have an AWS account with Amazon Location Service enabled
    2. Configure AWS CLI with your credentials and profile
    3. Set AWS_REGION environment variable if not using default

    ## Best Practices
    - Provide specific location details for more accurate results
    - Use the search_places tool for general search
    - Use get_place for details on a specific place
    - Use reverse_geocode for lat/lon to address
    - Use search_nearby for places near a point
    - Use search_places_open_now to find currently open places (if supported by data)
    """,
    dependencies=[
        'boto3',
        'pydantic',
    ],
)


class GeoPlacesClient:
    """Amazon Location Service geo-places client wrapper."""

    def __init__(self):
        """Initialize the Amazon geo-places client."""
        self.aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        self.geo_places_client = None
        config = botocore.config.Config(
            connect_timeout=15, read_timeout=15, retries={'max_attempts': 3}
        )
        aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
        try:
            if aws_access_key and aws_secret_key:
                client_args = {
                    'aws_access_key_id': aws_access_key,
                    'aws_secret_access_key': aws_secret_key,
                    'region_name': self.aws_region,
                    'config': config,
                }
                if aws_session_token:
                    client_args['aws_session_token'] = aws_session_token
                self.geo_places_client = boto3.client('geo-places', **client_args)
            else:
                self.geo_places_client = boto3.client(
                    'geo-places', region_name=self.aws_region, config=config
                )
            logger.debug(f'Amazon geo-places client initialized for region {self.aws_region}')
        except Exception as e:
            logger.error(f'Failed to initialize Amazon geo-places client: {str(e)}')
            self.geo_places_client = None


class GeoRoutesClient:
    """Amazon Location Service geo-routes client wrapper."""

    def __init__(self):
        self.aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        self.geo_routes_client = None
        config = botocore.config.Config(
            connect_timeout=15, read_timeout=15, retries={'max_attempts': 3}
        )
        aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
        try:
            if aws_access_key and aws_secret_key:
                client_args = {
                    'aws_access_key_id': aws_access_key,
                    'aws_secret_access_key': aws_secret_key,
                    'region_name': self.aws_region,
                    'config': config,
                }
                if aws_session_token:
                    client_args['aws_session_token'] = aws_session_token
                self.geo_routes_client = boto3.client('geo-routes', **client_args)
            else:
                self.geo_routes_client = boto3.client(
                    'geo-routes', region_name=self.aws_region, config=config
                )
            logger.debug(f'Amazon geo-routes client initialized for region {self.aws_region}')
        except Exception as e:
            logger.error(f'Failed to initialize Amazon geo-routes client: {str(e)}')
            self.geo_routes_client = None


# Initialize the geo-places client
geo_places_client = GeoPlacesClient()

# Initialize the geo-routes client
geo_routes_client = GeoRoutesClient()


@mcp.tool()
async def search_places(
    ctx: Context,
    query: str = Field(description='Search query (address, place name, etc.)'),
    max_results: int = Field(
        default=5, description='Maximum number of results to return', ge=1, le=50
    ),
    mode: str = Field(
        default='summary',
        description="Output mode: 'summary' (default) or 'raw' for all AWS fields",
    ),
) -> Dict:
    """Search for places using Amazon Location Service geo-places search_text API. Geocode the query using the geocode API to get BiasPosition. If no results, try a bounding box filter. Includes contact info and opening hours if present. Output is standardized and includes all fields, even if empty or not available."""
    if not geo_places_client.geo_places_client:
        error_msg = (
            'Amazon geo-places client not initialized. Please check AWS credentials and region.'
        )
        await ctx.error(error_msg)
        return {'error': error_msg}
    try:
        geo_response = geo_places_client.geo_places_client.geocode(QueryText=query)
        geo_items = geo_response.get('ResultItems', [])
        if geo_items:
            geo_point = geo_items[0]['Position']
            bias_position = geo_point
            response = geo_places_client.geo_places_client.search_text(
                QueryText=query,
                MaxResults=max_results,
                BiasPosition=bias_position,
                AdditionalFeatures=['Contact'],
            )
            places = response.get('ResultItems', [])
            if not places:
                lon, lat = bias_position
                bounding_box = [lon - 0.05, lat - 0.05, lon + 0.05, lat + 0.05]
                response = geo_places_client.geo_places_client.search_text(
                    QueryText=query,
                    MaxResults=max_results,
                    Filter={'BoundingBox': bounding_box},
                    AdditionalFeatures=['Contact'],
                )
                places = response.get('ResultItems', [])
        else:
            error_msg = f'Could not geocode query "{query}" for BiasPosition.'
            await ctx.error(error_msg)
            return {'error': error_msg}

        def safe_list(val):
            return val if isinstance(val, list) else ([] if val is None else [val])

        def parse_contacts(contacts):
            return {
                'phones': [p['Value'] for p in contacts.get('Phones', [])] if contacts else [],
                'websites': [w['Value'] for w in contacts.get('Websites', [])] if contacts else [],
                'emails': [e['Value'] for e in contacts.get('Emails', [])] if contacts else [],
                'faxes': [f['Value'] for f in contacts.get('Faxes', [])] if contacts else [],
            }

        def parse_opening_hours(result):
            oh = result.get('OpeningHours')
            if not oh:
                contacts = result.get('Contacts', {})
                oh = contacts.get('OpeningHours') if contacts else None
            if not oh:
                return []
            # Normalize to list of dicts with display and components
            if isinstance(oh, dict):
                oh = [oh]
            parsed = []
            for entry in oh:
                parsed.append(
                    {
                        'display': entry.get('Display', []) or entry.get('display', []),
                        'components': entry.get('Components', []) or entry.get('components', []),
                        'open_now': entry.get('OpenNow', None),
                        'categories': [cat.get('Name') for cat in entry.get('Categories', [])]
                        if 'Categories' in entry
                        else [],
                    }
                )
            return parsed

        result_places = []
        for result in places:
            if mode == 'raw':
                place_data = result
            else:
                contacts = parse_contacts(result.get('Contacts', {}))
                opening_hours = parse_opening_hours(result)
                place_data = {
                    'place_id': result.get('PlaceId', 'Not available'),
                    'name': result.get('Title', 'Not available'),
                    'address': result.get('Address', {}).get('Label', 'Not available'),
                    'coordinates': {
                        'longitude': result.get('Position', [None, None])[0],
                        'latitude': result.get('Position', [None, None])[1],
                    },
                    'categories': [cat.get('Name') for cat in result.get('Categories', [])]
                    if result.get('Categories')
                    else [],
                    'contacts': contacts,
                    'opening_hours': opening_hours,
                }
            result_places.append(place_data)
        result = {'query': query, 'places': result_places}
        return result
    except botocore.exceptions.ClientError as e:
        error_msg = f'Amazon geo-places Service error: {str(e)}'
        print(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}
    except Exception as e:
        error_msg = f'Error searching places: {str(e)}'
        print(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}


@mcp.tool()
async def get_place(
    ctx: Context,
    place_id: str = Field(description='The unique PlaceId for the place'),
    mode: str = Field(
        default='summary',
        description="Output mode: 'summary' (default) or 'raw' for all AWS fields",
    ),
) -> Dict:
    """Get details for a place using Amazon Location Service geo-places get_place API. Output is standardized and includes all fields, even if empty or not available."""
    if not geo_places_client.geo_places_client:
        error_msg = (
            'Amazon geo-places client not initialized. Please check AWS credentials and region.'
        )
        await ctx.error(error_msg)
        return {'error': error_msg}
    try:
        response = geo_places_client.geo_places_client.get_place(
            PlaceId=place_id, AdditionalFeatures=['Contact']
        )
        if mode == 'raw':
            return response
        contacts = {
            'phones': [p['Value'] for p in response.get('Contacts', {}).get('Phones', [])]
            if response.get('Contacts')
            else [],
            'websites': [w['Value'] for w in response.get('Contacts', {}).get('Websites', [])]
            if response.get('Contacts')
            else [],
            'emails': [e['Value'] for e in response.get('Contacts', {}).get('Emails', [])]
            if response.get('Contacts')
            else [],
            'faxes': [f['Value'] for f in response.get('Contacts', {}).get('Faxes', [])]
            if response.get('Contacts')
            else [],
        }

        def parse_opening_hours(result):
            oh = result.get('OpeningHours')
            if not oh:
                contacts = result.get('Contacts', {})
                oh = contacts.get('OpeningHours') if contacts else None
            if not oh:
                return []
            if isinstance(oh, dict):
                oh = [oh]
            parsed = []
            for entry in oh:
                parsed.append(
                    {
                        'display': entry.get('Display', []) or entry.get('display', []),
                        'components': entry.get('Components', []) or entry.get('components', []),
                        'open_now': entry.get('OpenNow', None),
                        'categories': [cat.get('Name') for cat in entry.get('Categories', [])]
                        if 'Categories' in entry
                        else [],
                    }
                )
            return parsed

        opening_hours = parse_opening_hours(response)
        result = {
            'name': response.get('Title', 'Not available'),
            'address': response.get('Address', {}).get('Label', 'Not available'),
            'contacts': contacts,
            'categories': [cat.get('Name', '') for cat in response.get('Categories', [])]
            if response.get('Categories')
            else [],
            'coordinates': {
                'longitude': response.get('Position', [None, None])[0],
                'latitude': response.get('Position', [None, None])[1],
            },
            'opening_hours': opening_hours,
        }
        return result
    except Exception as e:
        print(f'get_place error: {e}')
        await ctx.error(f'get_place error: {e}')
        return {'error': str(e)}


@mcp.tool()
async def reverse_geocode(
    ctx: Context,
    longitude: float = Field(description='Longitude of the location'),
    latitude: float = Field(description='Latitude of the location'),
) -> Dict:
    """Reverse geocode coordinates to an address using Amazon Location Service geo-places reverse_geocode API."""
    if not geo_places_client.geo_places_client:
        error_msg = (
            'Amazon geo-places client not initialized. Please check AWS credentials and region.'
        )
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}
    logger.debug(f'Reverse geocoding for longitude: {longitude}, latitude: {latitude}')
    try:
        response = geo_places_client.geo_places_client.reverse_geocode(
            QueryPosition=[longitude, latitude]
        )
        print(f'reverse_geocode raw response: {response}')
        place = response.get('Place', {})
        if not place:
            return {'raw_response': response}
        result = {
            'name': place.get('Label') or place.get('Title', 'Unknown'),
            'coordinates': {
                'longitude': place.get('Geometry', {}).get('Point', [0, 0])[0],
                'latitude': place.get('Geometry', {}).get('Point', [0, 0])[1],
            },
            'categories': [cat.get('Name') for cat in place.get('Categories', [])],
            'address': place.get('Address', {}).get('Label', ''),
        }
        logger.debug(f'Reverse geocoded address for coordinates: {longitude}, {latitude}')
        return result
    except botocore.exceptions.ClientError as e:
        error_msg = f'Amazon geo-places Service error: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}
    except Exception as e:
        error_msg = f'Error in reverse geocoding: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}


@mcp.tool()
async def search_nearby(
    ctx: Context,
    longitude: float = Field(description='Longitude of the center point'),
    latitude: float = Field(description='Latitude of the center point'),
    max_results: int = Field(
        default=5, description='Maximum number of results to return', ge=1, le=50
    ),
    query: Optional[str] = Field(default=None, description='Optional search query'),
    radius: int = Field(default=500, description='Search radius in meters', ge=1, le=50000),
) -> Dict:
    """Search for places near a location using Amazon Location Service geo-places search_nearby API. If no results, expand the radius up to max_radius. Output is standardized and includes all fields, even if empty or not available."""
    # Moved from parameters to local variables
    max_results = 5  # Maximum number of results to return
    max_radius = 10000  # Maximum search radius in meters for expansion
    expansion_factor = 2.0  # Factor to expand radius by if no results
    mode = 'summary'  # Output mode: 'summary' (default) or 'raw' for all AWS fields
    # Descriptions:
    # max_results: Maximum number of results to return (default=5, ge=1, le=50)
    # max_radius: Maximum search radius in meters for expansion (default=10000, ge=1, le=50000)
    # expansion_factor: Factor to expand radius by if no results (default=2.0, ge=1.1, le=10.0)
    # mode: Output mode: 'summary' (default) or 'raw' for all AWS fields
    if not geo_places_client.geo_places_client:
        error_msg = (
            'Amazon geo-places client not initialized. Please check AWS credentials and region.'
        )
        await ctx.error(error_msg)
        return {'error': error_msg}
    try:
        current_radius = radius
        while current_radius <= max_radius:
            params = {
                'QueryPosition': [longitude, latitude],
                'MaxResults': max_results,
                'QueryRadius': int(current_radius),
                'AdditionalFeatures': ['Contact'],
            }
            response = geo_places_client.geo_places_client.search_nearby(**params)
            items = response.get('ResultItems', [])
            results = []
            for item in items:
                if mode == 'raw':
                    results.append(item)
                else:
                    contacts = {
                        'phones': [p['Value'] for p in item.get('Contacts', {}).get('Phones', [])]
                        if item.get('Contacts')
                        else [],
                        'websites': [
                            w['Value'] for w in item.get('Contacts', {}).get('Websites', [])
                        ]
                        if item.get('Contacts')
                        else [],
                        'emails': [e['Value'] for e in item.get('Contacts', {}).get('Emails', [])]
                        if item.get('Contacts')
                        else [],
                        'faxes': [f['Value'] for f in item.get('Contacts', {}).get('Faxes', [])]
                        if item.get('Contacts')
                        else [],
                    }

                    def parse_opening_hours(result):
                        oh = result.get('OpeningHours')
                        if not oh:
                            contacts = result.get('Contacts', {})
                            oh = contacts.get('OpeningHours') if contacts else None
                        if not oh:
                            return []
                        if isinstance(oh, dict):
                            oh = [oh]
                        parsed = []
                        for entry in oh:
                            parsed.append(
                                {
                                    'display': entry.get('Display', [])
                                    or entry.get('display', []),
                                    'components': entry.get('Components', [])
                                    or entry.get('components', []),
                                    'open_now': entry.get('OpenNow', None),
                                    'categories': [
                                        cat.get('Name') for cat in entry.get('Categories', [])
                                    ]
                                    if 'Categories' in entry
                                    else [],
                                }
                            )
                        return parsed

                    opening_hours = parse_opening_hours(item)
                    results.append(
                        {
                            'place_id': item.get('PlaceId', 'Not available'),
                            'name': item.get('Title', 'Not available'),
                            'address': item.get('Address', {}).get('Label', 'Not available'),
                            'coordinates': {
                                'longitude': item.get('Position', [None, None])[0],
                                'latitude': item.get('Position', [None, None])[1],
                            },
                            'categories': [cat.get('Name') for cat in item.get('Categories', [])]
                            if item.get('Categories')
                            else [],
                            'contacts': contacts,
                            'opening_hours': opening_hours,
                        }
                    )
            if results:
                return {'places': results, 'radius_used': current_radius}
            current_radius *= expansion_factor
        return {'places': [], 'radius_used': current_radius / expansion_factor}
    except Exception as e:
        print(f'search_nearby error: {e}')
        await ctx.error(f'search_nearby error: {e}')
        return {'error': str(e)}


@mcp.tool()
async def search_places_open_now(
    ctx: Context,
    query: str = Field(description='Search query (address, place name, etc.)'),
    initial_radius: int = Field(
        default=500, description='Initial search radius in meters for expansion', ge=1, le=50000
    ),
) -> Dict:
    """Search for places that are open now using Amazon Location Service geo-places search_text API and filter by opening hours. If no open places, expand the search radius up to max_radius. Uses BiasPosition from geocode."""
    # Moved from parameters to local variables
    max_results = 5  # Maximum number of results to return
    max_radius = 50000  # Maximum search radius in meters for expansion
    expansion_factor = 2.0  # Factor to expand radius by if no open places
    # Descriptions:
    # max_results: Maximum number of results to return (default=5, ge=1, le=50)
    # max_radius: Maximum search radius in meters for expansion (default=50000, ge=1, le=50000)
    # expansion_factor: Factor to expand radius by if no open places (default=2.0, ge=1.1, le=10.0)
    if not geo_places_client.geo_places_client:
        error_msg = (
            'Amazon geo-places client not initialized. Please check AWS credentials and region.'
        )
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}
    logger.debug(f'Searching for places open now with query: {query}, max_results: {max_results}')
    try:
        geo_response = geo_places_client.geo_places_client.geocode(QueryText=query)
        geo_items = geo_response.get('ResultItems', [])
        if not geo_items:
            error_msg = f'Could not geocode query "{query}" for BiasPosition.'
            logger.error(error_msg)
            await ctx.error(error_msg)
            return {'error': error_msg}
        bias_position = geo_items[0]['Position']
        current_radius = initial_radius
        open_places = []
        all_places = []
        first_attempt = True
        while current_radius <= max_radius and len(open_places) < max_results:
            search_kwargs = {
                'QueryText': query,
                'MaxResults': max_results * 2,  # Fetch more to allow filtering
                'AdditionalFeatures': ['Contact'],
            }
            if first_attempt:
                # Use BiasPosition for the first (smallest) search
                search_kwargs['BiasPosition'] = bias_position
                first_attempt = False
            else:
                # Use Filter.Circle for expanded radius searches
                search_kwargs['Filter'] = {
                    'Circle': {'Center': bias_position, 'Radius': int(current_radius)}
                }
            response = geo_places_client.geo_places_client.search_text(**search_kwargs)
            result_items = response.get('ResultItems', [])
            for idx, result in enumerate(result_items):
                opening_hours = result.get('OpeningHours')
                open_now = False
                opening_hours_info = []
                if isinstance(opening_hours, list):
                    for oh in opening_hours:
                        display = oh.get('Display', [])
                        is_open = oh.get('OpenNow', False)
                        categories = (
                            [cat.get('Name') for cat in oh.get('Categories', [])]
                            if 'Categories' in oh
                            else []
                        )
                        opening_hours_info.append(
                            {'display': display, 'open_now': is_open, 'categories': categories}
                        )
                        if is_open:
                            open_now = True
                elif isinstance(opening_hours, dict):
                    display = opening_hours.get('Display', [])
                    is_open = opening_hours.get('OpenNow', False)
                    categories = (
                        [cat.get('Name') for cat in opening_hours.get('Categories', [])]
                        if 'Categories' in opening_hours
                        else []
                    )
                    opening_hours_info.append(
                        {'display': display, 'open_now': is_open, 'categories': categories}
                    )
                    if is_open:
                        open_now = True
                if not open_now and 'Contacts' in result:
                    contacts = result['Contacts']
                    ch = contacts.get('OpeningHours')
                    if isinstance(ch, list):
                        for oh in ch:
                            if oh.get('OpenNow', False):
                                open_now = True
                                break
                    elif isinstance(ch, dict):
                        if ch.get('OpenNow', False):
                            open_now = True
                place_data = {
                    'place_id': result.get('PlaceId', ''),
                    'name': result.get('Title', 'Unknown'),
                    'coordinates': {
                        'longitude': result.get('Position', [0, 0])[0],
                        'latitude': result.get('Position', [0, 0])[1],
                    },
                    'address': result.get('Address', {}).get('Label', ''),
                    'country': result.get('Address', {}).get('Country', {}).get('Name', ''),
                    'region': result.get('Address', {}).get('Region', {}).get('Name', ''),
                    'municipality': result.get('Address', {}).get('Locality', ''),
                    'categories': [cat.get('Name') for cat in result.get('Categories', [])],
                    'contacts': result.get('Contacts', {}),
                    'opening_hours': opening_hours_info,
                    'open_now': open_now,
                }
                all_places.append(place_data)
                if open_now and len(open_places) < max_results:
                    open_places.append(place_data)
            if open_places:
                break
            current_radius *= expansion_factor
        if not open_places:
            print(
                'search_places_open_now: No places found open now after expanding radius. Check OpeningHours and OpenNow fields above.'
            )
        result = {
            'query': query,
            'open_places': open_places,
            'all_places': all_places,
            'radius_used': current_radius / expansion_factor,
        }
        logger.debug(f'Found {len(open_places)} places open now for query: {query}')
        return result
    except botocore.exceptions.ClientError as e:
        error_msg = f'Amazon geo-places Service error: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}
    except Exception as e:
        error_msg = f'Error searching for open places: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': str(e)}


@mcp.tool()
async def calculate_route(
    ctx: Context,
    departure_position: list = Field(description='Departure position as [longitude, latitude]'),
    destination_position: list = Field(description='Destination position as [longitude, latitude]'),
    travel_mode: str = Field(default='Car', description="Travel mode: 'Car', 'Truck', 'Walking', or 'Bicycle' (default: 'Car')"),
    optimize_for: str = Field(default='FastestRoute', description="Optimize route for 'FastestRoute' or 'ShortestRoute' (default: 'FastestRoute')")
) -> dict:
    """
    Calculate a route and return summary info and turn-by-turn directions.
    Parameters:
        departure_position: [lon, lat]
        destination_position: [lon, lat]
        travel_mode: 'Car', 'Truck', 'Walking', or 'Bicycle' (default: 'Car')
        optimize_for: 'FastestRoute' or 'ShortestRoute' (default: 'FastestRoute')
    Returns:
        dict with distance, duration, and turn_by_turn directions (list of step summaries)
    """
    include_leg_geometry = False
    mode = 'summary'
    client = GeoRoutesClient().geo_routes_client
    
    # Check if client is None before proceeding
    if client is None:
        return {'error': 'Failed to initialize Amazon geo-routes client'}
    
    params = {
        'Origin': departure_position,
        'Destination': destination_position,
        'TravelMode': travel_mode,
        'TravelStepType': 'TurnByTurn',
        'OptimizeRoutingFor': optimize_for,
    }
    if include_leg_geometry:
        params['LegGeometryFormat'] = 'FlexiblePolyline'
    try:
        response = await asyncio.to_thread(client.calculate_routes, **params)
        if mode == 'raw':
            return response
        routes = response.get('Routes', [])
        if not routes:
            return {'error': 'No route found'}
        route = routes[0]
        distance_meters = route.get('Distance', None)
        duration_seconds = route.get('DurationSeconds', None)
        turn_by_turn = []
        for leg in route.get('Legs', []):
            vehicle_leg_details = leg.get('VehicleLegDetails', {})
            for step in vehicle_leg_details.get('TravelSteps', []):
                step_summary = {
                    'distance_meters': step.get('Distance'),
                    'duration_seconds': step.get('Duration'),
                    'type': step.get('Type'),
                    'road_name': step.get('NextRoad', {}).get('RoadName') if step.get('NextRoad') else None,
                }
                turn_by_turn.append(step_summary)
        return {
            'distance_meters': distance_meters,
            'duration_seconds': duration_seconds,
            'turn_by_turn': turn_by_turn,
        }
    except Exception as e:
        return {'error': str(e)}


@mcp.tool()
async def optimize_waypoints(
    ctx: Context,
    origin_position: list = Field(description='Origin position as [longitude, latitude]'),
    destination_position: list = Field(description='Destination position as [longitude, latitude]'),
    waypoints: list = Field(description='List of intermediate waypoints, each as a dict with at least Position [longitude, latitude], optionally Id'),
    travel_mode: str = Field(default='Car', description="Travel mode: 'Car', 'Truck', 'Walking', or 'Bicycle' (default: 'Car')"),
    mode: str = Field(default='summary', description="Output mode: 'summary' (default) or 'raw' for all AWS fields"),
) -> Dict:
    """
    Optimize the order of waypoints using Amazon Location Service geo-routes optimize_waypoints API (V2).
    Returns summary (optimized order, total distance, duration, etc.) or full response if mode='raw'.
    """
    client = GeoRoutesClient().geo_routes_client
    
    # Check if client is None before proceeding
    if client is None:
        return {'error': 'Failed to initialize Amazon geo-routes client'}
    
    params = {
        'Origin': origin_position,
        'Destination': destination_position,
        'Waypoints': [{'Position': wp['Position']} for wp in waypoints],
        'TravelMode': travel_mode,
    }
    try:
        response = await asyncio.to_thread(client.optimize_waypoints, **params)
        if mode == 'raw':
            return response
        routes = response.get('Routes', [])
        if not routes:
            return {'error': 'No route found'}
        route = routes[0]
        distance_meters = route.get('Distance', None)
        duration_seconds = route.get('DurationSeconds', None)
        optimized_order = [wp.get('Position') for wp in route.get('Waypoints', [])]
        return {
            'distance_meters': distance_meters,
            'duration_seconds': duration_seconds,
            'optimized_order': optimized_order,
        }
    except Exception as e:
        # import traceback
        # return {'error': str(e), 'traceback': traceback.format_exc()}
        return {'error': str(e)}


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for Amazon Location Service (geo-places)'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')
    args = parser.parse_args()
    logger.info('Starting Amazon Location Service MCP Server (geo-places)')
    if args.sse:
        logger.info(f'Using SSE transport on port {args.port}')
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        logger.info('Using standard stdio transport')
        mcp.run()


if __name__ == '__main__':
    main()
