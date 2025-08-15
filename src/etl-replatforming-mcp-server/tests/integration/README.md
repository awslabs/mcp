# Integration Test Configuration

## LLM Model Configuration

The integration test supports multiple ways to configure the LLM model used for AI-enhanced parsing:

### Option 1: Configuration File (Recommended)

Create `integration_test_config.json` in the `tests/integration/` directory:

```json
{
  "llm_config": {
    "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "max_tokens": 50000,
    "temperature": 0.1,
    "region": "us-east-1"
  }
}
```

**Available Models:**
- `anthropic.claude-sonnet-4-20250514-v1:0` (requires inference profile permissions, **may throttle**)
- `anthropic.claude-3-5-sonnet-20241022-v2:0` (requires inference profile permissions, **may throttle**)
- `anthropic.claude-3-sonnet-20240229-v1:0` (**⭐ RECOMMENDED FOR TESTING** - higher rate limits, no throttling)
- `anthropic.claude-3-haiku-20240307-v1:0` (fastest, good for simple workflows)

**⚠️ Throttling Issues:**
Newer models (Claude Sonnet 4, Claude 3.5 Sonnet) use AWS inference profiles with lower rate limits and **may cause integration tests to run indefinitely** due to `ThrottlingException` errors. **Always use Claude 3 Sonnet for integration testing.**

**Run test:**
```bash
# Activate virtual environment first
source venv/bin/activate

# Set environment variables
export AWS_PROFILE=your-profile
export AWS_REGION=us-east-1

# Run integration test directly
python tests/integration/test_integration.py
```

### Option 2: Environment Variables

Override specific settings without a config file:

```bash
# Activate virtual environment first
source venv/bin/activate

# Set environment variables
export AWS_PROFILE=your-profile
export BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
export BEDROCK_MAX_TOKENS=30000
export BEDROCK_TEMPERATURE=0.2
export MCP_LOG_FILE=integration_test.log

# Run integration test directly
python tests/integration/test_integration.py
```

### Option 3: Combined Approach

Use config file as base, override with environment variables:

1. Create `integration_test_config.json` with defaults
2. Set environment variables to override specific values
3. Environment variables take precedence over config file

## AWS Configuration

### Required Environment Variables

- `AWS_PROFILE`: AWS profile with Bedrock permissions (required)
- `AWS_REGION`: AWS region for Bedrock service (optional, defaults to us-east-1)

### IAM Permissions

Your AWS profile needs these permissions:

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

## Test Output

The integration test creates organized output directories:

```
outputs/integration_tests/integration_test_YYYYMMDD_HHMMSS/
├── integration_test.log                    # Test execution log
├── comprehensive_test_summary.json         # Detailed results
├── mcp_server.log                         # MCP server logs (if MCP_LOG_FILE set)
├── single_workflow_tools/                 # Individual workflow conversions
│   ├── flex/parse-single-workflow-to-flex/
│   ├── airflow/convert-single-etl-workflow/
│   └── step_functions/convert-single-etl-workflow/
└── directory_tools/                       # Batch processing results
    ├── flex/parse-to-flex/
    ├── airflow/convert-etl-workflow/
    └── step_functions/convert-etl-workflow/
```

## Example Commands

### Test with Claude 3 Sonnet (Recommended for Testing)
```bash
# Create config file
echo '{
  "llm_config": {
    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
    "max_tokens": 50000,
    "temperature": 0.1,
    "region": "us-east-1"
  }
}' > tests/integration/integration_test_config.json

# Activate venv and run test
source venv/bin/activate
export AWS_PROFILE=your-profile
export MCP_LOG_FILE=integration_test.log
python tests/integration/test_integration.py
```

### Test with Claude Sonnet 4
```bash
# Create config file
echo '{
  "llm_config": {
    "model_id": "anthropic.claude-sonnet-4-20250514-v1:0",
    "max_tokens": 50000,
    "temperature": 0.1,
    "region": "us-east-1"
  }
}' > tests/integration/integration_test_config.json

# Activate venv and run test
source venv/bin/activate
export AWS_PROFILE=your-profile
export MCP_LOG_FILE=integration_test.log
python tests/integration/test_integration.py
```

### Test without AI Enhancement
```bash
# No config file, no AWS credentials - uses deterministic parsing only
source venv/bin/activate
python tests/integration/test_integration.py
```

## Test Modes

The integration test supports two modes to balance coverage and execution time:

### Quick Mode (Default)
**Tests single most complex file per framework - covers all functionality in minimal time**

```bash
# Quick mode (default)
source venv/bin/activate
python tests/integration/test_integration.py

# Explicit quick mode
source venv/bin/activate
INTEGRATION_TEST_MODE=quick python tests/integration/test_integration.py
```

**Files tested:**
- Step Functions: `03_parallel_processing.json`, `05_error_handling_complex.json`, `07_advanced_loops_and_conditions.json`
- Airflow: `04_conditional_branching.py`, `06_extremely_complex_pipeline.py`, `07_advanced_loops_and_conditions.py`
- Azure Data Factory: `07_advanced_loops_and_conditions.json`

**Benefits:**
- **Fast execution** - 7 strategic files vs 20+ in full mode
- **Pattern coverage** - parallel processing, error handling, conditionals, loops
- **Throttling resistant** - moderate API calls, much safer than full mode
- **CI/CD friendly** - predictable execution time under 10 minutes

### Full Mode
**Tests all files in each framework directory - comprehensive but slower**

```bash
# Full mode
source venv/bin/activate
INTEGRATION_TEST_MODE=full python tests/integration/test_integration.py
```

**Files tested:**
- All 7 Step Functions files (01-07)
- All 7 Airflow files (01-07)
- All Azure Data Factory files

**Benefits:**
- **Comprehensive testing** - all sample files processed
- **Regression detection** - catches issues in simpler patterns
- **Performance testing** - validates bulk processing

**Drawbacks:**
- **Slower execution** - 20+ files processed
- **Higher throttling risk** - more API calls to Bedrock
- **Resource intensive** - more temporary files created

### Recommendation

**Use Quick Mode for:**
- Daily development testing
- CI/CD pipelines
- Throttling-prone environments
- Initial validation

**Use Full Mode for:**
- Pre-release validation
- Performance testing
- Comprehensive regression testing
- When you have high Bedrock quotas

## Troubleshooting

### Model Not Found Error
- Ensure model access is granted in AWS Bedrock console
- Check that you're in the correct AWS region
- Verify IAM permissions include the specific model ARN

### Throttling Errors
- **⭐ Switch to Claude 3 Sonnet** (`anthropic.claude-3-sonnet-20240229-v1:0`) - highest rate limits, no inference profile
- **Use Quick Mode** (`INTEGRATION_TEST_MODE=quick`) to minimize API calls
- Request quota increase from AWS Support for newer models
- Consider Provisioned Throughput for high-volume production use
- **Avoid Claude Sonnet 4 and Claude 3.5 Sonnet for integration testing** due to lower rate limits

### Tests Running Forever
- **Cause**: Bedrock throttling with newer models causes indefinite retries
- **Solution**: Use Claude 3 Sonnet model and Quick Mode
- **Emergency**: Kill test process and switch to Claude 3 Sonnet configuration

### Config Not Loading
- Ensure `integration_test_config.json` is in the `tests/integration/` directory
- Check JSON syntax is valid
- Look for "📄 Loaded LLM config" message in test output
