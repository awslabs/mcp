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

"""Agent loop for MCP tool evaluation.

Provides multi-turn conversation loop and tool execution utilities.
"""

import time
from .captor import (
    CONTENT_TEXT,
    CONTENT_TOOL_RESULT,
    CONTENT_TOOL_USE,
    MESSAGE_CONTENT,
    MESSAGE_ROLE,
    ROLE_ASSISTANT,
    ROLE_USER,
)
from .file_tools import (
    FILE_TOOL_LIST_FILES,
    FILE_TOOL_READ_FILE,
    FILE_TOOL_WRITE_FILE,
    get_file_tools,
)
from .metrics_tracker import MetricsTracker
from loguru import logger
from mcp import ClientSession
from pathlib import Path
from typing import Any, Dict, List


def convert_mcp_tools_to_bedrock(mcp_tools) -> List[Dict[str, Any]]:
    """Convert MCP tool format to Bedrock tool format.

    Args:
        mcp_tools: List of MCP tool definitions

    Returns:
        List of Bedrock-formatted tool specifications
    """
    bedrock_tools = []

    for tool in mcp_tools:
        bedrock_tool = {
            'toolSpec': {
                'name': tool.name,
                'description': tool.description or '',
                'inputSchema': {'json': tool.inputSchema},
            }
        }
        bedrock_tools.append(bedrock_tool)

    return bedrock_tools


# TODO: Add path validation to restrict file operations to workspace directory
async def execute_tool(
    tool_name: str,
    tool_input: Dict[str, Any],
    session: ClientSession,
    project_root: Path,
    metrics_tracker: MetricsTracker,
) -> Dict[str, Any]:
    """Execute a tool call (MCP tool or file operation).

    Args:
        tool_name: Name of the tool to execute
        tool_input: Input parameters for the tool
        session: MCP client session
        project_root: Root directory for file operations
        metrics_tracker: Metrics tracker instance

    Returns:
        Tool execution result
    """
    start = time.time()
    success = True
    error = None

    try:
        if tool_name == FILE_TOOL_LIST_FILES:
            dir_path = project_root / tool_input['path']

            if not dir_path.exists():
                raise FileNotFoundError(f'Directory not found: {tool_input["path"]}')
            if not dir_path.is_dir():
                raise NotADirectoryError(f'Path is not a directory: {tool_input["path"]}')

            try:
                files = [f.name for f in dir_path.iterdir()]
                result = {MESSAGE_CONTENT: [{CONTENT_TEXT: '\n'.join(files)}]}
            except PermissionError:
                raise PermissionError(
                    f'Permission denied accessing directory: {tool_input["path"]}'
                )

        elif tool_name == FILE_TOOL_READ_FILE:
            file_path = project_root / tool_input['path']

            if not file_path.exists():
                raise FileNotFoundError(f'File not found: {tool_input["path"]}')
            if not file_path.is_file():
                raise IsADirectoryError(f'Path is a directory, not a file: {tool_input["path"]}')

            try:
                content = file_path.read_text(encoding='utf-8', errors='replace')
                result = {MESSAGE_CONTENT: [{CONTENT_TEXT: content}]}
            except PermissionError:
                raise PermissionError(f'Permission denied reading file: {tool_input["path"]}')
            except UnicodeDecodeError:
                logger.warning(f'File appears to be binary: {tool_input["path"]}')
                raise ValueError(f'Cannot read binary file: {tool_input["path"]}')

        elif tool_name == FILE_TOOL_WRITE_FILE:
            file_path = project_root / tool_input['path']

            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                raise PermissionError(f'Permission denied creating directory: {file_path.parent}')

            if not file_path.parent.is_dir():
                raise IOError(f'Failed to create parent directory: {file_path.parent}')

            try:
                file_path.write_text(tool_input[MESSAGE_CONTENT], encoding='utf-8')
                result = {
                    MESSAGE_CONTENT: [
                        {CONTENT_TEXT: f'Successfully wrote to {tool_input["path"]}'}
                    ]
                }
            except PermissionError:
                raise PermissionError(f'Permission denied writing to file: {tool_input["path"]}')
            except OSError as e:
                raise IOError(f'Failed to write file {tool_input["path"]}: {str(e)}')

        else:
            # TODO: Improve MCP result handling/formatting
            mcp_result = await session.call_tool(tool_name, tool_input)
            result = {MESSAGE_CONTENT: [{CONTENT_TEXT: str(mcp_result.content)}]}

        return result
    except Exception as e:
        logger.error(f'Tool execution failed: {e}')
        success = False
        error = str(e)
        return {MESSAGE_CONTENT: [{CONTENT_TEXT: f'Error: {str(e)}'}], 'status': 'error'}
    finally:
        duration = time.time() - start
        params_to_log = {k: v for k, v in tool_input.items() if k != 'toolUseId'}
        metrics_tracker.record_tool_call(tool_name, params_to_log, duration, success, error)


