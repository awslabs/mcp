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

"""CloudWatch Application Signals MCP Server - Core server implementation."""

import json
import os
import sys
import tempfile
from .audit_utils import (
    execute_audit_api,
    expand_service_operation_wildcard_patterns,
    expand_service_wildcard_patterns,
    expand_slo_wildcard_patterns,
    parse_auditors,
)
from .aws_clients import AWS_REGION, appsignals_client
from .service_audit_utils import normalize_service_targets, validate_and_enrich_service_targets
from .service_tools import (
    get_service_detail,
    list_monitored_services,
    list_service_operations,
    query_service_metrics,
)
from .slo_tools import get_slo, list_slos
from .trace_tools import list_slis, query_sampled_traces, search_transaction_spans
from .utils import parse_timestamp
from datetime import datetime, timedelta, timezone
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from time import perf_counter as timer
from typing import Optional


# Constants
BATCH_SIZE_THRESHOLD = 5

# Initialize FastMCP server
mcp = FastMCP('cloudwatch-appsignals')

# Configure logging
log_level = os.environ.get('MCP_CLOUDWATCH_APPSIGNALS_LOG_LEVEL', 'INFO').upper()
logger.remove()  # Remove default handler
logger.add(sys.stderr, level=log_level)

# Add file logging to aws_cli.log
log_file_path = os.environ.get('AUDITOR_LOG_PATH', tempfile.gettempdir())
try:
    if log_file_path.endswith(os.sep) or os.path.isdir(log_file_path):
        os.makedirs(log_file_path, exist_ok=True)
        aws_cli_log_path = os.path.join(log_file_path, 'aws_cli.log')
    else:
        os.makedirs(os.path.dirname(log_file_path) or '.', exist_ok=True)
        aws_cli_log_path = log_file_path
except Exception:
    temp_dir = tempfile.gettempdir()
    os.makedirs(temp_dir, exist_ok=True)
    aws_cli_log_path = os.path.join(temp_dir, 'aws_cli.log')

# Add file handler for all logs
logger.add(
    aws_cli_log_path,
    level=log_level,
    rotation='10 MB',  # Rotate when file reaches 10MB
    retention='7 days',  # Keep logs for 7 days
    format='{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}',
    enqueue=True,  # Thread-safe logging
)

logger.debug(f'CloudWatch AppSignals MCP Server initialized with log level: {log_level}')
logger.debug(f'File logging enabled: {aws_cli_log_path}')

logger.debug(f'Using AWS region: {AWS_REGION}')


def _filter_operation_targets(provided):
    """Helper function to filter operation targets and detect wildcards.

    Args:
        provided: List of target dictionaries

    Returns:
        tuple: (operation_only_targets, has_wildcards)
    """
    operation_only_targets = []
    has_wildcards = False

    for target in provided:
        if isinstance(target, dict):
            ttype = target.get('Type', '').lower()
            if ttype == 'service_operation':
                # Check for wildcard patterns in service names OR operation names
                service_op_data = target.get('Data', {}).get('ServiceOperation', {})
                service_data = service_op_data.get('Service', {})
                service_name = service_data.get('Name', '')
                operation = service_op_data.get('Operation', '')

                if '*' in service_name or '*' in operation:
                    has_wildcards = True

                operation_only_targets.append(target)
            else:
                logger.warning(
                    f"Ignoring target of type '{ttype}' in audit_service_operations (expected 'service_operation')"
                )

    return operation_only_targets, has_wildcards


