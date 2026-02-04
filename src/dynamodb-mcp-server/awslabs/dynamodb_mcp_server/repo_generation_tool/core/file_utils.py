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

"""Common file operations and utilities for the DynamoDB code generation system.

This module provides shared functionality for file loading, path validation, and JSON parsing
that is used across loaders, validators, and other components.
"""

import json
from pathlib import Path
from typing import Any, Dict


class FileUtils:
    """Common utilities for file operations and JSON parsing."""

    @staticmethod
    def load_json_file(file_path: str, file_name: str = 'File') -> Dict[str, Any]:
        """Load JSON file with simple error handling (raises exceptions).

        Args:
            file_path: Path to JSON file
            file_name: Name for error messages (e.g., "Schema", "Usage Data")

        Returns:
            Parsed JSON data

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is invalid or other errors occur
        """
        file_obj = Path(file_path)
        if not file_obj.exists():
            raise FileNotFoundError(f'{file_name} file not found: {file_path}')

        try:
            with open(file_obj, encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f'Invalid JSON in {file_name} file: {e}')
        except Exception as e:
            raise ValueError(f'Error reading {file_name} file: {e}')

    @staticmethod
    def validate_and_resolve_path(
        file_path: Path,
        allow_absolute_paths: bool = True,
        base_dir: Path = None,
        file_name: str = 'File',
    ) -> Path:
        """Validate file path with security checks for path traversal.

        Args:
            file_path: Path to validate
            allow_absolute_paths: Whether to allow absolute paths
            base_dir: Base directory to restrict paths to (defaults to current working directory)
            file_name: Name for error messages (e.g., "Schema", "Usage Data")

        Returns:
            Resolved absolute path

        Raises:
            ValueError: If path validation fails
            FileNotFoundError: If file doesn't exist
        """
        # Security: Prevent path traversal attacks when used via MCP/LLM
        if not allow_absolute_paths and file_path.is_absolute():
            raise ValueError(
                f'Absolute paths are not allowed: {file_path}. '
                'Use relative paths only for security.'
            )

        # Resolve to absolute path and check for path traversal
        try:
            resolved_path = file_path.resolve()
        except (OSError, RuntimeError) as e:
            raise ValueError(f'Invalid {file_name} path: {file_path}') from e

        # Check for path traversal if base_dir is specified (before checking file existence)
        if base_dir is not None:
            base_dir = base_dir.resolve()

            try:
                # Check if resolved_path is within base_dir using relative_to
                resolved_path.relative_to(base_dir)
            except ValueError:
                raise ValueError(
                    f'Path traversal detected: {file_path} resolves outside allowed directory'
                )

        # Verify file exists (after path resolution and traversal checks)
        if not resolved_path.exists():
            raise FileNotFoundError(f'{file_name} file not found: {resolved_path}')

        # Verify it's a file, not a directory
        if not resolved_path.is_file():
            raise ValueError(f'{file_name} path must be a file, not a directory: {resolved_path}')

        return resolved_path