async def run_conversation(
    llm_provider,
    session: ClientSession,
    prompt: str,
    project_root: Path,
    mcp_tools,
    metrics_tracker: MetricsTracker,
    max_turns: int,
) -> List[Dict[str, Any]]:
    """Run the agent loop for task completion.

    Args:
        llm_provider: LLMProvider instance for agent interactions
        session: MCP client session
        prompt: Task prompt for the agent
        project_root: Root directory for file operations
        mcp_tools: List of MCP tools from server
        metrics_tracker: Metrics tracker instance
        max_turns: Maximum number of conversation turns

    Returns:
        List of conversation messages
    """
    logger.debug('Sending prompt to Claude...')

    bedrock_mcp_tools = convert_mcp_tools_to_bedrock(mcp_tools)
    file_tools = get_file_tools()
    all_tools = bedrock_mcp_tools + file_tools

    logger.debug(f'Configured {len(all_tools)} tools')

    messages = [{MESSAGE_ROLE: ROLE_USER, MESSAGE_CONTENT: [{CONTENT_TEXT: prompt}]}]

    turn = 0

    metrics_tracker.start_task()

    while turn < max_turns:
        turn += 1
        logger.debug(f'=== Turn {turn}/{max_turns} ===')

        start = time.time()

        try:
            response = llm_provider.converse(
                messages=messages,
                tools=all_tools,
            )

            elapsed = time.time() - start
            logger.debug(f'Claude responded in {elapsed:.2f}s')
            logger.debug(f'Stop reason: {response["stopReason"]}')

            messages.append(
                {
                    MESSAGE_ROLE: ROLE_ASSISTANT,
                    MESSAGE_CONTENT: response['output']['message'][MESSAGE_CONTENT],
                }
            )

            if response['stopReason'] == 'tool_use':
                tool_results = []

                for content_block in response['output']['message'][MESSAGE_CONTENT]:
                    if CONTENT_TOOL_USE in content_block:
                        tool_use = content_block[CONTENT_TOOL_USE]
                        tool_name = tool_use['name']
                        tool_input = tool_use['input']
                        tool_use_id = tool_use['toolUseId']

                        logger.debug(f'Tool requested: {tool_name} with {tool_input}')

                        tool_input['toolUseId'] = tool_use_id
                        result = await execute_tool(
                            tool_name, tool_input, session, project_root, metrics_tracker
                        )

                        tool_results.append(
                            {
                                CONTENT_TOOL_RESULT: {
                                    'toolUseId': tool_use_id,
                                    MESSAGE_CONTENT: result[MESSAGE_CONTENT],
                                }
                            }
                        )

                messages.append({MESSAGE_ROLE: ROLE_USER, MESSAGE_CONTENT: tool_results})
            else:
                logger.debug(f'Agent finished: {response["stopReason"]}')
                break
        except Exception as e:
            logger.error(f'Error in agent loop: {e}')
            raise

    if turn >= max_turns:
        logger.warning(f'Reached max turns ({max_turns})')

    metrics_tracker.record_turn_count(turn)
    metrics_tracker.end_task()

    return messages
