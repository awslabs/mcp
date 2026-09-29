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

"""Tests for the AWS CA bundle build hook (hatch_build.py).

Covers the integrity/atomicity fixes: validity check instead of existence
check, atomic write, per-source PEM + pinned-root-SHA validation, force-refresh
for release builds, and the offline fallback that never accepts a corrupt file.
"""

import hashlib
import hatch_build
import os
import pytest


def _pem_with(n: int) -> bytes:
    """Return bytes containing ``n`` PEM certificate blocks."""
    block = b'-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n'
    return block * n


# --- _count_certs / _is_valid_bundle ----------------------------------------


def test_count_certs():
    """_count_certs counts BEGIN CERTIFICATE markers."""
    assert hatch_build._count_certs(_pem_with(0)) == 0
    assert hatch_build._count_certs(_pem_with(3)) == 3


def test_is_valid_bundle_accepts_full_bundle(tmp_path):
    """A file with enough certs is considered valid."""
    p = tmp_path / 'bundle.pem'
    p.write_bytes(_pem_with(hatch_build._MIN_CERTS_IN_BUNDLE + 5))
    assert hatch_build._is_valid_bundle(str(p)) is True


@pytest.mark.parametrize('n', [0, 1, hatch_build._MIN_CERTS_IN_BUNDLE - 1])
def test_is_valid_bundle_rejects_truncated(tmp_path, n):
    """Empty / truncated files (below the cert floor) are invalid."""
    p = tmp_path / 'bundle.pem'
    p.write_bytes(_pem_with(n))
    assert hatch_build._is_valid_bundle(str(p)) is False


def test_is_valid_bundle_missing_file(tmp_path):
    """A missing file is invalid (not an error)."""
    assert hatch_build._is_valid_bundle(str(tmp_path / 'nope.pem')) is False


# --- _verify_source ---------------------------------------------------------


def test_verify_source_rejects_non_pem():
    """A source returning non-PEM data (e.g. an error page) is rejected."""
    with pytest.raises(hatch_build.BundleIntegrityError):
        hatch_build._verify_source('https://example/x.pem', b'<html>captive portal</html>')


def test_verify_source_pinned_root_mismatch(monkeypatch):
    """A pinned Amazon root whose SHA-256 does not match is rejected."""
    url = 'https://www.amazontrust.com/repository/AmazonRootCA1.pem'
    monkeypatch.setitem(hatch_build._AMAZON_ROOT_CA_SHA256, url, 'deadbeef')
    with pytest.raises(hatch_build.BundleIntegrityError, match='SHA-256 mismatch'):
        hatch_build._verify_source(url, _pem_with(1))


def test_verify_source_pinned_root_match(monkeypatch):
    """A pinned Amazon root whose SHA-256 matches passes."""
    url = 'https://www.amazontrust.com/repository/AmazonRootCA1.pem'
    chunk = _pem_with(1)
    monkeypatch.setitem(hatch_build._AMAZON_ROOT_CA_SHA256, url, hashlib.sha256(chunk).hexdigest())
    hatch_build._verify_source(url, chunk)  # no raise


def test_verify_source_unpinned_source_only_needs_pem():
    """The (unpinned) RDS bundle only needs to be valid PEM."""
    hatch_build._verify_source(hatch_build._RDS_CA_BUNDLE_URL, _pem_with(50))


# --- _assemble_bundle -------------------------------------------------------


def test_assemble_bundle_rejects_too_few_certs(monkeypatch):
    """A bundle assembled below the cert floor is rejected."""
    # Clear pins so the fake bytes exercise the cert-count path, not SHA checks.
    monkeypatch.setattr(hatch_build, '_AMAZON_ROOT_CA_SHA256', {})
    monkeypatch.setattr(hatch_build, '_fetch_url', lambda url, ctx: _pem_with(1))
    with pytest.raises(hatch_build.BundleIntegrityError, match='too few certificates'):
        hatch_build._assemble_bundle(ctx=None)


def test_assemble_bundle_success(monkeypatch):
    """A healthy set of sources assembles into a valid bundle."""
    monkeypatch.setattr(hatch_build, '_AMAZON_ROOT_CA_SHA256', {})
    monkeypatch.setattr(hatch_build, '_fetch_url', lambda url, ctx: _pem_with(40))
    content = hatch_build._assemble_bundle(ctx=None)
    assert hatch_build._count_certs(content) >= hatch_build._MIN_CERTS_IN_BUNDLE


# --- _atomic_write ----------------------------------------------------------


def test_atomic_write_creates_file_and_no_temp_left(tmp_path):
    """Atomic write creates the file (and parent dir) with no leftover temp."""
    target = tmp_path / 'sub' / 'bundle.pem'
    hatch_build._atomic_write(str(target), b'hello')
    assert target.read_bytes() == b'hello'
    assert [f for f in os.listdir(target.parent) if f.endswith('.tmp')] == []


