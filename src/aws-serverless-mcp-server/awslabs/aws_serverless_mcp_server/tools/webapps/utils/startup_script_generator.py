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
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

"""Startup Script Generator for AWS Serverless MCP Server.

Automatically generates appropriate startup scripts for different runtimes
to work with Lambda Web Adapter.
"""

import os
import stat
from loguru import logger
from typing import Dict, Optional


class EntryPointNotFoundError(Exception):
    """Custom error class for entry point not found errors."""

    def __init__(self, entry_point: str, built_artifacts_path: str):
        """Initializes the EntryPointNotFoundError with the specified entry point and built artifacts path.

        Args:
            entry_point (str): The name of the entry point file that was not found.
            built_artifacts_path (str): The path to the directory containing built artifacts.

        Raises:
            EntryPointNotFoundError: If the specified entry point file does not exist in the built artifacts path.
        """
        self.entry_point = entry_point
        self.built_artifacts_path = built_artifacts_path
        message = f'Entry point file not found: {os.path.join(built_artifacts_path, entry_point)}'
        super().__init__(message)
        self.name = 'EntryPointNotFoundError'


async def generate_startup_script(
    runtime: str,
    entry_point: str,
    built_artifacts_path: str,
    startup_script_name: Optional[str] = None,
    additional_env: Optional[Dict[str, str]] = None,
) -> str:
    """Generate a startup script based on runtime and entry point. This script starts up your web server so that beings listening for requests.

    Args:
        runtime: Lambda runtime (e.g., nodejs22.x, python3.13)
        entry_point: Application entry point
        built_artifacts_path: Path to the built artifacts
        startup_script_name: Name of the startup script (default: 'bootstrap')
        additional_env: Additional environment variables

    Returns:
        str: Path to the generated startup script

    Raises:
        EntryPointNotFoundError: If the entry point file doesn't exist
    """
    startup_script_name = startup_script_name or get_default_startup_script_name(runtime)
    script_path = os.path.join(built_artifacts_path, startup_script_name)
    entry_point_path = os.path.join(built_artifacts_path, entry_point)

    logger.info(f'Generating startup script for runtime: {runtime}, entry point: {entry_point}')

    # Check if entry point exists
    if not os.path.exists(entry_point_path):
        error = EntryPointNotFoundError(entry_point, built_artifacts_path)
        logger.error(error.args[0])

        # Provide helpful suggestions
        logger.info('Available files in the artifacts directory:')
        try:
            files = os.listdir(built_artifacts_path)
            if len(files) == 0:
                logger.info('  (directory is empty)')
            else:
                for file in files:
                    logger.info(f'  - {file}')
        except Exception:
            logger.error(f'Could not read directory: {built_artifacts_path}')

        raise error

    # Generate script content based on runtime
    script_content = generate_script_content(runtime, entry_point, additional_env)

    # Write script to file
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)

    # Make script executable
    os.chmod(
        script_path, os.stat(script_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    )

    logger.info(f'Startup script generated at: {script_path}')

    return startup_script_name


def get_default_startup_script_name(runtime: str) -> str:
    """Get default startup script name for a runtime.

    Args:
        runtime: Lambda runtime

    Returns:
        str: Default startup script name
    """
    # Lambda expects a file named "bootstrap" for custom runtimes
    return 'bootstrap'


def generate_script_content(
    runtime: str, entry_point: str, additional_env: Optional[Dict[str, str]] = None
) -> str:
    """Generate script content based on runtime and entry point.

    Args:
        runtime: Lambda runtime
        entry_point: Application entry point
        additional_env: Additional environment variables

    Returns:
        str: Script content
    """
    # Generate environment variables setup
    env_setup = ''
    if additional_env:
        env_vars = []
        for key, value in additional_env.items():
            env_vars.append(f'export {key}="{value}"')
        env_setup = '\n'.join(env_vars) + '\n\n'

    if runtime.startswith('nodejs'):
        return f"""#!/bin/bash
{env_setup}# Start the application
exec node {entry_point}
"""
    elif runtime.startswith('python'):
        return f"""#!/bin/bash
{env_setup}# Start the application
exec python {entry_point}
"""
    elif runtime.startswith('java'):
        # Determine if it's a JAR file or a class
        is_jar = entry_point.lower().endswith('.jar')

        if is_jar:
            return f"""#!/bin/bash
{env_setup}# Start the application
exec java -jar {entry_point}
"""
        else:
            return f"""#!/bin/bash
{env_setup}# Start the application
exec java {entry_point}
"""
    elif runtime.startswith('dotnet'):
        return f"""#!/bin/bash
{env_setup}# Start the application
exec dotnet {entry_point}
"""
    elif runtime.startswith('go'):
        return f"""#!/bin/bash
{env_setup}# Start the application
exec ./{entry_point}
"""
    elif runtime.startswith('ruby'):
        return f"""#!/bin/bash
{env_setup}# Start the application
exec ruby {entry_point}
"""
    else:
        # Generic script for unknown runtimes
        return f"""#!/bin/bash
{env_setup}# Start the application
exec {entry_point}
"""
