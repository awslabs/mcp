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
# Data store tools
from awslabs.aws_healthomics_mcp_server.tools.sequence_store_tools import (
    get_aho_read_set,
    get_aho_read_set_import_job,
    list_aho_read_set_import_jobs,
    list_aho_read_sets,
    list_aho_sequence_stores,
    start_aho_read_set_import_job,
)
from awslabs.aws_healthomics_mcp_server.tools.variant_store_tools import (
    count_aho_variants,
    get_aho_variant_import_job,
    get_aho_variant_store,
    list_aho_variant_stores,
    search_aho_variants,
    start_aho_variant_import_job,
)
from awslabs.aws_healthomics_mcp_server.tools.reference_store_tools import (
    get_aho_reference,
    get_aho_reference_import_job,
    get_aho_reference_store,
    list_aho_reference_stores,
    list_aho_references,
    start_aho_reference_import_job,
)
from awslabs.aws_healthomics_mcp_server.tools.annotation_store_tools import (
    get_aho_annotation_import_job,
    get_aho_annotation_store,
    list_aho_annotation_stores,
    search_aho_annotations,
    start_aho_annotation_import_job,
)
from awslabs.aws_healthomics_mcp_server.tools.data_import_tools import (
    discover_aho_genomic_files,
    get_aho_s3_file_metadata,
    list_aho_s3_bucket_contents,
    prepare_aho_import_sources,
    validate_aho_s3_uri_format,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    'awslabs.aws-healthomics-mcp-server',
    instructions="""
# AWS HealthOmics MCP Server

This MCP server provides comprehensive tools for managing AWS HealthOmics workflows and data stores. It enables AI assistants to help users with workflow creation, execution, monitoring, data management, and genomic analysis.

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

### Workflow Linting
- **LintAHOWorkflowDefinition**: Lint single WDL or CWL workflow files using miniwdl and cwltool
- **LintAHOWorkflowBundle**: Lint multi-file WDL or CWL workflow bundles with import/dependency support

### Sequence Store Operations
- **ListAHOSequenceStores**: List available sequence stores
- **ListAHOReadSets**: List read sets in a sequence store with optional filtering
- **GetAHOReadSet**: Get detailed metadata for a specific read set
- **StartAHOReadSetImportJob**: Start importing read sets from S3 to a sequence store
- **GetAHOReadSetImportJob**: Get status and details of a read set import job
- **ListAHOReadSetImportJobs**: List read set import jobs for a sequence store

### Variant Store Operations
- **ListAHOVariantStores**: List available variant stores
- **GetAHOVariantStore**: Get detailed information about a variant store
- **SearchAHOVariants**: Search for variants by gene, position, type, etc.
- **CountAHOVariants**: Count variants matching specific criteria
- **StartAHOVariantImportJob**: Start importing variants from VCF files to a variant store
- **GetAHOVariantImportJob**: Get status and details of a variant import job

### Reference Store Operations
- **ListAHOReferenceStores**: List available reference stores
- **GetAHOReferenceStore**: Get detailed information about a reference store
- **ListAHOReferences**: List reference genomes in a reference store
- **GetAHOReference**: Get detailed metadata for a specific reference
- **StartAHOReferenceImportJob**: Start importing reference genomes from S3
- **GetAHOReferenceImportJob**: Get status and details of a reference import job

### Annotation Store Operations
- **ListAHOAnnotationStores**: List available annotation stores
- **GetAHOAnnotationStore**: Get detailed information about an annotation store
- **SearchAHOAnnotations**: Search for annotations by gene, position, type, etc.
- **StartAHOAnnotationImportJob**: Start importing annotations from files
- **GetAHOAnnotationImportJob**: Get status and details of an annotation import job

### Data Import and S3 Integration
- **ValidateAHOS3UriFormat**: Validate S3 URI format and syntax
- **DiscoverAHOGenomicFiles**: Auto-discover genomic files in S3 locations
- **ListAHOS3BucketContents**: Browse S3 bucket contents with optional filtering
- **GetAHOS3FileMetadata**: Get metadata for specific S3 files
- **PrepareAHOImportSources**: Prepare source file configurations for import operations

### Helper Tools
- **PackageAHOWorkflow**: Package workflow definition files into a base64-encoded ZIP
- **GetAHOSupportedRegions**: Get the list of AWS regions where HealthOmics is available

## Usage Patterns

### Complete Genomic Analysis Workflow
1. Use S3 tools to discover and validate genomic files
2. Import data using sequence/variant/reference store import tools
3. Create and execute workflows using workflow management tools
4. Analyze results using variant search and annotation tools
5. Monitor and troubleshoot using analysis and diagnostic tools

### Data Management
- Organize genomic data across sequence, variant, reference, and annotation stores
- Import data from S3 with automatic file discovery and validation
- Search and retrieve specific genomic data for analysis

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

# Register workflow analysis tools
mcp.tool(name='GetAHORunLogs')(get_run_logs)
mcp.tool(name='GetAHORunManifestLogs')(get_run_manifest_logs)
mcp.tool(name='GetAHORunEngineLogs')(get_run_engine_logs)
mcp.tool(name='GetAHOTaskLogs')(get_task_logs)
mcp.tool(name='AnalyzeAHORunPerformance')(analyze_run_performance)

# Register troubleshooting tools
mcp.tool(name='DiagnoseAHORunFailure')(diagnose_run_failure)

# Register workflow linting tools
mcp.tool(name='LintAHOWorkflowDefinition')(lint_workflow_definition)
mcp.tool(name='LintAHOWorkflowBundle')(lint_workflow_bundle)

# Register helper tools
mcp.tool(name='PackageAHOWorkflow')(package_workflow)
mcp.tool(name='GetAHOSupportedRegions')(get_supported_regions)

# Register sequence store tools
mcp.tool(name='ListAHOSequenceStores')(list_aho_sequence_stores)
mcp.tool(name='ListAHOReadSets')(list_aho_read_sets)
mcp.tool(name='GetAHOReadSet')(get_aho_read_set)
mcp.tool(name='StartAHOReadSetImportJob')(start_aho_read_set_import_job)
mcp.tool(name='GetAHOReadSetImportJob')(get_aho_read_set_import_job)
mcp.tool(name='ListAHOReadSetImportJobs')(list_aho_read_set_import_jobs)

# Register variant store tools
mcp.tool(name='ListAHOVariantStores')(list_aho_variant_stores)
mcp.tool(name='GetAHOVariantStore')(get_aho_variant_store)
mcp.tool(name='SearchAHOVariants')(search_aho_variants)
mcp.tool(name='CountAHOVariants')(count_aho_variants)
mcp.tool(name='StartAHOVariantImportJob')(start_aho_variant_import_job)
mcp.tool(name='GetAHOVariantImportJob')(get_aho_variant_import_job)

# Register reference store tools
mcp.tool(name='ListAHOReferenceStores')(list_aho_reference_stores)
mcp.tool(name='GetAHOReferenceStore')(get_aho_reference_store)
mcp.tool(name='ListAHOReferences')(list_aho_references)
mcp.tool(name='GetAHOReference')(get_aho_reference)
mcp.tool(name='StartAHOReferenceImportJob')(start_aho_reference_import_job)
mcp.tool(name='GetAHOReferenceImportJob')(get_aho_reference_import_job)

# Register annotation store tools
mcp.tool(name='ListAHOAnnotationStores')(list_aho_annotation_stores)
mcp.tool(name='GetAHOAnnotationStore')(get_aho_annotation_store)
mcp.tool(name='SearchAHOAnnotations')(search_aho_annotations)
mcp.tool(name='StartAHOAnnotationImportJob')(start_aho_annotation_import_job)
mcp.tool(name='GetAHOAnnotationImportJob')(get_aho_annotation_import_job)

# Register data import tools
mcp.tool(name='ValidateAHOS3UriFormat')(validate_aho_s3_uri_format)
mcp.tool(name='DiscoverAHOGenomicFiles')(discover_aho_genomic_files)
mcp.tool(name='ListAHOS3BucketContents')(list_aho_s3_bucket_contents)
mcp.tool(name='GetAHOS3FileMetadata')(get_aho_s3_file_metadata)
mcp.tool(name='PrepareAHOImportSources')(prepare_aho_import_sources)


def main():
    """Run the MCP server with CLI argument support."""
    logger.info('AWS HealthOmics MCP server starting')

    mcp.run()


if __name__ == '__main__':
    main()
