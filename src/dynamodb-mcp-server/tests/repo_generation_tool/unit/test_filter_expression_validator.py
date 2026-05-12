"""Unit tests for FilterExpressionValidator."""

import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.filter_expression_validator import (
    FilterExpressionValidator,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_validator import (
    SchemaValidator,
)
from pathlib import Path


# Common test fixtures
ENTITY_FIELDS = {'status', 'total', 'delivery_fee', 'items', 'tags', 'name', 'description', 'tip'}
KEY_ATTRIBUTES = {'customer_id', 'order_date'}


@pytest.fixture
def validator():
    """Create a FilterExpressionValidator instance."""
    return FilterExpressionValidator()


@pytest.mark.unit
class TestFilterExpressionValidatorComparison:
    """Tests for comparison operator filter conditions."""

    def test_valid_equals(self, validator):
        """Test valid = operator."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'status', 'operator': '=', 'param': 'val'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 0

    def test_valid_not_equals(self, validator):
        """Test valid <> operator."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'status', 'operator': '<>', 'param': 'val'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 0

    def test_valid_gte(self, validator):
        """Test valid >= operator."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'total', 'operator': '>=', 'param': 'min_total'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 0

    def test_valid_lt(self, validator):
        """Test valid < operator."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'total', 'operator': '<', 'param': 'max_total'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Scan',
        )
        assert len(errors) == 0

    def test_comparison_missing_param(self, validator):
        """Test comparison operator without param."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'status', 'operator': '='}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert "'=' operator requires 'param'" in errors[0].message


@pytest.mark.unit
class TestFilterExpressionValidatorBetween:
    """Tests for between operator filter conditions."""

    def test_valid_between(self, validator):
        """Test valid between operator."""
        errors = validator.validate_filter_expression(
            {
                'conditions': [
                    {
                        'field': 'delivery_fee',
                        'operator': 'between',
                        'param': 'min',
                        'param2': 'max',
                    }
                ]
            },
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 0

    def test_between_missing_param2(self, validator):
        """Test between operator missing param2."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'delivery_fee', 'operator': 'between', 'param': 'min'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert "'between' operator requires 'param2'" in errors[0].message

    def test_between_missing_both_params(self, validator):
        """Test between operator missing both params."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'delivery_fee', 'operator': 'between'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 2


@pytest.mark.unit
class TestFilterExpressionValidatorIn:
    """Tests for in operator filter conditions."""

    def test_valid_in(self, validator):
        """Test valid in operator."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'status', 'operator': 'in', 'params': ['s1', 's2']}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 0

    def test_in_missing_params(self, validator):
        """Test in operator missing params array."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'status', 'operator': 'in'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert "'in' operator requires a non-empty 'params' array" in errors[0].message

    def test_in_empty_params(self, validator):
        """Test in operator with empty params array."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'status', 'operator': 'in', 'params': []}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1


@pytest.mark.unit
class TestFilterExpressionValidatorFunctions:
    """Tests for function-based filter conditions."""

    def test_valid_contains(self, validator):
        """Test valid contains function."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'tags', 'function': 'contains', 'param': 'tag_val'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 0

    def test_valid_begins_with(self, validator):
        """Test valid begins_with function."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'name', 'function': 'begins_with', 'param': 'prefix'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Scan',
        )
        assert len(errors) == 0

    def test_valid_attribute_exists(self, validator):
        """Test valid attribute_exists function (no param)."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'description', 'function': 'attribute_exists'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 0

    def test_valid_attribute_not_exists(self, validator):
        """Test valid attribute_not_exists function (no param)."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'tip', 'function': 'attribute_not_exists'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 0

    def test_contains_missing_param(self, validator):
        """Test contains function missing param."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'tags', 'function': 'contains'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert "'contains' function requires 'param'" in errors[0].message

    def test_begins_with_missing_param(self, validator):
        """Test begins_with function missing param."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'name', 'function': 'begins_with'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert "'begins_with' function requires 'param'" in errors[0].message


