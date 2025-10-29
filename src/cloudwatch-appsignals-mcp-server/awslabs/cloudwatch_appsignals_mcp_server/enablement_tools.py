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

"""CloudWatch Application Signals MCP Server - Enablement Tools."""

from loguru import logger
from pathlib import Path


async def get_enablement_guide(
    platform: str, language: str, iac_directory: str, app_directory: str
) -> str:
    """Get enablement guide for AWS Application Signals.

    This tool returns step-by-step enablement instructions that guide you through
    modifying your infrastructure and application code to enable Application Signals.

    After calling this tool, you should:
    1. Read the existing IaC files from iac_directory
    2. Read the existing application files from app_directory
    3. Apply the changes specified in the enablement guide to those files
    4. Verify the changes are correct and complete

    Args:
        platform: The deployment platform (ec2, ecs, lambda, eks)
        language: The programming language (python, nodejs, java, dotnet)
        iac_directory: ABSOLUTE path to the IaC directory (e.g., /home/user/project/infrastructure)
        app_directory: ABSOLUTE path to the application code directory (e.g., /home/user/project/app)

    Returns:
        Markdown-formatted enablement guide with step-by-step instructions
    """
    logger.debug(
        f'get_enablement_guide called: platform={platform}, language={language}, '
        f'iac_directory={iac_directory}, app_directory={app_directory}'
    )

    platform = platform.lower().strip()
    language = language.lower().strip()

    valid_platforms = ['ec2', 'ecs', 'lambda', 'eks']
    if platform not in valid_platforms:
        return f"Error: Invalid platform: '{platform}'. Valid platforms are: {', '.join(valid_platforms)}"

    valid_languages = ['python', 'nodejs', 'java', 'dotnet']
    if language not in valid_languages:
        return f"Error: Invalid language '{language}'. Valid languages are: {', '.join(valid_languages)}"

    # Validate that paths are absolute
    iac_path = Path(iac_directory)
    app_path = Path(app_directory)

    if not iac_path.is_absolute():
        error_msg = (
            f'Error: iac_directory must be an absolute path.\n\n'
            f'Received: {iac_directory}\n'
            f'Please provide an absolute path (e.g., /home/user/project/infrastructure)'
        )
        logger.error(error_msg)
        return error_msg

    if not app_path.is_absolute():
        error_msg = (
            f'Error: app_directory must be an absolute path.\n\n'
            f'Received: {app_directory}\n'
            f'Please provide an absolute path (e.g., /home/user/project/app)'
        )
        logger.error(error_msg)
        return error_msg

    logger.debug(f'IaC path: {iac_path}')
    logger.debug(f'App path: {app_path}')

    if not iac_path.exists():
        error_msg = (
            f'Error: IaC directory does not exist: {iac_path}\n\n'
            f'Please provide a valid path to your infrastructure code directory.'
        )
        logger.error(error_msg)
        return error_msg

    if not app_path.exists():
        error_msg = (
            f'Error: Application directory does not exist: {app_path}\n\n'
            f'Please provide a valid path to your application code directory.'
        )
        logger.error(error_msg)
        return error_msg

    guides_dir = Path(__file__).parent / 'enablement_guides'
    template_file = guides_dir / 'templates' / platform / f'{platform}-{language}-enablement.md'

    logger.debug(f'Looking for enablement guide: {template_file}')

    if not template_file.exists():
        logger.warning(f'Enablement guide not found: {template_file}')
        return (
            f"Error: Enablement guide for platform '{platform}' and language '{language}' "
            f' is not yet available.\n\n'
            f'Currently supported combinations:\n'
            f'- EC2 + Python\n\n'
            f'Requested: {platform} + {language}'
        )

    try:
        with open(template_file, 'r') as f:
            guide_content = f.read()

        context = f"""# Application Signals Enablement Guide

        ## Context

        **Platform:** {platform}
        **Language:** {language}
        **IaC Directory (absolute path):** `{iac_path}`
        **Application Directory (absolute path):** `{app_path}`

        ## Instructions

        1. Use the ABSOLUTE PATHS above when reading and writing files
        2. **IMPORTANT:** Only modify the IaC code or Dockerfiles. Actual application code should not be modified.
        Read application files if needed to understand the setup, but do not modify them.
        3. Follow the step-by-step enablement guide below to enable Application Signals

        ---
        """
        logger.info(f'Successfully loaded enablement guide: {template_file.name}')
        return context + guide_content
    except Exception as e:
        logger.error(f'Error reading enablement guide {template_file}: {e}')
        return f'Error: Failed to read enablement guide. {str(e)}'
