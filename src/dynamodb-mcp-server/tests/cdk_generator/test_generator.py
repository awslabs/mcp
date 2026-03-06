"""Tests for CdkGenerator class."""

import json
import pytest
from awslabs.dynamodb_mcp_server.cdk_generator import CdkGenerator, CdkGeneratorError
from awslabs.dynamodb_mcp_server.cdk_generator.models import DataModel
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.fixture
def sample_data_model():
    """Return a sample data model JSON."""
    return {
        'tables': [
            {
                'TableName': 'UserTable',
                'AttributeDefinitions': [
                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                    {'AttributeName': 'sk', 'AttributeType': 'S'},
                ],
                'KeySchema': [
                    {'AttributeName': 'pk', 'KeyType': 'HASH'},
                    {'AttributeName': 'sk', 'KeyType': 'RANGE'},
                ],
            }
        ]
    }


@pytest.fixture
def generator():
    """Return a CdkGenerator instance."""
    return CdkGenerator()


class TestCdkGeneratorInit:
    """Test CdkGenerator initialization."""

    def test_init(self):
        """Test CdkGenerator initialization."""
        generator = CdkGenerator()
        assert (
            generator.templates_dir
            == Path(__file__).parent.parent.parent
            / 'awslabs'
            / 'dynamodb_mcp_server'
            / 'cdk_generator'
            / 'templates'
        )
        assert generator.jinja_env is not None


class TestGenerateMethod:
    """Test the main generate() method."""

    def test_generate_missing_json_file(self, generator):
        """Test generate with missing JSON file."""
        with pytest.raises(CdkGeneratorError, match='JSON file not found'):
            generator.generate(Path('/nonexistent/file.json'))

    def test_generate_existing_directory(self, generator, sample_data_model, tmp_path):
        """Test generate when cdk directory already exists."""
        # Create JSON file
        json_file = tmp_path / 'data_model.json'
        json_file.write_text(json.dumps(sample_data_model))

        # Create cdk directory
        cdk_dir = tmp_path / 'cdk'
        cdk_dir.mkdir()

        with pytest.raises(CdkGeneratorError, match='already exists'):
            generator.generate(json_file)

    @patch.object(CdkGenerator, '_render_template')
    @patch.object(CdkGenerator, '_check_table_name_collisions')
    @patch.object(CdkGenerator, '_parse_data_model')
    @patch.object(CdkGenerator, '_run_cdk_init')
    def test_generate_success_flow(
        self,
        mock_run_cdk_init,
        mock_parse_data_model,
        mock_check_collisions,
        mock_render_template,
        generator,
        sample_data_model,
        tmp_path,
    ):
        """Test successful generate flow calls all methods in correct order."""
        # Setup
        json_file = tmp_path / 'data_model.json'
        json_file.write_text(json.dumps(sample_data_model))
        cdk_dir = tmp_path / 'cdk'

        mock_data_model = DataModel.from_json(sample_data_model)
        mock_parse_data_model.return_value = mock_data_model

        # Execute
        generator.generate(json_file)

        # Verify directory was created
        assert cdk_dir.exists()

        # Verify all methods were called in correct order
        mock_run_cdk_init.assert_called_once_with(cdk_dir)
        mock_parse_data_model.assert_called_once_with(json_file)
        mock_check_collisions.assert_called_once_with(mock_data_model)
        mock_render_template.assert_called_once_with(mock_data_model, cdk_dir)

    @patch.object(CdkGenerator, '_run_cdk_init')
    def test_generate_cdk_init_failure(
        self, mock_run_cdk_init, generator, sample_data_model, tmp_path
    ):
        """Test generate handles cdk init failure."""
        json_file = tmp_path / 'data_model.json'
        json_file.write_text(json.dumps(sample_data_model))

        mock_run_cdk_init.side_effect = CdkGeneratorError('cdk init failed')

        with pytest.raises(CdkGeneratorError, match='cdk init failed'):
            generator.generate(json_file)

    @patch.object(CdkGenerator, '_parse_data_model')
    @patch.object(CdkGenerator, '_run_cdk_init')
    def test_generate_parse_data_model_failure(
        self,
        mock_run_cdk_init,
        mock_parse_data_model,
        generator,
        sample_data_model,
        tmp_path,
    ):
        """Test generate handles parse_data_model failure."""
        json_file = tmp_path / 'data_model.json'
        json_file.write_text(json.dumps(sample_data_model))

        mock_parse_data_model.side_effect = ValueError('Invalid JSON')

        with pytest.raises(ValueError, match='Invalid JSON'):
            generator.generate(json_file)

    @patch.object(CdkGenerator, '_check_table_name_collisions')
    @patch.object(CdkGenerator, '_parse_data_model')
    @patch.object(CdkGenerator, '_run_cdk_init')
    def test_generate_table_collision_failure(
        self,
        mock_run_cdk_init,
        mock_parse_data_model,
        mock_check_collisions,
        generator,
        sample_data_model,
        tmp_path,
    ):
        """Test generate handles table name collision."""
        json_file = tmp_path / 'data_model.json'
        json_file.write_text(json.dumps(sample_data_model))

        mock_data_model = DataModel.from_json(sample_data_model)
        mock_parse_data_model.return_value = mock_data_model
        mock_check_collisions.side_effect = CdkGeneratorError('Table name collision')

        with pytest.raises(CdkGeneratorError, match='Table name collision'):
            generator.generate(json_file)

    @patch.object(CdkGenerator, '_render_template')
    @patch.object(CdkGenerator, '_check_table_name_collisions')
    @patch.object(CdkGenerator, '_parse_data_model')
    @patch.object(CdkGenerator, '_run_cdk_init')
    def test_generate_render_template_failure(
        self,
        mock_run_cdk_init,
        mock_parse_data_model,
        mock_check_collisions,
        mock_render_template,
        generator,
        sample_data_model,
        tmp_path,
    ):
        """Test generate handles render_template failure."""
        json_file = tmp_path / 'data_model.json'
        json_file.write_text(json.dumps(sample_data_model))

        mock_data_model = DataModel.from_json(sample_data_model)
        mock_parse_data_model.return_value = mock_data_model
        mock_render_template.side_effect = CdkGeneratorError('Template rendering failed')

        with pytest.raises(CdkGeneratorError, match='Template rendering failed'):
            generator.generate(json_file)


