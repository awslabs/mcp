# AWS HealthOmics MCP Server

A Model Context Protocol (MCP) server that provides AI assistants with comprehensive access to AWS HealthOmics services for genomic workflow management, execution, and analysis.

## Overview

AWS HealthOmics is a purpose-built service for storing, querying, and analyzing genomic, transcriptomic, and other omics data. This MCP server enables AI assistants to interact with HealthOmics workflows through natural language, making genomic data analysis more accessible and efficient.

## Key Capabilities

This MCP server provides tools for:

### 🧬 Workflow Management
- **Create and validate workflows**: Support for WDL, CWL, and Nextflow workflow languages
- **Lint workflow definitions**: Validate WDL and CWL workflows using industry-standard linting tools
- **Version management**: Create and manage workflow versions with different configurations
- **Package workflows**: Bundle workflow definitions into deployable packages

### 🚀 Workflow Execution
- **Start and monitor runs**: Execute workflows with custom parameters and monitor progress
- **Task management**: Track individual workflow tasks and their execution status
- **Resource configuration**: Configure compute resources, storage, and caching options

### 📊 Analysis and Troubleshooting
- **Performance analysis**: Analyze workflow execution performance and resource utilization
- **Failure diagnosis**: Comprehensive troubleshooting tools for failed workflow runs
- **Log access**: Retrieve detailed logs from runs, engines, tasks, and manifests

### 🔍 File Discovery and Search
- **Genomics file search**: Intelligent discovery of genomics files across S3 buckets, HealthOmics sequence stores, and reference stores
- **Pattern matching**: Advanced search with fuzzy matching against file paths and object tags
- **File associations**: Automatic detection and grouping of related files (BAM/BAI indexes, FASTQ pairs, FASTA indexes)
- **Relevance scoring**: Smart ranking of search results based on match quality and file relationships

### 🌍 Region Management
- **Multi-region support**: Get information about AWS regions where HealthOmics is available

## Available Tools

### Workflow Management Tools

1. **ListAHOWorkflows** - List available HealthOmics workflows with pagination support
2. **CreateAHOWorkflow** - Create new workflows with WDL, CWL, or Nextflow definitions from local ZIP files, S3 URIs, or base64-encoded content, with optional container registry mappings
3. **GetAHOWorkflow** - Retrieve detailed workflow information and export definitions
4. **CreateAHOWorkflowVersion** - Create new versions of existing workflows from local ZIP files, S3 URIs, or base64-encoded content, with optional container registry mappings
5. **ListAHOWorkflowVersions** - List all versions of a specific workflow
6. **LintAHOWorkflowDefinition** - Lint single WDL or CWL workflow files using miniwdl and cwltool, accepting local file paths, S3 URIs, or inline content
7. **LintAHOWorkflowBundle** - Lint multi-file WDL or CWL workflow bundles with import/dependency support, accepting local directories, ZIP files, S3 prefixes, or inline dictionaries
8. **PackageAHOWorkflow** - Package workflow files into base64-encoded ZIP format, accepting local file paths, S3 URIs, or inline content

### Workflow Execution Tools

1. **StartAHORun** - Start workflow runs with custom parameters, resource configuration, and optional VPC networking mode with a named configuration
2. **ListAHORuns** - List workflow runs with filtering by status and date ranges
3. **GetAHORun** - Retrieve detailed run information including status and metadata
4. **ListAHORunTasks** - List tasks for specific runs with status filtering
5. **GetAHORunTask** - Get detailed information about specific workflow tasks

### Analysis and Troubleshooting Tools

1. **AnalyzeAHORunPerformance** - Analyze workflow run performance and resource utilization
2. **DiagnoseAHORunFailure** - Comprehensive diagnosis of failed workflow runs with remediation suggestions
3. **GetAHORunLogs** - Access high-level workflow execution logs and events
4. **GetAHORunEngineLogs** - Retrieve workflow engine logs (STDOUT/STDERR) for debugging
5. **GetAHORunManifestLogs** - Access run manifest logs with runtime information and metrics
6. **GetAHOTaskLogs** - Get task-specific logs for debugging individual workflow steps

### File Discovery Tools

1. **SearchGenomicsFiles** - Intelligent search for genomics files across S3 buckets, HealthOmics sequence stores, and reference stores with pattern matching, file association detection, and relevance scoring

### Run Group Management Tools

1. **CreateAHORunGroup** - Create a new run group with optional resource limits (maxCpus, maxGpus, maxDuration, maxRuns) and tags
2. **GetAHORunGroup** - Retrieve detailed information about a specific run group
3. **ListAHORunGroups** - List available run groups with optional name filtering and pagination
4. **UpdateAHORunGroup** - Update an existing run group's name or resource limits

### Run Cache Management Tools

1. **CreateAHORunCache** - Create a new run cache with a cache behavior (CACHE_ALWAYS or CACHE_ON_FAILURE), S3 URI for cache storage, and optional name, description, tags, and cross-account bucket owner ID
2. **GetAHORunCache** - Retrieve detailed information about a specific run cache including configuration, status, and metadata
3. **ListAHORunCaches** - List available run caches with optional filtering by name, status, or cache behavior, with pagination support
4. **UpdateAHORunCache** - Update an existing run cache's cache behavior, name, or description

### Sequence Store Management Tools

