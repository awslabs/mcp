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
"""Tests for the template_list resource."""

import json
from awslabs.aws_serverless_mcp_server.resources.template_list import handle_template_list


class TestTemplateList:
    """Tests for the template_list resource."""

    def test_handle_template_list(self):
        """Test the handle_template_list function."""
        # Call the function
        result = handle_template_list()

        # Verify the result structure
        assert 'contents' in result
        assert 'metadata' in result
        assert 'count' in result['metadata']

        # Verify the count matches the number of templates
        assert result['metadata']['count'] == len(result['contents'])

        # Verify we have the expected templates
        template_names = [json.loads(item['text'])['name'] for item in result['contents']]
        assert 'backend' in template_names
        assert 'frontend' in template_names
        assert 'fullstack' in template_names

        # Verify the URI format
        for item in result['contents']:
            assert item['uri'].startswith('template://')

        # Verify each template has the required fields
        for item in result['contents']:
            template = json.loads(item['text'])
            assert 'name' in template
            assert 'description' in template
            assert 'frameworks' in template
            assert isinstance(template['frameworks'], list)
