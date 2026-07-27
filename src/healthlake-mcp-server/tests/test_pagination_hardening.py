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

"""Regression tests for pagination and FHIR resource-path hardening.

Covers the input-validation and host-scope properties introduced in 0.0.12:
  * Opaque pagination tokens.
  * Strict ``validate_pagination_token`` format.
  * Tightened ``validate_datastore_id`` (alphanumeric only).
  * ``AWSAuth`` refuses to sign requests to unexpected hosts.
  * ``search_resources`` / ``patient_everything`` perform no network I/O on
    an invalid ``next_token``.
  * FHIR ``resource_type`` / ``resource_id`` regex validators.
  * The MCP server maps ``ValueError`` to ``type: "validation_error"``.
"""

import httpx
import json
import pytest
from awslabs.healthlake_mcp_server.fhir_operations import (
    AWSAuth,
    HealthLakeClient,
    _decode_pagination_token,
    validate_datastore_id,
    validate_fhir_resource_id,
    validate_fhir_resource_type,
    validate_pagination_token,
)
from awslabs.healthlake_mcp_server.server import create_healthlake_server
from botocore.credentials import Credentials
from unittest.mock import patch


VALID_DATASTORE_ID = 'zz0123456789abcdef0123456789zzzz'  # 32 chars, alphanumeric
REGION = 'us-east-1'


# ---------------------------------------------------------------------------
# validate_pagination_token
# ---------------------------------------------------------------------------


class TestValidatePaginationToken:
    """Opaque pagination token format validation."""

    def test_accepts_typical_healthlake_page_value(self):
        """Security regression test."""
        # Base64-url-ish content that HealthLake page cursors use in practice.
        token = 'eyJhbGciOiJIUzI1NiJ9.ABCDEF_ghijkl-0123.456=='
        assert validate_pagination_token(token) == token

    def test_accepts_short_alnum(self):
        """Security regression test."""
        assert validate_pagination_token('abc123') == 'abc123'

    @pytest.mark.parametrize(
        'bad',
        [
            '',  # empty
            ' ',  # whitespace
            '\t',
            '\n',
            'abc def',  # internal whitespace
            'abc\x00def',  # NUL
            'abc\rdef',  # CR
            'abc\ndef',  # LF
            'https://foreign.example/x',  # URL-shaped, old format rejected
            'http://foreign.example/x',
            '<script>',  # disallowed chars
            'abc;DROP',
            'abc/def',  # slash not in charset
            'abc?page=1',  # query-string chars not in charset
        ],
    )
    def test_rejects_invalid_inputs(self, bad):
        """Security regression test."""
        with pytest.raises(ValueError, match='Invalid pagination token'):
            validate_pagination_token(bad)

    @pytest.mark.parametrize('bad', [None, 123, 0, [], {}, b'bytes'])
    def test_rejects_non_string_types(self, bad):
        """Security regression test."""
        with pytest.raises(ValueError, match='Invalid pagination token'):
            validate_pagination_token(bad)

    def test_rejects_overlong(self):
        """Security regression test."""
        with pytest.raises(ValueError, match='Invalid pagination token'):
            validate_pagination_token('a' * 2049)

    def test_accepts_max_length(self):
        """Security regression test."""
        token = 'a' * 2048
        assert validate_pagination_token(token) == token

    def test_error_message_does_not_echo_token(self):
        """Security regression test."""
        # The ValueError message must not include the input value in logs
        # or MCP responses.
        marker_value = 'https://MARKER-VALUE.example/x'
        with pytest.raises(ValueError) as excinfo:
            validate_pagination_token(marker_value)
        assert 'MARKER-VALUE' not in str(excinfo.value)


# ---------------------------------------------------------------------------
# validate_datastore_id (tightened)
# ---------------------------------------------------------------------------


class TestValidateDatastoreIdTightened:
    """Tightened datastore id validator: 32 chars AND alphanumeric."""

    def test_accepts_alnum_32(self):
        """Security regression test."""
        assert validate_datastore_id(VALID_DATASTORE_ID) == VALID_DATASTORE_ID

    @pytest.mark.parametrize(
        'bad',
        [
            '',
            'short',
            'a' * 31,
            'a' * 33,
            'a' * 32 + ' ',  # trailing space
            '-' * 32,  # dashes
            '../' + 'a' * 29,  # leading dots not alnum
            'abc/' + 'a' * 28,  # slash
            'abc.' + 'a' * 28,  # dot
            'abc@' + 'a' * 28,  # at
            'abc ' + 'a' * 28,  # space
        ],
    )
    def test_rejects_non_alnum_or_wrong_length(self, bad):
        """Security regression test."""
        with pytest.raises(ValueError, match='32 alphanumeric characters'):
            validate_datastore_id(bad)


