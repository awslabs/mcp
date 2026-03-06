"""MWAA MCP Server - Model Context Protocol server for Amazon Managed Workflows for Apache Airflow."""

import logging
import os
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from .tools import MWAATools
from .prompts import AIRFLOW_BEST_PRACTICES, DAG_DESIGN_GUIDANCE

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=getattr(logging, os.getenv("FASTMCP_LOG_LEVEL", "ERROR")))

# Initialize the MCP server
mcp = FastMCP(
    name="mwaa-mcp-server",
    instructions="Model Context Protocol server for Amazon Managed Workflows for Apache Airflow (MWAA)",
)

# Initialize tools
tools = MWAATools()


# Environment Management Tools
@mcp.tool(name="list_environments")
async def list_environments(
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    """List all MWAA environments in the current AWS account and region.

    Args:
        max_results: Maximum number of environments to return (1-25)

    Returns:
        Dictionary containing list of environment names and metadata
    """
    max_results_int = int(max_results) if max_results is not None else None
    return await tools.list_environments(max_results_int)


@mcp.tool(name="get_environment")
async def get_environment(
    name: str,
) -> Dict[str, Any]:
    """Get detailed information about a specific MWAA environment.

    Args:
        name: The name of the MWAA environment

    Returns:
        Dictionary containing environment details including configuration,
        status, endpoints, and other metadata
    """
    return await tools.get_environment(name)


@mcp.tool(name="create_environment")
async def create_environment(
    name: str,
    dag_s3_path: str,
    execution_role_arn: str,
    network_configuration: Dict[str, Any],
    source_bucket_arn: str,
    airflow_version: Optional[str] = None,
    environment_class: Optional[str] = None,
    max_workers: Optional[int] = None,
    min_workers: Optional[int] = None,
    schedulers: Optional[int] = None,
    webserver_access_mode: Optional[str] = None,
    weekly_maintenance_window_start: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    airflow_configuration_options: Optional[Dict[str, str]] = None,
    logging_configuration: Optional[Dict[str, Any]] = None,
    requirements_s3_path: Optional[str] = None,
    plugins_s3_path: Optional[str] = None,
    startup_script_s3_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new MWAA environment.

    Args:
        name: Environment name
        dag_s3_path: S3 path to DAGs folder (e.g., s3://bucket/dags)
        execution_role_arn: IAM role ARN for the environment
        network_configuration: VPC configuration with SubnetIds and SecurityGroupIds
        source_bucket_arn: ARN of the S3 bucket containing DAGs
        airflow_version: Apache Airflow version (e.g., "2.7.2")
        environment_class: Environment size (mw1.small, mw1.medium, mw1.large, mw1.xlarge, mw1.2xlarge)
        max_workers: Maximum number of workers (1-25)
        min_workers: Minimum number of workers (1-25)
        schedulers: Number of schedulers (2-5)
        webserver_access_mode: PUBLIC_ONLY or PRIVATE_ONLY
        weekly_maintenance_window_start: Maintenance window start (e.g., "SUN:03:00")
        tags: Resource tags
        airflow_configuration_options: Airflow configuration overrides
        logging_configuration: Logging settings for different components
        requirements_s3_path: S3 path to requirements.txt
        plugins_s3_path: S3 path to plugins.zip
        startup_script_s3_path: S3 path to startup script

    Returns:
        Dictionary containing the ARN of the created environment
    """
    max_workers_int = int(max_workers) if max_workers is not None else None
    min_workers_int = int(min_workers) if min_workers is not None else None
    schedulers_int = int(schedulers) if schedulers is not None else None

    return await tools.create_environment(
        name=name,
        dag_s3_path=dag_s3_path,
        execution_role_arn=execution_role_arn,
        network_configuration=network_configuration,
        source_bucket_arn=source_bucket_arn,
        airflow_version=airflow_version,
        environment_class=environment_class,
        max_workers=max_workers_int,
        min_workers=min_workers_int,
        schedulers=schedulers_int,
        webserver_access_mode=webserver_access_mode,
        weekly_maintenance_window_start=weekly_maintenance_window_start,
        tags=tags,
        airflow_configuration_options=airflow_configuration_options,
        logging_configuration=logging_configuration,
        requirements_s3_path=requirements_s3_path,
        plugins_s3_path=plugins_s3_path,
        startup_script_s3_path=startup_script_s3_path,
    )


@mcp.tool(name="update_environment")
async def update_environment(
    name: str,
    dag_s3_path: Optional[str] = None,
    execution_role_arn: Optional[str] = None,
    network_configuration: Optional[Dict[str, Any]] = None,
    source_bucket_arn: Optional[str] = None,
    airflow_version: Optional[str] = None,
    environment_class: Optional[str] = None,
    max_workers: Optional[int] = None,
    min_workers: Optional[int] = None,
    schedulers: Optional[int] = None,
    webserver_access_mode: Optional[str] = None,
    weekly_maintenance_window_start: Optional[str] = None,
    airflow_configuration_options: Optional[Dict[str, str]] = None,
    logging_configuration: Optional[Dict[str, Any]] = None,
    requirements_s3_path: Optional[str] = None,
    plugins_s3_path: Optional[str] = None,
    startup_script_s3_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an existing MWAA environment configuration.

    Only provide the parameters you want to change.

    Args:
        name: Environment name
        dag_s3_path: S3 path to DAGs folder
        execution_role_arn: IAM role ARN
        network_configuration: VPC configuration
        source_bucket_arn: S3 bucket ARN
        airflow_version: Apache Airflow version
        environment_class: Environment size
        max_workers: Maximum workers
        min_workers: Minimum workers
        schedulers: Number of schedulers
        webserver_access_mode: Access mode
        weekly_maintenance_window_start: Maintenance window
        airflow_configuration_options: Configuration overrides
        logging_configuration: Logging settings
        requirements_s3_path: Path to requirements.txt
        plugins_s3_path: Path to plugins.zip
        startup_script_s3_path: Path to startup script

    Returns:
        Dictionary containing the environment ARN
    """
    max_workers_int = int(max_workers) if max_workers is not None else None
    min_workers_int = int(min_workers) if min_workers is not None else None
    schedulers_int = int(schedulers) if schedulers is not None else None

    return await tools.update_environment(
        name=name,
        dag_s3_path=dag_s3_path,
        execution_role_arn=execution_role_arn,
        network_configuration=network_configuration,
        source_bucket_arn=source_bucket_arn,
        airflow_version=airflow_version,
        environment_class=environment_class,
        max_workers=max_workers_int,
        min_workers=min_workers_int,
        schedulers=schedulers_int,
        webserver_access_mode=webserver_access_mode,
        weekly_maintenance_window_start=weekly_maintenance_window_start,
        airflow_configuration_options=airflow_configuration_options,
        logging_configuration=logging_configuration,
        requirements_s3_path=requirements_s3_path,
        plugins_s3_path=plugins_s3_path,
        startup_script_s3_path=startup_script_s3_path,
    )


@mcp.tool(name="delete_environment")
async def delete_environment(
    name: str,
) -> Dict[str, Any]:
    """Delete an MWAA environment.

    Args:
        name: The name of the environment to delete

    Returns:
        Dictionary with deletion confirmation
    """
    return await tools.delete_environment(name)


@mcp.tool(name="create_cli_token")
async def create_cli_token(
    name: str,
) -> Dict[str, Any]:
    """Create a CLI token for executing Airflow CLI commands.

    Args:
        name: The name of the MWAA environment

    Returns:
        Dictionary containing the CLI token and webserver hostname
    """
    return await tools.create_cli_token(name)


@mcp.tool(name="create_web_login_token")
async def create_web_login_token(
    name: str,
) -> Dict[str, Any]:
    """Create a web login token for accessing the Airflow UI.

    Args:
        name: The name of the MWAA environment

    Returns:
        Dictionary containing the web token, webserver hostname, and IAM identity
    """
    return await tools.create_web_login_token(name)


# Airflow API Tools
@mcp.tool(name="list_dags")
async def list_dags(
    environment_name: str,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    tags: Optional[List[str]] = None,
    dag_id_pattern: Optional[str] = None,
    only_active: Optional[bool] = True,
) -> Dict[str, Any]:
    """List all DAGs in an MWAA environment.

    Args:
        environment_name: Name of the MWAA environment
        limit: Number of items to return (max 100)
        offset: Number of items to skip
        tags: Filter by DAG tags
        dag_id_pattern: Filter by DAG ID pattern (supports % wildcards)
        only_active: Only return active DAGs

    Returns:
        Dictionary containing list of DAGs with their details
    """
    limit_int = int(limit) if limit is not None else 100
    offset_int = int(offset) if offset is not None else 0

    return await tools.list_dags(
        environment_name, limit_int, offset_int, tags, dag_id_pattern, only_active
    )


@mcp.tool(name="get_dag")
async def get_dag(
    environment_name: str,
    dag_id: str,
) -> Dict[str, Any]:
    """Get details about a specific DAG.

    Args:
        environment_name: Name of the MWAA environment
        dag_id: The DAG ID

    Returns:
        Dictionary containing DAG details including schedule, tags, and state
    """
    return await tools.get_dag(environment_name, dag_id)


@mcp.tool(name="get_dag_source")
async def get_dag_source(
    environment_name: str,
    dag_id: str,
) -> Dict[str, Any]:
    """Get the source code of a DAG.

    Args:
        environment_name: Name of the MWAA environment
        dag_id: The DAG ID

    Returns:
        Dictionary containing the DAG source code
    """
    return await tools.get_dag_source(environment_name, dag_id)


@mcp.tool(name="trigger_dag_run")
async def trigger_dag_run(
    environment_name: str,
    dag_id: str,
    dag_run_id: Optional[str] = None,
    conf: Optional[Dict[str, Any]] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Trigger a new DAG run.

    Args:
        environment_name: Name of the MWAA environment
        dag_id: The DAG ID to trigger
        dag_run_id: Custom run ID (optional, will be auto-generated if not provided)
        conf: Configuration JSON for the DAG run
        note: Optional note for the DAG run

    Returns:
        Dictionary containing the created DAG run details
    """
    return await tools.trigger_dag_run(environment_name, dag_id, dag_run_id, conf, note)


@mcp.tool(name="get_dag_run")
async def get_dag_run(
    environment_name: str,
    dag_id: str,
    dag_run_id: str,
) -> Dict[str, Any]:
    """Get details about a specific DAG run.

    Args:
        environment_name: Name of the MWAA environment
        dag_id: The DAG ID
        dag_run_id: The DAG run ID

    Returns:
        Dictionary containing DAG run details including state and timing
    """
    return await tools.get_dag_run(environment_name, dag_id, dag_run_id)


@mcp.tool(name="list_dag_runs")
async def list_dag_runs(
    environment_name: str,
    dag_id: str,
    limit: Optional[int] = 100,
    state: Optional[List[str]] = None,
    execution_date_gte: Optional[str] = None,
    execution_date_lte: Optional[str] = None,
) -> Dict[str, Any]:
    """List DAG runs for a specific DAG.

    Args:
        environment_name: Name of the MWAA environment
        dag_id: The DAG ID
        limit: Number of items to return
        state: Filter by state (queued, running, success, failed)
        execution_date_gte: Filter by execution date >= (ISO format)
        execution_date_lte: Filter by execution date <= (ISO format)

    Returns:
        Dictionary containing list of DAG runs
    """
    limit_int = int(limit) if limit is not None else 100

    return await tools.list_dag_runs(
        environment_name,
        dag_id,
        limit_int,
        state,
        execution_date_gte,
        execution_date_lte,
    )


@mcp.tool(name="get_task_instance")
async def get_task_instance(
    environment_name: str,
    dag_id: str,
    dag_run_id: str,
    task_id: str,
) -> Dict[str, Any]:
    """Get details about a specific task instance.

    Args:
        environment_name: Name of the MWAA environment
        dag_id: The DAG ID
        dag_run_id: The DAG run ID
        task_id: The task ID

    Returns:
        Dictionary containing task instance details
    """
    return await tools.get_task_instance(environment_name, dag_id, dag_run_id, task_id)


@mcp.tool(name="get_task_logs")
async def get_task_logs(
    environment_name: str,
    dag_id: str,
    dag_run_id: str,
    task_id: str,
    task_try_number: Optional[int] = None,
) -> Dict[str, Any]:
    """Get logs for a specific task instance.

    Args:
        environment_name: Name of the MWAA environment
        dag_id: The DAG ID
        dag_run_id: The DAG run ID
        task_id: The task ID
        task_try_number: Specific try number (optional)

    Returns:
        Dictionary containing task logs
    """
    task_try_number_int = int(task_try_number) if task_try_number is not None else None

    return await tools.get_task_logs(
        environment_name, dag_id, dag_run_id, task_id, task_try_number_int
    )


@mcp.tool(name="list_connections")
async def list_connections(
    environment_name: str,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
) -> Dict[str, Any]:
    """List all Airflow connections in the environment.

    Args:
        environment_name: Name of the MWAA environment
        limit: Number of items to return
        offset: Number of items to skip

    Returns:
        Dictionary containing list of connections
    """
    limit_int = int(limit) if limit is not None else 100
    offset_int = int(offset) if offset is not None else 0

    return await tools.list_connections(environment_name, limit_int, offset_int)


@mcp.tool(name="list_variables")
async def list_variables(
    environment_name: str,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
) -> Dict[str, Any]:
    """List all Airflow variables in the environment.

    Args:
        environment_name: Name of the MWAA environment
        limit: Number of items to return
        offset: Number of items to skip

    Returns:
        Dictionary containing list of variables
    """
    limit_int = int(limit) if limit is not None else 100
    offset_int = int(offset) if offset is not None else 0

    return await tools.list_variables(environment_name, limit_int, offset_int)


@mcp.tool(name="get_import_errors")
async def get_import_errors(
    environment_name: str,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
) -> Dict[str, Any]:
    """Get DAG import errors in the environment.

    Args:
        environment_name: Name of the MWAA environment
        limit: Number of items to return
        offset: Number of items to skip

    Returns:
        Dictionary containing list of import errors
    """
    limit_int = int(limit) if limit is not None else 100
    offset_int = int(offset) if offset is not None else 0

    return await tools.get_import_errors(environment_name, limit_int, offset_int)


# Expert Guidance Tools
@mcp.tool(name="airflow_best_practices")
async def airflow_best_practices() -> str:
    """Get MWAA and Apache Airflow best practices guidance.

    Returns comprehensive guidance on:
    - DAG design patterns
    - Performance optimization
    - Resource management
    - Error handling
    - Security best practices
    - MWAA-specific considerations
    """
    return AIRFLOW_BEST_PRACTICES


@mcp.tool(name="dag_design_guidance")
async def dag_design_guidance() -> str:
    """Get detailed guidance on designing efficient Airflow DAGs.

    Returns expert guidance on:
    - Task dependencies and parallelism
    - Dynamic DAG generation
    - Sensor patterns
    - XCom usage
    - Testing strategies
    - Common pitfalls to avoid
    """
    return DAG_DESIGN_GUIDANCE
