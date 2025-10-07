# Changelog

All notable changes to the AWS DMS MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

#### Docker Infrastructure Improvements

- **Dockerfile modernization**: Updated to match security and performance standards across AWS MCP servers
  - Changed base image from `python:3.13-slim` to SHA256-pinned Alpine image (`python:3.13.5-alpine3.21@sha256:...`)
  - Implemented multi-stage build pattern for smaller production images
  - Added UV optimization environment variables (UV_COMPILE_BYTECODE, UV_LINK_MODE, UV_PYTHON_PREFERENCE, UV_FROZEN)
  - Added build cache mounts (`--mount=type=cache,target=/root/.cache/uv`) for faster rebuilds
  - Updated to modern `uv sync --frozen` workflow
  - Added Alpine build dependencies (build-base, gcc, musl-dev, libffi-dev, openssl-dev, cargo)

- **Security enhancements**:
  - Implemented hash-verified dependency installation with `--require-hashes` flag
  - Added `uv-requirements.txt` with SHA256 hashes for secure package installation
  - SHA256-pinned base images for Dependabot compatibility

- **Healthcheck improvements**:
  - Added external `docker-healthcheck.sh` script (replacing inline Python healthcheck)
  - Updated healthcheck intervals to 60s/10s/10s (matching other servers)
  - Made healthcheck script executable with proper permissions

### Infrastructure

- Added `uv-requirements.txt` for hash-verified UV installation (uv==0.8.10)
- Added `docker-healthcheck.sh` for container health monitoring

## [0.2.0] - 2025-10-06

### Added

**Total: 90 new tools** (13 original → 103 total)

#### Traditional DMS Operations (43 new tools)

**Replication Instance Operations (6 new tools)**
- `modify_replication_instance` - Modify instance configuration
- `delete_replication_instance` - Delete unused instance
- `reboot_replication_instance` - Reboot with optional failover
- `describe_orderable_replication_instances` - List available instance classes
- `describe_replication_instance_task_logs` - Get task log metadata
- `move_replication_task` - Move task between instances

**Endpoint Operations (7 new tools)**
- `modify_endpoint` - Modify endpoint configuration
- `describe_endpoint_settings` - Get valid settings for engines
- `describe_endpoint_types` - List supported endpoint types
- `describe_engine_versions` - List DMS engine versions
- `refresh_schemas` - Refresh schema definitions
- `describe_schemas` - List database schemas
- `describe_refresh_schemas_status` - Get refresh status

**Connection Operations (1 new tool)**
- `delete_connection` - Delete connection configuration

**Task Operations (4 new tools)**
- `modify_replication_task` - Modify task configuration
- `delete_replication_task` - Delete stopped task
- `describe_replication_table_statistics` - Get table stats (supports serverless)
- `reload_tables` - Reload tables (serverless)

**Task Assessment Operations (9 new tools)**
- `start_replication_task_assessment` - Start assessment (legacy)
- `start_replication_task_assessment_run` - Start new assessment run
- `cancel_replication_task_assessment_run` - Cancel running assessment
- `delete_replication_task_assessment_run` - Delete assessment run
- `describe_replication_task_assessment_results` - List results (legacy)
- `describe_replication_task_assessment_runs` - List assessment runs
- `describe_replication_task_individual_assessments` - List individual assessments
- `describe_applicable_individual_assessments` - List applicable assessments

**Certificate Operations (3 new tools)**
- `import_certificate` - Import PEM/Oracle wallet certificates
- `describe_certificates` - List SSL certificates
- `delete_certificate` - Delete unused certificate

**Subnet Group Operations (4 new tools)**
- `create_replication_subnet_group` - Create subnet group
- `modify_replication_subnet_group` - Modify subnet configuration
- `describe_replication_subnet_groups` - List subnet groups
- `delete_replication_subnet_group` - Delete unused subnet group

**Event Operations (7 new tools)**
- `create_event_subscription` - Create SNS event subscription
- `modify_event_subscription` - Modify subscription
- `delete_event_subscription` - Delete subscription
- `describe_event_subscriptions` - List subscriptions
- `describe_events` - List DMS events
- `describe_event_categories` - List event categories
- `update_subscriptions_to_event_bridge` - Migrate to EventBridge

**Maintenance and Tagging Operations (6 new tools)**
- `apply_pending_maintenance_action` - Apply maintenance updates
- `describe_pending_maintenance_actions` - List pending maintenance
- `describe_account_attributes` - Get account quotas and limits
- `add_tags_to_resource` - Add resource tags
- `remove_tags_from_resource` - Remove resource tags
- `list_tags_for_resource` - List resource tags

