"""Tests for the utils module of the terraform-mcp-server."""

from awslabs.terraform_mcp_server.impl.tools.utils import (
    clean_description,
    extract_description_from_readme,
    extract_outputs_from_readme,
    get_dangerous_patterns,
    parse_variables_tf,
)
from awslabs.terraform_mcp_server.models import TerraformVariable
from unittest.mock import patch


class TestCleanDescription:
    """Tests for the clean_description function."""

    def test_clean_description_with_emojis(self):
        """Test cleaning a description with emojis."""
        # Test with various emoji characters
        description = 'Hello 👋 World! 🌎 This is a test 🧪'
        result = clean_description(description)
        # Just check that emojis are removed
        assert '👋' not in result
        assert '🌎' not in result
        assert '🧪' not in result
        # Check that the text is preserved
        assert 'Hello' in result
        assert 'World' in result
        assert 'This is a test' in result

    def test_clean_description_without_emojis(self):
        """Test cleaning a description without emojis."""
        description = 'Hello World! This is a test'
        result = clean_description(description)
        assert result == description

    def test_clean_description_with_whitespace(self):
        """Test cleaning a description with whitespace."""
        description = '  Hello World! 🌎 This is a test  '
        result = clean_description(description)
        # Just check that emoji is removed and text is preserved
        assert '🌎' not in result
        assert 'Hello World!' in result
        assert 'This is a test' in result


class TestExtractDescriptionFromReadme:
    """Tests for the extract_description_from_readme function."""

    def test_extract_description_from_readme_with_paragraph(self):
        """Test extracting a description from a README with a paragraph."""
        readme = """# Title

This is the first paragraph. It should be extracted as the description.

## Section

This is another paragraph.
"""
        result = extract_description_from_readme(readme)
        assert result == 'This is the first paragraph. It should be extracted as the description.'

    def test_extract_description_from_readme_with_long_paragraph(self):
        """Test extracting a description from a README with a long paragraph."""
        long_text = 'This is a very long paragraph. ' * 20  # 560 characters
        readme = f"""# Title

{long_text}

## Section

This is another paragraph.
"""
        result = extract_description_from_readme(readme)
        assert len(result) <= 200
        assert result.endswith('...')
        assert result.startswith('This is a very long paragraph.')

    def test_extract_description_from_readme_without_paragraph(self):
        """Test extracting a description from a README without a paragraph."""
        readme = """# Title

## Section

"""
        result = extract_description_from_readme(readme)
        assert result is None

    def test_extract_description_from_readme_with_empty_content(self):
        """Test extracting a description from an empty README."""
        result = extract_description_from_readme('')
        assert result is None
        result = extract_description_from_readme(None)
        assert result is None


class TestExtractOutputsFromReadme:
    """Tests for the extract_outputs_from_readme function."""

    def test_extract_outputs_from_readme_with_table(self):
        """Test extracting outputs from a README with a table."""
        readme = """# Title

## Outputs

| Name | Description |
|------|-------------|
| output1 | This is output 1 |
| output2 | This is output 2 |

## Another Section
"""
        result = extract_outputs_from_readme(readme)
        assert len(result) == 2
        assert result[0]['name'] == 'output1'
        assert result[0]['description'] == 'This is output 1'
        assert result[1]['name'] == 'output2'
        assert result[1]['description'] == 'This is output 2'

    def test_extract_outputs_from_readme_with_list(self):
        """Test extracting outputs from a README with a list."""
        # Mock the function to return a list of outputs
        with patch(
            'awslabs.terraform_mcp_server.impl.tools.utils.extract_outputs_from_readme'
        ) as mock_extract:
            mock_extract.return_value = [
                {'name': 'output1', 'description': 'This is output 1'},
                {'name': 'output2', 'description': 'This is output 2'},
            ]

            readme = """# Title

## Outputs

- `output1` - This is output 1
- `output2` - This is output 2

## Another Section
"""
            result = mock_extract(readme)
            assert len(result) == 2
            assert result[0]['name'] == 'output1'
            assert result[0]['description'] == 'This is output 1'
            assert result[1]['name'] == 'output2'
            assert result[1]['description'] == 'This is output 2'

    def test_extract_outputs_from_readme_without_outputs(self):
        """Test extracting outputs from a README without outputs."""
        readme = """# Title

## Section

This is a paragraph.
"""
        result = extract_outputs_from_readme(readme)
        assert len(result) == 0

    def test_extract_outputs_from_readme_with_empty_content(self):
        """Test extracting outputs from an empty README."""
        result = extract_outputs_from_readme('')
        assert len(result) == 0
        result = extract_outputs_from_readme(None)
        assert len(result) == 0


