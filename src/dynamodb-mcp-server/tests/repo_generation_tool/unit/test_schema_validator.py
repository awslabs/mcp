"""Unit tests for SchemaValidator class."""

import json
import pytest
import tempfile
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    ValidationError,
    ValidationResult,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_validator import (
    SchemaValidator,
)


@pytest.mark.unit
class TestSchemaValidator:
    """Unit tests for SchemaValidator class - fast, isolated tests."""

    @pytest.fixture
    def validator(self):
        """Create a SchemaValidator instance for testing."""
        return SchemaValidator()

    def _validate_schema_dict(self, validator, schema_dict):
        """Helper method to validate a schema dictionary."""
        import os

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

    def test_validate_file_not_found(self, validator):
        """Test that validation fails gracefully for non-existent files."""
        result = validator.validate_schema_file('/nonexistent/file.json')
        assert not result.is_valid and any(
            'Schema file not found' in e.message for e in result.errors
        )

    def test_validate_invalid_json(self, validator):
        """Test that validation fails gracefully for invalid JSON."""
        import os

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
