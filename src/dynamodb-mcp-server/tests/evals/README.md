# DynamoDB MCP Evaluation System

A comprehensive evaluation framework for assessing DynamoDB data modeling guidance quality using advanced conversational AI and structured evaluation methodologies.

## Overview

This evaluation system combines realistic conversational interactions with sophisticated quality assessment to evaluate the effectiveness of DynamoDB modeling guidance. It uses a three-layer architecture integrating Strands agents, MCP protocol, and DSPy evaluation engines to provide objective, systematic assessment of both modeling process quality and technical design excellence.

### Key Features

- **Realistic Conversations**: Uses Strands agents with MCP protocol for authentic user-expert interactions
- **Dual Evaluation Framework**: Separately assesses modeling process (HOW) and design quality (WHAT)
- **Expert Knowledge Integration**: Leverages DynamoDB architect prompt for domain-specific evaluation
- **Comprehensive Scoring**: 10-dimensional assessment covering methodology and technical excellence
- **Multiple Scenarios**: Predefined scenarios across different complexity levels and domains
- **Performance Monitoring**: Detailed timing analysis and efficiency metrics

### Dual Evaluation Framework

**Session Evaluation** - Assesses the modeling process quality:
- Requirements Engineering (1-10)
- Access Pattern Analysis (1-10)
- Methodology Adherence (1-10)
- Technical Reasoning (1-10)
- Process Documentation (1-10)

**Model Evaluation** - Assesses the technical design quality:
- Completeness (1-10)
- Technical Accuracy (1-10)
- Access Pattern Coverage (1-10)
- Scalability Considerations (1-10)
- Cost Optimization (1-10)

## Quick Start

### Prerequisites

1. **AWS Credentials**: Configure AWS access with Bedrock permissions
```bash
export AWS_PROFILE=your-profile
export AWS_REGION=us-east-1
# OR
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
```

2. **Python Environment**: Python 3.10+ with uv package manager
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Navigate to the DynamoDB MCP server directory
cd src/dynamodb-mcp-server
```

3. **Dependencies**: Install required packages
```bash
uv sync
```

### Basic Usage

Run a basic evaluation with default settings:

```bash
uv run python tests/evals/test_dspy_evals.py
```

This will:
- Use the default model: `bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0`
- Run the "Simple E-commerce Schema" scenario
- Execute the complete evaluation pipeline
- Display comprehensive results

### Sample Output

```
🔧 EVALUATION CONFIGURATION
==============================
Model: bedrock/us.anthropic.claude-3-5-sonnet-20241022-v2:0
Scenario: Simple E-commerce Schema

✅ DSPy configured with bedrock/us.anthropic.claude-3-5-sonnet-20241022-v2:0
🎯 Testing scenario complexity: beginner
🔄 Running conversation for scenario: Simple E-commerce Schema
...
✅ Conversation completed in 61.20s
🔄 Running DSPy session evaluation...
✅ Session evaluation completed in 11.61s
📊 Session Score: 8.40 (good)
🔄 Running DSPy model evaluation...
✅ Model evaluation completed in 12.12s
📊 Model Score: 8.20 (good)
🎯 Complete evaluation finished in 84.93s

============================================================
COMPREHENSIVE EVALUATION RESULTS
============================================================
⏱️  Total Duration: 84.93s
   • Conversation: 61.20s
   • Session Evaluation: 11.61s
   • Model Evaluation: 12.12s

📋 SESSION EVALUATION (Requirements & Methodology)
--------------------------------------------------
🎯 Overall Session Score: 8.40 (good)

📊 Detailed Session Scores:
   • Requirements Engineering: 9.0/10
   • Access Pattern Analysis: 8.0/10
   • Methodology Adherence: 8.0/10
   • Technical Reasoning: 8.0/10
   • Process Documentation: 9.0/10

🏗️  MODEL EVALUATION (Technical Design)
--------------------------------------------------
🎯 Overall Model Score: 8.20 (good)

📊 Detailed Model Scores:
   • Completeness: 9.0/10
   • Technical Accuracy: 8.0/10
   • Access Pattern Coverage: 9.0/10
   • Scalability Considerations: 8.0/10
   • Cost Optimization: 7.0/10