class TestRunCdkInit:
    """Test _run_cdk_init method."""

    @patch('awslabs.dynamodb_mcp_server.cdk_generator.generator.subprocess.run')
    def test_run_cdk_init_success(self, mock_run, generator, tmp_path):
        """Test _run_cdk_init successful execution."""
        mock_run.return_value = None

        generator._run_cdk_init(tmp_path)

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ['npx', 'cdk', 'init', 'app', '--language', 'typescript']
        assert mock_run.call_args[1]['check'] is True

    @patch('awslabs.dynamodb_mcp_server.cdk_generator.generator.subprocess.run')
    def test_run_cdk_init_failure(self, mock_run, generator, tmp_path):
        """Test _run_cdk_init with command failure."""
        from subprocess import CalledProcessError

        mock_run.side_effect = CalledProcessError(returncode=1, cmd='npx', stderr='Error message')

        with pytest.raises(CdkGeneratorError, match='cdk init failed'):
            generator._run_cdk_init(tmp_path)

    @patch('awslabs.dynamodb_mcp_server.cdk_generator.generator.subprocess.run')
    def test_run_cdk_init_timeout(self, mock_run, generator, tmp_path):
        """Test _run_cdk_init with timeout."""
        from subprocess import TimeoutExpired

        mock_run.side_effect = TimeoutExpired(cmd='npx', timeout=120)

        with pytest.raises(CdkGeneratorError, match='cdk init timed out'):
            generator._run_cdk_init(tmp_path)

    @patch('awslabs.dynamodb_mcp_server.cdk_generator.generator.subprocess.run')
    def test_run_cdk_init_npx_not_found(self, mock_run, generator, tmp_path):
        """Test _run_cdk_init when npx is not found."""
        mock_run.side_effect = FileNotFoundError('npx not found')

        with pytest.raises(CdkGeneratorError, match='npx command not found'):
            generator._run_cdk_init(tmp_path)

    @patch('awslabs.dynamodb_mcp_server.cdk_generator.generator.subprocess.run')
    def test_run_cdk_init_generic_exception(self, mock_run, generator, tmp_path):
        """Test _run_cdk_init with generic exception."""
        mock_run.side_effect = RuntimeError('Unexpected error')

        with pytest.raises(CdkGeneratorError, match='cdk init failed.*Unexpected error'):
            generator._run_cdk_init(tmp_path)


