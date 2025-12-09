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

"""Tests for llm_context module."""

import unittest
from awslabs.amazon_keyspaces_mcp_server.llm_context import (
    build_query_result_context,
    build_table_details_context,
    dict_to_markdown,
)


class TestLlmContext(unittest.TestCase):
    """Test cases for llm_context functions."""

    def test_build_table_details_context_with_keyspaces_context(self):
        """Test building table context with Keyspaces-specific metadata."""
        table_details = {
            'keyspace_name': 'test_ks',
            'table_name': 'test_table',
            '_keyspaces_context': {'service_characteristics': 'serverless'},
        }
        result = build_table_details_context(table_details)
        self.assertIn('Service Characteristics', result)
        self.assertIn('serverless', result)

    def test_build_query_result_context_large_result(self):
        """Test query result context with large result set."""
        query_results = {'row_count': 150, 'columns': ['id'], 'rows': []}
        result = build_query_result_context(query_results)
        self.assertIn('Large Result', result)

    def test_dict_to_markdown_with_list_of_dicts(self):
        """Test markdown conversion with nested list of dicts."""
        data = {'items': [{'name': 'item1'}, {'name': 'item2'}]}
        result = dict_to_markdown(data)
        self.assertIn('Items', result)
        self.assertIn('Name', result)

    def test_dict_to_markdown_with_list_of_strings(self):
        """Test markdown conversion with list of strings (covers line 341)."""
        data = {'features': ['feature1', 'feature2', 'feature3']}
        result = dict_to_markdown(data)
        self.assertIn('Features', result)
        self.assertIn('- feature1', result)
        self.assertIn('- feature2', result)
        self.assertIn('- feature3', result)


if __name__ == '__main__':
    unittest.main()