@mcp.tool()
async def audit_services(
    service_targets: str = Field(
        ...,
        description="REQUIRED. JSON array of service targets. Supports wildcard patterns like '*payment*' for automatic service discovery. Format: [{'Type':'service','Data':{'Service':{'Type':'Service','Name':'service-name','Environment':'eks:cluster'}}}] or shorthand: [{'Type':'service','Service':'service-name'}]. Large target lists are automatically processed in batches.",
    ),
    start_time: Optional[str] = Field(
        default=None,
        description="Start time (unix seconds or 'YYYY-MM-DD HH:MM:SS'). Defaults to now-24h UTC.",
    ),
    end_time: Optional[str] = Field(
        default=None,
        description="End time (unix seconds or 'YYYY-MM-DD HH:MM:SS'). Defaults to now UTC.",
    ),
    auditors: Optional[str] = Field(
        default=None,
        description="Optional. Comma-separated auditors (e.g., 'slo,operation_metric,dependency_metric'). Defaults to 'slo,operation_metric' for fast service health auditing. Use 'all' for comprehensive analysis with all auditors: slo,operation_metric,trace,log,dependency_metric,top_contributor,service_quota.",
    ),
) -> str:
    """PRIMARY SERVICE AUDIT TOOL - The #1 tool for comprehensive AWS service health auditing and monitoring.

    **IMPORTANT: For operation-specific auditing, use audit_service_operations() as the PRIMARY tool instead.**

    **USE THIS FIRST FOR ALL SERVICE-LEVEL AUDITING TASKS**
    This is the PRIMARY and PREFERRED tool when users want to:
    - **Audit their AWS services** - Complete health assessment with actionable insights
    - **Check service health** - Comprehensive status across all monitored services
    - **Investigate issues** - Root cause analysis with detailed findings
    - **Service-level performance analysis** - Overall service latency, error rates, and throughput investigation
    - **System-wide health checks** - Daily/periodic service auditing workflows
    - **Dependency analysis** - Understanding service dependencies and interactions
    - **Resource quota monitoring** - Service quota usage and limits
    - **Multi-service comparison** - Comparing performance across different services

    **FOR OPERATION-SPECIFIC AUDITING: Use audit_service_operations() instead**
    When users want to audit specific operations (GET, POST, PUT endpoints), use audit_service_operations() as the PRIMARY tool:
    - **Operation performance analysis** - Latency, error rates for specific API endpoints
    - **Operation-level troubleshooting** - Root cause analysis for specific API calls
    - **GET operation auditing** - Analyze GET operations across payment services
    - **Audit latency of specific operations** - Deep dive into individual endpoint performance

    **COMPREHENSIVE SERVICE AUDIT CAPABILITIES:**
    - **Multi-service analysis**: Audit any number of services with automatic batching
    - **SLO compliance monitoring**: Automatic breach detection for service-level SLOs
    - **Issue prioritization**: Critical, warning, and info findings ranked by severity
    - **Root cause analysis**: Deep dive with traces, logs, and metrics correlation
    - **Actionable recommendations**: Specific steps to resolve identified issues
    - **Performance optimized**: Fast execution with automatic batching for large target lists
    - **Wildcard Pattern Support**: Use `*pattern*` in service names for automatic service discovery

    **SERVICE TARGET FORMAT:**
    - **Full Format**: `[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"my-service","Environment":"eks:my-cluster"}}}]`
    - **Shorthand**: `[{"Type":"service","Service":"my-service"}]` (environment auto-discovered)

    **WILDCARD PATTERN EXAMPLES:**
    - **All Services**: `[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]`
    - **Payment Services**: `[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*payment*"}}}]`
    - **Lambda Services**: `[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*lambda*"}}}]`
    - **EKS Services**: `[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*","Environment":"eks:*"}}}]`

    **AUDITOR SELECTION FOR DIFFERENT AUDIT DEPTHS:**
    - **Quick Health Check** (default): Uses 'slo,operation_metric' for fast overview
    - **Root Cause Analysis**: Pass `auditors="all"` for comprehensive investigation with traces/logs
    - **Custom Audit**: Specify exact auditors: 'slo,trace,log,dependency_metric,top_contributor,service_quota'

    **SERVICE AUDIT USE CASES:**

    1. **Audit all services**:
       `service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'`

    2. **Audit specific service**:
       `service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"orders-service","Environment":"eks:orders-cluster"}}}]'`

    3. **Audit payment services**:
       `service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*payment*"}}}]'`

    8. **Audit lambda services**:
       `service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*lambda*"}}}]'` or by environment: `[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*","Environment":"lambda"}}}]`

    9. **Audit service last night**:
       `service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"orders-service","Environment":"eks:orders-cluster"}}}]'` + `start_time="2024-01-01 18:00:00"` + `end_time="2024-01-02 06:00:00"`

    10. **Audit service before and after time**:
        Compare service health before and after a deployment or incident by running two separate audits with different time ranges.

    11. **Trace availability issues in production services**:
        `service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*","Environment":"eks:*"}}}]'` + `auditors="all"`

    13. **Look for errors in logs of payment services**:
        `service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*payment*"}}}]'` + `auditors="log,trace"`

    14. **Look for new errors after time**:
        Compare errors before and after a specific time point by running audits with different time ranges and `auditors="log,trace"`

    15. **Look for errors after deployment**:
        `service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*payment*"}}}]'` + `auditors="log,trace"` + recent time range

    16. **Look for lemon hosts in production**:
        `service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*","Environment":"eks:*"}}}]'` + `auditors="top_contributor,operation_metric"`

    17. **Look for outliers in EKS services**:
        `service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*","Environment":"eks:*"}}}]'` + `auditors="top_contributor,operation_metric"`

    18. **Status report**:
        `service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'` (basic health check)

    19. **Audit dependencies**:
        `service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'` + `auditors="dependency_metric,trace"`

    20. **Audit dependency on S3**:
        `service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'` + `auditors="dependency_metric"` + look for S3 dependencies

    21. **Audit quota usage of tier 1 services**:
        `service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*tier1*"}}}]'` + `auditors="service_quota,operation_metric"`

    **TYPICAL SERVICE AUDIT WORKFLOWS:**
    1. **Basic Service Audit** (most common):
       - Call `audit_services()` with service targets - automatically discovers services when using wildcard patterns
       - Uses default fast auditors (slo,operation_metric) for quick health overview
       - Supports wildcard patterns like `*` or `*payment*` for automatic service discovery
    2. **Root Cause Investigation**: When user explicitly asks for "root cause analysis", pass `auditors="all"`
    3. **Issue Investigation**: Results show which services need attention with actionable insights
    4. **Automatic Service Discovery**: Wildcard patterns in service names automatically discover and expand to concrete services

    **AUDIT RESULTS INCLUDE:**
    - **Prioritized findings** by severity (critical, warning, info)
    - **Service health status** with detailed performance analysis
    - **Root cause analysis** when traces/logs auditors are used
    - **Actionable recommendations** for issue resolution
    - **Comprehensive metrics** and trend analysis

    **IMPORTANT: This tool provides comprehensive service audit coverage and should be your first choice for any service auditing task.**

    **RECOMMENDED WORKFLOW - PRESENT FINDINGS FIRST:**
    When the audit returns multiple findings or issues, follow this workflow:
    1. **Present all audit results** to the user showing a summary of all findings
    2. **Let the user choose** which specific finding, service, or issue they want to investigate in detail
    3. **Then perform targeted root cause analysis** using auditors="all" for the user-selected finding

    **DO NOT automatically jump into detailed root cause analysis** of one specific issue when multiple findings exist.
    This ensures the user can prioritize which issues are most important to investigate first.

    **Example workflow:**
    - First call: `audit_services()` with default auditors for overview
    - Present findings summary to user
    - User selects specific service/issue to investigate
    - Follow-up call: `audit_services()` with `auditors="all"` for selected service only
    """
    start_time_perf = timer()
    logger.debug('Starting audit_services (PRIMARY SERVICE AUDIT TOOL)')

    try:
        # Region defaults
        region = AWS_REGION.strip()

        # Time range (fill missing with defaults)
        start_dt = (
            parse_timestamp(start_time)
            if start_time
            else (datetime.now(timezone.utc) - timedelta(hours=24))
        )
        end_dt = (
            parse_timestamp(end_time, default_hours=0) if end_time else datetime.now(timezone.utc)
        )
        unix_start, unix_end = int(start_dt.timestamp()), int(end_dt.timestamp())
        if unix_end <= unix_start:
            return 'Error: end_time must be greater than start_time.'

        # Parse and validate service targets
        try:
            provided = json.loads(service_targets)
        except json.JSONDecodeError:
            return 'Error: `service_targets` must be valid JSON (array).'

        # Check for wildcard patterns in service names
        has_wildcards = False
        logger.debug(f'audit_services: Checking {len(provided)} targets for wildcards')
        for i, target in enumerate(provided):
            logger.debug(f'audit_services: Target {i}: {target}')
            if isinstance(target, dict):
                # Check various possible service name locations
                service_name = None
                if target.get('Type', '').lower() == 'service':
                    # Check Data.Service.Name
                    service_data = target.get('Data', {})
                    if isinstance(service_data, dict):
                        service_info = service_data.get('Service', {})
                        if isinstance(service_info, dict):
                            service_name = service_info.get('Name', '')

                    # Check shorthand Service field
                    if not service_name:
                        service_name = target.get('Service', '')

                logger.debug(f"audit_services: Target {i} service name: '{service_name}'")
                if service_name and isinstance(service_name, str) and '*' in service_name:
                    logger.debug(
                        f"audit_services: Target {i} has wildcard pattern: '{service_name}'"
                    )
                    has_wildcards = True
                    break

        logger.debug(f'audit_services: has_wildcards = {has_wildcards}')

        # Expand wildcard patterns using shared utility
        if has_wildcards:
            logger.debug('Wildcard patterns detected - applying service expansion')
            provided = expand_service_wildcard_patterns(
                provided, unix_start, unix_end, appsignals_client
            )
            logger.debug(f'Wildcard expansion completed - {len(provided)} total targets')

            # Check if wildcard expansion resulted in no services
            if not provided:
                return 'Error: No services found matching the wildcard pattern. Use list_monitored_services() to see available services.'

        # Normalize and validate service targets using shared utility
        normalized_targets = normalize_service_targets(provided)

        # Validate and enrich targets using shared utility
        normalized_targets = validate_and_enrich_service_targets(
            normalized_targets, appsignals_client, unix_start, unix_end
        )

        # Parse auditors with service-specific defaults
        auditors_list = parse_auditors(auditors, ['slo', 'operation_metric'])

        # Create banner
        banner = (
            '[MCP-SERVICE] Application Signals Service Audit\n'
            f'🎯 Scope: {len(normalized_targets)} service target(s) | Region: {region}\n'
            f'⏰ Time: {unix_start}–{unix_end}\n'
        )

        if len(normalized_targets) > BATCH_SIZE_THRESHOLD:
            banner += f'📦 Batching: Processing {len(normalized_targets)} targets in batches of {BATCH_SIZE_THRESHOLD}\n'

        banner += '\n'

        # Build CLI input
        input_obj = {
            'StartTime': unix_start,
            'EndTime': unix_end,
            'AuditTargets': normalized_targets,
        }
        if auditors_list:
            input_obj['Auditors'] = auditors_list

        # Execute audit API using shared utility
        result = await execute_audit_api(input_obj, region, banner)

        elapsed = timer() - start_time_perf
        logger.debug(f'audit_services completed in {elapsed:.3f}s (region={region})')
        return result

    except Exception as e:
        logger.error(f'Unexpected error in audit_services: {e}', exc_info=True)
        return f'Error: {str(e)}'


