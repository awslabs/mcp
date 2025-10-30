"""Configuration constants for MCP tool evaluation framework.

Centralized location for all configurable values.
"""

# AWS Bedrock configuration
DEFAULT_MODEL_ID = 'us.anthropic.claude-sonnet-4-20250514-v1:0'
DEFAULT_AWS_REGION = 'us-east-1'

# Agent configuration
DEFAULT_MAX_TURNS = 20
DEFAULT_TEMPERATURE = 0.0

# Prompt templates
ENABLEMENT_TASK_PROMPT = """Enable Application Signals for my {language} {framework} on {platform}.

My infrastructure as code directory is: {iac_path}
My application directory is: {app_path}"""

LLM_JUDGE_VALIDATION_PROMPT = """You are evaluating code changes for a software modification task.

**Validation Rubric:**
{rubric_items}
{build_info}
**Git Diff of Changes:**
```diff
{git_diff}
```

Instructions:
For each criterion in the rubric, evaluate whether it is satisfied by the changes and build result.

Respond in this EXACT format:
1. [PASS/FAIL] Brief reasoning (1 sentence)
2. [PASS/FAIL] Brief reasoning (1 sentence)
... (continue for all {num_criteria} criteria)

Be strict but fair. Only mark as PASS if the criterion is clearly met."""
