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

"""Data-plane tools: invoke agents and manage sessions."""

import asyncio
from .error_handler import handle_runtime_error
from .models import ErrorResponse, InvokeRuntimeResponse, StopSessionResponse
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Callable, Optional, Union


def _read_response_body(resp: dict) -> str:
    """Read the response body from an invoke_agent_runtime response.

    Handles three boto3 response shapes:
    - StreamingBody (has .read())
    - EventStream (yields dicts with 'chunk'/'bytes' keys)
    - Iterable of bytes or strings

    All decoding uses errors='replace' to handle non-UTF8 content
    safely instead of crashing.
    """
    if 'response' not in resp:
        return ''

    body = resp['response']

    # StreamingBody — single .read()
    if hasattr(body, 'read'):
        return body.read().decode('utf-8', errors='replace')

    # Iterable (EventStream or list of chunks)
    if hasattr(body, '__iter__'):
        chunks: list[str] = []
        for chunk in body:
            if isinstance(chunk, dict):
                # EventStream format: {'chunk': {'bytes': b'...'}}
                chunk_data = chunk.get('chunk', {})
                if isinstance(chunk_data, dict) and 'bytes' in chunk_data:
                    chunks.append(chunk_data['bytes'].decode('utf-8', errors='replace'))
            elif isinstance(chunk, bytes):
                chunks.append(chunk.decode('utf-8', errors='replace'))
            else:
                chunks.append(str(chunk))
        return ''.join(chunks)

    return ''


class InvocationTools:
    """Tools for invoking agents and managing runtime sessions."""

    def __init__(self, data_client_factory: Callable) -> None:
        """Initialise with a data-plane client factory.

        Args:
            data_client_factory: Callable returning a boto3 client.
        """
        self._get_client = data_client_factory

    def register(self, mcp) -> None:
        """Register invocation tools with the MCP server."""
        mcp.tool(name='invoke_agent_runtime')(self.invoke_agent_runtime)
        mcp.tool(name='stop_runtime_session')(self.stop_runtime_session)

    async def invoke_agent_runtime(
        self,
        ctx: Context,
        agent_runtime_arn: Annotated[
            str,
            Field(
                description=(
                    'ARN of the agent runtime to invoke, e.g. '
                    '"arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-agent".'
                )
            ),
        ],
        payload: Annotated[
            str,
            Field(
                description=('JSON payload to send to the agent, e.g. \'{"prompt": "Hello"}\'.')
            ),
        ],
        runtime_session_id: Annotated[
            Optional[str],
            Field(
                description=(
                    'Session ID (33-256 chars). Reuse the same ID '
                    'for multi-turn conversations. Auto-generated if omitted.'
                )
            ),
        ] = None,
        qualifier: Annotated[
            str,
            Field(description='Endpoint name/qualifier. Defaults to DEFAULT.'),
        ] = 'DEFAULT',
    ) -> Union[InvokeRuntimeResponse, ErrorResponse]:
        """Invoke an agent hosted in AgentCore Runtime.

        Sends a request to the agent and returns the response. Each
        invocation uses or creates a microVM session identified by
        runtime_session_id.

        **BILLABLE OPERATION:** This creates or reuses a microVM
        session that incurs AWS compute charges for the duration of
        the session. Sessions auto-terminate after the configured
        idle timeout (default 15 minutes). Use stop_runtime_session
        to terminate early and save costs.
        """
        try:
            client = self._get_client()
            kwargs: dict = {
                'agentRuntimeArn': agent_runtime_arn,
                'payload': payload.encode('utf-8'),
                'qualifier': qualifier,
            }
            if runtime_session_id is not None:
                kwargs['runtimeSessionId'] = runtime_session_id

            # Run synchronous boto3 call in a thread to avoid
            # blocking the asyncio event loop.
            resp = await asyncio.to_thread(client.invoke_agent_runtime, **kwargs)

            # Read response body in a thread as well — streaming
            # reads can block for the full response duration.
            response_body = await asyncio.to_thread(_read_response_body, resp)

            content_type = resp.get('contentType', '')
            session_id = resp.get('runtimeSessionId', '')

            return InvokeRuntimeResponse(
                status='success',
                runtime_session_id=session_id,
                content_type=content_type,
                response_body=response_body,
                message='Agent invoked successfully.',
            )
        except Exception as e:
            return handle_runtime_error('InvokeAgentRuntime', e)

    async def stop_runtime_session(
        self,
        ctx: Context,
        agent_runtime_arn: Annotated[str, Field(description='ARN of the agent runtime.')],
        runtime_session_id: Annotated[
            str, Field(description='Session ID to stop (33-256 chars).')
        ],
        qualifier: Annotated[
            str, Field(description='Endpoint qualifier. Defaults to DEFAULT.')
        ] = 'DEFAULT',
    ) -> Union[StopSessionResponse, ErrorResponse]:
        """Stop a running runtime session to release its microVM.

        Use this to terminate sessions early and **save costs** instead
        of waiting for the idle timeout (default 15 minutes). This is
        the recommended cleanup action after your agent conversation
        is complete.

        This is a cost-saving operation that prevents runaway charges
        from idle sessions.
        """
        try:
            client = self._get_client()
            client.stop_runtime_session(
                agentRuntimeArn=agent_runtime_arn,
                runtimeSessionId=runtime_session_id,
                qualifier=qualifier,
            )
            return StopSessionResponse(
                status='success',
                runtime_session_id=runtime_session_id,
                message=f'Session {runtime_session_id} stop requested.',
            )
        except Exception as e:
            return handle_runtime_error('StopRuntimeSession', e)
