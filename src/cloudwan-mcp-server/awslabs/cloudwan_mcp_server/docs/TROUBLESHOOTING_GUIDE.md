# Infrastructure-as-Code Parsing Troubleshooting Guide

## Common Issues and Solutions

### 1. Format Detection Failures

**Problem**: "Unable to auto-detect IaC format from content"

**Common Causes**:
- Missing or malformed resource declarations
- Mixing multiple IaC formats in single file
- Non-standard file formatting

**Solutions**:
```python
# Solution 1: Provide explicit format hint
result = await analyze_iac_firewall_policy(
    content=file_content,
    format_hint="terraform"  # Explicitly specify format
)

# Solution 2: Ensure proper resource declarations
# Terraform: Must have resource "aws_networkfirewall_*" blocks
# CDK: Must have CfnFirewallPolicy or CfnRuleGroup imports
# CloudFormation: Must have Type: AWS::NetworkFirewall::* resources
```

### 2. Parsing Errors

**Problem**: "Invalid syntax detected"

**Common Causes**:
- Syntax errors in IaC code
- Unsupported language features
- Incomplete resource definitions

**Debugging Steps**:
1. Validate IaC syntax with native tools first:
   ```bash
   # Terraform
   terraform validate
   
   # CDK
   npx tsc --noEmit
   
   # CloudFormation
   cfn-lint template.yaml
   ```

2. Check for required fields:
   ```yaml
   # CloudFormation example - all required fields
   MyFirewallPolicy:
     Type: AWS::NetworkFirewall::FirewallPolicy
     Properties:
       FirewallPolicyName: my-policy  # Required
       FirewallPolicy:                 # Required
         StatelessDefaultActions:      # Required
           - "aws:forward_to_sfe"
   ```

### 3. Memory Issues with Large Policies

**Problem**: "Memory threshold exceeded during simulation"

**Solution**:
```python
# Process in smaller chunks
chunk_size = 100  # Reduce from default 500
for i in range(0, len(rules), chunk_size):
    chunk = rules[i:i + chunk_size]
    process_chunk(chunk)
```

### 4. Suricata Rule Parsing Failures

**Problem**: "Failed to parse Suricata rule"

**Common Issues**:
- Multi-line rules not properly formatted
- Special characters not escaped
- Invalid rule syntax

**Examples**:
```terraform
# BAD - Multi-line without proper escaping
rules_string = "
alert tcp any any -> any any (msg:\"test\";
content:\"bad\"; sid:1;)
"

# GOOD - Proper formatting
rules_string = <<-EOT
alert tcp any any -> any any (msg:"test"; content:"bad"; sid:1;)
EOT
```

### 5. Performance Issues

**Problem**: Slow analysis for large policies

**Optimization Strategies**:
1. **Enable caching**:
   ```python
   # Results are automatically cached
   # Repeated analysis of same content is instant
   ```

2. **Selective analysis**:
   ```python
   # Skip traffic simulation for faster results
   result = await analyze_iac_firewall_policy(
       content=content,
       include_traffic_simulation=False
   )
   ```

3. **Use format hints**:
   ```python
   # Skip auto-detection overhead
   result = await analyze_iac_firewall_policy(
       content=content,
       format_hint="cloudformation"
   )
   ```

## Error Code Reference

| Error Code | Description | Common Fix |
|------------|-------------|------------|
| `INVALID_SYNTAX` | IaC syntax validation failed | Check native tool validation |
| `ANALYSIS_FAILED` | General analysis failure | Check logs for details |
| `PARSER_NOT_FOUND` | Unknown IaC format | Provide format_hint |
| `MEMORY_EXCEEDED` | Resource limits hit | Reduce policy size |
| `AWS_COMPARISON_FAILED` | Can't compare with AWS | Check firewall ARN |

## Debug Mode

Enable detailed logging:
```python
import logging
logging.getLogger('awslabs.cloudwan_mcp_server').setLevel(logging.DEBUG)
```

## Getting Help

1. Check the comprehensive examples in `/examples` directory
2. Review test cases in `/tests` for working examples
3. Enable debug logging for detailed error traces
4. Ensure you're using supported IaC versions:
   - Terraform: 0.12+
   - CDK: 2.0+
   - CloudFormation: Latest schema

## Reporting Issues

When reporting parsing issues, please include:
1. IaC format and version
2. Minimal reproducible example
3. Full error message with stack trace
4. Expected vs actual behavior