1. **CreateAHOSequenceStore** - Create a new sequence store with optional encryption, description, fallback location, and tags
2. **ListAHOSequenceStores** - List sequence stores with optional name filtering and pagination
3. **GetAHOSequenceStore** - Get detailed information about a specific sequence store
4. **UpdateAHOSequenceStore** - Update a sequence store's name, description, or fallback location (manages ETags internally)
5. **ListAHOReadSets** - List read sets in a sequence store with filtering by sample ID, subject ID, reference ARN, status, file type, and date range
6. **GetAHOReadSetMetadata** - Get detailed metadata for a specific read set including sequence information and file details
7. **StartAHOReadSetImportJob** - Import genomic files from S3 into a sequence store with batch support
8. **GetAHOReadSetImportJob** - Get status and details of a read set import job including per-source statuses
9. **ListAHOReadSetImportJobs** - List import jobs for a sequence store with pagination
10. **StartAHOReadSetExportJob** - Export read sets from a sequence store to S3 with batch support
11. **GetAHOReadSetExportJob** - Get status and details of a read set export job
12. **ListAHOReadSetExportJobs** - List export jobs for a sequence store with pagination
13. **ActivateAHOReadSets** - Activate archived read sets for analysis access

### Reference Store Management Tools

1. **ListAHOReferenceStores** - List reference stores with optional name filtering and pagination
2. **GetAHOReferenceStore** - Get detailed information about a specific reference store
3. **ListAHOReferences** - List references in a reference store with optional name and status filtering
4. **GetAHOReferenceMetadata** - Get detailed metadata for a specific reference including file information
5. **StartAHOReferenceImportJob** - Import reference files from S3 into a reference store with batch support
6. **GetAHOReferenceImportJob** - Get status and details of a reference import job including per-source statuses
7. **ListAHOReferenceImportJobs** - List import jobs for a reference store with pagination

### Configuration Management Tools

1. **CreateAHOConfiguration** - Create a new HealthOmics configuration for workflow runs with optional run settings, description, and tags
2. **GetAHOConfiguration** - Get detailed information about a specific configuration including run settings and status
3. **ListAHOConfigurations** - List available configurations with pagination support
4. **DeleteAHOConfiguration** - Delete a configuration

### Region Management Tools

1. **GetAHOSupportedRegions** - List AWS regions where HealthOmics is available

## Instructions for AI Assistants

This MCP server enables AI assistants like Kiro, Cline, Cursor, and Windsurf to help users with AWS HealthOmics genomic workflow management. Here's how to effectively use these tools:

### Understanding AWS HealthOmics

AWS HealthOmics is designed for genomic data analysis workflows. Key concepts:

- **Workflows**: Computational pipelines written in WDL, CWL, or Nextflow that process genomic data
- **Runs**: Executions of workflows with specific input parameters and data
- **Tasks**: Individual steps within a workflow run
- **Storage Types**: STATIC (fixed storage) or DYNAMIC (auto-scaling storage)

### Workflow Management Best Practices

1. **Creating Workflows**:
   - **From local files**: Use `PackageAHOWorkflow` to bundle workflow files, then use the base64-encoded ZIP with `CreateAHOWorkflow`
   - **From S3**: Store your workflow definition ZIP file in S3 and reference it using the `definition_uri` parameter
   - Validate workflows with appropriate language syntax (WDL, CWL, Nextflow)
   - Include parameter templates to guide users on required inputs
   - Choose the appropriate method based on your workflow storage preferences

2. **S3 URI Support**:
   - Both `CreateAHOWorkflow` and `CreateAHOWorkflowVersion` support S3 URIs as an alternative to base64-encoded ZIP files
   - **Benefits of S3 URIs**:
     - Better for large workflow definitions (no base64 encoding overhead)
     - Easier integration with CI/CD pipelines that store artifacts in S3
     - Reduced memory usage during workflow creation
     - Direct reference to existing S3-stored workflow definitions
   - **Requirements**:
     - S3 URI must start with `s3://`
     - The S3 bucket must be in the same region as the HealthOmics service
     - Appropriate S3 permissions must be configured for the HealthOmics service
   - **Usage**: Specify either `definition_source` (local ZIP path, S3 URI, or base64 content) OR `definition_uri`, but not both. The legacy `definition_zip_base64` parameter is still accepted as a deprecated alias.

3. **Version Management**:
   - Create new versions for workflow updates rather than modifying existing ones
   - Use descriptive version names that indicate changes or improvements
   - List versions to help users choose the appropriate one
   - Both base64 ZIP and S3 URI methods are supported for version creation

### Workflow Execution Guidance

1. **Starting Runs**:
   - Always specify required parameters: workflow_id, role_arn, name, output_uri
   - Choose appropriate storage type (DYNAMIC recommended for most cases)
   - Use meaningful run names for easy identification
   - Configure caching when appropriate to save costs and time

2. **Monitoring Runs**:
   - Use `ListAHORuns` with status filters to track active workflows
   - Check individual run details with `GetAHORun` for comprehensive status
   - Monitor tasks with `ListAHORunTasks` to identify bottlenecks

### Troubleshooting Failed Runs

When workflows fail, follow this diagnostic approach:

1. **Start with DiagnoseAHORunFailure**: This comprehensive tool provides:
   - Failure reasons and error analysis
   - Failed task identification
   - Log summaries and recommendations
   - Actionable troubleshooting steps

2. **Access Specific Logs**:
   - **Run Logs**: High-level workflow events and status changes
   - **Engine Logs**: Workflow engine STDOUT/STDERR for system-level issues
   - **Task Logs**: Individual task execution details for specific failures
   - **Manifest Logs**: Resource utilization and workflow summary information

