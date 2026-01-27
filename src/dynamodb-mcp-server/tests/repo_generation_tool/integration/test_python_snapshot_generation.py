"""Python snapshot tests for generated code consistency."""

import difflib
import json
import pytest
from pathlib import Path


@pytest.mark.integration
@pytest.mark.snapshot
@pytest.mark.python
class TestPythonSnapshotGeneration:
    """Python snapshot tests to ensure generated code consistency across template changes."""

    def test_social_media_snapshot(self, generation_output_dir, sample_schemas, code_generator):
        """Test that social media generation matches expected snapshot."""
        # Generate code
        result = code_generator(
            sample_schemas['social_media'],
            generation_output_dir,
            generate_sample_usage=True,
            # Enable linting for consistent, high-quality output
        )

        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        # Compare against snapshots
        self._compare_with_snapshot(
            'social_media',
            generation_output_dir,
            [
                'entities.py',
                'repositories.py',
                'usage_examples.py',
                'access_pattern_mapping.json',
                'base_repository.py',
                'ruff.toml',
            ],
            'python',
        )

    def test_ecommerce_snapshot(self, generation_output_dir, sample_schemas, code_generator):
        """Test that ecommerce generation matches expected snapshot."""
        result = code_generator(
            sample_schemas['ecommerce'],
            generation_output_dir,
            generate_sample_usage=True,
            # Enable linting for consistent, high-quality output
        )

        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        self._compare_with_snapshot(
            'ecommerce',
            generation_output_dir,
            [
                'entities.py',
                'repositories.py',
                'usage_examples.py',
                'access_pattern_mapping.json',
                'base_repository.py',
                'ruff.toml',
            ],
            'python',
        )

    def test_elearning_snapshot(self, generation_output_dir, sample_schemas, code_generator):
        """Test that elearning generation matches expected snapshot."""
        result = code_generator(
            sample_schemas['elearning'],
            generation_output_dir,
            generate_sample_usage=True,
            # Enable linting for consistent, high-quality output
        )

        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        self._compare_with_snapshot(
            'elearning',
            generation_output_dir,
            [
                'entities.py',
                'repositories.py',
                'usage_examples.py',
                'access_pattern_mapping.json',
                'base_repository.py',
                'ruff.toml',
            ],
            'python',
        )

    def test_gaming_leaderboard_snapshot(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test that gaming_leaderboard generation matches expected snapshot (numeric sort keys)."""
        result = code_generator(
            sample_schemas['gaming_leaderboard'],
            generation_output_dir,
            generate_sample_usage=True,
            # Enable linting for consistent, high-quality output
        )

        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        self._compare_with_snapshot(
            'gaming_leaderboard',
            generation_output_dir,
            [
                'entities.py',
                'repositories.py',
                'usage_examples.py',
                'access_pattern_mapping.json',
                'base_repository.py',
                'ruff.toml',
            ],
            'python',
        )

    def test_saas_snapshot(self, generation_output_dir, sample_schemas, code_generator):
        """Test that saas generation matches expected snapshot."""
        result = code_generator(
            sample_schemas['saas'],
            generation_output_dir,
            generate_sample_usage=True,
            # Enable linting for consistent, high-quality output
        )

        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        self._compare_with_snapshot(
            'saas',
            generation_output_dir,
            [
                'entities.py',
                'repositories.py',
                'usage_examples.py',
                'access_pattern_mapping.json',
                'base_repository.py',
                'ruff.toml',
            ],
            'python',
        )

    def test_user_analytics_snapshot(self, generation_output_dir, sample_schemas, code_generator):
        """Test that user_analytics generation matches expected snapshot."""
        result = code_generator(
            sample_schemas['user_analytics'],
            generation_output_dir,
            generate_sample_usage=True,
            # Enable linting for consistent, high-quality output
        )

        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        self._compare_with_snapshot(
            'user_analytics',
            generation_output_dir,
            [
                'entities.py',
                'repositories.py',
                'usage_examples.py',
                'access_pattern_mapping.json',
                'base_repository.py',
                'ruff.toml',
            ],
            'python',
        )

    def test_deals_snapshot(self, generation_output_dir, sample_schemas, code_generator):
        """Test that deals generation matches expected snapshot (partition-key-only tables and GSIs)."""
        result = code_generator(
            sample_schemas['deals'],
            generation_output_dir,
            generate_sample_usage=True,
            # Enable linting for consistent, high-quality output
        )

        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        self._compare_with_snapshot(
            'deals',
            generation_output_dir,
            [
                'entities.py',
                'repositories.py',
                'usage_examples.py',
                'access_pattern_mapping.json',
                'base_repository.py',
                'ruff.toml',
            ],
            'python',
        )

    def _compare_with_snapshot(
        self,
        schema_name: str,
        output_dir: Path,
        files_to_compare: list[str],
        language: str = 'python',
    ):
        """Compare generated files with expected snapshots."""
        snapshots_dir = (
            Path(__file__).parent.parent / 'fixtures' / 'expected_outputs' / language / schema_name
        )

        for file_name in files_to_compare:
            generated_file = output_dir / file_name
            snapshot_file = snapshots_dir / file_name

            assert generated_file.exists(), f'Generated file {file_name} not found'

            if not snapshot_file.exists():
                # First run - create snapshot
                self._create_snapshot(snapshot_file, generated_file)
                pytest.skip(
                    f'Created new snapshot for {schema_name}/{file_name}. Re-run tests to validate.'
                )

            # Compare files
            self._assert_files_match(generated_file, snapshot_file, f'{schema_name}/{file_name}')

    def _create_snapshot(self, snapshot_file: Path, generated_file: Path):
        """Create a new snapshot file."""
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)

        if generated_file.suffix == '.json':
            # Pretty-print JSON for better diffs
            with open(generated_file) as f:
                data = json.load(f)
            with open(snapshot_file, 'w') as f:
                json.dump(data, f, indent=2, sort_keys=True)
        else:
            # Copy text files as-is
            snapshot_file.write_text(generated_file.read_text())

        print(f'Created snapshot: {snapshot_file}')

    def _assert_files_match(
        self, generated_file: Path, snapshot_file: Path, file_description: str
    ):
        """Assert that generated file matches snapshot."""
        if generated_file.suffix == '.json':
            # For JSON files, normalize before comparison to handle ordering differences
            self._assert_json_files_match(generated_file, snapshot_file, file_description)
        else:
            # For text files, do direct comparison
            generated_content = generated_file.read_text()
            snapshot_content = snapshot_file.read_text()

            if generated_content != snapshot_content:
                self._fail_with_diff(
                    generated_content, snapshot_content, file_description, snapshot_file
                )

    def _assert_json_files_match(
        self, generated_file: Path, snapshot_file: Path, file_description: str
    ):
        """Assert that JSON files match, ignoring key ordering."""
        import json

        with open(generated_file) as f:
            generated_data = json.load(f)
        with open(snapshot_file) as f:
            snapshot_data = json.load(f)

        # Normalize both by re-serializing with sorted keys
        generated_normalized = json.dumps(generated_data, indent=2, sort_keys=True)
        snapshot_normalized = json.dumps(snapshot_data, indent=2, sort_keys=True)

        if generated_normalized != snapshot_normalized:
            self._fail_with_diff(
                generated_normalized, snapshot_normalized, file_description, snapshot_file
            )

    def _fail_with_diff(
        self,
        generated_content: str,
        snapshot_content: str,
        file_description: str,
        snapshot_file: Path,
    ):
        """Fail with a detailed diff."""
        diff = list(
            difflib.unified_diff(
                snapshot_content.splitlines(keepends=True),
                generated_content.splitlines(keepends=True),
                fromfile=f'snapshot/{file_description}',
                tofile=f'generated/{file_description}',
                n=3,
            )
        )

        diff_text = ''.join(diff)

        # Provide helpful error message
        error_msg = f"""
Generated file {file_description} does not match snapshot.

To update the snapshot (if the change is intentional):
1. Delete the snapshot file: {snapshot_file}
2. Re-run this test to regenerate the snapshot
3. Review the new snapshot and commit if correct

Diff:
{diff_text}
"""
        pytest.fail(error_msg)


@pytest.mark.integration
@pytest.mark.snapshot
@pytest.mark.python
class TestPythonSnapshotManagement:
    """Tests for Python snapshot management and maintenance."""

    def test_snapshot_directory_structure(self):
        """Test that snapshot directory structure is correct."""
        snapshots_base_dir = Path(__file__).parent.parent / 'fixtures' / 'expected_outputs'

        # Expected language directories
        expected_languages = ['python']  # Add more as languages are supported
        expected_schemas = ['social_media', 'ecommerce', 'elearning', 'gaming_leaderboard', 'saas']

        for language in expected_languages:
            language_dir = snapshots_base_dir / language
            if language_dir.exists():
                for schema_name in expected_schemas:
                    schema_dir = language_dir / schema_name
                    if schema_dir.exists():
                        # If snapshot exists, verify it has expected files
                        expected_files = [
                            'entities.py',
                            'repositories.py',
                            'usage_examples.py',
                            'access_pattern_mapping.json',
                            'base_repository.py',
                            'ruff.toml',
                        ]
                        for file_name in expected_files:
                            snapshot_file = schema_dir / file_name
                            if snapshot_file.exists():
                                assert snapshot_file.stat().st_size > 0, (
                                    f'Snapshot {language}/{schema_name}/{file_name} is empty'
                                )

    def test_json_snapshots_are_valid(self):
        """Test that all JSON snapshots are valid JSON."""
        snapshots_base_dir = Path(__file__).parent.parent / 'fixtures' / 'expected_outputs'

        if not snapshots_base_dir.exists():
            pytest.skip('No snapshots directory found')

        json_files = list(snapshots_base_dir.rglob('*.json'))

        for json_file in json_files:
            try:
                with open(json_file) as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(
                    f'Invalid JSON in snapshot {json_file.relative_to(snapshots_base_dir)}: {e}'
                )

    def test_python_snapshots_have_valid_syntax(self):
        """Test that all Python snapshots have valid syntax."""
        snapshots_base_dir = Path(__file__).parent.parent / 'fixtures' / 'expected_outputs'

        if not snapshots_base_dir.exists():
            pytest.skip('No snapshots directory found')

        python_files = list(snapshots_base_dir.rglob('*.py'))

        for python_file in python_files:
            try:
                with open(python_file) as f:
                    content = f.read()
                compile(content, str(python_file), 'exec')
            except SyntaxError as e:
                pytest.fail(
                    f'Syntax error in snapshot {python_file.relative_to(snapshots_base_dir)}: {e}'
                )


# Pytest configuration for snapshot tests
def pytest_configure(config):
    """Configure snapshot test markers."""
    config.addinivalue_line('markers', 'snapshot: Snapshot tests for generated code consistency')


def pytest_collection_modifyitems(config, items):
    """Auto-mark snapshot tests."""
    for item in items:
        if 'snapshot' in str(item.fspath):
            item.add_marker(pytest.mark.snapshot)
