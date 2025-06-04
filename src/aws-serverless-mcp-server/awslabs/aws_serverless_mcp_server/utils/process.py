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

import asyncio
from loguru import logger


async def run_command(cmd_list, cwd=None):
    """Run a terminal command with arguments asynchronously.

    Args:
        cmd_list (str): The command and arguments to run in a list
        cwd (str, optional): Working directory to run the command in
    Returns:
        tuple: (stdout, stderr)

    Raises:
        Exception: If the command fails
    """
    process = await asyncio.create_subprocess_exec(
        *cmd_list, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        logger.error(f'Command failed with exit code {process.returncode}')
        logger.error(f'STDOUT: {stdout.decode()}')
        logger.error(f'STDERR: {stderr.decode()}')
        raise Exception(f'Command failed: {stderr.decode()}')

    return stdout, stderr
