# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Fixed

- `detect_tgw_inspection` raising `KeyError: 'VpcId'` because `list_firewalls()` doesn't return `VpcId` (#4286)

### Added

- Initial project setup
