"""Unit tests for Jinja2Generator class."""

import json
import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.generators.jinja2_generator import (
    Jinja2Generator,
)


@pytest.mark.unit
class TestJinja2Generator:
    """Unit tests for Jinja2Generator class."""

    @pytest.fixture
    def valid_schema_file(self, mock_schema_data, tmp_path):
        """Create a temporary valid schema file."""
        schema_file = tmp_path / 'schema.json'
        schema_file.write_text(json.dumps(mock_schema_data))
        return str(schema_file)

    @pytest.fixture
    def generator(self, valid_schema_file):
        """Create a Jinja2Generator instance for testing."""
        return Jinja2Generator(valid_schema_file, language='python')

    @pytest.fixture
    def sample_entity_config(self):
        """Sample entity configuration for testing."""
        return {
            'entity_type': 'USER',
            'pk_template': '{user_id}',
            'sk_template': 'PROFILE',
            'fields': [
                {'name': 'user_id', 'type': 'string', 'required': True},
                {'name': 'email', 'type': 'string', 'required': True},
            ],
            'access_patterns': [
                {
                    'pattern_id': 1,
                    'name': 'get_user',
                    'description': 'Get user by ID',
                    'operation': 'GetItem',
                    'parameters': [{'name': 'user_id', 'type': 'string'}],
                    'return_type': 'single_entity',
                }
            ],
        }

    @pytest.fixture
    def sample_table_config(self):
        """Sample table configuration for testing."""
        return {'table_name': 'TestTable', 'partition_key': 'pk', 'sort_key': 'sk'}

    def test_generator_initialization(self, valid_schema_file):
        """Test Jinja2Generator initialization."""
        generator = Jinja2Generator(valid_schema_file, language='python')
        assert generator.language == 'python'
        assert generator.language_config is not None
        assert generator.type_mapper is not None

    def test_generator_initialization_with_usage_data_path(self, valid_schema_file, tmp_path):
        """Test Jinja2Generator initialization with usage_data_path."""
        # Create a sample usage data file
        usage_data = {'field_mappings': {'test': 'value'}}
        usage_file = tmp_path / 'usage_data.json'
        usage_file.write_text(json.dumps(usage_data))

        generator = Jinja2Generator(
            valid_schema_file, language='python', usage_data_path=str(usage_file)
        )
        assert generator.language == 'python'
        assert generator.sample_generator.usage_data_path == str(usage_file)
        assert generator.sample_generator.language_generator.usage_data_loader is not None

    def test_generator_initialization_with_invalid_usage_data_path(self, valid_schema_file):
        """Test Jinja2Generator initialization with invalid usage_data_path."""
        generator = Jinja2Generator(
            valid_schema_file, language='python', usage_data_path='/nonexistent/path.json'
        )
        assert generator.language == 'python'
        assert generator.sample_generator.usage_data_path == '/nonexistent/path.json'
        # Should still initialize but with no data
        assert generator.sample_generator.language_generator.usage_data_loader is not None
        assert not generator.sample_generator.language_generator.usage_data_loader.has_data()

    def test_generate_entity_and_repository(
        self, generator, sample_entity_config, sample_table_config
    ):
        """Test entity and repository generation."""
        entity = generator.generate_entity('User', sample_entity_config)
        repo = generator.generate_repository('User', sample_entity_config, sample_table_config)
        assert isinstance(entity, str) and 'User' in entity
        assert isinstance(repo, str) and 'User' in repo

    def test_generate_with_gsi_mappings(self, generator, sample_table_config):
        """Test generation with GSI mappings."""
        config = {
            'entity_type': 'USER',
            'pk_template': '{user_id}',
            'sk_template': 'USER',
            'fields': [{'name': 'user_id', 'type': 'string'}],
            'access_patterns': [],
            'gsi_mappings': [{'name': 'GSI1', 'pk_template': '{email}', 'sk_template': 'USER'}],
        }
        result = generator.generate_entity('User', config)
        assert isinstance(result, str)

    def test_generate_all(self, generator, tmp_path):
        """Test generate_all with and without usage examples."""
        output_dir = str(tmp_path / 'output')
        generator.generate_all(output_dir, generate_usage_examples=True)
        assert (tmp_path / 'output').exists()

    def test_generate_repository_with_mapping(
        self, generator, sample_entity_config, sample_table_config
    ):
        """Test generate_repository_with_mapping."""
        code, mapping = generator.generate_repository_with_mapping(
            'User', sample_entity_config, sample_table_config
        )
        assert isinstance(code, str) and isinstance(mapping, dict)

    def test_missing_templates_raise_errors(self, valid_schema_file):
        """Test missing required templates raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match='entity_template.j2'):
            Jinja2Generator(valid_schema_file, templates_dir='/nonexistent', language='python')

    def test_missing_repository_template(self, mock_schema_data, tmp_path):
        """Test missing repository template raises error."""
        schema_file = tmp_path / 'schema.json'
        schema_file.write_text(json.dumps(mock_schema_data))
        templates_dir = tmp_path / 'templates'
        templates_dir.mkdir()
        (templates_dir / 'entity_template.j2').write_text('{{ entity_name }}')
        with pytest.raises(FileNotFoundError, match='repository_template.j2'):
            Jinja2Generator(str(schema_file), templates_dir=str(templates_dir), language='python')

    def test_missing_optional_templates_print_warnings(self, mock_schema_data, tmp_path, capsys):
        """Test missing optional templates print warnings."""
        schema_file = tmp_path / 'schema.json'
        schema_file.write_text(json.dumps(mock_schema_data))
        templates_dir = tmp_path / 'templates'
        templates_dir.mkdir()
        (templates_dir / 'entity_template.j2').write_text('{{ entity_name }}')
        (templates_dir / 'repository_template.j2').write_text('{{ entity_name }}Repository')
        Jinja2Generator(str(schema_file), templates_dir=str(templates_dir), language='python')
        captured = capsys.readouterr()
        assert any(
            x in captured.out for x in ['entities header', 'repositories header', 'usage examples']
        )

    def test_repository_without_table_config_raises_error(self, generator, sample_entity_config):
        """Test generate_repository raises ValueError without table_config."""
        with pytest.raises(ValueError, match='table_config is required'):
            generator.generate_repository('Test', sample_entity_config, table_config=None)

    def test_usage_examples_without_template(self, generator, sample_entity_config):
        """Test usage examples when template is missing."""
        generator.usage_examples_template = None
        result = generator.generate_usage_examples({}, {'Test': sample_entity_config}, [])
        assert 'Usage examples template not found' in result

    def test_repository_with_entity_type_parameter(self, generator, sample_table_config):
        """Test repository with entity type parameter."""
        config = {
            'entity_type': 'USER',
            'pk_template': '{user_id}',
            'sk_template': 'USER',
            'fields': [{'name': 'user_id', 'type': 'string'}],
            'access_patterns': [
                {
                    'pattern_id': 1,
                    'name': 'create',
                    'description': 'Create user',
                    'operation': 'PutItem',
                    'parameters': [{'name': 'entity', 'type': 'entity', 'entity_type': 'User'}],
                    'return_type': 'single_entity',
                }
            ],
        }
        result = generator.generate_repository('User', config, sample_table_config)
        assert isinstance(result, str)

    def test_gsi_mapping_lookup(self, mock_schema_data, tmp_path, sample_table_config):
        """Test GSI mapping lookup in templates."""
        schema_file = tmp_path / 'schema.json'
        schema_file.write_text(json.dumps(mock_schema_data))
        templates_dir = tmp_path / 'templates'
        templates_dir.mkdir()
        (templates_dir / 'entity_template.j2').write_text('{{ entity_name }}')
        (templates_dir / 'repository_template.j2').write_text(
            '{{ entity_name }}Repository\n'
            '{% for pattern in filtered_access_patterns %}'
            "{% if pattern.get('index_name') %}"
            '{% set gsi = get_gsi_mapping_for_index(pattern.index_name) %}'
            '{% if gsi %}Found:{{ gsi.name }}{% else %}NotFound{% endif %}'
            '{% endif %}'
            '{% endfor %}'
        )
        gen = Jinja2Generator(
            str(schema_file), templates_dir=str(templates_dir), language='python'
        )

        # Test with matching GSI
        config = {
            'entity_type': 'USER',
            'pk_template': '{user_id}',
            'sk_template': 'USER',
            'fields': [{'name': 'user_id', 'type': 'string'}, {'name': 'email', 'type': 'string'}],
            'access_patterns': [
                {
                    'pattern_id': 1,
                    'name': 'query_by_email',
                    'description': 'Query users by email',
                    'operation': 'Query',
                    'index_name': 'EmailIndex',
                    'parameters': [{'name': 'email', 'type': 'string'}],
                    'return_type': 'entity_list',
                }
            ],
            'gsi_mappings': [
                {'name': 'OtherIndex', 'pk_template': '{other}', 'sk_template': 'USER'},
                {'name': 'EmailIndex', 'pk_template': '{email}', 'sk_template': 'USER'},
            ],
        }
        result = gen.generate_repository('User', config, sample_table_config)
        assert 'Found:EmailIndex' in result

        # Test without matching GSI
        config['access_patterns'][0]['index_name'] = 'NonExistent'
        result = gen.generate_repository('User', config, sample_table_config)
        assert 'NotFound' in result


@pytest.mark.unit
class TestJinja2GeneratorGSIKeyBuilders:
    """Unit tests for GSI key builder generation in Jinja2Generator."""

    @pytest.fixture
    def gsi_entity_config(self):
        """Sample entity configuration with GSI mappings for testing."""
        return {
            'entity_type': 'USER_ANALYTICS',
            'pk_template': 'USER#{user_id}',
            'sk_template': 'PROFILE#{created_at}',
            'fields': [
                {'name': 'user_id', 'type': 'string', 'required': True},
                {'name': 'status', 'type': 'string', 'required': True},
                {'name': 'created_at', 'type': 'string', 'required': True},
                {'name': 'score', 'type': 'integer', 'required': False},
            ],
            'gsi_mappings': [
                {
                    'name': 'UserStatusIndex',
                    'pk_template': 'STATUS#{status}',
                    'sk_template': 'USER#{user_id}',
                },
                {
                    'name': 'ScoreIndex',
                    'pk_template': 'SCORE#{score}',
                    'sk_template': 'CREATED#{created_at}',
                },
            ],
            'access_patterns': [],
        }

    @pytest.fixture
    def valid_schema_file(self, mock_schema_data, tmp_path):
        """Create a temporary valid schema file."""
        schema_file = tmp_path / 'schema.json'
        schema_file.write_text(json.dumps(mock_schema_data))
        return str(schema_file)

    @pytest.fixture
    def generator(self, valid_schema_file):
        """Create a Jinja2Generator instance for testing."""
        return Jinja2Generator(valid_schema_file, language='python')

    def test_generate_entity_with_gsi_mappings(self, generator, gsi_entity_config):
        """Test that generate_entity creates GSI key builder methods."""
        result = generator.generate_entity('UserAnalytics', gsi_entity_config)

        # Should return non-empty string
        assert isinstance(result, str)
        assert len(result) > 0

        # Should contain GSI key builder class methods (snake_case for valid Python identifiers)
        assert 'build_gsi_pk_for_lookup_user_status_index' in result
        assert 'build_gsi_sk_for_lookup_user_status_index' in result
        assert 'build_gsi_pk_for_lookup_score_index' in result
        assert 'build_gsi_sk_for_lookup_score_index' in result

        # Should contain GSI key builder instance methods
        assert 'build_gsi_pk_user_status_index' in result
        assert 'build_gsi_sk_user_status_index' in result
        assert 'build_gsi_pk_score_index' in result
        assert 'build_gsi_sk_score_index' in result

        # Should contain GSI prefix helper methods
        assert 'get_gsi_pk_prefix_user_status_index' in result
        assert 'get_gsi_sk_prefix_user_status_index' in result
        assert 'get_gsi_pk_prefix_score_index' in result
        assert 'get_gsi_sk_prefix_score_index' in result

    def test_generate_entity_without_gsi_mappings(self, generator):
        """Test that entities without GSI mappings don't generate GSI methods."""
        sample_entity_config = {
            'entity_type': 'USER',
            'pk_template': '{user_id}',
            'sk_template': 'PROFILE',
            'fields': [
                {'name': 'user_id', 'type': 'string', 'required': True},
                {'name': 'email', 'type': 'string', 'required': True},
            ],
            'access_patterns': [],
        }
        result = generator.generate_entity('UserProfile', sample_entity_config)

        # Should not contain any GSI-related methods
        assert 'build_gsi_pk' not in result
        assert 'build_gsi_sk' not in result
        assert 'get_gsi_pk_prefix' not in result
        assert 'get_gsi_sk_prefix' not in result


