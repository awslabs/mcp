# FLEX (Framework for Linking ETL eXchange) Specification

## Overview
FLEX is a framework-agnostic intermediate representation for ETL orchestration workflows. It serves as the universal connector between different orchestration frameworks.

## Core Principles
1. **Framework Independence** - No framework-specific constructs
2. **Universal Task Types** - Generic task categories that map to any framework
3. **Declarative Dependencies** - Clear execution order specification
4. **Standardized Scheduling** - Universal time-based triggers
5. **Comprehensive Error Handling** - Framework-agnostic failure management

## FLEX Document Structure

```json
{
  "name": "workflow_identifier",
  "description": "Human-readable workflow purpose",
  "schedule": {
    "type": "cron|rate|manual|event",
    "expression": "0 9 * * *",
    "timezone": "UTC"
  },
  "tasks": [
    {
      "id": "unique_task_id",
      "name": "Human readable task name",
      "type": "free_form_string",
      "command": "Execution command/script",
      "timeout": 3600,
      "retries": 2,
      "retry_delay": 300,
      "depends_on": [
        {
          "task_id": "upstream_task_id",
          "condition": "success|failure|always"
        }
      ],
      "error_handling": {
        "on_failure": "fail|continue|retry",
        "notification_emails": ["team@company.com"],
        "escalation_policy": "critical-data-pipeline"
      }
    }
  ]
}
```

## Field Generation Rules

### Task ID Generation
- **Auto-generated**: Systems should automatically generate unique IDs if not provided
- **Format**: Use source task names, sanitized for target framework requirements
- **Uniqueness**: Ensure no conflicts within the workflow

### Task Type Flexibility
- **Free-form**: Not restricted to predefined enums
- **Context-aware**: Bedrock generates appropriate types based on target framework
- **Fallback**: User prompts with target framework context if auto-generation fails

## Common Task Types

### SQL Tasks
```json
{
  "type": "sql",
  "command": "SELECT * FROM customers WHERE date = CURRENT_DATE",
  "parameters": {
    "database": "analytics",
    "connection": "data_warehouse"
  }
}
```

### Python Tasks
```json
{
  "type": "python",
  "command": "process_data(input_file, output_file)",
  "script": "def process_data(input_file, output_file): ..."
}
```

### Data Copy Tasks
```json
{
  "type": "copy",
  "source": {
    "type": "sql_server",
    "dataset": "customers",
    "query": "SELECT * FROM customers"
  },
  "sink": {
    "type": "blob_storage",
    "dataset": "processed_customers"
  }
}
```

### Container Tasks
```json
{
  "type": "container",
  "command": "docker run my-etl-image --input s3://bucket/data",
  "resource_requirements": {
    "cpu": "2",
    "memory": "4Gi"
  }
}
```

**Note**: Task types are free-form strings. Use framework-specific types when needed (e.g., "RedshiftSQLOperator", "lambda_invoke", "copy_activity").

## Schedule Types

### Cron Expressions
- Format: `minute hour day month weekday`
- Examples:
  - `"0 9 * * *"` - Daily at 9 AM
  - `"0 */6 * * *"` - Every 6 hours
  - `"0 0 1 * *"` - Monthly on 1st

### Rate Expressions
- Format: `rate(number unit)`
- Examples:
  - `"rate(1 day)"` - Daily
  - `"rate(30 minutes)"` - Every 30 minutes
  - `"rate(2 hours)"` - Every 2 hours

### Manual/Event Triggers
- `"manual"` - User-initiated execution
- `"event"` - External event triggers

## Task Dependencies

Dependencies are defined within each task using the `depends_on` array:

```json
{
  "id": "process_data",
  "type": "python",
  "command": "process_customer_data()",
  "depends_on": [
    {
      "task_id": "extract_data",
      "condition": "success"
    },
    {
      "task_id": "validate_data",
      "condition": "success"
    }
  ]
}
```

### Dependency Conditions
- `"success"` - Run after upstream succeeds (default)
- `"failure"` - Run after upstream fails
- `"always"` - Run regardless of upstream status

## Task Error Handling

Error handling is defined within each task:

