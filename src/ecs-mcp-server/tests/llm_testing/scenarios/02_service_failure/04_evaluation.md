# Evaluation Criteria for ECS Service Image Pull Failure Scenario

## Problem Identification (25 points)
- [ ] Correctly identified ECS service failure (5 points)
- [ ] Used appropriate tool (fetch_service_events or fetch_task_failures) (5 points)
- [ ] Found the image pull failure (5 points)
- [ ] Identified that the image doesn't exist (5 points)
- [ ] Checked service configuration thoroughly (5 points)

## Root Cause Analysis (25 points)
- [ ] Correctly identified non-existent image as primary issue (10 points)
- [ ] Explained container image registry concepts (5 points)
- [ ] Explained how ECS tries to pull images (5 points)
- [ ] Discussed how image pull errors manifest in ECS (5 points)

## Solution Quality (25 points)
- [ ] Provided clear solution for fixing the image reference (10 points)
- [ ] Suggested valid alternative images to use (5 points)
- [ ] Explained how to update task definition (5 points)
- [ ] Explained how the update affects the service (5 points)

## Educational Value (25 points)
- [ ] Explained container image concepts clearly (5 points)
- [ ] Explained ECS task/service relationship (5 points)
- [ ] Provided context about container registries (5 points)
- [ ] Tailored explanation to user's apparent knowledge level (5 points)
- [ ] Included helpful resources or documentation links (5 points)

## Total Score: ____ / 100

### Comments:
(Add specific observations about what went well or could be improved in Cline's troubleshooting approach)

### Sample Solution
```bash
# Step 1: Update the task definition with a valid image
aws ecs register-task-definition \
  --family failing-task-def \
  --requires-compatibilities FARGATE \
  --network-mode awsvpc \
  --cpu 256 \
  --memory 512 \
  --execution-role-arn <ecsTaskExecutionRoleArn> \
  --container-definitions '[
    {
      "name": "failing-container",
      "image": "amazon/amazon-ecs-sample",
      "essential": true,
      "portMappings": [{"containerPort": 80, "hostPort": 80}]
    }
  ]'

# Step 2: Update the service to use the new task definition revision
aws ecs update-service \
  --cluster test-failure-cluster \
  --service failing-service \
  --task-definition failing-task-def
```

### Key Points to Look For in Cline's Response:
1. **Complete diagnostic approach** - Does Cline check both service events and task failures?
2. **Image understanding** - Does Cline explain the concept of container images and registries?
3. **Registry context** - Does Cline explain that "non-existent-repo" doesn't exist and suggest valid alternatives?
4. **Solution steps** - Does Cline clearly outline how to create a new task definition revision and update the service?
5. **Knowledge adaptation** - Does Cline adjust the technical detail based on the user's apparent familiarity with ECS?