@pytest.mark.unit
class TestJinja2GeneratorNumericFieldHandling:
    """Unit tests for numeric field handling in Jinja2Generator.

    Tests the helper methods that detect pure numeric field references
    and the code generation output for numeric PK/SK/GSI keys.
    """

    @pytest.fixture
    def valid_schema_file(self, mock_schema_data, tmp_path):
        """Create a temporary valid schema file."""
        schema_file = tmp_path / 'schema.json'
        schema_file.write_text(json.dumps(mock_schema_data))
        return str(schema_file)

    @pytest.fixture
    def generator(self, valid_schema_file):
        """Create a Jinja2Generator instance for testing."""
        return Jinja2Generator(valid_schema_file, language='python')

    # Tests for _is_pure_field_reference
    def test_is_pure_field_reference_valid(self, generator):
        """Test that pure field references like {field} are detected."""
        assert generator._is_pure_field_reference('{score}') is True
        assert generator._is_pure_field_reference('{user_id}') is True
        assert generator._is_pure_field_reference('{field_name}') is True

    def test_is_pure_field_reference_invalid(self, generator):
        """Test that non-pure templates (prefix, suffix, multiple fields, static) return False."""
        # With prefix
        assert generator._is_pure_field_reference('SCORE#{score}') is False
        assert generator._is_pure_field_reference('PREFIX{field}') is False
        # With suffix
        assert generator._is_pure_field_reference('{score}#SUFFIX') is False
        # Multiple fields
        assert generator._is_pure_field_reference('{user_id}#{score}') is False
        # Static text only
        assert generator._is_pure_field_reference('STATIC') is False
        # Edge cases
        assert generator._is_pure_field_reference('') is False
        assert generator._is_pure_field_reference(None) is False

    # Tests for _get_field_type
    def test_get_field_type(self, generator):
        """Test field type lookup by name."""
        fields = [
            {'name': 'score', 'type': 'integer'},
            {'name': 'price', 'type': 'decimal'},
            {'name': 'name', 'type': 'string'},
        ]
        # Found cases
        assert generator._get_field_type('score', fields) == 'integer'
        assert generator._get_field_type('price', fields) == 'decimal'
        # Not found cases
        assert generator._get_field_type('nonexistent', fields) is None
        assert generator._get_field_type('score', []) is None

    # Tests for _is_numeric_type
    def test_is_numeric_type(self, generator):
        """Test numeric type detection for all field types."""
        # Numeric types
        assert generator._is_numeric_type('integer') is True
        assert generator._is_numeric_type('decimal') is True
        # Non-numeric types
        assert generator._is_numeric_type('string') is False
        assert generator._is_numeric_type('boolean') is False
        assert generator._is_numeric_type('array') is False
        assert generator._is_numeric_type('object') is False
        assert generator._is_numeric_type('uuid') is False
        assert generator._is_numeric_type(None) is False

    # Tests for _check_template_is_pure_numeric
    def test_check_template_is_pure_numeric_true_cases(self, generator):
        """Test that pure numeric field references return True."""
        int_fields = [{'name': 'score', 'type': 'integer'}]
        dec_fields = [{'name': 'price', 'type': 'decimal'}]

        assert generator._check_template_is_pure_numeric('{score}', ['score'], int_fields) is True
        assert generator._check_template_is_pure_numeric('{price}', ['price'], dec_fields) is True

    def test_check_template_is_pure_numeric_false_cases(self, generator):
        """Test cases that should return False for pure numeric check."""
        str_fields = [{'name': 'user_id', 'type': 'string'}]
        int_fields = [{'name': 'score', 'type': 'integer'}]
        mixed_fields = [
            {'name': 'user_id', 'type': 'string'},
            {'name': 'score', 'type': 'integer'},
        ]

        # String field (not numeric)
        assert (
            generator._check_template_is_pure_numeric('{user_id}', ['user_id'], str_fields)
            is False
        )
        # Template with prefix (not pure)
        assert (
            generator._check_template_is_pure_numeric('SCORE#{score}', ['score'], int_fields)
            is False
        )
        # Multiple params (not pure)
        assert (
            generator._check_template_is_pure_numeric(
                '{user_id}#{score}', ['user_id', 'score'], mixed_fields
            )
            is False
        )
        # Field not found
        assert generator._check_template_is_pure_numeric('{score}', ['score'], str_fields) is False

    # Tests for generated code output with numeric fields
    def test_generate_entity_numeric_sort_key(self, generator):
        """Test that integer/decimal sort keys generate raw value (no f-string)."""
        # Integer SK
        int_config = {
            'entity_type': 'SCORE',
            'pk_template': '{game_id}',
            'sk_template': '{score}',
            'fields': [
                {'name': 'game_id', 'type': 'string', 'required': True},
                {'name': 'score', 'type': 'integer', 'required': True},
            ],
            'access_patterns': [],
        }
        result = generator.generate_entity('LeaderboardEntry', int_config)
        assert 'sk_builder=lambda entity: entity.score,' in result
        assert 'sk_lookup_builder=lambda score: score,' in result

        # Decimal SK
        dec_config = {
            'entity_type': 'PRICE',
            'pk_template': '{product_id}',
            'sk_template': '{price}',
            'fields': [
                {'name': 'product_id', 'type': 'string', 'required': True},
                {'name': 'price', 'type': 'decimal', 'required': True},
            ],
            'access_patterns': [],
        }
        result = generator.generate_entity('PriceEntry', dec_config)
        assert 'sk_builder=lambda entity: entity.price,' in result

    def test_generate_entity_numeric_partition_key(self, generator):
        """Test that numeric partition key generates raw value (no f-string)."""
        config = {
            'entity_type': 'ITEM',
            'pk_template': '{item_id}',
            'sk_template': 'METADATA',
            'fields': [{'name': 'item_id', 'type': 'integer', 'required': True}],
            'access_patterns': [],
        }
        result = generator.generate_entity('Item', config)
        assert 'pk_builder=lambda entity: entity.item_id,' in result
        assert 'pk_lookup_builder=lambda item_id: item_id,' in result

    def test_generate_entity_mixed_template_uses_fstring(self, generator):
        """Test that mixed templates (prefix + numeric field) still use f-string."""
        config = {
            'entity_type': 'SCORE',
            'pk_template': '{game_id}',
            'sk_template': 'SCORE#{score}',
            'fields': [
                {'name': 'game_id', 'type': 'string', 'required': True},
                {'name': 'score', 'type': 'integer', 'required': True},
            ],
            'access_patterns': [],
        }
        result = generator.generate_entity('ScoreEntry', config)
        assert 'sk_builder=lambda entity: f"SCORE#{entity.score}"' in result

    def test_generate_entity_numeric_gsi_sort_key(self, generator):
        """Test that numeric GSI sort key generates raw value (no f-string)."""
        config = {
            'entity_type': 'ENTRY',
            'pk_template': '{player_id}',
            'sk_template': '{entry_id}',
            'fields': [
                {'name': 'player_id', 'type': 'string', 'required': True},
                {'name': 'entry_id', 'type': 'string', 'required': True},
                {'name': 'game_id', 'type': 'string', 'required': True},
                {'name': 'points', 'type': 'integer', 'required': True},
            ],
            'gsi_mappings': [
                {'name': 'GamePointsIndex', 'pk_template': '{game_id}', 'sk_template': '{points}'}
            ],
            'access_patterns': [],
        }
        result = generator.generate_entity('GameEntry', config)

        # Class method returns raw value with KeyType annotation (snake_case for valid Python identifiers)
        assert 'def build_gsi_sk_for_lookup_game_points_index(cls, points) -> KeyType:' in result
        assert 'return points' in result
        # Instance method returns raw value with KeyType annotation
        assert 'def build_gsi_sk_game_points_index(self) -> KeyType:' in result
        assert 'return self.points' in result

    def test_generate_entity_string_gsi_sort_key(self, generator):
        """Test that string GSI sort key uses f-string with return type annotation."""
        config = {
            'entity_type': 'ENTRY',
            'pk_template': '{player_id}',
            'sk_template': '{entry_id}',
            'fields': [
                {'name': 'player_id', 'type': 'string', 'required': True},
                {'name': 'entry_id', 'type': 'string', 'required': True},
                {'name': 'game_id', 'type': 'string', 'required': True},
                {'name': 'created_at', 'type': 'string', 'required': True},
            ],
            'gsi_mappings': [
                {
                    'name': 'GameTimeIndex',
                    'pk_template': '{game_id}',
                    'sk_template': '{created_at}',
                }
            ],
            'access_patterns': [],
        }
        result = generator.generate_entity('TimeEntry', config)

        # String GSI SK uses f-string and has -> KeyType return type (snake_case for valid Python identifiers)
        assert 'def build_gsi_sk_for_lookup_game_time_index(cls, created_at) -> KeyType:' in result
        assert 'return f"{created_at}"' in result

    # Tests for prefix_builder generation
    def test_generate_entity_prefix_builder_with_static_prefix(self, generator):
        """Test that prefix_builder extracts static prefix correctly."""
        config = {
            'entity_type': 'POST',
            'pk_template': '{user_id}',
            'sk_template': 'POST#{timestamp}',
            'fields': [
                {'name': 'user_id', 'type': 'string', 'required': True},
                {'name': 'timestamp', 'type': 'string', 'required': True},
            ],
            'access_patterns': [],
        }
        result = generator.generate_entity('Post', config)
        assert 'prefix_builder=lambda **kwargs: "POST#"' in result

    def test_generate_entity_prefix_builder_with_dynamic_prefix(self, generator):
        """Test that prefix_builder falls back to entity_type when prefix contains field reference."""
        config = {
            'entity_type': 'ORDER',
            'pk_template': '{customer_id}',
            'sk_template': '{order_date}#{order_id}',
            'fields': [
                {'name': 'customer_id', 'type': 'string', 'required': True},
                {'name': 'order_date', 'type': 'string', 'required': True},
                {'name': 'order_id', 'type': 'string', 'required': True},
            ],
            'access_patterns': [],
        }
        result = generator.generate_entity('Order', config)
        # Should fall back to entity_type since {order_date} is dynamic
        assert 'prefix_builder=lambda **kwargs: "ORDER#"' in result

    def test_generate_entity_prefix_builder_no_hash_separator(self, generator):
        """Test that prefix_builder uses entity_type when sk_template has no #{."""
        config = {
            'entity_type': 'PROFILE',
            'pk_template': '{user_id}',
            'sk_template': 'PROFILE',
            'fields': [
                {'name': 'user_id', 'type': 'string', 'required': True},
            ],
            'access_patterns': [],
        }
        result = generator.generate_entity('UserProfile', config)
        assert 'prefix_builder=lambda **kwargs: "PROFILE#"' in result

    def test_generate_entity_prefix_builder_pure_field_reference(self, generator):
        """Test that prefix_builder uses entity_type when sk_template is pure field reference."""
        config = {
            'entity_type': 'SCORE',
            'pk_template': '{game_id}',
            'sk_template': '{score}',
            'fields': [
                {'name': 'game_id', 'type': 'string', 'required': True},
                {'name': 'score', 'type': 'integer', 'required': True},
            ],
            'access_patterns': [],
        }
        result = generator.generate_entity('LeaderboardEntry', config)
        # Pure field reference has no #{, so falls back to entity_type
        assert 'prefix_builder=lambda **kwargs: "SCORE#"' in result

    def test_generate_entity_prefix_builder_none_when_no_sk(self, generator):
        """Test that prefix_builder is None when there's no sort key."""
        config = {
            'entity_type': 'USER',
            'pk_template': '{user_id}',
            'fields': [
                {'name': 'user_id', 'type': 'string', 'required': True},
            ],
            'access_patterns': [],
        }
        result = generator.generate_entity('User', config)
        assert 'prefix_builder=None' in result


