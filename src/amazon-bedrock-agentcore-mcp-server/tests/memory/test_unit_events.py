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

"""Unit tests for Memory event, actor, and session tools."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory.events import (
    EventTools,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory.models import (
    DeleteEventResponse,
    ErrorResponse,
    EventResponse,
    ListActorsResponse,
    ListEventsResponse,
    ListSessionsResponse,
)
from botocore.exceptions import ClientError


class TestMemoryCreateEvent:
    """Tests for memory_create_event."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Creates event and returns event ID."""
        mock_boto3_client.create_event.return_value = {
            'event': {
                'eventId': '1#abc123',
                'memoryId': 'mem-id',
                'actorId': 'user-1',
                'sessionId': 'sess-1',
            }
        }
        tools = EventTools(client_factory)
        result = await tools.memory_create_event(
            ctx=mock_ctx,
            memory_id='mem-id',
            actor_id='user-1',
            payload=[
                {
                    'conversationalMessage': {
                        'role': 'user',
                        'content': [{'text': 'hi'}],
                    }
                }
            ],
            session_id='sess-1',
        )
        assert isinstance(result, EventResponse)
        assert result.status == 'success'
        assert '1#abc123' in result.message

    @pytest.mark.asyncio
    async def test_with_all_params(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes branch, metadata, and timestamp to API."""
        mock_boto3_client.create_event.return_value = {'event': {'eventId': '2#def456'}}
        tools = EventTools(client_factory)
        result = await tools.memory_create_event(
            ctx=mock_ctx,
            memory_id='mem-id',
            actor_id='user-1',
            payload=[],
            session_id='sess-1',
            event_timestamp=1700000000.0,
            branch={'name': 'alt', 'rootEventId': '1#abc'},
            metadata={'key': {'stringValue': 'val'}},
        )
        assert isinstance(result, EventResponse)
        kw = mock_boto3_client.create_event.call_args.kwargs
        assert kw['branch'] == {'name': 'alt', 'rootEventId': '1#abc'}
        assert kw['metadata'] == {'key': {'stringValue': 'val'}}
        assert kw['eventTimestamp'] == 1700000000.0

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.create_event.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'CreateEvent',
        )
        tools = EventTools(client_factory)
        result = await tools.memory_create_event(
            ctx=mock_ctx, memory_id='bad', actor_id='u', payload=[]
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestMemoryGetEvent:
    """Tests for memory_get_event."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns event details on success."""
        mock_boto3_client.get_event.return_value = {'event': {'eventId': '1#abc', 'actorId': 'u1'}}
        tools = EventTools(client_factory)
        result = await tools.memory_get_event(
            ctx=mock_ctx,
            memory_id='m',
            actor_id='u1',
            session_id='s1',
            event_id='1#abc',
        )
        assert isinstance(result, EventResponse)
        assert result.status == 'success'
        assert result.event['eventId'] == '1#abc'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.get_event.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'GetEvent',
        )
        tools = EventTools(client_factory)
        result = await tools.memory_get_event(
            ctx=mock_ctx,
            memory_id='m',
            actor_id='u',
            session_id='s',
            event_id='bad',
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestMemoryDeleteEvent:
    """Tests for memory_delete_event."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Deletes event and returns event ID."""
        mock_boto3_client.delete_event.return_value = {'eventId': '1#abc'}
        tools = EventTools(client_factory)
        result = await tools.memory_delete_event(
            ctx=mock_ctx,
            memory_id='m',
            actor_id='u1',
            session_id='s1',
            event_id='1#abc',
        )
        assert isinstance(result, DeleteEventResponse)
        assert result.status == 'success'
        assert result.event_id == '1#abc'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.delete_event.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'DeleteEvent',
        )
        tools = EventTools(client_factory)
        result = await tools.memory_delete_event(
            ctx=mock_ctx,
            memory_id='m',
            actor_id='u',
            session_id='s',
            event_id='bad',
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestMemoryListEvents:
    """Tests for memory_list_events."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns list of events."""
        mock_boto3_client.list_events.return_value = {
            'events': [{'eventId': '1#a'}, {'eventId': '2#b'}],
            'nextToken': None,
        }
        tools = EventTools(client_factory)
        result = await tools.memory_list_events(
            ctx=mock_ctx,
            memory_id='m',
            actor_id='u',
            session_id='s',
        )
        assert isinstance(result, ListEventsResponse)
        assert result.status == 'success'
        assert len(result.events) == 2

    @pytest.mark.asyncio
    async def test_with_filter(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes filter and pagination params to API."""
        mock_boto3_client.list_events.return_value = {'events': []}
        tools = EventTools(client_factory)
        await tools.memory_list_events(
            ctx=mock_ctx,
            memory_id='m',
            actor_id='u',
            session_id='s',
            include_payloads=True,
            max_results=5,
            next_token='tok',
            event_filter={'branch': {'name': 'main'}},
        )
        kw = mock_boto3_client.list_events.call_args.kwargs
        assert kw['includePayloads'] is True
        assert kw['maxResults'] == 5
        assert kw['nextToken'] == 'tok'
        assert kw['filter'] == {'branch': {'name': 'main'}}

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.list_events.side_effect = ClientError(
            {
                'Error': {'Code': 'ServiceException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 500},
            },
            'ListEvents',
        )
        tools = EventTools(client_factory)
        result = await tools.memory_list_events(
            ctx=mock_ctx,
            memory_id='m',
            actor_id='u',
            session_id='s',
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestMemoryListActors:
    """Tests for memory_list_actors."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns list of actor summaries."""
        mock_boto3_client.list_actors.return_value = {
            'actorSummaries': [{'actorId': 'u1'}, {'actorId': 'u2'}],
        }
        tools = EventTools(client_factory)
        result = await tools.memory_list_actors(ctx=mock_ctx, memory_id='m')
        assert isinstance(result, ListActorsResponse)
        assert result.status == 'success'
        assert len(result.actors) == 2

    @pytest.mark.asyncio
    async def test_with_pagination(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes pagination params to API."""
        mock_boto3_client.list_actors.return_value = {'actorSummaries': []}
        tools = EventTools(client_factory)
        await tools.memory_list_actors(
            ctx=mock_ctx,
            memory_id='m',
            max_results=5,
            next_token='tok',
        )
        kw = mock_boto3_client.list_actors.call_args.kwargs
        assert kw['maxResults'] == 5
        assert kw['nextToken'] == 'tok'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.list_actors.side_effect = ClientError(
            {
                'Error': {'Code': 'ServiceException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 500},
            },
            'ListActors',
        )
        tools = EventTools(client_factory)
        result = await tools.memory_list_actors(
            ctx=mock_ctx,
            memory_id='m',
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestMemoryListSessions:
    """Tests for memory_list_sessions."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns list of session summaries."""
        mock_boto3_client.list_sessions.return_value = {
            'sessionSummaries': [
                {
                    'sessionId': 's1',
                    'actorId': 'u1',
                    'createdAt': 1700000000,
                },
            ],
        }
        tools = EventTools(client_factory)
        result = await tools.memory_list_sessions(
            ctx=mock_ctx,
            memory_id='m',
            actor_id='u1',
        )
        assert isinstance(result, ListSessionsResponse)
        assert result.status == 'success'
        assert len(result.sessions) == 1

    @pytest.mark.asyncio
    async def test_with_pagination(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes pagination params to API."""
        mock_boto3_client.list_sessions.return_value = {'sessionSummaries': []}
        tools = EventTools(client_factory)
        await tools.memory_list_sessions(
            ctx=mock_ctx,
            memory_id='m',
            actor_id='u1',
            max_results=5,
            next_token='tok',
        )
        kw = mock_boto3_client.list_sessions.call_args.kwargs
        assert kw['maxResults'] == 5
        assert kw['nextToken'] == 'tok'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.list_sessions.side_effect = ClientError(
            {
                'Error': {'Code': 'ServiceException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 500},
            },
            'ListSessions',
        )
        tools = EventTools(client_factory)
        result = await tools.memory_list_sessions(
            ctx=mock_ctx,
            memory_id='m',
            actor_id='u1',
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
