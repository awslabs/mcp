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

"""Regression tests for post-0.0.12 bug fixes.

Covered:
  * Bug #3 — pagination must use the server's captured ``_count``, not the
    caller-supplied one. (Root cause of "Invalid pagination token" when an
    MCP agent didn't echo ``count`` on the follow-up call.)
  * Bug #5 — ``PermissionError`` from control-plane tools (e.g. import /
    export job) maps to ``auth_error`` at the MCP layer.
  * Bug #6 — ``start_fhir_export_job`` transforms snake_case input into
    the PascalCase shape boto3 expects.
  * HTTP 410 Gone — maps to ``not_found`` rather than a generic
    ``service_error``.
"""

import httpx
import json
import pytest
from awslabs.healthlake_mcp_server.fhir_operations import (
    HealthLakeClient,
    _decode_pagination_token,
    _encode_pagination_token,
)
from awslabs.healthlake_mcp_server.server import create_healthlake_server
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, MagicMock, patch


VALID_DATASTORE_ID = 'zz0123456789abcdef0123456789zzzz'
REGION = 'us-east-1'


# ---------------------------------------------------------------------------
# Bug #3 — Pagination round-trip uses the captured ``_count``
# ---------------------------------------------------------------------------


class TestPaginationTokenFormat:
    """v2 opaque pagination token shape and round-trip."""

    def test_encode_decode_roundtrip(self):
        """Encoding then decoding returns the same page/count pair."""
        token = _encode_pagination_token('OPAQUE123', 5)
        assert _decode_pagination_token(token) == {'page': 'OPAQUE123', 'count': 5}

    def test_encode_produces_charset_that_passes_validator(self):
        """Emitted tokens always pass ``validate_pagination_token``.

        Urlsafe-base64 uses ``[A-Za-z0-9_-]`` which is a strict subset of
        the token validator's charset; padding is stripped.
        """
        from awslabs.healthlake_mcp_server.fhir_operations import validate_pagination_token

        token = _encode_pagination_token('OPAQUE123', 42)
        assert validate_pagination_token(token) == token

    def test_decode_rejects_garbage(self):
        """Bytes that aren't v2 JSON return ``None`` — never raise."""
        assert _decode_pagination_token('') is None
        assert _decode_pagination_token('not-valid-base64!!!') is None
        # Not a dict when decoded.
        import base64

        for bad_payload in (b'"a string"', b'[1, 2, 3]', b'42'):
            token = base64.urlsafe_b64encode(bad_payload).rstrip(b'=').decode()
            assert _decode_pagination_token(token) is None

    def test_decode_rejects_wrong_version(self):
        """Tokens with a version other than 2 are not decoded."""
        import base64

        payload = json.dumps({'v': 1, 'p': 'x', 'c': 5}).encode()
        token = base64.urlsafe_b64encode(payload).rstrip(b'=').decode()
        assert _decode_pagination_token(token) is None

    def test_decode_rejects_out_of_range_count(self):
        """Decoded tokens must have a count inside the documented range."""
        import base64

        for bad_count in (0, -1, 101, 'abc', None):
            payload = json.dumps({'v': 2, 'p': 'x', 'c': bad_count}).encode()
            token = base64.urlsafe_b64encode(payload).rstrip(b'=').decode()
            assert _decode_pagination_token(token) is None

    def test_decode_rejects_page_outside_charset(self):
        """Decoded ``page`` value must still pass the conservative charset.

        Defence in depth: if a malicious or buggy emitter ever packed a
        ``page`` value with disallowed characters into an otherwise valid
        v2 envelope, decoding must reject it so it never reaches the URL
        builder.
        """
        import base64

        payload = json.dumps({'v': 2, 'p': 'has space', 'c': 10}).encode()
        token = base64.urlsafe_b64encode(payload).rstrip(b'=').decode()
        assert _decode_pagination_token(token) is None


