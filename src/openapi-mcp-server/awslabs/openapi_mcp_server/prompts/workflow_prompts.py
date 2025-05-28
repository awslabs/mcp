"""Backward compatibility module for workflow prompts.

This module re-exports functions from api_documentation_workflow.py to maintain
backward compatibility with existing code that imports from workflow_prompts.py.
"""

from awslabs.openapi_mcp_server.prompts.api_documentation_workflow import (
    _generate_list_get_update_workflow,
    _generate_search_create_workflow,
    generate_generic_workflow_prompts,
)


__all__ = [
    '_generate_list_get_update_workflow',
    '_generate_search_create_workflow',
    'generate_generic_workflow_prompts',
]