@pytest.mark.unit
class TestFilterExpressionValidatorSize:
    """Tests for size function filter conditions."""

    def test_valid_size_comparison(self, validator):
        """Test valid size function with comparison operator."""
        errors = validator.validate_filter_expression(
            {
                'conditions': [
                    {'field': 'items', 'function': 'size', 'operator': '>', 'param': 'min_items'}
                ]
            },
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 0

    def test_valid_size_between(self, validator):
        """Test valid size function with between operator."""
        errors = validator.validate_filter_expression(
            {
                'conditions': [
                    {
                        'field': 'items',
                        'function': 'size',
                        'operator': 'between',
                        'param': 'min',
                        'param2': 'max',
                    }
                ]
            },
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 0

    def test_size_missing_operator(self, validator):
        """Test size function without operator."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'items', 'function': 'size', 'param': 'min_items'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert "'size' function requires an 'operator'" in errors[0].message


@pytest.mark.unit
class TestFilterExpressionValidatorFieldValidation:
    """Tests for field existence and key attribute validation."""

    def test_unknown_field(self, validator):
        """Test filter on unknown field."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'nonexistent', 'operator': '=', 'param': 'val'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert "Field 'nonexistent' not found" in errors[0].message

    def test_unknown_field_with_suggestion(self, validator):
        """Test unknown field provides close match suggestion."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'statu', 'operator': '=', 'param': 'val'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert "Did you mean 'status'" in errors[0].suggestion

    def test_key_attribute_partition_key(self, validator):
        """Test filter on partition key attribute in Query operation."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'customer_id', 'operator': '=', 'param': 'val'}]},
            ENTITY_FIELDS | {'customer_id'},
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert (
            "Cannot filter on key attribute 'customer_id' in a Query operation"
            in errors[0].message
        )

    def test_key_attribute_sort_key(self, validator):
        """Test filter on sort key attribute in Query operation."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'order_date', 'operator': '=', 'param': 'val'}]},
            ENTITY_FIELDS | {'order_date'},
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert (
            "Cannot filter on key attribute 'order_date' in a Query operation" in errors[0].message
        )

    def test_scan_allows_key_attribute_partition_key(self, validator):
        """Test that Scan allows filtering on partition key attribute."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'customer_id', 'operator': '=', 'param': 'val'}]},
            ENTITY_FIELDS | {'customer_id'},
            KEY_ATTRIBUTES,
            'test',
            'Scan',
        )
        assert len(errors) == 0

    def test_scan_allows_key_attribute_sort_key(self, validator):
        """Test that Scan allows filtering on sort key attribute."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'order_date', 'operator': '=', 'param': 'val'}]},
            ENTITY_FIELDS | {'order_date'},
            KEY_ATTRIBUTES,
            'test',
            'Scan',
        )
        assert len(errors) == 0


@pytest.mark.unit
class TestFilterExpressionValidatorOperationAndLogic:
    """Tests for operation compatibility and logical operators."""

    def test_invalid_operation_getitem(self, validator):
        """Test filter on GetItem operation."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'status', 'operator': '=', 'param': 'val'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'GetItem',
        )
        assert len(errors) == 1
        assert 'only valid for Query and Scan' in errors[0].message

    def test_invalid_operation_putitem(self, validator):
        """Test filter on PutItem operation."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'status', 'operator': '=', 'param': 'val'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'PutItem',
        )
        assert len(errors) == 1

    def test_valid_logical_and(self, validator):
        """Test valid AND logical operator."""
        errors = validator.validate_filter_expression(
            {
                'conditions': [
                    {'field': 'status', 'operator': '<>', 'param': 'val1'},
                    {'field': 'total', 'operator': '>=', 'param': 'val2'},
                ],
                'logical_operator': 'AND',
            },
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 0

    def test_valid_logical_or(self, validator):
        """Test valid OR logical operator."""
        errors = validator.validate_filter_expression(
            {
                'conditions': [
                    {'field': 'total', 'operator': '>=', 'param': 'val1'},
                    {'field': 'tip', 'operator': '>=', 'param': 'val2'},
                ],
                'logical_operator': 'OR',
            },
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 0

    def test_invalid_logical_operator(self, validator):
        """Test invalid logical operator."""
        errors = validator.validate_filter_expression(
            {
                'conditions': [
                    {'field': 'status', 'operator': '=', 'param': 'val1'},
                    {'field': 'total', 'operator': '>=', 'param': 'val2'},
                ],
                'logical_operator': 'XOR',
            },
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert "Invalid logical_operator 'XOR'" in errors[0].message

    def test_empty_conditions(self, validator):
        """Test empty conditions list."""
        errors = validator.validate_filter_expression(
            {'conditions': []},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert 'non-empty list' in errors[0].message

    def test_both_operator_and_function_non_size(self, validator):
        """Test both operator and function set (non-size)."""
        errors = validator.validate_filter_expression(
            {
                'conditions': [
                    {'field': 'status', 'operator': '=', 'function': 'contains', 'param': 'val'}
                ]
            },
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert "Only one of 'operator' or 'function'" in errors[0].message

    def test_unsupported_operator(self, validator):
        """Test unsupported operator."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'status', 'operator': 'equals', 'param': 'val'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert "Invalid operator 'equals'" in errors[0].message

    def test_unsupported_function(self, validator):
        """Test unsupported function."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'status', 'function': 'matches', 'param': 'val'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert "Invalid function 'matches'" in errors[0].message

    def test_no_operator_or_function(self, validator):
        """Test condition with neither operator nor function."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'status', 'param': 'val'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert "must have either 'operator' or 'function'" in errors[0].message

    def test_single_condition_no_logical_operator(self, validator):
        """Test single condition works without logical_operator."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 'status', 'operator': '=', 'param': 'val'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 0


INVALID_FILTER_SCHEMA = (
    Path(__file__).parent.parent
    / 'fixtures'
    / 'invalid_schemas'
    / 'invalid_filter_expression_schema.json'
)


@pytest.mark.unit
class TestFilterExpressionSchemaValidation:
    """Tests that validate the invalid_filter_expression_schema.json fixture produces expected errors."""

    @pytest.fixture
    def validation_result(self):
        """Validate the invalid filter expression schema and return the result."""
        validator = SchemaValidator()
        return validator.validate_schema_file(str(INVALID_FILTER_SCHEMA))

    def test_schema_is_invalid(self, validation_result):
        """Test that the invalid filter expression schema fails validation."""
        assert not validation_result.is_valid

    def test_unknown_field_error(self, validation_result):
        """Test that filtering on unknown field 'nonexistent_field' is caught."""
        error_messages = [e.message for e in validation_result.errors]
        assert any("Field 'nonexistent_field' not found" in msg for msg in error_messages)

    def test_query_filter_on_partition_key_error(self, validation_result):
        """Test that Query filtering on PK attribute 'test_id' is caught."""
        error_messages = [e.message for e in validation_result.errors]
        assert any(
            "Cannot filter on key attribute 'test_id' in a Query operation" in msg
            for msg in error_messages
        )

    def test_query_filter_on_sort_key_error(self, validation_result):
        """Test that Query filtering on SK attribute 'created_at' is caught."""
        error_messages = [e.message for e in validation_result.errors]
        assert any(
            "Cannot filter on key attribute 'created_at' in a Query operation" in msg
            for msg in error_messages
        )

    def test_unsupported_operator_error(self, validation_result):
        """Test that unsupported operator 'equals' is caught."""
        error_messages = [e.message for e in validation_result.errors]
        assert any("Invalid operator 'equals'" in msg for msg in error_messages)

    def test_unsupported_function_error(self, validation_result):
        """Test that unsupported function 'matches' is caught."""
        error_messages = [e.message for e in validation_result.errors]
        assert any("Invalid function 'matches'" in msg for msg in error_messages)

    def test_invalid_logical_operator_error(self, validation_result):
        """Test that invalid logical operator 'XOR' is caught."""
        error_messages = [e.message for e in validation_result.errors]
        assert any("Invalid logical_operator 'XOR'" in msg for msg in error_messages)

    def test_both_operator_and_function_error(self, validation_result):
        """Test that having both operator and function (non-size) is caught."""
        error_messages = [e.message for e in validation_result.errors]
        assert any("Only one of 'operator' or 'function'" in msg for msg in error_messages)

    def test_between_missing_param2_error(self, validation_result):
        """Test that 'between' missing param2 is caught."""
        error_messages = [e.message for e in validation_result.errors]
        assert any("'between' operator requires 'param2'" in msg for msg in error_messages)

    def test_in_missing_params_error(self, validation_result):
        """Test that 'in' missing params array is caught."""
        error_messages = [e.message for e in validation_result.errors]
        assert any(
            "'in' operator requires a non-empty 'params' array" in msg for msg in error_messages
        )

    def test_contains_missing_param_error(self, validation_result):
        """Test that 'contains' missing param is caught."""
        error_messages = [e.message for e in validation_result.errors]
        assert any("'contains' function requires 'param'" in msg for msg in error_messages)

    def test_begins_with_missing_param_error(self, validation_result):
        """Test that 'begins_with' missing param is caught."""
        error_messages = [e.message for e in validation_result.errors]
        assert any("'begins_with' function requires 'param'" in msg for msg in error_messages)

    def test_filter_on_getitem_error(self, validation_result):
        """Test that filter expression on GetItem operation is caught."""
        error_messages = [e.message for e in validation_result.errors]
        assert any(
            "only valid for Query and Scan operations, got 'GetItem'" in msg
            for msg in error_messages
        )

    def test_empty_conditions_error(self, validation_result):
        """Test that empty conditions list is caught."""
        error_messages = [e.message for e in validation_result.errors]
        assert any('non-empty list' in msg for msg in error_messages)

    def test_comparison_missing_param_error(self, validation_result):
        """Test that comparison operator missing param is caught."""
        error_messages = [e.message for e in validation_result.errors]
        assert any("'=' operator requires 'param'" in msg for msg in error_messages)


@pytest.mark.unit
class TestFilterExpressionValidatorMissingField:
    """Tests for missing or invalid field in filter conditions."""

    @pytest.fixture
    def validator(self):
        """Create a FilterExpressionValidator instance."""
        return FilterExpressionValidator()

    def test_condition_missing_field_key(self, validator):
        """Test condition with no 'field' key returns error."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'operator': '=', 'param': 'val'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert 'non-empty string field' in errors[0].message

    def test_condition_field_is_not_string(self, validator):
        """Test condition where field is not a string returns error."""
        errors = validator.validate_filter_expression(
            {'conditions': [{'field': 123, 'operator': '=', 'param': 'val'}]},
            ENTITY_FIELDS,
            KEY_ATTRIBUTES,
            'test',
            'Query',
        )
        assert len(errors) == 1
        assert 'non-empty string field' in errors[0].message
