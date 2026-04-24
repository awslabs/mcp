# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- Initial project setup
- Auto-generated Pydantic models from botocore service model for typed tool parameters
- Tools for channel group, channel, and origin endpoint management (create, get, list, update, delete)
- Channel and origin endpoint policy management (get, put, delete)
- Harvest job tools for live-to-VOD clipping (create, get, list, cancel)
- Waiter tool for harvest job completion (harvest_job_finished)
- Hand-written description overrides for field-level gotchas and usage guidance
- Workflow context tool for understanding end-to-end media service pipelines
