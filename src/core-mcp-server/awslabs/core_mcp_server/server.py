# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
import argparse
import dotenv
import json
import loguru
import os
import platform
import subprocess
import sys
import traceback
from awslabs.core_mcp_server.available_servers import AVAILABLE_MCP_SERVERS
from awslabs.core_mcp_server.static import PROMPT_UNDERSTANDING
from mcp.server.fastmcp import FastMCP
from pathlib import Path
from typing import Dict, List, Optional, TypedDict


class ContentItem(TypedDict):
    """A TypedDict representing a single content item in an MCP response.

    This class defines the structure for content items used in MCP server responses.
    Each content item contains a type identifier and the actual content text.

    Attributes:
        type (str): The type identifier for the content (e.g., 'text', 'error')
        text (str): The actual content text
    """

    type: str
    text: str


class McpResponse(TypedDict, total=False):
    """A TypedDict representing an MCP server response.

    This class defines the structure for responses returned by MCP server tools.
    It supports optional fields through total=False, allowing responses to omit
    the isError field when not needed.

    Attributes:
        content (List[ContentItem]): List of content items in the response
        isError (bool, optional): Flag indicating if the response represents an error
    """

    content: List[ContentItem]
    isError: bool


logger = loguru.logger
dotenv.load_dotenv()


mcp = FastMCP(
    'mcp-core MCP server.  This is the starting point for all solutions created',
    dependencies=[
        'loguru',
    ],
)


@mcp.tool(name='prompt_understanding')
def get_prompt_understanding() -> str:
    """MCP-CORE Prompt Understanding.

    ALWAYS Use this tool first to understand the user's query and translate it into AWS expert advice.
    """
    return PROMPT_UNDERSTANDING


@mcp.tool(name='update')
def update_mcp_servers() -> McpResponse:
    """Update MCP servers.

    This tool updates all MCP servers in the configuration to ensure they are up-to-date.
    It will add any missing servers and update existing ones with the latest configuration.
    """
    try:
        logger.info('Running MCP server update')
        ensure_mcp_servers_installed()
        return {
            'content': [
                {
                    'type': 'text',
                    'text': 'MCP servers updated successfully! All servers are now up-to-date with the latest configuration.',
                }
            ]
        }
    except Exception as e:
        logger.error(f'Error updating MCP servers: {e}')
        logger.error(f'Stack trace: {traceback.format_exc()}')
        return {
            'content': [{'type': 'text', 'text': f'Error updating MCP servers: {e}'}],
            'isError': True,
        }


