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
"""AWS Location Service MCP Server implementation."""

import argparse
import os
import sys
from typing import Dict, List, Optional

import boto3
import botocore.config
import botocore.exceptions
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field


# Set up logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

# Initialize FastMCP server
mcp = FastMCP(
    'awslabs.aws-location-mcp-server',
    instructions="""
    # AWS Location Service MCP Server

    This server provides tools to interact with AWS Location Service capabilities, focusing on place search and geographical coordinates.

    ## Features

    - Search for places using geocoding
    - Get coordinates for locations

    ## Prerequisites

    Before using this MCP server, you need to:

    1. Have an AWS account with AWS Location Service enabled
    2. Create a Place Index in AWS Location Service (or the server will attempt to use an existing one)
    3. Configure AWS CLI with your credentials and profile

    ## Best Practices

    - For place searches, provide specific location details for more accurate results
    - When searching for coordinates, include country or region information for better accuracy
    - Use the search_places tool when you need multiple results for a query
    - Use the get_coordinates tool when you need detailed information about a specific location
    """,
    dependencies=[
        'boto3',
        'pydantic',
    ],
)


class LocationClient:
    """AWS Location Service client wrapper."""

    def __init__(self):
        """Initialize the AWS Location Service client."""
        # Get AWS region from environment variable or use default
        self.aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Initialize client
        self.location_client = None
        
        # Check for AWS credentials in environment variables
        aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        
        # Set a timeout for boto3 operations
        config = botocore.config.Config(
            connect_timeout=15,
            read_timeout=15,
            retries={'max_attempts': 3}
        )
        
        # Try to initialize the client using explicit credentials if available
        try:
            if aws_access_key and aws_secret_key:
                # Create client with explicit credentials
                client_args = {
                    'aws_access_key_id': aws_access_key,
                    'aws_secret_access_key': aws_secret_key,
                    'region_name': self.aws_region,
                    'config': config
                }
                
                self.location_client = boto3.client('location', **client_args)
            else:
                # Fall back to default credential resolution
                self.location_client = boto3.client('location', region_name=self.aws_region, config=config)
                
            logger.debug(f"AWS Location client initialized for region {self.aws_region}")
        except Exception as e:
            logger.error(f"Failed to initialize AWS Location client: {str(e)}")
            self.location_client = None
        
        # Get place index from environment variable or use default
        self.default_place_index = os.environ.get('AWS_LOCATION_PLACE_INDEX', 'ExamplePlaceIndex')
        logger.debug(f"Using place index: {self.default_place_index}")


# Initialize the location client
location_client = LocationClient()


@mcp.tool()
async def search_places(
    ctx: Context,
    query: str = Field(description="Search query (address, place name, etc.)"),
    max_results: int = Field(
        default=5,
        description="Maximum number of results to return",
        ge=1,
        le=50,
    ),
) -> Dict:
    """Search for places using AWS Location Service.

    ## Usage

    This tool searches for places using AWS Location Service geocoding capabilities.
    It's useful for finding locations based on text queries like addresses, landmarks, or place names.

    ## Search Tips

    - Include country or region information for more accurate results
    - For addresses, include as much detail as possible
    - For landmarks, include the city or region name

    ## Result Interpretation

    The results include:
    - query: The original search query
    - places: A list of places matching the query, each containing:
      - name: The formatted name/address of the place
      - coordinates: Longitude and latitude
      - country: Country code or name
      - region: State/province/region
      - municipality: City/town

    Args:
        ctx: MCP context for logging and error handling
        query: Search query (address, place name, etc.)
        max_results: Maximum number of results to return (1-50)

    Returns:
        Dictionary containing the search results
    """
    if not location_client.location_client:
        error_msg = "AWS Location client not initialized. Please check AWS credentials and region."
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {"error": error_msg}
    
    logger.debug(f"Searching places with query: {query}, max_results: {max_results}")
    
    try:
        # Call AWS Location Service
        response = location_client.location_client.search_place_index_for_text(
            IndexName=location_client.default_place_index,
            Text=query,
            MaxResults=max_results
        )
        
        # Process results
        places = []
        for result in response.get('Results', []):
            place = result.get('Place', {})
            
            # Extract place details
            place_data = {
                'name': place.get('Label', 'Unknown'),
                'coordinates': {
                    'longitude': place.get('Geometry', {}).get('Point', [0, 0])[0],
                    'latitude': place.get('Geometry', {}).get('Point', [0, 0])[1]
                },
                'country': place.get('Country', ''),
                'region': place.get('Region', ''),
                'municipality': place.get('Municipality', '')
            }
            places.append(place_data)
        
        result = {
            'query': query,
            'places': places
        }
        
        logger.debug(f"Found {len(places)} places for query: {query}")
        return result
        
    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_msg = str(e)
        
        if error_code == "ResourceNotFoundException" and "place index" in error_msg.lower():
            error_msg = f"Place index not found. Please create a place index in AWS Location Service or specify one with AWS_LOCATION_PLACE_INDEX environment variable."
        else:
            error_msg = f"AWS Location Service error: {error_msg}"
            
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {"error": error_msg}
        
    except Exception as e:
        error_msg = f"Error searching places: {str(e)}"
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {"error": error_msg}


