# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-05-10

### Added
- Initial project setup with OpenAPI MCP Server functionality
- Support for OpenAPI specifications in JSON and YAML formats
- Dynamic generation of MCP tools from OpenAPI endpoints
- Authentication support for Basic, Bearer Token, and API Key methods
- Command line arguments and environment variable configuration
- Support for SSE and stdio transports
- Dynamic prompt generation based on API structure
  - Operation-specific prompts for each API endpoint
  - Comprehensive API documentation prompts
- Centralized configuration system for all server settings
- Metrics collection and monitoring capabilities
  - In-memory metrics provider
  - Prometheus integration (optional)
  - API call tracking and performance metrics
- Caching system with multiple backend options
- HTTP client with resilience features and retry logic
- Comprehensive test suite with high code coverage
- Detailed documentation:
  - README with installation and usage instructions
  - Deployment guide with AWS service integration
  - AWS best practices implementation

### Changed
- Updated Docker configuration to require explicit API parameters
- Improved error handling and logging throughout the application
- Enhanced prompt generation with better natural language descriptions
- Optimized HTTP client with connection pooling

### Fixed
- Prompt registration in operation_instructions.py to handle different server implementations
- Environment variable handling for boolean flags
- Test client to use httpx directly instead of MCPClient

## [Unreleased]

### Added
- No specific features planned at this time
