# ETL Replatforming MCP Server

**The intelligent, cost-effective solution for ETL framework migration with AI-enhanced parsing and universal workflow conversion.**

MCP server for converting ETL orchestration code between frameworks using FLEX (Framework for Linking ETL eXchange) with validation and user interaction.

## 🚀 Why This Project?

**ETL framework migration is expensive, error-prone, and time-consuming.** This project solves that with:

- **💰 Cost-Optimized AI Usage**: Hybrid approach - deterministic parsing first, AI only for gaps. Significantly reduces LLM costs compared to "AI-everything" approaches
- **🤖 Targeted AI Enhancement**: AI fills specific gaps (schedules, placeholders) rather than handling entire conversions
- **🎯 Zero Manual Rewrites**: Automated conversion preserves complex pipeline logic and dependencies
- **🔄 Universal Framework Support**: One tool handles Airflow ↔ Step Functions ↔ Azure Data Factory ↔ Future frameworks
- **🏢 Organizational Standards**: Apply your naming conventions, coding patterns, and business rules to generated code
- **⚡ Production-Ready**: Handles real-world complexity with validation, error handling, and user interaction
- **🛡️ Migration Safety**: FLEX intermediate format ensures semantic preservation across frameworks
- **🏗️ Enterprise-Grade Code Quality**: Modular architecture, comprehensive testing (68+ tests), centralized configuration, professional logging

## Overview

This server provides intelligent ETL framework conversion through a hybrid multi-stage process:

```
Source Framework → DETERMINISTIC PARSE → Validate → [AI ENHANCEMENT] → Validate → Complete FLEX
                                                           ↓                           ↓
                                                   (with confidence)          Target Framework
```

**Hybrid Parsing Approach:**
- **Deterministic parsing** handles 80-90% of standard patterns (fast, reliable, free)
- **AI enhancement** fills complex gaps like TaskGroup dependencies (intelligent, cost-effective)
- **Confidence tracking** shows AI parsing quality in FLEX documents
- **Structured Enhancement**: FLEX provides organized context for targeted AI improvements

### Why Hybrid vs Pure LLM?

**Even with perfect context documents, hybrid parsing is superior because:**

#### **1. Structural Consistency & Reproducibility**

**Hybrid Approach:**
```python
# Deterministic parsing - identical input always produces identical output
def parse_airflow_task(node):
    if node.func.attr == 'BashOperator':
        return {
            "type": "bash",
            "command": extract_bash_command(node),
            "retries": extract_retries(node) or 0
        }
```

**Pure LLM with Context:**
```text
Context: "BashOperator tasks should have type 'bash' and extract bash_command parameter"
```

**Problem**: Even with perfect context, LLM may produce variations:
- Run 1: `{"type": "bash", "command": "echo hello"}`
- Run 2: `{"type": "shell", "command": "echo hello"}` (synonym confusion)
- Run 3: `{"type": "bash", "cmd": "echo hello"}` (parameter name variation)

**Real Evidence**: Integration logs show deterministic parsing achieved 95.7% completeness consistently across multiple workflows - same input, same result every time.

#### **2. Complex AST Pattern Recognition**

**Hybrid Approach:**
```python
# Handles complex nested AST patterns reliably
def extract_dependencies(self, dag_node):
    for node in ast.walk(dag_node):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.RShift):
            # Precisely identifies >> operators in AST
            left = self._extract_task_refs(node.left)
            right = self._extract_task_refs(node.right)
            return create_dependency(left, right)
```

**Pure LLM Challenge:**
```python
# Complex Airflow dependency patterns
task_a >> [task_b, task_c] >> task_d
[task_e, task_f] >> task_g
task_h >> task_i if condition else task_j
```

**Context Document would need:**
```text
"When you see >>, create dependencies. Handle lists on both sides.
Handle conditional dependencies. Handle nested expressions..."
```

**LLM Issues:**
- May miss subtle AST structures (nested lists, conditional expressions)
- Inconsistent handling of edge cases
- Cannot guarantee all syntactic variations are covered

#### **3. Multi-Layer Validation & Error Detection**

**Hybrid Approach:**
```python
# Deterministic validation catches structural errors
def validate_flex_workflow(workflow):
    errors = []

    # Guaranteed to catch missing required fields
    if not workflow.schedule:
        errors.append("Missing schedule")

    # Precise dependency validation
    for task in workflow.tasks:
        for dep in task.depends_on:
            if dep.task_id not in task_ids:
                errors.append(f"Invalid dependency: {dep.task_id}")

    return errors
```

**Pure LLM:**
- May miss validation rules despite context
- Inconsistent error detection
- Cannot guarantee all validation logic is applied

#### **4. Targeted AI Enhancement vs Overwhelming Context**

**Hybrid Approach:**
```python
# AI gets focused, specific task with structured context
if workflow.is_incomplete():
    prompt = f"""
    Add missing schedule for this ETL workflow:

    Workflow: {workflow.name}
    Tasks: {[t.name for t in workflow.tasks]}
    Context: {organizational_patterns}

    Only add the schedule field.
    """
```

**Pure LLM:**
```text
# Overwhelming context document (10,000+ tokens)
"Parse this entire Airflow DAG. Apply these 50 naming conventions,
100 transformation patterns, complex dependency rules,
framework mappings, error handling standards..."
```

**LLM Attention Issues:**
- Context dilution - important rules get lost in large documents
- Rule conflicts - LLM struggles to prioritize conflicting guidelines
- Cognitive overload - too many simultaneous constraints

#### **5. Performance & Reliability at Scale**

**Real Example from Integration Logs:**
```
✅ Workflow complete (100.0%) after deterministic parsing - no AI enhancement needed
🤖 Workflow incomplete (95.7%) - invoking Bedrock AI enhancement
```

**Hybrid Benefits:**
- **Fast processing**: 2 workflows needed no AI (instant completion)
- **Selective enhancement**: Only incomplete workflows trigger AI
- **Predictable performance**: Deterministic parsing always completes in milliseconds

**Pure LLM:**
- Every workflow requires full LLM processing
- Unpredictable response times
- Risk of rate limiting or service unavailability

#### **6. Framework-Specific Expertise**

**Hybrid Example:**
```python
# Deterministic parser has deep framework knowledge
def parse_step_functions_map_state(state_def):
    return {
        "type": "for_each",
        "loop": {
            "type": "for_each",
            "items": {
                "source": "parameter",
                "path": state_def.get("ItemsPath", "$")
            },
            "max_concurrency": state_def.get("MaxConcurrency", 0)
        }
    }
```

**Pure LLM Challenge:**
Even with context explaining Map states, LLM might:
- Miss subtle JSON path syntax (`$.items[*]`)
- Incorrectly handle MaxConcurrency defaults
- Confuse Map states with Parallel states

#### **7. Debugging & Transparency**

**Hybrid Approach:**
```json
{
  "parsing_info": {
    "parsing_completeness": 0.957,
    "parsing_method": "hybrid",
    "llm_enhancements": ["Added workflow schedule"],
    "ignored_elements": [
      {
        "element": "custom_sensor",
        "reason": "Sensors not supported",
        "suggestions": ["Convert to polling task"]
      }
    ]
  }
}
```

**Benefits:**
- Clear separation: what was parsed deterministically vs AI-enhanced
- Specific enhancement tracking
- Actionable suggestions for ignored elements

**Pure LLM:**
- Black box processing
- Unclear what was inferred vs extracted
- Difficult to debug incorrect conversions

#### **8. Incremental Improvement**

**Hybrid Approach:**
```python
# Can enhance deterministic parsing without retraining
def enhanced_airflow_parser():
    # Add new operator support
    if node.func.attr == 'KubernetesPodOperator':
        return parse_kubernetes_task(node)  # New deterministic rule
```

**Pure LLM:**
- Requires retraining or prompt engineering for new patterns
- Risk of regression when adding new capabilities
- Harder to incrementally improve specific parsing areas

#### **Real-World Evidence**

Integration test logs demonstrate hybrid approach working perfectly:

- **6 workflows processed**
- **2 workflows (33%) complete** with deterministic parsing only
- **4 workflows (67%) needed AI enhancement** for missing schedules only
- **95.7% average completeness** before AI enhancement

This shows deterministic parsing handles the vast majority of complexity reliably, with AI filling only specific gaps.

#### **Conclusion: Why Hybrid Wins Even With Perfect Context**

Even with comprehensive context documents, hybrid parsing provides:
- **Guaranteed consistency** for structural patterns
- **Precise AST/JSON parsing** that LLMs cannot match
- **Targeted AI usage** with focused prompts
- **Transparent debugging** with clear enhancement tracking
- **Incremental improvement** without retraining
- **Predictable performance** at scale

**Pure LLM Approach:**
```
Airflow Code → [Black Box LLM] → Step Functions JSON
```

**Hybrid Approach (Structured Enhancement):**
```
Airflow Code → Deterministic Parse → FLEX → [Targeted AI Enhancement] → Complete FLEX → Deterministic Generation → Step Functions JSON
```

The hybrid approach leverages each method's strengths while avoiding their weaknesses - deterministic parsing for reliable pattern matching, AI for intelligent semantic gap-filling. This follows **AI engineering best practices**: use AI for what it's good at (filling semantic gaps) while using deterministic methods for what they're good at (reliable pattern matching and code generation).

The enhanced FLEX model now captures **universal orchestration patterns** while remaining framework-agnostic, significantly improving generator output quality.

## ✨ Key Features

### 🔄 Universal Framework Conversion
- **Bidirectional Support**: Convert between any supported frameworks (Airflow ↔ Step Functions ↔ Azure Data Factory)
- **Semantic Preservation**: Maintains workflow logic, dependencies, error handling, and scheduling across platforms
- **Complex Pipeline Support**: Handles nested workflows, conditional branching, parallel execution, and advanced orchestration patterns
- **Python Code Extraction**: Automatically extracts Python functions from Airflow DAGs and creates standalone scripts for Step Functions Glue jobs and ADF custom activities

### 🤖 Hybrid Parsing Architecture
- **Deterministic Foundation**: AST and regex parsing handles 80-90% of standard patterns
- **AI Enhancement**: Bedrock fills complex gaps (TaskGroups, dynamic dependencies, custom operators)
- **Cost Optimization**: AI only used when deterministic parsing is incomplete
- **Confidence Tracking**: Every AI enhancement includes confidence scores (0.0-1.0)
- **Quality Assurance**: High confidence (>0.8) indicates production-ready conversions
- **Structured Enhancement**: FLEX provides organized context for targeted AI improvements

### 🎯 Production-Grade Reliability
- **Comprehensive Validation**: Catches missing schedules, invalid dependencies, malformed expressions
- **Clear Placeholders**: Returns FLEX documents with "?" markers for missing information
- **Two-Step Process**: Parse to FLEX, fill placeholders, generate target framework
- **External Script Generation**: Creates production-ready Python files with proper imports, argument parsing, and error handling for orchestration platforms
- **Centralized Configuration**: Constants-driven architecture with 40+ configurable parameters
- **Structured Logging**: Professional logging format with rotation and configurable levels

