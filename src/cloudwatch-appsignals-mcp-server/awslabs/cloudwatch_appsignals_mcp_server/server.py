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
import re
import sys
import tempfile
from .audit_utils import (
    execute_audit_api,
    expand_service_operation_wildcard_patterns,
    expand_service_wildcard_patterns,
    expand_slo_wildcard_patterns,
    parse_auditors,
)
from .aws_clients import (
    AWS_REGION,
    appsignals_client,
    iam_client,
    s3_client,
    synthetics_client,
)
from .batch_processing_utils import (
    create_batch_session,
    format_batch_result,
    get_batch_session,
    process_next_batch,
)
from .batch_tools import (
    cleanup_audit_sessions,
    continue_audit_batch,
)
from .canary_utils import (
    analyze_canary_logs_with_time_window,
    analyze_har_file,
    analyze_iam_role_and_policies,
    analyze_log_files,
    analyze_screenshots,
    check_resource_arns_correct,
    extract_disk_memory_usage_metrics,
    get_canary_code,
    get_canary_metrics_and_service_insights,
)
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
AUDIT_SERVICE_BATCH_SIZE_THRESHOLD = 10

RUN_STATES = {'RUNNING': 'RUNNING', 'PASSED': 'PASSED', 'FAILED': 'FAILED'}

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

                # For fault metrics, ListAuditFindings uses Availability metric type.
                # API only supports Availability/Latency/Error for service_operation targets.
                metric_type = service_op_data.get('MetricType', '')
                if metric_type == 'Fault':
                    service_op_data['MetricType'] = 'Availability'

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

    **🚨 CRITICAL: When findings are discovered, ALWAYS ASK USER TO CHOOSE:**
    - **Option A: Investigate specific finding** (deep dive with auditors="all")
    - **Option B: Continue processing** (use continue_audit_batch())
    **DO NOT auto-continue when findings exist - WAIT for user decision**

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
       - For large service lists (>5 services), uses interactive batch processing
       - Returns results of each batch
       - If services in batch look normal, continue with `continue_audit_batch()`
       - If audit returns findings/issues, ASK USER TO CHOOSE: investigate or continue
       - Uses default fast auditors (slo,operation_metric) for quick health overview
       - Supports wildcard patterns like `*` or `*payment*` for automatic service discovery
    2. **Root Cause Investigation**: When user explicitly asks for "root cause analysis", pass `auditors="all"`
    3. **Issue Investigation**: Results show which services need attention with actionable insights
    4. **Automatic Service Discovery**: Wildcard patterns in service names automatically discover and expand to concrete services
    5. **Interactive Batch Processing**: For large target lists, process in batches and interactively ask user to proceed

    **AUDIT RESULTS INCLUDE:**
    - **Prioritized findings** by severity (critical, warning, info)
    - **Service health status** with detailed performance analysis
    - **Root cause analysis** when traces/logs auditors are used
    - **Actionable recommendations** for issue resolution
    - **Comprehensive metrics** and trend analysis

    **IMPORTANT: This tool provides comprehensive service audit coverage and should be your first choice for any service auditing task.**

    **RECOMMENDED WORKFLOW - PRESENT FINDINGS FIRST:**
    **For Large Service Lists (>5 services):**
    1. **audit_services() automatically starts interactive batch processing**
    2. **System processes first batch and shows full JSON findings** for MCP observation
    3. **🚨 IF BATCH HAS FINDINGS/ISSUES - MANDATORY WORKFLOW:**
       1. **STOP processing immediately**
       2. **Present complete audit findings** in clear summary format
       3. **ASK USER TO CHOOSE:** Investigate specific finding OR continue processing
       4. **WAIT for user decision** - Do not auto-continue
       5. **If investigating:** Follow-up call with `auditors="all"` for user-selected finding only
       6. **If continuing:** Use `continue_audit_batch()` to process next batch
    4. **✅ If batch looks healthy (NO findings):**
       - Use `continue_audit_batch(session_id)` to process next batch immediately
    5. **When all services processed, conclude the audit results in all batches**

    **For Small Service Lists (≤5 services):**
    1. **Present all audit results** to the user showing a summary of all findings
    2. **🚨 IF FINDINGS EXIST:** Ask user to choose which specific finding to investigate
    3. **WAIT for user decision** before performing targeted root cause analysis
    4. **Then perform targeted root cause analysis** using auditors="all" for user-selected finding

    **Example workflow:**
    1. First call: `audit_services()` with default auditors for overview → Returns batch session with first batch results and findings
    2. **🚨 IF FINDINGS DISCOVERED:** Present findings summary to user and ask for choice
    3. **WAIT for user decision:** User selects specific service/issue to investigate OR user chooses to continue processing
    4. **If investigating:** Follow-up call: `audit_services()` with `auditors="all"` for selected service only
    5. **If continuing:** `continue_audit_batch(session_id)` → Process next batch
    6. **Repeat:** Continue batch processing cycle with user choice at each step when findings exist
    7. **Conclude:** When all services processed, summarize audit results from all batches
    8. **Cleanup:** After completing full audit, call `cleanup_audit_sessions()` to free memory resources
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

        if len(normalized_targets) > AUDIT_SERVICE_BATCH_SIZE_THRESHOLD:
            banner += f'📦 Batching: Processing {len(normalized_targets)} targets in batches of {AUDIT_SERVICE_BATCH_SIZE_THRESHOLD}\n'

        banner += '\n'

        # Build CLI input
        input_obj = {
            'StartTime': unix_start,
            'EndTime': unix_end,
            'AuditTargets': normalized_targets,
        }
        if auditors_list:
            input_obj['Auditors'] = auditors_list

        # Interactive Batch Processing Logic
        if len(normalized_targets) > AUDIT_SERVICE_BATCH_SIZE_THRESHOLD:
            # Create interactive batch session for large target lists
            session_id = create_batch_session(
                targets=normalized_targets,
                input_obj=input_obj,
                region=region,
                banner=banner,
                batch_size=AUDIT_SERVICE_BATCH_SIZE_THRESHOLD,
                auto_complete=None,  # Auto-decide based on target count
            )

            # Process first batch
            batch_result = process_next_batch(session_id, appsignals_client)
            session = get_batch_session(session_id)

            if batch_result.get('error'):
                return f'Error processing first batch: {batch_result["error"]}'

            # Format and return interactive batch result
            if session is not None:
                formatted_result = banner + format_batch_result(batch_result, session)
            else:
                formatted_result = banner + 'Error: Session not found for batch processing'

            elapsed = timer() - start_time_perf
            logger.debug(
                f'audit_services (interactive batch mode) completed first batch in {elapsed:.3f}s (region={region})'
            )
            return formatted_result
        else:
            # Execute audit API using shared utility for small target lists
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


