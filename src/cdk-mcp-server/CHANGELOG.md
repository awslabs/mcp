# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- Initial project setup
- New `GenerateLambdaLayerCode` tool for creating properly configured Lambda layers
  - Extracts data directly from AWS documentation
  - Provides smart fallback mechanisms for various AWS doc formats
  - Integrates with CDK General Guidance flow


### Changed

- Reorganized CDK_GENERAL_GUIDANCE.md to eliminate duplication
  - Created unified Implementation Approach and Workflow section
  - Added clear separation between common and GenAI patterns
  - Added section showing how both approaches can be used together
- Improved Lambda Powertools documentation
  - Centralized CDK integration guidance
  - Added explicit Lambda layer requirement notices
  - Removed duplicate code examples from feature-specific files
  - Updated Bedrock integration examples with proper layer creation patterns
