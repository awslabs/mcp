"""Integration tests for CLI functionality."""

import pytest
import subprocess


@pytest.mark.integration
class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    def _run_cli(self, repo_generation_tool_path, args):
        """Helper to run CLI as a module from project root."""
        project_root = repo_generation_tool_path.parent.parent.parent
        cmd = [
            'uv',
            'run',
            'python',
            '-m',
            'awslabs.dynamodb_mcp_server.repo_generation_tool.codegen',
        ] + args
        return subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)

    def test_cli_help_command(self, repo_generation_tool_path):
        """Test CLI help command works."""
        result = self._run_cli(repo_generation_tool_path, ['--help'])

        assert result.returncode == 0
        assert '--schema' in result.stdout
        assert '--output' in result.stdout
        assert '--generate_sample_usage' in result.stdout
        assert '--validate-only' in result.stdout
        assert '--language' in result.stdout

    def test_cli_with_all_options(self, tmp_path, sample_schemas, repo_generation_tool_path):
        """Test CLI with all available options."""
        output_dir = tmp_path / 'cli_full_options'
        output_dir.mkdir()

        result = self._run_cli(
            repo_generation_tool_path,
            [
                '--schema',
                str(sample_schemas['social_media']),
                '--output',
                str(output_dir),
                '--language',
                'python',
                '--generator',
                'jinja2',
                '--generate_sample_usage',
                '--no-lint',  # Skip linting for faster test
            ],
        )
        assert result.returncode == 0, f'CLI with all options failed: {result.stderr}'

        # Verify expected files were created
        assert (output_dir / 'entities.py').exists()
        assert (output_dir / 'repositories.py').exists()
        assert (output_dir / 'usage_examples.py').exists()  # Due to --generate_sample_usage

    def test_cli_error_handling_nonexistent_schema(self, tmp_path, repo_generation_tool_path):
        """Test CLI error handling with non-existent schema file."""
        output_dir = tmp_path / 'error_test'
        output_dir.mkdir()

        result = self._run_cli(
            repo_generation_tool_path,
            ['--schema', 'non_existent_schema.json', '--output', str(output_dir)],
        )

        assert result.returncode != 0, 'Expected failure for non-existent schema file'
        assert 'not found' in result.stdout.lower() or 'not found' in result.stderr.lower()

    def test_cli_validation_only_mode(self, sample_schemas, repo_generation_tool_path):
        """Test CLI validation-only mode."""
        result = self._run_cli(
            repo_generation_tool_path,
            ['--schema', str(sample_schemas['social_media']), '--validate-only'],
        )

        assert result.returncode == 0, f'Validation-only mode failed: {result.stderr}'
        assert '✅' in result.stdout, 'Should show validation success'
        assert 'Schema validation passed' in result.stdout

    def test_cli_invalid_schema_validation(self, sample_schemas, repo_generation_tool_path):
        """Test CLI validation with invalid schema."""
        result = self._run_cli(
            repo_generation_tool_path,
            ['--schema', str(sample_schemas['invalid_comprehensive']), '--validate-only'],
        )

        assert result.returncode != 0, 'Invalid schema should fail validation'
        assert '❌' in result.stdout, 'Should show validation failure'
        assert 'Schema validation failed' in result.stdout

    def test_cli_custom_output_directory(
        self, tmp_path, sample_schemas, repo_generation_tool_path
    ):
        """Test CLI with custom output directory."""
        custom_output = tmp_path / 'custom' / 'nested' / 'output'

        result = self._run_cli(
            repo_generation_tool_path,
            [
                '--schema',
                str(sample_schemas['social_media']),
                '--output',
                str(custom_output),
                '--no-lint',
            ],
        )

        assert result.returncode == 0, f'Custom output directory failed: {result.stderr}'

        # Verify files were created in custom location
        assert (custom_output / 'entities.py').exists()
        assert (custom_output / 'repositories.py').exists()

    def test_cli_no_lint_option(self, tmp_path, sample_schemas, repo_generation_tool_path):
        """Test CLI --no-lint option."""
        output_dir = tmp_path / 'no_lint_test'
        output_dir.mkdir()

        result = self._run_cli(
            repo_generation_tool_path,
            [
                '--schema',
                str(sample_schemas['social_media']),
                '--output',
                str(output_dir),
                '--no-lint',
            ],
        )

        assert result.returncode == 0, f'No-lint option failed: {result.stderr}'

        # Should not mention linting in output when --no-lint is used
        # (This is a bit implementation-dependent, but generally true)
        assert (output_dir / 'entities.py').exists()
        assert (output_dir / 'repositories.py').exists()

    def test_cli_language_option(self, tmp_path, sample_schemas, repo_generation_tool_path):
        """Test CLI --language option."""
        output_dir = tmp_path / 'language_test'
        output_dir.mkdir()

        # Test with explicit Python language
        result = self._run_cli(
            repo_generation_tool_path,
            [
                '--schema',
                str(sample_schemas['social_media']),
                '--output',
                str(output_dir),
                '--language',
                'python',
                '--no-lint',
            ],
        )

        assert result.returncode == 0, f'Language option failed: {result.stderr}'
        assert (output_dir / 'entities.py').exists()
        assert (output_dir / 'repositories.py').exists()

    def test_cli_generator_option(self, tmp_path, sample_schemas, repo_generation_tool_path):
        """Test CLI --generator option."""
        output_dir = tmp_path / 'generator_test'
        output_dir.mkdir()

        result = self._run_cli(
            repo_generation_tool_path,
            [
                '--schema',
                str(sample_schemas['social_media']),
                '--output',
                str(output_dir),
                '--generator',
                'jinja2',
                '--no-lint',
            ],
        )

        assert result.returncode == 0, f'Generator option failed: {result.stderr}'
        assert (output_dir / 'entities.py').exists()
        assert (output_dir / 'repositories.py').exists()

    def test_cli_output_messages(self, tmp_path, sample_schemas, repo_generation_tool_path):
        """Test that CLI provides informative output messages."""
        output_dir = tmp_path / 'output_messages_test'
        output_dir.mkdir()

        result = self._run_cli(
            repo_generation_tool_path,
            [
                '--schema',
                str(sample_schemas['social_media']),
                '--output',
                str(output_dir),
                '--generate_sample_usage',
            ],
        )

        assert result.returncode == 0

        # Check for expected output messages (updated for new result-based output)
        expected_messages = [
            'Schema validation passed',
            'code generated in',
            'Generation completed successfully',
        ]

        for message in expected_messages:
            assert message in result.stdout, f"Expected message '{message}' not found in output"
