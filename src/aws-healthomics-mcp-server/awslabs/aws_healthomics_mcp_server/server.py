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

### Workflow Analysis
- **GetAHORunLogs**: Retrieve high-level run logs showing workflow execution events
- **GetAHORunManifestLogs**: Retrieve run manifest logs with workflow summary
- **GetAHORunEngineLogs**: Retrieve engine logs containing STDOUT and STDERR
- **GetAHOTaskLogs**: Retrieve logs for specific workflow tasks
- **AnalyzeAHORunPerformance**: Analyze workflow run performance and resource utilization to provide optimization recommendations

### Troubleshooting
- **DiagnoseAHORunFailure**: Diagnose a failed workflow run

### Helper Tools
- **PackageAHOWorkflow**: Package workflow definition files into a base64-encoded ZIP
- **GetAHOSupportedRegions**: Get the list of AWS regions where HealthOmics is available

## Service Availability
AWS HealthOmics is available in select AWS regions. Use the GetAHOSupportedRegions tool to get the current list of supported regions.
""",
    dependencies=[
        'boto3',
        'pydantic',
        'loguru',
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

# Register workflow analysis tools
mcp.tool(name='GetAHORunLogs')(get_run_logs)
mcp.tool(name='GetAHORunManifestLogs')(get_run_manifest_logs)
mcp.tool(name='GetAHORunEngineLogs')(get_run_engine_logs)
mcp.tool(name='GetAHOTaskLogs')(get_task_logs)
mcp.tool(name='AnalyzeAHORunPerformance')(analyze_run_performance)

# Register troubleshooting tools
mcp.tool(name='DiagnoseAHORunFailure')(diagnose_run_failure)

# Register helper tools
mcp.tool(name='PackageAHOWorkflow')(package_workflow)
mcp.tool(name='GetAHOSupportedRegions')(get_supported_regions)


def main():
    """Run the MCP server with CLI argument support."""
    logger.info('AWS HealthOmics MCP server starting')

    mcp.run()


if __name__ == '__main__':
    main()
