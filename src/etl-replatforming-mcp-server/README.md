# ETL Replatforming MCP Server

**The intelligent, cost-effective solution for ETL framework migration with AI-enhanced parsing and universal workflow conversion.**

MCP server for converting ETL orchestration code between frameworks using FLEX (Framework for Linking ETL eXchange) with validation and user interaction.

## 🚀 Why This Project?

**ETL framework migration is expensive, error-prone, and time-consuming.** This project solves that with:

- **💰 Cost-Optimized AI Usage**: Three-tier approach - deterministic parsing first, AI only for gaps, minimal user prompts. Significantly reduces LLM costs compared to "AI-everything" approaches
- **🎯 Zero Manual Rewrites**: Automated conversion preserves complex pipeline logic and dependencies
- **🔄 Universal Framework Support**: One tool handles Airflow ↔ Step Functions ↔ Azure Data Factory ↔ Future frameworks
- **🏢 Organizational Standards**: Apply your naming conventions, coding patterns, and business rules to generated code
- **⚡ Production-Ready**: Handles real-world complexity with validation, error handling, and user interaction
- **🛡️ Migration Safety**: FLEX intermediate format ensures semantic preservation across frameworks

## Overview

This server provides intelligent ETL framework conversion through a multi-stage process:

```
Source Framework → DETERMINISTIC PARSE → Validate → AI ENHANCEMENT → Validate → FLEX with Placeholders
                                                                                        ↓
                                                                            User fills placeholders
                                                                                        ↓
                                                                            generate-from-flex → Target Framework
```

## ✨ Key Features

### 🔄 Universal Framework Conversion
- **Bidirectional Support**: Convert between any supported frameworks (Airflow ↔ Step Functions ↔ Azure Data Factory)
- **Semantic Preservation**: Maintains workflow logic, dependencies, error handling, and scheduling across platforms
- **Complex Pipeline Support**: Handles nested workflows, conditional branching, parallel execution, and advanced orchestration patterns

### 💡 Intelligent Parsing Engine
- **Context-Aware Enhancement**: Bedrock analyzes original source code for accurate gap-filling
- **Validation-Driven**: Multiple validation layers ensure completeness before generation
- **Custom Context Support**: Optional context documents improve AI accuracy for organization-specific patterns

### 🎯 Production-Grade Reliability
- **Comprehensive Validation**: Catches missing schedules, invalid dependencies, malformed expressions
- **Clear Placeholders**: Returns FLEX documents with "?" markers for missing information
- **Two-Step Process**: Parse to FLEX, fill placeholders, generate target framework

### 🏗️ FLEX Intermediate Format
- **Framework-Agnostic**: Universal representation that works with any orchestration platform
- **Human-Readable**: JSON format that's easy to understand, modify, and version control
- **Standards-Based**: Built on proven workflow representation principles
- **Future-Proof**: Easy to extend for new frameworks (Prefect, Dagster, etc.)

### 🔧 Developer Experience
- **MCP Integration**: Works seamlessly with Claude Desktop and other MCP clients
- **Extensible Architecture**: Simple interfaces for adding new source/target frameworks
- **Comprehensive Testing**: Unit and integration tests with real-world sample workflows
- **Rich Documentation**: Complete examples, API reference, and troubleshooting guides

## Supported Frameworks

| Framework | Parser | Generator | Status |
|-----------|--------|-----------|--------|
| Step Functions | ✅ | ✅ | Complete |
| Airflow | ✅ | ✅ | Complete |
| Azure Data Factory | ✅ | - | Complete |
| Prefect | 🚧 | 🚧 | Planned |
| Dagster | 🚧 | 🚧 | Planned |

## Installation

Choose your preferred Python package manager:

### Using uv (Recommended)

```bash
# Install dependencies
uv sync

# Run the server
uv run awslabs.etl-replatforming-mcp-server
```

### Using pip

```bash
# Install the package
pip install -e .

# Run the server
awslabs.etl-replatforming-mcp-server
```

### From PyPI (when published)

```bash
# Using uv
uvx awslabs.etl-replatforming-mcp-server@latest

# Using pip
pip install awslabs.etl-replatforming-mcp-server
awslabs.etl-replatforming-mcp-server
```

### Using Makefile (Recommended for Development)

```bash
# Install, test, and run server in one command
make run

# Or step by step
make install-and-test  # Install dependencies and run tests
awslabs.etl-replatforming-mcp-server  # Run server manually

# Other useful commands
make install  # Install dependencies only
make test     # Run tests only
make clean    # Uninstall package
```

## Configuration

### Environment Variables

Set environment variables:

```bash
export FASTMCP_LOG_LEVEL=INFO  # Optional: DEBUG, INFO, WARNING, ERROR
export AWS_REGION=us-east-1    # Required: For Bedrock LLM calls
export AWS_PROFILE=your-profile # Optional: AWS profile
```

### AWS Bedrock Setup (Required)

**⚠️ IMPORTANT: This MCP server uses AWS Bedrock for AI-enhanced workflow parsing to fill gaps in incomplete workflows and reduce user prompts.**

**Setup Steps:**