```json
{
  "id": "critical_data_load",
  "type": "sql",
  "command": "INSERT INTO production.customers SELECT * FROM staging.customers",
  "error_handling": {
    "on_failure": "fail",
    "notification_emails": ["data-team@company.com", "ops@company.com"],
    "escalation_policy": "critical-pipeline",
    "custom_error_handlers": {
      "data_quality_error": "rollback_and_alert",
      "connection_timeout": "retry_with_backoff"
    }
  }
}
```

### Error Handling Strategies
- `"fail"` - Stop workflow on task failure
- `"continue"` - Continue workflow despite failures
- `"retry"` - Retry failed tasks with backoff

### Task-Level vs Workflow-Level
- **Task-level**: Specific error handling per task (recommended)
- **Workflow-level**: Default error handling for all tasks
- **Precedence**: Task-level overrides workflow-level

## Framework Mapping Reference

### FLEX → Airflow
| FLEX Field | Airflow Equivalent | Notes |
|------------|-------------------|-------|
| `name` | `dag_id` | Workflow identifier |
| `description` | `description` | DAG description |
| `schedule.expression` | `schedule_interval` | Cron/rate expressions |
| `schedule.timezone` | `timezone` | DAG timezone |
| `tasks[].id` | `task_id` | Unique task identifier |
| `tasks[].name` | Task description | Human-readable name |
| `tasks[].type` | Operator class | `"sql"` → `PostgreSQLOperator`, `"python"` → `PythonOperator` |
| `tasks[].command` | Operator parameters | `sql`, `python_callable`, `bash_command` |
| `tasks[].timeout` | `execution_timeout` | Task timeout duration |
| `tasks[].retries` | `retries` | Retry count |
| `tasks[].retry_delay` | `retry_delay` | Delay between retries |
| `tasks[].depends_on` | `>>` operator | Task dependencies |
| `tasks[].error_handling` | Task-level error handling | Failure notifications, retry policies |

### FLEX → Step Functions
| FLEX Field | Step Functions Equivalent | Notes |
|------------|---------------------------|-------|
| `name` | `stateMachineName` | State machine identifier |
| `description` | `Comment` | State machine description |
| `schedule` | EventBridge Rule | External scheduling mechanism |
| `tasks[].id` | State name | Individual state identifier |
| `tasks[].name` | State comment | Human-readable description |
| `tasks[].type` | `Resource` type | `"sql"` → `arn:aws:states:::aws-sdk:redshiftdata:executeStatement` |
| `tasks[].command` | `Parameters` | Passed to AWS service |
| `tasks[].timeout` | `TimeoutSeconds` | State timeout |
| `tasks[].retries` | `Retry` block | Retry configuration |
| `tasks[].depends_on` | `Next` transitions | State flow control |
| `tasks[].error_handling` | `Catch` blocks | Error handling states |

### FLEX → Azure Data Factory
| FLEX Field | ADF Equivalent | Notes |
|------------|----------------|-------|
| `name` | `name` | Pipeline name |
| `description` | `description` | Pipeline description |
| `schedule` | Trigger | Schedule/event triggers |
| `tasks[].id` | Activity name | Unique activity identifier |
| `tasks[].type` | Activity type | `"sql"` → `SqlServerStoredProcedure`, `"copy"` → `Copy` |
| `tasks[].command` | Activity properties | SQL query, stored procedure, etc. |
| `tasks[].timeout` | `timeout` | Activity timeout |
| `tasks[].retries` | `retry` | Retry count |
| `tasks[].depends_on` | `dependsOn` | Activity dependencies |
| `tasks[].error_handling` | Activity policies | Retry and error policies |

## Field Requirements

### Workflow Level
| Field | Required | Default | Notes |
|-------|----------|---------|-------|
| `name` | ✅ | - | Unique workflow identifier |
| `description` | ❌ | `null` | Human-readable description |
| `schedule` | ❌ | `null` | Required for scheduled workflows |
| `tasks` | ✅ | - | At least one task required |
| `metadata` | ❌ | `{}` | Additional workflow metadata |
| `parameters` | ❌ | `{}` | Workflow parameters |
| `variables` | ❌ | `{}` | Workflow variables |
| `triggers` | ❌ | `[]` | Event triggers |
| `concurrency` | ❌ | `null` | Max concurrent executions |
| `tags` | ❌ | `[]` | Workflow classification |