@pytest.mark.unit
class TestParameterConsistency:
    """Test that repository methods and usage examples stay in sync for parameter handling."""

    def test_phantom_parameter_excluded_from_both_repository_and_usage_examples(self, tmp_path):
        """Test that phantom parameters are excluded from both repository signatures and usage examples."""
        # Schema with a "phantom" parameter that doesn't exist in entity fields
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'TestTable', 'pk_name': 'PK', 'sk_name': 'SK'},
                    'entities': {
                        'User': {
                            'fields': [
                                {'name': 'user_id', 'type': 'string'},
                                {'name': 'email', 'type': 'string'},
                            ],
                            'pk_template': 'USER#{user_id}',
                            'sk_template': 'PROFILE',
                            'access_patterns': [
                                {
                                    'pattern_id': 'AP1',
                                    'name': 'get_by_user_and_phantom',
                                    'description': 'Get user by ID and phantom',
                                    'method_name': 'get_by_user_and_phantom',
                                    'operation': 'GetItem',
                                    'parameters': [
                                        {'name': 'user_id', 'type': 'string'},
                                        {
                                            'name': 'phantom_field',
                                            'type': 'string',
                                        },  # Not in fields!
                                    ],
                                    'return_type': 'single',
                                }
                            ],
                        }
                    },
                }
            ]
        }

        schema_path = tmp_path / 'schema.json'
        schema_path.write_text(json.dumps(schema))
        generator = Jinja2Generator(str(schema_path))

        entity_config = schema['tables'][0]['entities']['User']
        table_config = schema['tables'][0]['table_config']
        repo_code = generator.generate_repository(
            'User', entity_config, table_config, schema['tables'][0]
        )

        preprocessed = generator._preprocess_entity_config(entity_config)
        usage_code = generator.generate_usage_examples(
            {'User': {'access_patterns': []}}, {'User': preprocessed}, schema['tables']
        )

        assert 'phantom_field' not in repo_code
        assert 'phantom_field' not in usage_code
        assert 'user_id' in repo_code
        assert 'user_id' in usage_code

    def test_range_query_parameters_included_in_both_repository_and_usage_examples(self, tmp_path):
        """Test that range query parameters are included even if they don't match entity field names."""
        # Schema with range query where parameter name differs from field name
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'ProductTable',
                        'partition_key': 'pk',
                        'sort_key': 'sk',
                    },
                    'entities': {
                        'ProductCategory': {
                            'entity_type': 'CATEGORY',
                            'pk_template': 'CATEGORY#{category_name}',
                            'sk_template': 'PRODUCT#{product_id}',
                            'fields': [
                                {'name': 'category_name', 'type': 'string', 'required': True},
                                {'name': 'product_id', 'type': 'string', 'required': True},
                                {'name': 'name', 'type': 'string', 'required': True},
                                {'name': 'price', 'type': 'decimal', 'required': True},
                            ],
                            'access_patterns': [
                                {
                                    'pattern_id': 1,
                                    'name': 'get_category_products_after_id',
                                    'description': 'Get products after a specific product ID',
                                    'operation': 'Query',
                                    'range_condition': '>',
                                    'parameters': [
                                        {'name': 'category_name', 'type': 'string'},
                                        {
                                            'name': 'last_product_id',
                                            'type': 'string',
                                        },  # Different from field name 'product_id'!
                                    ],
                                    'return_type': 'entity_list',
                                }
                            ],
                        }
                    },
                }
            ]
        }

        schema_path = tmp_path / 'schema.json'
        schema_path.write_text(json.dumps(schema))
        generator = Jinja2Generator(str(schema_path))

        entity_config = schema['tables'][0]['entities']['ProductCategory']
        table_config = schema['tables'][0]['table_config']
        repo_code = generator.generate_repository(
            'ProductCategory', entity_config, table_config, schema['tables'][0]
        )

        # Range query parameter should be included in signature even though it doesn't match field name
        assert 'last_product_id: str' in repo_code
        assert 'category_name: str' in repo_code

        # Verify it's in the method signature, not just comments
        assert (
            'def get_category_products_after_id(self, category_name: str, last_product_id: str'
            in repo_code
        )

        # Verify the parameter is documented in the docstring
        assert 'last_product_id:' in repo_code or 'Last product id' in repo_code

    def test_between_range_query_includes_both_range_parameters(self, tmp_path):
        """Test that 'between' range queries include both min and max parameters."""
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'OrderTable',
                        'partition_key': 'pk',
                        'sort_key': 'sk',
                    },
                    'entities': {
                        'UserOrderHistory': {
                            'entity_type': 'HISTORY',
                            'pk_template': 'USER#{user_id}',
                            'sk_template': 'ORDER#{order_date}#{order_id}',
                            'fields': [
                                {'name': 'user_id', 'type': 'string', 'required': True},
                                {'name': 'order_id', 'type': 'string', 'required': True},
                                {'name': 'order_date', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [
                                {
                                    'pattern_id': 1,
                                    'name': 'get_user_orders_in_range',
                                    'description': 'Get orders in date range',
                                    'operation': 'Query',
                                    'range_condition': 'between',
                                    'parameters': [
                                        {'name': 'user_id', 'type': 'string'},
                                        {'name': 'start_date', 'type': 'string'},
                                        {'name': 'end_date', 'type': 'string'},
                                    ],
                                    'return_type': 'entity_list',
                                }
                            ],
                        }
                    },
                }
            ]
        }

        schema_path = tmp_path / 'schema.json'
        schema_path.write_text(json.dumps(schema))
        generator = Jinja2Generator(str(schema_path))

        entity_config = schema['tables'][0]['entities']['UserOrderHistory']
        table_config = schema['tables'][0]['table_config']
        repo_code = generator.generate_repository(
            'UserOrderHistory', entity_config, table_config, schema['tables'][0]
        )

        # Both range parameters should be included
        assert 'start_date: str' in repo_code
        assert 'end_date: str' in repo_code
        assert (
            'def get_user_orders_in_range(self, user_id: str, start_date: str, end_date: str'
            in repo_code
        )