# ---------------------------------------------------------------------------
# FHIR resource_type / resource_id regex
# ---------------------------------------------------------------------------


class TestFhirResourceRegex:
    """FHIR R4 resource type and id formats."""

    @pytest.mark.parametrize('good', ['Patient', 'Observation', 'Condition', 'X', 'ABC123'])
    def test_accepts_valid_types(self, good):
        """Security regression test."""
        assert validate_fhir_resource_type(good) == good

    @pytest.mark.parametrize(
        'bad',
        [
            '',
            'patient',  # must start uppercase
            '1Patient',  # must start with letter
            'Patient/123',  # slash
            '../Patient',  # leading dots not alnum
            'https://foreign.example',
            'A' * 65,
            None,
            123,
        ],
    )
    def test_rejects_invalid_types(self, bad):
        """Security regression test."""
        with pytest.raises(ValueError, match='Invalid FHIR resource type'):
            validate_fhir_resource_type(bad)

    @pytest.mark.parametrize('good', ['abc-123', 'Patient.1', '1', 'A1B2.C3-D4', 'a' * 64])
    def test_accepts_valid_ids(self, good):
        """Security regression test."""
        assert validate_fhir_resource_id(good) == good

    @pytest.mark.parametrize(
        'bad',
        [
            '',
            'a' * 65,
            'abc/def',
            '../abc',
            'abc def',
            'abc#frag',
            'abc?x=1',
            None,
            123,
        ],
    )
    def test_rejects_invalid_ids(self, bad):
        """Security regression test."""
        with pytest.raises(ValueError, match='Invalid FHIR resource id'):
            validate_fhir_resource_id(bad)


# ---------------------------------------------------------------------------
# Bundle processing: opaque token extraction
# ---------------------------------------------------------------------------


