# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for explanation module."""

import pytest
from awslabs.ccapi_mcp_server.impl.tools.explanation import (
    _explain_dict,
    _explain_list,
    _explain_security_scan,
    _format_value,
    _generate_explanation,
    explain_impl,
)
from awslabs.ccapi_mcp_server.models.models import ExplainRequest


class TestExplanation:
    """Test explanation functions."""

    def test_format_value_string(self):
        """Test _format_value with string."""
        assert _format_value('test') == '"test"'

    def test_format_value_number(self):
        """Test _format_value with number."""
        assert _format_value(42) == '42'

    def test_format_value_boolean(self):
        """Test _format_value with boolean."""
        assert _format_value(True) == 'True'

    def test_format_value_none(self):
        """Test _format_value with None."""
        result = _format_value(None)
        assert 'NoneType object' in result

    def test_format_value_list(self):
        """Test _format_value with list."""
        result = _format_value([1, 2, 3])
        assert '[list with 3 items]' in result

    def test_format_value_dict(self):
        """Test _format_value with dict."""
        result = _format_value({'key': 'value'})
        assert '{dict with 1 keys}' in result

    def test_format_value_long_string(self):
        """Test _format_value with long string."""
        long_string = 'x' * 1000
        result = _format_value(long_string)
        assert len(result) < 1000
        assert '...' in result

    def test_explain_dict_basic(self):
        """Test _explain_dict with basic dict."""
        data = {'key': 'value', 'number': 42}
        result = _explain_dict(data, 'detailed')
        assert 'key' in result
        assert 'number' in result

    def test_explain_dict_with_tags(self):
        """Test _explain_dict with Tags."""
        data = {
            'Tags': [{'Key': 'user', 'Value': 'test'}, {'Key': 'MANAGED_BY', 'Value': 'system'}]
        }
        result = _explain_dict(data, 'detailed')
        assert 'user' in result

    def test_explain_dict_skip_private(self):
        """Test _explain_dict skips private keys."""
        data = {'public': 'value', '_private': 'hidden'}
        result = _explain_dict(data, 'detailed')
        assert 'public' in result
        assert '_private' not in result

    def test_explain_list_basic(self):
        """Test _explain_list with basic list."""
        data = ['item1', 'item2', 'item3']
        result = _explain_list(data, 'detailed')
        assert 'Item 1' in result

    def test_explain_list_summary(self):
        """Test _explain_list with summary format."""
        data = list(range(15))
        result = _explain_list(data, 'summary')
        assert 'items' in result

    def test_explain_security_scan_passed(self):
        """Test _explain_security_scan with passed scan."""
        data = {
            'scan_status': 'PASSED',
            'raw_failed_checks': [],
            'raw_passed_checks': [{'check_id': 'CKV_1', 'check_name': 'Test'}],
        }
        result = _explain_security_scan(data)
        assert 'PASSED' in result

    def test_explain_security_scan_failed(self):
        """Test _explain_security_scan with failed scan."""
        data = {
            'scan_status': 'FAILED',
            'raw_failed_checks': [{'check_id': 'CKV_1', 'check_name': 'Test'}],
            'raw_passed_checks': [],
        }
        result = _explain_security_scan(data)
        assert 'ISSUES FOUND' in result

    def test_generate_explanation_basic(self):
        """Test _generate_explanation with basic content."""
        result = _generate_explanation({'test': 'data'}, 'Test', 'create', 'detailed', 'Intent')
        assert 'Test' in result

    def test_generate_explanation_different_operations(self):
        """Test _generate_explanation with different operations."""
        content = {'test': 'data'}
        _generate_explanation(content, 'Test', 'update', 'detailed', 'Intent')
        _generate_explanation(content, 'Test', 'delete', 'detailed', 'Intent')
        _generate_explanation(content, 'Test', 'analyze', 'detailed', 'Intent')

    @pytest.mark.asyncio
    async def test_explain_impl_with_content(self):
        """Test explain_impl with content."""
        request = ExplainRequest(content={'test': 'data'})
        result = await explain_impl(request, {})
        assert 'explanation' in result

    @pytest.mark.asyncio
    async def test_explain_impl_with_generated_code_token(self):
        """Test explain_impl with generated code token."""
        workflow_store = {
            'test_token': {'type': 'generated_code', 'data': {'properties': {'test': 'data'}}}
        }
        request = ExplainRequest(generated_code_token='test_token', content=None)
        result = await explain_impl(request, workflow_store)
        assert 'explanation' in result
        assert 'explained_token' in result

    @pytest.mark.asyncio
    async def test_explain_impl_invalid_token(self):
        """Test explain_impl with invalid token."""
        request = ExplainRequest(generated_code_token='invalid', content=None)
        with pytest.raises(Exception):
            await explain_impl(request, {})
