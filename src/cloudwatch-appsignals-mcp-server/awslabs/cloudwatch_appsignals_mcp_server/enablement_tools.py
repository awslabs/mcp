# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
from loguru import logger


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
        iac_directory: Path to the IaC directory (relative or absolute)
        app_directory: Path to the application code directory (relative or absolute)

    Returns:
        Enablement guide with step-by-step instructions
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

    def resolve_path(path_str: str) -> str:
        """Resolve path to absolute, handling both relative and absolute paths."""
        path = Path(path_str)
        if path.is_absolute():
            return str(path)
        else:
            return str(Path.cwd() / path)

    iac_full_path = resolve_path(iac_directory)
    app_full_path = resolve_path(app_directory)

    logger.debug(f'Resolved IaC path: {iac_full_path}')
    logger.debug(f'Resolved app path: {app_full_path}')

    if not Path(iac_full_path).exists():
        error_msg = (
            f'Error: IaC directory does not exist: {iac_full_path}\n\n'
            f'Please provide a valid path to your infrastructure code directory.'
        )
        logger.error(error_msg)
        return error_msg

    if not Path(app_full_path).exists():
        error_msg = (
            f'Error: Application directory does not exist: {app_full_path}\n\n'
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
        **IaC Directory (absolute path):** `{iac_full_path}`
        **Application Directory (absolute path):** `{app_full_path}`

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