class TestBundleOpaqueTokenExtraction:
    """``_process_bundle`` returns an opaque token packing both page and count."""

    def _client(self):
        return HealthLakeClient.__new__(HealthLakeClient)

    def test_extracts_page_and_count_into_opaque_token(self):
        """Security regression test.

        The emitted ``next_token`` is opaque (never a URL) and round-trips
        through ``_decode_pagination_token`` to the original ``page`` value
        paired with the ``_count`` HealthLake had in effect when emitting
        the cursor. Capturing ``_count`` is what fixes Bug #3: the
        follow-up call must use the server's ``_count``, not whatever the
        caller happens to supply.
        """
        bundle = {
            'resourceType': 'Bundle',
            'link': [
                {
                    'relation': 'next',
                    'url': (
                        'https://healthlake.us-east-1.amazonaws.com/datastore/'
                        'abc/r4/Patient?_count=5&page=OPAQUE123'
                    ),
                }
            ],
            'entry': [],
        }
        result = self._client()._process_bundle(bundle)
        token = result['pagination']['next_token']
        assert result['pagination']['has_next'] is True
        # Still passes the caller-facing validator.
        assert validate_pagination_token(token) == token
        # Not a URL, not the bare page value — opaque.
        assert token != 'OPAQUE123'
        assert '://' not in token
        # Round-trips to the captured ``page`` + ``_count`` pair.
        assert _decode_pagination_token(token) == {'page': 'OPAQUE123', 'count': 5}

    def test_returns_none_when_no_next_link(self):
        """Security regression test."""
        bundle = {'resourceType': 'Bundle', 'link': [], 'entry': []}
        result = self._client()._process_bundle(bundle)
        assert result['pagination']['next_token'] is None
        assert result['pagination']['has_next'] is False

    def test_returns_none_when_next_link_has_no_page(self):
        """Security regression test."""
        bundle = {
            'resourceType': 'Bundle',
            'link': [{'relation': 'next', 'url': 'https://foreign.example/x'}],
            'entry': [],
        }
        result = self._client()._process_bundle(bundle)
        assert result['pagination']['next_token'] is None

    def test_rejects_malformed_page_value_from_healthlake(self):
        """Security regression test."""
        # Even if HealthLake somehow emits a value that would fail our own
        # validator, we must not pass it through.
        bundle = {
            'resourceType': 'Bundle',
            'link': [
                {'relation': 'next', 'url': 'https://x/y?page=has space'},
            ],
            'entry': [],
        }
        result = self._client()._process_bundle(bundle)
        assert result['pagination']['next_token'] is None

    def test_defaults_count_when_next_link_omits_it(self):
        """Security regression test.

        If HealthLake's ``next`` link somehow lacks ``_count``, we fall
        back to ``MAX_SEARCH_COUNT`` rather than fail extraction — the
        page cursor is still usable with the default count.
        """
        bundle = {
            'resourceType': 'Bundle',
            'link': [
                {'relation': 'next', 'url': 'https://x/y?page=OPAQUE123'},
            ],
            'entry': [],
        }
        result = self._client()._process_bundle(bundle)
        token = result['pagination']['next_token']
        assert token is not None
        decoded = _decode_pagination_token(token)
        assert decoded == {'page': 'OPAQUE123', 'count': 100}

    def test_clamps_out_of_range_count_from_next_link(self):
        """Security regression test.

        If HealthLake's ``next`` link emits a ``_count`` outside the
        documented 1–100 range (or a non-integer), fall back to the
        default rather than cache a value the client validator would
        later reject.
        """
        for bad_count in ('0', '101', '-5', 'abc', '1.5'):
            bundle = {
                'resourceType': 'Bundle',
                'link': [
                    {
                        'relation': 'next',
                        'url': f'https://x/y?_count={bad_count}&page=OPAQUE123',
                    },
                ],
                'entry': [],
            }
            result = self._client()._process_bundle(bundle)
            token = result['pagination']['next_token']
            assert token is not None, f'token unexpectedly None for _count={bad_count!r}'
            decoded = _decode_pagination_token(token)
            assert decoded == {'page': 'OPAQUE123', 'count': 100}, (
                f'expected fallback count for _count={bad_count!r}, got {decoded!r}'
            )

    def test_bundle_with_includes_also_emits_opaque(self):
        """Security regression test."""
        bundle = {
            'resourceType': 'Bundle',
            'link': [
                {
                    'relation': 'next',
                    'url': (
                        'https://healthlake.us-east-1.amazonaws.com/datastore/'
                        'abc/r4/Patient?_count=50&page=TOK-XYZ'
                    ),
                }
            ],
            'entry': [{'search': {'mode': 'match'}, 'resource': {'resourceType': 'Patient'}}],
        }
        result = self._client()._process_bundle_with_includes(bundle)
        token = result['pagination']['next_token']
        assert result['pagination']['has_next'] is True
        assert token is not None
        # Still opaque; decodes to the expected page/count pair.
        assert _decode_pagination_token(token) == {'page': 'TOK-XYZ', 'count': 50}


# ---------------------------------------------------------------------------
# Server-side URL reconstruction
# ---------------------------------------------------------------------------


class TestServerSideUrlReconstruction:
    """Paginated URLs are built from trusted components, not caller input."""

    def _client(self):
        c = HealthLakeClient.__new__(HealthLakeClient)
        c.region = REGION
        return c

    def test_search_pagination_url_is_trusted(self):
        """Security regression test."""
        url = self._client()._build_pagination_url(
            datastore_id=VALID_DATASTORE_ID,
            resource_type='Patient',
            count=100,
            next_token='OPAQUE123',
        )
        expected = (
            f'https://healthlake.{REGION}.amazonaws.com/datastore/'
            f'{VALID_DATASTORE_ID}/r4/Patient?_count=100&page=OPAQUE123'
        )
        assert url == expected

    def test_everything_pagination_url_is_trusted(self):
        """Security regression test."""
        url = self._client()._build_patient_everything_pagination_url(
            datastore_id=VALID_DATASTORE_ID,
            patient_id='pat-1',
            count=50,
            next_token='OPAQUE456',
        )
        expected = (
            f'https://healthlake.{REGION}.amazonaws.com/datastore/'
            f'{VALID_DATASTORE_ID}/r4/Patient/pat-1/$everything?_count=50&page=OPAQUE456'
        )
        assert url == expected

    def test_pagination_url_percent_encodes_token(self):
        """Security regression test."""
        # Even though validate_pagination_token restricts the charset, the
        # URL builder must still percent-encode defensively (safe='').
        url = self._client()._build_pagination_url(
            datastore_id=VALID_DATASTORE_ID,
            resource_type='Patient',
            count=100,
            next_token='a+b=c',
        )
        # '+' and '=' both quoted with safe=''
        assert 'page=a%2Bb%3Dc' in url


