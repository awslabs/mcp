# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import importlib
import inspect
import logging
from typing import Set, Any

# Import FastMCP as Any to avoid type issues

from .types import is_prompt_function, as_prompt_function

# Configure logging
logger = logging.getLogger(__name__)

# Define a whitelist of allowed prompt modules
ALLOWED_PROMPT_MODULES: Set[str] = set()


def register_all_prompts(mcp: Any) -> None:
    """
    Dynamically discover and register all prompts from the prompts directory.

    This function:
    1. Finds all Python files in the prompts directory
    2. Imports each file as a module
    3. Finds all functions decorated with @finops_prompt
    4. Registers them with the MCP server
    """
    # Get the directory where this __init__.py file is located
    prompts_dir = os.path.dirname(os.path.abspath(__file__))

    # Find all Python files in the directory (excluding __init__.py and decorator.py)
    prompt_files = [
        f[:-3]
        for f in os.listdir(prompts_dir)
        if f.endswith('.py') and f not in ['__init__.py', 'decorator.py']
    ]

    # Update the whitelist with discovered modules
    ALLOWED_PROMPT_MODULES.update(prompt_files)

    # Import each module and find decorated functions
    registered_count = 0
    for module_name in prompt_files:
        # Validate module name against whitelist
        if module_name not in ALLOWED_PROMPT_MODULES:
            logger.warning(f"Module '{module_name}' is not in the allowed modules list. Skipping.")
            continue

        # Import the module
        module_path = f'awslabs.aws_finops_mcp_server.prompts.{module_name}'
        try:
            module = importlib.import_module(module_path)

            # Find all functions decorated with @finops_prompt
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) and is_prompt_function(obj):
                    # Cast to PromptFunction for type checking
                    prompt_func = as_prompt_function(obj)

                    # Register the function with the MCP server
                    mcp.prompt(
                        name=prompt_func._prompt_name,
                        description=prompt_func._prompt_description,
                        # Removed tags parameter as it's not supported in this version of FastMCP
                    )(obj)
                    registered_count += 1
                    logger.info(f'Registered prompt: {prompt_func._prompt_name}')
        except Exception as e:
            logger.error(f'Error loading prompts from {module_path}: {e}')

    logger.info(f'Registered {registered_count} prompts from {len(prompt_files)} files')