class TestPaginationRoundTripUsesCapturedCount:
    """The follow-up call's ``_count`` comes from the token, not the caller.

    This is the fix for Bug #3: HealthLake binds its ``page`` cursor to
    the ``_count`` that was in effect when the cursor was emitted. If the
    MCP caller omits or changes ``count`` on the follow-up, a naive
    implementation would rebuild the URL with the caller's value and
    HealthLake would reject the token.
    """

    def _client(self):
        c = HealthLakeClient.__new__(HealthLakeClient)
        c.region = REGION
        return c

    def test_resolve_uses_captured_count_over_caller(self):
        """v2 token ignores the caller's ``count``."""
        token = _encode_pagination_token('OPAQUE123', 5)
        page, count = self._client()._resolve_pagination_state(
            token,
            caller_count=100,  # caller passed the schema default
        )
        assert page == 'OPAQUE123'
        assert count == 5  # captured, not caller's

    def test_resolve_falls_back_for_legacy_bare_token(self):
        """A bare (non-v2) token treats the whole string as the page value.

        This preserves compatibility with any previously emitted bare
        tokens still in flight; the caller-supplied ``count`` is used in
        that fallback path (best-effort — HealthLake may still reject).
        """
        page, count = self._client()._resolve_pagination_state(
            'LEGACY_BARE_TOKEN', caller_count=42
        )
        assert page == 'LEGACY_BARE_TOKEN'
        assert count == 42

    def test_search_pagination_url_uses_token_count_not_caller(self):
        """End-to-end URL built from a token ignores the caller's count.

        This exercises the path from ``_resolve_pagination_state`` through
        ``_build_pagination_url``: given a token that captured
        ``_count=5`` at emission, and a caller that passes ``count=100``
        on the follow-up, the reconstructed URL must use ``_count=5``.
        """
        client = self._client()
        token = _encode_pagination_token('OPAQUE123', 5)
        page, captured_count = client._resolve_pagination_state(token, caller_count=100)
        url = client._build_pagination_url(
            datastore_id=VALID_DATASTORE_ID,
            resource_type='Patient',
            count=captured_count,
            next_token=page,
        )
        assert '_count=5' in url
        assert '_count=100' not in url
        assert 'page=OPAQUE123' in url

    def test_everything_pagination_url_uses_token_count_not_caller(self):
        """Follow-up URL for ``$patient-everything`` also ignores caller count.

        Same as ``test_search_pagination_url_uses_token_count_not_caller``
        but exercised through the ``$patient-everything`` URL builder.
        """
        client = self._client()
        token = _encode_pagination_token('OPAQUE456', 25)
        page, captured_count = client._resolve_pagination_state(token, caller_count=100)
        url = client._build_patient_everything_pagination_url(
            datastore_id=VALID_DATASTORE_ID,
            patient_id='pat-1',
            count=captured_count,
            next_token=page,
        )
        assert '_count=25' in url
        assert '_count=100' not in url
        assert 'page=OPAQUE456' in url