### 🏗️ FLEX Intermediate Format
- **Framework-Agnostic**: Universal representation that works with any orchestration platform
- **Human-Readable**: JSON format that's easy to understand, modify, and version control
- **Standards-Based**: Built on proven workflow representation principles
- **Future-Proof**: Easy to extend for new frameworks (Prefect, Dagster, etc.)

### 🔧 Developer Experience
- **MCP Integration**: Works seamlessly with Claude Desktop and other MCP clients
- **Extensible Architecture**: Simple interfaces for adding new source/target frameworks
- **Comprehensive Testing**: Unit and integration tests with real-world sample workflows (68+ test cases)
- **Rich Documentation**: Complete examples, API reference, and troubleshooting guides
- **Modular Design**: Utility classes for workflow processing, Bedrock operations, and directory handling

## Architecture

### Core Components

**Server Layer (`server.py`)**
- Main MCP server with 12 tool endpoints
- Centralized configuration management
- Structured logging with rotation
- Global LLM configuration handling

**Utility Classes**
- `WorkflowProcessor`: Workflow processing logic, AI enhancement decisions, status determination
- `BedrockHelpers`: Bedrock operations, prompt generation, confidence calculation
- `DirectoryProcessor`: Batch processing of workflow directories
- `ResponseFormatter`: Consistent response formatting across tools

**Service Layer**
- `BedrockService`: AWS Bedrock integration with retry logic
- `WorkflowValidator`: FLEX workflow validation and completeness checking

**Configuration**
- `constants.py`: 40+ centralized constants for timeouts, retries, confidence thresholds
- `LLMConfig`: Pydantic model for LLM configuration validation

**Abstract Base Classes**
- `WorkflowParser`: 16 abstract methods for consistent parser implementation
- `BaseGenerator`: 13 abstract methods for consistent generator implementation

### Quality Improvements

**Code Structure**
- Eliminated 150+ line functions by breaking into focused 20-30 line methods
- Removed hardcoded values - all magic numbers centralized in constants
- Standardized package structure (removed conflicting setup.py)
- Professional logging format without excessive emojis

**Testing**
- 68+ unit tests covering all new utility classes and methods
- Comprehensive test coverage for abstract base classes
- Mock-based testing for external dependencies
- Integration tests with real workflow samples

## Supported Frameworks

| Framework | Parser | Generator | Python Scripts | Status |
|-----------|--------|-----------|----------------|--------|
| Step Functions | ✅ | ✅ | ✅ Glue Jobs | Complete |
| Airflow | ✅ | ✅ | ✅ Extraction | Complete |
| Azure Data Factory | ✅ | 🚧 | ✅ Ready for Generator | Parser Complete |
| Prefect | 🚧 | 🚧 | 🚧 | Planned |
| Dagster | 🚧 | 🚧 | 🚧 | Planned |

## Task Type Mapping

**The FLEX intermediate format uses standardized task types that map to framework-specific implementations:**

### Source Framework → FLEX Task Type Mapping

| Source Framework | Source Task Type | FLEX Task Type | Notes |
|------------------|------------------|----------------|---------|
| **Airflow** | `PythonOperator` | `python` | Extracts Python functions to external files |
| | `BashOperator` | `bash` | Shell command execution |
| | `RedshiftSQLOperator` | `sql` | SQL query execution |
| | `PostgresOperator` | `sql` | SQL query execution |
| | `MySQLOperator` | `sql` | SQL query execution |
| | `BranchPythonOperator` | `python` + `branch` | Splits into execution task + branching logic |
| | `EmailOperator` | `email` | Email notifications |
| | `HttpOperator` | `http` | HTTP API calls |
| | `TaskGroup` (range) | `for_each` | Loop iteration patterns |
| | `TaskGroup` (enumerate) | `for_each` | Loop iteration patterns |
| | Dynamic task creation | `for_each` | Runtime task generation |
| **Step Functions** | `Task` (Lambda) | `python` | AWS Lambda function invocation |
| | `Task` (Batch) | `container` | AWS Batch job execution |
| | `Task` (Redshift Data) | `sql` | SQL query via Redshift Data API |
| | `Task` (SNS) | `email` | SNS notification publishing |
| | `Task` (S3) | `file_transfer` | S3 file operations |
| | `Task` (Generic AWS) | `bash` | Generic AWS service calls |
| | `Choice` | `branch` | Conditional state transitions |
| | `Map` | `for_each` | Parallel item processing |
| | `Parallel` | `parallel` | Parallel branch execution |
| | `Pass` | `dummy` | No-operation state |
| **Azure Data Factory** | `Copy Activity` | `copy` | Data copy operations |
| | `Custom Activity` | `python` | Custom Python/script execution |
| | `Stored Procedure` | `sql` | SQL stored procedure calls |
| | `Web Activity` | `http` | HTTP API calls |
| | `If Condition` | `branch` | Conditional activity execution |
| | `ForEach` | `for_each` | Loop iteration over items |
| | `Execute Pipeline` | `parallel` | Nested pipeline execution |

### FLEX Task Type → Target Framework Mapping

| FLEX Task Type | Airflow Target | Step Functions Target | Azure Data Factory Target |
|----------------|----------------|----------------------|---------------------------|
| `python` | `PythonOperator` | Glue Python Shell Job | Custom Activity (Python) |
| `bash` | `BashOperator` | AWS Batch Job | Custom Activity (Script) |
| `sql` | `RedshiftSQLOperator` | Redshift Data API Task | Stored Procedure Activity |
| `container` | `DockerOperator` | AWS Batch Job | Container Activity |
| `copy` | `S3ToRedshiftOperator` | S3 + Redshift Tasks | Copy Activity |
| `file_transfer` | `S3FileTransformOperator` | S3 API Tasks | Copy Activity |
| `email` | `EmailOperator` | SNS Publish Task | Web Activity (Email API) |
| `http` | `HttpOperator` | HTTP API Task | Web Activity |
| `branch` | `BranchPythonOperator` | Choice State | If Condition Activity |
| `for_each` | `TaskGroup` (loop) | Map State | ForEach Activity |
| `parallel` | `[task1, task2]` syntax | Parallel State | Execute Pipeline |
| `wait` | `TimeDeltaSensor` | Wait State | Wait Activity |
| `dummy` | `DummyOperator` | Pass State | Wait Activity (0 seconds) |
| `sensor` | `FileSensor` | Custom Lambda Check | Lookup Activity |
| `check` | `SQLCheckOperator` | Custom Validation | Validation Activity |
| `validate` | `PythonOperator` | Custom Lambda | Custom Activity |
| `cleanup` | `BashOperator` | S3 Delete Task | Delete Activity |

### Enhanced FLEX Features

**Universal Orchestration Features (Optional):**
- **Task Groups**: Logical organization of related tasks
- **Trigger Rules**: Task execution dependencies (all_success, one_failed, etc.)
- **Connection References**: Database and service connection management
- **Enhanced Scheduling**: Time-based, data-based, and event-based triggers
- **Batch Processing**: Parallel execution control and concurrency limits
- **Monitoring Integration**: Custom metrics and observability hooks

**✅ Backward Compatibility:** All enhanced features are optional - existing workflows continue to work without modification.

### Task Type Categories

**Core Processing Tasks:**
- `python` - Python script execution with external file support
- `bash` - Shell command execution
- `sql` - SQL query execution across databases
- `container` - Docker/container-based processing

**Data Movement Tasks:**
- `copy` - Data copy/transfer operations
- `file_transfer` - File system operations
- `extract` - Data extraction from sources
- `transform` - Data transformation logic
- `load` - Data loading to destinations

**Control Flow Tasks:**
- `branch` - Conditional branching (Choice/If)
- `for_each` - Loop iteration (Map/ForEach)
- `while` - While loop patterns
- `parallel` - Parallel execution
- `wait` - Delay/wait operations

**Integration Tasks:**
- `email` - Email notifications
- `http` - HTTP API calls
- `webhook` - Webhook invocations
- `sns` - SNS notifications
- `sqs` - SQS operations

**Utility Tasks:**
- `sensor` - Wait for conditions
- `check` - Data quality checks
- `validate` - Validation operations
- `cleanup` - Cleanup operations
- `dummy` - No-operation placeholders

### Framework-Specific Notes

**Airflow → Step Functions:**
- Python functions extracted to external Glue Python Shell scripts
- TaskGroups converted to Map states for parallel processing
- BranchPythonOperator logic converted to Choice state conditions
- Dependencies converted to Next/End transitions

**Step Functions → Airflow:**
- Map states converted to TaskGroups with loop logic
- Choice states converted to BranchPythonOperator
- Parallel states converted to parallel task dependencies
- AWS service tasks mapped to equivalent Airflow operators

**Python File Extraction (Airflow → Orchestration Platforms):**
- Airflow: Compute + Orchestration (runs Python inline)
- Step Functions/ADF: Pure Orchestration (needs external scripts)
- System automatically extracts Python functions and creates standalone files
- Generated files include proper imports, argument parsing, and error handling
- Files stored in `outputs/{conversion_output}/glue_python_shell_jobs/` directory
- **AWS Glue Integration**: Automatically generates Glue Python Shell job definitions for each script

## Task Type Validation

**All task types are validated against the centralized task type constants:**

```python
# Valid FLEX task types (25+ types across 5 categories)
from awslabs.etl_replatforming_mcp_server.models.task_types import (
    get_all_task_types,
    is_valid_task_type,
    requires_script_file
)

# Check if task type is valid
if is_valid_task_type('python'):
    print("Valid task type")

# Check if task type needs external script
if requires_script_file('python'):
    print("Needs script_file field")
```

## Enhanced FLEX Format Example

```json
{
  "name": "enhanced_etl_pipeline",
  "description": "ETL pipeline with enhanced orchestration features",
  "schedule": {
    "type": "cron",
    "expression": "0 2 * * *",
    "timezone": "UTC",
    "data_triggers": [
      {
        "trigger_type": "file",
        "target": "/data/incoming/customers.csv",
        "poke_interval": 300,
        "timeout": 3600
      }
    ],
    "catchup": false,
    "max_active_runs": 1
  },
  "task_groups": [
    {
      "group_id": "data_extraction",
      "tooltip": "Extract data from multiple sources"
    }
  ],
  "connections": {
    "postgres_prod": "postgres",
    "s3_data_lake": "s3"
  },
  "tasks": [
    {
      "id": "extract_customers",
      "name": "Extract Customer Data",
      "type": "sql",
      "command": "SELECT * FROM customers WHERE updated_date >= CURRENT_DATE - 1",
      "connection_id": "postgres_prod",
      "task_group": {
        "group_id": "data_extraction"
      },
      "trigger_rule": "all_success",
      "batch_size": 1000,
      "monitoring_metrics": ["records_processed", "execution_time"]
    }
  ]
}
```

## Enhanced Orchestration Features

### ✅ **Optional Enhancement Fields**

These fields improve generator quality when present but don't break functionality when missing:

**Task-Level Enhancements:**
- `connection_id`: Database/service connection reference
- `trigger_rule`: Task execution dependencies (Airflow: `all_success`, `one_failed`, etc.)
- `batch_size`: Parallel processing concurrency limit
- `monitoring_metrics`: Custom metrics to publish
- `task_group`: Logical grouping information

