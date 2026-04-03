"""Integration tests for the Python code generation pipeline."""

import json
import pytest
import sys
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_validator import (
    validate_schema_file,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.usage_data_validator import (
    UsageDataValidator,
)
from pathlib import Path
from tests.repo_generation_tool.conftest import (
    INVALID_USAGE_DATA_DIR,
    VALID_USAGE_DATA_DIR,
)


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

    def test_gsi_projection_keys_only_returns_dict(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test KEYS_ONLY projection generates list[dict[str, Any]] return type."""
        result = code_generator(sample_schemas['deals'], generation_output_dir)

        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        repos_content = (generation_output_dir / 'repositories.py').read_text()

        # Check for KEYS_ONLY projection method (get_brand_watchers)
        assert 'def get_brand_watchers' in repos_content
        assert 'list[dict[str, Any]]' in repos_content
        assert 'Projection: KEYS_ONLY' in repos_content

    def test_gsi_projection_include_safe_returns_entity(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test INCLUDE projection returns Entity when all non-projected fields are optional."""
        result = code_generator(sample_schemas['deals'], generation_output_dir)

        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        repos_content = (generation_output_dir / 'repositories.py').read_text()

        # Check for safe INCLUDE projection method (get_watches_by_type)
        assert 'def get_watches_by_type' in repos_content
        assert 'tuple[list[UserWatch], dict | None]' in repos_content
        assert 'Projection: INCLUDE' in repos_content
        assert 'Non-projected optional fields will be None' in repos_content

    def test_gsi_projection_include_unsafe_returns_dict(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test INCLUDE projection returns dict when has required non-projected fields."""
        result = code_generator(sample_schemas['deals'], generation_output_dir)

        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        repos_content = (generation_output_dir / 'repositories.py').read_text()

        # Check for unsafe INCLUDE projection method (get_category_watchers)
        assert 'def get_category_watchers' in repos_content
        assert 'list[dict[str, Any]]' in repos_content
        assert 'Projection: INCLUDE' in repos_content

    def test_gsi_projection_all_returns_entity(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test ALL projection (default) returns Entity."""
        result = code_generator(sample_schemas['deals'], generation_output_dir)

        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        repos_content = (generation_output_dir / 'repositories.py').read_text()

        # Check for ALL projection method (get_deals_by_brand)
        assert 'def get_deals_by_brand' in repos_content
        assert 'tuple[list[Deal], dict | None]' in repos_content

    def test_access_pattern_mapping_includes_projection(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test access_pattern_mapping.json includes projection info."""
        result = code_generator(sample_schemas['deals'], generation_output_dir)

        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        with open(generation_output_dir / 'access_pattern_mapping.json') as f:
            data = json.load(f)
            mapping = data['access_pattern_mapping']

        # Find GSI patterns and check for projection info
        gsi_patterns = [p for p in mapping.values() if p.get('index_name')]

        assert len(gsi_patterns) > 0, 'No GSI patterns found in mapping'

        # Check that GSI patterns have projection info
        for pattern in gsi_patterns:
            assert 'projection' in pattern, f'Pattern {pattern["pattern_id"]} missing projection'

            # Check INCLUDE patterns have projected_attributes
            if pattern['projection'] == 'INCLUDE':
                assert 'projected_attributes' in pattern, (
                    f'INCLUDE pattern {pattern["pattern_id"]} missing projected_attributes'
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
class TestUsageDataValidationIntegration:
    """Integration tests for usage_data validation with real files."""

    def get_schema_entities(self, schema_file_path: str):
        """Helper to extract entities from schema validation."""
        schema_result = validate_schema_file(schema_file_path)
        if not schema_result.is_valid or not schema_result.extracted_entities:
            pytest.fail(
                f"Schema validation failed or didn't extract entities: {schema_result.errors}"
            )
        return schema_result.extracted_entities, schema_result.extracted_entity_fields

    def test_all_valid_usage_data_files_pass_validation(self, sample_schemas, tmp_path):
        """Test that all valid sample usage_data files pass validation."""
        valid_schema_names = [
            'social_media',
            'ecommerce',
            'elearning',
            'gaming_leaderboard',
            'saas',
            'user_analytics',
            'deals',
        ]

        for schema_name in valid_schema_names:
            if schema_name not in sample_schemas:
                continue

            schema_path = sample_schemas[schema_name]

            # Look for corresponding usage data file
            schema_dir_name = Path(schema_path).parent.name
            usage_data_file = (
                VALID_USAGE_DATA_DIR / schema_dir_name / f'{schema_name}_usage_data.json'
            )

            if not usage_data_file.exists():
                continue  # Skip if no usage data file exists

            # Validate usage data directly
            entities, entity_fields = self.get_schema_entities(str(schema_path))
            validator = UsageDataValidator()
            result = validator.validate_usage_data_file(
                str(usage_data_file), entities, entity_fields
            )

            assert result.is_valid, (
                f'Valid usage_data for {schema_name} failed validation: {result.errors}'
            )
            assert len(result.errors) == 0, (
                f'Valid usage_data for {schema_name} should have no errors: {result.errors}'
            )

    def test_comprehensive_invalid_usage_data_scenarios(self, sample_schemas, tmp_path):
        """Test multiple types of invalid usage_data files fail validation appropriately."""
        if 'social_media' not in sample_schemas:
            pytest.skip('social_media schema not available for testing')

        schema_path = sample_schemas['social_media']

        # Test cases: (filename, expected_error_pattern, description)
        test_cases = [
            ('invalid_field_names.json', 'Unknown field', 'Field name validation'),
            ('missing_entities.json', 'Missing required entities', 'Missing entity validation'),
            ('missing_required_sections.json', 'Missing required', 'Missing section validation'),
            ('unknown_entities.json', 'Unknown entities', 'Unknown entity validation'),
            ('unknown_top_level_keys.json', 'Unknown top-level keys', 'Top-level key validation'),
            ('empty_sample_data.json', 'Empty', 'Empty section validation'),
            ('invalid_json_structure.json', 'must be an object', 'JSON structure validation'),
            ('malformed_json.json.txt', 'Invalid JSON', 'JSON syntax validation'),
        ]

        for filename, expected_error, description in test_cases:
            invalid_file = INVALID_USAGE_DATA_DIR / filename
            if not invalid_file.exists():
                continue  # Skip if test file doesn't exist

            # Validate usage data directly
            entities, entity_fields = self.get_schema_entities(str(schema_path))
            validator = UsageDataValidator()
            result = validator.validate_usage_data_file(str(invalid_file), entities, entity_fields)

            # Verify validation fails
            assert not result.is_valid, f'{description} should fail validation'
            assert len(result.errors) > 0, f'{description} should have validation errors'

            # Verify specific error is detected
            error_messages = ' '.join([error.message for error in result.errors])
            assert expected_error in error_messages, (
                f'{description} should contain "{expected_error}" error. '
                f'Actual errors: {error_messages}'
            )

    def test_usage_data_validation_with_different_schemas(self, sample_schemas, tmp_path):
        """Test usage_data validation works correctly with different schema types."""
        # Test with different schema complexities
        schema_test_cases = [
            ('social_media', 'Single table design'),
            ('ecommerce', 'Multi-table design'),
            ('elearning', 'Complex hierarchical design'),
            ('gaming_leaderboard', 'Multi-table with GSIs'),
        ]

        for schema_name, description in schema_test_cases:
            if schema_name not in sample_schemas:
                continue

            schema_path = sample_schemas[schema_name]

            # Look for corresponding usage data file
            schema_dir_name = Path(schema_path).parent.name
            usage_data_file = (
                VALID_USAGE_DATA_DIR / schema_dir_name / f'{schema_name}_usage_data.json'
            )

            if not usage_data_file.exists():
                continue  # Skip if no usage data file exists

            # Validate usage data directly
            entities, entity_fields = self.get_schema_entities(str(schema_path))
            validator = UsageDataValidator()
            result = validator.validate_usage_data_file(
                str(usage_data_file), entities, entity_fields
            )

            assert result.is_valid, (
                f'{description} ({schema_name}) should pass validation: {result.errors}'
            )
            assert len(result.errors) == 0, (
                f'{description} ({schema_name}) should have no errors: {result.errors}'
            )

    def test_usage_data_validation_error_reporting(self, sample_schemas, tmp_path):
        """Test that usage_data validation provides helpful error messages."""
        if 'social_media' not in sample_schemas:
            pytest.skip('social_media schema not available for testing')

        schema_path = sample_schemas['social_media']

        # Create usage_data with multiple types of errors
        invalid_usage_data = {
            'description': 'Should not be allowed',  # Unknown top-level key
            'entities': {
                'UserProfile': {
                    'sample_data': {
                        'user_id': 'user-123',
                        'invalid_field_1': 'error1',  # Unknown field
                        'invalid_field_2': 'error2',  # Another unknown field
                    },
                    # Missing access_pattern_data and update_data sections
                },
                'UnknownEntity': {  # Unknown entity
                    'sample_data': {'id': 'test'},
                    'access_pattern_data': {'id': 'test'},
                    'update_data': {'id': 'test'},
                },
                # Missing Post entity
            },
        }

        usage_data_path = tmp_path / 'multi_error_usage_data.json'
        usage_data_path.write_text(json.dumps(invalid_usage_data, indent=2))

        # Validate usage data directly
        entities, entity_fields = self.get_schema_entities(str(schema_path))
        validator = UsageDataValidator()
        result = validator.validate_usage_data_file(str(usage_data_path), entities, entity_fields)

        # Should fail validation
        assert not result.is_valid
        assert len(result.errors) > 0

        # Should report multiple specific errors
        error_messages = ' '.join([error.message for error in result.errors])
        expected_errors = [
            'Unknown top-level keys',  # Top-level key error
            'Unknown field',  # Field validation errors
            'Unknown entities',  # Unknown entity error
            'Missing required entities',  # Missing entity error
            'Missing required',  # Missing section errors
        ]

        for expected_error in expected_errors:
            assert expected_error in error_messages, (
                f'Should report "{expected_error}" error. Errors: {error_messages}'
            )

    def test_usage_data_auto_detection_robustness(self, sample_schemas, tmp_path):
        """Test that usage_data auto-detection works reliably across all schemas."""
        for schema_name, schema_path in sample_schemas.items():
            if schema_name.startswith('invalid_'):
                continue  # Skip invalid schemas

            # Look for corresponding usage data file
            schema_dir_name = Path(schema_path).parent.name
            usage_data_file = (
                VALID_USAGE_DATA_DIR / schema_dir_name / f'{schema_name}_usage_data.json'
            )

            if not usage_data_file.exists():
                continue  # Skip if no usage data file exists

            # Validate usage data directly
            entities, entity_fields = self.get_schema_entities(str(schema_path))
            validator = UsageDataValidator()
            result = validator.validate_usage_data_file(
                str(usage_data_file), entities, entity_fields
            )

            # Should succeed and validate properly
            assert result.is_valid, f'Auto-detection failed for {schema_name}: {result.errors}'
            assert len(result.errors) == 0, (
                f'Usage data validation should pass for {schema_name}: {result.errors}'
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