1. **AWS Credentials**: Configure AWS credentials with Bedrock permissions
   ```bash
   aws configure --profile your-profile
   # Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output format (json)
   ```

2. **IAM Permissions**: Attach `AmazonBedrockFullAccess` policy to your IAM user/role

3. **Bedrock Model Access**: Enable Claude model access in AWS Console
   - **⚠️ IMPORTANT**: Model access must be granted in the **same region** as your AWS_REGION environment variable
   - Go to **AWS Console → Amazon Bedrock → Model access**
   - **Ensure you're in the correct region** (top-right corner of AWS Console)
   - Click **Request model access**
   - Select **Anthropic Claude 3 Sonnet** (`anthropic.claude-3-sonnet-20240229-v1:0`)
   - Submit request (usually approved instantly)
   - **Verify**: Model status should show "Access granted" in the same region

4. **Verify Setup**:
   ```bash
   # Replace us-east-1 with your AWS_REGION
   aws bedrock list-foundation-models --region us-east-1
   
   # Test model access
   aws bedrock get-foundation-model --model-identifier anthropic.claude-3-sonnet-20240229-v1:0 --region us-east-1
   ```

**⚠️ Without Bedrock Setup:**
- Workflows will still parse but may remain incomplete
- More user prompts will be required for missing information
- Conversion quality may be reduced
- You'll see "Bedrock enhancement failed" warnings in logs

## Bedrock LLM Configuration

Configure AI-enhanced parsing with custom Bedrock settings:

### Supported Models

| Model | Model ID |
|-------|----------|
| Claude 3.5 Sonnet (Recommended) | `anthropic.claude-3-5-sonnet-20240620-v1:0` |
| Claude 3 Sonnet | `anthropic.claude-3-sonnet-20240229-v1:0` |
| Claude 3 Haiku | `anthropic.claude-3-haiku-20240307-v1:0` |
| Claude 3 Opus | `anthropic.claude-3-opus-20240229-v1:0` |

### Default Configuration

**The `llm_config` parameter is optional.** If not provided, the system uses these defaults:

```json
{
  "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
  "max_tokens": 4000,
  "temperature": 0.1,
  "top_p": 0.9,
  "region": "us-east-1"
}
```

**⚠️ Region Note**: The MCP server will use the region from:
1. `llm_config.region` parameter (if provided)
2. `AWS_REGION` environment variable
3. Default: `us-east-1`

**Ensure Bedrock model access is granted in the same region the server will use.**

### Custom Configuration

Override any default values by providing `llm_config` parameter:

```json
{
  "llm_config": {
    "model_id": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "temperature": 0.2,
    "max_tokens": 6000
  }
}
```

**Parameters:**
- `model_id`: Choose from supported models above
- `max_tokens`: Maximum response length (1-8000)
- `temperature`: Creativity level (0.0-1.0, lower = more focused)
- `top_p`: Response diversity (0.0-1.0)
- `region`: AWS region for Bedrock service
- `extra_params`: Additional model-specific parameters

### AI Context Document

**✅ IMPLEMENTED: Enhance AI parsing accuracy with custom context documentation.**

You can provide an optional context document to help the AI better understand your specific coding patterns, naming conventions, and organizational standards. This significantly improves the AI's ability to infer missing information and reduces the need for user prompts.

#### Usage

The MCP tools support context files through the `context_file` parameter:

- `convert-etl-workflow` - Uses context for both parsing and generation
- `generate-from-flex` - Uses context for target code generation
- Single workflow tools - Accept `context_document` parameter directly

#### What to Include in Context Document (When Available)

**Organizational Standards:**
```text
# ETL Pipeline Standards - Data Engineering Team

## Naming Conventions
- All pipelines use prefix: data_pipeline_
- Task names follow: {source}_{action}_{destination}
- Example: s3_extract_customers, redshift_transform_sales

## Scheduling Patterns
- Daily ETL jobs run at 2 AM UTC: "0 2 * * *"
- Weekly reports run Sundays at midnight: "0 0 * * 0"
- Real-time processing uses event triggers

## Error Handling
- All production pipelines retry 3 times with exponential backoff
- Critical failures notify: data-team@company.com
- Non-critical failures log to CloudWatch only
```

**Framework-Specific Patterns:**
```text
# Step Functions Conventions

## Resource Mapping
- SQL tasks always use: arn:aws:states:::aws-sdk:redshiftdata:executeStatement
- Python processing uses: arn:aws:states:::lambda:invoke
- File operations use: arn:aws:states:::aws-sdk:s3:putObject

## State Naming
- Extract states: Extract{DataSource}
- Transform states: Transform{DataType}
- Load states: LoadTo{Destination}

## Timeout Standards
- SQL queries: 3600 seconds (1 hour)
- Lambda functions: 900 seconds (15 minutes)
- File transfers: 1800 seconds (30 minutes)
```