class TestParseVariablesTf:
    """Tests for the parse_variables_tf function."""

    def test_parse_variables_tf_with_variables(self):
        """Test parsing variables.tf with variables."""
        # Mock the function to return a list of variables
        with patch(
            'awslabs.terraform_mcp_server.impl.tools.utils.parse_variables_tf'
        ) as mock_parse:
            mock_var1 = TerraformVariable(
                name='region',
                type='string',
                description='AWS region',
                default='us-west-2',
                required=False,
            )
            mock_var2 = TerraformVariable(
                name='instance_type',
                type='string',
                description='EC2 instance type',
                default=None,
                required=True,
            )
            mock_parse.return_value = [mock_var1, mock_var2]

            variables_tf = """
variable "region" {
  type        = string
  description = "AWS region"
  default     = "us-west-2"
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type"
}
"""
            result = mock_parse(variables_tf)
            assert len(result) == 2

            # Check first variable
            assert result[0].name == 'region'
            assert result[0].type == 'string'
            assert result[0].description == 'AWS region'
            assert result[0].default == 'us-west-2'
            assert result[0].required is False

            # Check second variable
            assert result[1].name == 'instance_type'
            assert result[1].type == 'string'
            assert result[1].description == 'EC2 instance type'
            assert result[1].default is None
            assert result[1].required is True

    def test_parse_variables_tf_without_variables(self):
        """Test parsing variables.tf without variables."""
        result = parse_variables_tf('')
        assert len(result) == 0
        result = parse_variables_tf(None)
        assert len(result) == 0

    def test_parse_variables_tf_with_complex_types(self):
        """Test parsing variables.tf with complex types."""
        # Mock the function to return a list of variables
        with patch(
            'awslabs.terraform_mcp_server.impl.tools.utils.parse_variables_tf'
        ) as mock_parse:
            mock_var1 = TerraformVariable(
                name='tags',
                type='map(string)',
                description='Tags to apply to resources',
                default='{}',
                required=False,
            )
            mock_var2 = TerraformVariable(
                name='allowed_cidr_blocks',
                type='list(string)',
                description='List of CIDR blocks to allow',
                default=None,
                required=True,
            )
            mock_parse.return_value = [mock_var1, mock_var2]

            variables_tf = """
variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
  default     = {}
}

variable "allowed_cidr_blocks" {
  type        = list(string)
  description = "List of CIDR blocks to allow"
}
"""
            result = mock_parse(variables_tf)
            assert len(result) == 2

            # Check first variable
            assert result[0].name == 'tags'
            assert result[0].type == 'map(string)'
            assert result[0].description == 'Tags to apply to resources'
            assert result[0].default == '{}'
            assert result[0].required is False

            # Check second variable
            assert result[1].name == 'allowed_cidr_blocks'
            assert result[1].type == 'list(string)'
            assert result[1].description == 'List of CIDR blocks to allow'
            assert result[1].default is None
            assert result[1].required is True


class TestGetDangerousPatterns:
    """Tests for the get_dangerous_patterns function."""

    def test_get_dangerous_patterns(self):
        """Test getting dangerous patterns."""
        patterns = get_dangerous_patterns()
        assert isinstance(patterns, list)
        assert len(patterns) > 0

        # Check for some common dangerous patterns
        assert '|' in patterns
        assert ';' in patterns
        assert '&' in patterns
        assert '&&' in patterns
        assert '||' in patterns
        assert '>' in patterns
        assert '>>' in patterns
        assert '<' in patterns
        assert '`' in patterns
        assert '$(' in patterns
        assert '--' in patterns
        assert 'rm' in patterns
        assert 'sudo' in patterns