@mcp.tool()
async def analyze_canary_failures(canary_name: str, region: str = AWS_REGION) -> str:
    """Comprehensive canary failure analysis with deep dive into issues.

    Use this tool to:
    - Deep dive into canary failures with root cause identification
    - Analyze historical patterns and specific incident details
    - Get comprehensive artifact analysis including logs, screenshots, and HAR files
    - Receive actionable recommendations based on AWS debugging methodology
    - Correlate canary failures with Application Signals telemetry data
    - Identify performance degradation and availability issues across service dependencies

    Key Features:
    - **Failure Pattern Analysis**: Identifies recurring failure modes and temporal patterns
    - **Artifact Deep Dive**: Analyzes canary logs, screenshots, and network traces for root causes
    - **Service Correlation**: Links canary failures to upstream/downstream service issues using Application Signals
    - **Performance Insights**: Detects latency spikes, fault rates, and connection issues
    - **Actionable Remediation**: Provides specific steps based on AWS operational best practices

    Common Use Cases:
    1. **Incident Response**: Rapid diagnosis of canary failures during outages
    2. **Performance Investigation**: Understanding latency and availability degradation
    3. **Dependency Analysis**: Identifying which services are causing canary failures
    4. **Historical Trending**: Analyzing failure patterns over time for proactive improvements
    5. **Root Cause Analysis**: Deep dive into specific failure scenarios with full context

    Output Includes:
    - Severity-ranked findings with immediate action items
    - Service-level telemetry insights with trace analysis
    - Exception details and stack traces from canary artifacts
    - Network connectivity and performance metrics
    - Correlation with Application Signals audit findings
    - Historical failure patterns and recovery recommendations

    Args:
        canary_name (str): Name of the CloudWatch Synthetics canary to analyze
        region (str, optional): AWS region where the canary is deployed.

    Returns:
        dict: Comprehensive failure analysis containing:
            - Failure severity assessment and immediate recommendations
            - Detailed artifact analysis (logs, screenshots, HAR files)
            - Service dependency health and performance metrics
            - Root cause identification with specific remediation steps
            - Historical pattern analysis and trend insights
    """
    try:
        # Get recent canary runs
        response = synthetics_client.get_canary_runs(Name=canary_name, MaxResults=5)
        runs = response.get('CanaryRuns', [])

        # Get canary details
        canary_response = synthetics_client.get_canary(Name=canary_name)
        canary = canary_response['Canary']

        # Get telemetry and service insights
        try:
            telemetry_insights = await get_canary_metrics_and_service_insights(canary_name, region)
        except Exception as e:
            telemetry_insights = f'Telemetry API unavailable: {str(e)}'

        if not runs:
            return f'No run history found for {canary_name}'

        # Build analysis header
        result = f'🔍 Comprehensive Failure Analysis for {canary_name}\n'

        # Add telemetry insights if available
        if telemetry_insights and not telemetry_insights.startswith('Telemetry API unavailable'):
            result += f'\n📊 **Service and Canary Telemetry Insights**\n{telemetry_insights}\n\n'
        elif telemetry_insights:
            result += f'\n⚠️ {telemetry_insights}\n\n'

        # Get consecutive failures since last success
        consecutive_failures = []
        last_success_run = None

        for run in runs:
            if run.get('Status', {}).get('State') == RUN_STATES['FAILED']:
                consecutive_failures.append(run)
            elif run.get('Status', {}).get('State') == RUN_STATES['PASSED']:
                last_success_run = run
                break

        if not consecutive_failures:
            result += '✅ Canary is healthy - no failures since last success\n'
            if last_success_run:
                result += f'Last success: {last_success_run.get("Timeline", {}).get("Started")}\n'
            result += '\n🔍 Performing health check analysis ...\n\n'

        # Group failures by StateReason
        failure_causes = {}
        result += f'🔍 Found {len(consecutive_failures)} consecutive failures since last success\n'
        if last_success_run:
            result += f'Last success: {last_success_run.get("Timeline", {}).get("Started")}\n\n'
        else:
            result += 'No recent success run found in history\n\n'

        for failed_run in consecutive_failures:
            state_reason = failed_run.get('Status', {}).get('StateReason', 'Unknown')

            if state_reason not in failure_causes:
                failure_causes[state_reason] = []
            failure_causes[state_reason].append(failed_run)

        # Analysis section
        unique_reasons = list(failure_causes.keys())

        if not unique_reasons:
            result += '✅ No consecutive failures to analyze\n'
            result += '💡 Canary appears to be recovering or healthy\n'
            return result

        if len(unique_reasons) == 1:
            result += f'🎯 All failures have same cause: {unique_reasons[0]}\n'
            selected_reason = unique_reasons[0]
        else:
            result += f'🎯 Multiple failure causes ({len(unique_reasons)} different issues):\n\n'
            for i, reason in enumerate(unique_reasons, 1):
                count = len(failure_causes[reason])
                result += f'{i}. **{reason}** ({count} occurrences)\n'
            result += '\n'
            selected_reason = unique_reasons[0]

        selected_failure = failure_causes[selected_reason][0]
        result += f'Analyzing most recent failure: {selected_failure.get("Id", "")[:8]}...\n\n'

        # Initialize artifact variables
        har_files = []
        screenshots = []
        logs = []
        bucket_name = ''

        # Direct S3 artifact analysis integration
        artifact_location = canary.get('ArtifactS3Location', '')
        artifacts_available = False

        if artifact_location:
            # Handle S3 location format
            if not artifact_location.startswith('s3://'):
                artifact_location = f's3://{artifact_location}' if artifact_location else ''

            if artifact_location.startswith('s3://'):
                bucket_and_path = artifact_location[5:]
                bucket_name = bucket_and_path.split('/')[0]
                base_path = (
                    '/'.join(bucket_and_path.split('/')[1:]) if '/' in bucket_and_path else ''
                )

                # If base_path is empty, construct canary path
                if not base_path:
                    base_path = f'canary/{region}/{canary_name}'

                # Check for failure artifacts using date-based path
                from datetime import datetime

                failure_time = selected_failure.get('Timeline', {}).get('Started')
                if failure_time:
                    # Handle both datetime objects and string timestamps
                    if isinstance(failure_time, str):
                        dt = parse_timestamp(failure_time)
                    else:
                        dt = failure_time  # Already a datetime object
                    date_path = dt.strftime('%Y/%m/%d')
                    failure_run_path = (
                        f'{base_path}/{date_path}/' if base_path else f'{date_path}/'
                    )
                else:
                    # Fallback to today
                    today = datetime.now().strftime('%Y/%m/%d')
                    failure_run_path = f'{base_path}/{today}/' if base_path else f'{today}/'

                try:
                    artifacts_response = s3_client.list_objects_v2(
                        Bucket=bucket_name, Prefix=failure_run_path, MaxKeys=50
                    )
                    failure_artifacts = artifacts_response.get('Contents', [])

                    if failure_artifacts:
                        artifacts_available = True

                        # Categorize artifacts
                        har_files = [
                            a
                            for a in failure_artifacts
                            if a['Key'].lower().endswith(('.har', '.har.gz', '.har.html'))
                        ]
                        screenshots = [
                            a
                            for a in failure_artifacts
                            if any(ext in a['Key'].lower() for ext in ['.png', '.jpg', '.jpeg'])
                        ]
                        logs = [
                            a
                            for a in failure_artifacts
                            if any(ext in a['Key'].lower() for ext in ['.log', '.txt'])
                            or 'log' in a['Key'].lower()
                        ]

                        if last_success_run:
                            result += '🔄 HAR COMPARISON: Failure vs Success\n'
                            result += f'Failure: {selected_failure.get("Id", "")[:8]}... ({selected_failure.get("Timeline", {}).get("Started")})\n'
                            result += f'Success: {last_success_run.get("Id", "")[:8]}... ({last_success_run.get("Timeline", {}).get("Started")})\n\n'

                            # Get success artifacts for comparison
                            success_time = last_success_run.get('Timeline', {}).get('Started')
                            if success_time:
                                if isinstance(success_time, str):
                                    success_dt = parse_timestamp(success_time)
                                else:
                                    success_dt = success_time
                                success_date_path = success_dt.strftime('%Y/%m/%d')
                                success_run_path = (
                                    f'{base_path}/{success_date_path}/'
                                    if base_path
                                    else f'{success_date_path}/'
                                )
                            else:
                                success_run_path = failure_run_path  # Use same path as fallback
                            try:
                                success_artifacts_response = s3_client.list_objects_v2(
                                    Bucket=bucket_name, Prefix=success_run_path, MaxKeys=50
                                )
                                success_artifacts = success_artifacts_response.get('Contents', [])
                                success_har_files = [
                                    a
                                    for a in success_artifacts
                                    if a['Key'].lower().endswith(('.har', '.har.gz', '.har.html'))
                                ]

                                if har_files and success_har_files:
                                    failure_har = await analyze_har_file(
                                        s3_client, bucket_name, har_files, is_failed_run=True
                                    )
                                    success_har = await analyze_har_file(
                                        s3_client,
                                        bucket_name,
                                        success_har_files,
                                        is_failed_run=False,
                                    )

                                    result += f'• Failed requests: {failure_har.get("failed_requests", 0)} vs {success_har.get("failed_requests", 0)}\n'
                                    result += f'• Total requests: {failure_har.get("total_requests", 0)} vs {success_har.get("total_requests", 0)}\n\n'

                                    if failure_har.get('request_details'):
                                        result += '🚨 FAILED REQUESTS:\n'
                                        for req in failure_har['request_details'][:3]:
                                            result += f'• {req.get("url", "Unknown")}: {req.get("status", "Unknown")} ({req.get("time", 0):.1f}ms)\n'
                            except Exception as e:
                                logger.warning(
                                    f'Failed to analyze success artifacts for HAR comparison: {str(e)}'
                                )
                        else:
                            result += (
                                '🔍 FAILURE ANALYSIS (no success run available for comparison):\n'
                            )
                            result += f'Analyzing failure artifacts for: {selected_failure.get("Id", "")[:8]}...\n\n'

                            if har_files:
                                failure_har = await analyze_har_file(
                                    s3_client, bucket_name, har_files, is_failed_run=True
                                )
                                result += '🌐 HAR ANALYSIS:\n'
                                result += (
                                    f'• Failed requests: {failure_har.get("failed_requests", 0)}\n'
                                )
                                result += (
                                    f'• Total requests: {failure_har.get("total_requests", 0)}\n\n'
                                )

                        # Screenshot analysis
                        if screenshots:
                            screenshot_analysis = await analyze_screenshots(
                                s3_client, bucket_name, screenshots, is_failed_run=True
                            )
                            if screenshot_analysis.get('insights'):
                                result += '📸 SCREENSHOT ANALYSIS:\n'
                                for insight in screenshot_analysis['insights'][:3]:
                                    result += f'• {insight}\n'
                                result += '\n'

                        # Log analysis
                        if logs:
                            log_analysis = await analyze_log_files(
                                s3_client, bucket_name, logs, is_failed_run=True
                            )
                            if log_analysis.get('insights'):
                                result += '📋 LOG ANALYSIS:\n'
                                for insight in log_analysis['insights'][:3]:
                                    result += f'• {insight}\n'
                                result += '\n'

                except Exception:
                    artifacts_available = False

        if not artifacts_available:
            # Fallback: CloudWatch Logs analysis
            result += '⚠️ Artifacts not available - Checking CloudWatch Logs for root cause\n'
            result += f'🎯 StateReason: {selected_reason}\n\n'

            failure_time = selected_failure.get('Timeline', {}).get('Started')
            if failure_time:
                log_analysis = await analyze_canary_logs_with_time_window(
                    canary_name, failure_time, canary, window_minutes=5, region=region
                )

                if log_analysis.get('status') == 'success':
                    result += '📋 CLOUDWATCH LOGS ANALYSIS (±5 min around failure):\n'
                    result += f'Time window: {log_analysis["time_window"]}\n'
                    result += f'Log events found: {log_analysis["total_events"]}\n\n'

                    error_logs = log_analysis.get('error_events', [])
                    if error_logs:
                        result += '📋 ERROR LOGS AROUND FAILURE:\n'
                        for error in error_logs:
                            result += f'• {error["timestamp"].strftime("%H:%M:%S")}: {error["message"]}\n'
                else:
                    result += f'📋 {log_analysis.get("insights", ["Log analysis failed"])[0]}\n'
            else:
                result += '📋 No failure timestamp available for targeted log analysis\n'

        # Add critical IAM checking guidance for systematic issues
        if (
            'no test result' in str(selected_reason).lower()
            or 'permission' in str(selected_reason).lower()
            or 'access denied' in str(selected_reason).lower()
        ):
            try:
                result += f"\n🔍 RUNNING COMPREHENSIVE IAM ANALYSIS (common cause of '{selected_reason}'):\n"

                # 1. Check IAM role and policies
                iam_analysis = await analyze_iam_role_and_policies(canary, iam_client, region)

                # Display IAM analysis results
                result += f'IAM Role Analysis Status: {iam_analysis["status"]}\n'
                for check_name, check_result in iam_analysis.get('checks', {}).items():
                    result += f'• {check_name}: {check_result}\n'

                # 2. ENHANCED: Check resource ARN correctness with detailed validation
                result += '\n🔍 CHECKING RESOURCE ARN CORRECTNESS:\n'
                arn_check = check_resource_arns_correct(canary, iam_client)

                if arn_check.get('correct'):
                    result += '✅ Resource ARNs: Correct\n'
                else:
                    result += f'❌ Resource ARNs: {arn_check.get("error", "Issues found")}\n'

                # Combine all IAM issues with enhanced categorization
                all_iam_issues = []
                if iam_analysis.get('issues_found'):
                    all_iam_issues.extend(
                        [f'IAM Policy: {issue}' for issue in iam_analysis['issues_found']]
                    )
                if not arn_check.get('correct') and arn_check.get('issues'):
                    all_iam_issues.extend(
                        [f'Resource ARN: {issue}' for issue in arn_check['issues']]
                    )

                if all_iam_issues:
                    result += f'\n🚨 ALL IAM ISSUES FOUND ({len(all_iam_issues)} total):\n'
                    for issue in all_iam_issues:
                        result += f'• {issue}\n'

                # Enhanced IAM recommendations with priority
                all_iam_recommendations = []
                if iam_analysis.get('recommendations'):
                    all_iam_recommendations.extend(
                        [f'Policy Fix: {rec}' for rec in iam_analysis['recommendations']]
                    )
                if not arn_check.get('correct'):
                    all_iam_recommendations.extend(
                        [
                            'PRIORITY: Review and correct S3 bucket ARN patterns in IAM policies',
                            'PRIORITY: Ensure bucket names match expected patterns (e.g., cw-syn-* for CloudWatch Synthetics)',
                            'Verify canary has access to the correct S3 bucket for artifacts storage',
                            'Check if bucket exists and is in the same region as the canary',
                        ]
                    )

                if all_iam_recommendations:
                    result += (
                        f'\n💡 ALL IAM RECOMMENDATIONS ({len(all_iam_recommendations)} total):\n'
                    )
                    for rec in all_iam_recommendations:
                        result += f'• {rec}\n'

            except Exception as iam_error:
                result += f'⚠️ IAM analysis failed: {str(iam_error)[:200]}\n\n'

        # History-based diagnosis for specific error patterns
        error_recommendations = []

        # 1. ENOSPC: no space left on device
        if any(
            re.search(pattern, selected_reason, re.IGNORECASE)
            for pattern in ['enospc', 'no space left on device']
        ):
            try:
                telemetry_data = await extract_disk_memory_usage_metrics(canary_name, region)
                if 'error' not in telemetry_data:
                    result += '\n🔍 DISK USAGE ROOT CAUSE ANALYSIS:\n'
                    result += f'• Storage: {telemetry_data.get("maxEphemeralStorageUsageInMb", 0):.1f} MB peak\n'
                    result += f'• Usage: {telemetry_data.get("maxEphemeralStorageUsagePercent", 0):.1f}% peak\n'
                else:
                    result += f'\n🔍 DISK USAGE ROOT CAUSE ANALYSIS:\n{telemetry_data["error"]}\n'
            except Exception as debug_error:
                result += f'\n⚠️ Could not generate disk usage debugging code: {str(debug_error)}\n'

        # 2. Protocol error (Target.activateTarget): Session closed / detached Frame
        elif any(
            re.search(pattern, selected_reason, re.IGNORECASE)
            for pattern in [
                'protocol error',
                'target.activatetarget',
                'session closed',
                'detached frame',
                'session already detached',
            ]
        ):
            try:
                telemetry_data = await extract_disk_memory_usage_metrics(canary_name, region)
                if 'error' not in telemetry_data:
                    result += '\n🔍 MEMORY USAGE ROOT CAUSE ANALYSIS:\n'
                    result += f'• Memory: {telemetry_data.get("maxSyntheticsMemoryUsageInMB", 0):.1f} MB peak\n'
                else:
                    result += (
                        f'\n🔍 MEMORY USAGE ROOT CAUSE ANALYSIS:\n{telemetry_data["error"]}\n'
                    )
            except Exception as debug_error:
                result += f'\n⚠️ Could not collect memory usage metrics: {str(debug_error)}\n'

        # 3. Navigation timed out / Page.captureScreenshot timed out
        elif any(
            re.search(pattern, selected_reason, re.IGNORECASE)
            for pattern in [
                'navigation timeout',
                'navigation timed out',
                'ms exceeded',
                'page.capturescreenshot timed out',
                'protocoltimeout',
                'connection timed out',
            ]
        ):
            # Navigation timeout specific analysis using existing HAR data
            if har_files and bucket_name:
                try:
                    har_timeout_analysis = await analyze_har_file(
                        s3_client, bucket_name, har_files, is_failed_run=True
                    )

                    result += '\n🔍 HAR FILE ANALYSIS FOR NAVIGATION TIMEOUT:\n'
                    if har_timeout_analysis.get('failed_requests', 0) > 0:
                        result += (
                            f'• Failed HTTP requests: {har_timeout_analysis["failed_requests"]}\n'
                        )

                    if har_timeout_analysis.get('insights'):
                        for insight in har_timeout_analysis['insights'][:5]:
                            result += f'• {insight}\n'

                    # Additional timeout-specific analysis
                    result += f'• Total requests analyzed: {har_timeout_analysis.get("total_requests", 0)}\n'
                    result += (
                        f'• Analysis status: {har_timeout_analysis.get("status", "unknown")}\n'
                    )
                    result += '\n'
                except Exception as har_error:
                    result += f'\n⚠️ HAR analysis failed: {str(har_error)[:100]}\n'
            else:
                result += '\n🔍 NAVIGATION TIMEOUT DETECTED:\n'
                result += '• No HAR files available for detailed analysis\n'
                result += '• Timeout suggests page loading issues or UI changes\n'
                result += '• Check if target elements exist and page loads completely\n\n'

        # 4. Visual variation
        elif re.search('visual variation', selected_reason, re.IGNORECASE):
            error_recommendations.extend(
                [
                    '🔧 VISUAL MONITORING ISSUE DETECTED:',
                    '• Website UI changed - not a technical failure',
                    '• Check if website legitimately updated (ads, banners, content)',
                    '• Update visual baseline with new reference screenshots',
                    '• Adjust visual difference threshold (increase from default)',
                    '• Consider excluding dynamic content areas from comparison',
                ]
            )

        if error_recommendations:
            result += '\n💡 PATTERN-BASED RECOMMENDATIONS:\n'
            for rec in error_recommendations:
                result += f'{rec}\n'
            result += '\n'

        # Add canary code if available
        try:
            code_analysis = await get_canary_code(canary, region)
            if 'error' not in code_analysis and code_analysis.get('code_content'):
                result += f'\ncanary code:\n{code_analysis["code_content"]}\n'
        except Exception as e:
            result += f'Note: Could not retrieve canary code: {str(e)}\n'

        result += '\n'
        return result

    except Exception as e:
        return f'❌ Error in comprehensive failure analysis: {str(e)}'


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
mcp.tool()(analyze_canary_failures)

# Register batch processing tools
mcp.tool()(continue_audit_batch)
mcp.tool()(cleanup_audit_sessions)


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