**Data Source Information:**
```text
# Data Infrastructure Context

## Database Connections
- Production Redshift: data-warehouse cluster
- Staging PostgreSQL: staging-db.company.com
- Analytics MySQL: analytics-readonly.company.com

## S3 Bucket Structure
- Raw data: s3://company-data-raw/{source}/{date}/
- Processed data: s3://company-data-processed/{pipeline}/{date}/
- Archives: s3://company-data-archive/{year}/{month}/

## Common Queries
- Customer data: SELECT * FROM customers WHERE updated_date >= CURRENT_DATE - 1
- Sales data: SELECT * FROM sales WHERE transaction_date = CURRENT_DATE
- Inventory: SELECT * FROM inventory WHERE last_updated >= NOW() - INTERVAL '1 hour'
```

**Business Logic Context:**
```text
# Business Rules and Logic

## Data Processing Rules
- Customer PII must be encrypted before S3 storage
- Financial data requires dual approval workflow
- Marketing data can be processed in parallel

## SLA Requirements
- Daily customer reports: Complete by 6 AM EST
- Real-time fraud detection: < 30 second latency
- Weekly analytics: Complete by Monday 9 AM EST

## Dependencies
- Customer pipeline must complete before marketing pipeline
- Financial data depends on external vendor API (available 1-5 AM UTC)
- Inventory updates trigger downstream pricing calculations
```

#### Best Practices

- **Be Specific**: Include actual examples and code snippets rather than generic descriptions
- **Include Standards**: Document naming conventions, scheduling patterns, error handling, and business rules
- **Provide Context**: Explain infrastructure setup, data sources, and dependencies
- **Update Regularly**: Keep context current with evolving standards

## Getting Input Files

Before using the conversion tools, you need to extract the workflow definitions from your source frameworks:

### Step Functions
**Export state machine definition:**
```bash
# Using AWS CLI
aws stepfunctions describe-state-machine --state-machine-arn "arn:aws:states:region:account:stateMachine:MyStateMachine" --query "definition" --output text > state_machine.json

# Using AWS Console
# 1. Go to Step Functions console
# 2. Select your state machine
# 3. Click "Definition" tab
# 4. Copy the JSON definition
```

### Airflow
**Export DAG Python file:**
```bash
# Copy DAG file from Airflow dags folder
cp /opt/airflow/dags/my_dag.py ./my_dag.py

# Or from Airflow web UI
# 1. Go to Airflow web interface
# 2. Click on DAG name
# 3. Go to "Code" tab
# 4. Copy the Python code
```

### Azure Data Factory
**Export pipeline JSON:**
```bash
# Using Azure CLI
az datafactory pipeline show --factory-name "MyDataFactory" --resource-group "MyResourceGroup" --name "MyPipeline" > pipeline.json

# Using Azure Portal
# 1. Go to Azure Data Factory Studio
# 2. Select your pipeline
# 3. Click "{}" (JSON view) in toolbar
# 4. Copy the JSON definition
```

## Usage

**Natural Language Interface**: Simply describe what you want to do with directory paths or individual workflows.

### Directory-Based Tools (Batch Processing)

#### Tool 1: parse-to-flex

**Usage Examples:**
> **User**: "Get FLEX docs for files in ./my_workflows"

> **User**: "Parse the jobs in /path/to/step_functions directory to FLEX"

**What it does:**
- Auto-detects workflow formats in the directory (Step Functions, Airflow, Azure Data Factory)
- Parses each file to FLEX format with AI enhancement
- Creates output directory: `"output flex docs for jobs in {dir_name}"`

#### Tool 2: convert-etl-workflow

**Usage Examples:**
> **User**: "Convert jobs in ./step_functions_workflows to airflow"

> **User**: "Convert jobs in ./step_functions_workflows to airflow using context from ./context.txt"

**What it does:**
- Auto-detects source formats in the directory
- Converts to specified target framework
- Applies organizational context from file using LLM for consistency
- Creates two output directories:
  - `"output flex docs for jobs in {dir_name}"`
  - `"output jobs for jobs in {dir_name}"`

#### Tool 3: generate-from-flex

**Usage Examples:**
> **User**: "Convert FLEX docs in ./flex_output to step_functions"

> **User**: "Generate airflow jobs from FLEX files in /path/to/flex_docs using context from ./context.txt"

**What it does:**
- Reads FLEX files from the directory
- Generates target framework jobs
- Applies organizational context from file using LLM for consistency
- Creates output directory: `"output jobs for flex docs in {dir_name}"`

### Single Workflow Tools (Individual Processing)

#### Tool 4: parse-single-workflow-to-flex

**Usage Examples:**
> **User**: "Parse this Step Functions definition to FLEX: {JSON content}"

> **User**: "Convert this Airflow DAG to FLEX format: {Python code}"

**What it does:**
- Parses individual workflow content to FLEX format
- Uses AI enhancement to fill missing information
- Returns FLEX document with validation status
- No file system operations - works with content directly

#### Tool 5: convert-single-etl-workflow

**Usage Examples:**
> **User**: "Convert this Step Functions workflow to Airflow: {JSON content}"

> **User**: "Transform this Airflow DAG to Step Functions: {Python code}"

**What it does:**
- Complete conversion: Parse → FLEX → Generate target framework
- Single-step process for individual workflows
- Returns both FLEX document and target framework code
- Applies organizational context if provided

#### Tool 6: generate-single-workflow-from-flex

**Usage Examples:**
> **User**: "Generate Airflow DAG from this FLEX workflow: {FLEX JSON}"

