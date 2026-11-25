# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- Cached-input pricing: `price_usage`, `estimate_run_cost`, `compare_models_for_task`, and `record_spend` accept `cached_input_tokens`, billed at the model's published cache-read rate where the snapshot carries one and reported separately from uncached input
- Per-row price provenance: every snapshot row carries a `checked_date`; priced responses expose `price_checked_date` and flag rows older than 90 days as `price_stale`. Snapshot v2 re-verified against the llm-prices dataset (MIT), which also supplied the cache-read rates
- Unknown-model refusal in `compare_models_for_task`: a `success_rates` entry naming a model outside the snapshot now errors and names the model instead of being silently dropped (the other tools already refused unknown models by name)

- Initial project setup: agent cost MCP server with `price_usage`, `estimate_run_cost`, `compare_models_for_task`, `record_spend`, and `budget_status` tools, implementing RFC #4772
