# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

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
