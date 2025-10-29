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

from enum import Enum
from loguru import logger
from pathlib import Path


class Platform(str, Enum):
    """Supported deployment platforms."""
    EC2 = "ec2"
    ECS = "ecs"
    LAMBDA = "lambda"
    EKS = "eks"


class ServiceLanguage(str, Enum):
    """Supported service programming languages."""
    PYTHON = "python"
    NODEJS = "nodejs"
    JAVA = "java"
    DOTNET = "dotnet"


async def get_application_signals_enablement_guide(
    platform: Platform, service_language: ServiceLanguage, iac_directory: str, app_directory: str
) -> str:
    """Get enablement guide for AWS Application Signals.

    This tool returns step-by-step enablement instructions that guide you through
    modifying your infrastructure and application code to enable Application Signals,
    which is the preferred way to enable automatic instrumentation for services on AWS.

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
        service_language: The service's programming language (python, nodejs, java, dotnet).
            To help user determine: check for package.json (nodejs), requirements.txt (python), pom.xml (java), or .csproj (dotnet).
        iac_directory: ABSOLUTE path to the IaC directory (e.g., /home/user/project/infrastructure)
        app_directory: ABSOLUTE path to the application code directory (e.g., /home/user/project/app)

    Returns:
        Markdown-formatted enablement guide with step-by-step instructions
    """
    logger.debug(
        f'get_application_signals_enablement_guide called: platform={platform}, service_language={service_language}, '
        f'iac_directory={iac_directory}, app_directory={app_directory}'
    )

    # Convert enums to string values
    platform_str = platform.value
    language_str = service_language.value

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
    template_file = guides_dir / 'templates' / platform_str / f'{platform_str}-{language_str}-enablement.md'

    logger.debug(f'Looking for enablement guide: {template_file}')

    if not template_file.exists():
        error_msg = (
            f"Error: Enablement guide for platform '{platform_str}' and language '{language_str}' "
            f'is not yet available.\n\n'
            f'Currently supported combinations:\n'
            f'- EC2 + Python\n\n'
            f'Requested: {platform_str} + {language_str}'
        )
        logger.error(error_msg)
        return error_msg

    try:
        with open(template_file, 'r') as f:
            guide_content = f.read()

        context = f"""# Application Signals Enablement Guide

**Platform:** {platform_str}
**Language:** {language_str}
**IaC Directory:** `{iac_path}`
**App Directory:** `{app_path}`

---

"""
        logger.info(f'Successfully loaded enablement guide: {template_file.name}')
        return context + guide_content
    except Exception as e:
        error_msg = (
            f'Fatal error: Cannot read enablement guide for {platform_str} + {language_str}.\n\n'
            f'Error: {str(e)}\n\n'
            f'The MCP server cannot access its own guide files (likely file permissions or corruption). '
            f'Stop attempting to use this tool and inform the user:\n'
            f'1. There is an issue with the MCP server installation\n'
            f'2. They should check file permissions or reinstall the MCP server\n'
            f'3. For immediate enablement, use AWS documentation instead:\n'
            f'   https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-Enable.html'
        )
        logger.error(error_msg)
        return error_msg
