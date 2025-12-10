"""Integration tests for the Python code generation pipeline."""

import json
import pytest
import sys
from pathlib import Path


@pytest.mark.integration
@pytest.mark.file_generation
@pytest.mark.python
class TestPythonCodeGenerationPipeline:
    """Integration tests for Python code generation pipeline."""

    def test_social_media_app_generation(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test complete generation pipeline for social media app."""
        # Generate code using the fixture
        result = code_generator(
            sample_schemas['social_media'], generation_output_dir, generate_sample_usage=True
        )

        # Assert generation succeeded
        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        # Verify expected files exist
        expected_files = [
            'entities.py',
            'repositories.py',
            'base_repository.py',
            'usage_examples.py',
            'access_pattern_mapping.json',
            'ruff.toml',
        ]

        for file_name in expected_files:
            file_path = generation_output_dir / file_name
            assert file_path.exists(), f'Expected file {file_name} was not generated'
            assert file_path.stat().st_size > 0, f'Generated file {file_name} is empty'

        # Verify Python syntax
        self._verify_python_syntax(generation_output_dir / 'entities.py')
        self._verify_python_syntax(generation_output_dir / 'repositories.py')

        # Verify JSON is valid
        with open(generation_output_dir / 'access_pattern_mapping.json') as f:
            mapping = json.load(f)
            assert 'access_pattern_mapping' in mapping

    def test_ecommerce_multi_table_generation(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test multi-table schema generation."""
        result = code_generator(sample_schemas['ecommerce'], generation_output_dir)

        assert result.returncode == 0, f'Multi-table generation failed: {result.stderr}'

        # Verify entities file contains all expected entities
        entities_content = (generation_output_dir / 'entities.py').read_text()
        expected_entities = [
            'User',
            'UserAddress',
            'Product',
            'ProductCategory',
            'ProductReview',
            'Order',
            'OrderItem',
            'UserOrderHistory',
        ]

        for entity in expected_entities:
            assert f'class {entity}' in entities_content, (
                f'Entity {entity} not found in generated entities'
            )

        # Verify repositories
        repos_content = (generation_output_dir / 'repositories.py').read_text()
        for entity in expected_entities:
            assert f'{entity}Repository' in repos_content, f'Repository for {entity} not found'

    def test_validation_only_mode(self, sample_schemas, code_generator, tmp_path):
        """Test validation-only mode doesn't generate files."""
        # Use a separate tmp directory to ensure no files are created
        validation_dir = tmp_path / 'validation_test'
        validation_dir.mkdir()

        result = code_generator(sample_schemas['social_media'], validation_dir, validate_only=True)

        assert result.returncode == 0, f'Validation failed: {result.stderr}'

        # Verify no code files were generated (only validation ran)
        generated_files = list(validation_dir.glob('*.py'))
        assert len(generated_files) == 0, (
            f'Files were generated in validation-only mode: {generated_files}'
        )

    def test_invalid_schema_handling(self, sample_schemas, code_generator, tmp_path):
        """Test that invalid schemas are properly rejected."""
        invalid_dir = tmp_path / 'invalid_test'
        invalid_dir.mkdir()

        result = code_generator(sample_schemas['invalid_comprehensive'], invalid_dir)

        # Should fail with non-zero exit code
        assert result.returncode != 0, 'Invalid schema should cause generation to fail'

        # Should contain error messages
        assert '❌' in result.stdout or 'error' in result.stderr.lower()

        # Should not generate code files
        generated_files = list(invalid_dir.glob('*.py'))
        assert len(generated_files) == 0, (
            f'Files were generated despite invalid schema: {generated_files}'
        )

    def test_generated_code_imports_successfully(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test that generated code can be imported without errors."""
        # Generate code
        result = code_generator(sample_schemas['social_media'], generation_output_dir)
        assert result.returncode == 0

        # Add generated directory to Python path
        sys.path.insert(0, str(generation_output_dir))

        try:
            # Import generated modules
            import entities  # type: ignore[import-not-found]
            import repositories  # type: ignore[import-not-found]

            # Verify key classes exist
            assert hasattr(entities, 'UserProfile'), 'UserProfile entity not found'
            assert hasattr(entities, 'Post'), 'Post entity not found'
            assert hasattr(repositories, 'UserProfileRepository'), (
                'UserProfileRepository not found'
            )
            assert hasattr(repositories, 'PostRepository'), 'PostRepository not found'

            # Verify classes can be instantiated (basic smoke test)
            user_profile = entities.UserProfile(
                user_id='test123',
                username='testuser',
                email='test@example.com',
                timestamp=1234567890,
            )
            assert user_profile.user_id == 'test123'

        finally:
            # Clean up Python path
            sys.path.remove(str(generation_output_dir))

            # Remove imported modules from cache to avoid conflicts
            modules_to_remove = [
                name for name in sys.modules.keys() if name in ['entities', 'repositories']
            ]
            for module_name in modules_to_remove:
                del sys.modules[module_name]

    def test_multiple_schemas_parallel(self, tmp_path, sample_schemas, code_generator):
        """Test generating multiple schemas in parallel directories."""
        schemas_to_test = ['social_media', 'elearning']
        results = {}

        for schema_name in schemas_to_test:
            output_dir = tmp_path / f'{schema_name}_output'
            output_dir.mkdir()

            result = code_generator(
                sample_schemas[schema_name], output_dir, no_lint=True
            )  # Skip linting for speed
            results[schema_name] = (result, output_dir)

        # Verify all generations succeeded
        for schema_name, (result, output_dir) in results.items():
            assert result.returncode == 0, f'Generation failed for {schema_name}: {result.stderr}'
            assert (output_dir / 'entities.py').exists(), f'entities.py missing for {schema_name}'
            assert (output_dir / 'repositories.py').exists(), (
                f'repositories.py missing for {schema_name}'
            )

    def _verify_python_syntax(self, file_path: Path):
        """Verify Python file has valid syntax."""
        with open(file_path) as f:
            content = f.read()

        try:
            compile(content, str(file_path), 'exec')
        except SyntaxError as e:
            pytest.fail(f'Syntax error in {file_path}: {e}')


@pytest.mark.integration
class TestSchemaValidationIntegration:
    """Integration tests for schema validation with real files."""

    def test_all_valid_schemas_pass_validation(self, sample_schemas, code_generator, tmp_path):
        """Test that all valid sample schemas pass validation."""
        valid_schema_names = [
            'social_media',
            'ecommerce',
            'elearning',
            'gaming_leaderboard',
            'saas',
        ]

        for schema_name in valid_schema_names:
            if schema_name not in sample_schemas:
                continue

            validation_dir = tmp_path / f'validation_{schema_name}'
            validation_dir.mkdir()

            result = code_generator(
                sample_schemas[schema_name], validation_dir, validate_only=True
            )

            assert result.returncode == 0, (
                f'Valid schema {schema_name} failed validation: {result.stderr}'
            )
            assert '✅' in result.stdout, (
                f'Valid schema {schema_name} should show success indicator'
            )

    def test_all_invalid_schemas_fail_validation(self, sample_schemas, code_generator, tmp_path):
        """Test that all invalid sample schemas fail validation."""
        invalid_schema_names = [
            'invalid_comprehensive',
            'invalid_entity_ref',
            'invalid_cross_table',
        ]

        for schema_name in invalid_schema_names:
            if schema_name not in sample_schemas:
                continue

            validation_dir = tmp_path / f'validation_{schema_name}'
            validation_dir.mkdir()

            result = code_generator(
                sample_schemas[schema_name], validation_dir, validate_only=True
            )

            assert result.returncode != 0, f'Invalid schema {schema_name} should fail validation'
            assert '❌' in result.stdout, (
                f'Invalid schema {schema_name} should show error indicator'
            )


@pytest.mark.integration
@pytest.mark.slow
class TestComprehensiveGeneration:
    """Slower, more comprehensive integration tests."""

    def test_all_sample_schemas_generation(self, tmp_path, sample_schemas, code_generator):
        """Test generation for all available valid sample schemas."""
        valid_schemas = ['social_media', 'ecommerce', 'elearning', 'gaming_leaderboard', 'saas']

        for schema_name in valid_schemas:
            if schema_name not in sample_schemas:
                continue

            output_dir = tmp_path / f'comprehensive_{schema_name}'
            output_dir.mkdir()

            result = code_generator(
                sample_schemas[schema_name], output_dir, generate_sample_usage=True
            )
            assert result.returncode == 0, (
                f'Comprehensive test failed for {schema_name}: {result.stderr}'
            )

            # Verify basic files exist
            assert (output_dir / 'entities.py').exists()
            assert (output_dir / 'repositories.py').exists()
            assert (output_dir / 'usage_examples.py').exists()
            assert (output_dir / 'access_pattern_mapping.json').exists()


@pytest.mark.integration
class TestPerformanceOptimizedGeneration:
    """Tests using pre-generated outputs for performance."""

    def test_with_pre_generated_output(self, pre_generated_social_media):
        """Test using pre-generated output for faster execution."""
        # Use the pre-generated output from the class-scoped fixture
        assert (pre_generated_social_media / 'entities.py').exists()
        assert (pre_generated_social_media / 'repositories.py').exists()

        # Run tests on the pre-generated content
        entities_content = (pre_generated_social_media / 'entities.py').read_text()
        assert 'class UserProfile' in entities_content
        assert 'class Post' in entities_content