def has_nodejs() -> bool:
    """Check if Node.js is installed."""
    try:
        subprocess.run(['node', '--version'], check=True, capture_output=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def has_uv() -> bool:
    """Check if uv is installed."""
    try:
        subprocess.run(['uv', '--version'], check=True, capture_output=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def get_mcp_config_path() -> Path:
    """Get the path to the MCP config file from environment variables.

    This function checks environment variables to determine the MCP config file path.
    It requires that one of the environment variables be set.

    Returns:
        Path to the MCP config file

    Raises:
        ValueError: If no MCP config path can be determined from environment variables
    """
    # Check environment variables for MCP config path
    env_vars_to_check = ['MCP_CONFIG_PATH', 'CLINE_MCP_SETTINGS_PATH', 'MCP_SETTINGS_PATH']

    for var in env_vars_to_check:
        if var in os.environ and os.path.exists(os.environ[var]):
            logger.info(f'Found MCP config path in environment variable {var}: {os.environ[var]}')
            return Path(os.environ[var])

    # Try to get the config path from the parent process (the MCP client)
    try:
        # Get the parent process ID
        parent_pid = os.getppid()

        # On macOS/Linux, check the process environment
        if platform.system() != 'Windows':
            # Use ps command to get environment variables of parent process
            cmd = ['ps', 'e', '-p', str(parent_pid)]
            result = subprocess.run(cmd, capture_output=True, text=True)

            # Look for config path in the output
            for line in result.stdout.splitlines():
                for var in env_vars_to_check:
                    if f'{var}=' in line:
                        path_start = line.find(f'{var}=') + len(f'{var}=')
                        path_end = line.find(' ', path_start)
                        if path_end == -1:
                            path_end = len(line)
                        config_path = line[path_start:path_end]
                        if os.path.exists(config_path):
                            logger.info(
                                f'Found MCP config path in parent process environment: {config_path}'
                            )
                            return Path(config_path)
    except Exception as e:
        logger.warning(f'Error getting parent process environment: {e}')

    # If we couldn't determine the config path, raise an error
    raise ValueError(
        'No MCP config path found in environment variables. Please set MCP_CONFIG_PATH, CLAUDE_CONFIG_PATH, or CLINE_MCP_SETTINGS_PATH.'
    )


def install_to_mcp_config(
    name: str, cmd: str, args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None
) -> None:
    """Install an MCP server to the MCP config file."""
    config_path = get_mcp_config_path()

    # Create config directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing config or create new one
    if config_path.exists():
        with open(config_path, 'r') as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                config = {}
    else:
        config = {}

    # Ensure mcpServers exists
    if 'mcpServers' not in config:
        config['mcpServers'] = {}

    # Create new server config
    new_server = {
        'command': cmd,
        'args': args or [],
    }

    # Add environment variables if provided
    if env:
        new_server['env'] = env

    # Add server to config
    config['mcpServers'][name] = new_server

    # Write config back to file
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


@mcp.tool(name='install_awslabs_mcp_server')
def install_repo_mcp_server(
    name: str, args: Optional[List[str]] = None, env: Optional[List[str]] = None
) -> McpResponse:
    """Install an MCP server via uvx.

    Args:
        name: The package name of the MCP server
        args: The arguments to pass along
        env: The environment variables to set, delimited by =
    """
    # Convert env list to dict
    env_dict = {}
    if env:
        for item in env:
            if '=' in item:
                key, value = item.split('=', 1)
                env_dict[key] = value

    # Check if Node.js is installed
    if not has_nodejs():
        return {
            'content': [{'type': 'text', 'text': 'Node.js is not installed, please install it!'}],
            'isError': True,
        }

    # Check if uv is installed
    if not has_uv():
        return {
            'content': [
                {
                    'type': 'text',
                    'text': 'Python uv is not installed, please install it! Tell users to go to https://docs.astral.sh/',
                }
            ],
            'isError': True,
        }

    # Install via uvx
    install_to_mcp_config(name, 'uvx', [name] + (args or []), env_dict)
    return {
        'content': [
            {
                'type': 'text',
                'text': 'Installed MCP server via uvx successfully! Tell the user to restart the app',
            }
        ]
    }


def ensure_mcp_servers_installed() -> None:
    """Ensure all available MCP servers are installed in the MCP config."""
    try:
        # Get the MCP config path
        config_path = get_mcp_config_path()
        logger.info(f'Using MCP config path: {config_path}')

        # Read existing config
        if config_path.exists():
            logger.info('Config file exists, reading content')
            with open(config_path, 'r') as f:
                try:
                    config = json.load(f)
                    logger.info(
                        f'Successfully loaded config file with {len(config.get("mcpServers", {}))} servers'
                    )
                except json.JSONDecodeError as e:
                    logger.error(f'Error parsing config file: {e}')
                    config = {}
        else:
            logger.warning('Config file does not exist, creating new config')
            config = {}

        # Ensure mcpServers exists
        if 'mcpServers' not in config:
            logger.info('mcpServers key not found in config, adding it')
            config['mcpServers'] = {}

        # Track if changes were made
        changes_made = False

        # Log available servers
        logger.info(f'Checking {len(AVAILABLE_MCP_SERVERS)} available servers')

        # Check each available server
        for server_name, server_config in AVAILABLE_MCP_SERVERS.items():
            # Always update the server config to ensure we're using the latest
            if server_name not in config['mcpServers']:
                logger.info(f'Adding missing MCP server: {server_name}')
                changes_made = True
            else:
                logger.info(f'Updating existing MCP server: {server_name}')
                changes_made = True

            # Add or update server in config
            config['mcpServers'][server_name] = server_config

        # Always write config back to file to trigger reload
        logger.info(f'Writing config to file: {config_path}')
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                logger.info('Successfully wrote config file')
        except Exception as e:
            logger.error(f'Error writing config file: {e}')
            raise

        if changes_made:
            logger.info('Added missing MCP servers to config')
        else:
            logger.info('All MCP servers already in config, saved file to trigger reload')

        logger.info('MCP server installation check completed')
    except Exception as e:
        logger.error(f'Error ensuring MCP servers are installed: {e}')
        # Print stack trace for better debugging
        import traceback

        logger.error(f'Stack trace: {traceback.format_exc()}')


def main() -> None:
    """Run the MCP server."""
    parser = argparse.ArgumentParser(
        description='A Model Context Protocol (MCP) server for mcp-core'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')
    parser.add_argument(
        '--skip-server-check', action='store_true', help='Skip checking for missing MCP servers'
    )
    parser.add_argument('--debug-servers', action='store_true', help='Debug server installation')

    args = parser.parse_args()

    # Set up logging
    logger.remove()
    logger.add(sys.stderr, level='DEBUG')

    # Print environment variables for debugging
    logger.debug(f'Environment variables: MCP_CONFIG_PATH={os.environ.get("MCP_CONFIG_PATH")}')

    # Print available servers for debugging
    logger.debug(f'Available servers: {list(AVAILABLE_MCP_SERVERS.keys())}')

    # Check for missing MCP servers
    if not args.skip_server_check:
        logger.info('Running server installation check')
        ensure_mcp_servers_installed()
    else:
        logger.info('Skipping server installation check')

    # Debug server installation if requested
    if args.debug_servers:
        logger.info('Running server installation check in debug mode')
        ensure_mcp_servers_installed()
        return

    # Always run server installation check before starting the server
    # This ensures that the server installation check is run even if --skip-server-check is specified
    # This is necessary because the server installation check is not run when the server is restarted
    try:
        logger.info('Running server installation check before starting server')
        ensure_mcp_servers_installed()
    except Exception as e:
        logger.error(f'Error running server installation check: {e}')
        logger.error(f'Stack trace: {traceback.format_exc()}')
        logger.warning('Continuing with server startup despite error in server installation check')

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':
    main()
