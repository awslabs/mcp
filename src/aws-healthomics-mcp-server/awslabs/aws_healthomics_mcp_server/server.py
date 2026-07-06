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

"""awslabs aws-healthomics MCP Server implementation."""

import anyio
import sys
from awslabs.aws_healthomics_mcp_server import consts
from awslabs.aws_healthomics_mcp_server.config import (
    ServerConfig,
    TransportConfigError,
    parse_config,
)
from awslabs.aws_healthomics_mcp_server.mechanisms.explicit import InboundExplicitCredentials
from awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange import InboundJwtExchange
from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import (
    RegistryRoleResolver,
    RoleResolver,
    StaticRoleResolver,
)
from awslabs.aws_healthomics_mcp_server.mechanisms.sigv4 import InboundSigV4
from awslabs.aws_healthomics_mcp_server.middleware import (
    ASGIApp,
    IdentityMiddleware,
    InboundMechanism,
)
from awslabs.aws_healthomics_mcp_server.tools.codeconnections import (
    create_codeconnection,
    get_codeconnection,
    list_codeconnections,
)
from awslabs.aws_healthomics_mcp_server.tools.configuration_tools import (
    create_configuration,
    delete_configuration,
    get_configuration,
    list_configurations,
)
from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
    check_container_availability,
    clone_container_to_ecr,
    create_container_registry_map,
    create_pull_through_cache_for_healthomics,
    grant_healthomics_repository_access,
    list_ecr_repositories,
    list_pull_through_cache_rules,
    validate_healthomics_ecr_config,
)
from awslabs.aws_healthomics_mcp_server.tools.genomics_file_search import (
    get_supported_file_types,
    search_genomics_files,
)
from awslabs.aws_healthomics_mcp_server.tools.helper_tools import (
    get_supported_regions,
    package_workflow,
)
from awslabs.aws_healthomics_mcp_server.tools.reference_store_tools import (
    get_reference_import_job,
    get_reference_metadata,
    get_reference_store,
    list_reference_import_jobs,
    list_reference_stores,
    list_references,
    start_reference_import_job,
)
from awslabs.aws_healthomics_mcp_server.tools.run_analysis import analyze_run_performance
from awslabs.aws_healthomics_mcp_server.tools.run_batch import (
    cancel_run_batch,
    delete_batch,
    delete_run_batch,
    get_batch,
    list_batches,
    list_runs_in_batch,
    start_run_batch,
)
from awslabs.aws_healthomics_mcp_server.tools.run_cache import (
    create_run_cache,
    get_run_cache,
    list_run_caches,
    update_run_cache,
)
from awslabs.aws_healthomics_mcp_server.tools.run_group import (
    create_run_group,
    get_run_group,
    list_run_groups,
    update_run_group,
)
from awslabs.aws_healthomics_mcp_server.tools.run_timeline import generate_run_timeline
from awslabs.aws_healthomics_mcp_server.tools.sequence_store_tools import (
    activate_read_sets,
    create_sequence_store,
    get_read_set_export_job,
    get_read_set_import_job,
    get_read_set_metadata,
    get_sequence_store,
    list_read_set_export_jobs,
    list_read_set_import_jobs,
    list_read_sets,
    list_sequence_stores,
    start_read_set_export_job,
    start_read_set_import_job,
    update_sequence_store,
)
from awslabs.aws_healthomics_mcp_server.tools.troubleshooting import diagnose_run_failure
from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import (
    get_run_engine_logs,
    get_run_logs,
    get_run_manifest_logs,
    get_task_logs,
)
from awslabs.aws_healthomics_mcp_server.tools.workflow_execution import (
    get_run,
    get_run_task,
    list_run_tasks,
    list_runs,
    start_run,
)
from awslabs.aws_healthomics_mcp_server.tools.workflow_linting import (
    lint_workflow_bundle,
    lint_workflow_definition,
)
from awslabs.aws_healthomics_mcp_server.tools.workflow_management import (
    create_workflow,
    create_workflow_version,
    get_workflow,
    list_workflow_versions,
    list_workflows,
)
from awslabs.aws_healthomics_mcp_server.transport import TransportSelector
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    RequestScopedCredentialResolver,
    set_active_resolver,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP
from typing import cast


