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

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from awslabs.aws_sra_mcp_server.aws_documentation import (
    get_multiple_recommendations,
    get_recommendations,
    parse_recommendation_results,
    parse_search_results,
    search_sra_documentation,
)
from awslabs.aws_sra_mcp_server.models import RecommendationResult, SearchResult


class TestAwsDocumentation:
    """Test parse_recommendation_results function."""

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_execute_search_request_exception(self, mock_client, mock_context):
        """Test _execute_search_request with exception."""
        from awslabs.aws_sra_mcp_server.aws_documentation import _execute_search_request

        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = Exception("API Error")

        result = await _execute_search_request(mock_client_instance, "test query")
        assert result == {}

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_execute_recommendation_request_exception(self, mock_client, mock_context):
        """Test _execute_recommendation_request with exception."""
        from awslabs.aws_sra_mcp_server.aws_documentation import _execute_recommendation_request

        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = Exception("API Error")

        result = await _execute_recommendation_request(mock_client_instance, mock_context, "https://test.com")
        assert result == {}
        mock_client_instance.get.side_effect = Exception("API Error")

        result = await _execute_recommendation_request(
            mock_context, 
            mock_client_instance, 
            "https://example.com"
        )
        assert result == {}
        assert len(mock_context.errors) == 1

    def test_parse_empty_data(self):
        """Test parsing empty data."""
        result = parse_recommendation_results({})
        assert result == []

    def test_parse_highly_rated(self):
        """Test parsing highly rated recommendations."""
        data = {
            "highlyRated": {
                "items": [
                    {
                        "url": "https://example.com/1",
                        "assetTitle": "Test Title 1",
                        "abstract": "Test abstract 1",
                    },
                    {
                        "url": "https://example.com/2",
                        "assetTitle": "Test Title 2",
                        # No abstract
                    },
                ]
            }
        }
        results = parse_recommendation_results(data)
        assert len(results) == 2
        assert results[0].url == "https://example.com/1"
        assert results[0].title == "Test Title 1"
        assert results[0].context == "Test abstract 1"
        assert results[1].context is None

    def test_parse_journey(self):
        """Test parsing journey recommendations."""
        data = {
            "journey": {
                "items": [
                    {
                        "intent": "Security Setup",
                        "urls": [
                            {
                                "url": "https://example.com/journey1",
                                "assetTitle": "Journey Title 1",
                            }
                        ],
                    },
                    {
                        # No intent
                        "urls": [
                            {
                                "url": "https://example.com/journey2",
                                "assetTitle": "Journey Title 2",
                            }
                        ],
                    },
                ]
            }
        }
        results = parse_recommendation_results(data)
        assert len(results) == 2
        assert results[0].context == "Intent: Security Setup"
        assert results[1].context is None

    def test_parse_new_content(self):
        """Test parsing new content recommendations."""
        data = {
            "new": {
                "items": [
                    {
                        "url": "https://example.com/new1",
                        "assetTitle": "New Title 1",
                        "dateCreated": "2024-01-01",
                    },
                    {
                        "url": "https://example.com/new2",
                        "assetTitle": "New Title 2",
                        # No dateCreated
                    },
                ]
            }
        }
        results = parse_recommendation_results(data)
        assert len(results) == 2
        assert results[0].context == "New content added on 2024-01-01"
        assert results[1].context == "New content"

    def test_parse_similar_content(self):
        """Test parsing similar content recommendations."""
        data = {
            "similar": {
                "items": [
                    {
                        "url": "https://example.com/similar1",
                        "assetTitle": "Similar Title 1",
                        "abstract": "Similar abstract 1",
                    },
                    {
                        "url": "https://example.com/similar2",
                        "assetTitle": "Similar Title 2",
                        # No abstract
                    },
                ]
            }
        }
        results = parse_recommendation_results(data)
        assert len(results) == 2
        assert results[0].context == "Similar abstract 1"
        assert results[1].context == "Similar content"

    def test_parse_all_types(self):
        """Test parsing all recommendation types together."""
        data = {
            "highlyRated": {
                "items": [
                    {
                        "url": "https://example.com/rated",
                        "assetTitle": "Rated Title",
                        "abstract": "Rated abstract",
                    }
                ]
            },
            "journey": {
                "items": [
                    {
                        "intent": "Setup",
                        "urls": [
                            {
                                "url": "https://example.com/journey",
                                "assetTitle": "Journey Title",
                            }
                        ],
                    }
                ]
            },
            "new": {
                "items": [
                    {
                        "url": "https://example.com/new",
                        "assetTitle": "New Title",
                        "dateCreated": "2024-01-01",
                    }
                ]
            },
            "similar": {
                "items": [
                    {
                        "url": "https://example.com/similar",
                        "assetTitle": "Similar Title",
                        "abstract": "Similar abstract",
                    }
                ]
            },
        }
        results = parse_recommendation_results(data)
        assert len(results) == 4