3. **Performance Analysis**:
   - Use `AnalyzeAHORunPerformance` to identify resource bottlenecks
   - Review task resource utilization patterns
   - Optimize workflow parameters based on analysis results

### Workflow Linting and Validation

The MCP server includes built-in workflow linting capabilities for validating WDL and CWL workflows before deployment:

1. **Lint Workflow Definitions**:
   - **Single files**: Use `LintAHOWorkflowDefinition` for individual workflow files
   - **Multi-file bundles**: Use `LintAHOWorkflowBundle` for workflows with imports and dependencies
   - **Syntax errors**: Catch parsing issues before deployment
   - **Missing components**: Identify missing inputs, outputs, or steps
   - **Runtime requirements**: Ensure tasks have proper runtime specifications
   - **Import resolution**: Validate imports and dependencies between files
   - **Best practices**: Get warnings about potential improvements

2. **Supported Formats**:
   - **WDL**: Uses miniwdl for comprehensive validation
   - **CWL**: Uses cwltool for standards-compliant validation

3. **No Additional Installation Required**:
   Both miniwdl and cwltool are included as dependencies and available immediately after installing the MCP server.

### Genomics File Discovery

The MCP server includes a powerful genomics file search tool that helps users locate and discover genomics files across multiple storage systems:

1. **Multi-Storage Search**:
   - **S3 Buckets**: Search configured S3 bucket paths for genomics files
   - **HealthOmics Sequence Stores**: Discover read sets and their associated files
   - **HealthOmics Reference Stores**: Find reference genomes and associated indexes
   - **Unified Results**: Get combined, deduplicated results from all storage systems

2. **Intelligent Pattern Matching**:
   - **File Path Matching**: Search against S3 object keys and HealthOmics resource names
   - **Tag-Based Search**: Match against S3 object tags and HealthOmics metadata
   - **Fuzzy Matching**: Find files even with partial or approximate search terms
   - **Multiple Terms**: Support for multiple search terms with logical matching

3. **Automatic File Association**:
   - **BAM/CRAM Indexes**: Automatically group BAM files with their .bai indexes and CRAM files with .crai indexes
   - **FASTQ Pairs**: Detect and group R1/R2 read pairs using standard naming conventions (_R1/_R2, _1/_2)
   - **FASTA Indexes**: Associate FASTA files with their .fai, .dict, and BWA index collections
   - **Variant Indexes**: Group VCF/GVCF files with their .tbi and .csi index files
   - **Complete File Sets**: Identify complete genomics file collections for analysis pipelines

4. **Smart Relevance Scoring**:
   - **Pattern Match Quality**: Higher scores for exact matches, lower for fuzzy matches
   - **File Type Relevance**: Boost scores for files matching the requested type
   - **Associated Files Bonus**: Increase scores for files with complete index sets
   - **Storage Accessibility**: Consider storage class (Standard vs. Glacier) in scoring

5. **Comprehensive File Metadata**:
   - **Access Paths**: S3 URIs or HealthOmics S3 access point paths for direct data access
   - **File Characteristics**: Size, storage class, last modified date, and file type detection
   - **Storage Information**: Archive status and retrieval requirements
   - **Source System**: Clear indication of whether files are from S3, sequence stores, or reference stores

6. **Configuration and Setup**:
   - **S3 Bucket Configuration**: Set `GENOMICS_SEARCH_S3_BUCKETS` environment variable with comma-separated bucket paths
   - **Example**: `GENOMICS_SEARCH_S3_BUCKETS=s3://my-genomics-data/,s3://shared-references/hg38/`
   - **Permissions**: Ensure appropriate S3 and HealthOmics read permissions
   - **Performance**: Parallel searches across storage systems for optimal response times

7. **Performance Optimizations**:
   - **Smart S3 API Usage**: Optimized to minimize S3 API calls by 60-90% through intelligent caching and batching
   - **Lazy Tag Loading**: Only retrieves S3 object tags when needed for pattern matching
   - **Result Caching**: Caches search results to eliminate repeated S3 calls for identical searches
   - **Batch Operations**: Retrieves tags for multiple objects in parallel batches
   - **Configurable Performance**: Tune cache TTLs, batch sizes, and tag search behavior for your use case
   - **Path-First Matching**: Prioritizes file path matching over tag matching to reduce API calls

### File Search Usage Examples

1. **Find FASTQ Files for a Sample**:
   ```
   User: "Find all FASTQ files for sample NA12878"
   → Use SearchGenomicsFiles with file_type="fastq" and search_terms=["NA12878"]
   → Returns R1/R2 pairs automatically grouped together
   → Includes file sizes and storage locations
   ```

2. **Locate Reference Genomes**:
   ```
   User: "Find human reference genome hg38 files"
   → Use SearchGenomicsFiles with file_type="fasta" and search_terms=["hg38", "human"]
   → Returns FASTA files with associated .fai, .dict, and BWA indexes
   → Provides S3 access point paths for HealthOmics reference stores
   ```

3. **Search for Alignment Files**:
   ```
   User: "Find BAM files from the 1000 Genomes project"
   → Use SearchGenomicsFiles with file_type="bam" and search_terms=["1000", "genomes"]
   → Returns BAM files with their .bai index files
   → Ranked by relevance with complete file metadata
   ```

4. **Discover Variant Files**:
   ```
   User: "Locate VCF files containing SNP data"
   → Use SearchGenomicsFiles with file_type="vcf" and search_terms=["SNP"]
   → Returns VCF files with associated .tbi index files
   → Includes both S3 and HealthOmics store results
   ```

