# Bedrock Agent Integration

Use Lambda Powertools with Bedrock Agent actions:

```python
from typing import Dict, List, Optional
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import BedrockAgentResolver
from aws_lambda_powertools.event_handler.openapi.params import Body, Path, Query
from pydantic import BaseModel, Field

# Initialize Powertools
logger = Logger(service="agent-actions")
app = BedrockAgentResolver()

# Define request/response models with type hints
class Product(BaseModel):
    product_id: str = Field(description="Unique product identifier")
    name: str = Field(description="Product name")
    price: float = Field(description="Product price in USD")

@app.get("/products", description="List all products")
def list_products(
    category: Optional[str] = Query(None, description="Filter by category")
) -> List[Product]:
    """Get a list of products, optionally filtered by category"""
    logger.info("Listing products", extra={"category": category})

    # Your business logic here
    products = get_products_from_database(category)

    return products

@logger.inject_lambda_context
def lambda_handler(event, context):
    """Main Lambda handler for Bedrock Agent actions"""
    return app.resolve(event, context)
```

## Key Benefits

- **Type Safety**: Pydantic models ensure type safety and validation
- **OpenAPI Schema Generation**: Automatically generates OpenAPI schemas for Bedrock Agents
- **Structured Logging**: Integrates with Lambda Powertools logging
- **Parameter Validation**: Automatically validates request parameters
- **Documentation**: Generates documentation for your API

## Generating OpenAPI Schema

To generate a Bedrock-compatible OpenAPI schema:

```python
# Generate schema from a file
result = await use_mcp_tool(
    server_name="awslabs.mcp-cdk-expert",
    tool_name="GenerateBedrockAgentSchemaFromFile",
    arguments={
        "lambda_code_path": "/path/to/your/agent_actions.py",
        "output_path": "/path/to/output/schema.json"
    }
)
```

## Common Schema Issues

- **OpenAPI version**: Must be exactly 3.0.0
- **operationId**: Each operation needs a unique operationId
- **Response schemas**: All responses must have properly defined schemas
- **Parameter descriptions**: All parameters should have descriptions

## Best Practices

1. **Use Pydantic models**: Define request and response models with Pydantic
2. **Add descriptions**: Add descriptions to all fields and parameters
3. **Use type hints**: Specify return types for all route handlers
4. **Handle errors gracefully**: Return appropriate error responses
5. **Log with context**: Use structured logging with business context
6. **Validate inputs**: Use the validation features to ensure valid inputs

## CDK Integration

```typescript
import { bedrock } from '@cdklabs/generative-ai-cdk-constructs';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Runtime, Tracing } from 'aws-cdk-lib/aws-lambda';
import * as path from 'path';

// Create Lambda function for Bedrock Agent actions
const actionFunction = new PythonFunction(this, 'AgentActionFunction', {
  entry: path.join(__dirname, '../src/agent_actions'),
  runtime: Runtime.PYTHON_3_13,
  tracing: Tracing.ACTIVE,
  environment: {
    POWERTOOLS_SERVICE_NAME: "agent-actions",
    LOG_LEVEL: "INFO",
  },
});

// Create a Bedrock Agent
const agent = new bedrock.Agent(this, 'Agent', {
  name: 'PowertoolsAgent',
  foundationModel: bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_HAIKU_V1_0,
  shouldPrepareAgent: true,
  userInputEnabled: true,
  instruction: 'You are a helpful assistant that can perform product-related actions.',
  description: 'Agent for product management',
});

// Add action group to the agent
agent.addActionGroup(
  new bedrock.AgentActionGroup({
    name: 'product-actions',
    description: 'Actions for managing products',
    executor: bedrock.ActionGroupExecutor.fromlambdaFunction(actionFunction),
    apiSchema: bedrock.ApiSchema.fromAsset(
      path.join(__dirname, '../schema/product_actions.json')
    ),
  })
);

// Create agent alias for deployment
const agentAlias = new bedrock.AgentAlias(this, 'AgentAlias', {
  aliasName: 'latest',
  agent: agent,
  description: 'Latest agent alias',
});
```
