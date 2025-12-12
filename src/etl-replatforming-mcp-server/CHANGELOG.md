# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-01-15

### Added
- Initial release of ETL Replatforming MCP Server
- Two-stage conversion: Source → FLEX → Target with validation
- Support for Step Functions, Airflow, and Azure Data Factory
- FLEX workflow format - framework-agnostic intermediate representation
- Workflow validation with user prompts for missing information
- FastMCP-based server implementation
- Comprehensive test coverage with 6 sample workflows per framework
- AWS Bedrock integration for AI-enhanced parsing

### MCP Tools

#### Directory-Based Tools (Batch Processing)
- `parse-to-flex` - Parse directory of workflows to FLEX format
- `convert-etl-workflow` - Complete directory conversion with context support
- `generate-from-flex` - Generate target jobs from FLEX directory

#### Single Workflow Tools (Individual Processing)
- `parse-single-workflow-to-flex` - Parse individual workflow to FLEX
- `convert-single-etl-workflow` - Complete single workflow conversion
- `generate-single-workflow-from-flex` - Generate target code from FLEX

### Features
- Extensible parser and generator architecture
- FLEX workflow format with task-embedded dependencies
- Intelligent validation with completion percentage
- User-friendly prompts for missing information
- Organizational context support via plain text files
- Natural language interface for directory processing
- Auto-detection of workflow formats

### Supported Frameworks
- **Source**: Step Functions, Airflow, Azure Data Factory
- **Target**: Airflow, Step Functions
- **Planned**: Prefect, Dagster
