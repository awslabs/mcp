# AWS Location Service MCP Server

Model Context Protocol (MCP) server for AWS Location Service

This MCP server provides tools to access AWS Location Service capabilities, focusing on place search, geographical coordinates, and route planning.

## Features

- **Search for Places**: Search for places using geocoding
- **Get Place Details**: Get details for specific places by PlaceId
- **Reverse Geocode**: Convert coordinates to addresses
- **Search Nearby**: Search for places near a specified location
- **Open Now Search**: Search for places that are currently open
- **Route Calculation**: Calculate routes between locations with turn-by-turn directions
- **Waypoint Optimization**: Optimize the order of waypoints for efficient routing

## Prerequisites

### Requirements

1. Have an AWS account with AWS Location Service enabled
2. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
3. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)

## Installation

Here are the ways you can work with the AWS Location MCP server:

## Configuration

Configure the server in your MCP configuration file. Here are some ways you can work with MCP across AWS, and we'll be adding support to more products soon: (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.aws-location-mcp-server": {
        "command": "uvx",
        "args": ["awslabs.aws-location-mcp-server@latest"],
        "env": {
          "AWS_PROFILE": "your-aws-profile",
          "AWS_REGION": "us-east-1",
          "FASTMCP_LOG_LEVEL": "ERROR"
        },
        "disabled": false,
        "autoApprove": []
    }
  }
}
```

### Docker Configuration

After building with `docker build -t awslabs/aws-location-mcp-server .`:

```json
{
  "mcpServers": {
    "awslabs.aws-location-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "-i",
          "awslabs/aws-location-mcp-server"
        ],
        "env": {
          "AWS_PROFILE": "your-aws-profile",
          "AWS_REGION": "us-east-1"
        },
        "disabled": false,
        "autoApprove": []
    }
  }
}
```

### Environment Variables

- `AWS_PROFILE`: AWS CLI profile to use for credentials
- `AWS_REGION`: AWS region to use (default: us-east-1)
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`: Explicit AWS credentials (alternative to AWS_PROFILE)
- `FASTMCP_LOG_LEVEL`: Logging level (ERROR, WARNING, INFO, DEBUG)

## Tools

The server exposes the following tools through the MCP interface:

### search_places

Search for places using AWS Location Service geocoding capabilities.

```python
search_places(query: str, max_results: int = 5, mode: str = 'summary') -> dict
```

### get_place

Get details for a specific place using its unique place ID.

```python
get_place(place_id: str, mode: str = 'summary') -> dict
```

### reverse_geocode

Convert coordinates to an address using reverse geocoding.

```python
reverse_geocode(longitude: float, latitude: float) -> dict
```

### search_nearby

Search for places near a specific location with optional radius expansion.

```python
search_nearby(longitude: float, latitude: float, radius: int = 500, max_results: int = 5,
              query: str = None, max_radius: int = 10000, expansion_factor: float = 2.0,
              mode: str = 'summary') -> dict
```

### search_places_open_now

Search for places that are currently open, with radius expansion if needed.

```python
search_places_open_now(query: str, max_results: int = 5, initial_radius: int = 500,
                       max_radius: int = 50000, expansion_factor: float = 2.0) -> dict
```

### calculate_route

Calculate a route between two locations with turn-by-turn directions.

```python
calculate_route(
    departure_position: list,  # [longitude, latitude]
    destination_position: list,  # [longitude, latitude]
    travel_mode: str = 'Car',  # 'Car', 'Truck', 'Walking', or 'Bicycle'
    optimize_for: str = 'FastestRoute'  # 'FastestRoute' or 'ShortestRoute'
) -> dict
```

Returns:
- `distance_meters`: Total route distance in meters
- `duration_seconds`: Estimated travel time in seconds
- `legs`: List of route legs with distance and duration
- `turn_by_turn`: List of navigation instructions with:
  - `distance_meters`: Distance for this step
  - `duration_seconds`: Duration for this step
  - `type`: Maneuver type (e.g., 'Straight', 'Turn')
  - `road_name`: Name of the road for this step

Example usage:
```python
route = await calculate_route(
    ctx,
    departure_position=[-122.335167, 47.608013],  # Seattle
    destination_position=[-122.200676, 47.610149],  # Bellevue
    travel_mode='Car',
    optimize_for='FastestRoute'
)
```

### optimize_waypoints

Optimize the order of waypoints for efficient routing.

```python
optimize_waypoints(
    origin_position: list,  # [longitude, latitude]
    destination_position: list,  # [longitude, latitude]
    waypoints: list,  # List of waypoints, each as a dict with 'Id' and 'Position' [longitude, latitude]
    travel_mode: str = 'Car',
    mode: str = 'summary'
) -> dict
```

Returns:
- `optimized_order`: List of waypoint IDs in optimized order
- `total_distance_meters`: Total route distance in meters
- `total_duration_seconds`: Total estimated travel time in seconds
- `waypoints`: List of waypoints with arrival and departure times

Example usage:
```python
result = await optimize_waypoints(
    ctx,
    origin_position=[-122.335167, 47.608013],  # Seattle
    destination_position=[-122.121513, 47.673988],  # Redmond
    waypoints=[
        {'Id': 'bellevue', 'Position': [-122.200676, 47.610149]},
        {'Id': 'kirkland', 'Position': [-122.209032, 47.676607]}
    ],
    travel_mode='Car'
)
```

### get_coordinates

Get coordinates for a location name or address.

```python
get_coordinates(location: str) -> dict
```

## AWS Location Service Resources

This server uses the AWS Location Service APIs for:
- Geocoding (converting addresses to coordinates)
- Reverse geocoding (converting coordinates to addresses)
- Place search (finding places by name, category, etc.)
- Place details (getting information about specific places)
- Route calculation (finding routes between locations with turn-by-turn directions)
- Waypoint optimization (determining the most efficient order to visit multiple locations)

## Security Considerations

- Use AWS profiles for credential management
- Use IAM policies to restrict access to only the required AWS Location Service resources
- Consider using temporary credentials or AWS IAM roles for enhanced security
