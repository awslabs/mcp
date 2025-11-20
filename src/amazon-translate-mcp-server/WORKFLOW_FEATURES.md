# Amazon Translate MCP Server - Workflow Features

This document describes the intelligent workflow orchestration features added to the Amazon Translate MCP Server, which combine multiple translation operations into cohesive, automated workflows for enhanced user experience.

## Overview

The workflow features provide two main intelligent workflows:

1. **Smart Translation Workflow** - Automated language detection, translation, and quality validation
2. **Managed Batch Translation Workflow** - Complete batch job lifecycle management with monitoring

## Smart Translation Workflow

### Purpose
Intelligent translation with automatic language detection and quality validation, eliminating the need for users to manually identify languages or validate results.

### Features
- **Auto-Detection**: Eliminates manual language specification
- **Quality Assurance**: Built-in translation validation with confidence scoring
- **Language Validation**: Automatic verification of supported language pairs
- **Comprehensive Results**: Single response with detection, translation, and quality metrics

### Workflow Steps
1. `detect_language` - Automatically identify source text language with alternatives
2. `validate_language_pair` - Verify the language pair is supported
3. `translate_text` - Perform translation with optional terminology
4. `validate_translation` - Quality check with scoring and suggestions

### Usage

```python
# MCP Tool Call
result = await mcp_client.call_tool("smart_translate_workflow", {
    "text": "Bonjour, comment allez-vous?",
    "target_language": "en",
    "quality_threshold": 0.8,
    "terminology_names": ["business-terms"],  # Optional
    "auto_detect_language": True
})
```

### Response Structure

```json
{
    "workflow_type": "smart_translation",
    "original_text": "Bonjour, comment allez-vous?",
    "translated_text": "Hello, how are you?",
    "detected_language": "fr",
    "target_language": "en",
    "confidence_score": 0.95,
    "quality_score": 0.92,
    "applied_terminologies": ["business-terms"],
    "language_pair_supported": true,
    "validation_issues": [],
    "suggestions": [],
    "execution_time_ms": 1250.5,
    "workflow_steps": [
        "detect_language",
        "validate_language_pair",
        "translate_text",
        "validate_translation"
    ]
}
```

## Managed Batch Translation Workflow

### Purpose
Complete batch translation lifecycle management with automated monitoring, pre-validation of resources, and comprehensive progress tracking without manual intervention.

### Features
- **Pre-Validation**: Language pair and terminology validation before job start
- **Automated Monitoring**: Continuous progress tracking with detailed history
- **Performance Analytics**: Post-completion metrics and optimization insights
- **Error Recovery**: Comprehensive error handling and status reporting

### Workflow Steps
1. `validate_language_pairs` - Verify all requested language pairs are supported
2. `validate_terminologies` - Check terminology availability (if specified)
3. `start_batch_job` - Initialize batch translation with S3 integration
4. `monitor_job_progress` - Continuous monitoring with automated polling
5. `collect_metrics` - Gather performance analytics upon completion

### Usage

```python
# MCP Tool Call
result = await mcp_client.call_tool("managed_batch_translation_workflow", {
    "input_s3_uri": "s3://content-bucket/documents/",
    "output_s3_uri": "s3://output-bucket/translated/",
    "data_access_role_arn": "arn:aws:iam::123456789012:role/TranslateRole",
    "job_name": "website-localization",
    "source_language": "en",
    "target_languages": ["es", "fr", "de"],
    "terminology_names": ["ui-terms"],  # Optional
    "content_type": "text/html",
    "monitor_interval": 30,  # seconds
    "max_monitoring_duration": 3600  # seconds
})
```

### Response Structure

