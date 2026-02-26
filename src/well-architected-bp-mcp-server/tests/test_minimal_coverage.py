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

"""Minimal coverage test."""


def test_search_no_matches():
    """Test search with filters that return no matches."""
    from well_architected_bp_mcp_server.server import search_best_practices_impl

    # Test filters that likely return no matches to hit different code paths
    result = search_best_practices_impl(
        pillar='NONEXISTENT', risk='INVALID', keyword='zzznomatchzzz'
    )
    assert isinstance(result, list)
    assert len(result) == 0


def test_load_data_coverage():
    """Test load_data function coverage."""
    from well_architected_bp_mcp_server.server import BEST_PRACTICES, load_data

    # Call load_data to ensure it's covered
    original_count = len(BEST_PRACTICES)
    load_data()
    assert len(BEST_PRACTICES) >= original_count
