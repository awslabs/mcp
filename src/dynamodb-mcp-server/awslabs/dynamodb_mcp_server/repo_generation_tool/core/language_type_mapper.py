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

"""Abstract base class for language-specific type mappings."""

from abc import ABC, abstractmethod
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    FieldType,
    ParameterType,
    ReturnType,
)


class LanguageTypeMappingInterface(ABC):
    """Abstract base class that enforces required type mappings for each language."""

    @property
    @abstractmethod
    def field_type_mappings(self) -> dict[str, str]:
        """Must provide mappings for all FieldType enum values."""
        pass

    @property
    @abstractmethod
    def return_type_mappings(self) -> dict[str, str]:
        """Must provide mappings for all ReturnType enum values."""
        pass

    @property
    @abstractmethod
    def parameter_type_mappings(self) -> dict[str, str]:
        """Must provide mappings for all ParameterType enum values."""
        pass

    @property
    def all_mappings(self) -> dict[str, str]:
        """Combines all mappings into single dictionary."""
        return {
            **self.field_type_mappings,
            **self.return_type_mappings,
            **self.parameter_type_mappings,
        }

    def validate_completeness(self) -> None:
        """Validates that all required enum values are mapped."""
        # Check field types
        required_field_types = {ft.value for ft in FieldType}
        provided_field_types = set(self.field_type_mappings.keys())
        missing_field_types = required_field_types - provided_field_types

        if missing_field_types:
            raise ValueError(
                f'Missing field type mappings for {self.__class__.__name__}: {missing_field_types}'
            )

        # Check return types
        required_return_types = {rt.value for rt in ReturnType}
        provided_return_types = set(self.return_type_mappings.keys())
        missing_return_types = required_return_types - provided_return_types

        if missing_return_types:
            raise ValueError(
                f'Missing return type mappings for {self.__class__.__name__}: {missing_return_types}'
            )

        # Check parameter types
        required_param_types = {pt.value for pt in ParameterType}
        provided_param_types = set(self.parameter_type_mappings.keys())
        missing_param_types = required_param_types - provided_param_types

        if missing_param_types:
            raise ValueError(
                f'Missing parameter type mappings for {self.__class__.__name__}: {missing_param_types}'
            )

    def get_language_name(self) -> str:
        """Get the language name from the class name (e.g., PythonTypeMappings -> python)."""
        class_name = self.__class__.__name__
        if class_name.endswith('TypeMappings'):
            return class_name[:-12].lower()  # Remove 'TypeMappings' suffix
        return class_name.lower()
