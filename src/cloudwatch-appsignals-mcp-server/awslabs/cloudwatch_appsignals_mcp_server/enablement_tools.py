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
    1. Review the enablement guide and create a work list of required changes
    2. For each step in the work list:
       - Identify the specific files in iac_directory or app_directory that need modification
       - Apply the changes as specified in the guide
       - Verify the changes are correct before moving to the next step

    Important guidelines:
    - Use ABSOLUTE PATHS (iac_directory and app_directory) when reading and writing files
    - Modify IaC code, Dockerfiles, and dependency files (requirements.txt, pyproject.toml,
      package.json, pom.xml, build.gradle, *.csproj, etc.) as needed
    - Do NOT modify actual application logic files (.py, .js, .java source code)
    - Read application files if needed to understand the setup, but avoid modifying them

    Args:
        platform: The AWS platform where the service runs (ec2, ecs, lambda, eks).
            To help user determine: check their IaC for ECS services, Lambda functions, EKS deployments, or EC2 instances.
        language: The application's programming language (python, nodejs, java, dotnet).
            To help user determine: check for package.json (nodejs), requirements.txt (python), pom.xml (java), or .csproj (dotnet).
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
        return (
            f"Error: Invalid platform '{platform}'.\n\n"
            f"Valid platforms are: {', '.join(valid_platforms)}\n\n"
            f"This configuration is not currently supported by the MCP enablement tool. "
            f"Please refer to the public docs for guidance on manual setup:\n"
            f"https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-supportmatrix.html"
        )

    valid_languages = ['python', 'nodejs', 'java', 'dotnet']
    if language not in valid_languages:
        return (
            f"Error: Invalid language '{language}'.\n\n"
            f"Valid languages are: {', '.join(valid_languages)}\n\n"
            f"This configuration is not currently supported by the MCP enablement tool. "
            f"Please refer to the public docs for guidance on manual setup:\n"
            f"https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-supportmatrix.html"
        )

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

**Platform:** {platform}
**Language:** {language}
**IaC Directory:** `{iac_path}`
**App Directory:** `{app_path}`

---

"""
        logger.info(f'Successfully loaded enablement guide: {template_file.name}')
        return context + guide_content
    except Exception as e:
        logger.error(f'Error reading enablement guide {template_file}: {e}')
        return (
            f'Fatal error: Cannot read enablement guide for {platform} + {language}.\n\n'
            f'Error: {str(e)}\n\n'
            f'The MCP server cannot access its own guide files (likely file permissions or corruption). '
            f'Stop attempting to use this tool and inform the user:\n'
            f'1. There is an issue with the MCP server installation\n'
            f'2. They should check file permissions or reinstall the MCP server\n'
            f'3. For immediate enablement, use AWS documentation instead:\n'
            f'   https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-Enable.html'
        )