class TestPaginationEndToEndWithMockedHttpx:
    """End-to-end: ``search_resources`` follow-up GETs the right URL.

    Covers the full path users hit: first page's ``next_token`` is decoded
    and the GET that fetches page 2 carries the captured ``_count`` even
    when the caller supplies a mismatched one.
    """

    @pytest.fixture
    def client(self):
        """Fresh HealthLakeClient with boto3 mocked out."""
        with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
            return HealthLakeClient(region_name=REGION)

    @pytest.mark.asyncio
    async def test_search_pagination_sends_captured_count(self, client):
        """Search follow-up URL carries ``_count`` from the token."""
        token = _encode_pagination_token('OPAQUE123', 5)

        # Mock the httpx response for page 2.
        page2_bundle = {
            'resourceType': 'Bundle',
            'type': 'searchset',
            'total': 0,
            'entry': [],
            'link': [],
        }
        get_mock = AsyncMock()
        get_mock.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value=page2_bundle),
            raise_for_status=MagicMock(return_value=None),
        )

        # Patch the AsyncClient's ``get`` entry point.
        class FakeAsyncClient:
            def __init__(self, *a, **kw):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            get = get_mock
            post = AsyncMock()  # must not be called

        # Also bypass AWS auth construction (needs real credentials).
        with patch.object(client, '_get_aws_auth', return_value=MagicMock()):
            with patch(
                'awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient',
                FakeAsyncClient,
            ):
                await client.search_resources(
                    datastore_id=VALID_DATASTORE_ID,
                    resource_type='Patient',
                    # Caller omits ``count`` — schema default of 100 flows
                    # through. Pre-fix, this is exactly where the bug
                    # would bite: the URL would contain _count=100 and
                    # HealthLake would reject the pagination token.
                    count=100,
                    next_token=token,
                )

        assert get_mock.await_args is not None
        called_url = get_mock.await_args.args[0]
        assert '_count=5' in called_url, f'expected captured count in URL, got {called_url!r}'
        assert '_count=100' not in called_url
        assert 'page=OPAQUE123' in called_url
        # No POST on a pagination call.
        assert FakeAsyncClient.post.await_count == 0

    @pytest.mark.asyncio
    async def test_patient_everything_pagination_sends_captured_count(self, client):
        """$patient-everything follow-up URL also uses the captured count."""
        token = _encode_pagination_token('OPAQUE456', 25)

        page2_bundle = {
            'resourceType': 'Bundle',
            'type': 'searchset',
            'total': 0,
            'entry': [],
            'link': [],
        }
        get_mock = AsyncMock()
        get_mock.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value=page2_bundle),
            raise_for_status=MagicMock(return_value=None),
        )

        class FakeAsyncClient:
            def __init__(self, *a, **kw):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            get = get_mock

        with patch.object(client, '_get_aws_auth', return_value=MagicMock()):
            with patch(
                'awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient',
                FakeAsyncClient,
            ):
                await client.patient_everything(
                    datastore_id=VALID_DATASTORE_ID,
                    patient_id='pat-1',
                    count=100,  # caller mismatched
                    next_token=token,
                )

        assert get_mock.await_args is not None
        called_url = get_mock.await_args.args[0]
        assert '_count=25' in called_url
        assert '_count=100' not in called_url
        assert 'page=OPAQUE456' in called_url


# ---------------------------------------------------------------------------
# Bug #5 — PermissionError maps to auth_error at the MCP layer
# ---------------------------------------------------------------------------


def _mcp_call_tool(server, name, arguments):
    """Invoke an MCP tool and return the decoded payload dict.

    Helper shared by several tests below. Narrows the MCP union return
    types down to the ``CallToolResult`` shape we expect.
    """
    from mcp.types import CallToolRequest, CallToolRequestParams, CallToolResult, TextContent

    call_tool = server.request_handlers[CallToolRequest]
    import asyncio

    req = CallToolRequest(
        method='tools/call',
        params=CallToolRequestParams(name=name, arguments=arguments),
    )
    result = asyncio.get_event_loop().run_until_complete(call_tool(req))
    assert isinstance(result.root, CallToolResult)
    first = result.root.content[0]
    assert isinstance(first, TextContent)
    return json.loads(first.text)


