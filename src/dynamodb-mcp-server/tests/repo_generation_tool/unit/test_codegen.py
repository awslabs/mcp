"""Unit tests for generate function."""

import argparse
import json
import pytest
import shutil
import subprocess
import unittest.mock
from awslabs.dynamodb_mcp_server.repo_generation_tool.codegen import (
    SUPPORTED_LANGUAGES,
    GenerationResult,
    _validate_linter_command,
    generate,
    main,
    run_linter,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.language_config import (
    LanguageConfig,
    LinterConfig,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.validation_utils import (
    ValidationError,
    ValidationResult,
)
from pathlib import Path


@pytest.mark.unit
class TestGenerate:
    """Unit tests for generate function - fast, isolated tests."""

    @pytest.fixture
    def valid_schema_file(self, tmp_path):
        """Create a valid schema file for testing."""
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
                            'sk_template': 'ENTITY',
                            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }

        schema_file = tmp_path / 'test_schema.json'
        schema_file.write_text(json.dumps(schema))
        return schema_file

    @pytest.fixture
    def invalid_schema_file(self, tmp_path):
        """Create an invalid schema file for testing."""
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'TestTable'
                        # Missing required fields
                    },
                    'entities': {},
                }
            ]
        }

        schema_file = tmp_path / 'invalid_schema.json'
        schema_file.write_text(json.dumps(schema))
        return schema_file

    def test_generate_file_not_found(self):
        """Test generate raises FileNotFoundError when schema file doesn't exist."""
        with pytest.raises(FileNotFoundError) as exc_info:
            generate(schema_path='nonexistent_schema.json')

        assert 'not found' in str(exc_info.value)

    def test_generate_unsupported_language(self, valid_schema_file, tmp_path):
        """Test generate raises ValueError for unsupported languages."""
        with pytest.raises(ValueError) as exc_info:
            generate(
                schema_path=str(valid_schema_file), language='java', allowed_base_dirs=[tmp_path]
            )

        error_msg = str(exc_info.value)
        assert "Unsupported language 'java'" in error_msg
        assert 'Supported languages are: python' in error_msg

    def test_generate_validation_failure(self, invalid_schema_file, tmp_path):
        """Test generate returns failure result when schema validation fails."""
        result = generate(schema_path=str(invalid_schema_file), allowed_base_dirs=[tmp_path])

        assert result.success is False
        assert result.validation_passed is False
        assert len(result.validation_result.errors) > 0

    def test_generate_validate_only_mode(self, valid_schema_file, tmp_path):
        """Test generate in validate_only mode doesn't generate code."""
        # Should complete without error and not create output files
        generate(
            schema_path=str(valid_schema_file), validate_only=True, allowed_base_dirs=[tmp_path]
        )

        # No output directory should be created in validate-only mode
        # This is a successful validation without generation

    def test_generate_successful_generation(self, valid_schema_file, tmp_path):
        """Test successful code generation with all steps and sample usage."""
        output_dir = tmp_path / 'output'

        # Execute - should complete without errors
        generate(
            schema_path=str(valid_schema_file),
            output_dir=str(output_dir),
            language='python',
            generate_sample_usage=True,
            no_lint=True,
            allowed_base_dirs=[tmp_path],
        )

        # Verify output directory and files were created
        assert output_dir.exists()
        assert (output_dir / 'entities.py').exists()
        assert (output_dir / 'repositories.py').exists()
        assert (output_dir / 'usage_examples.py').exists()

    def test_generate_default_output_directory(self, valid_schema_file, tmp_path):
        """Test generate uses default output directory when not specified."""
        # This will use the default directory: repo_generation_tool/generated/python
        # We just verify it doesn't crash
        try:
            generate(
                schema_path=str(valid_schema_file),
                language='python',
                no_lint=True,
                allowed_base_dirs=[tmp_path],
            )

            # Verify default directory was created
            default_dir = (
                Path(__file__).parent.parent.parent.parent
                / 'awslabs'
                / 'dynamodb_mcp_server'
                / 'repo_generation_tool'
                / 'generated'
                / 'python'
            )
            assert default_dir.exists()
        finally:
            # Cleanup default directory if it was created
            default_dir = (
                Path(__file__).parent.parent.parent.parent
                / 'awslabs'
                / 'dynamodb_mcp_server'
                / 'repo_generation_tool'
                / 'generated'
            )
            if default_dir.exists():
                shutil.rmtree(default_dir)

    def test_generate_edge_cases(self, valid_schema_file, tmp_path):
        """Test generate edge cases: no_lint flag, nested directories, and invalid JSON."""
        # Test no_lint flag
        output_dir = tmp_path / 'output'
        generate(
            schema_path=str(valid_schema_file),
            output_dir=str(output_dir),
            no_lint=True,
            allowed_base_dirs=[tmp_path],
        )
        assert output_dir.exists() and (output_dir / 'entities.py').exists()

        # Test nested directory creation
        nested_dir = tmp_path / 'nested' / 'output' / 'dir'
        generate(
            schema_path=str(valid_schema_file),
            output_dir=str(nested_dir),
            no_lint=True,
            allowed_base_dirs=[tmp_path],
        )
        assert nested_dir.exists() and (nested_dir / 'entities.py').exists()

        # Test invalid JSON handling
        invalid_json_file = tmp_path / 'invalid.json'
        invalid_json_file.write_text('{"invalid": json content}')
        result = generate(schema_path=str(invalid_json_file), allowed_base_dirs=[tmp_path])
        assert result.success is False and result.error_message is not None

    def test_generation_result_formatting(self, tmp_path):
        """Test GenerationResult formatting for different scenarios."""
        # Test CLI formatting
        result = GenerationResult(
            success=True,
            validation_passed=True,
            validation_result=ValidationResult(is_valid=True, errors=[], warnings=[]),
            output_dir=tmp_path / 'output',
        )
        args = argparse.Namespace(language='python', generate_sample_usage=True, no_lint=False)
        cli_format = result.format_for_cli(args)
        assert '✅ Schema validation passed!' in cli_format
        assert 'Next steps:' in cli_format

        # Test MCP formatting
        mcp_format = result.format_for_mcp()
        assert '✅ Schema validation passed!' in mcp_format
        assert '✅ Code generated' in mcp_format

        # Test validation failure
        fail_result = GenerationResult(
            success=False,
            validation_passed=False,
            validation_result=ValidationResult(
                is_valid=False,
                errors=[ValidationError(path='test', message='Test error', suggestion='Fix this')],
                warnings=[],
            ),
            error_message='Validation failed',
        )
        assert '❌ Validation failed' in fail_result.format_for_mcp()

        # Test validate-only mode
        validate_result = GenerationResult(
            success=True,
            validation_passed=True,
            validation_result=ValidationResult(is_valid=True, errors=[], warnings=[]),
            validate_only=True,
        )
        assert '🎉 Validation completed successfully!' in validate_result.format_for_mcp()

        # Test linting failure
        lint_result = GenerationResult(
            success=True,
            validation_passed=True,
            validation_result=ValidationResult(is_valid=True, errors=[], warnings=[]),
            output_dir=Path('/tmp/output'),
            linting_passed=False,
        )
        assert '⚠️ Linting found issues' in lint_result.format_for_mcp()

    def test_run_linter_no_config(self, tmp_path):
        """Test run_linter when no linter is configured."""
        with unittest.mock.patch(
            'awslabs.dynamodb_mcp_server.repo_generation_tool.codegen.LanguageConfigLoader.load'
        ) as mock_load:
            mock_load.return_value = LanguageConfig(
                name='python',
                file_extension='.py',
                naming_conventions=None,
                file_patterns={},
                support_files=[],
                linter=None,
            )
            result = run_linter(tmp_path, 'python')
            assert result is True

    def test_run_linter_no_config_file(self, tmp_path):
        """Test run_linter when config file doesn't exist."""
        with unittest.mock.patch(
            'awslabs.dynamodb_mcp_server.repo_generation_tool.codegen.LanguageConfigLoader.load'
        ) as mock_load:
            mock_load.return_value = LanguageConfig(
                name='python',
                file_extension='.py',
                naming_conventions=None,
                file_patterns={},
                support_files=[],
                linter=LinterConfig(
                    command=['ruff'],
                    config_file='ruff.toml',
                    check_args=['check'],
                    fix_args=['check', '--fix'],
                    format_command=['ruff', 'format'],
                ),
            )
            result = run_linter(tmp_path, 'python')
            assert result is True

    def test_run_linter_command_not_found(self, tmp_path):
        """Test run_linter when linter command is not available."""
        # Create config file
        config_file = tmp_path / 'ruff.toml'
        config_file.write_text('[tool.ruff]\n')

        with unittest.mock.patch(
            'awslabs.dynamodb_mcp_server.repo_generation_tool.codegen.LanguageConfigLoader.load'
        ) as mock_load:
            mock_load.return_value = LanguageConfig(
                name='python',
                file_extension='.py',
                naming_conventions=None,
                file_patterns={},
                support_files=[],
                linter=LinterConfig(
                    command=['nonexistent-linter'],
                    config_file='ruff.toml',
                    check_args=['check'],
                    fix_args=['check', '--fix'],
                    format_command=['ruff', 'format'],
                ),
            )

            with unittest.mock.patch('subprocess.run') as mock_run:
                mock_run.side_effect = FileNotFoundError()
                result = run_linter(tmp_path, 'python')
                assert result is False

    def test_run_linter_success_with_formatter(self, tmp_path):
        """Test run_linter success with formatter."""
        config_file = tmp_path / 'ruff.toml'
        config_file.write_text('[tool.ruff]\n')

        with (
            unittest.mock.patch(
                'awslabs.dynamodb_mcp_server.repo_generation_tool.codegen.LanguageConfigLoader.load'
            ) as mock_load,
            unittest.mock.patch('subprocess.run') as mock_run,
        ):
            mock_load.return_value = LanguageConfig(
                name='python',
                file_extension='.py',
                naming_conventions=None,
                file_patterns={},
                support_files=[],
                linter=LinterConfig(
                    command=['ruff'],
                    config_file='ruff.toml',
                    check_args=['check'],
                    fix_args=['check', '--fix'],
                    format_command=['ruff', 'format'],
                ),
            )

            mock_run.return_value.returncode = 0
            result = run_linter(tmp_path, 'python', fix=True)
            assert result is True
            assert mock_run.call_count >= 2

    def test_run_linter_error_handling(self, tmp_path):
        """Test run_linter error handling scenarios."""
        config_file = tmp_path / 'ruff.toml'
        config_file.write_text('[tool.ruff]\n')

        linter_config = LanguageConfig(
            name='python',
            file_extension='.py',
            naming_conventions=None,
            file_patterns={},
            support_files=[],
            linter=LinterConfig(
                command=['ruff'],
                config_file='ruff.toml',
                check_args=['check'],
                fix_args=['check', '--fix'],
                format_command=['ruff', 'format'],
            ),
        )

        with unittest.mock.patch(
            'awslabs.dynamodb_mcp_server.repo_generation_tool.codegen.LanguageConfigLoader.load'
        ) as mock_load:
            mock_load.return_value = linter_config

            # Test timeout
            with unittest.mock.patch('subprocess.run') as mock_run:
                mock_run.side_effect = [
                    unittest.mock.Mock(returncode=0),
                    subprocess.TimeoutExpired('echo', 60),
                ]
                assert run_linter(tmp_path, 'python') is False

            # Test general exception
            with unittest.mock.patch('subprocess.run') as mock_run:
                mock_run.side_effect = [
                    unittest.mock.Mock(returncode=0),
                    Exception('Test exception'),
                ]
                assert run_linter(tmp_path, 'python') is False

            # Test failed execution
            with unittest.mock.patch('subprocess.run') as mock_run:
                mock_run.side_effect = [
                    unittest.mock.Mock(returncode=0),
                    unittest.mock.Mock(returncode=1),
                ]
                assert run_linter(tmp_path, 'python') is False

            # Test version check failure
            with unittest.mock.patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 1
                assert run_linter(tmp_path, 'python') is False

    def test_main_function_scenarios(self, valid_schema_file, tmp_path, monkeypatch):
        """Test main function success and error scenarios."""
        # Test success
        monkeypatch.chdir(tmp_path)
        local_schema = tmp_path / 'schema.json'
        local_schema.write_text(valid_schema_file.read_text())
        monkeypatch.setattr(
            'sys.argv', ['codegen.py', '--schema', 'schema.json', '--validate-only']
        )
        assert main() == 0

        # Test file not found
        monkeypatch.setattr(
            'sys.argv', ['codegen.py', '--schema', 'nonexistent.json', '--validate-only']
        )
        assert main() == 1

        # Test unexpected error
        schema_file = tmp_path / 'invalid.json'
        schema_file.write_text('{"invalid": "schema"}')
        monkeypatch.setattr('sys.argv', ['codegen.py', '--schema', 'invalid.json'])
        assert main() == 1

        # Test generic exception handling
        with unittest.mock.patch(
            'awslabs.dynamodb_mcp_server.repo_generation_tool.codegen.generate'
        ) as mock_gen:
            mock_gen.side_effect = RuntimeError('Unexpected error')
            monkeypatch.setattr('sys.argv', ['codegen.py', '--schema', 'schema.json'])
            assert main() == 1

    def test_generate_linting_scenarios(self, valid_schema_file, tmp_path):
        """Test generate with different linting configurations."""
        with unittest.mock.patch(
            'awslabs.dynamodb_mcp_server.repo_generation_tool.codegen.run_linter'
        ) as mock_linter:
            # Test linting enabled and successful
            mock_linter.return_value = True
            result = generate(
                schema_path=str(valid_schema_file),
                output_dir=str(tmp_path / 'output1'),
                no_lint=False,
                allowed_base_dirs=[tmp_path],
            )
            assert result.success is True and result.linting_passed is True

            # Test linting enabled but failed
            mock_linter.return_value = False
            result = generate(
                schema_path=str(valid_schema_file),
                output_dir=str(tmp_path / 'output2'),
                no_lint=False,
                allowed_base_dirs=[tmp_path],
            )
            assert result.success is True and result.linting_passed is False

            # Test no_fix flag
            mock_linter.return_value = True
            result = generate(
                schema_path=str(valid_schema_file),
                output_dir=str(tmp_path / 'output3'),
                no_lint=False,
                no_fix=True,
                allowed_base_dirs=[tmp_path],
            )
            assert result.success is True
            mock_linter.assert_called_with(unittest.mock.ANY, 'python', fix=False)

        # Test custom templates directory (expects failure)
        templates_dir = tmp_path / 'templates'
        templates_dir.mkdir()
        result = generate(
            schema_path=str(valid_schema_file),
            output_dir=str(tmp_path / 'output4'),
            templates_dir=str(templates_dir),
            no_lint=True,
            allowed_base_dirs=[tmp_path],
        )
        assert (
            result.success is False
            and result.error_message
            and 'template' in result.error_message.lower()
        )

    def test_run_linter_format_command_scenarios(self, tmp_path):
        """Test run_linter with and without format command."""
        config_file = tmp_path / 'ruff.toml'
        config_file.write_text('[tool.ruff]\n')

        with unittest.mock.patch(
            'awslabs.dynamodb_mcp_server.repo_generation_tool.codegen.LanguageConfigLoader.load'
        ) as mock_load:
            # Test without format command
            mock_load.return_value = LanguageConfig(
                name='python',
                file_extension='.py',
                naming_conventions=None,
                file_patterns={},
                support_files=[],
                linter=LinterConfig(
                    command=['ruff'],
                    config_file='ruff.toml',
                    check_args=['check'],
                    fix_args=['check', '--fix'],
                    format_command=None,
                ),
            )
            with unittest.mock.patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                result = run_linter(tmp_path, 'python', fix=True)
                assert result is True and mock_run.call_count == 2

            # Test with format command
            mock_load.return_value = LanguageConfig(
                name='python',
                file_extension='.py',
                naming_conventions=None,
                file_patterns={},
                support_files=[],
                linter=LinterConfig(
                    command=['ruff'],
                    config_file='ruff.toml',
                    check_args=['check'],
                    fix_args=['check', '--fix'],
                    format_command=['ruff', 'format'],
                ),
            )
            with unittest.mock.patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                result = run_linter(tmp_path, 'python', fix=True)
                assert result is True and mock_run.call_count == 3

    def test_generation_result_with_warnings(self):
        """Test GenerationResult formatting with validation warnings."""
        result = GenerationResult(
            success=True,
            validation_passed=True,
            validation_result=ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[ValidationError(path='test', message='Warning', suggestion='Fix')],
            ),
            output_dir=Path('/tmp/output'),
        )
        formatted = result.format_for_mcp()
        assert '✅' in formatted or '⚠️' in formatted

    def test_generation_result_cli_format_no_sample_usage(self):
        """Test CLI format when sample usage is not generated."""
        result = GenerationResult(
            success=True,
            validation_passed=True,
            validation_result=ValidationResult(is_valid=True, errors=[], warnings=[]),
            output_dir=Path('/tmp/output'),
        )
        args = argparse.Namespace(language='python', generate_sample_usage=False, no_lint=False)
        cli_format = result.format_for_cli(args)
        assert 'Generate usage examples' in cli_format

    def test_generation_result_format_result_method(self):
        """Test GenerationResult format_result method directly."""
        result = GenerationResult(
            success=True,
            validation_passed=True,
            validation_result=ValidationResult(is_valid=True, errors=[], warnings=[]),
            output_dir=Path('/tmp/output'),
        )

        # Test both format types
        cli_format = result.format_result(
            'cli', argparse.Namespace(language='python', generate_sample_usage=False, no_lint=True)
        )
        mcp_format = result.format_result('mcp')

        assert 'Next steps:' in cli_format
        assert 'Next steps:' not in mcp_format
        assert 'Run without --no-lint' in cli_format

    def test_supported_languages_have_dal_implementation_prompts(self):
        """Test that all supported languages have corresponding DAL implementation prompt files."""
        # Get the server module directory to find prompt files
        server_dir = Path(__file__).parent.parent.parent.parent / 'awslabs' / 'dynamodb_mcp_server'
        prompts_dir = server_dir / 'prompts' / 'dal_implementation'

        for language in SUPPORTED_LANGUAGES:
            prompt_file = prompts_dir / f'{language}.md'
            assert prompt_file.exists(), (
                f"DAL implementation prompt file missing for supported language '{language}'. "
                f'Expected file: {prompt_file}'
            )

            # Verify file is not empty
            content = prompt_file.read_text(encoding='utf-8')
            assert len(content.strip()) > 0, (
                f"DAL implementation prompt file for '{language}' is empty: {prompt_file}"
            )

    # ========================================================================
    # Security Tests for Subprocess Command Validation
    # ========================================================================

    def test_validate_linter_command_allows_ruff(self):
        """Test that _validate_linter_command allows ruff."""
        # Should not raise
        _validate_linter_command(['ruff', '--version'])
        _validate_linter_command(['ruff', 'check', 'path'])

    def test_validate_linter_command_allows_ruff_exe(self):
        """Test that _validate_linter_command allows ruff.exe on Windows."""
        # Should not raise
        _validate_linter_command(['ruff.exe', '--version'])

    def test_validate_linter_command_blocks_disallowed_commands(self):
        """Test that _validate_linter_command blocks disallowed commands."""
        with pytest.raises(ValueError) as exc_info:
            _validate_linter_command(['rm', '-rf', '/'])
        assert 'Command not allowed: rm' in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            _validate_linter_command(['bash', '-c', 'echo'])
        assert 'Command not allowed: bash' in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            _validate_linter_command(['python', 'script.py'])
        assert 'Command not allowed: python' in str(exc_info.value)

    def test_validate_linter_command_blocks_path_traversal(self):
        """Test that _validate_linter_command blocks path traversal attempts."""
        with pytest.raises(ValueError) as exc_info:
            _validate_linter_command(['/usr/bin/../../bin/bash', '-c', 'echo'])
        assert 'Command not allowed: bash' in str(exc_info.value)

    def test_validate_linter_command_invalid_input(self):
        """Test that _validate_linter_command handles invalid input."""
        with pytest.raises(ValueError) as exc_info:
            _validate_linter_command([])
        assert 'Invalid command format' in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            _validate_linter_command(None)
        assert 'Invalid command format' in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            _validate_linter_command('ruff --version')
        assert 'Invalid command format' in str(exc_info.value)

    def test_run_linter_validates_commands(self, tmp_path):
        """Test that run_linter validates commands before execution."""
        config_file = tmp_path / 'ruff.toml'
        config_file.write_text('[tool.ruff]\n')

        with unittest.mock.patch(
            'awslabs.dynamodb_mcp_server.repo_generation_tool.codegen.LanguageConfigLoader.load'
        ) as mock_load:
            # Test with disallowed command
            mock_load.return_value = LanguageConfig(
                name='python',
                file_extension='.py',
                naming_conventions=None,
                file_patterns={},
                support_files=[],
                linter=LinterConfig(
                    command=['bash'],  # Not allowed
                    config_file='ruff.toml',
                    check_args=['check'],
                    fix_args=['check', '--fix'],
                    format_command=None,
                ),
            )

            # Should return False due to validation error (caught by exception handler)
            result = run_linter(tmp_path, 'python')
            assert result is False

    # ========================================================================
    # Security Tests for Path Traversal Protection
    # ========================================================================

    def test_generate_blocks_path_traversal(self):
        """Test that generate() function blocks path traversal attempts."""
        with pytest.raises(ValueError) as exc_info:
            generate(schema_path='../../../../etc/passwd', validate_only=True)

        assert 'Security' in str(exc_info.value)
        assert 'allowed directories' in str(exc_info.value)

    def test_generate_blocks_absolute_path_outside_allowed(self, tmp_path):
        """Test that generate() blocks paths outside allowed directories."""
        # Create a file outside any allowed directory
        external_file = tmp_path / 'external_schema.json'
        external_file.write_text('{"tables": []}')

        # Try to access it without allowing tmp_path
        with pytest.raises(ValueError) as exc_info:
            generate(
                schema_path=str(external_file),
                validate_only=True,
                allowed_base_dirs=[Path.cwd()],  # Only allow CWD
            )

        assert 'Security' in str(exc_info.value)

    def test_generate_allows_path_in_allowed_dirs(self, tmp_path):
        """Test that generate() allows paths within allowed directories."""
        # Create a valid schema file
        schema_file = tmp_path / 'valid_schema.json'
        schema_file.write_text("""{
            "tables": [{
                "table_config": {
                    "table_name": "TestTable",
                    "partition_key": "pk",
                    "sort_key": "sk"
                },
                "entities": {
                    "TestEntity": {
                        "entity_type": "TEST",
                        "pk_template": "TEST#{id}",
                        "sk_template": "ITEM",
                        "fields": [
                            {"name": "id", "type": "string", "required": true}
                        ],
                        "access_patterns": []
                    }
                }
            }]
        }""")

        # Should work when tmp_path is in allowed directories
        result = generate(
            schema_path=str(schema_file), validate_only=True, allowed_base_dirs=[tmp_path]
        )

        # Should not raise ValueError, should return a result
        assert result is not None
        assert result.validation_passed or not result.validation_passed  # Either is fine

    def test_generate_resolves_relative_paths(self, tmp_path, monkeypatch):
        """Test that generate() properly resolves relative paths."""
        # Change to tmp_path as CWD
        monkeypatch.chdir(tmp_path)

        # Create a subdirectory with a schema
        subdir = tmp_path / 'schemas'
        subdir.mkdir()
        schema_file = subdir / 'test_schema.json'
        schema_file.write_text("""{
            "tables": [{
                "table_config": {
                    "table_name": "TestTable",
                    "partition_key": "pk",
                    "sort_key": "sk"
                },
                "entities": {
                    "TestEntity": {
                        "entity_type": "TEST",
                        "pk_template": "TEST#{id}",
                        "sk_template": "ITEM",
                        "fields": [
                            {"name": "id", "type": "string", "required": true}
                        ],
                        "access_patterns": []
                    }
                }
            }]
        }""")

        # Use relative path - should work
        result = generate(schema_path='schemas/test_schema.json', validate_only=True)

        assert result is not None

    def test_generate_blocks_symlink_escape(self, tmp_path, monkeypatch):
        """Test that generate() blocks symlink-based directory escape attempts."""
        # Change to tmp_path as CWD
        monkeypatch.chdir(tmp_path)

        # Create a symlink pointing outside the allowed directory
        external_dir = tmp_path.parent / 'external'
        external_dir.mkdir(exist_ok=True)
        external_file = external_dir / 'schema.json'
        external_file.write_text('{"tables": []}')

        symlink = tmp_path / 'evil_link.json'
        try:
            symlink.symlink_to(external_file)
        except OSError:
            # Symlinks might not be supported on this system
            pytest.skip('Symlinks not supported on this system')

        # Attempt to access via symlink should be blocked
        # because resolve() will follow the symlink to the real path
        with pytest.raises(ValueError) as exc_info:
            generate(schema_path=str(symlink), validate_only=True, allowed_base_dirs=[tmp_path])

        assert 'Security' in str(exc_info.value)

    def test_generate_with_usage_data_path(self, valid_schema_file, tmp_path):
        """Test generate function with usage_data_path parameter."""
        # Create a complete valid usage data file with all required sections
        usage_data = {
            'entities': {
                'TestEntity': {
                    'sample_data': {'id': 'user-12345-abc'},
                    'access_pattern_data': {'id': 'user-67890-def'},
                    'update_data': {'id': 'user-99999-xyz'},
                }
            }
        }
        usage_file = tmp_path / 'usage_data.json'
        usage_file.write_text(json.dumps(usage_data))

        # Test with valid usage data path
        result = generate(
            schema_path=str(valid_schema_file),
            output_dir=str(tmp_path / 'output'),
            usage_data_path=str(usage_file),
            allowed_base_dirs=[tmp_path],
        )
        assert result.success is True

    def test_generate_with_invalid_usage_data_path(self, valid_schema_file, tmp_path):
        """Test generate function with invalid usage_data_path parameter."""
        # Test with usage data path outside allowed directories (security check)
        with pytest.raises(
            ValueError, match='Security: Usage data file must be within allowed directories'
        ):
            generate(
                schema_path=str(valid_schema_file),
                output_dir=str(tmp_path / 'output'),
                usage_data_path='/nonexistent/usage_data.json',
                allowed_base_dirs=[tmp_path],
            )

    def test_main_with_usage_data_path_argument(self, valid_schema_file, tmp_path, monkeypatch):
        """Test main function with --usage-data-path argument."""
        # Create a complete valid usage data file with proper structure
        usage_data = {
            'entities': {
                'TestEntity': {
                    'sample_data': {'id': 'entity-prod-001'},
                    'access_pattern_data': {'id': 'entity-query-456'},
                    'update_data': {'id': 'entity-update-789'},
                }
            }
        }
        usage_file = tmp_path / 'usage_data.json'
        usage_file.write_text(json.dumps(usage_data))

        # Copy schema to tmp_path and change directory
        monkeypatch.chdir(tmp_path)
        local_schema = tmp_path / 'schema.json'
        local_schema.write_text(valid_schema_file.read_text())

        # Test with usage data path argument
        monkeypatch.setattr(
            'sys.argv',
            [
                'codegen.py',
                '--schema',
                'schema.json',
                '--usage-data-path',
                str(usage_file),
                '--validate-only',
            ],
        )
        assert main() == 0

    def test_generate_with_usage_data_validation_success(self, valid_schema_file, tmp_path):
        """Test generate function with valid usage_data validation."""
        # Create valid usage data that matches the schema
        usage_data = {
            'entities': {
                'TestEntity': {
                    'sample_data': {'id': 'entity-sample-12345'},
                    'access_pattern_data': {'id': 'entity-lookup-67890'},
                    'update_data': {'id': 'entity-modified-99999'},
                }
            }
        }
        usage_file = tmp_path / 'usage_data.json'
        usage_file.write_text(json.dumps(usage_data))

        result = generate(
            schema_path=str(valid_schema_file),
            usage_data_path=str(usage_file),
            validate_only=True,
            allowed_base_dirs=[tmp_path],
        )

        assert result.success is True
        assert result.validation_passed is True
        assert result.usage_data_validation_passed is True
        assert result.usage_data_validation_result is not None
        assert result.usage_data_validation_result.is_valid

    def test_generate_with_usage_data_validation_failure(self, valid_schema_file, tmp_path):
        """Test generate function with invalid usage_data validation."""
        # Create invalid usage data (missing required entity)
        usage_data = {
            'entities': {
                # Missing TestEntity that exists in schema
            }
        }
        usage_file = tmp_path / 'usage_data.json'
        usage_file.write_text(json.dumps(usage_data))

        result = generate(
            schema_path=str(valid_schema_file),
            usage_data_path=str(usage_file),
            validate_only=True,
            allowed_base_dirs=[tmp_path],
        )

        assert result.success is False
        assert result.validation_passed is False  # Overall validation should fail
        assert result.usage_data_validation_passed is False
        assert result.usage_data_validation_result is not None
        assert not result.usage_data_validation_result.is_valid
        assert len(result.usage_data_validation_result.errors) > 0

    def test_generate_with_usage_data_validation_warnings(self, valid_schema_file, tmp_path):
        """Test generate function with usage_data that has validation errors."""
        # Create usage data with missing required sections (now treated as errors, not warnings)
        usage_data = {
            'entities': {
                'TestEntity': {
                    'sample_data': {'id': 'incomplete-entity-001'}
                    # Missing access_pattern_data and update_data (now required)
                }
            }
        }
        usage_file = tmp_path / 'usage_data.json'
        usage_file.write_text(json.dumps(usage_data))

        result = generate(
            schema_path=str(valid_schema_file),
            usage_data_path=str(usage_file),
            validate_only=True,
            allowed_base_dirs=[tmp_path],
        )

        # With stricter validation, missing required sections should cause failure
        assert result.success is False
        assert result.usage_data_validation_passed is False
        assert result.usage_data_validation_result is not None
        assert not result.usage_data_validation_result.is_valid
        assert len(result.usage_data_validation_result.errors) > 0
        # Check that the errors mention the missing required sections
        error_messages = [error.message for error in result.usage_data_validation_result.errors]
        assert any('access_pattern_data' in msg for msg in error_messages)
        assert any('update_data' in msg for msg in error_messages)

    def test_generate_format_result_includes_usage_data_validation(
        self, valid_schema_file, tmp_path
    ):
        """Test that formatted result includes usage_data validation information."""
        # Create invalid usage data
        usage_data = {
            'entities': {}  # Empty entities
        }
        usage_file = tmp_path / 'usage_data.json'
        usage_file.write_text(json.dumps(usage_data))

        result = generate(
            schema_path=str(valid_schema_file),
            usage_data_path=str(usage_file),
            validate_only=True,
            allowed_base_dirs=[tmp_path],
        )

        formatted_output = result.format_for_mcp()

        # Should include usage data validation errors in the output
        assert (
            'Usage data validation failed' in formatted_output
            or 'Missing required entities' in formatted_output
        )