mcp = FastMCP(
    'awslabs.aws-healthomics-mcp-server',
    instructions="""
# AWS HealthOmics MCP Server

This MCP server provides tools for creating, managing, and analyzing genomic workflows using AWS HealthOmics. It enables AI assistants to help users with workflow creation, execution, monitoring, and troubleshooting.

## Available Tools

### Workflow Management
- **ListAHOWorkflows**: List available HealthOmics workflows
- **CreateAHOWorkflow**: Create a new HealthOmics workflow
- **GetAHOWorkflow**: Get details about a specific workflow
- **CreateAHOWorkflowVersion**: Create a new version of an existing workflow
- **ListAHOWorkflowVersions**: List versions of a workflow

### Workflow Execution
- **StartAHORun**: Start a workflow run
- **ListAHORuns**: List workflow runs
- **GetAHORun**: Get details about a specific run
- **ListAHORunTasks**: List tasks for a specific run
- **GetAHORunTask**: Get details about a specific task

### Run Group Management
- **CreateAHORunGroup**: Create a new run group to limit compute resources for workflow runs
- **GetAHORunGroup**: Get details of a specific run group including resource limits and tags
- **ListAHORunGroups**: List available run groups with optional name filtering
- **UpdateAHORunGroup**: Update an existing run group's name or resource limits

### Run Cache Management
- **CreateAHORunCache**: Create a new run cache to store intermediate workflow outputs and accelerate subsequent runs
- **GetAHORunCache**: Get details of a specific run cache including configuration and status
- **ListAHORunCaches**: List available run caches with optional filtering by name, status, or cache behavior
- **UpdateAHORunCache**: Update an existing run cache's behavior, name, or description

### Run Batch Management
- **StartAHORunBatch**: Submit multiple workflow runs in a single request (up to 100,000 runs)
- **GetAHOBatch**: Get detailed information about a specific batch including status, run summaries, and failure reasons
- **ListAHOBatches**: List batches with optional filtering by status, name, or run group
- **ListAHORunsInBatch**: List individual runs within a batch with optional filtering by submission status
- **CancelAHORunBatch**: Cancel all runs in a batch (only for batches in PENDING, SUBMITTING, or INPROGRESS state)
- **DeleteAHORunBatch**: Delete all runs in a batch (only for batches in PROCESSED or CANCELLED state)
- **DeleteAHOBatch**: Delete batch metadata (only for batches in terminal state: PROCESSED, FAILED, CANCELLED, or RUNS_DELETED)

### Workflow Analysis
- **GetAHORunLogs**: Retrieve high-level run logs showing workflow execution events
- **GetAHORunManifestLogs**: Retrieve run manifest logs with workflow summary
- **GetAHORunEngineLogs**: Retrieve engine logs containing STDOUT and STDERR
- **GetAHOTaskLogs**: Retrieve logs for specific workflow tasks
- **AnalyzeAHORunPerformance**: Analyze workflow run performance and resource utilization to provide optimization recommendations
- **GenerateAHORunTimeline**: Generate a Gantt-style SVG timeline visualization showing task execution phases and parallelism

### Troubleshooting
- **DiagnoseAHORunFailure**: Diagnose a failed workflow run

### Workflow Linting
- **LintAHOWorkflowDefinition**: Lint single WDL or CWL workflow files using miniwdl and cwltool
- **LintAHOWorkflowBundle**: Lint multi-file WDL or CWL workflow bundles with import/dependency support

### Genomics File Search
- **SearchGenomicsFiles**: Search for genomics files across S3 buckets, HealthOmics sequence stores, and reference stores with intelligent pattern matching and file association detection
- **GetSupportedFileTypes**: Get information about supported genomics file types and their descriptions

### ECR Container Tools
- **ListECRRepositories**: List ECR repositories with HealthOmics accessibility status
- **CheckContainerAvailability**: Check if a container image is available in ECR and accessible by HealthOmics
- **CloneContainerToECR**: Clone a container image from an upstream registry to ECR with HealthOmics permissions
- **GrantHealthOmicsRepositoryAccess**: Grant HealthOmics access to an ECR repository by updating its policy
- **ListPullThroughCacheRules**: List pull-through cache rules with HealthOmics usability status
- **CreatePullThroughCacheForHealthOmics**: Create a pull-through cache rule configured for HealthOmics
- **CreateContainerRegistryMap**: Create a container registry map for HealthOmics workflows using discovered pull-through caches
- **ValidateHealthOmicsECRConfig**: Validate ECR configuration for HealthOmics workflows

### Helper Tools
- **PackageAHOWorkflow**: Package workflow definition files into a base64-encoded ZIP
- **GetAHOSupportedRegions**: Get the list of AWS regions where HealthOmics is available

### CodeConnections Management
- **ListCodeConnections**: List available CodeConnections for use with HealthOmics workflows
- **CreateCodeConnection**: Create a new CodeConnection to a Git provider
- **GetCodeConnection**: Get details about a specific CodeConnection

### Sequence Store Management
- **CreateAHOSequenceStore**: Create a new HealthOmics sequence store
- **ListAHOSequenceStores**: List available sequence stores
- **GetAHOSequenceStore**: Get details about a specific sequence store
- **UpdateAHOSequenceStore**: Update a sequence store's configuration
- **ListAHOReadSets**: List read sets in a sequence store with filtering
- **GetAHOReadSetMetadata**: Get metadata for a specific read set
- **StartAHOReadSetImportJob**: Import genomic files from S3 into a sequence store
- **GetAHOReadSetImportJob**: Get status of a read set import job
- **ListAHOReadSetImportJobs**: List import jobs for a sequence store
- **StartAHOReadSetExportJob**: Export read sets from a sequence store to S3
- **GetAHOReadSetExportJob**: Get status of a read set export job
- **ListAHOReadSetExportJobs**: List export jobs for a sequence store
- **ActivateAHOReadSets**: Activate archived read sets

### Reference Store Management
- **ListAHOReferenceStores**: List available reference stores
- **GetAHOReferenceStore**: Get details about a specific reference store
- **ListAHOReferences**: List references in a reference store with filtering
- **GetAHOReferenceMetadata**: Get metadata for a specific reference
- **StartAHOReferenceImportJob**: Import reference files from S3 into a reference store
- **GetAHOReferenceImportJob**: Get status of a reference import job
- **ListAHOReferenceImportJobs**: List import jobs for a reference store

### Configuration Management
- **CreateAHOConfiguration**: Create a new HealthOmics configuration for workflow runs
- **GetAHOConfiguration**: Get details about a specific configuration
- **ListAHOConfigurations**: List available configurations
- **DeleteAHOConfiguration**: Delete a configuration

## Service Availability
AWS HealthOmics is available in select AWS regions. Use the GetAHOSupportedRegions tool to get the current list of supported regions.
""",
    dependencies=[
        'boto3',
        'pydantic',
        'loguru',
        'miniwdl',
        'cwltool',
    ],
)

