# ETL Replatforming MCP Server

**The intelligent, cost-effective solution for ETL framework migration with AI-enhanced parsing and universal workflow conversion.**

MCP server for converting ETL orchestration code between frameworks using FLEX (Framework for Linking ETL eXchange) with validation and user interaction.

## Why This Project?

**ETL framework migration is expensive, error-prone, and time-consuming.** This project solves that with:

- **Cost-Optimized AI Usage**: Hybrid approach - deterministic parsing first, AI only for gaps
- **Universal Framework Support**: One tool handles Airflow ↔ Step Functions ↔ Azure Data Factory
- **Zero Manual Rewrites**: Automated conversion preserves complex pipeline logic
- **Production-Ready**: Handles real-world complexity with validation and error handling
- **FLEX Intermediate Format**: Framework-agnostic representation ensures semantic preservation

## How It Works

```
Source Framework → DETERMINISTIC PARSE → [AI ENHANCEMENT] → FLEX → Target Framework
```

**Hybrid Parsing Benefits:**
- **Consistency**: Deterministic parsing produces identical results for identical inputs
- **Performance**: Only incomplete workflows trigger AI enhancement
- **Cost-Effective**: AI used selectively rather than for entire conversions
- **Transparency**: Clear tracking of what was parsed vs AI-enhanced

## Key Features

- **Universal Framework Support**: Convert between Airflow, Step Functions, Azure Data Factory
- **Hybrid Parsing**: Deterministic parsing + AI enhancement for optimal cost and accuracy
- **FLEX Intermediate Format**: Framework-agnostic JSON representation
- **Python Code Extraction**: Automatic extraction of Python functions to standalone scripts
- **Production-Ready**: Comprehensive validation, error handling, and logging
- **MCP Integration**: Works with Claude Desktop and other MCP clients

## Supported Frameworks

| Framework | Parser | Generator | Python Scripts | Status |
|-----------|--------|-----------|----------------|--------|
| Step Functions | ✅ | ✅ | ✅ Glue Jobs | Complete |
| Airflow | ✅ | ✅ | ✅ Extraction | Complete |
| Azure Data Factory | ✅ | 🚧 | ✅ Ready | Parser Complete |

## Installation

### Using uv (Recommended)
```bash
uv sync
uv run awslabs.etl-replatforming-mcp-server
```

### Using pip
```bash
pip install -e .
awslabs.etl-replatforming-mcp-server
```

## Usage

### Directory-Based Tools (Batch Processing)
- `parse-to-flex` - Convert directory of workflows to FLEX format
- `convert-etl-workflow` - Complete conversion: source directory → target framework
- `generate-from-flex` - Generate target code from FLEX directory

### Single Workflow Tools
- `parse-single-workflow-to-flex` - Convert individual workflow to FLEX
- `convert-single-etl-workflow` - Complete conversion of single workflow
- `generate-single-workflow-from-flex` - Generate target code from FLEX

### Examples
> "Convert jobs in ./step_functions_workflows to airflow"
> "Parse this Step Functions definition to FLEX: {JSON content}"
> "Generate Airflow DAG from this FLEX workflow: {FLEX JSON}"

## FLEX Format

FLEX is the universal intermediate format that enables framework-agnostic workflow representation:

```json
{
  "name": "etl_pipeline",
  "schedule": {
    "type": "cron",
    "expression": "0 2 * * *"
  },
  "tasks": [
    {
      "id": "extract_data",
      "type": "sql",
      "command": "SELECT * FROM customers",
      "depends_on": []
    }
  ]
}
```

## Task Type Mapping

| FLEX Type | Airflow | Step Functions | Azure Data Factory |
|-----------|---------|----------------|-------------------|
| `sql` | `RedshiftSQLOperator` | Redshift Data API | Stored Procedure |
| `python` | `PythonOperator` | Lambda/Glue | Custom Activity |
| `bash` | `BashOperator` | Batch Job | Script Activity |
| `for_each` | `TaskGroup` | Map State | ForEach Activity |

## Configuration

### Environment Variables
```bash
export AWS_REGION=us-east-1    # For Bedrock AI enhancement
export AWS_PROFILE=your-profile
export FASTMCP_LOG_LEVEL=INFO
```

### AWS Bedrock Setup (Optional)
AI enhancement requires AWS Bedrock access:
1. Configure AWS credentials with Bedrock permissions
2. Enable Claude model access in AWS Console
3. Verify setup: `aws bedrock list-foundation-models --region us-east-1`

## Testing

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires MCP server running)
python tests/integration/test_integration.py
```

## Adding New Frameworks

1. **Parser**: Implement `WorkflowParser` interface
2. **Generator**: Implement `BaseGenerator` interface
3. **Register**: Add to framework registry
4. **Test**: Create comprehensive unit tests

## Documentation

- `FLEX_SPECIFICATION.md` - Complete FLEX format documentation
- `samples/` - Example workflows for all supported frameworks
- `tests/integration/README.md` - Integration testing guide

## License

Licensed under the Apache License, Version 2.0.
