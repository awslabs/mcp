# Billing and Cost Management MCP Prompts

This directory contains prompts for the AWS Billing and Cost Management MCP Server. Prompts are structured conversations that guide LLMs through specific analysis tasks using the available tools.

## What are Prompts?

Prompts are reusable message templates that help LLMs generate structured, purposeful responses. In the context of the Billing and Cost Management MCP Server, prompts guide LLMs through complex cost optimization analyses using the available AWS tools.

## Creating a New Prompt

To create a new prompt:

1. Create a new Python file in this directory (e.g., `my_analysis.py`)
2. Import the necessary modules:
   ```python
   from typing import List
   from fastmcp.prompts.prompt import Message
   from .decorator import finops_prompt
   ```
3. Define your prompt function using the `@finops_prompt` decorator:
   ```python
   @finops_prompt(
       name="my_analysis_prompt",
       description="Description of what this prompt does",
       tags={"relevant", "tags"}
   )
   def my_analysis_function(param1: str, param2: int = 10) -> List[Message]:
       """Detailed docstring describing the prompt."""
       messages = [
           Message("User message guiding the LLM..."),
           Message("Initial assistant response...", role="assistant")
       ]
       return messages
   ```

## Prompt Structure

Each prompt should follow this structure:

1. **User Message**: A detailed message that:
   - Explains the task
   - Provides context and parameters
   - Outlines steps to follow
   - Specifies the expected output format

2. **Assistant Message**: An initial response from the assistant that:
   - Acknowledges the task
   - Sets expectations for what will be delivered

## Best Practices

1. **Be Specific**: Clearly outline the steps the LLM should follow
2. **Reference Tools**: Explicitly mention which tools to use
3. **Structure Output**: Specify how results should be presented
4. **Handle Edge Cases**: Provide guidance for potential issues
5. **Use Parameters**: Make prompts flexible with parameters

## Available Prompts

### Graviton Migration Analysis

Analyzes EC2 instances and identifies opportunities to migrate to AWS Graviton processors.

```python
analyze_graviton_opportunities(
    account_ids: List[str],
    lookback_days: int = 14,
    region: str = None
)
```

### Savings Plans Analysis

Analyzes AWS usage and identifies opportunities for Savings Plans purchases.

```python
analyze_savings_plans_opportunities(
    account_ids: List[str],
    lookback_days: int = 30,
    term_in_years: int = 1
)
```
