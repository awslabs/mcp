# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-05-26

### Removed

- **BREAKING CHANGE:** Server Sent Events (SSE) support has been removed in accordance with the Model Context Protocol specification's [backwards compatibility guidelines](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility)
- This change prepares for future support of [Streamable HTTP](https://modelcontextprotocol.io/specification/draft/basic/transports#streamable-http) transport

## [1.1.0] - 2025-05-06

### Added

- `GeoPlacesClient`: Client for AWS Location Service geo-places API.
- `GeoRoutesClient`: Client for AWS Location Service route calculation API.
- `search_places` tool: Search for places using text queries.
- `get_place` tool: Retrieve details for a specific place by PlaceId.
- `reverse_geocode` tool: Convert coordinates to a human-readable address.
- `search_nearby` tool: Find places near a given location, with radius expansion.
- `search_places_open_now` tool: Find places currently open, with support for opening hours and radius expansion.
- `get_coordinates` tool: Get coordinates for a location name or address.
- `calculate_route` tool: Calculate routes between two locations, supporting travel modes (`Car`, `Truck`, `Walking`, `Bicycle`) and route optimization (`FastestRoute`, `ShortestRoute`).
- `optimize_waypoints` tool: Optimize the order of waypoints for a route using AWS Location Service.

### Changed

- Refactored `calculate_route` to expose only `departure_position`, `destination_position`, `travel_mode`, and `optimize_for` as parameters. Internal options are now local variables.
- Updated tests and documentation to match the new tool signatures and AWS documentation.
- Improved error handling and output consistency for route calculation and waypoint optimization tools.

## [1.0.0] - 2025-04-17

### Added

- Initial release of the AWS Location Service MCP Server
- Added `search_places` tool for geocoding and place search
- Added `get_coordinates` tool for retrieving location coordinates
- Support for AWS credentials via environment variables or AWS CLI profiles
- Support for custom place index configuration

### Changed

- Implemented using FastMCP framework for MCP protocol handling
- Structured project to match other MCP servers

## [1.1.0] - 2025-05-06

### Added

- `GeoPlacesClient`: Client for AWS Location Service geo-places API.
- `GeoRoutesClient`: Client for AWS Location Service route calculation API.
- `search_places` tool: Search for places using text queries.
- `get_place` tool: Retrieve details for a specific place by PlaceId.
- `reverse_geocode` tool: Convert coordinates to a human-readable address.
- `search_nearby` tool: Find places near a given location, with radius expansion.
- `search_places_open_now` tool: Find places currently open, with support for opening hours and radius expansion.
- `get_coordinates` tool: Get coordinates for a location name or address.
- `calculate_route` tool: Calculate routes between two locations, supporting travel modes (`Car`, `Truck`, `Walking`, `Bicycle`) and route optimization (`FastestRoute`, `ShortestRoute`).
- `optimize_waypoints` tool: Optimize the order of waypoints for a route using AWS Location Service.

### Changed

- Refactored `calculate_route` to expose only `departure_position`, `destination_position`, `travel_mode`, and `optimize_for` as parameters. Internal options are now local variables.
- Updated tests and documentation to match the new tool signatures and AWS documentation.
- Improved error handling and output consistency for route calculation and waypoint optimization tools.