### Performance Tuning for File Search

The genomics file search includes several optimizations to minimize S3 API calls and improve performance:

1. **For Path-Based Searches** (Recommended):
   ```bash
   # Use specific file/sample names in search terms
   # This enables path matching without tag retrieval
   GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH=true  # Keep enabled for fallback
   GENOMICS_SEARCH_RESULT_CACHE_TTL=600       # Cache results for 10 minutes
   ```

2. **For Tag-Heavy Environments**:
   ```bash
   # Optimize batch sizes for your dataset
   GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE=200     # Larger batches for better performance
   GENOMICS_SEARCH_TAG_CACHE_TTL=900          # Longer tag cache for frequently accessed objects
   ```

3. **For Cost-Sensitive Environments**:
   ```bash
   # Disable tag search if only path matching is needed
   GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH=false  # Eliminates all tag API calls
   GENOMICS_SEARCH_RESULT_CACHE_TTL=1800       # Longer result cache to reduce repeated searches
   ```

4. **For Development/Testing**:
   ```bash
   # Disable caching for immediate results during development
   GENOMICS_SEARCH_RESULT_CACHE_TTL=0         # No result caching
   GENOMICS_SEARCH_TAG_CACHE_TTL=0            # No tag caching
   GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE=50      # Smaller batches for testing
   ```

**Performance Impact**: These optimizations can reduce S3 API calls by 60-90% and improve search response times by 5-10x compared to the unoptimized implementation.

### Common Use Cases

1. **Workflow Development**:
   ```
   User: "Help me create a new genomic variant calling workflow"
   → Option A: Use PackageAHOWorkflow to bundle files, then CreateAHOWorkflow with base64 ZIP
   → Option B: Upload workflow ZIP to S3, then CreateAHOWorkflow with S3 URI
   → Validate syntax and parameters
   → Choose method based on workflow size and storage preferences
   ```

2. **Production Execution**:
   ```
   User: "Run my alignment workflow on these FASTQ files"
   → Use SearchGenomicsFiles to find FASTQ files for the run
   → Use StartAHORun with appropriate parameters
   → Monitor with ListAHORuns and GetAHORun
   → Track task progress with ListAHORunTasks
   ```

3. **Troubleshooting**:
   ```
   User: "My workflow failed, what went wrong?"
   → Use DiagnoseAHORunFailure for comprehensive analysis
   → Access specific logs based on failure type
   → Provide actionable remediation steps
   ```

4. **Performance Optimization**:
   ```
   User: "How can I make my workflow run faster?"
   → Use AnalyzeAHORunPerformance to identify bottlenecks
   → Review resource utilization patterns
   → Suggest optimization strategies
   ```

5. **Workflow Validation**:
   ```
   User: "Check if my WDL workflow is valid"
   → Use LintAHOWorkflowDefinition for single files
   → Use LintAHOWorkflowBundle for multi-file workflows with imports
   → Check for missing inputs, outputs, or runtime requirements
   → Validate import resolution and dependencies
   → Get detailed error messages and warnings
   ```

### Important Considerations

- **IAM Permissions**: Ensure proper IAM roles with HealthOmics permissions
- **Regional Availability**: Use `GetAHOSupportedRegions` to verify service availability
- **Cost Management**: Monitor storage and compute costs, especially with STATIC storage
- **Data Security**: Follow genomic data handling best practices and compliance requirements
- **Resource Limits**: Be aware of service quotas and limits for concurrent runs

### Error Handling

When tools return errors:
- Check AWS credentials and permissions
- Verify resource IDs (workflow_id, run_id, task_id) are valid
- Ensure proper parameter formatting and required fields
- Use diagnostic tools to understand failure root causes
- Provide clear, actionable error messages to users

## Installation

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-healthomics-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-healthomics-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22WARNING%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-healthomics-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWhlYWx0aG9taWNzLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJBV1NfUFJPRklMRSI6InlvdXItcHJvZmlsZSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiV0FSTklORyJ9fQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20HealthOmics%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-healthomics-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22WARNING%22%7D%7D) |

Install using uvx:

```bash
uvx awslabs.aws-healthomics-mcp-server
```

Or install from source:

```bash
git clone <repository-url>
cd mcp/src/aws-healthomics-mcp-server
uv sync
uv run -m awslabs.aws_healthomics_mcp_server.server
```

## Configuration

### Environment Variables

#### Core Configuration

- `AWS_REGION` - AWS region for HealthOmics operations (default: us-east-1)
- `AWS_PROFILE` - AWS profile for authentication
- `FASTMCP_LOG_LEVEL` - Server logging level (default: WARNING)
- `HEALTHOMICS_DEFAULT_MAX_RESULTS` - Default maximum number of results for paginated API calls (default: 10)

#### Genomics File Search Configuration

- `GENOMICS_SEARCH_S3_BUCKETS` - Comma-separated list of S3 bucket paths to search for genomics files (e.g., "s3://my-genomics-data/,s3://shared-references/")
- `GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH` - Enable/disable S3 tag-based searching (default: true)
  - Set to `false` to disable tag retrieval and only use path-based matching
  - Significantly reduces S3 API calls when tag matching is not needed
- `GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE` - Maximum objects to retrieve tags for in a single batch (default: 100)
  - Larger values improve performance for tag-heavy searches but use more memory
  - Smaller values reduce memory usage but may increase API call latency
