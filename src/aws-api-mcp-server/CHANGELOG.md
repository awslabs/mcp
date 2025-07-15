# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased



## [0.1.1] - 2026-07-15
### Added

* First release of AWS API MCP Server.
* `call_aws` tool. Executes AWS CLI commands with validation and proper error handling
* `suggest_aws_commands` tool. Suggests AWS CLI commands based on a natural language query. This tool helps the model generate CLI commands by providing a description and the complete set of parameters for the 5 most likely CLI commands for the given query, including the most recent AWS CLI commands - some of which may be otherwise unknown to the model.