# Register workflow management tools
mcp.tool(name='ListAHOWorkflows')(list_workflows)
mcp.tool(name='CreateAHOWorkflow')(create_workflow)
mcp.tool(name='GetAHOWorkflow')(get_workflow)
mcp.tool(name='CreateAHOWorkflowVersion')(create_workflow_version)
mcp.tool(name='ListAHOWorkflowVersions')(list_workflow_versions)

# Register workflow execution tools
mcp.tool(name='StartAHORun')(start_run)
mcp.tool(name='ListAHORuns')(list_runs)
mcp.tool(name='GetAHORun')(get_run)
mcp.tool(name='ListAHORunTasks')(list_run_tasks)
mcp.tool(name='GetAHORunTask')(get_run_task)

# Register run group tools
mcp.tool(name='CreateAHORunGroup')(create_run_group)
mcp.tool(name='GetAHORunGroup')(get_run_group)
mcp.tool(name='ListAHORunGroups')(list_run_groups)
mcp.tool(name='UpdateAHORunGroup')(update_run_group)

# Register run cache tools
mcp.tool(name='CreateAHORunCache')(create_run_cache)
mcp.tool(name='GetAHORunCache')(get_run_cache)
mcp.tool(name='ListAHORunCaches')(list_run_caches)
mcp.tool(name='UpdateAHORunCache')(update_run_cache)

# Register run batch tools
mcp.tool(name='StartAHORunBatch')(start_run_batch)
mcp.tool(name='GetAHOBatch')(get_batch)
mcp.tool(name='ListAHOBatches')(list_batches)
mcp.tool(name='ListAHORunsInBatch')(list_runs_in_batch)
mcp.tool(name='CancelAHORunBatch')(cancel_run_batch)
mcp.tool(name='DeleteAHORunBatch')(delete_run_batch)
mcp.tool(name='DeleteAHOBatch')(delete_batch)