🎖️  QUALITY SUMMARY
--------------------------------------------------
Session Quality: good
Model Quality: good
```

## Command Line Usage

### Available Commands

**Basic evaluation:**
```bash
uv run python tests/evals/test_dspy_evals.py
```

**Custom model evaluation:**
```bash
uv run python tests/evals/test_dspy_evals.py --model "bedrock/us.anthropic.claude-3-5-sonnet-20241022-v2:0"
```

**Specific scenario testing:**
```bash
uv run python tests/evals/test_dspy_evals.py --scenario "High-Scale Social Media Platform"
```

**Combined configuration:**
```bash
uv run python tests/evals/test_dspy_evals.py --model "custom-model" --scenario "Content Management System"
```

**List available scenarios:**
```bash
uv run python tests/evals/test_dspy_evals.py --list-scenarios
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--model` | Bedrock model ID to use | `bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0` |
| `--scenario` | Scenario name to evaluate | `"Simple E-commerce Schema"` |
| `--list-scenarios` | Show all available scenarios | - |
| `--debug` | Show raw JSON output | - |
| `--aws-profile` | AWS profile to use for evaluation | `Bedrock` |

## Available Scenarios

The system includes predefined scenarios across different complexity levels:

### Beginner Scenarios
- **Simple E-commerce Schema**: Basic online retail with users, products, orders
- **Content Management System**: Blog/CMS with articles, authors, categories

### Advanced Scenarios
- **High-Scale Social Media Platform**: Social media with posts, likes, comments at scale

### Scenario Structure

Each scenario includes:
- **Application Details**: Type, domain, business model
- **Entities & Relationships**: Complete data model definition
- **Access Patterns**: Read/write patterns with performance requirements
- **Scale Requirements**: User base, transaction volume, growth projections
- **Performance Targets**: Latency and throughput specifications

To see all scenarios with descriptions:
```bash
uv run python tests/evals/test_dspy_evals.py --list-scenarios
```

## Understanding Results

### Quality Levels

Results are classified into quality levels based on overall scores:

| Score Range | Quality Level | Description |
|-------------|---------------|-------------|
| 8.5 - 10.0 | `excellent` | Exceptional quality - ready for production |
| 7.0 - 8.4 | `good` | Solid quality - minor improvements needed |
| 5.5 - 6.9 | `acceptable` | Adequate - meets basic requirements |
| 4.0 - 5.4 | `needs_improvement` | Deficient - significant gaps present |
| 1.0 - 3.9 | `poor` | Major issues - substantial rework required |

### Performance Characteristics

Typical evaluation timing:
- **Conversation Phase**: 30-60 seconds (depends on model and scenario complexity)
- **Session Evaluation**: 10-15 seconds (DSPy process assessment)
- **Model Evaluation**: 10-15 seconds (DSPy design assessment)
- **Total Duration**: 50-90 seconds for complete pipeline

### Session vs Model Evaluation

**Session Evaluation** focuses on **HOW** the modeling was conducted:
- Did the system follow proper methodology?
- Were requirements properly gathered and analyzed?
- Was the decision-making process well-documented?
- Were trade-offs and alternatives considered?

**Model Evaluation** focuses on **WHAT** was delivered:
- Is the final design technically correct?
- Does it handle all required access patterns?
- Are scalability concerns addressed?
- Is the solution cost-optimized?

## Configuration

### Model Selection

The system supports any Bedrock-compatible model. Popular choices:

```bash
# Claude 4 Sonnet (recommended)
--model "bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0"

# Claude 3.5 Sonnet
--model "bedrock/us.anthropic.claude-3-5-sonnet-20241022-v2:0"

# Other Bedrock models
--model "bedrock/amazon.titan-text-premier-v1:0"
```

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `AWS_PROFILE` | AWS credential profile | - |
| `AWS_REGION` | AWS region for Bedrock | `us-east-1` |
| `AWS_ACCESS_KEY_ID` | Direct AWS credentials | - |
| `AWS_SECRET_ACCESS_KEY` | Direct AWS credentials | - |

## Troubleshooting

### Common Issues

**AWS Credentials Error:**
```
AWS credentials not available - set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY or AWS_PROFILE
```
**Solution**: Configure AWS credentials as shown in Prerequisites section.

**Model Access Error:**
```
Could not access the model: bedrock/model-name
```
**Solution**: Ensure your AWS account has access to the requested Bedrock model and proper permissions.

**Scenario Not Found:**
```
Scenario 'Invalid Name' not found
```
**Solution**: Use `--list-scenarios` to see available options and check spelling.

**MCP Connection Issues:**
```
Error during Strands conversation: MCP connection failed
```
**Solution**: Ensure the DynamoDB MCP server is properly installed and accessible.

### Extending the System

**Adding New Scenarios:**
1. Add scenario definition to `scenarios.py`
2. Include all required fields (entities, access patterns, scale)
3. Test with different models for consistency

**Adding New Evaluation Dimensions:**

The system uses a dynamic registry pattern that makes adding new evaluation dimensions extremely simple - no code changes required to the evaluation engine!

**3-Step Process:**
1. **Add Dimension to Registry** - Simply add a new `DimensionConfig` to the appropriate evaluation in `evaluation_registry.py`
2. **Define Scoring Rubric** - Specify how the dimension should be evaluated (1-10 scale)
3. **Test Immediately** - The dynamic evaluator automatically picks up the new dimension

**Example - Adding Security Evaluation:**
```python
# In evaluation_registry.py, add to model_dimensions list:
DimensionConfig(
    name="security_considerations",
    display_name="Security Considerations",
    description="Data security and access control planning",
    scoring_rubric=(
        "Score 1-10: Evaluate security measures including "
        "encryption, access patterns, IAM policies, and data protection. "
        "Return single number 1-10."
    ),
    weight=1.0,
    justification_prompt="Explain security assessment and recommendations"
)
```

**That's it!** The `DynamicEvaluationEngine` will automatically:
- Generate DSPy signatures with your new dimension
- Create result dataclasses including the new field
- Integrate scoring and justification collection
- Make it available in CLI evaluations

**No changes needed to:**
- `dynamic_evaluators.py` - automatically adapts
- `test_dspy_evals.py` - CLI works immediately
- Result processing - handled automatically

**New Model Support:**
1. Ensure model is available in AWS Bedrock
2. Test compatibility with DSPy framework
3. Adjust timeout settings if needed

**Architecture Overview:**
- `evaluation_registry.py`: Dynamic registry for evaluation dimensions and types
- `dynamic_evaluators.py`: DSPy evaluation engine that adapts to registry configurations
- `multiturn_evaluator.py`: Multi-turn conversation evaluator using Strands agents
- `scenarios.py`: Test scenario definitions for evaluation
- `test_dspy_evals.py`: Command-line interface for the evaluation system

## Development and Contributing

### Running Tests

```bash
# Run a quick evaluation
uv run python tests/evals/test_dspy_evals.py

# Test different models
uv run python tests/evals/test_dspy_evals.py --model "bedrock/us.anthropic.claude-3-5-sonnet-20241022-v2:0"

# Test all scenarios
for scenario in "Simple E-commerce Schema" "High-Scale Social Media Platform" "Content Management System"; do
  uv run python tests/evals/test_dspy_evals.py --scenario "$scenario"
done
```
