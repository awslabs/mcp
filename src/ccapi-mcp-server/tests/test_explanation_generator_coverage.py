"""Additional tests for explanation_generator.py coverage."""

from awslabs.ccapi_mcp_server.explanation_generator import (
    _explain_dict,
    _explain_list,
    _format_value,
    generate_explanation,
)


class TestExplanationGeneratorCoverage:
    """Additional tests to boost explanation generator coverage."""

    def test_generate_explanation_no_context_no_operation(self):
        """Test generate_explanation with no context and analyze operation."""
        content = {'test': 'data'}
        result = generate_explanation(content, '', 'analyze', 'detailed', '')

        assert '## Data Analysis (dict)' in result
        assert 'test' in result

    def test_generate_explanation_with_user_intent(self):
        """Test generate_explanation with user intent."""
        content = {'service': 's3'}
        result = generate_explanation(
            content, 'S3 Setup', 'create', 'detailed', 'Testing deployment'
        )

        assert '**User Intent:** Testing deployment' in result
        assert '## S3 Setup - Create Operation' in result

    def test_generate_explanation_string_content(self):
        """Test generate_explanation with string content."""
        content = 'This is a test string content'
        result = generate_explanation(content, 'String Test', 'analyze', 'detailed', '')

        assert '**Content:** This is a test string content' in result

    def test_generate_explanation_long_string_content(self):
        """Test generate_explanation with very long string content."""
        content = 'a' * 600  # Longer than 500 chars
        result = generate_explanation(content, 'Long String', 'analyze', 'detailed', '')

        assert '**Content:**' in result
        assert '...' in result

    def test_generate_explanation_number_content(self):
        """Test generate_explanation with numeric content."""
        result = generate_explanation(42, 'Number Test', 'analyze', 'detailed', '')

        assert '**Value:** 42 (int)' in result

    def test_generate_explanation_boolean_content(self):
        """Test generate_explanation with boolean content."""
        result = generate_explanation(True, 'Boolean Test', 'analyze', 'detailed', '')

        assert '**Value:** True (bool)' in result

    def test_generate_explanation_other_content_type(self):
        """Test generate_explanation with other content types."""

        class CustomObject:
            def __str__(self):
                return 'custom object'

        obj = CustomObject()
        result = generate_explanation(obj, 'Custom Test', 'analyze', 'detailed', '')

        assert '**Content Type:** CustomObject' in result
        assert 'custom object' in result

    def test_generate_explanation_update_operation(self):
        """Test generate_explanation with update operation."""
        content = {'bucket': 'test'}
        result = generate_explanation(content, 'S3', 'update', 'detailed', '')

        assert '**Infrastructure Operation Notes:**' in result
        assert 'This operation will modify AWS resources' in result

    def test_explain_dict_with_underscore_keys(self):
        """Test _explain_dict ignores keys starting with underscore."""
        data = {
            'normal_key': 'value',
            '_private_key': 'hidden',  # pragma: allowlist secret
            '__internal': 'also hidden',
        }  # pragma: allowlist secret
        result = _explain_dict(data, 'detailed')

        assert 'normal_key' in result  # pragma: allowlist secret
        assert '_private_key' not in result  # pragma: allowlist secret
        assert '__internal' not in result

    def test_explain_dict_nested_detailed_format(self):
        """Test _explain_dict with nested dict in detailed format."""
        data = {
            'config': {
                'setting1': 'value1',
                'setting2': 'value2',
                'setting3': 'value3',
                'setting4': 'value4',
                'setting5': 'value5',
                'setting6': 'value6',  # More than 5 items
            }
        }
        result = _explain_dict(data, 'detailed')

        assert 'Nested configuration with 6 properties' in result
        assert 'setting1' in result
        assert '... and 1 more properties' in result

    def test_explain_dict_list_detailed_format(self):
        """Test _explain_dict with list in detailed format."""
        data = {
            'items': ['item1', 'item2', 'item3', 'item4']  # More than 3 items
        }
        result = _explain_dict(data, 'detailed')

        assert 'List with 4 items' in result
        assert 'Item 1' in result
        assert '... and 1 more items' in result

    def test_explain_dict_empty_tags(self):
        """Test _explain_dict with empty Tags list."""
        data = {'BucketName': 'test-bucket', 'Tags': []}
        result = _explain_dict(data, 'detailed')

        assert 'Tags:** (0 tags)' in result

    def test_explain_dict_mixed_tags(self):
        """Test _explain_dict with mixed user and default tags."""
        data = {
            'Tags': [
                {'Key': 'Environment', 'Value': 'Production'},
                {'Key': 'MANAGED_BY', 'Value': 'CCAPI-MCP-SERVER'},
                {'Key': 'Owner', 'Value': 'TeamA'},
                {'Key': 'MCP_SERVER_VERSION', 'Value': '1.0.0'},
            ]
        }
        result = _explain_dict(data, 'detailed')

        assert '*User Tags:*' in result
        assert 'Environment: Production' in result
        assert '*Management Tags:*' in result
        assert 'MANAGED_BY: CCAPI-MCP-SERVER (DEFAULT)' in result

    def test_explain_list_detailed_with_dicts(self):
        """Test _explain_list with dictionary items in detailed format."""
        data = [
            {'name': 'item1', 'type': 'A', 'extra1': 'val1', 'extra2': 'val2'},
            {'name': 'item2', 'type': 'B'},
        ]
        result = _explain_list(data, 'detailed')

        assert 'Dictionary with 4 keys' in result
        assert 'name: "item1"' in result
        assert '... and 1 more properties' in result

    def test_explain_list_large_detailed(self):
        """Test _explain_list with more than 10 items in detailed format."""
        data = [f'item{i}' for i in range(15)]
        result = _explain_list(data, 'detailed')

        assert '15 items' in result
        assert 'Item 1' in result
        assert 'Item 10' in result
        assert '... and 5 more items' in result

    def test_explain_list_summary_format(self):
        """Test _explain_list with summary format (non-detailed)."""
        data = ['item1', 'item2', 'item3']
        result = _explain_list(data, 'summary')

        assert '3 items' in result
        # Should not have detailed item breakdown
        assert 'Item 1:' not in result

    def test_format_value_edge_cases(self):
        """Test _format_value with various edge cases."""
        # Test with None
        assert 'NoneType object' in _format_value(None)

        # Test with empty containers
        assert 'dict with 0 keys' in _format_value({})
        assert 'list with 0 items' in _format_value([])

        # Test with complex object
        class ComplexObj:
            pass

        assert 'ComplexObj object' in _format_value(ComplexObj())

    def test_explain_dict_non_detailed_format(self):
        """Test _explain_dict with non-detailed format."""
        data = {
            'nested': {'key': 'value'},
            'list_items': ['a', 'b', 'c'],
        }  # pragma: allowlist secret
        result = _explain_dict(data, 'summary')

        assert 'nested' in result
        assert 'Nested configuration' in result
        # Should not show detailed breakdown in summary format
        assert 'key:' not in result  # pragma: allowlist secret