# Register workflow analysis tools
mcp.tool(name='GetAHORunLogs')(get_run_logs)
mcp.tool(name='GetAHORunManifestLogs')(get_run_manifest_logs)
mcp.tool(name='GetAHORunEngineLogs')(get_run_engine_logs)
mcp.tool(name='GetAHOTaskLogs')(get_task_logs)
mcp.tool(name='AnalyzeAHORunPerformance')(analyze_run_performance)
mcp.tool(name='GenerateAHORunTimeline')(generate_run_timeline)

# Register troubleshooting tools
mcp.tool(name='DiagnoseAHORunFailure')(diagnose_run_failure)

# Register workflow linting tools
mcp.tool(name='LintAHOWorkflowDefinition')(lint_workflow_definition)
mcp.tool(name='LintAHOWorkflowBundle')(lint_workflow_bundle)

# Register genomics file search tools
mcp.tool(name='SearchGenomicsFiles')(search_genomics_files)
mcp.tool(name='GetSupportedFileTypes')(get_supported_file_types)

# Register helper tools
mcp.tool(name='PackageAHOWorkflow')(package_workflow)
mcp.tool(name='GetAHOSupportedRegions')(get_supported_regions)

# Register CodeConnections tools
mcp.tool(name='ListCodeConnections')(list_codeconnections)
mcp.tool(name='CreateCodeConnection')(create_codeconnection)
mcp.tool(name='GetCodeConnection')(get_codeconnection)

# Register ECR container tools
mcp.tool(name='ListECRRepositories')(list_ecr_repositories)
mcp.tool(name='CheckContainerAvailability')(check_container_availability)
mcp.tool(name='CloneContainerToECR')(clone_container_to_ecr)
mcp.tool(name='GrantHealthOmicsRepositoryAccess')(grant_healthomics_repository_access)
mcp.tool(name='ListPullThroughCacheRules')(list_pull_through_cache_rules)
mcp.tool(name='CreatePullThroughCacheForHealthOmics')(create_pull_through_cache_for_healthomics)
mcp.tool(name='CreateContainerRegistryMap')(create_container_registry_map)
mcp.tool(name='ValidateHealthOmicsECRConfig')(validate_healthomics_ecr_config)

# Register sequence store tools
mcp.tool(name='CreateAHOSequenceStore')(create_sequence_store)
mcp.tool(name='ListAHOSequenceStores')(list_sequence_stores)
mcp.tool(name='GetAHOSequenceStore')(get_sequence_store)
mcp.tool(name='UpdateAHOSequenceStore')(update_sequence_store)
mcp.tool(name='ListAHOReadSets')(list_read_sets)
mcp.tool(name='GetAHOReadSetMetadata')(get_read_set_metadata)
mcp.tool(name='StartAHOReadSetImportJob')(start_read_set_import_job)
mcp.tool(name='GetAHOReadSetImportJob')(get_read_set_import_job)
mcp.tool(name='ListAHOReadSetImportJobs')(list_read_set_import_jobs)
mcp.tool(name='StartAHOReadSetExportJob')(start_read_set_export_job)
mcp.tool(name='GetAHOReadSetExportJob')(get_read_set_export_job)
mcp.tool(name='ListAHOReadSetExportJobs')(list_read_set_export_jobs)
mcp.tool(name='ActivateAHOReadSets')(activate_read_sets)

# Register reference store tools
mcp.tool(name='ListAHOReferenceStores')(list_reference_stores)
mcp.tool(name='GetAHOReferenceStore')(get_reference_store)
mcp.tool(name='ListAHOReferences')(list_references)
mcp.tool(name='GetAHOReferenceMetadata')(get_reference_metadata)
mcp.tool(name='StartAHOReferenceImportJob')(start_reference_import_job)
mcp.tool(name='GetAHOReferenceImportJob')(get_reference_import_job)
mcp.tool(name='ListAHOReferenceImportJobs')(list_reference_import_jobs)

# Register configuration tools
mcp.tool(name='CreateAHOConfiguration')(create_configuration)
mcp.tool(name='GetAHOConfiguration')(get_configuration)
mcp.tool(name='ListAHOConfigurations')(list_configurations)
mcp.tool(name='DeleteAHOConfiguration')(delete_configuration)


