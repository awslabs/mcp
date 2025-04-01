from importlib import resources


with resources.files('awslabs.core_mcp_server.static').joinpath('PROMPT_UNDERSTANDING.md').open('r') as f:
    PROMPT_UNDERSTANDING = f.read()