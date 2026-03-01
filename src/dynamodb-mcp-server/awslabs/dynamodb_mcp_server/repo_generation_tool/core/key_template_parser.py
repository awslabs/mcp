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

"""Template parameter extraction system for DynamoDB key templates.

This module provides functionality to extract parameters from templates using regex
and validate that parameters exist in entity fields. It supports the unified template
system for both main table and GSI keys.
"""

import re
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    Field,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.validation_utils import (
    ValidationError,
)


class KeyTemplateParser:
    r"""Parser for extracting and validating parameters from DynamoDB key templates.

    Supports the template format: "PREFIX#{field_name}#SUFFIX#{other_field}"
    Extracts parameter names using regex pattern {(\\w+)}
    """

    # Regex pattern to extract parameter names from templates
    # Regex pattern to match {parameter} or {parameter:format_spec}
    # Examples: {user_id}, {score:05d}, {price:.2f}
    PARAMETER_PATTERN = re.compile(r'\{(\w+)(?::[^}]*)?\}')

    def extract_parameters(self, template: str) -> list[str]:
        r"""Extract parameter names from template using regex {(\\w+)}.

        Args:
            template: Template string with {parameter} placeholders

        Returns:
            List of parameter names found in template

        Examples:
            >>> parser = KeyTemplateParser()
            >>> parser.extract_parameters('STATUS#{status}#USER#{user_id}')
            ['status', 'user_id']
            >>> parser.extract_parameters('PROFILE')
            []
        """
        if not isinstance(template, str):
            return []

        matches = self.PARAMETER_PATTERN.findall(template)
        # Return unique parameters while preserving order
        return list(dict.fromkeys(matches))

    def validate_parameters(
        self, parameters: list[str], entity_fields: list[Field]
    ) -> list[ValidationError]:
        """Validate that all extracted parameters exist as entity fields.

        Args:
            parameters: List of parameter names extracted from template
            entity_fields: List of Field objects from entity definition

        Returns:
            List of ValidationError objects for missing parameters
        """
        errors = []

        if not parameters:
            return errors

        # Create set of field names for efficient lookup
        field_names = {field.name for field in entity_fields}

        # Check each parameter
        for param in parameters:
            if param not in field_names:
                available_fields = ', '.join(sorted(field_names))
                errors.append(
                    ValidationError(
                        path=f'template.parameter.{param}',
                        message=f"Template parameter '{param}' not found in entity fields",
                        suggestion=f'Use one of the available fields: {available_fields}',
                    )
                )

        return errors

    def validate_template_syntax(self, template: str) -> list[ValidationError]:
        """Validate template syntax for common issues.

        Args:
            template: Template string to validate

        Returns:
            List of ValidationError objects for syntax issues
        """
        errors = []

        if not isinstance(template, str):
            errors.append(
                ValidationError(
                    path='template',
                    message='Template must be a string',
                    suggestion='Provide a valid string template',
                )
            )
            return errors

        if not template.strip():
            errors.append(
                ValidationError(
                    path='template',
                    message='Template cannot be empty',
                    suggestion='Provide a non-empty template string',
                )
            )
            return errors

        # Check for unmatched braces
        open_braces = template.count('{')
        close_braces = template.count('}')

        if open_braces != close_braces:
            errors.append(
                ValidationError(
                    path='template',
                    message=f'Unmatched braces in template: {open_braces} opening, {close_braces} closing',
                    suggestion='Ensure all { have matching } braces',
                )
            )

        # Check for empty parameter names
        empty_params = re.findall(r'\{\s*\}', template)
        if empty_params:
            errors.append(
                ValidationError(
                    path='template',
                    message='Template contains empty parameter placeholders {}',
                    suggestion='Provide parameter names inside braces like {field_name}',
                )
            )

        # Check for invalid parameter names (non-word characters)
        invalid_params = re.findall(r'\{([^}]*[^\w}][^}]*)\}', template)
        if invalid_params:
            errors.append(
                ValidationError(
                    path='template',
                    message=f'Template contains invalid parameter names: {", ".join(invalid_params)}',
                    suggestion='Parameter names should only contain letters, numbers, and underscores',
                )
            )

        return errors