> **User**: "Create Step Functions state machine from FLEX: {FLEX JSON}"

**What it does:**
- Generates target framework code from complete FLEX workflow
- Validates FLEX document before generation
- Returns target framework code (Airflow DAG, Step Functions JSON)
- Applies organizational context if provided

### When to Use Which Tools

**Use Directory-Based Tools When:**
- Migrating entire projects with multiple workflows
- Processing dozens or hundreds of workflow files
- Need organized output directories for team collaboration
- Want batch processing with consistent naming and structure

**Use Single Workflow Tools When:**
- Testing conversion of individual workflows
- Working with workflow content directly (copy/paste from UI)
- Prototyping or experimenting with conversions
- Integrating with other tools or scripts that provide workflow content

## Directory Processing

**Directory-based tools support batch processing for real-world migrations.**

**Input Directory Structure:**
```
my_workflows/
├── pipeline1.json          # Step Functions
├── pipeline2.py            # Airflow DAG
├── complex_etl.json        # Azure Data Factory
└── data_pipeline.flex.json # FLEX format
```

**Output Directory Structure:**
```
parent_directory/
├── my_workflows/                           # Original input
├── output flex docs for jobs in my_workflows/
│   ├── pipeline1.flex.json
│   ├── pipeline2.flex.json
│   └── complex_etl.flex.json
└── output jobs for jobs in my_workflows/
    ├── pipeline1.py                       # Generated Airflow
    ├── pipeline2.py                       # Generated Airflow
    └── complex_etl.py                     # Generated Airflow
```

**Benefits:**
- **Auto-Detection**: No need to specify source frameworks
- **Bulk Processing**: Handle hundreds of workflows at once
- **Organized Output**: Clear directory structure with descriptive names
- **Context Files**: Use optional plain text files for organizational standards

### Processing Results

**Directory processing returns detailed results:**

```json
{
  "status": "complete",
  "processed_files": 5,
  "completed_conversions": 4,
  "flex_output_directory": "/path/to/output flex docs for jobs in my_workflows",
  "jobs_output_directory": "/path/to/output jobs for jobs in my_workflows",
  "results": [
    {"file": "pipeline1.json", "status": "complete"},
    {"file": "pipeline2.py", "status": "incomplete", "missing": "Schedule information"}
  ],
  "message": "Processed 5 files, 4 completed successfully"
}
```

**The server provides:**
- File-by-file processing status
- Output directory locations
- Clear success/failure counts
- Specific missing information for incomplete files

## FLEX (Framework for Linking ETL eXchange)

**FLEX** is our framework-agnostic intermediate representation that serves as the "Rosetta Stone" for ETL orchestration. Think of it as the universal connector that allows any workflow framework to communicate with any other.

### Why FLEX?

**FLEX is like SQL for ETL orchestration - learn once, use everywhere.**

#### Business Value for ETL Developers

**🚀 Career Portability**
- Your pipeline knowledge becomes framework-independent
- Skills transfer across all orchestration platforms
- One expertise covers Airflow, Step Functions, Data Factory, and future tools

**🛡️ Migration Safety**
- Validated conversions preserve complex pipeline logic
- Eliminate error-prone manual rewrites during platform migrations
- Maintain workflow semantics across different frameworks

**☁️ Multi-Cloud Strategy**
- Write once, deploy to any cloud provider (AWS, Azure, GCP, on-premises)
- Same FLEX pipeline runs on Step Functions (AWS), Data Factory (Azure), Cloud Composer (GCP)
- Switch between orchestrators without rewriting business logic
- Avoid vendor lock-in with portable pipeline definitions
- Enable hybrid cloud deployments with consistent pipeline definitions

**⚡ Faster Development**
- Clear, readable syntax focuses on pipeline logic, not framework syntax
- Self-documenting workflows with standardized task types
- Reduced learning curve when switching between platforms

**🤝 Team Collaboration**
- Data Engineers focus on pipeline logic, not framework specifics
- DevOps can deploy same pipeline to different environments
- Analysts understand workflows without learning each orchestration tool

**🔍 Testing & Validation**
- FLEX validates workflows before deployment - catch errors early
- Standardized testing approach across all target platforms
- Consistent error handling and retry logic

**💰 Cost Optimization**
- Compare costs across platforms using identical pipeline logic
- Easy A/B testing of different orchestrators
- No rewrite costs when switching platforms

**🔮 Future-Proofing**
- Your pipelines survive technology changes
- New orchestrators (Prefect, Dagster) supported by adding generators
- Protect your pipeline investments from framework obsolescence

**📚 Documentation & Maintenance**
- FLEX documents are self-explanatory with clear task types
- Easier handoffs between team members
- Version control friendly JSON format

#### Technical Benefits

- **Framework Independence**: Write once, deploy anywhere - your business logic isn't tied to a specific orchestrator
- **Validation Layer**: Catch missing information before deployment to any target framework
- **Standards-Based**: Built on proven workflow representation principles
- **Human Readable**: JSON format that's easy to understand, version control, and modify
- **ETL-Focused**: Purpose-built for data orchestration patterns and cross-platform migration
- **Completeness Validation**: Ensures all required elements are present before target generation