- `GENOMICS_SEARCH_RESULT_CACHE_TTL` - Result cache TTL in seconds (default: 600)
  - Set to `0` to disable result caching
  - Caches complete search results to eliminate repeated S3 calls for identical searches
- `GENOMICS_SEARCH_TAG_CACHE_TTL` - Tag cache TTL in seconds (default: 300)
  - Set to `0` to disable tag caching
  - Caches individual object tags to avoid duplicate retrievals across searches
- `GENOMICS_SEARCH_MAX_CONCURRENT` - Maximum concurrent S3 bucket searches (default: 10)
- `GENOMICS_SEARCH_TIMEOUT_SECONDS` - Search timeout in seconds (default: 300)
- `GENOMICS_SEARCH_ENABLE_HEALTHOMICS` - Enable/disable HealthOmics sequence/reference store searches (default: true)

> **Note for Large S3 Buckets**: When searching very large S3 buckets (millions of objects), the genomics file search may take longer than the default MCP client timeout. If you encounter timeout errors, increase the MCP server timeout by adding a `"timeout"` property to your MCP server configuration (e.g., `"timeout": 300000` for five minutes, specified in milliseconds). This is particularly important when using the search tool with extensive S3 bucket configurations or when `GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH=true` is used with large datasets. The value of `"timeout"` should always be greater than the value of `GENOMICS_SEARCH_TIMEOUT_SECONDS` if you want to prevent the MCP timeout from preempting the genomics search timeout

#### Agent Identification

- `AGENT` - Agent identifier appended to the User-Agent string on all boto3 API calls as `agent/<value>` (optional)
  - **Use case**: Attributing API calls to specific AI agents for traceability via CloudTrail and AWS service logs
  - **Behavior**: When set, the value is sanitized to visible ASCII characters (0x20-0x7E), stripped of leading/trailing whitespace, lowercased, and appended to the User-Agent header as `agent/<value>`
  - **Validation**: Empty, whitespace-only, or values that become empty after sanitization are treated as unset
  - **Example**: `export AGENT=KIRO` produces `User-Agent: ... agent/kiro`

#### Testing Configuration Variables

The following environment variables are primarily intended for testing scenarios, such as integration testing against mock service endpoints:

- `HEALTHOMICS_SERVICE_NAME` - Override the AWS service name used by the HealthOmics client (default: omics)
  - **Use case**: Testing against mock services or alternative implementations
  - **Validation**: Cannot be empty or whitespace-only; falls back to default with warning if invalid
  - **Example**: `export HEALTHOMICS_SERVICE_NAME=omics-mock`

- `HEALTHOMICS_ENDPOINT_URL` - Override the endpoint URL used by the HealthOmics client
  - **Use case**: Integration testing against local mock services or alternative endpoints
  - **Validation**: Must begin with `http://` or `https://`; ignored with warning if invalid
  - **Example**: `export HEALTHOMICS_ENDPOINT_URL=http://localhost:8080`
  - **Note**: Only affects the HealthOmics client; other AWS services use default endpoints

> **Important**: These testing configuration variables should only be used in development and testing environments. In production, always use the default AWS HealthOmics service endpoints for security and reliability.

### AWS Credentials

This server requires AWS credentials with appropriate permissions for HealthOmics operations. Configure using:

1. AWS CLI: `aws configure`
2. Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
3. IAM roles (recommended for EC2/Lambda)
4. AWS profiles: Set `AWS_PROFILE` environment variable

### Required IAM Permissions

