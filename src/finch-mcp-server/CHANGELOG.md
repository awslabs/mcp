# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2025-05-19

### Added
- Added scan on push and immutable tags to ECR repository creation
- Enhanced `check_ecr_repository` function to always enable scan on push and set immutable tags

## [1.2.0] - 2025-05-19

### Added
- New tool `finch_create_ecr_repo` to check if an ECR repository exists and create it if it doesn't
- Added utility function `check_ecr_repository` to handle ECR repository operations
- Added unit tests for the new tool
- Updated documentation to include the new tool

## [1.1.0] - 2025-05-19

### Changed
- Enhanced `finch_push_image` to automatically replace the tag with the image hash before pushing
- Added new utility function `get_image_hash` to extract the hash from an image
- Updated documentation to reflect the new behavior

## [1.0.0] - 2025-05-16

### Added
- Initial release of the Finch MCP Server
