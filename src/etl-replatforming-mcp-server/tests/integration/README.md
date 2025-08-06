# Integration Tests

End-to-end tests using real sample data and full conversion workflows.

## Prerequisites

**⚠️ IMPORTANT: Complete setup required before running integration tests**

1. **Create and Activate Virtual Environment:**
   ```bash
   # Using uv (recommended - handles venv automatically)
   uv sync
   
   # Using pip with manual venv
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -e .
   ```

2. **Verify Installation:**
   ```bash
   # Test imports work
   python -c "from awslabs.etl_replatforming_mcp_server.server import main; print('✅ Installation successful')"
   ```
   
   **Expected output:** `✅ Installation successful`  
   **If you see import errors:** Dependencies not installed or package not in development mode

3. **Start the MCP Server:**
   ```bash
   # Using uv (recommended)
   uv run awslabs.etl-replatforming-mcp-server
   
   # Using pip (ensure venv is activated)
   awslabs.etl-replatforming-mcp-server
   ```

4. **AWS Bedrock Setup:** Configure AWS credentials and Bedrock model access (see main README)

## Troubleshooting

### AWS Token Expiration Issues

**Problem:** `ExpiredTokenException` when calling Bedrock

**Root Cause:** Environment variables with expired credentials take precedence over fresh AWS profile credentials.

**Automatic Fix:** The MCP server automatically falls back to your AWS profile when environment credentials expire. You should see: `"Environment credentials expired, trying AWS profile..."`

**Manual Fix (if automatic fails):**

1. **Clear Expired Environment Variables:**
   ```bash
   # Remove expired environment credentials
   unset AWS_ACCESS_KEY_ID
   unset AWS_SECRET_ACCESS_KEY
   unset AWS_SESSION_TOKEN
   
   # Keep profile and region
   export AWS_PROFILE=your-profile-name
   export AWS_REGION=us-east-1
   ```

2. **Verify Credentials Work:**
   ```bash
   # Test AWS CLI access
   aws sts get-caller-identity
   
   # Test Bedrock access
   aws bedrock list-foundation-models --region us-east-1
   ```

3. **Debug Credential Issues:**
   ```bash
   # Check which credentials Python sees
   python3 debug_aws_credentials.py
   ```

**Common Scenarios:**
- **AWS CLI works, Python fails** → Environment variables are expired
- **Both fail** → Profile credentials need refresh
- **Temporary credentials** → Session tokens expire frequently

**Note:** The integration test will continue to work without Bedrock - workflows may just be incomplete and require more user prompts.

## Test Assumptions

- **Package Installation**: Requires `pip install -e .` for imports to work
- **Server Process**: Expects `awslabs.etl-replatforming-mcp-server` process running locally
- **Direct Function Calls**: Tests import and call server functions directly (no MCP protocol)
- **Sample Data**: Uses Step Functions JSON files from `samples/step_function_jobs/` and Airflow Python files from `samples/airflow_jobs/`
- **Working Directory**: Must run from project root directory

## Test Files

- `test_all_conversions.py` - Bidirectional conversion tests (Step Functions ↔ Airflow)

## Test Outputs

- `output/test_all_conversions_YYYYMMDD_HHMMSS/` - Timestamped test results
  - `flex_docs/` - Generated FLEX JSON documents (both conversion directions)
  - `airflow_dags/` - Generated Airflow DAG Python files (from Step Functions)
  - `step_functions/` - Generated Step Functions JSON files (from Airflow)

## Running Integration Tests

```bash
# Ensure virtual environment is activated first
# Using uv: automatically handled
# Using pip: source venv/bin/activate

# Run bidirectional conversion tests directly (recommended)
python tests/integration/test_all_conversions.py

# Or via pytest
python -m pytest tests/integration/ -v
```

## Cleanup

Test output directories are timestamped and can be safely deleted after review.