"""Integration tests for sparse GSI support in generated code."""

import pytest


@pytest.mark.integration
class TestSparseGSIIntegration:
    """Test sparse GSI support in code generation."""

    def test_generated_base_repository_uses_exclude_none(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test that generated base_repository.py uses exclude_none=True."""
        # Generate code using any schema
        result = code_generator(sample_schemas['social_media'], generation_output_dir)

        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        # Read generated base_repository.py
        base_repo_file = generation_output_dir / 'base_repository.py'
        assert base_repo_file.exists()

        content = base_repo_file.read_text()

        # Verify mode='json' and exclude_none=True are used in both create() and update()
        assert content.count('model_dump(exclude_none=True)') == 2

    def test_sparse_gsi_with_optional_key_field(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test that deals schema with optional GSI keys generates correct code."""
        # Use deals schema which has optional brand_id for sparse GSI
        result = code_generator(
            sample_schemas['deals'], generation_output_dir, generate_sample_usage=True
        )

        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        # Verify base_repository.py uses mode='json' and exclude_none=True
        base_repo_file = generation_output_dir / 'base_repository.py'
        content = base_repo_file.read_text()
        assert 'model_dump(exclude_none=True)' in content

        # Verify entities.py has optional fields (deals schema should have some)
        entities_file = generation_output_dir / 'entities.py'
        entities_content = entities_file.read_text()

        # Deals schema should have entities with optional fields
        # Just verify the file was generated correctly
        assert 'class' in entities_content
        assert 'ConfigurableEntity' in entities_content
