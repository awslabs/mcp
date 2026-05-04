# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.0.13

### Fixed

- `list_datastores`: the `filter` parameter was silently ignored because
  the Pydantic model expected `status=`. Added an alias so the MCP
  schema's `filter=` correctly populates the server-side call.
- Data-plane errors (`read_fhir_resource`, `search_fhir_resources`,
  `patient_everything`, `create_fhir_resource`, `update_fhir_resource`,
  `delete_fhir_resource`) returned `server_error "Internal server error"`
  for all HealthLake 4xx/5xx responses, swallowing the underlying HTTP
  status. Now mapped: 404/410 → `not_found`, 400 → `validation_error`
  (with HealthLake's `OperationOutcome.diagnostics` when present),
  401/403 → `auth_error`, other → `service_error` with the HTTP status.
- Pagination on `search_fhir_resources` and `patient_everything` failed
  with `"Invalid pagination token"` whenever the caller did not re-supply
  the same `count` on follow-up calls. The opaque `next_token` now packs
  HealthLake's `page` cursor together with the `_count` captured from the
  server's `next` link; follow-up calls use the captured `_count`
  regardless of what the caller passes. Verified end-to-end against live
  HealthLake with count ∈ {5, 10, 25, 50, 100} and 3-page walks.
- `start_fhir_export_job` was completely broken: it passed snake_case
  `output_data_config` straight to boto3, which rejected it as
  `Unknown parameter in OutputDataConfig: "s3_configuration"`. Mirrored
  the transform from `start_import_job` (snake_case →
  `S3Configuration.S3Uri` / `.KmsKeyId`) and adopted the same
  `ClientError` rewrap pattern (`ValidationException` → `ValueError`,
  `AccessDeniedException` → `PermissionError`).
- `start_fhir_import_job` / `start_fhir_export_job` surfaced
  `AccessDeniedException` (e.g. data-access role missing `kms:DescribeKey`
  grants) as `server_error`. The rewrapped `PermissionError` now maps to
  `auth_error` with HealthLake's original diagnostic message, so missing
  KMS grants are self-diagnosing at the tool-response level.

### Added

- New test module `tests/test_server_dataplane_errors.py` (6 tests)
  covering the new `httpx.HTTPStatusError` mapping.
- New test module `tests/test_bugfixes_pagination_and_mapping.py`
  (19 tests) covering v2 opaque-token encode/decode/round-trip, caller
  vs captured `_count` precedence, legacy-token fallback, export-job
  snake_case transform + KMS propagation + `ClientError` rewraps, and
  HTTP 410 → `not_found`.
- Additional coverage on `tests/test_pagination_hardening.py` for v2
  token format, malformed server `_count`, and out-of-range clamping.

## 0.0.12

### Changed

- Maintenance release.

## Unreleased

### Added

- Initial project setup