The following IAM permissions are required:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "omics:ListWorkflows",
                "omics:CreateWorkflow",
                "omics:GetWorkflow",
                "omics:CreateWorkflowVersion",
                "omics:ListWorkflowVersions",
                "omics:StartRun",
                "omics:ListRuns",
                "omics:GetRun",
                "omics:ListRunTasks",
                "omics:GetRunTask",
                "omics:CreateRunGroup",
                "omics:GetRunGroup",
                "omics:ListRunGroups",
                "omics:UpdateRunGroup",
                "omics:CreateRunCache",
                "omics:GetRunCache",
                "omics:ListRunCaches",
                "omics:UpdateRunCache",
                "omics:ListSequenceStores",
                "omics:ListReadSets",
                "omics:GetReadSetMetadata",
                "omics:ListReferenceStores",
                "omics:ListReferences",
                "omics:GetReferenceMetadata",
                "omics:CreateSequenceStore",
                "omics:GetSequenceStore",
                "omics:UpdateSequenceStore",
                "omics:StartReadSetImportJob",
                "omics:GetReadSetImportJob",
                "omics:ListReadSetImportJobs",
                "omics:StartReadSetExportJob",
                "omics:GetReadSetExportJob",
                "omics:ListReadSetExportJobs",
                "omics:StartReadSetActivationJob",
                "omics:GetReferenceStore",
                "omics:StartReferenceImportJob",
                "omics:GetReferenceImportJob",
                "omics:ListReferenceImportJobs",
                "omics:CreateConfiguration",
                "omics:GetConfiguration",
                "omics:ListConfigurations",
                "omics:DeleteConfiguration",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "logs:GetLogEvents"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetObject",
                "s3:GetObjectTagging",
                "s3:HeadBucket"
            ],
            "Resource": [
                "arn:aws:s3:::*genomics*",
                "arn:aws:s3:::*genomics*/*",
                "arn:aws:s3:::*omics*",
                "arn:aws:s3:::*omics*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:PassRole"
            ],
            "Resource": "arn:aws:iam::*:role/HealthOmicsExecutionRole*"
        }
    ]
}
```

**Note**: The S3 permissions above use wildcard patterns for genomics-related buckets. In production, replace these with specific bucket ARNs that you want to search. For example:

```json
{
    "Effect": "Allow",
    "Action": [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:GetObjectTagging",
        "s3:HeadBucket"
    ],
    "Resource": [
        "arn:aws:s3:::my-genomics-data",
        "arn:aws:s3:::my-genomics-data/*",
        "arn:aws:s3:::shared-references",
        "arn:aws:s3:::shared-references/*"
    ]
}
```

## Remote Transport (HTTP/SSE)

By default the server runs over **stdio**, which is ideal for local, single-user use with an MCP client. The server can also run as a network-accessible service over HTTP-based transports (`streamable-http` or `sse`) for hosted and remote scenarios.

> **Security:** In this release the server performs **no inbound authentication** of its own. By default it binds only to the loopback address (`127.0.0.1`), so it is not reachable from the network. Exposing the server on a non-loopback address **requires** an external fronting authentication layer (see [Securing non-loopback exposure](#securing-non-loopback-exposure)). When a non-loopback host is configured, the server logs a warning at startup and still binds.

### Transport selection

The transport is selected with the `--transport` flag or the `MCP_TRANSPORT` environment variable. When both are supplied, the command-line flag wins. An unset, empty, or whitespace-only value selects `stdio`; any other unsupported value causes the server to log an error and exit without starting.

| Transport mode | Flag | Environment variable | Start command |
|----------------|------|----------------------|---------------|
| `stdio` (default) | `--transport stdio` | `MCP_TRANSPORT=stdio` | `uv run -m awslabs.aws_healthomics_mcp_server.server` |
| `streamable-http` | `--transport streamable-http` | `MCP_TRANSPORT=streamable-http` | `uv run -m awslabs.aws_healthomics_mcp_server.server --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp` |
| `sse` | `--transport sse` | `MCP_TRANSPORT=sse` | `uv run -m awslabs.aws_healthomics_mcp_server.server --transport sse` |

Each start command also has an environment-variable equivalent, for example:

```bash
# streamable-http via environment variables
export MCP_TRANSPORT=streamable-http
export MCP_HOST=127.0.0.1
export MCP_PORT=8000
export MCP_PATH=/mcp
uv run -m awslabs.aws_healthomics_mcp_server.server

