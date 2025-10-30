# MCP Tool Evaluation Framework

Generic evaluation framework for testing AI agents using Model Context Protocol (MCP) tools. Provides reusable components for metrics tracking, agent orchestration, and validation.

Currently used for evaluating the `get_enablement_guide` tool. Will be expanded to other MCP tools in the future.

## Quick Start

### Running Existing Evals

```bash
# Run enablement evaluation (all tasks)
python evals/eval_enablement.py

# Run with verbose logging
python evals/eval_enablement.py -v

# Run specific task without cleanup
python evals/eval_enablement.py --task ec2_python_flask --no-cleanup
```
