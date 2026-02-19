"""Integration tests for transaction service generation."""

import json
import pytest
from pathlib import Path


@pytest.mark.integration
@pytest.mark.file_generation
@pytest.mark.python
class TestTransactionServiceGeneration:
    """Integration tests for transaction service generation."""

    def test_generate_transaction_service_with_user_registration(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test end-to-end generation of transaction service with user_registration schema."""
        # Generate code using the user_registration schema
        result = code_generator(
            sample_schemas['user_registration'], generation_output_dir, generate_sample_usage=True
        )

        # Assert generation succeeded
        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        # Verify expected files exist
        expected_files = [
            'entities.py',
            'repositories.py',
            'base_repository.py',
            'transaction_service.py',  # NEW: Should be generated
            'usage_examples.py',
            'access_pattern_mapping.json',
            'ruff.toml',
        ]

        for file_name in expected_files:
            file_path = generation_output_dir / file_name
            assert file_path.exists(), f'Expected file {file_name} was not generated'
            assert file_path.stat().st_size > 0, f'Generated file {file_name} is empty'

        # Verify Python syntax
        self._verify_python_syntax(generation_output_dir / 'transaction_service.py')

    def test_transaction_service_content(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test transaction_service.py contains expected content."""
        # Generate code
        result = code_generator(sample_schemas['user_registration'], generation_output_dir)
        assert result.returncode == 0

        # Read transaction service content
        transaction_service_file = generation_output_dir / 'transaction_service.py'
        content = transaction_service_file.read_text()

        # Check class definition
        assert 'class TransactionService:' in content, 'TransactionService class not found'

        # Check imports
        assert 'import boto3' in content, 'boto3 import missing'
        assert 'ClientError' in content, 'ClientError import missing'
        assert 'from entities import' in content, 'Entity imports missing'
        assert 'User' in content, 'User entity not imported'
        assert 'EmailLookup' in content, 'EmailLookup entity not imported'

        # Check __init__ method
        assert 'def __init__(self, dynamodb_resource: boto3.resource)' in content, (
            '__init__ method signature incorrect'
        )
        assert 'self.dynamodb = dynamodb_resource' in content, 'dynamodb_resource not stored'
        assert 'self.client = dynamodb_resource.meta.client' in content, 'client not initialized'

        # Check method generation for all patterns
        expected_methods = [
            'def register_user(',
            'def delete_user_with_email(',
            'def get_user_and_email(',
        ]

        for method in expected_methods:
            assert method in content, f'Method {method} not found in transaction service'

        # Check docstrings
        assert 'Create user and email lookup atomically' in content, (
            'register_user docstring missing'
        )
        assert 'Delete user and email lookup atomically' in content, (
            'delete_user_with_email docstring missing'
        )
        assert 'Get user and email lookup atomically' in content, (
            'get_user_and_email docstring missing'
        )

        # Check TODO comments with implementation hints
        assert 'TODO: Implement Access Pattern #100' in content, 'Pattern #100 TODO missing'
        assert 'TODO: Implement Access Pattern #101' in content, 'Pattern #101 TODO missing'
        assert 'TODO: Implement Access Pattern #102' in content, 'Pattern #102 TODO missing'

        # Check operation hints
        assert 'Operation: TransactWrite' in content, 'TransactWrite operation hint missing'
        assert 'Operation: TransactGet' in content, 'TransactGet operation hint missing'

        # Check table references
        assert 'Tables: Users, EmailLookup' in content, 'Table references missing'

    def test_access_pattern_mapping_includes_transactions(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test access_pattern_mapping.json includes cross-table patterns."""
        # Generate code
        result = code_generator(sample_schemas['user_registration'], generation_output_dir)
        assert result.returncode == 0

        # Load mapping
        mapping_file = generation_output_dir / 'access_pattern_mapping.json'
        with open(mapping_file) as f:
            data = json.load(f)

        mapping = data['access_pattern_mapping']

        # Check cross-table patterns are included
        assert '100' in mapping, 'Pattern 100 (register_user) not in mapping'
        assert '101' in mapping, 'Pattern 101 (delete_user_with_email) not in mapping'
        assert '102' in mapping, 'Pattern 102 (get_user_and_email) not in mapping'

        # Verify pattern 100 structure
        pattern_100 = mapping['100']
        assert pattern_100['pattern_id'] == 100
        assert pattern_100['method_name'] == 'register_user'
        assert pattern_100['description'] == 'Create user and email lookup atomically'
        assert pattern_100['operation'] == 'TransactWrite'
        assert pattern_100['service'] == 'TransactionService', (
            'Should have service field instead of repository'
        )
        assert 'repository' not in pattern_100, 'Should not have repository field'
        assert pattern_100['transaction_type'] == 'cross_table'
        assert len(pattern_100['entities_involved']) == 2

        # Check entities_involved structure
        entities_involved = pattern_100['entities_involved']
        assert any(e['table'] == 'Users' and e['entity'] == 'User' for e in entities_involved)
        assert any(
            e['table'] == 'EmailLookup' and e['entity'] == 'EmailLookup' for e in entities_involved
        )

        # Verify pattern 101 structure (Delete operation)
        pattern_101 = mapping['101']
        assert pattern_101['operation'] == 'TransactWrite'
        assert pattern_101['service'] == 'TransactionService'
        assert pattern_101['transaction_type'] == 'cross_table'

        # Verify pattern 102 structure (TransactGet operation)
        pattern_102 = mapping['102']
        assert pattern_102['operation'] == 'TransactGet'
        assert pattern_102['service'] == 'TransactionService'
        assert pattern_102['transaction_type'] == 'cross_table'

    def test_no_transaction_service_without_patterns(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test transaction service not generated when no cross-table patterns."""
        # Use social_media schema which has no cross_table_access_patterns
        result = code_generator(sample_schemas['social_media'], generation_output_dir)

        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        # Check transaction_service.py was NOT generated
        transaction_service_file = generation_output_dir / 'transaction_service.py'
        assert not transaction_service_file.exists(), (
            'transaction_service.py should not be generated without cross_table_access_patterns'
        )

        # Verify other files are still generated
        assert (generation_output_dir / 'entities.py').exists()
        assert (generation_output_dir / 'repositories.py').exists()
        assert (generation_output_dir / 'base_repository.py').exists()

    def test_transaction_service_method_signatures(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test transaction service methods have correct signatures."""
        # Generate code
        result = code_generator(sample_schemas['user_registration'], generation_output_dir)
        assert result.returncode == 0

        content = (generation_output_dir / 'transaction_service.py').read_text()

        # Check register_user signature
        assert 'def register_user(self, user: User, email_lookup: EmailLookup) -> bool:' in content

        # Check delete_user_with_email signature
        assert 'def delete_user_with_email(self, user_id: str, email: str) -> bool:' in content

        # Check get_user_and_email signature
        assert (
            'def get_user_and_email(self, user_id: str, email: str) -> dict[str, Any]:' in content
        )

    def test_transaction_service_linting_passes(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test generated transaction service passes ruff linting."""
        # Generate code with linting enabled (default)
        result = code_generator(sample_schemas['user_registration'], generation_output_dir)

        assert result.returncode == 0, f'Generation with linting failed: {result.stderr}'

        # If linting is enabled and generation succeeded, linting passed
        # Check that no linting errors are in the output
        assert '❌' not in result.stdout or 'Linting failed' not in result.stdout

    def test_usage_examples_include_transactions(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test usage_examples.py includes transaction pattern examples."""
        # Generate code with usage examples
        result = code_generator(
            sample_schemas['user_registration'], generation_output_dir, generate_sample_usage=True
        )
        assert result.returncode == 0

        # Read usage examples content
        usage_examples_file = generation_output_dir / 'usage_examples.py'
        assert usage_examples_file.exists(), 'usage_examples.py not generated'
        content = usage_examples_file.read_text()

        # Check TransactionService import
        assert 'from transaction_service import TransactionService' in content, (
            'TransactionService import missing'
        )

        # Check TransactionService initialization in __init__
        assert 'self.transaction_service = TransactionService(dynamodb)' in content, (
            'TransactionService not initialized'
        )

        # Check cross-table pattern examples section
        assert 'Cross-Table Pattern Examples' in content or 'cross_table_patterns' in content, (
            'Cross-table pattern examples section missing'
        )

        # Check specific pattern examples
        assert 'register_user' in content, 'register_user example missing'
        assert 'delete_user_with_email' in content, 'delete_user_with_email example missing'
        assert 'get_user_and_email' in content, 'get_user_and_email example missing'

        # Check operation type is displayed
        assert 'TransactWrite' in content, 'TransactWrite operation type not displayed'
        assert 'TransactGet' in content, 'TransactGet operation type not displayed'

        # Check error handling examples
        assert 'try:' in content, 'Error handling (try) missing'
        assert 'except' in content, 'Error handling (except) missing'

        # Check realistic sample data usage
        assert 'User(' in content, 'User entity instantiation missing'
        assert 'EmailLookup(' in content, 'EmailLookup entity instantiation missing'

    def _verify_python_syntax(self, file_path: Path):
        """Verify Python file has valid syntax."""
        with open(file_path) as f:
            content = f.read()

        try:
            compile(content, str(file_path), 'exec')
        except SyntaxError as e:
            pytest.fail(f'Syntax error in {file_path}: {e}')
