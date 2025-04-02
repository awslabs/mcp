"""Tests for data models in the AWS Documentation MCP Server."""

import pytest
from awslabs.aws_documentation_mcp_server.models import (
    ReadDocumentationParams,
)
from pydantic import ValidationError


class TestReadDocumentationParams:
    """Tests for ReadDocumentationParams model."""

    def test_valid_params(self):
        """Test validation of valid parameters."""
        params = ReadDocumentationParams(
            url='https://docs.aws.amazon.com/lambda/latest/dg/welcome.html',
            max_length=5000,
            start_index=0,
        )
        assert str(params.url) == 'https://docs.aws.amazon.com/lambda/latest/dg/welcome.html'
        assert params.max_length == 5000
        assert params.start_index == 0

    def test_invalid_url_domain(self):
        """Test validation fails for invalid URL domain."""
        with pytest.raises(ValidationError):
            ReadDocumentationParams(
                url='https://example.com/lambda/latest/dg/welcome.html',
                max_length=5000,
                start_index=0,
            )

    def test_invalid_url_extension(self):
        """Test validation fails for invalid URL extension."""
        with pytest.raises(ValidationError):
            ReadDocumentationParams(
                url='https://docs.aws.amazon.com/lambda/latest/dg/welcome',
                max_length=5000,
                start_index=0,
            )

        with pytest.raises(ValidationError):
            ReadDocumentationParams(
                url='https://docs.aws.amazon.com/lambda/latest/dg/welcome.pdf',
                max_length=5000,
                start_index=0,
            )

    def test_default_values(self):
        """Test default values are set correctly."""
        params = ReadDocumentationParams(
            url='https://docs.aws.amazon.com/lambda/latest/dg/welcome.html',
            max_length=5000,
            start_index=0,
        )
        assert params.max_length == 5000
        assert params.start_index == 0

    def test_invalid_max_length(self):
        """Test validation fails for invalid max_length."""
        with pytest.raises(ValidationError):
            ReadDocumentationParams(
                url='https://docs.aws.amazon.com/lambda/latest/dg/welcome.html',
                max_length=0,
                start_index=0,
            )

        with pytest.raises(ValidationError):
            ReadDocumentationParams(
                url='https://docs.aws.amazon.com/lambda/latest/dg/welcome.html',
                max_length=1000001,
                start_index=0,
            )

    def test_invalid_start_index(self):
        """Test validation fails for invalid start_index."""
        with pytest.raises(ValidationError):
            ReadDocumentationParams(
                url='https://docs.aws.amazon.com/lambda/latest/dg/welcome.html',
                start_index=-1,
                max_length=5000,
            )
