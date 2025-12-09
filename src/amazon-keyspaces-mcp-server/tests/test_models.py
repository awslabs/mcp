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

"""Tests for models module."""

import unittest
from awslabs.amazon_keyspaces_mcp_server.models import QueryInput


class TestModels(unittest.TestCase):
    """Test cases for models."""

    def test_sanitize_query_with_hidden_characters(self):
        """Test query sanitization removes hidden unicode characters."""
        input_data = QueryInput(keyspace='test', query='SELECT\u200b * FROM\ufeff users\u0000')
        self.assertEqual(input_data.query, 'SELECT * FROM users')


if __name__ == '__main__':
    unittest.main()
