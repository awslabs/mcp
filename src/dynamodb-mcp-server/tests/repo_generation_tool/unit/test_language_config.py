"""Unit tests for LanguageConfig and LanguageConfigLoader classes."""

import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.language_config import (
    LanguageConfig,
    LanguageConfigLoader,
    LinterConfig,
    NamingConventions,
    SupportFile,
)
from unittest.mock import patch


@pytest.mark.unit
class TestLanguageConfig:
    """Unit tests for LanguageConfig dataclass."""

    @pytest.fixture
    def sample_language_config(self):
        """Create a sample LanguageConfig for testing."""
        naming = NamingConventions(
            method_naming='snake_case',
            crud_patterns={
                'create': 'create_{entity_name}',
                'get': 'get_{entity_name}',
                'update': 'update_{entity_name}',
                'delete': 'delete_{entity_name}',
            },
        )

        linter = LinterConfig(
            command=['ruff'],
            check_args=['check'],
            fix_args=['check', '--fix'],
            format_command=['ruff', 'format'],
            config_file='ruff.toml',
        )

        support_file = SupportFile(
            source='base_repository.py',
            dest='base_repository.py',
            description='Base repository class',
            category='base',
        )

        return LanguageConfig(
            name='python',
            file_extension='.py',
            naming_conventions=naming,
            file_patterns={'entities': 'entities.py', 'repositories': 'repositories.py'},
            support_files=[support_file],
            linter=linter,
        )

    def test_language_config_creation_and_properties(self, sample_language_config):
        """Test LanguageConfig creation and property access."""
        config = sample_language_config
        assert config.name == 'python'
        assert config.file_extension == '.py'
        assert config.naming_conventions.method_naming == 'snake_case'
        assert config.linter.command == ['ruff']
        assert config.support_files[0].source == 'base_repository.py'


@pytest.mark.unit
class TestLanguageConfigLoader:
    """Unit tests for LanguageConfigLoader class."""

    def test_load_python_config(self):
        """Test loading Python config using the load method."""
        config = LanguageConfigLoader.load('python')
        assert config.name == 'python'
        assert config.file_extension == '.py'
        assert config.naming_conventions is not None
        assert config.naming_conventions.method_naming == 'snake_case'

    def test_load_nonexistent_language_raises_error(self):
        """Test loading non-existent language raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match='Language configuration not found'):
            LanguageConfigLoader.load('nonexistent_language')

    def test_get_available_languages(self):
        """Test getting available languages."""
        languages = LanguageConfigLoader.get_available_languages()
        assert isinstance(languages, list)
        assert 'python' in languages

    def test_load_with_invalid_path(self):
        """Test that invalid path traversal is blocked."""
        with pytest.raises(ValueError, match='Invalid language'):
            LanguageConfigLoader.load('../../../etc/passwd')

    def test_config_validation_missing_fields(self):
        """Test config validation for missing required fields."""
        with patch('builtins.open'), patch('json.load') as mock_json_load:
            mock_json_load.return_value = {'file_extension': '.py'}
            with pytest.raises(ValueError, match='Missing required fields'):
                LanguageConfigLoader.load('python')
