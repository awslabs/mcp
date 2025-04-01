# Custom Orchestration

## Overview

Custom Orchestration allows you to override the default agent orchestration flow with your own Lambda function. This enables more control over how the agent processes user inputs, handles knowledge base queries, and invokes action groups.

## Orchestration Types

You can configure the orchestration type using the `orchestrationType` and `customOrchestration` properties in the `AgentProps` interface.

- **DEFAULT**: The default orchestration provided by Bedrock (default).
- **CUSTOM_ORCHESTRATION**: Custom orchestration using a Lambda function.

## Example

### TypeScript

```typescript
import { Agent, OrchestrationType, OrchestrationExecutor } from '@cdklabs/generative-ai-cdk-constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as path from 'path';

// Create a Lambda function for custom orchestration
const orchestrationFunction = new lambda.Function(this, 'OrchestrationFunction', {
  runtime: lambda.Runtime.PYTHON_3_10,
  handler: 'index.handler',
  code: lambda.Code.fromAsset(path.join(__dirname, 'lambda/orchestration')),
});

// Create an agent with custom orchestration
const agent = new Agent(this, 'CustomOrchestrationAgent', {
  name: 'CustomOrchestrationAgent',
  instruction: 'You are a helpful assistant with custom orchestration logic.',
  foundationModel: bedrock.BedrockFoundationModel.AMAZON_NOVA_LITE_V1,
  orchestrationType: OrchestrationType.CUSTOM_ORCHESTRATION,
  customOrchestration: {
    executor: OrchestrationExecutor.fromlambdaFunction(orchestrationFunction),
  },
});
```

### Python

```python
from cdklabs.generative_ai_cdk_constructs import (
    bedrock,
    OrchestrationType,
    OrchestrationExecutor
)
import aws_cdk.aws_lambda as lambda_
import os

# Create a Lambda function for custom orchestration
orchestration_function = lambda_.Function(self, 'OrchestrationFunction',
    runtime=lambda_.Runtime.PYTHON_3_10,
    handler='index.handler',
    code=lambda_.Code.from_asset(os.path.join(os.path.dirname(__file__), 'lambda/orchestration')),
)

# Create an agent with custom orchestration
agent = bedrock.Agent(self, 'CustomOrchestrationAgent',
    name='CustomOrchestrationAgent',
    instruction='You are a helpful assistant with custom orchestration logic.',
    foundation_model=bedrock.BedrockFoundationModel.AMAZON_NOVA_LITE_V1,
    orchestration_type=OrchestrationType.CUSTOM_ORCHESTRATION,
    custom_orchestration=bedrock.CustomOrchestration(
      executor= OrchestrationExecutor.fromlambda_function(orchestration_function),
    )
)
```

The custom orchestration Lambda function receives events from Bedrock with the user's input and context, and it can control the flow of the conversation by deciding when to query knowledge bases, invoke action groups, or respond directly to the user.

For more information on custom orchestration, refer to the [AWS Bedrock documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-custom-orchestration.html).
