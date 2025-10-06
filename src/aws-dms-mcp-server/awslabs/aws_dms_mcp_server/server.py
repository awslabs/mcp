"""
AWS DMS MCP Server - Main server implementation.

This module defines all MCP tools using FastMCP decorators and coordinates
interactions with AWS DMS through utility modules.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import sys

from fastmcp import FastMCP
from loguru import logger

from .config import DMSServerConfig
from .utils.dms_client import DMSClient
from .utils.replication_instance_manager import ReplicationInstanceManager
from .utils.endpoint_manager import EndpointManager
from .utils.task_manager import TaskManager
from .utils.table_operations import TableOperations
from .utils.connection_tester import ConnectionTester
from .utils.response_formatter import ResponseFormatter
from .exceptions import DMSMCPException

# Initialize server
mcp = FastMCP("aws-dms-mcp-server")

# Global configuration and clients (initialized in create_server)
config: DMSServerConfig
dms_client: DMSClient
instance_manager: ReplicationInstanceManager
endpoint_manager: EndpointManager
task_manager: TaskManager
table_ops: TableOperations
connection_tester: ConnectionTester


def create_server(server_config: Optional[DMSServerConfig] = None) -> FastMCP:
    """
    Create and configure the AWS DMS MCP server.
    
    Args:
        server_config: Optional configuration object. If None, loads from environment.
    
    Returns:
        Configured FastMCP server instance
    """
    global config, dms_client, instance_manager, endpoint_manager
    global task_manager, table_ops, connection_tester
    
    # Initialize configuration
    config = server_config or DMSServerConfig()
    
    # Configure logging
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        level=config.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    if config.enable_structured_logging:
        logger.add(
            sys.stderr,
            level=config.log_level,
            serialize=True
        )
    
    logger.info(
        "Initializing AWS DMS MCP Server",
        version="0.0.1",
        region=config.aws_region,
        read_only_mode=config.read_only_mode
    )
    
    # Initialize DMS client and managers
    dms_client = DMSClient(config)
    instance_manager = ReplicationInstanceManager(dms_client)
    endpoint_manager = EndpointManager(dms_client)
    task_manager = TaskManager(dms_client)
    table_ops = TableOperations(dms_client)
    connection_tester = ConnectionTester(dms_client, config.enable_connection_caching)
    
    logger.info("AWS DMS MCP Server initialized successfully")
    return mcp


# ============================================================================
# REPLICATION INSTANCE TOOLS
# ============================================================================

@mcp.tool()
def describe_replication_instances(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None
) -> Dict[str, Any]:
    """
    List and describe AWS DMS replication instances with optional filtering.
    
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
    logger.info("describe_replication_instances called", filters=filters, max_results=max_results)
    
    try:
        result = instance_manager.list_instances(
            filters=filters,
            max_results=max_results,
            marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error("Failed to describe replication instances", error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error("Unexpected error in describe_replication_instances", error=str(e))
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
    tags: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Create a new AWS DMS replication instance with Multi-AZ support.
    
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
    logger.info("create_replication_instance called", identifier=replication_instance_identifier)
    
    try:
        # Build parameters
        params = {
            "ReplicationInstanceIdentifier": replication_instance_identifier,
            "ReplicationInstanceClass": replication_instance_class,
            "AllocatedStorage": allocated_storage,
            "MultiAZ": multi_az,
            "PubliclyAccessible": publicly_accessible
        }
        
        if engine_version:
            params["EngineVersion"] = engine_version
        if vpc_security_group_ids:
            params["VpcSecurityGroupIds"] = vpc_security_group_ids
        if replication_subnet_group_identifier:
            params["ReplicationSubnetGroupIdentifier"] = replication_subnet_group_identifier
        if tags:
            params["Tags"] = tags
        
        result = instance_manager.create_instance(params)
        return result
    except DMSMCPException as e:
        logger.error("Failed to create replication instance", error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error("Unexpected error in create_replication_instance", error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# ENDPOINT TOOLS
# ============================================================================

@mcp.tool()
def describe_endpoints(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None
) -> Dict[str, Any]:
    """
    List and describe source/target database endpoints.
    
    Args:
        filters: Optional filters (by type, engine, status)
        max_results: Maximum results per page (1-100)
        marker: Pagination token
    
    Returns:
        Dictionary containing:
        - endpoints: List of endpoint details
        - count: Number of endpoints returned
    """
    logger.info("describe_endpoints called", filters=filters)
    
    try:
        result = endpoint_manager.list_endpoints(
            filters=filters,
            max_results=max_results,
            marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error("Failed to describe endpoints", error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error("Unexpected error in describe_endpoints", error=str(e))
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
    ssl_mode: str = "none",
    extra_connection_attributes: Optional[str] = None,
    certificate_arn: Optional[str] = None,
    secrets_manager_secret_id: Optional[str] = None,
    tags: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Create a database endpoint for source or target.
    
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
    logger.info("create_endpoint called", identifier=endpoint_identifier, engine=engine_name)
    
    try:
        # Build parameters
        params = {
            "EndpointIdentifier": endpoint_identifier,
            "EndpointType": endpoint_type,
            "EngineName": engine_name,
            "ServerName": server_name,
            "Port": port,
            "DatabaseName": database_name,
            "Username": username,
            "Password": password,
            "SslMode": ssl_mode
        }
        
        if extra_connection_attributes:
            params["ExtraConnectionAttributes"] = extra_connection_attributes
        if certificate_arn:
            params["CertificateArn"] = certificate_arn
        if secrets_manager_secret_id:
            params["SecretsManagerSecretId"] = secrets_manager_secret_id
        if tags:
            params["Tags"] = tags
        
        result = endpoint_manager.create_endpoint(params)
        return result
    except DMSMCPException as e:
        logger.error("Failed to create endpoint", error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error("Unexpected error in create_endpoint", error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def delete_endpoint(
    endpoint_arn: str
) -> Dict[str, Any]:
    """
    Delete a database endpoint.
    
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
    logger.info("delete_endpoint called", endpoint_arn=endpoint_arn)
    
    try:
        result = endpoint_manager.delete_endpoint(endpoint_arn=endpoint_arn)
        return result
    except DMSMCPException as e:
        logger.error("Failed to delete endpoint", error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error("Unexpected error in delete_endpoint", error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def test_connection(
    replication_instance_arn: str,
    endpoint_arn: str
) -> Dict[str, Any]:
    """
    Test connectivity between a replication instance and an endpoint.
    
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
    logger.info("test_connection called", instance=replication_instance_arn, endpoint=endpoint_arn)
    
    try:
        result = connection_tester.test_connection(
            instance_arn=replication_instance_arn,
            endpoint_arn=endpoint_arn
        )
        return result
    except DMSMCPException as e:
        logger.error("Failed to test connection", error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error("Unexpected error in test_connection", error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def describe_connections(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None
) -> Dict[str, Any]:
    """
    List existing connection test results.
    
    Args:
        filters: Optional filters (by status, endpoint, etc.)
        max_results: Maximum results per page
        marker: Pagination token
    
    Returns:
        Dictionary containing:
        - connections: List of connection test results
        - count: Number of connections returned
    """
    logger.info("describe_connections called", filters=filters)
    
    try:
        result = connection_tester.list_connection_tests(
            filters=filters,
            max_results=max_results,
            marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error("Failed to describe connections", error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error("Unexpected error in describe_connections", error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# REPLICATION TASK TOOLS
# ============================================================================

@mcp.tool()
def describe_replication_tasks(
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None,
    without_settings: bool = False
) -> Dict[str, Any]:
    """
    List and describe replication tasks with detailed status.
    
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
    logger.info("describe_replication_tasks called", filters=filters)
    
    try:
        result = task_manager.list_tasks(
            filters=filters,
            max_results=max_results,
            marker=marker,
            without_settings=without_settings
        )
        return result
    except DMSMCPException as e:
        logger.error("Failed to describe replication tasks", error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error("Unexpected error in describe_replication_tasks", error=str(e))
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
    tags: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Create a replication task with table mappings and CDC configuration.
    
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
    logger.info("create_replication_task called", identifier=replication_task_identifier)
    
    try:
        # Build parameters
        params = {
            "ReplicationTaskIdentifier": replication_task_identifier,
            "SourceEndpointArn": source_endpoint_arn,
            "TargetEndpointArn": target_endpoint_arn,
            "ReplicationInstanceArn": replication_instance_arn,
            "MigrationType": migration_type,
            "TableMappings": table_mappings
        }
        
        if replication_task_settings:
            params["ReplicationTaskSettings"] = replication_task_settings
        if cdc_start_position:
            params["CdcStartPosition"] = cdc_start_position
        if cdc_start_time:
            params["CdcStartTime"] = cdc_start_time
        if tags:
            params["Tags"] = tags
        
        result = task_manager.create_task(params)
        return result
    except DMSMCPException as e:
        logger.error("Failed to create replication task", error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error("Unexpected error in create_replication_task", error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def start_replication_task(
    replication_task_arn: str,
    start_replication_task_type: str,  # "start-replication", "resume-processing", or "reload-target"
    cdc_start_position: Optional[str] = None,
    cdc_start_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Start a replication task with support for new starts, resume, and reload.
    
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
    logger.info("start_replication_task called", task_arn=replication_task_arn)
    
    try:
        result = task_manager.start_task(
            task_arn=replication_task_arn,
            start_type=start_replication_task_type,
            cdc_start_position=cdc_start_position
        )
        return result
    except DMSMCPException as e:
        logger.error("Failed to start replication task", error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error("Unexpected error in start_replication_task", error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def stop_replication_task(
    replication_task_arn: str
) -> Dict[str, Any]:
    """
    Stop a running replication task safely.
    
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
    logger.info("stop_replication_task called", task_arn=replication_task_arn)
    
    try:
        result = task_manager.stop_task(task_arn=replication_task_arn)
        return result
    except DMSMCPException as e:
        logger.error("Failed to stop replication task", error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error("Unexpected error in stop_replication_task", error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# TABLE OPERATIONS TOOLS
# ============================================================================

@mcp.tool()
def describe_table_statistics(
    replication_task_arn: str,
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
    marker: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get detailed table-level replication statistics.
    
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
    logger.info("describe_table_statistics called", task_arn=replication_task_arn)
    
    try:
        result = table_ops.get_table_statistics(
            task_arn=replication_task_arn,
            filters=filters,
            max_results=max_results,
            marker=marker
        )
        return result
    except DMSMCPException as e:
        logger.error("Failed to describe table statistics", error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error("Unexpected error in describe_table_statistics", error=str(e))
        return ResponseFormatter.format_error(e)


@mcp.tool()
def reload_replication_tables(
    replication_task_arn: str,
    tables_to_reload: List[Dict[str, str]],
    reload_option: str = "data-reload"  # "data-reload" or "validate-only"
) -> Dict[str, Any]:
    """
    Reload specific tables during replication.
    
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
    logger.info("reload_replication_tables called", task_arn=replication_task_arn)
    
    try:
        # Convert to uppercase keys for API
        tables = [
            {
                "SchemaName": table.get("schema_name") or table.get("SchemaName"),
                "TableName": table.get("table_name") or table.get("TableName")
            }
            for table in tables_to_reload
        ]
        
        result = table_ops.reload_tables(
            task_arn=replication_task_arn,
            tables=tables,
            reload_option=reload_option
        )
        return result
    except DMSMCPException as e:
        logger.error("Failed to reload replication tables", error=str(e))
        return ResponseFormatter.format_error(e)
    except Exception as e:
        logger.error("Unexpected error in reload_replication_tables", error=str(e))
        return ResponseFormatter.format_error(e)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main() -> None:
    """Entry point for CLI execution."""
    try:
        # Initialize server with default configuration
        server = create_server()
        
        # Run the MCP server
        logger.info("Starting AWS DMS MCP Server")
        server.run()
        
    except Exception as e:
        logger.error("Failed to start server", error=str(e))
        raise


if __name__ == "__main__":
    main()