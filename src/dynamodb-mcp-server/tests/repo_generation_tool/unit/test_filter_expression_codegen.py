"""Unit tests for filter expression code generation in repository templates."""

import json
import pytest
import subprocess
import tempfile
from pathlib import Path


FOOD_DELIVERY_SCHEMA = (
    Path(__file__).parent.parent
    / 'fixtures'
    / 'valid_schemas'
    / 'food_delivery_app'
    / 'food_delivery_schema.json'
)


@pytest.fixture(scope='module')
def generated_repositories():
    """Generate repositories from food delivery schema and return the content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [
                'uv',
                'run',
                'python',
                '-m',
                'awslabs.dynamodb_mcp_server.repo_generation_tool.codegen',
                '--schema',
                str(FOOD_DELIVERY_SCHEMA),
                '--output',
                tmpdir,
                '--no-lint',
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f'Codegen failed: {result.stderr}'
        repo_path = Path(tmpdir) / 'repositories.py'
        mapping_path = Path(tmpdir) / 'access_pattern_mapping.json'
        return {
            'repositories': repo_path.read_text(),
            'mapping': json.loads(mapping_path.read_text()),
        }


@pytest.mark.unit
class TestFilterExpressionCodeGeneration:
    """Tests for filter expression rendering in generated repository code."""

    def test_comparison_filter_in_signature(self, generated_repositories):
        """Test comparison filter params appear in method signature."""
        repos = generated_repositories['repositories']
        # Pattern 2: get_active_customer_deliveries has excluded_status and min_total
        assert (
            'def get_active_customer_deliveries(self, customer_id: str, min_total: Decimal'
            in repos
        )
        assert 'excluded_status: str = "CANCELLED"' in repos

    def test_between_filter_in_signature(self, generated_repositories):
        """Test between filter params appear in method signature."""
        repos = generated_repositories['repositories']
        # Pattern 3: get_customer_deliveries_by_fee_range has min_fee and max_fee
        assert 'min_fee: Decimal' in repos
        assert 'max_fee: Decimal' in repos

    def test_in_filter_in_signature(self, generated_repositories):
        """Test in filter params appear in method signature."""
        repos = generated_repositories['repositories']
        # Pattern 4: get_customer_deliveries_by_status has status1, status2, status3
        assert 'status1: str' in repos
        assert 'status2: str' in repos
        assert 'status3: str' in repos

    def test_filter_expression_in_docstring(self, generated_repositories):
        """Test Filter Expression line appears in docstring."""
        repos = generated_repositories['repositories']
        assert 'Filter Expression: #status <> :excluded_status AND #total >= :min_total' in repos

    def test_filter_note_in_docstring(self, generated_repositories):
        """Test filter note about post-read behavior appears in docstring."""
        repos = generated_repositories['repositories']
        assert 'Filter expressions are applied AFTER data is read from DynamoDB' in repos
        assert 'Read capacity is consumed based on items read, not items returned' in repos

    def test_attribute_exists_renders_without_value(self, generated_repositories):
        """Test attribute_exists renders without ExpressionAttributeValues entry."""
        repos = generated_repositories['repositories']
        assert 'attribute_exists(#special_instructions)' in repos
        assert 'attribute_not_exists(#cancelled_at)' in repos

    def test_size_function_renders_correctly(self, generated_repositories):
        """Test size function renders with size(#field) syntax."""
        repos = generated_repositories['repositories']
        assert 'size(#items) > :min_items' in repos

    def test_size_between_renders_correctly(self, generated_repositories):
        """Test size function with between renders correctly."""
        repos = generated_repositories['repositories']
        assert 'size(#items) BETWEEN :min_count AND :max_count' in repos

    def test_contains_function_renders_correctly(self, generated_repositories):
        """Test contains function renders correctly."""
        repos = generated_repositories['repositories']
        assert 'contains(#tags, :skill_tag)' in repos

    def test_begins_with_function_renders_correctly(self, generated_repositories):
        """Test begins_with function renders correctly."""
        repos = generated_repositories['repositories']
        assert 'begins_with(#name, :name_prefix)' in repos

    def test_in_operator_renders_correctly(self, generated_repositories):
        """Test IN operator renders correctly."""
        repos = generated_repositories['repositories']
        assert '#status IN (:status1, :status2, :status3)' in repos

    def test_between_operator_renders_correctly(self, generated_repositories):
        """Test BETWEEN operator renders correctly."""
        repos = generated_repositories['repositories']
        assert '#delivery_fee BETWEEN :min_fee AND :max_fee' in repos

    def test_or_logical_operator_renders(self, generated_repositories):
        """Test OR logical operator renders correctly."""
        repos = generated_repositories['repositories']
        # Pattern 8: get_high_value_active_deliveries uses OR
        assert '#total >= :min_total OR #tip >= :min_tip' in repos

    def test_expression_attribute_names_in_hints(self, generated_repositories):
        """Test ExpressionAttributeNames appear in implementation hints."""
        repos = generated_repositories['repositories']
        assert "'#status': 'status'" in repos
        assert "'#total': 'total'" in repos

    def test_expression_attribute_values_in_hints(self, generated_repositories):
        """Test ExpressionAttributeValues appear in implementation hints."""
        repos = generated_repositories['repositories']
        assert "':excluded_status': excluded_status" in repos
        assert "':min_total': min_total" in repos

    def test_filter_expression_in_todo_comment(self, generated_repositories):
        """Test filter expression appears in TODO comment line."""
        repos = generated_repositories['repositories']
        assert '# Operation: Query | Index: Main Table | Filter Expression:' in repos


@pytest.mark.unit
class TestFilterExpressionInMapping:
    """Tests for filter_expression in access pattern mapping output."""

    def test_mapping_includes_filter_expression(self, generated_repositories):
        """Test mapping includes filter_expression for patterns that have one."""
        mapping = generated_repositories['mapping']['access_pattern_mapping']
        # Pattern 2 has filter_expression
        assert 'filter_expression' in mapping['2']
        assert mapping['2']['filter_expression']['logical_operator'] == 'AND'

    def test_mapping_omits_filter_expression_when_absent(self, generated_repositories):
        """Test mapping omits filter_expression for patterns without one."""
        mapping = generated_repositories['mapping']['access_pattern_mapping']
        # Pattern 1 (GetItem) has no filter_expression
        assert 'filter_expression' not in mapping['1']

    def test_mapping_preserves_all_conditions(self, generated_repositories):
        """Test mapping preserves all filter conditions."""
        mapping = generated_repositories['mapping']['access_pattern_mapping']
        # Pattern 4 has IN operator
        fe = mapping['4']['filter_expression']
        assert len(fe['conditions']) == 1
        assert fe['conditions'][0]['operator'] == 'in'
        assert fe['conditions'][0]['params'] == ['status1', 'status2', 'status3']


FOOD_DELIVERY_USAGE_DATA = (
    Path(__file__).parent.parent
    / 'fixtures'
    / 'valid_usage_data'
    / 'food_delivery_app'
    / 'food_delivery_usage_data.json'
)


@pytest.fixture(scope='module')
def generated_with_usage_data():
    """Generate code with usage data and return usage_examples content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [
                'uv',
                'run',
                'python',
                '-m',
                'awslabs.dynamodb_mcp_server.repo_generation_tool.codegen',
                '--schema',
                str(FOOD_DELIVERY_SCHEMA),
                '--output',
                tmpdir,
                '--generate_sample_usage',
                '--usage-data-path',
                str(FOOD_DELIVERY_USAGE_DATA),
                '--no-lint',
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f'Codegen failed: {result.stderr}'
        usage_path = Path(tmpdir) / 'usage_examples.py'
        return usage_path.read_text()


@pytest.mark.unit
class TestFilterValuesInUsageExamples:
    """Tests for filter values being passed in generated usage examples."""

    def test_filter_value_excluded_status_passed(self, generated_with_usage_data):
        """Test excluded_status filter value from usage_data is used."""
        assert '"CANCELLED"' in generated_with_usage_data

    def test_filter_value_min_total_passed(self, generated_with_usage_data):
        """Test min_total filter value from usage_data is used."""
        assert (
            'Decimal("25.0")' in generated_with_usage_data
            or 'Decimal("25.00")' in generated_with_usage_data
        )

    def test_filter_value_skill_tag_passed(self, generated_with_usage_data):
        """Test skill_tag filter value from usage_data is used."""
        assert '"express"' in generated_with_usage_data

    def test_filter_value_name_prefix_passed(self, generated_with_usage_data):
        """Test name_prefix filter value from usage_data is used."""
        assert '"A"' in generated_with_usage_data

    def test_filter_value_cuisine_keyword_passed(self, generated_with_usage_data):
        """Test cuisine_keyword filter value from usage_data is used."""
        assert '"Italian"' in generated_with_usage_data