class TestMcpMapsPermissionErrorToAuthError:
    """Permission errors from job tools surface as ``auth_error``."""

    @pytest.mark.asyncio
    async def test_import_job_permission_error_maps_to_auth_error(self):
        """``PermissionError`` from a tool handler becomes ``auth_error``.

        AccessDenied from boto3 rewraps to PermissionError inside the
        import-job code path; the MCP layer must turn that into the
        ``auth_error`` type rather than a generic ``server_error``.
        """
        from mcp.types import (
            CallToolRequest,
            CallToolRequestParams,
            CallToolResult,
            TextContent,
        )

        with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
            server = create_healthlake_server(read_only=False)

        call_tool = server.request_handlers[CallToolRequest]

        # Patch the already-instantiated client's method to raise.
        # ``create_healthlake_server`` captures a fresh HealthLakeClient in
        # a closure, so we need to find and patch it. Simplest: patch the
        # class method for the duration of the call.
        async def fake_start_import_job(*a, **kw):
            raise PermissionError('Access denied: role lacks permission')

        with patch.object(HealthLakeClient, 'start_import_job', new=fake_start_import_job):
            req = CallToolRequest(
                method='tools/call',
                params=CallToolRequestParams(
                    name='start_fhir_import_job',
                    arguments={
                        'datastore_id': VALID_DATASTORE_ID,
                        'input_data_config': {'s3_uri': 's3://bucket/in'},
                        'job_output_data_config': {
                            's3_configuration': {'s3_uri': 's3://bucket/out'}
                        },
                        'data_access_role_arn': 'arn:aws:iam::123:role/r',
                    },
                ),
            )
            result = await call_tool(req)

        assert isinstance(result.root, CallToolResult)
        first = result.root.content[0]
        assert isinstance(first, TextContent)
        payload = json.loads(first.text)
        assert payload == {
            'error': True,
            'type': 'auth_error',
            'message': 'Access denied: role lacks permission',
        }


# ---------------------------------------------------------------------------
# Bug #6 — start_fhir_export_job transforms snake_case -> PascalCase
# ---------------------------------------------------------------------------


class TestExportJobConfigTransform:
    """``start_export_job`` accepts snake_case and emits PascalCase to boto3."""

    @pytest.fixture
    def client(self):
        """Client with boto3 mocked; replace the healthlake_client with a Mock."""
        with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
            c = HealthLakeClient(region_name=REGION)
        c.healthlake_client = MagicMock()
        return c

    @pytest.mark.asyncio
    async def test_minimal_snake_case_input(self, client):
        """Without KMS, snake_case s3_configuration becomes the PascalCase boto3 shape."""
        client.healthlake_client.start_fhir_export_job.return_value = {
            'JobId': 'x',
            'JobStatus': 'SUBMITTED',
        }
        result = await client.start_export_job(
            datastore_id=VALID_DATASTORE_ID,
            output_data_config={'s3_configuration': {'s3_uri': 's3://bucket/out'}},
            data_access_role_arn='arn:aws:iam::123:role/r',
        )
        assert result == {'JobId': 'x', 'JobStatus': 'SUBMITTED'}
        client.healthlake_client.start_fhir_export_job.assert_called_once_with(
            DatastoreId=VALID_DATASTORE_ID,
            OutputDataConfig={'S3Configuration': {'S3Uri': 's3://bucket/out'}},
            DataAccessRoleArn='arn:aws:iam::123:role/r',
        )

    @pytest.mark.asyncio
    async def test_kms_key_id_propagated(self, client):
        """``kms_key_id`` (snake_case) becomes ``KmsKeyId`` in the boto3 payload."""
        client.healthlake_client.start_fhir_export_job.return_value = {'JobId': 'x'}
        await client.start_export_job(
            datastore_id=VALID_DATASTORE_ID,
            output_data_config={
                's3_configuration': {
                    's3_uri': 's3://bucket/out',
                    'kms_key_id': 'arn:aws:kms:eu-west-2:123:key/abc',
                }
            },
            data_access_role_arn='arn:aws:iam::123:role/r',
            job_name='MyExport',
        )
        call_kwargs = client.healthlake_client.start_fhir_export_job.call_args.kwargs
        s3 = call_kwargs['OutputDataConfig']['S3Configuration']
        assert s3['S3Uri'] == 's3://bucket/out'
        assert s3['KmsKeyId'] == 'arn:aws:kms:eu-west-2:123:key/abc'
        assert call_kwargs['JobName'] == 'MyExport'

    @pytest.mark.asyncio
    async def test_missing_s3_uri_raises_value_error(self, client):
        """Mirrors ``start_import_job``: missing ``s3_uri`` is a client-side error."""
        with pytest.raises(ValueError, match='s3_configuration with s3_uri'):
            await client.start_export_job(
                datastore_id=VALID_DATASTORE_ID,
                output_data_config={'s3_configuration': {}},
                data_access_role_arn='arn:aws:iam::123:role/r',
            )

    @pytest.mark.asyncio
    async def test_access_denied_rewraps_to_permission_error(self, client):
        """``AccessDeniedException`` is rewrapped as ``PermissionError``.

        This is the contract that lets the MCP layer map it to
        ``auth_error`` (Bug #5 path).
        """
        error_response = {
            'Error': {'Code': 'AccessDeniedException', 'Message': 'role lacks kms:DescribeKey'}
        }
        client.healthlake_client.start_fhir_export_job.side_effect = ClientError(
            error_response, 'StartFHIRExportJob'
        )
        with pytest.raises(PermissionError, match='Access denied'):
            await client.start_export_job(
                datastore_id=VALID_DATASTORE_ID,
                output_data_config={'s3_configuration': {'s3_uri': 's3://bucket/out'}},
                data_access_role_arn='arn:aws:iam::123:role/r',
            )

    @pytest.mark.asyncio
    async def test_validation_exception_rewraps_to_value_error(self, client):
        """``ValidationException`` -> ``ValueError`` -> MCP ``validation_error``."""
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Invalid S3 URI'}}
        client.healthlake_client.start_fhir_export_job.side_effect = ClientError(
            error_response, 'StartFHIRExportJob'
        )
        with pytest.raises(ValueError, match='Invalid parameters'):
            await client.start_export_job(
                datastore_id=VALID_DATASTORE_ID,
                output_data_config={'s3_configuration': {'s3_uri': 's3://bucket/out'}},
                data_access_role_arn='arn:aws:iam::123:role/r',
            )


