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

"""Python-specific usage data formatter."""

import json
import logging
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.usage_data_formatter import (
    UsageDataFormatterInterface,
)
from typing import Any


logger = logging.getLogger(__name__)


class PythonUsageDataFormatter(UsageDataFormatterInterface):
    """Formats usage data values into Python code."""

    def format_value(self, value: Any, field_type: str) -> str:
        """Format a value according to the field type for Python code generation."""
        if field_type == 'string':
            return self._format_string_value(value)
        elif field_type == 'integer':
            return self._format_integer_value(value)
        elif field_type == 'decimal':
            return self._format_decimal_value(value)
        elif field_type == 'boolean':
            return self._format_boolean_value(value)
        elif field_type == 'array':
            return self._format_array_value(value)
        elif field_type == 'object':
            return self._format_object_value(value)
        elif field_type == 'uuid':
            return self._format_string_value(value)
        else:
            logger.warning(f"Unknown field type '{field_type}', treating as string")
            return self._format_string_value(value)

    def _escape_string(self, value: str) -> str:
        """Escape backslashes and quotes in string."""
        return value.replace('\\', '\\\\').replace('"', '\\"')

    def _format_string_value(self, value: Any) -> str:
        """Format value as Python string literal."""
        return f'"{self._escape_string(str(value))}"'

    def _format_integer_value(self, value: Any) -> str:
        """Format value as Python integer."""
        if isinstance(value, (int, float)):
            return str(int(value))
        try:
            return str(int(float(str(value))))
        except (ValueError, TypeError):
            return '42'

    def _format_decimal_value(self, value: Any) -> str:
        """Format value as Python Decimal."""
        if isinstance(value, (int, float)):
            return f'Decimal("{value}")'
        try:
            float_val = float(str(value))
            return f'Decimal("{float_val}")'
        except (ValueError, TypeError):
            return 'Decimal("3.14")'

    def _format_boolean_value(self, value: Any) -> str:
        """Format value as Python boolean."""
        if isinstance(value, bool):
            return 'True' if value else 'False'
        if isinstance(value, str):
            return 'True' if value.lower() in ('true', 'yes', '1', 'on') else 'False'
        return 'True' if value else 'False'

    def _format_array_value(self, value: Any) -> str:
        """Format value as Python list."""
        if isinstance(value, list):
            formatted_items = []
            for item in value:
                if isinstance(item, str):
                    formatted_items.append(f'"{self._escape_string(item)}"')
                elif isinstance(item, bool):
                    formatted_items.append('True' if item else 'False')
                elif isinstance(item, dict):
                    formatted_items.append(self._format_dict_with_decimals(item))
                elif isinstance(item, float):
                    formatted_items.append(f'Decimal("{item}")')
                else:
                    formatted_items.append(str(item))
            return f'[{", ".join(formatted_items)}]'
        else:
            return f'[{self._format_string_value(value)}]'

    def _format_object_value(self, value: Any) -> str:
        """Format value as Python dictionary (JSON object)."""
        if isinstance(value, dict):
            return self._format_dict_with_decimals(value)
        elif isinstance(value, str):
            try:
                parsed = json.loads(value)
                return self._format_dict_with_decimals(parsed)
            except json.JSONDecodeError:
                return f'{{"value": "{self._escape_string(value)}"}}'
        else:
            return f'{{"value": "{self._escape_string(str(value))}"}}'

    def _format_dict_with_decimals(self, d: dict) -> str:
        """Format dictionary converting float values to Decimal."""
        formatted_pairs = []
        for key, val in d.items():
            escaped_key = self._escape_string(key)
            if isinstance(val, str):
                formatted_pairs.append(f'"{escaped_key}": "{self._escape_string(val)}"')
            elif isinstance(val, bool):
                formatted_pairs.append(f'"{escaped_key}": {"True" if val else "False"}')
            elif isinstance(val, float):
                formatted_pairs.append(f'"{escaped_key}": Decimal("{val}")')
            elif isinstance(val, int):
                formatted_pairs.append(f'"{escaped_key}": {val}')
            elif isinstance(val, dict):
                formatted_pairs.append(f'"{escaped_key}": {self._format_dict_with_decimals(val)}')
            elif isinstance(val, list):
                formatted_pairs.append(f'"{escaped_key}": {self._format_array_value(val)}')
            elif val is None:
                formatted_pairs.append(f'"{escaped_key}": None')
            else:
                formatted_pairs.append(f'"{escaped_key}": {json.dumps(val)}')
        return '{' + ', '.join(formatted_pairs) + '}'
