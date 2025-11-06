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

    TEMP_SERVER_WRAPPER_MOCK_FILE=/tmp/mocks.json python mock_server_wrapper.py path/to/server.py
"""

import importlib.util
import json
import os
import sys
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
        print(f'Warning: Mock file not found: {mock_file}', file=sys.stderr)
        return {}

    try:
        with open(mock_path, 'r') as f:
            config = json.load(f)
            return config
    except Exception as e:
        print(f'Warning: Failed to load mock config: {e}', file=sys.stderr)
        return {}


def apply_mocks(mock_config: dict):
    """Apply mocks using the mock handler registry.

    Args:
        mock_config: Mock configuration dictionary
    """
    if not mock_config:
        return

    from .mocking import get_registry

    registry = get_registry()

    try:
        registry.patch_all(mock_config, fixtures_dir=None)
        print(f'Applied mocks for: {", ".join(mock_config.keys())}', file=sys.stderr)
    except Exception as e:
        print(f'Warning: Failed to apply mocks: {e}', file=sys.stderr)


def run_server(server_path: str, server_cwd: Optional[str] = None):
    """Import and run the MCP server module.

    Args:
        server_path: Path to server.py file
        server_cwd: Working directory for the server (optional, auto-detected if not provided)
    """
    server_file = Path(server_path)
    if not server_file.exists():
        print(f'Error: Server file not found: {server_path}', file=sys.stderr)
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
            print(f'Error: Server module {module_path} has no main() function', file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f'Error running server: {e}', file=sys.stderr)
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

    # TODO: Improve logging configuration for subprocess.
    # Current setup uses Python's last resort handler (stderr only, no formatting).
    # Consider: proper handler configuration, file output, integration with parent process logs.
    log_level = os.environ.get('TEMP_SERVER_WRAPPER_LOG_LEVEL', 'INFO').upper()
    mcp_logger = logging.getLogger('mcp')
    mcp_logger.setLevel(getattr(logging, log_level))

    mock_config = load_mock_config()

    if mock_config:
        apply_mocks(mock_config)

    run_server(args.server_path, args.server_cwd)


if __name__ == '__main__':
    main()
