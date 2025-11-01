# AWS Database Migration Service (DMS) MCP Server

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

A Model Context Protocol (MCP) server providing natural language access to AWS Database Migration Service operations. Built on FastMCP framework with comprehensive type safety and validation.

## Features

- **103 MCP Tools** covering comprehensive DMS operations:
  - Replication instance management (9 tools)
  - Source/target endpoint configuration (11 tools)
  - Connection testing and management (3 tools)
  - Replication task lifecycle management (7 tools)
  - Table-level monitoring and operations (3 tools)
  - Task assessment and quality monitoring (9 tools)
  - SSL certificate management (3 tools)
  - VPC subnet group configuration (4 tools)
  - Event notifications and monitoring (7 tools)
  - Maintenance actions and resource tagging (6 tools)

- **Multi-Engine Support**: MySQL, PostgreSQL, Oracle, MariaDB, Aurora, Aurora-PostgreSQL, and more

- **Production Ready**:
  - Type-safe with Pydantic validation
  - Comprehensive error handling
  - Read-only mode for safe analysis
  - Structured logging with loguru
  - Modular architecture with specialized managers

## Quick Start

### 1. Configure AWS Credentials

```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
```

### 2. Use with MCP Client

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "awslabs.aws-dms-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-dms-mcp-server@latest"
      ],
      "env": {
        "AWS_REGION": "us-east-1",
        "DMS_READ_ONLY_MODE": "false",
        "DMS_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## Available Tools (103 Total)

### 1. Replication Instance Operations (9 tools)
- `describe_replication_instances` - List and filter replication instances
- `create_replication_instance` - Create new instance with Multi-AZ support
- `modify_replication_instance` - Modify instance configuration
- `delete_replication_instance` - Delete unused instance
- `reboot_replication_instance` - Reboot with optional failover
- `describe_orderable_replication_instances` - List available instance classes
- `describe_replication_instance_task_logs` - Get task log metadata
- `move_replication_task` - Move task between instances

### 2. Endpoint Operations (11 tools)
- `describe_endpoints` - List source/target endpoints
- `create_endpoint` - Create database endpoint with SSL
- `modify_endpoint` - Modify endpoint configuration
- `delete_endpoint` - Delete unused endpoint
- `describe_endpoint_settings` - Get valid settings for engines
- `describe_endpoint_types` - List supported endpoint types
- `describe_engine_versions` - List DMS engine versions
- `refresh_schemas` - Refresh schema definitions
- `describe_schemas` - List database schemas
- `describe_refresh_schemas_status` - Get refresh status

### 3. Connection Operations (3 tools)
- `test_connection` - Test connectivity (auto-polling)
- `describe_connections` - List connection test results
- `delete_connection` - Delete connection configuration

### 4. Replication Task Operations (7 tools)
- `describe_replication_tasks` - List tasks with status
- `create_replication_task` - Create migration task
- `modify_replication_task` - Modify task configuration
- `delete_replication_task` - Delete stopped task
- `start_replication_task` - Start/resume/reload task
- `stop_replication_task` - Stop running task

### 5. Table Operations (3 tools)
- `describe_table_statistics` - Get table metrics (traditional DMS)
- `describe_replication_table_statistics` - Get table stats (supports serverless)
- `reload_replication_tables` - Reload specific tables (traditional)
- `reload_tables` - Reload tables (serverless)

### 6. Task Assessment Operations (9 tools)
- `start_replication_task_assessment` - Start assessment (legacy)
- `start_replication_task_assessment_run` - Start new assessment run
- `cancel_replication_task_assessment_run` - Cancel running assessment
- `delete_replication_task_assessment_run` - Delete assessment run
- `describe_replication_task_assessment_results` - List results (legacy)
- `describe_replication_task_assessment_runs` - List assessment runs
- `describe_replication_task_individual_assessments` - List individual assessments
- `describe_applicable_individual_assessments` - List applicable assessments

### 7. Certificate Operations (3 tools)
- `import_certificate` - Import PEM/Oracle wallet certificates
- `describe_certificates` - List SSL certificates
- `delete_certificate` - Delete unused certificate

### 8. Subnet Group Operations (4 tools)
- `create_replication_subnet_group` - Create subnet group
- `modify_replication_subnet_group` - Modify subnet configuration
- `describe_replication_subnet_groups` - List subnet groups
- `delete_replication_subnet_group` - Delete unused subnet group

### 9. Event Operations (7 tools)
- `create_event_subscription` - Create SNS event subscription
- `modify_event_subscription` - Modify subscription configuration
- `delete_event_subscription` - Delete subscription
- `describe_event_subscriptions` - List subscriptions
- `describe_events` - List DMS events with filtering
- `describe_event_categories` - List available event categories
- `update_subscriptions_to_event_bridge` - Migrate to EventBridge

### 10. Maintenance and Tagging Operations (6 tools)
- `apply_pending_maintenance_action` - Apply maintenance updates
- `describe_pending_maintenance_actions` - List pending maintenance
- `describe_account_attributes` - Get account quotas and limits
- `add_tags_to_resource` - Add resource tags
- `remove_tags_from_resource` - Remove resource tags
- `list_tags_for_resource` - List resource tags

### 11. DMS Serverless: Replication Config Operations (7 tools)
- `create_replication_config` - Create serverless replication config
- `modify_replication_config` - Modify config
- `delete_replication_config` - Delete config
- `describe_replication_configs` - List configurations
- `describe_replications` - List running replications
- `start_replication` - Start serverless replication
- `stop_replication` - Stop serverless replication

### 12. DMS Serverless: Migration Project Operations (4 tools)
- `create_migration_project` - Create migration project
- `modify_migration_project` - Modify project
- `delete_migration_project` - Delete project
- `describe_migration_projects` - List projects

### 13. DMS Serverless: Data Provider Operations (4 tools)
- `create_data_provider` - Create data provider
- `modify_data_provider` - Modify provider
- `delete_data_provider` - Delete provider
- `describe_data_providers` - List providers

### 14. DMS Serverless: Instance Profile Operations (4 tools)
- `create_instance_profile` - Create instance profile
- `modify_instance_profile` - Modify profile
- `delete_instance_profile` - Delete profile
- `describe_instance_profiles` - List profiles

### 15. DMS Serverless: Data Migration Operations (6 tools)
- `create_data_migration` - Create data migration
- `modify_data_migration` - Modify migration
- `delete_data_migration` - Delete migration
- `describe_data_migrations` - List migrations
- `start_data_migration` - Start migration
- `stop_data_migration` - Stop migration

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DMS_AWS_REGION` | us-east-1 | AWS region for DMS operations |
| `DMS_AWS_PROFILE` | None | AWS credentials profile |
| `DMS_READ_ONLY_MODE` | false | Enable read-only mode |
| `DMS_DEFAULT_TIMEOUT` | 300 | Operation timeout (seconds) |
| `DMS_LOG_LEVEL` | INFO | Logging level |
| `DMS_ENABLE_STRUCTURED_LOGGING` | true | Enable JSON logging |

### Programmatic Configuration


### 16. DMS Serverless: Metadata Model Operations (15 tools)
Schema conversion and transformation tools for database migrations.

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

### 17. Fleet Advisor Operations (9 tools)
Database discovery and analysis for migration planning.

- `create_fleet_advisor_collector` - Create data collector
- `delete_fleet_advisor_collector` - Delete collector
- `describe_fleet_advisor_collectors` - List collectors
- `delete_fleet_advisor_databases` - Delete discovered databases
- `describe_fleet_advisor_databases` - List discovered databases
- `describe_fleet_advisor_lsa_analysis` - View LSA analysis results
- `run_fleet_advisor_lsa_analysis` - Run LSA analysis
- `describe_fleet_advisor_schema_object_summary` - View schema object summary
- `describe_fleet_advisor_schemas` - List schemas

### 18. Recommendation Operations (4 tools)
Migration optimization recommendations.

- `describe_recommendations` - List migration recommendations
- `describe_recommendation_limitations` - List recommendation limitations
- `start_recommendations` - Generate recommendations for a database
- `batch_start_recommendations` - Generate recommendations for multiple databases
```python
from awslabs.aws_dms_mcp_server import create_server, DMSServerConfig

config = DMSServerConfig(
    aws_region="us-west-2",
    read_only_mode=True,
    log_level="DEBUG"
)

server = create_server(config)
server.run()
```



## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the Apache License 2.0 - see [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [AWS Labs MCP Servers](https://awslabs.github.io/mcp/servers/aws-dms-mcp-server/)
- **Issues**: [GitHub Issues](https://github.com/awslabs/mcp/issues)
- **AWS DMS Documentation**: [AWS DMS User Guide](https://docs.aws.amazon.com/dms/)

## Related Projects

- [AWS Labs MCP](https://github.com/awslabs/mcp) - Monorepo for AWS MCP servers
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP framework used by this server
- [Model Context Protocol](https://modelcontextprotocol.io/) - Protocol specification
- [AWS DMS](https://aws.amazon.com/dms/) - AWS Database Migration Service