**Workflow-Level Enhancements:**
- `task_groups`: Logical task organization
- `connections`: Connection ID to type mapping
- `schedule.data_triggers`: File/data availability triggers
- `schedule.catchup`: Backfill configuration
- `schedule.max_active_runs`: Concurrent execution limit

### 🎯 **Framework-Specific Usage**

**Airflow Generator:**
- Uses `connection_id` for operator connection parameters
- Creates TaskGroup definitions from `task_groups`
- Adds FileSensor comments for `data_triggers`
- Uses `trigger_rule` for task execution logic

**Step Functions Generator:**
- Uses `connection_id` for AWS resource parameters (cluster:database)
- Uses `batch_size` for Map state MaxConcurrency
- Embeds connection info in resource ARNs

**Azure Data Factory Generator:**
- Maps `connection_id` to linkedServiceName references
- Uses `batch_size` for ForEach batchCount
- Creates logical groupings from ForEach activities

## Adding New Framework Support

**The server uses a plugin architecture with abstract base classes that enforce complete, consistent implementations.**

### Implementing a New Parser

**All parsers must inherit from `WorkflowParser` and implement ALL 11 required methods:**

```python
from awslabs.etl_replatforming_mcp_server.parsers.base_parser import WorkflowParser
from awslabs.etl_replatforming_mcp_server.models.flex_workflow import FlexWorkflow

class MyFrameworkParser(WorkflowParser):
    """Parser for MyFramework workflows"""

    def parse_code(self, input_code: str) -> FlexWorkflow:
        """Main entry point - parse raw code to FLEX format

        Called by: Server's main conversion pipeline
        Must return: Complete FlexWorkflow with parsing_info populated
        """
        # Your implementation here
        pass

    def detect_framework(self, input_code: str) -> bool:
        """Detect if input matches this framework

        Called by: Auto-detection system for directory processing
        Must return: True if input_code is valid for this framework
        """
        # Check for framework-specific patterns
        return "from myframework" in input_code

    def parse_metadata(self, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract workflow metadata (name, description, tags)

        Called by: parse_code() to build FlexWorkflow metadata
        Must return: Dict with 'name', 'description', 'tags' keys
        """
        pass

    def parse_tasks(self, source_data: Dict[str, Any]) -> List[Task]:
        """Extract all tasks from source workflow

        Called by: parse_code() to build FlexWorkflow.tasks
        Must return: List of Task objects with id, name, type, parameters
        """
        pass

    def parse_schedule(self, source_data: Dict[str, Any]) -> Optional[Schedule]:
        """Extract scheduling configuration

        Called by: parse_code() to build FlexWorkflow.schedule
        Must return: Schedule object or None if not available
        """
        pass

    def parse_error_handling(self, source_data: Dict[str, Any]) -> Optional[ErrorHandling]:
        """Extract error handling policies

        Called by: parse_code() to build FlexWorkflow.error_handling
        Must return: ErrorHandling object or None if not available
        """
        pass

    def parse_dependencies(self, source_data: Dict[str, Any]) -> List[TaskDependency]:
        """Extract task execution dependencies

        Called by: parse_code() to build task dependency relationships
        Must return: List of TaskDependency objects
        """
        pass

    def parse_loops(self, source_data: Dict[str, Any]) -> Dict[str, TaskLoop]:
        """Extract loop/iteration constructs

        Called by: parse_code() for workflows with iteration patterns
        Must return: Dict mapping task_id to TaskLoop, empty dict if none
        """
        return {}  # Return empty dict if framework doesn't support loops

    def parse_conditional_logic(self, source_data: Dict[str, Any]) -> List[Task]:
        """Extract branch/choice logic

        Called by: parse_code() for workflows with conditional execution
        Must return: List of choice/branch Task objects, empty list if none
        """
        return []  # Return empty list if no conditional logic

    def parse_parallel_execution(self, source_data: Dict[str, Any]) -> List[Task]:
        """Extract parallel execution patterns

        Called by: parse_code() for workflows with parallel tasks
        Must return: List of parallel Task objects, empty list if none
        """
        return []  # Return empty list if no parallel execution

    def validate_input(self, input_code: str) -> bool:
        """Validate input format before parsing

        Called by: parse_code() before processing begins
        Must return: True if input is valid, False otherwise
        """
        # Validate syntax, required elements, etc.
        return True

    def get_parsing_completeness(self, flex_workflow: FlexWorkflow) -> float:
        """Calculate parsing completeness percentage

        Called by: parse_code() to populate parsing_info.parsing_completeness
        Must return: Float between 0.0-1.0 (should be >= 0.8 for quality)
        """
        # Calculate based on required vs optional fields populated
        return 0.95  # Example: 95% complete

    def parse_task_groups(self, source_data: Dict[str, Any]) -> List[TaskGroup]:
        """Extract task groups/logical groupings

        Called by: parse_code() to extract task organization
        Must return: List of TaskGroup objects, empty list if none
        """
        pass

    def parse_connections(self, source_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract connection references

        Called by: parse_code() to extract connection mappings
        Must return: Dict mapping connection_id to connection_type
        """
        pass

    def parse_trigger_rules(self, source_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract task trigger rules

        Called by: parse_code() to extract execution dependencies
        Must return: Dict mapping task_id to trigger_rule
        """
        pass

    def parse_data_triggers(self, source_data: Dict[str, Any]) -> List[TriggerConfig]:
        """Extract data availability triggers

        Called by: parse_code() to extract sensor configurations
        Must return: List of TriggerConfig objects, empty list if none
        """
        pass

## Testing

### Comprehensive Test Suite

The project includes 68+ unit tests covering all components:

```bash
# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/unit/utils/ -v          # Test utility classes
pytest tests/unit/models/ -v         # Test FLEX models
pytest tests/unit/parsers/ -v        # Test framework parsers
pytest tests/unit/generators/ -v     # Test framework generators
pytest tests/integration/ -v         # Test end-to-end workflows
```

### Test Coverage

**New Utility Classes (100% coverage):**
- `WorkflowProcessor`: 12 test methods covering AI decisions, logging, status determination
- `BedrockHelpers`: 8 test methods covering prompt generation, confidence calculation
- `ServerFunctions`: 15 test methods covering refactored server functions
- `Constants`: 3 test methods validating constant definitions

**Abstract Base Classes:**
- `WorkflowParser`: Tests for all 16 abstract methods
- `BaseGenerator`: Tests for all 13 abstract methods

**Integration Tests:**
- Real workflow samples from Step Functions, Airflow, Azure Data Factory
- End-to-end conversion testing
- Error handling and edge case validation

### Running Tests

```bash
# Install test dependencies
uv sync --dev

# Run tests with coverage
pytest tests/ --cov=awslabs.etl_replatforming_mcp_server --cov-report=html

# Run specific test file
pytest tests/unit/utils/test_workflow_processor.py -v
```

## Migration Guide

### For Existing Users

**No action required** - enhanced features are fully backward compatible:

```python
# Existing workflows continue to work unchanged
workflow = FlexWorkflow(
    name="existing_workflow",
    tasks=[Task(id="task1", type="python", command="print('hello')")]
)

# Enhanced features are optional improvements
enhanced_workflow = FlexWorkflow(
    name="enhanced_workflow",
    tasks=[Task(
        id="task1",
        type="sql",
        command="SELECT * FROM customers",
        connection_id="postgres_prod"  # Optional enhancement
    )],
    task_groups=[TaskGroup(group_id="data_processing")]  # Optional enhancement
)
```

### For Framework Developers

Implement optional enhancement methods in generators:

```python
class MyFrameworkGenerator(BaseGenerator):
    # Required methods (unchanged)
    def generate(self, workflow): pass
    def generate_task(self, task, workflow): pass

    # Optional enhancement methods
    def generate_task_groups(self, workflow):
        if workflow.task_groups:
            # Generate framework-specific grouping
            return self._create_groups(workflow.task_groups)
        return None  # Graceful fallback
```
```

### Implementing a New Generator

**All generators must inherit from `BaseGenerator` and implement ALL 12 required methods:**

```python
from awslabs.etl_replatforming_mcp_server.generators.base_generator import BaseGenerator
from awslabs.etl_replatforming_mcp_server.models.flex_workflow import FlexWorkflow

class MyFrameworkGenerator(BaseGenerator):
    """Generator for MyFramework workflows"""

    def generate(self, workflow: FlexWorkflow, context_document: Optional[str] = None,
                llm_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Main entry point - generate framework code from FLEX

        Called by: Server's main conversion pipeline
        Must return: Dict with 'content' (generated code) and 'metadata'
        """
        # Your implementation here
        pass

    def get_supported_task_types(self) -> List[str]:
        """List task types this generator supports

        Called by: Validation system to check FLEX compatibility
        Must return: List of task type strings (e.g., ['bash', 'sql', 'copy'])
        """
        return ['bash', 'sql', 'copy', 'python']  # Example task types

    def supports_feature(self, feature: str) -> bool:
        """Check if generator supports specific FLEX feature

        Called by: Validation system before generation
        Must return: True if feature is supported, False otherwise
        Features: 'loops', 'conditional_logic', 'parallel_execution', 'error_handling'
        """
        supported_features = ['error_handling', 'conditional_logic']
        return feature in supported_features

    def generate_metadata(self, workflow: FlexWorkflow) -> Dict[str, Any]:
        """Generate workflow metadata section

        Called by: generate() to create workflow header/metadata
        Must return: Dict with framework-specific metadata structure
        """
        pass

    def generate_schedule(self, schedule: Schedule) -> Any:
        """Generate scheduling configuration

        Called by: generate() when workflow has schedule
        Must return: Framework-specific schedule object or None if not supported
        """
        pass

    def generate_task(self, task: Task, workflow: FlexWorkflow) -> Any:
        """Generate individual task definition

        Called by: generate() for each task in workflow
        Must return: Framework-specific task object
        """
        pass

    def generate_dependencies(self, tasks: List[Task]) -> Any:
        """Generate task dependency relationships

        Called by: generate() to create execution order
        Must return: Framework-specific dependency structure
        """
        pass

    def generate_error_handling(self, error_handling: ErrorHandling) -> Any:
        """Generate error handling configuration

        Called by: generate() when workflow has error_handling
        Must return: Framework-specific error config or None if not available
        """
        pass

    def generate_conditional_logic(self, task: Task, workflow: FlexWorkflow) -> Any:
        """Generate branch/choice logic for conditional tasks

        Called by: generate_task() for choice/branch task types
        Must return: Framework-specific conditional structure or None
        """
        pass

    def generate_loop_logic(self, task: Task, workflow: FlexWorkflow) -> Any:
        """Generate loop/iteration logic for loop tasks

        Called by: generate_task() for for_each/while task types
        Must return: Framework-specific loop structure or None
        """
        pass

    def generate_parallel_execution(self, tasks: List[Task], workflow: FlexWorkflow) -> Any:
        """Generate parallel execution patterns

        Called by: generate() for workflows with parallel tasks
        Must return: Framework-specific parallel structure or None
        """
        pass

    def format_output(self, generated_content: Any, workflow: FlexWorkflow) -> Dict[str, Any]:
        """Format generated content into standard output structure

        Called by: generate() to create final output
        Must return: Dict with 'content', 'metadata', 'framework' keys
        """
        return {
            'content': generated_content,
            'metadata': {'framework': 'myframework', 'version': '1.0'},
            'framework': 'myframework'
        }

    def validate_generated_output(self, output: Dict[str, Any]) -> bool:
        """Validate generated output before returning

        Called by: generate() before returning final result
        Must return: True if output is valid, False otherwise
        """
        # Validate syntax, required fields, etc.
        return 'content' in output and output['content'] is not None
```

