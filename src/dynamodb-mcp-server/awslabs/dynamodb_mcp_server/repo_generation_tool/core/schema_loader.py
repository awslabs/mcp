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

from awslabs.dynamodb_mcp_server.repo_generation_tool.core.file_utils import (
    FileUtils,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_validator import (
    validate_schema_file,
)
from pathlib import Path
from typing import Any


class SchemaLoader:
    """Handles the loading workflow: validate -> load -> cache."""

    def __init__(self, schema_path: str):
        """Initialize SchemaLoader.

        Args:
            schema_path: Path to the schema file
        """
        self.schema_path = Path(schema_path).resolve()

    def load_schema(self) -> dict[str, Any]:
        """Load and validate schema."""
        validated_path = self.schema_path

        # Use existing validator (don't duplicate logic)
        validation_result = validate_schema_file(str(validated_path))

        if not validation_result.is_valid:
            # Use existing error formatting
            from .schema_validator import SchemaValidator

            validator = SchemaValidator()
            validator.result = validation_result
            error_message = validator.format_validation_result()
            raise ValueError(f'Schema validation failed:\n{error_message}')

        # Load the validated schema using shared utility
        return FileUtils.load_json_file(str(validated_path), 'Schema')

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