# sse via environment variables
MCP_TRANSPORT=sse uv run -m awslabs.aws_healthomics_mcp_server.server
```

### Network bind configuration

When a network transport (`streamable-http` or `sse`) is selected, the bind address, port, and request path are configured with the following flags and environment variables. When both a flag and its environment variable are supplied, the command-line flag wins. These values are ignored when the transport is `stdio`.

| Value | Flag | Environment variable | Default |
|-------|------|----------------------|---------|
| Host  | `--host` | `MCP_HOST` | `127.0.0.1` (loopback) |
| Port  | `--port` | `MCP_PORT` | `8000` |
| Path  | `--path` | `MCP_PATH` | `/mcp` |

Validation:

- The port must be an integer in the range `1`–`65535`. An invalid port causes the server to log an error and exit without binding.
- The host must be a valid IPv4 address, IPv6 address, or syntactically valid hostname. An invalid host causes the server to log an error and exit without binding.

### Securing non-loopback exposure

The server does **not** perform inbound authentication. Binding to a non-loopback host (for example `0.0.0.0`) makes the endpoint reachable on the network with no built-in access control, so it **must** be placed behind an external fronting authentication layer. Concrete options include:

- **SigV4 via [`mcp-proxy-for-aws`](https://github.com/aws/mcp-proxy-for-aws)** — front the server with a proxy that requires AWS Signature Version 4 signed requests, so only callers with valid AWS credentials reach the server.
- **Reverse proxy** — terminate authentication at a reverse proxy (for example nginx or Envoy) that enforces mutual TLS, an auth subrequest, or token validation before forwarding to the loopback-bound server.
- **API gateway** — place an API gateway (for example Amazon API Gateway) in front of the server to handle authentication and authorization, forwarding only authenticated requests.
- **Amazon Bedrock AgentCore Runtime** — host the server on [AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html) with `server_protocol: MCP`. The runtime terminates inbound authentication at its boundary — either a **Custom JWT authorizer** (validates tokens against an OIDC discovery URL such as Amazon Cognito) or **AWS IAM (SigV4)** — before requests reach the server, and runs the server in an isolated microVM where the runtime is the only ingress. This pairs naturally with the server's `jwt` and `sigv4` inbound mechanisms: the runtime's Custom JWT authorizer cryptographically verifies the token signature (satisfying the `jwt` production requirement in [Multi-tenant mode](#multi-tenant-mode-phase-2)), then forwards the authenticated request. In this deployment the server serves `streamable-http` bound to the container port AgentCore expects (all interfaces) rather than loopback, since AgentCore itself is the network and authentication boundary.

A typical secure deployment keeps the server bound to loopback inside its host or container network namespace and lets the fronting layer be the only network-reachable entry point. The AgentCore Runtime option is the exception: there the server binds to the runtime's container port and AgentCore is the sole ingress.

## Multi-tenant mode (Phase 2)

By default the server runs in **single-tenant mode**: one process identity (the default AWS credential chain, or a named `aws_profile`) serves every request. **Multi-tenant mode** lets a single network endpoint serve many caller identities by deriving AWS credentials **per inbound request** instead of once per process. Each request runs with credentials scoped to the caller that made it.

> **Security:** Multi-tenant mode does not remove the need for a secured transport. The inbound identity mechanisms below either trust credential material forwarded by a fronting layer or decode (but do not cryptographically verify) bearer tokens. Multi-tenant mode **must** still be deployed behind an appropriately secured, trusted transport (TLS plus a fronting authentication layer). If no enabled mechanism can authenticate a request, the server rejects it with `401 Unauthorized` and makes no AWS call.

### Enabling multi-tenant mode

| Value | Flag | Environment variable | Default |
|-------|------|----------------------|---------|
| Multi-tenant | `--multi-tenant` | `MCP_MULTI_TENANT` | disabled |
| Inbound mechanisms | `--inbound-auth` | `MCP_INBOUND_AUTH` | none |

- Multi-tenant mode **requires a network transport** (`streamable-http` or `sse`); combining it with `stdio` causes the server to log an error and exit without starting.
- `--multi-tenant` accepts case-insensitive enable values (`true`, `1`, `yes`, `on`, `enabled`) and disable values (`false`, `0`, `no`, `off`, `disabled`). When both the flag and environment variable are supplied, the command-line flag wins.
- `--inbound-auth` takes a comma-separated subset of `sigv4`, `jwt`, `explicit` (for example `--inbound-auth sigv4,jwt`). At least one mechanism must be enabled; enabling multi-tenant mode with no mechanisms causes the server to exit at startup (it would otherwise reject every request).

```bash
# Multi-tenant streamable-http with SigV4 + JWT inbound mechanisms
export MCP_TRANSPORT=streamable-http
export MCP_MULTI_TENANT=true
export MCP_INBOUND_AUTH=sigv4,jwt
export MCP_JWT_ROLE_ARN=arn:aws:iam::123456789012:role/tenant-callers
uv run -m awslabs.aws_healthomics_mcp_server.server
```

### Inbound identity mechanisms and trust models

When more than one enabled mechanism can handle a request, exactly one is selected using the deterministic precedence order **`sigv4` > `jwt` > `explicit`**. Each mechanism assumes a trusted fronting layer / transport, as described below.

- **`sigv4`** — The caller signs the request with their own AWS Signature Version 4 credentials. SigV4 proves possession of the secret key without transmitting it, so the server cannot recover a usable secret from the signature alone. This mechanism therefore expects a trusted fronting layer (for example [`mcp-proxy-for-aws`](https://github.com/awslabs/mcp-proxy-for-aws)) that validates the signature and forwards the caller's short-lived credentials on trusted headers (`X-Aho-Forwarded-Secret-Access-Key`, and `X-Aho-Forwarded-Session-Token` or `X-Amz-Security-Token`). The access key id parsed from the `Authorization` header becomes the per-caller cache identity. If the forwarded credential material is absent, the mechanism **fails closed** and no session is built.
- **`jwt`** — A bearer/JWT token is exchanged server-side via AWS STS `AssumeRole` into a per-caller/per-tenant role (`MCP_JWT_ROLE_ARN`). The exchange runs with the **server's own** credentials, never the inbound token. The JWT **signature is not verified** by this server — it assumes a fronting layer (API gateway, load balancer, or hosting platform) has already authenticated the token; the server only decodes the claims to extract a caller identifier. That identifier is attached as an **ABAC session tag** (`caller=<sub>`) on the assumed-role session so the role's policies and CloudTrail can scope and attribute actions per caller. If the STS call fails, the request is rejected with `401` and no credential context is populated.

  > **Production requirement:** Because this server does **not** verify the token signature, the `jwt` mechanism **must** be deployed behind a fronting layer that cryptographically verifies the JWT signature (issuer, audience, expiry, and signature) before the request reaches the server — for example an API Gateway JWT authorizer, an ALB OIDC listener, or the hosting platform's authentication layer. The server must never be directly reachable by clients when `jwt` is enabled. Without upstream verification, any party that can reach the endpoint can forge a token with an arbitrary `sub`, obtain credentials for the assumed role, and impersonate any caller via the `caller` ABAC tag.
- **`explicit`** — Short-lived AWS credentials are supplied directly in request headers (`X-Aws-Access-Key-Id`, `X-Aws-Secret-Access-Key`, and optionally `X-Aws-Session-Token`). These headers carry live credential material, so this mechanism **requires a trusted transport** and short-lived (STS session) credentials.

Credential material (secret access keys, session tokens, bearer tokens) is **never logged** and never appears in error responses or the `401` body.

### Per-request credential freshness and isolation

- Credentials are derived **fresh for every request** from that request's inbound identity; no process-level or prior-request session is ever reused, so no separate credential-refresh mechanism is needed.
- The `aws_profile` tool argument is **non-authoritative** in multi-tenant mode: identity comes solely from the request context, so a caller cannot select another tenant's identity by passing a profile. The `aws_region` argument is still honored (falling back to the configured default region).
- Each request's credential context is installed before any tool runs and discarded when the request completes, so it is never visible to another request. Concurrent requests are isolated via `contextvars`.
- Credential-derived caches (the AWS partition cache) are keyed by caller identity, so a value derived for one identity is never served to another. The partition cache is bounded to avoid unbounded memory growth across many caller identities.

## Usage with MCP Clients

### Kiro

See the [Kiro IDE documentation](https://kiro.dev/docs/mcp/configuration/) or the [Kiro CLI documentation](https://kiro.dev/docs/cli/mcp/configuration/) for details.

For global configuration, edit `~/.kiro/settings/mcp.json`. For project-specific configuration, edit `.kiro/settings/mcp.json` in your project directory.

Add to your Kiro MCP configuration (`~/.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "aws-healthomics": {
      "command": "uvx",
      "args": ["awslabs.aws-healthomics-mcp-server"],
      "timeout": 300000,
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "your-profile",
        "HEALTHOMICS_DEFAULT_MAX_RESULTS": "10",
        "AGENT": "kiro",
        "GENOMICS_SEARCH_S3_BUCKETS": "s3://my-genomics-data/,s3://shared-references/",
        "GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH": "true",
        "GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE": "100",
        "GENOMICS_SEARCH_RESULT_CACHE_TTL": "600",
        "GENOMICS_SEARCH_TAG_CACHE_TTL": "300"
      }
    }
  }
}
```

#### Testing Configuration Example

For integration testing against mock services:

```json
{
  "mcpServers": {
    "aws-healthomics-test": {
      "command": "uvx",
      "args": ["awslabs.aws-healthomics-mcp-server"],
      "timeout": 300000,
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "test-profile",
        "HEALTHOMICS_SERVICE_NAME": "omics-mock",
        "HEALTHOMICS_ENDPOINT_URL": "http://localhost:8080",
        "GENOMICS_SEARCH_S3_BUCKETS": "s3://test-genomics-data/",
        "GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH": "false",
        "GENOMICS_SEARCH_RESULT_CACHE_TTL": "0",
        "FASTMCP_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

### Other MCP Clients

Configure according to your client's documentation, using:
- Command: `uvx`
- Args: `["awslabs.aws-healthomics-mcp-server"]`
- Environment variables as needed

### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.aws-healthomics-mcp-server": {
      "disabled": false,
      "timeout": 300000,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-healthomics-mcp-server@latest",
        "awslabs.aws-healthomics-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "GENOMICS_SEARCH_S3_BUCKETS": "s3://my-genomics-data/,s3://shared-references/",
        "GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH": "true",
        "GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE": "100",
        "GENOMICS_SEARCH_RESULT_CACHE_TTL": "600",
        "GENOMICS_SEARCH_TAG_CACHE_TTL": "300"
      }
    }
  }
}
```

#### Windows Testing Configuration

For testing scenarios on Windows:

```json
{
  "mcpServers": {
    "awslabs.aws-healthomics-mcp-server-test": {
      "disabled": false,
      "timeout": 300000,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-healthomics-mcp-server@latest",
        "awslabs.aws-healthomics-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "DEBUG",
        "AWS_PROFILE": "test-profile",
        "AWS_REGION": "us-east-1",
        "HEALTHOMICS_SERVICE_NAME": "omics-mock",
        "HEALTHOMICS_ENDPOINT_URL": "http://localhost:8080",
        "GENOMICS_SEARCH_S3_BUCKETS": "s3://test-genomics-data/",
        "GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH": "false",
        "GENOMICS_SEARCH_RESULT_CACHE_TTL": "0"
      }
    }
  }
}
```

## Development

### Setup

```bash
git clone <repository-url>
cd aws-healthomics-mcp-server
uv sync
```

### Testing

```bash
# Run tests with coverage
uv run pytest --cov --cov-branch --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_server.py -v
```

### Code Quality

```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check

