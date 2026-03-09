"""Integration tests for GSI (Global Secondary Index) pipeline functionality."""

import json
import pytest
import sys
from pathlib import Path


@pytest.mark.integration
@pytest.mark.file_generation
@pytest.mark.python
class TestGSIPipelineIntegration:
    """Integration tests for GSI code generation pipeline."""

    def test_user_analytics_gsi_generation(self, generation_output_dir, code_generator):
        """Test complete GSI generation pipeline for user analytics schema."""
        # Get the user analytics schema path
        fixtures_path = Path(__file__).parent.parent / 'fixtures'
        user_analytics_schema = (
            fixtures_path / 'valid_schemas' / 'user_analytics' / 'user_analytics_schema.json'
        )

        # Generate code using the fixture
        result = code_generator(
            user_analytics_schema, generation_output_dir, generate_sample_usage=True
        )

        # Assert generation succeeded
        assert result.returncode == 0, f'GSI generation failed: {result.stderr}'

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

    def test_gsi_entity_structure_generation(self, generation_output_dir, code_generator):
        """Test that GSI entities contain expected GSI key builder methods."""
        fixtures_path = Path(__file__).parent.parent / 'fixtures'
        user_analytics_schema = (
            fixtures_path / 'valid_schemas' / 'user_analytics' / 'user_analytics_schema.json'
        )

        result = code_generator(user_analytics_schema, generation_output_dir)
        assert result.returncode == 0, f'GSI entity generation failed: {result.stderr}'

        # Read generated entities file
        entities_content = (generation_output_dir / 'entities.py').read_text()

        # Verify User entity exists
        assert 'class User' in entities_content, 'User entity not found in generated entities'

        # Verify GSI key builder methods exist (instance methods)
        # Note: GSI names are converted to snake_case for valid Python identifiers
        expected_gsi_instance_methods = [
            'build_gsi_pk_status_index',
            'build_gsi_sk_status_index',
            'build_gsi_pk_location_index',
            'build_gsi_sk_location_index',
            'build_gsi_pk_engagement_index',
            'build_gsi_sk_engagement_index',
            'build_gsi_pk_age_group_index',
            'build_gsi_sk_age_group_index',
        ]

        for method_name in expected_gsi_instance_methods:
            assert method_name in entities_content, (
                f'GSI instance method {method_name} not found in generated entities'
            )

        # Verify lookup builder methods exist (class methods)
        expected_lookup_methods = [
            'build_gsi_pk_for_lookup_status_index',
            'build_gsi_sk_for_lookup_status_index',
            'build_gsi_pk_for_lookup_location_index',
            'build_gsi_sk_for_lookup_location_index',
        ]

        for method_name in expected_lookup_methods:
            assert method_name in entities_content, (
                f'GSI lookup method {method_name} not found in generated entities'
            )

    def test_gsi_repository_method_generation(self, generation_output_dir, code_generator):
        """Test that GSI repositories contain expected query method stubs."""
        fixtures_path = Path(__file__).parent.parent / 'fixtures'
        user_analytics_schema = (
            fixtures_path / 'valid_schemas' / 'user_analytics' / 'user_analytics_schema.json'
        )

        result = code_generator(user_analytics_schema, generation_output_dir)
        assert result.returncode == 0, f'GSI repository generation failed: {result.stderr}'

        # Read generated repositories file
        repos_content = (generation_output_dir / 'repositories.py').read_text()

        # Verify UserRepository exists
        assert 'class UserRepository' in repos_content, (
            'UserRepository not found in generated repositories'
        )

        # Verify GSI query method stubs exist
        expected_gsi_methods = [
            'get_active_users',
            'get_recent_active_users',
            'get_users_by_location',
            'get_users_by_country_prefix',
            'get_users_by_engagement_level',
            'get_highly_engaged_users_by_session_range',
            'get_users_by_age_group',
            'get_recent_signups_by_age_group',
            'get_users_signup_date_range',
        ]

        for method_name in expected_gsi_methods:
            assert f'def {method_name}' in repos_content, (
                f'GSI method {method_name} not found in generated repositories'
            )

        # Verify method signatures contain proper parameters (including pagination)
        # Note: ruff may reformat long lines, so we check for key components
        assert 'def get_recent_active_users(' in repos_content
        assert 'status: str' in repos_content
        assert 'limit: int = 100' in repos_content
        assert 'exclusive_start_key: dict | None = None' in repos_content
        assert 'skip_invalid_items: bool = True' in repos_content
        assert 'def get_highly_engaged_users_by_session_range' in repos_content

    def test_gsi_method_documentation_generation(self, generation_output_dir, code_generator):
        """Test that GSI methods contain rich documentation with metadata."""
        fixtures_path = Path(__file__).parent.parent / 'fixtures'
        user_analytics_schema = (
            fixtures_path / 'valid_schemas' / 'user_analytics' / 'user_analytics_schema.json'
        )

        result = code_generator(user_analytics_schema, generation_output_dir)
        assert result.returncode == 0, f'GSI documentation generation failed: {result.stderr}'

        repos_content = (generation_output_dir / 'repositories.py').read_text()

        # Verify documentation contains index information
        assert 'Index: StatusIndex (GSI)' in repos_content, 'StatusIndex documentation not found'
        assert 'Index: LocationIndex (GSI)' in repos_content, (
            'LocationIndex documentation not found'
        )
        assert 'Index: EngagementIndex (GSI)' in repos_content, (
            'EngagementIndex documentation not found'
        )
        assert 'Index: AgeGroupIndex (GSI)' in repos_content, (
            'AgeGroupIndex documentation not found'
        )

        # Verify range condition documentation
        assert 'Range Condition: >=' in repos_content, 'Range condition >= documentation not found'
        assert 'Range Condition: begins_with' in repos_content, (
            'Range condition begins_with documentation not found'
        )
        assert 'Range Condition: between' in repos_content, (
            'Range condition between documentation not found'
        )

        # Verify implementation hints in comments (Key Conditions moved to comments)
        assert '# Operation: Query | Index:' in repos_content, (
            'Operation documentation not found in comments'
        )
        # Key conditions are now in implementation examples, not in separate documentation
        assert 'build_gsi_pk_for_lookup' in repos_content, (
            'GSI key builder methods not found in implementation hints'
        )

    def test_gsi_sample_data_generation(self, generation_output_dir, code_generator):
        """Test that sample data includes GSI field values."""
        fixtures_path = Path(__file__).parent.parent / 'fixtures'
        user_analytics_schema = (
            fixtures_path / 'valid_schemas' / 'user_analytics' / 'user_analytics_schema.json'
        )

        result = code_generator(
            user_analytics_schema, generation_output_dir, generate_sample_usage=True
        )
        assert result.returncode == 0, f'GSI sample generation failed: {result.stderr}'

        # Read generated usage examples
        usage_content = (generation_output_dir / 'usage_examples.py').read_text()

        # Verify sample data contains GSI-required fields
        gsi_required_fields = [
            'status=',
            'last_active=',
            'country=',
            'city=',
            'engagement_level=',
            'session_count=',
            'age_group=',
            'signup_date=',
        ]

        for field in gsi_required_fields:
            assert field in usage_content, f'GSI field {field} not found in sample data'

        # Verify GSI query examples exist
        expected_gsi_examples = [
            'get_active_users',
            'get_users_by_location',
            'get_users_by_engagement_level',
            'get_users_by_age_group',
        ]

        for example in expected_gsi_examples:
            assert example in usage_content, f'GSI example {example} not found in usage examples'

    def test_generated_gsi_code_imports_successfully(self, generation_output_dir, code_generator):
        """Test that generated GSI code can be imported without errors."""
        fixtures_path = Path(__file__).parent.parent / 'fixtures'
        user_analytics_schema = (
            fixtures_path / 'valid_schemas' / 'user_analytics' / 'user_analytics_schema.json'
        )

        # Generate code
        result = code_generator(user_analytics_schema, generation_output_dir)
        assert result.returncode == 0

        # Add generated directory to Python path
        sys.path.insert(0, str(generation_output_dir))

        try:
            # Import generated modules
            import entities  # type: ignore[import-not-found]
            import repositories  # type: ignore[import-not-found]

            # Verify User entity exists and can be instantiated
            assert hasattr(entities, 'User'), 'User entity not found'
            assert hasattr(repositories, 'UserRepository'), 'UserRepository not found'

            # Verify GSI key builder methods exist
            user = entities.User(
                user_id='test123',
                email='test@example.com',
                status='active',
                last_active='2024-01-01',
                country='US',
                city='Seattle',
                signup_date='2023-01-01',
                engagement_level='high',
                session_count=50,
                age_group='25-34',
            )

            # Test GSI key builders (instance methods) - snake_case for valid Python identifiers
            assert hasattr(user, 'build_gsi_pk_status_index')
            assert hasattr(user, 'build_gsi_sk_status_index')
            assert hasattr(user, 'build_gsi_pk_location_index')
            assert hasattr(user, 'build_gsi_sk_location_index')

            # Test key building functionality
            status_pk = user.build_gsi_pk_status_index()
            assert status_pk == 'STATUS#active'

            location_pk = user.build_gsi_pk_location_index()
            assert location_pk == 'COUNTRY#US'

            location_sk = user.build_gsi_sk_location_index()
            assert location_sk == 'CITY#Seattle'

        finally:
            # Clean up Python path
            sys.path.remove(str(generation_output_dir))

            # Remove imported modules from cache to avoid conflicts
            modules_to_remove = [
                name for name in sys.modules.keys() if name in ['entities', 'repositories']
            ]
            for module_name in modules_to_remove:
                del sys.modules[module_name]

    def _verify_python_syntax(self, file_path: Path):
        """Verify Python file has valid syntax."""
        with open(file_path) as f:
            content = f.read()

        try:
            compile(content, str(file_path), 'exec')
        except SyntaxError as e:
            pytest.fail(f'Syntax error in {file_path}: {e}')


