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
        import json

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
