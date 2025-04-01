# Agent Collaboration

## Overview

Agent Collaboration enables multiple Bedrock Agents to work together on complex tasks. This feature allows agents to specialize in different areas and collaborate to provide more comprehensive responses to user queries.

## Collaboration Types

You can configure collaboration for an agent using the `agentCollaboration` and `agentCollaborators` properties in the `AgentProps` interface.

- **SUPERVISOR**: The agent acts as a supervisor that can delegate tasks to other agents.
- **SUPERVISOR_ROUTER**: The agent acts as a supervisor that can route requests to specialized agents.
- **DISABLED**: Collaboration is disabled (default).

## Example

### TypeScript

```typescript
import { Agent, AgentCollaboratorType, RelayConversationHistoryType } from '@cdklabs/generative-ai-cdk-constructs';

// Create a specialized agent for customer support
const customerSupportAgent = new Agent(this, 'CustomerSupportAgent', {
  name: 'CustomerSupportAgent',
  instruction: 'You specialize in answering customer support questions about our products.',
  foundationModel: bedrock.BedrockFoundationModel.AMAZON_NOVA_LITE_V1,
});

// Create an agent alias for the specialized agent
const customerSupportAlias = new AgentAlias(this, 'CustomerSupportAlias', {
  agent: customerSupportAgent,
  aliasName: 'production',
});

// Create a main agent that can collaborate with the specialized agent
const mainAgent = new Agent(this, 'MainAgent', {
  name: 'MainAgent',
  instruction: 'You are a helpful assistant that can answer general questions and route specialized customer support questions to the customer support agent.',
  foundationModel: bedrock.BedrockFoundationModel.AMAZON_NOVA_LITE_V1,
  agentCollaboration: AgentCollaboratorType.SUPERVISOR,
  agentCollaborators: [
    new bedrock.AgentCollaborator({
      agentAlias: customerSupportAlias,
      collaborationInstruction: 'Route customer support questions to this agent.',
      collaboratorName: 'CustomerSupport',
      relayConversationHistory: true,
    }),
  ],
});
```

### Python

```python
from cdklabs.generative_ai_cdk_constructs import (
    bedrock,
    AgentCollaboratorType,
    RelayConversationHistoryType
)

# Create a specialized agent for customer support
customer_support_agent = bedrock.Agent(self, 'CustomerSupportAgent',
    name='CustomerSupportAgent',
    instruction='You specialize in answering customer support questions about our products.',
    foundation_model=bedrock.BedrockFoundationModel.AMAZON_NOVA_LITE_V1,
)

# Create an agent alias for the specialized agent
customer_support_alias = bedrock.AgentAlias(self, 'CustomerSupportAlias',
    agent=customer_support_agent,
    alias_name='production',
)

# Create a main agent that can collaborate with the specialized agent
main_agent = bedrock.Agent(self, 'MainAgent',
    name='MainAgent',
    instruction='You are a helpful assistant that can answer general questions and route specialized customer support questions to the customer support agent.',
    foundation_model=bedrock.BedrockFoundationModel.AMAZON_NOVA_LITE_V1,
    agent_collaboration=AgentCollaboratorType.SUPERVISOR,
    agent_collaborators=[
      bedrock.AgentCollaborator(
        agent_alias= customer_support_alias,
        collaboration_instruction= 'Route customer support questions to this agent.',
        collaborator_name= 'CustomerSupport',
        relay_conversation_history= true,
      )
    ],
)
```

For more information on agent collaboration, refer to the [AWS Bedrock documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-collaboration.html).
