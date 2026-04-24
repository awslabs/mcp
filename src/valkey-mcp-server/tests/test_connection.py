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

"""Unit tests for GLIDE connection module."""

import pytest
from awslabs.valkey_mcp_server.common.connection import (
    _build_config,
    close_client,
    get_client,
    reset_client,
)
from glide import GlideClientConfiguration, GlideClusterClientConfiguration
from unittest.mock import AsyncMock, MagicMock, patch


pytestmark = pytest.mark.asyncio

MODULE = 'awslabs.valkey_mcp_server.common.connection'


@pytest.fixture(autouse=True)
async def _reset():
    await reset_client()
    yield
    await reset_client()


class TestBuildConfig:
    def test_standalone_config(self):
        with patch(
            f'{MODULE}.VALKEY_CFG',
            {
                'host': 'localhost',
                'port': 6379,
                'password': '',
                'username': None,
                'ssl': False,
                'cluster_mode': False,
            },
        ):
            config = _build_config()
        assert isinstance(config, GlideClientConfiguration)

    def test_cluster_config(self):
        with patch(
            f'{MODULE}.VALKEY_CFG',
            {
                'host': 'cluster.example.com',
                'port': 6379,
                'password': '',
                'username': None,
                'ssl': False,
                'cluster_mode': True,
            },
        ):
            config = _build_config()
        assert isinstance(config, GlideClusterClientConfiguration)

    def test_credentials_password_only(self):
        with patch(
            f'{MODULE}.VALKEY_CFG',
            {
                'host': 'localhost',
                'port': 6379,
                'password': 'secret',  # pragma: allowlist secret
                'username': None,
                'ssl': False,
                'cluster_mode': False,
            },
        ):
            config = _build_config()
        assert isinstance(config, GlideClientConfiguration)

    def test_credentials_username_and_password(self):
        with patch(
            f'{MODULE}.VALKEY_CFG',
            {
                'host': 'localhost',
                'port': 6379,
                'password': 'secret',  # pragma: allowlist secret
                'username': 'admin',
                'ssl': False,
                'cluster_mode': False,
            },
        ):
            config = _build_config()
        assert isinstance(config, GlideClientConfiguration)

    def test_tls_enabled(self):
        with patch(
            f'{MODULE}.VALKEY_CFG',
            {
                'host': 'localhost',
                'port': 6379,
                'password': '',
                'username': None,
                'ssl': True,
                'cluster_mode': False,
            },
        ):
            config = _build_config()
        assert isinstance(config, GlideClientConfiguration)

    def test_cluster_tls_uses_correct_advanced_config(self, tmp_path):
        ca_file = tmp_path / 'ca.pem'
        ca_file.write_bytes(b'fake-ca-cert')
        with patch(
            f'{MODULE}.VALKEY_CFG',
            {
                'host': 'cluster.example.com',
                'port': 6379,
                'password': '',
                'username': None,
                'ssl': True,
                'ssl_ca_certs': str(ca_file),
                'cluster_mode': True,
            },
        ):
            config = _build_config()
        assert isinstance(config, GlideClusterClientConfiguration)

    def test_standalone_tls_uses_correct_advanced_config(self, tmp_path):
        ca_file = tmp_path / 'ca.pem'
        ca_file.write_bytes(b'fake-ca-cert')
        with patch(
            f'{MODULE}.VALKEY_CFG',
            {
                'host': 'localhost',
                'port': 6379,
                'password': '',
                'username': None,
                'ssl': True,
                'ssl_ca_certs': str(ca_file),
                'cluster_mode': False,
            },
        ):
            config = _build_config()
        assert isinstance(config, GlideClientConfiguration)


class TestGetClient:
    async def test_creates_standalone_client(self):
        mock_client = AsyncMock()
        with (
            patch(
                f'{MODULE}._build_config', return_value=MagicMock(spec=GlideClientConfiguration)
            ),
            patch(f'{MODULE}.GlideClient') as mock_cls,
        ):
            mock_cls.create = AsyncMock(return_value=mock_client)
            client = await get_client()
        assert client is mock_client

    async def test_returns_cached_client(self):
        mock_client = AsyncMock()
        with (
            patch(
                f'{MODULE}._build_config', return_value=MagicMock(spec=GlideClientConfiguration)
            ),
            patch(f'{MODULE}.GlideClient') as mock_cls,
        ):
            mock_cls.create = AsyncMock(return_value=mock_client)
            c1 = await get_client()
            c2 = await get_client()
        assert c1 is c2
        mock_cls.create.assert_called_once()

    async def test_creates_cluster_client(self):
        mock_client = AsyncMock()
        with (
            patch(
                f'{MODULE}._build_config',
                return_value=MagicMock(spec=GlideClusterClientConfiguration),
            ),
            patch(f'{MODULE}.GlideClusterClient') as mock_cls,
        ):
            mock_cls.create = AsyncMock(return_value=mock_client)
            client = await get_client()
        assert client is mock_client


class TestCloseClient:
    async def test_close_noop_when_no_client(self):
        await close_client()  # should not raise

    async def test_close_calls_client_close(self):
        mock_client = AsyncMock()
        with (
            patch(
                f'{MODULE}._build_config', return_value=MagicMock(spec=GlideClientConfiguration)
            ),
            patch(f'{MODULE}.GlideClient') as mock_cls,
        ):
            mock_cls.create = AsyncMock(return_value=mock_client)
            await get_client()
        await close_client()
        mock_client.close.assert_called_once()


class TestResetClient:
    async def test_reset_allows_new_client(self):
        mock1 = AsyncMock()
        mock2 = AsyncMock()
        with (
            patch(
                f'{MODULE}._build_config', return_value=MagicMock(spec=GlideClientConfiguration)
            ),
            patch(f'{MODULE}.GlideClient') as mock_cls,
        ):
            mock_cls.create = AsyncMock(side_effect=[mock1, mock2])
            c1 = await get_client()
            await reset_client()
            c2 = await get_client()
        assert c1 is not c2
