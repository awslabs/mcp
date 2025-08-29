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

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


def process_template_body(template_body: Any, stack_name: str) -> Dict:
    """Process template body into proper dictionary format."""
    if isinstance(template_body, dict):
        return template_body
    elif isinstance(template_body, str):
        try:
            return json.loads(template_body)
        except json.JSONDecodeError:
            logger.error(f'Template body for {stack_name} is not valid JSON.')
            # Return a wrapper dict for invalid JSON strings
            return {'InvalidTemplateBody': template_body}
    else:
        logger.error(
            f'Template body for {stack_name} is of unexpected type: {type(template_body)}'
        )
        return {'UnexpectedTemplateBody': str(template_body)}


def save_template_file(
    stack_name: str, template_body: Any, working_directory: Optional[str] = None
) -> Optional[str]:
    """Save template file to the specified working directory.

    Args:
        stack_name: Name of the stack for the template
        template_body: Template body content to save
        working_directory: Directory to save the template (defaults to current working directory)

    Returns:
        Path to the saved template file, or None if saving failed
    """
    if not template_body:
        logger.warning(f'No template body provided for stack: {stack_name}')
        return None

    try:
        logger.info(f'Getting template for stack: {stack_name}')

        # Use provided working directory or default to current working directory
        target_dir = working_directory if working_directory else os.getcwd()
        template_file = Path(target_dir) / f'stack_template_{stack_name}.json'
        logger.info(f'Writing template to: {template_file}')

        # Handle different template body formats
        template_dict = process_template_body(template_body, stack_name)

        # Ensure the directory exists
        template_file.parent.mkdir(parents=True, exist_ok=True)

        with open(template_file, 'w') as f:
            json.dump(template_dict, f, indent=2)

        logger.info(f'Successfully wrote template to: {template_file}')
        return str(template_file)

    except Exception as e:
        logger.error(f'Failed to save template for {stack_name}: {str(e)}')
        return None


def save_multiple_templates(
    templates: Dict[str, Any], working_directory: Optional[str] = None
) -> Dict[str, Optional[str]]:
    """Save multiple template files to the specified working directory.

    Args:
        templates: Dictionary mapping stack names to template bodies
        working_directory: Directory to save the templates (defaults to current working directory)

    Returns:
        Dictionary mapping stack names to file paths (or None if saving failed)
    """
    results = {}
    for stack_name, template_body in templates.items():
        file_path = save_template_file(stack_name, template_body, working_directory)
        results[stack_name] = file_path
    return results
