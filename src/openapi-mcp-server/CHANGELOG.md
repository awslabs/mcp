# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-07-05

### Added
- OAuth 2.0 and OpenID Connect support through Cognito authentication
- Client credentials grant flow for service-to-service authentication
- Cline Marketplace integration support

### Changed
- Migrated from FastMCP 1.0 to 2.0
- Updated core dependencies to latest versions
- Enhanced documentation structure and authentication examples

### Security
- Updated base image with latest security patches

## [0.1.0] - 2025-05-15

### Added
- Initial project setup with OpenAPI MCP Server functionality
- Support for OpenAPI specifications in JSON and YAML formats
- Dynamic generation of MCP tools from OpenAPI endpoints
- Intelligent route mapping for GET operations with query parameters
- Authentication support for Basic, Bearer Token, and API Key methods
- Command line arguments and environment variable configuration
- Support for SSE and stdio transports
- Dynamic prompt generation based on API structure
- Centralized configuration system for all server settings
- Metrics collection and monitoring capabilities
- Caching system with multiple backend options
- HTTP client with resilience features and retry logic
- Error handling and logging throughout the application
- Graceful shutdown mechanism for clean server termination
- Docker configuration with explicit API parameters
- Comprehensive test suite with high code coverage
- Detailed documentation and deployment guides
