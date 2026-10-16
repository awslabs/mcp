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

"""Tests for the streaming client path: _invoke_stream_boto3 + call_transform_api_streaming."""
# ruff: noqa: D101, D102, D103

import pytest
from awslabs.aws_transform_mcp_server.consts import STREAMING_SERVICE, STREAMING_TARGET_BEARER
from awslabs.aws_transform_mcp_server.http_utils import HttpError
from awslabs.aws_transform_mcp_server.transform_api_client import (
    ProfileSelectionRequired,
    _invoke_stream_boto3,
    call_transform_api_streaming,
)
from botocore.exceptions import ClientError
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


_MOD = 'awslabs.aws_transform_mcp_server.transform_api_client'


# ── _invoke_stream_boto3 ────────────────────────────────────────────────


class TestInvokeStreamBoto3:
    def test_reassembles_metadata_and_payload_chunks(self):
        client = MagicMock()
        client.get_artifact.return_value = {
            'stream': [
                {'binaryMetadataEvent': {'fileName': 'f.bin', 'contentLengthBytes': 4}},
                {'binaryPayloadEvent': {'bytes': b'ab'}},
                {'binaryPayloadEvent': {'bytes': b'cd'}},
            ]
        }
        out = _invoke_stream_boto3(client, 'GetArtifact', {'artifactScope': {}})
        assert out['metadata']['fileName'] == 'f.bin'
        assert out['content'] == b'abcd'
        assert out['error'] is None
        client.get_artifact.assert_called_once_with(artifactScope={})

    def test_stream_error_event_breaks_and_is_returned(self):
        client = MagicMock()
        client.get_artifact.return_value = {
            'stream': [
                {'binaryMetadataEvent': {'fileName': 'f.bin'}},
                {
                    'streamErrorEvent': {
                        'code': 'CUSTOMER_BUCKET_ACCESS_DENIED',
                        'message': 'denied',
                    }
                },
                {'binaryPayloadEvent': {'bytes': b'unreached'}},
            ]
        }
        out = _invoke_stream_boto3(client, 'GetArtifact', {})
        assert out['error']['code'] == 'CUSTOMER_BUCKET_ACCESS_DENIED'
        assert out['content'] == b''  # broke before the trailing payload

    def test_unknown_operation_raises_valueerror(self):
        # getattr(client, 'get_artifact', None) is None -> ValueError
        client = SimpleNamespace()
        with pytest.raises(ValueError, match='Unknown operation'):
            _invoke_stream_boto3(client, 'GetArtifact', {})

    def test_client_error_maps_to_http_error(self):
        client = MagicMock()
        client.get_artifact.side_effect = ClientError(
            {'Error': {'Message': 'nope'}, 'ResponseMetadata': {'HTTPStatusCode': 403}},
            'GetArtifact',
        )
        with pytest.raises(HttpError) as ei:
            _invoke_stream_boto3(client, 'GetArtifact', {})
        assert ei.value.status_code == 403


# ── call_transform_api_streaming ────────────────────────────────────────


class TestCallTransformApiStreaming:
    async def test_sigv4_path_uses_streaming_service(self):
        with (
            patch(f'{_MOD}.config_store') as cs,
            patch(f'{_MOD}.AwsHelper') as aws,
            patch(f'{_MOD}._create_sigv4_client', return_value=MagicMock()) as mk,
            patch(
                f'{_MOD}._invoke_stream_boto3',
                return_value={'content': b'x', 'metadata': None, 'error': None},
            ) as inv,
        ):
            cs.get_config.return_value = None
            cs.is_sigv4_fes_available.return_value = True
            cs.get_sigv4_region.return_value = 'us-east-1'
            cs.derive_transform_api_endpoint.return_value = (
                'https://api.transform.us-east-1.on.aws/'
            )
            aws.resolve_region.return_value = 'us-east-1'

            out = await call_transform_api_streaming('GetArtifact', {'artifactScope': {}})

            assert out['content'] == b'x'
            assert mk.call_args.kwargs['service_name'] == STREAMING_SERVICE
            inv.assert_called_once()

    async def test_sigv4_multiple_regions_requires_profile_selection(self):
        with patch(f'{_MOD}.config_store') as cs:
            cs.get_config.return_value = None
            cs.is_sigv4_fes_available.return_value = True
            cs.get_sigv4_region.return_value = None
            cs.get_sigv4_regions.return_value = ['us-east-1', 'eu-west-2']
            with pytest.raises(ProfileSelectionRequired):
                await call_transform_api_streaming('GetArtifact', {})

    async def test_not_configured_raises(self):
        with patch(f'{_MOD}.config_store') as cs:
            cs.get_config.return_value = None
            cs.is_sigv4_fes_available.return_value = False
            with pytest.raises(RuntimeError, match='Not configured'):
                await call_transform_api_streaming('GetArtifact', {})

    async def test_cookie_path_injects_cookie_auth(self):
        cfg = MagicMock(
            auth_mode='cookie', region='us-east-1', origin='https://o', session_cookie='c=1'
        )
        with (
            patch(f'{_MOD}.config_store') as cs,
            patch(f'{_MOD}._create_unsigned_client', return_value=MagicMock()),
            patch(f'{_MOD}._inject_cookie_auth') as cook,
            patch(
                f'{_MOD}._invoke_stream_boto3',
                return_value={'content': b'', 'metadata': None, 'error': None},
            ),
        ):
            cs.get_config.return_value = cfg
            cs.derive_transform_api_endpoint.return_value = 'https://ep/'
            await call_transform_api_streaming('GetArtifact', {})
            cook.assert_called_once()

    async def test_bearer_path_refreshes_token_and_sets_streaming_target(self):
        cfg = MagicMock(auth_mode='bearer', region='us-east-1', origin=None, bearer_token='t')
        with (
            patch(f'{_MOD}.config_store') as cs,
            patch(f'{_MOD}._ensure_fresh_token', new=AsyncMock(return_value=cfg)) as fresh,
            patch(f'{_MOD}._create_unsigned_client', return_value=MagicMock()),
            patch(f'{_MOD}._inject_bearer_auth') as bearer,
            patch(
                f'{_MOD}._invoke_stream_boto3',
                return_value={'content': b'', 'metadata': None, 'error': None},
            ),
        ):
            cs.get_config.return_value = cfg
            cs.derive_transform_api_endpoint.return_value = 'https://ep/'
            await call_transform_api_streaming('GetArtifact', {})
            fresh.assert_awaited_once()
            assert bearer.call_args.kwargs['target_bearer'] == STREAMING_TARGET_BEARER

    async def test_fesrequest_body_is_serialized(self):
        from awslabs.aws_transform_mcp_server.transform_api_models import FESRequest

        req = MagicMock(spec=FESRequest)
        req.model_dump.return_value = {'artifactScope': {'x': 1}}
        cfg = MagicMock(auth_mode='cookie', region='us-east-1', origin='o', session_cookie='c')
        with (
            patch(f'{_MOD}.config_store') as cs,
            patch(f'{_MOD}._create_unsigned_client', return_value=MagicMock()),
            patch(f'{_MOD}._inject_cookie_auth'),
            patch(
                f'{_MOD}._invoke_stream_boto3',
                return_value={'content': b'', 'metadata': None, 'error': None},
            ),
        ):
            cs.get_config.return_value = cfg
            cs.derive_transform_api_endpoint.return_value = 'https://ep/'
            await call_transform_api_streaming('GetArtifact', req)
            req.model_dump.assert_called_once()
