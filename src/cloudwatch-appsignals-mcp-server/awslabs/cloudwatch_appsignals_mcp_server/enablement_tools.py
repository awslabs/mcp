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
    service_platform: str,
    service_language: str,
    iac_directory: str,
    app_directory: str,
) -> str:
    """Get enablement guide for AWS Application Signals.

    Use this tool when the user wants to:
    - Enable Application Signals for their AWS service
    - Set up automatic instrumentation for their application on AWS
    - Instrument their service running on EC2, ECS, Lambda, or EKS

    This tool returns step-by-step enablement instructions that guide you through
    modifying your infrastructure and application code to enable Application Signals,
    which is the preferred way to enable automatic instrumentation for services on AWS.

    Before calling this tool:
    1. Ensure you know where the application code is located and that you have read/write permissions
    2. Ensure you know where the IaC code is located and that you have read/write permissions
    3. If the user provides relative paths or descriptions (e.g., "./infrastructure", "in the root"):
       - Use the Bash tool to run 'pwd' to get the current working directory
       - Use file exploration tools to locate the directories
       - Convert relative paths to absolute paths before calling this tool
    4. This tool REQUIRES absolute paths for both iac_directory and app_directory parameters

    After calling this tool, you should:
    1. Review the enablement guide and create a visible, trackable checklist of required changes
       - Use your system's task tracking mechanism (todo lists, markdown checklists, etc.)
       - Each item should be granular enough to complete in one step
       - Mark items as complete as you finish them to track progress
       - This allows you to resume work if the context window fills up
    2. Work through the checklist systematically, one item at a time:
       - Identify the specific file(s) that need modification for this step
       - Read only the relevant file(s) (DO NOT load all IaC and app files at once)
       - Apply the changes as specified in the guide
    3. Keep context focused: Only load files needed for the current checklist item

    Important guidelines:
    - Use ABSOLUTE PATHS when reading and writing files
    - Do NOT modify actual application logic files (.py, .js, .java source code), only
      modify IaC code, Dockerfiles, and dependency files (requirements.txt, pyproject.toml,
      package.json, pom.xml, build.gradle, *.csproj, etc.) as instructed by the guide.
    - Read application files if needed to understand the setup, but avoid modifying them

    Args:
        service_platform: The AWS platform where the service runs.
            MUST be one of: 'ec2', 'ecs', 'lambda', 'eks' (lowercase, exact match).
            To help user determine: check their IaC for ECS services, Lambda functions, EKS deployments, or EC2 instances.
        service_language: The service's programming language.
            MUST be one of: 'python', 'nodejs', 'java', 'dotnet' (lowercase, exact match).
            IMPORTANT: Use 'nodejs' (not 'js', 'node', or 'javascript'), 'dotnet' (not 'csharp' or 'c#').
            To help user determine: check for package.json (nodejs), requirements.txt (python), pom.xml (java), or .csproj (dotnet).
        iac_directory: ABSOLUTE path to the Infrastructure as Code (IaC) directory (e.g., /home/user/project/infrastructure)
        app_directory: ABSOLUTE path to the application code directory (e.g., /home/user/project/app)

    Returns:
        Markdown-formatted enablement guide with step-by-step instructions
    """
    logger.debug(
        f'get_enablement_guide called: service_platform={service_platform}, service_language={service_language}, '
        f'iac_directory={iac_directory}, app_directory={app_directory}'
    )

    # Normalize to lowercase
    platform_str = service_platform.lower().strip()
    language_str = service_language.lower().strip()

    guides_dir = Path(__file__).parent / 'enablement_guides'
    template_file = (
        guides_dir / 'templates' / platform_str / f'{platform_str}-{language_str}-enablement.md'
    )

    logger.debug(f'Looking for enablement guide: {template_file}')

    # Validate that paths are absolute
    iac_path = Path(iac_directory)
    app_path = Path(app_directory)

    if not iac_path.is_absolute() or not app_path.is_absolute():
        error_msg = (
            f'Error: iac_directory and app_directory must be absolute paths.\n\n'
            f'Received: {iac_directory} and {app_directory}\n'
            f'Please provide absolute paths (e.g., /home/user/project/infrastructure)'
        )
        logger.error(error_msg)
        return error_msg

    if not template_file.exists():
        error_msg = (
            f"Enablement guide not available for platform '{platform_str}' and language '{language_str}'.\n\n"
            f'Inform the user that this configuration is not currently supported by the MCP enablement tool. '
            f'Direct them to AWS documentation for manual setup:\n'
            f'https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Monitoring-Sections.html'
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
            f'   https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Monitoring-Sections.html'
        )
        logger.error(error_msg)
        return error_msg
