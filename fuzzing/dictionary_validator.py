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

"""Dictionary format validation for OSS-Fuzz integration.

This module provides the DictionaryValidator class for validating libFuzzer
dictionary format compliance. Dictionaries are used by libFuzzer to generate
more effective inputs for structured data formats.

The libFuzzer dictionary format requires:
- Empty lines are allowed
- Lines starting with '#' are comments
- Token lines must be: "token" or name="token"

Example usage:
    ```python
    from fuzzing.dictionary_validator import DictionaryValidator

    validator = DictionaryValidator()

    # Validate a single line
    is_valid, error = validator.validate_line('"SELECT"')

    # Validate an entire dictionary file
    errors = validator.validate_file(Path('fuzzing/dictionaries/sql.dict'))
    ```
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ValidationError:
    """Represents a validation error in a dictionary file.

    Attributes:
        line_number: The 1-indexed line number where the error occurred
        line_content: The content of the invalid line
        error_message: Description of what's wrong with the line
    """

    line_number: int
    line_content: str
    error_message: str

    def __str__(self) -> str:
        """Return a human-readable error message."""
        return f'Line {self.line_number}: {self.error_message}\n  Content: {self.line_content!r}'


class DictionaryValidator:
    r"""Validates libFuzzer dictionary format compliance.

    The libFuzzer dictionary format allows:
    - Empty lines (ignored)
    - Comment lines starting with '#' (ignored)
    - Token lines in format: "token" or name="token"

    Token strings are enclosed in double quotes and may contain:
    - Regular characters
    - Escape sequences: \\, \", \\xNN (hex byte)

    Example valid dictionary:
        ```
        # This is a comment
        "SELECT"

        keyword = 'FROM'
        '\\x00'
        ```
    """

    # Regex pattern for valid token line: "token" or name="token"
    # Token content can include escaped characters
    # libFuzzer supports: \\ \" \' \n \r \t \xNN
    _TOKEN_PATTERN = re.compile(
        r'^'
        r'(?:([a-zA-Z_][a-zA-Z0-9_]*)=)?'  # Optional name= prefix
        r'"'  # Opening quote
        r'('  # Token content group
        r'(?:'
        r'[^"\\]'  # Regular character (not quote or backslash)
        r"|\\[\\\"'nrt`]"  # Escaped chars: \ " ' n r t `
        r'|\\x[0-9a-fA-F]{2}'  # Hex escape sequence
        r')*'
        r')'
        r'"'  # Closing quote
        r'$'
    )

    def validate_line(self, line: str) -> tuple[bool, Optional[str]]:
        """Validate a single dictionary line.

        Args:
            line: A single line from a dictionary file (without newline)

        Returns:
            A tuple of (is_valid, error_message).
            If valid, error_message is None.
            If invalid, error_message describes the issue.
        """
        # Strip trailing whitespace but preserve leading whitespace for error detection
        stripped = line.rstrip()

        # Empty lines are valid
        if not stripped:
            return True, None

        # Comment lines are valid
        if stripped.startswith('#'):
            return True, None

        # Check for leading whitespace (not allowed for token lines)
        if stripped != line.rstrip() or (line and line[0].isspace()):
            if line.lstrip().startswith('#'):
                # Indented comments are still valid
                return True, None
            # Leading whitespace on token lines is suspicious but we'll allow it
            # after stripping for the pattern match

        # Validate token format
        stripped_full = stripped.strip()
        if self._TOKEN_PATTERN.match(stripped_full):
            return True, None

        # Provide specific error messages for common issues
        if '"' not in stripped_full:
            return False, 'Token must be enclosed in double quotes'

        if stripped_full.count('"') == 1:
            return False, 'Token has unmatched quote'

        if stripped_full.startswith('"') and not stripped_full.endswith('"'):
            return False, 'Token must end with closing double quote'

        if not stripped_full.startswith('"') and '="' not in stripped_full:
            return False, 'Token must start with quote or be in name="token" format'

        # Check for invalid escape sequences
        if '\\' in stripped_full:
            # Find content between quotes
            quote_start = stripped_full.find('"')
            quote_end = stripped_full.rfind('"')
            if quote_start != -1 and quote_end > quote_start:
                content = stripped_full[quote_start + 1 : quote_end]
                # Check for invalid escapes
                i = 0
                while i < len(content):
                    if content[i] == '\\':
                        if i + 1 >= len(content):
                            return False, 'Incomplete escape sequence at end of token'
                        next_char = content[i + 1]
                        # Valid single-char escapes: \ " ' n r t `
                        if next_char in ('\\', '"', "'", 'n', 'r', 't', '`'):
                            i += 2
                        elif next_char == 'x':
                            if i + 3 >= len(content):
                                return False, 'Incomplete hex escape sequence'
                            hex_chars = content[i + 2 : i + 4]
                            if not all(c in '0123456789abcdefABCDEF' for c in hex_chars):
                                return False, f'Invalid hex escape sequence: \\x{hex_chars}'
                            i += 4
                        else:
                            return False, f'Invalid escape sequence: \\{next_char}'
                    else:
                        i += 1

        return False, 'Invalid dictionary line format'

    def validate_file(self, file_path: Path) -> list[ValidationError]:
        """Validate an entire dictionary file.

        Args:
            file_path: Path to the dictionary file to validate

        Returns:
            A list of ValidationError objects for any invalid lines.
            Empty list means the file is valid.

        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If the file can't be read
        """
        errors: list[ValidationError] = []

        with open(file_path, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, start=1):
                # Remove newline for validation
                line_content = line.rstrip('\n\r')
                is_valid, error_message = self.validate_line(line_content)

                if not is_valid:
                    errors.append(
                        ValidationError(
                            line_number=line_number,
                            line_content=line_content,
                            error_message=error_message or 'Unknown error',
                        )
                    )

        return errors

    def validate_directory(self, directory: Path) -> dict[Path, list[ValidationError]]:
        """Validate all dictionary files in a directory.

        Args:
            directory: Path to directory containing .dict files

        Returns:
            A dictionary mapping file paths to their validation errors.
            Files with no errors are not included in the result.

        Raises:
            NotADirectoryError: If the path is not a directory
        """
        if not directory.is_dir():
            raise NotADirectoryError(f'{directory} is not a directory')

        results: dict[Path, list[ValidationError]] = {}

        for dict_file in directory.glob('*.dict'):
            errors = self.validate_file(dict_file)
            if errors:
                results[dict_file] = errors

        return results

    def is_valid_token(self, token: str) -> bool:
        """Check if a string is a valid dictionary token (without quotes).

        This validates the content that would go inside the quotes.

        Args:
            token: The token content (without surrounding quotes)

        Returns:
            True if the token content is valid, False otherwise
        """
        # Wrap in quotes and validate as a line
        quoted = f'"{token}"'
        is_valid, _ = self.validate_line(quoted)
        return is_valid

    def format_token(self, value: str, name: Optional[str] = None) -> str:
        """Format a value as a valid dictionary token line.

        Escapes special characters as needed.

        Args:
            value: The token value to format
            name: Optional name for the token (name="value" format)

        Returns:
            A properly formatted dictionary line
        """
        # Escape backslashes first, then quotes
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')

        if name:
            return f'{name}="{escaped}"'
        return f'"{escaped}"'