@pytest.mark.unit
class TestAnyImportDetection:
    """Test that Any import is correctly detected for mixed_data and dict return types."""

    def test_check_needs_any_import_with_mixed_data(self, tmp_path):
        """Test that mixed_data return type triggers Any import."""
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'Tasks',
                        'partition_key': 'taskId',
                        'sort_key': 'SK',
                    },
                    'entities': {
                        'Task': {
                            'entity_type': 'METADATA',
                            'pk_template': '{taskId}',
                            'sk_template': 'METADATA',
                            'fields': [
                                {'name': 'taskId', 'type': 'string', 'required': True},
                                {'name': 'title', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [
                                {
                                    'pattern_id': 1,
                                    'name': 'get_task_details',
                                    'description': 'Get task with subtasks and comments',
                                    'operation': 'Query',
                                    'parameters': [{'name': 'taskId', 'type': 'string'}],
                                    'return_type': 'mixed_data',
                                }
                            ],
                        }
                    },
                }
            ]
        }

        schema_path = tmp_path / 'schema.json'
        schema_path.write_text(json.dumps(schema))
        generator = Jinja2Generator(str(schema_path))

        needs_any = generator._check_needs_any_import(schema['tables'])
        assert needs_any is True

    def test_check_needs_any_import_with_keys_only_projection(self, tmp_path):
        """Test that KEYS_ONLY GSI projection triggers Any import."""
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'Users',
                        'partition_key': 'userId',
                        'sort_key': 'SK',
                    },
                    'gsi_list': [
                        {
                            'name': 'EmailIndex',
                            'partition_key': 'email',
                            'projection': 'KEYS_ONLY',
                        }
                    ],
                    'entities': {
                        'User': {
                            'entity_type': 'PROFILE',
                            'pk_template': '{userId}',
                            'sk_template': 'PROFILE',
                            'fields': [
                                {'name': 'userId', 'type': 'string', 'required': True},
                                {'name': 'email', 'type': 'string', 'required': True},
                                {'name': 'name', 'type': 'string', 'required': True},
                            ],
                            'gsi_mappings': [{'name': 'EmailIndex', 'pk_template': '{email}'}],
                            'access_patterns': [
                                {
                                    'pattern_id': 1,
                                    'name': 'get_user_by_email',
                                    'description': 'Get user by email',
                                    'operation': 'Query',
                                    'index_name': 'EmailIndex',
                                    'parameters': [{'name': 'email', 'type': 'string'}],
                                    'return_type': 'entity_list',
                                }
                            ],
                        }
                    },
                }
            ]
        }

        schema_path = tmp_path / 'schema.json'
        schema_path.write_text(json.dumps(schema))
        generator = Jinja2Generator(str(schema_path))

        needs_any = generator._check_needs_any_import(schema['tables'])
        assert needs_any is True

    def test_check_needs_any_import_without_dict_returns(self, tmp_path):
        """Test that normal entity_list without dict returns doesn't trigger Any import."""
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'Users',
                        'partition_key': 'userId',
                        'sort_key': 'SK',
                    },
                    'gsi_list': [
                        {
                            'name': 'EmailIndex',
                            'partition_key': 'email',
                            'projection': 'ALL',  # ALL projection returns entities, not dicts
                        }
                    ],
                    'entities': {
                        'User': {
                            'entity_type': 'PROFILE',
                            'pk_template': '{userId}',
                            'sk_template': 'PROFILE',
                            'fields': [
                                {'name': 'userId', 'type': 'string', 'required': True},
                                {'name': 'email', 'type': 'string', 'required': True},
                            ],
                            'gsi_mappings': [{'name': 'EmailIndex', 'pk_template': '{email}'}],
                            'access_patterns': [
                                {
                                    'pattern_id': 1,
                                    'name': 'get_user_by_email',
                                    'description': 'Get user by email',
                                    'operation': 'Query',
                                    'index_name': 'EmailIndex',
                                    'parameters': [{'name': 'email', 'type': 'string'}],
                                    'return_type': 'entity_list',
                                }
                            ],
                        }
                    },
                }
            ]
        }

        schema_path = tmp_path / 'schema.json'
        schema_path.write_text(json.dumps(schema))
        generator = Jinja2Generator(str(schema_path))

        needs_any = generator._check_needs_any_import(schema['tables'])
        assert needs_any is False

    def test_check_needs_any_import_with_unsafe_include_projection(self, tmp_path):
        """Test that unsafe INCLUDE projection (required fields not projected) triggers Any import."""
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'Users',
                        'partition_key': 'userId',
                        'sort_key': 'SK',
                    },
                    'gsi_list': [
                        {
                            'name': 'EmailIndex',
                            'partition_key': 'email',
                            'projection': 'INCLUDE',
                            'included_attributes': ['userId'],  # Missing required 'name' field
                        }
                    ],
                    'entities': {
                        'User': {
                            'entity_type': 'PROFILE',
                            'pk_template': '{userId}',
                            'sk_template': 'PROFILE',
                            'fields': [
                                {'name': 'userId', 'type': 'string', 'required': True},
                                {'name': 'email', 'type': 'string', 'required': True},
                                {
                                    'name': 'name',
                                    'type': 'string',
                                    'required': True,
                                },  # Required but not projected
                            ],
                            'gsi_mappings': [{'name': 'EmailIndex', 'pk_template': '{email}'}],
                            'access_patterns': [
                                {
                                    'pattern_id': 1,
                                    'name': 'get_user_by_email',
                                    'description': 'Get user by email',
                                    'operation': 'Query',
                                    'index_name': 'EmailIndex',
                                    'parameters': [{'name': 'email', 'type': 'string'}],
                                    'return_type': 'entity_list',
                                }
                            ],
                        }
                    },
                }
            ]
        }

        schema_path = tmp_path / 'schema.json'
        schema_path.write_text(json.dumps(schema))
        generator = Jinja2Generator(str(schema_path))

        needs_any = generator._check_needs_any_import(schema['tables'])
        assert needs_any is True


