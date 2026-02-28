# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## [0.1.0] - 2026-02-24

### Added

- Initial project setup
- MWAA environment management tools (list, get, create, update, delete)
- Airflow REST API tools via invoke_rest_api (DAGs, DAG runs, task instances, logs, connections, variables, import errors)
- Read-only mode by default with --allow-write flag for mutations
- Secure design: no CLI/web token exposure, all operations via invoke_rest_api