### Task Level
| Field | Required | Default | Notes |
|-------|----------|---------|-------|
| `id` | ❌ | auto-generated | Unique task identifier |
| `name` | ✅ | - | Human-readable task name |
| `type` | ✅ | - | Task type (free-form string) |
| `command` | ❌* | `null` | *Required if no `script` |
| `script` | ❌* | `null` | *Required if no `command` |
| `parameters` | ❌ | `{}` | Task parameters |
| `timeout` | ❌ | `null` | Task timeout (1-86400 seconds) |
| `retries` | ❌ | `0` | Retry count (0-10 maximum) |
| `retry_delay` | ❌ | `300` | Delay between retries (seconds) |
| `depends_on` | ❌ | `[]` | Task dependencies |
| `error_handling` | ❌ | `null` | Task-specific error handling |
| `source` | ❌ | `null` | Data source (for copy tasks) |
| `sink` | ❌ | `null` | Data destination (for copy tasks) |
| `linked_service` | ❌ | `null` | Framework-specific connections |
| `compute_target` | ❌ | `null` | Execution environment |
| `resource_requirements` | ❌ | `{}` | CPU, memory requirements |

### Schedule Fields
| Field | Required | Default | Notes |
|-------|----------|---------|-------|
| `type` | ✅ | - | Schedule type (cron, rate, manual, event) |
| `expression` | ✅ | - | Cron/rate expression |
| `timezone` | ❌ | `"UTC"` | Timezone for schedule |
| `start_date` | ❌ | `null` | Schedule start date |
| `end_date` | ❌ | `null` | Schedule end date |

### Dependency Fields
| Field | Required | Default | Notes |
|-------|----------|---------|-------|
| `task_id` | ✅ | - | Referenced task ID |
| `condition` | ❌ | `"success"` | Dependency condition |

### Error Handling Fields
| Field | Required | Default | Notes |
|-------|----------|---------|-------|
| `on_failure` | ❌ | `"fail"` | Failure strategy |
| `notification_emails` | ❌ | `[]` | Email notifications |
| `max_retries` | ❌ | `0` | Maximum retry attempts |
| `retry_delay` | ❌ | `300` | Retry delay (seconds) |
| `notification_webhooks` | ❌ | `[]` | Webhook notifications |
| `escalation_policy` | ❌ | `null` | Escalation policy name |
| `custom_error_handlers` | ❌ | `{}` | Custom error handlers |

## Validation Rules

### Required Field Validation
- Only fields marked as ✅ Required will cause validation failure
- Optional fields with invalid values will generate warnings
- Missing optional fields use default values

### Value Validation
- `timeout`: 1 to 86400 seconds if provided
- `retries`: 0 to 10 maximum if provided
- `schedule.expression`: Valid cron (5-field) or rate format
- `depends_on.task_id`: Must reference existing task
- `depends_on.condition`: Must be "success", "failure", or "always"
- No circular dependencies in task graph

### Incomplete FLEX Handling
When validation fails, the MCP server response includes:
```json
{
  "status": "incomplete",
  "missing_information": "Missing required fields: tasks[0].name, schedule.expression",
  "message": "Please check FLEX_SPECIFICATION.md for field requirements and examples",
  "flex_workflow": { /* FLEX with placeholders */ }
}
```

## Usage Notes

- **✅ Required**: Field must be present and valid
- **❌ Optional**: Field can be omitted (uses default value)
- **❌***: Either this field OR alternative field is required

For missing required fields, check this specification document for:
- Field descriptions and examples
- Default values for optional fields
- Framework-specific mapping guidance
- Validation rules and constraints

## Complete Workflow Example

Here's a realistic ETL pipeline demonstrating all FLEX concepts:

