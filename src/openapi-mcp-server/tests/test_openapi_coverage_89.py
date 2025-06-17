"""Tests to achieve 89% coverage by targeting specific uncovered lines in openapi.py."""

import json
import pytest
import tempfile
from awslabs.openapi_mcp_server.utils.openapi import load_openapi_spec
from pathlib import Path
from unittest.mock import patch


class TestOpenAPICoverage89:
    """Tests to achieve 89% coverage."""

    def test_load_openapi_spec_file_not_found(self):
        """Test loading OpenAPI spec from non-existent file."""
        with pytest.raises(FileNotFoundError, match='File not found: /nonexistent/path.json'):
            load_openapi_spec(path='/nonexistent/path.json')

    def test_load_openapi_spec_yaml_without_pyyaml(self):
        """Test loading YAML file when pyyaml is not available."""
        # Create a temporary YAML file
        yaml_content = """
openapi: '3.0.0'
info:
  title: Test API
  version: '1.0.0'
paths:
  /test:
    get:
      responses:
        '200':
          description: OK
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            # Mock yaml import to raise ImportError
            with patch('builtins.__import__') as mock_import:
                def side_effect(name, *args, **kwargs):
                    if name == 'yaml':
                        raise ImportError('No module named yaml')
                    return __import__(name, *args, **kwargs)

                mock_import.side_effect = side_effect

                # This should raise ImportError about pyyaml
                with pytest.raises(ImportError, match="Required dependency 'pyyaml' not installed"):
                    load_openapi_spec(path=temp_path)
        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)

    def test_load_openapi_spec_invalid_yaml(self):
        """Test loading invalid YAML file."""
        # Create a temporary file with invalid YAML
        invalid_yaml = """
openapi: '3.0.0'
info:
  title: Test API
  version: '1.0.0'
paths:
  /test:
    get:
      responses:
        '200':
          description: OK
    invalid_yaml: [unclosed bracket
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name

        try:
            # This should raise ValueError about invalid YAML
            with pytest.raises(ValueError, match='Invalid YAML'):
                load_openapi_spec(path=temp_path)
        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)

    def test_load_openapi_spec_invalid_json_and_yaml_without_pyyaml(self):
        """Test loading invalid JSON when pyyaml is not available."""
        # Create a temporary file with invalid JSON
        invalid_json = '{"invalid": json content}'

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(invalid_json)
            temp_path = f.name

        try:
            # Mock prance to not be available and yaml import to fail
            with patch('awslabs.openapi_mcp_server.utils.openapi.PRANCE_AVAILABLE', False):
                with patch('builtins.__import__') as mock_import:
                    def side_effect(name, *args, **kwargs):
                        if name == 'yaml':
                            raise ImportError('No module named yaml')
                        return __import__(name, *args, **kwargs)

                    mock_import.side_effect = side_effect

                    # This should raise ImportError about pyyaml
                    with pytest.raises(ImportError, match="Required dependency 'pyyaml' not installed"):
                        load_openapi_spec(path=temp_path)
        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)

    def test_load_openapi_spec_prance_exception_fallback(self):
        """Test prance exception handling and fallback to basic parsing."""
        # Create a valid JSON OpenAPI spec
        spec_content = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(spec_content, f)
            temp_path = f.name

        try:
            # Mock prance to be available but raise an exception
            with patch('awslabs.openapi_mcp_server.utils.openapi.PRANCE_AVAILABLE', True):
                with patch('awslabs.openapi_mcp_server.utils.openapi.ResolvingParser') as mock_parser:
                    mock_parser.side_effect = Exception('Prance parsing failed')

                    # Mock logger to capture the warning
                    with patch('awslabs.openapi_mcp_server.utils.openapi.logger') as mock_logger:
                        # This should fall back to basic parsing and succeed
                        result = load_openapi_spec(path=temp_path)

                        # Verify the warning was logged
                        mock_logger.warning.assert_called_with(
                            'Failed to parse with prance: Prance parsing failed. Falling back to basic parsing.'
                        )

                        # Verify the spec was loaded correctly
                        assert result == spec_content
        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)
