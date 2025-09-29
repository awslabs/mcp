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
"""Tests for metadata handling in search results."""

import pytest
from awslabs.aws_documentation_mcp_server.server_aws import search_documentation
from unittest.mock import AsyncMock, MagicMock, patch


class MockContext:
    """Mock context for testing."""

    async def error(self, message):
        """Mock error method."""
        print(f'Error: {message}')


class TestMetadataHandling:
    """Tests for the new metadata handling logic in search results."""

    @pytest.mark.asyncio
    async def test_seo_abstract_priority(self):
        """Test that seo_abstract is used when available."""
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'queryId': 'test-query-id',
            'suggestions': [
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/test',
                        'title': 'Test Page',
                        'summary': 'Regular summary',
                        'suggestionBody': 'Suggestion body text',
                        'metadata': {
                            'seo_abstract': 'SEO optimized abstract',
                            'abstract': 'Regular abstract',
                            'summary': 'Metadata summary',
                        },
                    }
                }
            ],
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await search_documentation(ctx, search_phrase='test', limit=10)

            assert len(results) == 1
            assert results[0].context == 'SEO optimized abstract'

    @pytest.mark.asyncio
    async def test_abstract_fallback(self):
        """Test that abstract is used when seo_abstract is not available."""
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'queryId': 'test-query-id',
            'suggestions': [
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/test',
                        'title': 'Test Page',
                        'summary': 'Regular summary',
                        'suggestionBody': 'Suggestion body text',
                        'metadata': {
                            'abstract': 'Regular abstract',
                            'summary': 'Metadata summary',
                        },
                    }
                }
            ],
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await search_documentation(ctx, search_phrase='test', limit=10)

            assert len(results) == 1
            assert results[0].context == 'Regular abstract'

    @pytest.mark.asyncio
    async def test_summary_fallback(self):
        """Test that summary is used when metadata abstracts are not available."""
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'queryId': 'test-query-id',
            'suggestions': [
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/test',
                        'title': 'Test Page',
                        'summary': 'Regular summary',
                        'suggestionBody': 'Suggestion body text',
                        'metadata': {},
                    }
                }
            ],
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await search_documentation(ctx, search_phrase='test', limit=10)

            assert len(results) == 1
            assert results[0].context == 'Regular summary'

    @pytest.mark.asyncio
    async def test_suggestion_body_fallback(self):
        """Test that suggestionBody is used when no other context is available."""
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'queryId': 'test-query-id',
            'suggestions': [
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/test',
                        'title': 'Test Page',
                        'suggestionBody': 'Suggestion body text',
                        'metadata': {},
                    }
                }
            ],
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await search_documentation(ctx, search_phrase='test', limit=10)

            assert len(results) == 1
            assert results[0].context == 'Suggestion body text'

    @pytest.mark.asyncio
    async def test_no_context_available(self):
        """Test that context is None when no context fields are available."""
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'queryId': 'test-query-id',
            'suggestions': [
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/test',
                        'title': 'Test Page',
                        'metadata': {},
                    }
                }
            ],
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await search_documentation(ctx, search_phrase='test', limit=10)

            assert len(results) == 1
            assert results[0].context is None

    @pytest.mark.asyncio
    async def test_empty_metadata(self):
        """Test handling when metadata field is empty."""
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'queryId': 'test-query-id',
            'suggestions': [
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/test',
                        'title': 'Test Page',
                        'summary': 'Regular summary',
                        'metadata': {},
                    }
                }
            ],
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await search_documentation(ctx, search_phrase='test', limit=10)

            assert len(results) == 1
            assert results[0].context == 'Regular summary'

    @pytest.mark.asyncio
    async def test_mixed_metadata_availability(self):
        """Test handling multiple results with different metadata availability."""
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'queryId': 'test-query-id',
            'suggestions': [
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/test1',
                        'title': 'Test Page 1',
                        'summary': 'Regular summary 1',
                        'metadata': {'seo_abstract': 'SEO abstract 1'},
                    }
                },
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/test2',
                        'title': 'Test Page 2',
                        'summary': 'Regular summary 2',
                        'metadata': {'abstract': 'Regular abstract 2'},
                    }
                },
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/test3',
                        'title': 'Test Page 3',
                        'summary': 'Regular summary 3',
                        'metadata': {},
                    }
                },
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/test4',
                        'title': 'Test Page 4',
                        'suggestionBody': 'Suggestion body 4',
                        'metadata': {},
                    }
                },
            ],
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await search_documentation(ctx, search_phrase='test', limit=10)

            assert len(results) == 4
            assert results[0].context == 'SEO abstract 1'
            assert results[1].context == 'Regular abstract 2'
            assert results[2].context == 'Regular summary 3'
            assert results[3].context == 'Suggestion body 4'

    @pytest.mark.asyncio
    async def test_real_world_example_with_metadata(self):
        """Test with real-world example data that includes metadata."""
        ctx = MockContext()

        # Using actual structure from the provided CURL response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'queryId': 'test-query-id',
            'suggestions': [
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html',
                        'title': 'What is Amazon S3? - Amazon Simple Storage Service',
                        'suggestionBody': 'What is Amazon S3?',
                        'summary': 'Store data in the cloud and learn the core concepts of buckets and objects with the Amazon S3 web service.',
                        'metadata': {
                            'abstract': "This document introduces Amazon S3, a scalable object storage service offering various storage classes, management features, access controls, and data processing capabilities. It covers S3's core concepts, bucket types, versioning, consistency model, and integration with other AWS services.",
                            'last_updated': '2025-07-29T22:20:53.000Z',
                            'summary': "This document introduces Amazon S3, a scalable object storage service offering various storage classes, management features, access controls, and data processing capabilities. It covers S3's core concepts, bucket types, versioning, consistency model, and integration with other AWS services.",
                            'seo_abstract': 'Amazon S3 offers object storage service with scalability, availability, security, and performance. Manage storage classes, lifecycle policies, access permissions, data transformations, usage metrics, and query tabular data.',
                        },
                    }
                },
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/sdk-for-kotlin/api/latest/qbusiness/aws.sdk.kotlin.services.qbusiness.model/-document-content/-s3/index.html',
                        'title': 'S3',
                        'suggestionBody': 'funasS3OrNull():S3?',
                        'metadata': {'last_updated': '2025-08-23T15:00:48.000Z', 'summary': 'S3'},
                    }
                },
            ],
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await search_documentation(ctx, search_phrase='s3', limit=10)

            assert len(results) == 2
            # First result should use seo_abstract
            assert (
                results[0].context
                == 'Amazon S3 offers object storage service with scalability, availability, security, and performance. Manage storage classes, lifecycle policies, access permissions, data transformations, usage metrics, and query tabular data.'
            )
            # Second result should use suggestionBody since no seo_abstract or abstract in metadata
            assert results[1].context == 'funasS3OrNull():S3?'

    @pytest.mark.asyncio
    async def test_missing_metadata_field(self):
        """Test handling when metadata field is missing entirely."""
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'queryId': 'test-query-id',
            'suggestions': [
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/test',
                        'title': 'Test Page',
                        'summary': 'Regular summary',
                        # No metadata field at all
                    }
                }
            ],
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await search_documentation(ctx, search_phrase='test', limit=10)

            assert len(results) == 1
            assert results[0].context == 'Regular summary'