### FLEX Structure

FLEX captures the essential elements of any ETL workflow:

```json
{
  "name": "workflow_name",              // Unique workflow identifier
  "description": "Workflow description", // Human-readable purpose
  "parameters": {"env": "prod"},        // Workflow parameters
  "variables": {"batch_size": 1000},     // Workflow variables
  "schedule": {                          // When to run
    "type": "rate|cron|manual|event",
    "expression": "rate(1 day)",
    "timezone": "UTC"
  },
  "tasks": [                             // What to execute
    {
      "id": "copy_data",                 // Unique task identifier
      "name": "Copy Customer Data",       // Human-readable name
      "type": "copy",                    // Task category (enhanced types)
      "source": {                        // Data source configuration
        "type": "sql_server",
        "dataset": "customers",
        "query": "SELECT * FROM customers"
      },
      "sink": {                          // Data destination
        "type": "blob_storage",
        "dataset": "processed_customers"
      },
      "linked_service": "sql-connection", // Framework-specific connections
      "timeout": 3600,                   // Max execution time
      "retries": 2,                      // Failure recovery
      "resource_requirements": {         // Compute requirements
        "cpu": "2",
        "memory": "4Gi"
      }
    }
  ],
  // Dependencies are now embedded within tasks using depends_on arrays
  "error_handling": {                    // Enhanced failure management
    "on_failure": "fail|continue|retry",
    "notification_emails": ["team@company.com"],
    "notification_webhooks": ["https://alerts.company.com"],
    "escalation_policy": "critical-data-pipeline"
  },
  "concurrency": 1,                     // Max concurrent executions
  "tags": ["etl", "customer-data"]      // Workflow classification
}
```

### FLEX Core Concepts

1. **Tasks**: Atomic units of work with enhanced types (SQL, Python, Copy, Notebook, etc.)
2. **Data Sources/Sinks**: Explicit source and destination configurations for data movement
3. **Dependencies**: Define execution order and conditions
4. **Schedule**: When and how often the workflow runs
5. **Error Handling**: Comprehensive failure management with notifications and escalation
6. **Parameters/Variables**: Runtime configuration and state management
7. **Resource Requirements**: Compute and infrastructure specifications
8. **Metadata**: Additional context for governance and documentation

### FLEX Validation Process

**Completeness Check:**
- All required fields present
- Task dependencies are valid
- Schedule expressions are properly formatted
- Error handling is configured

**AI Enhancement:**
- Bedrock analyzes original source code
- Infers missing schedule patterns
- Suggests reasonable defaults for error handling
- Fills gaps based on orchestration best practices

**User Prompts:**
- Only for information that cannot be determined
- Specific questions with context and examples
- Clear explanation of why each field is needed

### Enhanced Task Types

- **sql**: SQL queries and database operations
- **python**: Python scripts and function calls
- **bash**: Shell commands and scripts
- **copy**: Data movement between systems (ADF Copy Activities)
- **stored_procedure**: Database stored procedure execution
- **notebook**: Jupyter/Databricks notebook execution
- **container**: Docker/container-based execution
- **pipeline**: Sub-pipeline or nested workflow execution
- **http**: HTTP API calls
- **email**: Email notifications
- **file_transfer**: File operations
- **sensor**: Data/file sensors

### FLEX Validation Rules

**Schedule Validation:**
- **Cron expressions**: Must be 5-field format (minute hour day month weekday)
  - Valid: `"0 9 * * *"` (daily at 9 AM), `"0 */6 * * *"` (every 6 hours)
  - Invalid: `"0 9 * *"` (missing weekday), `"60 9 * * *"` (invalid minute)
- **Rate expressions**: Must use format `rate(number unit)`
  - Valid: `"rate(1 day)"`, `"rate(30 minutes)"`, `"rate(2 hours)"`
  - Invalid: `"rate(1)"`, `"every 1 day"`
- **Schedule types**: `cron`, `rate`, `manual`, `event`

**Task Validation:**
- **Task types**: Must be valid enum values (sql, python, bash, etc.)
- **Commands**: Must be appropriate for task type
  - SQL tasks: Must contain SQL keywords (SELECT, INSERT, UPDATE, etc.)
  - Python tasks: Valid Python code or function calls
  - Bash tasks: Valid shell commands
- **Timeouts**: 1 to 86400 seconds (24 hours maximum)
- **Retries**: 0 to 10 retries maximum
- **Retry delay**: 0 to 3600 seconds (1 hour maximum)

**Dependency Validation:**
- **Conditions**: `success`, `failure`, `always`, or `null`
- **Task references**: All upstream/downstream tasks must exist
- **Cycles**: No circular dependencies allowed

**Error Handling Validation:**
- **Failure actions**: `fail`, `continue`, `retry`
- **Email format**: Valid email addresses for notifications
- **Retry limits**: Consistent with task-level retry settings

FLEX is purpose-built for ETL orchestration migration, avoiding the complexity of adapting existing standards that weren't designed for data pipeline use cases. While standards like BPMN exist for general workflow modeling, they require significant learning overhead and don't align with how ETL developers think about data pipelines.

### Parallel Execution in FLEX

FLEX represents parallel execution through **implicit parallelism** using task dependencies:

