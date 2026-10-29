# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- `connection_type` parameter on `create-serverless-cache` to create ElastiCache Serverless caches with a public endpoint (`'public'`) or a VPC endpoint (`'vpc'`, default).
- Jump-host tools now return a clear error for caches with a public endpoint, since those are reached directly over the internet with IAM authentication.
- Initial project setup
