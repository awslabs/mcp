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

"""Event, actor, and session tools for AgentCore Memory data plane.

Events represent interactions stored in short-term memory. Actors and
sessions organize events by user/entity and conversation.
"""

from .error_handler import handle_memory_error
from .models import (
    DeleteEventResponse,
    ErrorResponse,
    EventResponse,
    ListActorsResponse,
    ListEventsResponse,
    ListSessionsResponse,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any


class EventTools:
    """Tools for managing events, actors, and sessions in AgentCore Memory."""

    def __init__(self, client_factory):
        """Initialize with a callable that returns a boto3 data plane client."""
        self._get_client = client_factory

    def register(self, mcp):
        """Register event tools with the MCP server."""
        mcp.tool(name='memory_create_event')(self.memory_create_event)
        mcp.tool(name='memory_get_event')(self.memory_get_event)
        mcp.tool(name='memory_delete_event')(self.memory_delete_event)
        mcp.tool(name='memory_list_events')(self.memory_list_events)
        mcp.tool(name='memory_list_actors')(self.memory_list_actors)
        mcp.tool(name='memory_list_sessions')(self.memory_list_sessions)

    async def memory_create_event(
        self,
        ctx: Context,
        memory_id: Annotated[
            str,
            Field(description='Memory resource ID'),
        ],
        actor_id: Annotated[
            str,
            Field(
                description=('Actor identifier (1-255 chars). Pattern: [a-zA-Z0-9][a-zA-Z0-9-_/]*')
            ),
        ],
        payload: Annotated[
            list[dict[str, Any]],
            Field(
                description=(
                    'Content payload (0-100 items). Each item is a PayloadType '
                    'union — typically conversational messages with "role" and '
                    '"content" fields.'
                )
            ),
        ],
        session_id: Annotated[
            str | None,
            Field(
                description=(
                    'Session identifier (1-100 chars). Groups events into '
                    'conversations. Pattern: [a-zA-Z0-9][a-zA-Z0-9-_]*'
                )
            ),
        ] = None,
        event_timestamp: Annotated[
            float | None,
            Field(description='Event timestamp (epoch seconds). Defaults to now.'),
        ] = None,
        branch: Annotated[
            dict[str, str] | None,
            Field(
                description=(
                    'Branch info for threading. Object with "name" and optional "rootEventId".'
                )
            ),
        ] = None,
        metadata: Annotated[
            dict[str, Any] | None,
            Field(description='Key-value metadata (0-15 entries, keys 1-128 chars)'),
        ] = None,
    ) -> EventResponse | ErrorResponse:
        """Create an event in an AgentCore Memory resource (short-term memory).

        COST WARNING: Creating events triggers background long-term memory
        extraction if strategies are configured. This consumes compute
        resources and incurs AWS charges.

        Events represent interactions (messages, tool calls) within a session.
        They are immutable and timestamped.
        """
        logger.info(f'Creating event in memory {memory_id} for actor {actor_id}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                'memoryId': memory_id,
                'actorId': actor_id,
                'payload': payload,
            }
            if session_id is not None:
                kwargs['sessionId'] = session_id
            if event_timestamp is not None:
                kwargs['eventTimestamp'] = event_timestamp
            if branch is not None:
                kwargs['branch'] = branch
            if metadata is not None:
                kwargs['metadata'] = metadata

            response = client.create_event(**kwargs)
            event = response.get('event', {})

            return EventResponse(
                status='success',
                message=f'Event created. ID: {event.get("eventId", "unknown")}.',
                event=event,
            )
        except Exception as e:
            return handle_memory_error('CreateEvent', e)

    async def memory_get_event(
        self,
        ctx: Context,
        memory_id: Annotated[str, Field(description='Memory resource ID')],
        actor_id: Annotated[str, Field(description='Actor identifier')],
        session_id: Annotated[str, Field(description='Session identifier')],
        event_id: Annotated[
            str,
            Field(description='Event identifier. Pattern: [0-9]+#[a-fA-F0-9]+'),
        ],
    ) -> EventResponse | ErrorResponse:
        """Get a specific event from an AgentCore Memory resource.

        Retrieves full event details including payload and metadata.
        This is a read-only operation with no cost implications.
        """
        logger.info(f'Getting event {event_id} from memory {memory_id}')

        try:
            client = self._get_client()
            response = client.get_event(
                memoryId=memory_id,
                actorId=actor_id,
                sessionId=session_id,
                eventId=event_id,
            )
            event = response.get('event', {})

            return EventResponse(
                status='success',
                message=f'Event {event_id} retrieved.',
                event=event,
            )
        except Exception as e:
            return handle_memory_error('GetEvent', e)

    async def memory_delete_event(
        self,
        ctx: Context,
        memory_id: Annotated[str, Field(description='Memory resource ID')],
        actor_id: Annotated[str, Field(description='Actor identifier')],
        session_id: Annotated[str, Field(description='Session identifier')],
        event_id: Annotated[
            str,
            Field(description='Event identifier to delete'),
        ],
    ) -> DeleteEventResponse | ErrorResponse:
        """Permanently delete an event from an AgentCore Memory resource.

        WARNING: This permanently removes the event. This action cannot
        be undone. Already-extracted long-term memory records are not
        affected.
        """
        logger.info(f'Deleting event {event_id} from memory {memory_id}')

        try:
            client = self._get_client()
            response = client.delete_event(
                memoryId=memory_id,
                actorId=actor_id,
                sessionId=session_id,
                eventId=event_id,
            )

            return DeleteEventResponse(
                status='success',
                message=f'Event {event_id} deleted.',
                event_id=response.get('eventId', event_id),
            )
        except Exception as e:
            return handle_memory_error('DeleteEvent', e)

    async def memory_list_events(
        self,
        ctx: Context,
        memory_id: Annotated[str, Field(description='Memory resource ID')],
        actor_id: Annotated[str, Field(description='Actor identifier')],
        session_id: Annotated[str, Field(description='Session identifier')],
        include_payloads: Annotated[
            bool | None,
            Field(description='Whether to include event payloads'),
        ] = None,
        max_results: Annotated[
            int | None,
            Field(description='Max results per page (1-100, default 20)'),
        ] = None,
        next_token: Annotated[
            str | None,
            Field(description='Pagination token'),
        ] = None,
        event_filter: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Filter criteria. Object with optional "branch" '
                    '(name, includeParentBranches) and "eventMetadata" '
                    '(list of filter expressions).'
                )
            ),
        ] = None,
    ) -> ListEventsResponse | ErrorResponse:
        """List events in an AgentCore Memory resource.

        Lists events for a specific actor and session with optional
        filtering by branch or metadata. This is a read-only operation.
        """
        logger.info(
            f'Listing events in memory {memory_id} for actor {actor_id}, session {session_id}'
        )

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                'memoryId': memory_id,
                'actorId': actor_id,
                'sessionId': session_id,
            }
            if include_payloads is not None:
                kwargs['includePayloads'] = include_payloads
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token is not None:
                kwargs['nextToken'] = next_token
            if event_filter is not None:
                kwargs['filter'] = event_filter

            response = client.list_events(**kwargs)
            events = response.get('events', [])

            return ListEventsResponse(
                status='success',
                message=f'Found {len(events)} event(s).',
                events=events,
                next_token=response.get('nextToken'),
            )
        except Exception as e:
            return handle_memory_error('ListEvents', e)

    async def memory_list_actors(
        self,
        ctx: Context,
        memory_id: Annotated[str, Field(description='Memory resource ID')],
        max_results: Annotated[
            int | None,
            Field(description='Max results per page (1-100, default 20)'),
        ] = None,
        next_token: Annotated[
            str | None,
            Field(description='Pagination token'),
        ] = None,
    ) -> ListActorsResponse | ErrorResponse:
        """List all actors in an AgentCore Memory resource.

        Returns actor summaries (actor IDs) for the memory. This is
        a read-only operation with no cost implications.
        """
        logger.info(f'Listing actors in memory {memory_id}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {'memoryId': memory_id}
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token is not None:
                kwargs['nextToken'] = next_token

            response = client.list_actors(**kwargs)
            actors = response.get('actorSummaries', [])

            return ListActorsResponse(
                status='success',
                message=f'Found {len(actors)} actor(s).',
                actors=actors,
                next_token=response.get('nextToken'),
            )
        except Exception as e:
            return handle_memory_error('ListActors', e)

    async def memory_list_sessions(
        self,
        ctx: Context,
        memory_id: Annotated[str, Field(description='Memory resource ID')],
        actor_id: Annotated[str, Field(description='Actor identifier')],
        max_results: Annotated[
            int | None,
            Field(description='Max results per page (1-100, default 20)'),
        ] = None,
        next_token: Annotated[
            str | None,
            Field(description='Pagination token'),
        ] = None,
    ) -> ListSessionsResponse | ErrorResponse:
        """List sessions for an actor in an AgentCore Memory resource.

        Returns session summaries with session IDs, actor IDs, and
        creation timestamps. This is a read-only operation.
        """
        logger.info(f'Listing sessions in memory {memory_id} for actor {actor_id}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                'memoryId': memory_id,
                'actorId': actor_id,
            }
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token is not None:
                kwargs['nextToken'] = next_token

            response = client.list_sessions(**kwargs)
            sessions = response.get('sessionSummaries', [])

            return ListSessionsResponse(
                status='success',
                message=f'Found {len(sessions)} session(s).',
                sessions=sessions,
                next_token=response.get('nextToken'),
            )
        except Exception as e:
            return handle_memory_error('ListSessions', e)
