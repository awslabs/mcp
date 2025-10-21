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

"""Application Signals enablement tools for MCP server."""

from loguru import logger
from pathlib import Path


async def enable_application_signals(
    platform: str, language: str, iac_directory: str, app_directory: str
) -> str:
    """Enable AWS Application Signals by modifying the user's infrastructure and application code.

    This tool returns step-by-step enablement instructions that you MUST use to modify
    the user's actual infrastructure and application files. After calling this tool, you
    should immediately read the user's existing files and apply the changes specified in
    the returned guide.

    IMPORTANT: Do NOT just return the instructions to the user. You must:
    1. Read the user's existing IaC files from iac_directory
    2. Read the user's existing application files from app_directory
    3. Apply the changes specified in the enablement guide to those files
    4. Verify the changes are correct and complete

    The instructions are provided in CDK TypeScript format, which you can translate to
    the user's IaC tool (CDK, CloudFormation, or Terraform) if needed.

    Args:
        platform: The deployment platform (ec2, ecs, lambda, eks, kubernetes)
        language: The programming language (python, nodejs, java, dotnet)
        iac_directory: Path to the IaC directory (e.g., "infrastructure/ec2/cdk")
        app_directory: Path to the application code directory (e.g., "sample-apps/python/flask")

    Returns:
        Enablement guide with step-by-step instructions to apply to the user's code
    """
    logger.debug(
        f'enable_application_signals called: platform={platform}, language={language}, '
        f'iac_directory={iac_directory}, app_directory={app_directory}'
    )

    # Normalize inputs
    platform = platform.lower().strip()
    language = language.lower().strip()

    # Validate platform
    valid_platforms = ['ec2', 'ecs', 'lambda', 'eks', 'kubernetes']
    if platform not in valid_platforms:
        return f"Error: Invalid platform '{platform}'. Valid platforms are: {', '.join(valid_platforms)}"

    # Validate language
    valid_languages = ['python', 'nodejs', 'java', 'dotnet']
    if language not in valid_languages:
        return f"Error: Invalid language '{language}'. Valid languages are: {', '.join(valid_languages)}"

    # Build template path: enablement_guides/templates/{platform}/{platform}-{language}-enablement.md
    guides_dir = Path(__file__).parent / 'enablement_guides'
    template_file = guides_dir / 'templates' / platform / f'{platform}-{language}-enablement.md'

    logger.debug(f'Looking for enablement guide: {template_file}')

    # Check if template exists
    if not template_file.exists():
        logger.warning(f'Enablement guide not found: {template_file}')
        return f"Error: Enablement guide for platform '{platform}' and language '{language}' is not yet available. Currently supported: EC2 + Python."

    # Read template
    try:
        with open(template_file, 'r') as f:
            guide_content = f.read()

        # Prepend context about directories
        context = f"""# Application Signals Enablement Context

**IaC Directory:** `{iac_directory}`
**Application Directory:** `{app_directory}`
**Platform:** {platform}
**Language:** {language}

Modify the IaC files in the IaC directory to enable Application Signals for the application in the application directory.

---

"""

        logger.info(f'Successfully loaded enablement guide: {template_file.name}')
        return context + guide_content

    except Exception as e:
        logger.error(f'Error reading enablement guide {template_file}: {e}')
        return f'Error: Failed to read enablement guide. {str(e)}'
