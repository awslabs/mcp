"""Agent orchestration for MCP tool evaluation.

Provides multi-turn conversation loop and tool execution.
"""

import time
from .constants import DEFAULT_MAX_TURNS, DEFAULT_MODEL_ID, DEFAULT_TEMPERATURE
from .file_tools import get_file_tools
from .mcp_client import convert_mcp_tools_to_bedrock
from .metrics import MetricsTracker
from loguru import logger
from mcp import ClientSession
from pathlib import Path
from typing import Any, Dict, List


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
        if tool_name == 'list_files':
            dir_path = project_root / tool_input['path']
            files = [f.name for f in dir_path.iterdir()]
            result = {'content': [{'text': '\n'.join(files)}]}
        elif tool_name == 'read_file':
            file_path = project_root / tool_input['path']
            content = file_path.read_text()
            result = {'content': [{'text': content}]}
        elif tool_name == 'write_file':
            file_path = project_root / tool_input['path']
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(tool_input['content'])
            result = {'content': [{'text': f'Successfully wrote to {tool_input["path"]}'}]}
        else:
            mcp_result = await session.call_tool(tool_name, tool_input)
            result = {'content': [{'text': str(mcp_result.content)}]}

        return result
    except Exception as e:
        logger.error(f'Tool execution failed: {e}')
        success = False
        error = str(e)
        return {'content': [{'text': f'Error: {str(e)}'}], 'status': 'error'}
    finally:
        duration = time.time() - start
        params_to_log = {k: v for k, v in tool_input.items() if k != 'toolUseId'}
        metrics_tracker.record_tool_call(tool_name, params_to_log, duration, success, error)


async def run_agent_loop(
    bedrock_client,
    session: ClientSession,
    prompt: str,
    project_root: Path,
    mcp_tools,
    metrics_tracker: MetricsTracker,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> List[Dict[str, Any]]:
    """Run the agent loop for task completion.

    Args:
        bedrock_client: Boto3 Bedrock Runtime client
        session: MCP client session
        prompt: Task prompt for the agent
        project_root: Root directory for file operations
        mcp_tools: List of MCP tools from server
        metrics_tracker: Metrics tracker instance
        max_turns: Maximum number of conversation turns

    Returns:
        List of conversation messages
    """
    metrics_tracker.start_task()

    logger.debug('Sending prompt to Claude...')

    bedrock_mcp_tools = convert_mcp_tools_to_bedrock(mcp_tools)
    file_tools = get_file_tools()
    all_tools = bedrock_mcp_tools + file_tools

    toolConfig = {'tools': all_tools}
    logger.debug(f'Configured {len(all_tools)} tools')

    messages = [{'role': 'user', 'content': [{'text': prompt}]}]

    turn = 0

    while turn < max_turns:
        turn += 1
        logger.debug(f'=== Turn {turn}/{max_turns} ===')

        start = time.time()

        try:
            response = bedrock_client.converse(
                modelId=DEFAULT_MODEL_ID,
                messages=messages,
                toolConfig=toolConfig,
                inferenceConfig={'temperature': DEFAULT_TEMPERATURE},
            )

            elapsed = time.time() - start
            logger.debug(f'Claude responded in {elapsed:.2f}s')
            logger.debug(f'Stop reason: {response["stopReason"]}')

            messages.append(
                {'role': 'assistant', 'content': response['output']['message']['content']}
            )

            if response['stopReason'] == 'end_turn':
                logger.debug('Claude finished!')
                break
            elif response['stopReason'] == 'tool_use':
                tool_results = []

                for content_block in response['output']['message']['content']:
                    if 'toolUse' in content_block:
                        tool_use = content_block['toolUse']
                        tool_name = tool_use['name']
                        tool_input = tool_use['input']
                        tool_use_id = tool_use['toolUseId']

                        logger.debug(f'Tool requested: {tool_name}')

                        tool_input['toolUseId'] = tool_use_id
                        result = await execute_tool(
                            tool_name, tool_input, session, project_root, metrics_tracker
                        )

                        tool_results.append(
                            {
                                'toolResult': {
                                    'toolUseId': tool_use_id,
                                    'content': result['content'],
                                }
                            }
                        )

                messages.append({'role': 'user', 'content': tool_results})
            else:
                logger.warning(f'Unexpected stop reason: {response["stopReason"]}')
                break
        except Exception as e:
            logger.error(f'Error in agent loop: {e}')
            raise

    if turn >= max_turns:
        logger.warning(f'Reached max turns ({max_turns})')

    metrics_tracker.end_task()

    return messages