```json
{
  "name": "employee_department_analysis",
  "description": "ETL pipeline to analyze employee data by department with salary statistics",
  "schedule": {
    "type": "rate",
    "expression": "rate(1 day)",
    "timezone": "UTC",
    "start_date": "2024-01-01T08:00:00Z"
  },
  "tasks": [
    {
      "id": "load_employee_data",
      "name": "Load Employee Data",
      "type": "sql",
      "command": "CREATE TABLE staging.employees AS\nSELECT \n    employee_id,\n    name,\n    department,\n    salary,\n    hire_date,\n    status\nFROM raw_data.employees\nWHERE status = 'Active';",
      "parameters": {
        "cluster": "analytics_cluster",
        "database": "hr_analytics",
        "input_file": "s3://data-bucket/employees.csv"
      },
      "timeout": 1800,
      "retries": 2,
      "retry_delay": 300
    },
    {
      "id": "load_department_data",
      "name": "Load Department Data",
      "type": "sql",
      "command": "CREATE TABLE staging.departments AS\nSELECT \n    department,\n    budget,\n    manager\nFROM raw_data.departments;",
      "parameters": {
        "cluster": "analytics_cluster",
        "database": "hr_analytics",
        "input_file": "s3://data-bucket/departments.csv"
      },
      "timeout": 1800,
      "retries": 2,
      "retry_delay": 300
    },
    {
      "id": "create_department_summary",
      "name": "Create Department Summary Report",
      "type": "sql",
      "command": "CREATE TABLE analytics.department_summary AS\nSELECT \n    d.department,\n    d.manager,\n    d.budget,\n    COUNT(e.employee_id) as employee_count,\n    AVG(e.salary) as avg_salary,\n    MIN(e.salary) as min_salary,\n    MAX(e.salary) as max_salary,\n    SUM(e.salary) as total_salary_cost,\n    (d.budget - SUM(e.salary)) as remaining_budget,\n    CURRENT_DATE as report_date\nFROM staging.departments d\nLEFT JOIN staging.employees e ON d.department = e.department\nGROUP BY d.department, d.manager, d.budget;",
      "parameters": {
        "cluster": "analytics_cluster",
        "database": "hr_analytics",
        "output_table": "analytics.department_summary"
      },
      "timeout": 3600,
      "retries": 3,
      "retry_delay": 600,
      "depends_on": [
        {
          "task_id": "load_employee_data",
          "condition": "success"
        },
        {
          "task_id": "load_department_data",
          "condition": "success"
        }
      ]
    },
    {
      "id": "export_results",
      "name": "Export Results to S3",
      "type": "sql",
      "command": "UNLOAD ('SELECT * FROM analytics.department_summary ORDER BY department')\nTO 's3://output-bucket/department_analysis/dt=' || TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD') || '/'\nIAM_ROLE 'arn:aws:iam::123456789:role/RedshiftRole'\nFORMAT AS PARQUET;",
      "parameters": {
        "cluster": "analytics_cluster",
        "database": "hr_analytics",
        "output_path": "s3://output-bucket/department_analysis/"
      },
      "timeout": 1800,
      "retries": 2,
      "retry_delay": 300,
      "depends_on": [
        {
          "task_id": "create_department_summary",
          "condition": "success"
        }
      ],
      "error_handling": {
        "on_failure": "fail",
        "notification_emails": ["data-team@company.com", "hr-team@company.com"],
        "escalation_policy": "critical-data-pipeline"
      }
    }
  ],
  "metadata": {
    "source_framework": "flex",
    "author": "data-engineering-team",
    "created_date": "2024-01-15",
    "purpose": "Daily HR analytics pipeline for department-wise employee analysis",
    "data_sources": ["employees.csv", "departments.csv"],
    "output_format": "parquet",
    "business_owner": "HR Department"
  }
}
```

### Example Highlights

**Task Dependencies**: Notice how `create_department_summary` depends on both data loading tasks using task-embedded `depends_on` arrays.

**Error Handling**: The `export_results` task has specific error handling with email notifications and escalation policy.

**Scheduling**: Uses rate-based scheduling (`rate(1 day)`) with timezone specification.

**Parameters**: Each task includes framework-specific parameters for database connections and file paths.

**Metadata**: Rich metadata for governance, lineage, and documentation.

This specification ensures FLEX documents are truly framework-agnostic and can represent any ETL orchestration workflow.