class TestParseSearchResults:
    """Test parse_search_results function."""

    def test_parse_empty_data(self):
        """Test parsing empty search data."""
        result = parse_search_results({})
        assert result == []

    def test_parse_search_results_basic(self):
        """Test parsing basic search results."""
        data = {
            "suggestions": [
                {
                    "textExcerptSuggestion": {
                        "link": "https://example.com/1",
                        "title": "Test Title 1",
                        "summary": "Test summary 1",
                    }
                },
                {
                    "textExcerptSuggestion": {
                        "link": "https://example.com/2",
                        "title": "Test Title 2",
                        "suggestionBody": "Test body 2",
                    }
                },
                {
                    "textExcerptSuggestion": {
                        "link": "https://example.com/3",
                        "title": "Test Title 3",
                        "context": "Test context 3",
                    }
                },
            ]
        }
        results = parse_search_results(data)
        assert len(results) == 3
        assert results[0].rank_order == 1
        assert results[0].url == "https://example.com/1"
        assert results[0].title == "Test Title 1"
        assert results[0].context == "Test summary 1"
        assert results[1].context == "Test body 2"
        assert results[2].context == "Test context 3"

    def test_parse_search_results_with_limit(self):
        """Test parsing search results with limit."""
        data = {
            "suggestions": [
                {
                    "textExcerptSuggestion": {
                        "link": f"https://example.com/{i}",
                        "title": f"Test Title {i}",
                        "summary": f"Test summary {i}",
                    }
                }
                for i in range(1, 21)  # 20 items
            ]
        }
        results = parse_search_results(data, limit=5)
        assert len(results) == 5

    def test_parse_search_results_missing_fields(self):
        """Test parsing search results with missing fields."""
        data = {
            "suggestions": [
                {
                    "textExcerptSuggestion": {
                        # Missing link, title, and context fields
                    }
                },
                {
                    # Missing textExcerptSuggestion entirely
                },
            ]
        }
        results = parse_search_results(data)
        assert len(results) == 1  # Only the first one should be included
        assert results[0].url == ""
        assert results[0].title == ""
        assert results[0].context == ""


@pytest.mark.asyncio
class TestSearchSraDocumentation:
    """Test search_sra_documentation function."""

    @patch("awslabs.aws_sra_mcp_server.aws_documentation._execute_search_request")
    async def test_search_success(self, mock_execute, mock_context):
        """Test successful search."""
        mock_execute.return_value = {
            "suggestions": [
                {
                    "textExcerptSuggestion": {
                        "link": "https://example.com/1",
                        "title": "Test Title 1",
                        "summary": "Test summary 1",
                    }
                }
            ]
        }

        results = await search_sra_documentation(mock_context, "test query")
        assert len(results) == 1
        assert results[0].url == "https://example.com/1"
        mock_execute.assert_called_once()

    @patch("awslabs.aws_sra_mcp_server.aws_documentation._execute_search_request")
    async def test_search_exception(self, mock_execute, mock_context):
        """Test search with exception."""
        mock_execute.side_effect = Exception("API Error")

        results = await search_sra_documentation(mock_context, "test query")
        assert results == []
        assert len(mock_context.errors) == 1
        assert "Error searching AWS documentation" in mock_context.errors[0]


