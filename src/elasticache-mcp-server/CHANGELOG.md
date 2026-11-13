# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- `connection_type` parameter on `create-serverless-cache` to create ElastiCache Serverless caches with a public endpoint (`'public'`) or a VPC endpoint (`'vpc'`, default).
- Jump-host tools now return a clear error for caches with a public endpoint, since those are reached directly over the internet with IAM authentication.
- Initial project setup

### Fixed

- `modify-replication-group-shard-configuration` now always sends `ApplyImmediately` as a boolean. The API requires the parameter and rejected the string value the tool sent before.
- `modify-replication-group-shard-configuration` now accepts `node_groups_to_remove` and `node_groups_to_retain`. The API requires one of them when `node_group_count` is lower than the current number of shards, so reducing the shard count was not possible before.
