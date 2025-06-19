# Amazon Location Service MCP Server

Model Context Protocol (MCP) server for Amazon Location Service

This MCP server provides tools to access Amazon Location Service capabilities, focusing on place search and geographical coordinates.

## Features

- **Search for Places**: Search for places using geocoding
- **Get Place Details**: Get details for specific places by PlaceId
- **Reverse Geocode**: Convert coordinates to addresses
- **Search Nearby**: Search for places near a specified location
- **Open Now Search**: Search for places that are currently open
- **Route Calculation**: Calculate routes between locations using Amazon Location Service
- **Optimize Waypoints**: Optimize the order of waypoints for a route using Amazon Location Service

## Prerequisites

### Requirements

1. Have an AWS account with Amazon Location Service enabled
2. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
3. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)

## Installation

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.aws-location-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWxvY2F0aW9uLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D)

Here are the ways you can work with the Amazon Location MCP server:

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

### Using Temporary Credentials

For temporary credentials (such as those from AWS STS, IAM roles, or federation):


```json
{
  "mcpServers": {
    "awslabs.aws-location-mcp-server": {
        "command": "uvx",
        "args": ["awslabs.aws-location-mcp-server@latest"],
        "env": {
          "AWS_ACCESS_KEY_ID": "your-temporary-access-key",
          "AWS_SECRET_ACCESS_KEY": "your-temporary-secret-key",
          "AWS_SESSION_TOKEN": "your-session-token",
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

### Docker with Temporary Credentials

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
          "AWS_ACCESS_KEY_ID": "your-temporary-access-key",
          "AWS_SECRET_ACCESS_KEY": "your-temporary-secret-key",
          "AWS_SESSION_TOKEN": "your-session-token",
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
- `AWS_SESSION_TOKEN`: Session token for temporary credentials (used with AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)
- `FASTMCP_LOG_LEVEL`: Logging level (ERROR, WARNING, INFO, DEBUG)

## Tools

The server exposes the following tools through the MCP interface:

### search_places

Search for places using Amazon Location Service geocoding capabilities.

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

Calculate a route between two locations using Amazon Location Service.

```python
calculate_route(
    departure_position: list,  # [longitude, latitude]
    destination_position: list,  # [longitude, latitude]
    travel_mode: str = 'Car',  # 'Car', 'Truck', 'Walking', or 'Bicycle'
    optimize_for: str = 'FastestRoute'  # 'FastestRoute' or 'ShortestRoute'
) -> dict
```
Returns route geometry, distance, duration, and turn-by-turn directions.

- `departure_position`: List of [longitude, latitude] for the starting point.
- `destination_position`: List of [longitude, latitude] for the destination.
- `travel_mode`: Travel mode, one of `'Car'`, `'Truck'`, `'Walking'`, or `'Bicycle'`.
- `optimize_for`: Route optimization, either `'FastestRoute'` or `'ShortestRoute'`.

See [AWS documentation](https://docs.aws.amazon.com/location/latest/developerguide/calculate-routes-custom-avoidance-shortest.html) for more details.

### get_coordinates

Get coordinates for a location name or address.

```python
get_coordinates(location: str) -> dict
```

### optimize_waypoints

Optimize the order of waypoints using Amazon Location Service geo-routes API.

```python
optimize_waypoints(
    origin_position: list,  # [longitude, latitude]
    destination_position: list,  # [longitude, latitude]
    waypoints: list,  # List of waypoints, each as a dict with at least Position [longitude, latitude]
    travel_mode: str = 'Car',
    mode: str = 'summary'
) -> dict
```
Returns the optimized order of waypoints, total distance, and duration.

## Amazon Location Service Resources

This server uses the Amazon Location Service geo-places and route calculation APIs for:
- Geocoding (converting addresses to coordinates)
- Reverse geocoding (converting coordinates to addresses)
- Place search (finding places by name, category, etc.)
- Place details (getting information about specific places)
- **Route calculation (finding routes between locations)**

## Security Considerations

- Use AWS profiles for credential management
- Use IAM policies to restrict access to only the required Amazon Location Service resources
- Use temporary credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_SESSION_TOKEN) from AWS STS for enhanced security
- Implement AWS IAM roles with temporary credentials for applications and services
- Regularly rotate credentials and use the shortest practical expiration time for temporary credentials
