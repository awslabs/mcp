# Changelog

All notable changes to the Amazon Bedrock Advisor MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-06-25

### Added
- Initial release of Amazon Bedrock Advisor MCP Server
- 16 comprehensive tools for Bedrock model management:
  - `recommend_model` - Intelligent model recommendations
  - `get_model_info` - Detailed model information
  - `list_models` - List all available models with filtering
  - `search_models` - Natural language model search
  - `compare_models` - Side-by-side model comparison
  - `estimate_cost` - Cost estimation for usage patterns
  - `compare_costs` - Cost comparison across models
  - `check_model_availability` - Regional availability checking
  - `check_region_availability` - Region-specific model availability
  - `compare_model_availability` - Multi-model availability comparison
  - `get_supported_regions` - List of Bedrock-supported regions
  - `refresh_model_data` - Live data refresh from AWS API
  - `get_data_status` - Data freshness and status information
  - `get_models_by_provider` - Provider-specific model filtering
  - `get_models_by_capabilities` - Capability-based model filtering
- Real-time integration with AWS Bedrock API
- Comprehensive model comparison and analysis
- Cost optimization recommendations
- Regional deployment planning support
- Intelligent recommendation engine with multi-criteria scoring
- Full AWS Labs MCP server compliance
- Comprehensive test suite
- Docker support
- Documentation and examples

### Technical Features
- FastMCP framework integration
- Pydantic model validation
- Structured error handling
- Comprehensive logging
- Type hints throughout
- AWS SDK integration
- Async/await support
- Request/response validation
- Performance optimization
- Memory-efficient data handling

### Documentation
- Complete README with usage examples
- API documentation for all tools
- Configuration guide
- Development setup instructions
- AWS permissions documentation
- Contributing guidelines
- License and legal information
