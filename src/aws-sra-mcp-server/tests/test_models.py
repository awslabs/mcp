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

from awslabs.aws_sra_mcp_server.models import RecommendationResult, SearchResult


def test_search_result_model():
    """Test the SearchResult model."""
    # Test with all fields
    result = SearchResult(
        rank_order=1,
        url="https://docs.aws.amazon.com/security-reference-architecture/",
        title="AWS Security Reference Architecture",
        context="A guide for security architecture",
    )
    assert result.rank_order == 1
    assert result.url == "https://docs.aws.amazon.com/security-reference-architecture/"
    assert result.title == "AWS Security Reference Architecture"
    assert result.context == "A guide for security architecture"

    # Test with optional fields omitted
    result = SearchResult(
        rank_order=2,
        url="https://docs.aws.amazon.com/security-hub/",
        title="AWS Security Hub",
    )
    assert result.rank_order == 2
    assert result.url == "https://docs.aws.amazon.com/security-hub/"
    assert result.title == "AWS Security Hub"
    assert result.context is None


def test_recommendation_result_model():
    """Test the RecommendationResult model."""
    # Test with all fields
    result = RecommendationResult(
        url="https://docs.aws.amazon.com/security-reference-architecture/",
        title="AWS Security Reference Architecture",
        context="A guide for security architecture",
    )
    assert result.url == "https://docs.aws.amazon.com/security-reference-architecture/"
    assert result.title == "AWS Security Reference Architecture"
    assert result.context == "A guide for security architecture"

    # Test with optional fields omitted
    result = RecommendationResult(
        url="https://docs.aws.amazon.com/security-hub/",
        title="AWS Security Hub",
    )
    assert result.url == "https://docs.aws.amazon.com/security-hub/"
    assert result.title == "AWS Security Hub"
    assert result.context is None