@pytest.mark.integration
class TestGSIValidationIntegration:
    """Integration tests for GSI schema validation with real files."""

    def test_valid_gsi_schema_passes_validation(self, code_generator, tmp_path):
        """Test that valid GSI schema passes validation."""
        fixtures_path = Path(__file__).parent.parent / 'fixtures'
        user_analytics_schema = (
            fixtures_path / 'valid_schemas' / 'user_analytics' / 'user_analytics_schema.json'
        )

        validation_dir = tmp_path / 'validation_gsi'
        validation_dir.mkdir()

        result = code_generator(user_analytics_schema, validation_dir, validate_only=True)

        assert result.returncode == 0, f'Valid GSI schema failed validation: {result.stderr}'
        assert '✅' in result.stdout, 'Valid GSI schema should show success indicator'

    def test_invalid_gsi_schema_fails_validation(self, code_generator, tmp_path):
        """Test that invalid GSI schema fails validation with proper error messages."""
        fixtures_path = Path(__file__).parent.parent / 'fixtures'
        invalid_gsi_schema = fixtures_path / 'invalid_schemas' / 'invalid_gsi_schema.json'

        validation_dir = tmp_path / 'validation_invalid_gsi'
        validation_dir.mkdir()

        result = code_generator(invalid_gsi_schema, validation_dir, validate_only=True)

        # Should fail with non-zero exit code
        assert result.returncode != 0, 'Invalid GSI schema should cause validation to fail'

        # Should contain error messages
        assert '❌' in result.stdout or 'error' in result.stderr.lower()

        # Should not generate code files
        generated_files = list(validation_dir.glob('*.py'))
        assert len(generated_files) == 0, (
            f'Files were generated despite invalid GSI schema: {generated_files}'
        )

        # Verify specific GSI error messages
        error_output = result.stdout + result.stderr
        expected_errors = [
            'Duplicate GSI name',
            "GSI 'NonExistentIndex' referenced in entity mapping but not found",
            'Template parameter',
            'Invalid range_condition',
        ]

        for expected_error in expected_errors:
            assert expected_error in error_output, (
                f"Expected GSI error '{expected_error}' not found in output"
            )

    def test_gsi_error_recovery_and_reporting(self, code_generator, tmp_path):
        """Test that GSI validation provides comprehensive error reporting."""
        fixtures_path = Path(__file__).parent.parent / 'fixtures'
        invalid_gsi_schema = fixtures_path / 'invalid_schemas' / 'invalid_gsi_schema.json'

        validation_dir = tmp_path / 'validation_error_recovery'
        validation_dir.mkdir()

        result = code_generator(invalid_gsi_schema, validation_dir, validate_only=True)

        assert result.returncode != 0, 'Invalid GSI schema should fail validation'

        error_output = result.stdout + result.stderr

        # Verify multiple errors are reported (not just the first one)
        error_indicators = error_output.count('•')  # Each error starts with a bullet point
        assert error_indicators >= 8, (
            f'Should report multiple GSI validation errors, found {error_indicators}'
        )

        # Verify helpful suggestions are provided
        helpful_phrases = [
            '💡 Valid options:',
            '💡 Use one of the available GSI names:',
            '💡 Use one of the available fields:',
            '💡 Valid range_condition values:',
        ]

        found_helpful_phrases = sum(1 for phrase in helpful_phrases if phrase in error_output)
        assert found_helpful_phrases >= 3, (
            f'Should provide helpful error suggestions, found {found_helpful_phrases}'
        )

    def test_invalid_multi_attribute_keys_schema_fails_validation(self, code_generator, tmp_path):
        """Test that invalid multi-attribute key schemas fail with proper error messages."""
        fixtures_path = Path(__file__).parent.parent / 'fixtures'
        invalid_schema = (
            fixtures_path / 'invalid_schemas' / 'invalid_multi_attribute_keys_schema.json'
        )

        validation_dir = tmp_path / 'validation_invalid_multi_attr'
        validation_dir.mkdir()

        result = code_generator(invalid_schema, validation_dir, validate_only=True)

        assert result.returncode != 0, 'Invalid multi-attribute key schema should fail validation'

        error_output = result.stdout + result.stderr

        # Verify multi-attribute key specific errors
        expected_errors = [
            'partition_key array cannot be empty',
            'more than 4 attributes',
            'sort_key array cannot be empty',
            'Attribute at index 1 must be a string',
            'Attribute at index 1 cannot be empty',
            'pk_template type (string) does not match partition_key type (array)',
            'sk_template type (array) does not match sort_key type (string)',
            'sk_template array length (1) does not match sort_key array length (3)',
        ]

        for expected_error in expected_errors:
            assert expected_error in error_output, (
                f"Expected multi-attribute key error '{expected_error}' not found in output"
            )


