# ROSA E-book Analysis Scripts

These scripts use AWS Bedrock to analyze the ROSA e-book PDF and extract insights to enhance the ROSA MCP Server implementation.

## Prerequisites

1. **AWS Credentials**: Configure AWS credentials with access to Amazon Bedrock
2. **Bedrock Access**: Ensure you have access to Claude 3 Sonnet model in your AWS account
3. **Python Dependencies**:
   ```bash
   pip install boto3 click
   ```
4. **ROSA E-book**: Have the ROSA e-book PDF file available (default: `~/rosa-ebook.pdf`)

## Scripts

### 1. analyze_rosa_ebook.py

This script analyzes the ROSA e-book using AWS Bedrock to extract:
- CLI commands and patterns
- Networking best practices
- Authentication configurations
- Operational patterns
- Cost optimization strategies
- AWS service integrations

**Usage:**
```bash
python analyze_rosa_ebook.py --pdf-path ~/rosa-ebook.pdf --output-dir ./rosa_analysis --region us-east-1
```

**Options:**
- `--pdf-path`: Path to the ROSA e-book PDF (default: ~/rosa-ebook.pdf)
- `--output-dir`: Directory to save analysis results (default: ./rosa_analysis)
- `--region`: AWS region for Bedrock (default: us-east-1)

**Output Files:**
- `rosa_patterns.json`: All extracted patterns
- `rosa_cli_patterns.json`: CLI commands and workflows
- `rosa_networking.json`: Networking configurations
- `rosa_authentication.json`: Auth and security patterns
- `rosa_operations.json`: Operational best practices
- `rosa_cost_optimization.json`: Cost saving strategies
- `rosa_integrations.json`: AWS service integrations
- `rosa_mcp_enhancements.py`: Generated code improvements

### 2. apply_rosa_insights.py

This script processes the extracted insights and generates enhancement files for the MCP server:
- Enhanced constants based on e-book recommendations
- Validation helpers implementing best practices
- Workflow helpers for common operations

**Usage:**
```bash
python apply_rosa_insights.py --insights-dir ./rosa_analysis --output-dir ./rosa_enhancements
```

**Options:**
- `--insights-dir`: Directory containing insights from analyze_rosa_ebook.py (default: ./rosa_analysis)
- `--mcp-server-path`: Path to ROSA MCP server directory (default: current directory)
- `--output-dir`: Directory to save enhancement files (default: ./rosa_enhancements)

**Output Files:**
- `enhanced_consts.py`: Constants and configurations from e-book
- `validation_helpers.py`: Validation functions based on best practices
- `workflow_helpers.py`: Common workflow implementations

## Complete Workflow

1. **Analyze the ROSA e-book:**
   ```bash
   python analyze_rosa_ebook.py --pdf-path ~/rosa-ebook.pdf
   ```

2. **Generate MCP enhancements:**
   ```bash
   python apply_rosa_insights.py --insights-dir ./rosa_analysis
   ```

3. **Integrate enhancements into MCP server:**
   - Review generated files in `./rosa_enhancements/`
   - Copy relevant functions and constants to appropriate MCP server modules
   - Update existing handlers with new validation and workflow helpers

## Example Integration

After running the scripts, you can integrate the enhancements:

```python
# In rosa_cluster_handler.py
from awslabs.rosa_mcp_server.validation_helpers import (
    validate_cluster_configuration,
    recommend_instance_type,
    calculate_cluster_cost_estimate
)

# Use in create_rosa_cluster function
async def create_rosa_cluster(ctx, cluster_name, region, ...):
    # Validate configuration
    is_valid, error = validate_cluster_configuration(
        cluster_name, version, multi_az, replicas, machine_type
    )
    if not is_valid:
        return CallToolResult(success=False, content=error)
    
    # Show cost estimate
    cost_estimate = calculate_cluster_cost_estimate(
        region, machine_type, replicas, multi_az
    )
    log_with_request_id(ctx, LogLevel.INFO, 
        f"Estimated monthly cost: ${cost_estimate['total_monthly']:.2f}")
    
    # Continue with cluster creation...
```

## Notes

- The analysis uses AWS Bedrock's Claude 3 Sonnet model for PDF analysis
- Large PDFs may take several minutes to process
- Ensure your AWS account has sufficient Bedrock quota
- Generated code should be reviewed and tested before integration
- The scripts extract patterns and best practices, not verbatim content

## Cost Considerations

- Each PDF analysis makes multiple Bedrock API calls
- Costs depend on the size of the PDF and number of prompts
- Estimate: ~$0.50-$2.00 per complete analysis (varies by PDF size)

## Troubleshooting

1. **Bedrock Access Denied**: Ensure your AWS credentials have Bedrock permissions
2. **Model Not Available**: Check if Claude 3 Sonnet is available in your region
3. **PDF Too Large**: Consider splitting the PDF or increasing timeout values
4. **JSON Parse Errors**: The model output may need manual formatting for complex patterns