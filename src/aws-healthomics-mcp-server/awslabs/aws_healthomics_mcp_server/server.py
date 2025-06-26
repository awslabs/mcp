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

from awslabs.aws_healthomics_mcp_server.tools.helper_tools import (
    get_supported_regions,
    package_workflow,
)
from awslabs.aws_healthomics_mcp_server.tools.run_analysis import analyze_run_performance
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
from awslabs.aws_healthomics_mcp_server.tools.workflow_management import (
    create_workflow,
    create_workflow_version,
    get_workflow,
    list_workflow_versions,
    list_workflows,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    'awslabs.aws-healthomics-mcp-server',
    instructions="""
# AWS HealthOmics MCP Server

This MCP server provides tools for creating, managing, and analyzing genomic workflows using AWS HealthOmics. It enables AI assistants to help users with workflow creation, execution, monitoring, and troubleshooting.

## Available Tools

### Workflow Management
- **ListWorkflows**: List available HealthOmics workflows
- **CreateWorkflow**: Create a new HealthOmics workflow
- **GetWorkflow**: Get details about a specific workflow
- **CreateWorkflowVersion**: Create a new version of an existing workflow
- **ListWorkflowVersions**: List versions of a workflow

### Workflow Execution
- **StartRun**: Start a workflow run
- **ListRuns**: List workflow runs
- **GetRun**: Get details about a specific run
- **ListRunTasks**: List tasks for a specific run
- **GetRunTask**: Get details about a specific task

### Workflow Analysis
- **GetRunLogs**: Retrieve high-level run logs showing workflow execution events
- **GetRunManifestLogs**: Retrieve run manifest logs with workflow summary
- **GetRunEngineLogs**: Retrieve engine logs containing STDOUT and STDERR
- **GetTaskLogs**: Retrieve logs for specific workflow tasks
- **AnalyzeRunPerformance**: Analyze workflow run performance and resource utilization to provide optimization recommendations

### Troubleshooting
- **DiagnoseRunFailure**: Diagnose a failed workflow run

### Helper Tools
- **PackageWorkflow**: Package workflow definition files into a base64-encoded ZIP
- **GetSupportedRegions**: Get the list of AWS regions where HealthOmics is available

## Service Availability
AWS HealthOmics is available in select AWS regions. Use the GetSupportedRegions tool to get the current list of supported regions.
""",
    dependencies=[
        'boto3',
        'pydantic',
        'loguru',
    ],
)

# Register workflow management tools
mcp.tool(name='ListWorkflows')(list_workflows)
mcp.tool(name='CreateWorkflow')(create_workflow)
mcp.tool(name='GetWorkflow')(get_workflow)
mcp.tool(name='CreateWorkflowVersion')(create_workflow_version)
mcp.tool(name='ListWorkflowVersions')(list_workflow_versions)

# Register workflow execution tools
mcp.tool(name='StartRun')(start_run)
mcp.tool(name='ListRuns')(list_runs)
mcp.tool(name='GetRun')(get_run)
mcp.tool(name='ListRunTasks')(list_run_tasks)
mcp.tool(name='GetRunTask')(get_run_task)

# Register workflow analysis tools
mcp.tool(name='GetRunLogs')(get_run_logs)
mcp.tool(name='GetRunManifestLogs')(get_run_manifest_logs)
mcp.tool(name='GetRunEngineLogs')(get_run_engine_logs)
mcp.tool(name='GetTaskLogs')(get_task_logs)
mcp.tool(name='AnalyzeRunPerformance')(analyze_run_performance)

# Register troubleshooting tools
mcp.tool(name='DiagnoseRunFailure')(diagnose_run_failure)

# Register helper tools
mcp.tool(name='PackageWorkflow')(package_workflow)
mcp.tool(name='GetSupportedRegions')(get_supported_regions)


def main():
    """Run the MCP server with CLI argument support."""
    logger.info('AWS HealthOmics MCP server starting')

    mcp.run()


if __name__ == '__main__':
    main()
