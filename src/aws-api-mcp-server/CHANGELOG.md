# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Fixed

- Log errors thrown by the agent scripts manager (#1533)

### Changed

- Converted MCP server to use FastMCP framework instead of python mcp sdk (#1513)

## [1.0.2] - 2025-10-13

### Fixed

- CLI commands that don't expect any parameters (#1494)

### Added

- Support for `--endpoint-url` flag for localhost endpoints (#1452)
- Change max retries to 3 when interpreting CLI command (#1485)

## [1.0.1] - 2025-10-06

### Added

- Agent Script for creating Aurora DB with instances (#1401)
- AWS_API_MCP_STATELESS_HTTP configuration option (#1349)

## [1.0.0] - 2025-10-01

### Changed

- Replace local knowledge base with a remote endpoint for `suggest_aws_commands` (#1282)

### Removed

- `wait` and other polling AWS CLI commands(#1402)

## [0.3.4] - 2025-09-30

### Removed

- Command output logging (#1388)

### Fixed

- Mark more operations as mutating (#1387)

## [0.3.3] - 2025-09-30

### Fixed

- Mark sts:AssumeRole as mutating (#1364)

## [0.3.1] - 2025-09-23

### Added

- Agent script for CloudTrail Multi-Region Setup (#1320)
- Add telemetry for AWS CLI customizations (#1335)
- Enforcement of `AUTH_TYPE=no-auth` for streamable-http mode (#1345)
- Agent Script for troubleshooting permissions using CloudTrail events (#1313)

## [0.3.0] - 2025-09-22

### Fixed

- Loading of security policy from `~/.aws/aws-api-mcp/mcp-security-policy.json` (#1311)
- Enforcement of `READ_OPERATIONS_ONLY_MODE` and `REQUIRE_MUTATION_CONSENT` in security policy (#1301)

## [0.2.14] - 2025-09-15

### Added

- Agent Script for debugging Lambda timeouts (#1271)
- Agent Script for failure troubleshooting (#1276)
- Safe execution for AWS APIs within working directory (#1261)

## [0.2.13] - 2025-09-10

### Added

- Support for custom security policy configuration via `~/.aws/aws-api-mcp/mcp-security-policy.json` file (#1213)
- Custom deny list and elicitation required lists for AWS operations with pattern matching support (#1213)
- Documentation for security policy configuration in README (#1240)

## [0.2.12] - 2025-09-04

### Added

- Support for custom agent scripts directory via `AWS_API_MCP_AGENT_SCRIPTS_DIR` environment variable (#1227)
- Scrubbing of sensitive logs (#1228)

## [0.2.11] - 2025-08-29

### Changed

- Telemetry for consent mechanism (#1202)

## [0.2.10] - 2025-08-28

### Added

- Support for streamable HTTP transport mode via `AWS_API_MCP_TRANSPORT` environment variable (#1192)
- Configurable port for HTTP transport mode via `AWS_API_MCP_PORT` environment variable (defaults to 8000) (#1192)
- Configurable host for HTTP transport mode via `AWS_API_MCP_HOST` environment variable (defaults to 127.0.0.1) (#1192)

### Fixed

- Support commands with outfile parameter (#1154)

## [0.2.9] - 2025-08-25

### Added

- Experimental support for Agent Scripts (#1149)

## [0.2.8] - 2025-08-21

### Changed

- Fetch embedding model from AWS instead of Hugging Face (#1127)

### Fixed

- Use region from profile specified in cli command (#1123)

## [0.2.5] - 2025-08-11

### Changed

- Validate `AWS_REGION` environment variable (#1030)

## [0.2.4] - 2025-08-07

### Fixed

- Async model loading on Windows (#1035)

## [0.2.3] - 2025-08-06

### Changed

- Improve tool logging (#1004)

## [0.2.2] - 2025-08-05

### Changed

- Update README (#1020)

## [0.2.1] - 2025-08-01

### Added

- Support for `--profile` in boto3 operations. (#986)

## [0.2.0] - 2025-07-29

### Added

- First version of the consent mechanism using elicitation. This can be enabled using `REQUIRE_MUTATION_CONSENT` and will prompt for input before executing any mutating operations. (#926)

### Changed

- Load the sentence transformers in the background (#844)
- Switched to CPU-only PyTorch (#856)
- Tool annotations (#915)
- `AWS_REGION` is no longer a mandatory environment variable. The region will be determined similar to boto3 with a default fallback to `us-east-1` (#952)

### Fixed

- Support profile for customizations (e.g. `s3 ls`) (#896)

## [0.1.1] - 2025-07-15

### Added

- First release of AWS API MCP Server.
- `call_aws` tool. Executes AWS CLI commands with validation and proper error handling
- `suggest_aws_commands` tool. Suggests AWS CLI commands based on a natural language query. This tool helps the model generate CLI commands by providing a description and the complete set of parameters for the 5 most likely CLI commands for the given query, including the most recent AWS CLI commands - some of which may be otherwise unknown to the model.
