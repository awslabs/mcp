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

"""awslabs SSM for SAP MCP Server implementation."""

from awslabs.aws_for_sap_management_mcp_server.ssm_sap_applications.tools import (
    SSMSAPApplicationTools,
)
from awslabs.aws_for_sap_management_mcp_server.ssm_sap_config_checks.tools import (
    SSMSAPConfigCheckTools,
)
from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
    SSMSAPHealthTools,
)
from awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools import (
    SSMSAPSchedulingTools,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    'awslabs.aws-for-sap-management-mcp-server',
    instructions="""Use this MCP server to manage SAP applications registered with
AWS Systems Manager for SAP. Supports listing and inspecting SAP applications,
running and reviewing configuration checks, scheduling recurring operations
(configuration checks, start/stop) via Amazon EventBridge Scheduler,
and generating comprehensive health summary reports.
All tools support multi-region and multi-profile AWS access.

## Presenting Health Summary Results

When presenting results from get_sap_health_summary, follow these guidelines
to make the output understandable for SAP administrators:

### System Overview
- Describe the application in SAP terms: type (HANA, SAP_ABAP), HA pattern
  (e.g., "2-node High Availability Scale-Up"), HANA version, OS, instance type.
- Show HSR replication mode, operation mode, and AZ placement.
- List databases (SYSTEMDB, tenant DBs) from the HANA component.
- Do NOT expose internal SSM-SAP status codes like "ACTIVATED" or "SUCCESS"
  without explanation. These mean nothing to SAP administrators.
- When the application is healthy (ACTIVATED + SUCCESS discovery), do NOT
  show a status line at all — skip straight to the useful information
  (system overview, components, findings). The user asked about the app,
  they don't need a green badge confirming it exists.
- Only call out application status when something is WRONG. Translate to
  human-readable descriptions:
  - STOPPED/STOPPING = "Application is stopped / shutting down"
  - FAILED = "Application is in a failed state — investigate immediately"
  - REFRESH_FAILED = "Application discovery refresh failed — component info may be stale"
  - REGISTRATION_FAILED = "Application registration did not complete successfully"
  - UNKNOWN = "Application status could not be determined"

### Components
- Do NOT show the raw SSM-SAP component hierarchy (HANA parent + HANA_NODE children).
  This is confusing — customers don't understand why there's a component without
  an EC2 instance that says "RUNNING".
- Instead, present only the actual HANA nodes (the ones with EC2 instances).
  Show each node with: hostname, role (Primary / Secondary with replication mode),
  status, cluster status, and EC2 instance ID.
- Extract the hostname from the component ID (e.g., HDB-HDB00-sappridb → sappridb).
- Show HANA version and databases (SYSTEMDB, tenant DBs) in the system overview,
  not repeated per node.

### CloudWatch Metrics
- Present CPU (avg/max), memory %, disk %, and status check in a table.
- Flag any concerning values (e.g., memory > 90%, disk > 80%).
- If a metric value is null, say "Not available" or omit it — never display "null".

### Backup & Log Backup Status
- ALWAYS include both backup_status AND log_backup_status from the response.
- Show AWS Backup status with last backup time and type (e.g., CONTINUOUS).
- Show log backup check status per instance, including SSM agent status and version.
- If log_backup_details contains JSON with a "payload" array of backup entries,
  present ALL entries in a table (backupId, status, startTime, destination, size)
  rather than summarizing with "e.g." or picking one example.
- If log_backup_status is null, say "No log backup check history" rather than omitting it.

### Filesystem Usage
- Present filesystem usage from the filesystem_usage field in a readable table.
- Flag any filesystem at >80% usage as needing attention.

### Configuration Checks
- Do NOT present checks as "SAP_CHECK_01", "SAP_CHECK_02", "SAP_CHECK_03".
  These IDs are internal. Instead, use the check's purpose:
  - SAP_CHECK_01 = "EC2 Instance Type Selection"
  - SAP_CHECK_02 = "Storage Configuration"
  - SAP_CHECK_03 = "Pacemaker HA Configuration"
- Do NOT show the check operation status (SUCCESS/FAILED). This is confusing
  because "SUCCESS" means the check ran successfully, not that everything passed.
  Just show the findings.
- Group results by sub-check name (e.g., "SAP Certified EC2 Instance Types",
  "Pacemaker Cluster Bootstrap Configuration").
- For each sub-check, summarize the key findings from its rule_results:
  - Use status icons: 🔴 FAILED, ⚠️ WARNING, ✅ PASSED, 🔵 INFO
  - Show the rule description and message for FAILED and WARNING rules.
  - For PASSED rules, summarize briefly (e.g., "All 12 passed").
  - Include actual vs expected values for failed rules when available.
- Do NOT just show aggregate counts like "Failed: 4, Warning: 8, Passed: 24".
  These are not actionable. Show what specifically failed and why.

### Remediation Guidance
- For EVERY failed or warning rule result, provide actionable remediation steps.
  The raw report data shows what's wrong — your job is to tell the customer HOW to fix it.
- Structure remediation as a prioritized list, grouped by severity (failures first,
  then warnings).
- For each finding, include:
  - What the issue is (from the rule description and message)
  - Why it matters (impact on the SAP system)
  - How to fix it (specific commands, configuration changes, or AWS console steps)
  - Link to relevant documentation when available (from the rule message or metadata)
- When the rule message already contains a documentation link, include it in the
  remediation. When it doesn't, use your knowledge of SAP on AWS best practices
  to suggest the right fix.
- Examples of good remediation:
  - "EBS encryption not enabled → Create encrypted copies of the volumes and swap them.
    See [EBS encryption docs](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-encryption.html)"
  - "STONITH timeout is 150 (should be 600) → Run: `crm configure property stonith-timeout=600`"
  - "Kernel tainted on primary → Check `cat /proc/sys/kernel/tainted` to identify the
    taint source. Review SAP Note 784391."
- Group remediation at the end of the report as a "Recommended Actions" section,
  or inline with each finding — whichever the user prefers.

### Scheduling Results
- When presenting schedule creation results, confirm the schedule name,
  expression, and target application.
- When listing schedules, show operation type (Start/Stop/Config Checks),
  expression, state (enabled/disabled), and timezone.
""",
    dependencies=[
        'pydantic',
        'loguru',
        'boto3',
    ],
)

# Initialize and register tool modules
try:
    application_tools = SSMSAPApplicationTools()
    application_tools.register(mcp)
    logger.info('SSM SAP Application tools registered successfully')

    config_check_tools = SSMSAPConfigCheckTools()
    config_check_tools.register(mcp)
    logger.info('SSM SAP Configuration Check tools registered successfully')

    scheduling_tools = SSMSAPSchedulingTools()
    scheduling_tools.register(mcp)
    logger.info('SSM SAP Scheduling tools registered successfully')

    health_tools = SSMSAPHealthTools()
    health_tools.register(mcp)
    logger.info('SSM SAP Health Summary tools registered successfully')
except Exception as e:
    logger.error(f'Error initializing SSM SAP tools: {str(e)}')
    raise


def main():
    """Run the MCP server."""
    logger.info('SSM for SAP MCP server started')
    mcp.run()


if __name__ == '__main__':
    main()
