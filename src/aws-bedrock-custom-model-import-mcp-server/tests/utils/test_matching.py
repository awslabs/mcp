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

"""Tests for the matching utility functions."""

from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.matching import approximate_match


class TestApproximateMatch:
    """Tests for the approximate_match function."""

    def test_exact_match(self):
        """Test exact string matching."""
        candidates = ['test-model', 'other-model', 'another-model']
        target = 'test-model'

        result = approximate_match(candidates, target)

        assert result is not None
        assert len(result) == 1
        assert result[0] == 'test-model'

    def test_approximate_match(self):
        """Test approximate string matching."""
        candidates = ['test-model-v1', 'test-model-v2', 'other-model']
        target = 'test model'

        result = approximate_match(candidates, target)

        assert result is not None
        assert len(result) == 2
        assert 'test-model-v1' in result
        assert 'test-model-v2' in result

    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        candidates = ['Test-Model', 'OTHER-MODEL', 'another-model']
        target = 'test-model'

        result = approximate_match(candidates, target)

        assert result is not None
        assert len(result) == 1
        assert result[0] == 'Test-Model'

    def test_token_order_match(self):
        """Test token order independent matching."""
        candidates = ['model-test', 'test-model', 'model-other']
        target = 'test model'

        result = approximate_match(candidates, target)

        assert result is not None
        assert len(result) == 1
        assert 'test-model' in result

    def test_partial_match(self):
        """Test partial string matching."""
        candidates = ['test-model-extended', 'model-test', 'other-model']
        target = 'test'

        result = approximate_match(candidates, target)

        assert result is not None
        assert len(result) == 1
        assert 'model-test' in result

    def test_threshold_filtering(self):
        """Test threshold-based filtering."""
        candidates = ['completely-different', 'totally-unrelated', 'test-model']
        target = 'test'

        # With default threshold
        result = approximate_match(candidates, target)
        assert result is not None
        assert 'test-model' in result
        assert 'completely-different' not in result
        assert 'totally-unrelated' not in result

        # With very high threshold - should return None
        result = approximate_match(candidates, target, threshold=400)
        assert result is None

        # With very low threshold - should include more matches
        result = approximate_match(candidates, target, threshold=50)
        assert result is not None
        assert len(result) > 0

    def test_empty_candidates(self):
        """Test with empty candidates list."""
        candidates = []
        target = 'test'

        result = approximate_match(candidates, target)

        assert result is None

    def test_no_matches_above_threshold(self):
        """Test when no matches meet the threshold."""
        candidates = ['completely-different', 'totally-unrelated']
        target = 'test-model'

        result = approximate_match(candidates, target, threshold=200)

        assert result is None

    def test_multiple_equal_matches(self):
        """Test multiple matches with equal scores."""
        candidates = ['test-model-v1', 'test-model-v2']
        target = 'test-model'

        result = approximate_match(candidates, target)

        assert result is not None
        assert len(result) == 2
        assert 'test-model-v1' in result
        assert 'test-model-v2' in result

    def test_special_characters(self):
        """Test matching with special characters."""
        candidates = ['test_model', 'test-model', 'test.model']
        target = 'test model'

        result = approximate_match(candidates, target)

        assert result is not None
        assert len(result) > 0
        # All should match with similar scores
        assert set(result) == set(candidates)

    def test_whitespace_handling(self):
        """Test handling of whitespace in strings."""
        candidates = ['test model', 'test  model', 'test-model']
        target = 'test model'

        result = approximate_match(candidates, target)

        assert result is not None
        assert 'test model' in result