@pytest.mark.asyncio
class TestGetRecommendations:
    """Test get_recommendations function."""

    @patch("awslabs.aws_sra_mcp_server.aws_documentation._execute_recommendation_request")
    async def test_get_recommendations_success(self, mock_execute, mock_context):
        """Test successful recommendations retrieval."""
        mock_execute.return_value = {
            "highlyRated": {
                "items": [
                    {
                        "url": "https://example.com/1",
                        "assetTitle": "Test Title 1",
                        "abstract": "Test abstract 1",
                    }
                ]
            }
        }

        results = await get_recommendations(mock_context, "https://example.com/test")
        assert len(results) == 1
        assert results[0].url == "https://example.com/1"
        mock_execute.assert_called_once()

    @patch("awslabs.aws_sra_mcp_server.aws_documentation._execute_recommendation_request")
    async def test_get_recommendations_exception(self, mock_execute, mock_context):
        """Test recommendations with exception."""
        mock_execute.side_effect = Exception("API Error")

        results = await get_recommendations(mock_context, "https://example.com/test")
        assert results == []
        assert len(mock_context.errors) == 1
        assert "Error getting recommendations" in mock_context.errors[0]


@pytest.mark.asyncio
class TestGetMultipleRecommendations:
    """Test get_multiple_recommendations function."""

    @patch("awslabs.aws_sra_mcp_server.aws_documentation._execute_recommendation_request")
    async def test_get_multiple_recommendations_success(self, mock_execute, mock_context):
        """Test successful multiple recommendations retrieval."""
        mock_execute.return_value = {
            "highlyRated": {
                "items": [
                    {
                        "url": "https://example.com/rec1",
                        "assetTitle": "Rec Title 1",
                        "abstract": "Rec abstract 1",
                    }
                ]
            }
        }

        urls = ["https://example.com/test1", "https://example.com/test2"]
        results = await get_multiple_recommendations(mock_context, urls)
        
        assert len(results) == 2
        assert "https://example.com/test1" in results
        assert "https://example.com/test2" in results
        assert len(results["https://example.com/test1"]) == 1
        assert mock_execute.call_count == 2

    @patch("awslabs.aws_sra_mcp_server.aws_documentation._execute_recommendation_request")
    async def test_get_multiple_recommendations_exception(self, mock_execute, mock_context):
        """Test multiple recommendations with exception."""
        mock_execute.side_effect = Exception("API Error")

        urls = ["https://example.com/test1", "https://example.com/test2"]
        results = await get_multiple_recommendations(mock_context, urls)
        
        assert len(results) == 2
        assert results["https://example.com/test1"] == []
        assert results["https://example.com/test2"] == []
        assert len(mock_context.errors) == 1
        assert "Error getting multiple recommendations" in mock_context.errors[0]

    @patch("awslabs.aws_sra_mcp_server.aws_documentation._execute_recommendation_request")
    async def test_get_multiple_recommendations_batching(self, mock_execute, mock_context):
        """Test multiple recommendations with batching."""
        mock_execute.return_value = {"highlyRated": {"items": []}}

        # Create more URLs than MAX_CONCURRENT_REQUESTS to test batching
        urls = [f"https://example.com/test{i}" for i in range(15)]
        
        with patch("awslabs.aws_sra_mcp_server.aws_documentation.MAX_CONCURRENT_REQUESTS", 5):
            results = await get_multiple_recommendations(mock_context, urls)
        
        assert len(results) == 15
        assert mock_execute.call_count == 15