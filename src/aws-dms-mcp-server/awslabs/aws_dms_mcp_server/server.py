# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AWS DMS MCP Server - Main server implementation.

This module defines all MCP tools using FastMCP decorators and coordinates
interactions with AWS DMS through utility modules.
"""

import sys
from .config import DMSServerConfig
from .exceptions import DMSMCPException
from .utils.assessment_manager import AssessmentManager
from .utils.certificate_manager import CertificateManager
from .utils.connection_tester import ConnectionTester
from .utils.dms_client import DMSClient
from .utils.endpoint_manager import EndpointManager
from .utils.event_manager import EventManager
from .utils.fleet_advisor_manager import FleetAdvisorManager
from .utils.maintenance_manager import MaintenanceManager
from .utils.metadata_model_manager import MetadataModelManager
from .utils.recommendation_manager import RecommendationManager
from .utils.replication_instance_manager import ReplicationInstanceManager
from .utils.response_formatter import ResponseFormatter
from .utils.serverless_manager import ServerlessManager
from .utils.serverless_replication_manager import ServerlessReplicationManager
from .utils.subnet_group_manager import SubnetGroupManager
from .utils.table_operations import TableOperations
from .utils.task_manager import TaskManager
from datetime import datetime
from fastmcp import FastMCP
from loguru import logger
from typing import Any, Dict, List, Optional


# Initialize server with comprehensive instructions
mcp = FastMCP(
    'aws-dms-mcp-server',
    instructions="""
# AWS Database Migration Service (DMS) MCP Server

This server provides comprehensive AWS DMS management capabilities through 103 tools covering traditional DMS, serverless migrations, and advanced features.

## Tool Categories

### 1. Replication Instance Operations (9 tools)
Core infrastructure management for traditional DMS deployments.

**Tools:**
- `describe_replication_instances` - List and filter replication instances
- `create_replication_instance` - Create new replication instance with Multi-AZ support
- `modify_replication_instance` - Modify instance configuration (class, storage, networking)
- `delete_replication_instance` - Delete unused instances
- `reboot_replication_instance` - Reboot instance with optional failover
- `describe_orderable_replication_instances` - List available instance classes
- `describe_replication_instance_task_logs` - Get task log metadata
- `move_replication_task` - Move task between instances

### 2. Endpoint Operations (11 tools)
Source and target database endpoint management.

**Tools:**
- `describe_endpoints` - List and filter endpoints
- `create_endpoint` - Create source/target endpoint
- `modify_endpoint` - Modify endpoint configuration
- `delete_endpoint` - Delete unused endpoint
- `describe_endpoint_settings` - Get valid settings for database engines
- `describe_endpoint_types` - List supported endpoint types
- `describe_engine_versions` - List available DMS engine versions
- `refresh_schemas` - Refresh schema definitions
- `describe_schemas` - List database schemas
- `describe_refresh_schemas_status` - Get schema refresh status

### 3. Connection Operations (3 tools)
Test and manage connections between instances and endpoints.

**Tools:**
- `test_connection` - Test connectivity (includes automatic polling)
- `describe_connections` - List connection test results
- `delete_connection` - Delete connection configuration

### 4. Replication Task Operations (7 tools)
Manage migration tasks and lifecycle.

**Tools:**
- `describe_replication_tasks` - List tasks with status
- `create_replication_task` - Create migration task with table mappings
- `modify_replication_task` - Modify task configuration
- `delete_replication_task` - Delete stopped task
- `start_replication_task` - Start/resume/reload task
- `stop_replication_task` - Stop running task

### 5. Table Operations (3 tools)
Monitor and manage table-level replication.

**Tools:**
- `describe_table_statistics` - Get detailed table metrics (traditional DMS)
- `describe_replication_table_statistics` - Get table statistics (supports serverless)
- `reload_replication_tables` - Reload specific tables
- `reload_tables` - Reload tables (serverless)

### 6. Task Assessment Operations (9 tools)
Quality monitoring and premigration assessments.

**Tools:**
- `start_replication_task_assessment` - Start assessment (legacy API)
- `start_replication_task_assessment_run` - Start new assessment run
- `cancel_replication_task_assessment_run` - Cancel running assessment
- `delete_replication_task_assessment_run` - Delete assessment run
- `describe_replication_task_assessment_results` - List results (legacy)
- `describe_replication_task_assessment_runs` - List assessment runs
- `describe_replication_task_individual_assessments` - List individual assessments
- `describe_applicable_individual_assessments` - List applicable assessments

### 7. Certificate Operations (3 tools)
SSL certificate management for secure connections.

**Tools:**
- `import_certificate` - Import PEM or Oracle wallet certificates
- `describe_certificates` - List SSL certificates
- `delete_certificate` - Delete unused certificate

### 8. Subnet Group Operations (4 tools)
VPC networking configuration for replication instances.

**Tools:**
- `create_replication_subnet_group` - Create subnet group
- `modify_replication_subnet_group` - Modify subnet configuration
- `describe_replication_subnet_groups` - List subnet groups
- `delete_replication_subnet_group` - Delete unused subnet group

### 9. Event Operations (7 tools)
Event notifications and monitoring via SNS/EventBridge.

**Tools:**
- `create_event_subscription` - Create SNS event subscription
- `modify_event_subscription` - Modify subscription configuration
- `delete_event_subscription` - Delete subscription
- `describe_event_subscriptions` - List subscriptions
- `describe_events` - List DMS events with filtering
- `describe_event_categories` - List available event categories
- `update_subscriptions_to_event_bridge` - Migrate to EventBridge

### 10. Maintenance and Tagging Operations (6 tools)
Resource maintenance and organization.

**Tools:**
- `apply_pending_maintenance_action` - Apply maintenance updates
- `describe_pending_maintenance_actions` - List pending maintenance
- `describe_account_attributes` - Get account quotas and limits
- `add_tags_to_resource` - Add resource tags
- `remove_tags_from_resource` - Remove resource tags
- `list_tags_for_resource` - List resource tags

### 11. DMS Serverless: Replication Config Operations (7 tools)
Serverless replication without managing instances.

**Tools:**
- `create_replication_config` - Create serverless replication config
- `modify_replication_config` - Modify config
- `delete_replication_config` - Delete config
- `describe_replication_configs` - List configurations
- `describe_replications` - List running replications
- `start_replication` - Start serverless replication
- `stop_replication` - Stop serverless replication

### 12-15. DMS Serverless: Migration Management (18 tools)
Project organization and data provider management.

**Tools:**
- Migration Projects: `create/modify/delete/describe_migration_projects`
- Data Providers: `create/modify/delete/describe_data_providers`
- Instance Profiles: `create/modify/delete/describe_instance_profiles`
- Data Migrations: `create/modify/delete/describe/start/stop_data_migrations`

### 16. Metadata Model & Schema Conversion (15 tools)
Schema conversion and transformation for database migrations.

**Tools:**
- Conversion Config: `describe/modify_conversion_configuration`
- Extension Packs: `describe/start_extension_pack_associations`
- Assessments: `describe/start_metadata_model_assessments`
- Conversions: `describe/start_metadata_model_conversions`
- Script Exports: `describe/start_metadata_model_exports_as_script`
- Target Exports: `describe/start_metadata_model_exports_to_target`
- Imports: `describe/start_metadata_model_imports`
- Export Assessment: `export_metadata_model_assessment`

### 17. Fleet Advisor (9 tools)
Database discovery and analysis for migration planning.

**Tools:**
- `create/delete/describe_fleet_advisor_collectors`
- `delete/describe_fleet_advisor_databases`
- `describe/run_fleet_advisor_lsa_analysis`
- `describe_fleet_advisor_schema_object_summary`
- `describe_fleet_advisor_schemas`

### 18. Recommendations (4 tools)
Migration optimization recommendations.

**Tools:**
- `describe_recommendations` - List recommendations
- `describe_recommendation_limitations` - List limitations
- `start_recommendations` - Generate recommendations
- `batch_start_recommendations` - Batch generate recommendations

## Usage Guidelines

1. **Discovery**: Start with `describe_*` operations to list existing resources
2. **Creation**: Use `create_*` operations to provision new resources
3. **Modification**: Use `modify_*` operations to update configurations
4. **Lifecycle**: Use `start_*`/`stop_*` operations for task management
5. **Testing**: Use `test_connection` before creating tasks to verify connectivity
6. **Monitoring**: Use assessment and table statistics tools for quality checks
7. **Security**: Use certificates for SSL connections, manage access with IAM roles

## Read-Only Mode

When read-only mode is enabled, all mutating operations are blocked:
- All `create_*`, `modify_*`, `delete_*` operations return error
- All `start_*`, `stop_*`, `reboot_*` operations return error
- All `add_*`, `remove_*`, `import_*`, `apply_*` operations return error
- Only `describe_*`, `list_*`, and read operations allowed

## Common Workflows

### Setting Up a Migration
1. Create replication instance: `create_replication_instance`
2. Create source endpoint: `create_endpoint` (type: source)
3. Create target endpoint: `create_endpoint` (type: target)
4. Test connections: `test_connection` for both endpoints
5. Create replication task: `create_replication_task` with table mappings
6. Start task: `start_replication_task`

### Monitoring a Migration
1. Check task status: `describe_replication_tasks`
2. View table statistics: `describe_table_statistics`
3. Check for errors: `describe_events`
4. Run quality assessment: `start_replication_task_assessment_run`

## Reference Documentation

