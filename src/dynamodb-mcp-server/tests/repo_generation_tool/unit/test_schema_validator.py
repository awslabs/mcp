"""Unit tests for SchemaValidator class."""

import json
import os
import pytest
import tempfile
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_validator import (
    SchemaValidator,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.validation_utils import (
    ValidationError,
    ValidationResult,
)
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.unit
class TestSchemaValidator:
    """Unit tests for SchemaValidator class - fast, isolated tests."""

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
    def valid_minimal_schema(self):
        """Create a valid minimal schema for testing."""
        return {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'TestTable',
                        'partition_key': 'pk',
                        'sort_key': 'sk',
                    },
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'sk_template': 'ENTITY',
                            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }

    def test_validate_valid_schema(self, validator, valid_minimal_schema):
        """Test that a valid minimal schema passes validation."""
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert result.is_valid and len(result.errors) == 0

    def test_validate_schema_not_dict(self, validator):
        """Test that non-dictionary schema fails validation."""
        result = self._validate_schema_dict(validator, [])
        assert not result.is_valid and any(
            'Schema must be a JSON object' in e.message for e in result.errors
        )

    def test_validate_tables_not_list(self, validator):
        """Test that tables must be a list."""
        result = self._validate_schema_dict(validator, {'tables': 'not a list'})
        assert not result.is_valid and any(
            'tables must be an array' in e.message for e in result.errors
        )

    def test_validate_empty_tables(self, validator):
        """Test that tables list cannot be empty."""
        result = self._validate_schema_dict(validator, {'tables': []})
        assert not result.is_valid and any(
            'tables cannot be empty' in e.message for e in result.errors
        )

    def test_validate_table_not_dict(self, validator):
        """Test that each table must be a dictionary."""
        result = self._validate_schema_dict(validator, {'tables': ['not a dict']})
        assert not result.is_valid and any(
            'Table must be an object' in e.message for e in result.errors
        )

    def test_validate_table_config_not_dict(self, validator):
        """Test that table_config must be a dictionary."""
        result = self._validate_schema_dict(
            validator, {'tables': [{'table_config': 'not a dict', 'entities': {}}]}
        )
        assert not result.is_valid and any(
            'table_config must be an object' in e.message for e in result.errors
        )

    def test_validate_entities_not_dict(self, validator):
        """Test that entities must be a dictionary."""
        result = self._validate_schema_dict(
            validator,
            {
                'tables': [
                    {
                        'table_config': {'table_name': 'T', 'partition_key': 'pk'},
                        'entities': 'not a dict',
                    }
                ]
            },
        )
        assert not result.is_valid and any(
            'entities must be an object' in e.message for e in result.errors
        )

    def test_validate_empty_entities(self, validator):
        """Test that entities dictionary cannot be empty."""
        result = self._validate_schema_dict(
            validator,
            {
                'tables': [
                    {'table_config': {'table_name': 'T', 'partition_key': 'pk'}, 'entities': {}}
                ]
            },
        )
        assert not result.is_valid and any(
            'entities cannot be empty' in e.message for e in result.errors
        )

    def test_validate_entity_not_dict(self, validator):
        """Test that each entity must be a dictionary."""
        result = self._validate_schema_dict(
            validator,
            {
                'tables': [
                    {
                        'table_config': {'table_name': 'T', 'partition_key': 'pk'},
                        'entities': {'E': 'not a dict'},
                    }
                ]
            },
        )
        assert not result.is_valid and any('must be an object' in e.message for e in result.errors)

    def test_validate_fields_not_list(self, validator, valid_minimal_schema):
        """Test that fields must be a list."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['fields'] = 'not a list'
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid and any(
            'fields must be an array' in e.message for e in result.errors
        )

    def test_validate_empty_fields(self, validator, valid_minimal_schema):
        """Test that fields list cannot be empty."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['fields'] = []
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid and any(
            'fields cannot be empty' in e.message for e in result.errors
        )

    def test_validate_field_not_dict(self, validator, valid_minimal_schema):
        """Test that each field must be a dictionary."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['fields'] = ['not a dict']
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid and any(
            'Field must be an object' in e.message for e in result.errors
        )

    def test_validate_duplicate_field_names(self, validator, valid_minimal_schema):
        """Test that field names must be unique within an entity."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['fields'] = [
            {'name': 'id', 'type': 'string', 'required': True},
            {'name': 'id', 'type': 'string', 'required': False},
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid and any(
            'Duplicate field name' in e.message for e in result.errors
        )

    def test_validate_invalid_field_type(self, validator, valid_minimal_schema):
        """Test that field type must be valid."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['fields'][0]['type'] = (
            'invalid_type'
        )
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid and any(
            "Invalid type value 'invalid_type'" in e.message for e in result.errors
        )

    def test_validate_array_field_missing_item_type(self, validator, valid_minimal_schema):
        """Test that array fields must have item_type specified."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['fields'].append(
            {'name': 'tags', 'type': 'array', 'required': True}
        )
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid and any(
            'Array fields must specify item_type' in e.message for e in result.errors
        )

    def test_validate_field_required_not_bool(self, validator, valid_minimal_schema):
        """Test that field required must be boolean."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['fields'][0]['required'] = (
            'yes'
        )
        assert not self._validate_schema_dict(validator, valid_minimal_schema).is_valid

    def test_validate_sk_template_null(self, validator, valid_minimal_schema):
        """Test that sk_template can be null for partition-key-only tables."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['sk_template'] = None
        assert self._validate_schema_dict(validator, valid_minimal_schema).is_valid

    def test_validate_sk_template_invalid_type(self, validator, valid_minimal_schema):
        """Test that sk_template must be string or null."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['sk_template'] = 123
        assert not self._validate_schema_dict(validator, valid_minimal_schema).is_valid

    def test_validate_access_patterns_not_list(self, validator, valid_minimal_schema):
        """Test that access_patterns must be a list."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = (
            'not a list'
        )
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid and any(
            'access_patterns must be an array' in e.message for e in result.errors
        )

    def test_validate_access_pattern_not_dict(self, validator, valid_minimal_schema):
        """Test that each access pattern must be a dictionary."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            'not a dict'
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid and any(
            'Access pattern must be an object' in e.message for e in result.errors
        )

    def test_validate_pattern_id_not_int(self, validator, valid_minimal_schema):
        """Test that pattern_id must be an integer."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 'not_an_int',
                'name': 'test',
                'description': 'test',
                'operation': 'GetItem',
                'parameters': [],
                'return_type': 'single_entity',
            }
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid and any(
            'pattern_id must be an integer' in e.message for e in result.errors
        )

    def test_validate_duplicate_pattern_ids(self, validator, valid_minimal_schema):
        """Test that pattern IDs must be unique across all entities."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'p1',
                'description': 't1',
                'operation': 'GetItem',
                'parameters': [],
                'return_type': 'single_entity',
            },
            {
                'pattern_id': 1,
                'name': 'p2',
                'description': 't2',
                'operation': 'GetItem',
                'parameters': [],
                'return_type': 'single_entity',
            },
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid and any(
            'Duplicate pattern_id' in e.message for e in result.errors
        )

    def test_validate_duplicate_pattern_names(self, validator, valid_minimal_schema):
        """Test that pattern names must be unique within an entity."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'same',
                'description': 't1',
                'operation': 'GetItem',
                'parameters': [],
                'return_type': 'single_entity',
            },
            {
                'pattern_id': 2,
                'name': 'same',
                'description': 't2',
                'operation': 'GetItem',
                'parameters': [],
                'return_type': 'single_entity',
            },
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid and any(
            'Duplicate pattern name' in e.message for e in result.errors
        )

    def test_validate_invalid_enums(self, validator, valid_minimal_schema):
        """Test invalid operation and return_type in one test."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'test',
                'description': 'test',
                'operation': 'InvalidOp',
                'parameters': [],
                'return_type': 'invalid_type',
            }
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid
        assert any('Invalid operation' in e.message for e in result.errors)
        assert any('Invalid return_type' in e.message for e in result.errors)

    def test_validate_parameters_not_list(self, validator, valid_minimal_schema):
        """Test that parameters must be a list."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'test',
                'description': 'test',
                'operation': 'GetItem',
                'parameters': 'not a list',
                'return_type': 'single_entity',
            }
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid and any(
            'parameters must be an array' in e.message for e in result.errors
        )

    def test_validate_parameter_not_dict(self, validator, valid_minimal_schema):
        """Test that each parameter must be a dictionary."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'test',
                'description': 'test',
                'operation': 'GetItem',
                'parameters': ['not a dict'],
                'return_type': 'single_entity',
            }
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid and any(
            'Parameter must be an object' in e.message for e in result.errors
        )

    def test_validate_duplicate_parameter_names(self, validator, valid_minimal_schema):
        """Test that parameter names must be unique within a pattern."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'test',
                'description': 'test',
                'operation': 'GetItem',
                'parameters': [{'name': 'id', 'type': 'string'}, {'name': 'id', 'type': 'string'}],
                'return_type': 'single_entity',
            }
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid and any(
            'Duplicate parameter name' in e.message for e in result.errors
        )

    def test_validate_invalid_parameter_type(self, validator, valid_minimal_schema):
        """Test that parameter type must be valid."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'test',
                'description': 'test',
                'operation': 'GetItem',
                'parameters': [{'name': 'id', 'type': 'invalid_type'}],
                'return_type': 'single_entity',
            }
        ]
        assert not self._validate_schema_dict(validator, valid_minimal_schema).is_valid

    def test_validate_entity_parameter_missing_entity_type(self, validator, valid_minimal_schema):
        """Test that entity parameters must have entity_type."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'test',
                'description': 'test',
                'operation': 'PutItem',
                'parameters': [{'name': 'entity', 'type': 'entity'}],
                'return_type': 'single_entity',
            }
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid and any(
            'Entity parameters must specify entity_type' in e.message for e in result.errors
        )

    def test_validate_entity_reference(self, validator):
        """Test that entity references are validated correctly."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'T', 'partition_key': 'pk', 'sort_key': 'sk'},
                    'entities': {
                        'E1': {
                            'entity_type': 'E1',
                            'pk_template': '{id}',
                            'sk_template': 'E1',
                            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
                            'access_patterns': [
                                {
                                    'pattern_id': 1,
                                    'name': 'create',
                                    'description': 'test',
                                    'operation': 'PutItem',
                                    'parameters': [
                                        {
                                            'name': 'entity',
                                            'type': 'entity',
                                            'entity_type': 'NonExistent',
                                        }
                                    ],
                                    'return_type': 'single_entity',
                                }
                            ],
                        }
                    },
                }
            ]
        }
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid and any(
            "Unknown entity type 'NonExistent'" in e.message for e in result.errors
        )

    def test_validate_duplicate_entity_names_across_tables(self, validator):
        """Test that entity names must be unique across all tables."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'T1', 'partition_key': 'pk'},
                    'entities': {
                        'User': {
                            'entity_type': 'U',
                            'pk_template': '{id}',
                            'sk_template': 'U',
                            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
                            'access_patterns': [],
                        }
                    },
                },
                {
                    'table_config': {'table_name': 'T2', 'partition_key': 'pk'},
                    'entities': {
                        'User': {
                            'entity_type': 'U2',
                            'pk_template': '{id}',
                            'sk_template': 'U',
                            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
                            'access_patterns': [],
                        }
                    },
                },
            ]
        }
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid and any(
            "Duplicate entity name 'User' across tables" in e.message for e in result.errors
        )

    def test_validate_duplicate_table_names(self, validator):
        """Test that table names must be unique across all tables."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Users', 'partition_key': 'pk'},
                    'entities': {
                        'User': {
                            'entity_type': 'USER',
                            'pk_template': '{user_id}',
                            'fields': [{'name': 'user_id', 'type': 'string', 'required': True}],
                            'access_patterns': [],
                        }
                    },
                },
                {
                    'table_config': {'table_name': 'Users', 'partition_key': 'pk'},  # Duplicate!
                    'entities': {
                        'Profile': {
                            'entity_type': 'PROFILE',
                            'pk_template': '{profile_id}',
                            'fields': [{'name': 'profile_id', 'type': 'string', 'required': True}],
                            'access_patterns': [],
                        }
                    },
                },
            ]
        }
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any("Duplicate table name 'Users'" in e.message for e in result.errors)

    def test_validate_file_not_found(self, validator):
        """Test that validation fails gracefully for non-existent files."""
        result = validator.validate_schema_file('/nonexistent/file.json')
        assert not result.is_valid and any(
            'Schema file not found' in e.message for e in result.errors
        )

    def test_validate_invalid_json(self, validator):
        """Test that validation fails gracefully for invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{invalid json}')
            temp_file = f.name
        try:
            result = validator.validate_schema_file(temp_file)
            assert not result.is_valid and any('Invalid JSON' in e.message for e in result.errors)
        finally:
            os.unlink(temp_file)

    def test_format_validation_result_success(self, validator):
        """Test formatting of successful validation result."""
        validator.result = ValidationResult(is_valid=True, errors=[], warnings=[])
        assert '✅ Schema validation passed!' in validator.format_validation_result()

    def test_format_validation_result_with_errors_and_warnings(self, validator):
        """Test formatting of validation result with errors and warnings."""
        errors = [
            ValidationError('test.field', 'Test error', 'suggestion'),
            ValidationError('test.other', 'Another error', None),
        ]
        warnings = [ValidationError('test.warning', 'Test warning', None)]
        validator.result = ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        formatted = validator.format_validation_result()
        assert all(
            x in formatted
            for x in [
                '❌ Schema validation failed',
                'Test error',
                'Another error',
                '💡 suggestion',
                '⚠️  Warnings:',
                'Test warning',
            ]
        )

    def test_convenience_function(self):
        """Test the convenience validate_schema_file function."""
        from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_validator import (
            validate_schema_file,
        )

        assert not validate_schema_file('/nonexistent/file.json').is_valid

    def test_validate_consistent_read_boolean_type(self, validator, valid_minimal_schema):
        """Test that consistent_read must be a boolean type."""
        # Test with string value
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'get_item',
                'description': 'Get item',
                'operation': 'GetItem',
                'consistent_read': 'true',  # String instead of boolean
                'parameters': [{'name': 'id', 'type': 'string'}],
                'return_type': 'single_entity',
            }
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid
        assert any(
            'consistent_read must be a boolean' in e.message and 'Pattern 1' in e.message
            for e in result.errors
        )

    def test_validate_consistent_read_gsi_restriction(self, validator, valid_minimal_schema):
        """Test that consistent_read cannot be true for GSI queries."""
        # Add GSI to table config
        valid_minimal_schema['tables'][0]['gsi_list'] = [
            {
                'name': 'TestIndex',
                'partition_key': 'gsi_pk',
                'sort_key': 'gsi_sk',
            }
        ]
        # Add GSI mapping to entity
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['gsi_mappings'] = [
            {
                'name': 'TestIndex',
                'pk_template': '{id}',
                'sk_template': 'GSI',
            }
        ]
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'query_by_gsi',
                'description': 'Query by GSI',
                'operation': 'Query',
                'index_name': 'TestIndex',
                'consistent_read': True,  # Not allowed for GSI
                'parameters': [{'name': 'id', 'type': 'string'}],
                'return_type': 'entity_list',
            }
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid
        assert any(
            'consistent_read cannot be true for GSI queries' in e.message
            and 'Global Secondary Indexes only support eventually consistent reads' in e.message
            for e in result.errors
        )

    def test_validate_consistent_read_gsi_false_allowed(self, validator, valid_minimal_schema):
        """Test that consistent_read: false is allowed for GSI queries."""
        # Add GSI to table config
        valid_minimal_schema['tables'][0]['gsi_list'] = [
            {
                'name': 'TestIndex',
                'partition_key': 'gsi_pk',
                'sort_key': 'gsi_sk',
            }
        ]
        # Add GSI mapping to entity
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['gsi_mappings'] = [
            {
                'name': 'TestIndex',
                'pk_template': '{id}',
                'sk_template': 'GSI',
            }
        ]
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'query_by_gsi',
                'description': 'Query by GSI',
                'operation': 'Query',
                'index_name': 'TestIndex',
                'consistent_read': False,  # Allowed for GSI
                'parameters': [{'name': 'id', 'type': 'string'}],
                'return_type': 'entity_list',
            }
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert result.is_valid

    def test_validate_consistent_read_main_table_true(self, validator, valid_minimal_schema):
        """Test that consistent_read: true is allowed for main table queries."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'get_item',
                'description': 'Get item',
                'operation': 'GetItem',
                'consistent_read': True,  # Allowed for main table
                'parameters': [{'name': 'id', 'type': 'string'}],
                'return_type': 'single_entity',
            }
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert result.is_valid

    def test_validate_consistent_read_error_includes_pattern_info(
        self, validator, valid_minimal_schema
    ):
        """Test that error messages include pattern_id and pattern_name."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 42,
                'name': 'my_pattern',
                'description': 'Test pattern',
                'operation': 'GetItem',
                'consistent_read': 123,  # Invalid type
                'parameters': [{'name': 'id', 'type': 'string'}],
                'return_type': 'single_entity',
            }
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid
        assert any('Pattern 42' in e.message and 'my_pattern' in e.message for e in result.errors)

    def test_consistent_read_type_error_includes_pattern_id(self, validator, valid_minimal_schema):
        """Test that type validation error messages include pattern_id."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 99,
                'name': 'test_pattern',
                'description': 'Test pattern',
                'operation': 'GetItem',
                'consistent_read': 'invalid',  # Invalid type
                'parameters': [{'name': 'id', 'type': 'string'}],
                'return_type': 'single_entity',
            }
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid
        # Check that error message includes pattern_id
        assert any('Pattern 99' in e.message for e in result.errors), (
            f"Expected 'Pattern 99' in error messages, got: {[e.message for e in result.errors]}"
        )

    def test_consistent_read_type_error_includes_pattern_name(
        self, validator, valid_minimal_schema
    ):
        """Test that type validation error messages include pattern_name."""
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'get_user_by_id',
                'description': 'Test pattern',
                'operation': 'GetItem',
                'consistent_read': 42,  # Invalid type
                'parameters': [{'name': 'id', 'type': 'string'}],
                'return_type': 'single_entity',
            }
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid
        # Check that error message includes pattern_name
        assert any('get_user_by_id' in e.message for e in result.errors), (
            f"Expected 'get_user_by_id' in error messages, got: {[e.message for e in result.errors]}"
        )

    def test_consistent_read_gsi_error_includes_pattern_id(self, validator, valid_minimal_schema):
        """Test that GSI restriction error messages include pattern_id."""
        # Add GSI to table config
        valid_minimal_schema['tables'][0]['gsi_list'] = [
            {
                'name': 'TestIndex',
                'partition_key': 'gsi_pk',
                'sort_key': 'gsi_sk',
            }
        ]
        # Add GSI mapping to entity
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['gsi_mappings'] = [
            {
                'name': 'TestIndex',
                'pk_template': '{id}',
                'sk_template': 'GSI',
            }
        ]
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 77,
                'name': 'query_by_gsi',
                'description': 'Query by GSI',
                'operation': 'Query',
                'index_name': 'TestIndex',
                'consistent_read': True,  # Not allowed for GSI
                'parameters': [{'name': 'id', 'type': 'string'}],
                'return_type': 'entity_list',
            }
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid
        # Check that error message includes pattern_id
        assert any('Pattern 77' in e.message for e in result.errors), (
            f"Expected 'Pattern 77' in error messages, got: {[e.message for e in result.errors]}"
        )

    def test_consistent_read_gsi_error_includes_pattern_name(
        self, validator, valid_minimal_schema
    ):
        """Test that GSI restriction error messages include pattern_name."""
        # Add GSI to table config
        valid_minimal_schema['tables'][0]['gsi_list'] = [
            {
                'name': 'TestIndex',
                'partition_key': 'gsi_pk',
                'sort_key': 'gsi_sk',
            }
        ]
        # Add GSI mapping to entity
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['gsi_mappings'] = [
            {
                'name': 'TestIndex',
                'pk_template': '{id}',
                'sk_template': 'GSI',
            }
        ]
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'query_users_by_email',
                'description': 'Query by GSI',
                'operation': 'Query',
                'index_name': 'TestIndex',
                'consistent_read': True,  # Not allowed for GSI
                'parameters': [{'name': 'id', 'type': 'string'}],
                'return_type': 'entity_list',
            }
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid
        # Check that error message includes pattern_name
        assert any('query_users_by_email' in e.message for e in result.errors), (
            f"Expected 'query_users_by_email' in error messages, got: {[e.message for e in result.errors]}"
        )

    def test_consistent_read_gsi_error_explains_restriction(self, validator, valid_minimal_schema):
        """Test that GSI error message explains the restriction clearly."""
        # Add GSI to table config
        valid_minimal_schema['tables'][0]['gsi_list'] = [
            {
                'name': 'TestIndex',
                'partition_key': 'gsi_pk',
                'sort_key': 'gsi_sk',
            }
        ]
        # Add GSI mapping to entity
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['gsi_mappings'] = [
            {
                'name': 'TestIndex',
                'pk_template': '{id}',
                'sk_template': 'GSI',
            }
        ]
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'query_by_gsi',
                'description': 'Query by GSI',
                'operation': 'Query',
                'index_name': 'TestIndex',
                'consistent_read': True,  # Not allowed for GSI
                'parameters': [{'name': 'id', 'type': 'string'}],
                'return_type': 'entity_list',
            }
        ]
        result = self._validate_schema_dict(validator, valid_minimal_schema)
        assert not result.is_valid
        # Check that error message explains the GSI restriction
        assert any(
            'consistent_read cannot be true for GSI queries' in e.message
            and 'Global Secondary Index' in e.message
            and 'eventually consistent reads' in e.message
            for e in result.errors
        ), (
            f'Expected GSI restriction explanation in error messages, got: {[e.message for e in result.errors]}'
        )

    @given(
        consistent_read=st.one_of(
            st.text(),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.lists(st.booleans()),
            st.dictionaries(st.text(), st.booleans()),
            st.none(),
        )
    )
    def test_property_consistent_read_non_boolean_rejected(self, consistent_read):
        """Non-boolean values rejected.

        Test that for any non-boolean value, the schema validator rejects
        the pattern with a type validation error.
        """
        # Create validator and schema without using fixtures
        validator = SchemaValidator()

        valid_minimal_schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'TestTable',
                        'partition_key': 'pk',
                        'sort_key': 'sk',
                    },
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'sk_template': 'ENTITY',
                            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }

        # Create access pattern with non-boolean consistent_read value
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'test_pattern',
                'description': 'Test pattern',
                'operation': 'GetItem',
                'consistent_read': consistent_read,
                'parameters': [{'name': 'id', 'type': 'string'}],
                'return_type': 'single_entity',
            }
        ]

        result = self._validate_schema_dict(validator, valid_minimal_schema)

        # Should fail validation with boolean type error
        assert not result.is_valid
        assert any('consistent_read must be a boolean' in e.message.lower() for e in result.errors)

    @given(
        operation=st.sampled_from(['Query', 'Scan']),
        index_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ''),
    )
    def test_property_gsi_queries_reject_consistent_read_true(self, operation, index_name):
        """Property Test 5: GSI queries reject consistent_read true.

        Test that for any GSI query (with index_name) and consistent_read: true,
        the schema validator rejects the pattern with a validation error explaining
        that GSIs do not support strongly consistent reads.
        """
        # Create validator and schema without using fixtures
        validator = SchemaValidator()

        valid_minimal_schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'TestTable',
                        'partition_key': 'pk',
                        'sort_key': 'sk',
                    },
                    'gsi_list': [
                        {
                            'name': index_name,
                            'partition_key': 'gsi_pk',
                            'sort_key': 'gsi_sk',
                        }
                    ],
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'sk_template': 'ENTITY',
                            'gsi_mappings': [
                                {
                                    'name': index_name,
                                    'pk_template': '{gsi_pk}',
                                    'sk_template': '{gsi_sk}',
                                }
                            ],
                            'fields': [
                                {'name': 'id', 'type': 'string', 'required': True},
                                {'name': 'gsi_pk', 'type': 'string', 'required': True},
                                {'name': 'gsi_sk', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }

        # Create GSI query access pattern with consistent_read: true
        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'test_gsi_query',
                'description': 'Test GSI query',
                'operation': operation,
                'index_name': index_name,
                'consistent_read': True,  # Not allowed for GSI
                'parameters': [{'name': 'gsi_pk', 'type': 'string'}],
                'return_type': 'entity_list',
            }
        ]

        result = self._validate_schema_dict(validator, valid_minimal_schema)

        # Should fail validation with GSI restriction error
        assert not result.is_valid
        assert any(
            'consistent_read cannot be true for GSI queries' in e.message
            and 'Global Secondary Index' in e.message
            for e in result.errors
        )

    @given(
        operation=st.sampled_from(['Query', 'Scan']),
        index_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ''),
        consistent_read=st.one_of(st.just(False), st.none()),
    )
    def test_property_gsi_queries_accept_consistent_read_false_or_omitted(
        self, operation, index_name, consistent_read
    ):
        """GSI queries accept consistent_read false or omitted.

        consistent-read-parameter, Property 6: GSI queries accept consistent_read false or omitted

        Test that for any GSI query (with index_name), if consistent_read is set to false
        or omitted entirely, the schema validator accepts the pattern as valid.
        """
        # Create validator and schema without using fixtures
        validator = SchemaValidator()

        valid_minimal_schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'TestTable',
                        'partition_key': 'pk',
                        'sort_key': 'sk',
                    },
                    'gsi_list': [
                        {
                            'name': index_name,
                            'partition_key': 'gsi_pk',
                            'sort_key': 'gsi_sk',
                        }
                    ],
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'sk_template': 'ENTITY',
                            'gsi_mappings': [
                                {
                                    'name': index_name,
                                    'pk_template': '{gsi_pk}',
                                    'sk_template': '{gsi_sk}',
                                }
                            ],
                            'fields': [
                                {'name': 'id', 'type': 'string', 'required': True},
                                {'name': 'gsi_pk', 'type': 'string', 'required': True},
                                {'name': 'gsi_sk', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }

        # Create GSI query access pattern
        access_pattern = {
            'pattern_id': 1,
            'name': 'test_gsi_query',
            'description': 'Test GSI query',
            'operation': operation,
            'index_name': index_name,
            'parameters': [{'name': 'gsi_pk', 'type': 'string'}],
            'return_type': 'entity_list',
        }

        # Add consistent_read only if not None (to test omitted case)
        if consistent_read is not None:
            access_pattern['consistent_read'] = consistent_read

        valid_minimal_schema['tables'][0]['entities']['TestEntity']['access_patterns'] = [
            access_pattern
        ]

        result = self._validate_schema_dict(validator, valid_minimal_schema)

        # Should pass validation
        assert result.is_valid, (
            f'Expected valid schema but got errors: {[e.message for e in result.errors]}'
        )

    def test_validate_file_permission_error(self, validator):
        """Test handling of file permission errors (line 92)."""
        # Use a path that would trigger a permission/format error
        result = validator.validate_schema_file('/dev/null/nonexistent.json')
        assert not result.is_valid
        assert any('file' in e.path for e in result.errors)

    def test_validate_missing_pk_template_with_guidance(self, validator):
        """Test that missing pk_template provides template-specific guidance (lines 180-181)."""
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'TestTable',
                        'partition_key': 'pk',
                    },
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            # Missing pk_template
                            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        # Check for template-specific guidance
        assert any(
            'template syntax' in e.suggestion.lower() and 'USER#{user_id}' in e.suggestion
            for e in result.errors
        )

    def test_validate_array_field_with_item_type(self, validator):
        """Test that array fields with item_type are valid (lines 241-245)."""
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'TestTable',
                        'partition_key': 'pk',
                    },
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'fields': [
                                {'name': 'id', 'type': 'string', 'required': True},
                                {
                                    'name': 'tags',
                                    'type': 'array',
                                    'item_type': 'string',
                                    'required': False,
                                },
                            ],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }
        result = self._validate_schema_dict(validator, schema)
        # Should pass - array with item_type is valid
        assert result.is_valid

    def test_validate_main_table_range_query_exception_handling(self, validator):
        """Test exception handling in _validate_main_table_range_query (line 593)."""
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'TestTable',
                        'partition_key': 'pk',
                    },
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
                            'access_patterns': [
                                {
                                    'pattern_id': 1,
                                    'name': 'test_range',
                                    'description': 'Test',
                                    'operation': 'Query',
                                    'range_condition': 'invalid_condition',  # Invalid
                                    'parameters': [{'name': 'id', 'type': 'string'}],
                                    'return_type': 'entity_list',
                                }
                            ],
                        }
                    },
                }
            ]
        }
        result = self._validate_schema_dict(validator, schema)
        # Should have validation errors for invalid range condition
        assert not result.is_valid

    def test_validate_gsi_configuration_exception_handling(self, validator):
        """Test exception handling in _validate_gsi_configuration (lines 598-600)."""
        # Create a schema with malformed GSI structure that could trigger exceptions
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'TestTable',
                        'partition_key': 'pk',
                    },
                    'gsi_list': 'not_a_list',  # Invalid type
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }
        result = self._validate_schema_dict(validator, schema)
        # Should handle the error gracefully
        assert not result.is_valid

    def test_validate_file_value_error_non_json(self, validator):
        """Test handling of ValueError that's not JSON-related (line 92)."""
        # Create a file with invalid content that triggers ValueError but not JSON error
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('')  # Empty file
            temp_file = f.name

        try:
            result = validator.validate_schema_file(temp_file)
            assert not result.is_valid
            # Should have json or file-related error
            assert any('json' in e.path or 'file' in e.path for e in result.errors)
        finally:
            os.unlink(temp_file)

    def test_validate_entity_type_wrong_type(self, validator):
        """Test that entity_type must be string (lines 241-242)."""
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'TestTable',
                        'partition_key': 'pk',
                    },
                    'entities': {
                        'TestEntity': {
                            'entity_type': 123,  # Wrong type - should be string
                            'pk_template': '{id}',
                            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }
        result = self._validate_schema_dict(validator, schema)
        assert not result.is_valid
        assert any('entity_type' in e.path for e in result.errors)

    def test_validate_range_query_with_range_errors(self, validator):
        """Test range query validation that produces errors (lines 556-557)."""
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'TestTable',
                        'partition_key': 'pk',
                        'sort_key': 'sk',
                    },
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'sk_template': '{timestamp}',
                            'fields': [
                                {'name': 'id', 'type': 'string', 'required': True},
                                {'name': 'timestamp', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [
                                {
                                    'pattern_id': 1,
                                    'name': 'test_range',
                                    'description': 'Test',
                                    'operation': 'Query',
                                    'range_condition': 'between',
                                    # Wrong number of parameters for 'between' (needs 3: pk + 2 range)
                                    'parameters': [{'name': 'id', 'type': 'string'}],
                                    'return_type': 'entity_list',
                                }
                            ],
                        }
                    },
                }
            ]
        }
        result = self._validate_schema_dict(validator, schema)
        # Should have validation errors for wrong parameter count
        assert not result.is_valid
        assert any('parameter' in e.message.lower() for e in result.errors)

    def test_validate_range_query_exception_with_malformed_pattern(self, validator):
        """Test exception handling in range query validation (line 593)."""
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'TestTable',
                        'partition_key': 'pk',
                    },
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
                            'access_patterns': [
                                {
                                    'pattern_id': 1,
                                    'name': 'test_range',
                                    'description': 'Test',
                                    'operation': 'Query',
                                    'range_condition': '>',
                                    # Missing required fields to trigger exception
                                    'parameters': None,  # Invalid
                                    'return_type': 'entity_list',
                                }
                            ],
                        }
                    },
                }
            ]
        }
        result = self._validate_schema_dict(validator, schema)
        # Should handle exception gracefully
        assert not result.is_valid

    def test_validate_gsi_with_exception_in_validation(self, validator):
        """Test exception handling in GSI validation (lines 598-600)."""
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'TestTable',
                        'partition_key': 'pk',
                    },
                    'gsi_list': [
                        {
                            'name': 'TestGSI',
                            'partition_key': 'gsi_pk',
                            # Malformed structure that might cause issues
                        }
                    ],
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'gsi_mappings': [
                                {
                                    'name': 'TestGSI',
                                    'pk_template': '{gsi_field}',
                                }
                            ],
                            'fields': [
                                {'name': 'id', 'type': 'string', 'required': True},
                                # Missing gsi_field referenced in template
                            ],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }
        result = self._validate_schema_dict(validator, schema)
        # Should have validation errors
        assert not result.is_valid
