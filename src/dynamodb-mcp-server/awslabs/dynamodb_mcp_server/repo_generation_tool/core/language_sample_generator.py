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

"""Abstract interface for language-specific sample value generation.

This module defines the contract that all language-specific sample generators
must implement to ensure consistent behavior across different programming languages.
"""

from abc import ABC, abstractmethod
from typing import Any


class LanguageSampleGeneratorInterface(ABC):
    """Abstract interface for language-specific sample value generation."""

    @abstractmethod
    def get_sample_value(self, field_type: str, field_name: str, **kwargs) -> str:
        """Generate sample value for field type.

        Args:
            field_type: The type of field (string, integer, decimal, etc.)
            field_name: The name of the field (used for context-specific generation)
            **kwargs: Additional parameters (e.g., item_type for arrays)

        Returns:
            Language-specific sample value as string
        """
        pass

    @abstractmethod
    def get_update_value(self, field_type: str, field_name: str, **kwargs) -> str:
        """Generate update value for field type.

        Args:
            field_type: The type of field (string, integer, decimal, etc.)
            field_name: The name of the field (used for context-specific generation)
            **kwargs: Additional parameters (e.g., item_type for arrays)

        Returns:
            Language-specific update value as string
        """
        pass

    @abstractmethod
    def get_default_values(self) -> dict[str, str]:
        """Get default sample values for all field types.

        Returns:
            Dictionary mapping field types to default sample values
        """
        pass

    @abstractmethod
    def get_default_update_values(self) -> dict[str, str]:
        """Get default update values for all field types.

        Returns:
            Dictionary mapping field types to default update values
        """
        pass

    @abstractmethod
    def get_parameter_value(
        self, param: dict[str, Any], entity_name: str, all_entities: dict
    ) -> str | None:
        """Generate parameter value for access pattern testing.

        This method generates language-specific code for parameter values in usage examples.
        The generated code should reference created entities and their fields.

        Args:
            param: Parameter definition with 'name' and 'type'
            entity_name: Name of the entity this access pattern belongs to
            all_entities: Dictionary of all entity configurations from schema

        Returns:
            Language-specific string representation of the parameter value, or None if
            parameter should be skipped (e.g., phantom parameters without fallback generation)

        Example (Python):
            For param={'name': 'user_id', 'type': 'string'}, entity_name='User'
            Returns: 'created_entities["User"].user_id'
        """
        pass
