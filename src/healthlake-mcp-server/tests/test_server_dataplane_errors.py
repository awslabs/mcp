# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Tests for data-plane HTTP error mapping in the MCP server.

Regression tests for the bug where FHIR REST (httpx) errors were caught
by the generic ``except Exception`` branch and surfaced as
``server_error: Internal server error``, losing actionable information
such as 404 Not Found and 400 Bad Request with an OperationOutcome body.
"""

import httpx
from awslabs.healthlake_mcp_server.server import create_healthlake_server
from mcp.types import (
    CallToolRequest,
    CallToolRequestParams,
    CallToolResult,
    TextContent,
)
from typing import cast
from unittest.mock import AsyncMock, Mock, patch


def _make_http_status_error(status_code: int, body=None) -> httpx.HTTPStatusError:
    """Build an httpx.HTTPStatusError with a mocked response."""
    response = Mock(spec=httpx.Response)
    response.status_code = status_code
    if body is None:
        response.json.side_effect = ValueError('no json body')
    else:
        response.json.return_value = body
    request = Mock(spec=httpx.Request)
    return httpx.HTTPStatusError(f'HTTP {status_code}', request=request, response=response)


class TestDataPlaneHTTPErrorMapping:
    """Exercise the server-level mapping of httpx.HTTPStatusError."""

    async def test_read_resource_404_maps_to_not_found(self):
        """A 404 from the FHIR REST API must map to ``not_found``."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.read_resource.side_effect = _make_http_status_error(404)
            mock_client_class.return_value = mock_client

            server = create_healthlake_server()
            call_tool_handler = server.request_handlers[CallToolRequest]

            request = CallToolRequest(
                method='tools/call',
                params=CallToolRequestParams(
                    name='read_fhir_resource',
                    arguments={
                        'datastore_id': 'a' * 32,
                        'resource_type': 'Patient',
                        'resource_id': 'does-not-exist',
                    },
                ),
            )

            response = await call_tool_handler(request)
            result = cast(CallToolResult, response.root)
            text = cast(TextContent, result.content[0]).text

            assert '"type": "not_found"' in text
            assert '"Internal server error"' not in text

    async def test_patient_everything_404_maps_to_not_found(self):
        """A 404 on $patient-everything must map to ``not_found``."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.patient_everything.side_effect = _make_http_status_error(404)
            mock_client_class.return_value = mock_client

            server = create_healthlake_server()
            call_tool_handler = server.request_handlers[CallToolRequest]

            request = CallToolRequest(
                method='tools/call',
                params=CallToolRequestParams(
                    name='patient_everything',
                    arguments={
                        'datastore_id': 'a' * 32,
                        'patient_id': 'does-not-exist',
                    },
                ),
            )

            response = await call_tool_handler(request)
            result = cast(CallToolResult, response.root)
            text = cast(TextContent, result.content[0]).text

            assert '"type": "not_found"' in text

    async def test_search_400_with_operation_outcome_surfaces_diagnostics(self):
        """A 400 from search surfaces the OperationOutcome diagnostics.

        When HealthLake returns a FHIR ``OperationOutcome`` body on 400,
        the mapper pulls out ``issue[0].diagnostics`` so the
        ``validation_error`` message is actionable.
        """
        body = {
            'resourceType': 'OperationOutcome',
            'issue': [
                {
                    'severity': 'error',
                    'code': 'invalid',
                    'diagnostics': 'Unknown resource type NotReal',
                }
            ],
        }
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.search_resources.side_effect = _make_http_status_error(400, body=body)
            mock_client_class.return_value = mock_client

            server = create_healthlake_server()
            call_tool_handler = server.request_handlers[CallToolRequest]

            request = CallToolRequest(
                method='tools/call',
                params=CallToolRequestParams(
                    name='search_fhir_resources',
                    arguments={
                        'datastore_id': 'a' * 32,
                        'resource_type': 'Patient',
                    },
                ),
            )

            response = await call_tool_handler(request)
            result = cast(CallToolResult, response.root)
            text = cast(TextContent, result.content[0]).text

            assert '"type": "validation_error"' in text
            assert 'Unknown resource type NotReal' in text

    async def test_400_without_operation_outcome_uses_generic_message(self):
        """Non-JSON 400 bodies still map to ``validation_error``.

        The generic message is used when the body isn't a parseable
        OperationOutcome, rather than falling through to ``server_error``.
        """
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.search_resources.side_effect = _make_http_status_error(400, body=None)
            mock_client_class.return_value = mock_client

            server = create_healthlake_server()
            call_tool_handler = server.request_handlers[CallToolRequest]

            request = CallToolRequest(
                method='tools/call',
                params=CallToolRequestParams(
                    name='search_fhir_resources',
                    arguments={
                        'datastore_id': 'a' * 32,
                        'resource_type': 'Patient',
                    },
                ),
            )

            response = await call_tool_handler(request)
            result = cast(CallToolResult, response.root)
            text = cast(TextContent, result.content[0]).text

            assert '"type": "validation_error"' in text
            assert 'Invalid FHIR request' in text

    async def test_403_maps_to_auth_error(self):
        """Data-plane 401/403 must map to ``auth_error``."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.read_resource.side_effect = _make_http_status_error(403)
            mock_client_class.return_value = mock_client

            server = create_healthlake_server()
            call_tool_handler = server.request_handlers[CallToolRequest]

            request = CallToolRequest(
                method='tools/call',
                params=CallToolRequestParams(
                    name='read_fhir_resource',
                    arguments={
                        'datastore_id': 'a' * 32,
                        'resource_type': 'Patient',
                        'resource_id': 'any-id',
                    },
                ),
            )

            response = await call_tool_handler(request)
            result = cast(CallToolResult, response.root)
            text = cast(TextContent, result.content[0]).text

            assert '"type": "auth_error"' in text

    async def test_500_maps_to_service_error(self):
        """Unhandled 5xx from HealthLake map to ``service_error``.

        The mapped error carries the HTTP status for visibility, rather
        than falling through to the generic ``server_error`` /
        ``Internal server error`` path.
        """
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.read_resource.side_effect = _make_http_status_error(500)
            mock_client_class.return_value = mock_client

            server = create_healthlake_server()
            call_tool_handler = server.request_handlers[CallToolRequest]

            request = CallToolRequest(
                method='tools/call',
                params=CallToolRequestParams(
                    name='read_fhir_resource',
                    arguments={
                        'datastore_id': 'a' * 32,
                        'resource_type': 'Patient',
                        'resource_id': 'any-id',
                    },
                ),
            )

            response = await call_tool_handler(request)
            result = cast(CallToolResult, response.root)
            text = cast(TextContent, result.content[0]).text

            assert '"type": "service_error"' in text
            assert 'HTTP 500' in text