class TestParseDataModel:
    """Test _parse_data_model method."""

    def test_parse_data_model_invalid_json(self, generator, tmp_path):
        """Test _parse_data_model with invalid JSON."""
        json_file = tmp_path / 'invalid.json'
        json_file.write_text('{ invalid json }')

        with pytest.raises(ValueError, match='Invalid JSON'):
            generator._parse_data_model(json_file)

    def test_parse_data_model_valid(self, generator, sample_data_model, tmp_path):
        """Test _parse_data_model with valid JSON."""
        json_file = tmp_path / 'valid.json'
        json_file.write_text(json.dumps(sample_data_model))

        data_model = generator._parse_data_model(json_file)
        assert len(data_model.tables) == 1
        assert data_model.tables[0].table_name == 'UserTable'

    def test_parse_data_model_read_exception(self, generator, tmp_path):
        """Test _parse_data_model with file read exception."""
        json_file = tmp_path / 'data.json'
        json_file.write_text('{}')

        # Mock open to raise an exception
        with patch('builtins.open', side_effect=PermissionError('Access denied')):
            with pytest.raises(ValueError, match='Failed to read JSON file'):
                generator._parse_data_model(json_file)


class TestCheckTableNameCollisions:
    """Test _check_table_name_collisions method."""

    def test_table_name_collision_raises_error(self, generator):
        """Test that table name collisions are detected and raise an error."""
        # Two tables that would produce the same variable name after camelCase conversion
        data_model_json = {
            'tables': [
                {
                    'TableName': 'User-Table',
                    'AttributeDefinitions': [
                        {'AttributeName': 'pk', 'AttributeType': 'S'},
                    ],
                    'KeySchema': [
                        {'AttributeName': 'pk', 'KeyType': 'HASH'},
                    ],
                },
                {
                    'TableName': 'User_Table',
                    'AttributeDefinitions': [
                        {'AttributeName': 'pk', 'AttributeType': 'S'},
                    ],
                    'KeySchema': [
                        {'AttributeName': 'pk', 'KeyType': 'HASH'},
                    ],
                },
            ]
        }
        data_model = DataModel.from_json(data_model_json)

        with pytest.raises(
            CdkGeneratorError,
            match=r"Table name collision detected\. Rename one of the tables to fix\. table1: 'User-Table', table2: 'User_Table', camelCase_name: 'userTable'",
        ):
            generator._check_table_name_collisions(data_model)

    def test_no_collision_with_different_names(self, generator):
        """Test that different table names don't raise collision errors."""
        data_model_json = {
            'tables': [
                {
                    'TableName': 'UserTable',
                    'AttributeDefinitions': [
                        {'AttributeName': 'pk', 'AttributeType': 'S'},
                    ],
                    'KeySchema': [
                        {'AttributeName': 'pk', 'KeyType': 'HASH'},
                    ],
                },
                {
                    'TableName': 'OrderTable',
                    'AttributeDefinitions': [
                        {'AttributeName': 'pk', 'AttributeType': 'S'},
                    ],
                    'KeySchema': [
                        {'AttributeName': 'pk', 'KeyType': 'HASH'},
                    ],
                },
            ]
        }
        data_model = DataModel.from_json(data_model_json)

        # Should not raise any exception
        generator._check_table_name_collisions(data_model)


class TestRenderTemplate:
    """Test _render_template method."""

    def test_render_template_success(self, generator, tmp_path, sample_data_model):
        """Test _render_template successful rendering."""
        data_model = DataModel.from_json(sample_data_model)
        cdk_dir = tmp_path / 'cdk'
        cdk_dir.mkdir()

        # Mock the template to return a simple string
        with patch.object(generator.jinja_env, 'get_template') as mock_get_template:
            mock_template = MagicMock()
            mock_template.render.return_value = 'test content\n'
            mock_get_template.return_value = mock_template

            generator._render_template(data_model, cdk_dir)

            # Verify the file was created with the exact content from template
            output_file = cdk_dir / 'lib' / 'cdk-stack.ts'
            assert output_file.exists()
            assert output_file.read_text() == 'test content\n'

    def test_render_template_missing_template(self, generator, tmp_path, sample_data_model):
        """Test _render_template with missing template file."""
        # Create generator with empty templates directory
        empty_templates = tmp_path / 'templates'
        empty_templates.mkdir()
        generator.templates_dir = empty_templates
        generator.jinja_env = __import__('jinja2').Environment(
            loader=__import__('jinja2').FileSystemLoader(str(empty_templates))
        )

        data_model = DataModel.from_json(sample_data_model)

        with pytest.raises(CdkGeneratorError, match='Required template file is missing'):
            generator._render_template(data_model, tmp_path)

    def test_render_template_generic_exception(self, generator, tmp_path, sample_data_model):
        """Test _render_template with generic exception during rendering."""
        data_model = DataModel.from_json(sample_data_model)

        # Mock template.render to raise an exception
        with patch.object(generator.jinja_env, 'get_template') as mock_get_template:
            mock_template = MagicMock()
            mock_template.render.side_effect = RuntimeError('Rendering failed')
            mock_get_template.return_value = mock_template

            with pytest.raises(CdkGeneratorError, match='Failed to render template'):
                generator._render_template(data_model, tmp_path)


