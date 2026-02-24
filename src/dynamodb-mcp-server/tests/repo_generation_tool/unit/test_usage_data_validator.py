"""Unit tests for usage_data_validator module."""

import json
import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.core import file_utils
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.usage_data_validator import (
    UsageDataValidator,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.validation_utils import (
    ValidationResult,
)
from unittest.mock import patch


@pytest.mark.unit
class TestUsageDataValidator:
    """Unit tests for UsageDataValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a UsageDataValidator instance."""
        return UsageDataValidator()

    @pytest.fixture
    def schema_entities(self):
        """Schema entities for testing."""
        return {'User', 'Deal'}

    @pytest.fixture
    def entity_fields(self):
        """Entity fields for testing."""
        return {'User': {'user_id', 'username'}, 'Deal': {'deal_id', 'title'}}

    @pytest.fixture
    def valid_usage_data(self):
        """Valid usage data structure."""
        return {
            'entities': {
                'User': {
                    'sample_data': {'user_id': 'user-123', 'username': 'testuser'},
                    'access_pattern_data': {'user_id': 'sample_user_id'},
                    'update_data': {'username': 'updated_user'},
                },
                'Deal': {
                    'sample_data': {'deal_id': 'deal-456', 'title': 'Test Deal'},
                    'access_pattern_data': {'deal_id': 'sample_deal_id'},
                    'update_data': {'title': 'Updated Deal Title'},
                },
            }
        }

    def test_validate_valid_usage_data(
        self, validator, schema_entities, entity_fields, valid_usage_data, tmp_path
    ):
        """Test validation of valid usage_data."""
        usage_file = tmp_path / 'usage_data.json'
        usage_file.write_text(json.dumps(valid_usage_data))

        result = validator.validate_usage_data_file(
            str(usage_file), schema_entities, entity_fields
        )

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_missing_file(self, validator, schema_entities, entity_fields):
        """Test validation with non-existent usage_data file."""
        result = validator.validate_usage_data_file(
            '/nonexistent/file.json', schema_entities, entity_fields
        )

        assert not result.is_valid
        assert len(result.errors) == 1
        assert 'not found' in result.errors[0].message

    def test_validate_invalid_json(self, validator, schema_entities, entity_fields, tmp_path):
        """Test validation with invalid JSON."""
        usage_file = tmp_path / 'invalid.json'
        usage_file.write_text('{ invalid json }')

        result = validator.validate_usage_data_file(
            str(usage_file), schema_entities, entity_fields
        )

        assert not result.is_valid
        assert len(result.errors) == 1
        assert 'Invalid JSON' in result.errors[0].message

    def test_validate_not_dict(self, validator, schema_entities, entity_fields, tmp_path):
        """Test validation when root is not a dictionary."""
        usage_file = tmp_path / 'not_dict.json'
        usage_file.write_text('[]')

        result = validator.validate_usage_data_file(
            str(usage_file), schema_entities, entity_fields
        )

        assert not result.is_valid
        assert len(result.errors) == 1
        assert 'must be a JSON object' in result.errors[0].message

    def test_validate_missing_entities_key(
        self, validator, schema_entities, entity_fields, tmp_path
    ):
        """Test validation when 'entities' key is missing."""
        usage_data = {'other_key': 'value'}
        usage_file = tmp_path / 'no_entities.json'
        usage_file.write_text(json.dumps(usage_data))

        result = validator.validate_usage_data_file(
            str(usage_file), schema_entities, entity_fields
        )

        assert not result.is_valid
        assert len(result.errors) == 1
        assert "Missing required 'entities' key" in result.errors[0].message

    def test_validate_missing_required_entities(
        self, validator, schema_entities, entity_fields, tmp_path
    ):
        """Test validation when required entities are missing."""
        usage_data = {
            'entities': {
                'User': {
                    'sample_data': {'user_id': 'user-123', 'username': 'testuser'},
                    'access_pattern_data': {'user_id': 'sample_user_id'},
                    'update_data': {'username': 'updated_user'},
                }
                # Missing Deal entity
            }
        }
        usage_file = tmp_path / 'missing_entities.json'
        usage_file.write_text(json.dumps(usage_data))

        result = validator.validate_usage_data_file(
            str(usage_file), schema_entities, entity_fields
        )

        assert not result.is_valid
        assert any('Missing required entities' in error.message for error in result.errors)
        assert any('Deal' in error.message for error in result.errors)

    def test_validate_missing_required_sections(
        self, validator, schema_entities, entity_fields, tmp_path
    ):
        """Test validation when required sections are missing."""
        usage_data = {
            'entities': {
                'User': {
                    'sample_data': {'user_id': 'user-123', 'username': 'testuser'}
                    # Missing access_pattern_data and update_data
                },
                'Deal': {
                    'sample_data': {'deal_id': 'deal-456', 'title': 'Test Deal'},
                    'access_pattern_data': {'deal_id': 'sample_deal_id'},
                    # Missing update_data
                },
            }
        }
        usage_file = tmp_path / 'missing_sections.json'
        usage_file.write_text(json.dumps(usage_data))

        result = validator.validate_usage_data_file(
            str(usage_file), schema_entities, entity_fields
        )

        assert not result.is_valid
        error_messages = [error.message for error in result.errors]
        assert any(
            "Missing required 'access_pattern_data' section" in msg for msg in error_messages
        )
        assert any("Missing required 'update_data' section" in msg for msg in error_messages)

    def test_validate_unknown_entities(
        self, validator, schema_entities, entity_fields, valid_usage_data, tmp_path
    ):
        """Test validation when unknown entities are present."""
        valid_usage_data['entities']['UnknownEntity'] = {
            'sample_data': {'id': 'unknown-123'},
            'access_pattern_data': {'id': 'sample-id'},
            'update_data': {'id': 'updated-id'},
        }

        usage_file = tmp_path / 'unknown_entities.json'
        usage_file.write_text(json.dumps(valid_usage_data))

        result = validator.validate_usage_data_file(
            str(usage_file), schema_entities, entity_fields
        )

        assert not result.is_valid
        assert any('Unknown entities' in error.message for error in result.errors)
        assert any('UnknownEntity' in error.message for error in result.errors)

    def test_validate_invalid_field_names(
        self, validator, schema_entities, entity_fields, tmp_path
    ):
        """Test validation when invalid field names are used."""
        usage_data = {
            'entities': {
                'User': {
                    'sample_data': {
                        'user_id': 'user-123',
                        'username': 'testuser',
                        'invalid_field': 'should_not_exist',
                    },
                    'access_pattern_data': {'user_id': 'sample_user_id', 'usrname': 'typo_field'},
                    'update_data': {'username': 'updated_user'},
                },
                'Deal': {
                    'sample_data': {'deal_id': 'deal-456', 'title': 'Test Deal'},
                    'access_pattern_data': {'deal_id': 'sample_deal_id'},
                    'update_data': {'title': 'Updated Deal Title'},
                },
            }
        }
        usage_file = tmp_path / 'invalid_fields.json'
        usage_file.write_text(json.dumps(usage_data))

        result = validator.validate_usage_data_file(
            str(usage_file), schema_entities, entity_fields
        )

        assert not result.is_valid
        error_messages = [error.message for error in result.errors]
        assert any("Unknown field 'invalid_field'" in msg for msg in error_messages)
        assert any("Unknown field 'usrname'" in msg for msg in error_messages)

    def test_unknown_top_level_keys(self, validator, schema_entities, entity_fields, tmp_path):
        """Test validation with unknown top-level keys."""
        usage_data = {
            'entities': {
                'User': {
                    'sample_data': {'user_id': 'user-123', 'username': 'testuser'},
                    'access_pattern_data': {'user_id': 'sample_user_id'},
                    'update_data': {'username': 'updated_user'},
                },
                'Deal': {
                    'sample_data': {'deal_id': 'deal-456', 'title': 'Test Deal'},
                    'access_pattern_data': {'deal_id': 'sample_deal_id'},
                    'update_data': {'title': 'Updated Deal Title'},
                },
            },
            'description': 'This should not be allowed',
            'unknown_key': 'should_not_exist',
        }
        usage_file = tmp_path / 'unknown_keys.json'
        usage_file.write_text(json.dumps(usage_data))

        result = validator.validate_usage_data_file(
            str(usage_file), schema_entities, entity_fields
        )

        assert not result.is_valid
        error_messages = [error.message for error in result.errors]
        assert any('Unknown top-level keys' in msg for msg in error_messages)

    def test_empty_sample_data_section(self, validator, schema_entities, entity_fields, tmp_path):
        """Test validation when sample_data section is empty."""
        usage_data = {
            'entities': {
                'User': {
                    'sample_data': {},
                    'access_pattern_data': {'user_id': 'sample_user_id'},
                    'update_data': {'username': 'updated_user'},
                },
                'Deal': {
                    'sample_data': {'deal_id': 'deal-456', 'title': 'Test Deal'},
                    'access_pattern_data': {'deal_id': 'sample_deal_id'},
                    'update_data': {'title': 'Updated Deal Title'},
                },
            }
        }
        usage_file = tmp_path / 'empty_sample_data.json'
        usage_file.write_text(json.dumps(usage_data))

        result = validator.validate_usage_data_file(
            str(usage_file), schema_entities, entity_fields
        )

        assert not result.is_valid
        error_messages = [error.message for error in result.errors]
        assert any("Empty 'sample_data' section" in msg for msg in error_messages)

    def test_empty_entities_section(self, validator, schema_entities, entity_fields, tmp_path):
        """Test validation when entities section is empty."""
        usage_data = {'entities': {}}
        usage_file = tmp_path / 'empty_entities.json'
        usage_file.write_text(json.dumps(usage_data))

        result = validator.validate_usage_data_file(
            str(usage_file), schema_entities, entity_fields
        )

        assert not result.is_valid
        assert any('cannot be empty' in error.message for error in result.errors)

    def test_format_validation_result(self, validator):
        """Test the format_validation_result method."""
        # Test successful validation
        validator.result = ValidationResult(is_valid=True, errors=[], warnings=[])
        formatted = validator.format_validation_result()
        assert '✅' in formatted
        assert 'passed' in formatted

        # Test failed validation with errors
        validator.result = ValidationResult(is_valid=False, errors=[], warnings=[])
        validator.result.add_error('test.path', 'Test error message', 'Test suggestion')
        formatted = validator.format_validation_result()
        assert '❌' in formatted
        assert 'failed' in formatted
        assert 'test.path: Test error message' in formatted

    def test_constants_and_immutability(self, validator):
        """Test that class constants are properly defined and immutable."""
        assert isinstance(validator.REQUIRED_SECTIONS, frozenset)
        assert isinstance(validator.KNOWN_TOP_LEVEL_KEYS, frozenset)

        assert 'sample_data' in validator.REQUIRED_SECTIONS
        assert 'access_pattern_data' in validator.REQUIRED_SECTIONS
        assert 'update_data' in validator.REQUIRED_SECTIONS

        assert 'entities' in validator.KNOWN_TOP_LEVEL_KEYS
        assert len(validator.KNOWN_TOP_LEVEL_KEYS) == 1

    def test_entity_not_dict(self, validator, schema_entities, entity_fields, tmp_path):
        """Test validation when entity data is not a dict."""
        usage_data = {
            'entities': {
                'User': 'not_a_dict',
                'Deal': {
                    'sample_data': {'deal_id': 'deal-456', 'title': 'Test Deal'},
                    'access_pattern_data': {'deal_id': 'sample_deal_id'},
                    'update_data': {'title': 'Updated Deal Title'},
                },
            }
        }
        usage_file = tmp_path / 'entity_not_dict.json'
        usage_file.write_text(json.dumps(usage_data))

        result = validator.validate_usage_data_file(
            str(usage_file), schema_entities, entity_fields
        )

        assert not result.is_valid
        assert any('must be an object' in error.message for error in result.errors)

    def test_section_not_dict(self, validator, schema_entities, entity_fields, tmp_path):
        """Test validation when section data is not a dict."""
        usage_data = {
            'entities': {
                'User': {
                    'sample_data': 'not_a_dict',
                    'access_pattern_data': {'user_id': 'sample_user_id'},
                    'update_data': {'username': 'updated_user'},
                },
                'Deal': {
                    'sample_data': {'deal_id': 'deal-456', 'title': 'Test Deal'},
                    'access_pattern_data': {'deal_id': 'sample_deal_id'},
                    'update_data': {'title': 'Updated Deal Title'},
                },
            }
        }
        usage_file = tmp_path / 'section_not_dict.json'
        usage_file.write_text(json.dumps(usage_data))

        result = validator.validate_usage_data_file(
            str(usage_file), schema_entities, entity_fields
        )

        assert not result.is_valid
        assert any('must be an object' in error.message for error in result.errors)

    def test_unknown_section_name(self, validator, schema_entities, entity_fields, tmp_path):
        """Test validation with unknown section name."""
        usage_data = {
            'entities': {
                'User': {
                    'sample_data': {'user_id': 'user-123', 'username': 'testuser'},
                    'access_pattern_data': {'user_id': 'sample_user_id'},
                    'update_data': {'username': 'updated_user'},
                    'unknown_section': {'foo': 'bar'},
                },
                'Deal': {
                    'sample_data': {'deal_id': 'deal-456', 'title': 'Test Deal'},
                    'access_pattern_data': {'deal_id': 'sample_deal_id'},
                    'update_data': {'title': 'Updated Deal Title'},
                },
            }
        }
        usage_file = tmp_path / 'unknown_section.json'
        usage_file.write_text(json.dumps(usage_data))

        result = validator.validate_usage_data_file(
            str(usage_file), schema_entities, entity_fields
        )

        assert not result.is_valid
        assert any("Unknown section 'unknown_section'" in error.message for error in result.errors)

    def test_validate_non_json_value_error(
        self, validator, schema_entities, entity_fields, tmp_path
    ):
        """Test validation with a file that raises ValueError (non-JSON error path, line 70)."""
        usage_file = tmp_path / 'bad.json'
        usage_file.write_text('{"entities": {}}')

        with patch.object(
            file_utils.FileUtils, 'load_json_file', side_effect=ValueError('bad value')
        ):
            result = validator.validate_usage_data_file(
                str(usage_file), schema_entities, entity_fields
            )
        assert not result.is_valid

    def test_validate_empty_entities_dict(
        self, validator, schema_entities, entity_fields, tmp_path
    ):
        """Test validation when entities dict is present but empty (lines 123-126)."""
        usage_data = {'entities': {}}
        usage_file = tmp_path / 'empty_entities.json'
        usage_file.write_text(json.dumps(usage_data))

        result = validator.validate_usage_data_file(
            str(usage_file), schema_entities, entity_fields
        )
        assert not result.is_valid
        assert any('cannot be empty' in error.message for error in result.errors)

    def test_filter_values_section_not_dict(
        self, validator, schema_entities, entity_fields, tmp_path
    ):
        """Test validation when filter_values section is not a dict (lines 196-197)."""
        usage_data = {
            'entities': {
                'User': {
                    'sample_data': {'user_id': 'user-123', 'username': 'testuser'},
                    'access_pattern_data': {'user_id': 'sample_user_id'},
                    'update_data': {'username': 'updated_user'},
                    'filter_values': 'not_a_dict',  # Should be a dict
                },
                'Deal': {
                    'sample_data': {'deal_id': 'deal-456', 'title': 'Test Deal'},
                    'access_pattern_data': {'deal_id': 'sample_deal_id'},
                    'update_data': {'title': 'Updated Deal Title'},
                },
            }
        }
        usage_file = tmp_path / 'bad_filter_values.json'
        usage_file.write_text(json.dumps(usage_data))

        result = validator.validate_usage_data_file(
            str(usage_file), schema_entities, entity_fields
        )
        assert not result.is_valid
        assert any('must be an object' in error.message for error in result.errors)

    def test_filter_values_section_valid_dict_passes(
        self, validator, schema_entities, entity_fields, tmp_path
    ):
        """Test that a valid filter_values dict section passes validation (branch 196->189)."""
        usage_data = {
            'entities': {
                'User': {
                    'sample_data': {'user_id': 'user-123', 'username': 'testuser'},
                    'access_pattern_data': {'user_id': 'sample_user_id'},
                    'update_data': {'username': 'updated_user'},
                    'filter_values': {'excluded_status': 'CANCELLED', 'min_total': 25.0},
                },
                'Deal': {
                    'sample_data': {'deal_id': 'deal-456', 'title': 'Test Deal'},
                    'access_pattern_data': {'deal_id': 'sample_deal_id'},
                    'update_data': {'title': 'Updated Deal Title'},
                },
            }
        }
        usage_file = tmp_path / 'valid_filter_values.json'
        usage_file.write_text(json.dumps(usage_data))

        result = validator.validate_usage_data_file(
            str(usage_file), schema_entities, entity_fields
        )
        assert result.is_valid
