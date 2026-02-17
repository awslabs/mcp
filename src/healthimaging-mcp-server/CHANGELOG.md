# Changelog

All notable changes to the AWS HealthImaging MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Docker support with multi-stage build for optimized container images
- Installation method buttons for Kiro, Cursor, and VS Code in README
- User agent configuration for all HealthImaging API calls
- Comprehensive DICOM hierarchy operations (delete series, instances)
- Patient data management tools (bulk update, delete operations)
- Advanced search capabilities by patient ID, study UID, and series UID
- DICOMweb integration for study-level information retrieval
- Patient and study metadata update operations
- Bulk operations for patient metadata updates and deletions
- DICOM hierarchy manipulation (remove series/instances from image sets)

### Changed
- Updated installation instructions to reference Kiro instead of Q CLI
- Improved README documentation with better code examples and formatting
- Optimized client creation with centralized `get_medical_imaging_client()` function
- Enhanced error handling and logging across all operations
- Updated pyright to v1.1.408 for better type checking
- Toned down GDPR compliance language to be more accurate

### Fixed
- Security vulnerability CVE-2026-21441 in urllib3 (updated to v2.6.3)
- Security vulnerability CVE-2026-22701 in filelock (updated to v3.20.3)
- Security vulnerability CVE-2026-24486 in python-multipart (updated to v0.0.22)
- Security vulnerability GHSA-r6ph-v2qm-q3c2 in cryptography (updated to v46.0.5)
- Invalid JSON code fences in README documentation
- Docker healthcheck script executable permissions
- Removed unnecessary virtualenv dependency (uv handles virtual environments)

### Security
- All dependencies updated to address known vulnerabilities
- Docker image uses non-root user for enhanced security
- Hashed dependencies in uv-requirements.txt for supply chain security

## [0.1.0] - 2024-12-10

### Added
- Initial project structure
- Core MCP server implementation
- Basic HealthImaging API integration
- README with usage instructions
- Contributing guidelines
- Apache 2.0 license
