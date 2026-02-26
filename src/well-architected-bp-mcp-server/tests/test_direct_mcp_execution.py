# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Direct MCP tool execution tests."""

import unittest.mock


def test_mcp_tools_execution():
    """Test MCP tools execution through fn attribute."""
    from well_architected_bp_mcp_server.server import (
        get_best_practice,
        get_related_practices,
        list_pillars,
        search_best_practices,
        well_architected_framework_review,
    )

    # Test search_best_practices
    result = search_best_practices.fn()
    assert isinstance(result, list)

    # Test list_pillars
    result = list_pillars.fn()
    assert isinstance(result, dict)

    # Test well_architected_framework_review
    result = well_architected_framework_review.fn()
    assert isinstance(result, dict)

    # Test get_best_practice with valid ID
    practices = search_best_practices.fn()
    if practices:
        result = get_best_practice.fn(practices[0]['id'])
        assert result is not None

    # Test get_related_practices
    if practices:
        result = get_related_practices.fn(practices[0]['id'])
        assert isinstance(result, list)


def test_wrapper_functions_with_mocks():
    """Test wrapper functions with mocked implementations."""
    test_cases = [
        ('search_best_practices_impl', [{'id': 'test'}], 'search_best_practices'),
        ('get_best_practice_impl', {'id': 'test'}, 'get_best_practice'),
        ('list_pillars_impl', {'SECURITY': 10}, 'list_pillars'),
        ('get_related_practices_impl', [], 'get_related_practices'),
        (
            'well_architected_framework_review_impl',
            {'framework': 'test'},
            'well_architected_framework_review',
        ),
    ]

    for internal_func, mock_return, wrapper_name in test_cases:
        with unittest.mock.patch(
            f'well_architected_bp_mcp_server.server.{internal_func}'
        ) as mock_func:
            mock_func.return_value = mock_return

            module = __import__('well_architected_bp_mcp_server.server', fromlist=[wrapper_name])
            wrapper_func = getattr(module, wrapper_name)

            if wrapper_name in ['get_best_practice', 'get_related_practices']:
                result = wrapper_func.fn('test_id')
            else:
                result = wrapper_func.fn()

            assert result == mock_return
            mock_func.assert_called()