def _build_jwt_role_resolver(config: ServerConfig) -> RoleResolver:
    """Select and build the JWT :class:`RoleResolver` from the resolved config.

    The resolver is chosen by which single role-resolution source the config
    carries (``parse_config`` already rejects configuring both sources at once):

    - :attr:`ServerConfig.jwt_role_arn` set -> :class:`StaticRoleResolver`,
      reproducing the current static ``MCP_JWT_ROLE_ARN`` behavior (backward
      compatible; every request resolves to that ARN with no ``ExternalId``).
    - :attr:`ServerConfig.jwt_role_registry` set ->
      :class:`RegistryRoleResolver`, built from the provider-controlled registry
      source value (``file:///path/map.json`` or ``dynamodb://table-name``).
    - neither set -> a startup error, so the server fails closed rather than
      running the ``'jwt'`` mechanism with no way to resolve a role.

    Args:
        config: The resolved server configuration carrying the (already
            validated and mutually exclusive) role-resolution sources.

    Returns:
        The selected role resolver.

    Raises:
        TransportConfigError: If neither role-resolution source is configured, or
            if the configured registry source value is malformed / names an
            unsupported backend. The server does not start in either case.
    """
    if config.jwt_role_arn:
        return StaticRoleResolver(config.jwt_role_arn)

    if config.jwt_role_registry:
        try:
            return RegistryRoleResolver.from_registry_value(config.jwt_role_registry)
        except ValueError as exc:
            # Fail closed on a malformed/unsupported registry source value. The
            # value is provider-controlled configuration (not secret), so the
            # underlying reason is safe to surface for correction.
            raise TransportConfigError(
                consts.ERROR_INVALID_JWT_ROLE_REGISTRY.format(
                    consts.MCP_JWT_ROLE_REGISTRY_ENV, exc
                )
            ) from exc

    raise TransportConfigError(
        consts.ERROR_MISSING_JWT_ROLE_SOURCE.format(
            consts.MCP_JWT_ROLE_ARN_ENV, consts.MCP_JWT_ROLE_REGISTRY_ENV
        )
    )


def _build_inbound_mechanisms(config: ServerConfig) -> list[InboundMechanism]:
    """Build inbound identity mechanism instances from the resolved config.

    Maps each enabled mechanism name (already validated and ordered by precedence
    in :func:`config.parse_config`) to its concrete implementation: ``'sigv4'`` ->
    :class:`InboundSigV4`, ``'explicit'`` -> :class:`InboundExplicitCredentials`,
    and ``'jwt'`` -> :class:`InboundJwtExchange`.

    The JWT exchange mechanism is wired with the :class:`RoleResolver` selected by
    :func:`_build_jwt_role_resolver` (static or registry) and the validated
    :attr:`ServerConfig.jwt_session_duration`. Backward compatibility is preserved:
    with only ``MCP_JWT_ROLE_ARN`` set, a :class:`StaticRoleResolver` is built and
    the mechanism behaves exactly as before.

    Args:
        config: The resolved server configuration providing the enabled inbound
            mechanisms and the JWT role-resolution / session-duration settings.

    Returns:
        The constructed inbound mechanism instances, ordered by precedence.

    Raises:
        TransportConfigError: If ``'jwt'`` is enabled but no role-resolution source
            is configured, or the configured registry source is invalid. The
            server does not start (fails closed on misconfiguration).
    """
    built: list[InboundMechanism] = []
    for name in config.inbound_mechanisms:
        if name == 'sigv4':
            built.append(InboundSigV4())
        elif name == 'explicit':
            built.append(InboundExplicitCredentials())
        elif name == 'jwt':
            role_resolver = _build_jwt_role_resolver(config)
            built.append(
                InboundJwtExchange(
                    role_resolver=role_resolver,
                    session_duration=config.jwt_session_duration,
                )
            )
    return built


def _serve_asgi_app(mcp_instance: FastMCP, app) -> None:
    """Serve a wrapped ASGI application on the configured host/port.

    The MCP SDK's ``run_streamable_http_async`` / ``run_sse_async`` entry points
    build and serve the server's *own* Starlette app and do not accept a custom
    (middleware-wrapped) application. To actually serve the
    :class:`IdentityMiddleware`-wrapped app, this replicates the SDK's own uvicorn
    setup — reading host/port/log level from ``mcp_instance.settings`` exactly as
    the SDK does — and serves the supplied ``app``.

    Args:
        mcp_instance: The ``FastMCP`` instance whose settings provide the bind
            host, port, and log level.
        app: The wrapped ASGI application to serve.
    """
    import uvicorn

    uvicorn_config = uvicorn.Config(
        app,
        host=mcp_instance.settings.host,
        port=mcp_instance.settings.port,
        log_level=mcp_instance.settings.log_level.lower(),
    )
    server = uvicorn.Server(uvicorn_config)
    anyio.run(server.serve)