class TestToCamelCase:
    """Test _to_camel_case method."""

    @pytest.fixture
    def generator(self):
        """Create a CdkGenerator instance."""
        return CdkGenerator()

    def test_pascal_case_to_camel_case(self, generator):
        """Test converting PascalCase to camelCase."""
        assert generator._to_camel_case('UserProfiles') == 'userProfiles'
        assert generator._to_camel_case('OrderHistory') == 'orderHistory'

    def test_kebab_case_to_camel_case(self, generator):
        """Test converting kebab-case to camelCase."""
        assert generator._to_camel_case('Product-Catalog') == 'productCatalog'
        assert generator._to_camel_case('user-table') == 'userTable'

    def test_snake_case_to_camel_case(self, generator):
        """Test converting snake_case to camelCase."""
        assert generator._to_camel_case('Analytics_Events') == 'analyticsEvents'
        assert generator._to_camel_case('user_profiles') == 'userProfiles'

    def test_single_word_to_camel_case(self, generator):
        """Test converting single word to camelCase."""
        assert generator._to_camel_case('Users') == 'users'
        assert generator._to_camel_case('orders') == 'orders'

    def test_mixed_separators_to_camel_case(self, generator):
        """Test converting mixed separators to camelCase."""
        assert generator._to_camel_case('User-Profile_Table') == 'userProfileTable'


class TestToPascalCase:
    """Test _to_pascal_case method."""

    @pytest.fixture
    def generator(self):
        """Create a CdkGenerator instance."""
        return CdkGenerator()

    def test_pascal_case_preserved(self, generator):
        """Test that PascalCase is preserved."""
        assert generator._to_pascal_case('UserProfiles') == 'UserProfiles'
        assert generator._to_pascal_case('OrderHistory') == 'OrderHistory'

    def test_kebab_case_to_pascal_case(self, generator):
        """Test converting kebab-case to PascalCase."""
        assert generator._to_pascal_case('Product-Catalog') == 'ProductCatalog'
        assert generator._to_pascal_case('user-table') == 'UserTable'

    def test_snake_case_to_pascal_case(self, generator):
        """Test converting snake_case to PascalCase."""
        assert generator._to_pascal_case('Analytics_Events') == 'AnalyticsEvents'
        assert generator._to_pascal_case('user_profiles') == 'UserProfiles'

    def test_single_word_to_pascal_case(self, generator):
        """Test converting single word to PascalCase."""
        assert generator._to_pascal_case('users') == 'Users'
        assert generator._to_pascal_case('Orders') == 'Orders'

    def test_mixed_separators_to_pascal_case(self, generator):
        """Test converting mixed separators to PascalCase."""
        assert generator._to_pascal_case('User-Profile_Table') == 'UserProfileTable'

    def test_camel_case_to_pascal_case(self, generator):
        """Test converting camelCase to PascalCase."""
        assert generator._to_pascal_case('userProfiles') == 'UserProfiles'
        assert generator._to_pascal_case('orderHistory') == 'OrderHistory'


class TestReadmeTemplate:
    """Test README template functionality."""

    @patch('awslabs.dynamodb_mcp_server.cdk_generator.generator.shutil.copy2')
    def test_copy_readme_template_success(self, mock_copy2, generator, tmp_path):
        """Test _copy_readme_template successful execution."""
        target_dir = tmp_path / 'cdk'
        target_dir.mkdir()

        # Execute
        generator._copy_readme_template(target_dir)

        # Verify shutil.copy2 was called with correct paths
        readme_template = generator.templates_dir / 'README.md'
        readme_dest = target_dir / 'README.md'
        mock_copy2.assert_called_once_with(readme_template, readme_dest)

    @patch('awslabs.dynamodb_mcp_server.cdk_generator.generator.shutil.copy2')
    def test_copy_readme_template_failure(self, mock_copy2, generator, tmp_path):
        """Test _copy_readme_template with copy failure."""
        target_dir = tmp_path / 'cdk'
        target_dir.mkdir()

        # Mock shutil.copy2 to raise exception
        mock_copy2.side_effect = PermissionError('Permission denied')

        # Verify CdkGeneratorError is raised with proper format
        with pytest.raises(CdkGeneratorError) as exc_info:
            generator._copy_readme_template(target_dir)

        # Verify error message format includes all required parts
        error_msg = str(exc_info.value)
        assert 'README template copy failed' in error_msg
        assert 'readme_template:' in error_msg
        assert 'readme_dest:' in error_msg
        assert 'error:' in error_msg
        assert 'Permission denied' in error_msg

        # Verify exception chaining
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, PermissionError)
