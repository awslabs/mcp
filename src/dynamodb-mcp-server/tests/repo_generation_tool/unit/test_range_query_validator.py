"""Unit tests for Range Query validation system."""

import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.range_query_validator import (
    RangeQueryValidator,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    AccessPattern,
)


@pytest.mark.unit
class TestRangeQueryValidator:
    """Unit tests for RangeQueryValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = RangeQueryValidator()


@pytest.mark.unit
class TestValidateRangeCondition(TestRangeQueryValidator):
    """Test range condition validation."""

    def test_validate_all_valid_range_conditions(self):
        """Test validation passes for all valid range condition values."""
        valid_conditions = ['begins_with', 'between', '>', '<', '>=', '<=']

        for condition in valid_conditions:
            errors = self.validator.validate_range_condition(condition)
            assert errors == [], f"Valid condition '{condition}' should not produce errors"

    def test_validate_invalid_range_condition(self):
        """Test validation fails for invalid range condition."""
        errors = self.validator.validate_range_condition('invalid_condition')

        assert len(errors) == 1
        error = errors[0]
        assert error.path == 'range_condition'
        assert "Invalid range_condition 'invalid_condition'" in error.message
        assert 'Valid range_condition values:' in error.suggestion
        assert 'begins_with' in error.suggestion
        assert 'between' in error.suggestion

    def test_validate_non_string_range_condition(self):
        """Test validation fails for non-string range condition."""
        errors = self.validator.validate_range_condition(123)

        assert len(errors) == 1
        error = errors[0]
        assert 'range_condition must be a string' in error.message
        assert 'got int' in error.message

    def test_validate_case_sensitive(self):
        """Test validation is case sensitive."""
        errors = self.validator.validate_range_condition('BEGINS_WITH')

        assert len(errors) == 1
        assert "Invalid range_condition 'BEGINS_WITH'" in errors[0].message

    def test_validate_with_custom_path(self):
        """Test validation uses custom path for error reporting."""
        errors = self.validator.validate_range_condition('invalid', 'custom.path.range_condition')

        assert len(errors) == 1
        assert errors[0].path == 'custom.path.range_condition'


@pytest.mark.unit
class TestGetExpectedParameterCount(TestRangeQueryValidator):
    """Test expected parameter count calculation."""

    def test_between_requires_three_parameters(self):
        """Test 'between' requires 3 parameters (pk + 2 range values)."""
        count = self.validator.get_expected_parameter_count('between')
        assert count == 3

    def test_begins_with_requires_two_parameters(self):
        """Test 'begins_with' requires 2 parameters (pk + 1 range value)."""
        count = self.validator.get_expected_parameter_count('begins_with')
        assert count == 2

    def test_comparison_operators_require_two_parameters(self):
        """Test comparison operators require 2 parameters (pk + 1 range value)."""
        comparison_ops = ['>', '<', '>=', '<=']

        for op in comparison_ops:
            count = self.validator.get_expected_parameter_count(op)
            assert count == 2, f"Operator '{op}' should require 2 parameters"

    def test_unknown_condition_returns_zero(self):
        """Test unknown range condition returns 0."""
        count = self.validator.get_expected_parameter_count('unknown_condition')
        assert count == 0


@pytest.mark.unit
class TestValidateParameterCount(TestRangeQueryValidator):
    """Test parameter count validation for range conditions."""

    def test_between_with_correct_count(self):
        """Test validation passes for 'between' with 3 parameters."""
        pattern = AccessPattern(
            pattern_id=1,
            name='test_pattern',
            description='Test pattern',
            operation='Query',
            parameters=[{'name': 'pk'}, {'name': 'start'}, {'name': 'end'}],
            return_type='entity_list',
            range_condition='between',
        )

        errors = self.validator.validate_parameter_count(pattern)
        assert errors == []

    def test_between_with_incorrect_count(self):
        """Test validation fails for 'between' with wrong parameter count."""
        pattern = AccessPattern(
            pattern_id=1,
            name='test_pattern',
            description='Test pattern',
            operation='Query',
            parameters=[{'name': 'pk'}, {'name': 'start'}],  # Only 2 parameters
            return_type='entity_list',
            range_condition='between',
        )

        errors = self.validator.validate_parameter_count(pattern)

        assert len(errors) == 1
        error = errors[0]
        assert "Range condition 'between' requires exactly 3 parameters" in error.message
        assert 'got 2' in error.message
        assert 'Add 1 more parameters' in error.suggestion

    def test_begins_with_correct_count(self):
        """Test validation passes for 'begins_with' with 2 parameters."""
        pattern = AccessPattern(
            pattern_id=1,
            name='test_pattern',
            description='Test pattern',
            operation='Query',
            parameters=[{'name': 'pk'}, {'name': 'prefix'}],
            return_type='entity_list',
            range_condition='begins_with',
        )

        errors = self.validator.validate_parameter_count(pattern)
        assert errors == []

    def test_begins_with_incorrect_count(self):
        """Test validation fails for 'begins_with' with wrong parameter count."""
        pattern = AccessPattern(
            pattern_id=1,
            name='test_pattern',
            description='Test pattern',
            operation='Query',
            parameters=[{'name': 'pk'}],  # Only 1 parameter
            return_type='entity_list',
            range_condition='begins_with',
        )

        errors = self.validator.validate_parameter_count(pattern)

        assert len(errors) == 1
        assert "Range condition 'begins_with' requires exactly 2 parameters" in errors[0].message

    def test_comparison_operators_parameter_count(self):
        """Test validation for comparison operators with correct and incorrect count."""
        # Test correct count
        for op in ['>', '<', '>=', '<=']:
            pattern = AccessPattern(
                pattern_id=1,
                name='test_pattern',
                description='Test pattern',
                operation='Query',
                parameters=[{'name': 'pk'}, {'name': 'value'}],
                return_type='entity_list',
                range_condition=op,
            )
            errors = self.validator.validate_parameter_count(pattern)
            assert errors == [], f"Operator '{op}' with 2 parameters should be valid"

        # Test incorrect count
        pattern = AccessPattern(
            pattern_id=1,
            name='test_pattern',
            description='Test pattern',
            operation='Query',
            parameters=[{'name': 'pk'}],
            return_type='entity_list',
            range_condition='>=',
        )
        errors = self.validator.validate_parameter_count(pattern)
        assert len(errors) == 1
        assert "Range condition '>=' requires exactly 2 parameters" in errors[0].message

    def test_no_range_condition_parameter_count(self):
        """Test validation passes when no range condition is specified."""
        pattern = AccessPattern(
            pattern_id=1,
            name='test_pattern',
            description='Test pattern',
            operation='Query',
            parameters=[{'name': 'pk'}],
            return_type='entity_list',
            range_condition=None,
        )

        errors = self.validator.validate_parameter_count(pattern)
        assert errors == []

    def test_no_parameters_with_range_condition(self):
        """Test validation fails when range condition exists but no parameters."""
        pattern = AccessPattern(
            pattern_id=1,
            name='test_pattern',
            description='Test pattern',
            operation='Query',
            parameters=[],
            return_type='entity_list',
            range_condition='begins_with',
        )

        errors = self.validator.validate_parameter_count(pattern)

        assert len(errors) == 1
        assert 'Access patterns with range_condition must have parameters' in errors[0].message

    def test_too_many_parameters(self):
        """Test validation fails when too many parameters provided."""
        pattern = AccessPattern(
            pattern_id=1,
            name='test_pattern',
            description='Test pattern',
            operation='Query',
            parameters=[
                {'name': 'pk'},
                {'name': 'p1'},
                {'name': 'p2'},
                {'name': 'p3'},
            ],  # 4 parameters
            return_type='entity_list',
            range_condition='begins_with',  # Only needs 2
        )

        errors = self.validator.validate_parameter_count(pattern)

        assert len(errors) == 1
        assert 'Remove 2 parameters' in errors[0].suggestion


@pytest.mark.unit
class TestValidateOperationCompatibility(TestRangeQueryValidator):
    """Test operation compatibility validation."""

    def test_query_operation_with_range_condition(self):
        """Test validation passes for Query operation with range condition."""
        pattern = AccessPattern(
            pattern_id=1,
            name='test_pattern',
            description='Test pattern',
            operation='Query',
            parameters=[{'name': 'pk'}, {'name': 'value'}],
            return_type='entity_list',
            range_condition='>=',
        )

        errors = self.validator.validate_operation_compatibility(pattern)
        assert errors == []

    def test_get_item_operation_with_range_condition(self):
        """Test validation fails for GetItem operation with range condition."""
        pattern = AccessPattern(
            pattern_id=1,
            name='test_pattern',
            description='Test pattern',
            operation='GetItem',
            parameters=[{'name': 'pk'}, {'name': 'value'}],
            return_type='single_entity',
            range_condition='>=',
        )

        errors = self.validator.validate_operation_compatibility(pattern)

        assert len(errors) == 1
        error = errors[0]
        assert error.path == 'access_pattern.operation'
        assert "Range conditions require 'Query' operation" in error.message
        assert "got 'GetItem'" in error.message
        assert "Change operation to 'Query' or remove range_condition" in error.suggestion

    def test_no_range_condition_operation_compatibility(self):
        """Test validation passes when no range condition specified."""
        pattern = AccessPattern(
            pattern_id=1,
            name='test_pattern',
            description='Test pattern',
            operation='GetItem',
            parameters=[{'name': 'pk'}],
            return_type='single_entity',
            range_condition=None,
        )
        errors = self.validator.validate_operation_compatibility(pattern)
        assert errors == []


@pytest.mark.unit
class TestValidateCompleteRangeQuery(TestRangeQueryValidator):
    """Test complete range query validation."""

    def test_valid_complete_range_query(self):
        """Test validation passes for completely valid range query."""
        pattern = AccessPattern(
            pattern_id=1,
            name='test_pattern',
            description='Test pattern',
            operation='Query',
            parameters=[{'name': 'pk'}, {'name': 'value'}],
            return_type='entity_list',
            range_condition='>=',
        )

        errors = self.validator.validate_complete_range_query(pattern)
        assert errors == []

    def test_invalid_range_condition_syntax(self):
        """Test validation catches invalid range condition syntax."""
        pattern = AccessPattern(
            pattern_id=1,
            name='test_pattern',
            description='Test pattern',
            operation='Query',
            parameters=[{'name': 'pk'}, {'name': 'value'}],
            return_type='entity_list',
            range_condition='invalid_condition',
        )

        errors = self.validator.validate_complete_range_query(pattern)

        assert len(errors) == 1
        assert "Invalid range_condition 'invalid_condition'" in errors[0].message

    def test_multiple_validation_errors(self):
        """Test validation catches multiple errors in one pattern."""
        pattern = AccessPattern(
            pattern_id=1,
            name='test_pattern',
            description='Test pattern',
            operation='GetItem',  # Wrong operation
            parameters=[{'name': 'pk'}],  # Wrong parameter count
            return_type='single_entity',
            range_condition='between',  # Needs 3 parameters
        )

        errors = self.validator.validate_complete_range_query(pattern)

        # Should catch both parameter count and operation errors
        assert len(errors) == 2
        error_messages = [error.message for error in errors]
        assert any('requires exactly 3 parameters' in msg for msg in error_messages)
        assert any("Range conditions require 'Query' operation" in msg for msg in error_messages)

    def test_no_range_condition_returns_empty(self):
        """Test validation returns empty list when no range condition."""
        pattern = AccessPattern(
            pattern_id=1,
            name='test_pattern',
            description='Test pattern',
            operation='GetItem',
            parameters=[{'name': 'pk'}],
            return_type='single_entity',
            range_condition=None,
        )

        errors = self.validator.validate_complete_range_query(pattern)
        assert errors == []

    def test_stops_validation_on_syntax_error(self):
        """Test validation stops further checks if syntax is invalid."""
        pattern = AccessPattern(
            pattern_id=1,
            name='test_pattern',
            description='Test pattern',
            operation='GetItem',  # Wrong operation (but shouldn't be checked)
            parameters=[{'name': 'pk'}],  # Wrong count (but shouldn't be checked)
            return_type='single_entity',
            range_condition='invalid_syntax',  # Invalid syntax
        )

        errors = self.validator.validate_complete_range_query(pattern)

        # Should only report syntax error, not proceed to other validations
        assert len(errors) == 1
        assert "Invalid range_condition 'invalid_syntax'" in errors[0].message


@pytest.mark.unit
class TestRangeQueryValidatorRealisticScenarios(TestRangeQueryValidator):
    """Test realistic range query validation scenarios."""

    def test_main_table_range_query_scenario(self):
        """Test realistic main table range query scenario."""
        pattern = AccessPattern(
            pattern_id=1,
            name='get_user_posts_after_date',
            description='Get user posts created after a specific date',
            operation='Query',
            parameters=[
                {'name': 'user_id', 'type': 'string'},
                {'name': 'since_date', 'type': 'string'},
            ],
            return_type='entity_list',
            range_condition='>=',
        )
        errors = self.validator.validate_complete_range_query(pattern)
        assert errors == []

    def test_gsi_range_query_scenario(self):
        """Test realistic GSI range query scenario."""
        pattern = AccessPattern(
            pattern_id=1,
            name='get_active_users_in_date_range',
            description='Get active users within date range',
            operation='Query',
            parameters=[
                {'name': 'status', 'type': 'string'},
                {'name': 'start_date', 'type': 'string'},
                {'name': 'end_date', 'type': 'string'},
            ],
            return_type='entity_list',
            index_name='StatusIndex',
            range_condition='between',
        )
        errors = self.validator.validate_complete_range_query(pattern)
        assert errors == []
