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

        # Should contain GSI key builder class methods
        assert 'build_gsi_pk_for_lookup_userstatusindex' in result
        assert 'build_gsi_sk_for_lookup_userstatusindex' in result
        assert 'build_gsi_pk_for_lookup_scoreindex' in result
        assert 'build_gsi_sk_for_lookup_scoreindex' in result

        # Should contain GSI key builder instance methods
        assert 'build_gsi_pk_userstatusindex' in result
        assert 'build_gsi_sk_userstatusindex' in result
        assert 'build_gsi_pk_scoreindex' in result
        assert 'build_gsi_sk_scoreindex' in result

        # Should contain GSI prefix helper methods
        assert 'get_gsi_pk_prefix_userstatusindex' in result
        assert 'get_gsi_sk_prefix_userstatusindex' in result
        assert 'get_gsi_pk_prefix_scoreindex' in result
        assert 'get_gsi_sk_prefix_scoreindex' in result

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

        # Class method returns raw value
        assert 'def build_gsi_sk_for_lookup_gamepointsindex(cls, points):' in result
        assert 'return points' in result
        # Instance method returns raw value
        assert 'def build_gsi_sk_gamepointsindex(self):' in result
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

        # String GSI SK uses f-string and has -> str return type
        assert 'def build_gsi_sk_for_lookup_gametimeindex(cls, created_at) -> str:' in result
        assert 'return f"{created_at}"' in result