### Registration and Integration

**Add your parser/generator to the framework registry:**

```python
# In awslabs/etl_replatforming_mcp_server/core/framework_registry.py
from ..parsers.myframework_parser import MyFrameworkParser
from ..generators.myframework_generator import MyFrameworkGenerator

# Register parser
FRAMEWORK_PARSERS['myframework'] = MyFrameworkParser

# Register generator
FRAMEWORK_GENERATORS['myframework'] = MyFrameworkGenerator
```

### Testing Your Implementation

**Create comprehensive unit tests for all required methods:**

```python
# tests/unit/parsers/test_myframework_parser.py
class TestMyFrameworkParser:
    def test_parse_code(self):
        # Test main entry point
        pass

    def test_detect_framework(self):
        # Test framework detection
        pass

    # Test all 11 required methods...

# tests/unit/generators/test_myframework_generator.py
class TestMyFrameworkGenerator:
    def test_generate(self):
        # Test main entry point
        pass

    def test_get_supported_task_types(self):
        # Test task type support
        pass

    # Test all 12 required methods...
```

### Quality Guidelines

**Parser Quality Metrics:**
- `get_parsing_completeness()` should return >= 0.8 for production use
- Handle edge cases gracefully (return empty lists/None for unsupported features)
- Populate `parsing_info` with detailed completeness tracking

**Generator Quality Metrics:**
- Support core task types: `bash`, `sql`, `copy`, `python`
- Implement error handling and basic conditional logic if framework supports it
- Generate syntactically valid output that can execute in target framework
- Validate output before returning

**Both parsers and generators must:**
- Handle malformed input gracefully
- Provide clear error messages
- Follow framework-specific best practices
- Include comprehensive unit test coverage

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

## Development

### Code Quality Standards

The project follows strict code quality standards:

**Function Length**: Maximum 30 lines per function
- Long functions broken into focused helper methods
- Single responsibility principle enforced
- Clear separation of concerns

**Constants Management**: Zero magic numbers
- All configurable values in `constants.py`
- Centralized timeout, retry, and threshold values
- Type-safe constant definitions

**Logging Standards**: Professional structured logging
- Consistent format across all components
- Configurable levels and file rotation
- No excessive emoji usage in logs
- Structured error reporting

**Package Structure**: Standardized Python packaging
- Single `pyproject.toml` configuration
- Proper dependency management
- Clean import structure

### Adding New Features

**1. Create Utility Classes**
```python
# Follow existing patterns in utils/
class MyUtility:
    def __init__(self, config):
        self.config = config

    def process(self, data):
        # Keep methods under 30 lines
        pass
```

**2. Add Constants**
```python
# Add to constants.py
MY_FEATURE_TIMEOUT = 60
MY_FEATURE_MAX_RETRIES = 3
```

**3. Write Tests**
```python
# Create comprehensive test coverage
class TestMyUtility:
    def test_process_success(self):
        pass

    def test_process_error_handling(self):
        pass
```

**4. Update Documentation**
- Add feature description to README
- Update architecture diagrams
- Include usage examples

## Configuration

### Environment Variables

Set environment variables:

```bash
export FASTMCP_LOG_LEVEL=INFO  # Optional: DEBUG, INFO, WARNING, ERROR
export AWS_REGION=us-east-1    # Optional: For Bedrock AI enhancement (defaults to us-east-1)
export AWS_PROFILE=your-profile # Optional: For Bedrock AI enhancement
export MCP_LOG_FILE=/path/to/logfile.log  # Optional: Enable file logging with rotation
```

### Configuration Constants

The server uses centralized constants for consistent behavior:

```python
# Key configuration constants (from constants.py)
DEFAULT_CONFIDENCE_THRESHOLD = 0.8  # AI enhancement confidence threshold
DEFAULT_MAX_RETRIES = 3             # Bedrock API retry attempts
DEFAULT_TIMEOUT_SECONDS = 30        # Request timeout
MIN_COMPLETENESS_FOR_AI = 0.95      # Threshold for AI enhancement
LOG_ROTATION_SIZE = "10 MB"         # Log file rotation size
```

### Logging Configuration

**Structured Logging Format:**
```
{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}
```

**Features:**
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Optional file logging with automatic rotation
- Consistent formatting across all components
- No excessive emoji usage for professional logs

### AWS Bedrock Setup (Optional - For AI Enhancement)

**💡 OPTIONAL: This MCP server can use AWS Bedrock for AI-enhanced workflow parsing to fill gaps in incomplete workflows and reduce user prompts. The server works without AWS credentials using deterministic parsing only.**

**Setup Steps:**

1. **AWS Credentials**: Configure AWS credentials with Bedrock permissions
   ```bash
   aws configure --profile your-profile
   # Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output format (json)
   ```

2. **IAM Permissions**: Create a custom policy with minimal required permissions:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "bedrock:InvokeModel",
           "sts:GetCallerIdentity"
         ],
         "Resource": [
           "arn:aws:bedrock:*:*:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0",
           "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-*",
           "*"
         ]
       }
     ]
   }
   ```
   **Note**: Claude Sonnet 4 requires inference profile permissions. For other models, use foundation-model ARNs.

3. **Bedrock Model Access**: Enable Claude model access in AWS Console
   - **⚠️ IMPORTANT**: Model access must be granted in the **same region** as your AWS_REGION environment variable
   - Go to **AWS Console → Amazon Bedrock → Model access**
   - **Ensure you're in the correct region** (top-right corner of AWS Console)
   - Click **Request model access**
   - Select **Anthropic Claude Sonnet 4** (`anthropic.claude-sonnet-4-20250514-v1:0`)
   - Submit request (usually approved instantly)
   - **Verify**: Model status should show "Access granted" in the same region
   - **Note**: Claude Sonnet 4 uses inference profiles automatically - no additional setup needed

4. **Verify Setup**:
   ```bash
   # Replace us-east-1 with your AWS_REGION
   aws bedrock list-foundation-models --region us-east-1

   # Test model access
   aws bedrock get-foundation-model --model-identifier anthropic.claude-sonnet-4-20250514-v1:0 --region us-east-1
   ```

**⚠️ Without Bedrock Setup:**
- Workflows will still parse but may remain incomplete
- FLEX documents will contain "?" placeholders for missing information
- Conversion quality may be reduced
- You'll see "Bedrock enhancement failed" warnings in logs

## Bedrock LLM Configuration

Configure AI-enhanced parsing with custom Bedrock settings:

### Model Configuration

**Any AWS Bedrock foundation model can be used** by specifying the `model_id` in `llm_config`. The server defaults to **Claude Sonnet 4** (`anthropic.claude-sonnet-4-20250514-v1:0`).

**⚠️ Throttling Considerations:**
- **Claude Sonnet 4** and **Claude 3.5 Sonnet**: Use inference profiles, lower rate limits, **may cause throttling during integration tests**
- **Claude 3 Sonnet** (`anthropic.claude-3-sonnet-20240229-v1:0`): **Recommended for testing** - higher rate limits, direct invocation, **no throttling issues** # pragma: allowlist secret
- **Other models** (Amazon Titan, Cohere, Meta Llama): Supported but performance may vary for ETL-specific tasks
- **For Integration Tests**: Use Claude 3 Sonnet to avoid `ThrottlingException` errors that can cause tests to run indefinitely

### Default Configuration

**The `llm_config` parameter is optional.** If not provided, the system uses these defaults:

```json
{
  "model_id": "anthropic.claude-sonnet-4-20250514-v1:0",
  "max_tokens": 50000,
  "temperature": 0.1,
  "top_p": 0.9,
  "region": "us-east-1"
}
```

**💡 For Testing/Development:** Use Claude 3 Sonnet to avoid throttling:
```json
{
  "llm_config": {
    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0" // pragma: allowlist secret
  }
}
```

**⚠️ Integration Test Warning:** Integration tests may run indefinitely with Claude Sonnet 4 due to throttling. Always use Claude 3 Sonnet for automated testing.

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
    "model_id": "anthropic.claude-sonnet-4-20250514-v1:0",
    "temperature": 0.2,
    "max_tokens": 6000
  }
}
```

