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

"""Loader for structured usage data from JSON files."""

import logging
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.file_utils import (
    FileUtils,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.usage_data_formatter import (
    UsageDataFormatterInterface,
)
from pathlib import Path
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


class UsageDataLoader:
    """Loads realistic sample data from structured JSON files."""

    def __init__(
        self,
        usage_data_path: Optional[str] = None,
        formatter: Optional[UsageDataFormatterInterface] = None,
    ):
        """Initialize loader with optional usage data file path and formatter.

        Args:
            usage_data_path: Path to usage data JSON file
            formatter: Language-specific formatter for values
        """
        self.usage_data_path = usage_data_path
        self.usage_data = {}
        self.formatter = formatter

        if usage_data_path:
            usage_path = Path(usage_data_path)
            if usage_path.exists():
                self._load_usage_data()

    def get_sample_value_for_field(
        self,
        field_name: str,
        field_type: str,
        entity_name: Optional[str] = None,
        use_access_pattern_data: bool = False,
    ) -> Optional[str]:
        """Get a realistic sample value for a field based on the usage data.

        Lookup hierarchy:
        1. Entity-specific sample_data or access_pattern_data
        2. Return None if not found
        """
        if not self.formatter:
            return None

        # Try entity-specific data
        if entity_name:
            entities = self.usage_data.get('entities', {})
            if entity_name in entities:
                # Use access_pattern_data if requested, otherwise sample_data
                data_key = 'access_pattern_data' if use_access_pattern_data else 'sample_data'
                sample_data = entities[entity_name].get(data_key, {})
                if field_name in sample_data:
                    return self.formatter.format_value(sample_data[field_name], field_type)

        return None

    def get_update_value_for_field(
        self, field_name: str, field_type: str, entity_name: Optional[str] = None
    ) -> Optional[str]:
        """Get a realistic update value for a field.

        Lookup hierarchy:
        1. Entity-specific update_data
        2. Return None if not found
        """
        if not self.formatter:
            return None

        # Try entity-specific update data
        if entity_name:
            entities = self.usage_data.get('entities', {})
            if entity_name in entities:
                update_data = entities[entity_name].get('update_data', {})
                if field_name in update_data:
                    return self.formatter.format_value(update_data[field_name], field_type)

        return None

    def get_all_usage_data(self) -> Dict[str, Any]:
        """Get all loaded usage data."""
        return self.usage_data

    def has_data(self) -> bool:
        """Check if any usage data was successfully loaded."""
        return bool(self.usage_data)

    def get_entity_sample_data(self, entity_name: str) -> Dict[str, Any]:
        """Get all sample data for a specific entity."""
        entities = self.usage_data.get('entities', {})
        return entities.get(entity_name, {}).get('sample_data', {})

    def get_entity_update_data(self, entity_name: str) -> Dict[str, Any]:
        """Get all update data for a specific entity."""
        entities = self.usage_data.get('entities', {})
        return entities.get(entity_name, {}).get('update_data', {})

    def get_filter_value_for_param(
        self, param_name: str, param_type: str, entity_name: Optional[str] = None
    ) -> Optional[str]:
        """Get a filter value for a filter expression parameter.

        Lookup hierarchy:
        1. Entity-specific filter_values
        2. Return None if not found
        """
        if not self.formatter:
            return None

        if entity_name:
            entities = self.usage_data.get('entities', {})
            if entity_name in entities:
                filter_values = entities[entity_name].get('filter_values', {})
                if param_name in filter_values:
                    return self.formatter.format_value(filter_values[param_name], param_type)

        return None

    def _load_usage_data(self) -> None:
        """Load the usage data JSON file."""
        try:
            self.usage_data = FileUtils.load_json_file(self.usage_data_path, 'Usage data')
            logger.info(f'Successfully loaded usage data from {self.usage_data_path}')
        except (FileNotFoundError, ValueError) as e:
            logger.warning(f'Could not load usage data file {self.usage_data_path}: {e}')
            self.usage_data = {}
        except Exception as e:
            logger.warning(f'Unexpected error loading usage data file {self.usage_data_path}: {e}')
            self.usage_data = {}