def test_atomic_write_preserves_original_on_failure(tmp_path, monkeypatch):
    """If the replace fails, the original file is intact and no temp remains."""
    target = tmp_path / 'bundle.pem'
    target.write_bytes(b'ORIGINAL')

    def boom(src, dst):
        raise OSError('replace failed')

    monkeypatch.setattr(hatch_build.os, 'replace', boom)
    with pytest.raises(OSError):
        hatch_build._atomic_write(str(target), b'NEW')
    assert target.read_bytes() == b'ORIGINAL'
    assert [f for f in os.listdir(tmp_path) if f.endswith('.tmp')] == []


# --- fetch: reuse / refresh / fallback --------------------------------------


def test_fetch_reuses_valid_existing_without_network(tmp_path, monkeypatch):
    """Without force_refresh, a valid on-disk file is reused with no fetch."""
    p = tmp_path / 'bundle.pem'
    p.write_bytes(_pem_with(hatch_build._MIN_CERTS_IN_BUNDLE + 1))

    def fail(*a, **k):
        raise AssertionError('network must not be touched when a valid file exists')

    monkeypatch.setattr(hatch_build, '_assemble_bundle', fail)
    assert hatch_build.fetch(str(p)) == os.path.abspath(str(p))


def test_fetch_refetches_when_existing_is_invalid(tmp_path, monkeypatch):
    """An invalid on-disk file is not reused; a fresh bundle is fetched."""
    p = tmp_path / 'bundle.pem'
    p.write_bytes(_pem_with(1))  # invalid (too few)
    fresh = _pem_with(hatch_build._MIN_CERTS_IN_BUNDLE + 2)
    monkeypatch.setattr(hatch_build, '_assemble_bundle', lambda ctx: fresh)
    monkeypatch.setattr(hatch_build, '_ssl_context_for_aws_endpoint', lambda: None)
    hatch_build.fetch(str(p))
    assert p.read_bytes() == fresh


def test_fetch_force_refresh_always_refetches(tmp_path, monkeypatch):
    """force_refresh re-fetches even when a valid (stale) file exists."""
    p = tmp_path / 'bundle.pem'
    p.write_bytes(_pem_with(hatch_build._MIN_CERTS_IN_BUNDLE + 1))  # valid but stale
    fresh = _pem_with(hatch_build._MIN_CERTS_IN_BUNDLE + 9)
    monkeypatch.setattr(hatch_build, '_assemble_bundle', lambda ctx: fresh)
    monkeypatch.setattr(hatch_build, '_ssl_context_for_aws_endpoint', lambda: None)
    hatch_build.fetch(str(p), force_refresh=True)
    assert p.read_bytes() == fresh


def test_fetch_offline_falls_back_to_valid_existing(tmp_path, monkeypatch, capsys):
    """A network failure falls back to a valid existing file, with a warning."""
    p = tmp_path / 'bundle.pem'
    valid = _pem_with(hatch_build._MIN_CERTS_IN_BUNDLE + 1)
    p.write_bytes(valid)

    def offline(ctx):
        raise OSError('no network')

    monkeypatch.setattr(hatch_build, '_assemble_bundle', offline)
    monkeypatch.setattr(hatch_build, '_ssl_context_for_aws_endpoint', lambda: None)
    assert hatch_build.fetch(str(p), force_refresh=True) == os.path.abspath(str(p))
    assert p.read_bytes() == valid
    assert 'reusing the existing valid bundle' in capsys.readouterr().err


def test_fetch_offline_without_existing_raises(tmp_path, monkeypatch):
    """A network failure with no valid existing file raises a helpful error."""
    p = tmp_path / 'bundle.pem'  # does not exist

    def offline(ctx):
        raise OSError('no network')

    monkeypatch.setattr(hatch_build, '_assemble_bundle', offline)
    monkeypatch.setattr(hatch_build, '_ssl_context_for_aws_endpoint', lambda: None)
    with pytest.raises(RuntimeError, match='Failed to fetch the AWS CA bundle'):
        hatch_build.fetch(str(p), force_refresh=True)


def test_fetch_integrity_error_not_masked_by_existing(tmp_path, monkeypatch):
    """An integrity failure surfaces even when a valid existing file is present."""
    p = tmp_path / 'bundle.pem'
    p.write_bytes(_pem_with(hatch_build._MIN_CERTS_IN_BUNDLE + 1))  # valid existing

    def tampered(ctx):
        raise hatch_build.BundleIntegrityError('SHA-256 mismatch for pinned root')

    monkeypatch.setattr(hatch_build, '_assemble_bundle', tampered)
    monkeypatch.setattr(hatch_build, '_ssl_context_for_aws_endpoint', lambda: None)
    with pytest.raises(hatch_build.BundleIntegrityError):
        hatch_build.fetch(str(p), force_refresh=True)
