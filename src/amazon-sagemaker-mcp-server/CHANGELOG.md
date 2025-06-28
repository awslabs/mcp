# Changelog

All notable changes to the Amazon SageMaker MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial implementation of Amazon SageMaker MCP Server
- Endpoint management tools (create, update, delete, invoke, list, describe)
- Model management tools (create, delete, list, describe)
- Training job management tools (create, stop, list, describe)
- Processing job management tools (create, stop, list, describe)
- AutoML job management tools (create, stop, list, describe)
- Feature Store management tools (create, delete, list, describe, put/get records)
- Pipeline management tools (create, delete, start/stop execution, list, describe)
- SageMaker Studio domain and user profile management
- Notebook instance management tools
- Monitoring and metrics tools
- Guidance and best practices tools
- Resource handlers for all major SageMaker components
- Security controls with read-only defaults
- Support for AWS profiles and temporary credentials

### Security
- Implemented permission controls for write operations
- Added sensitive data access controls for endpoint invocation
- Read-only mode by default to prevent accidental modifications

## [0.1.0] - 2024-06-24

### Added
- Initial release of Amazon SageMaker MCP Server
- Basic project structure and configuration
- Placeholder implementations for all major SageMaker services
