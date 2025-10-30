"""Generic evaluation framework for MCP tools.

This framework provides reusable components for evaluating MCP tools:
- MetricsTracker: Track tool usage, success rates, hit rates
- Agent loop: Multi-turn conversation orchestration
- File tools: Generic file operations (list, read, write)
- Validation: LLM-as-judge evaluation with rubrics
"""

from .agent import execute_tool, run_agent_loop
from .file_tools import get_file_tools
from .mcp_client import connect_to_mcp_server, convert_mcp_tools_to_bedrock
from .metrics import MetricsTracker
from .validation import run_build_validation, validate_with_llm


__all__ = [
    'MetricsTracker',
    'connect_to_mcp_server',
    'convert_mcp_tools_to_bedrock',
    'get_file_tools',
    'execute_tool',
    'run_agent_loop',
    'validate_with_llm',
    'run_build_validation',
]
