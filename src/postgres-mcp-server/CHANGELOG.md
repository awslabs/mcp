# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-06-19

### Added
- **Complete PostgreSQL MCP Server** with 10 comprehensive tools
- **Core Tools**: run_query, get_table_schema, health_check
- **Analysis Tools**: analyze_database_structure, show_postgresql_settings, identify_slow_queries, analyze_table_fragmentation, analyze_query_performance, analyze_vacuum_stats, recommend_indexes
- **AWS RDS Data API Integration** for secure, serverless database connections
- **Comprehensive Test Suite** with 16/17 tests passing
- **Security-focused Documentation** with secure credential management
- **Amazon Q Developer CLI Integration** with tested configuration

### Security
- **Secure Credential Management** using AWS profiles, IAM roles, and SSO
- **Read-only Operations** enforced for database safety
- **SQL Injection Protection** with query validation
- **No Hardcoded Credentials** in documentation or examples

### Fixed
- **Type Conversion Issues** - Resolved "str vs float" comparison errors
- **JSON Import Error** - Fixed missing json module import
- **RDS Data API Compatibility** - Removed unsupported array data types
- **Infinite Recursion Bug** - Fixed connection management issues

### Changed
- **Consolidated Server Architecture** - Single server file instead of multiple versions
- **Organized Test Structure** - All tests in tests/ directory following Python conventions
- **Comprehensive Documentation** - Updated README with accurate implementation details
- **Security Best Practices** - Removed dangerous credential exposure examples

### Removed
- **Redundant Server Files** - Cleaned up backup and development versions
- **Duplicate Test Files** - Consolidated into single comprehensive test suite
- **Insecure Examples** - Removed hardcoded credential patterns from documentation

## [0.1.0] - Initial Development

### Added
- Initial project setup and basic structure
