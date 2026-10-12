# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- IAM authentication for Amazon ElastiCache (`VALKEY_IAM_AUTH`, `VALKEY_CACHE_NAME`; `AWS_REGION` is now also used to sign the token) using GLIDE's built-in token generation and refresh, enabling direct connections to ElastiCache Serverless caches with a public endpoint. TLS is enabled automatically in this mode.
- Initial project setup
