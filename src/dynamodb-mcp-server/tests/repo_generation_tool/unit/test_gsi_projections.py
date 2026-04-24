"""Unit tests for GSI projection support."""

import json
import tempfile
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.gsi_validator import (
    GSIValidator,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    VALID_GSI_PROJECTION_TYPES,
    GSIProjectionType,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_validator import (
    validate_schema_file,
)
from pathlib import Path


class TestGSIProjectionEnum:
    """Test GSI projection type enum."""

    def test_projection_types_exist(self):
        """Test all projection types are defined."""
        assert GSIProjectionType.ALL.value == 'ALL'
        assert GSIProjectionType.KEYS_ONLY.value == 'KEYS_ONLY'
        assert GSIProjectionType.INCLUDE.value == 'INCLUDE'

    def test_valid_projection_types_constant(self):
        """Test VALID_GSI_PROJECTION_TYPES contains all types."""
        assert 'ALL' in VALID_GSI_PROJECTION_TYPES
        assert 'KEYS_ONLY' in VALID_GSI_PROJECTION_TYPES
        assert 'INCLUDE' in VALID_GSI_PROJECTION_TYPES
        assert len(VALID_GSI_PROJECTION_TYPES) == 3


class TestGSIProjectionValidation:
    """Test GSI projection validation."""

    def test_valid_all_projection(self):
        """Test ALL projection validates successfully."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Test', 'partition_key': 'pk'},
                    'gsi_list': [
                        {'name': 'TestGSI', 'partition_key': 'gsi_pk', 'projection': 'ALL'}
                    ],
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

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(schema, f)
            temp_path = f.name

        try:
            result = validate_schema_file(temp_path)
            assert result.is_valid
            assert len(result.errors) == 0
        finally:
            Path(temp_path).unlink()

    def test_valid_keys_only_projection(self):
        """Test KEYS_ONLY projection validates successfully."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Test', 'partition_key': 'pk'},
                    'gsi_list': [
                        {
                            'name': 'TestGSI',
                            'partition_key': 'gsi_pk',
                            'projection': 'KEYS_ONLY',
                        }
                    ],
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

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(schema, f)
            temp_path = f.name

        try:
            result = validate_schema_file(temp_path)
            assert result.is_valid
            assert len(result.errors) == 0
        finally:
            Path(temp_path).unlink()

    def test_valid_include_projection(self):
        """Test INCLUDE projection with included_attributes validates."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Test', 'partition_key': 'pk'},
                    'gsi_list': [
                        {
                            'name': 'TestGSI',
                            'partition_key': 'gsi_pk',
                            'projection': 'INCLUDE',
                            'included_attributes': ['field1', 'field2'],
                        }
                    ],
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'fields': [
                                {'name': 'id', 'type': 'string', 'required': True},
                                {'name': 'field1', 'type': 'string', 'required': True},
                                {'name': 'field2', 'type': 'string', 'required': True},
                            ],
                            'gsi_mappings': [{'name': 'TestGSI', 'pk_template': '{id}'}],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(schema, f)
            temp_path = f.name

        try:
            result = validate_schema_file(temp_path)
            assert result.is_valid
            assert len(result.errors) == 0
        finally:
            Path(temp_path).unlink()

    def test_invalid_projection_type(self):
        """Test invalid projection type is rejected."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Test', 'partition_key': 'pk'},
                    'gsi_list': [
                        {
                            'name': 'TestGSI',
                            'partition_key': 'gsi_pk',
                            'projection': 'INVALID',
                        }
                    ],
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

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(schema, f)
            temp_path = f.name

        try:
            result = validate_schema_file(temp_path)
            assert not result.is_valid
            assert any('invalid projection' in e.message.lower() for e in result.errors)
        finally:
            Path(temp_path).unlink()

    def test_include_without_attributes(self):
        """Test INCLUDE projection requires included_attributes."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Test', 'partition_key': 'pk'},
                    'gsi_list': [
                        {'name': 'TestGSI', 'partition_key': 'gsi_pk', 'projection': 'INCLUDE'}
                    ],
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

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(schema, f)
            temp_path = f.name

        try:
            result = validate_schema_file(temp_path)
            assert not result.is_valid
            assert any('included_attributes' in e.message.lower() for e in result.errors)
        finally:
            Path(temp_path).unlink()

    def test_keys_only_with_attributes(self):
        """Test KEYS_ONLY rejects included_attributes."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Test', 'partition_key': 'pk'},
                    'gsi_list': [
                        {
                            'name': 'TestGSI',
                            'partition_key': 'gsi_pk',
                            'projection': 'KEYS_ONLY',
                            'included_attributes': ['field1'],
                        }
                    ],
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

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(schema, f)
            temp_path = f.name

        try:
            result = validate_schema_file(temp_path)
            assert not result.is_valid
            assert any(
                'included_attributes' in e.message.lower()
                and 'only allowed for include' in e.message.lower()
                for e in result.errors
            )
        finally:
            Path(temp_path).unlink()

    def test_invalid_included_attribute(self):
        """Test included_attributes must reference valid fields."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Test', 'partition_key': 'pk'},
                    'gsi_list': [
                        {
                            'name': 'TestGSI',
                            'partition_key': 'gsi_pk',
                            'projection': 'INCLUDE',
                            'included_attributes': ['invalid_field'],
                        }
                    ],
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'fields': [
                                {'name': 'id', 'type': 'string', 'required': True},
                                {'name': 'valid_field', 'type': 'string', 'required': True},
                            ],
                            'gsi_mappings': [{'name': 'TestGSI', 'pk_template': '{id}'}],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(schema, f)
            temp_path = f.name

        try:
            result = validate_schema_file(temp_path)
            assert not result.is_valid
            assert any(
                'invalid_field' in e.message and 'not found' in e.message.lower()
                for e in result.errors
            )
        finally:
            Path(temp_path).unlink()

    def test_default_projection_is_all(self):
        """Test projection defaults to ALL when not specified."""
        validator = GSIValidator()
        table_data = {
            'table_config': {'table_name': 'Test', 'partition_key': 'pk'},
            'gsi_list': [{'name': 'TestGSI', 'partition_key': 'gsi_pk'}],
            'entities': {},
        }

        gsi_list, errors = validator._parse_gsi_list(table_data, 'table')
        assert len(errors) == 0
        assert len(gsi_list) == 1
        assert gsi_list[0].projection == 'ALL'

    def test_projection_loaded_correctly(self):
        """Test projection field is loaded from schema."""
        validator = GSIValidator()
        table_data = {
            'table_config': {'table_name': 'Test', 'partition_key': 'pk'},
            'gsi_list': [
                {'name': 'TestGSI', 'partition_key': 'gsi_pk', 'projection': 'KEYS_ONLY'}
            ],
            'entities': {},
        }

        gsi_list, errors = validator._parse_gsi_list(table_data, 'table')
        assert len(errors) == 0
        assert len(gsi_list) == 1
        assert gsi_list[0].projection == 'KEYS_ONLY'

    def test_included_attributes_loaded(self):
        """Test included_attributes are loaded from schema."""
        validator = GSIValidator()
        table_data = {
            'table_config': {'table_name': 'Test', 'partition_key': 'pk'},
            'gsi_list': [
                {
                    'name': 'TestGSI',
                    'partition_key': 'gsi_pk',
                    'projection': 'INCLUDE',
                    'included_attributes': ['field1', 'field2'],
                }
            ],
            'entities': {},
        }

        gsi_list, errors = validator._parse_gsi_list(table_data, 'table')
        assert len(errors) == 0
        assert len(gsi_list) == 1
        assert gsi_list[0].included_attributes == ['field1', 'field2']

    def test_smart_warning_for_required_non_projected_fields(self):
        """Test smart validation warns when INCLUDE has required non-projected fields."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Test', 'partition_key': 'pk'},
                    'gsi_list': [
                        {
                            'name': 'TestGSI',
                            'partition_key': 'gsi_pk',
                            'projection': 'INCLUDE',
                            'included_attributes': ['field1'],
                        }
                    ],
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'fields': [
                                {'name': 'id', 'type': 'string', 'required': True},
                                {'name': 'field1', 'type': 'string', 'required': True},
                                {
                                    'name': 'field2',
                                    'type': 'string',
                                    'required': True,
                                },  # Required but NOT projected
                            ],
                            'gsi_mappings': [{'name': 'TestGSI', 'pk_template': '{id}'}],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(schema, f)
            temp_path = f.name

        try:
            result = validate_schema_file(temp_path)
            # Should be valid but have warnings
            assert result.is_valid
            assert len(result.warnings) > 0
            assert any('field2' in w.message for w in result.warnings)
            assert any(
                'required fields not in included_attributes' in w.message for w in result.warnings
            )
        finally:
            Path(temp_path).unlink()

    def test_no_warning_when_non_projected_fields_optional(self):
        """Test no warning when all non-projected fields are optional."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Test', 'partition_key': 'pk'},
                    'gsi_list': [
                        {
                            'name': 'TestGSI',
                            'partition_key': 'gsi_pk',
                            'projection': 'INCLUDE',
                            'included_attributes': ['field1'],
                        }
                    ],
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'fields': [
                                {'name': 'id', 'type': 'string', 'required': True},
                                {'name': 'field1', 'type': 'string', 'required': True},
                                {
                                    'name': 'field2',
                                    'type': 'string',
                                    'required': False,
                                },  # Optional - safe!
                            ],
                            'gsi_mappings': [{'name': 'TestGSI', 'pk_template': '{id}'}],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(schema, f)
            temp_path = f.name

        try:
            result = validate_schema_file(temp_path)
            # Should be valid with no warnings
            assert result.is_valid
            assert len(result.warnings) == 0
        finally:
            Path(temp_path).unlink()
