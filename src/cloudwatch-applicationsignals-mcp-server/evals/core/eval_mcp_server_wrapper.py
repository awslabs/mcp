#!/usr/bin/env python3
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

"""Mock server wrapper for MCP evaluation.

This wrapper applies mocks before starting the MCP server subprocess.
It reads mock configuration from a temporary file and patches libraries
(boto3, etc.) before importing and running the actual server.

Usage:
    Set TEMP_SERVER_WRAPPER_MOCK_FILE environment variable to path of mock config JSON,
    then run this script with the server module path as argument:

    TEMP_SERVER_WRAPPER_MOCK_FILE=/tmp/mocks.json python eval_mcp_server_wrapper.py path/to/server.py
"""

import importlib.util
import json
import os
import sys
from loguru import logger
from pathlib import Path
from typing import Optional


def load_mock_config() -> dict:
    """Load mock configuration from file specified in environment.

    Returns:
        Mock configuration dictionary, or empty dict if no mocks
    """
    mock_file = os.environ.get('TEMP_SERVER_WRAPPER_MOCK_FILE')
    if not mock_file:
        return {}

    mock_path = Path(mock_file)
    if not mock_path.exists():
        logger.warning(f'Mock file not found: {mock_file}')
        return {}

    try:
        with open(mock_path, 'r') as f:
            config = json.load(f)
            return config
    except Exception as e:
        logger.warning(f'Failed to load mock config: {e}')
        return {}


def apply_mocks(mock_config: dict):
    """Apply mocks using the mock handler registry.

    Args:
        mock_config: Mock configuration dictionary
    """
    if not mock_config:
        return

    from .mcp_dependency_mocking_handler import get_registry

    registry = get_registry()

    try:
        registry.patch_all(mock_config)
        logger.debug(f'Applied mocks for: {", ".join(mock_config.keys())}')
    except Exception as e:
        logger.warning(f'Failed to apply mocks: {e}')


def run_server(server_path: str, server_cwd: Optional[str] = None):
    """Import and run the MCP server module.

    Args:
        server_path: Path to server.py file
        server_cwd: Working directory for the server (optional, auto-detected if not provided)
    """
    server_file = Path(server_path)
    if not server_file.exists():
        logger.error(f'Server file not found: {server_path}')
        sys.exit(1)

    server_dir = server_file.parent
    package_name = server_dir.name
    namespace_dir = server_dir.parent
    namespace_name = namespace_dir.name

    if server_cwd:
        working_dir = Path(server_cwd)
    else:
        working_dir = namespace_dir.parent

    module_path = f'{namespace_name}.{package_name}.server'

    os.chdir(working_dir)
    if str(working_dir) not in sys.path:
        sys.path.insert(0, str(working_dir))

    try:
        module = importlib.import_module(module_path)

        if hasattr(module, 'main'):
            module.main()
        else:
            logger.error(f'Server module {module_path} has no main() function')
            sys.exit(1)
    except Exception as e:
        logger.error(f'Error running server: {e}')
        import traceback

        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    import argparse
    import logging

    parser = argparse.ArgumentParser(description='MCP server wrapper with mocking support')
    parser.add_argument('server_path', help='Path to MCP server.py file')
    parser.add_argument('--server-cwd', help='Working directory for the server', default=None)

    args = parser.parse_args()

    # TODO: Consolidate logging setup across wrapper, server subprocess, and main process
    # Configure loguru logger for wrapper diagnostics
    logger.remove()
    loguru_level = os.environ.get('TEMP_SERVER_WRAPPER_LOGURU_LEVEL', 'INFO').upper()
    logger.add(sys.stderr, level=loguru_level)

    # Configure Python logging for MCP server
    log_level = os.environ.get('TEMP_SERVER_WRAPPER_LOG_LEVEL', 'INFO').upper()
    mcp_logger = logging.getLogger('mcp')
    mcp_logger.setLevel(getattr(logging, log_level))

    mock_config = load_mock_config()

    if mock_config:
        apply_mocks(mock_config)

    run_server(args.server_path, args.server_cwd)


if __name__ == '__main__':
    main()
