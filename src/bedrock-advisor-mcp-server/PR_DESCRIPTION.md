# Add Bedrock Advisor MCP Server

This PR adds a new MCP server called "bedrock-advisor-mcp-server" that provides intelligent recommendations for Amazon Bedrock foundation models based on specific use case requirements.

## Features

- **Model Exploration Guidance**: Get personalized model suggestions based on specific requirements
- **Detailed Model Information**: Access comprehensive information about Bedrock foundation models
- **Model Comparison**: Compare multiple models across various dimensions
- **Cost Estimation**: Get usage-based cost projections and optimization recommendations
- **Regional Availability Checking**: Check model availability across AWS regions

## Tools

- `recommend_model`: Get intelligent model recommendations based on criteria
- `get_model_info`: Get detailed information about a specific model
- `list_models`: List all available models with optional filtering
- `refresh_models`: Refresh model data from AWS Bedrock service
- `compare_models`: Compare multiple models side-by-side with detailed analysis
- `estimate_cost`: Estimate costs based on usage patterns with optimization recommendations
- `check_model_availability`: Check availability of a specific model across AWS regions
- `check_region_availability`: Check which models are available in a specific AWS region

## Implementation Details

- Uses FastMCP for tool registration and request handling
- Follows the standard MCP server structure and patterns
- Includes comprehensive tests and documentation
- Uses the same build system and dependencies as other MCP servers

## Testing

- Unit tests for all tools and services
- Integration tests for the server
- All tests pass

## Documentation

- README.md with installation and usage instructions
- Tool reference documentation with examples
- Configuration documentation

## Related Issues

- None

## Checklist

- [x] Code follows the style guidelines of the project
- [x] Tests for the changes have been added
- [x] Documentation has been updated
- [x] All tests pass
- [x] License headers have been added to all files