- **boto3 DMS API**: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dms.html
- **AWS DMS User Guide**: https://docs.aws.amazon.com/dms/latest/userguide/
- **DMS Best Practices**: https://docs.aws.amazon.com/dms/latest/userguide/CHAP_BestPractices.html
""",
)

# Global configuration and clients (initialized in create_server)
config: DMSServerConfig
dms_client: DMSClient
instance_manager: ReplicationInstanceManager
endpoint_manager: EndpointManager
task_manager: TaskManager
table_ops: TableOperations
connection_tester: ConnectionTester
assessment_manager: AssessmentManager
certificate_manager: CertificateManager
subnet_group_manager: SubnetGroupManager
event_manager: EventManager
maintenance_manager: MaintenanceManager
serverless_replication_manager: ServerlessReplicationManager
serverless_manager: ServerlessManager
metadata_model_manager: MetadataModelManager
fleet_advisor_manager: FleetAdvisorManager
recommendation_manager: RecommendationManager


def create_server(server_config: Optional[DMSServerConfig] = None) -> FastMCP:
    """Create and configure the AWS DMS MCP server.

    Args:
        server_config: Optional configuration object. If None, loads from environment.

    Returns:
        Configured FastMCP server instance
    """
    global config, dms_client, instance_manager, endpoint_manager
    global \
        task_manager, \
        table_ops, \
        connection_tester, \
        assessment_manager, \
        certificate_manager, \
        subnet_group_manager, \
        event_manager, \
        maintenance_manager, \
        serverless_replication_manager, \
        serverless_manager, \
        metadata_model_manager, \
        fleet_advisor_manager, \
        recommendation_manager

    # Initialize configuration
    config = server_config or DMSServerConfig()

    # Configure logging
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        level=config.log_level,
        format='<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
        colorize=True,
    )

    if config.enable_structured_logging:
        logger.add(sys.stderr, level=config.log_level, serialize=True)

    logger.info(
        'Initializing AWS DMS MCP Server',
        version='0.0.3',
        region=config.aws_region,
        read_only_mode=config.read_only_mode,
    )

    # Initialize DMS client and managers
    dms_client = DMSClient(config)
    instance_manager = ReplicationInstanceManager(dms_client)
    endpoint_manager = EndpointManager(dms_client)
    task_manager = TaskManager(dms_client)
    table_ops = TableOperations(dms_client)
    connection_tester = ConnectionTester(dms_client, config.enable_connection_caching)
    assessment_manager = AssessmentManager(dms_client)
    certificate_manager = CertificateManager(dms_client)
    subnet_group_manager = SubnetGroupManager(dms_client)
    event_manager = EventManager(dms_client)
    maintenance_manager = MaintenanceManager(dms_client)
    serverless_replication_manager = ServerlessReplicationManager(dms_client)
    serverless_manager = ServerlessManager(dms_client)
    metadata_model_manager = MetadataModelManager(dms_client)
    fleet_advisor_manager = FleetAdvisorManager(dms_client)
    recommendation_manager = RecommendationManager(dms_client)

    logger.info('AWS DMS MCP Server initialized successfully')
    return mcp


# ============================================================================
# REPLICATION INSTANCE TOOLS
# ============================================================================


@mcp.tool()
def describe_replication_instances(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List and describe AWS DMS replication instances with optional filtering.

    Args:
        filters: Optional filters for instance selection (e.g., by status, class)
        max_results: Maximum number of results per page (1-100)
        marker: Pagination token from previous response

    Returns:
        Dictionary containing:
        - instances: List of replication instance details
        - marker: Next page token (if more results available)
        - count: Number of instances returned

    Raises:
        DMSAccessDeniedException: Insufficient IAM permissions
        DMSInvalidParameterException: Invalid filter values
    """
    logger.info('describe_replication_instances called', filters=filters, max_results=max_results)

    try:
        result = instance_manager.list_instances(
            filters=filters, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe replication instances', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_replication_instances', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def create_replication_instance(
    replication_instance_identifier: str,
    replication_instance_class: str,
    allocated_storage: int = 50,
    multi_az: bool = False,
    engine_version: Optional[str] = None,
    vpc_security_group_ids: Optional[List[str]] = None,
    replication_subnet_group_identifier: Optional[str] = None,
    publicly_accessible: bool = False,
    tags: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Create a new AWS DMS replication instance with Multi-AZ support.

    Args:
        replication_instance_identifier: Unique identifier for the instance
        replication_instance_class: Instance class (e.g., dms.t3.medium)
        allocated_storage: Storage in GB (5-6144)
        multi_az: Enable Multi-AZ deployment for high availability
        engine_version: DMS engine version (optional, uses latest if not specified)
        vpc_security_group_ids: VPC security group IDs
        replication_subnet_group_identifier: Replication subnet group
        publicly_accessible: Make instance publicly accessible
        tags: Resource tags as key-value pairs

    Returns:
        Dictionary containing:
        - instance: Created instance details
        - message: Status message

    Raises:
        DMSResourceInUseException: Identifier already exists
        DMSInvalidParameterException: Invalid configuration
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('create_replication_instance called', identifier=replication_instance_identifier)

    try:
        # Build parameters
        params: Dict[str, Any] = {
            'ReplicationInstanceIdentifier': replication_instance_identifier,
            'ReplicationInstanceClass': replication_instance_class,
            'AllocatedStorage': allocated_storage,
            'MultiAZ': multi_az,
            'PubliclyAccessible': publicly_accessible,
        }

        if engine_version:
            params['EngineVersion'] = engine_version
        if vpc_security_group_ids:
            params['VpcSecurityGroupIds'] = vpc_security_group_ids
        if replication_subnet_group_identifier:
            params['ReplicationSubnetGroupIdentifier'] = replication_subnet_group_identifier
        if tags:
            params['Tags'] = tags

        result = instance_manager.create_instance(params)
        return result
    except DMSMCPException as e:
        logger.error('Failed to create replication instance', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in create_replication_instance', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def modify_replication_instance(
    replication_instance_arn: str,
    allocated_storage: Optional[int] = None,
    apply_immediately: bool = False,
    replication_instance_class: Optional[str] = None,
    vpc_security_group_ids: Optional[List[str]] = None,
    preferred_maintenance_window: Optional[str] = None,
    multi_az: Optional[bool] = None,
    engine_version: Optional[str] = None,
    allow_major_version_upgrade: bool = False,
    auto_minor_version_upgrade: Optional[bool] = None,
    replication_instance_identifier: Optional[str] = None,
) -> Dict[str, Any]:
    """Modify AWS DMS replication instance configuration.

    Args:
        replication_instance_arn: Instance ARN to modify
        allocated_storage: New storage in GB (50-6144)
        apply_immediately: Apply changes immediately (true) or during maintenance window (false)
        replication_instance_class: New instance class
        vpc_security_group_ids: Updated VPC security group IDs
        preferred_maintenance_window: Maintenance window (format: ddd:hh24:mi-ddd:hh24:mi)
        multi_az: Enable/disable Multi-AZ
        engine_version: New DMS engine version
        allow_major_version_upgrade: Allow major version upgrade
        auto_minor_version_upgrade: Enable auto minor version upgrade
        replication_instance_identifier: New instance identifier

    Returns:
        Dictionary containing modified instance details

    Raises:
        DMSResourceNotFoundException: Instance not found
        DMSInvalidParameterException: Invalid configuration
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('modify_replication_instance called', instance_arn=replication_instance_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('modify_replication_instance not available in read-only mode')
        )

    try:
        params: Dict[str, Any] = {
            'ReplicationInstanceArn': replication_instance_arn,
            'ApplyImmediately': apply_immediately,
            'AllowMajorVersionUpgrade': allow_major_version_upgrade,
        }
        if allocated_storage is not None:
            params['AllocatedStorage'] = allocated_storage
        if replication_instance_class:
            params['ReplicationInstanceClass'] = replication_instance_class
        if vpc_security_group_ids:
            params['VpcSecurityGroupIds'] = vpc_security_group_ids
        if preferred_maintenance_window:
            params['PreferredMaintenanceWindow'] = preferred_maintenance_window
        if multi_az is not None:
            params['MultiAZ'] = multi_az
        if engine_version:
            params['EngineVersion'] = engine_version
        if auto_minor_version_upgrade is not None:
            params['AutoMinorVersionUpgrade'] = auto_minor_version_upgrade
        if replication_instance_identifier:
            params['ReplicationInstanceIdentifier'] = replication_instance_identifier

        result = instance_manager.modify_instance(params)
        return result
    except DMSMCPException as e:
        logger.error('Failed to modify replication instance', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in modify_replication_instance', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def delete_replication_instance(replication_instance_arn: str) -> Dict[str, Any]:
    """Delete an AWS DMS replication instance.

    Args:
        replication_instance_arn: Instance ARN to delete

    Returns:
        Dictionary containing deleted instance details

    Raises:
        DMSResourceNotFoundException: Instance not found
        DMSInvalidParameterException: Instance is in use
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('delete_replication_instance called', instance_arn=replication_instance_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('delete_replication_instance not available in read-only mode')
        )

    try:
        result = instance_manager.delete_instance(instance_arn=replication_instance_arn)
        return result
    except DMSMCPException as e:
        logger.error('Failed to delete replication instance', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in delete_replication_instance', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def reboot_replication_instance(
    replication_instance_arn: str, force_failover: bool = False
) -> Dict[str, Any]:
    """Reboot an AWS DMS replication instance.

    Args:
        replication_instance_arn: Instance ARN to reboot
        force_failover: Force failover to secondary AZ (Multi-AZ only)

    Returns:
        Dictionary containing instance details

    Raises:
        DMSResourceNotFoundException: Instance not found
        DMSInvalidParameterException: Invalid state for reboot
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('reboot_replication_instance called', instance_arn=replication_instance_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('reboot_replication_instance not available in read-only mode')
        )

    try:
        result = instance_manager.reboot_instance(
            instance_arn=replication_instance_arn, force_failover=force_failover
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to reboot replication instance', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in reboot_replication_instance', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_orderable_replication_instances(
    max_results: int = 100, marker: Optional[str] = None
) -> Dict[str, Any]:
    """List available replication instance classes and configurations.

    Args:
        max_results: Maximum results per page (20-100)
        marker: Pagination token

    Returns:
        Dictionary containing orderable instance configurations
    """
    logger.info('describe_orderable_replication_instances called')

    try:
        result = instance_manager.list_orderable_instances(max_results=max_results, marker=marker)
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe orderable replication instances', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_orderable_replication_instances', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_replication_instance_task_logs(
    replication_instance_arn: str, max_results: int = 100, marker: Optional[str] = None
) -> Dict[str, Any]:
    """Get task log metadata for a replication instance.

    Args:
        replication_instance_arn: Instance ARN
        max_results: Maximum results per page
        marker: Pagination token

    Returns:
        Dictionary containing task log details

    Raises:
        DMSResourceNotFoundException: Instance not found
    """
    logger.info(
        'describe_replication_instance_task_logs called', instance_arn=replication_instance_arn
    )

    try:
        result = instance_manager.get_task_logs(
            instance_arn=replication_instance_arn, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe replication instance task logs', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_replication_instance_task_logs', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def move_replication_task(
    replication_task_arn: str, target_replication_instance_arn: str
) -> Dict[str, Any]:
    """Move a replication task to a different replication instance.

    Args:
        replication_task_arn: Task ARN to move
        target_replication_instance_arn: Destination instance ARN

    Returns:
        Dictionary containing moved task details

    Raises:
        DMSResourceNotFoundException: Task or instance not found
        DMSInvalidParameterException: Invalid move operation
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('move_replication_task called', task_arn=replication_task_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('move_replication_task not available in read-only mode')
        )

    try:
        result = task_manager.move_task(
            task_arn=replication_task_arn, target_instance_arn=target_replication_instance_arn
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to move replication task', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in move_replication_task', error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# ENDPOINT TOOLS
# ============================================================================


@mcp.tool()
def describe_endpoints(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List and describe source/target database endpoints.

    Args:
        filters: Optional filters (by type, engine, status)
        max_results: Maximum results per page (1-100)
        marker: Pagination token

    Returns:
        Dictionary containing:
        - endpoints: List of endpoint details
        - count: Number of endpoints returned
    """
    logger.info('describe_endpoints called', filters=filters)

    try:
        result = endpoint_manager.list_endpoints(
            filters=filters, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe endpoints', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_endpoints', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def create_endpoint(
    endpoint_identifier: str,
    endpoint_type: str,  # "source" or "target"
    engine_name: str,
    server_name: str,
    port: int,
    database_name: str,
    username: str,
    password: str,
    ssl_mode: str = 'none',
    extra_connection_attributes: Optional[str] = None,
    certificate_arn: Optional[str] = None,
    secrets_manager_secret_id: Optional[str] = None,
    tags: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Create a database endpoint for source or target.

    Supported engines: mysql, postgres, oracle, mariadb, aurora, aurora-postgresql

    Args:
        endpoint_identifier: Unique identifier
        endpoint_type: "source" or "target"
        engine_name: Database engine type
        server_name: Database hostname or IP
        port: Database port (1-65535)
        database_name: Database name
        username: Database username
        password: Database password (will be masked in logs)
        ssl_mode: SSL connection mode (none, require, verify-ca, verify-full)
        extra_connection_attributes: Additional connection parameters
        certificate_arn: SSL certificate ARN
        secrets_manager_secret_id: AWS Secrets Manager secret ID
        tags: Resource tags

    Returns:
        Dictionary containing:
        - endpoint: Created endpoint details
        - message: Status message
        - security_warning: Credential storage warning

    Raises:
        DMSResourceInUseException: Endpoint identifier exists
        DMSInvalidParameterException: Invalid engine configuration
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('create_endpoint called', identifier=endpoint_identifier, engine=engine_name)

    try:
        # Build parameters
        params: Dict[str, Any] = {
            'EndpointIdentifier': endpoint_identifier,
            'EndpointType': endpoint_type,
            'EngineName': engine_name,
            'ServerName': server_name,
            'Port': port,
            'DatabaseName': database_name,
            'Username': username,
            'Password': password,
            'SslMode': ssl_mode,
        }

        if extra_connection_attributes:
            params['ExtraConnectionAttributes'] = extra_connection_attributes
        if certificate_arn:
            params['CertificateArn'] = certificate_arn
        if secrets_manager_secret_id:
            params['SecretsManagerSecretId'] = secrets_manager_secret_id
        if tags:
            params['Tags'] = tags

        result = endpoint_manager.create_endpoint(params)
        return result
    except DMSMCPException as e:
        logger.error('Failed to create endpoint', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in create_endpoint', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def modify_endpoint(
    endpoint_arn: str,
    endpoint_identifier: Optional[str] = None,
    endpoint_type: Optional[str] = None,
    engine_name: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    server_name: Optional[str] = None,
    port: Optional[int] = None,
    database_name: Optional[str] = None,
    extra_connection_attributes: Optional[str] = None,
    certificate_arn: Optional[str] = None,
    ssl_mode: Optional[str] = None,
    secrets_manager_secret_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Modify AWS DMS endpoint configuration.

    Args:
        endpoint_arn: Endpoint ARN to modify
        endpoint_identifier: New endpoint identifier
        endpoint_type: New endpoint type (source/target)
        engine_name: New engine name
        username: New username
        password: New password (will be masked in logs)
        server_name: New server hostname
        port: New port number
        database_name: New database name
        extra_connection_attributes: Additional connection parameters
        certificate_arn: SSL certificate ARN
        ssl_mode: SSL mode (none, require, verify-ca, verify-full)
        secrets_manager_secret_id: AWS Secrets Manager secret ID

    Returns:
        Dictionary containing modified endpoint details

    Raises:
        DMSResourceNotFoundException: Endpoint not found
        DMSInvalidParameterException: Invalid configuration
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('modify_endpoint called', endpoint_arn=endpoint_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('modify_endpoint not available in read-only mode')
        )

    try:
        params: Dict[str, Any] = {'EndpointArn': endpoint_arn}
        if endpoint_identifier:
            params['EndpointIdentifier'] = endpoint_identifier
        if endpoint_type:
            params['EndpointType'] = endpoint_type
        if engine_name:
            params['EngineName'] = engine_name
        if username:
            params['Username'] = username
        if password:
            params['Password'] = password
        if server_name:
            params['ServerName'] = server_name
        if port is not None:
            params['Port'] = port
        if database_name:
            params['DatabaseName'] = database_name
        if extra_connection_attributes:
            params['ExtraConnectionAttributes'] = extra_connection_attributes
        if certificate_arn:
            params['CertificateArn'] = certificate_arn
        if ssl_mode:
            params['SslMode'] = ssl_mode
        if secrets_manager_secret_id:
            params['SecretsManagerSecretId'] = secrets_manager_secret_id

        result = endpoint_manager.modify_endpoint(params)
        return result
    except DMSMCPException as e:
        logger.error('Failed to modify endpoint', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in modify_endpoint', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_endpoint_settings(
    engine_name: str, max_results: int = 100, marker: Optional[str] = None
) -> Dict[str, Any]:
    """Get valid endpoint settings for a database engine.

    Args:
        engine_name: Database engine (mysql, postgres, oracle, etc.)
        max_results: Maximum results per page
        marker: Pagination token

    Returns:
        Dictionary containing endpoint settings for the engine
    """
    logger.info('describe_endpoint_settings called', engine=engine_name)

    try:
        result = endpoint_manager.get_endpoint_settings(
            engine_name=engine_name, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe endpoint settings', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_endpoint_settings', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_endpoint_types(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List supported endpoint types and database engines.

    Args:
        filters: Optional filters for endpoint types
        max_results: Maximum results per page
        marker: Pagination token

    Returns:
        Dictionary containing supported endpoint types
    """
    logger.info('describe_endpoint_types called')

    try:
        result = endpoint_manager.list_endpoint_types(
            filters=filters, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe endpoint types', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_endpoint_types', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_engine_versions(
    engine_name: Optional[str] = None, max_results: int = 100, marker: Optional[str] = None
) -> Dict[str, Any]:
    """List available DMS engine versions.

    Args:
        engine_name: Optional engine name to filter
        max_results: Maximum results per page
        marker: Pagination token

    Returns:
        Dictionary containing available engine versions
    """
    logger.info('describe_engine_versions called', engine=engine_name)

    try:
        result = endpoint_manager.list_engine_versions(
            engine_name=engine_name, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe engine versions', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_engine_versions', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def refresh_schemas(endpoint_arn: str, replication_instance_arn: str) -> Dict[str, Any]:
    """Refresh schema definitions for an endpoint.

    Args:
        endpoint_arn: Endpoint ARN
        replication_instance_arn: Replication instance ARN to use

    Returns:
        Dictionary containing refresh status

    Raises:
        DMSResourceNotFoundException: Endpoint or instance not found
        DMSInvalidParameterException: Invalid parameters
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('refresh_schemas called', endpoint_arn=endpoint_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('refresh_schemas not available in read-only mode')
        )

    try:
        result = endpoint_manager.refresh_schemas(
            endpoint_arn=endpoint_arn, instance_arn=replication_instance_arn
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to refresh schemas', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in refresh_schemas', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_schemas(
    endpoint_arn: str, max_results: int = 100, marker: Optional[str] = None
) -> Dict[str, Any]:
    """List database schemas for an endpoint.

    Args:
        endpoint_arn: Endpoint ARN
        max_results: Maximum results per page
        marker: Pagination token

    Returns:
        Dictionary containing schema list

    Raises:
        DMSResourceNotFoundException: Endpoint not found
    """
    logger.info('describe_schemas called', endpoint_arn=endpoint_arn)

    try:
        result = endpoint_manager.list_schemas(
            endpoint_arn=endpoint_arn, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe schemas', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_schemas', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_refresh_schemas_status(endpoint_arn: str) -> Dict[str, Any]:
    """Get schema refresh operation status for an endpoint.

    Args:
        endpoint_arn: Endpoint ARN

    Returns:
        Dictionary containing refresh status

    Raises:
        DMSResourceNotFoundException: Endpoint not found
    """
    logger.info('describe_refresh_schemas_status called', endpoint_arn=endpoint_arn)

    try:
        result = endpoint_manager.get_refresh_status(endpoint_arn=endpoint_arn)
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe refresh schemas status', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_refresh_schemas_status', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def modify_replication_task(
    replication_task_arn: str,
    replication_task_identifier: Optional[str] = None,
    migration_type: Optional[str] = None,
    table_mappings: Optional[str] = None,
    replication_task_settings: Optional[str] = None,
    cdc_start_position: Optional[str] = None,
    cdc_start_time: Optional[datetime] = None,
    cdc_stop_position: Optional[str] = None,
    task_data: Optional[str] = None,
) -> Dict[str, Any]:
    """Modify AWS DMS replication task configuration.

    Args:
        replication_task_arn: Task ARN to modify
        replication_task_identifier: New task identifier
        migration_type: New migration type (full-load, cdc, full-load-and-cdc)
        table_mappings: New table mappings JSON string
        replication_task_settings: New task settings JSON string
        cdc_start_position: New CDC start position
        cdc_start_time: New CDC start time
        cdc_stop_position: CDC stop position
        task_data: Task data configuration

    Returns:
        Dictionary containing modified task details

    Raises:
        DMSResourceNotFoundException: Task not found
        DMSInvalidParameterException: Invalid configuration
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('modify_replication_task called', task_arn=replication_task_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('modify_replication_task not available in read-only mode')
        )

    try:
        params: Dict[str, Any] = {'ReplicationTaskArn': replication_task_arn}
        if replication_task_identifier:
            params['ReplicationTaskIdentifier'] = replication_task_identifier
        if migration_type:
            params['MigrationType'] = migration_type
        if table_mappings:
            params['TableMappings'] = table_mappings
        if replication_task_settings:
            params['ReplicationTaskSettings'] = replication_task_settings
        if cdc_start_position:
            params['CdcStartPosition'] = cdc_start_position
        if cdc_start_time:
            params['CdcStartTime'] = cdc_start_time
        if cdc_stop_position:
            params['CdcStopPosition'] = cdc_stop_position
        if task_data:
            params['TaskData'] = task_data

        result = task_manager.modify_task(params)
        return result
    except DMSMCPException as e:
        logger.error('Failed to modify replication task', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in modify_replication_task', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def delete_replication_task(replication_task_arn: str) -> Dict[str, Any]:
    """Delete an AWS DMS replication task.

    Args:
        replication_task_arn: Task ARN to delete

    Returns:
        Dictionary containing deleted task details

    Raises:
        DMSResourceNotFoundException: Task not found
        DMSInvalidParameterException: Task is running
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('delete_replication_task called', task_arn=replication_task_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('delete_replication_task not available in read-only mode')
        )

    try:
        result = task_manager.delete_task(task_arn=replication_task_arn)
        return result
    except DMSMCPException as e:
        logger.error('Failed to delete replication task', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in delete_replication_task', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_replication_table_statistics(
    replication_task_arn: Optional[str] = None,
    replication_config_arn: Optional[str] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """Get table statistics for a replication task or configuration.

    Args:
        replication_task_arn: Task ARN (for traditional DMS)
        replication_config_arn: Config ARN (for DMS Serverless)
        filters: Optional filters (by schema, table)
        max_results: Maximum results per page
        marker: Pagination token

    Returns:
        Dictionary containing table statistics

    Raises:
        DMSResourceNotFoundException: Task/config not found
        DMSInvalidParameterException: Must provide task_arn or config_arn
    """
    logger.info('describe_replication_table_statistics called')

    try:
        result = table_ops.get_replication_table_statistics(
            task_arn=replication_task_arn,
            config_arn=replication_config_arn,
            filters=filters,
            max_results=max_results,
            marker=marker,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe replication table statistics', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_replication_table_statistics', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def reload_tables(
    replication_config_arn: str,
    tables_to_reload: List[Dict[str, str]],
    reload_option: str = 'data-reload',
) -> Dict[str, Any]:
    """Reload specific tables in a DMS Serverless replication.

    Args:
        replication_config_arn: Replication config ARN
        tables_to_reload: List of tables [{schema_name, table_name}, ...]
        reload_option: Reload option (data-reload or validate-only)

    Returns:
        Dictionary containing reload status

    Raises:
        DMSResourceNotFoundException: Config not found
        DMSInvalidParameterException: Invalid table specification
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('reload_tables called', config_arn=replication_config_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('reload_tables not available in read-only mode')
        )

    try:
        tables = [
            {
                'SchemaName': t.get('schema_name') or t.get('SchemaName'),
                'TableName': t.get('table_name') or t.get('TableName'),
            }
            for t in tables_to_reload
        ]
        result = table_ops.reload_serverless_tables(
            config_arn=replication_config_arn, tables=tables, reload_option=reload_option
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to reload tables', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in reload_tables', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def delete_endpoint(endpoint_arn: str) -> Dict[str, Any]:
    """Delete a database endpoint.

    This operation permanently removes the endpoint configuration from AWS DMS.
    The endpoint must not be in use by any replication tasks.

    Args:
        endpoint_arn: The Amazon Resource Name (ARN) of the endpoint to delete

    Returns:
        Dictionary containing:
        - endpoint: Deleted endpoint details
        - message: Confirmation message

    Raises:
        DMSResourceNotFoundException: Endpoint not found
        DMSInvalidParameterException: Endpoint is in use by a task
        DMSReadOnlyModeException: Read-only mode enabled

    Example:
        delete_endpoint(
            endpoint_arn="arn:aws:dms:us-east-1:123456789012:endpoint:ABCD1234"
        )
    """
    logger.info('delete_endpoint called', endpoint_arn=endpoint_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('delete_endpoint not available in read-only mode')
        )

    try:
        result = endpoint_manager.delete_endpoint(endpoint_arn=endpoint_arn)
        return result
    except DMSMCPException as e:
        logger.error('Failed to delete endpoint', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in delete_endpoint', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def test_connection(replication_instance_arn: str, endpoint_arn: str) -> Dict[str, Any]:
    """Test connectivity between a replication instance and an endpoint.

    Args:
        replication_instance_arn: Replication instance ARN
        endpoint_arn: Endpoint ARN

    Returns:
        Dictionary containing:
        - connection_test: Test results with status and message

    Raises:
        DMSConnectionTestException: Connection test failed
        DMSResourceNotFoundException: Instance or endpoint not found
    """
    logger.info('test_connection called', instance=replication_instance_arn, endpoint=endpoint_arn)

    try:
        result = connection_tester.test_connection(
            instance_arn=replication_instance_arn, endpoint_arn=endpoint_arn
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to test connection', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in test_connection', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_connections(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List existing connection test results.

    Args:
        filters: Optional filters (by status, endpoint, etc.)
        max_results: Maximum results per page
        marker: Pagination token

    Returns:
        Dictionary containing:
        - connections: List of connection test results
        - count: Number of connections returned
    """
    logger.info('describe_connections called', filters=filters)

    try:
        result = connection_tester.list_connection_tests(
            filters=filters, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe connections', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_connections', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def delete_connection(endpoint_arn: str, replication_instance_arn: str) -> Dict[str, Any]:
    """Delete a connection between a replication instance and endpoint.

    This removes the connection test results and configuration.

    Args:
        endpoint_arn: Endpoint ARN
        replication_instance_arn: Replication instance ARN

    Returns:
        Dictionary containing:
        - connection: Deleted connection details
        - message: Confirmation message

    Raises:
        DMSResourceNotFoundException: Connection not found
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info(
        'delete_connection called', endpoint=endpoint_arn, instance=replication_instance_arn
    )

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('delete_connection not available in read-only mode')
        )

    try:
        result = connection_tester.delete_connection(
            endpoint_arn=endpoint_arn, replication_instance_arn=replication_instance_arn
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to delete connection', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in delete_connection', error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# REPLICATION TASK TOOLS
# ============================================================================


@mcp.tool()
def describe_replication_tasks(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
    without_settings: bool = False,
) -> Dict[str, Any]:
    """List and describe replication tasks with detailed status.

    Args:
        filters: Optional filters (by status, type, instance)
        max_results: Maximum results per page
        marker: Pagination token
        without_settings: Exclude task settings from response

    Returns:
        Dictionary containing:
        - tasks: List of replication task details
        - count: Number of tasks returned
    """
    logger.info('describe_replication_tasks called', filters=filters)

    try:
        result = task_manager.list_tasks(
            filters=filters,
            max_results=max_results,
            marker=marker,
            without_settings=without_settings,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe replication tasks', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_replication_tasks', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def create_replication_task(
    replication_task_identifier: str,
    source_endpoint_arn: str,
    target_endpoint_arn: str,
    replication_instance_arn: str,
    migration_type: str,  # "full-load", "cdc", or "full-load-and-cdc"
    table_mappings: str,
    replication_task_settings: Optional[str] = None,
    cdc_start_position: Optional[str] = None,
    cdc_start_time: Optional[datetime] = None,
    tags: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Create a replication task with table mappings and CDC configuration.

    Args:
        replication_task_identifier: Unique identifier
        source_endpoint_arn: Source endpoint ARN
        target_endpoint_arn: Target endpoint ARN
        replication_instance_arn: Replication instance ARN
        migration_type: Migration type (full-load, cdc, full-load-and-cdc)
        table_mappings: Table mappings JSON string
        replication_task_settings: Task settings JSON string
        cdc_start_position: CDC start position
        cdc_start_time: CDC start time
        tags: Resource tags

    Returns:
        Dictionary containing:
        - task: Created task details
        - message: Status message

    Raises:
        DMSResourceInUseException: Task identifier exists
        DMSValidationException: Table mappings validation failed
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('create_replication_task called', identifier=replication_task_identifier)

    try:
        # Build parameters
        params: Dict[str, Any] = {
            'ReplicationTaskIdentifier': replication_task_identifier,
            'SourceEndpointArn': source_endpoint_arn,
            'TargetEndpointArn': target_endpoint_arn,
            'ReplicationInstanceArn': replication_instance_arn,
            'MigrationType': migration_type,
            'TableMappings': table_mappings,
        }

        if replication_task_settings:
            params['ReplicationTaskSettings'] = replication_task_settings
        if cdc_start_position:
            params['CdcStartPosition'] = cdc_start_position
        if cdc_start_time:
            params['CdcStartTime'] = cdc_start_time
        if tags:
            params['Tags'] = tags

        result = task_manager.create_task(params)
        return result
    except DMSMCPException as e:
        logger.error('Failed to create replication task', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in create_replication_task', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def start_replication_task(
    replication_task_arn: str,
    start_replication_task_type: str,  # "start-replication", "resume-processing", or "reload-target"
    cdc_start_position: Optional[str] = None,
    cdc_start_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Start a replication task with support for new starts, resume, and reload.

    Args:
        replication_task_arn: Task ARN
        start_replication_task_type: Start type (start-replication, resume-processing, reload-target)
        cdc_start_position: CDC start position (for resume operations)
        cdc_start_time: CDC start time

    Returns:
        Dictionary containing:
        - task: Task details with updated status
        - message: Status message

    Raises:
        DMSResourceNotFoundException: Task not found
        DMSResourceInUseException: Task already running
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('start_replication_task called', task_arn=replication_task_arn)

    try:
        result = task_manager.start_task(
            task_arn=replication_task_arn,
            start_type=start_replication_task_type,
            cdc_start_position=cdc_start_position,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to start replication task', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in start_replication_task', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def stop_replication_task(replication_task_arn: str) -> Dict[str, Any]:
    """Stop a running replication task safely.

    Args:
        replication_task_arn: Task ARN

    Returns:
        Dictionary containing:
        - task: Task details with updated status
        - message: Status message

    Raises:
        DMSResourceNotFoundException: Task not found
        DMSInvalidParameterException: Task not in stoppable state
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('stop_replication_task called', task_arn=replication_task_arn)

    try:
        result = task_manager.stop_task(task_arn=replication_task_arn)
        return result
    except DMSMCPException as e:
        logger.error('Failed to stop replication task', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in stop_replication_task', error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# TABLE OPERATIONS TOOLS
# ============================================================================


@mcp.tool()
def describe_table_statistics(
    replication_task_arn: str,
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """Get detailed table-level replication statistics.

    Provides metrics including:
    - Row counts (inserts, updates, deletes, DDLs)
    - Full load progress and errors
    - Validation status
    - Last update times

    Args:
        replication_task_arn: Task ARN
        filters: Optional filters (by schema, table, status)
        max_results: Maximum results per page
        marker: Pagination token

    Returns:
        Dictionary containing:
        - table_statistics: List of table statistics
        - count: Number of tables returned
        - summary: Aggregate statistics

    Raises:
        DMSResourceNotFoundException: Task not found
    """
    logger.info('describe_table_statistics called', task_arn=replication_task_arn)

    try:
        result = table_ops.get_table_statistics(
            task_arn=replication_task_arn, filters=filters, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe table statistics', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_table_statistics', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def reload_replication_tables(
    replication_task_arn: str,
    tables_to_reload: List[Dict[str, str]],
    reload_option: str = 'data-reload',  # "data-reload" or "validate-only"
) -> Dict[str, Any]:
    """Reload specific tables during replication.

    Args:
        replication_task_arn: Task ARN
        tables_to_reload: List of tables [{schema_name, table_name}, ...]
        reload_option: Reload option (data-reload or validate-only)

    Returns:
        Dictionary containing:
        - task_arn: Task ARN
        - tables_reloaded: List of reloaded tables
        - reload_option: Reload option used
        - message: Status message

    Raises:
        DMSResourceNotFoundException: Task not found
        DMSInvalidParameterException: Invalid table specification
        DMSResourceInUseException: Task not in reloadable state
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('reload_replication_tables called', task_arn=replication_task_arn)

    try:
        # Convert to uppercase keys for API
        tables = [
            {
                'SchemaName': table.get('schema_name') or table.get('SchemaName'),
                'TableName': table.get('table_name') or table.get('TableName'),
            }
            for table in tables_to_reload
        ]

        result = table_ops.reload_tables(
            task_arn=replication_task_arn, tables=tables, reload_option=reload_option
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to reload replication_tables', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in reload_replication_tables', error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# TASK ASSESSMENT TOOLS
# ============================================================================


@mcp.tool()
def start_replication_task_assessment(replication_task_arn: str) -> Dict[str, Any]:
    """Start a replication task assessment (legacy API).

    Args:
        replication_task_arn: Task ARN to assess

    Returns:
        Dictionary containing task details with assessment status

    Raises:
        DMSResourceNotFoundException: Task not found
        DMSInvalidParameterException: Task not in valid state
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('start_replication_task_assessment called', task_arn=replication_task_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('start_replication_task_assessment not available in read-only mode')
        )

    try:
        result = assessment_manager.start_assessment(task_arn=replication_task_arn)
        return result
    except DMSMCPException as e:
        logger.error('Failed to start replication task assessment', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in start_replication_task_assessment', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def start_replication_task_assessment_run(
    replication_task_arn: str,
    service_access_role_arn: str,
    result_location_bucket: str,
    result_location_folder: Optional[str] = None,
    result_encryption_mode: Optional[str] = None,
    result_kms_key_arn: Optional[str] = None,
    assessment_run_name: Optional[str] = None,
    include_only: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Start a new replication task assessment run.

    Args:
        replication_task_arn: Task ARN to assess
        service_access_role_arn: IAM role ARN for S3 access
        result_location_bucket: S3 bucket name for results
        result_location_folder: Optional S3 folder path
        result_encryption_mode: Encryption mode (sse-s3 or sse-kms)
        result_kms_key_arn: KMS key ARN (required if sse-kms)
        assessment_run_name: Optional custom name
        include_only: List of assessment types to include
        exclude: List of assessment types to exclude

    Returns:
        Dictionary containing assessment run details

    Raises:
        DMSResourceNotFoundException: Task not found
        DMSInvalidParameterException: Invalid configuration
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('start_replication_task_assessment_run called', task_arn=replication_task_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException(
                'start_replication_task_assessment_run not available in read-only mode'
            )
        )

    try:
        result = assessment_manager.start_assessment_run(
            task_arn=replication_task_arn,
            service_access_role_arn=service_access_role_arn,
            result_location_bucket=result_location_bucket,
            result_location_folder=result_location_folder,
            result_encryption_mode=result_encryption_mode,
            result_kms_key_arn=result_kms_key_arn,
            assessment_run_name=assessment_run_name,
            include_only=include_only,
            exclude=exclude,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to start assessment run', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in start_replication_task_assessment_run', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def cancel_replication_task_assessment_run(
    replication_task_assessment_run_arn: str,
) -> Dict[str, Any]:
    """Cancel a running replication task assessment.

    Args:
        replication_task_assessment_run_arn: Assessment run ARN to cancel

    Returns:
        Dictionary containing cancelled assessment run details

    Raises:
        DMSResourceNotFoundException: Assessment run not found
        DMSInvalidParameterException: Assessment not in cancellable state
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info(
        'cancel_replication_task_assessment_run called',
        run_arn=replication_task_assessment_run_arn,
    )

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException(
                'cancel_replication_task_assessment_run not available in read-only mode'
            )
        )

    try:
        result = assessment_manager.cancel_assessment_run(
            assessment_run_arn=replication_task_assessment_run_arn
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to cancel assessment run', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in cancel_replication_task_assessment_run', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def delete_replication_task_assessment_run(
    replication_task_assessment_run_arn: str,
) -> Dict[str, Any]:
    """Delete a replication task assessment run.

    Args:
        replication_task_assessment_run_arn: Assessment run ARN to delete

    Returns:
        Dictionary containing deleted assessment run details

    Raises:
        DMSResourceNotFoundException: Assessment run not found
        DMSInvalidParameterException: Assessment run still running
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info(
        'delete_replication_task_assessment_run called',
        run_arn=replication_task_assessment_run_arn,
    )

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException(
                'delete_replication_task_assessment_run not available in read-only mode'
            )
        )

    try:
        result = assessment_manager.delete_assessment_run(
            assessment_run_arn=replication_task_assessment_run_arn
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to delete assessment run', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in delete_replication_task_assessment_run', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_replication_task_assessment_results(
    replication_task_arn: Optional[str] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List replication task assessment results (legacy API).

    Args:
        replication_task_arn: Optional task ARN to filter results
        max_results: Maximum results per page (1-100)
        marker: Pagination token

    Returns:
        Dictionary containing:
        - assessment_results: List of assessment results
        - count: Number of results returned
        - next_marker: Next page token (if more results available)

    Raises:
        DMSResourceNotFoundException: Task not found
    """
    logger.info(
        'describe_replication_task_assessment_results called', task_arn=replication_task_arn
    )

    try:
        result = assessment_manager.list_assessment_results(
            task_arn=replication_task_arn, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe assessment results', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error(
            'Unexpected error in describe_replication_task_assessment_results', error=str(e)
        )
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_replication_task_assessment_runs(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List replication task assessment runs with optional filtering.

    Args:
        filters: Optional filters (by task ARN, status, etc.)
        max_results: Maximum results per page (1-100)
        marker: Pagination token

    Returns:
        Dictionary containing:
        - assessment_runs: List of assessment run details
        - count: Number of runs returned
        - next_marker: Next page token (if more results available)
    """
    logger.info('describe_replication_task_assessment_runs called', filters=filters)

    try:
        result = assessment_manager.list_assessment_runs(
            filters=filters, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe assessment runs', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_replication_task_assessment_runs', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_replication_task_individual_assessments(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List individual premigration assessments with optional filtering.

    Args:
        filters: Optional filters (by assessment name, status, etc.)
        max_results: Maximum results per page (1-100)
        marker: Pagination token

    Returns:
        Dictionary containing:
        - individual_assessments: List of individual assessment details
        - count: Number of assessments returned
        - next_marker: Next page token (if more results available)
    """
    logger.info('describe_replication_task_individual_assessments called', filters=filters)

    try:
        result = assessment_manager.list_individual_assessments(
            filters=filters, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe individual assessments', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error(
            'Unexpected error in describe_replication_task_individual_assessments', error=str(e)
        )
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_applicable_individual_assessments(
    replication_task_arn: Optional[str] = None,
    migration_type: Optional[str] = None,
    source_engine_name: Optional[str] = None,
    target_engine_name: Optional[str] = None,
    replication_instance_arn: Optional[str] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List individual assessments applicable to a migration configuration.

    Args:
        replication_task_arn: Optional task ARN
        migration_type: Migration type (full-load, cdc, full-load-and-cdc)
        source_engine_name: Source database engine
        target_engine_name: Target database engine
        replication_instance_arn: Replication instance ARN
        max_results: Maximum results per page (1-100)
        marker: Pagination token

    Returns:
        Dictionary containing:
        - applicable_assessments: List of applicable assessment names
        - count: Number of assessments returned
        - next_marker: Next page token (if more results available)
    """
    logger.info('describe_applicable_individual_assessments called')

    try:
        result = assessment_manager.list_applicable_assessments(
            task_arn=replication_task_arn,
            migration_type=migration_type,
            source_engine_name=source_engine_name,
            target_engine_name=target_engine_name,
            replication_instance_arn=replication_instance_arn,
            max_results=max_results,
            marker=marker,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe applicable individual assessments', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error(
            'Unexpected error in describe_applicable_individual_assessments', error=str(e)
        )
        return ResponseFormatter.format_error(e)


# ============================================================================

# ============================================================================
# CERTIFICATE OPERATIONS
# ============================================================================


@mcp.tool()
def import_certificate(
    certificate_identifier: str,
    certificate_pem: Optional[str] = None,
    certificate_wallet: Optional[bytes] = None,
    tags: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Import an SSL certificate for DMS endpoint connections.

    Certificates are used to establish secure connections between DMS
    and database endpoints. Supports PEM-encoded certificates and
    Oracle wallet formats.

    Args:
        certificate_identifier: Unique identifier for the certificate
        certificate_pem: PEM-encoded certificate data (for most databases)
        certificate_wallet: Oracle wallet certificate data (for Oracle)
        tags: Resource tags

    Returns:
        Dictionary containing:
        - certificate: Imported certificate details
        - message: Status message

    Raises:
        DMSResourceInUseException: Certificate identifier already exists
        DMSInvalidParameterException: Invalid certificate data
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('import_certificate called', identifier=certificate_identifier)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('import_certificate not available in read-only mode')
        )

    try:
        result = certificate_manager.import_certificate(
            certificate_identifier=certificate_identifier,
            certificate_pem=certificate_pem,
            certificate_wallet=certificate_wallet,
            tags=tags,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to import certificate', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in import_certificate', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_certificates(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List SSL certificates used for DMS endpoint connections.

    Args:
        filters: Optional filters for certificate selection
        max_results: Maximum results per page (1-100)
        marker: Pagination token

    Returns:
        Dictionary containing:
        - certificates: List of certificate details
        - count: Number of certificates returned
        - next_marker: Next page token (if more results available)
    """
    logger.info('describe_certificates called', filters=filters)

    try:
        result = certificate_manager.list_certificates(
            filters=filters, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe certificates', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_certificates', error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# SUBNET GROUP OPERATIONS
# ============================================================================


@mcp.tool()
def create_replication_subnet_group(
    replication_subnet_group_identifier: str,
    replication_subnet_group_description: str,
    subnet_ids: List[str],
    tags: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Create a replication subnet group for VPC networking.

    Subnet groups define the VPC subnets where replication instances will be placed.
    At least two subnets in different Availability Zones are required for Multi-AZ deployments.

    Args:
        replication_subnet_group_identifier: Unique identifier
        replication_subnet_group_description: Description
        subnet_ids: List of subnet IDs (at least one required)
        tags: Resource tags

    Returns:
        Dictionary containing:
        - subnet_group: Created subnet group details
        - message: Status message

    Raises:
        DMSResourceInUseException: Identifier already exists
        DMSInvalidParameterException: Invalid subnet IDs
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info(
        'create_replication_subnet_group called', identifier=replication_subnet_group_identifier
    )

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('create_replication_subnet_group not available in read-only mode')
        )

    try:
        result = subnet_group_manager.create_subnet_group(
            identifier=replication_subnet_group_identifier,
            description=replication_subnet_group_description,
            subnet_ids=subnet_ids,
            tags=tags,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to create replication subnet group', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in create_replication_subnet_group', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def modify_replication_subnet_group(
    replication_subnet_group_identifier: str,
    replication_subnet_group_description: Optional[str] = None,
    subnet_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Modify a replication subnet group configuration.

    Args:
        replication_subnet_group_identifier: Subnet group identifier
        replication_subnet_group_description: New description
        subnet_ids: New list of subnet IDs (at least one if provided)

    Returns:
        Dictionary containing modified subnet group details

    Raises:
        DMSResourceNotFoundException: Subnet group not found
        DMSInvalidParameterException: Invalid subnet IDs
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info(
        'modify_replication_subnet_group called', identifier=replication_subnet_group_identifier
    )

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('modify_replication_subnet_group not available in read-only mode')
        )

    try:
        result = subnet_group_manager.modify_subnet_group(
            identifier=replication_subnet_group_identifier,
            description=replication_subnet_group_description,
            subnet_ids=subnet_ids,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to modify replication subnet group', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in modify_replication_subnet_group', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_replication_subnet_groups(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List replication subnet groups with optional filtering.

    Args:
        filters: Optional filters for subnet group selection
        max_results: Maximum results per page (1-100)
        marker: Pagination token

    Returns:
        Dictionary containing:
        - subnet_groups: List of subnet group details
        - count: Number of subnet groups returned
        - next_marker: Next page token (if more results available)
    """
    logger.info('describe_replication_subnet_groups called', filters=filters)

    try:
        result = subnet_group_manager.list_subnet_groups(
            filters=filters, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe replication subnet groups', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_replication_subnet_groups', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def delete_replication_subnet_group(replication_subnet_group_identifier: str) -> Dict[str, Any]:
    """Delete a replication subnet group.

    The subnet group must not be in use by any replication instances.

    Args:
        replication_subnet_group_identifier: Subnet group identifier to delete

    Returns:
        Dictionary containing:
        - message: Confirmation message
        - identifier: Deleted subnet group identifier

    Raises:
        DMSResourceNotFoundException: Subnet group not found
        DMSInvalidParameterException: Subnet group is in use
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info(
        'delete_replication_subnet_group called', identifier=replication_subnet_group_identifier
    )

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('delete_replication_subnet_group not available in read-only mode')
        )

    try:
        result = subnet_group_manager.delete_subnet_group(
            identifier=replication_subnet_group_identifier
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to delete replication subnet group', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in delete_replication_subnet_group', error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# EVENT OPERATIONS
# ============================================================================


@mcp.tool()
def create_event_subscription(
    subscription_name: str,
    sns_topic_arn: str,
    source_type: Optional[str] = None,
    event_categories: Optional[List[str]] = None,
    source_ids: Optional[List[str]] = None,
    enabled: bool = True,
    tags: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Create an event subscription for DMS notifications via SNS.

    Event subscriptions allow you to receive notifications about DMS events
    such as replication instance status changes, task failures, etc.

    Args:
        subscription_name: Unique subscription name
        sns_topic_arn: SNS topic ARN for notifications
        source_type: Event source type (replication-instance, replication-task, replication-subnet-group)
        event_categories: List of event categories to subscribe to
        source_ids: List of source identifiers to monitor
        enabled: Enable subscription immediately
        tags: Resource tags

    Returns:
        Dictionary containing:
        - event_subscription: Created subscription details
        - message: Status message

    Raises:
        DMSResourceInUseException: Subscription name already exists
        DMSInvalidParameterException: Invalid SNS topic ARN
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('create_event_subscription called', name=subscription_name)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('create_event_subscription not available in read-only mode')
        )

    try:
        result = event_manager.create_event_subscription(
            subscription_name=subscription_name,
            sns_topic_arn=sns_topic_arn,
            source_type=source_type,
            event_categories=event_categories,
            source_ids=source_ids,
            enabled=enabled,
            tags=tags,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to create event subscription', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in create_event_subscription', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def modify_event_subscription(
    subscription_name: str,
    sns_topic_arn: Optional[str] = None,
    source_type: Optional[str] = None,
    event_categories: Optional[List[str]] = None,
    enabled: Optional[bool] = None,
) -> Dict[str, Any]:
    """Modify an event subscription configuration.

    Args:
        subscription_name: Subscription name to modify
        sns_topic_arn: New SNS topic ARN
        source_type: New source type
        event_categories: New event categories
        enabled: Enable or disable subscription

    Returns:
        Dictionary containing modified subscription details

    Raises:
        DMSResourceNotFoundException: Subscription not found
        DMSInvalidParameterException: Invalid configuration
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('modify_event_subscription called', name=subscription_name)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('modify_event_subscription not available in read-only mode')
        )

    try:
        result = event_manager.modify_event_subscription(
            subscription_name=subscription_name,
            sns_topic_arn=sns_topic_arn,
            source_type=source_type,
            event_categories=event_categories,
            enabled=enabled,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to modify event subscription', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in modify_event_subscription', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def delete_event_subscription(subscription_name: str) -> Dict[str, Any]:
    """Delete an event subscription.

    Args:
        subscription_name: Subscription name to delete

    Returns:
        Dictionary containing:
        - event_subscription: Deleted subscription details
        - message: Confirmation message

    Raises:
        DMSResourceNotFoundException: Subscription not found
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('delete_event_subscription called', name=subscription_name)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('delete_event_subscription not available in read-only mode')
        )

    try:
        result = event_manager.delete_event_subscription(subscription_name=subscription_name)
        return result
    except DMSMCPException as e:
        logger.error('Failed to delete event subscription', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in delete_event_subscription', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_event_subscriptions(
    subscription_name: Optional[str] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List event subscriptions with optional filtering.

    Args:
        subscription_name: Optional subscription name to filter
        filters: Optional filters
        max_results: Maximum results per page (1-100)
        marker: Pagination token

    Returns:
        Dictionary containing:
        - event_subscriptions: List of subscription details
        - count: Number of subscriptions returned
        - next_marker: Next page token (if more results available)
    """
    logger.info('describe_event_subscriptions called')

    try:
        result = event_manager.list_event_subscriptions(
            subscription_name=subscription_name,
            filters=filters,
            max_results=max_results,
            marker=marker,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe event subscriptions', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_event_subscriptions', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_events(
    source_identifier: Optional[str] = None,
    source_type: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    duration: Optional[int] = None,
    event_categories: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List DMS events with optional filtering.

    Args:
        source_identifier: Source identifier (instance/task/subnet group identifier)
        source_type: Source type (replication-instance, replication-task, replication-subnet-group)
        start_time: Start time for events (ISO 8601 format)
        end_time: End time for events (ISO 8601 format)
        duration: Duration in minutes from now (alternative to start/end time)
        event_categories: Event categories to filter
        filters: Optional filters
        max_results: Maximum results per page (1-100)
        marker: Pagination token

    Returns:
        Dictionary containing:
        - events: List of event details
        - count: Number of events returned
        - next_marker: Next page token (if more results available)
    """
    logger.info('describe_events called')

    try:
        result = event_manager.list_events(
            source_identifier=source_identifier,
            source_type=source_type,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            event_categories=event_categories,
            filters=filters,
            max_results=max_results,
            marker=marker,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe events', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_events', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_event_categories(
    source_type: Optional[str] = None, filters: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """List available event categories for a source type.

    Args:
        source_type: Source type to get categories for (replication-instance, replication-task, etc.)
        filters: Optional filters

    Returns:
        Dictionary containing:
        - event_category_groups: List of event category groups
        - count: Number of category groups returned
    """
    logger.info('describe_event_categories called', source_type=source_type)

    try:
        result = event_manager.list_event_categories(source_type=source_type, filters=filters)
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe event categories', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_event_categories', error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# MAINTENANCE AND TAGGING OPERATIONS
# ============================================================================


@mcp.tool()
def apply_pending_maintenance_action(
    replication_instance_arn: str, apply_action: str, opt_in_type: str
) -> Dict[str, Any]:
    """Apply a pending maintenance action to a replication instance.

    Maintenance actions include software updates, patches, and other
    system maintenance operations.

    Args:
        replication_instance_arn: Instance ARN
        apply_action: Maintenance action to apply (e.g., 'db-upgrade', 'system-update')
        opt_in_type: When to apply action (immediate, next-maintenance, undo-opt-in)

    Returns:
        Dictionary containing:
        - resource: Resource with updated maintenance actions
        - message: Status message

    Raises:
        DMSResourceNotFoundException: Instance not found
        DMSInvalidParameterException: Invalid action or opt-in type
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('apply_pending_maintenance_action called', instance_arn=replication_instance_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('apply_pending_maintenance_action not available in read-only mode')
        )

    try:
        result = maintenance_manager.apply_pending_maintenance_action(
            resource_arn=replication_instance_arn,
            apply_action=apply_action,
            opt_in_type=opt_in_type,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to apply pending maintenance action', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in apply_pending_maintenance_action', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_pending_maintenance_actions(
    replication_instance_arn: Optional[str] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List pending maintenance actions for DMS resources.

    Args:
        replication_instance_arn: Optional instance ARN to filter
        filters: Optional filters
        max_results: Maximum results per page (1-100)
        marker: Pagination token

    Returns:
        Dictionary containing:
        - pending_maintenance_actions: List of resources with pending maintenance
        - count: Number of resources returned
        - next_marker: Next page token (if more results available)
    """
    logger.info('describe_pending_maintenance_actions called')

    try:
        result = maintenance_manager.list_pending_maintenance_actions(
            resource_arn=replication_instance_arn,
            filters=filters,
            max_results=max_results,
            marker=marker,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe pending maintenance actions', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_pending_maintenance_actions', error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# DMS SERVERLESS: REPLICATION CONFIG OPERATIONS
# ============================================================================


@mcp.tool()
def create_replication_config(
    replication_config_identifier: str,
    source_endpoint_arn: str,
    target_endpoint_arn: str,
    compute_config: Dict[str, Any],
    replication_type: str,
    table_mappings: str,
    replication_settings: Optional[str] = None,
    supplemental_settings: Optional[str] = None,
    resource_identifier: Optional[str] = None,
    tags: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Create a replication configuration for DMS Serverless.

    DMS Serverless automatically provisions and scales compute resources for migrations.

    Args:
        replication_config_identifier: Unique identifier
        source_endpoint_arn: Source endpoint ARN
        target_endpoint_arn: Target endpoint ARN
        compute_config: Compute configuration (format: {"ReplicationSubnetGroupId": "...", "MaxCapacityUnits": 16, "MinCapacityUnits": 1})
        replication_type: Replication type (full-load, cdc, full-load-and-cdc)
        table_mappings: Table mappings JSON string
        replication_settings: Replication settings JSON
        supplemental_settings: Supplemental settings JSON
        resource_identifier: Optional resource identifier
        tags: Resource tags

    Returns:
        Dictionary containing created replication config details

    Raises:
        DMSResourceInUseException: Identifier already exists
        DMSInvalidParameterException: Invalid configuration
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('create_replication_config called', identifier=replication_config_identifier)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('create_replication_config not available in read-only mode')
        )

    try:
        result = serverless_replication_manager.create_replication_config(
            identifier=replication_config_identifier,
            source_endpoint_arn=source_endpoint_arn,
            target_endpoint_arn=target_endpoint_arn,
            compute_config=compute_config,
            replication_type=replication_type,
            table_mappings=table_mappings,
            replication_settings=replication_settings,
            supplemental_settings=supplemental_settings,
            resource_identifier=resource_identifier,
            tags=tags,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to create replication config', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in create_replication_config', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def modify_replication_config(
    replication_config_arn: str,
    replication_config_identifier: Optional[str] = None,
    compute_config: Optional[Dict[str, Any]] = None,
    replication_type: Optional[str] = None,
    table_mappings: Optional[str] = None,
    replication_settings: Optional[str] = None,
    supplemental_settings: Optional[str] = None,
    source_endpoint_arn: Optional[str] = None,
    target_endpoint_arn: Optional[str] = None,
) -> Dict[str, Any]:
    """Modify a DMS Serverless replication configuration.

    Args:
        replication_config_arn: Replication config ARN
        replication_config_identifier: New identifier
        compute_config: New compute configuration
        replication_type: New replication type
        table_mappings: New table mappings
        replication_settings: New replication settings
        supplemental_settings: New supplemental settings
        source_endpoint_arn: New source endpoint ARN
        target_endpoint_arn: New target endpoint ARN

    Returns:
        Dictionary containing modified replication config details

    Raises:
        DMSResourceNotFoundException: Config not found
        DMSInvalidParameterException: Invalid configuration
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('modify_replication_config called', config_arn=replication_config_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('modify_replication_config not available in read-only mode')
        )

    try:
        result = serverless_replication_manager.modify_replication_config(
            arn=replication_config_arn,
            identifier=replication_config_identifier,
            compute_config=compute_config,
            replication_type=replication_type,
            table_mappings=table_mappings,
            replication_settings=replication_settings,
            supplemental_settings=supplemental_settings,
            source_endpoint_arn=source_endpoint_arn,
            target_endpoint_arn=target_endpoint_arn,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to modify replication config', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in modify_replication_config', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def delete_replication_config(replication_config_arn: str) -> Dict[str, Any]:
    """Delete a DMS Serverless replication configuration.

    The replication must be stopped before deletion.

    Args:
        replication_config_arn: Replication config ARN

    Returns:
        Dictionary containing deleted replication config details

    Raises:
        DMSResourceNotFoundException: Config not found
        DMSInvalidParameterException: Replication is running
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('delete_replication_config called', config_arn=replication_config_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('delete_replication_config not available in read-only mode')
        )

    try:
        result = serverless_replication_manager.delete_replication_config(
            arn=replication_config_arn
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to delete replication config', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in delete_replication_config', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_replication_configs(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List DMS Serverless replication configurations.

    Args:
        filters: Optional filters for configuration selection
        max_results: Maximum results per page (1-100)
        marker: Pagination token

    Returns:
        Dictionary containing:
        - replication_configs: List of configuration details
        - count: Number of configs returned
        - next_marker: Next page token (if more results available)
    """
    logger.info('describe_replication_configs called', filters=filters)

    try:
        result = serverless_replication_manager.list_replication_configs(
            filters=filters, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe replication configs', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_replication_configs', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_replications(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List DMS Serverless replications (running instances of configs).

    Args:
        filters: Optional filters for replication selection
        max_results: Maximum results per page (1-100)
        marker: Pagination token

    Returns:
        Dictionary containing:
        - replications: List of replication details
        - count: Number of replications returned
        - next_marker: Next page token (if more results available)
    """
    logger.info('describe_replications called', filters=filters)

    try:
        result = serverless_replication_manager.list_replications(
            filters=filters, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe replications', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_replications', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def start_replication(
    replication_config_arn: str,
    start_replication_type: str,
    cdc_start_time: Optional[str] = None,
    cdc_start_position: Optional[str] = None,
    cdc_stop_position: Optional[str] = None,
) -> Dict[str, Any]:
    """Start a DMS Serverless replication.

    Args:
        replication_config_arn: Replication config ARN
        start_replication_type: Start type (start-replication, resume-processing, reload-target)
        cdc_start_time: CDC start time (ISO 8601 format)
        cdc_start_position: CDC start position
        cdc_stop_position: CDC stop position

    Returns:
        Dictionary containing started replication details

    Raises:
        DMSResourceNotFoundException: Config not found
        DMSInvalidParameterException: Invalid start type
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('start_replication called', config_arn=replication_config_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('start_replication not available in read-only mode')
        )

    try:
        result = serverless_replication_manager.start_replication(
            arn=replication_config_arn,
            start_replication_type=start_replication_type,
            cdc_start_time=cdc_start_time,
            cdc_start_position=cdc_start_position,
            cdc_stop_position=cdc_stop_position,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to start replication', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in start_replication', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def stop_replication(replication_config_arn: str) -> Dict[str, Any]:
    """Stop a running DMS Serverless replication.

    Args:
        replication_config_arn: Replication config ARN

    Returns:
        Dictionary containing stopped replication details

    Raises:
        DMSResourceNotFoundException: Config not found
        DMSInvalidParameterException: Replication not in stoppable state
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('stop_replication called', config_arn=replication_config_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('stop_replication not available in read-only mode')
        )

    try:
        result = serverless_replication_manager.stop_replication(arn=replication_config_arn)
        return result
    except DMSMCPException as e:
        logger.error('Failed to stop replication', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in stop_replication', error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# DMS SERVERLESS: MIGRATION PROJECT OPERATIONS
# ============================================================================


@mcp.tool()
def create_migration_project(
    migration_project_identifier: str,
    instance_profile_arn: str,
    source_data_provider_descriptors: List[Dict[str, Any]],
    target_data_provider_descriptors: List[Dict[str, Any]],
    transformation_rules: Optional[str] = None,
    description: Optional[str] = None,
    schema_conversion_application_attributes: Optional[Dict[str, Any]] = None,
    tags: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Create a migration project for DMS Serverless.

    Migration projects organize serverless resources for database migrations.

    Args:
        migration_project_identifier: Unique identifier
        instance_profile_arn: Instance profile ARN
        source_data_provider_descriptors: Source data provider configurations
        target_data_provider_descriptors: Target data provider configurations
        transformation_rules: Transformation rules JSON
        description: Project description
        schema_conversion_application_attributes: Schema conversion settings
        tags: Resource tags

    Returns:
        Dictionary containing created migration project details

    Raises:
        DMSResourceInUseException: Identifier already exists
        DMSInvalidParameterException: Invalid configuration
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('create_migration_project called', identifier=migration_project_identifier)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('create_migration_project not available in read-only mode')
        )

    try:
        result = serverless_manager.create_migration_project(
            identifier=migration_project_identifier,
            instance_profile_arn=instance_profile_arn,
            source_data_provider_descriptors=source_data_provider_descriptors,
            target_data_provider_descriptors=target_data_provider_descriptors,
            transformation_rules=transformation_rules,
            description=description,
            schema_conversion_application_attributes=schema_conversion_application_attributes,
            tags=tags,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to create migration project', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in create_migration_project', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def modify_migration_project(
    migration_project_arn: str,
    migration_project_identifier: Optional[str] = None,
    instance_profile_arn: Optional[str] = None,
    source_data_provider_descriptors: Optional[List[Dict[str, Any]]] = None,
    target_data_provider_descriptors: Optional[List[Dict[str, Any]]] = None,
    transformation_rules: Optional[str] = None,
    description: Optional[str] = None,
    schema_conversion_application_attributes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Modify a migration project configuration.

    Args:
        migration_project_arn: Migration project ARN
        migration_project_identifier: New identifier
        instance_profile_arn: New instance profile ARN
        source_data_provider_descriptors: New source data providers
        target_data_provider_descriptors: New target data providers
        transformation_rules: New transformation rules
        description: New description
        schema_conversion_application_attributes: New schema conversion settings

    Returns:
        Dictionary containing modified migration project details

    Raises:
        DMSResourceNotFoundException: Project not found
        DMSInvalidParameterException: Invalid configuration
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('modify_migration_project called', project_arn=migration_project_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('modify_migration_project not available in read-only mode')
        )

    try:
        result = serverless_manager.modify_migration_project(
            arn=migration_project_arn,
            identifier=migration_project_identifier,
            instance_profile_arn=instance_profile_arn,
            source_data_provider_descriptors=source_data_provider_descriptors,
            target_data_provider_descriptors=target_data_provider_descriptors,
            transformation_rules=transformation_rules,
            description=description,
            schema_conversion_application_attributes=schema_conversion_application_attributes,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to modify migration project', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in modify_migration_project', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def delete_migration_project(migration_project_arn: str) -> Dict[str, Any]:
    """Delete a migration project.

    Args:
        migration_project_arn: Migration project ARN

    Returns:
        Dictionary containing deleted project details

    Raises:
        DMSResourceNotFoundException: Project not found
        DMSInvalidParameterException: Project is in use
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('delete_migration_project called', project_arn=migration_project_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('delete_migration_project not available in read-only mode')
        )

    try:
        result = serverless_manager.delete_migration_project(arn=migration_project_arn)
        return result
    except DMSMCPException as e:
        logger.error('Failed to delete migration project', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in delete_migration_project', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_migration_projects(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List migration projects with optional filtering.

    Args:
        filters: Optional filters for project selection
        max_results: Maximum results per page (1-100)
        marker: Pagination token

    Returns:
        Dictionary containing:
        - migration_projects: List of project details
        - count: Number of projects returned
        - next_marker: Next page token (if more results available)
    """
    logger.info('describe_migration_projects called', filters=filters)

    try:
        result = serverless_manager.list_migration_projects(
            filters=filters, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe migration projects', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_migration_projects', error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# DMS SERVERLESS: DATA PROVIDER OPERATIONS
# ============================================================================


@mcp.tool()
def create_data_provider(
    data_provider_identifier: str,
    engine: str,
    settings: Dict[str, Any],
    description: Optional[str] = None,
    tags: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Create a data provider for DMS Serverless.

    Data providers define source/target database connections for serverless migrations.

    Args:
        data_provider_identifier: Unique identifier
        engine: Database engine (mysql, postgres, oracle, etc.)
        settings: Engine-specific connection settings
        description: Provider description
        tags: Resource tags

    Returns:
        Dictionary containing created data provider details

    Raises:
        DMSResourceInUseException: Identifier already exists
        DMSInvalidParameterException: Invalid engine or settings
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('create_data_provider called', identifier=data_provider_identifier)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('create_data_provider not available in read-only mode')
        )

    try:
        result = serverless_manager.create_data_provider(
            identifier=data_provider_identifier,
            engine=engine,
            settings=settings,
            description=description,
            tags=tags,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to create data provider', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in create_data_provider', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def modify_data_provider(
    data_provider_arn: str,
    data_provider_identifier: Optional[str] = None,
    engine: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Modify a data provider configuration.

    Args:
        data_provider_arn: Data provider ARN
        data_provider_identifier: New identifier
        engine: New engine
        settings: New settings
        description: New description

    Returns:
        Dictionary containing modified data provider details

    Raises:
        DMSResourceNotFoundException: Provider not found
        DMSInvalidParameterException: Invalid configuration
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('modify_data_provider called', provider_arn=data_provider_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('modify_data_provider not available in read-only mode')
        )

    try:
        result = serverless_manager.modify_data_provider(
            arn=data_provider_arn,
            identifier=data_provider_identifier,
            engine=engine,
            settings=settings,
            description=description,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to modify data provider', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in modify_data_provider', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def delete_data_provider(data_provider_arn: str) -> Dict[str, Any]:
    """Delete a data provider.

    Args:
        data_provider_arn: Data provider ARN

    Returns:
        Dictionary containing deleted data provider details

    Raises:
        DMSResourceNotFoundException: Provider not found
        DMSInvalidParameterException: Provider is in use
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('delete_data_provider called', provider_arn=data_provider_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('delete_data_provider not available in read-only mode')
        )

    try:
        result = serverless_manager.delete_data_provider(arn=data_provider_arn)
        return result
    except DMSMCPException as e:
        logger.error('Failed to delete data provider', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in delete_data_provider', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_data_providers(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List data providers with optional filtering.

    Args:
        filters: Optional filters for provider selection
        max_results: Maximum results per page (1-100)
        marker: Pagination token

    Returns:
        Dictionary containing:
        - data_providers: List of provider details
        - count: Number of providers returned
        - next_marker: Next page token (if more results available)
    """
    logger.info('describe_data_providers called', filters=filters)

    try:
        result = serverless_manager.list_data_providers(
            filters=filters, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe data providers', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_data_providers', error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# DMS SERVERLESS: INSTANCE PROFILE OPERATIONS
# ============================================================================


@mcp.tool()
def create_instance_profile(
    instance_profile_identifier: str,
    description: Optional[str] = None,
    kms_key_arn: Optional[str] = None,
    publicly_accessible: Optional[bool] = None,
    network_type: Optional[str] = None,
    subnet_group_identifier: Optional[str] = None,
    vpc_security_groups: Optional[List[str]] = None,
    tags: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Create an instance profile for DMS Serverless.

    Instance profiles configure compute and networking for serverless migrations.

    Args:
        instance_profile_identifier: Unique identifier
        description: Profile description
        kms_key_arn: KMS key ARN for encryption
        publicly_accessible: Make resources publicly accessible
        network_type: Network type (IPV4 or DUAL)
        subnet_group_identifier: Subnet group identifier
        vpc_security_groups: VPC security group IDs
        tags: Resource tags

    Returns:
        Dictionary containing created instance profile details

    Raises:
        DMSResourceInUseException: Identifier already exists
        DMSInvalidParameterException: Invalid configuration
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('create_instance_profile called', identifier=instance_profile_identifier)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('create_instance_profile not available in read-only mode')
        )

    try:
        result = serverless_manager.create_instance_profile(
            identifier=instance_profile_identifier,
            description=description,
            kms_key_arn=kms_key_arn,
            publicly_accessible=publicly_accessible,
            network_type=network_type,
            subnet_group_identifier=subnet_group_identifier,
            vpc_security_groups=vpc_security_groups,
            tags=tags,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to create instance profile', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in create_instance_profile', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def modify_instance_profile(
    instance_profile_arn: str,
    instance_profile_identifier: Optional[str] = None,
    description: Optional[str] = None,
    kms_key_arn: Optional[str] = None,
    publicly_accessible: Optional[bool] = None,
    network_type: Optional[str] = None,
    subnet_group_identifier: Optional[str] = None,
    vpc_security_groups: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Modify an instance profile configuration.

    Args:
        instance_profile_arn: Instance profile ARN
        instance_profile_identifier: New identifier
        description: New description
        kms_key_arn: New KMS key ARN
        publicly_accessible: New public accessibility setting
        network_type: New network type
        subnet_group_identifier: New subnet group identifier
        vpc_security_groups: New VPC security groups

    Returns:
        Dictionary containing modified instance profile details

    Raises:
        DMSResourceNotFoundException: Profile not found
        DMSInvalidParameterException: Invalid configuration
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('modify_instance_profile called', profile_arn=instance_profile_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('modify_instance_profile not available in read-only mode')
        )

    try:
        result = serverless_manager.modify_instance_profile(
            arn=instance_profile_arn,
            identifier=instance_profile_identifier,
            description=description,
            kms_key_arn=kms_key_arn,
            publicly_accessible=publicly_accessible,
            network_type=network_type,
            subnet_group_identifier=subnet_group_identifier,
            vpc_security_groups=vpc_security_groups,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to modify instance profile', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in modify_instance_profile', error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# DMS SERVERLESS: METADATA MODEL OPERATIONS
# ============================================================================


@mcp.tool()
def describe_conversion_configuration(migration_project_arn: str) -> Dict[str, Any]:
    """Get conversion configuration for a migration project."""
    try:
        return metadata_model_manager.describe_conversion_configuration(arn=migration_project_arn)
    except Exception as e:
        logger.error('Failed to describe conversion configuration', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def modify_conversion_configuration(
    migration_project_arn: str, conversion_configuration: Dict[str, Any]
) -> Dict[str, Any]:
    """Modify conversion configuration."""
    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('modify_conversion_configuration not available in read-only mode')
        )
    try:
        return metadata_model_manager.modify_conversion_configuration(
            arn=migration_project_arn, configuration=conversion_configuration
        )
    except Exception as e:
        logger.error('Failed to modify conversion configuration', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_extension_pack_associations(
    migration_project_arn: str,
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List extension pack associations."""
    try:
        return metadata_model_manager.describe_extension_pack_associations(
            arn=migration_project_arn, filters=filters, max_results=max_results, marker=marker
        )
    except Exception as e:
        logger.error('Failed to describe extension pack associations', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def start_extension_pack_association(migration_project_arn: str) -> Dict[str, Any]:
    """Start extension pack association."""
    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('start_extension_pack_association not available in read-only mode')
        )
    try:
        return metadata_model_manager.start_extension_pack_association(arn=migration_project_arn)
    except Exception as e:
        logger.error('Failed to start extension pack association', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_metadata_model_assessments(
    migration_project_arn: str,
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List metadata model assessments."""
    try:
        return metadata_model_manager.describe_metadata_model_assessments(
            arn=migration_project_arn, filters=filters, max_results=max_results, marker=marker
        )
    except Exception as e:
        logger.error('Failed to describe metadata model assessments', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def start_metadata_model_assessment(
    migration_project_arn: str, selection_rules: str
) -> Dict[str, Any]:
    """Start metadata model assessment."""
    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('start_metadata_model_assessment not available in read-only mode')
        )
    try:
        return metadata_model_manager.start_metadata_model_assessment(
            arn=migration_project_arn, selection_rules=selection_rules
        )
    except Exception as e:
        logger.error('Failed to start metadata model assessment', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_metadata_model_conversions(
    migration_project_arn: str,
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List metadata model conversions."""
    try:
        return metadata_model_manager.describe_metadata_model_conversions(
            arn=migration_project_arn, filters=filters, max_results=max_results, marker=marker
        )
    except Exception as e:
        logger.error('Failed to describe metadata model conversions', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def start_metadata_model_conversion(
    migration_project_arn: str, selection_rules: str
) -> Dict[str, Any]:
    """Start metadata model conversion."""
    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('start_metadata_model_conversion not available in read-only mode')
        )
    try:
        return metadata_model_manager.start_metadata_model_conversion(
            arn=migration_project_arn, selection_rules=selection_rules
        )
    except Exception as e:
        logger.error('Failed to start metadata model conversion', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_metadata_model_exports_as_script(
    migration_project_arn: str,
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List metadata model script exports."""
    try:
        return metadata_model_manager.describe_metadata_model_exports_as_script(
            arn=migration_project_arn, filters=filters, max_results=max_results, marker=marker
        )
    except Exception as e:
        logger.error('Failed to describe metadata model exports as script', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def start_metadata_model_export_as_script(
    migration_project_arn: str, selection_rules: str, origin: str, file_name: Optional[str] = None
) -> Dict[str, Any]:
    """Start metadata model export as script."""
    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException(
                'start_metadata_model_export_as_script not available in read-only mode'
            )
        )
    try:
        return metadata_model_manager.start_metadata_model_export_as_script(
            arn=migration_project_arn,
            selection_rules=selection_rules,
            origin=origin,
            file_name=file_name,
        )
    except Exception as e:
        logger.error('Failed to start metadata model export as script', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_metadata_model_exports_to_target(
    migration_project_arn: str,
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List metadata model target exports."""
    try:
        return metadata_model_manager.describe_metadata_model_exports_to_target(
            arn=migration_project_arn, filters=filters, max_results=max_results, marker=marker
        )
    except Exception as e:
        logger.error('Failed to describe metadata model exports to target', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def start_metadata_model_export_to_target(
    migration_project_arn: str,
    selection_rules: str,
    overwrite_extension_pack: Optional[bool] = None,
) -> Dict[str, Any]:
    """Start metadata model export to target."""
    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException(
                'start_metadata_model_export_to_target not available in read-only mode'
            )
        )
    try:
        return metadata_model_manager.start_metadata_model_export_to_target(
            arn=migration_project_arn,
            selection_rules=selection_rules,
            overwrite_extension_pack=overwrite_extension_pack,
        )
    except Exception as e:
        logger.error('Failed to start metadata model export to target', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_metadata_model_imports(
    migration_project_arn: str,
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List metadata model imports."""
    try:
        return metadata_model_manager.describe_metadata_model_imports(
            arn=migration_project_arn, filters=filters, max_results=max_results, marker=marker
        )
    except Exception as e:
        logger.error('Failed to describe metadata model imports', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def start_metadata_model_import(
    migration_project_arn: str, selection_rules: str, origin: str
) -> Dict[str, Any]:
    """Start metadata model import."""
    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('start_metadata_model_import not available in read-only mode')
        )
    try:
        return metadata_model_manager.start_metadata_model_import(
            arn=migration_project_arn, selection_rules=selection_rules, origin=origin
        )
    except Exception as e:
        logger.error('Failed to start metadata model import', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def export_metadata_model_assessment(
    migration_project_arn: str,
    selection_rules: str,
    file_name: Optional[str] = None,
    assessment_report_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Export metadata model assessment."""
    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('export_metadata_model_assessment not available in read-only mode')
        )
    try:
        return metadata_model_manager.export_metadata_model_assessment(
            arn=migration_project_arn,
            selection_rules=selection_rules,
            file_name=file_name,
            assessment_report_types=assessment_report_types,
        )
    except Exception as e:
        logger.error('Failed to export metadata model assessment', error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# FLEET ADVISOR OPERATIONS
# ============================================================================


@mcp.tool()
def create_fleet_advisor_collector(
    collector_name: str, description: str, service_access_role_arn: str, s3_bucket_name: str
) -> Dict[str, Any]:
    """Create Fleet Advisor collector for database discovery."""
    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('create_fleet_advisor_collector not available in read-only mode')
        )
    try:
        return fleet_advisor_manager.create_collector(
            name=collector_name,
            description=description,
            service_access_role_arn=service_access_role_arn,
            s3_bucket_name=s3_bucket_name,
        )
    except Exception as e:
        logger.error('Failed to create Fleet Advisor collector', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def delete_fleet_advisor_collector(collector_referenced_id: str) -> Dict[str, Any]:
    """Delete Fleet Advisor collector."""
    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('delete_fleet_advisor_collector not available in read-only mode')
        )
    try:
        return fleet_advisor_manager.delete_collector(ref=collector_referenced_id)
    except Exception as e:
        logger.error('Failed to delete Fleet Advisor collector', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_fleet_advisor_collectors(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List Fleet Advisor collectors."""
    try:
        return fleet_advisor_manager.list_collectors(
            filters=filters, max_results=max_results, marker=marker
        )
    except Exception as e:
        logger.error('Failed to describe Fleet Advisor collectors', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def delete_fleet_advisor_databases(database_ids: List[str]) -> Dict[str, Any]:
    """Delete Fleet Advisor databases."""
    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('delete_fleet_advisor_databases not available in read-only mode')
        )
    try:
        return fleet_advisor_manager.delete_databases(database_ids=database_ids)
    except Exception as e:
        logger.error('Failed to delete Fleet Advisor databases', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_fleet_advisor_databases(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List Fleet Advisor databases."""
    try:
        return fleet_advisor_manager.list_databases(
            filters=filters, max_results=max_results, marker=marker
        )
    except Exception as e:
        logger.error('Failed to describe Fleet Advisor databases', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_fleet_advisor_lsa_analysis(
    max_results: int = 100, marker: Optional[str] = None
) -> Dict[str, Any]:
    """Describe Fleet Advisor LSA analysis."""
    try:
        return fleet_advisor_manager.describe_lsa_analysis(max_results=max_results, marker=marker)
    except Exception as e:
        logger.error('Failed to describe Fleet Advisor LSA analysis', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def run_fleet_advisor_lsa_analysis() -> Dict[str, Any]:
    """Run Fleet Advisor LSA analysis."""
    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('run_fleet_advisor_lsa_analysis not available in read-only mode')
        )
    try:
        return fleet_advisor_manager.run_lsa_analysis()
    except Exception as e:
        logger.error('Failed to run Fleet Advisor LSA analysis', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_fleet_advisor_schema_object_summary(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """Describe Fleet Advisor schema object summary."""
    try:
        return fleet_advisor_manager.describe_schema_object_summary(
            filters=filters, max_results=max_results, marker=marker
        )
    except Exception as e:
        logger.error('Failed to describe Fleet Advisor schema object summary', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_fleet_advisor_schemas(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List Fleet Advisor schemas."""
    try:
        return fleet_advisor_manager.list_schemas(
            filters=filters, max_results=max_results, marker=marker
        )
    except Exception as e:
        logger.error('Failed to describe Fleet Advisor schemas', error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# RECOMMENDATION OPERATIONS
# ============================================================================


@mcp.tool()
def describe_recommendations(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List migration recommendations."""
    try:
        return recommendation_manager.list_recommendations(
            filters=filters, max_results=max_results, marker=marker
        )
    except Exception as e:
        logger.error('Failed to describe recommendations', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_recommendation_limitations(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List recommendation limitations."""
    try:
        return recommendation_manager.list_recommendation_limitations(
            filters=filters, max_results=max_results, marker=marker
        )
    except Exception as e:
        logger.error('Failed to describe recommendation limitations', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def start_recommendations(database_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Start generating recommendations for a database."""
    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('start_recommendations not available in read-only mode')
        )
    try:
        return recommendation_manager.start_recommendations(
            database_id=database_id, settings=settings
        )
    except Exception as e:
        logger.error('Failed to start recommendations', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def batch_start_recommendations(data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Batch start recommendations for multiple databases."""
    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('batch_start_recommendations not available in read-only mode')
        )
    try:
        return recommendation_manager.batch_start_recommendations(data=data)
    except Exception as e:
        logger.error('Failed to batch start recommendations', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def delete_instance_profile(instance_profile_arn: str) -> Dict[str, Any]:
    """Delete an instance profile.

    Args:
        instance_profile_arn: Instance profile ARN

    Returns:
        Dictionary containing deleted instance profile details

    Raises:
        DMSResourceNotFoundException: Profile not found
        DMSInvalidParameterException: Profile is in use
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('delete_instance_profile called', profile_arn=instance_profile_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('delete_instance_profile not available in read-only mode')
        )

    try:
        result = serverless_manager.delete_instance_profile(arn=instance_profile_arn)
        return result
    except DMSMCPException as e:
        logger.error('Failed to delete instance profile', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in delete_instance_profile', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_instance_profiles(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List instance profiles with optional filtering.

    Args:
        filters: Optional filters for profile selection
        max_results: Maximum results per page (1-100)
        marker: Pagination token

    Returns:
        Dictionary containing:
        - instance_profiles: List of profile details
        - count: Number of profiles returned
        - next_marker: Next page token (if more results available)
    """
    logger.info('describe_instance_profiles called', filters=filters)

    try:
        result = serverless_manager.list_instance_profiles(
            filters=filters, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe instance profiles', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_instance_profiles', error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# DMS SERVERLESS: DATA MIGRATION OPERATIONS
# ============================================================================


@mcp.tool()
def create_data_migration(
    data_migration_identifier: str,
    migration_type: str,
    service_access_role_arn: str,
    source_data_settings: List[Dict[str, Any]],
    data_migration_settings: Optional[Dict[str, Any]] = None,
    data_migration_name: Optional[str] = None,
    tags: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Create a data migration for DMS Serverless.

    Data migrations are the serverless equivalent of replication tasks.

    Args:
        data_migration_identifier: Unique identifier
        migration_type: Migration type (full-load, cdc, full-load-and-cdc)
        service_access_role_arn: IAM role ARN for DMS
        source_data_settings: Source data configuration
        data_migration_settings: Migration settings
        data_migration_name: Custom name
        tags: Resource tags

    Returns:
        Dictionary containing created data migration details

    Raises:
        DMSResourceInUseException: Identifier already exists
        DMSInvalidParameterException: Invalid configuration
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('create_data_migration called', identifier=data_migration_identifier)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('create_data_migration not available in read-only mode')
        )

    try:
        result = serverless_manager.create_data_migration(
            identifier=data_migration_identifier,
            migration_type=migration_type,
            service_access_role_arn=service_access_role_arn,
            source_data_settings=source_data_settings,
            data_migration_settings=data_migration_settings,
            data_migration_name=data_migration_name,
            tags=tags,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to create data migration', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in create_data_migration', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def modify_data_migration(
    data_migration_arn: str,
    data_migration_identifier: Optional[str] = None,
    migration_type: Optional[str] = None,
    data_migration_name: Optional[str] = None,
    data_migration_settings: Optional[Dict[str, Any]] = None,
    source_data_settings: Optional[List[Dict[str, Any]]] = None,
    number_of_jobs: Optional[int] = None,
) -> Dict[str, Any]:
    """Modify a data migration configuration.

    Args:
        data_migration_arn: Data migration ARN
        data_migration_identifier: New identifier
        migration_type: New migration type
        data_migration_name: New name
        data_migration_settings: New settings
        source_data_settings: New source data settings
        number_of_jobs: New number of parallel jobs

    Returns:
        Dictionary containing modified data migration details

    Raises:
        DMSResourceNotFoundException: Migration not found
        DMSInvalidParameterException: Invalid configuration
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('modify_data_migration called', migration_arn=data_migration_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('modify_data_migration not available in read-only mode')
        )

    try:
        result = serverless_manager.modify_data_migration(
            arn=data_migration_arn,
            identifier=data_migration_identifier,
            migration_type=migration_type,
            data_migration_name=data_migration_name,
            data_migration_settings=data_migration_settings,
            source_data_settings=source_data_settings,
            number_of_jobs=number_of_jobs,
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to modify data migration', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in modify_data_migration', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def delete_data_migration(data_migration_arn: str) -> Dict[str, Any]:
    """Delete a data migration.

    Args:
        data_migration_arn: Data migration ARN

    Returns:
        Dictionary containing deleted data migration details

    Raises:
        DMSResourceNotFoundException: Migration not found
        DMSInvalidParameterException: Migration is running
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('delete_data_migration called', migration_arn=data_migration_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('delete_data_migration not available in read-only mode')
        )

    try:
        result = serverless_manager.delete_data_migration(arn=data_migration_arn)
        return result
    except DMSMCPException as e:
        logger.error('Failed to delete data migration', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in delete_data_migration', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_data_migrations(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
) -> Dict[str, Any]:
    """List data migrations with optional filtering.

    Args:
        filters: Optional filters for migration selection
        max_results: Maximum results per page (1-100)
        marker: Pagination token

    Returns:
        Dictionary containing:
        - data_migrations: List of migration details
        - count: Number of migrations returned
        - next_marker: Next page token (if more results available)
    """
    logger.info('describe_data_migrations called', filters=filters)

    try:
        result = serverless_manager.list_data_migrations(
            filters=filters, max_results=max_results, marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe data migrations', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_data_migrations', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def start_data_migration(data_migration_arn: str, start_type: str) -> Dict[str, Any]:
    """Start a data migration.

    Args:
        data_migration_arn: Data migration ARN
        start_type: Start type (start-replication, resume-processing, reload-target)

    Returns:
        Dictionary containing started data migration details

    Raises:
        DMSResourceNotFoundException: Migration not found
        DMSInvalidParameterException: Invalid start type
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('start_data_migration called', migration_arn=data_migration_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('start_data_migration not available in read-only mode')
        )

    try:
        result = serverless_manager.start_data_migration(
            arn=data_migration_arn, start_type=start_type
        )
        return result
    except DMSMCPException as e:
        logger.error('Failed to start data migration', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in start_data_migration', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def stop_data_migration(data_migration_arn: str) -> Dict[str, Any]:
    """Stop a running data migration.

    Args:
        data_migration_arn: Data migration ARN

    Returns:
        Dictionary containing stopped data migration details

    Raises:
        DMSResourceNotFoundException: Migration not found
        DMSInvalidParameterException: Migration not in stoppable state
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('stop_data_migration called', migration_arn=data_migration_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('stop_data_migration not available in read-only mode')
        )

    try:
        result = serverless_manager.stop_data_migration(arn=data_migration_arn)
        return result
    except DMSMCPException as e:
        logger.error('Failed to stop data migration', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in stop_data_migration', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_account_attributes() -> Dict[str, Any]:
    """Get DMS account attributes and resource quotas.

    Returns information about account limits such as:
    - Maximum replication instances
    - Maximum endpoints
    - Maximum replication tasks
    - Other service quotas

    Returns:
        Dictionary containing:
        - account_quotas: List of account quotas
        - unique_account_identifier: Account identifier
        - count: Number of quotas returned
    """
    logger.info('describe_account_attributes called')

    try:
        result = maintenance_manager.get_account_attributes()
        return result
    except DMSMCPException as e:
        logger.error('Failed to describe account attributes', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in describe_account_attributes', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def add_tags_to_resource(resource_arn: str, tags: List[Dict[str, str]]) -> Dict[str, Any]:
    """Add tags to a DMS resource.

    Tags are key-value pairs used for resource organization, cost tracking,
    and access control.

    Args:
        resource_arn: Resource ARN to tag
        tags: List of tags to add (format: [{"Key": "key", "Value": "value"}])

    Returns:
        Dictionary containing:
        - resource_arn: Tagged resource ARN
        - tags_added: Number of tags added
        - message: Status message

    Raises:
        DMSResourceNotFoundException: Resource not found
        DMSInvalidParameterException: Invalid tag format
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('add_tags_to_resource called', resource_arn=resource_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('add_tags_to_resource not available in read-only mode')
        )

    try:
        result = maintenance_manager.add_tags(resource_arn=resource_arn, tags=tags)
        return result
    except DMSMCPException as e:
        logger.error('Failed to add tags to resource', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in add_tags_to_resource', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def remove_tags_from_resource(resource_arn: str, tag_keys: List[str]) -> Dict[str, Any]:
    """Remove tags from a DMS resource.

    Args:
        resource_arn: Resource ARN
        tag_keys: List of tag keys to remove

    Returns:
        Dictionary containing:
        - resource_arn: Resource ARN
        - tags_removed: Number of tags removed
        - message: Status message

    Raises:
        DMSResourceNotFoundException: Resource not found
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('remove_tags_from_resource called', resource_arn=resource_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('remove_tags_from_resource not available in read-only mode')
        )

    try:
        result = maintenance_manager.remove_tags(resource_arn=resource_arn, tag_keys=tag_keys)
        return result
    except DMSMCPException as e:
        logger.error('Failed to remove tags from resource', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in remove_tags_from_resource', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def list_tags_for_resource(resource_arn: str) -> Dict[str, Any]:
    """List all tags for a DMS resource.

    Args:
        resource_arn: Resource ARN

    Returns:
        Dictionary containing:
        - resource_arn: Resource ARN
        - tags: List of tags
        - count: Number of tags

    Raises:
        DMSResourceNotFoundException: Resource not found
    """
    logger.info('list_tags_for_resource called', resource_arn=resource_arn)

    try:
        result = maintenance_manager.list_tags(resource_arn=resource_arn)
        return result
    except DMSMCPException as e:
        logger.error('Failed to list tags for resource', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in list_tags_for_resource', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def update_subscriptions_to_event_bridge(force_move: bool = False) -> Dict[str, Any]:
    """Update existing DMS event subscriptions to use Amazon EventBridge.

    This migrates SNS-based event subscriptions to EventBridge for better
    integration with AWS event-driven architectures.

    Args:
        force_move: Force move even if some subscriptions fail

    Returns:
        Dictionary containing:
        - result: Migration result message
        - message: Status message

    Raises:
        DMSInvalidParameterException: Invalid configuration
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('update_subscriptions_to_event_bridge called', force_move=force_move)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('update_subscriptions_to_event_bridge not available in read-only mode')
        )

    try:
        result = event_manager.update_subscriptions_to_event_bridge(force_move=force_move)
        return result
    except DMSMCPException as e:
        logger.error('Failed to update subscriptions to EventBridge', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in update_subscriptions_to_event_bridge', error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def delete_certificate(certificate_arn: str) -> Dict[str, Any]:
    """Delete an SSL certificate.

    The certificate must not be in use by any endpoints.

    Args:
        certificate_arn: Certificate ARN to delete

    Returns:
        Dictionary containing:
        - certificate: Deleted certificate details
        - message: Confirmation message

    Raises:
        DMSResourceNotFoundException: Certificate not found
        DMSInvalidParameterException: Certificate is in use
        DMSReadOnlyModeException: Read-only mode enabled
    """
    logger.info('delete_certificate called', certificate_arn=certificate_arn)

    if config.read_only_mode:
        return ResponseFormatter.format_error(
            DMSMCPException('delete_certificate not available in read-only mode')
        )

    try:
        result = certificate_manager.delete_certificate(certificate_arn=certificate_arn)
        return result
    except DMSMCPException as e:
        logger.error('Failed to delete certificate', error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error('Unexpected error in delete_certificate', error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================


def main() -> None:
    """Entry point for CLI execution."""
    try:
        # Initialize server with default configuration
        server = create_server()

        # Run the MCP server
        logger.info('Starting AWS DMS MCP Server')
        server.run()

    except Exception as e:
        logger.error('Failed to start server', error=str(e))
        raise


if __name__ == '__main__':
    main()