**Parameters:**
- `model_id`: Any AWS Bedrock foundation model ID (see supported models above for recommendations)
- `max_tokens`: Maximum response length for generated FLEX workflows. **Required by [AWS Bedrock API](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages.html)**. Range: 1-200000 (Claude Sonnet 4's limit), default: 50000
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
# Business Rules and Logic (Inference Context Only)

## Data Processing Patterns
- Standard ETL patterns used in your organization
- Common data transformation approaches
- Typical data quality checks and validation rules

## Dependencies and Timing
- Standard dependency patterns between pipeline stages
- Common data availability windows
- Typical processing schedules and timing constraints

Note: This section should only contain organizational standards and patterns,
not specific logic from individual source workflows. The AI uses this context
to make reasonable inferences about missing information, but all actual business
logic comes from the source workflow code being converted.
```

#### Best Practices

- **Be Specific**: Include actual examples and code snippets rather than generic descriptions
- **Include Standards**: Document naming conventions, scheduling patterns, error handling, and business rules
- **Provide Context**: Explain infrastructure setup, data sources, and dependencies
- **Update Regularly**: Keep context current with evolving standards

## Usage

**Natural Language Interface**: Simply describe what you want to do with directory paths or individual workflows.

### Two Types of Usage

#### 1. Directory-Based Tools (Batch Processing)
**For migrating multiple workflow files at once**

**Input**: Directory containing workflow files
**Output**: Organized directories with converted files
**Use when**: Processing dozens/hundreds of workflows, team migrations
**Input Preparation**: Extract workflow definitions from source frameworks (see below)

#### 2. Single Workflow Tools (Individual Processing)
**For converting individual workflows**

**Input**: Workflow content directly (JSON/Python code)
**Output**: Converted workflow content
**Use when**: Testing conversions, working with content from UI, prototyping
**Input Preparation**: Copy workflow content directly - no file extraction needed

### Input Preparation

**Two approaches based on tool type:**

**Directory-Based Tools (Batch Processing)**: Extract workflow definitions from source frameworks and organize in directories
**Single Workflow Tools (Individual Processing)**: Provide workflow content directly (copy/paste from UI, API responses, etc.) - no file extraction needed

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

### Python Script Extraction (Airflow → Step Functions)

**When converting from Airflow to orchestration-only platforms (Step Functions), the system automatically:**

1. **Extracts Python functions** from Airflow DAG files
2. **Creates standalone scripts** with proper imports and argument parsing
3. **Updates FLEX tasks** with `script_file` references
4. **Generates Step Functions configurations** with Glue Python Shell jobs and S3 script locations

**Generated files location**: `outputs/{conversion_output}/python_files/`

**Example file structure**:
```
outputs/
└── target_step_functions_from_source_airflow_jobs/
    ├── my_workflow.json              # Step Functions state machine
    ├── my_workflow.flex.json         # FLEX intermediate format
    └── glue_python_shell_jobs/       # AWS Glue Python Shell jobs
        └── my_workflow/
            ├── extract_data.py           # Python script
            ├── extract_data_glue_job.json # Glue job definition
            ├── transform_data.py
            ├── transform_data_glue_job.json
            ├── load_data.py
            └── load_data_glue_job.json
```

**Note**: Azure Data Factory generator is planned - the parser extracts Python files and stores them in FLEX metadata for future ADF generator implementation.

**Example**:
```python
# Original Airflow DAG
def extract_data():
    return {"records": 1000}

extract_task = PythonOperator(
    task_id='extract_data',
    python_callable=extract_data
)
```

**Generated `extract_data.py`**:
```python
#!/usr/bin/env python3
import sys
import json
import boto3
from datetime import datetime

def extract_data():
    return {"records": 1000}

if __name__ == "__main__":
    result = extract_data()
    print(f"Task completed: {result}")
```

**Generated `extract_data_glue_job.json`**:
```json
{
  "Name": "my_workflow_extract_data",
  "Role": "arn:aws:iam::ACCOUNT_ID:role/GlueServiceRole",
  "Command": {
    "Name": "pythonshell",
    "ScriptLocation": "s3://YOUR_BUCKET/glue_scripts/my_workflow/extract_data.py",
    "PythonVersion": "3.9"
  },
  "DefaultArguments": {
    "--job-language": "python",
    "--enable-metrics": "",
    "--enable-continuous-cloudwatch-log": "true"
  },
  "MaxRetries": 0,
  "Timeout": 2880,
  "GlueVersion": "3.0"
}
```

**Step Functions state**:
```json
{
  "Resource": "arn:aws:states:::glue:startJobRun.sync",
  "Parameters": {
    "JobName": "etl-pipeline-extract_data-python-shell",
    "Arguments": {
      "--script_location": "s3://{glue_scripts_bucket}/scripts/extract_data.py"
    }
  }
}
```

**FLEX Task Reference**:
```json
{
  "id": "extract_data",
  "type": "python",
  "command": "extract_data",
  "script_file": "extract_data.py"
}
```

## AWS Glue Python Shell Integration

**When converting Airflow to Step Functions, the system automatically generates AWS Glue Python Shell job definitions for seamless deployment.**

### Generated Glue Job Features

- **Python Shell Jobs**: Optimized for lightweight Python scripts (up to 1 DPU)
- **CloudWatch Logging**: Automatic log streaming enabled
- **Metrics**: Built-in job metrics and monitoring
- **Timeout**: 48-hour maximum execution time
- **Retry Logic**: Configurable retry attempts
- **Python 3.9**: Latest supported Python version

### Deployment Instructions

**1. Upload Scripts to S3:**
```bash
# Create S3 bucket for Glue scripts
aws s3 mb s3://your-glue-scripts-bucket

# Upload Python files
aws s3 cp outputs/target_step_functions_from_source_airflow_jobs/glue_python_shell_jobs/my_workflow/ s3://your-glue-scripts-bucket/glue_scripts/my_workflow/ --recursive --exclude "*_glue_job.json"
```

**2. Create Glue Jobs using AWS CLI:**
```bash
# Update job definitions with your S3 bucket and account ID
sed -i 's/YOUR_BUCKET/my-glue-bucket/g' outputs/converted_workflows/glue_jobs/my_workflow/*_glue_job.json
sed -i 's/ACCOUNT_ID/YOUR_AWS_ACCOUNT_NUMBER/g' outputs/target_step_functions_from_source_airflow_jobs/glue_python_shell_jobs/my_workflow/*_glue_job.json # pragma: allowlist secret

# Create each Glue job
for job_file in outputs/target_step_functions_from_source_airflow_jobs/glue_python_shell_jobs/my_workflow/*_glue_job.json; do
    aws glue create-job --cli-input-json file://$job_file
done
```

**3. Deploy Step Functions State Machine:**
```bash
# Create state machine using generated definition
aws stepfunctions create-state-machine \
    --name "my_workflow" \
    --definition file://outputs/target_step_functions_from_source_airflow_jobs/my_workflow.json \
    --role-arn "arn:aws:iam::YOUR_AWS_ACCOUNT_NUMBER:role/StepFunctionsExecutionRole"
```

### Required IAM Roles

**GlueServiceRole** (for Glue jobs):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

**StepFunctionsExecutionRole** (for Step Functions):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "glue:StartJobRun",
        "glue:GetJobRun",
        "glue:BatchStopJobRun"
      ],
      "Resource": "*"
    }
  ]
}
```

### Glue Job Configuration Options

**Customizable Parameters:**
- **MaxRetries**: Number of retry attempts (0-10)
- **Timeout**: Maximum execution time in minutes (1-2880)
- **PythonVersion**: Python runtime version (3.9 recommended)
- **DefaultArguments**: Additional job parameters
- **GlueVersion**: Glue runtime version (3.0 recommended)

**Example Customization:**
```json
{
  "MaxRetries": 3,
  "Timeout": 60,
  "DefaultArguments": {
    "--additional-python-modules": "pandas==1.5.0,numpy==1.21.0",
    "--python-modules-installer-option": "--upgrade"
  }
}
```

### Benefits

- **Production Ready**: Complete job definitions with best practices
- **Cost Effective**: Python Shell jobs use minimal resources (0.0625-1 DPU)
- **Serverless**: No infrastructure management required
- **Integrated**: Works seamlessly with Step Functions orchestration
- **Scalable**: Automatic scaling based on workload
- **Monitored**: Built-in CloudWatch integration

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

## Framework Auto-Detection

**How the system identifies source frameworks automatically:**

### Detection Strategy
- **File Extension Analysis**: `.py` files → check for Airflow imports, `.json` files → analyze JSON structure
- **Content Pattern Matching**: Look for framework-specific keywords and structures
- **Hierarchical Detection**: Most specific patterns checked first to avoid false positives
- **Extensible Design**: New frameworks can be added by extending detection rules

### Current Detection Rules

| Framework | File Type | Detection Pattern |
|-----------|-----------|------------------|
| **Airflow** | `.py` | `from airflow`, `import airflow`, `DAG(` |
| **Step Functions** | `.json` | `"States"` + `"StartAt"` keys |
| **Azure Data Factory** | `.json` | `"properties"` + `"activities"` structure |
| **FLEX** | `.json` | `"name"` + `"tasks"` array with `"id"` fields |

### Scalability for New Frameworks

**The auto-detection system is designed for easy extension:**

```python
# Adding new framework detection (example)
if path.suffix == '.py':
    if 'from prefect' in content or '@flow' in content:
        return 'prefect'
    if 'from dagster' in content or '@op' in content:
        return 'dagster'

elif path.suffix == '.yaml':
    if 'apiVersion: argoproj.io' in content:
        return 'argo_workflows'
```

**Benefits:**
- **No Manual Classification**: Users don't specify source frameworks
- **Mixed Directory Support**: Handle multiple framework types in one directory
- **Future-Proof**: Easy to add Prefect, Dagster, GitHub Actions, etc.
- **Reliable Detection**: Hierarchical patterns prevent misclassification

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
- **Hybrid Parsing**: Combines fast deterministic parsing with intelligent AI enhancement
- **Quality Metrics**: Confidence scores help assess conversion quality

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
  "tags": ["etl", "customer-data"],     // Workflow classification
  "parsing_info": {                     // Parsing completeness information
    "source_framework": "airflow",
    "parsing_completeness": 0.85,
    "parsing_method": "ast",
    "ignored_elements": [
      {
        "element": "imports.sensors",
        "content": "FileSensor imports detected",
        "reason": "Sensors not fully supported",
        "type": "task",
        "suggestions": ["Convert to polling tasks"]
      }
    ],
    "warnings": ["Complex TaskGroup detected"],
    "suggestions": ["⚠️ 15% of elements ignored - review below"]
  }
}
```

### FLEX Core Concepts

1. **Tasks**: Atomic units of work with **free-form type strings** - use any descriptive string (not restricted to predefined enums)
2. **Data Sources/Sinks**: Explicit source and destination configurations for data movement
3. **Dependencies**: Define execution order and conditions
4. **Schedule**: When and how often the workflow runs
5. **Error Handling**: Comprehensive failure management with notifications and escalation
6. **Parameters/Variables**: Runtime configuration and state management
7. **Resource Requirements**: Compute and infrastructure specifications
8. **Metadata**: Additional context for governance and documentation
9. **Parsing Info**: Completeness tracking and ignored elements for user review

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

**Parsing Completeness:**
- Tracks what was successfully parsed vs ignored
- Provides specific reasons for ignored elements
- Includes actionable suggestions for manual work
- Shows parsing method (deterministic, ai_enhanced) and confidence level
- **LLM Confidence**: AI-enhanced elements include confidence scores (0.0-1.0)
- **Enhancement Tracking**: Lists what the LLM specifically enhanced



### FLEX Parsing Info Section

**Every FLEX document includes parsing completeness information:**

```json
{
  "parsing_info": {
    "source_framework": "airflow",
    "parsing_completeness": 0.85,
    "parsing_method": "ai_enhanced",
    "llm_confidence": 0.92,
    "llm_enhancements": [
      "Added command for task 'process_data'",
      "Resolved dependencies for task 'cleanup_task'",
      "Added workflow schedule"
    ],
    "ignored_elements": [
      {
        "element": "imports.sensors",
        "content": "FileSensor imports detected",
        "reason": "Sensors not fully supported - may need manual conversion",
        "type": "task",
        "suggestions": ["Consider converting sensors to polling tasks"]
      }
    ],
    "warnings": ["Complex dynamic TaskGroup detected - verify loop conversion"],
    "suggestions": [
      "⚠️ Only 85.0% of elements were parsed - review ignored elements below",
      "🤖 AI enhanced 3 elements with 92% confidence"
    ]
  }
}
```

**New AI Enhancement Fields:**
- **llm_confidence**: AI parsing confidence (0.0-1.0) - higher is better
- **llm_enhancements**: Specific list of what the LLM enhanced
- **parsing_method**: "deterministic", "ai_enhanced", or "hybrid"

**Key Fields:**
- **parsing_completeness**: Percentage of elements successfully parsed (0.0-1.0)
- **parsing_method**: "deterministic", "ai_enhanced", or "hybrid"
- **llm_confidence**: AI parsing confidence (0.0-1.0) when AI was used
- **llm_enhancements**: List of specific AI enhancements made
- **ignored_elements**: Detailed list of what was not converted
- **warnings**: Potential issues that need attention
- **suggestions**: User-friendly guidance for next steps

**Element Types:**
- `task`: Regular workflow tasks
- `loop`: Iterative constructs
- `conditional_logic`: Branching logic
- `schedule`: Timing configuration
- `resource`: Connections and infrastructure
- `unknown`: Unrecognized elements

**User Review Process:**
1. **Check parsing_completeness** - aim for >80% for production workflows
2. **Review AI confidence** - llm_confidence >0.8 indicates high-quality AI enhancements
3. **Review ignored_elements** - determine if manual implementation is needed
4. **Address warnings** - verify complex patterns converted correctly
5. **Follow suggestions** - actionable steps for completing migration

**AI Enhancement Quality:**
- **0.9-1.0**: Excellent - AI very confident in enhancements
- **0.8-0.9**: Good - AI confident, minor review recommended
- **0.7-0.8**: Fair - AI moderately confident, review recommended
- **<0.7**: Poor - AI uncertain, manual review required

### FLEX Validation Rules

**Schedule Validation:**
- **Cron expressions**: Must be 5-field format (minute hour day month weekday)
  - Valid: `"0 9 * * *"` (daily at 9 AM), `"0 */6 * * *"` (every 6 hours)
  - Invalid: `"0 9 * *"` (missing weekday), `"60 9 * * *"` (invalid minute)
- **Rate expressions**: Must use format `rate(number unit)` (AWS Step Functions style)
  - Valid: `"rate(1 day)"`, `"rate(30 minutes)"`, `"rate(2 hours)"`
  - Invalid: `"rate(1)"`, `"every 1 day"`
  - **Note**: Rate expressions are converted to cron equivalents for frameworks that don't support them
- **Schedule types**: `cron`, `rate`, `manual`, `event`

**Task Validation:**
- **Task types**: Free-form strings (any descriptive string is valid - no restrictions)
- **Commands**: Minimal validation only
  - Placeholder detection: Identifies commands like "?", "TODO", "invoke_function()" that need AI enhancement
  - No syntax validation: FLEX doesn't validate SQL, Python, or bash syntax
  - Framework-agnostic: Same FLEX task can generate different target implementations
- **Timeouts**: 1 to 86400 seconds (24 hours maximum)
- **Retries**: 0 to 10 retries maximum
- **Retry delay**: 0 to 3600 seconds (1 hour maximum)

**Dependency Validation:**
- **Status Conditions**: `success`, `failure`, `always`, or `null`
- **Expression Conditions**: Support comparison and logical operators (`>`, `<`, `==`, `AND`, `OR`)
- **Condition Types**: `status` (default) or `expression`
- **Task references**: All upstream/downstream tasks must exist
- **Cycles**: No circular dependencies allowed

**Error Handling Validation:**
- **Failure actions**: `fail`, `continue`, `retry`
- **Email format**: Valid email addresses for notifications
- **Retry limits**: Consistent with task-level retry settings

FLEX is purpose-built for ETL orchestration migration, avoiding the complexity of adapting existing standards that weren't designed for data pipeline use cases. While standards like BPMN exist for general workflow modeling, they require significant learning overhead and don't align with how ETL developers think about data pipelines.

### Parallel Execution in FLEX

**FLEX represents parallel execution through task dependencies, not explicit parallel constructs.**

#### Example: A → (B,C) → D Pattern

```json
{
  "tasks": [
    {
      "id": "task_a",
      "name": "Task A",
      "type": "extract",
      "depends_on": []
    },
    {
      "id": "task_b",
      "name": "Task B",
      "type": "transform",
      "depends_on": [
        {"task_id": "task_a", "condition": "success"}
      ]
    },
    {
      "id": "task_c",
      "name": "Task C",
      "type": "transform",
      "depends_on": [
        {"task_id": "task_a", "condition": "success"}
      ]
    },
    {
      "id": "task_d",
      "name": "Task D",
      "type": "load",
      "depends_on": [
        {"task_id": "task_b", "condition": "success"},
        {"task_id": "task_c", "condition": "success"}
      ]
    }
  ]
}
```

**How this works:**
- **Task A** runs first (no dependencies)
- **Tasks B and C** run in parallel after A completes (both depend only on A)
- **Task D** waits for both B and C to complete (depends on both)

#### Complex Scenarios FLEX Can Represent

**✅ Supported Patterns:**
- **Fan-out/Fan-in**: A → (B,C,D) → E
- **Conditional Dependencies**: A → B (if success) or C (if failure)
- **Mixed Conditions**: A → B → (C,D) → E (where E needs both C and D)
- **Expression-based Dependencies**: Task runs if `output.count > 100`
- **Loop Constructs**: For-each loops with parallel execution limits

**❌ Limitations:**
- **Dynamic Task Generation**: Cannot create tasks at runtime based on data
- **Complex State Machines**: No support for complex branching logic within single tasks
- **Resource Constraints**: Limited modeling of compute resource dependencies
- **Time-based Dependencies**: Cannot express "wait 5 minutes after task A"

#### Framework-Specific Parallel Execution

**Target Framework Generation:**
- **Airflow**: Generates task dependencies using `>>` operators and task groups
- **Step Functions**: Creates Parallel states for concurrent execution
- **Azure Data Factory**: Uses dependency conditions and parallel activities

### Step Functions and Scheduling

**Step Functions doesn't have built-in scheduling, but FLEX handles this through target framework generation:**

#### How FLEX Schedule Information is Used

**For Step Functions Target:**
```json
// FLEX schedule
{
  "schedule": {
    "type": "cron",
    "expression": "0 2 * * *",
    "timezone": "UTC"
  }
}

// Generates Step Functions + EventBridge setup
{
  "state_machine_definition": { /* Step Functions JSON */ },
  "eventbridge_rule": {
    "ScheduleExpression": "cron(0 2 * * ? *)",
    "State": "ENABLED",
    "Targets": [{
      "Arn": "arn:aws:states:region:account:stateMachine:WorkflowName",
      "Id": "WorkflowTarget",
      "RoleArn": "arn:aws:iam::account:role/StepFunctionsExecutionRole"
    }]
  }
}
```

**Generated Components:**
1. **Step Functions State Machine**: The workflow logic
2. **EventBridge Rule**: Handles the scheduling
3. **IAM Role**: Permissions for EventBridge to invoke Step Functions
4. **CloudFormation Template**: Infrastructure as code for deployment

**For Airflow Target:**
```python
# FLEX schedule generates Airflow DAG schedule_interval
dag = DAG(
    'workflow_name',
    schedule_interval='0 2 * * *',  # From FLEX schedule
    start_date=datetime(2024, 1, 1),
    catchup=False
)
```

**Benefits:**
- **Universal Scheduling**: Same FLEX schedule works for all target frameworks
- **Framework Translation**: Automatically converts between scheduling systems
- **Infrastructure Generation**: Creates necessary supporting resources
- **Best Practices**: Applies framework-specific scheduling best practices

FLEX represents parallel execution through **dependency-based parallelism**:

```json
{
  "tasks": [
    {
      "id": "extract_data",
      "type": "sql",
      "command": "CREATE TABLE staging.raw_data AS SELECT * FROM source",
      "depends_on": []  // No dependencies = runs first
    },
    {
      "id": "process_customers",
      "type": "sql",
      "command": "CREATE TABLE processed.customers AS SELECT * FROM staging.raw_data WHERE type='customer'",
      "depends_on": [{"task_id": "extract_data", "condition": "success"}]  // Runs after extract_data
    },
    {
      "id": "process_orders",
      "type": "sql",
      "command": "CREATE TABLE processed.orders AS SELECT * FROM staging.raw_data WHERE type='order'",
      "depends_on": [{"task_id": "extract_data", "condition": "success"}]  // Runs after extract_data (parallel with process_customers)
    },
    {
      "id": "generate_report",
      "type": "sql",
      "command": "CREATE TABLE reports.summary AS SELECT * FROM processed.customers JOIN processed.orders",
      "depends_on": [
        {"task_id": "process_customers", "condition": "success"},
        {"task_id": "process_orders", "condition": "success"}
      ]  // Waits for both parallel tasks to complete
    }
  ]
}
```

**Key Principles:**
- **Tasks with no dependencies** can execute immediately when workflow starts
- **Tasks with same dependencies** can execute in parallel once dependencies are satisfied
- **Framework generators** determine actual parallel execution based on target platform capabilities
- **Dependencies define execution order** - parallelism emerges from dependency structure

**Framework Mapping:**
- **Airflow**: Handles parallel execution correctly using task dependencies (`[A] >> B`, `[A] >> C`, `[B, C] >> D`)
- **Step Functions**: Limited parallel support - complex patterns may require manual optimization
- **Azure Data Factory**: Parallel activities with dependency chains

### Complex Parallel Scenarios

**A → (B,C) → D Pattern:**
```json
{
  "tasks": [
    {
      "id": "A",
      "depends_on": []  // Runs first (no dependencies)
    },
    {
      "id": "B",
      "depends_on": [{"task_id": "A", "condition": "success"}]  // Runs after A
    },
    {
      "id": "C",
      "depends_on": [{"task_id": "A", "condition": "success"}]  // Runs after A (parallel with B)
    },
    {
      "id": "D",
      "depends_on": [
        {"task_id": "B", "condition": "success"},
        {"task_id": "C", "condition": "success"}
      ]  // Runs after both B and C complete
    }
  ]
}
```

**Execution Flow:**
1. **extract_data** runs first (no dependencies)
2. **process_customers** and **process_orders** run in parallel after extract_data completes (both depend only on extract_data)
3. **generate_report** runs after both processing tasks complete (depends on both)

**FLEX Limitations:**
FLEX can represent most orchestration patterns, but complex scenarios requiring:
- **Dynamic task generation** (tasks created at runtime)
- **Advanced error handling** with custom retry logic per condition

May require framework-specific implementations.

**Note**: FLEX now supports conditional branching through expression-based dependencies and loop constructs for iterative processing patterns.

### Conditional Logic in FLEX

**FLEX supports conditional task execution through extended dependency conditions:**

#### Basic Status Conditions
```json
{
  "depends_on": [
    {"task_id": "check_data", "condition": "success", "condition_type": "status"}
  ]
}
```

#### Expression-Based Conditions
```json
{
  "depends_on": [
    {
      "task_id": "check_inventory",
      "condition": "output.count > 1000",
      "condition_type": "expression"
    }
  ]
}
```

#### Complex Conditional Workflows
```json
{
  "tasks": [
    {
      "id": "check_inventory",
      "type": "sql",
      "command": "SELECT COUNT(*) as count, AVG(quality) as avg_quality FROM inventory"
    },
    {
      "id": "process_large_batch",
      "name": "Process Large Batch",
      "type": "python",
      "command": "process_large_batch()",
      "depends_on": [
        {
          "task_id": "check_inventory",
          "condition": "output.count > 1000",
          "condition_type": "expression"
        }
      ]
    },
    {
      "id": "process_small_batch",
      "name": "Process Small Batch",
      "type": "python",
      "command": "process_small_batch()",
      "depends_on": [
        {
          "task_id": "check_inventory",
          "condition": "output.count <= 1000 AND output.count > 0",
          "condition_type": "expression"
        }
      ]
    },
    {
      "id": "handle_empty",
      "name": "Handle Empty Dataset",
      "type": "python",
      "command": "handle_empty_dataset()",
      "depends_on": [
        {
          "task_id": "check_inventory",
          "condition": "output.count == 0",
          "condition_type": "expression"
        }
      ]
    }
  ]
}
```

**Supported Expression Operators:**
- **Comparison**: `>`, `<`, `>=`, `<=`, `==`, `!=`
- **Logical**: `AND`, `OR`, `NOT`
- **Output References**: `output.field_name`, `output.nested.field`

**Framework Mapping:**
- **Airflow**: Generates BranchPythonOperator with conditional logic
- **Step Functions**: Maps to Choice states with condition rules
- **Azure Data Factory**: Uses If Condition activities

### Loop Constructs in FLEX

**FLEX supports iterative processing patterns through loop constructs:**

#### For-Each Loops
**Process each item in a collection:**
```json
{
  "id": "process_files",
  "name": "Process Each File",
  "type": "python",
  "command": "process_file(file)",
  "loop": {
    "type": "for_each",
    "items": {
      "source": "static",
      "values": ["file1.csv", "file2.csv", "file3.csv"]
    },
    "item_variable": "file",
    "max_concurrency": 3
  }
}
```

#### Range Loops
**Process data in batches or ranges:**
```json
{
  "id": "process_batches",
  "name": "Process Data Batches",
  "type": "sql",
  "command": "SELECT * FROM data WHERE id BETWEEN {batch_id} AND {batch_id + 9}",
  "loop": {
    "type": "range",
    "items": {
      "source": "range",
      "start": 1,
      "end": 100,
      "step": 10
    },
    "item_variable": "batch_id"
  }
}
```

#### While Loops
**Continue until condition is met:**
```json
{
  "id": "improve_quality",
  "name": "Improve Data Quality",
  "type": "python",
  "command": "improve_data_quality()",
  "loop": {
    "type": "while",
    "condition": "output.quality_score < 0.95",
    "item_variable": "iteration",
    "max_iterations": 10
  }
}
```

#### Dynamic Loops from Task Output
**Use output from previous tasks as loop items:**
```json
{
  "id": "process_files",
  "name": "Process Files from List",
  "type": "python",
  "command": "process_file(file)",
  "loop": {
    "type": "for_each",
    "items": {
      "source": "task_output",
      "task_id": "list_files",
      "path": "output.files"
    },
    "item_variable": "file",
    "max_concurrency": 5
  },
  "depends_on": [
    {"task_id": "list_files", "condition": "success"}
  ]
}
```

#### Loop Configuration Options

**Loop Types:**
- `for_each`: Iterate over collection of items
- `range`: Iterate over numeric range
- `while`: Continue while condition is true

**Items Sources:**
- `static`: Predefined list of values
- `task_output`: Items from previous task output
- `range`: Numeric range with start/end/step

**Concurrency Control:**
- `max_concurrency`: Limit parallel execution (for_each loops)
- `max_iterations`: Safety limit for while loops

**Error Handling:**
- `on_failure`: "fail" (stop all), "continue" (skip failed), "break" (exit loop)

#### Framework Mapping for Loops

| FLEX Loop | Airflow | Step Functions | Azure Data Factory |
|-----------|---------|----------------|--------------------|
| `for_each` | TaskGroup with dynamic tasks | Map State | ForEach Activity |
| `range` | TaskGroup with range() | Map State with range | ForEach with range |
| `while` | Custom sensor + recursive | Choice + Pass loop | Until Activity |

**Airflow Loop Generation:**
- Uses TaskGroup for organization
- Dynamic task creation within groups
- Supports concurrency limits
- Variable substitution in task commands

**Step Functions Loop Generation:**
- Map states for for_each and range loops
- Choice states with recursive patterns for while loops
- Iterator definitions for task logic
- Concurrency control via MaxConcurrency

**Example Generated Airflow Code:**
```python
# For-each loop generates:
with TaskGroup(group_id='process_files_loop_group', dag=dag) as process_files_loop_group:
    for i, file in enumerate(items):
        task_id = f"process_files_{i}"
        python_task = PythonOperator(
            task_id=task_id,
            python_callable=loop_func,
            params={'file': file},
            dag=dag
        )
```

**Example Generated Step Functions:**
```json
{
  "process_files_map": {
    "Type": "Map",
    "ItemsPath": "$.files",
    "MaxConcurrency": 3,
    "Iterator": {
      "StartAt": "process_files_iterator",
      "States": {
        "process_files_iterator": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "End": true
        }
      }
    }
  }
}
```

## FLEX Framework Mapping

FLEX acts as the connector between different orchestration frameworks. Here's how FLEX elements translate:

### Source Framework → FLEX Parsing

#### Step Functions → FLEX

| Step Functions Element | FLEX Element | Notes |
|------------------------|--------------|-------|
| Task State | `tasks[].type` based on Resource | See AWS Service mapping |
| Map State | `tasks[].type = "for_each"` with `loop` config | Parallel processing |
| Choice State | `tasks[].depends_on` with expressions | Conditional logic |
| Pass State | `tasks[].type = "bash"` | No-op placeholder |
| Parallel State | Multiple tasks with same dependencies | Parallel execution |
| Wait State | Ignored (not supported) | Manual conversion needed |
| Succeed/Fail States | Ignored (terminal states) | Workflow completion logic |

#### Step Functions Resource → FLEX Task Type

| Step Functions Resource | FLEX Task Type | Command Generation |
|-------------------------|----------------|--------------------|
| `arn:aws:states:::aws-sdk:redshiftdata:executeStatement` | `sql` | Extract SQL from Parameters.Sql |
| `arn:aws:states:::lambda:invoke` | `python` | `invoke_function(FunctionName)` |
| `arn:aws:states:::batch:submitJob` | `bash` | `run_batch_job(JobDefinition)` |
| `arn:aws:states:::sns:publish` | `email` | `send_notification(Message)` |
| `arn:aws:states:::s3:*` | `file_transfer` | `s3_operation` |
| Other AWS services | `bash` | `generic_aws_service_call` |

#### Airflow → FLEX

| Airflow Element | FLEX Element | Notes |
|-----------------|--------------|-------|
| Task (Operator) | `tasks[]` | Based on operator type |
| TaskGroup | `tasks[].loop` for dynamic groups | Loop constructs |
| Dependencies (`>>`) | `tasks[].depends_on` | Task execution order |
| BranchPythonOperator | `tasks[].depends_on` with expressions | Conditional logic |
| DAG schedule | `schedule` | Cron/rate expressions |
| default_args | Task-level timeout/retries | Error handling |

#### Azure Data Factory → FLEX

| ADF Element | FLEX Element | Notes |
|-------------|--------------|-------|
| Activity | `tasks[]` | Based on activity type |
| ForEach Activity | `tasks[].type = "for_each"` with `loop` | Parallel processing |
| If Condition Activity | `tasks[].depends_on` with expressions | Conditional logic |
| Pipeline parameters | `parameters` | Runtime configuration |
| Linked Services | `tasks[].linked_service` | Connection references |
| Triggers | `schedule` | Scheduling configuration |

### FLEX → Target Framework Generation

#### FLEX → Airflow

| FLEX Field | Airflow Equivalent | Notes |
|---------------|-------------------|-------|
| `name` | `dag_id` | DAG identifier |
| `description` | `description` | DAG description |
| `schedule.expression` | `schedule_interval` | Converted to Airflow format |
| `schedule.timezone` | `timezone` | DAG timezone |
| `tasks[].id` | `task_id` | Task identifier |
| `tasks[].name` | Task name/description | Human readable name |
| `tasks[].type` | Operator type | See task type mapping below |
| `tasks[].command` | `sql`/`python_callable`/`bash_command` | Task execution code |
| `tasks[].timeout` | `execution_timeout` | Task timeout |
| `tasks[].retries` | `retries` | Retry count |
| `tasks[].depends_on` | `>>` operator | Task dependencies |
| `tasks[].loop` | TaskGroup with dynamic tasks | Loop constructs |
| `error_handling.notification_emails` | `email` in default_args | Failure notifications |

**Loop Generation Example:**
```python
# FLEX for_each loop generates:
with TaskGroup(group_id='process_files_loop_group', dag=dag) as loop_group:
    for i, item in enumerate(items):
        task = PythonOperator(
            task_id=f"process_files_{i}",
            python_callable=loop_func,
            params={'item': item},
            dag=dag
        )
```

#### Complete Task Type Mappings

#### FLEX Task Type → Airflow Operator Mapping

| FLEX Task Type | Airflow Operator | Use Case |
|----------------|------------------|----------|
| `sql` | `RedshiftSQLOperator` | SQL queries, data transformations |
| `bash` | `BashOperator` | Shell scripts, command execution |
| `python` | `PythonOperator` | Python functions, custom logic |
| `for_each` | `TaskGroup` with dynamic tasks | Parallel processing of items |
| Other types | `PythonOperator` (fallback) | Custom task types |

#### FLEX → Step Functions

| FLEX Field | Step Functions Equivalent | Notes |
|---------------|---------------------------|-------|
| `name` | `stateMachineName` | State machine name |
| `description` | `Comment` | State machine description |
| `schedule` | EventBridge Rule | External scheduling via EventBridge |
| `tasks[].id` | State name | Individual state identifier |
| `tasks[].name` | State comment | Human readable description |
| `tasks[].type` | `Resource` type | See task type mapping below |
| `tasks[].command` | `Parameters` | Passed to resource |
| `tasks[].timeout` | `TimeoutSeconds` | State timeout |
| `tasks[].retries` | `Retry` block | Retry configuration |
| `tasks[].depends_on` | `Next` transitions | State flow control |
| `tasks[].loop` | Map State or Choice loop | Loop constructs |
| `error_handling` | `Catch` blocks | Error handling states |

**Loop Generation Example:**
```json
// FLEX for_each loop generates:
{
  "ProcessFiles": {
    "Type": "Map",
    "ItemsPath": "$.fileList.files",
    "MaxConcurrency": 5,
    "Iterator": {
      "StartAt": "ProcessFile",
      "States": {
        "ProcessFile": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "End": true
        }
      }
    }
  }
}
```

#### FLEX Task Type → AWS Service Mapping

| FLEX Task Type | AWS Service | Resource ARN | Use Case |
|----------------|-------------|--------------|----------|
| `sql` | Redshift Data API | `arn:aws:states:::aws-sdk:redshiftdata:executeStatement` | SQL queries, data transformations |
| `bash` | AWS Batch | `arn:aws:states:::batch:submitJob.sync` | Shell scripts, command execution |
| `python` | Lambda | `arn:aws:states:::lambda:invoke` | Python functions, custom logic |
| `for_each` | Map State | `arn:aws:states:::states:startExecution.sync` | Parallel processing of items |
| Other types | Lambda (fallback) | `arn:aws:states:::lambda:invoke` | Custom task types |

**Lambda Functions Generated:**
- Complete Python code templates provided for Lambda tasks
- Includes error handling, parameter extraction, and deployment instructions
- Ready to copy-paste into AWS Lambda console

**Map State Features:**
- Converts FLEX `for_each` loops to Step Functions Map states
- Supports `max_concurrency` for parallel execution control
- Handles dynamic items from task output via `ItemsPath`
- Generates complete Iterator state machine for loop body

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

### Conditional Workflow Example

**Business Case:** Data processing pipeline that handles different batch sizes with conditional logic.

```json
{
  "name": "conditional_data_processing",
  "description": "Process data with conditional logic based on batch size",
  "schedule": {
    "type": "cron",
    "expression": "0 2 * * *",
    "timezone": "UTC"
  },
  "tasks": [
    {
      "id": "check_data_volume",
      "name": "Check Data Volume",
      "type": "sql",
      "command": "SELECT COUNT(*) as record_count FROM staging.daily_data",
      "timeout": 1800,
      "retries": 2
    },
    {
      "id": "process_large_batch",
      "name": "Process Large Batch",
      "type": "python",
      "command": "process_large_batch_parallel()",
      "depends_on": [
        {
          "task_id": "check_data_volume",
          "condition": "output.record_count > 100000",
          "condition_type": "expression"
        }
      ]
    },
    {
      "id": "process_small_batch",
      "name": "Process Small Batch",
      "type": "sql",
      "command": "INSERT INTO processed.data SELECT * FROM staging.daily_data",
      "depends_on": [
        {
          "task_id": "check_data_volume",
          "condition": "output.record_count <= 100000 AND output.record_count > 0",
          "condition_type": "expression"
        }
      ]
    },
    {
      "id": "handle_no_data",
      "name": "Handle No Data",
      "type": "python",
      "command": "send_no_data_notification()",
      "depends_on": [
        {
          "task_id": "check_data_volume",
          "condition": "output.record_count == 0",
          "condition_type": "expression"
        }
      ]
    }
  ]
}
```

**Execution Flow:**
1. **check_data_volume** runs first and determines record count
2. Based on the count, **only one** of the following executes:
   - **process_large_batch** if count > 100,000
   - **process_small_batch** if count 1-100,000
   - **handle_no_data** if count = 0

This demonstrates **true conditional branching** where different execution paths are taken based on data-driven decisions.

### Loop Workflow Example

**Business Case:** Process multiple data files with parallel execution and error handling.

```json
{
  "name": "file_processing_pipeline",
  "description": "Process multiple data files in parallel",
  "schedule": {
    "type": "cron",
    "expression": "0 3 * * *",
    "timezone": "UTC"
  },
  "tasks": [
    {
      "id": "list_files",
      "name": "List Files to Process",
      "type": "python",
      "command": "return {'files': ['customers.csv', 'orders.csv', 'products.csv']}",
      "timeout": 300,
      "retries": 2
    },
    {
      "id": "process_files",
      "name": "Process Each File",
      "type": "python",
      "command": "process_data_file(file)",
      "loop": {
        "type": "for_each",
        "items": {
          "source": "task_output",
          "task_id": "list_files",
          "path": "output.files"
        },
        "item_variable": "file",
        "max_concurrency": 3,
        "on_failure": "continue"
      },
      "depends_on": [
        {"task_id": "list_files", "condition": "success"}
      ],
      "timeout": 1800,
      "retries": 1
    },
    {
      "id": "generate_report",
      "name": "Generate Processing Report",
      "type": "python",
      "command": "generate_processing_report()",
      "depends_on": [
        {"task_id": "process_files", "condition": "success"}
      ]
    }
  ],
  "error_handling": {
    "on_failure": "fail",
    "notification_emails": ["data-team@company.com"]
  }
}
```

**Execution Flow:**
1. **list_files** runs first and returns list of files to process
2. **process_files** runs in parallel for each file (max 3 concurrent)
3. If any file processing fails, continue with remaining files
4. **generate_report** runs after all file processing completes

**Key Benefits:**
- **Parallel Processing**: Multiple files processed simultaneously
- **Error Resilience**: Failed files don't stop the entire pipeline
- **Dynamic Items**: File list determined at runtime
- **Resource Control**: Concurrency limits prevent resource exhaustion

### Batch Processing Loop Example

**Business Case:** Process large dataset in manageable batches.

```json
{
  "name": "batch_data_processing",
  "description": "Process large dataset in batches",
  "tasks": [
    {
      "id": "process_batches",
      "name": "Process Data Batches",
      "type": "sql",
      "command": "INSERT INTO processed_data SELECT * FROM raw_data WHERE id BETWEEN {batch_start} AND {batch_end}",
      "loop": {
        "type": "range",
        "items": {
          "source": "range",
          "start": 1,
          "end": 1000000,
          "step": 10000
        },
        "item_variable": "batch_start",
        "max_concurrency": 5
      },
      "timeout": 3600,
      "retries": 2
    }
  ]
}
```

**Processing Pattern:**
- Batch 1: IDs 1-10,000
- Batch 2: IDs 10,001-20,000
- Batch 3: IDs 20,001-30,000
- ... (up to 1,000,000)
- Maximum 5 batches processing simultaneously

### Quality Improvement Loop Example

**Business Case:** Iteratively improve data quality until threshold is met.

```json
{
  "name": "iterative_quality_improvement",
  "description": "Improve data quality iteratively",
  "tasks": [
    {
      "id": "improve_quality",
      "name": "Improve Data Quality",
      "type": "python",
      "command": "return improve_data_quality_iteration()",
      "loop": {
        "type": "while",
        "condition": "output.quality_score < 0.95",
        "item_variable": "iteration",
        "max_iterations": 10
      },
      "timeout": 1800,
      "retries": 1
    },
    {
      "id": "finalize_data",
      "name": "Finalize High-Quality Data",
      "type": "sql",
      "command": "INSERT INTO production.clean_data SELECT * FROM staging.improved_data",
      "depends_on": [
        {"task_id": "improve_quality", "condition": "success"}
      ]
    }
  ]
}
```

**Execution Pattern:**
- Iteration 1: quality_score = 0.85 → continue
- Iteration 2: quality_score = 0.91 → continue
- Iteration 3: quality_score = 0.96 → stop (threshold met)
- **finalize_data** runs with high-quality data

### Loop Validation Rules

**Loop Configuration Validation:**
- **Loop types**: `for_each`, `range`, `while`
- **Items source**: `static`, `task_output`, `range`
- **Max concurrency**: 1 to 100 (for_each loops)
- **Max iterations**: 1 to 1000 (while loops)
- **Item variable**: Valid identifier string
- **On failure**: `fail`, `continue`, `break`

**Items Validation:**
- **Static items**: Non-empty array of values
- **Task output**: Valid task_id and JSONPath
- **Range items**: start < end, step > 0

**Loop Dependencies:**
- Tasks with loops can have normal dependencies
- Loop execution happens after dependencies are satisfied
- Downstream tasks wait for entire loop completion

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

### Step Functions Scheduling

**Step Functions does not have built-in scheduling** - it relies on external triggers:

- **EventBridge Rules**: FLEX schedule expressions are converted to EventBridge rules that trigger the state machine
- **Cron expressions**: `"0 9 * * *"` becomes EventBridge cron rule `cron(0 9 * * ? *)`
- **Rate expressions**: `"rate(1 day)"` becomes EventBridge rate rule `rate(1 day)`
- **Manual execution**: No EventBridge rule created
- **Event-driven**: EventBridge rules based on S3, DynamoDB, or other AWS service events

**Generated Step Functions include:**
- State machine definition (workflow logic)
- EventBridge rule configuration (scheduling)
- IAM roles and permissions
- Integration with other AWS services

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

## Business Rules (Organization-Specific Only)
- Actual scheduling patterns from your existing workflows
- Specific retry configurations from source code
- Documented notification patterns from original pipelines

## Common Patterns (Specific Examples Only)
- Actual data flow patterns from your existing workflows
- Specific query templates used in your organization
- Documented parallel processing configurations from source code
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

**⚠️ Throttling Warning for Integration Tests**

Integration tests may run indefinitely due to Bedrock throttling with newer models. **Always use Claude 3 Sonnet for testing:**

```bash
# Create config to avoid throttling
echo '{
  "llm_config": {
    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0" // pragma: allowlist secret
  }
}' > tests/integration/integration_test_config.json
```

**⚠️ AWS Credentials Setup for Integration Tests**

For full integration testing with AI enhancement, you must have AWS credentials configured:

**Option 1: Configure Default Profile (Recommended)**
```bash
# Set up default AWS profile
aws configure
# Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output format (json)
```

**Option 2: Copy Existing Profile as Default**
```bash
# If you have an existing profile, copy its credentials to default
echo -e "\n[default]\naws_access_key_id = YOUR_ACCESS_KEY\naws_secret_access_key = YOUR_SECRET_KEY\nregion = us-east-1" >> ~/.aws/credentials
```

**Option 3: Use Named Profile (May require additional config)**
```bash
# Ensure profile exists in both ~/.aws/credentials AND ~/.aws/config
echo -e "\n[profile your-profile-name]\nregion = us-east-1\noutput = json" >> ~/.aws/config

# Run tests with specific profile
AWS_PROFILE=your-profile-name python -m pytest tests/integration/test_integration.py::TestIntegration::test_all_mcp_tools -v -s
```

**Required AWS Setup:**
- **IAM Permissions**: `bedrock:InvokeModel` and `sts:GetCallerIdentity`
- **Bedrock Model Access**: Enable Claude Sonnet 4 in AWS Console → Bedrock → Model access
- **Region**: Model access must be granted in the same region as your AWS credentials (us-east-1)

**Integration Test Commands:**
```bash
# Quick test mode (strategic file selection) - ALWAYS use -s to see progress
python -m pytest tests/integration/test_integration.py::TestIntegration::test_all_mcp_tools -v -s

# Full test mode (all files in each framework directory)
INTEGRATION_TEST_MODE=full python -m pytest tests/integration/test_integration.py::TestIntegration::test_all_mcp_tools -v -s

# With named profile (if properly configured)
AWS_PROFILE=your-profile-name python -m pytest tests/integration/test_integration.py::TestIntegration::test_all_mcp_tools -v -s
```

**⚠️ Important**: Always use `-s` flag to see detailed test progress. Without `-s`, you only see the final PASSED/FAILED result.

**The `-s` Option Explained:**
- **Without `-s`**: pytest captures all output and only shows final PASSED/FAILED status
- **With `-s`**: Shows real-time progress including:
  - MCP server startup messages
  - AWS configuration details
  - Individual tool execution progress
  - File processing status
  - AI enhancement logs
  - Detailed error messages if failures occur

**Test Modes:**
- **Quick Mode** (default): Tests 7 strategic files covering key patterns - fast execution with good coverage
- **Full Mode**: Tests all files in each framework directory - comprehensive but slower

**Verify AWS Setup:**
```bash
# Test default profile
aws sts get-caller-identity

# Test named profile
AWS_PROFILE=your-profile-name aws sts get-caller-identity
```

**Without AWS Credentials:**
- Tests still pass using deterministic parsing only
- AI enhancement skipped with "Unable to locate credentials" warnings
- Demonstrates hybrid approach: 95%+ completeness from deterministic parsing alone

**What it tests:**
- Spawns fresh MCP server process via MCP protocol
- Tests all 6 MCP tools with most complex workflow files
- Single workflow tools: parse-single, convert-single, generate-single
- Directory tools: parse-to-flex, convert-etl-workflow, generate-from-flex
- Creates organized output in outputs/integration_tests/ with clear naming

**See `tests/unit/README.md` and `tests/integration/README.md` for detailed testing instructions.**

#### Test Categories

**Unit Tests** (`tests/unit/`):
- Fast, isolated component tests
- No external dependencies required
- `test_llm_config.py`, `test_generators.py`, `test_parsers.py`, etc.

**Integration Tests** (`tests/integration/`):
- End-to-end workflow tests using real sample data
- **Requires MCP server to be running locally**
- **Optional AWS credentials for AI enhancement** (tests pass without credentials using deterministic parsing)
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
