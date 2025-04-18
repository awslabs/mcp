# AWS Location Service MCP Server

A Model Context Protocol (MCP) server that provides access to AWS Location Service capabilities, focusing on place search and geographical coordinates.

## Features

- Search for places using geocoding
- Get coordinates for locations

## Prerequisites

Before using this MCP server, you need to:

1. Have an AWS account with AWS Location Service enabled
2. Create a Place Index in AWS Location Service (or the server will attempt to use an existing one)
3. Configure AWS CLI with your credentials and profile

## Installation

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .
```

## Configuration

Configure the server in your MCP settings:

```json
{
  "aws-location-mcp-server": {
    "command": "/path/to/venv/bin/python",
    "args": ["-m", "awslabs.aws_location_server.server"],
    "env": {
      "AWS_PROFILE": "your-aws-profile",
      "AWS_REGION": "us-east-1",
      "AWS_LOCATION_PLACE_INDEX": "your-place-index-name"
    },
    "disabled": false,
    "autoApprove": []
  }
}
```

### Environment Variables

- `AWS_PROFILE`: AWS CLI profile to use for credentials
- `AWS_REGION`: AWS region to use (default: us-east-1)
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`: Explicit AWS credentials (alternative to AWS_PROFILE)
- `AWS_LOCATION_PLACE_INDEX`: Name of the AWS Location Service Place Index to use (default: ExamplePlaceIndex)

## Tools

### search_places

Search for places using AWS Location Service geocoding.

**Parameters:**
- `query` (required): Search query (address, place name, etc.)
- `max_results` (optional): Maximum number of results to return (1-50, default: 5)

**Example:**
```json
{
  "query": "Empire State Building",
  "max_results": 3
}
```

### get_coordinates

Get coordinates for a specific location.

**Parameters:**
- `location` (required): Location name (city, address, landmark, etc.)

**Example:**
```json
{
  "location": "Quebec City, Canada"
}
```

**Response includes:**
- Location name
- Formatted address
- Coordinates (longitude, latitude)
- Country, region, and municipality information

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/awslabs/mcp.git
cd mcp/src/aws-location-mcp-server

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run tests with coverage
./run_tests.sh

# Or manually
python -m pytest tests/ -v --cov=awslabs --cov-report=term-missing
```

## AWS Location Service Resources

This server uses the following AWS Location Service resource:

**Place Index**: Used for geocoding and place search
- Create in AWS Console: Amazon Location Service > Place indexes > Create place index
- Recommended data provider: Esri or HERE
- If not specified, the server will attempt to use an existing place index

## Security Considerations

- Use AWS profiles for credential management
- Use IAM policies to restrict access to only the required AWS Location Service resources
- Consider using temporary credentials or AWS IAM roles for enhanced security
