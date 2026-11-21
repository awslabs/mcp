# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Fixed

- `get_eks_insights` returned an error for every insight that lists resources when called with an `insight_id`, because the response model typed `resources` as a list of strings while `DescribeInsight` returns resource details (`insightStatus`, `kubernetesResourceUri`, `arn`).

### Added

- Initial project setup
