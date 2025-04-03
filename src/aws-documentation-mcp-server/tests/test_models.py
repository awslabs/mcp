"""Tests for data models in the AWS Documentation MCP Server."""

from awslabs.aws_documentation_mcp_server.models import (
    RecommendationResult,
    SearchResult,
)


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_search_result_creation(self):
        """Test creation of SearchResult."""
        result = SearchResult(
            rank_order=1,
            url='https://docs.aws.amazon.com/lambda/latest/dg/welcome.html',
            title='Welcome to AWS Lambda',
            context='AWS Lambda is a compute service...',
        )
        assert result.rank_order == 1
        assert result.url == 'https://docs.aws.amazon.com/lambda/latest/dg/welcome.html'
        assert result.title == 'Welcome to AWS Lambda'
        assert result.context == 'AWS Lambda is a compute service...'

    def test_search_result_without_context(self):
        """Test creation of SearchResult without context."""
        result = SearchResult(
            rank_order=1,
            url='https://docs.aws.amazon.com/lambda/latest/dg/welcome.html',
            title='Welcome to AWS Lambda',
        )
        assert result.rank_order == 1
        assert result.url == 'https://docs.aws.amazon.com/lambda/latest/dg/welcome.html'
        assert result.title == 'Welcome to AWS Lambda'
        assert result.context is None


class TestRecommendationResult:
    """Tests for RecommendationResult model."""

    def test_recommendation_result_creation(self):
        """Test creation of RecommendationResult."""
        result = RecommendationResult(
            url='https://docs.aws.amazon.com/lambda/latest/dg/welcome.html',
            title='Welcome to AWS Lambda',
            context='AWS Lambda is a compute service...',
        )
        assert result.url == 'https://docs.aws.amazon.com/lambda/latest/dg/welcome.html'
        assert result.title == 'Welcome to AWS Lambda'
        assert result.context == 'AWS Lambda is a compute service...'

    def test_recommendation_result_without_context(self):
        """Test creation of RecommendationResult without context."""
        result = RecommendationResult(
            url='https://docs.aws.amazon.com/lambda/latest/dg/welcome.html',
            title='Welcome to AWS Lambda',
        )
        assert result.url == 'https://docs.aws.amazon.com/lambda/latest/dg/welcome.html'
        assert result.title == 'Welcome to AWS Lambda'
        assert result.context is None
