# Evaluation for ECS Task Exit Code Failure Scenario

## Problem Identification (25 points)
- [ ] Correctly identified the task exited with error code 1 (5 points)
- [ ] Used appropriate troubleshooting tool(s), particularly the fetch_task_failures and fetch_task_logs tools (5 points)
- [ ] Found the specific error messages in the logs about the missing DATABASE_URL environment variable (5 points)
- [ ] Identified the container that failed and understood the task configuration (5 points)
- [ ] Checked the task definition for environment variable configuration (5 points)

## Root Cause Analysis (25 points)
- [ ] Correctly identified the primary issue: missing required environment variable (10 points)
- [ ] Explained the relationship between environment variables and container execution (5 points)
- [ ] Identified that this is an application-specific requirement rather than an AWS infrastructure issue (5 points)
- [ ] Explained the process of how ECS handles task failures and exit codes (5 points)

## Solution Quality (25 points)
- [ ] Provided clear instructions to add the required DATABASE_URL environment variable (10 points)
- [ ] Gave correct syntax for updating the task definition with environment variables (5 points)
- [ ] Explained how to run the updated task with proper environment configuration (5 points)
- [ ] Solution would actually fix the problem (5 points)

## Educational Value (25 points)
- [ ] Explained ECS task execution and exit code concepts clearly (5 points)
- [ ] Explained how to debug task failures using CloudWatch logs (5 points)
- [ ] Provided context about environment variables in containerized applications (5 points)
- [ ] Tailored explanation to user's apparent knowledge level (5 points)
- [ ] Included helpful resources or documentation links (5 points)

## Total Score: ____ / 100

### Comments:
(Add specific observations about what went well or could be improved in Cline's troubleshooting approach)

### Key Points to Look For in Cline's Response:
1. **Log Analysis Skills** - Does Cline properly review the CloudWatch logs to identify the specific error about DATABASE_URL?
2. **Container Environment Understanding** - Does Cline demonstrate understanding of how environment variables work in ECS tasks?
3. **Correct Solution** - Does Cline provide the correct solution of adding the DATABASE_URL environment variable to the task definition?
4. **Knowledge Adaptation** - How well does Cline adjust the explanation based on the user's apparent level of knowledge?
5. **Follow-up Considerations** - Does Cline mention additional best practices like using AWS Secrets Manager or Parameter Store for sensitive environment variables?

### Expected Solution Elements:
```json
"containerDefinitions": [
  {
    "name": "exit-code-container",
    "image": "amazonlinux:2",
    "essential": true,
    "environment": [
      {
        "name": "DATABASE_URL",
        "value": "postgresql://username:password@hostname:port/database"
      }
    ]
    /* Other container configuration would go here */
  }
]
```
