# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
"""Tests for CA bundle loading and --ca_bundle override.

These tests guard the IAM-auth trust resolution path: which CA file ends
up trusted by the SSL context depending on whether the bundled PEM is
present and whether the operator passed --ca_bundle <path>.
"""

import os
from awslabs.mysql_mcp_server.connection import asyncmy_pool_connection as mod
from awslabs.mysql_mcp_server.connection.asyncmy_pool_connection import (
    AsyncmyPoolConnection,
    _bundled_ca_file,
)


class TestBundledCaFile:
    """Behaviour of the _bundled_ca_file() helper."""

    def test_bundle_file_exists(self):
        """The bundled PEM must ship with the package (fetched at build time)."""
        assert os.path.isfile(mod._RDS_CA_BUNDLE_PATH), (
            f'Bundled RDS CA missing at {mod._RDS_CA_BUNDLE_PATH}. '
            'Run `python hatch_build.py` to fetch it.'
        )

    def test_returns_path_when_file_present(self):
        """_bundled_ca_file returns the path when the file is on disk."""
        assert _bundled_ca_file() == mod._RDS_CA_BUNDLE_PATH

    def test_returns_none_when_file_missing(self, tmp_path, monkeypatch):
        """_bundled_ca_file returns None when the bundle file is absent."""
        monkeypatch.setattr(mod, '_RDS_CA_BUNDLE_PATH', str(tmp_path / 'nope.pem'))
        assert _bundled_ca_file() is None


class TestCaBundleOverride:
    """The --ca_bundle override path on the connection class."""

    def test_constructor_accepts_override(self, tmp_path):
        """ca_bundle_path should be stored on the instance."""
        pem = tmp_path / 'custom.pem'
        pem.write_text('')
        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='',
            db_user='u',
            region='us-east-1',
            is_iam_auth=True,
            is_test=True,
            ca_bundle_path=str(pem),
        )
        assert conn.ca_bundle_path == str(pem)

    def test_constructor_default_is_none(self):
        """Without an override, ca_bundle_path is None so the bundled PEM is used."""
        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='',
            db_user='u',
            region='us-east-1',
            is_iam_auth=True,
            is_test=True,
        )
        assert conn.ca_bundle_path is None