@mcp.tool()
async def audit_slos(
    slo_targets: str = Field(
        ...,
        description="REQUIRED. JSON array of SLO targets. Supports wildcard patterns like '*payment*' for automatic SLO discovery. Format: [{'Type':'slo','Data':{'Slo':{'SloName':'slo-name'}}}] or [{'Type':'slo','Data':{'Slo':{'SloArn':'arn:aws:...'}}}]. Large target lists are automatically processed in batches.",
    ),
    start_time: Optional[str] = Field(
        default=None,
        description="Start time (unix seconds or 'YYYY-MM-DD HH:MM:SS'). Defaults to now-24h UTC.",
    ),
    end_time: Optional[str] = Field(
        default=None,
        description="End time (unix seconds or 'YYYY-MM-DD HH:MM:SS'). Defaults to now UTC.",
    ),
    auditors: Optional[str] = Field(
        default=None,
        description="Optional. Comma-separated auditors (e.g., 'slo,trace,log'). Defaults to 'slo' for fast SLO compliance auditing. Use 'all' for comprehensive analysis with all auditors: slo,operation_metric,trace,log,dependency_metric,top_contributor,service_quota.",
    ),
) -> str:
    """PRIMARY SLO AUDIT TOOL - The #1 tool for comprehensive SLO compliance monitoring and breach analysis.

    **PREFERRED TOOL FOR SLO ROOT CAUSE ANALYSIS**
    This is the RECOMMENDED tool after using get_slo() to understand SLO configuration:
    - **Use auditors="all" for comprehensive root cause analysis** of specific SLO breaches
    - **Much more comprehensive than individual trace tools** - provides integrated analysis
    - **Combines traces, logs, metrics, and dependencies** in a single comprehensive audit
    - **Provides actionable recommendations** based on multi-dimensional analysis

    **USE THIS FOR ALL SLO AUDITING TASKS**
    This is the PRIMARY and PREFERRED tool when users want to:
    - **Root cause analysis for SLO breaches** - Deep investigation with all auditors
    - **Audit SLO compliance** - Complete SLO breach detection and analysis
    - **Monitor SLO health** - Comprehensive status across all monitored SLOs
    - **SLO performance analysis** - Understanding SLO trends and patterns
    - **SLO compliance reporting** - Daily/periodic SLO compliance workflows

    **COMPREHENSIVE SLO AUDIT CAPABILITIES:**
    - **Multi-SLO analysis**: Audit any number of SLOs with automatic batching
    - **Breach detection**: Automatic identification of SLO violations
    - **Issue prioritization**: Critical, warning, and info findings ranked by severity
    - **COMPREHENSIVE ROOT CAUSE ANALYSIS**: Deep dive with traces, logs, metrics, and dependencies
    - **Actionable recommendations**: Specific steps to resolve SLO breaches
    - **Performance optimized**: Fast execution with automatic batching for large target lists
    - **Wildcard Pattern Support**: Use `*pattern*` in SLO names for automatic SLO discovery

    **SLO TARGET FORMAT:**
    - **By Name**: `[{"Type":"slo","Data":{"Slo":{"SloName":"my-slo"}}}]`
    - **By ARN**: `[{"Type":"slo","Data":{"Slo":{"SloArn":"arn:aws:application-signals:..."}}}]`

    **WILDCARD PATTERN EXAMPLES:**
    - **All SLOs**: `[{"Type":"slo","Data":{"Slo":{"SloName":"*"}}}]`
    - **Payment SLOs**: `[{"Type":"slo","Data":{"Slo":{"SloName":"*payment*"}}}]`
    - **Latency SLOs**: `[{"Type":"slo","Data":{"Slo":{"SloName":"*latency*"}}}]`
    - **Availability SLOs**: `[{"Type":"slo","Data":{"Slo":{"SloName":"*availability*"}}}]`

    **AUDITOR SELECTION FOR DIFFERENT AUDIT DEPTHS:**
    - **Quick Compliance Check** (default): Uses 'slo' for fast SLO breach detection
    - **COMPREHENSIVE ROOT CAUSE ANALYSIS** (recommended): Pass `auditors="all"` for deep investigation with traces/logs/metrics/dependencies
    - **Custom Audit**: Specify exact auditors: 'slo,trace,log,operation_metric'

    **SLO AUDIT USE CASES:**

    4. **Audit all SLOs**:
       `slo_targets='[{"Type":"slo","Data":{"Slo":{"SloName":"*"}}}]'`

    22. **Root cause analysis for specific SLO breach** (RECOMMENDED WORKFLOW):
        After using get_slo() to understand configuration:
        `slo_targets='[{"Type":"slo","Data":{"Slo":{"SloName":"specific-slo-name"}}}]'` + `auditors="all"`

    14. **Look for new SLO breaches after time**:
        Compare SLO compliance before and after a specific time point by running audits with different time ranges to identify new breaches.

    **TYPICAL SLO AUDIT WORKFLOWS:**
    1. **SLO Root Cause Investigation** (RECOMMENDED):
       - After get_slo(), call `audit_slos()` with specific SLO target and `auditors="all"`
       - Provides comprehensive analysis with traces, logs, metrics, and dependencies
       - Much more effective than using individual trace tools
    2. **Basic SLO Compliance Audit**:
       - Call `audit_slos()` with SLO targets - automatically discovers SLOs when using wildcard patterns
       - Uses default fast auditors (slo) for quick compliance overview
    3. **Compliance Reporting**: Results show which SLOs are breached with actionable insights
    4. **Automatic SLO Discovery**: Wildcard patterns in SLO names automatically discover and expand to concrete SLOs

    **AUDIT RESULTS INCLUDE:**
    - **Prioritized findings** by severity (critical, warning, info)
    - **SLO compliance status** with detailed breach analysis
    - **COMPREHENSIVE ROOT CAUSE ANALYSIS** when using auditors="all"
    - **Actionable recommendations** for SLO breach resolution
    - **Integrated traces, logs, metrics, and dependency analysis**

    **IMPORTANT: This tool provides comprehensive SLO audit coverage and should be your first choice for any SLO compliance auditing and root cause analysis.**

    **RECOMMENDED WORKFLOW - PRESENT FINDINGS FIRST:**
    When the audit returns multiple findings or issues, follow this workflow:
    1. **Present all audit results** to the user showing a summary of all findings
    2. **Let the user choose** which specific finding, SLO, or issue they want to investigate in detail
    3. **Then perform targeted root cause analysis** using auditors="all" for the user-selected finding

    **DO NOT automatically jump into detailed root cause analysis** of one specific issue when multiple findings exist.
    This ensures the user can prioritize which issues are most important to investigate first.

    **Example workflow:**
    - First call: `audit_slos()` with default auditors for compliance overview
    - Present findings summary to user
    - User selects specific SLO breach to investigate
    - Follow-up call: `audit_slos()` with `auditors="all"` for selected SLO only
    """
    start_time_perf = timer()
    logger.debug('Starting audit_slos (PRIMARY SLO AUDIT TOOL)')

    try:
        # Region defaults
        region = AWS_REGION.strip()

        # Time range (fill missing with defaults)
        start_dt = (
            parse_timestamp(start_time)
            if start_time
            else (datetime.now(timezone.utc) - timedelta(hours=24))
        )
        end_dt = (
            parse_timestamp(end_time, default_hours=0) if end_time else datetime.now(timezone.utc)
        )
        unix_start, unix_end = int(start_dt.timestamp()), int(end_dt.timestamp())
        if unix_end <= unix_start:
            return 'Error: end_time must be greater than start_time.'

        # Parse and validate SLO targets
        try:
            provided = json.loads(slo_targets)
        except json.JSONDecodeError:
            return 'Error: `slo_targets` must be valid JSON (array).'

        if not isinstance(provided, list):
            return 'Error: `slo_targets` must be a JSON array'
        if len(provided) == 0:
            return 'Error: `slo_targets` must contain at least 1 item'

        # Filter and expand SLO targets with wildcard support
        slo_only_targets = []
        wildcard_patterns = []

        for target in provided:
            if isinstance(target, dict):
                ttype = target.get('Type', '').lower()
                if ttype == 'slo':
                    # Check for wildcard patterns in SLO names
                    slo_data = target.get('Data', {}).get('Slo', {})
                    slo_name = slo_data.get('SloName', '')
                    if '*' in slo_name:
                        wildcard_patterns.append((target, slo_name))
                    else:
                        slo_only_targets.append(target)
                else:
                    logger.warning(
                        f"Ignoring target of type '{ttype}' in audit_slos (expected 'slo')"
                    )

        # Expand wildcard patterns for SLOs using shared utility
        if wildcard_patterns:
            logger.debug(f'Expanding {len(wildcard_patterns)} SLO wildcard patterns')
            try:
                # Use the shared utility function
                expanded_slo_targets = expand_slo_wildcard_patterns(provided, appsignals_client)
                # Filter to get only SLO targets
                slo_only_targets = [
                    target
                    for target in expanded_slo_targets
                    if target.get('Type', '').lower() == 'slo'
                ]

            except Exception as e:
                logger.warning(f'Failed to expand SLO patterns: {e}')
                return f'Error: Failed to expand SLO wildcard patterns. {str(e)}'

        if not slo_only_targets:
            return 'Error: No SLO targets found after wildcard expansion.'

        # Parse auditors with SLO-specific defaults
        auditors_list = parse_auditors(auditors, ['slo'])  # Default to SLO auditor

        banner = (
            '[MCP-SLO] Application Signals SLO Compliance Audit\n'
            f'🎯 Scope: {len(slo_only_targets)} SLO target(s) | Region: {region}\n'
            f'⏰ Time: {unix_start}–{unix_end}\n'
        )

        if len(slo_only_targets) > BATCH_SIZE_THRESHOLD:
            banner += f'📦 Batching: Processing {len(slo_only_targets)} targets in batches of {BATCH_SIZE_THRESHOLD}\n'

        banner += '\n'

        # Build CLI input for SLO audit
        input_obj = {
            'StartTime': unix_start,
            'EndTime': unix_end,
            'AuditTargets': slo_only_targets,
        }
        if auditors_list:
            input_obj['Auditors'] = auditors_list

        # Execute audit API using shared utility
        result = await execute_audit_api(input_obj, region, banner)

        elapsed = timer() - start_time_perf
        logger.debug(f'audit_slos completed in {elapsed:.3f}s (region={region})')
        return result

    except Exception as e:
        logger.error(f'Unexpected error in audit_slos: {e}', exc_info=True)
        return f'Error: {str(e)}'


