# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-05-15

### Added
- Initial project setup with OpenAPI MCP Server functionality
- Support for OpenAPI specifications in JSON and YAML formats
- Dynamic generation of MCP tools from OpenAPI endpoints
- Intelligent route mapping for GET operations with query parameters
  - Maps GET operations with query parameters to TOOLS instead of RESOURCES
  - Makes API operations with query parameters easier for LLMs to understand and use
  - Improves usability of search and filtering endpoints
  - Configurable via the route_patch module
- Authentication support for Basic, Bearer Token, and API Key methods
- Command line arguments and environment variable configuration
- Support for SSE and stdio transports
- Dynamic prompt generation based on API structure
  - Operation-specific prompts for each API endpoint
  - Comprehensive API documentation prompts
  - Prompt generation with Prompt.from_function method for FastMCP compatibility
- Centralized configuration system for all server settings
- Metrics collection and monitoring capabilities
  - In-memory metrics provider
  - Prometheus integration (optional)
  - API call tracking and performance metrics
- Caching system with multiple backend options
- HTTP client with resilience features and retry logic
- Error handling and logging throughout the application
- Graceful shutdown mechanism for clean server termination
  - Proper handling of SIGINT and SIGTERM signals
  - Metrics logging during shutdown
  - Integration with uvicorn's graceful shutdown process
- Docker configuration with explicit API parameters
- Comprehensive test suite with high code coverage (100% for route_patch.py)
- Detailed documentation:
  - README with installation and usage instructions
  - Deployment guide with AWS service integration
  - AWS best practices implementation
