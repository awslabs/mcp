# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
