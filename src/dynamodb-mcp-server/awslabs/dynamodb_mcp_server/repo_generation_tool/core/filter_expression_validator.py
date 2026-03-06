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

"""Filter expression validation for DynamoDB access patterns.

This module validates filter_expression definitions within access patterns,
ensuring fields exist, operators/functions are supported, parameter requirements
are met, and key attributes are not used in filter expressions.
"""

from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    VALID_FILTER_FUNCTIONS,
    VALID_FILTER_LOGICAL_OPERATORS,
    VALID_FILTER_OPERATORS,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.validation_utils import (
    ValidationError,
)
from difflib import get_close_matches


# Functions that require no parameter value
NO_PARAM_FUNCTIONS = frozenset({'attribute_exists', 'attribute_not_exists'})

# Functions that require exactly one param (contains, begins_with)
# Note: 'size' with 'between' requires two params (param + param2) — handled separately
SINGLE_PARAM_REQUIRED_FUNCTIONS = frozenset({'contains', 'begins_with'})

# Valid operations for filter expressions
VALID_FILTER_OPERATIONS = frozenset({'Query', 'Scan'})


class FilterExpressionValidator:
    """Validator for filter expression definitions in access patterns.

    Validates:
    - Operation is Query or Scan
    - Conditions list is non-empty
    - Logical operator is AND or OR
    - Each condition's field exists in entity fields
    - Each condition's field is not a key attribute (PK or SK)
    - Each condition has valid operator or function
    - Parameter requirements match operator/function type
    """

    def validate_filter_expression(
        self,
        filter_expr: dict,
        entity_fields: set[str],
        key_attributes: set[str],
        pattern_path: str,
        operation: str,
    ) -> list[ValidationError]:
        """Validate a complete filter expression block.

        Args:
            filter_expr: The filter_expression dict from the access pattern
            entity_fields: Set of valid field names for the entity
            key_attributes: Set of field names used in PK/SK templates
            pattern_path: Path context for error reporting
            operation: The access pattern operation (Query, Scan, GetItem, etc.)

        Returns:
            List of ValidationError objects for invalid configurations
        """
        errors = []

        # Validate operation compatibility
        if operation not in VALID_FILTER_OPERATIONS:
            valid_ops = ', '.join(sorted(VALID_FILTER_OPERATIONS))
            errors.append(
                ValidationError(
                    path=pattern_path,
                    message=f"Filter expressions are only valid for Query and Scan operations, got '{operation}'",
                    suggestion=f'Change operation to one of: {valid_ops}, or remove filter_expression',
                )
            )
            return errors

        # Validate conditions list
        conditions = filter_expr.get('conditions')
        if not isinstance(conditions, list) or len(conditions) == 0:
            errors.append(
                ValidationError(
                    path=f'{pattern_path}.conditions',
                    message='filter_expression.conditions must be a non-empty list',
                    suggestion='Add at least one filter condition',
                )
            )
            return errors

        # Validate logical_operator if present
        logical_op = filter_expr.get('logical_operator')
        if logical_op is not None:
            if logical_op not in VALID_FILTER_LOGICAL_OPERATORS:
                valid_ops = ', '.join(sorted(VALID_FILTER_LOGICAL_OPERATORS))
                errors.append(
                    ValidationError(
                        path=f'{pattern_path}.logical_operator',
                        message=f"Invalid logical_operator '{logical_op}'",
                        suggestion=f'Valid logical operators: {valid_ops}',
                    )
                )

        # Validate each condition
        for i, condition in enumerate(conditions):
            condition_path = f'{pattern_path}.conditions[{i}]'
            condition_errors = self._validate_condition(
                condition, entity_fields, key_attributes, condition_path, operation
            )
            errors.extend(condition_errors)

        return errors

    def _validate_condition(
        self,
        condition: dict,
        entity_fields: set[str],
        key_attributes: set[str],
        condition_path: str,
        operation: str,
    ) -> list[ValidationError]:
        """Validate a single filter condition.

        Args:
            condition: The condition dict to validate
            entity_fields: Set of valid field names for the entity
            key_attributes: Set of field names used in PK/SK templates
            condition_path: Path context for error reporting
            operation: The access pattern operation (Query, Scan, etc.)

        Returns:
            List of ValidationError objects for invalid configurations
        """
        errors = []

        # Validate field exists
        field = condition.get('field')
        if not field or not isinstance(field, str):
            errors.append(
                ValidationError(
                    path=f'{condition_path}.field',
                    message='Filter condition must have a non-empty string field',
                    suggestion='Add a field name referencing an entity field',
                )
            )
            return errors

        if field not in entity_fields:
            suggestion = f'Available fields: {", ".join(sorted(entity_fields))}'
            close = get_close_matches(field, entity_fields, n=1, cutoff=0.6)
            if close:
                suggestion = f"Did you mean '{close[0]}'? {suggestion}"
            errors.append(
                ValidationError(
                    path=f'{condition_path}.field',
                    message=f"Field '{field}' not found in entity fields",
                    suggestion=suggestion,
                )
            )
            return errors

        # Validate field is not a key attribute (only for Query — Scan has no KeyConditionExpression)
        if field in key_attributes and operation == 'Query':
            errors.append(
                ValidationError(
                    path=f'{condition_path}.field',
                    message=f"Cannot filter on key attribute '{field}' in a Query operation",
                    suggestion='For Query, key attributes must be in KeyConditionExpression, not FilterExpression. For Scan operations, filtering on key attributes is allowed.',
                )
            )
            return errors

        # Validate operator/function
        operator = condition.get('operator')
        function = condition.get('function')

        if operator and function and function != 'size':
            errors.append(
                ValidationError(
                    path=condition_path,
                    message="Only one of 'operator' or 'function' is allowed (except for 'size' which requires both)",
                    suggestion="Remove either 'operator' or 'function', or use function='size' with an operator",
                )
            )
            return errors

        if not operator and not function:
            errors.append(
                ValidationError(
                    path=condition_path,
                    message="Filter condition must have either 'operator' or 'function'",
                    suggestion=f"Add 'operator' ({', '.join(sorted(VALID_FILTER_OPERATORS))}) or 'function' ({', '.join(sorted(VALID_FILTER_FUNCTIONS))})",
                )
            )
            return errors

        # Validate based on function or operator
        if function:
            errors.extend(self._validate_function_condition(condition, condition_path))
        else:
            errors.extend(self._validate_operator_condition(condition, condition_path))

        return errors

    def _validate_operator_condition(
        self, condition: dict, condition_path: str
    ) -> list[ValidationError]:
        """Validate a condition that uses an operator (no function)."""
        errors = []
        operator = condition.get('operator')

        if operator not in VALID_FILTER_OPERATORS:
            valid_ops = ', '.join(sorted(VALID_FILTER_OPERATORS))
            errors.append(
                ValidationError(
                    path=f'{condition_path}.operator',
                    message=f"Invalid operator '{operator}'",
                    suggestion=f'Valid operators: {valid_ops}',
                )
            )
            return errors

        # Validate parameter requirements
        if operator == 'between':
            if not condition.get('param'):
                errors.append(
                    ValidationError(
                        path=condition_path,
                        message="'between' operator requires 'param' field",
                        suggestion='Add param for the lower bound value',
                    )
                )
            if not condition.get('param2'):
                errors.append(
                    ValidationError(
                        path=condition_path,
                        message="'between' operator requires 'param2' field",
                        suggestion='Add param2 for the upper bound value',
                    )
                )
        elif operator == 'in':
            params = condition.get('params')
            if not params or not isinstance(params, list) or len(params) == 0:
                errors.append(
                    ValidationError(
                        path=condition_path,
                        message="'in' operator requires a non-empty 'params' array",
                        suggestion='Add params array, e.g. "params": ["value1", "value2"]',
                    )
                )
        else:
            # Comparison operators require param
            if not condition.get('param'):
                errors.append(
                    ValidationError(
                        path=condition_path,
                        message=f"'{operator}' operator requires 'param' field",
                        suggestion='Add param referencing a parameter name',
                    )
                )

        return errors

    def _validate_function_condition(
        self, condition: dict, condition_path: str
    ) -> list[ValidationError]:
        """Validate a condition that uses a function."""
        errors = []
        function = condition.get('function')

        if function not in VALID_FILTER_FUNCTIONS:
            valid_fns = ', '.join(sorted(VALID_FILTER_FUNCTIONS))
            errors.append(
                ValidationError(
                    path=f'{condition_path}.function',
                    message=f"Invalid function '{function}'",
                    suggestion=f'Valid functions: {valid_fns}',
                )
            )
            return errors

        if function == 'size':
            # size requires an operator and appropriate params
            operator = condition.get('operator')
            if not operator:
                errors.append(
                    ValidationError(
                        path=condition_path,
                        message="'size' function requires an 'operator' field",
                        suggestion="Add operator like '>', '>=', '<', '<=', '=', '<>', 'between'",
                    )
                )
                return errors
            # Validate the operator and its params via the operator validator
            errors.extend(self._validate_operator_condition(condition, condition_path))
        elif function in NO_PARAM_FUNCTIONS:
            # attribute_exists / attribute_not_exists need no params
            pass
        elif function in SINGLE_PARAM_REQUIRED_FUNCTIONS:
            # contains / begins_with require param
            if not condition.get('param'):
                errors.append(
                    ValidationError(
                        path=condition_path,
                        message=f"'{function}' function requires 'param' field",
                        suggestion='Add param referencing a parameter name',
                    )
                )

        return errors