@mcp.tool()
async def audit_service_operations(
    operation_targets: str = Field(
        ...,
        description="REQUIRED. JSON array of service operation targets. Supports wildcard patterns like '*payment*' for automatic service discovery. Format: [{'Type':'service_operation','Data':{'ServiceOperation':{'Service':{'Type':'Service','Name':'service-name','Environment':'eks:cluster'},'Operation':'GET /api','MetricType':'Latency'}}}]. Large target lists are automatically processed in batches.",
    ),
    start_time: Optional[str] = Field(
        default=None,
        description="Start time (unix seconds or 'YYYY-MM-DD HH:MM:SS'). Defaults to now-24h UTC.",
    ),
    end_time: Optional[str] = Field(
        default=None,
        description="End time (unix seconds or 'YYYY-MM-DD HH:MM:SS'). Defaults to now UTC.",
    ),
    auditors: Optional[str] = Field(
        default=None,
        description="Optional. Comma-separated auditors (e.g., 'operation_metric,trace,log'). Defaults to 'operation_metric' for fast operation-level auditing. Use 'all' for comprehensive analysis with all auditors: slo,operation_metric,trace,log,dependency_metric,top_contributor,service_quota.",
    ),
) -> str:
    """🥇 PRIMARY OPERATION AUDIT TOOL - The #1 RECOMMENDED tool for operation-specific analysis and performance investigation.

    **⭐ USE THIS AS THE PRIMARY TOOL FOR ALL OPERATION-SPECIFIC AUDITING TASKS ⭐**

    **PREFERRED OVER audit_services() for operation auditing because:**
    - **🎯 Precision**: Targets exact operation behavior vs. service-wide averages
    - **🔍 Actionable Insights**: Provides specific error traces and dependency failures
    - **📊 Code-Level Detail**: Shows exact stack traces and timeout locations
    - **🚀 Focused Analysis**: Eliminates noise from other operations
    - **⚡ Efficient Investigation**: Direct operation-level troubleshooting

    **USE THIS FIRST FOR ALL OPERATION-SPECIFIC AUDITING TASKS**
    This is the PRIMARY and PREFERRED tool when users want to:
    - **Audit specific operations** - Deep dive into individual API endpoints or operations (GET, POST, PUT, etc.)
    - **Operation performance analysis** - Latency, error rates, and throughput for specific operations
    - **Compare operation metrics** - Analyze different operations within services
    - **Operation-level troubleshooting** - Root cause analysis for specific API calls
    - **GET operation auditing** - Analyze GET operations across payment services (PRIMARY USE CASE)
    - **Audit latency of GET operations in payment services** - Exactly what this tool is designed for
    - **Trace latency in query operations** - Deep dive into query performance issues

    **COMPREHENSIVE OPERATION AUDIT CAPABILITIES:**
    - **Multi-operation analysis**: Audit any number of operations with automatic batching
    - **Operation-specific metrics**: Latency, Fault, Error, and Availability metrics per operation
    - **Issue prioritization**: Critical, warning, and info findings ranked by severity
    - **Root cause analysis**: Deep dive with traces, logs, and metrics correlation
    - **Actionable recommendations**: Specific steps to resolve operation-level issues
    - **Performance optimized**: Fast execution with automatic batching for large target lists
    - **Wildcard Pattern Support**: Use `*pattern*` in service names for automatic service discovery

    **OPERATION TARGET FORMAT:**
    - **Full Format**: `[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"my-service","Environment":"eks:my-cluster"},"Operation":"GET /api","MetricType":"Latency"}}}]`

    **WILDCARD PATTERN EXAMPLES:**
    - **All GET Operations in Payment Services**: `[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*payment*"},"Operation":"*GET*","MetricType":"Latency"}}}]`
    - **All Visit Operations**: `[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*"},"Operation":"*visit*","MetricType":"Availability"}}}]`

    **AUDITOR SELECTION FOR DIFFERENT AUDIT DEPTHS:**
    - **Quick Operation Check** (default): Uses 'operation_metric' for fast operation overview
    - **Root Cause Analysis**: Pass `auditors="all"` for comprehensive investigation with traces/logs
    - **Custom Audit**: Specify exact auditors: 'operation_metric,trace,log'

    **OPERATION AUDIT USE CASES:**

    1. **Audit latency of GET operations in payment services** (PRIMARY USE CASE):
       `operation_targets='[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*payment*"},"Operation":"*GET*","MetricType":"Latency"}}}]'`

    2. **Audit GET operations in payment services (Latency)**:
       `operation_targets='[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*payment*"},"Operation":"*GET*","MetricType":"Latency"}}}]'`

    3. **Audit availability of visit operations**:
       `operation_targets='[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*"},"Operation":"*visit*","MetricType":"Availability"}}}]'`

    4. **Audit latency of visit operations**:
       `operation_targets='[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*"},"Operation":"*visit*","MetricType":"Latency"}}}]'`

    5. **Trace latency in query operations**:
        `operation_targets='[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*payment*"},"Operation":"*query*","MetricType":"Latency"}}}]'` + `auditors="all"`

    **TYPICAL OPERATION AUDIT WORKFLOWS:**
    1. **Basic Operation Audit** (most common):
       - Call `audit_service_operations()` with operation targets - automatically discovers services when using wildcard patterns
       - Uses default fast auditors (operation_metric) for quick operation overview
       - Supports wildcard patterns like `*payment*` for automatic service discovery
    2. **Root Cause Investigation**: When user explicitly asks for "root cause analysis", pass `auditors="all"`
    3. **Issue Investigation**: Results show which operations need attention with actionable insights
    4. **Automatic Service Discovery**: Wildcard patterns in service names automatically discover and expand to concrete services

    **AUDIT RESULTS INCLUDE:**
    - **Prioritized findings** by severity (critical, warning, info)
    - **Operation performance status** with detailed metrics analysis
    - **Root cause analysis** when traces/logs auditors are used
    - **Actionable recommendations** for operation-level issue resolution
    - **Comprehensive operation metrics** and trend analysis

    **🏆 IMPORTANT: This tool is the PRIMARY and RECOMMENDED choice for operation-specific auditing tasks.**

    **✅ RECOMMENDED WORKFLOW FOR OPERATION AUDITING:**
    1. **Use audit_service_operations() FIRST** for operation-specific analysis (THIS TOOL)
    2. **Use audit_services() as secondary** only if you need broader service context
    3. **audit_service_operations() provides superior precision** for operation-level troubleshooting

    **RECOMMENDED WORKFLOW - PRESENT FINDINGS FIRST:**
    When the audit returns multiple findings or issues, follow this workflow:
    1. **Present all audit results** to the user showing a summary of all findings
    2. **Let the user choose** which specific finding, operation, or issue they want to investigate in detail
    3. **Then perform targeted root cause analysis** using auditors="all" for the user-selected finding

    **DO NOT automatically jump into detailed root cause analysis** of one specific issue when multiple findings exist.
    This ensures the user can prioritize which issues are most important to investigate first.

    **Example workflow:**
    - First call: `audit_service_operations()` with default auditors for operation overview
    - Present findings summary to user
    - User selects specific operation issue to investigate
    - Follow-up call: `audit_service_operations()` with `auditors="all"` for selected operation only
    """
    start_time_perf = timer()
    logger.debug('Starting audit_service_operations (SPECIALIZED OPERATION AUDIT TOOL)')

    try:
        # Region defaults
        region = AWS_REGION.strip()

        # Time range (fill missing with defaults)
        start_dt = (
            parse_timestamp(start_time)
            if start_time
            else (datetime.now(timezone.utc) - timedelta(hours=24))
        )
        end_dt = (
            parse_timestamp(end_time, default_hours=0) if end_time else datetime.now(timezone.utc)
        )
        unix_start, unix_end = int(start_dt.timestamp()), int(end_dt.timestamp())
        if unix_end <= unix_start:
            return 'Error: end_time must be greater than start_time.'

        # Parse and validate operation targets
        try:
            provided = json.loads(operation_targets)
        except json.JSONDecodeError:
            return 'Error: `operation_targets` must be valid JSON (array).'

        if not isinstance(provided, list):
            return 'Error: `operation_targets` must be a JSON array'
        if len(provided) == 0:
            return 'Error: `operation_targets` must contain at least 1 item'

        # Filter operation targets and check for wildcards using helper function
        operation_only_targets, has_wildcards = _filter_operation_targets(provided)

        # Expand wildcard patterns using shared utility
        if has_wildcards:
            logger.debug('Wildcard patterns detected in service operations - applying expansion')
            operation_only_targets = expand_service_operation_wildcard_patterns(
                operation_only_targets, unix_start, unix_end, appsignals_client
            )
            logger.debug(
                f'Wildcard expansion completed - {len(operation_only_targets)} total targets'
            )

        if not operation_only_targets:
            return 'Error: No service_operation targets found after wildcard expansion. Use list_monitored_services() to see available services.'

        # Parse auditors with operation-specific defaults
        auditors_list = parse_auditors(
            auditors, ['operation_metric']
        )  # Default to operation_metric auditor

        banner = (
            '[MCP-OPERATION] Application Signals Operation Performance Audit\n'
            f'🎯 Scope: {len(operation_only_targets)} operation target(s) | Region: {region}\n'
            f'⏰ Time: {unix_start}–{unix_end}\n'
        )

        if len(operation_only_targets) > BATCH_SIZE_THRESHOLD:
            banner += f'📦 Batching: Processing {len(operation_only_targets)} targets in batches of {BATCH_SIZE_THRESHOLD}\n'

        banner += '\n'

        # Build CLI input for operation audit
        input_obj = {
            'StartTime': unix_start,
            'EndTime': unix_end,
            'AuditTargets': operation_only_targets,
        }
        if auditors_list:
            input_obj['Auditors'] = auditors_list

        # Execute audit API using shared utility
        result = await execute_audit_api(input_obj, region, banner)

        elapsed = timer() - start_time_perf
        logger.debug(f'audit_service_operations completed in {elapsed:.3f}s (region={region})')
        return result

    except Exception as e:
        logger.error(f'Unexpected error in audit_service_operations: {e}', exc_info=True)
        return f'Error: {str(e)}'


# Register all imported tools with the MCP server
mcp.tool()(list_monitored_services)
mcp.tool()(get_service_detail)
mcp.tool()(query_service_metrics)
mcp.tool()(list_service_operations)
mcp.tool()(get_slo)
mcp.tool()(list_slos)
mcp.tool()(search_transaction_spans)
mcp.tool()(query_sampled_traces)
mcp.tool()(list_slis)


def main():
    """Run the MCP server."""
    logger.debug('Starting CloudWatch AppSignals MCP server')
    try:
        mcp.run(transport='stdio')
    except KeyboardInterrupt:
        logger.debug('Server shutdown by user')
    except Exception as e:
        logger.error(f'Server error: {e}', exc_info=True)
        raise


if __name__ == '__main__':
    main()