@pytest.mark.unit
class TestFormatSpecifierSupport:
    """Test support for Python format specifiers in templates."""

    def test_extract_parameters_with_format_specifiers(self, tmp_path):
        """Test that parameters with format specifiers are extracted correctly."""
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'TestTable',
                        'partition_key': 'pk',
                        'sort_key': 'sk',
                    },
                    'entities': {
                        'Lesson': {
                            'entity_type': 'LESSON',
                            'pk_template': 'COURSE#{course_id}',
                            'sk_template': 'LESSON#{lesson_order:05d}',
                            'fields': [
                                {'name': 'course_id', 'type': 'string', 'required': True},
                                {'name': 'lesson_order', 'type': 'integer', 'required': True},
                            ],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }

        schema_path = tmp_path / 'schema.json'
        schema_path.write_text(json.dumps(schema))
        generator = Jinja2Generator(str(schema_path))

        entity_config = schema['tables'][0]['entities']['Lesson']
        entity_code = generator.generate_entity('Lesson', entity_config)

        # Verify format specifier is preserved in generated code
        assert 'sk_builder=lambda entity: f"LESSON#{entity.lesson_order:05d}"' in entity_code
        assert 'sk_lookup_builder=lambda lesson_order: f"LESSON#{lesson_order:05d}"' in entity_code

    def test_mixed_format_specifiers(self, tmp_path):
        """Test templates with multiple parameters and mixed format specifiers."""
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'TestTable',
                        'partition_key': 'pk',
                        'sort_key': 'sk',
                    },
                    'entities': {
                        'Score': {
                            'entity_type': 'SCORE',
                            'pk_template': 'GAME#{game_id}',
                            'sk_template': 'SCORE#{score:08d}#USER#{user_id}',
                            'fields': [
                                {'name': 'game_id', 'type': 'string', 'required': True},
                                {'name': 'score', 'type': 'integer', 'required': True},
                                {'name': 'user_id', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }

        schema_path = tmp_path / 'schema.json'
        schema_path.write_text(json.dumps(schema))
        generator = Jinja2Generator(str(schema_path))

        entity_config = schema['tables'][0]['entities']['Score']
        entity_code = generator.generate_entity('Score', entity_config)

        # Verify both parameters extracted and format spec preserved
        assert (
            'sk_builder=lambda entity: f"SCORE#{entity.score:08d}#USER#{entity.user_id}"'
            in entity_code
        )
        assert (
            'sk_lookup_builder=lambda score, user_id: f"SCORE#{score:08d}#USER#{user_id}"'
            in entity_code
        )


@pytest.mark.unit
class TestTransactionServiceTemplateRendering:
    """Unit tests for transaction service template rendering."""

    @pytest.fixture
    def user_registration_schema_path(self):
        """Path to user_registration test fixture schema."""
        return 'tests/repo_generation_tool/fixtures/valid_schemas/user_registration/user_registration_schema.json'

    @pytest.fixture
    def generator_with_transactions(self, user_registration_schema_path):
        """Create a Jinja2Generator instance with transaction patterns."""
        return Jinja2Generator(user_registration_schema_path, language='python')

    @pytest.fixture
    def schema_without_transactions(self, tmp_path):
        """Create a schema without cross_table_access_patterns."""
        schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'Users',
                        'partition_key': 'pk',
                    },
                    'entities': {
                        'User': {
                            'entity_type': 'USER',
                            'pk_template': 'USER#{user_id}',
                            'fields': [
                                {'name': 'user_id', 'type': 'string', 'required': True},
                                {'name': 'email', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }
        schema_path = tmp_path / 'schema_no_tx.json'
        schema_path.write_text(json.dumps(schema))
        return str(schema_path)

    def test_transaction_service_template_loads(self, generator_with_transactions):
        """Test that transaction service template loads successfully."""
        # The template should be loaded during initialization
        # If it fails to load, it should print a warning but not crash
        assert generator_with_transactions is not None

    def test_generate_transaction_service_with_user_registration(
        self, generator_with_transactions
    ):
        """Test transaction service generation with user_registration schema."""
        # Get cross_table_patterns from schema
        cross_table_patterns = generator_with_transactions.schema.get(
            'cross_table_access_patterns', []
        )
        assert (
            len(cross_table_patterns) == 3
        )  # register_user, delete_user_with_email, get_user_and_email

        # Get all entities for imports
        all_entities = {}
        for table in generator_with_transactions.schema['tables']:
            all_entities.update(table['entities'])

        # Generate transaction service code
        # Note: We need to check if the template exists first
        if not hasattr(generator_with_transactions, 'transaction_service_template'):
            pytest.skip('Transaction service template not loaded')

        # For now, we'll test the helper methods that would be used in generation
        entity_imports = generator_with_transactions._get_entity_imports(cross_table_patterns)
        assert 'User' in entity_imports
        assert 'EmailLookup' in entity_imports

    def test_all_methods_generated(self, generator_with_transactions):
        """Test that all transaction methods are generated."""
        cross_table_patterns = generator_with_transactions.schema.get(
            'cross_table_access_patterns', []
        )

        # Check that we have the expected patterns
        pattern_names = [p['name'] for p in cross_table_patterns]
        assert 'register_user' in pattern_names
        assert 'delete_user_with_email' in pattern_names
        assert 'get_user_and_email' in pattern_names

        # Check pattern operations
        operations = [p['operation'] for p in cross_table_patterns]
        assert 'TransactWrite' in operations
        assert 'TransactGet' in operations

    def test_imports_are_correct(self, generator_with_transactions):
        """Test that entity imports are correctly extracted."""
        cross_table_patterns = generator_with_transactions.schema.get(
            'cross_table_access_patterns', []
        )

        entity_imports = generator_with_transactions._get_entity_imports(cross_table_patterns)

        # Should have both User and EmailLookup
        assert 'User' in entity_imports
        assert 'EmailLookup' in entity_imports

        # Should be comma-separated and sorted
        import_parts = entity_imports.split(', ')
        assert len(import_parts) == 2
        assert import_parts == sorted(import_parts)

    def test_format_parameters_for_transactions(self, generator_with_transactions):
        """Test parameter formatting for transaction methods."""
        cross_table_patterns = generator_with_transactions.schema.get(
            'cross_table_access_patterns', []
        )

        # Test register_user pattern (entity parameters)
        register_pattern = next(p for p in cross_table_patterns if p['name'] == 'register_user')
        formatted = generator_with_transactions._format_parameters(register_pattern['parameters'])
        assert 'user: User' in formatted
        assert 'email_lookup: EmailLookup' in formatted

        # Test delete_user_with_email pattern (primitive parameters)
        delete_pattern = next(
            p for p in cross_table_patterns if p['name'] == 'delete_user_with_email'
        )
        formatted = generator_with_transactions._format_parameters(delete_pattern['parameters'])
        assert 'user_id: str' in formatted
        assert 'email: str' in formatted

    def test_get_return_description(self, generator_with_transactions):
        """Test return description generation for different return types."""
        # Boolean return type
        pattern_bool = {'return_type': 'boolean', 'operation': 'TransactWrite'}
        desc = generator_with_transactions._get_return_description(pattern_bool)
        assert 'True if transaction succeeded' in desc

        # Object return type with TransactGet
        pattern_obj = {'return_type': 'object', 'operation': 'TransactGet'}
        desc = generator_with_transactions._get_return_description(pattern_obj)
        assert 'Dictionary containing retrieved entities' in desc

        # Array return type
        pattern_arr = {'return_type': 'array', 'operation': 'TransactWrite'}
        desc = generator_with_transactions._get_return_description(pattern_arr)
        assert 'List of results' in desc

    def test_get_table_list(self, generator_with_transactions):
        """Test table list extraction from patterns."""
        cross_table_patterns = generator_with_transactions.schema.get(
            'cross_table_access_patterns', []
        )

        register_pattern = next(p for p in cross_table_patterns if p['name'] == 'register_user')
        table_list = generator_with_transactions._get_table_list(register_pattern)

        assert 'Users' in table_list
        assert 'EmailLookup' in table_list
        assert ',' in table_list  # Should be comma-separated

    def test_get_param_description(self, generator_with_transactions):
        """Test parameter description generation."""
        # Entity parameter
        entity_param = {'name': 'user', 'type': 'entity', 'entity_type': 'User'}
        desc = generator_with_transactions._get_param_description(entity_param)
        assert 'User entity' in desc

        # Primitive parameter
        string_param = {'name': 'user_id', 'type': 'string'}
        desc = generator_with_transactions._get_param_description(string_param)
        assert 'str' in desc

    def test_schema_without_transactions_has_no_patterns(self, schema_without_transactions):
        """Test that schema without cross_table_access_patterns works correctly."""
        generator = Jinja2Generator(schema_without_transactions, language='python')

        cross_table_patterns = generator.schema.get('cross_table_access_patterns', [])
        assert len(cross_table_patterns) == 0

        # Should not generate entity imports for transactions
        entity_imports = generator._get_entity_imports(cross_table_patterns)
        assert entity_imports == ''

    def test_transaction_patterns_have_required_fields(self, generator_with_transactions):
        """Test that all transaction patterns have required fields."""
        cross_table_patterns = generator_with_transactions.schema.get(
            'cross_table_access_patterns', []
        )

        for pattern in cross_table_patterns:
            # Required fields
            assert 'pattern_id' in pattern
            assert 'name' in pattern
            assert 'description' in pattern
            assert 'operation' in pattern
            assert 'entities_involved' in pattern
            assert 'parameters' in pattern
            assert 'return_type' in pattern

            # Validate entities_involved structure
            for entity_inv in pattern['entities_involved']:
                assert 'table' in entity_inv
                assert 'entity' in entity_inv
                assert 'action' in entity_inv

    def test_transact_write_patterns_have_valid_actions(self, generator_with_transactions):
        """Test that TransactWrite patterns have valid actions."""
        cross_table_patterns = generator_with_transactions.schema.get(
            'cross_table_access_patterns', []
        )

        valid_write_actions = {'Put', 'Update', 'Delete', 'ConditionCheck'}

        for pattern in cross_table_patterns:
            if pattern['operation'] == 'TransactWrite':
                for entity_inv in pattern['entities_involved']:
                    assert entity_inv['action'] in valid_write_actions

    def test_transact_get_patterns_have_get_action(self, generator_with_transactions):
        """Test that TransactGet patterns only have Get actions."""
        cross_table_patterns = generator_with_transactions.schema.get(
            'cross_table_access_patterns', []
        )

        for pattern in cross_table_patterns:
            if pattern['operation'] == 'TransactGet':
                for entity_inv in pattern['entities_involved']:
                    assert entity_inv['action'] == 'Get'

    def test_create_transaction_pattern_mapping(self, generator_with_transactions):
        """Test that _create_transaction_pattern_mapping creates correct mapping structure."""
        cross_table_patterns = generator_with_transactions.schema.get(
            'cross_table_access_patterns', []
        )

        # Test with first pattern (register_user - TransactWrite)
        pattern = cross_table_patterns[0]
        mapping = generator_with_transactions._create_transaction_pattern_mapping(pattern)

        # Verify required fields
        assert mapping['pattern_id'] == pattern['pattern_id']
        assert mapping['description'] == pattern['description']
        assert mapping['service'] == 'TransactionService'
        assert mapping['method_name'] == pattern['name']
        assert mapping['parameters'] == pattern['parameters']
        assert mapping['operation'] == pattern['operation']
        assert mapping['transaction_type'] == 'cross_table'

        # Verify return type is mapped
        assert 'return_type' in mapping
        assert mapping['return_type'] == 'bool'  # boolean -> bool

        # Verify entities_involved structure
        assert 'entities_involved' in mapping
        assert len(mapping['entities_involved']) == len(pattern['entities_involved'])
        for i, entity_inv in enumerate(mapping['entities_involved']):
            assert 'table' in entity_inv
            assert 'entity' in entity_inv
            assert 'action' in entity_inv
            assert entity_inv['table'] == pattern['entities_involved'][i]['table']
            assert entity_inv['entity'] == pattern['entities_involved'][i]['entity']
            assert entity_inv['action'] == pattern['entities_involved'][i]['action']

        # Verify no 'repository' field
        assert 'repository' not in mapping

    def test_create_transaction_pattern_mapping_transact_get(self, generator_with_transactions):
        """Test mapping creation for TransactGet patterns."""
        cross_table_patterns = generator_with_transactions.schema.get(
            'cross_table_access_patterns', []
        )

        # Find TransactGet pattern (get_user_and_email)
        transact_get_pattern = next(
            p for p in cross_table_patterns if p['operation'] == 'TransactGet'
        )
        mapping = generator_with_transactions._create_transaction_pattern_mapping(
            transact_get_pattern
        )

        # Verify operation and return type
        assert mapping['operation'] == 'TransactGet'
        assert mapping['return_type'] == 'dict[str, Any]'  # object -> dict[str, Any]
        assert mapping['transaction_type'] == 'cross_table'

    def test_generate_all_includes_transaction_patterns_in_mapping(
        self, generator_with_transactions, tmp_path
    ):
        """Test that generate_all includes transaction patterns in access_pattern_mapping."""
        output_dir = str(tmp_path / 'output')
        generator_with_transactions.generate_all(output_dir)

        # Load the access pattern mapping
        mapping_file = tmp_path / 'output' / 'access_pattern_mapping.json'
        assert mapping_file.exists()

        with open(mapping_file, 'r') as f:
            mapping_data = json.load(f)

        access_patterns = mapping_data['access_pattern_mapping']

        # Verify transaction patterns are included
        assert '100' in access_patterns  # register_user
        assert '101' in access_patterns  # delete_user_with_email
        assert '102' in access_patterns  # get_user_and_email

        # Verify structure of transaction patterns
        for pattern_id in ['100', '101', '102']:
            pattern = access_patterns[pattern_id]
            assert pattern['service'] == 'TransactionService'
            assert 'entities_involved' in pattern
            assert 'transaction_type' in pattern
            assert pattern['transaction_type'] == 'cross_table'
            assert 'repository' not in pattern


@pytest.mark.unit
class TestJinja2GeneratorEdgeCases:
    """Test edge cases in Jinja2Generator."""

    @pytest.fixture
    def generator(self, mock_schema_data, tmp_path):
        """Create a Jinja2Generator instance for testing."""
        schema_file = tmp_path / 'schema.json'
        schema_file.write_text(json.dumps(mock_schema_data))
        return Jinja2Generator(str(schema_file), language='python')

    def test_is_unsafe_include_projection_with_safe_projection(self, generator):
        """Test _is_unsafe_include_projection returns False when all required fields are projected."""
        entity_config = {
            'fields': [
                {'name': 'id', 'type': 'string', 'required': True},
                {'name': 'name', 'type': 'string', 'required': True},
                {'name': 'optional', 'type': 'string', 'required': False},
            ],
            'pk_template': '{id}',
        }
        pattern = {
            'projection': 'INCLUDE',
            'projected_attributes': ['id', 'name'],
        }
        table_config = {'partition_key': 'pk'}

        # All required fields are projected, should return False
        result = generator._is_unsafe_include_projection(entity_config, pattern, table_config)
        assert result is False

    def test_get_gsi_mapping_for_index_returns_none_when_no_mappings(self, generator):
        """Test that get_gsi_mapping_for_index returns None when no GSI mappings exist."""
        entity_config = {
            'entity_type': 'USER',
            'pk_template': '{user_id}',
            'fields': [{'name': 'user_id', 'type': 'string', 'required': True}],
            'access_patterns': [],
        }
        table_config = {'table_name': 'Users', 'partition_key': 'pk'}

        # Generate repository which internally calls get_gsi_mapping_for_index
        repo = generator.generate_repository('User', entity_config, table_config)
        assert isinstance(repo, str)
        # The function should handle None gracefully

    def test_generate_transaction_service_with_no_template(self, generator):
        """Test generate_transaction_service returns empty string when template is missing."""
        # Temporarily remove the template
        original_template = generator.transaction_service_template
        generator.transaction_service_template = None

        result = generator.generate_transaction_service([], {})
        assert result == ''

        # Restore template
        generator.transaction_service_template = original_template

    def test_generate_transaction_service_with_empty_patterns(self, generator):
        """Test generate_transaction_service returns empty string when no patterns provided."""
        result = generator.generate_transaction_service([], {})
        assert result == ''

    def test_get_return_description_for_object_return_type(self, generator):
        """Test _get_return_description for 'object' return type."""
        pattern = {'return_type': 'object', 'operation': 'TransactWrite'}
        result = generator._get_return_description(pattern)
        assert result == 'Result object from transaction'

    def test_get_return_description_for_unknown_return_type(self, generator):
        """Test _get_return_description for unknown return type."""
        pattern = {'return_type': 'unknown', 'operation': 'TransactWrite'}
        result = generator._get_return_description(pattern)
        assert result == 'Transaction result'

    def test_get_entity_imports_with_empty_patterns(self, generator):
        """Test _get_entity_imports returns empty string for empty patterns."""
        result = generator._get_entity_imports([])
        assert result == ''

    def test_get_table_list_with_empty_entities(self, generator):
        """Test _get_table_list returns empty string for empty entities_involved."""
        pattern = {'entities_involved': []}
        result = generator._get_table_list(pattern)
        assert result == ''

    def test_generate_usage_examples_with_usage_data(self, mock_schema_data, tmp_path):
        """Test generate_usage_examples with usage_data_path."""
        # Create usage data file
        usage_data = {
            'field_mappings': {
                'User': {
                    'user_id': 'user_123',
                    'email': 'test@example.com',
                }
            }
        }
        usage_file = tmp_path / 'usage_data.json'
        usage_file.write_text(json.dumps(usage_data))

        # Create schema file
        schema_file = tmp_path / 'schema.json'
        schema_file.write_text(json.dumps(mock_schema_data))

        # Create generator with usage data
        generator = Jinja2Generator(
            str(schema_file), language='python', usage_data_path=str(usage_file)
        )

        # Prepare required arguments
        all_entities = mock_schema_data['tables'][0]['entities']
        all_tables = mock_schema_data['tables']
        access_pattern_mapping = {}

        # Generate usage examples
        result = generator.generate_usage_examples(
            access_pattern_mapping, all_entities, all_tables
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_filter_resolvable_params_with_range_condition(self, tmp_path):
        """Test filter_resolvable_access_pattern_params with range conditions."""
        # Create schema with range condition pattern
        schema_with_range = {
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
                            'sk_template': '{timestamp}',
                            'fields': [
                                {'name': 'id', 'type': 'string', 'required': True},
                                {'name': 'timestamp', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [
                                {
                                    'pattern_id': 99,
                                    'name': 'query_by_date',
                                    'description': 'Query by date range',
                                    'operation': 'Query',
                                    'range_condition': '>=',
                                    'parameters': [
                                        {'name': 'id', 'type': 'string'},
                                        {'name': 'start_date', 'type': 'string'},
                                    ],
                                    'return_type': 'entity_list',
                                }
                            ],
                        }
                    },
                }
            ]
        }

        schema_file = tmp_path / 'schema.json'
        schema_file.write_text(json.dumps(schema_with_range))

        generator = Jinja2Generator(str(schema_file), language='python')

        # Prepare required arguments
        all_entities = schema_with_range['tables'][0]['entities']
        all_tables = schema_with_range['tables']
        access_pattern_mapping = {}

        # Generate usage examples which uses the filter
        result = generator.generate_usage_examples(
            access_pattern_mapping, all_entities, all_tables
        )
        assert isinstance(result, str)
        # The filter should handle range parameters correctly

    def test_check_template_is_pure_numeric_with_non_numeric_field(self, generator):
        """Test _check_template_is_pure_numeric returns False for non-numeric fields."""
        fields = [{'name': 'user_id', 'type': 'string'}]
        params = ['user_id']
        result = generator._check_template_is_pure_numeric('{user_id}', params, fields)
        assert result is False

    def test_preprocess_entity_config_with_numeric_gsi_keys(self, generator):
        """Test _preprocess_entity_config handles numeric GSI keys correctly."""
        entity_config = {
            'entity_type': 'USER',
            'pk_template': '{user_id}',
            'sk_template': '{timestamp}',
            'fields': [
                {'name': 'user_id', 'type': 'string', 'required': True},
                {'name': 'timestamp', 'type': 'integer', 'required': True},
                {'name': 'score', 'type': 'decimal', 'required': True},
            ],
            'gsi_mappings': [
                {
                    'name': 'ScoreIndex',
                    'pk_template': '{user_id}',
                    'sk_template': '{score}',
                }
            ],
            'access_patterns': [],
        }

        result = generator._preprocess_entity_config(entity_config)
        assert 'gsi_mappings' in result
        # Should detect numeric sort key in GSI
        assert result['gsi_mappings'][0]['sk_is_numeric'] is True


class TestMultiAttributeKeyHelpers:
    """Test helper methods for multi-attribute key processing."""

    @pytest.fixture
    def valid_schema_file(self, mock_schema_data, tmp_path):
        """Create a temporary valid schema file."""
        schema_file = tmp_path / 'schema.json'
        schema_file.write_text(json.dumps(mock_schema_data))
        return str(schema_file)

    @pytest.fixture
    def generator(self, valid_schema_file):
        """Create a Jinja2Generator instance for testing."""
        return Jinja2Generator(valid_schema_file, language='python')

    @pytest.fixture
    def sample_fields(self):
        """Sample field definitions for testing."""
        return [
            {'name': 'status', 'type': 'string'},
            {'name': 'created_at', 'type': 'string'},
            {'name': 'score', 'type': 'integer'},
            {'name': 'price', 'type': 'decimal'},
        ]

    # Tests for _extract_template_fields
    def test_extract_template_fields_from_string(self, generator):
        """Test extracting fields from a single template string."""
        result = generator._extract_template_fields('{status}')
        assert result == ['status']

        result = generator._extract_template_fields('STATUS#{status}#DATE#{created_at}')
        assert result == ['status', 'created_at']

    def test_extract_template_fields_from_list(self, generator):
        """Test extracting fields from a list of templates."""
        result = generator._extract_template_fields(['{status}', '{created_at}'])
        assert result == ['status', 'created_at']

        result = generator._extract_template_fields(['STATUS#{status}', 'DATE#{created_at}'])
        assert result == ['status', 'created_at']

    def test_extract_template_fields_from_none(self, generator):
        """Test extracting fields from None returns empty list."""
        result = generator._extract_template_fields(None)
        assert result == []

    def test_extract_template_fields_from_empty_string(self, generator):
        """Test extracting fields from empty string returns empty list."""
        result = generator._extract_template_fields('')
        assert result == []

    def test_extract_template_fields_from_empty_list(self, generator):
        """Test extracting fields from empty list returns empty list."""
        result = generator._extract_template_fields([])
        assert result == []

    # Tests for _process_key_template
    def test_process_key_template_single_attribute_string(self, generator, sample_fields):
        """Test processing a single-attribute string template."""
        result = generator._process_key_template('{status}', sample_fields, 'test_key')
        assert result['params'] == ['status']
        assert result['is_multi_attribute'] is False
        assert result['templates'] is None
        assert result['is_numeric'] is False

    def test_process_key_template_single_attribute_numeric(self, generator, sample_fields):
        """Test processing a single-attribute numeric template."""
        result = generator._process_key_template('{score}', sample_fields, 'test_key')
        assert result['params'] == ['score']
        assert result['is_multi_attribute'] is False
        assert result['templates'] is None
        assert result['is_numeric'] is True

    def test_process_key_template_multi_attribute_two_attrs(self, generator, sample_fields):
        """Test processing a multi-attribute template with 2 attributes."""
        result = generator._process_key_template(
            ['{status}', '{created_at}'], sample_fields, 'sort_key'
        )
        assert result['params'] == ['status', 'created_at']
        assert result['is_multi_attribute'] is True
        assert result['templates'] == ['{status}', '{created_at}']
        assert result['is_numeric'] is False

    def test_process_key_template_multi_attribute_four_attrs(self, generator, sample_fields):
        """Test processing a multi-attribute template with 4 attributes (max)."""
        fields = sample_fields + [
            {'name': 'attr3', 'type': 'string'},
            {'name': 'attr4', 'type': 'string'},
        ]
        result = generator._process_key_template(
            ['{status}', '{created_at}', '{attr3}', '{attr4}'], fields, 'sort_key'
        )
        assert result['params'] == ['status', 'created_at', 'attr3', 'attr4']
        assert result['is_multi_attribute'] is True
        assert len(result['templates']) == 4
        assert result['is_numeric'] is False

    def test_process_key_template_multi_attribute_empty_list_raises(
        self, generator, sample_fields
    ):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match='must have 1-4 attributes, got 0'):
            generator._process_key_template([], sample_fields, 'partition_key')

    def test_process_key_template_multi_attribute_too_many_raises(self, generator, sample_fields):
        """Test that >4 attributes raises ValueError."""
        fields = sample_fields + [
            {'name': 'a3', 'type': 'string'},
            {'name': 'a4', 'type': 'string'},
        ]
        with pytest.raises(ValueError, match='must have 1-4 attributes, got 5'):
            generator._process_key_template(
                ['{status}', '{created_at}', '{a3}', '{a4}', '{score}'], fields, 'sort_key'
            )

    def test_process_key_template_none_returns_empty(self, generator, sample_fields):
        """Test processing None template returns empty metadata."""
        result = generator._process_key_template(None, sample_fields, 'test_key')
        assert result['params'] == []
        assert result['is_multi_attribute'] is False
        assert result['templates'] is None
        assert result['is_numeric'] is False

    def test_process_key_template_empty_string_returns_empty(self, generator, sample_fields):
        """Test processing empty string returns empty metadata."""
        result = generator._process_key_template('', sample_fields, 'test_key')
        assert result['params'] == []
        assert result['is_multi_attribute'] is False
        assert result['templates'] is None
        assert result['is_numeric'] is False


@pytest.mark.unit
class TestMultiAttributeKeyPreprocessing:
    """Test preprocessing of entity configs with multi-attribute keys."""

    @pytest.fixture
    def valid_schema_file(self, mock_schema_data, tmp_path):
        """Create a temporary valid schema file."""
        schema_file = tmp_path / 'schema.json'
        schema_file.write_text(json.dumps(mock_schema_data))
        return str(schema_file)

    @pytest.fixture
    def generator(self, valid_schema_file):
        """Create a Jinja2Generator instance for testing."""
        return Jinja2Generator(valid_schema_file, language='python')

    def test_preprocess_entity_with_multi_attribute_sk(self, generator):
        """Test preprocessing entity with multi-attribute sort key."""
        entity_config = {
            'entity_type': 'ORDER',
            'pk_template': '{order_id}',
            'fields': [
                {'name': 'order_id', 'type': 'string'},
                {'name': 'store_id', 'type': 'string'},
                {'name': 'status', 'type': 'string'},
                {'name': 'created_at', 'type': 'string'},
            ],
            'gsi_mappings': [
                {
                    'name': 'StoreIndex',
                    'pk_template': '{store_id}',
                    'sk_template': ['{status}', '{created_at}'],
                }
            ],
            'access_patterns': [],
        }

        result = generator._preprocess_entity_config(entity_config)
        gsi = result['gsi_mappings'][0]

        assert gsi['pk_is_multi_attribute'] is False
        assert gsi['sk_is_multi_attribute'] is True
        assert gsi['sk_params'] == ['status', 'created_at']
        assert gsi['sk_templates'] == ['{status}', '{created_at}']
        assert gsi['sk_is_numeric'] is False

    def test_preprocess_entity_with_multi_attribute_pk(self, generator):
        """Test preprocessing entity with multi-attribute partition key."""
        entity_config = {
            'entity_type': 'MATCH',
            'pk_template': '{match_id}',
            'fields': [
                {'name': 'match_id', 'type': 'string'},
                {'name': 'tournament_id', 'type': 'string'},
                {'name': 'region', 'type': 'string'},
            ],
            'gsi_mappings': [
                {
                    'name': 'TournamentIndex',
                    'pk_template': ['{tournament_id}', '{region}'],
                    'sk_template': None,
                }
            ],
            'access_patterns': [],
        }

        result = generator._preprocess_entity_config(entity_config)
        gsi = result['gsi_mappings'][0]

        assert gsi['pk_is_multi_attribute'] is True
        assert gsi['pk_params'] == ['tournament_id', 'region']
        assert gsi['pk_templates'] == ['{tournament_id}', '{region}']
        assert gsi['pk_is_numeric'] is False

    def test_preprocess_entity_with_multi_attribute_pk_and_sk(self, generator):
        """Test preprocessing entity with both multi-attribute PK and SK."""
        entity_config = {
            'entity_type': 'MATCH',
            'pk_template': '{match_id}',
            'fields': [
                {'name': 'match_id', 'type': 'string'},
                {'name': 'tournament_id', 'type': 'string'},
                {'name': 'region', 'type': 'string'},
                {'name': 'round', 'type': 'string'},
                {'name': 'bracket', 'type': 'string'},
            ],
            'gsi_mappings': [
                {
                    'name': 'TournamentRegionIndex',
                    'pk_template': ['{tournament_id}', '{region}'],
                    'sk_template': ['{round}', '{bracket}'],
                }
            ],
            'access_patterns': [],
        }

        result = generator._preprocess_entity_config(entity_config)
        gsi = result['gsi_mappings'][0]

        assert gsi['pk_is_multi_attribute'] is True
        assert gsi['pk_params'] == ['tournament_id', 'region']
        assert gsi['sk_is_multi_attribute'] is True
        assert gsi['sk_params'] == ['round', 'bracket']

    def test_preprocess_entity_with_invalid_multi_attribute_pk_raises(self, generator):
        """Test that >4 attributes in PK raises ValueError."""
        entity_config = {
            'entity_type': 'TEST',
            'pk_template': '{id}',
            'fields': [
                {'name': 'id', 'type': 'string'},
                {'name': 'a1', 'type': 'string'},
                {'name': 'a2', 'type': 'string'},
                {'name': 'a3', 'type': 'string'},
                {'name': 'a4', 'type': 'string'},
                {'name': 'a5', 'type': 'string'},
            ],
            'gsi_mappings': [
                {
                    'name': 'TestIndex',
                    'pk_template': ['{a1}', '{a2}', '{a3}', '{a4}', '{a5}'],
                    'sk_template': None,
                }
            ],
            'access_patterns': [],
        }

        with pytest.raises(
            ValueError, match="Invalid GSI 'TestIndex'.*must have 1-4 attributes, got 5"
        ):
            generator._preprocess_entity_config(entity_config)

    def test_preprocess_entity_with_invalid_multi_attribute_sk_raises(self, generator):
        """Test that >4 attributes in SK raises ValueError."""
        entity_config = {
            'entity_type': 'TEST',
            'pk_template': '{id}',
            'fields': [
                {'name': 'id', 'type': 'string'},
                {'name': 'pk', 'type': 'string'},
                {'name': 's1', 'type': 'string'},
                {'name': 's2', 'type': 'string'},
                {'name': 's3', 'type': 'string'},
                {'name': 's4', 'type': 'string'},
                {'name': 's5', 'type': 'string'},
            ],
            'gsi_mappings': [
                {
                    'name': 'TestIndex',
                    'pk_template': '{pk}',
                    'sk_template': ['{s1}', '{s2}', '{s3}', '{s4}', '{s5}'],
                }
            ],
            'access_patterns': [],
        }

        with pytest.raises(
            ValueError, match="Invalid GSI 'TestIndex'.*must have 1-4 attributes, got 5"
        ):
            generator._preprocess_entity_config(entity_config)


@pytest.mark.unit
class TestMultiAttributeKeyCodeGeneration:
    """Test code generation for multi-attribute keys."""

    def test_generate_entity_with_multi_attribute_sk(self, tmp_path):
        """Test entity generation with multi-attribute sort key."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Orders', 'partition_key': 'order_id'},
                    'gsi_list': [
                        {
                            'name': 'StoreIndex',
                            'partition_key': 'store_id',
                            'sort_key': ['status', 'created_at'],
                            'projection': 'ALL',
                        }
                    ],
                    'entities': {
                        'Order': {
                            'entity_type': 'ORDER',
                            'pk_template': '{order_id}',
                            'gsi_mappings': [
                                {
                                    'name': 'StoreIndex',
                                    'pk_template': '{store_id}',
                                    'sk_template': ['{status}', '{created_at}'],
                                }
                            ],
                            'fields': [
                                {'name': 'order_id', 'type': 'string', 'required': True},
                                {'name': 'store_id', 'type': 'string', 'required': True},
                                {'name': 'status', 'type': 'string', 'required': True},
                                {'name': 'created_at', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }

        schema_file = tmp_path / 'schema.json'
        schema_file.write_text(json.dumps(schema))
        generator = Jinja2Generator(str(schema_file))

        entity_config = schema['tables'][0]['entities']['Order']
        result = generator.generate_entity('Order', entity_config)

        # Check for tuple return type
        assert (
            'def build_gsi_sk_for_lookup_store_index(cls, status, created_at) -> tuple:' in result
        )
        # Check for tuple return statement
        assert (
            'return (f"{status}", f"{created_at}")' in result
            or "return (f'{status}', f'{created_at}')" in result
        )
        # Check instance method
        assert 'def build_gsi_sk_store_index(self) -> tuple:' in result
        assert (
            'return (f"{self.status}", f"{self.created_at}")' in result
            or "return (f'{self.status}', f'{self.created_at}')" in result
        )

    def test_generate_entity_with_multi_attribute_pk(self, tmp_path):
        """Test entity generation with multi-attribute partition key."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Matches', 'partition_key': 'match_id'},
                    'gsi_list': [
                        {
                            'name': 'TournamentIndex',
                            'partition_key': ['tournament_id', 'region'],
                            'projection': 'ALL',
                        }
                    ],
                    'entities': {
                        'Match': {
                            'entity_type': 'MATCH',
                            'pk_template': '{match_id}',
                            'gsi_mappings': [
                                {
                                    'name': 'TournamentIndex',
                                    'pk_template': ['{tournament_id}', '{region}'],
                                    'sk_template': None,
                                }
                            ],
                            'fields': [
                                {'name': 'match_id', 'type': 'string', 'required': True},
                                {'name': 'tournament_id', 'type': 'string', 'required': True},
                                {'name': 'region', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }

        schema_file = tmp_path / 'schema.json'
        schema_file.write_text(json.dumps(schema))
        generator = Jinja2Generator(str(schema_file))

        entity_config = schema['tables'][0]['entities']['Match']
        result = generator.generate_entity('Match', entity_config)

        # Check for tuple return type on PK
        assert (
            'def build_gsi_pk_for_lookup_tournament_index(cls, tournament_id, region) -> tuple:'
            in result
        )
        assert (
            'return (f"{tournament_id}", f"{region}")' in result
            or "return (f'{tournament_id}', f'{region}')" in result
        )

    def test_repository_with_multi_attribute_sk_range_query(self, tmp_path):
        """Test repository with multi-attribute SK and range condition."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Orders', 'partition_key': 'order_id'},
                    'gsi_list': [
                        {
                            'name': 'StoreIndex',
                            'partition_key': 'store_id',
                            'sort_key': ['status', 'created_at'],
                            'projection': 'ALL',
                        }
                    ],
                    'entities': {
                        'Order': {
                            'entity_type': 'ORDER',
                            'pk_template': '{order_id}',
                            'gsi_mappings': [
                                {
                                    'name': 'StoreIndex',
                                    'pk_template': '{store_id}',
                                    'sk_template': ['{status}', '{created_at}'],
                                }
                            ],
                            'fields': [
                                {'name': 'order_id', 'type': 'string', 'required': True},
                                {'name': 'store_id', 'type': 'string', 'required': True},
                                {'name': 'status', 'type': 'string', 'required': True},
                                {'name': 'created_at', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [
                                {
                                    'pattern_id': 1,
                                    'name': 'get_store_orders_by_status',
                                    'description': 'Get store orders filtered by status',
                                    'operation': 'Query',
                                    'index_name': 'StoreIndex',
                                    'range_condition': 'begins_with',
                                    'parameters': [
                                        {'name': 'store_id', 'type': 'string'},
                                        {'name': 'status', 'type': 'string'},
                                        {'name': 'created_at', 'type': 'string'},
                                    ],
                                    'return_type': 'entity_list',
                                }
                            ],
                        }
                    },
                }
            ]
        }

        schema_file = tmp_path / 'schema.json'
        schema_file.write_text(json.dumps(schema))
        generator = Jinja2Generator(str(schema_file))

        entity_config = schema['tables'][0]['entities']['Order']
        table_config = schema['tables'][0]['table_config']
        result = generator.generate_repository(
            'Order', entity_config, table_config, schema['tables'][0]
        )

        # Should generate multi-attribute query with range condition
        assert "Key('store_id').eq(gsi_pk)" in result
        assert "Key('status').eq(status)" in result
        assert "Key('created_at').begins_with(created_at)" in result

    def test_repository_with_multi_attribute_pk_query(self, tmp_path):
        """Test repository with multi-attribute PK query."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Matches', 'partition_key': 'match_id'},
                    'gsi_list': [
                        {
                            'name': 'TournamentRegionIndex',
                            'partition_key': ['tournament_id', 'region'],
                            'sort_key': ['round', 'bracket'],
                            'projection': 'ALL',
                        }
                    ],
                    'entities': {
                        'Match': {
                            'entity_type': 'MATCH',
                            'pk_template': '{match_id}',
                            'gsi_mappings': [
                                {
                                    'name': 'TournamentRegionIndex',
                                    'pk_template': ['{tournament_id}', '{region}'],
                                    'sk_template': ['{round}', '{bracket}'],
                                }
                            ],
                            'fields': [
                                {'name': 'match_id', 'type': 'string', 'required': True},
                                {'name': 'tournament_id', 'type': 'string', 'required': True},
                                {'name': 'region', 'type': 'string', 'required': True},
                                {'name': 'round', 'type': 'string', 'required': True},
                                {'name': 'bracket', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [
                                {
                                    'pattern_id': 1,
                                    'name': 'get_tournament_matches',
                                    'description': 'Get tournament matches',
                                    'operation': 'Query',
                                    'index_name': 'TournamentRegionIndex',
                                    'parameters': [
                                        {'name': 'tournament_id', 'type': 'string'},
                                        {'name': 'region', 'type': 'string'},
                                    ],
                                    'return_type': 'entity_list',
                                }
                            ],
                        }
                    },
                }
            ]
        }

        schema_file = tmp_path / 'schema.json'
        schema_file.write_text(json.dumps(schema))
        generator = Jinja2Generator(str(schema_file))

        entity_config = schema['tables'][0]['entities']['Match']
        table_config = schema['tables'][0]['table_config']
        result = generator.generate_repository(
            'Match', entity_config, table_config, schema['tables'][0]
        )

        # Should generate multi-attribute PK query
        assert 'gsi_pk_tuple = Match.build_gsi_pk_for_lookup_tournament_region_index' in result
        assert "Key('tournament_id').eq(gsi_pk_tuple[0])" in result
        assert "Key('region').eq(gsi_pk_tuple[1])" in result

    def test_is_unsafe_include_projection_with_multi_attribute_templates(self, tmp_path):
        """Test _is_unsafe_include_projection handles multi-attribute templates."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Orders', 'partition_key': 'order_id'},
                    'gsi_list': [
                        {
                            'name': 'StoreIndex',
                            'partition_key': 'store_id',
                            'sort_key': ['status', 'created_at'],
                            'projection': 'INCLUDE',
                            'included_attributes': ['driver_id'],
                        }
                    ],
                    'entities': {
                        'Order': {
                            'entity_type': 'ORDER',
                            'pk_template': '{order_id}',
                            'gsi_mappings': [
                                {
                                    'name': 'StoreIndex',
                                    'pk_template': '{store_id}',
                                    'sk_template': ['{status}', '{created_at}'],
                                }
                            ],
                            'fields': [
                                {'name': 'order_id', 'type': 'string', 'required': True},
                                {'name': 'store_id', 'type': 'string', 'required': True},
                                {'name': 'status', 'type': 'string', 'required': True},
                                {'name': 'created_at', 'type': 'string', 'required': True},
                                {'name': 'driver_id', 'type': 'string', 'required': False},
                                {'name': 'customer_address', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }

        schema_file = tmp_path / 'schema.json'
        schema_file.write_text(json.dumps(schema))
        generator = Jinja2Generator(str(schema_file))

        gsi = schema['tables'][0]['gsi_list'][0]
        entity_config = schema['tables'][0]['entities']['Order']
        table_config = schema['tables'][0]['table_config']

        # customer_address is required but not projected (and not a key field)
        # status and created_at are in multi-attribute SK template (always projected)
        result = generator._is_unsafe_include_projection(gsi, entity_config, table_config)
        assert result is True

    def test_is_unsafe_include_projection_safe_with_multi_attribute_keys(self, tmp_path):
        """Test _is_unsafe_include_projection returns False when all required fields are projected."""
        schema = {
            'tables': [
                {
                    'table_config': {'table_name': 'Orders', 'partition_key': 'order_id'},
                    'gsi_list': [
                        {
                            'name': 'StoreIndex',
                            'partition_key': 'store_id',
                            'sort_key': ['status', 'created_at'],
                            'projection': 'INCLUDE',
                            'included_attributes': ['customer_address'],
                        }
                    ],
                    'entities': {
                        'Order': {
                            'entity_type': 'ORDER',
                            'pk_template': '{order_id}',
                            'gsi_mappings': [
                                {
                                    'name': 'StoreIndex',
                                    'pk_template': '{store_id}',
                                    'sk_template': ['{status}', '{created_at}'],
                                }
                            ],
                            'fields': [
                                {'name': 'order_id', 'type': 'string', 'required': True},
                                {'name': 'store_id', 'type': 'string', 'required': True},
                                {'name': 'status', 'type': 'string', 'required': True},
                                {'name': 'created_at', 'type': 'string', 'required': True},
                                {'name': 'customer_address', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [],
                        }
                    },
                }
            ]
        }

        schema_file = tmp_path / 'schema.json'
        schema_file.write_text(json.dumps(schema))
        generator = Jinja2Generator(str(schema_file))

        gsi = schema['tables'][0]['gsi_list'][0]
        entity_config = schema['tables'][0]['entities']['Order']
        table_config = schema['tables'][0]['table_config']

        # All required fields are either projected or in key templates
        result = generator._is_unsafe_include_projection(gsi, entity_config, table_config)
        assert result is False
