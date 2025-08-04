# Changelog

## [Unreleased]
### Fixed
- Updated MCP server naming convention to use proper AWS Labs format `awslabs.cloudwan_mcp_server`
- Fixed all configuration examples in README.md to use consistent naming
- Updated tool names to follow pattern: `awslabs.cloudwan_mcp_server___<tool_name>`
- Removed unimplemented environment variables from documentation
- Corrected repository path references from `cloudwan_mcp` to `cloud-wan-mcp-server`

## [1.0.0] - 2024-02-20
### Structural Changes
- Migrated to AWS Labs flat package structure (`awslabs/cloudwan_mcp_server` instead of `src/awslabs`)
- Updated all imports to use `awslabs.cloudwan_mcp_server` namespace
- Aligned with AWS Labs pyproject.toml standards for dependency groups

### Features
- Initial AWS Labs compliant release
- Full CloudWAN analysis tool suite
- MCP protocol v1.1 implementation