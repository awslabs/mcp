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

"""Range query validation system for DynamoDB queries.

This module provides common validation logic for range queries on both main table
sort keys and GSI sort keys. It ensures range conditions are valid and parameter
counts match the requirements of each range condition type.
"""

from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    VALID_RANGE_CONDITIONS,
    AccessPattern,
    RangeCondition,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.validation_utils import (
    ValidationError,
)


class RangeQueryValidator:
    """Common validator for range queries on both main table and GSI sort keys.

    Provides validation for:
    - Range condition syntax (begins_with, between, >=, <=, >, <)
    - Parameter count matching range condition requirements
    - Query operation compatibility
    """

    def validate_range_condition(
        self, range_condition: str, pattern_path: str = 'range_condition'
    ) -> list[ValidationError]:
        """Validate range_condition against allowed DynamoDB operators.

        Args:
            range_condition: Range condition value to validate
            pattern_path: Path context for error reporting

        Returns:
            List of ValidationError objects for invalid range conditions
        """
        errors = []

        if not isinstance(range_condition, str):
            errors.append(
                ValidationError(
                    path=pattern_path,
                    message=f'range_condition must be a string, got {type(range_condition).__name__}',
                    suggestion='Provide range_condition as a string value',
                )
            )
            return errors

        if range_condition not in VALID_RANGE_CONDITIONS:
            valid_conditions = ', '.join(sorted(VALID_RANGE_CONDITIONS))
            errors.append(
                ValidationError(
                    path=pattern_path,
                    message=f"Invalid range_condition '{range_condition}'",
                    suggestion=f'Valid range_condition values: {valid_conditions}',
                )
            )

        return errors

    def get_expected_parameter_count(
        self, range_condition: str, partition_key_count: int = 1
    ) -> int:
        """Get the expected total parameter count for a given range condition.

        Args:
            range_condition: The range condition operator
            partition_key_count: Number of attributes in partition key (1-4 for multi-attribute)

        Returns:
            Expected number of parameters (partition key attributes + range parameters)
        """
        if range_condition == RangeCondition.BETWEEN.value:
            # Between requires: partition_key_count + 2 range parameters
            return partition_key_count + 2
        elif range_condition in {
            RangeCondition.BEGINS_WITH.value,
            RangeCondition.GREATER_THAN.value,
            RangeCondition.LESS_THAN.value,
            RangeCondition.GREATER_THAN_OR_EQUAL.value,
            RangeCondition.LESS_THAN_OR_EQUAL.value,
        }:
            # These conditions require: partition_key_count + 1 range parameter
            return partition_key_count + 1

        # Unknown range condition - return 0 to trigger validation error
        return 0

    def validate_parameter_count(
        self, pattern: AccessPattern, pattern_path: str = 'access_pattern', gsi_def=None
    ) -> list[ValidationError]:
        """Validate parameter count matches range condition requirements.

        Handles multi-attribute partition keys and multi-attribute sort keys.

        For multi-attribute sort keys, you can query left-to-right and stop at any point.
        The range condition applies to the LAST queried SK attribute, not necessarily
        the last attribute in the GSI definition. For example, with SK ["a", "b", "c"]:
        - Query "a = X AND b <= Y" is valid (range on b, c not used)
        - Query "a = X AND b = Y AND c <= Z" is valid (range on c)

        Args:
            pattern: AccessPattern object to validate
            pattern_path: Path context for error reporting
            gsi_def: GSI definition (for multi-attribute key support)

        Returns:
            List of ValidationError objects for incorrect parameter counts
        """
        errors = []

        if not pattern.range_condition:
            return errors

        if not pattern.parameters:
            errors.append(
                ValidationError(
                    path=f'{pattern_path}.parameters',
                    message='Access patterns with range_condition must have parameters',
                    suggestion='Add parameters for partition key and range conditions',
                )
            )
            return errors

        # Calculate partition key count
        pk_count = 1
        if gsi_def and gsi_def.partition_key:
            pk_count = len(gsi_def.partition_key) if isinstance(gsi_def.partition_key, list) else 1

        param_count = len(pattern.parameters)
        range_condition = pattern.range_condition

        # Range parameters: 2 for 'between', 1 for all others
        range_param_count = 2 if range_condition == RangeCondition.BETWEEN.value else 1

        # For multi-attribute SK, validate that parameter count follows left-to-right rule:
        # - Must have all PK attributes
        # - SK attributes are queried left-to-right, can stop at any point
        # - The last queried SK attribute can have a range condition
        #
        # Minimum: pk_count + range_param_count (just PK + range on first SK attribute)
        # Maximum: pk_count + (sk_count - 1) + range_param_count (all SK equality + range on last)

        sk_count = 0
        if gsi_def and gsi_def.sort_key:
            sk_count = len(gsi_def.sort_key) if isinstance(gsi_def.sort_key, list) else 1

        min_params = pk_count + range_param_count
        max_params = pk_count + max(0, sk_count - 1) + range_param_count

        if param_count < min_params:
            errors.append(
                ValidationError(
                    path=f'{pattern_path}.parameters',
                    message=f"Range condition '{range_condition}' requires at least {min_params} parameters ({pk_count} PK + {range_param_count} range value(s)), got {param_count}",
                    suggestion=f'Provide at least {min_params} parameters',
                )
            )
        elif gsi_def is None and param_count > min_params:
            # No GSI context (main table query): single-attribute keys use exact count
            errors.append(
                ValidationError(
                    path=f'{pattern_path}.parameters',
                    message=f"Range condition '{range_condition}' requires exactly {min_params} parameters ({pk_count} PK + {range_param_count} range value(s)), got {param_count}",
                    suggestion=f'Provide exactly {min_params} parameters for main table range queries',
                )
            )
        elif sk_count > 0 and param_count > max_params:
            sk_equality_max = max(0, sk_count - 1)
            errors.append(
                ValidationError(
                    path=f'{pattern_path}.parameters',
                    message=f"Range condition '{range_condition}' allows at most {max_params} parameters ({pk_count} PK + {sk_equality_max} SK equality + {range_param_count} range value(s)), got {param_count}",
                    suggestion=f'Provide at most {max_params} parameters. SK attributes must be queried left-to-right.',
                )
            )

        return errors

    def validate_operation_compatibility(
        self, pattern: AccessPattern, pattern_path: str = 'access_pattern'
    ) -> list[ValidationError]:
        """Validate that range conditions are only used with Query operations.

        Range conditions require Query operations, not GetItem, PutItem, etc.

        Args:
            pattern: AccessPattern object to validate
            pattern_path: Path context for error reporting

        Returns:
            List of ValidationError objects for incompatible operations
        """
        errors = []

        if not pattern.range_condition:
            return errors

        # Range conditions only work with Query operations
        if pattern.operation != 'Query':
            errors.append(
                ValidationError(
                    path=f'{pattern_path}.operation',
                    message=f"Range conditions require 'Query' operation, got '{pattern.operation}'",
                    suggestion="Change operation to 'Query' or remove range_condition",
                )
            )

        return errors

    def validate_complete_range_query(
        self, pattern: AccessPattern, pattern_path: str = 'access_pattern'
    ) -> list[ValidationError]:
        """Perform comprehensive validation for a range query access pattern.

        Validates:
        - Range condition syntax
        - Parameter count
        - Operation compatibility

        Args:
            pattern: AccessPattern object to validate
            pattern_path: Path context for error reporting

        Returns:
            List of all ValidationError objects found
        """
        errors = []

        if not pattern.range_condition:
            return errors

        # Validate range condition syntax
        range_errors = self.validate_range_condition(
            pattern.range_condition, f'{pattern_path}.range_condition'
        )
        errors.extend(range_errors)

        # Only proceed with further validation if range condition is valid
        if not range_errors:
            # Validate parameter count
            param_errors = self.validate_parameter_count(pattern, pattern_path)
            errors.extend(param_errors)

            # Validate operation compatibility
            op_errors = self.validate_operation_compatibility(pattern, pattern_path)
            errors.extend(op_errors)

        return errors
