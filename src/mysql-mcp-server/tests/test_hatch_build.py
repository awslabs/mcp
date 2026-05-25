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

"""Tests for the hatch_build.py build hook.

These tests pin the build-hook contract: hash verification on every fetch,
idempotent fast-path when the file is already on disk with the correct hash,
and a clean error message on network failure that points at the curl
recovery command. The hook is security-critical — it controls which CA
chain ends up inside the published wheel — so regressions here would
silently change the package's trust posture.
"""

import hashlib
import hatch_build
import os
import pytest
from unittest.mock import patch


class MockUrlopenResponse:
    """Minimal context-manager-shaped fake for urllib.request.urlopen().

    The real `urlopen()` returns an object whose protocol is roughly
    `with urlopen(url) as resp: resp.read()`. Python looks up the
    context-manager dunders on the *type*, so a class-based fake is
    required — instance-attribute __enter__/__exit__ won't work.
    """

    def __init__(self, content: bytes) -> None:
        """Store the content the fake `read()` should return."""
        self._content = content

    def __enter__(self):
        """Enter the context manager and return self."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit without suppressing exceptions."""
        return False

    def read(self) -> bytes:
        """Return the bytes provided at construction time."""
        return self._content


class TestVerifyExisting:
    """The idempotent fast-path: existing file with matching hash, no network."""

    def test_returns_true_when_hash_matches(self, tmp_path, monkeypatch):
        """Existing file whose SHA-256 matches the pin should short-circuit."""
        path = tmp_path / 'rds_global_bundle.pem'
        content = b'matching-content'
        path.write_bytes(content)
        monkeypatch.setattr(
            hatch_build, '_RDS_CA_BUNDLE_SHA256', hashlib.sha256(content).hexdigest()
        )
        assert hatch_build._verify_existing(str(path)) is True

    def test_returns_false_when_hash_mismatches(self, tmp_path, monkeypatch):
        """File on disk whose SHA-256 does not match the pin must trigger a fetch."""
        path = tmp_path / 'rds_global_bundle.pem'
        path.write_bytes(b'wrong-content')
        monkeypatch.setattr(
            hatch_build, '_RDS_CA_BUNDLE_SHA256', hashlib.sha256(b'expected').hexdigest()
        )
        assert hatch_build._verify_existing(str(path)) is False

    def test_returns_false_when_file_missing(self, tmp_path):
        """Missing file means we cannot short-circuit."""
        assert hatch_build._verify_existing(str(tmp_path / 'does-not-exist.pem')) is False


class TestFetchAndVerify:
    """The download path: hash verification, network error wrapping."""

    def test_idempotent_skip_when_already_verified(self, tmp_path, monkeypatch):
        """If the file already matches the pin, no network call is made."""
        path = tmp_path / 'bundle.pem'
        content = b'pre-existing'
        path.write_bytes(content)
        monkeypatch.setattr(
            hatch_build, '_RDS_CA_BUNDLE_SHA256', hashlib.sha256(content).hexdigest()
        )

        with patch.object(hatch_build.urllib.request, 'urlopen') as mock_urlopen:
            result = hatch_build.fetch_and_verify(str(path))

        assert mock_urlopen.call_count == 0, (
            'fetch_and_verify made a network call when the file on disk '
            'already had the correct hash. The fast-path is broken.'
        )
        assert os.path.abspath(str(path)) == result

    def test_writes_bundle_when_hash_matches(self, tmp_path, monkeypatch):
        """Fresh download whose hash matches the pin is written to the target path."""
        path = tmp_path / 'subdir' / 'bundle.pem'
        content = b'freshly-downloaded'
        monkeypatch.setattr(
            hatch_build, '_RDS_CA_BUNDLE_SHA256', hashlib.sha256(content).hexdigest()
        )

        mock_resp = MockUrlopenResponse(content)

        with patch.object(hatch_build.urllib.request, 'urlopen', return_value=mock_resp):
            result = hatch_build.fetch_and_verify(str(path))

        assert os.path.exists(result)
        assert open(result, 'rb').read() == content

    def test_hash_mismatch_raises_with_actionable_message(self, tmp_path, monkeypatch):
        """Hash mismatch must fail loudly with the new hash printed for review."""
        path = tmp_path / 'bundle.pem'
        downloaded = b'rotated-bundle'
        downloaded_digest = hashlib.sha256(downloaded).hexdigest()
        monkeypatch.setattr(
            hatch_build,
            '_RDS_CA_BUNDLE_SHA256',
            'e' * 64,  # any value other than downloaded_digest
        )

        mock_resp = MockUrlopenResponse(downloaded)

        with patch.object(hatch_build.urllib.request, 'urlopen', return_value=mock_resp):
            with pytest.raises(RuntimeError) as exc_info:
                hatch_build.fetch_and_verify(str(path))

        msg = str(exc_info.value)
        assert 'hash mismatch' in msg.lower()
        assert downloaded_digest in msg, (
            'Hash-mismatch error must include the actually-downloaded SHA-256 '
            'so the reviewer can paste it into the pin without rerunning curl.'
        )
        assert hatch_build._RDS_CA_BUNDLE_URL in msg
        assert not path.exists(), (
            'A file that fails hash verification must NOT be written to disk; '
            'doing so would let a tampered bundle leak into the build output '
            'on a retry.'
        )

    def test_network_error_includes_curl_recovery_hint(self, tmp_path):
        """Network failure error message must include a curl one-liner.

        The hook runs in build environments where the developer cannot edit
        the hook source; the error has to teach the recovery path inline.
        """
        path = tmp_path / 'bundle.pem'

        with patch.object(
            hatch_build.urllib.request,
            'urlopen',
            side_effect=OSError('SSL: CERTIFICATE_VERIFY_FAILED'),
        ):
            with pytest.raises(RuntimeError) as exc_info:
                hatch_build.fetch_and_verify(str(path))

        msg = str(exc_info.value)
        assert 'curl' in msg
        assert hatch_build._RDS_CA_BUNDLE_URL in msg
        assert str(path.resolve()) in msg or os.path.abspath(str(path)) in msg


class TestSslContext:
    """Builder for the SSL context used during the fetch."""

    def test_falls_back_to_default_when_certifi_missing(self, monkeypatch):
        """If certifi isn't installed, return a default context (system store)."""
        # Force ImportError on `import certifi` inside the helper
        import builtins

        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == 'certifi':
                raise ImportError('simulated: certifi not installed')
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, '__import__', fake_import)

        ctx = hatch_build._ssl_context_for_aws_endpoint()
        # Cannot easily check internal cafile of a default context, but at
        # least confirm we got an SSLContext back rather than crashing.
        import ssl

        assert isinstance(ctx, ssl.SSLContext)

    def test_uses_certifi_when_available(self):
        """When certifi is importable, the context loads its CA bundle."""
        certifi = pytest.importorskip('certifi')
        ctx = hatch_build._ssl_context_for_aws_endpoint()

        import ssl

        assert isinstance(ctx, ssl.SSLContext)
        # Verify the CA store is non-empty (certifi ships hundreds of roots).
        # This is a coarse check, but proves create_default_context(cafile=...)
        # was invoked rather than a default no-arg context.
        ca_count = ctx.cert_store_stats()['x509_ca']
        assert ca_count > 0, (
            'Expected certifi-backed context to load CA roots; got empty store. '
            f'certifi.where()={certifi.where()}'
        )
