# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- Initial project setup

### Fixed

- Correctly report additional VPC CIDR blocks when the primary CIDR is not the first entry in `CidrBlockAssociationSet`. The EC2 `describe_vpcs` API does not guarantee ordering, so the previous positional slice could drop a legitimate additional CIDR and duplicate the primary.