```json
{
    "workflow_type": "managed_batch_translation",
    "job_id": "batch-translate-job-12345",
    "job_name": "website-localization",
    "status": "COMPLETED",
    "source_language": "en",
    "target_languages": ["es", "fr", "de"],
    "input_s3_uri": "s3://content-bucket/documents/",
    "output_s3_uri": "s3://output-bucket/translated/",
    "terminology_names": ["ui-terms"],
    "pre_validation_results": {
        "supported_pairs": ["en->es", "en->fr", "en->de"],
        "unsupported_pairs": [],
        "terminologies": {
            "requested": ["ui-terms"],
            "available": ["ui-terms", "legal-terms"],
            "validated": true
        }
    },
    "monitoring_history": [
        {
            "timestamp": "2024-01-15T10:00:00Z",
            "status": "SUBMITTED",
            "progress": 0,
            "elapsed_time": 0
        },
        {
            "timestamp": "2024-01-15T10:20:00Z",
            "status": "COMPLETED",
            "progress": 100,
            "elapsed_time": 1200
        }
    ],
    "performance_metrics": {
        "language_pairs": {
            "en-es": {
                "translation_count": 1250,
                "character_count": 125000,
                "average_response_time": 0.85,
                "error_rate": 0.001
            }
        },
        "total_monitoring_time": 1200,
        "monitoring_checks": 40,
        "final_status": "COMPLETED"
    },
    "created_at": "2024-01-15T10:00:00Z",
    "completed_at": "2024-01-15T10:20:00Z",
    "total_execution_time": 1200.5,
    "workflow_steps": [
        "validate_language_pairs",
        "validate_terminologies",
        "start_batch_job",
        "monitor_job_progress",
        "collect_metrics"
    ]
}
```

## Workflow Management Tools

### List Active Workflows

Monitor all currently executing workflows:

```python
result = await mcp_client.call_tool("list_active_workflows", {})
```

### Get Workflow Status

Check the status of a specific workflow:

```python
result = await mcp_client.call_tool("get_workflow_status", {
    "workflow_id": "smart_translate_1642234567890"
})
```

## Implementation Details

### Architecture
- **Tool Orchestration**: Combines existing MCP tools in intelligent sequences
- **State Management**: Lightweight session storage for workflow context
- **Error Recovery**: Comprehensive retry logic and failure handling
- **Backward Compatibility**: All existing tools continue to work independently

### Error Handling
- Comprehensive error tracking with workflow context
- Automatic retry logic for transient failures
- Detailed error reporting with step-by-step failure analysis
- Graceful degradation when individual steps fail

### Performance Considerations
- Asynchronous execution with thread pool for synchronous operations
- Efficient resource cleanup and memory management
- Configurable monitoring intervals to balance responsiveness and API usage
- Automatic cleanup of old workflow results

## Use Cases

### Enterprise Content Localization
```python
# Smart workflow for quick document translation
await smart_translate_workflow(
    text=document_content,
    target_language="es",
    quality_threshold=0.9,
    terminology_names=["legal-terms"]
)
```

### Large-Scale Website Localization
```python
# Managed batch workflow for comprehensive site translation
await managed_batch_translation_workflow(
    input_s3_uri="s3://website-content/pages/",
    output_s3_uri="s3://localized-content/",
    source_language="en",
    target_languages=["es", "fr", "de", "it", "pt"],
    terminology_names=["ui-terms", "product-terms"],
    monitor_interval=60
)
```

### Real-time Customer Support
```python
# Smart workflow for instant message translation
await smart_translate_workflow(
    text=customer_message,
    target_language=agent_language,
    quality_threshold=0.8,
    auto_detect_language=True
)
```

## Benefits

### For Developers
- **Simplified Integration**: Single tool calls replace complex multi-step processes
- **Automatic Error Handling**: Built-in retry logic and error recovery
- **Comprehensive Monitoring**: Real-time progress tracking and analytics
- **Quality Assurance**: Automatic validation and quality scoring

### For Organizations
- **Reduced Complexity**: Eliminates need for custom orchestration logic
- **Improved Reliability**: Professional-grade error handling and monitoring
- **Cost Optimization**: Efficient resource usage and automatic cleanup
- **Enhanced Visibility**: Detailed analytics and performance metrics

### For End Users
- **Better Experience**: Faster, more reliable translation workflows
- **Quality Assurance**: Automatic validation ensures translation quality
- **Transparency**: Clear progress tracking and status reporting
- **Flexibility**: Configurable quality thresholds and monitoring intervals

## Getting Started

1. **Install/Update** the Amazon Translate MCP Server with workflow features
2. **Configure** AWS credentials and permissions for Translate, S3, and IAM services
3. **Test** with the provided examples in `examples/workflow_examples.py`
4. **Integrate** workflow tools into your MCP client application
5. **Monitor** workflow execution using the management tools

For detailed examples and integration patterns, see the `examples/` directory.
