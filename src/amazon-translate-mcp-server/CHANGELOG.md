# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Enhanced README.md with comprehensive installation and usage instructions
- Improved project metadata and packaging configuration
- Additional MCP client configuration examples

### Changed
- Updated pyproject.toml with complete project scripts and entry points
- Enhanced documentation structure and navigation

## [1.0.0] - 2025-01-05

### Added
- Initial release of Amazon Translate MCP Server
- **Translation Operations**:
  - `translate_text` - Real-time text translation with terminology support
  - `start_batch_translation` - Initialize batch translation jobs for large documents
  - `get_translation_job` - Monitor job status and retrieve results
  - `list_translation_jobs` - View all translation tasks with filtering
- **Terminology Management**:
  - `list_terminologies` - Browse available custom terminology sets
  - `create_terminology` - Create new terminology for domain-specific translations
  - `import_terminology` - Import terminology from CSV or TMX files
  - `get_terminology` - Access detailed terminology information
- **Language Operations**:
  - `list_language_pairs` - Show all 75+ supported language combinations
  - `detect_language` - Automatically identify source text language
  - `get_language_metrics` - View translation usage statistics
  - `validate_translation` - Perform quality checks on translations
- **Core Infrastructure**:
  - AWS client manager with credential chain support
  - Comprehensive data models with Pydantic validation
  - Translation service with caching and performance optimization
  - Batch job manager for large-scale processing
  - Terminology manager with CSV/TMX import support
  - Language operations with metrics and validation
- **Security and Compliance**:
  - Content filtering and profanity detection
  - Audit logging for all translation operations
  - Secure file handling for terminology imports
  - AWS IAM integration for fine-grained permissions
- **Error Handling and Resilience**:
  - Comprehensive exception hierarchy
  - Exponential backoff retry logic for rate limiting
  - Circuit breaker pattern for service failures
  - Detailed error reporting with correlation IDs
- **Performance Features**:
  - Translation result caching with configurable TTL
  - Connection pooling for AWS clients
  - Async operation support for batch jobs
  - Intelligent batching for high-volume requests
- **Monitoring and Observability**:
  - Health check endpoints for service monitoring
  - CloudWatch integration for metrics collection
  - Performance tracking with response time monitoring
  - Cost tracking metrics for billing correlation
- **Deployment and Configuration**:
  - Docker support with multi-stage builds and health checks
  - Environment variable configuration
  - MCP client configuration examples
  - Comprehensive documentation and deployment guides

### Dependencies
- Python 3.10+ support
- boto3 >= 1.38.12 for AWS SDK integration
- mcp[cli] >= 1.11.0 for Model Context Protocol support
- pydantic >= 2.0.0 for data validation
- fastmcp >= 0.2.0 for MCP server framework

### Documentation
- Complete README.md with installation and usage instructions
- Deployment guide for various environments
- Environment variable configuration documentation
- MCP client setup examples for popular clients
- AWS IAM permissions documentation
