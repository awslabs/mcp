"""Tests for explanation_generator.py module."""

from awslabs.ccapi_mcp_server.explanation_generator import (
    _explain_dict,
    _explain_list,
    _format_value,
    generate_explanation,
)


class TestExplanationGenerator:
    """Test explanation generator functions."""

    def test_generate_explanation_basic(self):
        """Test basic explanation generation."""
        content = {'key': 'value', 'number': 42}
        result = generate_explanation(content, 'Test Context', 'create', 'detailed', 'Testing')

        assert 'Test Context' in result
        assert 'create' in result.lower()
        assert 'key' in result
        assert 'value' in result

    def test_generate_explanation_no_context(self):
        """Test explanation without context."""
        content = {'simple': 'data'}
        result = generate_explanation(content, '', 'analyze', 'summary', '')

        assert 'simple' in result
        assert 'data' in result

    def test_explain_dict_basic(self):
        """Test explaining dictionary content."""
        props = {'name': 'test', 'count': 5, 'enabled': True}
        result = _explain_dict(props, 'detailed')

        assert 'name' in result
        assert 'test' in result
        assert 'count' in result
        assert '5' in result

    def test_explain_list_basic(self):
        """Test explaining list content."""
        items = ['item1', 'item2', 'item3']
        result = _explain_list(items, 'detailed')

        assert 'item1' in result
        assert 'item2' in result
        assert 'item3' in result

    def test_format_value_string(self):
        """Test formatting string values."""
        result = _format_value('test string')
        assert 'test string' in result

    def test_format_value_number(self):
        """Test formatting numeric values."""
        result = _format_value(42)
        assert '42' in result

    def test_format_value_boolean(self):
        """Test formatting boolean values."""
        result = _format_value(True)
        assert 'True' in result

    def test_explain_list_complex(self):
        """Test explaining complex lists."""
        items = [{'name': 'item1'}, {'name': 'item2'}]
        result = _explain_list(items, 'detailed')

        assert 'item1' in result
        assert 'item2' in result

    def test_explain_dict_nested(self):
        """Test explaining nested dictionaries."""
        data = {'level1': {'level2': {'value': 'nested'}}}
        result = _explain_dict(data, 'detailed')

        assert 'level1' in result
        # The nested content is shown in the detailed format
        assert 'level2' in result or 'Nested configuration' in result
        assert 'nested' in result or 'dict with' in result

    def test_explain_dict_with_tags(self):
        """Test explaining dictionary with AWS tags."""
        content = {
            'BucketName': 'test-bucket',
            'Tags': [
                {'Key': 'Environment', 'Value': 'Test'},
                {'Key': 'MANAGED_BY', 'Value': 'CCAPI-MCP-SERVER'},
            ],
        }
        result = _explain_dict(content, 'detailed')

        assert 'Environment' in result
        assert 'MANAGED_BY' in result
        assert 'DEFAULT' in result

    def test_explain_dict_empty(self):
        """Test explaining empty dictionary."""
        result = _explain_dict({}, 'detailed')
        assert result is not None
        assert '0 properties' in result

    def test_explain_list_empty(self):
        """Test explaining empty list."""
        result = _explain_list([], 'detailed')
        assert result is not None
        assert '0 items' in result

    def test_generate_explanation_different_formats(self):
        """Test explanation with different formats."""
        content = {'test': 'data'}

        detailed = generate_explanation(content, 'Test', 'create', 'detailed', '')
        summary = generate_explanation(content, 'Test', 'create', 'summary', '')
        technical = generate_explanation(content, 'Test', 'create', 'technical', '')

        # All should contain the basic structure
        assert '## Test - Create Operation' in detailed
        assert '## Test - Create Operation' in summary
        assert '## Test - Create Operation' in technical
        assert 'test' in detailed
        assert 'data' in detailed

    def test_generate_explanation_different_operations(self):
        """Test explanation with different operations."""
        content = {'test': 'data'}

        create = generate_explanation(content, 'Test', 'create', 'detailed', '')
        update = generate_explanation(content, 'Test', 'update', 'detailed', '')
        delete = generate_explanation(content, 'Test', 'delete', 'detailed', '')

        assert 'create' in create.lower()
        assert 'update' in update.lower()
        assert 'delete' in delete.lower()

    def test_format_value_long_string(self):
        """Test formatting very long strings."""
        long_string = 'a' * 200
        result = _format_value(long_string)
        assert len(result) < len(long_string) + 50  # Should be truncated
        assert '...' in result

    def test_explain_list_large(self):
        """Test explaining large lists."""
        large_list = [f'item{i}' for i in range(20)]
        result = _explain_list(large_list, 'detailed')
        assert '...' in result or 'more' in result.lower()

    def test_explain_dict_large(self):
        """Test explaining large dictionaries."""
        large_dict = {f'key{i}': f'value{i}' for i in range(20)}
        result = _explain_dict(large_dict, 'detailed')
        assert result is not None
        assert '20 properties' in result
        # The function shows all properties, not truncated
        assert 'key0' in result
        assert 'key19' in result
