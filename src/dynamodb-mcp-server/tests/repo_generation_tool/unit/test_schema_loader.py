"""Unit tests for SchemaLoader class."""

import json
import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_loader import SchemaLoader
from unittest.mock import MagicMock, mock_open, patch


@pytest.mark.unit
class TestSchemaLoader:
    """Unit tests for SchemaLoader class - high-level public functionality."""

    def test_load_valid_schema_success(self, mock_schema_data):
        """Test loading a valid schema succeeds."""
        with patch(
            'awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_loader.validate_schema_file'
        ) as mock_validate:
            mock_validate.return_value.is_valid = True

            with patch('builtins.open', mock_open(read_data=json.dumps(mock_schema_data))):
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('pathlib.Path.is_file', return_value=True):
                        loader = SchemaLoader('test.json')
                        schema = loader.load_schema()

        assert schema is not None
        assert 'tables' in schema
        assert len(schema['tables']) > 0
        assert 'table_config' in schema['tables'][0]
        assert 'entities' in schema['tables'][0]

    def test_load_invalid_schema_raises_error(self):
        """Test loading an invalid schema raises ValueError."""
        mock_result = MagicMock()
        mock_result.is_valid = False

        with patch(
            'awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_loader.validate_schema_file',
            return_value=mock_result,
        ):
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('pathlib.Path.is_file', return_value=True):
                        loader = SchemaLoader('test.json')
                        with pytest.raises(ValueError, match='Schema validation failed'):
                            loader.load_schema()

    def test_load_nonexistent_file_raises_error(self):
        """Test loading non-existent file raises appropriate error."""
        loader = SchemaLoader('non_existent_file.json')

        with pytest.raises(ValueError, match='Invalid schema path'):
            loader.load_schema()

    def test_security_mode_path_validation(self):
        """Test path validation in security mode (allow_absolute_paths=False)."""
        # Test path traversal blocked
        loader = SchemaLoader('../../../etc/passwd', allow_absolute_paths=False)
        with pytest.raises(ValueError, match='Path traversal detected'):
            loader.load_schema()

        # Test absolute paths blocked
        loader = SchemaLoader('/etc/passwd', allow_absolute_paths=False)
        with pytest.raises(ValueError, match='Absolute paths are not allowed'):
            loader.load_schema()

    def test_schema_properties(self, mock_schema_data):
        """Test schema loading and properties."""
        with patch(
            'awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_loader.validate_schema_file'
        ) as mock_validate:
            mock_validate.return_value.is_valid = True

            with patch('builtins.open', mock_open(read_data=json.dumps(mock_schema_data))):
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('pathlib.Path.is_file', return_value=True):
                        loader = SchemaLoader('test.json')

                        # Test schema property
                        schema = loader.schema
                        assert schema is not None
                        assert 'tables' in schema

                        # Test entities and table_config properties
                        entities = loader.entities
                        table_config = loader.table_config
                        assert entities == {}  # Legacy format compatibility
                        assert table_config == {}  # Legacy format compatibility

    def test_directory_path_raises_error(self):
        """Test that directory path raises appropriate error."""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.is_file', return_value=False):
                loader = SchemaLoader('test_dir')
                with pytest.raises(
                    ValueError, match='Schema path must be a file, not a directory'
                ):
                    loader.load_schema()
