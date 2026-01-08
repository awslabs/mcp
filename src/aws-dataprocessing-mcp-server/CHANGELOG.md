# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Fixed

- Fixed datetime serialization bug causing `TypeError: Object of type datetime is not JSON serializable` 
  when AWS API responses contain datetime fields (#1990, #2023)
- Applied fix across all handlers by using `model_dump(mode='json')` instead of `model_dump()`
- Updated test mocks to include datetime fields matching real AWS API responses

### Added

- Initial project setup
