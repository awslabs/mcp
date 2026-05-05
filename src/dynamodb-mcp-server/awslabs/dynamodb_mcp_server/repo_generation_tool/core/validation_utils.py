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

"""Validation models for schema validation.

This module defines dataclasses for representing validation errors and results.
"""

from dataclasses import dataclass


@dataclass
class ValidationError:
    """Represents a validation error with context and suggestions."""

    path: str  # e.g., "entities.UserProfile.access_patterns[0].return_type"
    message: str  # Clear error description
    suggestion: str  # Helpful suggestion for fixing
    severity: str = 'error'  # "error" | "warning"


@dataclass
class ValidationResult:
    """Result of schema validation."""

    is_valid: bool
    errors: list[ValidationError]
    warnings: list[ValidationError]
    extracted_entities: set[str] | None = None
    extracted_entity_fields: dict[str, set[str]] | None = None

    def add_error(self, path: str, message: str, suggestion: str = '') -> None:
        """Add an error to the validation result."""
        self.errors.append(ValidationError(path, message, suggestion, 'error'))
        self.is_valid = False

    def add_errors(self, errors: list[ValidationError]) -> None:
        """Add multiple errors to the validation result."""
        if errors:
            self.errors.extend(errors)
            self.is_valid = False

    def add_warning(self, path: str, message: str, suggestion: str = '') -> None:
        """Add a warning to the validation result."""
        self.warnings.append(ValidationError(path, message, suggestion, 'warning'))

    def store_entity_info(self, entities: set[str], entity_fields: dict[str, set[str]]) -> None:
        """Store extracted entity information for reuse in other validations."""
        self.extracted_entities = entities
        self.extracted_entity_fields = entity_fields

    def format(self, success_message: str, failure_prefix: str) -> str:
        """Format validation result as human-readable string.

        Args:
            success_message: Message to show on success
            failure_prefix: Prefix for failure message

        Returns:
            Formatted string representation
        """
        if self.is_valid and not self.warnings:
            return f'✅ {success_message}'

        output = []

        if self.errors:
            output.append(f'❌ {failure_prefix}:')
            for error in self.errors:
                output.append(f'  • {error.path}: {error.message}')
                if error.suggestion:
                    output.append(f'    💡 {error.suggestion}')

        if self.warnings:
            output.append('⚠️  Warnings:')
            for warning in self.warnings:
                output.append(f'  • {warning.path}: {warning.message}')
                if warning.suggestion:
                    output.append(f'    💡 {warning.suggestion}')

        return '\n'.join(output)
