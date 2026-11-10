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

"""Unit tests for the web_search tool."""

import boto3
import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.web_search.models import (
    ErrorResponse,
    WebSearchResponse,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.web_search.search import (
    build_filters,
    parse_timestamp,
    web_search,
)
from botocore.exceptions import ClientError
from botocore.stub import Stubber
from datetime import datetime, timedelta, timezone
from unittest.mock import patch


UTC = timezone.utc
SEARCH_MODULE = 'awslabs.amazon_bedrock_agentcore_mcp_server.tools.web_search.search'


class TestParseTimestamp:
    """Tests for parse_timestamp."""

    def test_bare_date_is_midnight_utc(self):
        """A bare date becomes midnight UTC."""
        assert parse_timestamp('2026-01-01', 'f') == datetime(2026, 1, 1, tzinfo=UTC)

    def test_z_suffix(self):
        """A trailing Z is read as UTC."""
        assert parse_timestamp('2026-01-01T10:20:30Z', 'f') == datetime(
            2026, 1, 1, 10, 20, 30, tzinfo=UTC
        )

    def test_offset_is_converted_to_utc(self):
        """An explicit offset is converted to UTC."""
        assert parse_timestamp('2026-01-01T10:00:00+02:00', 'f') == datetime(
            2026, 1, 1, 8, 0, 0, tzinfo=UTC
        )

    def test_naive_datetime_is_utc(self):
        """A date-time with no offset is read as UTC."""
        assert parse_timestamp('2026-01-01T10:00:00', 'f').tzinfo == UTC

    @pytest.mark.parametrize(
        'value',
        [
            '2026-01-01T10:00:00.5Z',
            '2026-01-01T10:00:00.123Z',
            '2026-01-01T10:00:00.123456789Z',
            '2026-01-01 10:00:00.5+00:00',
        ],
    )
    def test_fractional_seconds_are_dropped(self, value):
        """Any fraction length is accepted and removed, so botocore sends whole seconds."""
        assert parse_timestamp(value, 'f') == datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)

    def test_invalid_value_names_the_field(self):
        """An unparseable value raises ValueError naming the parameter."""
        with pytest.raises(ValueError, match='published_after'):
            parse_timestamp('last week', 'published_after')


class TestBuildFilters:
    """Tests for build_filters."""

    def test_no_filters(self):
        """No arguments produce an empty filter dict."""
        assert build_filters(None, None, None, None) == {}

    def test_empty_lists_are_ignored(self):
        """Empty domain lists are not sent."""
        assert build_filters([], [], None, None) == {}

    def test_all_filters(self):
        """Every argument maps to its API field."""
        filters = build_filters(['a.com'], ['b.com'], '2026-01-01', '2026-02-01T00:00:00Z')
        assert filters == {
            'domainFilter': {'include': ['a.com'], 'exclude': ['b.com']},
            'publishedDateFilter': {
                'publishedAfter': datetime(2026, 1, 1, tzinfo=UTC),
                'publishedBefore': datetime(2026, 2, 1, tzinfo=UTC),
            },
        }


class TestWebSearch:
    """Tests for web_search."""

    async def test_minimal_call(self, mock_ctx, mock_boto3_client):
        """A query alone sends the fixed id and default max results, and no filters."""
        mock_boto3_client.invoke_web_search.return_value = {
            'results': [{'title': 'T', 'url': 'https://x.com', 'text': 'body'}]
        }

        result = await web_search(mock_ctx, search_query='eks best practices')

        assert isinstance(result, WebSearchResponse)
        assert result.status == 'success'
        assert result.results[0].title == 'T'
        assert result.results[0].published_at is None
        mock_boto3_client.invoke_web_search.assert_called_once_with(
            webSearchId='web-search.v1', searchQuery='eks best practices', maxResults=10
        )

    async def test_filters_are_passed(self, mock_ctx, mock_boto3_client):
        """Filters are sent to the API."""
        mock_boto3_client.invoke_web_search.return_value = {'results': []}

        result = await web_search(
            mock_ctx,
            search_query='q',
            max_results=5,
            include_domains=['aws.amazon.com'],
            published_after='2026-01-01',
        )

        assert isinstance(result, WebSearchResponse)
        mock_boto3_client.invoke_web_search.assert_called_once_with(
            webSearchId='web-search.v1',
            searchQuery='q',
            maxResults=5,
            filters={
                'domainFilter': {'include': ['aws.amazon.com']},
                'publishedDateFilter': {'publishedAfter': datetime(2026, 1, 1, tzinfo=UTC)},
            },
        )

    async def test_published_at_is_iso_utc(self, mock_ctx, mock_boto3_client):
        """A publishedAt datetime is returned as an ISO 8601 UTC string."""
        published = datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone(timedelta(hours=1)))
        mock_boto3_client.invoke_web_search.return_value = {
            'results': [{'text': 'body', 'publishedAt': published}]
        }

        result = await web_search(mock_ctx, search_query='q')

        assert isinstance(result, WebSearchResponse)
        assert result.results[0].published_at == '2026-03-04T04:06:07Z'

    async def test_invalid_date_skips_the_api(self, mock_ctx, mock_boto3_client):
        """An unparseable date returns an error without calling the API."""
        result = await web_search(mock_ctx, search_query='q', published_before='soon')

        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'ValidationError'
        assert 'published_before' in result.message
        mock_boto3_client.invoke_web_search.assert_not_called()

    async def test_client_error_is_structured(self, mock_ctx, mock_boto3_client):
        """A ClientError becomes an ErrorResponse."""
        mock_boto3_client.invoke_web_search.side_effect = ClientError(
            {
                'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'},
                'ResponseMetadata': {'HTTPStatusCode': 429},
            },
            'InvokeWebSearch',
        )

        result = await web_search(mock_ctx, search_query='q')

        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'ThrottlingException'
        assert result.error_code == '429'


class TestWebSearchAgainstServiceModel:
    """Checks the request against the real botocore service model."""

    async def test_request_matches_service_model(self, mock_ctx):
        """Stubber validates the parameters against the InvokeWebSearch model."""
        client = boto3.client(
            'bedrock-agentcore',
            region_name='us-east-1',
            aws_access_key_id='testing',
            aws_secret_access_key='testing',  # pragma: allowlist secret
        )

        with (
            patch(f'{SEARCH_MODULE}.get_web_search_client', return_value=client),
            Stubber(client) as stubber,
        ):
            stubber.add_response(
                'invoke_web_search',
                {'results': [{'title': 'T', 'url': 'https://x.com', 'text': 'body'}]},
                {
                    'webSearchId': 'web-search.v1',
                    'searchQuery': 'q',
                    'maxResults': 3,
                    'filters': {
                        'domainFilter': {'include': ['aws.amazon.com'], 'exclude': ['x.com']},
                        'publishedDateFilter': {
                            'publishedAfter': datetime(2026, 1, 1, tzinfo=UTC),
                            'publishedBefore': datetime(2026, 2, 1, 12, 0, 0, tzinfo=UTC),
                        },
                    },
                },
            )
            result = await web_search(
                mock_ctx,
                search_query='q',
                max_results=3,
                include_domains=['aws.amazon.com'],
                exclude_domains=['x.com'],
                published_after='2026-01-01',
                published_before='2026-02-01T12:00:00.5Z',
            )
            stubber.assert_no_pending_responses()

        assert isinstance(result, WebSearchResponse)
        assert len(result.results) == 1
