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
- **Geofencing**: Create and manage geofence collections, define geofences, and evaluate device positions

## Prerequisites

### Requirements

1. Have an AWS account with Amazon Location Service enabled
2. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
3. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)

## Installation

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-location-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-location-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-location-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWxvY2F0aW9uLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Location%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-location-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Here are the ways you can work with the Amazon Location MCP server:

## Configuration

Configure the server in your MCP configuration file. Here are some ways you can work with MCP across AWS, and we'll be adding support to more products soon: (e.g. for Kiro, `~/.kiro/settings/mcp.json`):

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
### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.aws-location-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-location-mcp-server@latest",
        "awslabs.aws-location-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
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

### geocode

Get coordinates for a location name or address.

```python
geocode(location: str) -> dict
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

## Geofencing Tools

### create_geofence_collection

Create a new geofence collection to store geofences.

```python
create_geofence_collection(collection_name: str, description: str = None) -> dict
```
Returns collection_name, collection_arn, and create_time.

### list_geofence_collections

List all geofence collections in the account.

```python
list_geofence_collections(max_results: int = 10) -> dict
```
Returns a list of collections with collection_name, collection_arn, and create_time.

### describe_geofence_collection

Get details about a specific geofence collection.

```python
describe_geofence_collection(collection_name: str) -> dict
```
Returns collection details including collection_name, collection_arn, description, create_time, and update_time.

### delete_geofence_collection

Delete a geofence collection and all its geofences.

```python
delete_geofence_collection(collection_name: str) -> dict
```
Returns success status and collection_name.

### put_geofence

Create or update a geofence in a collection.

```python
put_geofence(
    collection_name: str,
    geofence_id: str,
    geometry_type: str,  # 'Circle' or 'Polygon'
    circle_center: list = None,  # [longitude, latitude] for Circle geometry
    circle_radius: float = None,  # Radius in meters for Circle geometry
    polygon_ring: list = None,  # List of [longitude, latitude] coordinates for Polygon geometry
    properties: dict = None  # Optional custom properties
) -> dict
```
Returns geofence_id, create_time, and update_time.

**Circle Geometry Example:**
```python
put_geofence(
    collection_name='my-collection',
    geofence_id='warehouse-zone',
    geometry_type='Circle',
    circle_center=[-122.3321, 47.6062],
    circle_radius=1000.0  # 1km radius
)
```

**Polygon Geometry Example:**
```python
put_geofence(
    collection_name='my-collection',
    geofence_id='delivery-zone',
    geometry_type='Polygon',
    polygon_ring=[
        [-122.3321, 47.6062],
        [-122.3421, 47.6062],
        [-122.3421, 47.6162],
        [-122.3321, 47.6162],
        [-122.3321, 47.6062]  # Must close the ring
    ]
)
```

### get_geofence

Get details about a specific geofence.

```python
get_geofence(collection_name: str, geofence_id: str) -> dict
```
Returns geofence_id, geometry, status, create_time, and update_time.

### list_geofences

List all geofences in a collection.

```python
list_geofences(collection_name: str, max_results: int = 10) -> dict
```
Returns a list of geofences with geofence_id, geometry, status, and create_time.

### batch_delete_geofences

Delete multiple geofences from a collection.

```python
batch_delete_geofences(collection_name: str, geofence_ids: list) -> dict
```
Returns lists of successfully deleted geofence IDs and any errors.

### batch_evaluate_geofences

Evaluate device positions against geofences to detect entry/exit events.

```python
batch_evaluate_geofences(
    collection_name: str,
    device_position_updates: list  # List of dicts with device_id, position [lon, lat], sample_time
) -> dict
```
Returns evaluation results with device_id, geofence_id, and event_type ('ENTER' or 'EXIT').

**Example:**
```python
batch_evaluate_geofences(
    collection_name='my-collection',
    device_position_updates=[
        {
            'device_id': 'truck-001',
            'position': [-122.3321, 47.6062],
            'sample_time': '2024-01-15T10:30:00Z'
        }
    ]
)
```

### forecast_geofence_events

Predict when a device will enter or exit geofences based on its current position and speed.

```python
forecast_geofence_events(
    collection_name: str,
    device_id: str,
    device_state: dict,  # Dict with position [lon, lat] and speed (m/s)
    time_horizon_minutes: int = 30
) -> dict
```
Returns forecasted events with geofence_id, event_type, and forecasted_time.

**Example:**
```python
forecast_geofence_events(
    collection_name='my-collection',
    device_id='truck-001',
    device_state={
        'position': [-122.3321, 47.6062],
        'speed': 15.0  # meters per second
    },
    time_horizon_minutes=60
)
```

## Use Cases

### Geofencing Use Cases

- **Delivery Zone Management**: Define delivery zones and track when drivers enter/exit
- **Restricted Area Monitoring**: Alert when devices enter restricted areas
- **Fleet Tracking**: Monitor vehicle positions against predefined routes and zones
- **Asset Tracking**: Track when assets move in or out of designated areas
- **Event Forecasting**: Predict arrival times based on current position and speed

## Amazon Location Service Resources

This server uses the Amazon Location Service APIs for:
- Geocoding (converting addresses to coordinates)
- Reverse geocoding (converting coordinates to addresses)
- Place search (finding places by name, category, etc.)
- Place details (getting information about specific places)
- Route calculation (finding routes between locations)
- Geofencing (creating geofences and evaluating device positions)

## Security Considerations

- Use AWS profiles for credential management
- Use IAM policies to restrict access to only the required Amazon Location Service resources
- Use temporary credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_SESSION_TOKEN) from AWS STS for enhanced security
- Implement AWS IAM roles with temporary credentials for applications and services
- Regularly rotate credentials and use the shortest practical expiration time for temporary credentials
