# AWS Security Pillar MCP Server Prompt Template

This template provides a user-friendly way to interact with the AWS Security Pillar MCP Server. Simply copy and paste the sections below, replacing the placeholder values with your AWS region and profile information.

## Basic Security Assessment

```
I'd like to assess the security posture of my AWS environment using the AWS Security Pillar MCP Server.

Region: us-east-1  # Replace with your target AWS region
AWS Profile: default  # Replace with your AWS profile name

Please perform the following steps:
1. Check if all recommended security services are properly configured
2. Explore the resources in my environment
3. Analyze my security posture against the AWS Well-Architected Framework
4. Provide a summary of findings and remediation steps
```

## Check Security Services Status

```
Check if the following security services are properly enabled and configured in my AWS environment:

Region: us-east-1  # Replace with your target AWS region
AWS Profile: default  # Replace with your AWS profile name

1. IAM Access Analyzer
2. AWS Security Hub
3. Amazon GuardDuty
4. Amazon Inspector
```

## Explore AWS Resources

```
I'd like to explore what AWS resources I have deployed in my environment:

Region: us-east-1  # Replace with your target AWS region
AWS Profile: default  # Replace with your AWS profile name
Services to explore: ec2,s3,rds,lambda  # Modify as needed

Please provide a resource inventory with counts by service type.
```

## Get Security Findings

```
I'd like to retrieve security findings from my AWS environment:

Region: us-east-1  # Replace with your target AWS region
AWS Profile: default  # Replace with your AWS profile name
Security Service: securityhub  # Options: guardduty, securityhub, inspector, accessanalyzer
Severity: HIGH  # Optional: Filter by severity (HIGH, CRITICAL, etc.)

Please provide a summary of the findings.
```

## Advanced Security Assessment with Debug Output

```
I'd like to perform a detailed security assessment with debug information:

Regions: ["us-east-1", "us-west-2"]  # Replace with your target AWS regions
AWS Profile: default  # Replace with your AWS profile name
Services: ["ec2", "s3", "rds", "iam", "lambda"]  # Optional: Specify services to focus on
Debug: true  # Enable detailed debug output

Please provide a detailed report with timing information for each phase.
```

## Resource Compliance Check

```
I'd like to check the compliance status of a specific AWS resource:

Region: us-east-1  # Replace with your target AWS region
AWS Profile: default  # Replace with your AWS profile name
Resource ID: i-1234567890abcdef0  # Replace with your resource ID
Resource Type: ec2-instance  # Replace with the resource type (e.g., ec2-instance, s3-bucket)

Please provide the compliance details.
```

---

## Example Workflow

Here's a recommended workflow for a comprehensive security assessment:

1. **First, check your security services**:
   ```
   Check if the following security services are properly enabled and configured in my AWS environment:

   Region: us-east-1
   AWS Profile: default

   1. IAM Access Analyzer
   2. AWS Security Hub
   3. Amazon GuardDuty
   4. Amazon Inspector
   ```

2. **Next, explore your resources**:
   ```
   I'd like to explore what AWS resources I have deployed in my environment:

   Region: us-east-1
   AWS Profile: default
   Services to explore: ec2,s3,rds,iam,lambda

   Please provide a resource inventory with counts by service type.
   ```

3. **Then, perform a comprehensive security assessment**:
   ```
   I'd like to assess the security posture of my AWS environment:

   Region: us-east-1
   AWS Profile: default

   Please perform a comprehensive security assessment and provide remediation recommendations.
   ```

4. **Finally, review specific findings for critical services**:
   ```
   I'd like to retrieve critical findings from my AWS environment:

   Region: us-east-1
   AWS Profile: default
   Security Service: guardduty
   Severity: HIGH

   Please summarize the findings and their potential impact.
