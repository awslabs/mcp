# Evaluation Criteria for ECS Security Analysis Scenario

## Security Tool Usage (25 points)
- [ ] Correctly used list_clusters tool when appropriate (5 points)
- [ ] Used analyze_cluster_security tool effectively (5 points)
- [ ] Used generate_security_report tool when requested (5 points)
- [ ] Used get_security_recommendations tool appropriately (5 points)
- [ ] Used check_compliance_status tool for compliance queries (5 points)

## Security Issue Identification (25 points)
- [ ] Identified privileged container configuration (5 points)
- [ ] Found root user container execution (5 points)
- [ ] Detected hardcoded secrets in environment variables (5 points)
- [ ] Identified missing execute command logging (5 points)
- [ ] Found other network or configuration security issues (5 points)

## Risk Assessment and Prioritization (25 points)
- [ ] Correctly assessed severity levels (Critical, High, Medium, Low) (10 points)
- [ ] Prioritized issues based on actual security impact (5 points)
- [ ] Explained why each issue is a security concern (5 points)
- [ ] Provided context about potential attack vectors (5 points)

## Solution Quality and Remediation (25 points)
- [ ] Provided specific, actionable remediation steps (10 points)
- [ ] Gave correct configuration examples (5 points)
- [ ] Addressed all identified security issues (5 points)
- [ ] Solutions would actually resolve the security problems (5 points)

## Total Score: ____ / 100

### Comments:
(Add specific observations about the quality of security analysis, tool usage, and remediation guidance)

### Expected Security Findings:

#### Critical Issues:
1. **Privileged Container**
   - Finding: Container running with privileged=true
   - Risk: Full host access, container escape potential
   - Remediation: Remove privileged flag, use specific capabilities if needed

2. **Hardcoded Secrets**
   - Finding: API_KEY environment variable with hardcoded value
   - Risk: Secret exposure, credential compromise
   - Remediation: Use AWS Secrets Manager or Parameter Store

#### High Issues:
3. **Root User Execution**
   - Finding: Container running as root user
   - Risk: Privilege escalation, broader attack surface
   - Remediation: Create non-root user in container image

4. **Missing Execute Command Logging**
   - Finding: Execute command logging disabled
   - Risk: Lack of audit trail for container access
   - Remediation: Enable CloudWatch logging for execute commands

### Sample Remediation Examples:

```json
// Fix for privileged container
{
  "name": "test-container",
  "image": "nginx:latest",
  "privileged": false,  // Changed from true
  "user": "1001:1001",  // Added non-root user
  // ... other configuration
}
```

```yaml
# Fix for execute command logging
ECSCluster:
  Type: AWS::ECS::Cluster
  Properties:
    Configuration:
      ExecuteCommandConfiguration:
        Logging: DEFAULT  # Changed from NONE
```

### Key Evaluation Points:

1. **Conversational Quality**
   - Does the assistant explain security concepts clearly?
   - Are responses tailored to user's apparent expertise level?
   - Does the assistant ask clarifying questions when needed?

2. **Technical Accuracy**
   - Are security findings technically correct?
   - Are remediation steps accurate and complete?
   - Does the assistant understand ECS security model?

3. **Practical Value**
   - Are recommendations actionable?
   - Does the assistant prioritize issues appropriately?
   - Are compliance mappings accurate?

4. **Multi-Turn Conversation Handling**
   - Does the assistant maintain context across turns?
   - Can it handle follow-up questions effectively?
   - Does it provide appropriate level of detail based on user requests?

### Compliance Framework Expectations:

#### AWS Security Best Practices:
- [ ] Identifies non-compliance with least privilege principle
- [ ] Flags missing encryption configurations
- [ ] Checks for proper network segmentation

#### PCI-DSS (if requested):
- [ ] Identifies issues related to access controls
- [ ] Flags potential data exposure risks
- [ ] Recommends encryption and logging improvements

### Red Flags (Deduct Points):
- [ ] Incorrect security assessment (-5 points)
- [ ] Missing critical security issues (-10 points)
- [ ] Providing insecure remediation advice (-10 points)
- [ ] Failing to use appropriate security tools (-5 points)
- [ ] Not explaining security risks clearly (-5 points)