@mcp.tool()
async def get_coordinates(
    ctx: Context,
    location: str = Field(description="Location name (city, address, landmark, etc.)"),
) -> Dict:
    """Get coordinates for a location.

    ## Usage

    This tool retrieves the geographical coordinates (latitude and longitude) for a specified location.
    It's useful when you need precise location data for a specific place.

    ## Location Tips

    - Include country or region information for more accurate results
    - For addresses, include as much detail as possible
    - For landmarks, include the city or region name

    ## Result Interpretation

    The result includes:
    - location: The original location query
    - formatted_address: The formatted address of the location
    - coordinates: Longitude and latitude
    - country: Country code or name
    - region: State/province/region
    - municipality: City/town

    Args:
        ctx: MCP context for logging and error handling
        location: Location name (city, address, landmark, etc.)

    Returns:
        Dictionary containing the location details and coordinates
    """
    if not location_client.location_client:
        error_msg = "AWS Location client not initialized. Please check AWS credentials and region."
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {"error": error_msg}
    
    logger.debug(f"Getting coordinates for location: {location}")
    
    try:
        # Search for the location using AWS Location Service
        response = location_client.location_client.search_place_index_for_text(
            IndexName=location_client.default_place_index,
            Text=location,
            MaxResults=1
        )
        
        if not response.get('Results') or len(response['Results']) == 0:
            error_msg = f"No results found for location: {location}"
            logger.error(error_msg)
            await ctx.error(error_msg)
            return {"error": error_msg}
        
        place = response['Results'][0]['Place']
        coordinates = place['Geometry']['Point']  # [longitude, latitude]
        
        result = {
            'location': location,
            'formatted_address': place.get('Label', ''),
            'coordinates': {
                'longitude': coordinates[0],
                'latitude': coordinates[1]
            },
            'country': place.get('Country', ''),
            'region': place.get('Region', ''),
            'municipality': place.get('Municipality', '')
        }
        
        logger.debug(f"Found coordinates for location: {location}")
        return result
        
    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_msg = str(e)
        
        if error_code == "ResourceNotFoundException" and "place index" in error_msg.lower():
            error_msg = f"Place index not found. Please create a place index in AWS Location Service or specify one with AWS_LOCATION_PLACE_INDEX environment variable."
        else:
            error_msg = f"AWS Location Service error: {error_msg}"
            
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {"error": error_msg}
        
    except Exception as e:
        error_msg = f"Error getting coordinates: {str(e)}"
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {"error": error_msg}


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for AWS Location Service'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()

    # Log startup information
    logger.info('Starting AWS Location Service MCP Server')

    # Run server with appropriate transport
    if args.sse:
        logger.info(f'Using SSE transport on port {args.port}')
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        logger.info('Using standard stdio transport')
        mcp.run()


if __name__ == '__main__':
    main()
