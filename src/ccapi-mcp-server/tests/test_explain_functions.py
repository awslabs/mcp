"""Tests for explanation helper functions."""

import pytest
from awslabs.ccapi_mcp_server.server import _generate_explanation, _explain_dict, _explain_list, _format_value


class TestExplainFunctions:
    """Test explanation helper functions."""

    def test_generate_explanation_dict(self):
        """Test _generate_explanation with dict content."""
        content = {'key1': 'value1', 'key2': {'nested': 'value'}}
        result = _generate_explanation(content, 'Test Context', 'create', 'detailed', 'Test Intent')
        
        assert '## Test Context - Create Operation' in result
        assert '**User Intent:** Test Intent' in result
        assert 'Configuration Summary' in result
        assert 'Infrastructure Operation Notes' in result

    def test_generate_explanation_list(self):
        """Test _generate_explanation with list content."""
        content = ['item1', 'item2', 'item3']
        result = _generate_explanation(content, 'List Context', 'analyze', 'summary', '')
        
        assert '## List Context Analysis' in result
        assert 'List Summary' in result
        assert '3 items' in result

    def test_generate_explanation_string(self):
        """Test _generate_explanation with string content."""
        content = 'This is a test string'
        result = _generate_explanation(content, '', 'analyze', 'detailed', '')
        
        assert '## Data Analysis (str)' in result
        assert '**Content:** This is a test string' in result

    def test_generate_explanation_long_string(self):
        """Test _generate_explanation with long string."""
        content = 'x' * 600  # Longer than 500 chars
        result = _generate_explanation(content, '', 'analyze', 'detailed', '')
        
        assert '...' in result  # Should be truncated

    def test_generate_explanation_number(self):
        """Test _generate_explanation with number."""
        content = 42
        result = _generate_explanation(content, '', 'analyze', 'detailed', '')
        
        assert '**Value:** 42 (int)' in result

    def test_generate_explanation_boolean(self):
        """Test _generate_explanation with boolean."""
        content = True
        result = _generate_explanation(content, '', 'analyze', 'detailed', '')
        
        assert '**Value:** True (bool)' in result

    def test_generate_explanation_other_type(self):
        """Test _generate_explanation with other type."""
        content = set([1, 2, 3])
        result = _generate_explanation(content, '', 'analyze', 'detailed', '')
        
        assert '**Content Type:** set' in result

    def test_explain_dict_with_tags(self):
        """Test _explain_dict with AWS tags."""
        data = {
            'BucketName': 'test-bucket',
            'Tags': [
                {'Key': 'MANAGED_BY', 'Value': 'CCAPI-MCP-SERVER'},
                {'Key': 'user-tag', 'Value': 'user-value'}
            ]
        }
        result = _explain_dict(data, 'detailed')
        
        assert 'Configuration Summary' in result
        assert 'BucketName' in result
        assert 'Tags:** (2 tags)' in result
        assert 'Management Tags' in result
        assert 'User Tags' in result

    def test_explain_dict_nested_objects(self):
        """Test _explain_dict with nested objects."""
        data = {
            'simple': 'value',
            'nested_dict': {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6},  # More than 5
            'nested_list': ['item1', 'item2', 'item3', 'item4']
        }
        result = _explain_dict(data, 'detailed')
        
        assert 'nested_dict:** (Nested configuration with 6 properties)' in result
        assert '... and 1 more properties' in result
        assert 'List with 4 items' in result
        assert '... and 1 more items' in result

    def test_explain_dict_summary_format(self):
        """Test _explain_dict with summary format."""
        data = {
            'nested_dict': {'a': 1, 'b': 2},
            'nested_list': ['item1', 'item2']
        }
        result = _explain_dict(data, 'summary')
        
        assert 'nested_dict:** (Nested configuration with 2 properties)' in result
        # Should not show detailed breakdown in summary format

    def test_explain_list_detailed(self):
        """Test _explain_list with detailed format."""
        data = ['item1', 'item2', 'item3', 'item4', 'item5', 'item6', 'item7', 'item8', 'item9', 'item10', 'item11']
        result = _explain_list(data, 'detailed')
        
        assert 'List Summary:** 11 items' in result
        assert 'Item 1:' in result
        assert 'Item 10:' in result
        assert '... and 1 more items' in result

    def test_explain_list_summary(self):
        """Test _explain_list with summary format."""
        data = ['item1', 'item2', 'item3', 'item4', 'item5', 'item6']
        result = _explain_list(data, 'summary')
        
        assert 'List Summary:** 6 items' in result
        assert 'Items: [' in result
        assert '... and 1 more' in result

    def test_format_value_string(self):
        """Test _format_value with string."""
        # Short string
        result = _format_value('short')
        assert result == '"short"'
        
        # Long string
        long_string = 'x' * 150
        result = _format_value(long_string)
        assert '...' in result
        assert len(result) < len(long_string) + 10

    def test_format_value_numbers(self):
        """Test _format_value with numbers."""
        assert _format_value(42) == '42'
        assert _format_value(3.14) == '3.14'
        assert _format_value(True) == 'True'

    def test_format_value_collections(self):
        """Test _format_value with collections."""
        assert _format_value({'a': 1, 'b': 2}) == '{dict with 2 keys}'
        assert _format_value([1, 2, 3]) == '[list with 3 items]'

    def test_format_value_other_types(self):
        """Test _format_value with other types."""
        result = _format_value(set([1, 2, 3]))
        assert 'set object' in result

    def test_explain_dict_private_keys(self):
        """Test _explain_dict skips private keys."""
        data = {
            'public_key': 'value',
            '_private_key': 'private_value',
            '__dunder_key': 'dunder_value'
        }
        result = _explain_dict(data, 'detailed')
        
        assert 'public_key' in result
        assert '_private_key' not in result
        assert '__dunder_key' not in result

    def test_explain_dict_empty_tags(self):
        """Test _explain_dict with empty tags."""
        data = {
            'BucketName': 'test-bucket',
            'Tags': []
        }
        result = _explain_dict(data, 'detailed')
        
        assert 'Tags:** (0 tags)' in result

    def test_explain_dict_non_dict_tags(self):
        """Test _explain_dict with non-dict tags."""
        data = {
            'BucketName': 'test-bucket',
            'Tags': ['not-a-dict', {'Key': 'valid', 'Value': 'tag'}]
        }
        result = _explain_dict(data, 'detailed')
        
        assert 'Tags:' in result
        # Should handle mixed content gracefully