```json
{
  "tasks": [
    {
      "id": "process_customers",
      "type": "sql",
      "command": "CREATE TABLE processed.customers AS ...",
      "depends_on": []  // No dependencies = can run in parallel
    },
    {
      "id": "process_orders", 
      "type": "sql",
      "command": "CREATE TABLE processed.orders AS ...",
      "depends_on": []  // No dependencies = can run in parallel
    },
    {
      "id": "combine_results",
      "type": "sql",
      "command": "CREATE TABLE summary AS ...",
      "depends_on": [
        {"task_id": "process_customers", "condition": "success"},
        {"task_id": "process_orders", "condition": "success"}
      ]  // Waits for parallel tasks to complete
    }
  ]
}
```

**Key Principles:**
- **Tasks with no dependencies** run in parallel at workflow start
- **Tasks with identical dependencies** run in parallel after dependencies complete
- **Framework generators** optimize parallel execution for target platform capabilities
- **No explicit parallel constructs** needed - dependencies define execution flow

**Framework Mapping:**
- **Airflow**: Independent tasks execute concurrently, task groups for organization
- **Step Functions**: Reconstructed as `Parallel` states with branches
- **Azure Data Factory**: Parallel activities with dependency chains

## FLEX Framework Mapping

FLEX acts as the connector between different orchestration frameworks. Here's how FLEX elements translate:

### FLEX → Airflow

| FLEX Field | Airflow Equivalent | Notes |
|---------------|-------------------|-------|
| `name` | `dag_id` | DAG identifier |
| `description` | `description` | DAG description |
| `schedule.expression` | `schedule_interval` | Converted to Airflow format |
| `schedule.timezone` | `timezone` | DAG timezone |
| `tasks[].id` | `task_id` | Task identifier |
| `tasks[].name` | Task name/description | Human readable name |
| `tasks[].type` | Operator type | `sql`→`RedshiftSQLOperator`, `python`→`PythonOperator` |
| `tasks[].command` | `sql`/`python_callable`/`bash_command` | Task execution code |
| `tasks[].timeout` | `execution_timeout` | Task timeout |
| `tasks[].retries` | `retries` | Retry count |
| `tasks[].depends_on` | `>>` operator | Task dependencies |
| `error_handling.notification_emails` | `email` in default_args | Failure notifications |

### FLEX → Step Functions