#### DMS Serverless Operations (25 new tools)

**Replication Config Operations (7 new tools)**
- `create_replication_config` - Create serverless replication config
- `modify_replication_config` - Modify config
- `delete_replication_config` - Delete config
- `describe_replication_configs` - List configurations
- `describe_replications` - List running replications
- `start_replication` - Start serverless replication
- `stop_replication` - Stop serverless replication

**Migration Project Operations (4 new tools)**
- `create_migration_project` - Create migration project
- `modify_migration_project` - Modify project
- `delete_migration_project` - Delete project
- `describe_migration_projects` - List projects

**Data Provider Operations (4 new tools)**
- `create_data_provider` - Create data provider
- `modify_data_provider` - Modify provider
- `delete_data_provider` - Delete provider
- `describe_data_providers` - List providers

**Instance Profile Operations (4 new tools)**
- `create_instance_profile` - Create instance profile
- `modify_instance_profile` - Modify profile
- `delete_instance_profile` - Delete profile
- `describe_instance_profiles` - List profiles

**Data Migration Operations (6 new tools)**
- `create_data_migration` - Create data migration
- `modify_data_migration` - Modify migration
- `delete_data_migration` - Delete migration
- `describe_data_migrations` - List migrations
- `start_data_migration` - Start migration
- `stop_data_migration` - Stop migration

**Metadata Model Operations (15 new tools)**
- `describe_conversion_configuration` - Get conversion configuration
- `modify_conversion_configuration` - Modify conversion settings
- `describe_extension_pack_associations` - List extension pack associations
- `start_extension_pack_association` - Start extension pack association
- `describe_metadata_model_assessments` - List metadata model assessments
- `start_metadata_model_assessment` - Start metadata model assessment
- `describe_metadata_model_conversions` - List metadata model conversions
- `start_metadata_model_conversion` - Start metadata model conversion
- `describe_metadata_model_exports_as_script` - List script exports
- `start_metadata_model_export_as_script` - Start script export
- `describe_metadata_model_exports_to_target` - List target exports
- `start_metadata_model_export_to_target` - Start target export
- `describe_metadata_model_imports` - List metadata model imports
- `start_metadata_model_import` - Start metadata model import
- `export_metadata_model_assessment` - Export assessment report

#### Advanced Features (13 new tools)

**Fleet Advisor Operations (9 new tools)**
- `create_fleet_advisor_collector` - Create data collector
- `delete_fleet_advisor_collector` - Delete collector
- `describe_fleet_advisor_collectors` - List collectors
- `delete_fleet_advisor_databases` - Delete discovered databases
- `describe_fleet_advisor_databases` - List discovered databases
- `describe_fleet_advisor_lsa_analysis` - View LSA analysis results
- `run_fleet_advisor_lsa_analysis` - Run LSA analysis
- `describe_fleet_advisor_schema_object_summary` - View schema object summary
- `describe_fleet_advisor_schemas` - List schemas

**Recommendation Operations (4 new tools)**
- `describe_recommendations` - List migration recommendations
- `describe_recommendation_limitations` - List recommendation limitations
- `start_recommendations` - Generate recommendations for a database
- `batch_start_recommendations` - Generate recommendations for multiple databases

### Changed

- Updated README to document all 75 tools across 15 categories
- Enhanced server instructions with comprehensive tool documentation
- Improved project structure with specialized manager utilities

### Infrastructure

- Added `AssessmentManager` for task assessment operations
- Added `CertificateManager` for SSL certificate management
- Added `SubnetGroupManager` for VPC networking configuration
- Added `EventManager` for event subscriptions and monitoring
- Added `MaintenanceManager` for maintenance and tagging operations
- Added `ServerlessReplicationManager` for serverless replication configs
- Added `ServerlessManager` for serverless projects, providers, profiles, and migrations
- Added `MetadataModelManager` for schema conversion operations
- Added `FleetAdvisorManager` for database discovery operations
- Added `RecommendationManager` for migration optimization recommendations

## [0.1.0] - 2024

### Added

- Initial release with 13 core DMS tools
- Replication instance management (2 tools)
- Endpoint management (5 tools)
- Replication task management (4 tools)
- Table operations (2 tools)
- FastMCP framework integration
- Type-safe Pydantic validation
- Structured logging with loguru
- Read-only mode support
- Docker support