# ---------------------------------------------------------------------------
# AWSAuth host scope (defense in depth)
# ---------------------------------------------------------------------------


def _make_request(url: str, method: str = 'GET') -> httpx.Request:
    """Build a real httpx.Request for AWSAuth.auth_flow."""
    return httpx.Request(method, url)


class TestAwsAuthHostScope:
    """AWSAuth refuses to sign requests for unexpected hosts."""

    @pytest.fixture
    def creds(self):
        """Real botocore Credentials (SigV4Auth introspects the object)."""
        return Credentials(
            access_key='AKIATEST',
            secret_key='secretkey',  # pragma: allowlist secret
            token=None,
        )

    def test_signs_when_host_matches(self, creds):
        """Security regression test."""
        auth = AWSAuth(
            credentials=creds,
            region=REGION,
            expected_host=f'healthlake.{REGION}.amazonaws.com',
        )
        req = _make_request(f'https://healthlake.{REGION}.amazonaws.com/datastore/x/r4/')
        gen = auth.auth_flow(req)
        next(gen)  # should not raise
        assert 'Authorization' in req.headers
        assert req.headers['Authorization'].startswith('AWS4-HMAC-SHA256 Credential=AKIATEST/')

    def test_refuses_foreign_host(self, creds):
        """Security regression test."""
        auth = AWSAuth(
            credentials=creds,
            region=REGION,
            expected_host=f'healthlake.{REGION}.amazonaws.com',
        )
        req = _make_request('http://foreign.example/x')
        with pytest.raises(ValueError, match='Refusing to sign request'):
            next(auth.auth_flow(req))
        # No Authorization header written.
        assert 'Authorization' not in req.headers

    def test_refuses_wrong_region_host(self, creds):
        """Security regression test."""
        auth = AWSAuth(
            credentials=creds,
            region=REGION,
            expected_host=f'healthlake.{REGION}.amazonaws.com',
        )
        req = _make_request('https://healthlake.us-west-2.amazonaws.com/x')
        with pytest.raises(ValueError, match='Refusing to sign request'):
            next(auth.auth_flow(req))

    def test_refuses_mismatched_subdomain(self, creds):
        """Security regression test."""
        auth = AWSAuth(
            credentials=creds,
            region=REGION,
            expected_host=f'healthlake.{REGION}.amazonaws.com',
        )
        req = _make_request(f'https://healthlake.{REGION}.amazonaws.com.foreign.example/x')
        with pytest.raises(ValueError, match='Refusing to sign request'):
            next(auth.auth_flow(req))

    def test_match_is_case_insensitive(self, creds):
        """Security regression test."""
        auth = AWSAuth(
            credentials=creds,
            region=REGION,
            expected_host=f'HEALTHLAKE.{REGION}.AMAZONAWS.COM',
        )
        req = _make_request(f'https://healthlake.{REGION}.amazonaws.com/datastore/x/r4/')
        next(auth.auth_flow(req))  # must not raise
        assert 'Authorization' in req.headers

    def test_backward_compat_when_expected_host_none(self, creds):
        """Security regression test."""
        # When expected_host is None (unchanged behaviour for non-pagination
        # callers that don't pass it), auth proceeds to sign regardless of host.
        auth = AWSAuth(credentials=creds, region=REGION, expected_host=None)
        req = _make_request('https://healthlake.us-east-1.amazonaws.com/datastore/x/r4/')
        next(auth.auth_flow(req))
        assert 'Authorization' in req.headers

    def test_error_message_does_not_echo_host(self, creds):
        """Security regression test."""
        auth = AWSAuth(
            credentials=creds,
            region=REGION,
            expected_host=f'healthlake.{REGION}.amazonaws.com',
        )
        marker_url = 'https://MARKER-VALUE.example/x'
        req = _make_request(marker_url)
        with pytest.raises(ValueError) as excinfo:
            next(auth.auth_flow(req))
        assert 'MARKER-VALUE' not in str(excinfo.value)


# ---------------------------------------------------------------------------
# No network I/O on invalid next_token (end-to-end proof)
# ---------------------------------------------------------------------------


class _AsyncClientMustNotBeConstructed:
    """Sentinel: raises AssertionError the moment httpx.AsyncClient is built."""

    def __init__(self, *a, **kw):
        raise AssertionError('httpx.AsyncClient must not be constructed')