@pytest.mark.integration
@pytest.mark.slow
class TestGSIComprehensiveIntegration:
    """Comprehensive GSI integration tests."""

    def test_gsi_access_pattern_mapping_generation(self, generation_output_dir, code_generator):
        """Test that GSI access patterns are properly mapped in JSON output."""
        fixtures_path = Path(__file__).parent.parent / 'fixtures'
        user_analytics_schema = (
            fixtures_path / 'valid_schemas' / 'user_analytics' / 'user_analytics_schema.json'
        )

        result = code_generator(user_analytics_schema, generation_output_dir)
        assert result.returncode == 0, (
            f'GSI access pattern mapping generation failed: {result.stderr}'
        )

        # Read and validate access pattern mapping
        with open(generation_output_dir / 'access_pattern_mapping.json') as f:
            mapping = json.load(f)

        assert 'access_pattern_mapping' in mapping
        pattern_mapping = mapping['access_pattern_mapping']

        # Verify GSI access patterns are included (patterns 2-10 are GSI patterns)
        gsi_pattern_ids = [str(i) for i in range(2, 11)]  # patterns 2-10 are GSI patterns
        gsi_patterns = [pattern_mapping[pid] for pid in gsi_pattern_ids if pid in pattern_mapping]
        assert len(gsi_patterns) >= 8, 'Should have multiple GSI access patterns'

        # Verify specific GSI patterns exist
        pattern_names = [pattern_mapping[pid]['method_name'] for pid in pattern_mapping.keys()]
        expected_gsi_patterns = [
            'get_active_users',
            'get_recent_active_users',
            'get_users_by_location',
            'get_users_by_country_prefix',
            'get_users_by_engagement_level',
            'get_highly_engaged_users_by_session_range',
            'get_users_by_age_group',
            'get_recent_signups_by_age_group',
            'get_users_signup_date_range',
        ]

        for expected_pattern in expected_gsi_patterns:
            assert expected_pattern in pattern_names, (
                f'GSI pattern {expected_pattern} not found in mapping'
            )

        # Verify GSI patterns have correct metadata
        status_index_pattern = pattern_mapping['2']  # get_active_users is pattern 2
        assert status_index_pattern['method_name'] == 'get_active_users'
        assert status_index_pattern['operation'] == 'Query'

        range_pattern = pattern_mapping['3']  # get_recent_active_users is pattern 3
        assert len(range_pattern['parameters']) == 2  # status + since_date

    def test_end_to_end_gsi_pipeline_with_sample_usage(
        self, generation_output_dir, code_generator
    ):
        """Test complete end-to-end GSI pipeline including sample usage generation."""
        fixtures_path = Path(__file__).parent.parent / 'fixtures'
        user_analytics_schema = (
            fixtures_path / 'valid_schemas' / 'user_analytics' / 'user_analytics_schema.json'
        )

        # Generate with all features enabled
        result = code_generator(
            user_analytics_schema, generation_output_dir, generate_sample_usage=True
        )

        assert result.returncode == 0, f'End-to-end GSI pipeline failed: {result.stderr}'

        # Verify all expected files exist
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

        # Verify GSI functionality in each file
        entities_content = (generation_output_dir / 'entities.py').read_text()
        repos_content = (generation_output_dir / 'repositories.py').read_text()
        usage_content = (generation_output_dir / 'usage_examples.py').read_text()

        # Entities should have GSI key builders (snake_case for valid Python identifiers)
        assert 'build_gsi_pk_status_index' in entities_content
        assert 'build_gsi_sk_location_index' in entities_content

        # Repositories should have GSI query methods
        assert 'def get_active_users' in repos_content
        assert 'def get_users_by_location' in repos_content

        # Usage examples should demonstrate GSI queries
        assert 'get_active_users' in usage_content
        assert 'status=' in usage_content  # GSI field in sample data

        # Verify Python syntax for all generated files
        for py_file in ['entities.py', 'repositories.py', 'usage_examples.py']:
            self._verify_python_syntax(generation_output_dir / py_file)

        # Verify JSON is valid
        with open(generation_output_dir / 'access_pattern_mapping.json') as f:
            mapping = json.load(f)
            assert 'access_pattern_mapping' in mapping
            assert (
                len(mapping['access_pattern_mapping']) >= 10
            )  # Should have main table + GSI patterns

    def _verify_python_syntax(self, file_path: Path):
        """Verify Python file has valid syntax."""
        with open(file_path) as f:
            content = f.read()

        try:
            compile(content, str(file_path), 'exec')
        except SyntaxError as e:
            pytest.fail(f'Syntax error in {file_path}: {e}')
