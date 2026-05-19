# Amazon Translate MCP Server

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

A Model Context Protocol (MCP) server that provides AI applications with access to neural machine translation service, Amazon Translate for text translation, managed batch processing, and smart translation workflow management across 75+ languages.

## Features

- **Text Translation**: Real-time translation with custom terminology support
- **Managed Batch Processing**: End to End Large-scale document translation with S3 integration , monitoring and error analysis
- **Language Detection**: Automatic source language identification
- **Custom Terminology**: Domain-specific translation consistency
- **Intelligent Workflows**: Automated multi-step translation processes with workflow orchestration
- **Error Analysis**: Comprehensive error analysis for failed jobs

## Installation

### Using uvx (Recommended)

```bash
uvx awslabs.amazon-translate-mcp-server@latest
```

### Using pip

```bash
pip install awslabs.amazon-translate-mcp-server
python -m awslabs.amazon_translate_mcp_server.server
```

## Configuration

### Environment Variables

```bash
# AWS Configuration (required)
export AWS_REGION=us-east-1
export AWS_PROFILE=your-profile

# Optional Settings
export FASTMCP_LOG_LEVEL=INFO
export TRANSLATE_MAX_TEXT_LENGTH=10000
```

### MCP Client Setup

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "amazon-translate": {
      "command": "uvx",
      "args": ["awslabs.amazon-translate-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "default"
      }
    }
  }
}
```

## Available Tools

### Translation Operations
- `translate_text` - Translate text between languages
- `detect_language` - Identify source language automatically
- `validate_translation` - Quality assessment of translations

### Batch Operations
- `start_batch_translation` - Process multiple documents
- `get_translation_job` - Monitor job status
- `list_translation_jobs` - View all translation jobs
- `trigger_batch_translation` - Start job without monitoring
- `monitor_batch_translation` - Monitor until completion
- `analyze_batch_translation_errors` - Analyze failed jobs

### Terminology Management
- `list_terminologies` - Browse custom terminology sets
- `create_terminology` - Create domain-specific terms
- `import_terminology` - Import from CSV/TMX files
- `get_terminology` - Get terminology details

### Language Operations
- `list_language_pairs` - Show supported language combinations
- `get_language_metrics` - View usage statistics

### Workflow Operations
- `smart_translate_workflow` - Automated translation with quality validation
- `managed_batch_translation_workflow` - Complete batch lifecycle management
- `list_active_workflows` - Monitor running workflows
- `get_workflow_status` - Get workflow progress

## Usage Examples

### Basic Translation

```python
# Translate text
translate_text(
    text="Hello, world!",
    source_language="en",
    target_language="es"
)
# Returns: "¡Hola, mundo!"

# Auto-detect language
detect_language(text="Bonjour le monde")
# Returns: {"detected_language": "fr", "confidence_score": 0.99}
```

### Batch Translation

```python
# Start batch job
start_batch_translation(
    input_s3_uri="s3://my-bucket/documents/",
    output_s3_uri="s3://my-bucket/translated/",
    data_access_role_arn="arn:aws:iam::123456789012:role/TranslateRole",
    job_name="my-translation-job",
    source_language="en",
    target_languages=["es", "fr", "de"]
)
```

### Smart Workflow

```python
# Automated translation with quality validation
smart_translate_workflow(
    text="Hello, how are you?",
    target_language="es",
    quality_threshold=0.8
)
```

## AWS Permissions

Required IAM permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "translate:*",
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket",
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
```

## Troubleshooting

1. **Authentication Errors**: Ensure AWS credentials are configured
2. **Translation Failures**: Check language pair support and text length limits
3. **Batch Job Issues**: Verify S3 permissions and IAM role configuration
4. **Workflow Issues**: Check workflow orchestrator in health check

## Development

```bash
# Clone and install
git clone https://github.com/awslabs/mcp.git
cd mcp/src/amazon-translate-mcp-server
uv venv && uv sync --all-groups

#mcp inspector
npx @modelcontextprotocol/inspector uv --directory <directory path to amazon-translate-mcp-server> run --module awslabs.amazon_translate_mcp_server.server

# Run tests
uv run --frozen pytest --cov --cov-branch --cov-report=term-missing

```

## License

Apache License 2.0

## Support

- [Documentation](https://awslabs.github.io/mcp/)
- [Issues](https://github.com/awslabs/mcp/issues)
- [Discussions](https://github.com/awslabs/mcp/discussions)

---

**Note**: Requires AWS account with Amazon Translate access. AWS charges apply.
