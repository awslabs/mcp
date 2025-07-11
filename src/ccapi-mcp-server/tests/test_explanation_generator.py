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

    def test_explain_list_with_large_dictionaries(self):
        """Test explaining lists containing dictionaries with many keys."""
        large_dict = {f'key{i}': f'value{i}' for i in range(10)}
        items = [large_dict, {'simple': 'dict'}]
        result = _explain_list(items, 'detailed')

        assert 'Dictionary with' in result
        assert 'more properties' in result  # Should mention there are more properties

    def test_explain_list_with_many_items(self):
        """Test explaining lists with more than 10 items."""
        items = [f'item{i}' for i in range(15)]
        result = _explain_list(items, 'detailed')

        assert 'item0' in result
        assert 'more items' in result  # Should mention there are more items

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

    def test_format_value_none(self):
        """Test _format_value with None."""
        result = _format_value(None)
        assert 'None' in result

    def test_format_value_list_long(self):
        """Test _format_value with long list."""
        long_list = list(range(10))
        result = _format_value(long_list)
        assert '10 items' in result

    def test_explain_dict_summary_with_long_list(self):
        """Test _explain_dict with summary format and long list."""
        data = {'short_key': 'value', 'long_list': list(range(10)), 'nested': {'deep': 'value'}}
        result = _explain_dict(data, 'summary')
        assert '3 properties' in result
        assert '10 items' in result

    def test_generate_explanation_all_operations(self):
        """Test generate_explanation for all operations."""
        properties = {'BucketName': 'test-bucket'}

        # Create
        result = generate_explanation(
            properties, 'Creating', 'create', 'detailed', 'AWS::S3::Bucket'
        )
        assert 'Creating' in result
        assert 'Infrastructure Operation Notes' in result

        # Update
        result = generate_explanation(
            properties, 'Updating', 'update', 'detailed', 'AWS::S3::Bucket'
        )
        assert 'Updating' in result
        assert 'Infrastructure Operation Notes' in result

        # Delete
        result = generate_explanation(
            properties, 'Deleting', 'delete', 'detailed', 'AWS::S3::Bucket'
        )
        assert 'Deleting' in result
        assert 'Infrastructure Operation Notes' in result

        # Analyze (no operation notes)
        result = generate_explanation(
            properties, 'Analyzing', 'analyze', 'detailed', 'AWS::S3::Bucket'
        )
        assert 'Analyzing Analysis' in result
        assert 'Infrastructure Operation Notes' not in result

    def test_generate_explanation_with_different_content_types(self):
        """Test generate_explanation with various content types."""
        # String content
        result = generate_explanation(
            'This is a string content', 'String Test', 'analyze', 'detailed', ''
        )
        assert 'String Test' in result
        assert 'Content:' in result

        # Long string content (should be truncated)
        long_string = 'x' * 1000
        result = generate_explanation(long_string, 'Long String', 'analyze', 'detailed', '')
        assert 'Long String' in result
        assert '...' in result  # Should be truncated

        # Numeric content
        result = generate_explanation(42, 'Number Test', 'analyze', 'detailed', '')
        assert 'Number Test' in result
        assert '42' in result
        assert 'int' in result

        # Boolean content
        result = generate_explanation(True, 'Boolean Test', 'analyze', 'detailed', '')
        assert 'Boolean Test' in result
        assert 'True' in result
        assert 'bool' in result

        # Custom object content
        class CustomObject:
            def __str__(self):
                return 'Custom object string representation'

        obj = CustomObject()
        result = generate_explanation(obj, 'Object Test', 'analyze', 'detailed', '')
        assert 'Object Test' in result
        assert 'CustomObject' in result
        assert 'Content Type:' in result

    def test_format_value_edge_cases(self):
        """Test _format_value with edge cases."""
        # Empty string
        result = _format_value('')
        assert '""' in result or result == ''

        # Zero
        result = _format_value(0)
        assert '0' in result

        # Empty list
        result = _format_value([])
        assert '[]' in result or '0 items' in result

        # Empty dict
        result = _format_value({})
        assert '{}' in result or '0 properties' in result

        # Single item list
        result = _format_value(['single'])
        assert 'single' in result

        # None value
        result = _format_value(None)
        assert 'None' in result

        # Custom object
        class TestObject:
            pass

        result = _format_value(TestObject())
        assert 'TestObject' in result
