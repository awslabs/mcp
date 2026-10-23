# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- Initial project setup

### Fixed

- `get_all_tgw_routes` now sends `NextToken` when paging transit gateway route tables, so a transit gateway with more than one page of route tables no longer loops forever on page one