| FLEX Field | Step Functions Equivalent | Notes |
|---------------|---------------------------|-------|
| `name` | `stateMachineName` | State machine name |
| `description` | `Comment` | State machine description |
| `schedule` | EventBridge Rule | External scheduling |
| `tasks[].id` | State name | Individual state identifier |
| `tasks[].name` | State comment | Human readable description |
| `tasks[].type` | `Resource` type | `sql`→Lambda/Batch, `python`→Lambda |
| `tasks[].command` | `Parameters` | Passed to resource |
| `tasks[].timeout` | `TimeoutSeconds` | State timeout |
| `tasks[].retries` | `Retry` block | Retry configuration |
| `tasks[].depends_on` | `Next` transitions | State flow control |
| `error_handling` | `Catch` blocks | Error handling states |
```

## Documentation

| File | Purpose | Description |
|------|---------|-------------|
| `README.md` | Main documentation | Complete setup, usage, and API reference |
| `FLEX_SPECIFICATION.md` | FLEX format specification | Complete FLEX format documentation with examples |
| `samples/step_function_jobs/README.md` | Step Functions samples | 6 progressively complex Step Functions definitions |
| `samples/airflow_jobs/README.md` | Airflow samples | 6 progressively complex Airflow DAGs |
| `tests/unit/README.md` | Unit testing guide | Fast, isolated component tests |
| `tests/integration/README.md` | Integration testing guide | End-to-end workflow tests with setup requirements |
| `tests/integration/output/README.md` | Test output structure | Generated test artifacts and cleanup instructions |

## Examples

See the `samples/` directory for complete examples:

- **Step Functions Samples**: 6 progressively complex Step Functions definitions (`samples/step_function_jobs/`)
- **Airflow Samples**: 6 progressively complex Airflow DAGs (`samples/airflow_jobs/`)
- **FLEX Specification**: Complete format documentation with examples (`FLEX_SPECIFICATION.md`)

### Complete Usage Example: Employee Department Analysis Pipeline

**Business Case:** Daily ETL pipeline that analyzes employee data by department, calculates salary statistics, and exports results to S3.

**Data Flow:**
```
employees.csv + departments.csv → Staging Tables → Analytics Summary → S3 Export
```

#### Step 1: Prepare Sample Data

**employees.csv**
```csv
employee_id,name,department,salary,hire_date,status
1001,John Smith,Engineering,75000,2023-01-15,Active
1002,Sarah Johnson,Marketing,65000,2023-02-20,Active
1003,Mike Davis,Engineering,80000,2022-11-10,Active
1004,Lisa Wilson,HR,60000,2023-03-05,Active
```

**departments.csv**
```csv
department,budget,manager
Engineering,500000,Alice Cooper
Marketing,300000,Bob Wilson
HR,200000,Carol Davis
Finance,250000,Dan Miller
```

#### Step 2: Define FLEX Workflow

```json
{
  "name": "employee_department_analysis",
  "description": "Daily ETL pipeline analyzing employee data by department",
  "schedule": {
    "type": "rate",
    "expression": "rate(1 day)",
    "timezone": "UTC"
  },
  "tasks": [
    {
      "id": "load_employees",
      "name": "Load Employee Data",
      "type": "sql",
      "command": "CREATE TABLE staging.employees AS SELECT * FROM raw_data.employees WHERE status = 'Active'",
      "timeout": 1800,
      "retries": 2
    },
    {
      "id": "create_summary",
      "name": "Create Department Summary",
      "type": "sql",
      "command": "CREATE TABLE analytics.department_summary AS SELECT d.department, d.manager, COUNT(e.employee_id) as employee_count, AVG(e.salary) as avg_salary FROM staging.departments d LEFT JOIN staging.employees e ON d.department = e.department GROUP BY d.department, d.manager",
      "timeout": 3600,
      "retries": 3,
      "depends_on": [
        {"task_id": "load_employees", "condition": "success"}
      ]
    }
  ]
}
```

#### Step 3: Convert Using MCP Server

**Convert to Airflow:**
> **User**: "Generate Airflow DAG from this FLEX workflow: {FLEX JSON above}"

**Convert to Step Functions:**
> **User**: "Generate Step Functions state machine from this FLEX workflow: {FLEX JSON above}"

#### Step 4: Expected Results

| department | manager | employee_count | avg_salary |
|------------|---------|----------------|------------|
| Engineering | Alice Cooper | 3 | 75000 |
| Marketing | Bob Wilson | 2 | 66500 |
| HR | Carol Davis | 1 | 60000 |
| Finance | Dan Miller | 1 | 70000 |

**Key Benefits:**
- **Single Source of Truth**: One FLEX workflow definition
- **Multi-Target Deployment**: Same logic deployed to different platforms
- **Production Ready**: Includes error handling, retries, and dependencies

### Validation Error Example
```json
{
  "status": "incomplete",
  "completion_percentage": 0.75,
  "missing_information": "• Schedule: Invalid cron expression. Use format: minute hour day month weekday\n• Task 'process': Command must contain SQL keywords (SELECT, INSERT, UPDATE, etc.)",
  "flex_workflow": {
    "schedule": {
      "expression": "? # REQUIRED: Cron expression (e.g., \"0 9 * * *\" for daily at 9 AM)",
      "_validation": "Cron: \"0 9 * * *\" (daily 9AM) | Rate: \"rate(1 day)\" | Type: cron, rate, manual, event"
    }
  }
}
```

### FLEX Schedule Expression Conversion

| FLEX Format | Airflow | Step Functions |
|----------------|---------|----------------|
| `"0 9 * * *"` (cron) | `"0 9 * * *"` | EventBridge: `cron(0 9 * * ? *)` |
| `"0 */6 * * *"` (cron) | `"0 */6 * * *"` | EventBridge: `cron(0 */6 * * ? *)` |
| `"rate(1 day)"` | `@daily` | EventBridge: `rate(1 day)` |
| `"rate(1 hour)"` | `@hourly` | EventBridge: `rate(1 hour)` |
| `"manual"` | `None` | Manual execution only |

### FLEX Validation Examples

**Valid FLEX Workflow:**
```json
{
  "name": "etl_pipeline",
  "schedule": {
    "type": "cron",
    "expression": "0 9 * * *",
    "timezone": "UTC"
  },
  "tasks": [
    {
      "id": "extract_data",
      "name": "Extract Customer Data",
      "type": "sql",
      "command": "SELECT * FROM customers WHERE updated_date >= CURRENT_DATE",
      "timeout": 3600,
      "retries": 2
    }
  ],
  "error_handling": {
    "on_failure": "fail",
    "notification_emails": ["team@company.com"]
  }
}
```

**Invalid FLEX Examples:**
```json
{
  "schedule": {
    "type": "cron",
    "expression": "0 25 * *"  // ❌ Missing weekday field
  },
  "tasks": [
    {
      "type": "invalid_type",  // ❌ Not a valid TaskType
      "command": "?",          // ❌ Placeholder not replaced
      "timeout": 90000,        // ❌ Exceeds 24 hour limit
      "retries": 15            // ❌ Exceeds 10 retry limit
    }
  ],
  "error_handling": {
    "on_failure": "maybe",           // ❌ Invalid failure action
    "notification_emails": ["invalid-email"]  // ❌ Invalid email format
  }
}
```

## Organizational Context

The server supports optional **context files** that provide organizational standards, patterns, and rules to the LLM for consistent code generation.

### Context File (Optional)

**Create a context file** (e.g., `context.txt`):

```text
# ETL Context - Data Engineering Team

## Naming Standards
- Workflows: data_pipeline_{purpose}_{env}
- Tasks: task_{source}_{action}_{destination}
- Files: {name}_dag.py (Airflow), sm_{name} (Step Functions)

## Infrastructure
- Production Redshift: data-warehouse cluster
- S3 buckets: s3://company-data-{raw|processed|archive}/
- Lambda timeout: 900s, SQL timeout: 3600s

