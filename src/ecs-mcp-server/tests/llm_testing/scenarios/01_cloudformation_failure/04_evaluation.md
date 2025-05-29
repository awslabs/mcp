# Evaluation Criteria for CloudFormation Stack Failure Scenario

## Problem Identification (25 points)
- [ ] Correctly identified CloudFormation stack failure (5 points)
- [ ] Used appropriate tool (fetch_cloudformation_status) (5 points)
- [ ] Correctly identified the resource that failed (ECSService) (5 points)
- [ ] Found all relevant error messages (5 points)
- [ ] Didn't make incorrect assumptions about the stack (5 points)

## Root Cause Analysis (25 points)
- [ ] Correctly identified missing NetworkConfiguration as primary issue (10 points)
- [ ] Explained why NetworkConfiguration is required for Fargate tasks (5 points)
- [ ] Identified any secondary issues (invalid container image) (5 points)
- [ ] Explained relationship between the issues (5 points)

## Solution Quality (25 points)
- [ ] Provided clear solution for missing NetworkConfiguration (10 points)
- [ ] Gave correct CloudFormation syntax (5 points)
- [ ] Addressed all identified issues (5 points)
- [ ] Solution would actually fix the problem (5 points)

## Educational Value (25 points)
- [ ] Explained ECS concepts clearly (5 points)
- [ ] Explained Fargate networking requirements (5 points)
- [ ] Provided context about CloudFormation deployments (5 points)
- [ ] Tailored explanation to user's apparent knowledge level (5 points)
- [ ] Included helpful resources or documentation links (5 points)

## Total Score: ____ / 100

### Comments:
(Add specific observations about what went well or could be improved in Cline's troubleshooting approach)

### Sample Solution
```yaml
# Example fix for the NetworkConfiguration issue:
ECSService:
  Type: AWS::ECS::Service
  Properties:
    ServiceName: test-failure-stack-service
    Cluster: !Ref ECSCluster
    TaskDefinition: !Ref TaskDefinition
    DesiredCount: 1
    LaunchType: FARGATE
    NetworkConfiguration:
      AwsvpcConfiguration:
        AssignPublicIp: ENABLED
        Subnets:
          - subnet-12345678  # Replace with actual subnet IDs
        SecurityGroups:
          - sg-12345678      # Replace with actual security group ID
```

### Key Points to Look For in Cline's Response:
1. **Methodical troubleshooting** - Does Cline systematically investigate the issue?
2. **Correct tool usage** - Does Cline select the right tools for the job?
3. **Accurate diagnostics** - Does Cline correctly identify both issues?
4. **Complete solution** - Does Cline address all problems in the solution?
5. **Educational approach** - Does Cline explain concepts at an appropriate level for the user?
