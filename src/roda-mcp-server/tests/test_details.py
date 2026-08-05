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

"""Tests for the get_dataset_details tool.

Covers successful lookup and not-found case.

Run: uv run python -m pytest tests/test_details.py -v
"""

import json
from awslabs.roda_mcp_server.server import get_dataset_details


async def test_get_dataset_details_found(setup_server, patch_fetch):
    """Looking up a valid slug returns the full dataset object."""
    result = await get_dataset_details('nasa-nex')
    data = json.loads(result)

    assert data['Slug'] == 'nasa-nex'
    assert data['Name'] == 'NASA NEX Climate Data'
    assert 'Resources' in data
    assert 'License' in data


async def test_get_dataset_details_not_found(setup_server, patch_fetch):
    """Looking up a nonexistent slug returns an error with a suggestion."""
    result = await get_dataset_details('nonexistent-slug')
    data = json.loads(result)

    assert 'error' in data
    assert 'nonexistent-slug' in data['error']
    assert 'suggestion' in data
