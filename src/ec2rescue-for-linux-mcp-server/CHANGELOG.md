# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-05

### Added

- Auto-register 209 ec2rl diagnostic modules as MCP tools from bundled YAML definitions
- YAML-driven module loader (`mod.d/*.yaml`) with validation of names, packages, and software binaries
- Per-binary software precheck via `which <binary>` with exit-code-based detection
- Per-package software precheck via `ec2rl software-check | grep`
- Login shell wrapper (`bash -l -c`) for SSM commands that need full PATH
- Gathered-output module support with curation, listing, grep, and comment-strip flows
- MCP elicitation gates for perfimpact modules (user consent required before running)
- MCP elicitation for uncurated gathered files and large-output modules
- `grep_keys` parameter for targeted extraction from large module outputs (kernelconfig, sysctl, dpkgpackages, rpmpackages)
- `install_ec2rescue_linux` tool via AWSSupport-InstallEC2Rescue SSM automation
- Streamable HTTP transport support via `--transport` CLI flag
- Curated default module set to reduce MCP context usage
- AWSLABS MCP user agent on all boto3 API calls for download dashboard tracking
- Pydantic-based structured JSON responses for all tools

### Fixed

- Diagnose modules (fstabfailures, hungtasks, kernelpanic, oomkiller, softlockup) now surface log content on non-zero exit instead of reporting bare failure
- SSM timeout split into delivery, execution, and poll-deadline for reliable long-running modules
- Dynamic tool functions correctly skip Pydantic FieldInfo sentinels for optional args
- Software-check precheck fails loud on SSM errors instead of silently skipping

### Changed

- Architecture split: `server.py` (MCP registration), `execution.py` (SSM flow), `ec2rl/` (module model + command allowlist)
- Command allowlist uses strict regex anchoring for all command forms (security hardening)
- Module metadata dicts moved to `ec2rl/registry.py` for single-source-of-truth
- Version sourced from `__init__.__version__` (single source of truth for user agent and package metadata)
