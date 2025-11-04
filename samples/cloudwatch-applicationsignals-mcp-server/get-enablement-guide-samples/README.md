# Get Enablement Guide Samples

Sample infrastructure for testing the `get_enablement_guide` tool.

## Testing Requirements

**Important:** All changes to this infrastructure should be tested to ensure the IaC and sample apps work correctly.

## Deployment

### Prerequisites

- AWS CLI configured with appropriate credentials
- Node.js and npm installed
- AWS CDK CLI installed (`npm install -g aws-cdk`)

### Deploy EC2 CDK Sample

```bash
cd infrastructure/ec2/cdk

# Install dependencies
npm install

# Deploy the Python Flask stack
cdk deploy PythonFlaskStack

# Clean up
cdk destroy PythonFlaskStack
```

This deploys an EC2 instance running a containerized Python Flask sample application pulled from an ECR Image Repo.
