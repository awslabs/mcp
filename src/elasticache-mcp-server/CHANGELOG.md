# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Fixed

- `delete-replication-group` (`RetainPrimaryCluster`), `modify-serverless-cache` (every boolean, for example `RemoveUserGroup`), `create-serverless-cache` (`SnapshotRetentionLimit`) and `describe-engine-default-parameters` (`MaxRecords`) sent those values to boto3 as strings. botocore rejects a string where the API takes a boolean or an integer, so each of those calls failed with a parameter validation error before reaching ElastiCache. The native values are now passed through.

### Added

- `connection_type` parameter on `create-serverless-cache` to create ElastiCache Serverless caches with a public endpoint (`'public'`) or a VPC endpoint (`'vpc'`, default).
- Jump-host tools now return a clear error for caches with a public endpoint, since those are reached directly over the internet with IAM authentication.
- Initial project setup
