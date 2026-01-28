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

"""Interface for language-specific usage data formatting."""

from abc import ABC, abstractmethod
from typing import Any


class UsageDataFormatterInterface(ABC):
    """Interface for formatting usage data values into language-specific code."""

    @abstractmethod
    def format_value(self, value: Any, field_type: str) -> str:
        """Format a value according to the field type for target language code generation.

        Args:
            value: The raw value from usage data
            field_type: The field type (string, integer, decimal, boolean, array, object, uuid)

        Returns:
            Formatted string representation for the target language
        """
        pass
