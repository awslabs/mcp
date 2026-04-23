# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- Initial project setup
- Auto-generated Pydantic models from botocore service model for typed tool parameters
- Tools for channel, input, and multiplex lifecycle management (create, describe, list, start, stop, delete, update)
- Waiter tools for channel state transitions (channel_created, channel_running, channel_stopped, channel_deleted)
- Hand-written description overrides for field-level gotchas and usage guidance
- Tier 2 cross-reference validation (e.g., VideoDescriptionName must match VideoDescriptions)
- Workflow context tool for understanding end-to-end media service pipelines
