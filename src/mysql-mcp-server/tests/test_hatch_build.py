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

These tests pin the build-hook contract: download the bundle, write it
to disk, skip the network call when the file is already there, and
emit an actionable error message on network failure.
"""

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


class TestFetch:
    """The download path: fetch + write + idempotency + error reporting."""

    def test_idempotent_skip_when_file_exists(self, tmp_path):
        """If the file is already on disk, no network call is made."""
        path = tmp_path / 'bundle.pem'
        path.write_bytes(b'pre-existing')

        with patch.object(hatch_build.urllib.request, 'urlopen') as mock_urlopen:
            result = hatch_build.fetch(str(path))

        assert mock_urlopen.call_count == 0, (
            'fetch() made a network call when the file on disk already '
            'existed. The fast-path is broken.'
        )
        assert os.path.abspath(str(path)) == result

    def test_writes_downloaded_bundle(self, tmp_path):
        """Fresh download is written to the target path."""
        path = tmp_path / 'subdir' / 'bundle.pem'
        content = b'freshly-downloaded'

        mock_resp = MockUrlopenResponse(content)

        with patch.object(hatch_build.urllib.request, 'urlopen', return_value=mock_resp):
            result = hatch_build.fetch(str(path))

        assert os.path.exists(result)
        assert open(result, 'rb').read() == content

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
                hatch_build.fetch(str(path))

        msg = str(exc_info.value)
        assert 'curl' in msg
        assert hatch_build._RDS_CA_BUNDLE_URL in msg
        assert str(path.resolve()) in msg or os.path.abspath(str(path)) in msg

    def test_rejects_non_https_url(self, tmp_path, monkeypatch):
        """fetch() must refuse to call urlopen on any non-https URL.

        Defensive guard against a future bug that points _RDS_CA_BUNDLE_URL
        at file://, ftp://, or any other scheme urllib would happily accept.
        Bandit B310 was correct to flag this; the explicit check makes the
        invariant enforceable.
        """
        path = tmp_path / 'bundle.pem'
        # Point the constant at file:// so the guard fires before urlopen.
        monkeypatch.setattr(
            hatch_build,
            '_RDS_CA_BUNDLE_URL',
            'file:///etc/passwd',
        )

        with patch.object(hatch_build.urllib.request, 'urlopen') as mock_urlopen:
            with pytest.raises(RuntimeError, match='must use https://'):
                hatch_build.fetch(str(path))

        assert mock_urlopen.call_count == 0, (
            'fetch() must refuse non-https URLs before invoking urlopen, '
            'so a tampered constant cannot trigger a file:// read.'
        )


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
