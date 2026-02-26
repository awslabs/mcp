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

"""MCP function execution tests."""


def test_mcp_tool_functions():
    """Test all MCP tool functions."""
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

    result = search_best_practices.fn(pillar='SECURITY')
    assert isinstance(result, list)

    # Test list_pillars
    result = list_pillars.fn()
    assert isinstance(result, dict)

    # Test well_architected_framework_review
    result = well_architected_framework_review.fn()
    assert isinstance(result, dict)
    assert 'framework' in result

    # Test get_best_practice
    practices = search_best_practices.fn()
    if practices:
        result = get_best_practice.fn(practices[0]['id'])
        assert result is None or isinstance(result, dict)

    # Test get_related_practices
    if practices:
        result = get_related_practices.fn(practices[0]['id'])
        assert isinstance(result, list)


def test_tool_names():
    """Test tool names."""
    from well_architected_bp_mcp_server.server import (
        get_best_practice,
        get_related_practices,
        list_pillars,
        search_best_practices,
        well_architected_framework_review,
    )

    assert search_best_practices.name == 'search_best_practices'
    assert get_best_practice.name == 'get_best_practice'
    assert list_pillars.name == 'list_pillars'
    assert get_related_practices.name == 'get_related_practices'
    assert well_architected_framework_review.name == 'well_architected_framework_review'
