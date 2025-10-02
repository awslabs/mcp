# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- S3 URI support for workflow definitions in `CreateAHOWorkflow` and `CreateAHOWorkflowVersion` tools
  - Added `definition_uri` parameter as alternative to `definition_zip_base64`
  - Supports direct reference to workflow definition ZIP files stored in S3
  - Includes validation for S3 URI format and mutual exclusivity with base64 parameter
  - Added comprehensive test coverage for S3 URI functionality
- Initial project setup