def _run_multi_tenant(mcp_instance: FastMCP, config: ServerConfig) -> None:
    """Start the server in request-scoped multi-tenant mode (Phase 2).

    Installs the :class:`RequestScopedCredentialResolver` as the active resolver so
    every tool call derives credentials from the per-request
    ``CredentialContext``, builds the enabled inbound mechanisms, applies the
    network bind settings and the secure-by-default exposure check, then serves the
    SDK's network ASGI app wrapped with :class:`IdentityMiddleware`.

    Multi-tenant mode is only valid with a network transport (the stdio + multi-tenant
    combination is rejected during configuration parsing), so ``config.transport`` is
    assumed to be ``'streamable-http'`` or ``'sse'`` here.

    Args:
        mcp_instance: The ``FastMCP`` instance to serve.
        config: The resolved server configuration (multi-tenant enabled).

    Raises:
        TransportConfigError: If a required configuration value is missing (for
            example a JWT role ARN when the ``'jwt'`` mechanism is enabled). The
            server does not start.
    """
    # Fail closed and loudly: multi-tenant mode with no inbound mechanisms would
    # reject 100% of requests, which is almost always a misconfiguration. Surface
    # it as a startup error before swapping the resolver or binding a socket.
    if not config.inbound_mechanisms:
        raise TransportConfigError(
            consts.ERROR_MULTI_TENANT_REQUIRES_MECHANISM.format(
                ', '.join(consts.INBOUND_MECHANISMS), consts.MCP_INBOUND_AUTH_ENV
            )
        )

    # Build the enabled mechanisms first so any configuration error (e.g. a missing
    # JWT role-resolution source) surfaces before the resolver is swapped or the
    # server binds.
    enabled_mechanisms = _build_inbound_mechanisms(config)

    set_active_resolver(RequestScopedCredentialResolver())

    mode = config.transport
    # Reuse the Phase 1 bind-settings application and exposure check so behavior is
    # identical to the single-tenant network path.
    TransportSelector._apply_network_settings(mcp_instance, config, mode)
    TransportSelector._check_secure_exposure(config)

    if mode == 'streamable-http':
        base_app = mcp_instance.streamable_http_app()
    else:  # 'sse'
        base_app = mcp_instance.sse_app()

    # The SDK returns a Starlette app; cast to the middleware's ASGIApp callable
    # alias (the two describe the same ASGI callable with differing dict typings).
    app = IdentityMiddleware(cast(ASGIApp, base_app), enabled_mechanisms)
    _serve_asgi_app(mcp_instance, app)


def main():
    """Run the MCP server with CLI argument support.

    Parses and validates transport/network configuration from CLI flags and
    environment variables, then starts the selected transport. On a configuration
    error (unsupported transport, invalid host, invalid port, or a missing JWT role
    ARN when multi-tenant JWT auth is enabled) a descriptive message is logged and
    the process exits with a non-zero status without starting any transport.

    In single-tenant mode the Phase 1 path is used unchanged: the default
    :class:`DefaultCredentialResolver` stays active and ``mcp.run(transport=...)``
    is invoked via :meth:`TransportSelector.start`. In multi-tenant mode the
    request-scoped resolver is installed and the SDK's network ASGI app is served
    wrapped with :class:`IdentityMiddleware`.
    """
    logger.info('AWS HealthOmics MCP server starting')

    try:
        config = parse_config()
    except TransportConfigError as exc:
        # Covers UnsupportedTransportError as well as invalid host/port errors.
        logger.error(str(exc))
        sys.exit(1)

    if config.multi_tenant:
        try:
            _run_multi_tenant(mcp, config)
        except TransportConfigError as exc:
            # Covers a missing JWT role ARN and any other multi-tenant setup error.
            logger.error(str(exc))
            sys.exit(1)
    else:
        TransportSelector.start(mcp, config)


if __name__ == '__main__':
    main()