class TestCaBundleSslContextWiring:
    """Verify which CA file ends up trusted by the SSL context during pool init.

    The IAM auth code has a three-step trust resolution chain:
      1. --ca_bundle override
      2. bundled RDS CA (fetched at build time)
      3. system trust store (warned)

    These tests pin which branch is taken in each scenario so a regression
    that silently changes the trust resolution gets caught.
    """

    @staticmethod
    def _make_iam_conn(**overrides):
        kwargs = {
            'host': 'mydb.cluster-xyz.us-east-1.rds.amazonaws.com',
            'port': 3306,
            'database': 'testdb',
            'readonly': False,
            'secret_arn': '',
            'db_user': 'admin',
            'region': 'us-east-1',
            'is_iam_auth': True,
            'is_test': True,
        }
        kwargs.update(overrides)
        return AsyncmyPoolConnection(**kwargs)

    async def test_override_takes_precedence_over_bundled(self, tmp_path, monkeypatch):
        """Operator-provided --ca_bundle wins even when the bundled file exists."""
        from unittest.mock import AsyncMock, MagicMock, patch

        override = tmp_path / 'override.pem'
        override.write_text(
            '-----BEGIN CERTIFICATE-----\nFAKE-OVERRIDE\n-----END CERTIFICATE-----\n'
        )
        # Also make _bundled_ca_file() succeed without depending on the
        # build-hook-fetched PEM, which is absent in fresh CI checkouts.
        bundled = tmp_path / 'bundled.pem'
        bundled.write_text(
            '-----BEGIN CERTIFICATE-----\nFAKE-BUNDLED\n-----END CERTIFICATE-----\n'
        )
        monkeypatch.setattr(mod, '_RDS_CA_BUNDLE_PATH', str(bundled))

        captured = {}

        def fake_create_default_context(cafile=None):
            captured['cafile'] = cafile
            return MagicMock()

        monkeypatch.setattr(mod.ssl_module, 'create_default_context', fake_create_default_context)
        # initialize_pool() calls get_iam_auth_token() which hits boto3+RDS
        # to mint a real auth token. CI runners have no AWS credentials,
        # so we short-circuit that call to keep the test focused on the
        # SSL trust-chain wiring under test.
        with (
            patch.object(
                AsyncmyPoolConnection,
                'get_iam_auth_token',
                return_value='fake-iam-token',
            ),
            patch.object(mod.asyncmy, 'create_pool', new_callable=AsyncMock),
        ):
            conn = self._make_iam_conn(ca_bundle_path=str(override))
            await conn.initialize_pool()

        assert captured['cafile'] == str(override), (
            'Override --ca_bundle path was not used; the trust chain may have '
            'silently fallen through to the bundled or system store.'
        )

    async def test_bundled_used_when_override_absent(self, tmp_path, monkeypatch):
        """With no override and a present bundled file, the bundled path is used."""
        from unittest.mock import AsyncMock, MagicMock, patch

        # Point the module at a temp file the test creates so this test does
        # not depend on the build-hook-fetched PEM being present on disk
        # (CI checkouts run pytest without first building the wheel).
        bundled = tmp_path / 'bundled.pem'
        bundled.write_text(
            '-----BEGIN CERTIFICATE-----\nFAKE-BUNDLED\n-----END CERTIFICATE-----\n'
        )
        monkeypatch.setattr(mod, '_RDS_CA_BUNDLE_PATH', str(bundled))

        captured = {}

        def fake_create_default_context(cafile=None):
            captured['cafile'] = cafile
            return MagicMock()

        monkeypatch.setattr(mod.ssl_module, 'create_default_context', fake_create_default_context)
        with (
            patch.object(
                AsyncmyPoolConnection,
                'get_iam_auth_token',
                return_value='fake-iam-token',
            ),
            patch.object(mod.asyncmy, 'create_pool', new_callable=AsyncMock),
        ):
            conn = self._make_iam_conn()
            await conn.initialize_pool()

        assert captured['cafile'] == str(bundled), (
            'Expected the bundled RDS CA path to be passed to '
            'ssl.create_default_context when no override is provided.'
        )

    async def test_system_store_fallback_when_bundle_missing(self, tmp_path, monkeypatch):
        """If the bundled file is absent, fall back to the system store.

        This exercises the warning path: connection still attempts to come up,
        but with no explicit cafile so the operator can recover by providing
        --ca_bundle on the next start, or by rebuilding the package to refetch
        the bundle.
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        # Point the module at a missing path so _bundled_ca_file() returns None
        monkeypatch.setattr(mod, '_RDS_CA_BUNDLE_PATH', str(tmp_path / 'missing.pem'))

        captured: dict = {'cafile': 'sentinel-not-set'}

        def fake_create_default_context(cafile=None):
            captured['cafile'] = cafile
            return MagicMock()

        monkeypatch.setattr(mod.ssl_module, 'create_default_context', fake_create_default_context)
        with (
            patch.object(
                AsyncmyPoolConnection,
                'get_iam_auth_token',
                return_value='fake-iam-token',
            ),
            patch.object(mod.asyncmy, 'create_pool', new_callable=AsyncMock),
        ):
            conn = self._make_iam_conn()
            await conn.initialize_pool()

        assert captured['cafile'] is None, (
            'When the bundled file is missing, create_default_context must be '
            'called with no cafile so the system trust store is used (warned).'
        )

    async def test_no_ssl_context_for_non_iam(self, monkeypatch):
        """Non-IAM connections must not configure an SSL context.

        Setting an SSL context on `mysqlwire` (no IAM) connections would
        force-upgrade them to TLS, which can break installations relying on
        plaintext or server-certificate-managed TLS.
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        captured = {'ssl_calls': 0}

        def fake_create_default_context(cafile=None):
            captured['ssl_calls'] += 1
            return MagicMock()

        monkeypatch.setattr(mod.ssl_module, 'create_default_context', fake_create_default_context)
        with patch.object(mod.asyncmy, 'create_pool', new_callable=AsyncMock) as mock_pool:
            conn = AsyncmyPoolConnection(
                host='localhost',
                port=3306,
                database='testdb',
                readonly=True,
                secret_arn='arn:secret',
                db_user='',
                region='us-east-1',
                is_iam_auth=False,
                is_test=True,
            )
            await conn.initialize_pool()

        assert captured['ssl_calls'] == 0, (
            'create_default_context was called for a non-IAM connection. '
            'mysqlwire must remain plaintext-capable.'
        )
        assert mock_pool.call_args.kwargs['ssl'] is None