## Business Rules
- Daily ETL runs at 2 AM UTC
- Customer PII must be encrypted
- All production jobs retry 3 times
- Email notifications: data-team@company.com

## Common Patterns
- Extract from source → Transform in Lambda → Load to Redshift
- Use parameterized queries for date ranges
- Parallel processing for independent data sources
```

### Usage Examples

**With context file:**
> **User**: "Convert jobs in ./workflows to airflow using context from ./context.txt"

**Without context file (uses defaults):**
> **User**: "Convert jobs in ./workflows to airflow"

### Benefits

- **🎯 Consistency**: LLM applies all organizational context uniformly
- **📝 Flexibility**: Single file covers naming, infrastructure, business rules, and patterns
- **🔄 Version Control**: Context files can be versioned and shared across teams
- **⚡ Simplicity**: No complex configuration - just plain text
- **🚀 Extensibility**: Add any organizational context without code changes



## Architecture

```
awslabs/etl_replatforming_mcp_server/
├── models/           # FLEX workflow models
├── services/         # Bedrock AI service
├── parsers/          # Source framework parsers
├── generators/       # Target framework generators
├── validators/       # Workflow validation
└── server.py         # MCP server implementation
```

### Core Functions

**Parsing & Validation:**
- `_parse_to_flex_workflow()` - Parse source → FLEX with validation
- `_validate_flex_workflow()` - Check FLEX completeness
- `_enhance_with_bedrock()` - AI enhancement using original source
- `_prompt_user_for_missing()` - Generate user prompts

**Generation:**
- `_generate_from_flex_workflow()` - Generate target code (assumes complete FLEX)

**Directory-Based Tools:**
- `parse-to-flex` - Directory → FLEX documents with user interaction
- `convert-etl-workflow` - Directory → FLEX → Target with user interaction
- `generate-from-flex` - FLEX directory → Target with validation

**Single Workflow Tools:**
- `parse-single-workflow-to-flex` - Individual workflow → FLEX with validation
- `convert-single-etl-workflow` - Individual workflow → FLEX → Target (complete conversion)
- `generate-single-workflow-from-flex` - FLEX workflow → Target framework code

## Development

### Adding New Frameworks

**Source Framework:**
1. Create `parsers/new_framework_parser.py`
2. Implement `WorkflowParser` interface
3. Register in `server.py`

**Target Framework:**
1. Create `generators/new_framework_generator.py`
2. Implement `generate()` method
3. Register in `server.py`

### Process Flow Guidelines

**For Parsing:**
- Extract as much as possible from source code
- Let Bedrock fill gaps using original source context
- Only prompt users for information that cannot be inferred

**For Generation:**
- Assume FLEX workflow is complete and valid
- No additional validation or user prompts
- Focus on accurate target framework code generation

**For User Interaction:**
- Provide specific, actionable prompts
- Explain why each piece of information is needed
- Allow users to terminate by not responding

### Testing

#### Installation

```bash
# Using Makefile (recommended)
make install  # Installs all dependencies including tests

# Manual approach
pip install -r requirements.txt  # All dependencies
# Or install test dependencies separately
pip install pytest pytest-asyncio pytest-cov
```

#### Running Tests

```bash
# Using Makefile (recommended)
make test  # Runs unit tests with proper setup

# Manual approach
python -m pytest tests/unit/ -v  # Unit tests only (fast)
python -m pytest --cov=awslabs.etl_replatforming_mcp_server --cov-report=term-missing  # With coverage
```

#### Integration Tests

**End-to-End MCP Server Test:**
```bash
# Set AWS profile if using named profiles
export AWS_PROFILE=your-bedrock-profile

# Run integration test (spawns its own MCP server)
python tests/integration/test_mcp_server_e2e.py
```

**What it tests:**
- Spawns fresh MCP server process via stdio protocol
- Tests all single-workflow tools with sample data
- Verifies complete request/response cycle
- Creates timestamped output directory with results
- Handles AWS credentials through environment inheritance

**See `tests/unit/README.md` and `tests/integration/README.md` for detailed testing instructions.**

#### Test Categories

**Unit Tests** (`tests/unit/`):
- Fast, isolated component tests
- No external dependencies required
- `test_llm_config.py`, `test_generators.py`, `test_parsers.py`, etc.

**Integration Tests** (`tests/integration/`):
- End-to-end workflow tests using real sample data
- **Requires MCP server to be running locally**
- `test_all_conversions.py` - Complete Step Functions → Airflow conversion tests
- See `tests/integration/README.md` for setup requirements

#### Test Configuration

The project includes `pytest.ini` for test configuration:
- Automatic async test support
- Verbose output by default
- Test discovery in `tests/` directory

## Dependencies

See `requirements.txt` for complete dependency list:

**Core Dependencies:**
- `fastmcp>=0.5.0` - MCP server framework
- `pydantic>=2.0.0` - Data validation
- `boto3>=1.26.0` - AWS SDK for Bedrock integration
- `loguru>=0.7.0` - Logging

**Test Dependencies:**
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `pytest-cov>=4.0.0` - Coverage reporting

## License

Licensed under the Apache License, Version 2.0.