@pytest.fixture
def client_with_region():
    """Fresh HealthLakeClient with a mocked boto3 session."""
    with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
        c = HealthLakeClient(region_name=REGION)
    return c


class TestNoNetworkIoOnInvalidInputs:
    """Invalid next_token must raise before any HTTP client is constructed."""

    @pytest.mark.asyncio
    async def test_search_rejects_url_shaped_token(self, client_with_region):
        """Security regression test."""
        with patch(
            'awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient',
            _AsyncClientMustNotBeConstructed,
        ):
            with pytest.raises(ValueError, match='Invalid pagination token'):
                await client_with_region.search_resources(
                    datastore_id=VALID_DATASTORE_ID,
                    resource_type='Patient',
                    next_token='http://foreign.example/x',
                )

    @pytest.mark.asyncio
    async def test_search_rejects_whitespace_token(self, client_with_region):
        """Security regression test."""
        with patch(
            'awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient',
            _AsyncClientMustNotBeConstructed,
        ):
            with pytest.raises(ValueError, match='Invalid pagination token'):
                await client_with_region.search_resources(
                    datastore_id=VALID_DATASTORE_ID,
                    resource_type='Patient',
                    next_token='abc def',
                )

    @pytest.mark.asyncio
    async def test_patient_everything_rejects_url_shaped_token(self, client_with_region):
        """Security regression test."""
        with patch(
            'awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient',
            _AsyncClientMustNotBeConstructed,
        ):
            with pytest.raises(ValueError, match='Invalid pagination token'):
                await client_with_region.patient_everything(
                    datastore_id=VALID_DATASTORE_ID,
                    patient_id='pat-1',
                    next_token='https://foreign.example/x',
                )

    @pytest.mark.asyncio
    async def test_search_rejects_invalid_datastore_id(self, client_with_region):
        """Security regression test."""
        with patch(
            'awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient',
            _AsyncClientMustNotBeConstructed,
        ):
            with pytest.raises(ValueError, match='32 alphanumeric characters'):
                await client_with_region.search_resources(
                    datastore_id='../abc',
                    resource_type='Patient',
                )

    @pytest.mark.asyncio
    async def test_read_resource_rejects_invalid_resource_id_chars(self, client_with_region):
        """Security regression test."""
        with patch(
            'awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient',
            _AsyncClientMustNotBeConstructed,
        ):
            with pytest.raises(ValueError, match='Invalid FHIR resource id'):
                await client_with_region.read_resource(
                    datastore_id=VALID_DATASTORE_ID,
                    resource_type='Patient',
                    resource_id='../../../abc',
                )

    @pytest.mark.asyncio
    async def test_read_resource_rejects_slash_in_resource_type(self, client_with_region):
        """Security regression test."""
        with patch(
            'awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient',
            _AsyncClientMustNotBeConstructed,
        ):
            with pytest.raises(ValueError, match='Invalid FHIR resource type'):
                await client_with_region.read_resource(
                    datastore_id=VALID_DATASTORE_ID,
                    resource_type='../abc',
                    resource_id='abc',
                )


# ---------------------------------------------------------------------------
# MCP server error mapping: ValueError -> validation_error
# ---------------------------------------------------------------------------


class TestMcpServerErrorMapping:
    """handle_call_tool maps ValueError to type=validation_error."""

    @pytest.mark.asyncio
    async def test_invalid_next_token_becomes_validation_error(self):
        """Security regression test."""
        from mcp.types import (
            CallToolRequest,
            CallToolRequestParams,
            CallToolResult,
            TextContent,
        )

        with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
            server = create_healthlake_server(read_only=False)

        # Reach into the registered tool handler.
        call_tool = server.request_handlers[CallToolRequest]

        req = CallToolRequest(
            method='tools/call',
            params=CallToolRequestParams(
                name='search_fhir_resources',
                arguments={
                    'datastore_id': VALID_DATASTORE_ID,
                    'resource_type': 'Patient',
                    'next_token': 'https://foreign.example/x',
                },
            ),
        )
        result = await call_tool(req)

        # Narrow the union return type. ``server.request_handlers`` is typed
        # as returning ``ServerResult`` whose ``.root`` is a union of every
        # MCP response type; here we know it's a CallToolResult with a
        # TextContent payload.
        assert isinstance(result.root, CallToolResult)
        first = result.root.content[0]
        assert isinstance(first, TextContent)
        payload = json.loads(first.text)
        assert payload['error'] is True
        assert payload['type'] == 'validation_error'
