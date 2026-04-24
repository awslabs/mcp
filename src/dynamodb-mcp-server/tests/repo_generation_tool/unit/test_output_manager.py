"""Unit tests for OutputManager and related classes."""

import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.output.output_manager import (
    GeneratedFile,
    GenerationResult,
    OutputManager,
)
from pathlib import Path


@pytest.mark.unit
class TestGeneratedFile:
    """Unit tests for GeneratedFile dataclass."""

    def test_generated_file_creation(self):
        """Test that GeneratedFile can be created with all parameters."""
        generated_file = GeneratedFile(
            path='entities.py',
            description='User entity class',
            category='entity',
            content='# Generated entities\nclass User: pass',
            count=1,
        )
        assert generated_file.path == 'entities.py'
        assert 'class User' in generated_file.content
        assert generated_file.description == 'User entity class'
        assert generated_file.category == 'entity'
        assert generated_file.count == 1

    def test_generated_file_minimal(self):
        """Test GeneratedFile creation with minimal required parameters."""
        generated_file = GeneratedFile(path='test.py', description='Test file', category='test')
        assert generated_file.path == 'test.py'
        assert generated_file.content == ''
        assert generated_file.count == 0


@pytest.mark.unit
class TestGenerationResult:
    """Unit tests for GenerationResult dataclass."""

    def test_generation_result_creation(self):
        """Test that GenerationResult can be created with files and mappings."""
        files = [
            GeneratedFile('entities.py', 'Entity classes', 'entities'),
            GeneratedFile('repositories.py', 'Repository classes', 'repositories'),
        ]
        access_pattern_mapping = {
            '1': {'pattern_id': 1, 'name': 'get_user', 'status': 'generated'}
        }
        result = GenerationResult(
            generated_files=files,
            access_pattern_mapping=access_pattern_mapping,
            generator_type='jinja2',
        )
        assert len(result.generated_files) == 2
        assert result.access_pattern_mapping['1']['pattern_id'] == 1
        assert result.generator_type == 'jinja2'


@pytest.mark.unit
class TestOutputManager:
    """Unit tests for OutputManager class."""

    @pytest.fixture
    def output_manager(self, tmp_path):
        """Create an OutputManager instance for testing."""
        return OutputManager(str(tmp_path))

    def test_output_manager_initialization(self, tmp_path):
        """Test OutputManager initialization with custom language."""
        output_manager = OutputManager(str(tmp_path), language='typescript')
        assert output_manager.output_path == Path(tmp_path)
        assert output_manager.language == 'typescript'

    def test_write_generated_files_creates_all_files(self, output_manager, tmp_path):
        """Test that write_generated_files creates all specified files."""
        files = [
            GeneratedFile(
                'entities.py', 'User entity', 'entities', '# User\nclass User:\n    pass\n', 1
            ),
            GeneratedFile(
                'repositories.py',
                'User repo',
                'repositories',
                '# Repo\nclass UserRepository:\n    pass\n',
                1,
            ),
            GeneratedFile(
                'models/base.py', 'Base model', 'support', '# Base\nclass BaseModel:\n    pass\n'
            ),
        ]
        result = GenerationResult(files, {'1': {'pattern_id': 1}}, 'jinja2')
        output_manager.write_generated_files(result)

        assert (tmp_path / 'entities.py').exists()
        assert (tmp_path / 'repositories.py').exists()
        assert (tmp_path / 'models' / 'base.py').exists()
        assert 'class User:' in (tmp_path / 'entities.py').read_text()

    def test_write_files_creates_directories(self, output_manager, tmp_path):
        """Test that nested directories are created automatically."""
        nested_file = GeneratedFile('deep/nested/structure/file.py', 'Nested', 'test', '# Nested')
        result = GenerationResult([nested_file], {}, 'test')
        output_manager.write_generated_files(result)
        assert (tmp_path / 'deep' / 'nested' / 'structure' / 'file.py').exists()

    def test_write_empty_result_creates_mapping_file(self, output_manager, tmp_path):
        """Test that access pattern mapping file is created even with no generated files."""
        import json

        empty_result = GenerationResult([], {'1': {'id': 1}}, 'test')
        output_manager.write_generated_files(empty_result)
        mapping_file = tmp_path / 'access_pattern_mapping.json'
        assert mapping_file.exists()
        mapping_content = json.loads(mapping_file.read_text())
        assert 'access_pattern_mapping' in mapping_content
        assert mapping_content['access_pattern_mapping']['1']['id'] == 1

    def test_overwrite_existing_files(self, output_manager, tmp_path):
        """Test that existing files are overwritten with new content."""
        existing_file = tmp_path / 'entities.py'
        existing_file.write_text('# Old content')
        new_file = GeneratedFile('entities.py', 'Updated', 'entities', '# New content')
        result = GenerationResult([new_file], {}, 'test')
        output_manager.write_generated_files(result)
        assert '# New content' in existing_file.read_text()
        assert '# Old content' not in existing_file.read_text()

    def test_copy_support_file_not_found(self, output_manager, capsys):
        """Test warning is printed when support file is not found."""
        file = GeneratedFile('missing.py', 'Missing', 'test', '')
        result = GenerationResult([file], {}, 'test')
        output_manager.write_generated_files(result)
        captured = capsys.readouterr()
        assert 'Warning: Support file not found' in captured.out

    def test_print_summary_with_categories(self, output_manager, capsys):
        """Test that summary is printed with file categories and counts."""
        files = [
            GeneratedFile('entities.py', '5 entities', 'entities', '#', 5),
            GeneratedFile('repos.py', 'Repos', 'repositories', '#'),
        ]
        result = GenerationResult(files, {'1': {}}, 'test')
        output_manager.write_generated_files(result)
        captured = capsys.readouterr()
        assert 'entities.py: 5 entities' in captured.out
        assert 'repos.py: Repos' in captured.out

    def test_copy_support_file_exists(self, tmp_path, monkeypatch):
        """Test that support files are copied when they exist."""
        from awslabs.dynamodb_mcp_server.repo_generation_tool.output import output_manager

        lang_dir = tmp_path / 'languages' / 'python'
        lang_dir.mkdir(parents=True)
        (lang_dir / 'support.py').write_text('# Support')
        monkeypatch.setattr(
            output_manager, '__file__', str(tmp_path / 'output' / 'output_manager.py')
        )
        output_dir = tmp_path / 'output_test'
        om = OutputManager(str(output_dir), language='python')
        file = GeneratedFile('support.py', 'Support', 'test', '')
        result = GenerationResult([file], {}, 'test')
        om.write_generated_files(result)
        assert (output_dir / 'support.py').exists()
        assert '# Support' in (output_dir / 'support.py').read_text()