# ---------------------------------------------------------------------------
# HTTP 410 Gone -> not_found
# ---------------------------------------------------------------------------


class TestHttp410MapsToNotFound:
    """410 Gone from HealthLake is collapsed to ``not_found``.

    Previously 410 fell through the httpx-status mapping and surfaced as
    ``service_error "HealthLake service error (HTTP 410)"``. From a
    caller's perspective it is semantically equivalent to 404 (resource
    used to exist, doesn't now), so we report it as ``not_found``.
    """

    @pytest.mark.asyncio
    async def test_410_on_read_maps_to_not_found(self):
        """HealthLake 410 on a read surfaces as ``not_found`` at the MCP layer."""
        from mcp.types import (
            CallToolRequest,
            CallToolRequestParams,
            CallToolResult,
            TextContent,
        )

        with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
            server = create_healthlake_server(read_only=False)

        call_tool = server.request_handlers[CallToolRequest]

        # Build a synthetic 410 HTTPStatusError (requires a Response with a
        # Request attached for httpx to be happy).
        request = httpx.Request('GET', 'https://healthlake.example/datastore/x/r4/Patient/y')
        response = httpx.Response(status_code=410, content=b'', request=request)
        http_error = httpx.HTTPStatusError('Gone', request=request, response=response)

        async def fake_read_resource(*a, **kw):
            raise http_error

        with patch.object(HealthLakeClient, 'read_resource', new=fake_read_resource):
            req = CallToolRequest(
                method='tools/call',
                params=CallToolRequestParams(
                    name='read_fhir_resource',
                    arguments={
                        'datastore_id': VALID_DATASTORE_ID,
                        'resource_type': 'Patient',
                        'resource_id': 'deleted-one',
                    },
                ),
            )
            result = await call_tool(req)

        assert isinstance(result.root, CallToolResult)
        first = result.root.content[0]
        assert isinstance(first, TextContent)
        payload = json.loads(first.text)
        assert payload == {
            'error': True,
            'type': 'not_found',
            'message': 'Resource not found',
        }
