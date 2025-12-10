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

"""Schema loading orchestration - coordinates validation and loading."""

import json
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_validator import (
    validate_schema_file,
)
from pathlib import Path
from typing import Any


class SchemaLoader:
    """Handles the loading workflow: validate -> load -> cache."""

    def __init__(self, schema_path: str, allow_absolute_paths: bool = True):
        """Initialize SchemaLoader with path validation.

        Args:
            schema_path: Path to the schema file
            allow_absolute_paths: If False, restricts to relative paths only (safer for MCP/LLM usage)

        Security Note:
            When exposing via MCP tools, set allow_absolute_paths=False to prevent
            path traversal attacks where LLMs could be tricked into reading sensitive files.
        """
        self.schema_path = Path(schema_path)
        self.allow_absolute_paths = allow_absolute_paths

    def _validate_path(self) -> Path:
        """Validate and resolve the schema path with security checks.

        Returns:
            Resolved absolute path to the schema file

        Raises:
            ValueError: If path validation fails (path traversal, absolute path when not allowed, etc.)
            FileNotFoundError: If the file doesn't exist
        """
        # Security: Prevent path traversal attacks when used via MCP/LLM
        if not self.allow_absolute_paths and self.schema_path.is_absolute():
            raise ValueError(
                f'Absolute paths are not allowed: {self.schema_path}. '
                'Use relative paths only for security.'
            )

        # Resolve to absolute path and check for path traversal
        try:
            resolved_path = self.schema_path.resolve()

            # If relative paths only, ensure it doesn't escape current directory
            if not self.allow_absolute_paths:
                cwd = Path.cwd().resolve()
                if not str(resolved_path).startswith(str(cwd)):
                    raise ValueError(
                        f'Path traversal detected: {self.schema_path} resolves outside current directory'
                    )

            # Verify file exists
            if not resolved_path.exists():
                raise FileNotFoundError(f'Schema file not found: {resolved_path}')

            # Verify it's a file, not a directory
            if not resolved_path.is_file():
                raise ValueError(f'Schema path must be a file, not a directory: {resolved_path}')

            return resolved_path

        except (OSError, RuntimeError) as e:
            raise ValueError(f'Invalid schema path: {self.schema_path}') from e

    def load_schema(self) -> dict[str, Any]:
        """Load and validate schema."""
        # Validate path with security checks
        validated_path = self._validate_path()

        # Use existing validator (don't duplicate logic)
        validation_result = validate_schema_file(str(validated_path))

        if not validation_result.is_valid:
            # Use existing error formatting
            from .schema_validator import SchemaValidator

            validator = SchemaValidator()
            validator.result = validation_result
            error_message = validator.format_validation_result()
            raise ValueError(f'Schema validation failed:\n{error_message}')

        # Load the validated schema
        with open(validated_path) as f:
            return json.load(f)

    @property
    def schema(self) -> dict[str, Any]:
        """Get the loaded schema."""
        return self.load_schema()

    @property
    def entities(self) -> dict[str, Any]:
        """Get entities from the schema."""
        return self.schema.get('entities', {})

    @property
    def table_config(self) -> dict[str, Any]:
        """Get table configuration from the schema."""
        return self.schema.get('table_config', {})