# Type checking
uv run pyright
```

## Running in a container

The published image runs the server over **stdio** by default and binds nothing
on the network, matching the local single-tenant behavior:

```bash
docker run -e AWS_REGION=us-east-1 aws-healthomics-mcp-server
```

### Running the container with a network transport

A network transport (`streamable-http` or `sse`) can be started using only the
documented environment variables — the image and its entry point do not need to
change. The relevant variables and their defaults are:

| Variable | Purpose | Default |
| --- | --- | --- |
| `MCP_TRANSPORT` | Transport mode: `stdio`, `streamable-http`, or `sse` | `stdio` |
| `MCP_HOST` | Network bind address | `127.0.0.1` (loopback) |
| `MCP_PORT` | Network bind port | `8000` |
| `MCP_PATH` | Request path served | `/mcp` |

To reach the server from outside the container you must do two things:

1. Bind a non-loopback host inside the container (for example `MCP_HOST=0.0.0.0`).
   The default `127.0.0.1` is only reachable from within the container.
2. Publish the configured port to the host with `-p`/`--publish`.

```bash
docker run \
  -e MCP_TRANSPORT=streamable-http \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=8000 \
  -p 8000:8000 \
  -e AWS_REGION=us-east-1 \
  aws-healthomics-mcp-server
```

For the SSE transport, set `MCP_TRANSPORT=sse` instead; `MCP_PATH` then controls
the SSE request path.

> **Security: non-loopback exposure requires a fronting auth layer.** Binding a
> non-loopback host (such as `0.0.0.0`) exposes AWS access on the network. The
> server performs **no inbound authentication of its own in Phase 1**, and it
> logs a warning at startup when it binds a non-loopback host. You must place the
> endpoint behind an external fronting authentication layer — for example SigV4
> via `mcp-proxy-for-aws`, a reverse proxy, or an API gateway. See the
> secure-by-default and fronting-authentication notes elsewhere in this README
> for details.

## Contributing

Contributions are welcome! Please see the [contributing guidelines](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) for more information.

## License

This project is licensed under the Apache-2.0 License. See the [LICENSE](https://github.com/awslabs/mcp/blob/main/LICENSE) file for details.
