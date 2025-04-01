# Agent Alias

## Overview

After you have sufficiently iterated on your working draft and are satisfied with the behavior of your agent, you can set it up for deployment and integration into your application by creating aliases of your agent.

To deploy your agent, you need to create an alias. During alias creation, Amazon Bedrock automatically creates a version of your agent. The alias points to this newly created version. You can point the alias to a previously created version if necessary. You then configure your application to make API calls to that alias.

By default, the `Agent` resource does not create any aliases, and you can use the 'DRAFT' version.

## Specific Version

You can use the `AgentAlias` resource if you want to create an Alias for an existing Agent.

## Example

### TypeScript

```ts
const agentAlias2 = new bedrock.AgentAlias(this, 'myalias2', {
  aliasName: 'myalias',
  agent: agent,
  agentVersion: '1', // optional
  description: 'mytest'
});
```

### Python

```python
agent_alias_2 = bedrock.AgentAlias(self, 'myalias2',
    alias_name='myalias',
    agent=agent,
    agent_version='1', # optional
    description='mytest'
)
```

[View full documentation](https://github.com/awslabs/generative-ai-cdk-constructs/blob/main/src/cdk-lib/bedrock/README.md)
