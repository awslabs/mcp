"""Unit tests for cross-table access pattern validation."""

import json
import os
import pytest
import tempfile
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_validator import (
    SchemaValidator,
)
from pathlib import Path


@pytest.mark.unit
class TestCrossTableValidation:
    """Unit tests for cross-table access pattern validation."""

    @pytest.fixture
    def validator(self):
        """Create a SchemaValidator instance for testing."""
        return SchemaValidator()

    def _validate_schema_dict(self, validator, schema_dict):
        """Helper method to validate a schema dictionary."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(schema_dict, f)
            temp_file = f.name
        try:
            return validator.validate_schema_file(temp_file)
        finally:
            os.unlink(temp_file)

    @pytest.fixture
    def valid_cross_table_schema(self):
        """Create a valid schema with cross-table patterns."""
        return {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'Users',
                        'partition_key': 'pk',
                    },
                    'entities': {
                        'User': {
                            'entity_type': 'USER',
                            'pk_template': 'USER#{user_id}',
                            'fields': [
                                {'name': 'user_id', 'type': 'string', 'required': True},
                                {'name': 'email', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [],
                        }
                    },
                },
                {
                    'table_config': {
                        'table_name': 'EmailLookup',
                        'partition_key': 'pk',
                    },
                    'entities': {
                        'EmailLookup': {
                            'entity_type': 'EMAIL_LOOKUP',
                            'pk_template': 'EMAIL#{email}',
                            'fields': [
                                {'name': 'email', 'type': 'string', 'required': True},
                                {'name': 'user_id', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [],
                        }
                    },
                },
            ],
            'cross_table_access_patterns': [
                {
                    'pattern_id': 100,
                    'name': 'register_user',
                    'description': 'Create user and email lookup atomically',
                    'operation': 'TransactWrite',
                    'entities_involved': [
                        {
                            'table': 'Users',
                            'entity': 'User',
                            'action': 'Put',
                        },
                        {
                            'table': 'EmailLookup',
                            'entity': 'EmailLookup',
                            'action': 'Put',
                        },
                    ],
                    'parameters': [
                        {'name': 'user', 'type': 'entity', 'entity_type': 'User'},
                        {'name': 'email_lookup', 'type': 'entity', 'entity_type': 'EmailLookup'},
                    ],
                    'return_type': 'boolean',
                }
            ],
        }

    def test_validate_valid_cross_table_schema(self, validator, valid_cross_table_schema):
        """Test that a valid cross-table schema passes validation."""
        result = self._validate_schema_dict(validator, valid_cross_table_schema)
        assert result.is_valid, (
            f'Validation failed with errors: {[e.message for e in result.errors]}'
        )
        assert len(result.errors) == 0

    def test_validate_user_registration_schema_fixture(self, validator):
        """Test successful validation with the actual user_registration schema fixture."""
        # Load the actual user_registration schema fixture
        fixture_path = (
            Path(__file__).parent.parent
            / 'fixtures'
            / 'valid_schemas'
            / 'user_registration'
            / 'user_registration_schema.json'
        )

        if not fixture_path.exists():
            pytest.skip(f'User registration schema fixture not found at {fixture_path}')

        result = validator.validate_schema_file(str(fixture_path))
        assert result.is_valid, (
            f'Validation failed with errors: {[e.message for e in result.errors]}'
        )
        assert len(result.errors) == 0

        # Verify the schema has cross-table patterns
        with open(fixture_path) as f:
            schema = json.load(f)
        assert 'cross_table_access_patterns' in schema
        assert len(schema['cross_table_access_patterns']) > 0

    def test_validate_cross_table_patterns_not_list(self, validator):
        """Test that cross_table_access_patterns must be a list."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Test', 'partition_key': 'pk'},
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
                            'access_patterns': [],
                        }
                    },
                }
            ],
            'cross_table_access_patterns': 'not a list',
        }
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any(
            'cross_table_access_patterns must be an array' in e.message for e in result.errors
        )

    def test_validate_empty_cross_table_patterns(self, validator):
        """Test that empty cross_table_access_patterns array is valid."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Test', 'partition_key': 'pk'},
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
                            'access_patterns': [],
                        }
                    },
                }
            ],
            'cross_table_access_patterns': [],
        }
        result = self._validate_schema_dict(validator, schema)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_invalid_operation_type(self, validator, valid_cross_table_schema):
        """Test that invalid operation type is rejected."""
        schema = valid_cross_table_schema.copy()
        schema['cross_table_access_patterns'][0]['operation'] = 'InvalidOperation'
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any("Invalid operation 'InvalidOperation'" in e.message for e in result.errors)

    def test_validate_table_not_found(self, validator, valid_cross_table_schema):
        """Test that referencing non-existent table is rejected."""
        schema = valid_cross_table_schema.copy()
        schema['cross_table_access_patterns'][0]['entities_involved'][0]['table'] = (
            'NonExistentTable'
        )
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any("Table 'NonExistentTable' not found" in e.message for e in result.errors)

    def test_validate_entity_not_found(self, validator, valid_cross_table_schema):
        """Test that referencing non-existent entity is rejected."""
        schema = valid_cross_table_schema.copy()
        schema['cross_table_access_patterns'][0]['entities_involved'][0]['entity'] = (
            'NonExistentEntity'
        )
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any("Entity 'NonExistentEntity' not found" in e.message for e in result.errors)

    def test_validate_action_incompatible_with_transact_get(
        self, validator, valid_cross_table_schema
    ):
        """Test that Put action is rejected for TransactGet operation."""
        schema = valid_cross_table_schema.copy()
        schema['cross_table_access_patterns'][0]['operation'] = 'TransactGet'
        # Keep Put action which is invalid for TransactGet
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any(
            "Invalid action 'Put' for operation 'TransactGet'" in e.message for e in result.errors
        )

    def test_validate_action_compatible_with_transact_write(
        self, validator, valid_cross_table_schema
    ):
        """Test that valid TransactWrite actions are accepted."""
        schema = valid_cross_table_schema.copy()
        # Test Put action (already in schema)
        result = self._validate_schema_dict(validator, schema)
        assert result.is_valid

        # Test Update action
        schema['cross_table_access_patterns'][0]['entities_involved'][0]['action'] = 'Update'
        result = self._validate_schema_dict(validator, schema)
        assert result.is_valid

        # Test Delete action
        schema['cross_table_access_patterns'][0]['entities_involved'][0]['action'] = 'Delete'
        result = self._validate_schema_dict(validator, schema)
        assert result.is_valid

        # Test ConditionCheck action
        schema['cross_table_access_patterns'][0]['entities_involved'][0]['action'] = (
            'ConditionCheck'
        )
        result = self._validate_schema_dict(validator, schema)
        assert result.is_valid

    def test_validate_pattern_id_uniqueness_across_tables(self, validator):
        """Test that pattern IDs must be unique across per-table and cross-table patterns."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Test', 'partition_key': 'pk'},
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
                            'access_patterns': [
                                {
                                    'pattern_id': 100,
                                    'name': 'get_test',
                                    'description': 'Get test',
                                    'operation': 'GetItem',
                                    'parameters': [{'name': 'id', 'type': 'string'}],
                                    'return_type': 'single_entity',
                                }
                            ],
                        }
                    },
                }
            ],
            'cross_table_access_patterns': [
                {
                    'pattern_id': 100,  # Duplicate!
                    'name': 'cross_pattern',
                    'description': 'Cross pattern',
                    'operation': 'TransactWrite',
                    'entities_involved': [
                        {'table': 'Test', 'entity': 'TestEntity', 'action': 'Put'}
                    ],
                    'parameters': [],
                    'return_type': 'boolean',
                }
            ],
        }
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any('Duplicate pattern_id 100' in e.message for e in result.errors)

    def test_validate_entity_parameter_with_valid_entity_type(
        self, validator, valid_cross_table_schema
    ):
        """Test that entity parameters with valid entity_type are accepted."""
        result = self._validate_schema_dict(validator, valid_cross_table_schema)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_entity_parameter_missing_entity_type(
        self, validator, valid_cross_table_schema
    ):
        """Test that entity parameters without entity_type are rejected."""
        schema = valid_cross_table_schema.copy()
        # Remove entity_type from first parameter
        schema['cross_table_access_patterns'][0]['parameters'][0] = {
            'name': 'user',
            'type': 'entity',
            # Missing entity_type
        }
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any(
            'Entity parameters must specify entity_type' in e.message for e in result.errors
        )

    def test_validate_entity_parameter_invalid_entity_type(
        self, validator, valid_cross_table_schema
    ):
        """Test that entity parameters with invalid entity_type are rejected."""
        schema = valid_cross_table_schema.copy()
        # Use non-existent entity type
        schema['cross_table_access_patterns'][0]['parameters'][0]['entity_type'] = (
            'NonExistentEntity'
        )
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any("Unknown entity type 'NonExistentEntity'" in e.message for e in result.errors)

    def test_validate_primitive_parameter_types(self, validator, valid_cross_table_schema):
        """Test that primitive parameter types are accepted."""
        schema = valid_cross_table_schema.copy()
        # Replace parameters with primitive types
        schema['cross_table_access_patterns'][0]['parameters'] = [
            {'name': 'user_id', 'type': 'string'},
            {'name': 'age', 'type': 'integer'},
            {'name': 'balance', 'type': 'decimal'},
            {'name': 'active', 'type': 'boolean'},
            {'name': 'tags', 'type': 'array'},
            {'name': 'metadata', 'type': 'object'},
            {'name': 'id', 'type': 'uuid'},
        ]
        result = self._validate_schema_dict(validator, schema)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_invalid_parameter_type(self, validator, valid_cross_table_schema):
        """Test that invalid parameter types are rejected."""
        schema = valid_cross_table_schema.copy()
        schema['cross_table_access_patterns'][0]['parameters'] = [
            {'name': 'param1', 'type': 'invalid_type'},
        ]
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any("Invalid type value 'invalid_type'" in e.message for e in result.errors)

    def test_validate_duplicate_parameter_names(self, validator, valid_cross_table_schema):
        """Test that duplicate parameter names are rejected."""
        schema = valid_cross_table_schema.copy()
        schema['cross_table_access_patterns'][0]['parameters'] = [
            {'name': 'user_id', 'type': 'string'},
            {'name': 'user_id', 'type': 'string'},  # Duplicate!
        ]
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any("Duplicate parameter name 'user_id'" in e.message for e in result.errors)

    def test_validate_parameters_not_list(self, validator, valid_cross_table_schema):
        """Test that parameters must be a list."""
        schema = valid_cross_table_schema.copy()
        schema['cross_table_access_patterns'][0]['parameters'] = 'not a list'
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any('parameters must be an array' in e.message for e in result.errors)

    def test_validate_empty_parameters_list(self, validator, valid_cross_table_schema):
        """Test that empty parameters list is valid."""
        schema = valid_cross_table_schema.copy()
        schema['cross_table_access_patterns'][0]['parameters'] = []
        result = self._validate_schema_dict(validator, schema)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_parameter_missing_required_fields(self, validator, valid_cross_table_schema):
        """Test that parameters with missing required fields are rejected."""
        schema = valid_cross_table_schema.copy()
        # Missing 'type' field
        schema['cross_table_access_patterns'][0]['parameters'] = [
            {'name': 'user_id'},  # Missing type
        ]
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any("Missing required field 'type'" in e.message for e in result.errors)

        # Missing 'name' field
        schema['cross_table_access_patterns'][0]['parameters'] = [
            {'type': 'string'},  # Missing name
        ]
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any("Missing required field 'name'" in e.message for e in result.errors)

    def test_validate_multiple_errors_reported_together(self, validator):
        """Test that multiple validation errors are reported together in a single validation run."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Users', 'partition_key': 'pk'},
                    'entities': {
                        'User': {
                            'entity_type': 'USER',
                            'pk_template': '{id}',
                            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
                            'access_patterns': [
                                {
                                    'pattern_id': 100,
                                    'name': 'get_user',
                                    'description': 'Get user',
                                    'operation': 'GetItem',
                                    'parameters': [{'name': 'id', 'type': 'string'}],
                                    'return_type': 'single_entity',
                                }
                            ],
                        }
                    },
                }
            ],
            'cross_table_access_patterns': [
                {
                    'pattern_id': 100,  # Error 1: Duplicate pattern ID
                    'name': 'bad_pattern',
                    'description': 'Pattern with multiple errors',
                    'operation': 'InvalidOp',  # Error 2: Invalid operation
                    'entities_involved': [
                        {
                            'table': 'NonExistentTable',  # Error 3: Table not found
                            'entity': 'NonExistentEntity',  # Error 4: Entity not found (if table existed)
                            'action': 'Put',
                        }
                    ],
                    'parameters': [
                        {
                            'name': 'param1',
                            'type': 'invalid_type',
                        },  # Error 5: Invalid parameter type
                        {'name': 'param1', 'type': 'string'},  # Error 6: Duplicate parameter name
                    ],
                    'return_type': 'invalid_return',  # Error 7: Invalid return type
                }
            ],
        }

        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid

        # Verify multiple errors are reported
        assert len(result.errors) >= 5, (
            f'Expected at least 5 errors, got {len(result.errors)}: {[e.message for e in result.errors]}'
        )

        # Check for specific errors
        error_messages = [e.message for e in result.errors]

        # Error 1: Duplicate pattern ID
        assert any('Duplicate pattern_id 100' in msg for msg in error_messages), (
            'Missing duplicate pattern_id error'
        )

        # Error 2: Invalid operation
        assert any("Invalid operation 'InvalidOp'" in msg for msg in error_messages), (
            'Missing invalid operation error'
        )

        # Error 3: Table not found
        assert any("Table 'NonExistentTable' not found" in msg for msg in error_messages), (
            'Missing table not found error'
        )

        # Error 5: Invalid parameter type
        assert any("Invalid type value 'invalid_type'" in msg for msg in error_messages), (
            'Missing invalid parameter type error'
        )

        # Error 6: Duplicate parameter name
        assert any("Duplicate parameter name 'param1'" in msg for msg in error_messages), (
            'Missing duplicate parameter name error'
        )

    def test_validate_parameter_type_mismatch_with_field(self, validator):
        """Test that parameter type must match entity field type."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Balances', 'partition_key': 'account_id'},
                    'entities': {
                        'Balance': {
                            'entity_type': 'BALANCE',
                            'pk_template': '{account_id}',
                            'fields': [
                                {'name': 'account_id', 'type': 'string', 'required': True},
                                {'name': 'amount', 'type': 'decimal', 'required': True},
                            ],
                            'access_patterns': [],
                        }
                    },
                }
            ],
            'cross_table_access_patterns': [
                {
                    'pattern_id': 100,
                    'name': 'transfer',
                    'description': 'Transfer money',
                    'operation': 'TransactWrite',
                    'entities_involved': [
                        {'table': 'Balances', 'entity': 'Balance', 'action': 'Update'}
                    ],
                    'parameters': [
                        {'name': 'account_id', 'type': 'string'},
                        {'name': 'amount', 'type': 'string'},  # Wrong! Should be 'decimal'
                    ],
                    'return_type': 'boolean',
                }
            ],
        }

        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any(
            "Parameter 'amount' type 'string' doesn't match field type 'decimal'" in err.message
            for err in result.errors
        )
        assert any("Change parameter type to 'decimal'" in err.suggestion for err in result.errors)

    def test_validate_cross_table_pattern_not_dict(self, validator):
        """Test that cross-table pattern must be a dict."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Test', 'partition_key': 'pk'},
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
                            'access_patterns': [],
                        }
                    },
                }
            ],
            'cross_table_access_patterns': ['not a dict'],
        }
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any('Cross-table pattern must be an object' in e.message for e in result.errors)

    def test_validate_pattern_id_not_integer(self, validator, valid_cross_table_schema):
        """Test that pattern_id must be an integer."""
        schema = valid_cross_table_schema.copy()
        schema['cross_table_access_patterns'][0]['pattern_id'] = 'not_an_int'
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any('pattern_id must be an integer' in e.message for e in result.errors)

    def test_validate_entities_involved_not_list(self, validator, valid_cross_table_schema):
        """Test that entities_involved must be a list."""
        schema = valid_cross_table_schema.copy()
        schema['cross_table_access_patterns'][0]['entities_involved'] = 'not a list'
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any('entities_involved must be an array' in e.message for e in result.errors)

    def test_validate_entities_involved_empty(self, validator, valid_cross_table_schema):
        """Test that entities_involved cannot be empty."""
        schema = valid_cross_table_schema.copy()
        schema['cross_table_access_patterns'][0]['entities_involved'] = []
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any('entities_involved cannot be empty' in e.message for e in result.errors)

    def test_validate_entity_involvement_not_dict(self, validator, valid_cross_table_schema):
        """Test that entity involvement must be a dict."""
        schema = valid_cross_table_schema.copy()
        schema['cross_table_access_patterns'][0]['entities_involved'] = ['not a dict']
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any('Entity involvement must be an object' in e.message for e in result.errors)
