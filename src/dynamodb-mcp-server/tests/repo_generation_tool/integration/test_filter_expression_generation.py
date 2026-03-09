"""Integration tests for filter expression end-to-end code generation."""

import json
import pytest


FOOD_DELIVERY_SCHEMA = 'food_delivery'


@pytest.mark.integration
class TestFilterExpressionGeneration:
    """Integration tests for filter expression code generation pipeline."""

    def test_food_delivery_schema_generates_successfully(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test that the food delivery schema with filter expressions generates code."""
        result = code_generator(sample_schemas[FOOD_DELIVERY_SCHEMA], generation_output_dir)
        assert result.returncode == 0, f'Generation failed: {result.stderr}'
        assert (generation_output_dir / 'repositories.py').exists()
        assert (generation_output_dir / 'entities.py').exists()
        assert (generation_output_dir / 'access_pattern_mapping.json').exists()

    def test_repositories_contain_filter_params_in_signatures(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test that generated repositories include filter parameters in method signatures."""
        result = code_generator(sample_schemas[FOOD_DELIVERY_SCHEMA], generation_output_dir)
        assert result.returncode == 0
        repos = (generation_output_dir / 'repositories.py').read_text()

        # Pattern 2: comparison filter params
        assert 'excluded_status: str' in repos
        assert 'min_total: Decimal' in repos

        # Pattern 3: between filter params
        assert 'min_fee: Decimal' in repos
        assert 'max_fee: Decimal' in repos

        # Pattern 4: in filter params
        assert 'status1: str' in repos
        assert 'status2: str' in repos

        # Pattern 6: size filter param
        assert 'min_items: int' in repos

    def test_repositories_contain_filter_docstrings(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test that generated repositories include filter expression docstrings."""
        result = code_generator(sample_schemas[FOOD_DELIVERY_SCHEMA], generation_output_dir)
        assert result.returncode == 0
        repos = (generation_output_dir / 'repositories.py').read_text()

        # Filter Expression line in docstring
        assert 'Filter Expression: #status <> :excluded_status AND #total >= :min_total' in repos

        # Post-read note
        assert 'Filter expressions are applied AFTER data is read from DynamoDB' in repos

    def test_repositories_contain_filter_implementation_hints(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test that generated repositories include filter implementation hints."""
        result = code_generator(sample_schemas[FOOD_DELIVERY_SCHEMA], generation_output_dir)
        assert result.returncode == 0
        repos = (generation_output_dir / 'repositories.py').read_text()

        # ExpressionAttributeNames
        assert "'#status': 'status'" in repos
        assert "'#total': 'total'" in repos

        # ExpressionAttributeValues
        assert "':excluded_status': excluded_status" in repos
        assert "':min_total': min_total" in repos

    def test_all_filter_variants_present(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test that all filter expression variants are rendered in generated code."""
        result = code_generator(sample_schemas[FOOD_DELIVERY_SCHEMA], generation_output_dir)
        assert result.returncode == 0
        repos = (generation_output_dir / 'repositories.py').read_text()

        # Comparison
        assert '#status <> :excluded_status' in repos
        # Between
        assert '#delivery_fee BETWEEN :min_fee AND :max_fee' in repos
        # In
        assert '#status IN (:status1, :status2, :status3)' in repos
        # attribute_exists / attribute_not_exists
        assert 'attribute_exists(#special_instructions)' in repos
        assert 'attribute_not_exists(#cancelled_at)' in repos
        # size
        assert 'size(#items) > :min_items' in repos
        assert 'size(#items) BETWEEN :min_count AND :max_count' in repos
        # contains / begins_with
        assert 'contains(#tags, :skill_tag)' in repos
        assert 'begins_with(#name, :name_prefix)' in repos
        # OR logical operator
        assert '#total >= :min_total OR #tip >= :min_tip' in repos

    def test_access_pattern_mapping_includes_filter_metadata(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test that access_pattern_mapping.json includes filter_expression metadata."""
        result = code_generator(sample_schemas[FOOD_DELIVERY_SCHEMA], generation_output_dir)
        assert result.returncode == 0
        mapping = json.loads((generation_output_dir / 'access_pattern_mapping.json').read_text())[
            'access_pattern_mapping'
        ]

        # Pattern 2 should have filter_expression
        assert 'filter_expression' in mapping['2']
        fe = mapping['2']['filter_expression']
        assert fe['logical_operator'] == 'AND'
        assert len(fe['conditions']) == 2
        assert fe['conditions'][0]['field'] == 'status'
        assert fe['conditions'][0]['operator'] == '<>'

        # Pattern 1 (GetItem) should NOT have filter_expression
        assert 'filter_expression' not in mapping['1']

        # Pattern 5 (attribute_exists + attribute_not_exists) should have filter_expression
        assert 'filter_expression' in mapping['5']
        fe5 = mapping['5']['filter_expression']
        assert fe5['conditions'][0]['function'] == 'attribute_exists'
        assert fe5['conditions'][1]['function'] == 'attribute_not_exists'

    def test_no_regressions_on_non_filter_patterns(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test that patterns without filter_expression are unaffected."""
        result = code_generator(sample_schemas[FOOD_DELIVERY_SCHEMA], generation_output_dir)
        assert result.returncode == 0
        repos = (generation_output_dir / 'repositories.py').read_text()

        # Pattern 1 (GetItem, no filter) should not have filter-related content
        # Find the get_delivery_by_id method
        lines = repos.split('\n')
        in_method = False
        method_lines = []
        for line in lines:
            if 'def get_delivery_by_id' in line:
                in_method = True
            elif in_method and line.strip().startswith('def '):
                break
            elif in_method:
                method_lines.append(line)

        method_text = '\n'.join(method_lines)
        assert 'Filter Expression' not in method_text
        assert 'FilterExpression' not in method_text
